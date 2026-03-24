"""MCP Server for Cocoon API Proxy.

Wraps the Cocoon API Proxy REST endpoints as MCP tools for agent consumption.
Requires the Cocoon API Proxy to be running (default: http://localhost:8000).
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

# Configuration
BASE_URL = os.environ.get("COCOON_PROXY_URL", "http://localhost:8000")
API_KEY = os.environ.get("COCOON_API_KEY", "")

mcp = FastMCP(
    "cocoon-api-proxy",
    version="0.1.0",
    description="MCP server for Cocoon API Proxy — query decentralized AI models on the Cocoon/TON network via OpenAI-compatible API.",
)


def _headers() -> dict:
    """Build auth headers."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def chat_completion(
    model: str,
    messages: list[dict],
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Send messages to a Cocoon AI model and get a text response. Returns the model's reply as plain text. Use when you need AI-generated text from decentralized models like Qwen/Qwen3-32B. Costs are deducted per-token from your account balance.

    Args:
        model: Model ID to use (e.g. 'Qwen/Qwen3-32B'). Get valid IDs from list_models.
        messages: Conversation messages as list of {role, content} dicts. Roles: 'system', 'user', 'assistant'.
        max_tokens: Maximum tokens to generate (1-128000, default 4096).
        temperature: Sampling temperature 0-2. Higher = more random. Default 0.7.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=300.0) as client:
        resp = await client.post(
            "/v1/chat/completions",
            headers=_headers(),
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            },
        )
        data = resp.json()
        if resp.status_code != 200:
            error = data.get("error", {})
            return json.dumps({"error": error.get("message", "Unknown error"), "code": error.get("code")})

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return json.dumps({
            "content": content,
            "model": data.get("model"),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "finish_reason": choice.get("finish_reason"),
        })


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def list_models() -> str:
    """List AI models available on the Cocoon network. Returns model IDs that can be used in chat_completion requests. Use when you need to discover which models are available before sending a query. No authentication required.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.get("/v1/models")
        data = resp.json()
        if resp.status_code != 200:
            return json.dumps({"error": "Failed to fetch models", "status": resp.status_code})
        models = [m.get("id", "unknown") for m in data.get("data", [])]
        return json.dumps({"models": models})


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def check_balance() -> str:
    """Check the current TON balance for your API key. Returns balance in TON and nanoton. Use before making chat_completion requests to verify you have sufficient funds (minimum 0.01 TON required). Requires COCOON_API_KEY environment variable.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.get("/v1/balance", headers=_headers())
        data = resp.json()
        if resp.status_code != 200:
            error = data.get("error", data.get("detail", {}).get("error", {}))
            return json.dumps({"error": error.get("message", "Auth failed"), "code": error.get("code")})
        return json.dumps(data)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def get_deposit_info() -> str:
    """Get TON wallet address and memo code for depositing funds to your account. Returns the wallet address and unique memo to include as transaction comment. Use when your balance is low and you need to add TON. Deposits are credited within ~30 seconds. Requires COCOON_API_KEY environment variable.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.get("/v1/deposit", headers=_headers())
        data = resp.json()
        if resp.status_code != 200:
            error = data.get("error", data.get("detail", {}).get("error", {}))
            return json.dumps({"error": error.get("message", "Auth failed"), "code": error.get("code")})
        return json.dumps(data)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
async def create_api_key() -> str:
    """Create a new API key and deposit code for a new Cocoon API Proxy account. The API key (ck_...) is shown once and cannot be retrieved again. Use when setting up a new user account. If admin token is configured on the server, requires COCOON_API_KEY to be set to the admin token.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        resp = await client.post("/v1/keys", headers=_headers())
        data = resp.json()
        if resp.status_code not in (200, 201):
            error = data.get("error", {})
            return json.dumps({"error": error.get("message", "Failed to create key"), "code": error.get("code")})
        return json.dumps(data)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def health_check() -> str:
    """Check if the Cocoon API Proxy service is running and healthy. Returns status 'ok' if the service is up. Use to verify connectivity before making other requests. No authentication required.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5.0) as client:
        try:
            resp = await client.get("/health")
            data = resp.json()
            return json.dumps({"status": data.get("status", "unknown"), "http_code": resp.status_code})
        except Exception as e:
            return json.dumps({"status": "unreachable", "error": str(e)})


if __name__ == "__main__":
    mcp.run()
