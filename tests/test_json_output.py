"""Tests for --json output mode."""

import json
from io import StringIO
from pathlib import Path

import py_verify.console
import py_verify.runner
from py_verify.cli import _build_verify_config, app
from py_verify.config import VerifyConfig
from py_verify.models import RunResult, StepResult, StepStatus
from py_verify.runner import VerifyRunner
from py_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_verify.tasks.registry import TaskRegistry
from rich.console import Console
from typer.testing import CliRunner

import py_verify.cli

cli_runner = CliRunner()


def _make_mock_runner(exit_code: int = 0):
    """Create a MockRunner class for CLI tests."""

    class MockRunner:
        def __init__(self, config):
            self.config = config
            self.result = RunResult(
                run_id="test-json-run",
                started_at=1000.0,
                finished_at=1001.5,
                status=StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED,
                steps=[
                    StepResult(
                        name="fake-task",
                        status=(
                            StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED
                        ),
                        start_epoch=1000.0,
                        end_epoch=1001.5,
                        exit_code=exit_code,
                    )
                ],
            )

        def run(self):
            return exit_code

        def run_and_get_result(self):
            return exit_code, self.result

    return MockRunner


def _make_config(tmp_path: Path, **overrides) -> VerifyConfig:
    defaults = {
        "project_root": tmp_path,
        "cache_dir": tmp_path / ".py_verify" / "cache",
        "log_dir": tmp_path / ".py_verify" / "logs",
        "tasks": ["fake"],
    }
    defaults.update(overrides)
    return VerifyConfig(**defaults)


def _silence_console(monkeypatch):
    """Silence all console output and return capture buffer."""
    from py_verify.console import get_theme

    buf = StringIO()
    test_console = Console(file=buf, theme=get_theme(), width=120)
    monkeypatch.setattr(py_verify.console, "console", test_console)
    monkeypatch.setattr(py_verify.runner, "console", test_console)
    return buf


class FakeTask(BaseTask):
    """Fake task for JSON mode tests."""

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


class TestConfigJsonMode:
    def test_json_mode_default_false(self):
        config = VerifyConfig()
        assert config.json_mode is False

    def test_json_mode_set_true(self):
        config = VerifyConfig(json_mode=True)
        assert config.json_mode is True


class TestBuildVerifyConfigJsonMode:
    def test_json_mode_default(self):
        config = _build_verify_config(
            tasks=None,
            tools=None,
            paths=None,
            skip_tests=False,
            no_cache=False,
            include_tests=False,
            ignore_warnings=False,
            min_severity=5,
            continue_mode=False,
            verbose=False,
            upgrade_deps=False,
            full_tests=False,
            since="main",
            staged=False,
        )
        assert config.json_mode is False

    def test_json_mode_true(self):
        config = _build_verify_config(
            tasks=None,
            tools=None,
            paths=None,
            skip_tests=False,
            no_cache=False,
            include_tests=False,
            ignore_warnings=False,
            min_severity=5,
            continue_mode=False,
            verbose=False,
            upgrade_deps=False,
            full_tests=False,
            since="main",
            staged=False,
            json_mode=True,
        )
        assert config.json_mode is True


class TestRunnerJsonMode:
    def test_json_mode_suppresses_banner(self, monkeypatch, tmp_path: Path):
        """Runner produces no console output in json_mode."""
        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_verify.runner, "task_registry", reg)

        buf = _silence_console(monkeypatch)
        config = _make_config(tmp_path, tasks=["fake"], no_cache=True, json_mode=True)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        runner_inst = VerifyRunner(config)
        runner_inst.run()
        output = buf.getvalue()
        # Should have no banner or step output
        assert "py-verify" not in output.lower() or output.strip() == ""

    def test_json_mode_still_writes_last_run(self, monkeypatch, tmp_path: Path):
        """last_run.json is still written in json_mode."""
        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_verify.runner, "task_registry", reg)

        _silence_console(monkeypatch)
        config = _make_config(tmp_path, tasks=["fake"], no_cache=True, json_mode=True)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        VerifyRunner(config).run()
        json_path = tmp_path / ".py_verify" / "last_run.json"
        assert json_path.exists()

    def test_run_and_get_result(self, monkeypatch, tmp_path: Path):
        """run_and_get_result returns (exit_code, RunResult)."""
        import shutil

        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        reg = TaskRegistry()
        reg.register(FakeTask)
        monkeypatch.setattr(py_verify.runner, "task_registry", reg)

        _silence_console(monkeypatch)
        config = _make_config(tmp_path, tasks=["fake"], no_cache=True, json_mode=True)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")

        runner_inst = VerifyRunner(config)
        exit_code, result = runner_inst.run_and_get_result()
        assert exit_code == 0
        assert isinstance(result, RunResult)
        assert result.status == StepStatus.SUCCESS


