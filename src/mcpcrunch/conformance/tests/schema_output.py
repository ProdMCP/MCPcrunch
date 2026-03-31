"""
CT-3.2 — Output Conformance Tests

Ensures runtime output matches the declared output schema.
"""

import time
from typing import Any, Dict, List

import jsonschema

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator


def run_all(
    client: MCPClient,
    spec: Dict[str, Any],
    entity_type: str = "tools",
) -> List[ConformanceTestResult]:
    """Run all CT-3.2 tests for every entity with an output schema."""
    results = []
    entities = spec.get(entity_type, {})

    for entity_name, entity in entities.items():
        output_schema = entity.get("output")
        input_schema = entity.get("input", {})
        if not output_schema or not isinstance(output_schema, dict):
            continue

        call_fn = client.call_tool if entity_type == "tools" else client.get_prompt
        entity_label = f"{entity_type[:-1]}.{entity_name}"

        results.append(test_3_2_1_output_schema_validation(call_fn, entity_name, input_schema, output_schema, entity_label))
        results.append(test_3_2_2_missing_output_fields(call_fn, entity_name, input_schema, output_schema, entity_label))
        results.append(test_3_2_3_extra_output_fields(call_fn, entity_name, input_schema, output_schema, entity_label))
        results.append(test_3_2_4_type_mismatch_output(call_fn, entity_name, input_schema, output_schema, entity_label))
        results.append(test_3_2_5_deterministic_structure(call_fn, entity_name, input_schema, entity_label))

    return results


def _get_output_data(response: Dict[str, Any]) -> Any:
    """Extract the actual output data from a JSON-RPC response."""
    if "error" in response:
        return None
    result = response.get("result", {})
    # MCP tool results are in result.content[0].text usually, or just result
    if isinstance(result, dict) and "content" in result:
        content = result["content"]
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and "text" in first:
                try:
                    import json
                    return json.loads(first["text"])
                except (json.JSONDecodeError, TypeError):
                    return first.get("text", first)
            return first
    return result


