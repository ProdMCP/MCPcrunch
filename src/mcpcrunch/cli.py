import argparse
import json
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .engine import MCPcrunch
from .llm.gemini import GeminiProvider
from .llm.openai import OpenAIProvider

console = Console()


def main():
    # Check if the first arg is "conformance" — route accordingly
    if len(sys.argv) > 1 and sys.argv[1] == "conformance":
        _main_conformance()
    else:
        _main_audit()


def _main_audit():
    """Original audit command (backward compatible)."""
    parser = argparse.ArgumentParser(description="MCPcrunch: OpenMCP Security & Structural Validator")
    parser.add_argument("spec", help="Path to OpenMCP JSON/YAML specification")
    parser.add_argument("--schema", help="Path to OpenMCP JSON Schema", default="schema.json")
    parser.add_argument("--llm", choices=["gemini", "openai"], help="LLM provider for semantic validation")
    parser.add_argument("--api-key", help="API key for LLM provider")

    args = parser.parse_args()

    if not os.path.exists(args.spec):
        console.print(f"[red]Error: Spec file not found at {args.spec}[/red]")
        sys.exit(1)

    if not os.path.exists(args.schema):
        console.print(f"[yellow]Warning: Schema file not found at {args.schema}. Using default schema if available.[/yellow]")

    # Load spec
    with open(args.spec, 'r') as f:
        spec_data = json.load(f)

    # Setup LLM if requested
    llm = None
    if args.llm == "gemini":
        llm = GeminiProvider(api_key=args.api_key)
    elif args.llm == "openai":
        llm = OpenAIProvider(api_key=args.api_key)

    # Initialize Engine
    crunch = MCPcrunch(args.schema, llm=llm)

    console.print(Panel.fit("🔍 [bold blue]MCPcrunch Security Audit[/bold blue]", border_style="blue"))

    with console.status("[bold green]Analyzing OpenMCP specification..."):
        report = crunch.audit(spec_data)

    # Display Summary
    summary_table = Table(title="Audit Summary")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Sec (/30)", justify="right", style="bold red")
    summary_table.add_column("Dat (/70)", justify="right", style="bold yellow")
    summary_table.add_column("Overall (/100)", justify="right", style="bold green")
    summary_table.add_column("Issues", justify="right", style="red")

    summary_table.add_row(
        "Deterministic (FMT, DAT, SEC)", 
        str(report.deterministic.security_score), 
        str(report.deterministic.validation_score),
        str(report.deterministic.score),
        str(len(report.deterministic.issues))
    )
    if llm:
        summary_table.add_row(
            "Semantic (ADV)", 
            str(report.semantic.security_score), 
            str(report.semantic.validation_score),
            str(report.semantic.score),
            str(len(report.semantic.issues))
        )

    console.print(summary_table)
    console.print(f"\n[bold]Global score:[/bold] {report.overall_score}/100")
    console.print(f"[bold]Security score:[/bold] {report.deterministic.security_score}/30")
    console.print(f"[bold]Data validation score:[/bold] {report.deterministic.validation_score}/70\n")

    # Display Per-Entity Scores
    ep_scores = report.deterministic.capability_scores
    if ep_scores:
        ep_table = Table(title="Tool / Resource / Prompt Scores")
        ep_table.add_column("Name", style="cyan", no_wrap=True)
        ep_table.add_column("Type", style="dim")
        ep_table.add_column("Sec (/30)", justify="right", style="bold red")
        ep_table.add_column("Dat (/70)", justify="right", style="bold yellow")
        ep_table.add_column("Score (/100)", justify="right", style="bold green")
        ep_table.add_column("Issues", justify="right", style="red")

        for ep in ep_scores:
            score_style = "green" if ep.score == 100 else ("yellow" if ep.score >= 70 else "red")
            ep_table.add_row(
                ep.name,
                ep.type,
                str(ep.security_score),
                str(ep.validation_score),
                f"[{score_style}]{ep.score}[/{score_style}]",
                str(len(ep.issues)),
            )
        console.print(ep_table)
        console.print()

    # Display Issues grouped by entity
    ep_scores_with_issues = [ep for ep in ep_scores if ep.issues] if ep_scores else []
    # Collect global issues (not tied to any entity)
    all_ep_issue_paths = set()
    for ep in (ep_scores or []):
        for issue in ep.issues:
            all_ep_issue_paths.add(id(issue))
    
    all_issues = report.deterministic.issues + report.semantic.issues
    global_issues = [i for i in all_issues if id(i) not in all_ep_issue_paths]

    if ep_scores_with_issues or global_issues:
        if global_issues:
            global_table = Table(title="Global Issues")
            global_table.add_column("Rule ID", style="magenta")
            global_table.add_column("Severity", style="bold")
            global_table.add_column("Path", style="yellow")
            global_table.add_column("Message")
            for issue in global_issues:
                severity_style = "red" if issue.severity in ["Critical", "High"] else "yellow"
                global_table.add_row(
                    issue.rule_id,
                    f"[{severity_style}]{issue.severity}[/{severity_style}]",
                    issue.path,
                    issue.message,
                )
            console.print(global_table)
            console.print()

        for ep in ep_scores_with_issues:
            score_color = "green" if ep.score == 100 else ("yellow" if ep.score >= 70 else "red")
            console.print(
                f"[bold cyan]{ep.name}[/bold cyan] "
                f"[dim]({ep.type})[/dim]  "
                f"Sec: [bold red]{ep.security_score}/30[/bold red]  "
                f"Dat: [bold yellow]{ep.validation_score}/70[/bold yellow]  "
                f"Score: [{score_color}]{ep.score}/100[/{score_color}]"
            )
            issue_table = Table(show_header=True, box=None, padding=(0, 1))
            issue_table.add_column("Rule ID", style="magenta")
            issue_table.add_column("Severity", style="bold")
            issue_table.add_column("Message")
            for issue in ep.issues:
                severity_style = "red" if issue.severity in ["Critical", "High"] else "yellow"
                issue_table.add_row(
                    issue.rule_id,
                    f"[{severity_style}]{issue.severity}[/{severity_style}]",
                    issue.message,
                )
            console.print(issue_table)
            console.print()
    else:
        console.print("[bold green]No issues found! Your OpenMCP spec is secure and robust.[/bold green]")


