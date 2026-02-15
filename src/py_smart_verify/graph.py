"""Dependency graph building for py-smart-verify."""

import ast
import json
from pathlib import Path
from typing import Any

from py_smart_verify.models import DependencyGraph, DependencyNode


class DependencyGraphBuilder:
    """Builds and analyzes import dependencies."""

    def __init__(self, project_root: Path = Path.cwd()) -> None:  # noqa: B008
        """Initialize graph builder."""
        self.project_root = project_root
        self.graph = DependencyGraph()

    def build(self, python_files: list[Path]) -> DependencyGraph:
        """Build dependency graph from Python files."""
        # First pass: create all nodes
        for file_path in python_files:
            module_name = self._file_to_module(file_path)
            if module_name and module_name not in self.graph.nodes:
                self.graph.nodes[module_name] = DependencyNode(
                    module=module_name,
                    file=str(file_path.relative_to(self.project_root)),
                )

        # Second pass: extract imports
        for file_path in python_files:
            module_name = self._file_to_module(file_path)
            if not module_name:
                continue

            imports = self._parse_imports(file_path)
            if module_name in self.graph.nodes:
                self.graph.nodes[module_name].imports = imports

                # Update imported_by relationships
                for imported in imports:
                    if imported in self.graph.nodes:
                        self.graph.nodes[imported].imported_by.append(module_name)

        # Detect cycles
        self.graph.cycles = self.detect_cycles(self.graph)

        return self.graph

    def _parse_imports(self, file_path: Path) -> list[str]:
        """Extract imports from a Python file using AST."""
        imports = set()

        try:
            with open(file_path) as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except (SyntaxError, OSError):
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])

        return sorted(imports)

    def _file_to_module(self, file_path: Path) -> str | None:
        """Convert file path to module name."""
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            return None

        # Skip non-Python files
        if rel_path.suffix != ".py":
            return None

        # Skip __pycache__ and other special dirs
        if any(part.startswith("__") for part in rel_path.parts[:-1]):
            return None

        # Skip test files for now (can be added to test_map separately)
        if "test" in str(rel_path).lower():
            return None

        # Convert path to module name
        parts = list(rel_path.parts[:-1])  # All but filename
        parts.append(rel_path.stem)  # Add module name without .py

        # Skip source directory prefixes
        filtered = [p for p in parts if p not in ["src", "lib", "app", "scripts", "__init__"]]

        if not filtered:
            return None

        return ".".join(filtered)

    def detect_cycles(self, graph: DependencyGraph) -> list[list[str]]:
        """Detect circular dependencies using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(module: str, path: list[str]) -> None:
            """Traverse the graph depth-first to find cycles."""
            visited.add(module)
            rec_stack.add(module)
            path.append(module)

            node = graph.nodes.get(module)
            if node:
                for imported in node.imports:
                    if imported not in visited:
                        dfs(imported, path.copy())
                    elif imported in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(imported)
                        cycle = [*path[cycle_start:], imported]
                        if cycle not in cycles:
                            cycles.append(cycle)

            rec_stack.discard(module)

        for module in graph.nodes:
            if module not in visited:
                dfs(module, [])

        return cycles

    def to_json(self, output_path: Path) -> None:
        """Serialize graph to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        modules: dict[str, dict[str, Any]] = {}
        for name, node in self.graph.nodes.items():
            modules[name] = {
                "imports": node.imports,
                "file": node.file,
                "imported_by": node.imported_by,
            }

        data: dict[str, Any] = {
            "modules": modules,
            "cycles": self.graph.cycles,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_json(cls, file_path: Path) -> DependencyGraph:
        """Load graph from JSON file."""
        with open(file_path) as f:
            data = json.load(f)

        graph = DependencyGraph()
        for name, node_data in data.get("modules", {}).items():
            graph.nodes[name] = DependencyNode(
                module=name,
                file=node_data.get("file", ""),
                imports=node_data.get("imports", []),
                imported_by=node_data.get("imported_by", []),
            )
        graph.cycles = data.get("cycles", [])
        return graph
