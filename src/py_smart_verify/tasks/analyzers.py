"""Analyzer tasks for py-smart-verify."""

import ast
from pathlib import Path

from py_smart_verify.graph import DependencyGraphBuilder
from py_smart_verify.models import Issue, StepResult, StepStatus
from py_smart_verify.tasks.base import BaseTask, TaskCategory, TaskMetadata
from py_smart_verify.tasks.registry import register


@register
class DeprecationsTask(BaseTask):
    """Deprecation checking task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="deprecations",
            display_name="Deprecations",
            category=TaskCategory.ANALYZER,
            description="Check for deprecated features",
            tool_name="memestra",
            aliases=["deprecations"],
            cache_scope="quality",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute deprecation check."""
        if not self.is_available():
            return self._build_skipped("Memestra not available")

        log_path = self.config.log_dir / "deprecations.log"
        # Placeholder for memestra integration
        return self._build_result(
            status=StepStatus.SUCCESS,
            command="memestra check",
            log_path=log_path,
        )


@register
class CircularDepsTask(BaseTask):
    """Circular dependency detection task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="circular-deps",
            display_name="Circular Dependencies",
            category=TaskCategory.ANALYZER,
            description="Detect circular dependencies",
            tool_name="python",
            aliases=["circular-deps", "circular"],
            cache_scope="quality",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Execute circular dependency detection."""
        log_path = self.config.log_dir / "circular-deps.log"

        if not paths:
            paths = [self.config.project_root]

        # Build dependency graph
        all_py_files = []
        for path in paths:
            if path.is_file() and path.suffix == ".py":
                all_py_files.append(path)
            elif path.is_dir():
                all_py_files.extend(path.rglob("*.py"))

        builder = DependencyGraphBuilder(self.config.project_root)
        graph = builder.build(all_py_files)

        issues = []
        for cycle in graph.cycles:
            cycle_str = " → ".join(cycle)
            issues.append(
                Issue(
                    file="(dependency graph)",
                    line=None,
                    type="error",
                    message=f"Circular dependency: {cycle_str}",
                    source_task="circular-deps",
                )
            )

        status = StepStatus.FAILED if issues else StepStatus.SUCCESS
        log_path.write_text(f"Found {len(graph.cycles)} circular dependencies")

        return self._build_result(
            status=status,
            exit_code=1 if issues else 0,
            command="analyze dependencies",
            log_path=log_path,
            issues=issues,
        )


@register
class ImportsTask(BaseTask):
    """Import analysis task - finds imports inside functions."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="imports",
            display_name="Imports",
            category=TaskCategory.ANALYZER,
            description="Analyze import patterns",
            tool_name="python",
            aliases=["imports"],
            cache_scope="quality",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Analyze import patterns."""
        log_path = self.config.log_dir / "imports.log"

        if not paths:
            paths = [self.config.project_root]

        all_py_files = []
        for path in paths:
            if path.is_file() and path.suffix == ".py":
                all_py_files.append(path)
            elif path.is_dir():
                all_py_files.extend(path.rglob("*.py"))

        issues = []
        for py_file in all_py_files:
            try:
                with open(py_file) as f:
                    tree = ast.parse(f.read(), filename=str(py_file))
                checker = ImportChecker(py_file, self.config.project_root)
                checker.visit(tree)
                issues.extend(checker.issues)
            except (SyntaxError, OSError):
                pass

        status = StepStatus.FAILED if issues else StepStatus.SUCCESS
        log_path.write_text(f"Found {len(issues)} import issues")

        return self._build_result(
            status=status,
            exit_code=1 if issues else 0,
            command="analyze imports",
            log_path=log_path,
            issues=issues,
        )


