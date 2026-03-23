"""Core proxy: forward requests to Cocoon upstream."""

import json
import logging

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth import verify_api_key
from app.billing import calculate_cost_nanoton, check_balance, deduct_balance
from app.config import settings

logger = logging.getLogger("cocoon_proxy")

router = APIRouter(prefix="/v1")

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.cocoon_upstream_url,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )
    return _client


async def close_client():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


@router.get("/models")
async def list_models():
    """Passthrough to upstream /v1/models."""
    client = await get_client()
    resp = await client.get("/v1/models")
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@router.post("/chat/completions")
async def chat_completions(request: Request, user: dict = Depends(verify_api_key)):
    """Proxy chat completions with billing."""
    await check_balance(user)

    body = await request.json()

    # Validate required fields
    if "model" not in body or "messages" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "model and messages are required",
                               "type": "invalid_request_error", "param": None, "code": None}},
        )

    # Cap max_tokens
    if body.get("max_tokens", 0) > settings.max_tokens_cap:
        body["max_tokens"] = settings.max_tokens_cap

    is_streaming = body.get("stream", False)

    # Force usage reporting for streaming
    if is_streaming:
        body.setdefault("stream_options", {})["include_usage"] = True

    client = await get_client()
    model = body.get("model", "unknown")

    if not is_streaming:
        resp = await client.post("/v1/chat/completions", json=body)
        data = resp.json()

        if resp.status_code == 200 and "usage" in data:
            usage = data["usage"]
            cost = calculate_cost_nanoton(usage)
            await deduct_balance(user["id"], cost, usage, model)
            logger.info("request_completed", extra={
                "user_id": user["id"], "model": model,
                "tokens": usage.get("total_tokens", 0), "cost_nanoton": cost,
            })

        return JSONResponse(content=data, status_code=resp.status_code)

    # Streaming
    upstream_req = client.build_request("POST", "/v1/chat/completions", json=body)
    upstream_resp = await client.send(upstream_req, stream=True)

    async def stream_and_bill():
        usage_data = None
        try:
            async for line in upstream_resp.aiter_lines():
                yield line + "\n"
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        if chunk.get("usage"):
                            usage_data = chunk["usage"]
                    except (json.JSONDecodeError, KeyError):
                        pass
        finally:
            await upstream_resp.aclose()
            if usage_data:
                cost = calculate_cost_nanoton(usage_data)
                await deduct_balance(user["id"], cost, usage_data, model)
                logger.info("stream_completed", extra={
                    "user_id": user["id"], "model": model,
                    "tokens": usage_data.get("total_tokens", 0), "cost_nanoton": cost,
                })

    return StreamingResponse(
        stream_and_bill(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/balance")
async def get_balance(user: dict = Depends(verify_api_key)):
    """Return current user balance."""
    balance_nanoton = user["balance_nanoton"]
    return {
        "balance_ton": balance_nanoton / 1e9,
        "balance_nanoton": balance_nanoton,
    }


@router.get("/deposit")
async def get_deposit_info(user: dict = Depends(verify_api_key)):
    """Return deposit instructions for the user."""
    return {
        "wallet": settings.deposit_wallet,
        "memo": user["deposit_code"],
        "instructions": (
            f"Send TON to {settings.deposit_wallet} with the comment/memo: {user['deposit_code']}. "
            "Your balance will be credited automatically within ~30 seconds."
        ),
    }
