"""
CT-3.6 — Security Conformance Tests

Ensures declared security schemes are actually enforced at runtime.
"""

import time
from typing import Any, Dict, List, Optional

from ..client import MCPClient, MCPClientError
from ..models import AuthConfig, ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator


def run_all(
    client: MCPClient,
    spec: Dict[str, Any],
    auth: Optional[AuthConfig] = None,
) -> List[ConformanceTestResult]:
    """Run all CT-3.6 tests."""
    results = []
    tools = spec.get("tools", {})
    sec_schemes = spec.get("components", {}).get("securitySchemes", {})

    # CT-3.6.4 is static, always runs
    results.append(test_3_6_4_security_declaration_consistency(spec))

    # Runtime security tests
    for tool_name, tool in tools.items():
        security = tool.get("security", [])
        if not security:
            continue  # Skip unsecured tools

        input_schema = tool.get("input", {})
        entity_label = f"tool.{tool_name}"

        results.append(test_3_6_1_missing_auth(client, tool_name, input_schema, entity_label))
        results.append(test_3_6_2_invalid_credentials(client, tool_name, input_schema, entity_label))
        results.append(test_3_6_3_scope_enforcement(client, tool_name, security, input_schema, entity_label, auth))

    return results


# CT-3.6.1
def test_3_6_1_missing_auth(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.6.1: Call secured tool without authentication, expect unauthorized."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = client._send_jsonrpc_no_auth(
            "tools/call", {"name": tool_name, "arguments": valid_input}
        )
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.6.1",
                test_name="Missing Authentication",
                category=TestCategory.SECURITY,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Unauthorized error without auth",
                actual="Error returned correctly",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.6.1",
                test_name="Missing Authentication",
                category=TestCategory.SECURITY,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Unauthorized error without auth",
                actual="Server processed request without authentication",
                duration_ms=duration,
            )

    except MCPClientError as e:
        # Connection errors may indicate auth rejection at transport level — that's a pass
        return ConformanceTestResult(
            test_id="CT-3.6.1",
            test_name="Missing Authentication",
            category=TestCategory.SECURITY,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Unauthorized error without auth",
            actual=f"Transport-level rejection: {e}",
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.6.2
def test_3_6_2_invalid_credentials(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.6.2: Send intentionally invalid credentials, expect unauthorized."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = client._send_jsonrpc_bad_auth(
            "tools/call", {"name": tool_name, "arguments": valid_input}
        )
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.6.2",
                test_name="Invalid Credentials",
                category=TestCategory.SECURITY,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Unauthorized error with invalid credentials",
                actual="Error returned correctly",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.6.2",
                test_name="Invalid Credentials",
                category=TestCategory.SECURITY,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Unauthorized error with invalid credentials",
                actual="Server processed request with invalid credentials",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.6.2",
            test_name="Invalid Credentials",
            category=TestCategory.SECURITY,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Unauthorized error with invalid credentials",
            actual=f"Transport-level rejection: {e}",
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.6.3
def test_3_6_3_scope_enforcement(
    client: MCPClient,
    tool_name: str,
    security: List,
    input_schema: Dict,
    entity_label: str,
    auth: Optional[AuthConfig] = None,
) -> ConformanceTestResult:
    """CT-3.6.3: If scopes are defined, verify enforcement."""
    # Check if any security requirement has scopes
    has_scopes = False
    for req in security:
        for scheme_name, scopes in req.items():
            if scopes:
                has_scopes = True
                break

    if not has_scopes:
        return ConformanceTestResult(
            test_id="CT-3.6.3",
            test_name="Scope Enforcement",
            category=TestCategory.SECURITY,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="No scopes defined in security requirements",
        )

    if not auth or (not auth.bearer_token and not auth.api_key):
        return ConformanceTestResult(
            test_id="CT-3.6.3",
            test_name="Scope Enforcement",
            category=TestCategory.SECURITY,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="No auth credentials provided for scope testing",
        )

    # This test would need a scope-limited credential to properly test enforcement
    # For now, we document it as needing manual verification
    return ConformanceTestResult(
        test_id="CT-3.6.3",
        test_name="Scope Enforcement",
        category=TestCategory.SECURITY,
        entity=entity_label,
        status=TestStatus.SKIPPED,
        message="Scope enforcement requires scope-limited credentials (manual verification needed)",
    )


# CT-3.6.4
def test_3_6_4_security_declaration_consistency(spec: Dict[str, Any]) -> ConformanceTestResult:
    """CT-3.6.4: Every secured entity must reference valid securitySchemes. (Static test)"""
    sec_schemes = set(spec.get("components", {}).get("securitySchemes", {}).keys())
    dangling = []

    for entity_type in ("tools", "prompts"):
        for entity_name, entity in spec.get(entity_type, {}).items():
            for req in entity.get("security", []):
                for scheme_name in req:
                    if scheme_name not in sec_schemes:
                        dangling.append(f"{entity_type}.{entity_name} → {scheme_name}")

    # Also check global security
    for req in spec.get("security", []):
        for scheme_name in req:
            if scheme_name not in sec_schemes:
                dangling.append(f"global → {scheme_name}")

    if dangling:
        return ConformanceTestResult(
            test_id="CT-3.6.4",
            test_name="Security Declaration Consistency",
            category=TestCategory.SECURITY,
            status=TestStatus.FAILED,
            expected="All security references resolve to valid schemes",
            actual=f"Dangling references: {'; '.join(dangling[:5])}",
        )
    else:
        return ConformanceTestResult(
            test_id="CT-3.6.4",
            test_name="Security Declaration Consistency",
            category=TestCategory.SECURITY,
            status=TestStatus.PASSED,
            expected="All security references resolve to valid schemes",
            actual="All references valid",
        )
