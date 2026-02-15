"""Typer CLI for py-verify."""

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import typer

from py_verify import __app_name__, __version__
from py_verify.config import RunMode, Severity, VerifyConfig
from py_verify.console import console
from py_verify.runner import VerifyRunner

if TYPE_CHECKING:
    pass

# Import for graph command
from py_verify.console import print_dependency_graph
from py_verify.discovery import PathDiscovery
from py_verify.graph import DependencyGraphBuilder

app = typer.Typer(
    help="Professional Python verification tool",
    no_args_is_help=True,
)


@app.command()
def verify(
    tasks: Optional[list[str]] = typer.Argument(
        None, help="Tasks to run (quality, tests, ruff, mypy, etc)"
    ),
    skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip test execution"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable caching"),
    include_tests: bool = typer.Option(
        False, "--include-tests", help="Include test files in checks"
    ),
    ignore_warnings: bool = typer.Option(
        False, "--ignore-warnings", help="Ignore warnings"
    ),
    min_severity: int = typer.Option(
        5, "--min-severity", help="Minimum severity level to report (1-5)"
    ),
    continue_mode: bool = typer.Option(
        False, "--continue", help="Continue after errors (vs fast-fail)"
    ),
    tools: Optional[str] = typer.Option(
        None, "--tools", help="Filter to specific tools (comma-separated)"
    ),
    paths: Optional[str] = typer.Option(
        None, "--paths", help="Paths to verify (comma-separated)"
    ),
    upgrade_deps: bool = typer.Option(
        False, "--upgrade-deps", help="Upgrade tool dependencies"
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    full_tests: bool = typer.Option(
        False, "--full-tests", help="Run all tests with smart prioritization"
    ),
    since: str = typer.Option("main", "--since", help="Git ref for smart test diff"),
    staged: bool = typer.Option(
        False, "--staged", help="Test only staged changes (pre-commit mode)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output JSON to stdout (for AI agents)"
    ),
    version: bool = typer.Option(None, "--version", help="Show version"),
) -> None:
    """Run verification checks on Python code."""
    if version:
        console.print(f"{__app_name__} {__version__}")
        raise typer.Exit(0)

    config = _build_verify_config(
        tasks,
        tools,
        paths,
        skip_tests,
        no_cache,
        include_tests,
        ignore_warnings,
        min_severity,
        continue_mode,
        verbose,
        upgrade_deps,
        full_tests,
        since,
        staged,
        json_mode=json_output,
    )

    runner = VerifyRunner(config)
    exit_code, result = runner.run_and_get_result()

    if json_output:
        sys.stdout.write(result.model_dump_json(indent=2))
        sys.stdout.write("\n")

    raise typer.Exit(code=exit_code)


def _build_verify_config(
    tasks: Optional[list[str]],
    tools: Optional[str],
    paths: Optional[str],
    skip_tests: bool,
    no_cache: bool,
    include_tests: bool,
    ignore_warnings: bool,
    min_severity: int,
    continue_mode: bool,
    verbose: bool,
    upgrade_deps: bool,
    full_tests: bool,
    since: str,
    staged: bool,
    json_mode: bool = False,
) -> VerifyConfig:
    """Build VerifyConfig from CLI arguments.

    Args:
        tasks: List of task names to run.
        tools: Comma-separated tools to filter.
        paths: Comma-separated paths to verify.
        skip_tests: Whether to skip tests.
        no_cache: Whether to disable caching.
        include_tests: Whether to include test files.
        ignore_warnings: Whether to ignore warnings.
        min_severity: Minimum severity level.
        continue_mode: Whether to continue on errors.
        verbose: Whether to show verbose output.
        upgrade_deps: Whether to upgrade dependencies.
        full_tests: Whether to run all tests.
        since: Git ref for comparison.
        staged: Whether to use staged changes only.
        json_mode: Whether to output JSON to stdout.

    Returns:
        Configured VerifyConfig instance.
    """
    return VerifyConfig(
        tasks=list(tasks) if tasks else [],
        tools_filter=[t.strip() for t in tools.split(",")] if tools else [],
        paths=[p.strip() for p in paths.split(",")] if paths else [],
        skip_tests=skip_tests,
        no_cache=no_cache,
        include_tests=include_tests,
        ignore_warnings=ignore_warnings,
        min_severity=Severity(min_severity),
        run_mode=RunMode.CONTINUE if continue_mode else RunMode.FAST_FAIL,
        verbose=verbose,
        json_mode=json_mode,
        upgrade_deps=upgrade_deps,
        full_tests=full_tests,
        since=since,
        staged=staged,
        project_root=Path.cwd(),
    )


@app.command()
def graph(
    output: Optional[Path] = typer.Option(
        None, "--output", help="Output file for graph JSON"
    ),
    paths: Optional[str] = typer.Option(
        None, "--paths", help="Paths to analyze (comma-separated)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output JSON to stdout (for AI agents)"
    ),
) -> None:
    """Build and display dependency graph."""
    project_root = Path.cwd()
    discovery = PathDiscovery(project_root)

    # Resolve paths
    path_list = [p.strip() for p in paths.split(",")] if paths else []
    resolved_paths = discovery.resolve_paths(path_list)
    py_files = discovery.find_python_files(resolved_paths, scope="quality")

    # Build graph
    builder = DependencyGraphBuilder(project_root)
    graph_result = builder.build(py_files)

    if json_output:
        sys.stdout.write(graph_result.model_dump_json(indent=2))
        sys.stdout.write("\n")
    else:
        # Display graph
        print_dependency_graph(graph_result)

        # Save to file if requested
        if output:
            builder.to_json(output)
            console.print(f"Graph saved to {output}")


@app.command()
def affected(
    since: str = typer.Option("main", "--since", help="Git ref for diff"),
    staged: bool = typer.Option(False, "--staged", help="Only staged changes"),
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List tests affected by code changes (via py-smart-test)."""
    # Delegate to py-smart-test-affected (alias: pst-affected)
    cmd = ["py-smart-test-affected"]

    if json:
        cmd.append("--json")

    if since != "main":
        cmd.extend(["--base", since])

    if staged:
        cmd.append("--staged")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            console.print(result.stdout)
        if result.returncode != 0:
            console.print("[red]Error: pst-affected failed[/red]")
            raise typer.Exit(1)
    except FileNotFoundError:
        console.print(
            "[red]py-smart-test-affected not found. Install py-smart-test.[/red]"
        )
        raise typer.Exit(1)


@app.command()
def regen_graph() -> None:
    """Regenerate py-smart-test dependency graph."""
    # Delegate to py-smart-test-graph-gen (alias: pst-gen)
    cmd = ["py-smart-test-graph-gen"]

    try:
        result = subprocess.run(cmd)
        if result.returncode != 0:
            console.print("[red]Failed to regenerate graph[/red]")
            raise typer.Exit(1)
        else:
            console.print("[green]Dependency graph regenerated[/green]")
    except FileNotFoundError:
        console.print(
            "[red]py-smart-test-graph-gen not found. Install py-smart-test.[/red]"
        )
        raise typer.Exit(1)


@app.command()
def mcp() -> None:
    """Start the MCP (Model Context Protocol) server for AI agent integration."""
    try:
        from py_verify.mcp_server import main as mcp_main

        mcp_main()
    except ImportError:
        console.print(
            "[red]MCP dependencies not installed. "
            "Install with: pip install 'py-verify\\[mcp]'[/red]"
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
