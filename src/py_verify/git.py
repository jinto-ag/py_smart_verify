"""Git integration for py-verify."""

import subprocess
from pathlib import Path


class GitIntegration:
    """Manages Git operations for py-verify."""

    def __init__(self, project_root: Path = Path.cwd()) -> None:
        """Initialize Git integration."""
        self.project_root = project_root

    def is_git_repo(self) -> bool:
        """Check if project is a Git repository."""
        return (self.project_root / ".git").exists()

    def get_changed_files(
        self,
        base_ref: str = "main",
        include_staged: bool = True,
        include_unstaged: bool = True,
        include_untracked: bool = False,
    ) -> list[str]:
        """Get list of changed files."""
        if not self.is_git_repo():
            return []

        changed = set()

        # Get diff against base ref
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10,
            )
            if result.returncode == 0:
                changed.update(result.stdout.strip().split("\n"))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Get staged changes
        if include_staged:
            try:
                result = subprocess.run(
                    ["git", "diff", "--cached", "--name-only"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=10,
                )
                if result.returncode == 0:
                    changed.update(result.stdout.strip().split("\n"))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Get unstaged changes
        if include_unstaged:
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=10,
                )
                if result.returncode == 0:
                    changed.update(result.stdout.strip().split("\n"))
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        # Get untracked files
        if include_untracked:
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=10,
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if line.startswith("??"):
                            changed.add(line[3:].strip())
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return sorted([f for f in changed if f])

    def get_affected_modules(self, changed_files: list[str]) -> list[str]:
        """Map changed files to module names."""
        modules = set()
        for file_path in changed_files:
            if file_path.endswith(".py"):
                # Convert file path to module name
                # e.g., src/my_pkg/module.py -> my_pkg.module
                parts = Path(file_path).with_suffix("").parts
                # Skip common prefixes
                filtered = [p for p in parts if p not in ["src", "lib", "app", "tests"]]
                if filtered:
                    modules.add(".".join(filtered))
        return sorted(modules)

    def get_diff_stats(self, base_ref: str = "main") -> dict[str, int]:
        """Get diff statistics."""
        if not self.is_git_repo():
            return {"insertions": 0, "deletions": 0, "files_changed": 0}

        try:
            result = subprocess.run(
                ["git", "diff", "--stat", base_ref],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10,
            )
            if result.returncode == 0:
                # Simple parsing of git diff --stat output
                lines = result.stdout.strip().split("\n")
                stats = {
                    "insertions": 0,
                    "deletions": 0,
                    "files_changed": len(lines) - 1,
                }
                for line in lines[:-1]:
                    # Count + and - signs
                    if "+" in line:
                        stats["insertions"] += line.count("+")
                    if "-" in line:
                        stats["deletions"] += line.count("-")
                return stats
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return {"insertions": 0, "deletions": 0, "files_changed": 0}
