"""Tests for the scoring module: partitioned sec/dat pools and per-capability bucketing."""
import pytest
from mcpcrunch.scoring import calculate_score, generate_report, _classify_entity
from mcpcrunch.models import ValidationIssue, Severity, CapabilityScore


# ── Helpers ───────────────────────────────────────────────────────────────────

def _issue(rule_id: str, path: str, severity: Severity = Severity.CRITICAL) -> ValidationIssue:
    return ValidationIssue(rule_id=rule_id, path=path, message="test", severity=severity)


# ── calculate_score ───────────────────────────────────────────────────────────

def test_score_perfect():
    total, sec, val = calculate_score([])
    assert total == 100
    assert sec == 30
    assert val == 70


def test_score_sec_penalty_only():
    """A pure security issue should only reduce the security pool."""
    issues = [_issue("OMCP-SEC-012", "$.paths['/prompts/foo'].post")]
    total, sec, val = calculate_score(issues)
    assert val == 70          # data validation untouched
    assert sec < 30           # security reduced
    assert total == sec + val


def test_score_dat_penalty_only():
    """A pure data issue should only reduce the validation pool."""
    issues = [_issue("OMCP-DAT-001", "$.tools.foo.input")]
    total, sec, val = calculate_score(issues)
    assert sec == 30          # security untouched
    assert val < 70           # validation reduced
    assert total == sec + val


def test_score_floors_at_zero():
    """Neither pool should go below 0."""
    many_critical = [_issue("OMCP-SEC-001", "$.x")] * 20
    total, sec, val = calculate_score(many_critical)
    assert sec == 0
    assert total >= 0

    many_dat = [_issue("OMCP-DAT-001", "$.x")] * 20
    total2, sec2, val2 = calculate_score(many_dat)
    assert val2 == 0
    assert total2 >= 0


def test_score_mixed_penalties():
    issues = [
        _issue("OMCP-SEC-005", "$.servers[0].url"),   # -20 from sec pool
        _issue("OMCP-DAT-003", "$.tools.t.input", Severity.HIGH),   # -10 from val pool
    ]
    total, sec, val = calculate_score(issues)
    assert sec == 10   # 30 - 20
    assert val == 60   # 70 - 10
    assert total == 70


def test_severity_weights_applied():
    """All severity levels are weighted correctly."""
    from mcpcrunch.scoring import SEVERITY_WEIGHTS
    assert SEVERITY_WEIGHTS[Severity.CRITICAL] == 20
    assert SEVERITY_WEIGHTS[Severity.HIGH] == 10
    assert SEVERITY_WEIGHTS[Severity.MEDIUM] == 5
    assert SEVERITY_WEIGHTS[Severity.LOW] == 2
    assert SEVERITY_WEIGHTS[Severity.INFO] == 0


# ── _classify_entity ──────────────────────────────────────────────────────────

def test_classify_openmcp_tool():
    assert _classify_entity("$.tools.create_ticket.input") == ("tool", "create_ticket")


def test_classify_openmcp_prompt():
    assert _classify_entity("$.prompts.summarize_text.input") == ("prompt", "summarize_text")


def test_classify_openmcp_resource():
    assert _classify_entity("$.resources.system_status.output") == ("resource", "system_status")


def test_classify_openapi_prompt_path():
    ep = _classify_entity("$.paths['/prompts/summarize_text'].post")
    assert ep == ("prompt", "summarize_text")


def test_classify_openapi_tool_path():
    ep = _classify_entity("$.paths['/tools/create_ticket'].post")
    assert ep == ("tool", "create_ticket")


def test_classify_openapi_resource_path():
    ep = _classify_entity("$.paths['/resources/{mcp_uri}'].get")
    assert ep[0] == "resource"


def test_classify_global_path_returns_none():
    assert _classify_entity("$.servers[0].url") is None
    assert _classify_entity("$.info.title") is None
    assert _classify_entity("$.components.securitySchemes.bearer") is None


# ── generate_report / capability_scores ───────────────────────────────────────

def test_report_capability_scores_populated():
    spec = {
        "openmcp": "1.0.0",
        "tools": {"create_ticket": {"input": {}, "output": {}}},
        "prompts": {"summarize": {"input": {}, "output": {}}},
        "resources": {"status": {"output": {}}},
    }
    issues = [
        _issue("OMCP-DAT-003", "$.tools.create_ticket.input", Severity.HIGH),
        _issue("OMCP-SEC-012", "$.paths['/prompts/summarize'].post"),
    ]
    report = generate_report(rules_count=10, issues=issues, spec=spec)

    names = {cap.name for cap in report.capability_scores}
    types = {cap.type for cap in report.capability_scores}

    assert "create_ticket" in names
    assert "summarize" in names
    assert "status" in names
    assert "tool" in types
    assert "prompt" in types
    assert "resource" in types


def test_report_capability_score_instance_type():
    """capability_scores items must be CapabilityScore instances."""
    report = generate_report(rules_count=5, issues=[], spec={})
    for cap in report.capability_scores:
        assert isinstance(cap, CapabilityScore)


def test_report_capability_issues_bucketed_correctly():
    """Issues must be assigned to the right capability."""
    spec = {
        "tools": {"my_tool": {}},
        "prompts": {"my_prompt": {}},
    }
    issues = [
        _issue("OMCP-DAT-001", "$.tools.my_tool.input"),
        _issue("OMCP-SEC-012", "$.paths['/prompts/my_prompt'].post"),
    ]
    report = generate_report(rules_count=10, issues=issues, spec=spec)

    tool_caps = [c for c in report.capability_scores if c.name == "my_tool"]
    prompt_caps = [c for c in report.capability_scores if c.name == "my_prompt"]

    assert len(tool_caps) == 1
    assert len(tool_caps[0].issues) == 1
    assert tool_caps[0].issues[0].rule_id == "OMCP-DAT-001"

    assert len(prompt_caps) == 1
    assert len(prompt_caps[0].issues) == 1
    assert prompt_caps[0].issues[0].rule_id == "OMCP-SEC-012"


def test_report_clean_capabilities_score_100():
    """Capabilities with no issues should report 100/100."""
    spec = {"tools": {"safe_tool": {}}}
    report = generate_report(rules_count=5, issues=[], spec=spec)
    cap = next(c for c in report.capability_scores if c.name == "safe_tool")
    assert cap.score == 100
    assert cap.security_score == 30
    assert cap.validation_score == 70
    assert cap.issues == []


def test_report_global_scores_match_sum():
    """Overall score = security_score + validation_score."""
    issues = [
        _issue("OMCP-SEC-005", "$.servers[0].url"),
        _issue("OMCP-DAT-003", "$.tools.t.input", Severity.HIGH),
    ]
    report = generate_report(rules_count=10, issues=issues)
    assert report.score == report.security_score + report.validation_score


def test_report_capability_type_values():
    """capability.type should only be tool/prompt/resource."""
    spec = {
        "tools": {"t": {}},
        "prompts": {"p": {}},
        "resources": {"r": {}},
    }
    report = generate_report(rules_count=5, issues=[], spec=spec)
    for cap in report.capability_scores:
        assert cap.type in {"tool", "prompt", "resource"}
