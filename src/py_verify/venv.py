"""Virtual environment and tool management."""

import shutil
import subprocess
from pathlib import Path


class VenvManager:
    """Manages virtual environment and tool availability."""

    def __init__(self, project_root: Path = Path.cwd()) -> None:  # noqa: B008
        """Initialize venv manager."""
        self.project_root = project_root

    def detect_venv(self) -> Path | None:
        """Detect virtual environment directory."""
        for venv_name in [".venv", "venv"]:
            venv_path = self.project_root / venv_name
            if venv_path.is_dir():
                return venv_path
        return None

    def detect_package_manager(self) -> str:
        """Detect package manager (uv > poetry > pip)."""
        # Check for uv
        if shutil.which("uv"):
            return "uv"
        # Check for poetry
        if (self.project_root / "poetry.lock").exists():
            return "poetry"
        # Check for pip (has pyproject.toml or requirements.txt)
        if (self.project_root / "pyproject.toml").exists() or (
            self.project_root / "requirements.txt"
        ).exists():
            return "pip"
        return "pip"  # Default fallback

    def check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH."""
        return shutil.which(tool) is not None

    def get_tool_version(self, tool: str) -> str | None:
        """Get tool version string."""
        try:
            result = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def get_missing_tools(self, tools: list[str]) -> list[str]:
        """Get list of missing tools."""
        return [tool for tool in tools if not self.check_tool_available(tool)]

    def install_missing_tools(self, tools: list[str], package_manager: str = "uv") -> int:
        """Install missing tools. Returns exit code."""
        missing = self.get_missing_tools(tools)
        if not missing:
            return 0

        if package_manager == "uv":
            cmd = ["uv", "pip", "install", *missing]
        elif package_manager == "poetry":
            cmd = ["poetry", "add", "--group", "dev", *missing]
        else:  # pip
            cmd = ["pip", "install", *missing]

        try:
            result = subprocess.run(cmd, timeout=300)
            return result.returncode
        except subprocess.TimeoutExpired:
            return 1
        except FileNotFoundError:
            return 1
