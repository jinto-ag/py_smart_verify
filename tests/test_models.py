"""Tests for py_verify.models."""

import json
from pathlib import Path

from py_verify.models import (
    DependencyGraph,
    DependencyNode,
    Issue,
    RunResult,
    StepResult,
    StepStatus,
)


# --- StepStatus ---


class TestStepStatus:
    def test_values(self):
        assert StepStatus.PENDING == "pending"
        assert StepStatus.RUNNING == "running"
        assert StepStatus.SUCCESS == "success"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.CACHED == "cached"
        assert StepStatus.SKIPPED == "skipped"

    def test_is_str(self):
        assert isinstance(StepStatus.SUCCESS, str)


# --- Issue ---


class TestIssue:
    def test_minimal(self):
        issue = Issue(file="a.py", type="error", message="bad", source_task="ruff")
        assert issue.file == "a.py"
        assert issue.line is None
        assert issue.col is None
        assert issue.severity == 5
        assert issue.action is None

    def test_all_fields(self):
        issue = Issue(
            file="b.py",
            line=10,
            col=5,
            type="warning",
            severity=2,
            message="warn",
            action="fix it",
            source_task="mypy",
        )
        assert issue.line == 10
        assert issue.col == 5
        assert issue.severity == 2
        assert issue.action == "fix it"


# --- StepResult ---


class TestStepResult:
    def test_duration_both_epochs(self):
        r = StepResult(
            name="t",
            status=StepStatus.SUCCESS,
            start_epoch=100.0,
            end_epoch=105.5,
        )
        assert r.duration == 5.5

    def test_duration_no_epochs(self):
        r = StepResult(name="t", status=StepStatus.SUCCESS)
        assert r.duration == 0.0

    def test_duration_only_start(self):
        r = StepResult(name="t", status=StepStatus.SUCCESS, start_epoch=100.0)
        assert r.duration == 0.0

    def test_is_success_true(self):
        assert StepResult(name="t", status=StepStatus.SUCCESS).is_success()

    def test_is_success_cached(self):
        assert StepResult(name="t", status=StepStatus.CACHED).is_success()

    def test_is_success_failed(self):
        assert not StepResult(name="t", status=StepStatus.FAILED).is_success()

    def test_is_success_skipped(self):
        assert not StepResult(name="t", status=StepStatus.SKIPPED).is_success()

    def test_dict_without_log_path(self):
        r = StepResult(name="t", status=StepStatus.SUCCESS)
        d = r.dict()
        assert d["name"] == "t"
        assert d["log_path"] is None

    def test_dict_with_log_path(self, tmp_path: Path):
        log_path = tmp_path / "test.log"
        r = StepResult(name="t", status=StepStatus.SUCCESS, log_path=log_path)
        d = r.dict()
        assert d["log_path"] == str(log_path)

    def test_issues_default_empty(self):
        r = StepResult(name="t", status=StepStatus.SUCCESS)
        assert r.issues == []


# --- DependencyNode / DependencyGraph ---


class TestDependencyModels:
    def test_node_defaults(self):
        node = DependencyNode(module="pkg.mod", file="src/pkg/mod.py")
        assert node.imports == []
        assert node.imported_by == []

    def test_node_with_data(self):
        node = DependencyNode(module="a", file="a.py", imports=["b"], imported_by=["c"])
        assert node.imports == ["b"]
        assert node.imported_by == ["c"]

    def test_graph_defaults(self):
        g = DependencyGraph()
        assert g.nodes == {}
        assert g.cycles == []


# --- RunResult ---


class TestRunResult:
    def test_add_step(self, make_step_result):
        run = RunResult(run_id="r1", started_at=100.0)
        step = make_step_result()
        run.add_step(step)
        assert len(run.steps) == 1

    def test_mark_success(self):
        run = RunResult(run_id="r1", started_at=100.0)
        run.mark_success()
        assert run.status == StepStatus.SUCCESS
        assert run.finished_at is not None

    def test_mark_failed(self):
        run = RunResult(run_id="r1", started_at=100.0)
        run.mark_failed()
        assert run.status == StepStatus.FAILED
        assert run.finished_at is not None

    def test_duration_with_finish(self):
        run = RunResult(run_id="r1", started_at=100.0, finished_at=110.0)
        assert run.duration == 10.0

    def test_duration_without_finish(self):
        run = RunResult(run_id="r1", started_at=100.0)
        assert run.duration == 0.0

    def test_default_status(self):
        run = RunResult(run_id="r1", started_at=100.0)
        assert run.status == StepStatus.PENDING

    def test_to_json_file(self, tmp_path: Path, make_step_result):
        run = RunResult(run_id="r1", started_at=100.0)
        step = make_step_result(log_path=tmp_path / "step.log")
        run.add_step(step)
        run.mark_success()

        json_path = tmp_path / "output" / "run.json"
        run.to_json_file(json_path)

        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["run_id"] == "r1"
        assert isinstance(data["steps"][0]["log_path"], str)

    def test_from_json_file(self, tmp_path: Path):
        run = RunResult(run_id="r2", started_at=200.0)
        run.mark_success()

        json_path = tmp_path / "run.json"
        run.to_json_file(json_path)

        loaded = RunResult.from_json_file(json_path)
        assert loaded.run_id == "r2"
        assert loaded.status == StepStatus.SUCCESS

    def test_to_json_file_with_no_log_path(self, tmp_path: Path, make_step_result):
        run = RunResult(run_id="r3", started_at=100.0)
        step = make_step_result()  # no log_path
        run.add_step(step)

        json_path = tmp_path / "run.json"
        run.to_json_file(json_path)

        data = json.loads(json_path.read_text())
        assert data["steps"][0]["log_path"] is None
