"""Linter tasks for py-smart-verify."""

import contextlib
from pathlib import Path

from py_smart_verify.models import Issue, StepResult, StepStatus
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import register


@register
class Flake8Task(BaseTask):
    """Flake8 linting task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="flake8",
            display_name="Flake8",
            category=TaskCategory.LINTER,
            description="Lint with Flake8",
            tool_name="flake8",
            aliases=["flake8"],
            cache_scope="quality",
            phase=1,
            optimized=False,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Flake8."""
        if not self.is_available():
            return self._build_skipped("Flake8 not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "flake8.log"
        cmd = ["flake8", "--quiet"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        issues = self._parse_flake8_output(output)
        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
            issues=issues,
        )

    def _parse_flake8_output(self, output: str) -> list[Issue]:
        """Parse Flake8 output into Issues."""
        issues = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            # flake8 format: file.py:line:col: code message
            parts = line.split(":", 3)
            if len(parts) >= 4:
                with contextlib.suppress(ValueError):
                    issues.append(
                        Issue(
                            file=parts[0],
                            line=int(parts[1]),
                            col=int(parts[2]),
                            type="error",
                            message=parts[3].strip(),
                            source_task="flake8",
                        )
                    )
        return issues


@register
class PyflakesTask(BaseTask):
    """Pyflakes linting task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="pyflakes",
            display_name="Pyflakes",
            category=TaskCategory.LINTER,
            description="Lint with Pyflakes",
            tool_name="pyflakes",
            aliases=["pyflakes"],
            cache_scope="quality",
            phase=1,
            optimized=False,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Pyflakes."""
        if not self.is_available():
            return self._build_skipped("Pyflakes not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "pyflakes.log"
        # Pyflakes accepts directories or files
        cmd = ["pyflakes"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        issues = self._parse_pyflakes_output(output)
        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
            issues=issues,
        )

    def _parse_pyflakes_output(self, output: str) -> list[Issue]:
        """Parse Pyflakes output into Issues."""
        issues = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            # pyflakes format: file.py:line: message
            parts = line.split(":", 2)
            if len(parts) >= 3:
                with contextlib.suppress(ValueError):
                    issues.append(
                        Issue(
                            file=parts[0],
                            line=int(parts[1]),
                            type="warning",
                            message=parts[2].strip(),
                            source_task="pyflakes",
                        )
                    )
        return issues


@register
class RuffLintTask(BaseTask):
    """Ruff lint task - replaces Flake8 and Pyflakes."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="ruff-lint",
            display_name="Ruff Lint",
            category=TaskCategory.LINTER,
            description="Lint with Ruff",
            tool_name="ruff",
            aliases=["ruff-lint"],
            cache_scope="quality",
            phase=1,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Ruff lint."""
        if not self.is_available():
            return self._build_skipped("Ruff not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "ruff-lint.log"
        cmd = ["ruff", "check", "--quiet"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        issues = self._parse_ruff_output(output)
        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
            issues=issues,
        )

    def _parse_ruff_output(self, output: str) -> list[Issue]:
        """Parse Ruff output into Issues."""
        issues = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            # ruff format: file.py:line:col: code message
            parts = line.split(":", 3)
            if len(parts) >= 4:
                with contextlib.suppress(ValueError):
                    issues.append(
                        Issue(
                            file=parts[0],
                            line=int(parts[1]),
                            col=int(parts[2]),
                            type="error",
                            message=parts[3].strip(),
                            source_task="ruff-lint",
                        )
                    )
        return issues
