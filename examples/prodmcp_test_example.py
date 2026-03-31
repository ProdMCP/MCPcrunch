#!/usr/bin/env python3
"""
ProdMCP Test Example — Production-Grade MCP Server
====================================================

This example shows how a fully-constrained OpenMCP spec written with ProdMCP
best practices achieves a perfect 100/100 conformance score (Grade A).

Spec: examples/taskforge_production.json
  - 6 tools, 5 prompts, 4 resources
  - Every input has additionalProperties: false
  - Every string has maxLength
  - Every array has maxItems
  - Every number has minimum/maximum
  - Every tool has security bindings
  - HTTPS transport only
  - All entities have descriptions

Usage:
    python examples/prodmcp_test_example.py
    python examples/prodmcp_test_example.py --validate   # CI mode
"""

import json
import os
import sys

# Ensure we run from the project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcpcrunch import MCPcrunch, ConformanceRunner


SPEC_PATH = "examples/taskforge_production.json"
SCHEMA_PATH = "schema.json"


def run_audit():
    """Run the security audit and display results."""
    with open(SPEC_PATH) as f:
        spec = json.load(f)

    crunch = MCPcrunch(SCHEMA_PATH)
    report = crunch.audit(spec)

    print("=" * 60)
    print("🔍 SECURITY AUDIT")
    print("=" * 60)
    print(f"  Score:  {report.overall_score}/100")
    print(f"  Issues: {len(report.deterministic.issues)}")
    for issue in report.deterministic.issues:
        print(f"    [{issue.severity.value}] {issue.rule_id}: {issue.message}")
    if not report.deterministic.issues:
        print("  ✅ No issues found!")
    print()
    return report.overall_score


def run_conformance():
    """Run conformance tests and display results."""
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
            print(f"     → {r.actual}")
    print()
    return report.summary.score, report.summary.grade


def run_spec_overview():
    """Print a summary of the spec."""
    with open(SPEC_PATH) as f:
        spec = json.load(f)

    print("=" * 60)
    print(f"📋 SPEC: {spec['info']['title']}")
    print("=" * 60)
    print(f"  Version:   {spec['info']['version']}")
    print(f"  OpenMCP:   {spec['openmcp']}")
    print(f"  Server:    {spec['servers'][0]['url']}")
    print(f"  Tools:     {len(spec.get('tools', {}))}")
    print(f"  Prompts:   {len(spec.get('prompts', {}))}")
    print(f"  Resources: {len(spec.get('resources', {}))}")
    print()

    for cat, label in [("tools", "🔧"), ("prompts", "📝"), ("resources", "📦")]:
        for name, entity in spec.get(cat, {}).items():
            sec = "🔒" if entity.get("security") or spec.get("security") else "🔓"
            desc = entity.get("description", "")[:60]
            print(f"  {label} {sec} {name}")
            print(f"       {desc}...")
    print()


def main():
    validate_mode = "--validate" in sys.argv

    run_spec_overview()
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
        if audit_score < 90:
            print(f"  ❌ FAIL: Audit score {audit_score} < 90")
            ok = False
        if conformance_score < 90:
            print(f"  ❌ FAIL: Conformance score {conformance_score} < 90")
            ok = False
        if grade != "A":
            print(f"  ❌ FAIL: Grade {grade} ≠ A")
            ok = False
        if ok:
            print("  ✅ ALL VALIDATION CHECKS PASSED")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
