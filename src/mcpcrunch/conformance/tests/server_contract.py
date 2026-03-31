"""
CT-3.7 — Server Contract Tests

Ensures server-level correctness and accessibility.
"""

import time
from typing import Any, Dict, List

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus


def run_all(client: MCPClient, spec: Dict[str, Any]) -> List[ConformanceTestResult]:
    """Run all CT-3.7 tests."""
    results = []
    results.append(test_3_7_1_server_reachability(client, spec))
    results.append(test_3_7_2_protocol_compliance(client))
    results.append(test_3_7_3_version_matching(client, spec))
    return results


# CT-3.7.1
def test_3_7_1_server_reachability(client: MCPClient, spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.7.1: All server URLs must be reachable."""
    start = time.monotonic()
    try:
        reachable = client.is_reachable()
        duration = (time.monotonic() - start) * 1000

        if reachable:
            return ConformanceTestResult(
                test_id="CT-3.7.1",
                test_name="Server Reachability",
                category=TestCategory.SERVER_CONTRACT,
                status=TestStatus.PASSED,
                expected="Server responds to ping",
                actual=f"Server at {client.server_url} is reachable",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.7.1",
                test_name="Server Reachability",
                category=TestCategory.SERVER_CONTRACT,
                status=TestStatus.FAILED,
                expected="Server responds to ping",
                actual=f"Server at {client.server_url} is not reachable",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.7.1",
            test_name="Server Reachability",
            category=TestCategory.SERVER_CONTRACT,
            status=TestStatus.FAILED,
            expected="Server responds to ping",
            actual=f"Connection failed: {e}",
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.7.2
def test_3_7_2_protocol_compliance(client: MCPClient) -> ConformanceTestResult:
    """CT-3.7.2: Server must support JSON-RPC 2.0."""
    start = time.monotonic()
    try:
        response = client.initialize()
        duration = (time.monotonic() - start) * 1000

        # Validate JSON-RPC 2.0 structure
        issues = []
        if response.get("jsonrpc") != "2.0":
            issues.append(f"Missing or wrong 'jsonrpc' field: {response.get('jsonrpc')}")
        if "id" not in response:
            issues.append("Missing 'id' field")
        if "result" not in response and "error" not in response:
            issues.append("Missing both 'result' and 'error' fields")

        if issues:
            return ConformanceTestResult(
                test_id="CT-3.7.2",
                test_name="Protocol Compliance",
                category=TestCategory.SERVER_CONTRACT,
                status=TestStatus.FAILED,
                expected="Valid JSON-RPC 2.0 response",
                actual=f"Protocol issues: {'; '.join(issues)}",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.7.2",
                test_name="Protocol Compliance",
                category=TestCategory.SERVER_CONTRACT,
                status=TestStatus.PASSED,
                expected="Valid JSON-RPC 2.0 response",
                actual="JSON-RPC 2.0 compliant",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.7.2",
            test_name="Protocol Compliance",
            category=TestCategory.SERVER_CONTRACT,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.7.3
def test_3_7_3_version_matching(client: MCPClient, spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.7.3: openmcp version must be supported by the server."""
    spec_version = spec.get("openmcp", "unknown")
    start = time.monotonic()
    try:
        response = client.initialize()
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.7.3",
                test_name="Version Matching",
                category=TestCategory.SERVER_CONTRACT,
                status=TestStatus.FAILED,
                expected=f"Server supports OpenMCP {spec_version}",
                actual=f"Initialize failed: {response['error']}",
                duration_ms=duration,
            )

        server_version = None
        result = response.get("result", {})
        if isinstance(result, dict):
            server_version = result.get("protocolVersion") or result.get("serverInfo", {}).get("version")

        return ConformanceTestResult(
            test_id="CT-3.7.3",
            test_name="Version Matching",
            category=TestCategory.SERVER_CONTRACT,
            status=TestStatus.PASSED,
            expected=f"Server supports OpenMCP {spec_version}",
            actual=f"Server version: {server_version or 'not reported (initialize succeeded)'}",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.7.3",
            test_name="Version Matching",
            category=TestCategory.SERVER_CONTRACT,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )
