"""Caching system for py-verify."""

import hashlib
from pathlib import Path


class CacheManager:
    """Manages caching of verification scopes."""

    def __init__(self, cache_dir: Path) -> None:
        """Initialize cache manager."""
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def compute_hash(
        self, scope: str, file_paths: list[Path], tool_versions: dict[str, str]
    ) -> str:
        """Compute SHA256 hash of file contents + tool versions."""
        hasher = hashlib.sha256()

        # Hash file contents
        for file_path in sorted(file_paths):
            if file_path.exists():
                with open(file_path, "rb") as f:
                    hasher.update(f.read())

        # Hash tool versions
        for tool, version in sorted(tool_versions.items()):
            hasher.update(f"{tool}:{version}".encode())

        return hasher.hexdigest()

    def is_cached(self, scope: str) -> bool:
        """Check if scope is cached and valid."""
        marker = self.cache_dir / f".{scope}.ok"
        return marker.exists()

    def mark_ok(self, scope: str, duration: float) -> None:
        """Mark scope as successfully cached."""
        ok_file = self.cache_dir / f".{scope}.ok"
        time_file = self.cache_dir / f".{scope}.time"

        ok_file.write_text("ok")
        time_file.write_text(str(duration))

    def get_last_duration(self, scope: str) -> float | None:
        """Get duration of last successful run."""
        time_file = self.cache_dir / f".{scope}.time"
        if time_file.exists():
            try:
                return float(time_file.read_text())
            except (ValueError, OSError):
                return None
        return None

    def invalidate(self, scope: str) -> None:
        """Invalidate cache for a scope."""
        for pattern in [f".{scope}.ok", f".{scope}.time", f".{scope}.hash"]:
            file_path = self.cache_dir / pattern
            if file_path.exists():
                file_path.unlink()

    def save_hash(self, scope: str, file_hash: str) -> None:
        """Save hash for a scope."""
        hash_file = self.cache_dir / f".{scope}.hash"
        hash_file.write_text(file_hash)

    def get_saved_hash(self, scope: str) -> str | None:
        """Get saved hash for a scope."""
        hash_file = self.cache_dir / f".{scope}.hash"
        if hash_file.exists():
            try:
                return hash_file.read_text().strip()
            except OSError:
                return None
        return None
