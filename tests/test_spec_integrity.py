"""
Tests for mcpcrunch.conformance.tests.spec_integrity (CT-3.8.x)

Tests all 5 static spec integrity checks against various valid,
invalid, and edge-case OpenMCP specifications.
"""

import pytest
import json
from mcpcrunch.conformance.tests import spec_integrity
from mcpcrunch.conformance.models import TestStatus

# Aliases to keep test code clean
_run_all = spec_integrity.run_all
_check_3_8_1 = spec_integrity.test_3_8_1_schema_validity
_check_3_8_2 = spec_integrity.test_3_8_2_component_references
_check_3_8_3 = spec_integrity.test_3_8_3_circular_references
_check_3_8_4 = spec_integrity.test_3_8_4_unused_components
_check_3_8_5 = spec_integrity.test_3_8_5_name_collisions


# ── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def openmcp_schema():
    with open("schema.json", "r") as f:
        return json.load(f)


VALID_SPEC = {
    "openmcp": "1.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com"}],
    "tools": {
        "echo": {
            "description": "Echo tool",
            "input": {
                "type": "object",
                "properties": {"message": {"type": "string", "maxLength": 100}},
                "additionalProperties": False,
            },
            "output": {
                "type": "object",
                "properties": {"response": {"type": "string", "maxLength": 200}},
            },
            "security": [{"bearerAuth": []}],
        }
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        }
    },
}

SPEC_WITH_REFS = {
    "openmcp": "1.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "tools": {
        "create_user": {
            "description": "Create user",
            "input": {"$ref": "#/components/schemas/UserInput"},
            "output": {"$ref": "#/components/schemas/UserOutput"},
        }
    },
    "components": {
        "schemas": {
            "UserInput": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            },
            "UserOutput": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
            },
        }
    },
}

SPEC_WITH_DANGLING_REF = {
    "openmcp": "1.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "tools": {
        "broken": {
            "description": "Broken tool",
            "input": {"$ref": "#/components/schemas/DoesNotExist"},
            "output": {"type": "object"},
        }
    },
}

SPEC_WITH_SECURITY = {
    "openmcp": "1.0.0",
    "info": {"title": "Test", "version": "1.0.0"},
    "tools": {
        "secure_tool": {
            "description": "Secured",
            "input": {"type": "object"},
            "output": {"type": "object"},
            "security": [{"bearerAuth": ["admin"]}],
        }
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer"},
        }
    },
}


# ── CT-3.8.1: Schema Validity ──────────────────────────────

class TestSchemaValidity:
    def test_valid_spec_passes(self, openmcp_schema):
        result = _check_3_8_1(VALID_SPEC, openmcp_schema)
        assert result.test_id == "CT-3.8.1"
        assert result.status == TestStatus.PASSED

    def test_invalid_spec_fails(self, openmcp_schema):
        invalid = {"not_openmcp": True}  # Missing required fields
        result = _check_3_8_1(invalid, openmcp_schema)
        assert result.status == TestStatus.FAILED

    def test_no_schema_skips(self):
        result = _check_3_8_1(VALID_SPEC, None)
        assert result.status == TestStatus.SKIPPED

    def test_missing_info_field(self, openmcp_schema):
        spec = {"openmcp": "1.0.0", "tools": {"t": {"input": {}, "output": {}}}}
        result = _check_3_8_1(spec, openmcp_schema)
        assert result.status == TestStatus.FAILED

    def test_missing_version(self, openmcp_schema):
        spec = {"info": {"title": "Test", "version": "1"}, "tools": {"t": {"input": {}, "output": {}}}}
        result = _check_3_8_1(spec, openmcp_schema)
        assert result.status == TestStatus.FAILED


# ── CT-3.8.2: Component References ─────────────────────────

class TestComponentReferences:
    def test_valid_refs_pass(self):
        result = _check_3_8_2(SPEC_WITH_REFS)
        assert result.test_id == "CT-3.8.2"
        assert result.status == TestStatus.PASSED

    def test_dangling_ref_fails(self):
        result = _check_3_8_2(SPEC_WITH_DANGLING_REF)
        assert result.status == TestStatus.FAILED
        assert "DoesNotExist" in result.actual

    def test_no_refs_passes(self):
        result = _check_3_8_2(VALID_SPEC)
        assert result.status == TestStatus.PASSED

    def test_multiple_dangling_refs(self):
        spec = {
            "openmcp": "1.0.0",
            "info": {"title": "T", "version": "1"},
            "tools": {
                "a": {"input": {"$ref": "#/components/schemas/Missing1"}, "output": {"$ref": "#/components/schemas/Missing2"}},
            },
        }
        result = _check_3_8_2(spec)
        assert result.status == TestStatus.FAILED


# ── CT-3.8.3: Circular References ──────────────────────────

