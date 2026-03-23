# Requirements: Cocoon API Proxy

**Defined:** 2026-03-23
**Core Value:** Simple, privacy-respecting paid API access to Cocoon AI models with zero content logging.

## v1 Requirements

### API Proxy

- [ ] **PROXY-01**: POST /v1/chat/completions proxies requests to Cocoon client at localhost:10000
- [ ] **PROXY-02**: Streaming (SSE) responses forwarded chunk-by-chunk to client
- [ ] **PROXY-03**: Non-streaming responses forwarded as complete JSON
- [ ] **PROXY-04**: GET /v1/models returns available Cocoon models
- [ ] **PROXY-05**: Request body validated (model, messages required)
- [ ] **PROXY-06**: Inject stream_options.include_usage=true for billing on streaming requests

### Authentication

- [ ] **AUTH-01**: API keys in format ck_<64 hex chars> generated securely
- [ ] **AUTH-02**: Keys stored as SHA-256 hash in database (plaintext shown once at creation)
- [ ] **AUTH-03**: Authorization: Bearer ck_xxx header required on all /v1/ endpoints
- [ ] **AUTH-04**: POST /v1/keys creates new API key (admin-protected or open registration TBD)

### Billing

- [ ] **BILL-01**: Pre-check: reject request if balance < 0.01 TON
- [ ] **BILL-02**: Post-charge: deduct calculated cost after response completes
- [ ] **BILL-03**: Allow small negative balance (up to -0.05 TON) for long responses
- [ ] **BILL-04**: GET /v1/balance returns current user balance in TON
- [ ] **BILL-05**: Usage logging: timestamp, model, prompt_tokens, completion_tokens, cost (no content)

### Payments

- [ ] **PAY-01**: Each user gets unique 8-char deposit code
- [ ] **PAY-02**: GET /v1/deposit returns wallet address + user's deposit code + instructions
- [ ] **PAY-03**: Background process monitors tonapi.io SSE for incoming TON transfers
- [ ] **PAY-04**: Transfers with matching memo/comment credited to user balance
- [ ] **PAY-05**: Deposit history stored (tx_hash, amount, timestamp)

### Privacy

- [ ] **PRIV-01**: No prompt or response content written to disk or database
- [ ] **PRIV-02**: In-memory processing only for request/response content
- [ ] **PRIV-03**: Usage logs contain only metadata (no content fields)

### Infrastructure

- [ ] **INFRA-01**: Caddy reverse proxy with auto-SSL for api.knyazevai.work
- [ ] **INFRA-02**: Application runs as systemd service
- [ ] **INFRA-03**: SQLite database with WAL mode for concurrent access
- [ ] **INFRA-04**: Graceful shutdown preserving in-flight requests

## v2 Requirements

### Enhanced Billing
- **BILL-V2-01**: Usage dashboard with per-day/per-model breakdown
- **BILL-V2-02**: Spending alerts when balance drops below threshold

### Multi-user
- **MULTI-01**: Admin panel for managing users/keys
- **MULTI-02**: Per-key rate limits

### Monitoring
- **MON-01**: Prometheus metrics endpoint
- **MON-02**: Health check endpoint with upstream status

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI / Dashboard | API-only MVP, add later if demand exists |
| Fiat payments | Complexity, regulatory; TON-native users only |
| Multiple upstream backends | Single Cocoon client, no load balancing needed |
| User accounts / login | API keys are the identity, no passwords |
| Content filtering / moderation | Pass-through proxy, Cocoon handles this |
| WebSocket streaming | SSE is standard for OpenAI-compatible APIs |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROXY-01..06 | Phase 1 | Pending |
| AUTH-01..04 | Phase 1 | Pending |
| BILL-01..05 | Phase 2 | Pending |
| PAY-01..05 | Phase 3 | Pending |
| PRIV-01..03 | Phase 1 | Pending |
| INFRA-01..04 | Phase 4 | Pending |
