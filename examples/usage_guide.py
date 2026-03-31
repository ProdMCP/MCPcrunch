#!/usr/bin/env python3
"""
MCPcrunch Usage Examples — Complete Guide
==========================================

This file demonstrates every way to use MCPcrunch for security auditing
and conformance testing of OpenMCP specifications.

Spec used: examples/taskforge_production.json
 - 6 tools, 5 prompts, 4 resources
 - 100/100 security audit score
 - 100% conformance pass rate
"""

# ╔══════════════════════════════════════════════════════╗
# ║  1. SECURITY AUDIT — Python API                     ║
# ╚══════════════════════════════════════════════════════╝

import json
from mcpcrunch import MCPcrunch, FullReport


def example_1_basic_audit():
    """Run a security audit and print the results."""
    # Load the OpenMCP spec
    with open("examples/taskforge_production.json") as f:
        spec = json.load(f)

    # Initialize the engine with the OpenMCP JSON Schema
    crunch = MCPcrunch("schema.json")

    # Run the audit
    report: FullReport = crunch.audit(spec)

    # Inspect results
    print(f"Overall Score:       {report.overall_score}/100")
    print(f"Deterministic Score: {report.deterministic.score}/100")
    print(f"Issues Found:        {len(report.deterministic.issues)}")

    # Iterate over issues (if any)
    for issue in report.deterministic.issues:
        print(f"  [{issue.severity}] {issue.rule_id}: {issue.message}")
        print(f"    Path: {issue.path}")


def example_2_audit_with_assertions():
    """Use audit results in CI/CD to gate deployments."""
    with open("examples/taskforge_production.json") as f:
        spec = json.load(f)

    crunch = MCPcrunch("schema.json")
    report = crunch.audit(spec)

    # CI gate: fail if score below 90
    assert report.overall_score >= 90, f"Security score {report.overall_score} is below threshold"

    # CI gate: fail if any CRITICAL issues
    critical_issues = [i for i in report.deterministic.issues if i.severity.value == "Critical"]
    assert len(critical_issues) == 0, f"Found {len(critical_issues)} critical issues"

    print("✅ All CI gates passed!")


# ╔══════════════════════════════════════════════════════╗
# ║  2. CONFORMANCE TESTING — Python API                 ║
# ╚══════════════════════════════════════════════════════╝

from mcpcrunch import ConformanceRunner, ConformanceReport, AuthConfig, TestCategory, TestStatus


def example_3_static_conformance():
    """Run static spec integrity tests (no server needed)."""
    runner = ConformanceRunner(
        spec_path="examples/taskforge_production.json",
        schema_path="schema.json",
    )

    report: ConformanceReport = runner.run_static()

    print(f"\n{'='*50}")
    print(f"Static Conformance Results")
    print(f"{'='*50}")
    print(f"  Total Tests: {report.summary.total_tests}")
    print(f"  Passed:      {report.summary.passed}")
    print(f"  Failed:      {report.summary.failed}")
    print(f"  Pass Rate:   {report.summary.pass_rate}")

    # Show each test result
    for r in report.results:
        icon = "✅" if r.status == TestStatus.PASSED else "❌"
        print(f"  {icon} {r.test_id} — {r.test_name}")
        if r.actual:
            print(f"      → {r.actual}")


def example_4_full_conformance_with_server():
    """
    Run the full conformance suite against a live MCP server.

    NOTE: This requires a running MCP server. Uncomment to use.
    """
    # Set up auth credentials
    auth = AuthConfig(
        bearer_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",  # Your JWT here
    )

    runner = ConformanceRunner(
        spec_path="examples/taskforge_production.json",
        server_url="https://api.taskforge.prodmcp.dev/mcp",
        schema_path="schema.json",
        auth=auth,
        timeout=15.0,  # 15-second timeout per request
    )

    # Run everything: static + runtime
    report = runner.run_all()

    print(f"\nFull Conformance: {report.summary.pass_rate}")
    print(f"  Passed: {report.summary.passed}/{report.summary.total_tests}")

    if report.failures:
        print(f"\n  Failures:")
        for f in report.failures:
            print(f"    ❌ {f.test_id} [{f.entity or 'global'}]: {f.actual or f.message}")


def example_5_single_category():
    """Run conformance tests for a specific category only."""
    runner = ConformanceRunner(
        spec_path="examples/taskforge_production.json",
        schema_path="schema.json",
    )

    # Static category — no server needed
    report = runner.run_category(TestCategory.SPEC_INTEGRITY)

    print(f"\nSpec Integrity: {report.summary.pass_rate}")
    for r in report.results:
        print(f"  {r.test_id}: {r.status.value}")


def example_6_json_report_export():
    """Export conformance results as JSON for CI pipelines."""
    runner = ConformanceRunner(
        spec_path="examples/taskforge_production.json",
        schema_path="schema.json",
    )
    report = runner.run_static()

    # Export as JSON string
    from mcpcrunch.conformance.reporter import export_json

    json_str = export_json(report)
    data = json.loads(json_str)

    print(f"\nJSON Report Fields: {list(data.keys())}")
    print(f"  Total Tests: {data['summary']['total_tests']}")
    print(f"  Pass Rate:   {data['summary']['pass_rate']}")

    # Write to file
    export_json(report, "conformance_report.json")
    print(f"  → Saved to conformance_report.json")


def example_7_rich_terminal_report():
    """Display the beautiful Rich terminal report."""
    from mcpcrunch.conformance.reporter import print_report

    runner = ConformanceRunner(
        spec_path="examples/taskforge_production.json",
        schema_path="schema.json",
    )
    report = runner.run_static()
    print_report(report)


# ╔══════════════════════════════════════════════════════╗
# ║  3. SCHEMA MUTATOR — Direct Usage                   ║
# ╚══════════════════════════════════════════════════════╝

