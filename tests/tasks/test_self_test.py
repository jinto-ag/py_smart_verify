"""Tests for py_verify.tasks.self_test."""

from py_verify.models import StepStatus
from py_verify.tasks.base import TaskCategory
from py_verify.tasks.self_test import SelfTestTask


class TestSelfTestTask:
    def test_metadata(self, task_config):
        task = SelfTestTask(task_config)
        assert task.metadata.name == "self-test"
        assert task.metadata.category == TaskCategory.META

    def test_all_pass(self, task_config):
        task = SelfTestTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_log_written(self, task_config):
        task = SelfTestTask(task_config)
        task.execute([])
        log_path = task_config.log_dir / "self-test.log"
        assert log_path.exists()
        content = log_path.read_text()
        assert "Task Registry" in content
        assert "Config Validation" in content

    def test_result_output(self, task_config):
        task = SelfTestTask(task_config)
        result = task.execute([])
        assert result.command == "py-verify self-test"

    def test_cache_dir_missing(self, task_config):
        """Test when cache_dir doesn't exist but parent does."""
        import shutil

        shutil.rmtree(task_config.cache_dir)
        task = SelfTestTask(task_config)
        result = task.execute([])
        # Cache dir parent still exists, so this should still pass
        assert result.status == StepStatus.SUCCESS
