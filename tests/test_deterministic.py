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