class TestCircularReferences:
    def test_no_cycles_passes(self):
        result = _check_3_8_3(SPEC_WITH_REFS)
        assert result.test_id == "CT-3.8.3"
        assert result.status == TestStatus.PASSED

    def test_no_refs_passes(self):
        result = _check_3_8_3(VALID_SPEC)
        assert result.status == TestStatus.PASSED

    def test_simple_spec_passes(self):
        spec = {"openmcp": "1.0.0", "info": {"title": "T", "version": "1"}, "tools": {}}
        result = _check_3_8_3(spec)
        assert result.status == TestStatus.PASSED


# ── CT-3.8.4: Unused Components ────────────────────────────

class TestUnusedComponents:
    def test_all_used_passes(self):
        result = _check_3_8_4(SPEC_WITH_REFS)
        assert result.test_id == "CT-3.8.4"
        assert result.status == TestStatus.PASSED

    def test_unused_schema_warning(self):
        spec = {
            "openmcp": "1.0.0",
            "info": {"title": "T", "version": "1"},
            "tools": {"t": {"input": {}, "output": {}}},
            "components": {
                "schemas": {"UnusedSchema": {"type": "object"}},
            },
        }
        result = _check_3_8_4(spec)
        # Still PASSES but with warning
        assert result.status == TestStatus.PASSED
        assert "Unused" in result.actual or "warning" in (result.message or "")

    def test_no_components_passes(self):
        result = _check_3_8_4(VALID_SPEC)
        assert result.status == TestStatus.PASSED

    def test_security_scheme_used_via_tool_security(self):
        result = _check_3_8_4(SPEC_WITH_SECURITY)
        assert result.status == TestStatus.PASSED

    def test_unused_security_scheme(self):
        spec = {
            "openmcp": "1.0.0",
            "info": {"title": "T", "version": "1"},
            "tools": {"t": {"input": {}, "output": {}}},
            "components": {
                "securitySchemes": {
                    "unused": {"type": "apiKey", "name": "x", "in": "header"},
                },
            },
        }
        result = _check_3_8_4(spec)
        assert "Unused" in result.actual or "warning" in (result.message or "")


# ── CT-3.8.5: Name Collisions ─────────────────────────────

class TestNameCollisions:
    def test_unique_names_pass(self):
        result = _check_3_8_5(VALID_SPEC)
        assert result.test_id == "CT-3.8.5"
        assert result.status == TestStatus.PASSED

    def test_tool_prompt_collision(self):
        spec = {
            "openmcp": "1.0.0",
            "info": {"title": "T", "version": "1"},
            "tools": {"duplicate": {"input": {}, "output": {}}},
            "prompts": {"duplicate": {"input": {}, "output": {}}},
        }
        result = _check_3_8_5(spec)
        assert result.status == TestStatus.FAILED
        assert "duplicate" in result.actual

    def test_tool_resource_collision(self):
        spec = {
            "openmcp": "1.0.0",
            "info": {"title": "T", "version": "1"},
            "tools": {"shared_name": {"input": {}, "output": {}}},
            "resources": {"shared_name": {"output": {}}},
        }
        result = _check_3_8_5(spec)
        assert result.status == TestStatus.FAILED

    def test_no_collision_different_names(self):
        spec = {
            "openmcp": "1.0.0",
            "info": {"title": "T", "version": "1"},
            "tools": {"tool_1": {"input": {}, "output": {}}},
            "prompts": {"prompt_1": {"input": {}, "output": {}}},
            "resources": {"resource_1": {"output": {}}},
        }
        result = _check_3_8_5(spec)
        assert result.status == TestStatus.PASSED
        assert "3" in result.actual  # 3 total entities

    def test_empty_namespaces(self):
        spec = {"openmcp": "1.0.0", "info": {"title": "T", "version": "1"}}
        result = _check_3_8_5(spec)
        assert result.status == TestStatus.PASSED


# ── run_all ────────────────────────────────────────────────

class TestRunAll:
    def test_returns_thirteen_results(self, openmcp_schema):
        results = _run_all(VALID_SPEC, openmcp_schema)
        assert len(results) == 13

    def test_all_ids_present(self, openmcp_schema):
        results = _run_all(VALID_SPEC, openmcp_schema)
        ids = [r.test_id for r in results]
        for i in range(1, 14):
            assert f"CT-3.8.{i}" in ids, f"CT-3.8.{i} missing"

    def test_valid_spec_all_pass(self, openmcp_schema):
        results = _run_all(VALID_SPEC, openmcp_schema)
        assert all(r.status == TestStatus.PASSED for r in results)

    def test_without_schema(self):
        results = _run_all(VALID_SPEC, None)
        assert len(results) == 13
        assert results[0].status == TestStatus.SKIPPED  # 3.8.1 skipped

    def test_against_example_specs(self, openmcp_schema):
        """Run against all example specs in the repo."""
        import os
        example_dir = "examples"
        for filename in os.listdir(example_dir):
            if filename.endswith(".json"):
                with open(os.path.join(example_dir, filename)) as f:
                    spec = json.load(f)
                results = _run_all(spec, openmcp_schema)
                assert len(results) == 13, f"Failed for {filename}"
                # All should at least not ERROR
                for r in results:
                    assert r.status != TestStatus.ERROR, f"{filename}: {r.test_id} errored: {r.message}"
