# PyRefactor

A comprehensive Python refactoring and optimization linter that detects code quality issues beyond what traditional linters catch. PyRefactor focuses on identifying refactoring opportunities, performance anti-patterns, and optimization suggestions.

## Features

### Complexity Detection
- Functions with excessive branches (>10 by default)
- Deep nesting levels (>3 by default)
- Long functions (>50 lines by default)
- Too many function arguments (>5 by default)
- Too many local variables (>15 by default)
- High cyclomatic complexity (>10 by default)

### Performance Anti-Patterns
- String concatenation in loops (suggest `str.join()`)
- List concatenation in loops (suggest `list.extend()`)
- Inefficient dictionary key checks (suggest `in dict` instead of `in dict.keys()`)
- Redundant list conversions
- Using `len() > 0` instead of truthiness checks

### Boolean Logic Simplification
- Complex boolean expressions (>3 operators)
- Redundant boolean comparisons (`x == True`)
- De Morgan's law simplification opportunities
- Early return opportunities in nested conditions

### Loop Optimization
- `range(len())` patterns that should use `enumerate()`
- Manual index tracking in loops
- Nested loops that could benefit from dictionary lookups
- Loop-invariant code that should be hoisted

### Code Duplication
- Identical code blocks (>5 lines by default)
- Similar code with minor variations
- Token-based similarity analysis

## Installation

```bash
# Install dependencies
py -m pip install -r requirements.txt

# Install in development mode
py -m pip install -e .
```

## Usage

### Basic Usage

```bash
# Analyze a single file
py -m pyrefactor myfile.py

# Analyze a directory
py -m pyrefactor src/

# Analyze multiple files
py -m pyrefactor file1.py file2.py src/

# Use custom configuration
py -m pyrefactor --config custom.toml src/
```

### Command Line Options

```
usage: pyrefactor [-h] [-c CONFIG] [-g {file,severity}]
                  [--min-severity {info,low,medium,high}]
                  [-j JOBS] [-v] [--version]
                  paths [paths ...]

Options:
  paths                 Python files or directories to analyze
  -c, --config CONFIG   Path to configuration file (default: pyproject.toml)
  -g, --group-by {file,severity}
                        Group output by file or severity (default: file)
  --min-severity {info,low,medium,high}
                        Minimum severity level to report (default: info)
  -j, --jobs JOBS       Number of parallel jobs (default: 4)
  -v, --verbose         Enable verbose logging
  --version             Show version and exit
```

### Exit Codes

- `0` - No issues or only INFO/LOW severity issues
- `1` - MEDIUM or HIGH severity issues found
- `2` - Error during analysis

## Configuration

PyRefactor can be configured via a `pyproject.toml` file:

```toml
[tool.pyrefactor.complexity]
max_branches = 10
max_nesting_depth = 3
max_function_lines = 50
max_arguments = 5
max_local_variables = 15
max_cyclomatic_complexity = 10

[tool.pyrefactor.performance]
enabled = true

[tool.pyrefactor.duplication]
enabled = true
min_duplicate_lines = 5
similarity_threshold = 0.85

[tool.pyrefactor.boolean_logic]
enabled = true
max_boolean_operators = 3

[tool.pyrefactor.loops]
enabled = true

[tool.pyrefactor]
exclude_patterns = ["test_", "__pycache__", ".venv"]
```

## Suppressing Issues

Use inline comments to suppress specific issues:

```python
def long_function():  # pyrefactor: ignore
    # This function is intentionally long
    pass

for i in range(len(items)):  # noqa
    print(items[i])
```

## Rule Reference

### Complexity Rules (C)

- **C001**: Function too long
- **C002**: Too many arguments
- **C003**: Too many local variables
- **C004**: Too many branches
- **C005**: Excessive nesting depth
- **C006**: High cyclomatic complexity

### Performance Rules (P)

- **P001**: String concatenation in loop
- **P002**: List concatenation in loop
- **P003**: Unnecessary dict.keys() call
- **P004**: Redundant list() conversion
- **P005**: Use truthiness instead of len() > 0
- **P006**: Use truthiness instead of len() == 0

### Boolean Logic Rules (B)

- **B001**: Complex boolean expression
- **B002**: Redundant comparison with True
- **B003**: Redundant comparison with False
- **B004**: Using 'is' for boolean comparison
- **B005**: Deeply nested if statements with early exit
- **B006**: Complex negation (De Morgan's law - and)
- **B007**: Complex negation (De Morgan's law - or)

### Loop Rules (L)

- **L001**: Use enumerate() instead of range(len())
- **L002**: Manual index tracking
- **L003**: Nested loops with comparisons
- **L004**: Loop-invariant code

### Duplication Rules (D)

- **D001**: Duplicate code block

## Examples

### Before and After

**Before:**
```python
def process_items(item_list, user_id, admin_flag, debug_mode, log_level, cache):
    result_str = ""
    for i in range(len(item_list)):
        if len(item_list[i]) > 0:
            if admin_flag == True:
                if user_id in cache.keys():
                    result_str += str(item_list[i])
    return result_str
```

**Issues Detected:**
- C002: Too many arguments (6, max 5)
- P001: String concatenation in loop
- P005: Use truthiness instead of len() > 0
- P003: Unnecessary dict.keys() call
- B002: Redundant comparison with True
- L001: Use enumerate() instead of range(len())

**After:**
```python
def process_items(item_list, context):
    if not (context.admin_flag and context.user_id in context.cache):
        return ""

    return ", ".join(
        str(item)
        for item in item_list
        if item
    )
```

## Development

### Running Tests

```bash
# Run all tests
py -m pytest

# Run with coverage
py -m pytest --cov=src/pyrefactor --cov-report=html

# Run specific test file
py -m pytest tests/test_complexity_detector.py

# Run in parallel
py -m pytest -n auto
```

### Code Quality

```bash
# Run mypy
py -m mypy src/pyrefactor

# Run pylint
py -m pylint src/pyrefactor > pylint_output.txt

# Run black
py -m black src/ tests/

# Run isort
py -m isort src/ tests/

# Remove trailing whitespace
py -m autopep8 --in-place --select=W291,W293 src/ tests/
```

### Running PyRefactor on Itself

```bash
py -m pyrefactor src/pyrefactor/
```

## Architecture

PyRefactor uses a modular architecture with the following components:

- **AST Visitors**: Traverse Python's Abstract Syntax Tree to analyze code
- **Detectors**: Individual modules for different analysis types
- **Analyzer**: Orchestrates detectors and manages parallel processing
- **Reporter**: Formats and displays results
- **Config**: Manages configuration from TOML files

## Contributing

Contributions are welcome! Please ensure:

1. All tests pass
2. Code coverage remains >90%
3. Mypy type checking passes with strict settings
4. Pylint reports no errors
5. Code is formatted with black and isort

## License

Copyright 2025 tboy1337

## Author

tboy1337