def _extract_shape(data: Any) -> Any:
    """Extract the structural shape of data (keys + types, recursively)."""
    if isinstance(data, dict):
        return {k: _extract_shape(v) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        if data:
            return [_extract_shape(data[0])]
        return ["empty"]
    else:
        return type(data).__name__


# CT-3.2.1
def test_3_2_1_output_schema_validation(
    call_fn, entity_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.2.1: Validate full response against declared output schema."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = call_fn(entity_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.2.1",
                test_name="Output Schema Validation",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message=f"Server returned error, cannot validate output: {response['error']}",
                duration_ms=duration,
            )

        output_data = _get_output_data(response)
        if output_data is None:
            return ConformanceTestResult(
                test_id="CT-3.2.1",
                test_name="Output Schema Validation",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Valid output data",
                actual="No output data in response",
                duration_ms=duration,
            )

        try:
            jsonschema.validate(instance=output_data, schema=output_schema)
            return ConformanceTestResult(
                test_id="CT-3.2.1",
                test_name="Output Schema Validation",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Output validates against schema",
                actual="Validation passed",
                duration_ms=duration,
            )
        except jsonschema.ValidationError as e:
            return ConformanceTestResult(
                test_id="CT-3.2.1",
                test_name="Output Schema Validation",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Output validates against schema",
                actual=f"Validation error: {e.message}",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.2.1",
            test_name="Output Schema Validation",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.2.2
def test_3_2_2_missing_output_fields(
    call_fn, entity_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.2.2: Check if server omits required output fields."""
    start = time.monotonic()
    required_fields = output_schema.get("required", [])
    if not required_fields:
        return ConformanceTestResult(
            test_id="CT-3.2.2",
            test_name="Missing Output Fields",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="No required fields defined in output schema",
        )

    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = call_fn(entity_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.2.2",
                test_name="Missing Output Fields",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Server returned error, cannot check output fields",
                duration_ms=duration,
            )

        output_data = _get_output_data(response)
        if not isinstance(output_data, dict):
            return ConformanceTestResult(
                test_id="CT-3.2.2",
                test_name="Missing Output Fields",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Output is not an object, cannot check fields",
                duration_ms=duration,
            )

        missing = [f for f in required_fields if f not in output_data]
        if missing:
            return ConformanceTestResult(
                test_id="CT-3.2.2",
                test_name="Missing Output Fields",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected=f"Required fields present: {required_fields}",
                actual=f"Missing: {missing}",
                duration_ms=duration,
            )
        return ConformanceTestResult(
            test_id="CT-3.2.2",
            test_name="Missing Output Fields",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="All required output fields present",
            actual="All present",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.2.2",
            test_name="Missing Output Fields",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.2.3
def test_3_2_3_extra_output_fields(
    call_fn, entity_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.2.3: Check for undeclared fields in output."""
    start = time.monotonic()
    declared_props = set(output_schema.get("properties", {}).keys())
    additional = output_schema.get("additionalProperties")

    if not declared_props:
        return ConformanceTestResult(
            test_id="CT-3.2.3",
            test_name="Extra Fields in Output",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.SKIPPED,
            message="No properties defined in output schema",
        )

    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = call_fn(entity_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.2.3",
                test_name="Extra Fields in Output",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Server returned error",
                duration_ms=duration,
            )

        output_data = _get_output_data(response)
        if not isinstance(output_data, dict):
            return ConformanceTestResult(
                test_id="CT-3.2.3",
                test_name="Extra Fields in Output",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Output is not an object",
                duration_ms=duration,
            )

        extra = set(output_data.keys()) - declared_props
        if extra and additional is False:
            return ConformanceTestResult(
                test_id="CT-3.2.3",
                test_name="Extra Fields in Output",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="No extra fields when additionalProperties is false",
                actual=f"Extra fields: {sorted(extra)}",
                duration_ms=duration,
            )

        return ConformanceTestResult(
            test_id="CT-3.2.3",
            test_name="Extra Fields in Output",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="No undeclared extra fields",
            actual="Output fields match schema" + (f" (extra: {sorted(extra)} — allowed)" if extra else ""),
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.2.3",
            test_name="Extra Fields in Output",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.2.4
def test_3_2_4_type_mismatch_output(
    call_fn, entity_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.2.4: Validate every output field has the correct type."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = call_fn(entity_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.2.4",
                test_name="Type Mismatch in Output",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Server returned error",
                duration_ms=duration,
            )

        output_data = _get_output_data(response)
        props = output_schema.get("properties", {})
        mismatches = []

        if isinstance(output_data, dict):
            for prop_name, prop_schema in props.items():
                if prop_name in output_data:
                    expected_type = prop_schema.get("type")
                    actual_value = output_data[prop_name]
                    if expected_type and not _type_matches(actual_value, expected_type):
                        mismatches.append(f"{prop_name}: expected {expected_type}, got {type(actual_value).__name__}")

        if mismatches:
            return ConformanceTestResult(
                test_id="CT-3.2.4",
                test_name="Type Mismatch in Output",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="All output field types correct",
                actual=f"Mismatches: {'; '.join(mismatches)}",
                duration_ms=duration,
            )

        return ConformanceTestResult(
            test_id="CT-3.2.4",
            test_name="Type Mismatch in Output",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="All output field types correct",
            actual="All types match",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.2.4",
            test_name="Type Mismatch in Output",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.2.5
def test_3_2_5_deterministic_structure(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str, runs: int = 3
) -> ConformanceTestResult:
    """CT-3.2.5: Same input → same output shape across runs."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        shapes = []

        for _ in range(runs):
            response = call_fn(entity_name, valid_input)
            if "error" in response:
                continue
            output_data = _get_output_data(response)
            shapes.append(_extract_shape(output_data))

        duration = (time.monotonic() - start) * 1000

        if len(shapes) < 2:
            return ConformanceTestResult(
                test_id="CT-3.2.5",
                test_name="Deterministic Output Structure",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Not enough successful responses to compare",
                duration_ms=duration,
            )

        all_same = all(s == shapes[0] for s in shapes)
        if all_same:
            return ConformanceTestResult(
                test_id="CT-3.2.5",
                test_name="Deterministic Output Structure",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Identical shape across runs",
                actual=f"Shape consistent across {len(shapes)} runs",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.2.5",
                test_name="Deterministic Output Structure",
                category=TestCategory.SCHEMA_OUTPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Identical shape across runs",
                actual="Output shape varies between invocations",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.2.5",
            test_name="Deterministic Output Structure",
            category=TestCategory.SCHEMA_OUTPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


def _type_matches(value: Any, expected_type: str) -> bool:
    """Check if a Python value matches a JSON Schema type."""
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    if isinstance(expected_type, list):
        return any(_type_matches(value, t) for t in expected_type)
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    # Special case: bool is subclass of int in Python
    if expected_type == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, expected)
