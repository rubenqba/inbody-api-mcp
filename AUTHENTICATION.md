# Authentication

The InBody MCP server includes an **authentication proxy** that protects remote deployments with Bearer token (API key) authentication.

## Generate an API Key

```bash
# Generate a random secure API key
uv run python generate_api_key.py
```

Output example:
```
API Key: M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc
```

Save this key securely — anyone with it can access your InBody data.

---

## Local Development (No Authentication)

When running locally, the proxy is optional. Just run the server directly:

```bash
export INBODY_LOGIN_ID="3026323617"
export INBODY_LOGIN_PW="your-password"
uv run inbody-api-mcp
```

---

## Remote Deployment with Authentication

### Deploy on Fly.io

1. **Generate API key:**
   ```bash
   uv run python generate_api_key.py
   # Save: M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc
   ```

2. **Deploy to Fly.io:**
   ```bash
   fly launch
   fly secrets set INBODY_LOGIN_ID="3026323617"
   fly secrets set INBODY_LOGIN_PW="your-password"
   fly secrets set INBODY_COUNTRY_CODE="US"
   fly secrets set MCP_API_KEY="M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc"
   fly deploy
   ```

3. **Your server URL:**
   ```
   https://your-app.fly.dev/mcp
   ```

### Deploy on Railway

1. Connect your repo to [railway.app](https://railway.app)
2. In Railway dashboard, add Environment Variables:
   ```
   INBODY_LOGIN_ID=3026323617
   INBODY_LOGIN_PW=your-password
   INBODY_COUNTRY_CODE=US
   MCP_API_KEY=M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc
   ```
3. Deploy

Your server URL:
```
https://your-app.up.railway.app/mcp
```

---

## Use with ChatGPT or Claude.ai

Once deployed remotely, configure your MCP client to use the Bearer token.

### With curl (testing):

```bash
curl -H "Authorization: Bearer M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc" \
  https://your-app.fly.dev/mcp
```

### With ChatGPT

ChatGPT's MCP configuration (when setting up the remote MCP server):
```json
{
  "type": "remote",
  "url": "https://your-app.fly.dev/mcp",
  "auth": {
    "bearer": "M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc"
  }
}
```

### With Claude.ai (Desktop)

Claude Desktop's `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "inbody-remote": {
      "url": "https://your-app.fly.dev/mcp",
      "auth": {
        "bearer": "M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc"
      }
    }
  }
}
```

---

## Security Notes

- ⚠️ **Never commit API keys** to git. Use `.env` files or your platform's secrets manager.
- 🔒 **Always use HTTPS** for remote connections (Fly.io/Railway provide SSL automatically).
- 🔑 Rotate API keys periodically.
- 📋 If a key is compromised, regenerate a new one immediately.

---

## How It Works

The deployment architecture:

```
ChatGPT/Claude.ai
       ↓
   HTTPS (Bearer token)
       ↓
Auth Proxy (port 8080)
   validates token
       ↓
supergateway (port 9000)
   converts HTTP ↔ stdio
       ↓
MCP Server (stdio)
   talks to InBody API
```

The **Auth Proxy** (new):
- Listens on port 8080 (public)
- Requires `Authorization: Bearer <MCP_API_KEY>` header
- Proxies valid requests to supergateway on port 9000
- Returns 401 (missing token) or 403 (invalid token) for unauthorized requests

---

## Troubleshooting

### "Missing or invalid Authorization header" (401)

Your request didn't include the Bearer token. Add this header:
```
Authorization: Bearer M4J0AhW7mZL_ewdtjUXRIHW5S5BhlkId4Ou4Ty8qCqc
```

### "Invalid API key" (403)

The token doesn't match the one set in `MCP_API_KEY`. Verify you're using the correct key.

### Auth proxy not starting

In Fly.io/Railway logs, check:
- Is `MCP_API_KEY` set in secrets?
- Is the Dockerfile building correctly? (`fly logs`, `railway logs`)

### Server works locally but fails remotely

Local development doesn't require `MCP_API_KEY`. When deploying:
1. Generate a key: `uv run python generate_api_key.py`
2. Set it as a secret: `fly secrets set MCP_API_KEY="..."`
3. Redeploy: `fly deploy`
