"""Tests for py_smart_verify.venv."""

import shutil
import subprocess
from pathlib import Path

from py_smart_verify.venv import VenvManager


class TestDetectVenv:
    def test_dot_venv(self, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        vm = VenvManager(tmp_path)
        assert vm.detect_venv() == tmp_path / ".venv"

    def test_venv(self, tmp_path: Path):
        (tmp_path / "venv").mkdir()
        vm = VenvManager(tmp_path)
        assert vm.detect_venv() == tmp_path / "venv"

    def test_dot_venv_preferred(self, tmp_path: Path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / "venv").mkdir()
        vm = VenvManager(tmp_path)
        assert vm.detect_venv() == tmp_path / ".venv"

    def test_none(self, tmp_path: Path):
        vm = VenvManager(tmp_path)
        assert vm.detect_venv() is None


class TestDetectPackageManager:
    def test_uv(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/uv" if tool == "uv" else None)
        vm = VenvManager(tmp_path)
        assert vm.detect_package_manager() == "uv"

    def test_poetry(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        (tmp_path / "poetry.lock").write_text("")
        vm = VenvManager(tmp_path)
        assert vm.detect_package_manager() == "poetry"

    def test_pip_pyproject(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        (tmp_path / "pyproject.toml").write_text("")
        vm = VenvManager(tmp_path)
        assert vm.detect_package_manager() == "pip"

    def test_pip_requirements(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        (tmp_path / "requirements.txt").write_text("")
        vm = VenvManager(tmp_path)
        assert vm.detect_package_manager() == "pip"

    def test_fallback(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        vm = VenvManager(tmp_path)
        assert vm.detect_package_manager() == "pip"


class TestCheckToolAvailable:
    def test_available(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        vm = VenvManager(tmp_path)
        assert vm.check_tool_available("ruff")

    def test_not_available(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(shutil, "which", lambda tool: None)
        vm = VenvManager(tmp_path)
        assert not vm.check_tool_available("ruff")


class TestGetToolVersion:
    def test_success(self, tmp_path: Path, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="ruff 0.15.0\n", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.get_tool_version("ruff") == "ruff 0.15.0"

    def test_nonzero(self, tmp_path: Path, monkeypatch):
        def mock_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.get_tool_version("ruff") is None

    def test_timeout(self, tmp_path: Path, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 5)

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.get_tool_version("ruff") is None

    def test_file_not_found(self, tmp_path: Path, monkeypatch):
        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.get_tool_version("ruff") is None


class TestGetMissingTools:
    def test_none_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        vm = VenvManager(tmp_path)
        assert vm.get_missing_tools(["ruff", "mypy"]) == []

    def test_some_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            shutil, "which", lambda tool: "/usr/bin/" + tool if tool == "ruff" else None
        )
        vm = VenvManager(tmp_path)
        assert vm.get_missing_tools(["ruff", "mypy"]) == ["mypy"]


class TestInstallMissingTools:
    def test_nothing_to_install(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: "/usr/bin/" + tool)
        vm = VenvManager(tmp_path)
        assert vm.install_missing_tools(["ruff"]) == 0

    def test_uv_install(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)

        def mock_run(cmd, **kwargs):
            assert cmd[:3] == ["uv", "pip", "install"]
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.install_missing_tools(["mypy"], package_manager="uv") == 0

    def test_poetry_install(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)

        def mock_run(cmd, **kwargs):
            assert cmd[:4] == ["poetry", "add", "--group", "dev"]
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.install_missing_tools(["mypy"], package_manager="poetry") == 0

    def test_pip_install(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)

        def mock_run(cmd, **kwargs):
            assert cmd[:2] == ["pip", "install"]
            return subprocess.CompletedProcess(cmd, 0)

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.install_missing_tools(["mypy"], package_manager="pip") == 0

    def test_timeout(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)

        def mock_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 300)

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.install_missing_tools(["mypy"]) == 1

    def test_file_not_found(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda tool: None)

        def mock_run(cmd, **kwargs):
            raise FileNotFoundError()

        monkeypatch.setattr(subprocess, "run", mock_run)
        vm = VenvManager(tmp_path)
        assert vm.install_missing_tools(["mypy"]) == 1
