"""TON deposit monitoring via tonapi.io polling."""

import asyncio
import logging

import httpx

from app.config import settings
from app.database import get_db

logger = logging.getLogger("cocoon_proxy.payments")

# TonAPI base URL
TONAPI_BASE = "https://tonapi.io/v2"


async def get_ton_transactions(wallet: str, limit: int = 20) -> list:
    """Fetch recent transactions for wallet via TonAPI."""
    url = f"{TONAPI_BASE}/blockchain/accounts/{wallet}/transactions"
    params = {"limit": limit}
    headers = {}
    if settings.tonapi_key:
        headers["Authorization"] = f"Bearer {settings.tonapi_key}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            logger.error("tonapi_error: status=%d body=%s", resp.status_code, resp.text[:200])
            return []
        data = resp.json()
        return data.get("transactions", [])


def extract_comment(tx: dict) -> str:
    """Extract text comment from a TON transaction."""
    in_msg = tx.get("in_msg", {})
    # Try decoded_body first
    decoded = in_msg.get("decoded_body")
    if isinstance(decoded, dict):
        text = decoded.get("text", "")
        if text:
            return text.strip()
    # Try raw_body / decoded_op_name
    op_name = in_msg.get("decoded_op_name", "")
    if op_name == "text_comment":
        decoded = in_msg.get("decoded_body", {})
        if isinstance(decoded, dict):
            return decoded.get("text", "").strip()
    return ""


async def process_transaction(tx: dict):
    """Match transaction memo to a user and credit balance."""
    in_msg = tx.get("in_msg", {})
    value = in_msg.get("value", 0)
    if value <= 0:
        return

    tx_hash = tx.get("hash", "")
    if not tx_hash:
        return

    comment = extract_comment(tx)
    if not comment or len(comment) < 4:
        return

    db = await get_db()

    # Check if already processed
    existing = await db.execute_fetchall(
        "SELECT 1 FROM deposits WHERE tx_hash = ?", (tx_hash,)
    )
    if existing:
        return

    # Match deposit code
    cursor = await db.execute(
        "SELECT id, deposit_code FROM users WHERE deposit_code = ?", (comment,)
    )
    user = await cursor.fetchone()
    if user is None:
        logger.warning("unmatched_deposit: memo=%s amount=%.4f TON tx=%s",
                        comment, value / 1e9, tx_hash[:16])
        return

    # Credit balance
    await db.execute(
        "UPDATE users SET balance_nanoton = balance_nanoton + ? WHERE id = ?",
        (value, user["id"]),
    )
    # Record deposit
    await db.execute(
        "INSERT INTO deposits (user_id, tx_hash, amount_nanoton) VALUES (?, ?, ?)",
        (user["id"], tx_hash, value),
    )
    await db.commit()

    logger.info("deposit_credited: user_id=%d amount=%.4f TON memo=%s tx=%s",
                user["id"], value / 1e9, comment, tx_hash[:16])


async def payment_monitor_loop():
    """Background task polling for new deposits."""
    logger.info("Payment monitor started, watching wallet %s", settings.deposit_wallet)
    seen_hashes: set = set()

    while True:
        try:
            txs = await get_ton_transactions(settings.deposit_wallet)
            for tx in txs:
                tx_hash = tx.get("hash", "")
                if tx_hash and tx_hash not in seen_hashes:
                    seen_hashes.add(tx_hash)
                    await process_transaction(tx)

            # Keep seen_hashes bounded
            if len(seen_hashes) > 1000:
                seen_hashes = set(list(seen_hashes)[-500:])

        except Exception as e:
            logger.error("payment_monitor_error: %s", str(e)[:200])

        await asyncio.sleep(10)
