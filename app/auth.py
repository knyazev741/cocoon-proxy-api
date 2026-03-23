"""API key generation, storage, and validation."""

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Header, HTTPException

from app.database import get_db


def generate_api_key() -> str:
    """Generate a new API key: ck_<64 hex chars>."""
    return "ck_" + secrets.token_hex(32)


def hash_key(api_key: str) -> str:
    """SHA-256 hash of an API key."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_deposit_code() -> str:
    """Generate unique 8-char alphanumeric deposit code."""
    return secrets.token_urlsafe(6)[:8]


async def create_user() -> dict:
    """Create a new user with API key and deposit code. Returns plaintext key (shown once)."""
    db = await get_db()
    api_key = generate_api_key()
    key_hash = hash_key(api_key)
    deposit_code = generate_deposit_code()

    # Ensure deposit code uniqueness
    for _ in range(10):
        existing = await db.execute_fetchall(
            "SELECT 1 FROM users WHERE deposit_code = ?", (deposit_code,)
        )
        if not existing:
            break
        deposit_code = generate_deposit_code()

    await db.execute(
        "INSERT INTO users (api_key_hash, deposit_code) VALUES (?, ?)",
        (key_hash, deposit_code),
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT id, deposit_code, balance_nanoton, created_at FROM users WHERE api_key_hash = ?",
        (key_hash,),
    )
    user = await cursor.fetchone()

    return {
        "api_key": api_key,
        "deposit_code": user["deposit_code"],
        "balance_ton": user["balance_nanoton"] / 1e9,
        "created_at": user["created_at"],
    }


async def verify_api_key(authorization: str = Header(...)) -> dict:
    """Validate Bearer token and return user record."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Invalid authorization header. Use: Bearer ck_xxx",
                              "type": "invalid_auth", "param": None, "code": "invalid_api_key"}},
        )

    api_key = authorization[7:]
    if not api_key.startswith("ck_"):
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Invalid API key format",
                              "type": "invalid_auth", "param": None, "code": "invalid_api_key"}},
        )

    key_hash = hash_key(api_key)
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, deposit_code, balance_nanoton, created_at FROM users WHERE api_key_hash = ?",
        (key_hash,),
    )
    user = await cursor.fetchone()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Invalid API key",
                              "type": "invalid_auth", "param": None, "code": "invalid_api_key"}},
        )

    # Update last_used_at
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE users SET last_used_at = ? WHERE id = ?", (now, user["id"]))
    await db.commit()

    return dict(user)
