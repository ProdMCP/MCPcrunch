"""
CT-3.1 — Schema Input Conformance Tests

Ensures tool/prompt input strictly follows the declared JSON Schema.
"""

import time
from typing import Any, Dict, List, Optional

import jsonschema

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator


def run_all(
    client: MCPClient,
    spec: Dict[str, Any],
    entity_type: str = "tools",
) -> List[ConformanceTestResult]:
    """Run all CT-3.1 tests for every entity with an input schema."""
    results = []
    entities = spec.get(entity_type, {})

    for entity_name, entity in entities.items():
        input_schema = entity.get("input")
        if not input_schema or not isinstance(input_schema, dict):
            continue

        call_fn = client.call_tool if entity_type == "tools" else client.get_prompt
        entity_label = f"{entity_type[:-1]}.{entity_name}"  # e.g. "tool.echo"

        results.append(test_3_1_1_valid_input(call_fn, entity_name, input_schema, entity.get("output", {}), entity_label))
        results.extend(test_3_1_2_missing_required(call_fn, entity_name, input_schema, entity_label))
        results.append(test_3_1_3_additional_properties(call_fn, entity_name, input_schema, entity_label))
        results.extend(test_3_1_4_type_violations(call_fn, entity_name, input_schema, entity_label))
        results.extend(test_3_1_5_constraint_violations(call_fn, entity_name, input_schema, entity_label))
        results.extend(test_3_1_6_nullability_violations(call_fn, entity_name, input_schema, entity_label))
        results.extend(test_3_1_7_deep_violations(call_fn, entity_name, input_schema, entity_label))

    return results


# CT-3.1.1
def test_3_1_1_valid_input(
    call_fn, entity_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.1.1: Send valid input, expect success + output matches schema."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = call_fn(entity_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.1.1",
                test_name="Valid Input Happy Path",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Success response for valid input",
                actual=f"Error: {response['error'].get('message', str(response['error']))}",
                duration_ms=duration,
            )

        # Validate output schema if present
        result_data = response.get("result", {})
        if output_schema and isinstance(output_schema, dict) and output_schema.get("type"):
            try:
                jsonschema.validate(instance=result_data, schema=output_schema)
            except jsonschema.ValidationError as e:
                return ConformanceTestResult(
                    test_id="CT-3.1.1",
                    test_name="Valid Input Happy Path",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected="Output matches declared schema",
                    actual=f"Output schema mismatch: {e.message}",
                    duration_ms=duration,
                )

        return ConformanceTestResult(
            test_id="CT-3.1.1",
            test_name="Valid Input Happy Path",
            category=TestCategory.SCHEMA_INPUT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Success response for valid input",
            actual="Success",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.1.1",
            test_name="Valid Input Happy Path",
            category=TestCategory.SCHEMA_INPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.1.2
def test_3_1_2_missing_required(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str
) -> List[ConformanceTestResult]:
    """CT-3.1.2: Remove each required field one at a time, expect error."""
    results = []
    for field_name, mutated_input in schema_mutator.generate_missing_required(input_schema):
        start = time.monotonic()
        try:
            response = call_fn(entity_name, mutated_input)
            duration = (time.monotonic() - start) * 1000

            if "error" in response:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.2",
                    test_name=f"Missing Required Field: {field_name}",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected=f"Error when '{field_name}' is missing",
                    actual="Error returned correctly",
                    duration_ms=duration,
                ))
            else:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.2",
                    test_name=f"Missing Required Field: {field_name}",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected=f"Error when '{field_name}' is missing",
                    actual="Server accepted input with missing required field",
                    duration_ms=duration,
                ))
        except MCPClientError as e:
            results.append(ConformanceTestResult(
                test_id="CT-3.1.2",
                test_name=f"Missing Required Field: {field_name}",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            ))
    return results


