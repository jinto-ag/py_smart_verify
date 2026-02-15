"""VerifyRunner orchestrator for py-verify."""

import uuid
from datetime import datetime
from pathlib import Path

from py_verify.cache import CacheManager
from py_verify.config import VerifyConfig
from py_verify.console import (
    console,
    print_banner,
    print_run_summary,
    print_step_result,
    print_step_start,
)
from py_verify.discovery import PathDiscovery
from py_verify.models import RunResult, StepStatus
from py_verify.tasks import task_registry
from py_verify.tasks.quality import QualityCompositeTask
from py_verify.venv import VenvManager


class VerifyRunner:
    """Orchestrator for running verification tasks."""

    def __init__(self, config: VerifyConfig) -> None:
        """Initialize runner."""
        self.config = config
        self.result = RunResult(
            run_id=str(uuid.uuid4()),
            started_at=datetime.now().timestamp(),
        )
        self.discovery = PathDiscovery(config.project_root)
        self.venv_manager = VenvManager(config.project_root)
        self.cache_manager = CacheManager(config.cache_dir)

    def run(self) -> int:
        """Run verification. Returns exit code."""
        try:
            if not self.config.json_mode:
                print_banner()

            # Setup
            self._setup()

            # Resolve paths
            paths = self.discovery.resolve_paths(self.config.paths)
            py_files = self.discovery.find_python_files(paths, scope="quality")

            if not py_files and not self.config.skip_tests and not self.config.json_mode:
                console.print("[yellow]No Python files found[/yellow]")

            # Resolve tasks
            task_names = self._resolve_tasks()

            if not task_names:
                if not self.config.json_mode:
                    console.print("[yellow]No tasks to run[/yellow]")
                return 0

            # Execute tasks
            for task_name in task_names:
                self._execute_task(task_name, py_files)

            # Teardown
            self._teardown()

            return 0 if self.result.status == StepStatus.SUCCESS else 1

        except Exception as e:
            if not self.config.json_mode:
                console.print(f"[error]Error: {e}[/error]")
            self.result.mark_failed()
            return 1

    def run_and_get_result(self) -> tuple[int, RunResult]:
        """Run verification, returning both exit code and structured result."""
        exit_code = self.run()
        return exit_code, self.result

    def _setup(self) -> None:
        """Setup verification environment."""
        # Create .py_verify directory structure
        (self.config.project_root / ".py_verify").mkdir(exist_ok=True)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitignore
        self._ensure_gitignore()

        # Ensure tool configs exist
        self._ensure_configs()

    def _ensure_gitignore(self) -> None:
        """Create .py_verify/.gitignore"""
        gitignore_path = self.config.project_root / ".py_verify" / ".gitignore"
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text("*\n!.gitignore\n")

    def _ensure_configs(self) -> None:
        """Create default tool configs if missing."""
        # These would be created as needed by individual tasks
        pass

    def _resolve_tasks(self) -> list[str]:
        """Resolve task names, expanding composites."""
        task_names = self.config.tasks or ["quality", "tests"]

        resolved = []
        for name in task_names:
            if name == "quality":
                # Expand quality composite
                try:
                    quality_task = QualityCompositeTask(VerifyConfig())
                    resolved.extend(quality_task.get_subtasks())
                except Exception:
                    resolved.append(name)
            elif name == "tests":
                # Expand tests - use smart by default, or full if --full-tests
                if self.config.full_tests:
                    resolved.extend(["full-tests", "full-e2e-tests"])
                else:
                    resolved.extend(["tests", "e2e-tests"])
            else:
                resolved.append(name)

        return resolved

    def _execute_task(self, task_name: str, paths: list[Path]) -> None:
        """Execute a single task."""
        task_class = task_registry.get(task_name)
        if not task_class:
            if not self.config.json_mode:
                console.print(f"[yellow]Task not found: {task_name}[/yellow]")
            return

        # Instantiate task
        task = task_class(self.config)
        if not self.config.json_mode:
            print_step_start(task.metadata.display_name)

        # Check if task is available
        if not task.is_available():
            if not self.config.json_mode:
                console.print(f"[yellow]  Tool not available: {task.metadata.tool_name}[/yellow]")
            return

        # Check cache
        if (
            not self.config.no_cache
            and task.metadata.cache_scope
            and self.cache_manager.is_cached(task.metadata.cache_scope)
        ):
            duration = self.cache_manager.get_last_duration(task.metadata.cache_scope) or 0
            if not self.config.json_mode:
                console.print(f"[cyan]  Cache hit ({duration:.2f}s)[/cyan]")
            return

        # Execute task
        result = task.execute(paths)
        if not self.config.json_mode:
            print_step_result(result)
        self.result.add_step(result)

        # Update run result JSON after each step
        json_path = self.config.project_root / ".py_verify" / "last_run.json"
        self.result.to_json_file(json_path)

        # Handle fast-fail mode
        if result.status == StepStatus.FAILED and self.config.run_mode.value == "fast-fail":
            self.result.mark_failed()
            raise RuntimeError(f"Task {task_name} failed in fast-fail mode")

        # Mark cache if successful
        if (
            result.status in [StepStatus.SUCCESS, StepStatus.CACHED]
            and not self.config.no_cache
            and task.metadata.cache_scope
        ):
            self.cache_manager.mark_ok(task.metadata.cache_scope, result.duration)

    def _teardown(self) -> None:
        """Finalize verification run."""
        # Check if all steps succeeded
        failures = [s for s in self.result.steps if s.status == StepStatus.FAILED]

        if failures:
            self.result.mark_failed()
        else:
            self.result.mark_success()

        # Write final JSON
        json_path = self.config.project_root / ".py_verify" / "last_run.json"
        self.result.to_json_file(json_path)

        # Print summary
        if not self.config.json_mode:
            print_run_summary(self.result)
