"""Path discovery for py-verify."""

from pathlib import Path
from typing import Optional


class PathDiscovery:
    """Discovers Python files and paths in a project."""

    # Common source directories to check
    COMMON_SRC_DIRS = ["src", "lib", "app", "scripts"]

    def __init__(self, project_root: Path = Path.cwd()) -> None:
        """Initialize path discovery."""
        self.project_root = project_root

    def resolve_paths(self, user_paths: list[str]) -> list[Path]:
        """Resolve paths with priority: user > auto-detected > fallback."""
        if user_paths:
            return [self.project_root / p for p in user_paths]

        # Try to auto-detect common source directories
        auto_paths = self._auto_detect_paths()
        if auto_paths:
            return auto_paths

        # Fallback to current directory
        return [self.project_root]

    def _auto_detect_paths(self) -> list[Path]:
        """Auto-detect common source directories."""
        detected = []
        for dir_name in self.COMMON_SRC_DIRS:
            path = self.project_root / dir_name
            if path.is_dir():
                detected.append(path)

        # Also check for main.py at project root
        if (self.project_root / "main.py").exists():
            detected.insert(0, self.project_root)

        return detected

    def find_python_files(
        self,
        paths: list[Path],
        scope: str = "all",
        exclude_dirs: Optional[list[str]] = None,
    ) -> list[Path]:
        """Find Python files in paths with optional scope filtering."""
        if exclude_dirs is None:
            exclude_dirs = [
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                "dist",
                "build",
            ]

        python_files = []

        for path in paths:
            if not path.exists():
                continue

            if path.is_file() and path.suffix == ".py":
                if self._matches_scope(path, scope):
                    python_files.append(path)
            elif path.is_dir():
                for py_file in path.rglob("*.py"):
                    # Skip excluded directories
                    if any(excluded in py_file.parts for excluded in exclude_dirs):
                        continue
                    if self._matches_scope(py_file, scope):
                        python_files.append(py_file)

        return sorted(set(python_files))

    def _matches_scope(self, file_path: Path, scope: str) -> bool:
        """Check if file matches the scope."""
        if scope == "all":
            return True

        rel_path = file_path.relative_to(self.project_root)
        parts = rel_path.parts

        if scope == "quality":
            # Exclude test files from quality checks
            return "test" not in parts[0].lower()
        elif scope == "unit":
            # Only test files, exclude e2e
            return "test" in parts[0].lower() and "e2e" not in str(file_path)
        elif scope == "e2e":
            # Only e2e test files
            return "e2e" in str(file_path).lower()

        return True
