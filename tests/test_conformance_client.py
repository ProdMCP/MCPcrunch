"""
Tests for mcpcrunch.conformance.client (MCPClient)

Tests the MCP JSON-RPC 2.0 client including header building,
auth handling, and error cases. Uses mocking since we don't
have a real server in unit tests.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from mcpcrunch.conformance.models import AuthConfig

# Only import if httpx is available
try:
    from mcpcrunch.conformance.client import MCPClient, MCPClientError
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False

pytestmark = pytest.mark.skipif(not HAS_CLIENT, reason="httpx not available")


# ── Header Building ────────────────────────────────────────

class TestHeaderBuilding:
    def test_default_headers(self):
        client = MCPClient("http://localhost:3000")
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"

    def test_bearer_token_header(self):
        auth = AuthConfig(bearer_token="my-token")
        client = MCPClient("http://localhost:3000", auth=auth)
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer my-token"

    def test_api_key_header(self):
        auth = AuthConfig(api_key="key-123", api_key_in="header", api_key_header_name="X-API-Key")
        client = MCPClient("http://localhost:3000", auth=auth)
        headers = client._build_headers()
        assert headers["X-API-Key"] == "key-123"

    def test_api_key_query(self):
        auth = AuthConfig(api_key="key-123", api_key_in="query")
        client = MCPClient("http://localhost:3000", auth=auth)
        params = client._build_params()
        assert params["api_key"] == "key-123"

    def test_no_auth(self):
        client = MCPClient("http://localhost:3000")
        headers = client._build_headers()
        assert "Authorization" not in headers

    def test_no_query_params_without_query_auth(self):
        client = MCPClient("http://localhost:3000")
        params = client._build_params()
        assert len(params) == 0


# ── Request ID ─────────────────────────────────────────────

class TestRequestId:
    def test_increments(self):
        client = MCPClient("http://localhost:3000")
        id1 = client._next_id()
        id2 = client._next_id()
        assert id2 == id1 + 1

    def test_starts_at_one(self):
        client = MCPClient("http://localhost:3000")
        assert client._next_id() == 1


# ── URL Handling ───────────────────────────────────────────

class TestURLHandling:
    def test_strips_trailing_slash(self):
        client = MCPClient("http://localhost:3000/")
        assert client.server_url == "http://localhost:3000"

    def test_preserves_path(self):
        client = MCPClient("http://localhost:3000/mcp")
        assert client.server_url == "http://localhost:3000/mcp"


# ── Context Manager ────────────────────────────────────────

class TestContextManager:
    def test_can_use_as_context_manager(self):
        with MCPClient("http://localhost:3000") as client:
            assert client.server_url == "http://localhost:3000"

    def test_close_doesnt_raise(self):
        client = MCPClient("http://localhost:3000")
        client.close()  # Should not raise


# ── Connection Errors ──────────────────────────────────────

class TestConnectionErrors:
    def test_unreachable_server(self):
        """Connecting to a non-existent server should raise MCPClientError."""
        client = MCPClient("http://127.0.0.1:19999", timeout=1.0)
        with pytest.raises(MCPClientError, match="Connection failed"):
            client.ping()

    def test_is_reachable_returns_false(self):
        client = MCPClient("http://127.0.0.1:19999", timeout=1.0)
        assert client.is_reachable() is False


# ── Timeout ────────────────────────────────────────────────

class TestTimeout:
    def test_custom_timeout(self):
        client = MCPClient("http://localhost:3000", timeout=5.0)
        assert client.timeout == 5.0
