"""Shared fixtures for e2e tests."""

from pathlib import Path

import pytest

from py_smart_verify.config import VerifyConfig


@pytest.fixture()
def e2e_project(tmp_path: Path) -> Path:
    """Create a realistic Python project for e2e testing."""
    # Source package
    pkg = tmp_path / "src" / "myapp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text('"""myapp package."""\n\n__version__ = "0.1.0"\n')
    (pkg / "core.py").write_text(
        '"""Core module."""\n'
        "\n"
        "from myapp.utils import add\n"
        "\n"
        "\n"
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        '    return f"Hello, {name}"\n'
        "\n"
        "\n"
        "def compute(a: int, b: int) -> int:\n"
        '    """Add two numbers."""\n'
        "    return add(a, b)\n"
    )
    (pkg / "utils.py").write_text(
        '"""Utility functions."""\n'
        "\n"
        "\n"
        "def add(a: int, b: int) -> int:\n"
        '    """Add two integers."""\n'
        "    return a + b\n"
        "\n"
        "\n"
        "def clamp(value: int, low: int, high: int) -> int:\n"
        '    """Clamp value to range."""\n'
        "    return max(low, min(high, value))\n"
    )

    # Git marker
    (tmp_path / ".git").mkdir()

    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "myapp"\n'
        'version = "0.1.0"\n'
        "\n"
        "[tool.ruff]\n"
        'target-version = "py311"\n'
        "line-length = 100\n"
    )

    # .py_smart_verify directories
    (tmp_path / ".py_smart_verify" / "cache").mkdir(parents=True)
    (tmp_path / ".py_smart_verify" / "logs").mkdir(parents=True)

    return tmp_path


@pytest.fixture()
def e2e_project_with_issues(e2e_project: Path) -> Path:
    """Add files with lint issues to the e2e project."""
    pkg = e2e_project / "src" / "myapp"
    (pkg / "bad.py").write_text(
        '"""Module with issues."""\n'
        "\n"
        "import os\n"
        "import sys\n"
        "\n"
        "\n"
        "def no_types(x):\n"
        "    y = 1\n"
        "    return x\n"
    )
    return e2e_project


@pytest.fixture()
def e2e_config(e2e_project: Path):
    """Factory for VerifyConfig pointing at the e2e project."""

    def _make(**overrides):
        defaults = {
            "project_root": e2e_project,
            "cache_dir": e2e_project / ".py_smart_verify" / "cache",
            "log_dir": e2e_project / ".py_smart_verify" / "logs",
            "no_cache": True,
            "json_mode": True,
        }
        defaults.update(overrides)
        return VerifyConfig(**defaults)

    return _make
