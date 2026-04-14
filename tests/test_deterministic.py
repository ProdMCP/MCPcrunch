import pytest
from mcpcrunch.validators.deterministic import DeterministicValidator
from mcpcrunch.models import Severity

@pytest.fixture
def validator():
    return DeterministicValidator("schema.json")

def test_fmt_001_id_version(validator):
    # Invalid version
    spec = {"openmcp": "1.0", "info": {"title": "T", "version": "1"}}
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-FMT-001" for i in issues)

    # Valid version
    spec = {"openmcp": "1.0.0", "info": {"title": "T", "version": "1"}}
    issues = validator.validate(spec)
    assert not any(i.rule_id == "OMCP-FMT-001" for i in issues)

def test_fmt_002_metadata(validator):
    spec = {"openmcp": "1.0.0", "info": {"title": "Test"}} # Missing version
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-FMT-002" for i in issues)

def test_sec_002_query_key(validator):
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "T", "version": "1"},
        "components": {
            "securitySchemes": {
                "key": {"type": "apiKey", "in": "query", "name": "k"}
            }
        }
    }
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-SEC-002" for i in issues)

def test_dat_001_strict_objects(validator):
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "T", "version": "1"},
        "tools": {
            "t": {
                "input": {"type": "object", "properties": {"a": {"type": "string", "maxLength": 1}}, "additionalProperties": True}
            }
        }
    }
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-DAT-001" for i in issues)

def test_dat_003_string_length(validator):
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "T", "version": "1"},
        "tools": {
            "t": {
                "input": {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": False}
            }
        }
    }
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-DAT-003" for i in issues)

def test_sec_005_transport_safety(validator):
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "T", "version": "1"},
        "servers": [{"url": "http://api.com"}]
    }
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-SEC-005" for i in issues)

def test_protocol_error_handling_rules(validator):
    """Test OMCP-SEC-008 through OMCP-SEC-011 (Protocol Error Handling)."""
    # 1. Missing all
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "T", "version": "1"},
        "tools": {
            "t1": {
                "input": {"type": "object", "properties": {"a": {"type": "string", "maxLength": 10}}, "additionalProperties": False},
                "error_handling": {"422": {"type": "object"}}
            }
        }
    }
    issues = validator.validate(spec)
    rule_ids = {i.rule_id for i in issues}
    assert "OMCP-SEC-008" in rule_ids # 406
    assert "OMCP-SEC-009" in rule_ids # 415
    assert "OMCP-SEC-010" in rule_ids # 429
    assert "OMCP-SEC-011" in rule_ids # default

    # 2. Valid all
    spec["tools"]["t1"]["error_handling"].update({
        "406": {"type": "object"},
        "415": {"type": "object"},
        "429": {"type": "object"},
        "default": {"type": "object"}
    })
    issues = validator.validate(spec)
    rule_ids = {i.rule_id for i in issues}
    assert "OMCP-SEC-008" not in rule_ids
    assert "OMCP-SEC-009" not in rule_ids
    assert "OMCP-SEC-010" not in rule_ids
    assert "OMCP-SEC-011" not in rule_ids


def test_sec_012_missing_operation_security(validator):
    """OMCP-SEC-012: fires when securitySchemes present but no global security and operations lack security."""
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "T", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}
        },
        "paths": {
            "/prompts/summarize": {"post": {"operationId": "summarize", "responses": {"200": {"description": "ok"}}}},
        }
    }
    issues = validator.validate(spec)
    assert any(i.rule_id == "OMCP-SEC-012" for i in issues)
    affected = [i for i in issues if i.rule_id == "OMCP-SEC-012"]
    assert any("/prompts/summarize" in i.path for i in affected)


def test_sec_012_suppressed_by_global_security(validator):
    """OMCP-SEC-012: does NOT fire when a top-level 'security' field is set."""
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "T", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com"}],
        "security": [{"bearer": []}],
        "components": {
            "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}
        },
        "paths": {
            "/prompts/summarize": {"post": {"operationId": "summarize", "responses": {"200": {"description": "ok"}}}},
        }
    }
    issues = validator.validate(spec)
    assert not any(i.rule_id == "OMCP-SEC-012" for i in issues)


def test_sec_012_suppressed_by_operation_security(validator):
    """OMCP-SEC-012: does NOT fire when the operation defines its own security."""
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "T", "version": "1.0.0"},
        "servers": [{"url": "https://api.example.com"}],
        "components": {
            "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}
        },
        "paths": {
            "/tools/do_thing": {
                "post": {
                    "operationId": "do_thing",
                    "security": [{"bearer": []}],
                    "responses": {"200": {"description": "ok"}},
                }
            },
        }
    }
    issues = validator.validate(spec)
    assert not any(i.rule_id == "OMCP-SEC-012" for i in issues)


def test_sec_012_no_false_positive_without_schemes(validator):
    """OMCP-SEC-012: must NOT fire when there are no securitySchemes at all."""
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "T", "version": "1.0.0"},
        "paths": {
            "/tools/open_tool": {"post": {"operationId": "open", "responses": {"200": {"description": "ok"}}}},
        }
    }
    issues = validator.validate(spec)
    assert not any(i.rule_id == "OMCP-SEC-012" for i in issues)
