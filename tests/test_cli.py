"""Tests for py_smart_verify.cli."""

import subprocess
from pathlib import Path

from typer.testing import CliRunner

import py_smart_verify.cli
from py_smart_verify.cli import _build_verify_config, app
from py_smart_verify.config import RunMode, Severity
from py_smart_verify.models import RunResult, StepStatus

runner = CliRunner()


def _make_mock_runner(exit_code: int = 0):
    """Create a MockRunner class that returns the given exit code."""

    class MockRunner:
        def __init__(self, config):
            self.config = config
            self.result = RunResult(
                run_id="test-run",
                started_at=0.0,
                status=StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED,
            )

        def run(self):
            return exit_code

        def run_and_get_result(self):
            return exit_code, self.result

    return MockRunner


class TestVerifyCommand:
    def test_version(self):
        result = runner.invoke(app, ["verify", "--version"])
        assert result.exit_code == 0
        assert "py-smart-verify" in result.output

    def test_default_run(self, monkeypatch, tmp_path: Path):
        """Verify command runs without crashing."""
        monkeypatch.setattr(py_smart_verify.cli, "VerifyRunner", _make_mock_runner(0))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = runner.invoke(app, ["verify", "quality"])
        assert result.exit_code == 0

    def test_with_options(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(py_smart_verify.cli, "VerifyRunner", _make_mock_runner(0))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = runner.invoke(
            app,
            [
                "verify",
                "--skip-tests",
                "--no-cache",
                "--verbose",
                "--min-severity",
                "2",
                "quality",
            ],
        )
        assert result.exit_code == 0

    def test_exit_code_propagation(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(py_smart_verify.cli, "VerifyRunner", _make_mock_runner(1))
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = runner.invoke(app, ["verify", "quality"])
        assert result.exit_code == 1


class TestBuildVerifyConfig:
    def test_defaults(self):
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
        assert config.tasks == []
        assert config.tools_filter == []
        assert config.paths == []
        assert config.run_mode == RunMode.FAST_FAIL

    def test_with_tasks(self):
        config = _build_verify_config(
            tasks=["ruff", "mypy"],
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
        assert config.tasks == ["ruff", "mypy"]

    def test_tools_split(self):
        config = _build_verify_config(
            tasks=None,
            tools="ruff,mypy,pyright",
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
        assert config.tools_filter == ["ruff", "mypy", "pyright"]

    def test_paths_split(self):
        config = _build_verify_config(
            tasks=None,
            tools=None,
            paths="src,tests",
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
        assert config.paths == ["src", "tests"]

    def test_continue_mode(self):
        config = _build_verify_config(
            tasks=None,
            tools=None,
            paths=None,
            skip_tests=False,
            no_cache=False,
            include_tests=False,
            ignore_warnings=False,
            min_severity=5,
            continue_mode=True,
            verbose=False,
            upgrade_deps=False,
            full_tests=False,
            since="main",
            staged=False,
        )
        assert config.run_mode == RunMode.CONTINUE

    def test_severity(self):
        config = _build_verify_config(
            tasks=None,
            tools=None,
            paths=None,
            skip_tests=False,
            no_cache=False,
            include_tests=False,
            ignore_warnings=False,
            min_severity=1,
            continue_mode=False,
            verbose=False,
            upgrade_deps=False,
            full_tests=False,
            since="main",
            staged=False,
        )
        assert config.min_severity == Severity.CRITICAL

    def test_all_flags(self):
        config = _build_verify_config(
            tasks=["quality"],
            tools="ruff",
            paths="src",
            skip_tests=True,
            no_cache=True,
            include_tests=True,
            ignore_warnings=True,
            min_severity=2,
            continue_mode=True,
            verbose=True,
            upgrade_deps=True,
            full_tests=True,
            since="develop",
            staged=True,
        )
        assert config.skip_tests is True
        assert config.no_cache is True
        assert config.include_tests is True
        assert config.ignore_warnings is True
        assert config.verbose is True
        assert config.upgrade_deps is True
        assert config.full_tests is True
        assert config.since == "develop"
        assert config.staged is True


class TestGraphCommand:
    def test_default(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        # Create a src dir with a file
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = runner.invoke(app, ["graph"])
        # May have no dependencies message, but should not crash
        assert result.exit_code == 0

    def test_with_output(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        out = tmp_path / "graph.json"
        result = runner.invoke(app, ["graph", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()


class TestAffectedCommand:
    def test_default(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="test_a.py\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected"])
        assert result.exit_code == 0

    def test_with_json(self, monkeypatch):
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="{}\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        _result = runner.invoke(app, ["affected", "--json"])
        assert "--json" in captured[0]

    def test_with_since(self, monkeypatch):
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        _result = runner.invoke(app, ["affected", "--since", "develop"])
        assert "--base" in captured[0]

    def test_with_staged(self, monkeypatch):
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        _result = runner.invoke(app, ["affected", "--staged"])
        assert "--staged" in captured[0]

    def test_file_not_found(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected"])
        assert result.exit_code == 1

    def test_nonzero(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected"])
        assert result.exit_code == 1


class TestRegenGraphCommand:
    def test_success(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["regen-graph"])
        assert result.exit_code == 0

    def test_failure(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["regen-graph"])
        assert result.exit_code == 1

    def test_file_not_found(self, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["regen-graph"])
        assert result.exit_code == 1
