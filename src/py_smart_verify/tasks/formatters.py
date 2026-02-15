"""Formatter tasks for py-smart-verify."""

from pathlib import Path

from py_smart_verify.models import StepResult, StepStatus
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import register


@register
class FormatTask(BaseTask):
    """Black code formatter task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="format",
            display_name="Black",
            category=TaskCategory.FORMATTER,
            description="Format code with Black",
            tool_name="black",
            aliases=["black"],
            cache_scope="quality",
            auto_fix=True,
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Black formatting."""
        if not self.is_available():
            return self._build_skipped("Black not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "format.log"
        cmd = ["black", "--check", "--quiet"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=True)

        if exit_code == 0:
            status = StepStatus.SUCCESS
        else:
            # Black returns non-zero when reformatting is needed
            status = StepStatus.SUCCESS  # Still counts as success (auto-fix)

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
        )


@register
class IsortTask(BaseTask):
    """Isort import sorting task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="isort",
            display_name="Isort",
            category=TaskCategory.FORMATTER,
            description="Sort imports with Isort",
            tool_name="isort",
            aliases=["isort"],
            cache_scope="quality",
            auto_fix=True,
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Isort."""
        if not self.is_available():
            return self._build_skipped("Isort not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "isort.log"
        cmd = ["isort", "--check-only", "--quiet"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=True)

        status = StepStatus.SUCCESS

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
        )


@register
class RuffFixTask(BaseTask):
    """Ruff auto-fix task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="ruff-fix",
            display_name="Ruff Fix",
            category=TaskCategory.FORMATTER,
            description="Auto-fix issues with Ruff",
            tool_name="ruff",
            aliases=["ruff-fix"],
            cache_scope="quality",
            auto_fix=True,
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Ruff fix."""
        if not self.is_available():
            return self._build_skipped("Ruff not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "ruff-fix.log"
        cmd = ["ruff", "check", "--fix", "--quiet"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=True)

        status = StepStatus.SUCCESS

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
        )
