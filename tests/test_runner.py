"""Tests for py_smart_verify.runner."""

from pathlib import Path

import py_smart_verify.console
import py_smart_verify.runner
from py_smart_verify.config import RunMode, ToolProfile, VerifyConfig
from py_smart_verify.models import StepResult, StepStatus
from py_smart_verify.runner import VerifyRunner
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import TaskRegistry


class FakeTask(BaseTask):
    """Fake task for runner tests."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="fake",
            display_name="Fake",
            category=TaskCategory.LINTER,
            description="Fake",
            tool_name="fake-tool",
            aliases=["fake"],
            cache_scope="quality",
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        return self._build_result(StepStatus.SUCCESS)


def _make_config(tmp_path: Path, **overrides) -> VerifyConfig:
    defaults = {
        "project_root": tmp_path,
        "cache_dir": tmp_path / ".py_smart_verify" / "cache",
        "log_dir": tmp_path / ".py_smart_verify" / "logs",
        "tasks": ["fake"],
    }
    defaults.update(overrides)
    return VerifyConfig(**defaults)


def _silence_console(monkeypatch):
    """Silence all console output."""
    from io import StringIO

    from rich.console import Console

    from py_smart_verify.console import get_theme

    buf = StringIO()
    test_console = Console(file=buf, theme=get_theme(), width=120)
    monkeypatch.setattr(py_smart_verify.console, "console", test_console)
    # Also patch runner's local import of console
    monkeypatch.setattr(py_smart_verify.runner, "console", test_console)
    return buf


class TestVerifyRunnerInit:
    def test_init(self, tmp_path: Path):
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        assert runner.config is config
        assert runner.result.status == StepStatus.PENDING


class TestSetup:
    def test_creates_directories(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        assert (tmp_path / ".py_smart_verify").exists()
        assert config.log_dir.exists()
        assert config.cache_dir.exists()


class TestEnsureGitignore:
    def test_creates_gitignore(self, tmp_path: Path):
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._ensure_gitignore()
        gitignore = tmp_path / ".py_smart_verify" / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "*" in content
        assert "!.gitignore" in content


class TestResolveTasks:
    def test_default_tasks(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=[])
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        # Default is quality + tests, which get expanded
        assert len(tasks) > 0

    def test_explicit_task(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=["fake"])
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        assert "fake" in tasks

    def test_quality_expansion(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=["quality"])
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        # quality gets expanded into subtasks
        assert len(tasks) > 1
        assert "quality" not in tasks

    def test_tests_smart(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=["tests"])
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        assert "tests" in tasks
        assert "e2e-tests" in tasks

    def test_tests_full(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=["tests"], full_tests=True)
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        assert "full-tests" in tasks
        assert "full-e2e-tests" in tasks

    def test_quality_optimized_profile(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=["quality"], tool_profile=ToolProfile.OPTIMIZED)
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        # Optimized profile should exclude non-optimized tools
        assert "format" not in tasks
        assert "isort" not in tasks
        assert "flake8" not in tasks
        assert "pyflakes" not in tasks
        # Should include ruff tasks
        assert "ruff-fix" in tasks
        assert "ruff-lint" in tasks

    def test_quality_full_profile(self, tmp_path: Path):
        config = _make_config(tmp_path, tasks=["quality"], tool_profile=ToolProfile.FULL)
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        # Full profile should include all tools
        assert "format" in tasks
        assert "isort" in tasks
        assert "ruff-fix" in tasks


class TestExecuteTask:
    def test_not_found(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        # Should not crash
        runner._execute_task("nonexistent", [])

    def test_not_available(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        # Register a fake task that's not available
        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: None)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        runner._execute_task("fake", [])
        # Should handle gracefully

    def test_success(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path, no_cache=True)
        runner = VerifyRunner(config)
        runner._setup()
        runner._execute_task("fake", [])
        assert len(runner.result.steps) == 1
        assert runner.result.steps[0].status == StepStatus.SUCCESS

    def test_cache_hit(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()

        # Pre-cache the scope
        runner.cache_manager.mark_ok("quality", 1.0)

        runner._execute_task("fake", [])
        # Cached - no step added
        assert len(runner.result.steps) == 0


class TestTeardown:
    def test_all_success(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        step = StepResult(name="t", status=StepStatus.SUCCESS)
        runner.result.add_step(step)
        runner._teardown()
        assert runner.result.status == StepStatus.SUCCESS

    def test_some_failures(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        runner.result.add_step(StepResult(name="ok", status=StepStatus.SUCCESS))
        runner.result.add_step(StepResult(name="bad", status=StepStatus.FAILED))
        runner._teardown()
        assert runner.result.status == StepStatus.FAILED

    def test_no_steps(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        runner._teardown()
        assert runner.result.status == StepStatus.SUCCESS

    def test_writes_json(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        runner._setup()
        runner._teardown()
        json_path = tmp_path / ".py_smart_verify" / "last_run.json"
        assert json_path.exists()


class TestExecuteTaskFastFail:
    def test_fast_fail_raises(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        class FailTask(BaseTask):
            def _get_metadata(self) -> TaskMetadata:
                return TaskMetadata(
                    name="fail",
                    display_name="Fail",
                    category=TaskCategory.LINTER,
                    description="Fail",
                    tool_name="fail-tool",
                    aliases=["fail"],
                    cache_scope="quality",
                    phase=0,
                )

            def execute(self, paths):
                return self._build_result(StepStatus.FAILED, exit_code=1)

        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FailTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path, no_cache=True, run_mode=RunMode.FAST_FAIL)
        runner = VerifyRunner(config)
        runner._setup()
        import pytest as _pytest

        with _pytest.raises(RuntimeError, match="fast-fail"):
            runner._execute_task("fail", [])

    def test_cache_marking_on_success(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path)  # cache enabled by default
        runner = VerifyRunner(config)
        runner._setup()
        runner._execute_task("fake", [])
        # After success, cache should be marked
        assert runner.cache_manager.is_cached("quality")


class TestResolveTasksEdgeCases:
    def test_quality_expansion_exception(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        # Force QualityCompositeTask to raise during initialization
        import py_smart_verify.runner

        def broken_quality(config):
            raise RuntimeError("boom")

        monkeypatch.setattr(py_smart_verify.runner, "QualityCompositeTask", broken_quality)
        config = _make_config(tmp_path, tasks=["quality"])
        runner = VerifyRunner(config)
        tasks = runner._resolve_tasks()
        # Falls back to keeping "quality" as-is
        assert "quality" in tasks


class TestRun:
    def test_full_run_success(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path, tasks=["fake"], no_cache=True)
        # Create a Python file so py_files is not empty
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        exit_code = VerifyRunner(config).run()
        assert exit_code == 0

    def test_no_tasks_returns_zero(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)

        config = _make_config(tmp_path, tasks=["nonexistent_group"])
        runner = VerifyRunner(config)
        # Monkeypatch _resolve_tasks to return empty
        monkeypatch.setattr(runner, "_resolve_tasks", lambda: [])
        exit_code = runner.run()
        assert exit_code == 0

    def test_no_files_warning(self, tmp_path: Path, monkeypatch):
        buf = _silence_console(monkeypatch)

        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_smart_verify.runner, "task_registry", reg)

        config = _make_config(tmp_path, tasks=["fake"], no_cache=True)
        # Don't create any Python files
        VerifyRunner(config).run()
        output = buf.getvalue()
        assert "No Python files" in output

    def test_exception_handling(self, tmp_path: Path, monkeypatch):
        _silence_console(monkeypatch)
        config = _make_config(tmp_path)
        runner = VerifyRunner(config)
        # Force _setup to raise
        monkeypatch.setattr(runner, "_setup", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        exit_code = runner.run()
        assert exit_code == 1
