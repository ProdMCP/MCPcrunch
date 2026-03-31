"""
Conformance Test Suite — MCP JSON-RPC Client

Minimal JSON-RPC 2.0 client for calling MCP servers over HTTP.
Supports tool invocation, prompt retrieval, resource reading, and initialization.
"""

import json
import time
from typing import Any, Dict, Optional
from .models import AuthConfig

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class MCPClientError(Exception):
    """Raised when the MCP client encounters a transport or protocol error."""
    pass


class MCPClient:
    """
    JSON-RPC 2.0 client for MCP servers.

    Usage (Python API):
        client = MCPClient("http://localhost:3000", auth=AuthConfig(bearer_token="tok"))
        result = client.call_tool("echo", {"message": "hello"})
    """

    def __init__(self, server_url: str, auth: Optional[AuthConfig] = None, timeout: float = 10.0):
        if not HAS_HTTPX:
            raise ImportError(
                "httpx is required for conformance testing. Install with: pip install httpx"
            )
        self.server_url = server_url.rstrip("/")
        self.auth = auth or AuthConfig()
        self.timeout = timeout
        self._request_id = 0
        self._client = httpx.Client(timeout=timeout)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers including authentication."""
        headers = {"Content-Type": "application/json"}
        if self.auth.bearer_token:
            headers["Authorization"] = f"Bearer {self.auth.bearer_token}"
        elif self.auth.api_key and self.auth.api_key_in == "header":
            header_name = self.auth.api_key_header_name or "Authorization"
            headers[header_name] = self.auth.api_key
        return headers

    def _build_params(self) -> Dict[str, str]:
        """Build query parameters for authentication if needed."""
        params = {}
        if self.auth.api_key and self.auth.api_key_in == "query":
            params["api_key"] = self.auth.api_key
        return params

    def _send_jsonrpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 request and return the full response dict.

        Returns the raw JSON-RPC response (may contain 'result' or 'error').
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        try:
            response = self._client.post(
                self.server_url,
                json=payload,
                headers=self._build_headers(),
                params=self._build_params(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise MCPClientError(f"Connection failed to {self.server_url}: {e}")
        except httpx.TimeoutException as e:
            raise MCPClientError(f"Request timed out after {self.timeout}s: {e}")
        except httpx.HTTPStatusError as e:
            raise MCPClientError(f"HTTP error {e.response.status_code}: {e}")
        except json.JSONDecodeError as e:
            raise MCPClientError(f"Invalid JSON response: {e}")

    def _send_jsonrpc_raw(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Like _send_jsonrpc but returns the response even on HTTP errors.
        Used for tests that expect errors.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        try:
            response = self._client.post(
                self.server_url,
                json=payload,
                headers=self._build_headers(),
                params=self._build_params(),
            )
            return response.json()
        except httpx.ConnectError as e:
            raise MCPClientError(f"Connection failed to {self.server_url}: {e}")
        except httpx.TimeoutException as e:
            raise MCPClientError(f"Request timed out after {self.timeout}s: {e}")
        except json.JSONDecodeError as e:
            raise MCPClientError(f"Invalid JSON response: {e}")

    def _send_jsonrpc_no_auth(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request WITHOUT authentication headers."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        try:
            response = self._client.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            return response.json()
        except httpx.ConnectError as e:
            raise MCPClientError(f"Connection failed to {self.server_url}: {e}")
        except httpx.TimeoutException as e:
            raise MCPClientError(f"Request timed out: {e}")
        except json.JSONDecodeError as e:
            raise MCPClientError(f"Invalid JSON response: {e}")

    def _send_jsonrpc_bad_auth(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request with intentionally invalid credentials."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        bad_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer __invalid_token_for_conformance_test__",
        }
        try:
            response = self._client.post(
                self.server_url,
                json=payload,
                headers=bad_headers,
            )
            return response.json()
        except httpx.ConnectError as e:
            raise MCPClientError(f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            raise MCPClientError(f"Request timed out: {e}")
        except json.JSONDecodeError as e:
            raise MCPClientError(f"Invalid JSON response: {e}")

    # ── Public API ──────────────────────────────────────────────

    def initialize(self) -> Dict[str, Any]:
        """Send MCP initialize handshake."""
        return self._send_jsonrpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcpcrunch-conformance",
                "version": "0.1.0",
            },
        })

    def ping(self) -> Dict[str, Any]:
        """Send MCP ping request."""
        return self._send_jsonrpc("ping")

    def list_tools(self) -> Dict[str, Any]:
        """List available tools on the server."""
        return self._send_jsonrpc("tools/list")

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.

        Returns the full JSON-RPC response (with 'result' or 'error').
        """
        params = {"name": name}
        if arguments is not None:
            params["arguments"] = arguments
        return self._send_jsonrpc_raw(method="tools/call", params=params)

    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a prompt from the MCP server."""
        params = {"name": name}
        if arguments is not None:
            params["arguments"] = arguments
        return self._send_jsonrpc_raw(method="prompts/get", params=params)

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the MCP server."""
        return self._send_jsonrpc_raw(method="resources/read", params={"uri": uri})

    def is_reachable(self) -> bool:
        """Check if the server is reachable."""
        try:
            self.ping()
            return True
        except MCPClientError:
            return False

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
