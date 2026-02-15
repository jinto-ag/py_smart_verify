"""Rich console output for py-verify."""

from rich.console import Console
from rich.table import Table
from rich.theme import Theme
from rich.tree import Tree

from py_verify.models import DependencyGraph, Issue, RunResult, StepResult, StepStatus


def get_theme() -> Theme:
    """Build and return the py-verify Rich theme."""
    return Theme(
        {
            "success": "bold green",
            "error": "bold red",
            "warning": "bold yellow",
            "info": "cyan",
            "cached": "dim cyan",
            "critical": "bold red",
            "note": "yellow",
        }
    )


# Create console instances
console = Console(theme=get_theme())
err_console = Console(stderr=True, theme=get_theme())


def print_banner() -> None:
    """Print py-verify banner."""
    console.print(
        "[bold cyan]py-verify[/bold cyan] - Professional Python Verification Tool",
        justify="center",
    )
    console.print()


def print_step_start(name: str, description: str = "") -> None:
    """Print at the start of a step."""
    if description:
        console.print(f"▶️  [bold]{name}[/bold] - {description}")
    else:
        console.print(f"▶️  [bold]{name}[/bold]")


def print_step_result(step: StepResult) -> None:
    """Print the result of a step."""
    icon = {
        StepStatus.SUCCESS: "✓",
        StepStatus.FAILED: "✗",
        StepStatus.CACHED: "⚡",
        StepStatus.SKIPPED: "⊘",
    }.get(step.status, "?")

    style = {
        StepStatus.SUCCESS: "success",
        StepStatus.FAILED: "error",
        StepStatus.CACHED: "cached",
        StepStatus.SKIPPED: "warning",
    }.get(step.status, "info")

    duration_str = f" ({step.duration:.2f}s)" if step.duration > 0 else ""
    console.print(f"  {icon} [bold {style}]{step.name}[/bold {style}]{duration_str}")

    if step.issues:
        for issue in step.issues[:3]:  # Show first 3 issues
            console.print(f"    ⚠️  {issue.message} ({issue.file}:{issue.line})")
        if len(step.issues) > 3:
            console.print(f"    ... and {len(step.issues) - 3} more issues")


def print_cache_hit(scope: str, duration: float) -> None:
    """Print when cache is hit."""
    console.print(f"⚡ [cached]Cache hit for {scope}[/cached] ({duration:.2f}s)")


def print_issues_table(issues: list[Issue]) -> None:
    """Print issues in a Rich table."""
    if not issues:
        return

    table = Table(title="Issues Found", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right", style="magenta")
    table.add_column("Type", style="yellow")
    table.add_column("Message")

    for issue in sorted(issues, key=lambda x: (x.file, x.line or 0)):
        line_str = str(issue.line) if issue.line else "-"
        table.add_row(issue.file, line_str, issue.type, issue.message)

    console.print(table)


def print_run_summary(result: RunResult) -> None:
    """Print summary of a complete run."""
    console.print()
    console.print("[bold]=" * 50)
    console.print("[bold]Run Summary[/bold]")
    console.print(
        f"Status: [bold {result.status.value}]"
        f"{result.status.value}[/bold {result.status.value}]"
    )
    console.print(f"Duration: {result.duration:.2f}s")
    console.print(f"Steps completed: {len(result.steps)}")

    # Count issues by severity
    all_issues = [issue for step in result.steps for issue in step.issues]
    if all_issues:
        console.print(f"Total issues: {len(all_issues)}")

    # Show step results
    console.print()
    console.print("[bold]Step Results:[/bold]")
    for step in result.steps:
        print_step_result(step)

    console.print("[bold]=" * 50)
    console.print()


def print_dependency_graph(graph: DependencyGraph, max_depth: int = 3) -> None:
    """Print dependency graph as Rich tree."""
    if not graph.nodes:
        console.print("No dependencies found")
        return

    # Find root nodes (not imported by anything in the graph)
    all_imported = set()
    for node in graph.nodes.values():
        all_imported.update(node.imported_by)

    roots = [name for name in graph.nodes.keys() if name not in all_imported]

    if not roots:
        roots = list(graph.nodes.keys())[:1]

    tree = Tree(f"[bold blue]Dependency Graph[/bold blue] ({len(graph.nodes)} modules)")

    def add_node(parent_tree: Tree, module: str, depth: int = 0) -> None:
        """Recursively add nodes to tree."""
        if depth > max_depth:
            return

        node = graph.nodes.get(module)
        if not node:
            return

        for imported in node.imports[:5]:  # Show max 5 imports
            child = parent_tree.add(f"[cyan]{imported}[/cyan]")
            add_node(child, imported, depth + 1)

        if len(node.imports) > 5:
            parent_tree.add(f"[dim]... and {len(node.imports) - 5} more[/dim]")

    for root in roots[:3]:  # Show max 3 roots
        root_branch = tree.add(f"[bold green]{root}[/bold green]")
        add_node(root_branch, root)

    console.print(tree)

    # Show cycles if any
    if graph.cycles:
        console.print("[bold yellow]Circular Dependencies Found:[/bold yellow]")
        for cycle in graph.cycles:
            console.print(f"  [red]→ {' → '.join(cycle)}[/red]")
