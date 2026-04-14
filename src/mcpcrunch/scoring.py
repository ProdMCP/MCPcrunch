import re
from typing import List, Dict
from .models import ValidationIssue, CapabilityScore, Severity, ValidationReport

SEVERITY_WEIGHTS = {
    Severity.CRITICAL: 20,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
    Severity.INFO: 0
}


def calculate_score(issues: List[ValidationIssue]) -> tuple[int, int, int]:
    """Calculate overall, security, and data validation scores from issues."""
    security_score = 30
    validation_score = 70

    for issue in issues:
        penalty = SEVERITY_WEIGHTS.get(issue.severity, 0)
        if issue.rule_id.startswith("OMCP-SEC"):
            security_score -= penalty
        else:
            validation_score -= penalty

    security_score = max(0, security_score)
    validation_score = max(0, validation_score)
    total_score = security_score + validation_score
    return total_score, security_score, validation_score


# ---------------------------------------------------------------------------
# Path → endpoint mapping
# ---------------------------------------------------------------------------

# OpenMCP paths:  $.tools.<name>.*, $.prompts.<name>.*, $.resources.<name>.*
_OPENMCP_RE = re.compile(
    r"^\$\.(tools|prompts|resources)\.([^.]+)"
)

# OpenAPI paths:  $.paths['/prompts/summarize_text'].post, $.paths['/resources/{mcp_uri}'].get
_OPENAPI_RE = re.compile(
    r"^\$\.paths\['(/[^']+)'\]"
)

# OpenAPI component schemas:  $.components.schemas.<SchemaName>.*
_COMPONENT_RE = re.compile(
    r"^\$\.components\.schemas\.([^.]+)"
)


def _classify_entity(path: str) -> tuple[str, str] | None:
    """Return (type, endpoint_name) if the path belongs to a specific endpoint."""

    m = _OPENMCP_RE.match(path)
    if m:
        kind = m.group(1).rstrip("s")          # tools→tool, prompts→prompt, resources→resource
        return kind, m.group(2)

    m = _OPENAPI_RE.match(path)
    if m:
        raw = m.group(1)                       # e.g. "/prompts/summarize_text"
        # Derive MCP type from the OpenAPI path prefix and strip it from the name
        if raw.startswith("/prompts/"):
            return "prompt", raw[len("/prompts/"):]
        elif raw.startswith("/tools/"):
            return "tool", raw[len("/tools/"):]
        elif raw.startswith("/resources/"):
            return "resource", raw[len("/resources/"):]
        elif raw.startswith("/resources"):
            return "resource", raw[len("/resources"):] or raw
        return "tool", raw.lstrip("/")

    return None


def _build_capability_scores(
    issues: List[ValidationIssue],
    spec: dict | None = None,
) -> List[CapabilityScore]:
    """Bucket issues by endpoint and compute per-endpoint scores."""

    # Collect all known endpoint names from the spec so we can report clean
    # scores for endpoints that have zero issues too.
    known: Dict[str, str] = {}   # name → type
    if spec:
        for t in spec.get("tools", {}):
            known[t] = "tool"
        for p in spec.get("prompts", {}):
            known[p] = "prompt"
        for r in spec.get("resources", {}):
            known[r] = "resource"
        for path_key in spec.get("paths", {}):
            if path_key.startswith("/prompts/"):
                known[path_key[len("/prompts/"):]] = "prompt"
            elif path_key.startswith("/tools/"):
                known[path_key[len("/tools/"):]] = "tool"
            elif path_key.startswith("/resources/"):
                known[path_key[len("/resources/"):]] = "resource"
            elif path_key.startswith("/resources"):
                known[path_key[len("/resources"):] or path_key] = "resource"
            else:
                known[path_key.lstrip("/")] = "tool"

    # Bucket issues
    buckets: Dict[str, List[ValidationIssue]] = {}
    bucket_types: Dict[str, str] = {}

    for issue in issues:
        ep = _classify_entity(issue.path)
        if ep is None:
            continue
        ep_type, ep_name = ep
        buckets.setdefault(ep_name, []).append(issue)
        bucket_types[ep_name] = ep_type

    # Merge known endpoints (to show perfect-score endpoints too)
    for name, ep_type in known.items():
        if name not in buckets:
            buckets[name] = []
            bucket_types[name] = ep_type

    # Build scores
    scores: List[CapabilityScore] = []
    for name in sorted(buckets):
        ep_issues = buckets[name]
        total, sec, val = calculate_score(ep_issues)
        scores.append(CapabilityScore(
            name=name,
            type=bucket_types.get(name, "unknown"),
            security_score=sec,
            validation_score=val,
            score=total,
            issues=ep_issues,
        ))

    return scores


def generate_report(
    rules_count: int,
    issues: List[ValidationIssue],
    spec: dict | None = None,
) -> ValidationReport:
    score, sec_score, val_score = calculate_score(issues)
    unique_failed_rules = {issue.rule_id for issue in issues}
    passed_rules = max(0, rules_count - len(unique_failed_rules))

    capability_scores = _build_capability_scores(issues, spec)

    return ValidationReport(
        score=score,
        security_score=sec_score,
        validation_score=val_score,
        total_rules=rules_count,
        passed_rules=passed_rules,
        issues=issues,
        capability_scores=capability_scores,
    )
