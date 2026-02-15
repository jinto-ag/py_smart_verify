"""MCP (Model Context Protocol) server for py-verify.

Exposes py-verify functionality as MCP tools and resources for
integration with LLM agents (Claude, etc.).

Usage:
    py-verify-mcp          # Start MCP server (stdio transport)
    py-verify mcp          # Alternate entry point
"""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="py-verify",
    instructions="Python verification tool - linting, type checking, and smart testing",
)


# ─── Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
def verify(
    tasks: list[str] | None = None,
    paths: list[str] | None = None,
    skip_tests: bool = False,
    no_cache: bool = False,
    full_tests: bool = False,
    since: str = "main",
    staged: bool = False,
    continue_on_error: bool = False,
    verbose: bool = False,
) -> str:
    """Run Python verification checks (linting, type checking, testing).

    Returns structured JSON with all step results, issues found, and timing.
    """
    from py_verify.config import RunMode, VerifyConfig
    from py_verify.runner import VerifyRunner

    config = VerifyConfig(
        tasks=tasks or [],
        paths=paths or [],
        skip_tests=skip_tests,
        no_cache=no_cache,
        full_tests=full_tests,
        since=since,
        staged=staged,
        run_mode=RunMode.CONTINUE if continue_on_error else RunMode.FAST_FAIL,
        verbose=verbose,
        json_mode=True,
        project_root=Path.cwd(),
    )

    runner = VerifyRunner(config)
    _exit_code, result = runner.run_and_get_result()
    return result.model_dump_json(indent=2)


@mcp.tool()
def graph(paths: list[str] | None = None) -> str:
    """Build and return the dependency graph for the project.

    Returns JSON with all modules, their imports, and any circular dependencies.
    """
    from py_verify.discovery import PathDiscovery
    from py_verify.graph import DependencyGraphBuilder

    project_root = Path.cwd()
    discovery = PathDiscovery(project_root)
    path_list = paths or []
    resolved_paths = discovery.resolve_paths(path_list)
    py_files = discovery.find_python_files(resolved_paths, scope="quality")

    builder = DependencyGraphBuilder(project_root)
    graph_result = builder.build(py_files)
    return graph_result.model_dump_json(indent=2)


@mcp.tool()
def affected(since: str = "main", staged: bool = False) -> str:
    """List tests affected by code changes (via py-smart-test).

    Returns JSON with affected test modules.
    """
    import subprocess

    cmd = ["py-smart-test-affected", "--json"]
    if since != "main":
        cmd.extend(["--base", since])
    if staged:
        cmd.append("--staged")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stdout:
            return result.stdout
        return json.dumps({"affected": [], "error": None})
    except FileNotFoundError:
        return json.dumps({"error": "py-smart-test-affected not found. Install py-smart-test."})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out"})


@mcp.tool()
def regen_graph() -> str:
    """Regenerate the py-smart-test dependency graph.

    Returns JSON with success/failure status.
    """
    import subprocess

    cmd = ["py-smart-test-graph-gen"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.dumps(
            {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        )
    except FileNotFoundError:
        return json.dumps(
            {
                "success": False,
                "error": "py-smart-test-graph-gen not found. Install py-smart-test.",
            }
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "Command timed out"})


@mcp.tool()
def list_tasks() -> str:
    """List all available verification tasks with their metadata.

    Returns JSON array of task objects with name, category, description, etc.
    """
    from py_verify.config import VerifyConfig
    from py_verify.tasks import task_registry

    tasks_info = []
    for name in sorted(task_registry.all_names()):
        task_class = task_registry.get(name)
        if task_class:
            try:
                config = VerifyConfig()
                instance = task_class(config)
                meta = instance.metadata
                tasks_info.append(
                    {
                        "name": meta.name,
                        "display_name": meta.display_name,
                        "category": meta.category.value,
                        "description": meta.description,
                        "tool_name": meta.tool_name,
                        "aliases": meta.aliases,
                        "cache_scope": meta.cache_scope,
                        "auto_fix": meta.auto_fix,
                        "phase": meta.phase,
                    }
                )
            except Exception:
                pass

    return json.dumps(tasks_info, indent=2)


# ─── Resources ───────────────────────────────────────────────────────────


@mcp.resource("pyverify://last-run")
def last_run_resource() -> str:
    """Last verification run result.

    Reads from .py_verify/last_run.json. Returns the full RunResult
    including all step results, issues, and timing information.
    """
    last_run_path = Path.cwd() / ".py_verify" / "last_run.json"
    if last_run_path.exists():
        return last_run_path.read_text()
    return json.dumps({"error": "No previous run found. Run 'py-verify verify' first."})


@mcp.resource("pyverify://graph")
def graph_resource() -> str:
    """Current dependency graph for the project.

    Builds the graph fresh from the source files and returns it as JSON.
    """
    from py_verify.discovery import PathDiscovery
    from py_verify.graph import DependencyGraphBuilder

    project_root = Path.cwd()
    discovery = PathDiscovery(project_root)
    resolved_paths = discovery.resolve_paths([])
    py_files = discovery.find_python_files(resolved_paths, scope="quality")

    builder = DependencyGraphBuilder(project_root)
    graph_result = builder.build(py_files)
    return graph_result.model_dump_json(indent=2)


@mcp.resource("pyverify://tasks")
def tasks_resource() -> str:
    """Available verification tasks with metadata.

    Returns all registered tasks, their categories, tool requirements, etc.
    """
    result: str = list_tasks()
    return result


@mcp.resource("pyverify://config")
def config_resource() -> str:
    """Current project configuration.

    Shows the default VerifyConfig values and detected project structure.
    """
    from py_verify.config import VerifyConfig
    from py_verify.discovery import PathDiscovery
    from py_verify.venv import VenvManager

    project_root = Path.cwd()
    config = VerifyConfig(project_root=project_root)
    discovery = PathDiscovery(project_root)
    venv_mgr = VenvManager(project_root)

    detected_paths = discovery.resolve_paths([])
    venv = venv_mgr.detect_venv()
    pkg_mgr = venv_mgr.detect_package_manager()

    return json.dumps(
        {
            "config": config.model_dump(mode="json"),
            "detected_paths": [str(p) for p in detected_paths],
            "venv": str(venv) if venv else None,
            "package_manager": pkg_mgr,
            "project_root": str(project_root),
        },
        indent=2,
        default=str,
    )


# ─── Entry point ─────────────────────────────────────────────────────────


def main() -> None:
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
