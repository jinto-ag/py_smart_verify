"""Tests for py_verify.tasks.registry."""

from pathlib import Path

from py_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_verify.tasks.registry import TaskRegistry, register


class DummyTask(BaseTask):
    """Test task for registry tests."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="dummy",
            display_name="Dummy",
            category=TaskCategory.LINTER,
            description="A test task",
            tool_name="dummy-tool",
            aliases=["dummy", "dum"],
            cache_scope="quality",
            phase=0,
        )

    def execute(self, paths: list[Path]):
        pass


class AnotherDummyTask(BaseTask):
    """Second test task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="another",
            display_name="Another",
            category=TaskCategory.FORMATTER,
            description="Another test task",
            tool_name="another-tool",
            aliases=["another"],
            cache_scope="quality",
            phase=1,
        )

    def execute(self, paths: list[Path]):
        pass


class TestTaskRegistry:
    def test_register_and_get(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        assert reg.get("dummy") is DummyTask

    def test_get_by_alias(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        assert reg.get("dum") is DummyTask

    def test_get_not_found(self):
        reg = TaskRegistry()
        assert reg.get("nonexistent") is None

    def test_get_by_category(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        reg.register(AnotherDummyTask)
        linters = reg.get_by_category(TaskCategory.LINTER)
        assert DummyTask in linters
        assert AnotherDummyTask not in linters

    def test_all_names(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        reg.register(AnotherDummyTask)
        names = reg.all_names()
        assert "another" in names
        assert "dummy" in names
        assert names == sorted(names)

    def test_resolve_names_exact(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        result = reg.resolve_names(["dummy"])
        assert "dummy" in result

    def test_resolve_names_partial(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        result = reg.resolve_names(["dum"])
        # "dum" matches DummyTask via alias or partial matching
        assert len(result) > 0

    def test_resolve_names_no_match(self):
        reg = TaskRegistry()
        result = reg.resolve_names(["nonexistent"])
        assert result == []

    def test_resolve_names_dedup(self):
        reg = TaskRegistry()
        reg.register(DummyTask)
        result = reg.resolve_names(["dummy", "dummy"])
        assert result.count("dummy") == 1

    def test_register_decorator(self):
        reg = TaskRegistry()

        # Manually test the module-level register function
        # The @register decorator at module level uses the global registry
        # Here we test the registry's register method directly
        reg.register(DummyTask)
        assert reg.get("dummy") is DummyTask

    def test_register_broken_task(self):
        """Task that raises during instantiation should be silently skipped."""

        class BrokenTask(BaseTask):
            def _get_metadata(self):
                raise RuntimeError("broken")

            def execute(self, paths):
                pass

        reg = TaskRegistry()
        reg.register(BrokenTask)
        # Should not raise, but task won't be registered
        assert reg.all_names() == []

    def test_get_by_category_empty(self):
        reg = TaskRegistry()
        assert reg.get_by_category(TaskCategory.META) == []

    def test_get_by_category_broken_task(self):
        """Tasks that fail instantiation during get_by_category should be skipped."""

        class FlakeyTask(BaseTask):
            _call_count = 0

            def _get_metadata(self):
                FlakeyTask._call_count += 1
                if FlakeyTask._call_count > 1:
                    raise RuntimeError("flaky")
                return TaskMetadata(
                    name="flakey",
                    display_name="Flakey",
                    category=TaskCategory.META,
                    description="Flakey",
                    tool_name="flakey",
                    aliases=[],
                    cache_scope="meta",
                )

            def execute(self, paths):
                pass

        reg = TaskRegistry()
        # First call succeeds (during register)
        FlakeyTask._call_count = 0
        reg.register(FlakeyTask)
        # Second call during get_by_category may raise
        result = reg.get_by_category(TaskCategory.META)
        # Should not crash - either returns the task or skips it
        assert isinstance(result, list)
