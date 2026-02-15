# py-verify: Implementation Plan

Transform `~/scripts/python-verify.sh` (1658-line bash script) into a professional, modular Python CLI app using Typer + Pydantic + Rich.

---

## Project Structure

```text
src/py_verify/
  __init__.py              # Package version, metadata
  __main__.py              # python -m py_verify support
  cli.py                   # Typer app, all commands/options
  config.py                # Pydantic VerifyConfig, Severity, RunMode
  models.py                # StepResult, RunResult, Issue, DependencyGraph
  console.py               # Rich console singleton, theme, print helpers
  runner.py                # VerifyRunner orchestrator
  cache.py                 # SHA256 hash-based caching
  git.py                   # Git integration: affected files, diff detection
  discovery.py             # Path auto-detection, Python file discovery
  venv.py                  # Venv detection, tool install, version checks
  graph.py                 # Dependency graph builder (AST + cycle detection)
  tasks/
    __init__.py            # TaskRegistry singleton, @register decorator
    base.py                # BaseTask ABC, TaskCategory enum, TaskMetadata
    formatters.py          # FormatTask (black), IsortTask, RuffFixTask
    linters.py             # Flake8Task, PyflakesTask
    type_checkers.py       # MypyTask, PyrightTask, BasedPyrightTask
    analyzers.py           # CircularDeps, Imports, Architecture, Standards, Deprecations
    testing.py             # UnitTestTask, E2ETestTask
    quality.py             # QualityCompositeTask (orchestrates sub-tasks in phases)
    self_test.py           # SelfTestTask

tests/
  conftest.py
  test_config.py
  test_models.py
  test_cache.py
  test_discovery.py
  test_runner.py
  test_tasks/
    test_base.py
    test_formatters.py
    test_analyzers.py
```

Runtime artifacts (in the project being verified):

```text
.py_verify/
  .gitignore               # Auto-created, ignores everything except itself
  last_run.json            # Structured JSON for AI agents
  logs/                    # Per-task log files (format.log, ruff.log, etc.)
  cache/                   # Hash files (.hash, .ok, .time)
  graph.json               # Dependency graph (when graph command is run)

.py_smart_test/            # Managed by py-smart-test (auto-created)
  dependency_graph.json    # AST-based import dependency graph
  file_hashes.json         # MD5 snapshots for change detection
  test_outcomes.json       # Historical test pass/fail/duration data
  .gitignore               # Auto-created by py-smart-test
  logs/
    latest_run.log         # py-smart-test execution logs
```

---

## Implementation Order

### Phase 1: Foundation (6 files)

1. **`src/py_verify/__init__.py`** - `__version__ = "0.1.0"`, `__app_name__`
2. **`src/py_verify/config.py`** - Pydantic models:
   - `Severity(IntEnum)` - CRITICAL(1) through INFO(5)
   - `RunMode(str, Enum)` - FAST_FAIL, CONTINUE
   - `VerifyConfig(BaseModel)` - all CLI flags as fields: `tasks`, `tools_filter`, `paths`, `skip_tests`, `no_cache`, `include_tests`, `ignore_warnings`, `min_severity`, `run_mode`, `verbose`, `upgrade_deps`, `project_root`, `cache_dir`, `log_dir`, `full_tests`, `since`, `staged`
3. **`src/py_verify/models.py`** - Data models:
   - `StepStatus(Enum)` - pending/running/success/failed/cached/skipped
   - `Issue(BaseModel)` - file, line, col, type, severity, message, action, source_task
   - `StepResult(BaseModel)` - name, status, start/end epoch, exit_code, log path, command, issues
   - `RunResult(BaseModel)` - run_id, started_at, finished_at, status, steps list, with `add_step()`, `mark_success/failed()`, `to_json_file()`
   - `DependencyNode(BaseModel)`, `DependencyGraph(BaseModel)`
4. **`src/py_verify/console.py`** - Rich singleton + helpers:
   - `PV_THEME` with success/error/warning/cached/severity styles
   - `console`, `err_console` instances
   - `print_banner()`, `print_step_start()`, `print_step_result()`, `print_cache_hit()`, `print_issues_table()`, `print_run_summary()` (Rich table), `print_dependency_graph()` (Rich Tree)
5. **`src/py_verify/discovery.py`** - `PathDiscovery` class:
   - `resolve_paths()` - user-specified > auto-detected (src/lib/app/scripts/main.py) > fallback "."
   - `find_python_files(scope)` - walk paths, exclude dirs, filter by scope (quality/unit/e2e)
6. **`src/py_verify/cache.py`** - `CacheManager` class:
   - `compute_hash(scope)` - SHA256 of file contents + tool versions (port of bash `py_hash_scope`)
   - `is_cached(scope)` - compare hash file, check .ok marker
   - `mark_ok(scope, duration)` - write .ok and .time files
   - `invalidate(scope)` - remove cache files

