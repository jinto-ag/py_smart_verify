# py-verify

Professional Python verification CLI tool combining linting, type checking, and smart testing into a single command.

## Features

- **Unified pipeline** - Run formatters, linters, type checkers, and tests in one command
- **Smart testing** - Only run tests affected by your changes (via [py-smart-test](https://pypi.org/project/py-smart-test/))
- **Caching** - Skip steps that haven't changed since the last run
- **Dependency graph** - Detect circular dependencies and visualize module relationships
- **Code analysis** - Check architecture guidelines, import patterns, and coding standards

## Installation

```bash
pip install py-verify
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add py-verify
```

### Optional tools

Install all supported verification tools:

```bash
pip install py-verify[all-tools]
```

## Quick start

```bash
# Run all quality checks (format, lint, type check, analyze)
py-verify verify quality

# Run tests (smart mode - only affected tests)
py-verify verify tests

# Run everything
py-verify verify

# Use the short alias
pyv verify quality
```

## Commands

### `verify`

Run verification checks on Python code.

```bash
# Run specific tasks
py-verify verify ruff mypy

# Run with options
py-verify verify --no-cache --continue quality
py-verify verify --paths src,lib --full-tests
py-verify verify --staged tests  # pre-commit mode
```

**Options:**

| Flag           | Description                                 |
| -------------- | ------------------------------------------- |
| `--no-cache`   | Disable caching                             |
| `--continue`   | Continue after errors (default: fast-fail)  |
| `--paths`      | Paths to verify (comma-separated)           |
| `--full-tests` | Run all tests with smart prioritization     |
| `--staged`     | Test only staged changes (pre-commit mode)  |
| `--since REF`  | Git ref for smart test diff (default: main) |
| `--skip-tests` | Skip test execution                         |
| `-v`           | Verbose output                              |

### `graph`

Build and display the dependency graph.

```bash
py-verify graph
py-verify graph --output deps.json
```

### `affected`

List tests affected by code changes.

```bash
py-verify affected
py-verify affected --since main --json
```

### `regen-graph`

Regenerate the py-smart-test dependency graph.

```bash
py-verify regen-graph
```

## Available tasks

| Category          | Tasks                                                                   |
| ----------------- | ----------------------------------------------------------------------- |
| **Formatters**    | `format` (black), `isort`, `ruff-fix`                                   |
| **Linters**       | `flake8`, `pyflakes`                                                    |
| **Type checkers** | `mypy`, `pyright`, `basedpyright`                                       |
| **Analyzers**     | `architecture`, `standards`, `imports`, `circular-deps`, `deprecations` |
| **Testing**       | `tests`, `full-tests`, `e2e-tests`, `full-e2e-tests`                    |
| **Composite**     | `quality` (all formatters + linters + type checkers + analyzers)        |

## Requirements

- Python 3.11+
- Individual tools (ruff, mypy, etc.) installed separately or via `py-verify[all-tools]`

## License

[MIT](LICENSE)
