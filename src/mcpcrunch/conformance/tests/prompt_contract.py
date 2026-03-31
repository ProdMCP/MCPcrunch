"""
CT-3.4 — Prompt Conformance Tests

Ensures prompts behave like structured templates with strict contracts.
"""

import time
from typing import Any, Dict, List

import jsonschema

from ..client import MCPClient, MCPClientError
from ..models import ConformanceTestResult, TestCategory, TestStatus
from .. import schema_mutator
from .schema_output import _extract_shape, _get_output_data


def run_all(client: MCPClient, spec: Dict[str, Any]) -> List[ConformanceTestResult]:
    """Run all CT-3.4 tests for every prompt."""
    results = []
    prompts = spec.get("prompts", {})

    for prompt_name, prompt in prompts.items():
        input_schema = prompt.get("input", {})
        output_schema = prompt.get("output", {})
        entity_label = f"prompt.{prompt_name}"

        results.append(test_3_4_1_prompt_input_validation(client, prompt_name, input_schema, entity_label))
        results.append(test_3_4_2_prompt_output_shape(client, prompt_name, input_schema, output_schema, entity_label))
        results.append(test_3_4_3_deterministic_template(client, prompt_name, input_schema, entity_label))

    return results


# CT-3.4.1
def test_3_4_1_prompt_input_validation(
    client: MCPClient, prompt_name: str, input_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.4.1: Apply input validation tests to prompt inputs."""
    start = time.monotonic()
    try:
        # Test with valid input first
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = client.get_prompt(prompt_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.4.1",
                test_name="Prompt Input Validation",
                category=TestCategory.PROMPT_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Success for valid prompt input",
                actual=f"Error: {response['error']}",
                duration_ms=duration,
            )

        # Now test with type-violated input
        violations = list(schema_mutator.generate_type_violations(input_schema))
        if violations:
            _, _, _, mutated = violations[0]
            invalid_response = client.get_prompt(prompt_name, mutated)
            if "error" not in invalid_response:
                return ConformanceTestResult(
                    test_id="CT-3.4.1",
                    test_name="Prompt Input Validation",
                    category=TestCategory.PROMPT_CONTRACT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected="Error for invalid prompt input",
                    actual="Prompt accepted invalid input",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

        return ConformanceTestResult(
            test_id="CT-3.4.1",
            test_name="Prompt Input Validation",
            category=TestCategory.PROMPT_CONTRACT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Valid input accepted, invalid rejected",
            actual="Input validation working correctly",
            duration_ms=(time.monotonic() - start) * 1000,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.4.1",
            test_name="Prompt Input Validation",
            category=TestCategory.PROMPT_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.4.2
def test_3_4_2_prompt_output_shape(
    client: MCPClient, prompt_name: str, input_schema: Dict, output_schema: Dict, entity_label: str
) -> ConformanceTestResult:
    """CT-3.4.2: Validate prompt output matches declared output schema."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        response = client.get_prompt(prompt_name, valid_input)
        duration = (time.monotonic() - start) * 1000

        if "error" in response:
            return ConformanceTestResult(
                test_id="CT-3.4.2",
                test_name="Prompt Output Shape",
                category=TestCategory.PROMPT_CONTRACT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Server returned error",
                duration_ms=duration,
            )

        output_data = _get_output_data(response)
        if output_schema and isinstance(output_schema, dict) and output_schema.get("type"):
            try:
                jsonschema.validate(instance=output_data, schema=output_schema)
                return ConformanceTestResult(
                    test_id="CT-3.4.2",
                    test_name="Prompt Output Shape",
                    category=TestCategory.PROMPT_CONTRACT,
                    entity=entity_label,
                    status=TestStatus.PASSED,
                    expected="Output matches schema",
                    actual="Validation passed",
                    duration_ms=duration,
                )
            except jsonschema.ValidationError as e:
                return ConformanceTestResult(
                    test_id="CT-3.4.2",
                    test_name="Prompt Output Shape",
                    category=TestCategory.PROMPT_CONTRACT,
                    entity=entity_label,
                    status=TestStatus.FAILED,
                    expected="Output matches schema",
                    actual=f"Validation error: {e.message}",
                    duration_ms=duration,
                )

        return ConformanceTestResult(
            test_id="CT-3.4.2",
            test_name="Prompt Output Shape",
            category=TestCategory.PROMPT_CONTRACT,
            entity=entity_label,
            status=TestStatus.PASSED,
            expected="Output present",
            actual="Response received",
            duration_ms=duration,
        )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.4.2",
            test_name="Prompt Output Shape",
            category=TestCategory.PROMPT_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )


# CT-3.4.3
def test_3_4_3_deterministic_template(
    client: MCPClient, prompt_name: str, input_schema: Dict, entity_label: str, runs: int = 3
) -> ConformanceTestResult:
    """CT-3.4.3: Same input → same prompt structure (not content)."""
    start = time.monotonic()
    try:
        valid_input = schema_mutator.generate_valid_input(input_schema)
        shapes = []

        for _ in range(runs):
            response = client.get_prompt(prompt_name, valid_input)
            if "error" not in response:
                output_data = _get_output_data(response)
                shapes.append(_extract_shape(output_data))

        duration = (time.monotonic() - start) * 1000

        if len(shapes) < 2:
            return ConformanceTestResult(
                test_id="CT-3.4.3",
                test_name="Deterministic Template Binding",
                category=TestCategory.PROMPT_CONTRACT,
                entity=entity_label,
                status=TestStatus.SKIPPED,
                message="Not enough successful responses",
                duration_ms=duration,
            )

        all_same = all(s == shapes[0] for s in shapes)
        if all_same:
            return ConformanceTestResult(
                test_id="CT-3.4.3",
                test_name="Deterministic Template Binding",
                category=TestCategory.PROMPT_CONTRACT,
                entity=entity_label,
                status=TestStatus.PASSED,
                expected="Identical shape across runs",
                actual=f"Shape consistent across {len(shapes)} runs",
                duration_ms=duration,
            )
        else:
            return ConformanceTestResult(
                test_id="CT-3.4.3",
                test_name="Deterministic Template Binding",
                category=TestCategory.PROMPT_CONTRACT,
                entity=entity_label,
                status=TestStatus.FAILED,
                expected="Identical shape across runs",
                actual="Prompt structure varies between invocations",
                duration_ms=duration,
            )

    except MCPClientError as e:
        return ConformanceTestResult(
            test_id="CT-3.4.3",
            test_name="Deterministic Template Binding",
            category=TestCategory.PROMPT_CONTRACT,
            entity=entity_label,
            status=TestStatus.ERROR,
            message=str(e),
            duration_ms=(time.monotonic() - start) * 1000,
        )
