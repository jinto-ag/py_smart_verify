"""Tests for py_verify.tasks.linters."""

import shutil
import subprocess
from pathlib import Path

import pytest

from py_verify.models import StepStatus
from py_verify.tasks.base import TaskCategory
from py_verify.tasks.linters import Flake8Task, PyflakesTask


class TestFlake8Task:
    def test_metadata(self, task_config):
        task = Flake8Task(task_config)
        assert task.metadata.name == "flake8"
        assert task.metadata.category == TaskCategory.LINTER

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = Flake8Task(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = Flake8Task(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS
        assert result.issues == []

    def test_failure_with_issues(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="a.py:10:5: E501 line too long\nb.py:3:1: W503 bad\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = Flake8Task(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 2

    def test_empty_paths(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = Flake8Task(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS


class TestFlake8Parse:
    @pytest.mark.parametrize(
        "output, expected_count",
        [
            ("a.py:10:5: E501 line too long", 1),
            ("a.py:10:5: E501 msg1\nb.py:3:1: W503 msg2", 2),
            ("", 0),
            ("\n\n", 0),
            ("invalid line without colons", 0),
        ],
    )
    def test_parse_flake8_output(self, task_config, output, expected_count):
        task = Flake8Task(task_config)
        issues = task._parse_flake8_output(output)
        assert len(issues) == expected_count

    def test_parse_value_error(self, task_config):
        task = Flake8Task(task_config)
        # Line with non-numeric line/col numbers
        issues = task._parse_flake8_output("a.py:abc:def: E501 msg")
        assert issues == []


class TestPyflakesTask:
    def test_metadata(self, task_config):
        task = PyflakesTask(task_config)
        assert task.metadata.name == "pyflakes"
        assert task.metadata.category == TaskCategory.LINTER

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = PyflakesTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = PyflakesTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="a.py:5: 'os' imported but unused\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = PyflakesTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1


class TestPyflakesParse:
    @pytest.mark.parametrize(
        "output, expected_count",
        [
            ("a.py:5: 'os' imported but unused", 1),
            ("", 0),
            ("invalid line", 0),
        ],
    )
    def test_parse_pyflakes_output(self, task_config, output, expected_count):
        task = PyflakesTask(task_config)
        issues = task._parse_pyflakes_output(output)
        assert len(issues) == expected_count

    def test_parse_value_error(self, task_config):
        task = PyflakesTask(task_config)
        issues = task._parse_pyflakes_output("a.py:abc: msg")
        assert issues == []


class TestPyflakesEmptyPaths:
    def test_empty_paths_uses_project_root(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = PyflakesTask(task_config)
        task.execute([])
        assert str(task_config.project_root) in captured_cmds[0]
