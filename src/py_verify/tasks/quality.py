"""Quality composite task for py-verify."""

from pathlib import Path

from py_verify.models import StepResult, StepStatus
from py_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_verify.tasks.registry import register, task_registry


@register
class QualityCompositeTask(BaseTask):
    """Composite task that orchestrates all quality checks in phases."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="quality",
            display_name="Quality Checks",
            category=TaskCategory.COMPOSITE,
            description=(
                "Run all quality checks (formatters, "
                "linters, type checkers, analyzers)"
            ),
            tool_name="python",
            aliases=["quality", "qa"],
            cache_scope="quality",
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute quality composite task.

        This is typically expanded by the runner, so this method is for
        informational purposes. The actual orchestration is in runner.py.
        """
        return self._build_result(
            status=StepStatus.SUCCESS,
            command="(quality composite - expanded by runner)",
        )

    def get_subtasks(self) -> list[str]:
        """Get list of subtasks to run in order."""
        # Ordered by phase: formatters (0), linters (1),
        # type-checkers (2), analyzers (3)
        subtasks = []

        # Get all formatters
        for task_class in task_registry.get_by_category(TaskCategory.FORMATTER):
            dummy_config = type("DummyConfig", (), {})()
            try:
                instance = task_class(dummy_config)
                subtasks.append((instance.metadata.phase, instance.metadata.name))
            except Exception:
                pass

        # Get all linters
        for task_class in task_registry.get_by_category(TaskCategory.LINTER):
            dummy_config = type("DummyConfig", (), {})()
            try:
                instance = task_class(dummy_config)
                subtasks.append((instance.metadata.phase, instance.metadata.name))
            except Exception:
                pass

        # Get all type checkers
        for task_class in task_registry.get_by_category(TaskCategory.TYPE_CHECKER):
            dummy_config = type("DummyConfig", (), {})()
            try:
                instance = task_class(dummy_config)
                subtasks.append((instance.metadata.phase, instance.metadata.name))
            except Exception:
                pass

        # Get all analyzers
        for task_class in task_registry.get_by_category(TaskCategory.ANALYZER):
            dummy_config = type("DummyConfig", (), {})()
            try:
                instance = task_class(dummy_config)
                subtasks.append((instance.metadata.phase, instance.metadata.name))
            except Exception:
                pass

        # Sort by phase, then by name
        subtasks.sort(key=lambda x: (x[0], x[1]))
        return [name for _, name in subtasks]
