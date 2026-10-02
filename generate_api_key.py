#!/usr/bin/env python3
"""Generate a secure API key for the InBody MCP server."""

import secrets
import sys


def generate_api_key(length: int = 32) -> str:
    """Generate a random API key."""
    return secrets.token_urlsafe(length)


def main() -> None:
    """Generate and display API key."""
    api_key = generate_api_key()
    print("\n" + "=" * 70)
    print("Generated API Key for InBody MCP Server")
    print("=" * 70)
    print(f"\nAPI Key: {api_key}\n")
    print("Save this key securely. You'll need it to authenticate requests.\n")
    print("Usage with curl:")
    print(f'  curl -H "Authorization: Bearer {api_key}" https://your-server/mcp\n')
    print("Usage in Claude.ai/ChatGPT:")
    print("  Set the Bearer token in the MCP configuration\n")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
