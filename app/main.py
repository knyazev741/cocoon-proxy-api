"""Cocoon API Proxy — main application."""

import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import get_db, close_db
from app.proxy import router as proxy_router, close_client
from app.auth import create_user, verify_api_key
from app.payments import payment_monitor_loop

# Configure logging — no content, only metadata
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cocoon_proxy")

app = FastAPI(
    title="Cocoon API Proxy",
    description="OpenAI-compatible paid API proxy for Cocoon decentralized AI network",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)

app.include_router(proxy_router)


_payment_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup():
    global _payment_task
    if not settings.deposit_wallet:
        logger.warning("COCOON_DEPOSIT_WALLET is not set — deposit and payment features will not work")
    await get_db()
    _payment_task = asyncio.create_task(payment_monitor_loop())
    logger.info("Cocoon API Proxy started, upstream=%s", settings.cocoon_upstream_url)


@app.on_event("shutdown")
async def shutdown():
    if _payment_task:
        _payment_task.cancel()
    await close_client()
    await close_db()
    logger.info("Cocoon API Proxy stopped")


@app.post("/v1/keys")
async def create_api_key(request: Request):
    """Create a new API key. Requires admin token if configured."""
    if settings.admin_token:
        auth = request.headers.get("authorization", "")
        if auth != f"Bearer {settings.admin_token}":
            return JSONResponse(
                status_code=403,
                content={"error": {"message": "Admin token required",
                                   "type": "auth_error", "param": None, "code": "forbidden"}},
            )

    result = await create_user()
    return JSONResponse(content=result, status_code=201)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def safe_error_handler(request: Request, exc: Exception):
    """Never log request/response content in errors."""
    logger.error("request_error: path=%s error_type=%s error=%s",
                 request.url.path, type(exc).__name__, str(exc)[:200])
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "Internal server error",
                           "type": "server_error", "param": None, "code": "internal_error"}},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        access_log=False,
    )
