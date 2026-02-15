"""Testing tasks for py-smart-verify with py-smart-test integration."""

from pathlib import Path

from py_smart_verify.models import Issue, StepResult, StepStatus
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import register


@register
class SmartTestTask(BaseTask):
    """Smart test execution - runs only affected tests via py-smart-test."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="tests",
            display_name="Smart Tests",
            category=TaskCategory.TESTING,
            description="Run tests affected by changes (via py-smart-test)",
            tool_name="pytest",
            aliases=["tests", "unit-tests"],
            cache_scope="unit",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute smart tests using pytest --smart."""
        if not self.config.skip_tests:
            log_path = self.config.log_dir / "tests.log"

            # Build pytest command with py-smart-test plugin
            cmd = [
                "pytest",
                "--smart",  # Enable py-smart-test smart selection
                "--smart-working-tree",  # Use git working tree for changes
                "-q",  # Quiet mode
                "--maxfail=1",  # Stop after first failure
                "--disable-warnings",
                "--ignore=tests/e2e",  # Exclude E2E tests
            ]

            # Forward --since if provided
            if self.config.since and self.config.since != "main":
                cmd.extend(["--smart-since", self.config.since])

            # Forward --staged if provided
            if self.config.staged:
                cmd.append("--smart-staged")

            exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

            # Exit code 5 = no tests collected (e.g. --smart-staged with no staged changes)
            status = StepStatus.SUCCESS if exit_code in (0, 5) else StepStatus.FAILED
            issues = self._parse_pytest_output(output) if exit_code not in (0, 5) else []

            return self._build_result(
                status=status,
                exit_code=exit_code,
                command=" ".join(cmd),
                log_path=log_path,
                output=output,
                issues=issues,
            )
        else:
            return self._build_skipped("Tests skipped")

    def _parse_pytest_output(self, output: str) -> list[Issue]:
        """Parse pytest output for failed tests."""
        issues = []
        # Simple parsing - look for FAILED markers
        for line in output.split("\n"):
            if "FAILED" in line:
                issues.append(
                    Issue(
                        file="(test output)",
                        type="error",
                        message=line.strip(),
                        source_task="tests",
                    )
                )
        return issues[:5]  # Return first 5 issues


@register
class FullTestTask(BaseTask):
    """Full test execution with smart prioritization."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="full-tests",
            display_name="Full Tests (Smart)",
            category=TaskCategory.TESTING,
            description="Run all tests with smart prioritization",
            tool_name="pytest",
            aliases=["full-tests"],
            cache_scope="unit",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute full test suite with smart prioritization."""
        if not self.config.skip_tests:
            log_path = self.config.log_dir / "full-tests.log"

            # Build pytest command with --smart-first for prioritization
            cmd = [
                "pytest",
                "--smart-first",  # Run all tests but reorder with smart prioritization
                "-q",
                "--maxfail=1",
                "--disable-warnings",
                "--ignore=tests/e2e",
            ]

            # Forward --since if provided
            if self.config.since and self.config.since != "main":
                cmd.extend(["--smart-since", self.config.since])

            # Forward --staged if provided
            if self.config.staged:
                cmd.append("--smart-staged")

            exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

            # Exit code 5 = no tests collected
            status = StepStatus.SUCCESS if exit_code in (0, 5) else StepStatus.FAILED
            issues = self._parse_pytest_output(output) if exit_code not in (0, 5) else []

            return self._build_result(
                status=status,
                exit_code=exit_code,
                command=" ".join(cmd),
                log_path=log_path,
                output=output,
                issues=issues,
            )
        else:
            return self._build_skipped("Tests skipped")

    def _parse_pytest_output(self, output: str) -> list[Issue]:
        """Parse pytest output for failed tests."""
        issues = []
        for line in output.split("\n"):
            if "FAILED" in line:
                issues.append(
                    Issue(
                        file="(test output)",
                        type="error",
                        message=line.strip(),
                        source_task="tests",
                    )
                )
        return issues[:5]


