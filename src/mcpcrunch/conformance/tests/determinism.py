"""
CT-3.10 — Determinism Tests

Ensures MCP server behavior is predictable and consistent for AI agents.
"""

import time
from typing import Any, Dict, List

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator
from .schema_output import _extract_shape, _get_output_data


def run_all(
    client: MCPClient,
    spec: Dict[str, Any],
    runs: int = 3,
) -> List[ConformanceTestResult]:
    """Run all CT-3.10 tests."""
    results = []
    tools = spec.get("tools", {})

    for tool_name, tool in tools.items():
        input_schema = tool.get("input", {})
        output_schema = tool.get("output", {})
        entity_label = f"tool.{tool_name}"

        results.append(test_3_10_1_schema_determinism(client, tool_name, input_schema, entity_label, runs))
        results.append(test_3_10_2_contract_stability(client, tool_name, input_schema, entity_label, runs))
        results.append(test_3_10_3_no_undeclared_fields(client, tool_name, input_schema, output_schema, entity_label, runs))

    return results


# CT-3.10.1
def test_3_10_1_schema_determinism(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str, runs: int = 3
) -> ConformanceTestResult:
    """CT-3.10.1: Output shape must NOT change across runs."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        shapes = []

        for _ in range(runs):
            response = client.call_tool(tool_name, valid_input)
            if "error" not in response:
                output_data = _get_output_data(response)
                shapes.append(_extract_shape(output_data))

        duration = (time.monotonic() - start) * 1000

        if len(shapes) < 2:
            return ConformanceTestResult(
                test_id="CT-3.10.1",
                test_name="Schema Determinism",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Not enough successful responses to compare",
                duration_ms=duration,
            )

        all_same = all(s == shapes[0] for s in shapes)
        if all_same:
            return ConformanceTestResult(
                test_id="CT-3.10.1",
                test_name="Schema Determinism",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Identical shape across runs",
                actual=f"Shape stable across {len(shapes)} runs",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.10.1",
                test_name="Schema Determinism",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Identical shape across runs",
                actual="Output shape varies between runs",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.10.1",
            test_name="Schema Determinism",
            category=TestCategory.DETERMINISM,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.10.2
def test_3_10_2_contract_stability(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str, runs: int = 3
) -> ConformanceTestResult:
    """CT-3.10.2: Same input → same accept/reject behavior across runs."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)

        # Test valid input consistency
        valid_results = []
        for _ in range(runs):
            response = client.call_tool(tool_name, valid_input)
            valid_results.append("error" not in response)

        # Test invalid input consistency
        violations = list(schema_mutator.generate_type_violations(input_schema))
        invalid_results = []
        if violations:
            _, _, _, mutated = violations[0]
            for _ in range(runs):
                response = client.call_tool(tool_name, mutated)
                invalid_results.append("error" in response)

        duration = (time.monotonic() - start) * 1000

        issues = []
        if valid_results and not all(r == valid_results[0] for r in valid_results):
            issues.append("Valid input produces inconsistent accept/reject")
        if invalid_results and not all(r == invalid_results[0] for r in invalid_results):
            issues.append("Invalid input produces inconsistent accept/reject")

        if issues:
            return ConformanceTestResult(
                test_id="CT-3.10.2",
                test_name="Tool Contract Stability",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Consistent accept/reject behavior",
                actual="; ".join(issues),
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.10.2",
                test_name="Tool Contract Stability",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Consistent accept/reject behavior",
                actual=f"Stable behavior across {runs} runs",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.10.2",
            test_name="Tool Contract Stability",
            category=TestCategory.DETERMINISM,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.10.3
def test_3_10_3_no_undeclared_fields(
    client: MCPClient, tool_name: str, input_schema: Dict, output_schema: Dict,
    entity_label: str, runs: int = 3
) -> ConformanceTestResult:
    """CT-3.10.3: Runtime must not introduce fields not in the spec across any run."""
    start = time.monotonic()
    declared_fields = set(output_schema.get("properties", {}).keys())

    if not declared_fields:
        return ConformanceTestResult(
            test_id="CT-3.10.3",
            test_name="No Undeclared Fields",
            category=TestCategory.DETERMINISM,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="No output properties declared in schema",
        )

    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        all_fields_seen = set()

        for _ in range(runs):
            response = client.call_tool(tool_name, valid_input)
            if "error" not in response:
                output_data = _get_output_data(response)
                if isinstance(output_data, dict):
                    all_fields_seen.update(output_data.keys())

        duration = (time.monotonic() - start) * 1000

        if not all_fields_seen:
            return ConformanceTestResult(
                test_id="CT-3.10.3",
                test_name="No Undeclared Fields",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="No output fields observed across runs",
                duration_ms=duration,
            )

        undeclared = all_fields_seen - declared_fields
        # Check if additionalProperties is allowed
        additional_allowed = output_schema.get("additionalProperties", True) is not False

        if undeclared and not additional_allowed:
            return ConformanceTestResult(
                test_id="CT-3.10.3",
                test_name="No Undeclared Fields",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Only declared fields in output",
                actual=f"Undeclared fields: {sorted(undeclared)}",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.10.3",
                test_name="No Undeclared Fields",
                category=TestCategory.DETERMINISM,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Only declared fields in output",
                actual=f"All fields match schema across {runs} runs"
                       + (f" (extra fields allowed by schema: {sorted(undeclared)})" if undeclared else ""),
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.10.3",
            test_name="No Undeclared Fields",
            category=TestCategory.DETERMINISM,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )
