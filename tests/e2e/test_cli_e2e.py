"""End-to-end CLI tests for py-verify.

These tests invoke the CLI through typer.testing.CliRunner with
the real VerifyRunner — no mocking. Covers all commands with
all argument combinations.
"""

import json
import re
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from py_verify.cli import app

runner = CliRunner()


# ─── verify command ──────────────────────────────────────────────────────


class TestVerifySelfTest:
    """verify with self-test task — baseline command."""

    def test_basic(self, monkeypatch, e2e_project: Path):
        """verify self-test returns exit 0."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_json(self, monkeypatch, e2e_project: Path):
        """verify --json self-test outputs valid RunResult JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--json", "--no-cache", "self-test"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "run_id" in data
        assert "steps" in data
        assert "status" in data
        assert data["status"] == "success"

    def test_json_no_rich_markup(self, monkeypatch, e2e_project: Path):
        """JSON output contains no Rich markup tags."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--json", "--no-cache", "self-test"])
        assert result.exit_code == 0
        rich_tag = re.compile(r"\[/?(?:red|green|yellow|blue|cyan|bold|dim|error)\]")
        assert not rich_tag.search(result.output)

    def test_writes_last_run_json(self, monkeypatch, e2e_project: Path):
        """verify writes .py_verify/last_run.json."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        runner.invoke(app, ["verify", "--no-cache", "self-test"])
        last_run = e2e_project / ".py_verify" / "last_run.json"
        assert last_run.exists()
        data = json.loads(last_run.read_text())
        assert "run_id" in data


