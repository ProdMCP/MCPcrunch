from mcpcrunch.engine import MCPcrunch

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
        "openmcp": "1.0", # Invalid -20 (Critical)
        "info": {"title": "Test"} # Missing version -10 (High)
    }
    # Total penalty 30. Score 70.
    report = crunch.audit(spec)
    assert report.overall_score == 70
    assert len(report.deterministic.issues) == 2