### Phase 2: Infrastructure (3 files)

1. **`src/py_verify/venv.py`** - `VenvManager` class:
   - `detect_venv(project_root)` - check .venv/ and venv/
   - `detect_package_manager(project_root)` - uv > poetry > pip
   - `check_tool_available(tool)` - `shutil.which()`
   - `get_missing_tools(scope)`, `install_missing_tools(tools, pm)`
   - `get_tool_version(tool)` - run `<tool> --version`, return string
2. **`src/py_verify/git.py`** - `GitIntegration` class:
   - `is_git_repo()` - check `.git/`
   - `get_changed_files(base_ref, include_staged, include_unstaged, include_untracked)` - `git diff --name-only`, `git status --porcelain`
   - `get_affected_modules(changed_files)` - map files to module names
   - `get_diff_stats()` - insertions/deletions/files_changed
3. **`src/py_verify/graph.py`** - `DependencyGraphBuilder` class:
   - `build()` - walk all .py files, parse imports with `ast`, build DependencyGraph
   - `_parse_imports(filepath)` - AST-based import extraction
   - `_file_to_module(filepath, base)` - path to dotted module name
   - `detect_cycles(graph)` - DFS cycle detection (port of bash `check_circular.py` DependencyGraph)
   - `to_json(graph, output_path)` - serialize to JSON file

### Phase 3: Task System (8 files)

1. **`src/py_verify/tasks/base.py`** - Task foundation:
   - `TaskCategory(str, Enum)` - FORMATTER, LINTER, TYPE_CHECKER, ANALYZER, TESTING, COMPOSITE, META
   - `TaskMetadata(dataclass)` - name, display_name, category, description, tool_name, aliases, cache_scope, auto_fix, phase
   - `BaseTask(ABC)` with:
     - `execute(paths) -> StepResult` (abstract)
     - `is_available()` - check `shutil.which(tool_name)`
     - `_run_subprocess(cmd, log_path, allow_failure)` - run tool, tee to log, return (exit_code, output)
     - `_build_result(...)` - construct StepResult
     - `_build_skipped(reason)` - construct skipped StepResult
2. **`src/py_verify/tasks/__init__.py`** - Registry:
   - `TaskRegistry` class with `register()`, `get(name)`, `get_by_category()`, `all_names()`, `resolve_names()`
   - `task_registry` singleton
   - `@register` decorator
   - Import all task modules to trigger registration
3. **`src/py_verify/tasks/formatters.py`** - Phase 0 auto-fixers:
   - `FormatTask` (black) - `allow_failure=True`
   - `IsortTask` (isort) - `allow_failure=True`
   - `RuffFixTask` (ruff check --fix) - `allow_failure=True`
4. **`src/py_verify/tasks/linters.py`** - Phase 1 checks:
   - `Flake8Task` (flake8)
   - `PyflakesTask` (pyflakes)
5. **`src/py_verify/tasks/type_checkers.py`** - Phase 2:
   - `MypyTask` - config detection: mypy.ini > pyproject.toml > --ignore-missing-imports
   - `PyrightTask` - `pyright <paths> --level error`
   - `BasedPyrightTask` - aliases=["pylance"]
6. **`src/py_verify/tasks/analyzers.py`** - Phase 3 (largest file, ports all embedded Python scripts):
   - `DeprecationsTask` - check memestra availability, skip on Python 3.13+
   - `CircularDepsTask` - delegates to `DependencyGraphBuilder`, returns cycles as issues
   - `ImportsTask` - port `ImportChecker(ast.NodeVisitor)` from bash lines 879-961, finds imports inside functions
   - `ArchitectureTask` - port `ArchitectureChecker(ast.NodeVisitor)` from bash lines 963-1257: placeholder code, type:ignore counts, global state, direct service imports, helper-in-service mixing
   - `StandardsTask` - port `StandardsChecker(ast.NodeVisitor)` from bash lines 1260-1421: complex functions (>50 lines), missing docstrings, missing type hints, hardcoded values
