"""HTTP proxy with Bearer token authentication for the InBody MCP server."""

import json
import logging
import os
import sys
from typing import Any

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthProxy(BaseHTTPRequestHandler):
    """HTTP proxy that validates Bearer token before forwarding to MCP server."""

    upstream_url = os.getenv("MCP_UPSTREAM_URL", "http://localhost:9000")
    api_key = os.getenv("MCP_API_KEY")

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _validate_token(self) -> bool:
        """Validate Bearer token from Authorization header."""
        if not self.api_key:
            logger.warning("MCP_API_KEY not set, allowing all requests (INSECURE)")
            return True

        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": "Missing or invalid Authorization header"}).encode()
            )
            return False

        token = auth_header[7:]
        if token != self.api_key:
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid API key"}).encode())
            return False

        return True

    def _proxy_request(self, method: str) -> None:
        """Forward request to upstream MCP server."""
        if not self._validate_token():
            return

        content_length = self.headers.get("Content-Length")
        body = self.rfile.read(int(content_length)) if content_length else b""

        url = f"{self.upstream_url}{self.path}"
        headers = dict(self.headers)
        headers.pop("Host", None)

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.request(method, url, content=body, headers=headers)
                self.send_response(resp.status_code)
                for key, value in resp.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(resp.content)
        except Exception as e:
            logger.error("Proxy error: %s", e)
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Gateway error"}).encode())

    def do_GET(self) -> None:
        """Handle GET requests."""
        self._proxy_request("GET")

    def do_POST(self) -> None:
        """Handle POST requests."""
        self._proxy_request("POST")

    def do_PUT(self) -> None:
        """Handle PUT requests."""
        self._proxy_request("PUT")

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        self._proxy_request("DELETE")

    def log_message(self, format: str, *args: Any) -> None:
        """Log HTTP requests."""
        logger.info(format, *args)


def main() -> None:
    """Run the auth proxy."""
    api_key = os.getenv("MCP_API_KEY")
    if not api_key:
        logger.warning(
            "⚠️  MCP_API_KEY not set. Server will accept requests without authentication!"
        )
    else:
        logger.info("✓ API key authentication enabled")

    upstream = os.getenv("MCP_UPSTREAM_URL", "http://localhost:9000")
    logger.info(f"Proxying to upstream: {upstream}")

    server = HTTPServer(("0.0.0.0", 8080), AuthProxy)
    logger.info("Auth proxy listening on http://0.0.0.0:8080")
    logger.info("Set Bearer token with: Authorization: Bearer <MCP_API_KEY>")
    server.serve_forever()


if __name__ == "__main__":
    main()
