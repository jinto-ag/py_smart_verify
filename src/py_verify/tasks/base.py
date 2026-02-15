"""Base task classes for py-verify."""

import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from py_verify.models import Issue, StepResult, StepStatus

if TYPE_CHECKING:
    from py_verify.config import VerifyConfig


class TaskCategory(StrEnum):
    """Task categories."""

    FORMATTER = "formatter"
    LINTER = "linter"
    TYPE_CHECKER = "type_checker"
    ANALYZER = "analyzer"
    TESTING = "testing"
    COMPOSITE = "composite"
    META = "meta"


@dataclass
class TaskMetadata:
    """Metadata about a task."""

    name: str
    display_name: str
    category: TaskCategory
    description: str
    tool_name: str  # e.g., "black", "mypy"
    aliases: list[str]
    cache_scope: str  # "quality", "unit", "e2e"
    auto_fix: bool = False
    phase: int = 0  # execution phase


class BaseTask(ABC):
    """Abstract base class for all verification tasks."""

    def __init__(self, config: "VerifyConfig") -> None:
        """Initialize task with config."""
        self.config = config
        self.metadata = self._get_metadata()

    @abstractmethod
    def _get_metadata(self) -> TaskMetadata:
        """Get task metadata. Must be overridden by subclasses."""
        pass

    @abstractmethod
    def execute(self, paths: list[Path]) -> StepResult:
        """Execute the task. Must be overridden by subclasses."""
        pass

    def is_available(self) -> bool:
        """Check if the task's tool is available."""
        return shutil.which(self.metadata.tool_name) is not None

    def _run_subprocess(
        self,
        cmd: list[str],
        log_path: Path,
        allow_failure: bool = False,
    ) -> tuple[int, str]:
        """Run a subprocess command and log output."""
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(log_path, "w") as log_file:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                log_file.write(result.stdout)
                if result.stderr:
                    log_file.write(f"\nSTDERR:\n{result.stderr}")

            if result.returncode != 0 and not allow_failure:
                return result.returncode, result.stdout + result.stderr
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            log_path.write_text("Command timed out after 300 seconds")
            return 1, "Timeout"
        except Exception as e:
            log_path.write_text(str(e))
            return 1, str(e)

    def _build_result(
        self,
        status: StepStatus,
        exit_code: int = 0,
        command: str | None = None,
        log_path: Path | None = None,
        output: str = "",
        issues: list[Issue] | None = None,
    ) -> StepResult:
        """Build a StepResult."""
        now = datetime.now().timestamp()
        return StepResult(
            name=self.metadata.display_name,
            status=status,
            start_epoch=now - 0.1,  # Approximate
            end_epoch=now,
            exit_code=exit_code,
            command=command,
            log_path=log_path,
            issues=issues or [],
        )

    def _build_skipped(self, reason: str = "Not available") -> StepResult:
        """Build a skipped StepResult."""
        return self._build_result(StepStatus.SKIPPED)
