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

### 2. Run it on a server

Pick one. Both listen on `$PORT` (default `8080`) and read `INBODY_*` and
`MCP_API_KEY` from the environment or a `.env` file.

#### Option A: Docker

```bash
git clone git@github.com:rubenqba/inbody-api-mcp.git && cd inbody-api-mcp
# create .env with INBODY_LOGIN_ID, INBODY_LOGIN_PW, INBODY_COUNTRY_CODE, MCP_API_KEY
docker build -t inbody-mcp .
docker run -d --name inbody-mcp --restart unless-stopped \
  -p 8080:8080 --env-file .env inbody-mcp
```

Check it: `curl http://localhost:8080/healthz` returns `ok`. Update with
`git pull`, rebuild, and re-run the container.

#### Option B: Run directly (no Docker)

Requires [uv](https://docs.astral.sh/uv/) on the server.

```bash
git clone git@github.com:rubenqba/inbody-api-mcp.git && cd inbody-api-mcp
uv sync
uv run inbody-api-mcp-http
```

To keep it running across reboots, use a systemd unit
(`/etc/systemd/system/inbody-mcp.service`):

```ini
[Unit]
Description=InBody MCP (HTTP)
After=network-online.target

[Service]
WorkingDirectory=/opt/inbody-api-mcp
EnvironmentFile=/opt/inbody-api-mcp/.env
ExecStart=/usr/local/bin/uv run inbody-api-mcp-http
Restart=on-failure
User=inbody

[Install]
WantedBy=multi-user.target
```

Then `sudo systemctl enable --now inbody-mcp`. Keep `.env` readable only by
that user (`chmod 600`).

### 3. Expose it over HTTPS

Claude.ai and ChatGPT need a public HTTPS URL. The server speaks plain HTTP, so
put a TLS terminator in front of it, for example Caddy (automatic certificates):

```
inbody.example.com {
    reverse_proxy localhost:8080
}
```

Do not publish port 8080 directly to the internet; let only the proxy reach it.
For quick tests, tunnel your machine instead
(`ngrok http 8080` / `cloudflared tunnel --url http://localhost:8080`). Your MCP
URL is `https://<host>/mcp`.

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

### Deploy on Render (free tier)

[Render](https://render.com) can build this repo's `Dockerfile` and keep it online
at no cost. The free web service sleeps after 15 minutes without traffic and
wakes on the next request (the first call after a sleep takes about a minute),
and includes 750 instance hours per month per workspace, enough for one service
running all month.

1. Push this repo to your GitHub account (a fork works).
2. In the Render dashboard choose **New > Blueprint**, connect the repo, and
   select the branch. Render reads [`render.yaml`](render.yaml).
3. When prompted, enter the secrets: `INBODY_LOGIN_ID`, `INBODY_LOGIN_PW`,
   `INBODY_COUNTRY_CODE` and `MCP_API_KEY` (generate it with
   `uv run python generate_api_key.py`). They are never stored in the repo.
4. Wait for the first deploy. Your MCP URL is
   `https://<service-name>.onrender.com/mcp`.
5. Verify with the commands in [Verify](#verify), then add the URL and the
   Bearer key as a custom connector in Claude.ai or ChatGPT.

Render injects `PORT` (default `10000`) and terminates HTTPS for you, so no
extra proxy is needed. Render's health check uses `/healthz`, which does not
require the token. If the first request after a sleep times out in the client,
retry it once the instance has woken up.

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
