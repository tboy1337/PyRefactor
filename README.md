# PyRefactor

A powerful Python refactoring and optimization linter that analyzes your code for performance issues, complexity problems, and opportunities for improvement.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

## Overview

PyRefactor uses Abstract Syntax Tree (AST) analysis to identify code patterns that can be refactored for better performance, readability, and maintainability. It provides actionable insights with severity levels and detailed explanations for each detected issue.

## Features

- **Multi-threaded Analysis**: Analyze multiple files in parallel for faster results
- **Configurable Detectors**: Enable or disable specific detectors based on your needs
- **Severity Levels**: Issues categorized as INFO, LOW, MEDIUM, or HIGH severity
- **Multiple Output Formats**: Group results by file or severity level
- **Flexible Configuration**: Configure via `pyproject.toml`, custom config files, or command-line arguments
- **Cross-platform**: Works on Windows, macOS, and Linux

## Detectors

PyRefactor includes the following specialized detectors:

### Complexity Detector
Identifies functions and methods with high cyclomatic complexity that should be refactored for better maintainability.

### Performance Detector
Finds performance anti-patterns including:
- Inefficient string concatenation in loops
- Multiple function calls that could be cached
- Inefficient list operations
- Unnecessary comprehensions

### Boolean Logic Detector
Detects overcomplicated boolean expressions and suggests simplifications:
- Complex conditional chains
- Redundant boolean operations
- Opportunities for boolean algebra simplification

### Loops Detector
Identifies loop-related issues:
- Nested loops that could be optimized
- Loop invariant code that should be hoisted
- Loops that could be replaced with comprehensions or built-in functions

### Duplication Detector
Finds duplicated code blocks that should be extracted into reusable functions.

### Context Manager Detector
Detects resource-allocating operations that should use `with` statements:
- File operations (`open()`, etc.)
- Lock acquisitions
- Context managers not used properly
- **Impact**: Prevents resource leaks and ensures proper cleanup

### Control Flow Detector
Identifies unnecessary control flow patterns:
- Unnecessary `else` after `return` statement
- Unnecessary `else` after `raise` statement
- Unnecessary `else` after `break` statement
- Unnecessary `else` after `continue` statement
- **Impact**: Reduces nesting and improves code readability

### Dictionary Operations Detector
Finds inefficient or non-idiomatic dictionary operations:
- Opportunities to use `dict.get(key, default)` instead of if/else
- Unnecessary `.keys()` calls when iterating
- Loops that should use `.items()` instead of indexing
- Opportunities for dictionary comprehensions
- **Impact**: More Pythonic and performant code

### Comparisons Detector
Detects non-idiomatic comparison patterns:
- Multiple `==` comparisons that could use `in` operator
- Comparisons that could be chained (e.g., `a < b < c`)
- Singleton comparisons with `==` instead of `is` (for `None`, `True`, `False`)
- Using `type()` instead of `isinstance()` for type checking
- **Impact**: Cleaner, more idiomatic code

## Installation

### From Source

```powershell
# Clone the repository
git clone https://github.com/tboy1337/PyRefactor.git
cd PyRefactor

# Install dependencies
py -m pip install -r requirements.txt

# Install in development mode
py -m pip install -e .
```

### Requirements

- Python 3.13 or higher
- colorama (for colored console output)

## Usage

### Basic Usage

```powershell
# Analyze a single file
pyrefactor myfile.py

# Analyze a directory
pyrefactor src/

# Analyze multiple files
pyrefactor file1.py file2.py src/module.py

# Analyze with custom configuration
pyrefactor --config custom.toml src/
```

### Command-line Options

```
positional arguments:
  paths                 Python files or directories to analyze

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to configuration file (default: pyproject.toml)
  -g {file,severity}, --group-by {file,severity}
                        Group output by file or severity (default: file)
  --min-severity {info,low,medium,high}
                        Minimum severity level to report (default: info)
  -j JOBS, --jobs JOBS  Number of parallel jobs (default: 4)
  -v, --verbose         Enable verbose logging
  --version             Show version and exit
```

### Examples

```powershell
# Show only HIGH and MEDIUM severity issues
pyrefactor --min-severity medium src/

# Group results by severity level
pyrefactor --group-by severity src/

# Use 8 parallel workers for faster analysis
pyrefactor --jobs 8 large_project/

# Verbose output with detailed logging
pyrefactor -v src/
```

### Exit Codes

PyRefactor uses the following exit codes:

- `0` - No issues found, or only INFO/LOW severity issues
- `1` - MEDIUM or HIGH severity issues found
- `2` - Error during analysis (syntax errors, invalid paths, etc.)

This makes PyRefactor suitable for use in CI/CD pipelines where you can fail builds based on code quality issues.

## Configuration

PyRefactor can be configured using a TOML configuration file. By default, it looks for configuration in `pyproject.toml` or a file specified with `--config`.

### Example Configuration

```toml
[tool.pyrefactor]
# Patterns to exclude from analysis
exclude_patterns = [
    "__pycache__",
    ".venv",
    "venv",
    ".git",
    "build",
    "dist",
]

[tool.pyrefactor.complexity]
# Maximum allowed cyclomatic complexity
max_complexity = 10

[tool.pyrefactor.performance]
enabled = true
# Minimum number of string concatenations to report
min_concatenations = 3
# Minimum number of duplicate calls to report
min_duplicate_calls = 3

[tool.pyrefactor.boolean_logic]
enabled = true
# Minimum depth of nested boolean expressions to report
min_depth = 3

[tool.pyrefactor.loops]
enabled = true
# Maximum allowed nesting depth for loops
max_nesting = 3

[tool.pyrefactor.duplication]
enabled = true
# Minimum number of lines for a code block to be considered for duplication detection
min_lines = 5
# Minimum similarity threshold (0.0 to 1.0)
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

### Configuration File Location

PyRefactor searches for configuration in the following order:

1. Path specified with `--config` option
2. `pyproject.toml` in the current directory
3. `pyrefactor.ini` in the current directory
4. Default configuration values

## Integration

### Pre-commit Hook

Add PyRefactor to your `.pre-commit-config.yaml`:

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

### CI/CD Integration

#### GitHub Actions

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  pyrefactor:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          py -m pip install --upgrade pip
          py -m pip install pyrefactor
      - name: Run PyRefactor
        run: pyrefactor --min-severity medium src/
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'pyrefactor'`

**Solution**: Make sure PyRefactor is installed: `py -m pip install -e .`

---

**Issue**: Syntax errors when analyzing Python 3.12 or older code

**Solution**: PyRefactor requires Python 3.13+. Ensure your environment is using Python 3.13 or newer.

---

**Issue**: Analysis is slow on large codebases

**Solution**: Increase the number of parallel workers: `pyrefactor --jobs 8 src/`

## Contributing

Contributions are welcome! Please note that this project is under a Commercial Restricted License (CRL). For commercial use, please contact the copyright holder.

### Guidelines

1. Follow the existing code style (Black, isort)
2. Add tests for new features
3. Ensure all tests pass and coverage remains >95%
4. Update documentation as needed
5. Run type checking and linting before submitting

## License

This project is licensed under the CRL license - see [LICENSE.md](LICENSE.md) for details.