class TestVerifyJsonCLI:
    def test_json_flag_outputs_json(self, monkeypatch, tmp_path: Path):
        """verify --json outputs valid JSON to stdout."""
        monkeypatch.setattr(py_verify.cli, "VerifyRunner", _make_mock_runner(0))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = cli_runner.invoke(app, ["verify", "--json", "quality"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "run_id" in data
        assert "steps" in data
        assert data["status"] == "success"

    def test_json_flag_preserves_exit_code(self, monkeypatch, tmp_path: Path):
        """Exit code is 1 on failure even with --json."""
        monkeypatch.setattr(py_verify.cli, "VerifyRunner", _make_mock_runner(1))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = cli_runner.invoke(app, ["verify", "--json", "quality"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["status"] == "failed"

    def test_json_output_has_step_details(self, monkeypatch, tmp_path: Path):
        """JSON output includes step name and status."""
        monkeypatch.setattr(py_verify.cli, "VerifyRunner", _make_mock_runner(0))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = cli_runner.invoke(app, ["verify", "--json", "quality"])
        data = json.loads(result.output)
        assert len(data["steps"]) == 1
        assert data["steps"][0]["name"] == "fake-task"

    def test_no_json_flag_no_json_output(self, monkeypatch, tmp_path: Path):
        """Without --json, output is not JSON."""
        monkeypatch.setattr(py_verify.cli, "VerifyRunner", _make_mock_runner(0))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = cli_runner.invoke(app, ["verify", "quality"])
        assert result.exit_code == 0
        # Should not be valid JSON (or may be empty)
        try:
            json.loads(result.output)
            # If output happens to be empty or just whitespace, that's fine
            assert result.output.strip() == "" or not result.output.strip().startswith(
                "{"
            )
        except json.JSONDecodeError:
            pass  # Expected - output is not JSON


class TestGraphJsonCLI:
    def test_graph_json_output(self, monkeypatch, tmp_path: Path):
        """graph --json outputs valid JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = cli_runner.invoke(app, ["graph", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "nodes" in data
        assert "cycles" in data

    def test_graph_json_suppresses_tree(self, monkeypatch, tmp_path: Path):
        """graph --json does not show Rich tree."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = cli_runner.invoke(app, ["graph", "--json"])
        # Output should be pure JSON, no tree decorations
        data = json.loads(result.output)
        assert isinstance(data, dict)

    def test_graph_no_json_shows_tree(self, monkeypatch, tmp_path: Path):
        """graph without --json shows tree output."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = cli_runner.invoke(app, ["graph"])
        assert result.exit_code == 0
        # Should not be valid JSON
        try:
            json.loads(result.output)
            assert result.output.strip() == ""
        except json.JSONDecodeError:
            pass  # Expected - output is tree, not JSON


class TestMCPCommand:
    def test_mcp_import_error(self, monkeypatch):
        """mcp command fails gracefully when mcp not installed."""

        def mock_import_error(*args, **kwargs):
            raise ImportError("No module named 'mcp'")

        monkeypatch.setattr(
            py_verify.cli,
            "mcp",
            lambda: (_ for _ in ()).throw(ImportError("No module named 'mcp'")),
        )
        # Test via direct invocation with import failure
        import builtins

        original_import = builtins.__import__

        def blocking_import(name, *args, **kwargs):
            if name == "py_verify.mcp_server":
                raise ImportError("No module named 'mcp'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocking_import)
        result = cli_runner.invoke(app, ["mcp"])
        assert result.exit_code == 1
        assert "MCP" in result.output or "mcp" in result.output
