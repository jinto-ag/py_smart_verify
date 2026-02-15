"""Task registry for py-verify."""

from typing import TypeVar

from py_verify.tasks.base import BaseTask, TaskCategory

_T = TypeVar("_T", bound=BaseTask)


class TaskRegistry:
    """Registry for managing verification tasks."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._tasks: dict[str, type[BaseTask]] = {}
        self._aliases: dict[str, str] = {}

    def register(self, task_class: type[BaseTask]) -> None:
        """Register a task class."""
        # Create a dummy instance to get metadata
        dummy_config = type("DummyConfig", (), {})()
        try:
            instance = task_class(dummy_config)
            name = instance.metadata.name
            self._tasks[name] = task_class

            # Register aliases
            for alias in instance.metadata.aliases:
                self._aliases[alias] = name
        except Exception:
            # Skip if metadata can't be extracted
            pass

    def get(self, name: str) -> type[BaseTask] | None:
        """Get task class by name or alias."""
        # Check if it's an alias
        if name in self._aliases:
            name = self._aliases[name]
        return self._tasks.get(name)

    def get_by_category(self, category: TaskCategory) -> list[type[BaseTask]]:
        """Get all tasks of a category."""
        result = []
        for task_class in self._tasks.values():
            dummy_config = type("DummyConfig", (), {})()
            try:
                instance = task_class(dummy_config)
                if instance.metadata.category == category:
                    result.append(task_class)
            except Exception:
                pass
        return result

    def all_names(self) -> list[str]:
        """Get all registered task names."""
        return sorted(self._tasks.keys())

    def resolve_names(self, names: list[str]) -> list[str]:
        """Resolve task names, expanding composites like 'quality'."""
        resolved = []
        for name in names:
            task_class = self.get(name)
            if task_class:
                # For now, just return the name
                # 'quality' expansion will be handled by runner
                resolved.append(name)
            else:
                # Try to find partial matches
                matching = [n for n in self._tasks if name.lower() in n.lower()]
                resolved.extend(matching)
        return sorted(set(resolved))


# Global registry instance
task_registry = TaskRegistry()


def register(task_class: type[_T]) -> type[_T]:
    """Decorator to register a task."""
    task_registry.register(task_class)
    return task_class
