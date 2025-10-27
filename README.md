# PyRefactor

A Python refactoring and optimization linter that uses AST analysis to identify performance issues, complexity problems, and code improvements.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Multi-threaded Analysis**: Fast parallel file processing
- **Configurable Detectors**: Enable/disable specific detectors
- **Severity Levels**: Issues categorized as INFO, LOW, MEDIUM, or HIGH
- **Flexible Output**: Group by file or severity
- **Cross-platform**: Works on Windows, macOS, and Linux

## Detectors

- **Complexity**: High cyclomatic complexity functions
- **Performance**: String concatenation in loops, uncached calls, inefficient operations
- **Boolean Logic**: Overcomplicated boolean expressions
- **Loops**: Nested loops, invariant code, comprehension opportunities
- **Duplication**: Duplicate code blocks
- **Context Manager**: Missing `with` statements for resource operations
- **Control Flow**: Unnecessary `else` after `return`/`raise`/`break`/`continue`
- **Dictionary Operations**: Non-idiomatic dict patterns, missing `.get()`, unnecessary `.keys()`
- **Comparisons**: Chained comparisons, singleton checks, `type()` vs `isinstance()`

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

**Requirements**: Python 3.9+

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

- `-c, --config`: Configuration file path (default: `pyproject.toml`)
- `-g, --group-by`: Group by `file` or `severity` (default: `file`)
- `--min-severity`: Minimum severity to report: `info`, `low`, `medium`, `high` (default: `info`)
- `-j, --jobs`: Number of parallel workers (default: 4)
- `-v, --verbose`: Enable verbose logging
- `--version`: Show version

### Exit Codes

- `0` - No issues or only INFO/LOW severity
- `1` - MEDIUM/HIGH severity issues found
- `2` - Analysis error (syntax errors, invalid paths)

## Configuration

Configure via TOML file (e.g., `pyproject.toml`):

```toml
[tool.pyrefactor]
exclude_patterns = ["__pycache__", ".venv", "build", "dist"]

[tool.pyrefactor.complexity]
max_complexity = 10

[tool.pyrefactor.performance]
enabled = true
min_concatenations = 3
min_duplicate_calls = 3

[tool.pyrefactor.boolean_logic]
enabled = true
min_depth = 3

[tool.pyrefactor.loops]
enabled = true
max_nesting = 3

[tool.pyrefactor.duplication]
enabled = true
min_lines = 5
similarity_threshold = 0.8

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

```yaml
name: Code Quality
on: [push, pull_request]

jobs:
  pyrefactor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install pyrefactor
      - run: pyrefactor --min-severity medium src/
```

## Contributing

Contributions are welcome! This project is under a Commercial Restricted License (CRL). For commercial use, contact the copyright holder.

1. Follow existing code style (Black, isort)
2. Add tests for new features (>95% coverage)
3. Run type checking and linting

## License

Licensed under the CRL license - see [LICENSE.md](LICENSE.md) for details.