from mcpcrunch.conformance.schema_mutator import (
    generate_valid_input,
    generate_missing_required,
    generate_type_violations,
    generate_constraint_violations,
    generate_extra_properties,
)


def example_8_schema_mutator():
    """Use the mutation engine directly for custom testing."""
    # Load the spec and extract a tool's input schema
    with open("examples/taskforge_production.json") as f:
        spec = json.load(f)

    create_task_input = spec["tools"]["create_task"]["input"]

    # Generate a valid input
    valid = generate_valid_input(create_task_input)
    print(f"\n{'='*50}")
    print(f"Schema Mutator Examples (create_task)")
    print(f"{'='*50}")
    print(f"\n1. Valid Input:")
    print(f"   {json.dumps(valid, indent=2)[:200]}...")

    # Generate missing-required mutations
    print(f"\n2. Missing Required Field Mutations:")
    for field_name, mutated_input in generate_missing_required(create_task_input):
        print(f"   Missing '{field_name}': keys = {list(mutated_input.keys())}")

    # Generate type violations
    print(f"\n3. Type Violation Mutations:")
    for prop, orig_type, wrong_val, _ in generate_type_violations(create_task_input):
        print(f"   {prop}: {orig_type} → {type(wrong_val).__name__} ({wrong_val})")

    # Generate constraint violations
    print(f"\n4. Constraint Violation Mutations:")
    for prop, constraint, wrong_val, _ in generate_constraint_violations(create_task_input):
        display_val = str(wrong_val)[:50]
        print(f"   {prop}.{constraint}: {display_val}")

    # Generate extra properties (additionalProperties test)
    extra = generate_extra_properties(create_task_input)
    injected = [k for k in extra if k.startswith("__")]
    print(f"\n5. Extra Properties Injection:")
    print(f"   Injected fields: {injected}")


# ╔══════════════════════════════════════════════════════╗
# ║  4. COMBINED WORKFLOW — Audit + Conformance          ║
# ╚══════════════════════════════════════════════════════╝

def example_9_full_validation_pipeline():
    """
    Complete validation pipeline: audit → conformance → report.
    This is the recommended pattern for CI/CD integration.
    """
    spec_path = "examples/taskforge_production.json"
    schema_path = "schema.json"
    MIN_AUDIT_SCORE = 90
    MAX_CONFORMANCE_FAILURES = 0

    print(f"\n{'='*50}")
    print(f"Full Validation Pipeline")
    print(f"{'='*50}")

    # Step 1: Security Audit
    with open(spec_path) as f:
        spec = json.load(f)
    crunch = MCPcrunch(schema_path)
    audit_report = crunch.audit(spec)
    print(f"\n  🔍 Audit Score: {audit_report.overall_score}/100")

    if audit_report.overall_score < MIN_AUDIT_SCORE:
        print(f"  ❌ FAILED — Below {MIN_AUDIT_SCORE} threshold")
        return False

    # Step 2: Conformance Testing
    runner = ConformanceRunner(spec_path=spec_path, schema_path=schema_path)
    conf_report = runner.run_static()
    print(f"  🧪 Conformance: {conf_report.summary.pass_rate} ({conf_report.summary.passed}/{conf_report.summary.total_tests})")

    if conf_report.summary.failed > MAX_CONFORMANCE_FAILURES:
        print(f"  ❌ FAILED — {conf_report.summary.failed} conformance failures")
        return False

    # Step 3: Export Report
    from mcpcrunch.conformance.reporter import export_json
    export_json(conf_report, "pipeline_report.json")

    print(f"  ✅ ALL CHECKS PASSED")
    print(f"  → Report saved to pipeline_report.json")
    return True


# ╔══════════════════════════════════════════════════════╗
# ║  5. SPEC INSPECTION UTILITIES                        ║
# ╚══════════════════════════════════════════════════════╝

def example_10_spec_overview():
    """Print a summary of what's in the spec."""
    with open("examples/taskforge_production.json") as f:
        spec = json.load(f)

    print(f"\n{'='*50}")
    print(f"Spec Overview: {spec['info']['title']}")
    print(f"{'='*50}")
    print(f"  Version:    {spec['info']['version']}")
    print(f"  OpenMCP:    {spec['openmcp']}")
    print(f"  Server:     {spec['servers'][0]['url']}")
    print(f"  Tools:      {len(spec.get('tools', {}))}")
    print(f"  Prompts:    {len(spec.get('prompts', {}))}")
    print(f"  Resources:  {len(spec.get('resources', {}))}")

    print(f"\n  Tools:")
    for name, tool in spec.get('tools', {}).items():
        req = tool['input'].get('required', [])
        sec = '🔒' if tool.get('security') else '🔓'
        print(f"    {sec} {name} — {len(req)} required params")

    print(f"\n  Prompts:")
    for name, prompt in spec.get('prompts', {}).items():
        req = prompt['input'].get('required', [])
        print(f"    📝 {name} — {len(req)} required params")

    print(f"\n  Resources:")
    for name in spec.get('resources', {}):
        print(f"    📦 {name}")


# ╔══════════════════════════════════════════════════════╗
# ║  RUN ALL EXAMPLES                                   ║
# ╚══════════════════════════════════════════════════════╝

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    example_1_basic_audit()
    example_2_audit_with_assertions()
    example_3_static_conformance()
    # example_4_full_conformance_with_server()  # Requires live server
    example_5_single_category()
    example_6_json_report_export()
    # example_7_rich_terminal_report()  # Prints full Rich table
    example_8_schema_mutator()
    example_9_full_validation_pipeline()
    example_10_spec_overview()

    print(f"\n{'='*50}")
    print(f"All examples completed successfully! ✅")
    print(f"{'='*50}")
