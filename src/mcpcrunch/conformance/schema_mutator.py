"""
Conformance Test Suite — Schema Mutator

Deterministic mutation engine that generates test inputs from a JSON Schema.
All mutations are deterministic: same schema → same test cases.
"""

import copy
import random
import string
from typing import Any, Dict, Generator, List, Optional, Tuple


# Fixed seed for deterministic generation
_RNG = random.Random(42)


def _random_string(length: int = 8) -> str:
    """Generate a deterministic pseudo-random string."""
    return "".join(_RNG.choices(string.ascii_lowercase, k=length))


def _random_int(min_val: int = 0, max_val: int = 100) -> int:
    return _RNG.randint(min_val, max_val)


def _random_float(min_val: float = 0.0, max_val: float = 100.0) -> float:
    return round(_RNG.uniform(min_val, max_val), 2)


def generate_valid_input(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a valid instance that satisfies the given JSON Schema.
    Handles type: object with properties, and basic scalar types.
    """
    if not isinstance(schema, dict):
        return {}

    schema_type = schema.get("type", "object")

    if schema_type == "object":
        result = {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            result[prop_name] = _generate_value_for_schema(prop_schema)
        return result
    else:
        return _generate_value_for_schema(schema)


def _generate_value_for_schema(schema: Dict[str, Any]) -> Any:
    """Generate a single valid value for a given schema."""
    if not isinstance(schema, dict):
        return "test_value"

    schema_type = schema.get("type", "string")

    # Handle enum first
    if "enum" in schema:
        return schema["enum"][0] if schema["enum"] else None

    # Handle const
    if "const" in schema:
        return schema["const"]

    # Handle default
    if "default" in schema:
        return schema["default"]

    if schema_type == "string":
        max_len = schema.get("maxLength", 20)
        min_len = schema.get("minLength", 1)
        length = max(min_len, min(max_len, 8))
        if "pattern" in schema:
            # Best-effort: return a simple matching string
            return _random_string(length)
        return _random_string(length)

    elif schema_type == "integer":
        min_val = schema.get("minimum", 0)
        max_val = schema.get("maximum", 100)
        return _random_int(int(min_val), int(max_val))

    elif schema_type == "number":
        min_val = schema.get("minimum", 0.0)
        max_val = schema.get("maximum", 100.0)
        return _random_float(float(min_val), float(max_val))

    elif schema_type == "boolean":
        return True

    elif schema_type == "array":
        items_schema = schema.get("items", {"type": "string"})
        min_items = schema.get("minItems", 1)
        max_items = schema.get("maxItems", 3)
        count = max(min_items, min(max_items, 2))
        return [_generate_value_for_schema(items_schema) for _ in range(count)]

    elif schema_type == "object":
        return generate_valid_input(schema)

    elif schema_type == "null":
        return None

    # Fallback for arrays of types (e.g., ["string", "null"])
    elif isinstance(schema_type, list):
        non_null = [t for t in schema_type if t != "null"]
        if non_null:
            return _generate_value_for_schema({**schema, "type": non_null[0]})
        return None

    return "test_value"


def generate_missing_required(
    schema: Dict[str, Any],
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """
    For each required field, yield (field_name, mutated_input) with that field removed.
    """
    required = schema.get("required", [])
    if not required:
        return

    base = generate_valid_input(schema)

    for field in required:
        if field in base:
            mutated = copy.deepcopy(base)
            del mutated[field]
            yield (field, mutated)


def generate_extra_properties(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a valid input with additional undeclared properties injected.
    """
    base = generate_valid_input(schema)
    base["__injected_field"] = "malicious_value"
    base["__extra_number"] = 99999
    return base


def generate_type_violations(
    schema: Dict[str, Any],
) -> Generator[Tuple[str, str, Any, Dict[str, Any]], None, None]:
    """
    For each property, yield (prop_name, original_type, wrong_value, mutated_input).
    """
    properties = schema.get("properties", {})
    if not properties:
        return

    base = generate_valid_input(schema)
    type_swaps = {
        "string": 42,
        "integer": "not_a_number",
        "number": "not_a_number",
        "boolean": "not_a_bool",
        "object": [1, 2, 3],
        "array": {"not": "an_array"},
    }

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        if isinstance(prop_type, list):
            prop_type = prop_type[0]
        if prop_type in type_swaps:
            mutated = copy.deepcopy(base)
            wrong_value = type_swaps[prop_type]
            mutated[prop_name] = wrong_value
            yield (prop_name, prop_type, wrong_value, mutated)


def generate_constraint_violations(
    schema: Dict[str, Any],
) -> Generator[Tuple[str, str, Any, Dict[str, Any]], None, None]:
    """
    For each property with constraints, yield (prop_name, constraint, wrong_value, mutated_input).
    """
    properties = schema.get("properties", {})
    if not properties:
        return

    base = generate_valid_input(schema)

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")

        # minLength violation
        if "minLength" in prop_schema and prop_type == "string":
            mutated = copy.deepcopy(base)
            min_len = prop_schema["minLength"]
            if min_len > 0:
                mutated[prop_name] = ""
                yield (prop_name, "minLength", "", mutated)

        # maxLength violation
        if "maxLength" in prop_schema and prop_type == "string":
            mutated = copy.deepcopy(base)
            max_len = prop_schema["maxLength"]
            long_string = "x" * (max_len + 10)
            mutated[prop_name] = long_string
            yield (prop_name, "maxLength", long_string, mutated)

        # minimum violation
        if "minimum" in prop_schema and prop_type in ("integer", "number"):
            mutated = copy.deepcopy(base)
            below = prop_schema["minimum"] - 1
            mutated[prop_name] = below
            yield (prop_name, "minimum", below, mutated)

        # maximum violation
        if "maximum" in prop_schema and prop_type in ("integer", "number"):
            mutated = copy.deepcopy(base)
            above = prop_schema["maximum"] + 1
            mutated[prop_name] = above
            yield (prop_name, "maximum", above, mutated)

        # enum violation
        if "enum" in prop_schema:
            mutated = copy.deepcopy(base)
            bad_val = "__NOT_IN_ENUM__"
            mutated[prop_name] = bad_val
            yield (prop_name, "enum", bad_val, mutated)

        # pattern violation
        if "pattern" in prop_schema and prop_type == "string":
            mutated = copy.deepcopy(base)
            bad_val = "!!!invalid!!!"
            mutated[prop_name] = bad_val
            yield (prop_name, "pattern", bad_val, mutated)

        # minItems violation
        if "minItems" in prop_schema and prop_type == "array":
            mutated = copy.deepcopy(base)
            mutated[prop_name] = []
            yield (prop_name, "minItems", [], mutated)

        # maxItems violation
        if "maxItems" in prop_schema and prop_type == "array":
            mutated = copy.deepcopy(base)
            max_items = prop_schema["maxItems"]
            items_schema = prop_schema.get("items", {"type": "string"})
            overflow = [_generate_value_for_schema(items_schema) for _ in range(max_items + 5)]
            mutated[prop_name] = overflow
            yield (prop_name, "maxItems", overflow, mutated)


def generate_null_violations(
    schema: Dict[str, Any],
) -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """
    For each non-nullable property, yield (prop_name, mutated_input) with null.
    """
    properties = schema.get("properties", {})
    if not properties:
        return

    base = generate_valid_input(schema)

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type")
        nullable = prop_schema.get("nullable", False)

        # Check if null is allowed via type list
        is_null_allowed = False
        if isinstance(prop_type, list) and "null" in prop_type:
            is_null_allowed = True
        if nullable:
            is_null_allowed = True
        if prop_type == "null":
            is_null_allowed = True

        if not is_null_allowed:
            mutated = copy.deepcopy(base)
            mutated[prop_name] = None
            yield (prop_name, mutated)


def generate_deep_violations(
    schema: Dict[str, Any],
) -> Generator[Tuple[str, str, Dict[str, Any]], None, None]:
    """
    For nested object properties, break the inner schema.
    Yields (path, violation_type, mutated_input).
    """
    properties = schema.get("properties", {})
    if not properties:
        return

    base = generate_valid_input(schema)

    for prop_name, prop_schema in properties.items():
        if prop_schema.get("type") == "object" and prop_schema.get("properties"):
            nested_props = prop_schema.get("properties", {})
            nested_required = prop_schema.get("required", [])

            # Missing required nested field
            for nested_field in nested_required:
                if nested_field in nested_props:
                    mutated = copy.deepcopy(base)
                    if isinstance(mutated.get(prop_name), dict) and nested_field in mutated[prop_name]:
                        del mutated[prop_name][nested_field]
                        yield (f"{prop_name}.{nested_field}", "missing_required", mutated)

            # Type violation in nested field
            for nested_name, nested_schema in nested_props.items():
                nested_type = nested_schema.get("type", "string")
                if isinstance(nested_type, list):
                    nested_type = nested_type[0]
                type_swaps = {
                    "string": 42,
                    "integer": "wrong",
                    "number": "wrong",
                    "boolean": "wrong",
                }
                if nested_type in type_swaps:
                    mutated = copy.deepcopy(base)
                    if isinstance(mutated.get(prop_name), dict):
                        mutated[prop_name][nested_name] = type_swaps[nested_type]
                        yield (f"{prop_name}.{nested_name}", "type_violation", mutated)
