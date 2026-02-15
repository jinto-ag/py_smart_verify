"""Task registry for py-smart-verify."""

# Import all task modules at module level to trigger @register decorators.
# No circular dependency: task modules import from py_smart_verify.tasks.registry.
from py_smart_verify.tasks import (
    analyzers,
    formatters,
    linters,
    quality,
    self_test,
    testing,
    type_checkers,
)
from py_smart_verify.tasks.registry import TaskRegistry, register, task_registry

__all__ = [
    "TaskRegistry",
    "analyzers",
    "formatters",
    "linters",
    "quality",
    "register",
    "self_test",
    "task_registry",
    "testing",
    "type_checkers",
]
