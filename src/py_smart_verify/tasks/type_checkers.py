"""Type checker tasks for py-smart-verify."""

import contextlib
from pathlib import Path

from py_smart_verify.models import Issue, StepResult, StepStatus
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import register


@register
class MypyTask(BaseTask):
    """Mypy type checking task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="mypy",
            display_name="Mypy",
            category=TaskCategory.TYPE_CHECKER,
            description="Type check with Mypy",
            tool_name="mypy",
            aliases=["mypy"],
            cache_scope="quality",
            phase=2,
            optimized=False,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Mypy."""
        if not self.is_available():
            return self._build_skipped("Mypy not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "mypy.log"
        cmd = ["mypy", "--quiet", "--ignore-missing-imports"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        issues = self._parse_mypy_output(output)
        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
            issues=issues,
        )

    def _parse_mypy_output(self, output: str) -> list[Issue]:
        """Parse Mypy output into Issues."""
        issues = []
        for line in output.strip().split("\n"):
            if not line or "error:" not in line:
                continue
            # mypy format: file.py:line:col: error: message
            parts = line.split(":", 4)
            if len(parts) >= 5:
                with contextlib.suppress(ValueError):
                    issues.append(
                        Issue(
                            file=parts[0],
                            line=int(parts[1]),
                            col=int(parts[2]),
                            type="error",
                            message=parts[4].strip(),
                            source_task="mypy",
                        )
                    )
        return issues


@register
class PyrightTask(BaseTask):
    """Pyright type checking task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="pyright",
            display_name="Pyright",
            category=TaskCategory.TYPE_CHECKER,
            description="Type check with Pyright",
            tool_name="pyright",
            aliases=["pyright"],
            cache_scope="quality",
            phase=2,
            optimized=False,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute Pyright."""
        if not self.is_available():
            return self._build_skipped("Pyright not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "pyright.log"
        cmd = ["pyright", "--level", "error"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        issues = self._parse_pyright_output(output)
        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
            issues=issues,
        )

    def _parse_pyright_output(self, output: str) -> list[Issue]:
        """Parse Pyright output into Issues."""
        issues = []
        for line in output.strip().split("\n"):
            if not line or "error:" not in line:
                continue
            # pyright format similar to mypy
            parts = line.split(":", 4)
            if len(parts) >= 5:
                with contextlib.suppress(ValueError):
                    issues.append(
                        Issue(
                            file=parts[0],
                            line=int(parts[1]),
                            col=int(parts[2]),
                            type="error",
                            message=parts[4].strip(),
                            source_task="pyright",
                        )
                    )
        return issues


@register
class BasedPyrightTask(BaseTask):
    """BasedPyright type checking task (stricter Pyright variant)."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="basedpyright",
            display_name="BasedPyright",
            category=TaskCategory.TYPE_CHECKER,
            description="Type check with BasedPyright",
            tool_name="basedpyright",
            aliases=["basedpyright", "pylance"],
            cache_scope="quality",
            phase=2,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute BasedPyright."""
        if not self.is_available():
            return self._build_skipped("BasedPyright not available")

        if not paths:
            paths = [self.config.project_root]

        log_path = self.config.log_dir / "basedpyright.log"
        cmd = ["basedpyright", "--level", "error"] + [str(p) for p in paths]

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        issues = self._parse_pyright_output(output)
        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
            issues=issues,
        )

    def _parse_pyright_output(self, output: str) -> list[Issue]:
        """Parse BasedPyright output into Issues."""
        issues = []
        for line in output.strip().split("\n"):
            if not line or "error:" not in line:
                continue
            parts = line.split(":", 4)
            if len(parts) >= 5:
                with contextlib.suppress(ValueError):
                    issues.append(
                        Issue(
                            file=parts[0],
                            line=int(parts[1]),
                            col=int(parts[2]),
                            type="error",
                            message=parts[4].strip(),
                            source_task="basedpyright",
                        )
                    )
        return issues
