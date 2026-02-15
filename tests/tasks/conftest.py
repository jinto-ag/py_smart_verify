"""Task-specific fixtures for py-verify tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture()
def task_config(tmp_path: Path):
    """Create a SimpleNamespace config suitable for tasks."""
    log_dir = tmp_path / ".py_verify" / "logs"
    log_dir.mkdir(parents=True)
    cache_dir = tmp_path / ".py_verify" / "cache"
    cache_dir.mkdir(parents=True)

    return SimpleNamespace(
        project_root=tmp_path,
        log_dir=log_dir,
        cache_dir=cache_dir,
        skip_tests=False,
        since="main",
        staged=False,
        verbose=False,
        full_tests=False,
    )


@pytest.fixture()
def task_paths(tmp_path: Path) -> list[Path]:
    """Create test Python files and return paths."""
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "module.py").write_text(
        '"""Module docstring."""\n'
        "\n"
        "\n"
        "def hello() -> str:\n"
        '    """Say hello."""\n'
        '    return "hi"\n'
    )
    return [tmp_path / "src"]
