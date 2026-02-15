"""Tests for py_verify.tasks.__init__."""

from py_verify.tasks import TaskRegistry, register, task_registry


def test_task_registry_is_instance():
    assert isinstance(task_registry, TaskRegistry)


def test_register_is_callable():
    assert callable(register)


def test_all_names_populated():
    names = task_registry.all_names()
    assert len(names) > 0


def test_expected_names():
    names = task_registry.all_names()
    # Verify some known task names are registered
    expected = ["format", "flake8", "mypy", "quality"]
    for name in expected:
        assert name in names, f"{name} not in task registry"
