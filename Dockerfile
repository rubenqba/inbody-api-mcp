# InBody MCP image, wrapped with supergateway.
#
# Exposes the stdio MCP server over streamable-HTTP so it can be reverse-proxied
# or run as a standalone container:
#   - MCP streamable-HTTP on 0.0.0.0:$PORT at /mcp
#   - Health endpoint at /healthz
#   - stdio-speaking MCP process is spawned by supergateway as a child.
#
# Base: supercorp/supergateway:uvx (Alpine + Node 20 + uv).
# We install Python 3.14 via uv.

FROM supercorp/supergateway:uvx

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_INSTALL_DIR=/opt/uv-python \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PORT=8080

WORKDIR /app

# Copy the package source. Uses the .dockerignore alongside this file.
COPY pyproject.toml README.md ./
COPY src ./src

# Pre-install Python 3.14 into a deterministic location, then install the MCP
# as a uv tool so its console entry point (`inbody-api-mcp`) lands in
# /usr/local/bin on $PATH. `--compile-bytecode` writes .pyc files during the
# build so cold container starts don't pay the compile tax on every spawn of
# the stdio child by supergateway.
RUN uv python install 3.14 \
    && uv tool install --compile-bytecode --python 3.14 . \
    && inbody-api-mcp --help >/dev/null 2>&1 || true

# Start supergateway on internal port 9000, then run auth proxy on public port 8080.
# Auth proxy validates Bearer token, then forwards to supergateway.
ENTRYPOINT ["/bin/sh", "-c", "\
  supergateway \
    --stdio 'inbody-api-mcp' \
    --outputTransport streamableHttp \
    --stateful \
    --streamableHttpPath /mcp \
    --healthEndpoint /healthz \
    --port 9000 \
    --sessionTimeout 3600000 \
    --logLevel info &\
  sleep 2 && \
  exec inbody-api-mcp-auth-proxy \
  "]
