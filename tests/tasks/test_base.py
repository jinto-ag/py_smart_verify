"""Tests for py_verify.tasks.base."""

import shutil
import subprocess
from pathlib import Path

from py_verify.models import Issue, StepResult, StepStatus
from py_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata


class ConcreteTask(BaseTask):
    """Concrete implementation for testing BaseTask."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="concrete",
            display_name="Concrete",
            category=TaskCategory.LINTER,
            description="Test task",
            tool_name="test-tool",
            aliases=["concrete"],
            cache_scope="quality",
            phase=1,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        return self._build_result(StepStatus.SUCCESS)


# --- TaskCategory ---


class TestTaskCategory:
    def test_all_values(self):
        assert TaskCategory.FORMATTER == "formatter"
        assert TaskCategory.LINTER == "linter"
        assert TaskCategory.TYPE_CHECKER == "type_checker"
        assert TaskCategory.ANALYZER == "analyzer"
        assert TaskCategory.TESTING == "testing"
        assert TaskCategory.COMPOSITE == "composite"
        assert TaskCategory.META == "meta"


# --- TaskMetadata ---


class TestTaskMetadata:
    def test_fields(self):
        meta = TaskMetadata(
            name="test",
            display_name="Test",
            category=TaskCategory.LINTER,
            description="desc",
            tool_name="tool",
            aliases=["t"],
            cache_scope="quality",
        )
        assert meta.name == "test"
        assert meta.auto_fix is False
        assert meta.phase == 0

    def test_auto_fix_default(self):
        meta = TaskMetadata(
            name="t",
            display_name="T",
            category=TaskCategory.FORMATTER,
            description="d",
            tool_name="t",
            aliases=[],
            cache_scope="q",
            auto_fix=True,
        )
        assert meta.auto_fix is True


# --- BaseTask ---


class TestBaseTask:
    def test_init(self, task_config):
        task = ConcreteTask(task_config)
        assert task.metadata.name == "concrete"
        assert task.config is task_config

    def test_is_available_true(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        task = ConcreteTask(task_config)
        assert task.is_available()

    def test_is_available_false(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = ConcreteTask(task_config)
        assert not task.is_available()


class TestRunSubprocess:
    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = ConcreteTask(task_config)
        log_path = task_config.log_dir / "test.log"
        code, output = task._run_subprocess(["echo", "hi"], log_path)
        assert code == 0
        assert "ok" in output

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="err\n")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = ConcreteTask(task_config)
        log_path = task_config.log_dir / "test.log"
        code, _output = task._run_subprocess(["bad"], log_path)
        assert code == 1

    def test_stderr_logged(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="out\n", stderr="warn\n")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = ConcreteTask(task_config)
        log_path = task_config.log_dir / "test.log"
        task._run_subprocess(["cmd"], log_path)
        log_content = log_path.read_text()
        assert "STDERR" in log_content
        assert "warn" in log_content

    def test_timeout(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 300)

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = ConcreteTask(task_config)
        log_path = task_config.log_dir / "test.log"
        code, output = task._run_subprocess(["slow"], log_path)
        assert code == 1
        assert "Timeout" in output

    def test_exception(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise OSError("permission denied")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = ConcreteTask(task_config)
        log_path = task_config.log_dir / "test.log"
        code, output = task._run_subprocess(["nope"], log_path)
        assert code == 1
        assert "permission denied" in output

    def test_creates_log_dir(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = ConcreteTask(task_config)
        log_path = task_config.log_dir / "subdir" / "test.log"
        task._run_subprocess(["cmd"], log_path)
        assert log_path.parent.exists()


class TestBuildResult:
    def test_minimal(self, task_config):
        task = ConcreteTask(task_config)
        result = task._build_result(StepStatus.SUCCESS)
        assert result.name == "Concrete"
        assert result.status == StepStatus.SUCCESS
        assert result.issues == []

    def test_with_all_fields(self, task_config, tmp_path: Path):
        task = ConcreteTask(task_config)
        log_path = tmp_path / "test.log"
        issues = [Issue(file="a.py", type="error", message="bad", source_task="test")]
        result = task._build_result(
            status=StepStatus.FAILED,
            exit_code=1,
            command="test cmd",
            log_path=log_path,
            output="output",
            issues=issues,
        )
        assert result.status == StepStatus.FAILED
        assert result.exit_code == 1
        assert result.command == "test cmd"
        assert result.log_path == log_path
        assert len(result.issues) == 1

    def test_has_timestamps(self, task_config):
        task = ConcreteTask(task_config)
        result = task._build_result(StepStatus.SUCCESS)
        assert result.start_epoch is not None
        assert result.end_epoch is not None
        assert result.duration >= 0


class TestBuildSkipped:
    def test_skipped(self, task_config):
        task = ConcreteTask(task_config)
        result = task._build_skipped("not available")
        assert result.status == StepStatus.SKIPPED
