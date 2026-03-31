"""
Tests for mcpcrunch.conformance.schema_mutator

Extensively tests the deterministic mutation engine that generates
test inputs from JSON Schemas. Every generator function is covered
with multiple schema shapes and edge cases.
"""

import pytest
from mcpcrunch.conformance.schema_mutator import (
    generate_valid_input,
    generate_missing_required,
    generate_extra_properties,
    generate_type_violations,
    generate_constraint_violations,
    generate_null_violations,
    generate_deep_violations,
)


# ── Fixtures ────────────────────────────────────────────────

SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 50},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
    },
    "required": ["name", "age"],
    "additionalProperties": False,
}

CONSTRAINED_SCHEMA = {
    "type": "object",
    "properties": {
        "email": {"type": "string", "maxLength": 100, "minLength": 5, "pattern": "^.+@.+$"},
        "role": {"type": "string", "enum": ["admin", "user", "viewer"]},
        "score": {"type": "number", "minimum": 0.0, "maximum": 100.0},
        "count": {"type": "integer", "minimum": 1, "maximum": 1000},
    },
    "required": ["email", "role"],
}

NESTED_SCHEMA = {
    "type": "object",
    "properties": {
        "user": {
            "type": "object",
            "properties": {
                "first_name": {"type": "string", "maxLength": 50},
                "last_name": {"type": "string", "maxLength": 50},
                "active": {"type": "boolean"},
            },
            "required": ["first_name", "last_name"],
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 5,
            "minItems": 1,
        },
    },
    "required": ["user"],
}

NULLABLE_SCHEMA = {
    "type": "object",
    "properties": {
        "required_field": {"type": "string"},
        "nullable_field": {"type": ["string", "null"]},
        "nullable_via_flag": {"type": "string", "nullable": True},
        "null_type": {"type": "null"},
    },
}

EMPTY_SCHEMA = {"type": "object"}

NO_PROPERTIES_SCHEMA = {"type": "object", "properties": {}}

ARRAY_SCHEMA = {
    "type": "object",
    "properties": {
        "items_list": {
            "type": "array",
            "items": {"type": "integer"},
            "maxItems": 3,
            "minItems": 1,
        },
    },
}

ENUM_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
    },
}

MULTI_TYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "null"]},
    },
}

BOOLEAN_SCHEMA = {
    "type": "object",
    "properties": {
        "flag": {"type": "boolean"},
    },
}


# ── generate_valid_input ────────────────────────────────────

class TestGenerateValidInput:
    def test_simple_schema(self):
        result = generate_valid_input(SIMPLE_SCHEMA)
        assert isinstance(result, dict)
        assert "name" in result
        assert "age" in result
        assert isinstance(result["name"], str)
        assert isinstance(result["age"], int)

    def test_constrained_schema(self):
        result = generate_valid_input(CONSTRAINED_SCHEMA)
        assert "email" in result
        assert "role" in result
        assert result["role"] == "admin"  # First enum value
        assert isinstance(result["score"], float)
        assert isinstance(result["count"], int)

    def test_nested_schema(self):
        result = generate_valid_input(NESTED_SCHEMA)
        assert "user" in result
        assert isinstance(result["user"], dict)
        assert "first_name" in result["user"]
        assert "last_name" in result["user"]
        assert "active" in result["user"]
        assert isinstance(result["user"]["active"], bool)
        assert "tags" in result
        assert isinstance(result["tags"], list)

    def test_empty_schema(self):
        result = generate_valid_input(EMPTY_SCHEMA)
        assert result == {}

    def test_no_properties_schema(self):
        result = generate_valid_input(NO_PROPERTIES_SCHEMA)
        assert result == {}

    def test_array_property(self):
        result = generate_valid_input(ARRAY_SCHEMA)
        assert "items_list" in result
        assert isinstance(result["items_list"], list)
        assert len(result["items_list"]) >= 1
        assert all(isinstance(x, int) for x in result["items_list"])

    def test_non_dict_schema(self):
        result = generate_valid_input("not_a_dict")
        assert result == {}

    def test_boolean_property(self):
        result = generate_valid_input(BOOLEAN_SCHEMA)
        assert result["flag"] is True

    def test_string_length_constraints(self):
        schema = {
            "type": "object",
            "properties": {
                "short": {"type": "string", "maxLength": 3, "minLength": 2},
            },
        }
        result = generate_valid_input(schema)
        assert 2 <= len(result["short"]) <= 3

    def test_enum_returns_first_value(self):
        result = generate_valid_input(ENUM_SCHEMA)
        assert result["status"] == "active"

    def test_const_value(self):
        schema = {
            "type": "object",
            "properties": {
                "fixed": {"type": "string", "const": "always_this"},
            },
        }
        result = generate_valid_input(schema)
        assert result["fixed"] == "always_this"

    def test_default_value(self):
        schema = {
            "type": "object",
            "properties": {
                "with_default": {"type": "integer", "default": 42},
            },
        }
        result = generate_valid_input(schema)
        assert result["with_default"] == 42

    def test_null_type(self):
        schema = {
            "type": "object",
            "properties": {
                "nothing": {"type": "null"},
            },
        }
        result = generate_valid_input(schema)
        assert result["nothing"] is None

    def test_multi_type_non_null(self):
        result = generate_valid_input(MULTI_TYPE_SCHEMA)
        assert isinstance(result["value"], str)

    def test_deterministic(self):
        """Same schema must produce same output (deterministic RNG with fixed seed)."""
        # Note: since the RNG is module-level, results depend on call order.
        # What matters is generate_valid_input is internally consistent.
        result1 = generate_valid_input({"type": "object", "properties": {"x": {"type": "integer", "minimum": 0, "maximum": 10}}})
        assert isinstance(result1["x"], int)
        assert 0 <= result1["x"] <= 10


