"""Shared fixtures for py-verify tests."""

from pathlib import Path

import pytest

from py_verify.config import VerifyConfig
from py_verify.models import Issue, StepResult, StepStatus


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    # Create src package
    pkg = tmp_path / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "module.py").write_text(
        '"""Module docstring."""\n\ndef hello() -> str:\n    """Greet."""\n    return "hi"\n'
    )

    # Create .git marker
    (tmp_path / ".git").mkdir()

    # Create pyproject.toml
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")

    # Create .py_verify dirs
    cache_dir = tmp_path / ".py_verify" / "cache"
    cache_dir.mkdir(parents=True)
    log_dir = tmp_path / ".py_verify" / "logs"
    log_dir.mkdir(parents=True)

    return tmp_path


@pytest.fixture()
def make_config(project_root: Path):
    """Factory for VerifyConfig with tmp_path directories."""

    def _make(**overrides):
        defaults = {
            "project_root": project_root,
            "cache_dir": project_root / ".py_verify" / "cache",
            "log_dir": project_root / ".py_verify" / "logs",
        }
        defaults.update(overrides)
        return VerifyConfig(**defaults)

    return _make


@pytest.fixture()
def sample_py_file(tmp_path: Path) -> Path:
    """Create a clean Python file with docstrings and type hints."""
    f = tmp_path / "clean.py"
    f.write_text(
        '"""Module docstring."""\n'
        "\n"
        "\n"
        "def greet(name: str) -> str:\n"
        '    """Return greeting."""\n'
        '    return f"Hello {name}"\n'
    )
    return f


@pytest.fixture()
def sample_py_file_with_issues(tmp_path: Path) -> Path:
    """Create a Python file with various issues."""
    lines = [
        '"""Module with issues."""\n',
        "\n",
        "MUTABLE_GLOBAL = []\n",
        "\n",
        "\n",
        "def bad_func(x):\n",
        "    import os\n",
        "    global MUTABLE_GLOBAL\n",
    ]
    # Add 55 lines to make a long function
    for i in range(50):
        lines.append(f"    _ = {i}\n")
    lines.append("    return x\n")

    f = tmp_path / "issues.py"
    f.write_text("".join(lines))
    return f


@pytest.fixture()
def make_step_result():
    """Factory for StepResult."""

    def _make(**overrides):
        defaults = {
            "name": "test-step",
            "status": StepStatus.SUCCESS,
            "exit_code": 0,
        }
        defaults.update(overrides)
        return StepResult(**defaults)

    return _make


@pytest.fixture()
def make_issue():
    """Factory for Issue."""

    def _make(**overrides):
        defaults = {
            "file": "test.py",
            "type": "error",
            "message": "test issue",
            "source_task": "test",
        }
        defaults.update(overrides)
        return Issue(**defaults)

    return _make