def _main_conformance():
    """Conformance test subcommand."""
    parser = argparse.ArgumentParser(
        prog="mcpcrunch conformance",
        description="MCP Conformance Test Suite — validates runtime behavior against spec",
    )
    parser.add_argument("_cmd", help=argparse.SUPPRESS)  # consumes "conformance"
    parser.add_argument("spec", help="Path to OpenMCP JSON specification")
    parser.add_argument("--schema", help="Path to OpenMCP JSON Schema", default="schema.json")
    parser.add_argument("--server-url", help="URL of the MCP server to test against")
    parser.add_argument("--static-only", action="store_true",
                        help="Run only static spec integrity tests (no server needed)")
    parser.add_argument("--category", help="Run only a specific test category",
                        choices=["schema_input", "schema_output", "tool_contract", "prompt_contract",
                                 "resource_contract", "security", "server_contract", "spec_integrity",
                                 "error_handling", "determinism"])
    parser.add_argument("--bearer-token", help="Bearer token for authentication")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--api-key-header", help="Header name for API key", default="Authorization")
    parser.add_argument("--api-key-in", choices=["header", "query", "cookie"], default="header",
                        help="Where to send the API key")
    parser.add_argument("--output", help="Path to save JSON report")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds")

    args = parser.parse_args()

    from .conformance.runner import ConformanceRunner
    from .conformance.models import AuthConfig, TestCategory
    from .conformance import reporter

    if not os.path.exists(args.spec):
        console.print(f"[red]Error: Spec file not found at {args.spec}[/red]")
        sys.exit(1)

    if not args.static_only and not args.server_url and args.category != "spec_integrity":
        console.print("[red]Error: --server-url is required for runtime tests. Use --static-only for static tests only.[/red]")
        sys.exit(1)

    # Build auth config
    auth = AuthConfig(
        bearer_token=args.bearer_token,
        api_key=args.api_key,
        api_key_header_name=args.api_key_header,
        api_key_in=args.api_key_in,
    )

    # Initialize runner
    runner = ConformanceRunner(
        spec_path=args.spec,
        server_url=args.server_url,
        schema_path=args.schema,
        auth=auth,
        timeout=args.timeout,
    )

    console.print(Panel.fit(
        "🧪 [bold blue]MCPcrunch Conformance Test Suite[/bold blue]",
        border_style="blue",
    ))

    # Execute tests
    with console.status("[bold green]Running conformance tests..."):
        if args.static_only or args.category == "spec_integrity":
            report = runner.run_static()
        elif args.category:
            category = TestCategory(args.category)
            report = runner.run_category(category)
        else:
            report = runner.run_all()

    # Display results
    reporter.print_report(report)

    # Save JSON if requested
    if args.output:
        reporter.export_json(report, args.output)

    # Exit code
    if report.summary.failed > 0 or report.summary.errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