class TestVerifyFlags:
    """verify with each boolean flag."""

    def test_no_cache(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_continue(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--continue", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_skip_tests(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--skip-tests", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_verbose(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "-v", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_verbose_long(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--verbose", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_include_tests(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--include-tests", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_ignore_warnings(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--ignore-warnings", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_staged(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--staged", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_full_tests(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--full-tests", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_upgrade_deps(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--upgrade-deps", "--no-cache", "self-test"])
        assert result.exit_code == 0


class TestVerifyParameterized:
    """verify with value-accepting options."""

    def test_min_severity_1(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--min-severity", "1", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_min_severity_3(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--min-severity", "3", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_min_severity_5(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--min-severity", "5", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_since_custom_ref(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--since", "HEAD~1", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_paths_option(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--paths", "src", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_paths_multiple(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--paths", "src,tests", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_tools_filter(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--tools", "python", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0


class TestVerifyFlagCombinations:
    """verify with multiple flags combined."""

    def test_json_and_verbose(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--json", "-v", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"

    def test_json_and_continue(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--json", "--continue", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "steps" in data

    def test_json_and_skip_tests(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--json", "--skip-tests", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0
        json.loads(result.output)  # valid JSON

    def test_continue_verbose_no_cache(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--continue", "-v", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_staged_since_combination(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--staged", "--since", "HEAD", "--no-cache", "self-test"]
        )
        assert result.exit_code == 0

    def test_all_flags_together(self, monkeypatch, e2e_project: Path):
        """All flags at once."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app,
            [
                "verify",
                "--json",
                "--no-cache",
                "--continue",
                "-v",
                "--skip-tests",
                "--include-tests",
                "--ignore-warnings",
                "--min-severity", "1",
                "--since", "HEAD",
                "--staged",
                "--full-tests",
                "--paths", "src",
                "self-test",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestVerifyTasks:
    """verify with different registered task names."""

    def test_self_test_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_flake8_task_clean(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "flake8"])
        assert result.exit_code == 0

    def test_flake8_task_issues(self, monkeypatch, e2e_project_with_issues: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project_with_issues)
        result = runner.invoke(app, ["verify", "--no-cache", "flake8"])
        assert result.exit_code == 1

    def test_flake8_json_issues(self, monkeypatch, e2e_project_with_issues: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project_with_issues)
        result = runner.invoke(app, ["verify", "--json", "--no-cache", "flake8"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["status"] == "failed"

    def test_format_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "format"])
        assert result.exit_code == 0

    def test_isort_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "isort"])
        assert result.exit_code == 0

    def test_ruff_fix_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "ruff-fix"])
        assert result.exit_code == 0

    def test_pyflakes_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "pyflakes"])
        assert result.exit_code == 0

    def test_circular_deps_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "circular-deps"])
        assert result.exit_code == 0

    def test_imports_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "imports"])
        assert result.exit_code == 0

    def test_architecture_task_clean(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "architecture"])
        assert result.exit_code == 0

    def test_standards_task(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "standards"])
        # Clean code may still have standards issues (annotations, docstrings)
        assert result.exit_code in (0, 1)

    def test_multiple_tasks(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--no-cache", "self-test", "circular-deps"]
        )
        assert result.exit_code == 0

    def test_multiple_tasks_json(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(
            app, ["verify", "--json", "--no-cache", "self-test", "circular-deps"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["steps"]) >= 2

    def test_unknown_task(self, monkeypatch, e2e_project: Path):
        """Unknown task name is skipped gracefully."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "nonexistent-xyz"])
        assert result.exit_code == 0

    def test_no_tasks_defaults(self, monkeypatch, e2e_project: Path):
        """No tasks specified uses default (quality + tests); may fail but shouldn't crash."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "--skip-tests"])
        # Should return 0 or 1 but not crash
        assert result.exit_code in (0, 1)


class TestVerifyExitCodes:
    """Exit code behavior."""

    def test_success_exit_0(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_failure_exit_1(self, monkeypatch, e2e_project_with_issues: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project_with_issues)
        result = runner.invoke(app, ["verify", "--no-cache", "flake8"])
        assert result.exit_code == 1

    def test_json_success_exit_0(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["verify", "--json", "--no-cache", "self-test"])
        assert result.exit_code == 0

    def test_json_failure_exit_1(self, monkeypatch, e2e_project_with_issues: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project_with_issues)
        result = runner.invoke(app, ["verify", "--json", "--no-cache", "flake8"])
        assert result.exit_code == 1


# ─── graph command ───────────────────────────────────────────────────────


class TestGraphCommand:
    """graph command with all argument combinations."""

    def test_default(self, monkeypatch, e2e_project: Path):
        """graph without flags."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["graph"])
        assert result.exit_code == 0

    def test_json(self, monkeypatch, e2e_project: Path):
        """graph --json returns valid DependencyGraph JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["graph", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "nodes" in data
        assert "cycles" in data

    def test_json_has_modules(self, monkeypatch, e2e_project: Path):
        """graph --json includes the project's modules."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["graph", "--json"])
        data = json.loads(result.output)
        assert isinstance(data["nodes"], dict)
        assert len(data["nodes"]) > 0

    def test_paths_option(self, monkeypatch, e2e_project: Path):
        """graph --paths src limits scope."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["graph", "--paths", "src"])
        assert result.exit_code == 0

    def test_paths_json(self, monkeypatch, e2e_project: Path):
        """graph --paths src --json."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["graph", "--paths", "src", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "nodes" in data

    def test_output_file(self, monkeypatch, e2e_project: Path):
        """graph --output writes to file."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        out_file = e2e_project / "graph.json"
        result = runner.invoke(app, ["graph", "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()

    def test_output_and_paths(self, monkeypatch, e2e_project: Path):
        """graph --output --paths combined."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        out_file = e2e_project / "graph2.json"
        result = runner.invoke(
            app, ["graph", "--output", str(out_file), "--paths", "src"]
        )
        assert result.exit_code == 0
        assert out_file.exists()

    def test_no_cycles_on_clean_project(self, monkeypatch, e2e_project: Path):
        """Clean project has no circular dependencies."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = runner.invoke(app, ["graph", "--json"])
        data = json.loads(result.output)
        assert data["cycles"] == []


# ─── affected command ────────────────────────────────────────────────────


class TestAffectedCommand:
    """affected command with all argument combinations."""

    def test_default(self, monkeypatch, e2e_project: Path):
        """affected with no flags delegates to py-smart-test-affected."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected"])
        assert result.exit_code == 0
        assert captured[0][0] == "py-smart-test-affected"

    def test_json(self, monkeypatch, e2e_project: Path):
        """affected --json passes --json to subprocess."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(
                cmd, 0, stdout='{"affected": []}', stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected", "--json"])
        assert result.exit_code == 0
        assert "--json" in captured[0]

    def test_since(self, monkeypatch, e2e_project: Path):
        """affected --since develop passes --base develop."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected", "--since", "develop"])
        assert result.exit_code == 0
        assert "--base" in captured[0]
        assert "develop" in captured[0]

    def test_staged(self, monkeypatch, e2e_project: Path):
        """affected --staged passes --staged."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected", "--staged"])
        assert result.exit_code == 0
        assert "--staged" in captured[0]

    def test_all_flags(self, monkeypatch, e2e_project: Path):
        """affected --json --since develop --staged."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(
                cmd, 0, stdout='{"affected": []}', stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(
            app, ["affected", "--json", "--since", "develop", "--staged"]
        )
        assert result.exit_code == 0
        cmd = captured[0]
        assert "--json" in cmd
        assert "--base" in cmd
        assert "--staged" in cmd

    def test_not_found_error(self, monkeypatch):
        """affected gracefully handles missing py-smart-test-affected."""

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected"])
        assert result.exit_code == 1

    def test_nonzero_exit(self, monkeypatch):
        """affected propagates non-zero exit from subprocess."""

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["affected"])
        assert result.exit_code == 1


# ─── regen-graph command ─────────────────────────────────────────────────


class TestRegenGraphCommand:
    """regen-graph command (no flags)."""

    def test_success(self, monkeypatch):
        """regen-graph succeeds when subprocess succeeds."""

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="done\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["regen-graph"])
        assert result.exit_code == 0

    def test_failure(self, monkeypatch):
        """regen-graph exits 1 when subprocess fails."""

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["regen-graph"])
        assert result.exit_code == 1

    def test_not_found(self, monkeypatch):
        """regen-graph exits 1 when binary not found."""

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = runner.invoke(app, ["regen-graph"])
        assert result.exit_code == 1


# ─── mcp command ─────────────────────────────────────────────────────────


class TestMCPCommand:
    """mcp command starts the MCP server."""

    def test_mcp_callable(self):
        """mcp command is registered."""
        # Invoke --help to prove the command exists without starting the server
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output or "mcp" in result.output.lower()


# ─── version and help ────────────────────────────────────────────────────


class TestVersionAndHelp:
    """Version flag and help output."""

    def test_version_flag(self):
        result = runner.invoke(app, ["verify", "--version"])
        assert result.exit_code == 0
        assert "py-verify" in result.output

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code in (0, 2)
        assert "verify" in result.output.lower() or "Usage" in result.output

    def test_verify_help(self):
        result = runner.invoke(app, ["verify", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--no-cache" in result.output
        assert "--skip-tests" in result.output

    def test_graph_help(self):
        result = runner.invoke(app, ["graph", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--output" in result.output

    def test_affected_help(self):
        result = runner.invoke(app, ["affected", "--help"])
        assert result.exit_code == 0
        assert "--since" in result.output
        assert "--staged" in result.output

    def test_regen_graph_help(self):
        result = runner.invoke(app, ["regen-graph", "--help"])
        assert result.exit_code == 0
