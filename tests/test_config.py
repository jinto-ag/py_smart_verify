"""Tests for py_verify.config."""

from pathlib import Path

from py_verify.config import RunMode, Severity, VerifyConfig


# --- Severity enum ---


def test_severity_values():
    assert Severity.CRITICAL == 1
    assert Severity.ERROR == 2
    assert Severity.WARNING == 3
    assert Severity.NOTE == 4
    assert Severity.INFO == 5


def test_severity_ordering():
    assert Severity.CRITICAL < Severity.INFO


# --- RunMode enum ---


def test_run_mode_values():
    assert RunMode.FAST_FAIL.value == "fast-fail"
    assert RunMode.CONTINUE.value == "continue"


# --- VerifyConfig ---


def test_config_defaults():
    config = VerifyConfig()
    assert config.tasks == []
    assert config.tools_filter == []
    assert config.paths == []
    assert config.skip_tests is False
    assert config.no_cache is False
    assert config.include_tests is False
    assert config.ignore_warnings is False
    assert config.min_severity == Severity.INFO
    assert config.run_mode == RunMode.FAST_FAIL
    assert config.full_tests is False
    assert config.since == "main"
    assert config.staged is False
    assert config.verbose is False
    assert config.upgrade_deps is False


def test_config_custom_values(tmp_path: Path):
    config = VerifyConfig(
        tasks=["ruff", "mypy"],
        tools_filter=["ruff"],
        paths=["src"],
        skip_tests=True,
        no_cache=True,
        include_tests=True,
        ignore_warnings=True,
        min_severity=Severity.CRITICAL,
        run_mode=RunMode.CONTINUE,
        full_tests=True,
        since="develop",
        staged=True,
        verbose=True,
        upgrade_deps=True,
        project_root=tmp_path,
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
    )
    assert config.tasks == ["ruff", "mypy"]
    assert config.skip_tests is True
    assert config.run_mode == RunMode.CONTINUE
    assert config.min_severity == Severity.CRITICAL
    assert config.project_root == tmp_path


def test_config_str(tmp_path: Path):
    config = VerifyConfig(
        tasks=["quality"],
        paths=["src"],
        project_root=tmp_path,
    )
    s = str(config)
    assert "quality" in s
    assert "src" in s


def test_config_default_paths():
    config = VerifyConfig()
    assert isinstance(config.project_root, Path)
    assert isinstance(config.cache_dir, Path)
    assert isinstance(config.log_dir, Path)
