"""Tests for py_smart_verify.discovery."""

from pathlib import Path

from py_smart_verify.discovery import PathDiscovery


class TestResolverPaths:
    def test_user_provided_paths(self, tmp_path: Path):
        disc = PathDiscovery(tmp_path)
        result = disc.resolve_paths(["src", "lib"])
        assert result == [tmp_path / "src", tmp_path / "lib"]

    def test_auto_detect_src(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        disc = PathDiscovery(tmp_path)
        result = disc.resolve_paths([])
        assert tmp_path / "src" in result

    def test_auto_detect_multiple(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "lib").mkdir()
        disc = PathDiscovery(tmp_path)
        result = disc.resolve_paths([])
        assert tmp_path / "src" in result
        assert tmp_path / "lib" in result

    def test_auto_detect_main_py(self, tmp_path: Path):
        (tmp_path / "main.py").write_text("x = 1\n")
        disc = PathDiscovery(tmp_path)
        result = disc.resolve_paths([])
        # main.py detection inserts project root at position 0
        assert tmp_path in result

    def test_fallback_to_project_root(self, tmp_path: Path):
        disc = PathDiscovery(tmp_path)
        result = disc.resolve_paths([])
        assert result == [tmp_path]


class TestFindPythonFiles:
    def test_single_file(self, tmp_path: Path):
        f = tmp_path / "a.py"
        f.write_text("x = 1")
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([f])
        assert result == [f]

    def test_directory(self, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("x = 1")
        (pkg / "b.py").write_text("y = 2")
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([pkg])
        assert len(result) == 2

    def test_nonexistent(self, tmp_path: Path):
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([tmp_path / "nope"])
        assert result == []

    def test_excludes_pycache(self, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text("x=1")
        pycache = pkg / "__pycache__"
        pycache.mkdir()
        (pycache / "mod.cpython-311.pyc.py").write_text("x=1")  # fake .py in pycache name
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([pkg])
        assert all("__pycache__" not in str(p) for p in result)

    def test_excludes_venv(self, tmp_path: Path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("x=1")
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([tmp_path])
        assert all(".venv" not in str(p) for p in result)

    def test_custom_excludes(self, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text("x=1")
        custom = tmp_path / "custom_dir"
        custom.mkdir()
        (custom / "x.py").write_text("x=1")
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([tmp_path], exclude_dirs=["custom_dir"])
        assert all("custom_dir" not in str(p) for p in result)

    def test_sorted_and_deduped(self, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "b.py").write_text("pass")
        (pkg / "a.py").write_text("pass")
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([pkg, pkg])  # duplicate path
        names = [p.name for p in result]
        assert names == sorted(names)
        assert len(names) == len(set(names))

    def test_non_py_ignored(self, tmp_path: Path):
        (tmp_path / "readme.md").write_text("hi")
        (tmp_path / "data.json").write_text("{}")
        disc = PathDiscovery(tmp_path)
        result = disc.find_python_files([tmp_path])
        assert result == []


class TestMatchesScope:
    def test_all_scope(self, project_root: Path):
        disc = PathDiscovery(project_root)
        f = project_root / "src" / "pkg" / "module.py"
        assert disc._matches_scope(f, "all")

    def test_quality_scope_excludes_tests(self, project_root: Path):
        disc = PathDiscovery(project_root)
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_x.py"
        test_file.write_text("pass")
        assert not disc._matches_scope(test_file, "quality")

    def test_quality_scope_includes_src(self, project_root: Path):
        disc = PathDiscovery(project_root)
        f = project_root / "src" / "pkg" / "module.py"
        assert disc._matches_scope(f, "quality")

    def test_unit_scope(self, project_root: Path):
        disc = PathDiscovery(project_root)
        tests_dir = project_root / "tests"
        tests_dir.mkdir()
        test_file = tests_dir / "test_x.py"
        test_file.write_text("pass")
        assert disc._matches_scope(test_file, "unit")

    def test_unit_scope_excludes_e2e(self, project_root: Path):
        disc = PathDiscovery(project_root)
        e2e_dir = project_root / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        e2e_file = e2e_dir / "test_e2e.py"
        e2e_file.write_text("pass")
        assert not disc._matches_scope(e2e_file, "unit")

    def test_e2e_scope(self, project_root: Path):
        disc = PathDiscovery(project_root)
        e2e_dir = project_root / "tests" / "e2e"
        e2e_dir.mkdir(parents=True)
        e2e_file = e2e_dir / "test_e2e.py"
        e2e_file.write_text("pass")
        assert disc._matches_scope(e2e_file, "e2e")

    def test_unknown_scope_returns_true(self, project_root: Path):
        disc = PathDiscovery(project_root)
        f = project_root / "src" / "pkg" / "module.py"
        assert disc._matches_scope(f, "unknown")
