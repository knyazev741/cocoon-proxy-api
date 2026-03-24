# Cocoon API Proxy MCP Server

MCP (Model Context Protocol) server that wraps the Cocoon API Proxy REST API as tools for LLM agents.

## Setup

```bash
pip install -r requirements.txt
```

## Configuration

Set environment variables:
- `COCOON_PROXY_URL` — Cocoon API Proxy URL (default: `http://localhost:8000`)
- `COCOON_API_KEY` — Your API key (`ck_...`)

## Run

```bash
python server.py
```

## Tools

| Tool | Description | Read-Only |
|------|-------------|-----------|
| chat_completion | Send messages to AI model, get response | No |
| list_models | List available AI models | Yes |
| check_balance | Check TON balance | Yes |
| get_deposit_info | Get deposit wallet and memo | Yes |
| create_api_key | Create new API key | No |
| health_check | Check service health | Yes |

## Claude Desktop Config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cocoon-api-proxy": {
      "command": "python",
      "args": ["/path/to/mcp-server/server.py"],
      "env": {
        "COCOON_PROXY_URL": "http://localhost:8000",
        "COCOON_API_KEY": "ck_your_key"
      }
    }
  }
}
```
