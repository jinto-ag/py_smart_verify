"""Tests for py_smart_verify.tasks.formatters."""

import shutil
import subprocess

from py_smart_verify.models import StepStatus
from py_smart_verify.tasks.base import TaskCategory
from py_smart_verify.tasks.formatters import FormatTask, IsortTask, RuffFixTask


class TestFormatTask:
    def test_metadata(self, task_config):
        task = FormatTask(task_config)
        assert task.metadata.name == "format"
        assert task.metadata.category == TaskCategory.FORMATTER
        assert task.metadata.auto_fix is True
        assert task.metadata.tool_name == "black"

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = FormatTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FormatTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_nonzero_still_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="reformatted\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FormatTask(task_config)
        result = task.execute(task_paths)
        # auto_fix task always returns SUCCESS
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths_uses_project_root(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FormatTask(task_config)
        task.execute([])
        assert str(task_config.project_root) in captured_cmds[0]


class TestIsortTask:
    def test_metadata(self, task_config):
        task = IsortTask(task_config)
        assert task.metadata.name == "isort"
        assert task.metadata.auto_fix is True

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = IsortTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = IsortTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_nonzero_still_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = IsortTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths_uses_project_root(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = IsortTask(task_config)
        task.execute([])
        assert str(task_config.project_root) in captured_cmds[0]


class TestRuffFixTask:
    def test_metadata(self, task_config):
        task = RuffFixTask(task_config)
        assert task.metadata.name == "ruff-fix"
        assert task.metadata.auto_fix is True

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = RuffFixTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = RuffFixTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_nonzero_still_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="fixed\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = RuffFixTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths_uses_project_root(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = RuffFixTask(task_config)
        task.execute([])
        assert str(task_config.project_root) in captured_cmds[0]