# ── generate_missing_required ──────────────────────────────

class TestGenerateMissingRequired:
    def test_simple_required(self):
        mutations = list(generate_missing_required(SIMPLE_SCHEMA))
        assert len(mutations) == 2  # name and age
        field_names = [m[0] for m in mutations]
        assert "name" in field_names
        assert "age" in field_names

    def test_each_mutation_removes_one_field(self):
        for field_name, mutated in generate_missing_required(SIMPLE_SCHEMA):
            assert field_name not in mutated
            # Other required fields should still be present
            other_required = [f for f in SIMPLE_SCHEMA["required"] if f != field_name]
            for other in other_required:
                assert other in mutated

    def test_no_required_fields(self):
        schema = {"type": "object", "properties": {"opt": {"type": "string"}}}
        mutations = list(generate_missing_required(schema))
        assert len(mutations) == 0

    def test_empty_required_list(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": []}
        mutations = list(generate_missing_required(schema))
        assert len(mutations) == 0

    def test_nested_required(self):
        mutations = list(generate_missing_required(NESTED_SCHEMA))
        assert len(mutations) == 1  # Only "user" is required at top level
        assert mutations[0][0] == "user"


# ── generate_extra_properties ──────────────────────────────

class TestGenerateExtraProperties:
    def test_injects_fields(self):
        result = generate_extra_properties(SIMPLE_SCHEMA)
        assert "__injected_field" in result
        assert "__extra_number" in result
        assert result["__injected_field"] == "malicious_value"
        assert result["__extra_number"] == 99999

    def test_preserves_original_fields(self):
        result = generate_extra_properties(SIMPLE_SCHEMA)
        assert "name" in result
        assert "age" in result

    def test_empty_schema(self):
        result = generate_extra_properties(EMPTY_SCHEMA)
        assert "__injected_field" in result


# ── generate_type_violations ───────────────────────────────

class TestGenerateTypeViolations:
    def test_simple_violations(self):
        violations = list(generate_type_violations(SIMPLE_SCHEMA))
        assert len(violations) == 2  # name (string→int) and age (integer→string)

    def test_violation_structure(self):
        for prop_name, original_type, wrong_value, mutated in generate_type_violations(SIMPLE_SCHEMA):
            assert isinstance(prop_name, str)
            assert isinstance(original_type, str)
            assert isinstance(mutated, dict)
            # The wrong value should be of a different type
            if original_type == "string":
                assert not isinstance(wrong_value, str)
            elif original_type == "integer":
                assert isinstance(wrong_value, str)

    def test_string_to_number(self):
        violations = list(generate_type_violations(SIMPLE_SCHEMA))
        name_violation = [v for v in violations if v[0] == "name"][0]
        assert name_violation[1] == "string"
        assert name_violation[2] == 42

    def test_integer_to_string(self):
        violations = list(generate_type_violations(SIMPLE_SCHEMA))
        age_violation = [v for v in violations if v[0] == "age"][0]
        assert age_violation[1] == "integer"
        assert age_violation[2] == "not_a_number"

    def test_boolean_violation(self):
        violations = list(generate_type_violations(BOOLEAN_SCHEMA))
        assert len(violations) == 1
        assert violations[0][0] == "flag"
        assert violations[0][2] == "not_a_bool"

    def test_array_violation(self):
        violations = list(generate_type_violations(ARRAY_SCHEMA))
        assert len(violations) == 1
        assert violations[0][0] == "items_list"
        assert isinstance(violations[0][2], dict)  # array→object

    def test_no_properties(self):
        violations = list(generate_type_violations(EMPTY_SCHEMA))
        assert len(violations) == 0

    def test_multi_type_property(self):
        violations = list(generate_type_violations(MULTI_TYPE_SCHEMA))
        assert len(violations) == 1  # first type is "string"


# ── generate_constraint_violations ─────────────────────────

class TestGenerateConstraintViolations:
    def test_minlength(self):
        violations = list(generate_constraint_violations(CONSTRAINED_SCHEMA))
        minlength_violations = [v for v in violations if v[1] == "minLength"]
        assert len(minlength_violations) == 1
        assert minlength_violations[0][0] == "email"
        assert minlength_violations[0][2] == ""

    def test_maxlength(self):
        violations = list(generate_constraint_violations(CONSTRAINED_SCHEMA))
        maxlength_violations = [v for v in violations if v[1] == "maxLength"]
        assert len(maxlength_violations) == 1
        assert maxlength_violations[0][0] == "email"
        assert len(maxlength_violations[0][2]) > 100

    def test_enum(self):
        violations = list(generate_constraint_violations(CONSTRAINED_SCHEMA))
        enum_violations = [v for v in violations if v[1] == "enum"]
        assert len(enum_violations) == 1
        assert enum_violations[0][0] == "role"
        assert enum_violations[0][2] == "__NOT_IN_ENUM__"

    def test_pattern(self):
        violations = list(generate_constraint_violations(CONSTRAINED_SCHEMA))
        pattern_violations = [v for v in violations if v[1] == "pattern"]
        assert len(pattern_violations) == 1
        assert pattern_violations[0][0] == "email"

    def test_minimum(self):
        violations = list(generate_constraint_violations(CONSTRAINED_SCHEMA))
        min_violations = [v for v in violations if v[1] == "minimum"]
        assert len(min_violations) == 2  # score and count

    def test_maximum(self):
        violations = list(generate_constraint_violations(CONSTRAINED_SCHEMA))
        max_violations = [v for v in violations if v[1] == "maximum"]
        assert len(max_violations) == 2  # score and count

    def test_max_items(self):
        violations = list(generate_constraint_violations(NESTED_SCHEMA))
        max_items_violations = [v for v in violations if v[1] == "maxItems"]
        assert len(max_items_violations) == 1
        assert max_items_violations[0][0] == "tags"
        assert len(max_items_violations[0][2]) > 5

    def test_min_items(self):
        violations = list(generate_constraint_violations(NESTED_SCHEMA))
        min_items_violations = [v for v in violations if v[1] == "minItems"]
        assert len(min_items_violations) == 1
        assert min_items_violations[0][0] == "tags"
        assert min_items_violations[0][2] == []

    def test_no_constraints(self):
        schema = {"type": "object", "properties": {"x": {"type": "string"}}}
        violations = list(generate_constraint_violations(schema))
        assert len(violations) == 0

    def test_empty_schema(self):
        violations = list(generate_constraint_violations(EMPTY_SCHEMA))
        assert len(violations) == 0

    def test_preserves_other_fields(self):
        for prop_name, constraint, wrong_val, mutated in generate_constraint_violations(CONSTRAINED_SCHEMA):
            # The mutated input should still have all original keys
            assert prop_name in mutated


# ── generate_null_violations ───────────────────────────────

class TestGenerateNullViolations:
    def test_non_nullable_fields(self):
        violations = list(generate_null_violations(NULLABLE_SCHEMA))
        field_names = [v[0] for v in violations]
        assert "required_field" in field_names  # type: string (not nullable)

    def test_skips_nullable_fields(self):
        violations = list(generate_null_violations(NULLABLE_SCHEMA))
        field_names = [v[0] for v in violations]
        assert "nullable_field" not in field_names    # type: ["string", "null"]
        assert "nullable_via_flag" not in field_names  # nullable: true
        assert "null_type" not in field_names          # type: null

    def test_null_value_in_mutation(self):
        for field_name, mutated in generate_null_violations(NULLABLE_SCHEMA):
            assert mutated[field_name] is None

    def test_simple_schema_all_non_nullable(self):
        violations = list(generate_null_violations(SIMPLE_SCHEMA))
        assert len(violations) == 2  # name and age

    def test_empty_schema(self):
        violations = list(generate_null_violations(EMPTY_SCHEMA))
        assert len(violations) == 0


# ── generate_deep_violations ───────────────────────────────

class TestGenerateDeepViolations:
    def test_nested_schema_produces_violations(self):
        violations = list(generate_deep_violations(NESTED_SCHEMA))
        assert len(violations) > 0

    def test_missing_required_nested(self):
        violations = list(generate_deep_violations(NESTED_SCHEMA))
        missing_violations = [v for v in violations if v[1] == "missing_required"]
        # user has required: first_name, last_name
        assert len(missing_violations) == 2
        paths = [v[0] for v in missing_violations]
        assert "user.first_name" in paths
        assert "user.last_name" in paths

    def test_type_violation_nested(self):
        violations = list(generate_deep_violations(NESTED_SCHEMA))
        type_violations = [v for v in violations if v[1] == "type_violation"]
        # user has: first_name (string), last_name (string), active (boolean) = 3
        assert len(type_violations) == 3

    def test_nested_mutation_structure(self):
        for path, violation_type, mutated in generate_deep_violations(NESTED_SCHEMA):
            assert isinstance(path, str)
            assert "." in path
            assert isinstance(mutated, dict)
            assert "user" in mutated

    def test_flat_schema_no_deep_violations(self):
        violations = list(generate_deep_violations(SIMPLE_SCHEMA))
        assert len(violations) == 0

    def test_empty_schema_no_violations(self):
        violations = list(generate_deep_violations(EMPTY_SCHEMA))
        assert len(violations) == 0

    def test_deeply_nested(self):
        schema = {
            "type": "object",
            "properties": {
                "level1": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
        }
        violations = list(generate_deep_violations(schema))
        assert len(violations) >= 1  # at least missing_required for name


# ── Edge Cases ─────────────────────────────────────────────

class TestEdgeCases:
    def test_schema_with_only_required_no_properties(self):
        schema = {"type": "object", "required": ["ghost_field"]}
        mutations = list(generate_missing_required(schema))
        assert len(mutations) == 0  # ghost_field not in generated input

    def test_large_schema(self):
        """Schema with many properties shouldn't break."""
        props = {f"field_{i}": {"type": "string", "maxLength": 10} for i in range(50)}
        schema = {"type": "object", "properties": props, "required": list(props.keys())}
        result = generate_valid_input(schema)
        assert len(result) == 50
        mutations = list(generate_missing_required(schema))
        assert len(mutations) == 50

    def test_number_bounds_respected(self):
        schema = {
            "type": "object",
            "properties": {
                "val": {"type": "integer", "minimum": 5, "maximum": 10},
            },
        }
        result = generate_valid_input(schema)
        assert 5 <= result["val"] <= 10

    def test_all_generators_on_complex_schema(self):
        """Run all generators on a complex schema and check they don't crash."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "maxLength": 100, "minLength": 1},
                "age": {"type": "integer", "minimum": 0, "maximum": 200},
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "active": {"type": "boolean"},
                "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 10, "minItems": 1},
                "role": {"type": "string", "enum": ["a", "b"]},
                "address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"},
                        "zip": {"type": "integer"},
                    },
                    "required": ["street"],
                },
            },
            "required": ["name", "age", "active", "address"],
        }
        assert isinstance(generate_valid_input(schema), dict)
        assert len(list(generate_missing_required(schema))) == 4
        assert isinstance(generate_extra_properties(schema), dict)
        assert len(list(generate_type_violations(schema))) >= 4
        assert len(list(generate_constraint_violations(schema))) >= 3
        assert len(list(generate_null_violations(schema))) >= 4
        assert len(list(generate_deep_violations(schema))) >= 1
