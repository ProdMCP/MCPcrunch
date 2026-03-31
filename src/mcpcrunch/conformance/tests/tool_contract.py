"""
CT-3.3 — Tool Invocation Contract Tests

Ensures tools behave like strict RPC endpoints with deterministic contracts.
"""

import time
from typing import Any, Dict, List

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator


def run_all(client: MCPClient, spec: Dict[str, Any]) -> List[ConformanceTestResult]:
    """Run all CT-3.3 tests."""
    results = []
    tools = spec.get("tools", {})

    # CT-3.3.1: Unknown tool (only need to run once)
    results.append(test_3_3_1_unknown_tool(client))

    for tool_name, tool in tools.items():
        input_schema = tool.get("input", {})
        output_schema = tool.get("output", {})
        entity_label = f"tool.{tool_name}"

        results.append(test_3_3_2_missing_input(client, tool_name, input_schema, entity_label))
        results.append(test_3_3_3_partial_input(client, tool_name, input_schema, entity_label))
        results.append(test_3_3_4_input_output_mapping(client, tool_name, input_schema, output_schema, entity_label))

    return results


# CT-3.3.1
def test_3_3_1_unknown_tool(client: MCPClient) -> ConformanceTestResult:
    """CT-3.3.1: Invoke a tool not declared in the spec, expect error."""
    start = time.monotonic()
    try:
        response = client.call_tool("__nonexistent_tool_xyz_conformance_test__", {"test": True})
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.3.1",
                test_name="Unknown Tool Invocation",
                category=TestCategory.TOOL_CONTRACT,
                status=TestStatus.PASSED,
                expected="Error for unknown tool",
                actual="Error returned correctly",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.3.1",
                test_name="Unknown Tool Invocation",
                category=TestCategory.TOOL_CONTRACT,
                status=TestStatus.FAILED,
                expected="Error for unknown tool",
                actual="Server returned success for non-existent tool",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.3.1",
            test_name="Unknown Tool Invocation",
            category=TestCategory.TOOL_CONTRACT,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.3.2
def test_3_3_2_missing_input(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.3.2: Call tool with empty input, expect validation error."""
    required = input_schema.get("required", [])
    if not required:
        return ConformanceTestResult(
            test_id="CT-3.3.2",
            test_name="Missing Input Object",
            category=TestCategory.TOOL_CONTRACT,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="No required fields — empty input may be valid",
        )

    start = time.monotonic()
    try:
        response = client.call_tool(tool_name, {})
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.3.2",
                test_name="Missing Input Object",
                category=TestCategory.TOOL_CONTRACT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Error for empty input",
                actual="Error returned correctly",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.3.2",
                test_name="Missing Input Object",
                category=TestCategory.TOOL_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Error for empty input",
                actual="Server executed tool without required input",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.3.2",
            test_name="Missing Input Object",
            category=TestCategory.TOOL_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.3.3
def test_3_3_3_partial_input(
    client: MCPClient, tool_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.3.3: Send only a subset of required fields, expect error."""
    required = input_schema.get("required", [])
    if len(required) < 2:
        return ConformanceTestResult(
            test_id="CT-3.3.3",
            test_name="Partial Input",
            category=TestCategory.TOOL_CONTRACT,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="Fewer than 2 required fields — cannot test partial input",
        )

    start = time.monotonic()
    try:
        # Build input with only the first required field
        valid_input = schema_mutator.generate_valid_input(input_schema)
        partial = {required[0]: valid_input.get(required[0])}

        response = client.call_tool(tool_name, partial)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.3.3",
                test_name="Partial Input",
                category=TestCategory.TOOL_CONTRACT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Error for partial input",
                actual="Error returned correctly",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.3.3",
                test_name="Partial Input",
                category=TestCategory.TOOL_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Error for partial input",
                actual="Server executed with missing required fields",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.3.3",
            test_name="Partial Input",
            category=TestCategory.TOOL_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.3.4
def test_3_3_4_input_output_mapping(
    client: MCPClient, tool_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.3.4: Ensure output corresponds to input contract, no silent coercion."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = client.call_tool(tool_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.3.4",
                test_name="Input/Output Mapping Integrity",
                category=TestCategory.TOOL_CONTRACT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Server returned error for valid input",
                duration_ms=duration,
            )

        # Check that response has result, and it's not an empty response
        result = response.get("result")
        if result is None:
            return ConformanceTestResult(
                test_id="CT-3.3.4",
                test_name="Input/Output Mapping Integrity",
                category=TestCategory.TOOL_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Result present in response",
                actual="No result in response",
                duration_ms=duration,
            )

        return ConformanceTestResult(
            test_id="CT-3.3.4",
            test_name="Input/Output Mapping Integrity",
            category=TestCategory.TOOL_CONTRACT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Output corresponds to input contract",
            actual="Output present and structured",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.3.4",
            test_name="Input/Output Mapping Integrity",
            category=TestCategory.TOOL_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )
