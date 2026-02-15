"""Tests for py_verify.cache."""

from pathlib import Path

from py_verify.cache import CacheManager


class TestCacheManager:
    def test_init_creates_directory(self, tmp_path: Path):
        cache_dir = tmp_path / "cache"
        assert not cache_dir.exists()
        _cm = CacheManager(cache_dir)
        assert cache_dir.exists()

    # --- compute_hash ---

    def test_compute_hash_deterministic(self, tmp_path: Path):
        cache_dir = tmp_path / "cache"
        cm = CacheManager(cache_dir)
        f = tmp_path / "a.py"
        f.write_text("hello")

        h1 = cm.compute_hash("q", [f], {"ruff": "1.0"})
        h2 = cm.compute_hash("q", [f], {"ruff": "1.0"})
        assert h1 == h2

    def test_compute_hash_different_content(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        f = tmp_path / "a.py"

        f.write_text("hello")
        h1 = cm.compute_hash("q", [f], {})

        f.write_text("world")
        h2 = cm.compute_hash("q", [f], {})
        assert h1 != h2

    def test_compute_hash_tool_versions_matter(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        f = tmp_path / "a.py"
        f.write_text("x")

        h1 = cm.compute_hash("q", [f], {"ruff": "1.0"})
        h2 = cm.compute_hash("q", [f], {"ruff": "2.0"})
        assert h1 != h2

    def test_compute_hash_nonexistent_file_skipped(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        missing = tmp_path / "missing.py"
        # Should not raise
        h = cm.compute_hash("q", [missing], {})
        assert isinstance(h, str)

    def test_compute_hash_empty_inputs(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        h = cm.compute_hash("q", [], {})
        assert isinstance(h, str) and len(h) == 64

    def test_compute_hash_sorted_files(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        a.write_text("a")
        b.write_text("b")

        h1 = cm.compute_hash("q", [a, b], {})
        h2 = cm.compute_hash("q", [b, a], {})
        assert h1 == h2

    # --- is_cached ---

    def test_is_cached_true(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        cm.mark_ok("quality", 1.5)
        assert cm.is_cached("quality")

    def test_is_cached_false(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        assert not cm.is_cached("quality")

    # --- mark_ok ---

    def test_mark_ok_creates_files(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        cm.mark_ok("unit", 3.14)

        assert (tmp_path / "cache" / ".unit.ok").exists()
        assert (tmp_path / "cache" / ".unit.time").read_text() == "3.14"

    # --- get_last_duration ---

    def test_get_last_duration_exists(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        cm.mark_ok("scope", 2.5)
        assert cm.get_last_duration("scope") == 2.5

    def test_get_last_duration_not_exists(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        assert cm.get_last_duration("scope") is None

    def test_get_last_duration_invalid_content(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        (tmp_path / "cache" / ".scope.time").write_text("bad")
        assert cm.get_last_duration("scope") is None

    # --- invalidate ---

    def test_invalidate_removes_files(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        cm.mark_ok("scope", 1.0)
        cm.save_hash("scope", "abc123")
        cm.invalidate("scope")
        assert not (tmp_path / "cache" / ".scope.ok").exists()
        assert not (tmp_path / "cache" / ".scope.time").exists()
        assert not (tmp_path / "cache" / ".scope.hash").exists()

    def test_invalidate_no_files(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        cm.invalidate("scope")  # should not raise

    # --- save_hash / get_saved_hash ---

    def test_save_hash_and_get(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        cm.save_hash("quality", "abc123")
        assert cm.get_saved_hash("quality") == "abc123"

    def test_get_saved_hash_not_exists(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        assert cm.get_saved_hash("quality") is None

    def test_get_saved_hash_strips_whitespace(self, tmp_path: Path):
        cm = CacheManager(tmp_path / "cache")
        (tmp_path / "cache" / ".quality.hash").write_text("  abc  \n")
        assert cm.get_saved_hash("quality") == "abc"

    def test_get_saved_hash_oserror(self, tmp_path: Path, monkeypatch):
        cm = CacheManager(tmp_path / "cache")
        hash_file = tmp_path / "cache" / ".quality.hash"
        hash_file.write_text("abc123")

        # Make read_text raise OSError
        def broken_read(*args, **kwargs):
            raise OSError("permission denied")

        monkeypatch.setattr(type(hash_file), "read_text", broken_read)
        assert cm.get_saved_hash("quality") is None
