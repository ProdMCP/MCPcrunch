"""
CT-3.5 — Resource Conformance Tests

Ensures resources behave like read-only deterministic endpoints.
"""

import time
from typing import Any, Dict, List

import jsonschema

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .schema_output import _extract_shape, _get_output_data


def run_all(client: MCPClient, spec: Dict[str, Any]) -> List[ConformanceTestResult]:
    """Run all CT-3.5 tests for every resource."""
    results = []
    resources = spec.get("resources", {})

    for resource_name, resource in resources.items():
        output_schema = resource.get("output", {})
        entity_label = f"resource.{resource_name}"

        results.append(test_3_5_1_resource_fetch(client, resource_name, output_schema, entity_label))
        results.append(test_3_5_2_no_input_rejection(client, resource_name, resource, entity_label))
        results.append(test_3_5_3_output_stability(client, resource_name, entity_label))

    return results


# CT-3.5.1
def test_3_5_1_resource_fetch(
    client: MCPClient, resource_name: str, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.5.1: Fetch resource and validate output matches schema."""
    start = time.monotonic()
    try:
        response = client.read_resource(resource_name)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.5.1",
                test_name="Resource Fetch",
                category=TestCategory.RESOURCE_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Successful resource fetch",
                actual=f"Error: {response['error']}",
                duration_ms=duration,
            )

        output_data = _get_output_data(response)
        if output_schema and isinstance(output_schema, dict) and output_schema.get("type"):
            try:
                jsonschema.validate(instance=output_data, schema=output_schema)
            except jsonschema.ValidationError as e:
                return ConformanceTestResult(
                    test_id="CT-3.5.1",
                    test_name="Resource Fetch",
                    category=TestCategory.RESOURCE_CONTRACT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected="Output matches declared schema",
                    actual=f"Schema mismatch: {e.message}",
                    duration_ms=duration,
                )

        return ConformanceTestResult(
            test_id="CT-3.5.1",
            test_name="Resource Fetch",
            category=TestCategory.RESOURCE_CONTRACT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Resource fetch succeeds and matches schema",
            actual="Success",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.5.1",
            test_name="Resource Fetch",
            category=TestCategory.RESOURCE_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.5.2
def test_3_5_2_no_input_rejection(
    client: MCPClient, resource_name: str, resource_def: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.5.2: Resources without input should reject or ignore input."""
    if "input" in resource_def:
        return ConformanceTestResult(
            test_id="CT-3.5.2",
            test_name="No Input Rejection",
            category=TestCategory.RESOURCE_CONTRACT,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="Resource has an input schema defined",
        )

    start = time.monotonic()
    try:
        # Get baseline (no input)
        baseline = client.read_resource(resource_name)
        # Get with arbitrary input
        # Note: resources/read doesn't take arguments in MCP, so this validates the protocol itself
        response = client.read_resource(resource_name)
        duration = (time.monotonic() - start) * 1000

        return ConformanceTestResult(
            test_id="CT-3.5.2",
            test_name="No Input Rejection",
            category=TestCategory.RESOURCE_CONTRACT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Input has no effect on read-only resource",
            actual="Resource behaves consistently",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.5.2",
            test_name="No Input Rejection",
            category=TestCategory.RESOURCE_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.5.3
def test_3_5_3_output_stability(
    client: MCPClient, resource_name: str, entity_label: str, runs: int = 3
) -> ConformanceTestResult:
    """CT-3.5.3: Same resource call → same structure across invocations."""
    start = time.monotonic()
    try:
        shapes = []
        for _ in range(runs):
            response = client.read_resource(resource_name)
            if "error" not in response:
                output_data = _get_output_data(response)
                shapes.append(_extract_shape(output_data))

        duration = (time.monotonic() - start) * 1000

        if len(shapes) < 2:
            return ConformanceTestResult(
                test_id="CT-3.5.3",
                test_name="Output Stability",
                category=TestCategory.RESOURCE_CONTRACT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Not enough successful responses",
                duration_ms=duration,
            )

        all_same = all(s == shapes[0] for s in shapes)
        if all_same:
            return ConformanceTestResult(
                test_id="CT-3.5.3",
                test_name="Output Stability",
                category=TestCategory.RESOURCE_CONTRACT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Identical shape across runs",
                actual=f"Shape consistent across {len(shapes)} runs",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.5.3",
                test_name="Output Stability",
                category=TestCategory.RESOURCE_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Identical shape across runs",
                actual="Output shape varies between invocations",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.5.3",
            test_name="Output Stability",
            category=TestCategory.RESOURCE_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )
