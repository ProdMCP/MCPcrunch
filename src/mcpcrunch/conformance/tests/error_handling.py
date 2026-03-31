"""
CT-3.9 — Error Handling Conformance Tests

Ensures consistent, predictable failure behavior.
"""

import time
from typing import Any, Dict, List

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator


def run_all(client: MCPClient, spec: Dict[str, Any]) -> List[ConformanceTestResult]:
    """Run all CT-3.9 tests."""
    results = []
    tools = spec.get("tools", {})

    for tool_name, tool in tools.items():
        input_schema = tool.get("input", {})
        entity_label = f"tool.{tool_name}"

        results.append(test_3_9_1_invalid_input_returns_error(client, tool_name, input_schema, entity_label))
        results.append(test_3_9_2_error_structure(client, tool_name, input_schema, entity_label))
        results.append(test_3_9_3_no_silent_failures(client, tool_name, input_schema, entity_label))

    return results


# CT-3.9.1
def test_3_9_1_invalid_input_returns_error(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.9.1: Invalid input must NOT return success."""
    start = time.monotonic()
    try:
        # Generate a type-violated input
        violations = list(schema_mutator.generate_type_violations(input_schema))
        if not violations:
            return ConformanceTestResult(
                test_id="CT-3.9.1",
                test_name="Invalid Input Returns Error",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="No type violations possible for this schema",
            )

        _, _, _, mutated = violations[0]
        response = client.call_tool(tool_name, mutated)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.9.1",
                test_name="Invalid Input Returns Error",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Error for invalid input",
                actual="Error returned correctly",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.9.1",
                test_name="Invalid Input Returns Error",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Error for invalid input",
                actual="Success returned for invalid input",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.9.1",
            test_name="Invalid Input Returns Error",
            category=TestCategory.ERROR_HANDLING,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.9.2
def test_3_9_2_error_structure(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.9.2: Error responses must follow JSON-RPC error format."""
    start = time.monotonic()
    try:
        # Trigger an error by sending empty input when required fields exist
        required = input_schema.get("required", [])
        if not required:
            # Use type violation instead
            violations = list(schema_mutator.generate_type_violations(input_schema))
            if not violations:
                return ConformanceTestResult(
                    test_id="CT-3.9.2",
                    test_name="Error Structure",
                    category=TestCategory.ERROR_HANDLING,
                    entity=entity_label,
                    status=TestStatus.SKIPPED,
                    message="Cannot trigger an error for this schema",
                )
            _, _, _, mutated = violations[0]
            response = client.call_tool(tool_name, mutated)
        else:
            response = client.call_tool(tool_name, {})

        duration = (time.monotonic() - start) * 1000

        if "error" not in response:
            return ConformanceTestResult(
                test_id="CT-3.9.2",
                test_name="Error Structure",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Server did not return an error, cannot validate structure",
                duration_ms=duration,
            )

        error = response["error"]
        issues = []

        if not isinstance(error, dict):
            issues.append("Error is not an object")
        else:
            if "code" not in error:
                issues.append("Missing 'code' field")
            elif not isinstance(error["code"], int):
                issues.append(f"'code' is not an integer: {type(error['code']).__name__}")

            if "message" not in error:
                issues.append("Missing 'message' field")
            elif not isinstance(error["message"], str):
                issues.append(f"'message' is not a string: {type(error['message']).__name__}")

        if issues:
            return ConformanceTestResult(
                test_id="CT-3.9.2",
                test_name="Error Structure",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Error has 'code' (int) and 'message' (str)",
                actual=f"Structural issues: {'; '.join(issues)}",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.9.2",
                test_name="Error Structure",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Error has 'code' (int) and 'message' (str)",
                actual="Error structure is valid",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.9.2",
            test_name="Error Structure",
            category=TestCategory.ERROR_HANDLING,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.9.3
def test_3_9_3_no_silent_failures(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.9.3: Response must have result XOR error, never both or neither."""
    start = time.monotonic()
    try:
        # Test with valid input
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = client.call_tool(tool_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        has_result = "result" in response
        has_error = "error" in response

        if has_result and has_error:
            return ConformanceTestResult(
                test_id="CT-3.9.3",
                test_name="No Silent Failures",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Response has result XOR error",
                actual="Response contains BOTH result and error",
                duration_ms=duration,
            )
        elif not has_result and not has_error:
            return ConformanceTestResult(
                test_id="CT-3.9.3",
                test_name="No Silent Failures",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Response has result XOR error",
                actual="Response contains NEITHER result nor error",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.9.3",
                test_name="No Silent Failures",
                category=TestCategory.ERROR_HANDLING,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Response has result XOR error",
                actual="Unambiguous response",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.9.3",
            test_name="No Silent Failures",
            category=TestCategory.ERROR_HANDLING,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )
