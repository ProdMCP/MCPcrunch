from mcpcrunch.scoring import calculate_score
from mcpcrunch.models import ValidationIssue, Severity

def test_calculate_score_perfect():
    issues = []
    score = calculate_score(issues)
    assert score == 100

def test_calculate_score_penalties():
    issues = [
        ValidationIssue(rule_id="1", path="$", message="m", severity=Severity.CRITICAL), # -20
        ValidationIssue(rule_id="2", path="$", message="m", severity=Severity.HIGH),     # -10
        ValidationIssue(rule_id="3", path="$", message="m", severity=Severity.MEDIUM),   # -5
        ValidationIssue(rule_id="4", path="$", message="m", severity=Severity.LOW),      # -2
    ]
    # Total penalty: 37
    score = calculate_score(issues)
    assert score == 63

def test_calculate_score_floor():
    issues = [ValidationIssue(rule_id="1", path="$", message="m", severity=Severity.CRITICAL)] * 10
    score = calculate_score(issues)
    assert score == 0
