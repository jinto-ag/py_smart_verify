"""Self-test task for py-smart-verify."""

from pathlib import Path

from py_smart_verify.models import StepResult, StepStatus
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import register, task_registry


@register
class SelfTestTask(BaseTask):
    """Self-test task that validates py-smart-verify itself."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="self-test",
            display_name="Self-Test",
            category=TaskCategory.META,
            description="Validate py-smart-verify configuration and registry",
            tool_name="python",
            aliases=["self-test"],
            cache_scope="meta",
            phase=0,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Run self-tests."""
        log_path = self.config.log_dir / "self-test.log"
        tests = []

        # Test 1: Registry completeness
        all_tasks = task_registry.all_names()
        test1 = {
            "name": "Task Registry",
            "passed": len(all_tasks) > 0,
            "message": f"Found {len(all_tasks)} registered tasks",
        }
        tests.append(test1)

        # Test 2: Config validation
        test2 = {
            "name": "Config Validation",
            "passed": hasattr(self.config, "project_root"),
            "message": "Config has required fields",
        }
        tests.append(test2)

        # Test 3: Cache directory
        cache_ok = self.config.cache_dir.exists() or self.config.cache_dir.parent.exists()
        test3 = {
            "name": "Cache Directory",
            "passed": cache_ok,
            "message": f"Cache dir: {self.config.cache_dir}",
        }
        tests.append(test3)

        # Test 4: Log directory
        log_ok = self.config.log_dir.exists() or self.config.log_dir.parent.exists()
        test4 = {
            "name": "Log Directory",
            "passed": log_ok,
            "message": f"Log dir: {self.config.log_dir}",
        }
        tests.append(test4)

        # Write test results
        results = []
        for test in tests:
            status = "PASS" if test["passed"] else "FAIL"
            results.append(f"{status} {test['name']}: {test['message']}")

        log_path.write_text("\n".join(results))

        all_passed = all(t["passed"] for t in tests)
        status = StepStatus.SUCCESS if all_passed else StepStatus.FAILED

        return self._build_result(
            status=status,
            exit_code=0 if all_passed else 1,
            command="py-smart-verify self-test",
            log_path=log_path,
            output="\n".join(results),
        )
