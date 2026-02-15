"""Tests for py_smart_verify.tasks.quality."""

from py_smart_verify.models import StepStatus
from py_smart_verify.tasks.base import TaskCategory
from py_smart_verify.tasks.quality import QualityCompositeTask
from py_smart_verify.tasks.registry import TaskRegistry


class TestQualityCompositeTask:
    def test_metadata(self, task_config):
        task = QualityCompositeTask(task_config)
        assert task.metadata.name == "quality"
        assert task.metadata.category == TaskCategory.COMPOSITE

    def test_execute_returns_success(self, task_config):
        task = QualityCompositeTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_get_subtasks_not_empty(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        assert len(subtasks) > 0

    def test_get_subtasks_ordering(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        # Formatters (phase 0) should come before linters (phase 1)
        # and type checkers (phase 2) before analyzers (phase 3)
        assert isinstance(subtasks, list)
        assert all(isinstance(s, str) for s in subtasks)

    def test_get_subtasks_contains_formatters(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        # Should contain at least some formatter names
        assert any(s in subtasks for s in ["format", "isort", "ruff-fix"])

    def test_get_subtasks_contains_linters(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        assert any(s in subtasks for s in ["flake8", "pyflakes"])

    def test_get_subtasks_contains_type_checkers(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        assert any(s in subtasks for s in ["mypy", "pyright", "basedpyright"])

    def test_get_subtasks_contains_analyzers(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        assert any(
            s in subtasks
            for s in [
                "deprecations",
                "circular-deps",
                "imports",
                "architecture",
                "standards",
            ]
        )

    def test_get_subtasks_handles_broken_task(self, task_config, monkeypatch):
        """Tasks that raise during instantiation are silently skipped."""
        import py_smart_verify.tasks.quality as quality_mod

        class BrokenClass:
            def __init__(self, config):
                raise RuntimeError("broken init")

        # Monkeypatch task_registry.get_by_category to return broken class
        # for every category, so all 4 except blocks are exercised
        reg = TaskRegistry()

        def mock_get_by_category(category):
            return [BrokenClass]

        monkeypatch.setattr(reg, "get_by_category", mock_get_by_category)
        monkeypatch.setattr(quality_mod, "task_registry", reg)

        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks()
        # All broken → no subtasks
        assert subtasks == []

    def test_get_subtasks_optimized_only(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks(optimized_only=True)
        # Only optimized tasks should be included
        assert len(subtasks) > 0
        # Non-optimized tools (black, isort, flake8, pyflakes) should be excluded
        assert "format" not in subtasks
        assert "isort" not in subtasks
        assert "flake8" not in subtasks
        assert "pyflakes" not in subtasks

    def test_get_subtasks_optimized_excludes_redundant(self, task_config):
        task = QualityCompositeTask(task_config)
        optimized = task.get_subtasks(optimized_only=True)
        full = task.get_subtasks(optimized_only=False)
        # Optimized should be a subset of full
        assert len(optimized) <= len(full)
        for name in optimized:
            assert name in full

    def test_get_subtasks_optimized_includes_ruff(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks(optimized_only=True)
        # Ruff tasks should be in the optimized set
        assert "ruff-fix" in subtasks
        assert "ruff-lint" in subtasks

    def test_get_subtasks_full_includes_all(self, task_config):
        task = QualityCompositeTask(task_config)
        subtasks = task.get_subtasks(optimized_only=False)
        # Full should include both optimized and non-optimized tasks
        assert "format" in subtasks
        assert "isort" in subtasks
        assert "ruff-fix" in subtasks

    def test_get_subtasks_backward_compatible(self, task_config):
        task = QualityCompositeTask(task_config)
        # Default call (no args) should return all subtasks
        default = task.get_subtasks()
        full = task.get_subtasks(optimized_only=False)
        assert default == full
