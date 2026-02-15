"""Tests for py_verify.console."""

from io import StringIO

from rich.console import Console

import py_verify.console
from py_verify.console import (
    get_theme,
    print_banner,
    print_cache_hit,
    print_dependency_graph,
    print_issues_table,
    print_run_summary,
    print_step_result,
    print_step_start,
)
from py_verify.models import (
    DependencyGraph,
    DependencyNode,
    Issue,
    RunResult,
    StepResult,
    StepStatus,
)


def _capture(monkeypatch) -> StringIO:
    """Helper to capture console output."""
    buf = StringIO()
    test_console = Console(file=buf, theme=get_theme(), width=120)
    monkeypatch.setattr(py_verify.console, "console", test_console)
    return buf


class TestPrintBanner:
    def test_prints(self, monkeypatch):
        buf = _capture(monkeypatch)
        print_banner()
        output = buf.getvalue()
        assert "py-verify" in output


class TestPrintStepStart:
    def test_without_description(self, monkeypatch):
        buf = _capture(monkeypatch)
        print_step_start("Ruff")
        output = buf.getvalue()
        assert "Ruff" in output

    def test_with_description(self, monkeypatch):
        buf = _capture(monkeypatch)
        print_step_start("Ruff", "Fast linter")
        output = buf.getvalue()
        assert "Ruff" in output
        assert "Fast linter" in output


