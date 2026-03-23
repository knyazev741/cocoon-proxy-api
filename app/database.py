"""SQLite database setup and access."""

import os
import aiosqlite

from app.config import settings

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_hash TEXT UNIQUE NOT NULL,
    deposit_code TEXT UNIQUE NOT NULL,
    balance_nanoton INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    model TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_nanoton INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tx_hash TEXT UNIQUE NOT NULL,
    amount_nanoton INTEGER NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_users_api_key_hash ON users(api_key_hash);
CREATE INDEX IF NOT EXISTS idx_users_deposit_code ON users(deposit_code);
CREATE INDEX IF NOT EXISTS idx_deposits_tx_hash ON deposits(tx_hash);
"""


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        os.makedirs(os.path.dirname(settings.database_path) or ".", exist_ok=True)
        _db = await aiosqlite.connect(settings.database_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA busy_timeout=5000")
        await _db.executescript(SCHEMA)
        await _db.commit()
    return _db


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
