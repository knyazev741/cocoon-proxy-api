"""Billing: cost calculation and balance management."""

from fastapi import HTTPException

from app.config import settings
from app.database import get_db


def calculate_cost_nanoton(usage: dict) -> int:
    """Calculate cost in nanotons from usage data, with markup."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    # Cocoon reports total_cost but it's often 0 — always calculate manually
    cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0) if isinstance(usage.get("prompt_tokens_details"), dict) else 0
    reasoning = usage.get("reasoning_tokens", 0)

    # Separate cached from regular prompt tokens
    regular_prompt = max(0, prompt - cached)
    prompt_cost = regular_prompt * settings.price_per_token * settings.prompt_multiplier
    cached_cost = cached * settings.price_per_token * settings.cached_multiplier
    completion_cost = completion * settings.price_per_token * settings.completion_multiplier
    reasoning_cost = reasoning * settings.price_per_token * settings.reasoning_multiplier
    base_cost = prompt_cost + cached_cost + completion_cost + reasoning_cost
    return int(base_cost * settings.markup_multiplier)


async def check_balance(user: dict):
    """Pre-check: ensure user has minimum balance."""
    balance_ton = user["balance_nanoton"] / 1e9
    if balance_ton < settings.min_balance_ton:
        raise HTTPException(
            status_code=402,
            detail={
                "error": {
                    "message": f"Insufficient balance: {balance_ton:.4f} TON. Minimum: {settings.min_balance_ton} TON. Top up via /v1/deposit.",
                    "type": "insufficient_balance",
                    "param": None,
                    "code": "insufficient_balance",
                }
            },
        )


async def deduct_balance(user_id: int, cost_nanoton: int, usage: dict, model: str):
    """Post-charge: deduct cost from user balance and log usage."""
    db = await get_db()

    # Atomic deduction (allow small overdraft)
    max_overdraft = int(settings.max_overdraft_ton * 1e9)
    await db.execute(
        "UPDATE users SET balance_nanoton = balance_nanoton - ? WHERE id = ? AND balance_nanoton > ?",
        (cost_nanoton, user_id, -max_overdraft),
    )

    # Log usage (metadata only, no content)
    await db.execute(
        """INSERT INTO usage_log (user_id, model, prompt_tokens, completion_tokens, total_tokens, cost_nanoton)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
            usage.get("total_tokens", 0),
            cost_nanoton,
        ),
    )
    await db.commit()
