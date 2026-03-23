# Cocoon API Proxy

OpenAI-compatible paid API proxy for the Cocoon decentralized AI network on TON.

## Quick Start
```bash
pip install -r requirements.txt
python -m app.main
```

## Architecture
- `app/main.py` — FastAPI app, startup/shutdown
- `app/proxy.py` — /v1/chat/completions proxy (streaming + non-streaming)
- `app/auth.py` — API key generation, validation, Bearer token middleware
- `app/billing.py` — balance checks, post-charge billing, cost calculation
- `app/payments.py` — TON deposit monitoring via tonapi.io SSE
- `app/database.py` — SQLite setup, migrations, aiosqlite wrapper
- `app/models.py` — Pydantic models
- `app/config.py` — settings (env vars)

## Key Design Decisions
- **Privacy first**: No prompt/response content ever written to disk
- **Post-charge billing**: Deduct after response (token count unknown until stream ends)
- **Configurable pricing**: Cost multiplier applied on top of Cocoon network rates
- **Upstream**: Cocoon client at localhost:10000

## Environment Variables
- `COCOON_UPSTREAM_URL` — default http://localhost:10000
- `DATABASE_PATH` — default ./data/cocoon_proxy.db
- `DEPOSIT_WALLET` — TON wallet address for receiving deposits
- `TONAPI_SSE_URL` — tonapi.io SSE endpoint for transaction monitoring
- `ADMIN_TOKEN` — admin token for key creation (optional)

## GSD Development
This project uses [Get Shit Done](https://github.com/gsd-build/get-shit-done) for development.
- `/gsd:plan-phase 1` — plan current phase
- `/gsd:execute-phase 1` — execute current phase
- `/gsd:progress` — check progress
