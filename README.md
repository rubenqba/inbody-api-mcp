# inbody-api-mcp

<!-- mcp-name: io.github.rubenqba/inbody-api-mcp -->

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/rubenqba/inbody-api-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/rubenqba/inbody-api-mcp/actions/workflows/ci.yml)
[![Build Docker image](https://github.com/rubenqba/inbody-api-mcp/actions/workflows/docker.yml/badge.svg)](https://github.com/rubenqba/inbody-api-mcp/actions/workflows/docker.yml)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server for
[InBody](https://inbody.com/) body-composition data, built on the
reverse-engineered mobile REST API used by the InBody Android app.

InBody has no public API and no web UI for personal scan data. This server talks
to the same JSON REST endpoints the mobile app uses, exposing your body
composition history (body fat, muscle mass, body water, segmental impedance) to
any MCP client.

## Features

- **Profile** -- identity and baseline metrics (height, weight, age, gender)
- **Scan history** -- chronological summaries (weight, BMI, % body fat, muscle mass)
- **Full scan metrics** -- complete body composition (BCA), BMI/%fat/muscle with
  normal ranges (MFA), and segmental/multi-frequency impedance (IMP)
- **Automatic region routing** -- resolves the correct regional API host from
  your country code
- **Automatic re-authentication** -- caches the 24h JWT and re-logs in on expiry

## Quick Start

Run the server from a local checkout of this repository (it requires Python
3.14 and MCP SDK v2, both handled by `uv`).

### 1. Install [uv](https://docs.astral.sh/uv/) and clone the repo

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone git@github.com:rubenqba/inbody-api-mcp.git
cd inbody-api-mcp
uv sync
```

### 2. Set credentials

Copy `.env.example` to `.env` (loaded automatically) or export the variables:

```bash
INBODY_LOGIN_ID=3026323617    # registration phone number, digits only
INBODY_LOGIN_PW=your-password
INBODY_COUNTRY_CODE=US        # ISO country code (default US)
```

> **`INBODY_LOGIN_ID` is the phone number used at registration**, not your email
> -- digits only, no country code or `+` (e.g. `3026323617`). InBody keys login
> on the phone number; the email is only returned as profile data. An email
> value will fail login with `EmptyData`.

### 3. Configure your MCP client

Local clients spawn the server over **stdio** with `uv run`. Replace the
`--directory` path with your checkout.

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "inbody": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/inbody-api-mcp", "inbody-api-mcp"],
      "env": {
        "INBODY_LOGIN_ID": "3026323617",
        "INBODY_LOGIN_PW": "your-password",
        "INBODY_COUNTRY_CODE": "US"
      }
    }
  }
}
```

#### OpenCode (`opencode.json`)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "inbody": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/inbody-api-mcp", "inbody-api-mcp"],
      "environment": {
        "INBODY_LOGIN_ID": "{env:INBODY_LOGIN_ID}",
        "INBODY_LOGIN_PW": "{env:INBODY_LOGIN_PW}",
        "INBODY_COUNTRY_CODE": "US"
      },
      "enabled": true
    }
  }
}
```

## Remote Use (Claude.ai, ChatGPT)

Web clients cannot spawn local processes, so the server also runs as a
**streamable-HTTP** endpoint at `/mcp` (entry point `inbody-api-mcp-http`). It
is read-only but exposes your body-composition data, so it **refuses to start
without `MCP_API_KEY`** and requires `Authorization: Bearer <MCP_API_KEY>` on
every request except `GET /healthz`.

### 1. Generate an API key

```bash
uv run python generate_api_key.py
```

Add it to `.env` as `MCP_API_KEY=...`. Never commit it.

### 2. Run it

With Docker (listens on `$PORT`, default 8080):

```bash
docker build -t inbody-mcp .
docker run -d -p 8080:8080 --env-file .env inbody-mcp
```

Or without Docker:

```bash
uv run inbody-api-mcp-http
```

### 3. Expose it over HTTPS

Deploy the image to any container host, or tunnel your machine for testing
(`ngrok http 8080` / `cloudflared tunnel --url http://localhost:8080`). Your
MCP URL is `https://<host>/mcp`.

### 4. Add it to your client

In Claude.ai or ChatGPT, add a custom MCP connector with the URL above and
send the key as a Bearer token (`Authorization: Bearer <MCP_API_KEY>`).

### Verify

```bash
curl -i -X POST https://<host>/mcp                      # 401 without a token
curl -s -X POST https://<host>/mcp \
  -H "Authorization: Bearer $MCP_API_KEY" \
  -H "MCP-Protocol-Version: 2026-07-28" -H "Mcp-Method: tools/call" \
  -H "Mcp-Name: get_scan_count" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_scan_count","arguments":{}}}'
```

Rotate the key if it is ever exposed: generate a new one, update `.env` or your
host's secrets, and restart.

## Available Tools

| Tool | Description |
|------|-------------|
| `get_profile` | User identity and baseline metrics (height, weight, age, gender) |
| `get_scan_count` | Total number of scans on the account |
| `list_scans` | Chronological scan summaries (weight, BMI, % body fat, muscle mass) |
| `get_scan` | Full metric set for one scan (BCA / MFA / IMP blocks) |

This server is read-only: no write or delete endpoints are exposed.

## How It Works

This server communicates with the regional `*.lookinbody.com` REST API -- the
same backend used by the InBody Android app (v2.8.31). The API was
reverse-engineered by capturing app traffic with mitmproxy and confirming
payload shapes against the live API.

The auth flow:

1. `POST /CommonAPI/GetCountryInfoV2` (on `appapicommon.lookinbody.com`) returns
   a per-country host table. The `Type == "API"` row for your ISO country code
   gives the regional API base (US -> `appapiusav2.lookinbody.com`) and the
   numeric phone code used in request bodies.
2. `POST /V2/Main/GetLoginWithSyncDataPartV2` exchanges the login ID + password
   for a 24-hour JWT, a refresh token, and the account UID.
3. Subsequent calls send `Authorization: Bearer <JWT>`. The client
   re-authenticates automatically when the token expires.

Each scan record nests three blocks: **BCA** (body composition analysis -- body
water, protein, mineral, fat, segmental water), **MFA** (BMI, % body fat,
skeletal muscle mass, WHR with normal ranges), and **IMP** (raw impedance per
frequency and body segment).

## Python API

You can use the client directly:

```python
from inbody_api_mcp.client import InBodyClient

client = InBodyClient()

# Total number of scans
count = client.get_scan_count()

# Recent scans (newest first), paginated
scans = client.get_scans(number=20, index=0)

# User profile
profile = client.get_user_info()
```

## Transport

- **stdio** (`inbody-api-mcp`) -- for local clients such as Claude Desktop and OpenCode.
- **streamable-HTTP** (`inbody-api-mcp-http`) -- for Claude.ai and ChatGPT; Bearer-protected (see [Remote Use](#remote-use-claudeai-chatgpt)).

Built on the MCP Python SDK v2 (`mcp>=2`).

## License

MIT
