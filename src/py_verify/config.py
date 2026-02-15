"""Configuration models for py-verify."""

from enum import IntEnum, StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Severity(IntEnum):
    """Issue severity levels."""

    CRITICAL = 1
    ERROR = 2
    WARNING = 3
    NOTE = 4
    INFO = 5


class RunMode(StrEnum):
    """Execution mode for running tasks."""

    FAST_FAIL = "fast-fail"
    CONTINUE = "continue"


class VerifyConfig(BaseModel):
    """Configuration for py-verify runner."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Core execution
    tasks: list[str] = Field(default_factory=list, description="Tasks to run")
    tools_filter: list[str] = Field(default_factory=list, description="Filter to specific tools")
    paths: list[str] = Field(default_factory=list, description="Paths to verify")

    # Behavior flags
    skip_tests: bool = Field(default=False, description="Skip test execution")
    no_cache: bool = Field(default=False, description="Disable caching")
    include_tests: bool = Field(default=False, description="Include test files in checks")
    ignore_warnings: bool = Field(default=False, description="Ignore warnings")
    min_severity: Severity = Field(
        default=Severity.INFO, description="Minimum severity level to report"
    )
    run_mode: RunMode = Field(
        default=RunMode.FAST_FAIL, description="Run mode (fast-fail or continue)"
    )

    # Smart test options (py-smart-test integration)
    full_tests: bool = Field(
        default=False,
        description="Run all tests with smart prioritization (--smart-first)",
    )
    since: str = Field(default="main", description="Git ref for smart test diff (default: main)")
    staged: bool = Field(default=False, description="Use only staged changes for smart tests")

    # Output and verbosity
    verbose: bool = Field(default=False, description="Verbose output")
    json_mode: bool = Field(
        default=False, description="Output JSON to stdout, suppress Rich output"
    )
    upgrade_deps: bool = Field(default=False, description="Upgrade tool dependencies")

    # Paths and directories
    project_root: Path = Field(default_factory=Path.cwd, description="Project root")
    cache_dir: Path = Field(
        default_factory=lambda: Path.cwd() / ".py_verify" / "cache",
        description="Cache directory",
    )
    log_dir: Path = Field(
        default_factory=lambda: Path.cwd() / ".py_verify" / "logs",
        description="Log directory",
    )

    def __str__(self) -> str:
        """String representation."""
        return f"VerifyConfig(tasks={self.tasks}, paths={self.paths})"
