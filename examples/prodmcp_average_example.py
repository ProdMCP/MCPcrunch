#!/usr/bin/env python3
"""
ProdMCP Average Example — Typical MCP Server with Common Issues
================================================================

This example shows how a typical "quick-start" MCP spec fares under
MCPcrunch conformance testing. It deliberately has common issues.

Usage:
    python examples/prodmcp_average_example.py
    python examples/prodmcp_average_example.py --validate
"""

import json
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcpcrunch import MCPcrunch, ConformanceRunner

SPEC_PATH = "examples/notekeeper_average.json"
SCHEMA_PATH = "schema.json"


def run_audit():
    with open(SPEC_PATH) as f:
        spec = json.load(f)
    crunch = MCPcrunch(SCHEMA_PATH)
    report = crunch.audit(spec)
    print("=" * 60)
    print("🔍 SECURITY AUDIT")
    print("=" * 60)
    print(f"  Score:  {report.overall_score}/100")
    print(f"  Issues: {len(report.deterministic.issues)}")
    for issue in report.deterministic.issues[:10]:
        print(f"    [{issue.severity.value:8s}] {issue.rule_id}: {issue.message[:70]}")
    remaining = len(report.deterministic.issues) - 10
    if remaining > 0:
        print(f"    ... and {remaining} more issues")
    print()
    return report.overall_score


def run_conformance():
    runner = ConformanceRunner(spec_path=SPEC_PATH, schema_path=SCHEMA_PATH)
    report = runner.run_static()
    print("=" * 60)
    print("🧪 CONFORMANCE TESTS")
    print("=" * 60)
    print(f"  Score:     {report.summary.score}/100")
    print(f"  Grade:     {report.summary.grade}")
    print(f"  Passed:    {report.summary.passed}/{report.summary.total_tests}")
    print(f"  Pass Rate: {report.summary.pass_rate}")
    print()
    for r in report.results:
        icon = "✅" if r.status.value == "PASSED" else "❌"
        sev_tag = f"[{r.severity.value}]"
        print(f"  {icon} {r.test_id} {sev_tag:10s} {r.test_name}")
        if r.status.value != "PASSED" and r.actual:
            print(f"     → {r.actual[:80]}")
    print()
    return report.summary.score, report.summary.grade


def main():
    validate_mode = "--validate" in sys.argv
    audit_score = run_audit()
    conformance_score, grade = run_conformance()
    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    print(f"  Audit Score:       {audit_score}/100")
    print(f"  Conformance Score: {conformance_score}/100  Grade: {grade}")
    print()
    if validate_mode:
        ok = True
        if conformance_score >= 90:
            print(f"  ⚠️  Score {conformance_score} >= 90 — expected lower")
            ok = False
        if grade == "A":
            print(f"  ⚠️  Grade A — expected lower")
            ok = False
        if ok:
            print(f"  ✅ Average spec correctly scored: {conformance_score}/100 (Grade {grade})")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
