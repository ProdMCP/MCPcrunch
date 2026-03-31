"""
Conformance Test Suite — Reporter

Rich terminal output and JSON report generation for conformance test results.
"""

import json
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .models import ConformanceReport, ConformanceTestResult, TestStatus


console = Console()

STATUS_ICONS = {
    TestStatus.PASSED: "✅",
    TestStatus.FAILED: "❌",
    TestStatus.SKIPPED: "⏭️",
    TestStatus.ERROR: "💥",
}

STATUS_STYLES = {
    TestStatus.PASSED: "green",
    TestStatus.FAILED: "red",
    TestStatus.SKIPPED: "yellow",
    TestStatus.ERROR: "red bold",
}


def print_report(report: ConformanceReport) -> None:
    """Print a rich terminal report."""
    console.print()
    console.print(Panel.fit(
        "🧪 [bold blue]MCPcrunch Conformance Test Report[/bold blue]",
        border_style="blue",
    ))

    # Summary
    _print_summary(report)

    # Results by category
    _print_results_table(report)

    # Failures detail
    if report.failures:
        _print_failures(report)

    # Footer
    console.print()
    if report.server_url:
        console.print(f"  Server: [cyan]{report.server_url}[/cyan]")
    console.print(f"  Spec Version: [cyan]{report.spec_version}[/cyan]")
    if report.duration_ms:
        console.print(f"  Duration: [cyan]{report.duration_ms:.0f}ms[/cyan]")
    console.print()


# Grade display styles
_GRADE_STYLES = {
    "A": "bold green",
    "B": "bold cyan",
    "C": "bold yellow",
    "D": "bold red",
    "F": "bold red",
}


def _print_summary(report: ConformanceReport) -> None:
    """Print the summary panel."""
    s = report.summary
    pass_rate = s.pass_rate

    # Color based on grade
    grade_style = _GRADE_STYLES.get(s.grade, "bold")
    score_style = grade_style

    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="dim")
    summary_table.add_column("Value", style="bold")
    summary_table.add_row("Score", f"[{score_style}]{s.score}/100[/{score_style}]")
    summary_table.add_row("Grade", f"[{grade_style}]{s.grade}[/{grade_style}]")
    summary_table.add_row("", "")
    summary_table.add_row("Total Tests", str(s.total_tests))
    summary_table.add_row("Passed", f"[green]{s.passed}[/green]")
    summary_table.add_row("Failed", f"[red]{s.failed}[/red]")
    summary_table.add_row("Skipped", f"[yellow]{s.skipped}[/yellow]")
    summary_table.add_row("Errors", f"[red]{s.errors}[/red]")
    summary_table.add_row("Pass Rate", f"{pass_rate}")

    console.print(Panel(summary_table, title="Summary", border_style="dim"))


def _print_results_table(report: ConformanceReport) -> None:
    """Print the results grouped by category."""
    # Group results by category
    categories = {}
    for result in report.results:
        cat = result.category.value
        if cat not in categories:
            categories[cat] = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": 0}
        categories[cat]["total"] += 1
        if result.status == TestStatus.PASSED:
            categories[cat]["passed"] += 1
        elif result.status == TestStatus.FAILED:
            categories[cat]["failed"] += 1
        elif result.status == TestStatus.SKIPPED:
            categories[cat]["skipped"] += 1
        elif result.status == TestStatus.ERROR:
            categories[cat]["errors"] += 1

    cat_table = Table(title="Results by Category")
    cat_table.add_column("Category", style="cyan")
    cat_table.add_column("Total", justify="right")
    cat_table.add_column("✅ Pass", justify="right", style="green")
    cat_table.add_column("❌ Fail", justify="right", style="red")
    cat_table.add_column("⏭️ Skip", justify="right", style="yellow")
    cat_table.add_column("💥 Err", justify="right", style="red")

    for cat, counts in sorted(categories.items()):
        cat_table.add_row(
            cat.replace("_", " ").title(),
            str(counts["total"]),
            str(counts["passed"]),
            str(counts["failed"]),
            str(counts["skipped"]),
            str(counts["errors"]),
        )

    console.print(cat_table)


def _print_failures(report: ConformanceReport) -> None:
    """Print detailed failure information."""
    fail_table = Table(title="Failures & Errors")
    fail_table.add_column("ID", style="magenta", width=10)
    fail_table.add_column("Test", style="white")
    fail_table.add_column("Entity", style="yellow")
    fail_table.add_column("Issue", style="red")

    for result in report.failures:
        icon = STATUS_ICONS.get(result.status, "❓")
        issue = result.actual or result.message or "Unknown issue"
        fail_table.add_row(
            result.test_id,
            f"{icon} {result.test_name}",
            result.entity or "—",
            issue[:80],
        )

    console.print(fail_table)


def export_json(report: ConformanceReport, output_path: Optional[str] = None) -> str:
    """Export the report as JSON. Returns JSON string, optionally writes to file."""
    report_dict = {
        "summary": {
            "total_tests": report.summary.total_tests,
            "passed": report.summary.passed,
            "failed": report.summary.failed,
            "skipped": report.summary.skipped,
            "errors": report.summary.errors,
            "pass_rate": report.summary.pass_rate,
            "score": report.summary.score,
            "grade": report.summary.grade,
        },
        "server_url": report.server_url,
        "spec_version": report.spec_version,
        "timestamp": report.timestamp,
        "duration_ms": report.duration_ms,
        "results": [
            {
                "test_id": r.test_id,
                "test_name": r.test_name,
                "category": r.category.value,
                "entity": r.entity,
                "status": r.status.value,
                "expected": r.expected,
                "actual": r.actual,
                "message": r.message,
                "duration_ms": r.duration_ms,
            }
            for r in report.results
        ],
        "failures": [
            {
                "test_id": r.test_id,
                "type": r.category.value,
                "entity": r.entity,
                "issue": r.actual or r.message,
            }
            for r in report.failures
        ],
    }

    json_str = json.dumps(report_dict, indent=2)

    if output_path:
        with open(output_path, "w") as f:
            f.write(json_str)
        console.print(f"\n[green]Report saved to {output_path}[/green]")

    return json_str
