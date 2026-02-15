"""Tests for py_verify.tasks.testing."""

import shutil
import subprocess
from pathlib import Path

import pytest

from py_verify.models import StepStatus
from py_verify.tasks.base import TaskCategory
from py_verify.tasks.testing import (
    AffectedTestsTask,
    E2ETestTask,
    FullE2ETestTask,
    FullTestTask,
    RegenerateGraphTask,
    SmartTestTask,
)


# --- SmartTestTask ---


class TestSmartTestTask:
    def test_metadata(self, task_config):
        task = SmartTestTask(task_config)
        assert task.metadata.name == "tests"
        assert task.metadata.category == TaskCategory.TESTING

    def test_skip_tests(self, task_config):
        task_config.skip_tests = True
        task = SmartTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="2 passed\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = SmartTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="FAILED test_x\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = SmartTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_with_since(self, task_config, monkeypatch):
        task_config.since = "develop"
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = SmartTestTask(task_config)
        task.execute([])
        assert any("--smart-since" in c for c in captured[0])

    def test_with_staged(self, task_config, monkeypatch):
        task_config.staged = True
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = SmartTestTask(task_config)
        task.execute([])
        assert "--smart-staged" in captured[0]

    def test_parse_pytest_output_failures(self, task_config):
        task = SmartTestTask(task_config)
        output = "FAILED test_a\nFAILED test_b\npassed 3"
        issues = task._parse_pytest_output(output)
        assert len(issues) == 2

    def test_parse_pytest_output_no_failures(self, task_config):
        task = SmartTestTask(task_config)
        issues = task._parse_pytest_output("5 passed\n")
        assert issues == []

    def test_parse_pytest_output_limit_5(self, task_config):
        task = SmartTestTask(task_config)
        output = "\n".join(f"FAILED test_{i}" for i in range(10))
        issues = task._parse_pytest_output(output)
        assert len(issues) == 5


# --- FullTestTask ---


class TestFullTestTask:
    def test_metadata(self, task_config):
        task = FullTestTask(task_config)
        assert task.metadata.name == "full-tests"

    def test_skip_tests(self, task_config):
        task_config.skip_tests = True
        task = FullTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="FAILED test_x\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.FAILED

    def test_with_since(self, task_config, monkeypatch):
        task_config.since = "develop"
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullTestTask(task_config)
        task.execute([])
        assert any("--smart-since" in c for c in captured[0])

    def test_with_staged(self, task_config, monkeypatch):
        task_config.staged = True
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullTestTask(task_config)
        task.execute([])
        assert "--smart-staged" in captured[0]


# --- E2ETestTask ---


class TestE2ETestTask:
    def test_metadata(self, task_config):
        task = E2ETestTask(task_config)
        assert task.metadata.name == "e2e-tests"

    def test_skip_tests(self, task_config):
        task_config.skip_tests = True
        task = E2ETestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = E2ETestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="FAILED test_e2e\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = E2ETestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_with_since(self, task_config, monkeypatch):
        task_config.since = "develop"
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = E2ETestTask(task_config)
        task.execute([])
        assert any("--smart-since" in c for c in captured[0])

    def test_with_staged(self, task_config, monkeypatch):
        task_config.staged = True
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = E2ETestTask(task_config)
        task.execute([])
        assert "--smart-staged" in captured[0]

    def test_parse_pytest_output(self, task_config):
        task = E2ETestTask(task_config)
        output = "FAILED test_a\nFAILED test_b"
        issues = task._parse_pytest_output(output)
        assert len(issues) == 2


# --- FullE2ETestTask ---


class TestFullE2ETestTask:
    def test_metadata(self, task_config):
        task = FullE2ETestTask(task_config)
        assert task.metadata.name == "full-e2e-tests"

    def test_skip_tests(self, task_config):
        task_config.skip_tests = True
        task = FullE2ETestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SKIPPED

    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullE2ETestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd, 1, stdout="FAILED test_full\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullE2ETestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_with_since(self, task_config, monkeypatch):
        task_config.since = "develop"
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullE2ETestTask(task_config)
        task.execute([])
        assert any("--smart-since" in c for c in captured[0])

    def test_with_staged(self, task_config, monkeypatch):
        task_config.staged = True
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = FullE2ETestTask(task_config)
        task.execute([])
        assert "--smart-staged" in captured[0]

    def test_parse_pytest_output(self, task_config):
        task = FullE2ETestTask(task_config)
        output = "FAILED test_x\nFAILED test_y\n5 passed"
        issues = task._parse_pytest_output(output)
        assert len(issues) == 2


# --- RegenerateGraphTask ---


class TestRegenerateGraphTask:
    def test_metadata(self, task_config):
        task = RegenerateGraphTask(task_config)
        assert task.metadata.name == "regen-graph"

    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="done\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = RegenerateGraphTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="err")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = RegenerateGraphTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.FAILED


# --- AffectedTestsTask ---


class TestAffectedTestsTask:
    def test_metadata(self, task_config):
        task = AffectedTestsTask(task_config)
        assert task.metadata.name == "affected"

    def test_success(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="test_a.py\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = AffectedTestsTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_failure(self, task_config, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="err")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = AffectedTestsTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.FAILED

    def test_with_since(self, task_config, monkeypatch):
        task_config.since = "develop"
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = AffectedTestsTask(task_config)
        task.execute([])
        assert "--base" in captured[0]

    def test_with_staged(self, task_config, monkeypatch):
        task_config.staged = True
        captured = []

        def mock_run(cmd, **kwargs):
            captured.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        task = AffectedTestsTask(task_config)
        task.execute([])
        assert "--staged" in captured[0]