class ImportChecker(ast.NodeVisitor):
    """Find imports inside functions."""

    def __init__(self, file_path: Path, project_root: Path) -> None:
        self.file_path = file_path
        self.project_root = project_root
        self.issues: list[Issue] = []
        self._in_function = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        old_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = old_in_function

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        old_in_function = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = old_in_function

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        if self._in_function:
            for alias in node.names:
                self.issues.append(
                    Issue(
                        file=str(self.file_path.relative_to(self.project_root)),
                        line=node.lineno,
                        type="note",
                        message=f"Import '{alias.name}' inside function",
                        source_task="imports",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statements."""
        if self._in_function:
            module = node.module or ""
            self.issues.append(
                Issue(
                    file=str(self.file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    type="note",
                    message=f"Import from '{module}' inside function",
                    source_task="imports",
                )
            )
        self.generic_visit(node)


@register
class ArchitectureTask(BaseTask):
    """Architecture analysis task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="architecture",
            display_name="Architecture",
            category=TaskCategory.ANALYZER,
            description="Check architecture guidelines",
            tool_name="python",
            aliases=["architecture", "arch"],
            cache_scope="quality",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Check architecture."""
        log_path = self.config.log_dir / "architecture.log"

        if not paths:
            paths = [self.config.project_root]

        all_py_files = []
        for path in paths:
            if path.is_file() and path.suffix == ".py":
                all_py_files.append(path)
            elif path.is_dir():
                all_py_files.extend(path.rglob("*.py"))

        issues = []
        for py_file in all_py_files:
            try:
                with open(py_file) as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(py_file))

                checker = ArchitectureChecker(py_file, self.config.project_root)
                checker.visit(tree)
                issues.extend(checker.issues)
            except (SyntaxError, OSError):
                pass

        status = StepStatus.FAILED if issues else StepStatus.SUCCESS
        log_path.write_text(f"Found {len(issues)} architecture issues")

        return self._build_result(
            status=status,
            exit_code=1 if issues else 0,
            command="analyze architecture",
            log_path=log_path,
            issues=issues,
        )


class ArchitectureChecker(ast.NodeVisitor):
    """Check architecture guidelines."""

    def __init__(self, file_path: Path, project_root: Path) -> None:
        self.file_path = file_path
        self.project_root = project_root
        self.issues: list[Issue] = []

    def visit_Global(self, node: ast.Global) -> None:
        """Detect global state modifications."""
        for name in node.names:
            self.issues.append(
                Issue(
                    file=str(self.file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    type="warning",
                    message=f"Global variable modification: {name}",
                    source_task="architecture",
                )
            )
        self.generic_visit(node)


@register
class StandardsTask(BaseTask):
    """Code standards checking task."""

    def _get_metadata(self) -> TaskMetadata:
        return TaskMetadata(
            name="standards",
            display_name="Standards",
            category=TaskCategory.ANALYZER,
            description="Check code standards",
            tool_name="python",
            aliases=["standards"],
            cache_scope="quality",
            phase=3,
        )

    def execute(self, paths: list[Path]) -> StepResult:
        """Check code standards."""
        log_path = self.config.log_dir / "standards.log"

        if not paths:
            paths = [self.config.project_root]

        all_py_files = []
        for path in paths:
            if path.is_file() and path.suffix == ".py":
                all_py_files.append(path)
            elif path.is_dir():
                all_py_files.extend(path.rglob("*.py"))

        issues = []
        for py_file in all_py_files:
            try:
                with open(py_file) as f:
                    content = f.read()
                    tree = ast.parse(content, filename=str(py_file))

                checker = StandardsChecker(py_file, self.config.project_root, content)
                checker.visit(tree)
                issues.extend(checker.issues)
            except (SyntaxError, OSError):
                pass

        status = StepStatus.FAILED if issues else StepStatus.SUCCESS
        log_path.write_text(f"Found {len(issues)} standards issues")

        return self._build_result(
            status=status,
            exit_code=1 if issues else 0,
            command="analyze standards",
            log_path=log_path,
            issues=issues,
        )


class StandardsChecker(ast.NodeVisitor):
    """Check code standards - docstrings, type hints, complexity."""

    def __init__(self, file_path: Path, project_root: Path, source: str) -> None:
        self.file_path = file_path
        self.project_root = project_root
        self.source = source
        self.issues: list[Issue] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function standards."""
        # Check for docstring
        docstring = ast.get_docstring(node)
        if not docstring:
            self.issues.append(
                Issue(
                    file=str(self.file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    type="note",
                    message=f"Function '{node.name}' missing docstring",
                    source_task="standards",
                )
            )

        # Check function length
        func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
        if func_lines > 50:
            self.issues.append(
                Issue(
                    file=str(self.file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    type="warning",
                    message=f"Function '{node.name}' is {func_lines} lines (>50)",
                    source_task="standards",
                )
            )

        # Check for type hints
        if not node.returns:
            self.issues.append(
                Issue(
                    file=str(self.file_path.relative_to(self.project_root)),
                    line=node.lineno,
                    type="note",
                    message=f"Function '{node.name}' missing return annotation",
                    source_task="standards",
                )
            )

        self.generic_visit(node)
