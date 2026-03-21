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
    summary_table.add_column("Score", style="bold")
    summary_table.add_column("IssuesFound", style="red")
    
    summary_table.add_row("Deterministic (FMT, DAT, SEC)", str(report.deterministic.score), str(len(report.deterministic.issues)))
    if llm:
        summary_table.add_row("Semantic (ADV)", str(report.semantic.score), str(len(report.semantic.issues)))
    
    console.print(summary_table)
    console.print(f"\n[bold]Overall Security Score: {report.overall_score}/100[/bold]\n")

    # Display Issues
    issues = report.deterministic.issues + report.semantic.issues
    if issues:
        issues_table = Table(title="Security & Structural Issues")
        issues_table.add_column("Rule ID", style="magenta")
        issues_table.add_column("Severity", style="bold")
        issues_table.add_column("Path", style="yellow")
        issues_table.add_column("Message")
        
        for issue in issues:
            severity_style = "red" if issue.severity in ["Critical", "High"] else "yellow"
            issues_table.add_row(
                issue.rule_id,
                f"[{severity_style}]{issue.severity}[/{severity_style}]",
                issue.path,
                issue.message
            )
        console.print(issues_table)
    else:
        console.print("[bold green]No issues found! Your OpenMCP spec is secure and robust.[/bold green]")

if __name__ == "__main__":
    main()
