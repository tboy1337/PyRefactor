# PyRefactor

A Python refactoring and optimization linter that uses AST analysis to identify performance issues, complexity problems, and code improvements.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Multi-threaded Analysis**: Fast parallel file processing
- **Configurable Detectors**: Enable/disable specific detectors
- **Severity Levels**: Issues categorized as INFO, LOW, MEDIUM, or HIGH
- **Flexible Output**: Group by file or severity
- **Cross-platform**: Works on Windows, macOS, and Linux

## Detectors

- **Complexity**: High cyclomatic complexity functions
- **Performance**: String concatenation in loops (thresholded), repeated uncached calls in loops, inefficient operations
- **Boolean Logic**: Overcomplicated boolean expressions
- **Loops**: Index patterns, nested loops with lookups, loop-invariant calls
- **Duplication**: Duplicate code blocks
- **Context Manager**: Missing `with` statements for resource operations
- **Control Flow**: Unnecessary `else` after `return`/`raise`/`break`/`continue`
- **Dictionary Operations**: Non-idiomatic dict patterns, missing `.get()`, unnecessary `.keys()`, dict comprehensions (R010)
- **Comparisons**: Chained comparisons, singleton checks, `type()` vs `isinstance()`

See [docs/RULES.md](docs/RULES.md) for the full rule catalog (C001–C006, P001–P007, B001/B004–B007, L001–L004, D001, R001–R016).

## Installation

### Recommended: Via pip

```bash
pip install pyrefactor
```

### Standalone Executable

Download the latest release from the [Releases](https://github.com/tboy1337/PyRefactor/releases/latest) section. No Python installation required.

### From Source

```bash
git clone https://github.com/tboy1337/PyRefactor.git
cd PyRefactor
pip install -e .
```

**Requirements**: Python 3.12+

**Status**: PyRefactor is **Production/Stable** (see PyPI classifiers).

**License**: This project uses the [Commercial Restricted License (CRL)](LICENSE.md). Personal and non-commercial use is permitted; commercial use requires permission from the copyright holder.

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full configuration reference (TOML and INI formats).

## Usage

```bash
# Analyze a file or directory
pyrefactor myfile.py
pyrefactor src/

# Show only medium/high severity issues
pyrefactor --min-severity medium src/

# Group by severity level
pyrefactor --group-by severity src/

# Use more workers for faster analysis
pyrefactor --jobs 8 src/

# Custom configuration file
pyrefactor --config custom.toml src/
```

### Options

- `-c, --config`: Configuration file path; when omitted, auto-discover `pyproject.toml` (`[tool.pyrefactor]`), then `pyrefactor.ini`, then built-in defaults
- `-g, --group-by`: Group by `file` or `severity` (default: `file`)
- `--min-severity`: Minimum severity to report: `info`, `low`, `medium`, `high` (default: `info`). Also filters which issues count toward the exit code.
- `-j, --jobs`: Number of parallel workers (default: 4)
- `-v, --verbose`: Enable verbose logging
- `--fail-on-parse-errors`: Exit with code 1 when any file has a syntax or parse error
- `--version`: Show version

### Exit Codes

Exit codes are computed **after** applying `--min-severity`. For example, `--min-severity high` can exit `0` even when MEDIUM issues exist, because those issues are filtered out before the exit code is determined.

- `0` - No MEDIUM/HIGH severity issues remain after filtering (INFO/LOW only). Per-file syntax or parse errors are reported in output but do not change the exit code unless `--fail-on-parse-errors` is set.
- `1` - MEDIUM/HIGH severity issues remain after filtering, or parse errors when `--fail-on-parse-errors` is used
- `2` - Configuration, path, or orchestration error (invalid paths, missing config, no Python files to analyze)

### Analysis Limits

Files larger than **10 MB** are skipped with a parse-style error message. This limit is fixed and not configurable.

## Configuration

Configure via TOML file (e.g., `pyproject.toml`):

```toml
[tool.pyrefactor]
exclude_patterns = ["__pycache__", ".venv", "build", "dist"]

[tool.pyrefactor.complexity]
enabled = true
max_cyclomatic_complexity = 10
max_branches = 10
max_nesting_depth = 3
max_function_lines = 50
max_arguments = 5
max_local_variables = 15

[tool.pyrefactor.performance]
enabled = true
min_concatenations = 3
min_duplicate_calls = 3

[tool.pyrefactor.boolean_logic]
enabled = true
max_boolean_operators = 3

[tool.pyrefactor.loops]
enabled = true

[tool.pyrefactor.duplication]
enabled = true
min_duplicate_lines = 5
similarity_threshold = 0.85

[tool.pyrefactor.context_manager]
enabled = true

[tool.pyrefactor.control_flow]
enabled = true

[tool.pyrefactor.dict_operations]
enabled = true

[tool.pyrefactor.comparisons]
enabled = true
```

Configuration is searched in: `--config` → `pyproject.toml` → `pyrefactor.ini` → defaults

### INI configuration (`pyrefactor.ini`)

See the repository's [`pyrefactor.ini`](pyrefactor.ini) for a full annotated example with every detector section. A minimal example:

```ini
[complexity]
enabled = true
max_cyclomatic_complexity = 10

[duplication]
enabled = true
min_duplicate_lines = 5
similarity_threshold = 0.85

[general]
exclude_patterns = __pycache__, .venv, build, dist
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for the complete configuration reference.

**Note:** The PyPI package version (`pyproject.toml`) may differ from GitHub release build numbers used for standalone executables.

## CI/CD Integration

### Pre-commit Hook

```yaml
repos:
  - repo: local
    hooks:
      - id: pyrefactor
        name: PyRefactor
        entry: pyrefactor
        language: system
        types: [python]
        args: [--min-severity=medium]
```

### GitHub Actions

Example workflow for consumers (not maintained in this repository):

```yaml
name: Code Quality
on: [push, pull_request]

jobs:
  pyrefactor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install pyrefactor
      - run: pyrefactor --min-severity medium --fail-on-parse-errors src/
```

## Contributing

Contributions are welcome! This project is under a Commercial Restricted License (CRL). For commercial use, contact the copyright holder.

### Development

Install the package with development dependencies:

```bash
pip install -e ".[dev]"
```

Alternatively:

```bash
pip install -e .
pip install -r requirements-dev.txt
```

Run the local verification script (formatting, type checks, lint, security scan, self-lint, and pytest with coverage):

```bash
python scripts/verify.py
```

On Windows you can also use `py scripts/verify.py`. The script uses `sys.executable` and absolute paths so it behaves the same on Windows, macOS, and Linux.

Run tests directly (same suite as verify, without formatting or lint steps):

```bash
pytest
```

1. Follow existing code style (Black, isort)
2. Add tests for new features (>90% coverage)
3. Run type checking and linting

## License

Licensed under the CRL license - see [LICENSE.md](LICENSE.md) for details.
