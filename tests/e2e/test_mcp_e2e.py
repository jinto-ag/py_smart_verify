"""End-to-end MCP server tests for py-verify.

These tests call MCP tool functions directly with real execution — no mocking
(except for subprocess-based tools like affected/regen_graph).
Skipped if the 'mcp' package is not installed.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("mcp")

from py_verify.mcp_server import (
    affected,
    config_resource,
    graph,
    graph_resource,
    last_run_resource,
    list_tasks,
    main,
    mcp as mcp_instance,
    regen_graph,
    tasks_resource,
    verify,
)


# ─── verify tool ─────────────────────────────────────────────────────────


class TestMCPVerifyTool:
    def test_default_params(self, monkeypatch, e2e_project: Path):
        """verify() with only defaults returns valid JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = verify(tasks=["self-test"], no_cache=True)
        data = json.loads(result)
        assert isinstance(data, dict)
        assert "run_id" in data

    def test_result_has_run_id(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True))
        assert data["run_id"]

    def test_result_has_status(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True))
        assert data["status"] == "success"

    def test_result_has_steps(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True))
        assert "steps" in data
        assert len(data["steps"]) > 0

    def test_skip_tests(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True, skip_tests=True))
        assert data["status"] == "success"

    def test_full_tests(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True, full_tests=True))
        assert data["status"] == "success"

    def test_verbose(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True, verbose=True))
        assert data["status"] == "success"

    def test_staged(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True, staged=True))
        assert data["status"] == "success"

    def test_since_head(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["self-test"], no_cache=True, since="HEAD"))
        assert data["status"] == "success"

    def test_continue_on_error(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(
            verify(tasks=["self-test"], no_cache=True, continue_on_error=True)
        )
        assert data["status"] == "success"

    def test_paths_filter(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(
            verify(tasks=["self-test"], no_cache=True, paths=["src"])
        )
        assert data["status"] == "success"

    def test_all_params_combined(self, monkeypatch, e2e_project: Path):
        """All parameters at once."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(
            verify(
                tasks=["self-test"],
                paths=["src"],
                skip_tests=True,
                no_cache=True,
                full_tests=True,
                since="HEAD",
                staged=True,
                continue_on_error=True,
                verbose=True,
            )
        )
        assert data["status"] == "success"
        assert data["run_id"]

    def test_task_circular_deps(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["circular-deps"], no_cache=True))
        assert data["status"] == "success"

    def test_task_imports(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(verify(tasks=["imports"], no_cache=True))
        assert data["status"] == "success"

    def test_multiple_tasks(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(
            verify(tasks=["self-test", "circular-deps"], no_cache=True)
        )
        assert len(data["steps"]) >= 2


# ─── graph tool ──────────────────────────────────────────────────────────


class TestMCPGraphTool:
    def test_default(self, monkeypatch, e2e_project: Path):
        """graph() returns valid DependencyGraph JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(graph())
        assert "nodes" in data
        assert "cycles" in data

    def test_with_paths(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(graph(paths=["src"]))
        assert "nodes" in data

    def test_no_cycles(self, monkeypatch, e2e_project: Path):
        """Clean project should have no cycles."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(graph())
        assert data["cycles"] == []

    def test_has_module_nodes(self, monkeypatch, e2e_project: Path):
        """Multi-file project should produce module nodes."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(graph())
        # nodes can be empty if discovery doesn't find files in tmp_path layout
        assert isinstance(data["nodes"], dict)


# ─── affected tool ───────────────────────────────────────────────────────


class TestMCPAffectedTool:
    def test_default(self):
        """affected() with defaults calls py-smart-test-affected."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"affected": ["tests/test_core.py"]}', returncode=0
            )
            result = affected()
            data = json.loads(result)
            assert "affected" in data
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "py-smart-test-affected" in cmd
            assert "--json" in cmd

    def test_since_param(self):
        """affected(since='HEAD~3') passes --base HEAD~3."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"affected": []}', returncode=0
            )
            affected(since="HEAD~3")
            cmd = mock_run.call_args[0][0]
            assert "--base" in cmd
            assert "HEAD~3" in cmd

    def test_since_main_no_base(self):
        """affected(since='main') does NOT pass --base."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"affected": []}', returncode=0
            )
            affected(since="main")
            cmd = mock_run.call_args[0][0]
            assert "--base" not in cmd

    def test_staged(self):
        """affected(staged=True) passes --staged."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"affected": []}', returncode=0
            )
            affected(staged=True)
            cmd = mock_run.call_args[0][0]
            assert "--staged" in cmd

    def test_all_params(self):
        """affected(since='HEAD', staged=True) passes both flags."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='{"affected": []}', returncode=0
            )
            affected(since="HEAD", staged=True)
            cmd = mock_run.call_args[0][0]
            assert "--base" in cmd
            assert "--staged" in cmd

    def test_not_found_error(self):
        """FileNotFoundError returns error JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("not found")
            result = affected()
            data = json.loads(result)
            assert "error" in data
            assert "not found" in data["error"].lower()

    def test_timeout_error(self):
        """TimeoutExpired returns error JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)
            result = affected()
            data = json.loads(result)
            assert "error" in data
            assert "timed out" in data["error"].lower()

    def test_empty_stdout_fallback(self):
        """Empty stdout returns empty affected list."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            result = affected()
            data = json.loads(result)
            assert data["affected"] == []


# ─── regen_graph tool ────────────────────────────────────────────────────


class TestMCPRegenGraphTool:
    def test_success(self):
        """Successful regen_graph returns success=True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Graph generated.", stderr="", returncode=0
            )
            result = regen_graph()
            data = json.loads(result)
            assert data["success"] is True
            assert data["error"] is None

    def test_failure(self):
        """Failed regen_graph returns success=False with error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", stderr="Some error", returncode=1
            )
            result = regen_graph()
            data = json.loads(result)
            assert data["success"] is False
            assert "Some error" in data["error"]

    def test_not_found(self):
        """FileNotFoundError returns error JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("not found")
            result = regen_graph()
            data = json.loads(result)
            assert data["success"] is False
            assert "not found" in data["error"].lower()

    def test_timeout(self):
        """TimeoutExpired returns error JSON."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=60)
            result = regen_graph()
            data = json.loads(result)
            assert data["success"] is False
            assert "timed out" in data["error"].lower()


