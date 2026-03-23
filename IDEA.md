# Cocoon API Proxy

## What
A paid OpenAI-compatible API proxy that gives simple access to Cocoon AI network. Users get an API key, top up balance in TON, and make standard OpenAI API calls. No need to compile C++ client or deploy smart contracts.

## Business Model
- 50% markup on Cocoon network prices
- Prepaid model: user deposits TON → we deduct per request
- Cocoon base pricing: 20 nanograms/token (prompt ×1, completion ×8, reasoning ×8, cached ×0.1)

## Available Models (via Cocoon network)
- Qwen/Qwen3-32B (5 workers)
- ByteDance-Seed/Seed-X-PPO-7B (15 workers)

## Architecture
- **Python FastAPI** — async proxy with SSE streaming
- **SQLite WAL** (aiosqlite) — balances, usage, deposits
- **tonapi.io SSE** — real-time monitoring of incoming TON payments
- **Caddy** — zero-config HTTPS with auto SSL
- **Upstream**: local Cocoon client at localhost:10000

## Payment Flow
1. User registers → gets API key (ck_<64 hex>) + unique deposit code (8 chars)
2. User sends TON to our wallet with deposit code in memo/comment
3. Background process listens to tonapi.io SSE, matches memo → credits balance
4. User makes API calls with `Authorization: Bearer ck_xxx`
5. Proxy: check balance ≥ 0.01 TON → forward to Cocoon → take total_cost from response × 1.5 → deduct

## Billing
- Pre-check: balance ≥ 0.01 TON (gate)
- Post-charge: after response, usage.total_cost × 1.5
- Small negative allowed (up to -0.05 TON) for long responses

## Privacy (key selling point)
- NO prompt/response logging — only metadata (timestamp, model, tokens, cost)
- In-memory processing, content never written to disk
- Open source code
- Position: "we're like a VPN — trust + open source, no cryptographic guarantee"

## API Endpoints
- POST /v1/chat/completions (streaming + non-streaming)
- GET /v1/models
- GET /v1/balance
- GET /v1/deposit (instructions)
- POST /v1/keys (create key)

## Key Storage
- Format: ck_<64 hex chars>
- Stored as SHA-256 hash

## Infrastructure Already Available
- Working Cocoon client on server (localhost:10000)
- Domain: knyazevai.work
- Python 3.12
- TON wallet for receiving payments: EQDJxdrlRruDA9KuV7nGNXAPVs8cTIS2fbyMx2BOWioB_hib

## Target
- ~800-1200 lines of Python across 5-6 files
- Deployable on single VPS
- Public GitHub repo (open source)
