# Cocoon API Proxy

## What This Is

A paid OpenAI-compatible API proxy that provides simple access to the Cocoon decentralized AI network on TON blockchain. Users get an API key, deposit TON to a wallet with a memo code, and make standard `/v1/chat/completions` calls — no C++ client compilation or smart contract deployment needed.

## Core Value

Simple, privacy-respecting paid API access to Cocoon AI models with zero content logging.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] OpenAI-compatible /v1/chat/completions endpoint (streaming + non-streaming)
- [ ] API key authentication (ck_<64 hex>, stored as SHA-256)
- [ ] Prepaid TON balance system with per-request billing (Cocoon cost × 1.5)
- [ ] TON deposit monitoring via tonapi.io SSE (memo-based matching)
- [ ] /v1/models, /v1/balance, /v1/deposit endpoints
- [ ] Zero content logging — only metadata (timestamp, model, tokens, cost)
- [ ] HTTPS via Caddy with auto-SSL

### Out of Scope

- User dashboard/web UI — API-only for MVP
- Multiple payment methods — TON only
- Rate limiting — not needed at MVP scale (10-100 users)
- Fiat on-ramp — users get TON themselves
- WebSocket support — SSE streaming only
- Multi-backend routing — single Cocoon client upstream

## Context

- Cocoon network has 20 active workers (5 Qwen3-32B, 15 Seed-X-PPO-7B)
- Network processes ~834 TON/day (~$1,920/day) in inference payments
- Our Cocoon client runs at localhost:10000, fully operational
- Server has Python 3.12, domain knyazevai.work, existing nginx+certbot
- TON wallet for deposits: EQDJxdrlRruDA9KuV7nGNXAPVs8cTIS2fbyMx2BOWioB_hib
- Cocoon pricing: 20 nanograms/token base, completion ×8, reasoning ×8, cached ×0.1

## Constraints

- **Tech stack**: Python FastAPI + SQLite + Caddy — chosen for speed-to-ship
- **Privacy**: No prompt/response content written to disk or database, ever
- **Single server**: Everything runs on one VPS alongside Cocoon client
- **Open source**: Code will be public on GitHub
- **Billing**: Post-charge model — deduct after response, allow small negative balance (up to -0.05 TON)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Flask/aiohttp | Native SSE streaming, dependency injection, auto-docs | — Pending |
| SQLite over PostgreSQL | Zero infra, single file, sufficient for 10-100 users | — Pending |
| Caddy over nginx | 3-line config vs 30+, auto-SSL, no buffering issues | — Pending |
| Post-charge billing | Can't know token count until stream ends | — Pending |
| tonapi.io SSE over polling | Real-time deposit detection, no API rate limits | — Pending |
| SHA-256 key hashing | Industry standard, keys never stored in plaintext | — Pending |

---
*Last updated: 2026-03-23 after project initialization*
