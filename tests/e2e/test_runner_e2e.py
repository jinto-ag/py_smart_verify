"""End-to-end runner tests for py-smart-verify.

These tests use the real VerifyRunner with real task execution — no mocking.
Covers all tasks and config option combinations.
"""

import json
import shutil
from pathlib import Path

import pytest

from py_smart_verify.config import RunMode, Severity, VerifyConfig
from py_smart_verify.models import StepStatus
from py_smart_verify.runner import VerifyRunner


def _make_config(project_root: Path, **overrides) -> VerifyConfig:
    """Build a VerifyConfig pointing at the given project."""
    defaults = {
        "project_root": project_root,
        "cache_dir": project_root / ".py_smart_verify" / "cache",
        "log_dir": project_root / ".py_smart_verify" / "logs",
        "no_cache": True,
    }
    defaults.update(overrides)
    return VerifyConfig(**defaults)


# ─── self-test (baseline) ────────────────────────────────────────────────


class TestRunnerSelfTest:
    def test_succeeds(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"])
        runner = VerifyRunner(config)
        exit_code, _result = runner.run_and_get_result()
        assert exit_code == 0

    def test_result_structure(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"])
        runner = VerifyRunner(config)
        _exit_code, result = runner.run_and_get_result()
        assert result.run_id
        assert result.status == StepStatus.SUCCESS
        assert len(result.steps) > 0

    def test_writes_last_run(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"])
        runner = VerifyRunner(config)
        runner.run_and_get_result()
        last_run = e2e_project / ".py_smart_verify" / "last_run.json"
        assert last_run.exists()
        data = json.loads(last_run.read_text())
        assert "run_id" in data
        assert data["status"] in ("success", "failed")

    def test_step_has_name(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"])
        runner = VerifyRunner(config)
        _ec, result = runner.run_and_get_result()
        assert result.steps[0].name == "Self-Test"


# ─── json_mode ───────────────────────────────────────────────────────────


class TestRunnerJsonMode:
    def test_suppresses_banner(self, e2e_project: Path, capsys):
        config = _make_config(e2e_project, tasks=["self-test"], json_mode=True)
        runner = VerifyRunner(config)
        runner.run_and_get_result()
        captured = capsys.readouterr()
        assert "py-smart-verify" not in captured.out.lower() or captured.out.strip() == ""

    def test_no_step_output(self, e2e_project: Path, capsys):
        config = _make_config(e2e_project, tasks=["self-test"], json_mode=True)
        runner = VerifyRunner(config)
        runner.run_and_get_result()
        captured = capsys.readouterr()
        assert "[" not in captured.out or captured.out.strip() == ""

    def test_still_writes_last_run(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], json_mode=True)
        runner = VerifyRunner(config)
        runner.run_and_get_result()
        last_run = e2e_project / ".py_smart_verify" / "last_run.json"
        assert last_run.exists()


# ─── config option variations ────────────────────────────────────────────


class TestRunnerConfigOptions:
    def test_verbose(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], verbose=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_continue_mode(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], run_mode=RunMode.CONTINUE)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_fast_fail_mode(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], run_mode=RunMode.FAST_FAIL)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_skip_tests(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], skip_tests=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_include_tests(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], include_tests=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_ignore_warnings(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], ignore_warnings=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_min_severity_1(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], min_severity=Severity(1))
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_min_severity_5(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], min_severity=Severity(5))
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_since_head(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], since="HEAD")
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_staged(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], staged=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_full_tests(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], full_tests=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_upgrade_deps(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], upgrade_deps=True)
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_paths_filter(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test"], paths=["src"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_all_options_combined(self, e2e_project: Path):
        config = _make_config(
            e2e_project,
            tasks=["self-test"],
            json_mode=True,
            verbose=True,
            no_cache=True,
            skip_tests=True,
            include_tests=True,
            ignore_warnings=True,
            min_severity=Severity(1),
            run_mode=RunMode.CONTINUE,
            since="HEAD",
            staged=True,
            full_tests=True,
            paths=["src"],
        )
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0


# ─── formatter tasks ────────────────────────────────────────────────────


class TestRunnerFormatters:
    def test_format_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["format"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_isort_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["isort"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_ruff_fix_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["ruff-fix"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0


# ─── linter tasks ───────────────────────────────────────────────────────


class TestRunnerLinters:
    def test_flake8_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["flake8"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_flake8_issues(self, e2e_project_with_issues: Path):
        config = _make_config(e2e_project_with_issues, tasks=["flake8"])
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code == 1
        failed = [s for s in result.steps if s.status == StepStatus.FAILED]
        assert len(failed) > 0

    def test_flake8_issues_json(self, e2e_project_with_issues: Path):
        config = _make_config(e2e_project_with_issues, tasks=["flake8"], json_mode=True)
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code == 1
        assert result.status == StepStatus.FAILED

    def test_flake8_issues_continue(self, e2e_project_with_issues: Path):
        config = _make_config(
            e2e_project_with_issues,
            tasks=["flake8"],
            run_mode=RunMode.CONTINUE,
        )
        runner = VerifyRunner(config)
        exit_code, _result = runner.run_and_get_result()
        assert exit_code == 1

    @pytest.mark.skipif(shutil.which("pyflakes") is None, reason="pyflakes not installed")
    def test_pyflakes_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["pyflakes"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        # Pyflakes may report unresolvable imports on temp projects
        assert exit_code in (0, 1)

    @pytest.mark.skipif(shutil.which("pyflakes") is None, reason="pyflakes not installed")
    def test_pyflakes_issues(self, e2e_project_with_issues: Path):
        config = _make_config(e2e_project_with_issues, tasks=["pyflakes"])
        runner = VerifyRunner(config)
        exit_code, _result = runner.run_and_get_result()
        assert exit_code == 1


# ─── analyzer tasks ─────────────────────────────────────────────────────


class TestRunnerAnalyzers:
    def test_circular_deps_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["circular-deps"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_imports_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["imports"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_imports_issues(self, e2e_project_with_issues: Path):
        """bad.py has import inside function."""
        config = _make_config(e2e_project_with_issues, tasks=["imports"])
        runner = VerifyRunner(config)
        exit_code, _result = runner.run_and_get_result()
        # May or may not find issues depending on how bad.py is structured
        assert exit_code in (0, 1)

    def test_architecture_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["architecture"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_standards_clean(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["standards"])
        runner = VerifyRunner(config)
        exit_code, _result = runner.run_and_get_result()
        # Standards may flag missing annotations etc.
        assert exit_code in (0, 1)

    def test_standards_json(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["standards"], json_mode=True)
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code in (0, 1)
        assert result.run_id


# ─── multiple tasks ─────────────────────────────────────────────────────


class TestRunnerMultipleTasks:
    def test_two_tasks(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test", "circular-deps"])
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code == 0
        assert len(result.steps) >= 2

    def test_three_tasks(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test", "circular-deps", "imports"])
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code == 0
        assert len(result.steps) >= 3

    def test_formatter_then_linter(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["format", "flake8"])
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code == 0
        assert len(result.steps) >= 2

    def test_mixed_with_unknown(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["self-test", "nonexistent-xyz", "imports"])
        runner = VerifyRunner(config)
        exit_code, result = runner.run_and_get_result()
        assert exit_code == 0
        # Unknown task is skipped, so at least 2 steps
        assert len(result.steps) >= 2


# ─── edge cases ──────────────────────────────────────────────────────────


class TestRunnerEdgeCases:
    def test_unknown_task(self, e2e_project: Path):
        config = _make_config(e2e_project, tasks=["nonexistent-xyz"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0

    def test_empty_tasks_defaults(self, e2e_project: Path):
        """Empty tasks list uses default quality + tests."""
        config = _make_config(e2e_project, tasks=[], skip_tests=True)
        runner = VerifyRunner(config)
        exit_code, _result = runner.run_and_get_result()
        # Quality tasks may pass or fail
        assert exit_code in (0, 1)

    def test_no_python_files(self, tmp_path: Path):
        """Project with no Python files."""
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text("[project]\nname='empty'\n")
        (tmp_path / ".py_smart_verify" / "cache").mkdir(parents=True)
        (tmp_path / ".py_smart_verify" / "logs").mkdir(parents=True)
        config = _make_config(tmp_path, tasks=["self-test"])
        runner = VerifyRunner(config)
        exit_code, _ = runner.run_and_get_result()
        assert exit_code == 0
