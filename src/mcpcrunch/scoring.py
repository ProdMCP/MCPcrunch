from typing import List
from .models import ValidationIssue, Severity, ValidationReport

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 20,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
    Severity.INFO: 0
}

def calculate_score(issues: List[ValidationIssue]) -> int:
    score = 100
    for issue in issues:
        score -= SEVERITY_WEIGHTS.get(issue.severity, 0)
    return max(0, score)

def generate_report(rules_count: int, issues: List[ValidationIssue]) -> ValidationReport:
    score = calculate_score(issues)
    # This is a simplified calculation for passed rules
    # In a real scenario, we'd track which specific rules failed
    unique_failed_rules = {issue.rule_id for issue in issues}
    passed_rules = max(0, rules_count - len(unique_failed_rules))
    
    return ValidationReport(
        score=score,
        total_rules=rules_count,
        passed_rules=passed_rules,
        issues=issues
    )