# CT-3.1.3
def test_3_1_3_additional_properties(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.1.3: Inject undeclared properties, expect rejection if additionalProperties: false."""
    start = time.monotonic()
    try:
        mutated_input = schema_mutator.generate_extra_properties(input_schema)
        response = call_fn(entity_name, mutated_input)
        duration = (time.monotonic() - start) * 1000

        additional_props = input_schema.get("additionalProperties")

        if additional_props is False:
            # Must reject
            if "error" in response:
                return ConformanceTestResult(
                    test_id="CT-3.1.3",
                    test_name="Additional Properties Injection",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected="Rejection when additionalProperties is false",
                    actual="Correctly rejected",
                    duration_ms=duration,
                )
            else:
                return ConformanceTestResult(
                    test_id="CT-3.1.3",
                    test_name="Additional Properties Injection",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected="Rejection when additionalProperties is false",
                    actual="Server accepted input with undeclared properties",
                    duration_ms=duration,
                )
        else:
            # additionalProperties allowed — just pass (server may accept or ignore)
            return ConformanceTestResult(
                test_id="CT-3.1.3",
                test_name="Additional Properties Injection",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Server handles extra properties consistently",
                actual="additionalProperties is allowed, server responded",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.1.3",
            test_name="Additional Properties Injection",
            category=TestCategory.SCHEMA_INPUT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.1.4
def test_3_1_4_type_violations(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str
) -> List[ConformanceTestResult]:
    """CT-3.1.4: Send inputs with incorrect types, expect validation errors."""
    results = []
    for prop_name, original_type, wrong_value, mutated_input in schema_mutator.generate_type_violations(input_schema):
        start = time.monotonic()
        try:
            response = call_fn(entity_name, mutated_input)
            duration = (time.monotonic() - start) * 1000

            if "error" in response:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.4",
                    test_name=f"Type Violation: {prop_name} ({original_type}→{type(wrong_value).__name__})",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected=f"Error for type mismatch on '{prop_name}'",
                    actual="Error returned correctly",
                    duration_ms=duration,
                ))
            else:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.4",
                    test_name=f"Type Violation: {prop_name} ({original_type}→{type(wrong_value).__name__})",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected=f"Error for type mismatch on '{prop_name}'",
                    actual="Server accepted incorrectly typed input",
                    duration_ms=duration,
                ))
        except MCPClientError as e:
            results.append(ConformanceTestResult(
                test_id="CT-3.1.4",
                test_name=f"Type Violation: {prop_name}",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            ))
    return results


# CT-3.1.5
def test_3_1_5_constraint_violations(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str
) -> List[ConformanceTestResult]:
    """CT-3.1.5: Violate JSON Schema constraints (minLength, maxLength, enum, etc.)."""
    results = []
    for prop_name, constraint, wrong_value, mutated_input in schema_mutator.generate_constraint_violations(input_schema):
        start = time.monotonic()
        try:
            response = call_fn(entity_name, mutated_input)
            duration = (time.monotonic() - start) * 1000

            if "error" in response:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.5",
                    test_name=f"Constraint Violation: {prop_name}.{constraint}",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected=f"Error for {constraint} violation on '{prop_name}'",
                    actual="Error returned correctly",
                    duration_ms=duration,
                ))
            else:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.5",
                    test_name=f"Constraint Violation: {prop_name}.{constraint}",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected=f"Error for {constraint} violation on '{prop_name}'",
                    actual="Server accepted value violating constraint",
                    duration_ms=duration,
                ))
        except MCPClientError as e:
            results.append(ConformanceTestResult(
                test_id="CT-3.1.5",
                test_name=f"Constraint Violation: {prop_name}.{constraint}",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            ))
    return results


# CT-3.1.6
def test_3_1_6_nullability_violations(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str
) -> List[ConformanceTestResult]:
    """CT-3.1.6: Send null where not allowed, expect validation error."""
    results = []
    for prop_name, mutated_input in schema_mutator.generate_null_violations(input_schema):
        start = time.monotonic()
        try:
            response = call_fn(entity_name, mutated_input)
            duration = (time.monotonic() - start) * 1000

            if "error" in response:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.6",
                    test_name=f"Nullability Violation: {prop_name}",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected=f"Error when '{prop_name}' is null",
                    actual="Error returned correctly",
                    duration_ms=duration,
                ))
            else:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.6",
                    test_name=f"Nullability Violation: {prop_name}",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected=f"Error when '{prop_name}' is null",
                    actual="Server accepted null for non-nullable field",
                    duration_ms=duration,
                ))
        except MCPClientError as e:
            results.append(ConformanceTestResult(
                test_id="CT-3.1.6",
                test_name=f"Nullability Violation: {prop_name}",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            ))
    return results


# CT-3.1.7
def test_3_1_7_deep_violations(
    call_fn, entity_name: str, input_schema: Dict, entity_label: str
) -> List[ConformanceTestResult]:
    """CT-3.1.7: Break nested schemas, expect deep validation errors."""
    results = []
    for path, violation_type, mutated_input in schema_mutator.generate_deep_violations(input_schema):
        start = time.monotonic()
        try:
            response = call_fn(entity_name, mutated_input)
            duration = (time.monotonic() - start) * 1000

            if "error" in response:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.7",
                    test_name=f"Deep Violation: {path} ({violation_type})",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected=f"Error for nested violation at {path}",
                    actual="Error returned correctly",
                    duration_ms=duration,
                ))
            else:
                results.append(ConformanceTestResult(
                    test_id="CT-3.1.7",
                    test_name=f"Deep Violation: {path} ({violation_type})",
                    category=TestCategory.SCHEMA_INPUT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected=f"Error for nested violation at {path}",
                    actual="Server accepted invalid nested data",
                    duration_ms=duration,
                ))
        except MCPClientError as e:
            results.append(ConformanceTestResult(
                test_id="CT-3.1.7",
                test_name=f"Deep Violation: {path}",
                category=TestCategory.SCHEMA_INPUT,
                entity=entity_label,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.monotonic() - start) * 1000,
            ))
    return results