@register
class E2ETestTask(BaseTask):
    """Smart E2E test execution."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="e2e-tests",
            display_name="Smart E2E Tests",
            category=TaskCategory.TESTING,
            description="Run E2E tests affected by changes",
            tool_name="pytest",
            aliases=["e2e-tests", "e2e"],
            cache_scope="e2e",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute smart E2E tests."""
        if not self.config.skip_tests:
            log_path = self.config.log_dir / "e2e-tests.log"

            cmd = [
                "pytest",
                "--smart",
                "--smart-working-tree",
                "-q",
                "--maxfail=1",
                "--disable-warnings",
                "tests/e2e",
            ]

            if self.config.since and self.config.since != "main":
                cmd.extend(["--smart-since", self.config.since])

            if self.config.staged:
                cmd.append("--smart-staged")

            exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

            # Exit code 5 = no tests collected
            status = StepStatus.SUCCESS if exit_code in (0, 5) else StepStatus.FAILED
            issues = self._parse_pytest_output(output) if exit_code not in (0, 5) else []

            return self._build_result(
                status=status,
                exit_code=exit_code,
                command=" ".join(cmd),
                log_path=log_path,
                output=output,
                issues=issues,
            )
        else:
            return self._build_skipped("Tests skipped")

    def _parse_pytest_output(self, output: str) -> list[Issue]:
        """Parse pytest output."""
        issues = []
        for line in output.split("\n"):
            if "FAILED" in line:
                issues.append(
                    Issue(
                        file="(test output)",
                        type="error",
                        message=line.strip(),
                        source_task="e2e-tests",
                    )
                )
        return issues[:5]


@register
class FullE2ETestTask(BaseTask):
    """Full E2E test execution with prioritization."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="full-e2e-tests",
            display_name="Full E2E Tests (Smart)",
            category=TaskCategory.TESTING,
            description="Run all E2E tests with smart prioritization",
            tool_name="pytest",
            aliases=["full-e2e-tests"],
            cache_scope="e2e",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute full E2E test suite with prioritization."""
        if not self.config.skip_tests:
            log_path = self.config.log_dir / "full-e2e-tests.log"

            cmd = [
                "pytest",
                "--smart-first",
                "-q",
                "--maxfail=1",
                "--disable-warnings",
                "tests/e2e",
            ]

            if self.config.since and self.config.since != "main":
                cmd.extend(["--smart-since", self.config.since])

            if self.config.staged:
                cmd.append("--smart-staged")

            exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

            # Exit code 5 = no tests collected
            status = StepStatus.SUCCESS if exit_code in (0, 5) else StepStatus.FAILED
            issues = self._parse_pytest_output(output) if exit_code not in (0, 5) else []

            return self._build_result(
                status=status,
                exit_code=exit_code,
                command=" ".join(cmd),
                log_path=log_path,
                output=output,
                issues=issues,
            )
        else:
            return self._build_skipped("Tests skipped")

    def _parse_pytest_output(self, output: str) -> list[Issue]:
        """Parse pytest output."""
        issues = []
        for line in output.split("\n"):
            if "FAILED" in line:
                issues.append(
                    Issue(
                        file="(test output)",
                        type="error",
                        message=line.strip(),
                        source_task="e2e-tests",
                    )
                )
        return issues[:5]


@register
class RegenerateGraphTask(BaseTask):
    """Regenerate dependency graph for py-smart-test."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="regen-graph",
            display_name="Regenerate Graph",
            category=TaskCategory.META,
            description="Regenerate py-smart-test dependency graph",
            tool_name="py-smart-test",
            aliases=["regen-graph", "regenerate-graph"],
            cache_scope="meta",
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Regenerate dependency graph."""
        log_path = self.config.log_dir / "regen-graph.log"

        cmd = ["py-smart-test-graph-gen"]  # Alias: pst-gen
        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
        )


@register
class AffectedTestsTask(BaseTask):
    """List affected tests without running them."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="affected",
            display_name="Affected Tests",
            category=TaskCategory.META,
            description="Show tests affected by changes",
            tool_name="py-smart-test",
            aliases=["affected", "affected-tests"],
            cache_scope="meta",
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """List affected tests."""
        log_path = self.config.log_dir / "affected.log"

        cmd = ["py-smart-test-affected", "--json"]  # Alias: pst-affected

        if self.config.since and self.config.since != "main":
            cmd.extend(["--base", self.config.since])

        if self.config.staged:
            cmd.append("--staged")

        exit_code, output = self._run_subprocess(cmd, log_path, allow_failure=False)

        status = StepStatus.SUCCESS if exit_code == 0 else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=exit_code,
            command=" ".join(cmd),
            log_path=log_path,
            output=output,
        )