class TestPrintStepResult:
    def test_success(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(
            name="Test", status=StepStatus.SUCCESS, start_epoch=0, end_epoch=1.5
        )
        print_step_result(step)
        output = buf.getvalue()
        assert "Test" in output

    def test_failed(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.FAILED)
        print_step_result(step)
        output = buf.getvalue()
        assert "Test" in output

    def test_cached(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.CACHED)
        print_step_result(step)
        output = buf.getvalue()
        assert "Test" in output

    def test_skipped(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.SKIPPED)
        print_step_result(step)
        output = buf.getvalue()
        assert "Test" in output

    def test_unknown_status(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.PENDING)
        print_step_result(step)
        output = buf.getvalue()
        assert "Test" in output

    def test_with_duration(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(
            name="Test", status=StepStatus.SUCCESS, start_epoch=100.0, end_epoch=102.5
        )
        print_step_result(step)
        output = buf.getvalue()
        assert "2.50" in output

    def test_without_duration(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.SUCCESS)
        print_step_result(step)
        output = buf.getvalue()
        assert "Test" in output

    def test_with_issues(self, monkeypatch):
        buf = _capture(monkeypatch)
        issues = [
            Issue(
                file="a.py", line=10, type="error", message="bad", source_task="test"
            ),
            Issue(
                file="b.py", line=20, type="error", message="worse", source_task="test"
            ),
        ]
        step = StepResult(name="Test", status=StepStatus.FAILED, issues=issues)
        print_step_result(step)
        output = buf.getvalue()
        assert "bad" in output
        assert "worse" in output

    def test_with_many_issues(self, monkeypatch):
        buf = _capture(monkeypatch)
        issues = [
            Issue(
                file=f"f{i}.py",
                line=i,
                type="error",
                message=f"msg{i}",
                source_task="test",
            )
            for i in range(5)
        ]
        step = StepResult(name="Test", status=StepStatus.FAILED, issues=issues)
        print_step_result(step)
        output = buf.getvalue()
        assert "more" in output

    def test_no_issues(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.SUCCESS, issues=[])
        print_step_result(step)
        # Should not crash


class TestPrintCacheHit:
    def test_prints(self, monkeypatch):
        buf = _capture(monkeypatch)
        print_cache_hit("quality", 1.5)
        output = buf.getvalue()
        assert "quality" in output
        assert "1.50" in output


class TestPrintIssuesTable:
    def test_empty(self, monkeypatch):
        buf = _capture(monkeypatch)
        print_issues_table([])
        assert buf.getvalue() == ""

    def test_with_issues(self, monkeypatch):
        buf = _capture(monkeypatch)
        issues = [
            Issue(
                file="a.py", line=10, type="error", message="bad", source_task="test"
            ),
        ]
        print_issues_table(issues)
        output = buf.getvalue()
        assert "a.py" in output
        assert "bad" in output

    def test_null_line(self, monkeypatch):
        buf = _capture(monkeypatch)
        issues = [
            Issue(
                file="a.py", line=None, type="error", message="bad", source_task="test"
            ),
        ]
        print_issues_table(issues)
        output = buf.getvalue()
        assert "-" in output


class TestPrintRunSummary:
    def test_success(self, monkeypatch):
        buf = _capture(monkeypatch)
        run = RunResult(
            run_id="r1", started_at=100.0, finished_at=110.0, status=StepStatus.SUCCESS
        )
        print_run_summary(run)
        output = buf.getvalue()
        assert "Run Summary" in output
        assert "10.00" in output

    def test_with_issues(self, monkeypatch):
        buf = _capture(monkeypatch)
        issues = [Issue(file="a.py", type="error", message="bad", source_task="test")]
        step = StepResult(name="Test", status=StepStatus.FAILED, issues=issues)
        run = RunResult(run_id="r1", started_at=100.0, status=StepStatus.FAILED)
        run.add_step(step)
        print_run_summary(run)
        output = buf.getvalue()
        assert "1" in output  # Total issues count

    def test_no_issues(self, monkeypatch):
        buf = _capture(monkeypatch)
        step = StepResult(name="Test", status=StepStatus.SUCCESS)
        run = RunResult(run_id="r1", started_at=100.0, status=StepStatus.SUCCESS)
        run.add_step(step)
        print_run_summary(run)
        # Should not crash


class TestPrintDependencyGraph:
    def test_empty(self, monkeypatch):
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        print_dependency_graph(graph)
        output = buf.getvalue()
        assert "No dependencies" in output

    def test_with_nodes(self, monkeypatch):
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        graph.nodes["a"] = DependencyNode(module="a", file="a.py", imports=["b"])
        graph.nodes["b"] = DependencyNode(module="b", file="b.py")
        print_dependency_graph(graph)
        output = buf.getvalue()
        assert "Dependency Graph" in output

    def test_no_roots(self, monkeypatch):
        """All nodes are imported by something -> fallback to first node."""
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        graph.nodes["a"] = DependencyNode(
            module="a", file="a.py", imports=["b"], imported_by=["b"]
        )
        graph.nodes["b"] = DependencyNode(
            module="b", file="b.py", imports=["a"], imported_by=["a"]
        )
        print_dependency_graph(graph)
        # Should not crash

    def test_with_cycles(self, monkeypatch):
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        graph.nodes["a"] = DependencyNode(module="a", file="a.py")
        graph.cycles = [["a", "b", "a"]]
        print_dependency_graph(graph)
        output = buf.getvalue()
        assert "Circular" in output

    def test_max_depth(self, monkeypatch):
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        graph.nodes["a"] = DependencyNode(module="a", file="a.py", imports=["b"])
        graph.nodes["b"] = DependencyNode(module="b", file="b.py", imports=["c"])
        graph.nodes["c"] = DependencyNode(module="c", file="c.py")
        print_dependency_graph(graph, max_depth=1)
        # Should not crash, depth limits traversal

    def test_many_imports(self, monkeypatch):
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        imports = [f"mod{i}" for i in range(10)]
        graph.nodes["root"] = DependencyNode(
            module="root", file="root.py", imports=imports
        )
        for imp in imports:
            graph.nodes[imp] = DependencyNode(module=imp, file=f"{imp}.py")
        print_dependency_graph(graph)
        output = buf.getvalue()
        assert "more" in output  # Shows "... and N more"

    def test_many_roots(self, monkeypatch):
        buf = _capture(monkeypatch)
        graph = DependencyGraph()
        for i in range(5):
            graph.nodes[f"root{i}"] = DependencyNode(module=f"root{i}", file=f"r{i}.py")
        print_dependency_graph(graph)
        # Shows max 3 roots
