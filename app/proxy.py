"""Core proxy: forward requests to Cocoon upstream."""

import json
import logging
import time

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth import verify_api_key
from app.billing import calculate_cost_nanoton, check_balance, deduct_balance
from app.config import settings

logger = logging.getLogger("cocoon_proxy")

router = APIRouter(prefix="/v1")

# Model metadata for enriching /v1/models responses
MODEL_META = {
    "Qwen/Qwen3-32B": {
        "owned_by": "Alibaba",
        "endpoint": "/v1/chat/completions",
        "type": "chat",
        "context_window": 131072,
    },
    "ByteDance-Seed/Seed-X-PPO-7B": {
        "owned_by": "ByteDance",
        "endpoint": "/v1/completions",
        "type": "translation",
        "context_window": 8192,
    },
}

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
    """List available AI models on the Cocoon network with worker and load info, endpoint type, context window, and ownership. No auth required."""
    client = await get_client()
    resp = await client.get("/v1/models")
    data = resp.json()
    # Enrich with metadata
    for model in data.get("data", []):
        meta = MODEL_META.get(model.get("id"), {})
        model["owned_by"] = meta.get("owned_by", "unknown")
        model["endpoint"] = meta.get("endpoint", "/v1/chat/completions")
        model["type"] = meta.get("type", "chat")
        model["context_window"] = meta.get("context_window", None)
    return JSONResponse(content=data, status_code=resp.status_code)


@router.post("/chat/completions")
async def chat_completions(request: Request, user: dict = Depends(verify_api_key)):
    """Send messages to an AI model and receive a response. Supports streaming (stream: true) and non-streaming. Requires funded API key. Cost deducted per-token after completion."""
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

    # If upstream returned an error, pass it through as JSON (not SSE)
    if upstream_resp.status_code != 200:
        error_body = await upstream_resp.aread()
        await upstream_resp.aclose()
        try:
            error_data = json.loads(error_body)
            # Normalize error format
            if "error" not in error_data and "message" in error_data:
                error_data = {"error": {"message": error_data["message"],
                                        "type": error_data.get("type", "upstream_error"),
                                        "param": None, "code": None}}
        except (json.JSONDecodeError, KeyError):
            error_data = {"error": {"message": "Upstream error", "type": "upstream_error",
                                    "param": None, "code": None}}
        return JSONResponse(content=error_data, status_code=upstream_resp.status_code)

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


@router.post("/completions")
async def text_completions(request: Request, user: dict = Depends(verify_api_key)):
    """Send a text prompt to an AI model and receive a completion. Use for models without chat templates (e.g. ByteDance-Seed/Seed-X-PPO-7B translation model). Requires funded API key. Cost deducted per-token after completion."""
    await check_balance(user)

    body = await request.json()

    # Validate required fields
    if "model" not in body or "prompt" not in body:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "model and prompt are required",
                               "type": "invalid_request_error", "param": None, "code": None}},
        )

    # Cap max_tokens
    if body.get("max_tokens", 0) > settings.max_tokens_cap:
        body["max_tokens"] = settings.max_tokens_cap

    is_streaming = body.get("stream", False)

    if is_streaming:
        body.setdefault("stream_options", {})["include_usage"] = True

    client = await get_client()
    model = body.get("model", "unknown")

    if not is_streaming:
        resp = await client.post("/v1/completions", json=body)
        data = resp.json()

        if resp.status_code == 200 and "usage" in data:
            usage = data["usage"]
            cost = calculate_cost_nanoton(usage)
            await deduct_balance(user["id"], cost, usage, model)
            logger.info("completion_completed", extra={
                "user_id": user["id"], "model": model,
                "tokens": usage.get("total_tokens", 0), "cost_nanoton": cost,
            })

        return JSONResponse(content=data, status_code=resp.status_code)

    # Streaming
    upstream_req = client.build_request("POST", "/v1/completions", json=body)
    upstream_resp = await client.send(upstream_req, stream=True)

    if upstream_resp.status_code != 200:
        error_body = await upstream_resp.aread()
        await upstream_resp.aclose()
        try:
            error_data = json.loads(error_body)
            if "error" not in error_data and "message" in error_data:
                error_data = {"error": {"message": error_data["message"],
                                        "type": error_data.get("type", "upstream_error"),
                                        "param": None, "code": None}}
        except (json.JSONDecodeError, KeyError):
            error_data = {"error": {"message": "Upstream error", "type": "upstream_error",
                                    "param": None, "code": None}}
        return JSONResponse(content=error_data, status_code=upstream_resp.status_code)

    async def stream_completions():
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
                logger.info("completion_stream_completed", extra={
                    "user_id": user["id"], "model": model,
                    "tokens": usage_data.get("total_tokens", 0), "cost_nanoton": cost,
                })

    return StreamingResponse(
        stream_completions(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_balance_rate_cache = {"rate": None, "ts": 0}

async def _get_ton_usd():
    """Get cached TON/USD rate for balance display."""
    if _balance_rate_cache["rate"] and time.time() - _balance_rate_cache["ts"] < 120:
        return _balance_rate_cache["rate"]
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get("https://tonapi.io/v2/rates?tokens=ton&currencies=usd")
            rate = float(r.json()["rates"]["TON"]["prices"]["USD"])
            _balance_rate_cache["rate"] = rate
            _balance_rate_cache["ts"] = time.time()
            return rate
    except Exception:
        return _balance_rate_cache["rate"]


@router.get("/balance")
async def get_balance(user: dict = Depends(verify_api_key)):
    """Check current TON balance for the authenticated user. Returns balance in TON, nanoton, and USD equivalent."""
    balance_nanoton = user["balance_nanoton"]
    balance_ton = balance_nanoton / 1e9
    ton_usd = await _get_ton_usd()
    result = {
        "balance_ton": balance_ton,
        "balance_nanoton": balance_nanoton,
    }
    if ton_usd:
        result["balance_usd"] = round(balance_ton * ton_usd, 4)
        result["ton_usd_rate"] = ton_usd
    return result


@router.get("/deposit")
async def get_deposit_info(user: dict = Depends(verify_api_key)):
    """Get TON deposit wallet address and unique memo code. Send TON to the wallet with the memo to credit your account. Auto-detected within ~30 seconds."""
    return {
        "wallet": settings.deposit_wallet,
        "memo": user["deposit_code"],
        "instructions": (
            f"Send TON to {settings.deposit_wallet} with the comment/memo: {user['deposit_code']}. "
            "Your balance will be credited automatically within ~30 seconds."
        ),
    }