7. **`src/py_verify/tasks/testing.py`** (powered by `py-smart-test`):
   - `SmartTestTask` (default test task) - runs `pytest --smart --smart-working-tree -q --maxfail=1 --disable-warnings --exclude-e2e`
     - Only executes tests affected by code changes (via py_smart_test's dependency graph + git diff)
     - Automatically prioritizes previously-failed tests, then affected tests, sorted by historical duration
     - Falls back to full test suite on first run or when no historical data exists
   - `FullTestTask` - runs `pytest --smart-first -q --maxfail=1 --disable-warnings --exclude-e2e`
     - Executes all tests but reorders them: failed → affected → rest (smart prioritization)
     - Used when `--full-tests` flag is passed to py-verify
   - `E2ETestTask` - `pytest --smart --smart-working-tree -q --maxfail=1 --disable-warnings tests/e2e --no-exclude-e2e`
     - Runs only affected E2E tests by default
   - `FullE2ETestTask` - `pytest --smart-first -q --maxfail=1 --disable-warnings tests/e2e --no-exclude-e2e`
     - Runs all E2E tests with smart prioritization when `--full-tests` is passed
   - Common behavior:
     - All tasks respect `skip_tests` flag and cache scope
     - `--smart-since REF` is forwarded when py-verify's `--since` flag is set (defaults to `main`, useful in CI)
     - `--smart-staged` is forwarded when py-verify's `--staged` flag is set (useful for pre-commit hooks)
     - py_smart_test's dependency graph (`.py_smart_test/dependency_graph.json`) is auto-generated and auto-regenerated when stale
     - Test outcomes (pass/fail/duration) are persisted in `.py_smart_test/test_outcomes.json` across runs
   - `RegenerateGraphTask` - runs `py-smart-test-graph-gen` (alias `pst-gen`)
     - Exposed as `py-verify regen-graph` subcommand for manual graph regeneration
   - `AffectedTestsTask` - runs `py-smart-test-affected --json` (alias `pst-affected`)
     - Exposed as `py-verify affected` subcommand to list affected tests without running them
8. **`src/py_verify/tasks/quality.py`** - Composite task:
   - `QualityCompositeTask` - orchestrates phases 0-3 in order
   - If `tools_filter` set, only run those specific tools
   - Cache-aware (whole quality scope)
   - Respects `run_mode` (fast-fail vs continue)

### Phase 4: Orchestration & CLI (4 files)

1. **`src/py_verify/tasks/self_test.py`** - `SelfTestTask`:
   - Validates config edge cases, registry completeness, cache round-trip
   - Reports pass/fail with Rich table
2. **`src/py_verify/runner.py`** - `VerifyRunner` orchestrator:
   - `run() -> int` (exit code):
     1. `_setup()` - create .py_verify/ dirs, .gitignore, install missing tools, init RunResult JSON
     2. Resolve paths via `PathDiscovery`
     3. `_resolve_tasks()` - expand task names (quality expands to sub-tasks, tests expands to unit+e2e), prioritize quality first
     4. Execute each task, update `last_run.json` after each step
     5. Handle fast-fail (stop on first error) vs continue (run all)
     6. `_teardown()` - mark run success/failed, print Rich summary table
   - `_ensure_gitignore()` - create `.py_verify/.gitignore`
   - `_ensure_configs()` - create default mypy.ini, ruff.toml, .flake8, isort.cfg if missing
3. **`src/py_verify/cli.py`** - Typer app:
   - Main command: `py-verify [OPTIONS] [TASKS...]`
   - All options: `--skip-tests`, `--no-cache`, `--include-tests`, `--ignore-warnings`, `--continue`, `--fast-fail`, `--min-severity`, `--tools`, `--paths`, `--upgrade-deps`, `-v`, `--version`, `--full-tests`, `--since REF`, `--staged`
   - `graph` subcommand: `py-verify graph [--output FILE] [--paths PATHS]`
   - `affected` subcommand: `py-verify affected [--since REF] [--staged] [--json]` - delegates to `pst-affected`, lists affected tests
   - `regen-graph` subcommand: `py-verify regen-graph` - delegates to `pst-gen`, regenerates dependency graph
   - Build `VerifyConfig` from CLI args, pass to `VerifyRunner`
4. **`src/py_verify/__main__.py`** - one line: `from py_verify.cli import app; app()`

### Phase 5: Project Config & Finalization (3 files)

1. **`pyproject.toml`** - Update:
   - `[project.scripts]` entry points: `py-verify` and `python-verify` (alias)
   - Core deps (pydantic, rich, typer, **py-smart-test**) plus optional `[project.optional-dependencies]` `all-tools` group
   - `[tool.setuptools.packages.find] where = ["src"]`
   - Tool configs for ruff, mypy, pyright, isort under `[tool.*]`
   - `[tool.py-smart-test]` config section (src_dir, packages, test_dir, default_branch) for the target project's smart test behavior
2. **`.gitignore`** - Add `.py_verify/` and `.py_smart_test/` entries to project root `.gitignore`
3. **Delete `main.py`** - replaced by the proper CLI

---

## Key Design Decisions

| Decision                                                                       | Rationale                                                                                                                                                                                                                                       |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tasks as positional args, not subcommands                                      | Matches bash behavior: `py-verify ruff mypy` runs both. Only `graph`, `affected`, `regen-graph` are subcommands (different workflows).                                                                                                          |
| Embedded Python scripts become classes                                         | `check_circular.py`, `check_imports.py`, `check_architecture.py`, `check_standards.py` become proper classes in `analyzers.py` using `self.config` instead of env vars. No temp file creation.                                                  |
| Cache at scope level (quality/unit/e2e), not per-task                          | Preserves bash behavior. A file change invalidates all quality checks together. Tool version changes re-trigger all.                                                                                                                            |
| `allow_failure` for formatters                                                 | Black/isort/ruff return non-zero when they reformat. These are auto-fixers, not errors.                                                                                                                                                         |
| `RunResult.to_json_file()` after every step                                    | AI agents can read `last_run.json` while the run is in progress.                                                                                                                                                                                |
| `DependencyGraphBuilder` shared between `graph` command and `CircularDepsTask` | DRY - cycle detection logic lives once in `graph.py`.                                                                                                                                                                                           |
| Both entry points: `py-verify` and `python-verify`                             | `python-verify` for backward compat with existing scripts/habits.                                                                                                                                                                               |
| `py-smart-test` for all test execution                                         | Our own package (`py-smart-test` on PyPI). Provides smart affected-test selection via AST dependency graph, test prioritization (failed→affected→rest by duration), and outcome tracking. Avoids reimplementing test intelligence in py-verify. |
| `pytest --smart` as default, `--smart-first` for full runs                     | Default runs only affected tests (fast feedback). `--full-tests` flag switches to `--smart-first` which runs everything but reorders intelligently. Both leverage py_smart_test's prioritization.                                               |
| Forward `--since` and `--staged` to py-smart-test                              | Enables CI (`--since=origin/main`) and pre-commit (`--staged`) workflows without py-verify needing its own change detection for tests.                                                                                                          |

---

## CLI Usage Examples (matching bash feature parity)

```bash
# Default: quality + smart tests (only affected tests run)
py-verify

# Specific tasks
py-verify ruff mypy
py-verify quality tests

# Flags
py-verify --skip-tests quality
py-verify --no-cache quality
py-verify --tools=ruff,mypy quality
py-verify --paths=src,tests quality
py-verify --continue quality
py-verify --min-severity=2 quality
py-verify --include-tests quality
py-verify --ignore-warnings quality

# Smart test options
py-verify --full-tests              # Run ALL tests with smart prioritization (failed first)
py-verify --since=origin/main       # Diff against specific ref (CI usage)
py-verify --staged                  # Only test staged changes (pre-commit hook)
py-verify tests                     # Run only smart tests (skip quality)
py-verify --full-tests tests        # Run all tests with prioritization

# Smart test utility subcommands
py-verify affected                  # List affected tests without running
py-verify affected --json           # JSON output for CI/scripting
py-verify affected --staged         # Show tests affected by staged changes
py-verify regen-graph               # Force dependency graph regeneration

# Dependency graph
py-verify graph
py-verify graph --output deps.json --paths=src

# Upgrade tools
py-verify --upgrade-deps
```

---

## Verification

1. **Smoke test**: `uv run py-verify --help` shows all options including `--full-tests`, `--since`, `--staged`
2. **Single task**: `uv run py-verify format` runs only black
3. **Multiple tasks**: `uv run py-verify ruff mypy` runs both
4. **Quality**: `uv run py-verify quality` runs all quality checks in phase order
5. **Smart tests (default)**: `uv run py-verify tests` runs only affected tests via `pytest --smart`
6. **Full tests**: `uv run py-verify --full-tests tests` runs all tests with smart prioritization via `pytest --smart-first`
7. **Staged tests**: `uv run py-verify --staged tests` runs tests affected by staged changes only
8. **CI tests**: `uv run py-verify --since=origin/main tests` diffs against specific ref
9. **Affected listing**: `uv run py-verify affected --json` outputs affected test list as JSON
10. **Graph regen**: `uv run py-verify regen-graph` regenerates `.py_smart_test/dependency_graph.json`
11. **Caching**: Run `py-verify quality` twice - second run should show "cache hit"
12. **No-cache**: `py-verify --no-cache quality` forces full re-run
13. **JSON output**: Check `.py_verify/last_run.json` has correct structure
14. **Logs**: Check `.py_verify/logs/` has per-task log files
15. **Graph**: `py-verify graph` renders Rich tree, `--output` writes JSON
16. **Git integration**: Modify a file, run `py-verify` - verify affected detection works
17. **Smart test artifacts**: Verify `.py_smart_test/test_outcomes.json` persists across runs
18. **Global install**: `uv tool install .` then `py-verify quality` from another project
