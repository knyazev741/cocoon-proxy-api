# Cocoon API Proxy

An OpenAI-compatible API proxy for the [Cocoon](https://cocoon.ws/) decentralized AI network on TON blockchain. Provides a familiar REST API interface with built-in billing, API key management, and automatic TON deposit detection.

Users get an API key, deposit TON to your wallet with a memo code, and make standard OpenAI-format API calls. No need to compile C++ clients or deploy smart contracts.

## Features

- **OpenAI-compatible API** -- drop-in replacement for any OpenAI client library
- **Streaming support** -- full SSE streaming for chat completions
- **Prepaid billing** -- per-request cost tracking with configurable pricing
- **TON payments** -- automatic deposit detection via tonapi.io
- **Privacy first** -- no prompt or response content is ever logged or stored
- **API key auth** -- secure key generation with SHA-256 hashed storage

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A running [Cocoon client](https://github.com/nickel-lang/cocoon) at localhost:10000
- A TON wallet address for receiving deposits
- (Optional) A [tonapi.io](https://tonapi.io/) API key for faster deposit detection

### 2. Install

```bash
git clone https://github.com/knyazev741/cocoon-api-proxy.git
cd cocoon-api-proxy
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Required settings:
- `COCOON_DEPOSIT_WALLET` -- your TON wallet address for receiving user deposits

See `.env.example` for all available options.

### 4. Run

```bash
python -m app.main
```

The server starts on `http://0.0.0.0:8000` by default.

For production, use a reverse proxy (Caddy, nginx) for HTTPS.

## API Endpoints

### Create API Key

```bash
curl -X POST http://localhost:8000/v1/keys
```

Returns an API key (`ck_...`) and a unique deposit code. The API key is shown once -- save it.

If `COCOON_ADMIN_TOKEN` is set, include it as `Authorization: Bearer <token>`.

### Deposit TON

```bash
curl http://localhost:8000/v1/deposit \
  -H "Authorization: Bearer ck_your_api_key"
```

Returns wallet address and memo code. Send TON to the wallet with the memo -- balance credits automatically within ~30 seconds.

### Check Balance

```bash
curl http://localhost:8000/v1/balance \
  -H "Authorization: Bearer ck_your_api_key"
```

### List Models

```bash
curl http://localhost:8000/v1/models
```

### Chat Completions

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ck_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-32B",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

Streaming is supported -- set `"stream": true` in the request body.

### Health Check

```bash
curl http://localhost:8000/health
```

## Using with OpenAI Client Libraries

```python
from openai import OpenAI

client = OpenAI(
    api_key="ck_your_api_key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-32B",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

## Configuration

All settings are configured via environment variables (prefixed with `COCOON_`) or a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `COCOON_DEPOSIT_WALLET` | *(required)* | TON wallet address for receiving deposits |
| `COCOON_UPSTREAM_URL` | `http://localhost:10000` | Cocoon client URL |
| `COCOON_DATABASE_PATH` | `./data/cocoon_proxy.db` | SQLite database path |
| `COCOON_HOST` | `0.0.0.0` | Server bind address |
| `COCOON_PORT` | `8000` | Server port |
| `COCOON_MARKUP_MULTIPLIER` | `1.5` | Price multiplier on top of network costs |
| `COCOON_MIN_BALANCE_TON` | `0.01` | Minimum balance required to make requests |
| `COCOON_MAX_OVERDRAFT_TON` | `0.05` | Maximum allowed negative balance |
| `COCOON_TONAPI_KEY` | *(empty)* | tonapi.io API key for deposit monitoring |
| `COCOON_ADMIN_TOKEN` | *(empty)* | Admin token for key creation (if empty, open registration) |
| `COCOON_MAX_TOKENS_CAP` | `128000` | Maximum allowed max_tokens per request |

## Architecture

```
User --> [Cocoon API Proxy] --> [Cocoon Client] --> [Cocoon Network (TON)]
                |
           SQLite (WAL)
         balances, usage
```

- **FastAPI** async proxy with SSE streaming
- **SQLite** with WAL mode for concurrent reads
- **tonapi.io** polling for real-time deposit detection
- **No content logging** -- only metadata (timestamp, model, token counts, cost)

## Project Structure

```
app/
  main.py       -- FastAPI app, startup/shutdown
  proxy.py      -- /v1/chat/completions proxy (streaming + non-streaming)
  auth.py       -- API key generation, validation, Bearer token middleware
  billing.py    -- balance checks, post-charge billing, cost calculation
  payments.py   -- TON deposit monitoring via tonapi.io
  database.py   -- SQLite setup, schema, aiosqlite wrapper
  config.py     -- settings from environment variables
```

## License

MIT
