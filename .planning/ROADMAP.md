# Roadmap: Cocoon API Proxy

**Created:** 2026-03-23
**Granularity:** Coarse (4 phases)
**Mode:** YOLO

## Phase 1: Core Proxy + Auth
**Goal:** Working OpenAI-compatible proxy with API key auth and privacy guarantees.
**Requirements:** PROXY-01..06, AUTH-01..04, PRIV-01..03
**Delivers:** Users can create API key and make chat completion requests (no billing yet — free during testing).

### Plans
1. **Database schema + models** — SQLite setup, user/key tables, aiosqlite wrapper
2. **Auth middleware** — API key validation, Bearer token extraction, key creation endpoint
3. **Proxy core** — /v1/chat/completions (streaming + non-streaming), /v1/models passthrough
4. **Privacy enforcement** — ensure no content logging, audit all write paths

## Phase 2: Billing System
**Goal:** Per-request billing with configurable pricing on top of Cocoon costs.
**Requirements:** BILL-01..05
**Delivers:** Balance checks before requests, automatic cost deduction after responses.

### Plans
1. **Balance management** — balance field, pre-check middleware, /v1/balance endpoint
2. **Post-charge billing** — extract usage from response, calculate cost with multiplier, atomic deduction
3. **Streaming billing** — parse final SSE chunk for usage data, handle edge cases (disconnect, timeout)
4. **Usage logging** — metadata-only usage records (timestamp, model, tokens, cost)

## Phase 3: TON Payments
**Goal:** Automated deposit detection via TON blockchain monitoring.
**Requirements:** PAY-01..05
**Delivers:** Users send TON with memo code, balance auto-credited.

### Plans
1. **Deposit codes** — generate unique 8-char codes per user, /v1/deposit endpoint
2. **tonapi.io SSE listener** — background task monitoring wallet transactions
3. **Memo matching + crediting** — parse transfer comments, match to users, credit balance
4. **Deposit history** — store tx_hash, amount, timestamp; prevent double-crediting

## Phase 4: Deployment
**Goal:** Production-ready deployment with HTTPS and process management.
**Requirements:** INFRA-01..04
**Delivers:** Live at api.knyazevai.work with auto-SSL.

### Plans
1. **Caddy config** — reverse proxy to FastAPI, auto-SSL for api.knyazevai.work
2. **Systemd services** — proxy app + TON listener as managed services
3. **Startup + graceful shutdown** — proper signal handling, in-flight request completion
