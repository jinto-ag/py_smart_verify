"""Tests for py_verify.tasks.type_checkers."""

import shutil
import subprocess

import pytest

from py_verify.models import StepStatus
from py_verify.tasks.base import TaskCategory
from py_verify.tasks.type_checkers import BasedPyrightTask, MypyTask, PyrightTask


class TestMypyTask:
    def test_metadata(self, task_config):
        task = MypyTask(task_config)
        assert task.metadata.name == "mypy"
        assert task.metadata.category == TaskCategory.TYPE_CHECKER

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = MypyTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="Success\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = MypyTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="a.py:10:5: error: Incompatible types\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = MypyTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_empty_paths(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = MypyTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS


class TestMypyParse:
    @pytest.mark.parametrize(
        "output, count",
        [
            ("a.py:10:5: error: bad type", 1),
            ("a.py:10:5: error: msg1\nb.py:3:1: error: msg2", 2),
            ("", 0),
            ("a.py:10: note: some info", 0),  # no "error:" keyword
            ("short", 0),
        ],
    )
    def test_parse_mypy_output(self, task_config, output, count):
        task = MypyTask(task_config)
        issues = task._parse_mypy_output(output)
        assert len(issues) == count

    def test_parse_value_error(self, task_config):
        task = MypyTask(task_config)
        issues = task._parse_mypy_output("a.py:abc:def: error: bad")
        assert issues == []

    def test_parse_short_parts(self, task_config):
        task = MypyTask(task_config)
        issues = task._parse_mypy_output("a.py:10: error: bad")
        # Only 4 parts, needs >= 5
        assert issues == []


class TestPyrightTask:
    def test_metadata(self, task_config):
        task = PyrightTask(task_config)
        assert task.metadata.name == "pyright"
        assert task.metadata.category == TaskCategory.TYPE_CHECKER

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = PyrightTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="0 errors\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = PyrightTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="a.py:5:3: error: Type not assignable\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = PyrightTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_empty_paths_uses_project_root(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = PyrightTask(task_config)
        task.execute([])
        assert str(task_config.project_root) in captured_cmds[0]


class TestPyrightParse:
    @pytest.mark.parametrize(
        "output, count",
        [
            ("a.py:5:3: error: bad", 1),
            ("", 0),
            ("no error here", 0),
            ("short:parts", 0),
        ],
    )
    def test_parse_pyright_output(self, task_config, output, count):
        task = PyrightTask(task_config)
        issues = task._parse_pyright_output(output)
        assert len(issues) == count

    def test_parse_value_error(self, task_config):
        task = PyrightTask(task_config)
        issues = task._parse_pyright_output("a.py:abc:def: error: bad")
        assert issues == []


class TestBasedPyrightTask:
    def test_metadata(self, task_config):
        task = BasedPyrightTask(task_config)
        assert task.metadata.name == "basedpyright"
        assert "pylance" in task.metadata.aliases

    def test_not_available(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        task = BasedPyrightTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = BasedPyrightTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, task_paths, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)

        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="x.py:1:1: error: Missing type\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = BasedPyrightTask(task_config)
        result = task.execute(task_paths)
        assert result.status == StepStatus.FAILED

    def test_empty_paths_uses_project_root(self, task_config, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = BasedPyrightTask(task_config)
        task.execute([])
        assert str(task_config.project_root) in captured_cmds[0]


class TestBasedPyrightParse:
    @pytest.mark.parametrize(
        "output, count",
        [
            ("x.py:1:1: error: Missing type", 1),
            ("", 0),
            ("no error", 0),
        ],
    )
    def test_parse(self, task_config, output, count):
        task = BasedPyrightTask(task_config)
        issues = task._parse_pyright_output(output)
        assert len(issues) == count

    def test_source_task(self, task_config):
        task = BasedPyrightTask(task_config)
        issues = task._parse_pyright_output("x.py:1:1: error: bad")
        assert issues[0].source_task == "basedpyright"

    def test_parse_value_error(self, task_config):
        task = BasedPyrightTask(task_config)
        issues = task._parse_pyright_output("a.py:abc:def: error: bad")
        assert issues == []
