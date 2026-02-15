"""Tests for py_smart_verify.tasks.analyzers."""

import ast
from pathlib import Path

from py_smart_verify.models import StepStatus
from py_smart_verify.tasks.analyzers import (
    ArchitectureChecker,
    ArchitectureTask,
    CircularDepsTask,
    DeprecationsTask,
    ImportChecker,
    ImportsTask,
    StandardsChecker,
    StandardsTask,
)
from py_smart_verify.tasks.base import TaskCategory

# --- DeprecationsTask ---


class TestDeprecationsTask:
    def test_metadata(self, task_config):
        task = DeprecationsTask(task_config)
        assert task.metadata.name == "deprecations"
        assert task.metadata.category == TaskCategory.ANALYZER

    def test_always_available(self, task_config):
        """DeprecationsTask uses AST analysis (tool_name='python'), always available."""
        task = DeprecationsTask(task_config)
        assert task.is_available()

    def test_empty_paths_returns_success(self, task_config):
        task = DeprecationsTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_detects_deprecated_decorator(self, task_config, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text(
            "from typing_extensions import deprecated\n\n@deprecated\ndef old_func():\n    pass\n"
        )
        task = DeprecationsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1
        assert "deprecated" in result.issues[0].message

    def test_clean_file_no_deprecations(self, task_config, tmp_path: Path):
        f = tmp_path / "clean.py"
        f.write_text("def foo():\n    pass\n")
        task = DeprecationsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS
        assert result.issues == []


# --- CircularDepsTask ---


class TestCircularDepsTask:
    def test_metadata(self, task_config):
        task = CircularDepsTask(task_config)
        assert task.metadata.name == "circular-deps"

    def test_no_cycles(self, task_config, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("import os\n")
        task = CircularDepsTask(task_config)
        result = task.execute([pkg])
        assert result.status == StepStatus.SUCCESS
        assert result.issues == []

    def test_file_path(self, task_config, tmp_path: Path):
        f = tmp_path / "single.py"
        f.write_text("x = 1\n")
        task = CircularDepsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths(self, task_config):
        task = CircularDepsTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS

    def test_with_cycles(self, task_config, tmp_path: Path):
        """Two files that import each other → cycle detected."""
        (tmp_path / "alpha.py").write_text("import beta\n")
        (tmp_path / "beta.py").write_text("import alpha\n")
        task = CircularDepsTask(task_config)
        result = task.execute([tmp_path / "alpha.py", tmp_path / "beta.py"])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) > 0
        assert "Circular dependency" in result.issues[0].message


# --- ImportChecker ---


class TestImportChecker:
    def test_init(self, tmp_path: Path):
        checker = ImportChecker(tmp_path / "a.py", tmp_path)
        assert checker.issues == []
        assert not checker._in_function

    def test_import_outside_function(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("import os\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert checker.issues == []

    def test_import_inside_function(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    import os\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "import" in checker.issues[0].message.lower()

    def test_from_import_inside_function(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    from os import path\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert len(checker.issues) == 1

    def test_import_inside_class(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("class Foo:\n    import os\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert len(checker.issues) == 1

    def test_nested_restore(self, tmp_path: Path):
        """Verify _in_function is restored after visiting nested structures."""
        f = tmp_path / "mod.py"
        f.write_text("import os\ndef foo():\n    pass\nimport sys\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert checker.issues == []

    def test_multiple_import_names(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    import os, sys\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert len(checker.issues) == 2

    def test_from_import_no_module(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("def foo():\n    from . import something\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ImportChecker(f, tmp_path)
        checker.visit(tree)
        assert len(checker.issues) == 1
        # module is empty string ""
        assert "''" in checker.issues[0].message


# --- ImportsTask ---


class TestImportsTask:
    def test_metadata(self, task_config):
        task = ImportsTask(task_config)
        assert task.metadata.name == "imports"

    def test_clean_file(self, task_config, tmp_path: Path):
        f = tmp_path / "clean.py"
        f.write_text("import os\n\ndef foo():\n    pass\n")
        task = ImportsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS

    def test_function_level_import(self, task_config, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def foo():\n    import os\n")
        task = ImportsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_syntax_error_skipped(self, task_config, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def foo(\n")
        task = ImportsTask(task_config)
        result = task.execute([f])
        # Syntax error is silently skipped
        assert result.status == StepStatus.SUCCESS

    def test_directory(self, task_config, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("import os\n")
        task = ImportsTask(task_config)
        result = task.execute([pkg])
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths(self, task_config):
        task = ImportsTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS


# --- ArchitectureChecker ---


class TestArchitectureChecker:
    def test_init(self, tmp_path: Path):
        checker = ArchitectureChecker(tmp_path / "a.py", tmp_path)
        assert checker.issues == []

    def test_visit_global(self, tmp_path: Path):
        f = tmp_path / "mod.py"
        f.write_text("x = 0\ndef foo():\n    global x\n    x = 1\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ArchitectureChecker(f, tmp_path)
        checker.visit(tree)
        assert len(checker.issues) == 1
        assert "global" in checker.issues[0].message.lower()

    def test_no_global(self, tmp_path: Path):
        f = tmp_path / "clean.py"
        f.write_text("def foo():\n    x = 1\n")
        tree = ast.parse(f.read_text(), str(f))
        checker = ArchitectureChecker(f, tmp_path)
        checker.visit(tree)
        assert checker.issues == []


# --- ArchitectureTask ---


class TestArchitectureTask:
    def test_metadata(self, task_config):
        task = ArchitectureTask(task_config)
        assert task.metadata.name == "architecture"

    def test_clean(self, task_config, tmp_path: Path):
        f = tmp_path / "clean.py"
        f.write_text("def foo():\n    return 1\n")
        task = ArchitectureTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS

    def test_with_global(self, task_config, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("x = 0\ndef foo():\n    global x\n    x = 1\n")
        task = ArchitectureTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) == 1

    def test_syntax_error_skipped(self, task_config, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def foo(\n")
        task = ArchitectureTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS

    def test_directory(self, task_config, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("pass\n")
        task = ArchitectureTask(task_config)
        result = task.execute([pkg])
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths(self, task_config):
        task = ArchitectureTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS


# --- StandardsChecker ---


class TestStandardsChecker:
    def test_init(self, tmp_path: Path):
        checker = StandardsChecker(tmp_path / "a.py", tmp_path, "")
        assert checker.issues == []

    def test_missing_docstring(self, tmp_path: Path):
        source = "def foo():\n    pass\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        assert any("docstring" in i.message.lower() for i in checker.issues)

    def test_has_docstring(self, tmp_path: Path):
        source = 'def foo():\n    """Doc."""\n    pass\n'
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        docstring_issues = [i for i in checker.issues if "docstring" in i.message.lower()]
        assert docstring_issues == []

    def test_long_function(self, tmp_path: Path):
        lines = ["def foo() -> int:\n", '    """Doc."""\n']
        for i in range(55):
            lines.append(f"    x = {i}\n")
        lines.append("    return x\n")
        source = "".join(lines)
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        length_issues = [i for i in checker.issues if "lines" in i.message]
        assert len(length_issues) == 1

    def test_short_function(self, tmp_path: Path):
        source = 'def foo() -> int:\n    """Doc."""\n    return 1\n'
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        length_issues = [i for i in checker.issues if "lines" in i.message]
        assert length_issues == []

    def test_missing_annotation(self, tmp_path: Path):
        source = "def foo():\n    pass\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        annotation_issues = [i for i in checker.issues if "annotation" in i.message.lower()]
        assert len(annotation_issues) == 1

    def test_has_annotation(self, tmp_path: Path):
        source = "def foo() -> int:\n    pass\n"
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        annotation_issues = [i for i in checker.issues if "annotation" in i.message.lower()]
        assert annotation_issues == []

    def test_all_clean(self, tmp_path: Path):
        source = 'def greet(name: str) -> str:\n    """Greet."""\n    return f"hi {name}"\n'
        f = tmp_path / "mod.py"
        f.write_text(source)
        tree = ast.parse(source, str(f))
        checker = StandardsChecker(f, tmp_path, source)
        checker.visit(tree)
        assert checker.issues == []


# --- StandardsTask ---


class TestStandardsTask:
    def test_metadata(self, task_config):
        task = StandardsTask(task_config)
        assert task.metadata.name == "standards"
        assert task.metadata.category == TaskCategory.ANALYZER

    def test_clean(self, task_config, tmp_path: Path):
        f = tmp_path / "clean.py"
        f.write_text('def greet(name: str) -> str:\n    """Greet."""\n    return f"hi {name}"\n')
        task = StandardsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS

    def test_missing_docstring(self, task_config, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def foo():\n    pass\n")
        task = StandardsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.FAILED
        assert len(result.issues) > 0

    def test_syntax_error_skipped(self, task_config, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text("def foo(\n")
        task = StandardsTask(task_config)
        result = task.execute([f])
        assert result.status == StepStatus.SUCCESS

    def test_directory(self, task_config, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text('def foo() -> int:\n    """Doc."""\n    return 1\n')
        task = StandardsTask(task_config)
        result = task.execute([pkg])
        assert result.status == StepStatus.SUCCESS

    def test_empty_paths(self, task_config):
        task = StandardsTask(task_config)
        result = task.execute([])
        assert result.status == StepStatus.SUCCESS
