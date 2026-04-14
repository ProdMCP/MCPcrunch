from mcpcrunch.engine import MCPcrunch
from mcpcrunch.models import CapabilityScore

def test_engine_audit_no_llm():
    crunch = MCPcrunch("schema.json")
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "servers": [{"url": "https://api.com"}]
    }
    report = crunch.audit(spec)
    
    assert report.overall_score == 100
    assert len(report.deterministic.issues) == 0
    assert report.semantic.score == 100
    assert len(report.semantic.issues) == 0


def test_engine_audit_vulnerable():
    crunch = MCPcrunch("schema.json")
    spec = {
        "openmcp": "1.0",  # OMCP-FMT-001 (CRITICAL) → -20 from val pool
        "info": {"title": "Test"}  # OMCP-FMT-002 (HIGH) → -10 from val pool
    }
    report = crunch.audit(spec)
    # sec=30, val=70-20-10=40 → total=70
    assert report.overall_score == 70
    assert report.deterministic.security_score == 30
    assert report.deterministic.validation_score == 40
    assert len(report.deterministic.issues) == 2


def test_engine_capability_scores_exposed():
    """report.deterministic.capability_scores must be a list of CapabilityScore."""
    crunch = MCPcrunch("schema.json")
    spec = {
        "openmcp": "1.0.0",
        "info": {"title": "T", "version": "1.0.0"},
        "tools": {"my_tool": {"input": {"type": "object", "additionalProperties": False, "properties": {"q": {"type": "string", "maxLength": 10}}}, "output": {"type": "object", "additionalProperties": False}}},
    }
    report = crunch.audit(spec)
    for cap in report.deterministic.capability_scores:
        assert isinstance(cap, CapabilityScore)
        assert cap.type in {"tool", "prompt", "resource"}
