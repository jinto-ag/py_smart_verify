"""Data models for py-smart-verify."""

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StepStatus(StrEnum):
    """Status of a verification step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
    SKIPPED = "skipped"


class Issue(BaseModel):
    """Represents an issue found during verification."""

    file: str = Field(description="File path")
    line: int | None = Field(default=None, description="Line number")
    col: int | None = Field(default=None, description="Column number")
    type: str = Field(description="Issue type (error, warning, note)")
    severity: int = Field(default=5, description="Severity level (1-5, 1=critical)")
    message: str = Field(description="Issue message")
    action: str | None = Field(default=None, description="Suggested action")
    source_task: str = Field(description="Task that found this issue")


class StepResult(BaseModel):
    """Result of executing a single verification step/task."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(description="Task name")
    status: StepStatus = Field(description="Execution status")
    start_epoch: float | None = Field(default=None, description="Start time (epoch)")
    end_epoch: float | None = Field(default=None, description="End time (epoch)")
    exit_code: int = Field(default=0, description="Exit code")
    log_path: Path | None = Field(default=None, description="Log file path")
    command: str | None = Field(default=None, description="Command executed")
    issues: list[Issue] = Field(default_factory=list, description="Issues found")

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if self.start_epoch and self.end_epoch:
            return self.end_epoch - self.start_epoch
        return 0.0

    def is_success(self) -> bool:
        """Check if step succeeded."""
        return self.status == StepStatus.SUCCESS or self.status == StepStatus.CACHED

    def dict(self, **kwargs: Any) -> dict[str, Any]:
        """Convert to dict, handling Path types."""
        data = super().model_dump(**kwargs)
        if data.get("log_path"):
            data["log_path"] = str(data["log_path"])
        return data


class DependencyNode(BaseModel):
    """A node in the dependency graph."""

    module: str = Field(description="Module name")
    file: str = Field(description="File path")
    imports: list[str] = Field(default_factory=list, description="Imported modules")
    imported_by: list[str] = Field(default_factory=list, description="Modules that import this")


class DependencyGraph(BaseModel):
    """Dependency graph for the project."""

    nodes: dict[str, DependencyNode] = Field(default_factory=dict)
    cycles: list[list[str]] = Field(default_factory=list, description="Cycle paths")


class RunResult(BaseModel):
    """Results of a complete verification run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str = Field(description="Unique run ID")
    started_at: float = Field(description="Start time (epoch)")
    finished_at: float | None = Field(default=None, description="End time (epoch)")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Overall status")
    steps: list[StepResult] = Field(default_factory=list, description="All steps")

    def add_step(self, step: StepResult) -> None:
        """Add a step result."""
        self.steps.append(step)

    def mark_success(self) -> None:
        """Mark run as successful."""
        self.status = StepStatus.SUCCESS
        self.finished_at = datetime.now().timestamp()

    def mark_failed(self) -> None:
        """Mark run as failed."""
        self.status = StepStatus.FAILED
        self.finished_at = datetime.now().timestamp()

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        if self.finished_at:
            return self.finished_at - self.started_at
        return 0.0

    def to_json_file(self, path: Path) -> None:
        """Write results to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            data = self.model_dump()
            # Handle any Path types
            for step in data.get("steps", []):
                if step.get("log_path"):
                    step["log_path"] = str(step["log_path"])
            json.dump(data, f, indent=2)

    @classmethod
    def from_json_file(cls, path: Path) -> "RunResult":
        """Load results from JSON file."""
        with open(path) as f:
            return cls.model_validate_json(f.read())
