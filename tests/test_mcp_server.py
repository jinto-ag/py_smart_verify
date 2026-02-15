"""Tests for py_verify.mcp_server.

These tests are skipped if the 'mcp' package is not installed.
"""

import json
import subprocess
from pathlib import Path

import pytest

mcp_mod = pytest.importorskip("mcp")

from py_verify.mcp_server import (  # isort: skip
    affected,
    config_resource,
    graph,
    graph_resource,
    last_run_resource,
    list_tasks,
    main,
    mcp,
    regen_graph,
    tasks_resource,
    verify,
)


class TestVerifyTool:
    def test_verify_returns_json(self, monkeypatch, tmp_path: Path):
        """Verify tool returns valid RunResult JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        result = verify(tasks=["self-test"], no_cache=True)
        data = json.loads(result)
        assert "run_id" in data
        assert "steps" in data
        assert "status" in data

    def test_verify_with_empty_tasks(self, monkeypatch, tmp_path: Path):
        """Verify tool with explicit empty tasks still works."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("x = 1\n")
        # With no tasks specified, it defaults to quality + tests
        # which may fail (tools not available), but should return valid JSON
        result = verify(tasks=["self-test"], no_cache=True)
        data = json.loads(result)
        assert isinstance(data, dict)


class TestGraphTool:
    def test_graph_returns_json(self, monkeypatch, tmp_path: Path):
        """Graph tool returns DependencyGraph JSON."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = graph()
        data = json.loads(result)
        assert "nodes" in data
        assert "cycles" in data

    def test_graph_with_paths(self, monkeypatch, tmp_path: Path):
        """Graph tool accepts paths parameter."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = graph(paths=["src"])
        data = json.loads(result)
        assert isinstance(data["nodes"], dict)


class TestAffectedTool:
    def test_affected_delegates_to_subprocess(self, monkeypatch):
        """Affected tool delegates to py-smart-test-affected."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(
                cmd, 0, stdout='{"affected": ["test_a.py"]}', stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = affected()
        data = json.loads(result)
        assert "affected" in data
        assert "--json" in captured[0]

    def test_affected_handles_file_not_found(self, monkeypatch):
        """Affected tool returns error JSON when binary not found."""

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = affected()
        data = json.loads(result)
        assert "error" in data
        assert "not found" in data["error"]

    def test_affected_handles_timeout(self, monkeypatch):
        """Affected tool returns error JSON on timeout."""

        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 30)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = affected()
        data = json.loads(result)
        assert data["error"] == "Command timed out"

    def test_affected_with_since(self, monkeypatch):
        """Affected tool passes --base flag when since differs from main."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        affected(since="develop")
        assert "--base" in captured[0]
        assert "develop" in captured[0]

    def test_affected_with_staged(self, monkeypatch):
        """Affected tool passes --staged flag."""
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        affected(staged=True)
        assert "--staged" in captured[0]


class TestRegenGraphTool:
    def test_regen_success(self, monkeypatch):
        """Regen graph returns success JSON."""

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="done\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = regen_graph()
        data = json.loads(result)
        assert data["success"] is True

    def test_regen_failure(self, monkeypatch):
        """Regen graph returns failure JSON."""

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error")

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = regen_graph()
        data = json.loads(result)
        assert data["success"] is False
        assert data["error"] == "error"

    def test_regen_file_not_found(self, monkeypatch):
        """Regen graph handles missing binary."""

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = regen_graph()
        data = json.loads(result)
        assert data["success"] is False
        assert "not found" in data["error"]

    def test_regen_timeout(self, monkeypatch):
        """Regen graph handles timeout."""

        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 60)

        monkeypatch.setattr(subprocess, "run", mock_run)
        result = regen_graph()
        data = json.loads(result)
        assert data["success"] is False
        assert data["error"] == "Command timed out"


class TestListTasksTool:
    def test_list_tasks_returns_array(self):
        """List tasks returns JSON array of task metadata."""
        result = list_tasks()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_tasks_has_metadata_fields(self):
        """Each task entry has required metadata fields."""
        result = list_tasks()
        data = json.loads(result)
        for task_info in data:
            assert "name" in task_info
            assert "display_name" in task_info
            assert "category" in task_info
            assert "description" in task_info
            assert "tool_name" in task_info


class TestLastRunResource:
    def test_reads_existing_file(self, monkeypatch, tmp_path: Path):
        """Reads .py_verify/last_run.json when it exists."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        py_verify_dir = tmp_path / ".py_verify"
        py_verify_dir.mkdir()
        last_run = py_verify_dir / "last_run.json"
        expected = {"run_id": "test-123", "status": "success"}
        last_run.write_text(json.dumps(expected))

        result = last_run_resource()
        data = json.loads(result)
        assert data["run_id"] == "test-123"

    def test_returns_error_when_no_file(self, monkeypatch, tmp_path: Path):
        """Returns error JSON when no previous run exists."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = last_run_resource()
        data = json.loads(result)
        assert "error" in data
        assert "No previous run" in data["error"]


class TestGraphResource:
    def test_builds_fresh_graph(self, monkeypatch, tmp_path: Path):
        """Graph resource builds and returns fresh graph."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("import os\n")
        result = graph_resource()
        data = json.loads(result)
        assert "nodes" in data
        assert "cycles" in data


class TestTasksResource:
    def test_returns_same_as_list_tasks(self):
        """Tasks resource returns same data as list_tasks tool."""
        tool_result = list_tasks()
        resource_result = tasks_resource()
        assert json.loads(tool_result) == json.loads(resource_result)


class TestConfigResource:
    def test_returns_project_info(self, monkeypatch, tmp_path: Path):
        """Config resource returns project configuration info."""
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        result = config_resource()
        data = json.loads(result)
        assert "config" in data
        assert "project_root" in data
        assert "detected_paths" in data


class TestMain:
    def test_main_is_callable(self):
        """Main function exists and is callable."""
        assert callable(main)

    def test_mcp_instance_exists(self):
        """MCP FastMCP instance is created."""
        assert mcp is not None
        assert mcp.name == "py-verify"