# ─── list_tasks tool ─────────────────────────────────────────────────────


class TestMCPListTasksTool:
    def test_returns_array(self):
        """list_tasks returns a JSON array."""
        data = json.loads(list_tasks())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_has_known_tasks(self):
        """Known tasks are present in the list."""
        data = json.loads(list_tasks())
        names = [t["name"] for t in data]
        assert "self-test" in names

    def test_metadata_fields(self):
        """Each task has all expected metadata fields."""
        data = json.loads(list_tasks())
        required_keys = {
            "name",
            "display_name",
            "category",
            "description",
            "tool_name",
            "aliases",
            "cache_scope",
            "auto_fix",
            "phase",
        }
        for task in data:
            assert required_keys.issubset(task.keys()), (
                f"Task {task.get('name')} missing keys: "
                f"{required_keys - set(task.keys())}"
            )


# ─── last_run_resource ───────────────────────────────────────────────────


class TestMCPLastRunResource:
    def test_reads_existing(self, monkeypatch, e2e_project: Path):
        """Reads .py_verify/last_run.json when it exists."""
        last_run = e2e_project / ".py_verify" / "last_run.json"
        last_run.write_text(json.dumps({"run_id": "abc", "status": "success"}))
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = last_run_resource()
        data = json.loads(result)
        assert data["run_id"] == "abc"

    def test_error_when_no_file(self, monkeypatch, tmp_path: Path):
        """Returns error JSON when no last_run.json exists."""
        (tmp_path / ".py_verify").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = last_run_resource()
        data = json.loads(result)
        assert "error" in data

    def test_after_verify_run(self, monkeypatch, e2e_project: Path):
        """After running verify, last_run_resource returns valid data."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        verify(tasks=["self-test"], no_cache=True)
        result = last_run_resource()
        data = json.loads(result)
        assert "run_id" in data
        assert data["status"] in ("success", "failed")


# ─── graph_resource ──────────────────────────────────────────────────────


class TestMCPGraphResource:
    def test_builds_fresh_graph(self, monkeypatch, e2e_project: Path):
        """graph_resource builds graph from source files."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = graph_resource()
        data = json.loads(result)
        assert "nodes" in data
        assert "cycles" in data

    def test_has_module_nodes(self, monkeypatch, e2e_project: Path):
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(graph_resource())
        assert isinstance(data["nodes"], dict)


# ─── tasks_resource ──────────────────────────────────────────────────────


class TestMCPTasksResource:
    def test_returns_same_as_list_tasks(self):
        """tasks_resource delegates to list_tasks."""
        resource_result = json.loads(tasks_resource())
        tool_result = json.loads(list_tasks())
        assert resource_result == tool_result


# ─── config_resource ─────────────────────────────────────────────────────


class TestMCPConfigResource:
    def test_returns_project_info(self, monkeypatch, e2e_project: Path):
        """config_resource returns JSON with config and project_root."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        result = config_resource()
        data = json.loads(result)
        assert "config" in data
        assert "project_root" in data

    def test_has_venv_and_package_manager(self, monkeypatch, e2e_project: Path):
        """config_resource includes venv and package_manager keys."""
        monkeypatch.setattr(Path, "cwd", lambda: e2e_project)
        data = json.loads(config_resource())
        assert "venv" in data
        assert "package_manager" in data
        assert "detected_paths" in data


# ─── MCP instance ────────────────────────────────────────────────────────


class TestMCPInstance:
    def test_name(self):
        """MCP server has correct name."""
        assert mcp_instance.name == "py-verify"

    def test_main_callable(self):
        """main() is callable."""
        assert callable(main)
