# PyRefactor Configuration

PyRefactor supports TOML and INI configuration formats. Settings control which detectors run, their thresholds, and which paths to skip.

## Discovery Order

When you run `pyrefactor`, configuration is loaded in this order:

1. **`--config` path** — if provided, load that file (`.toml`/`.tml` as TOML, otherwise INI)
2. **`pyproject.toml`** in the current working directory — only if a non-empty `[tool.pyrefactor]` section exists
3. **`pyrefactor.ini`** in the current working directory
4. **Built-in defaults** — used when no config file is found

After loading, all values are validated. Invalid settings (negative thresholds, out-of-range similarity, and so on) raise an error at startup.

When you pass `--config`, the path must exist. A missing explicit config file raises an error instead of silently falling back to defaults. Auto-discovery still uses built-in defaults only when no config file is found in the search order above.

## TOML Format (`pyproject.toml`)

Add a `[tool.pyrefactor]` section to your project's `pyproject.toml`:

```toml
[tool.pyrefactor]
exclude_patterns = ["__pycache__", ".venv", "build", "dist", "tests/*"]

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

[tool.pyrefactor.duplication]
enabled = true
min_duplicate_lines = 5
similarity_threshold = 0.85

[tool.pyrefactor.boolean_logic]
enabled = true
max_boolean_operators = 3

[tool.pyrefactor.loops]
enabled = true

[tool.pyrefactor.context_manager]
enabled = true

[tool.pyrefactor.control_flow]
enabled = true

[tool.pyrefactor.dict_operations]
enabled = true

[tool.pyrefactor.comparisons]
enabled = true
```

The duplication detector also applies fixed scan limits (first 5,000 lines per file, block size up to 20 lines). See [RULES.md](RULES.md#duplication-d001).

`exclude_patterns` uses glob-style patterns matched against file paths (POSIX-style, forward slashes).

## INI Format (`pyrefactor.ini`)

Alternatively, use a standalone INI file. See the repository's [`pyrefactor.ini`](../pyrefactor.ini) for a full annotated example:

```ini
[complexity]
enabled = true
max_cyclomatic_complexity = 10

[performance]
enabled = true
min_concatenations = 3

[duplication]
enabled = true
min_duplicate_lines = 5
similarity_threshold = 0.85

[general]
exclude_patterns = __pycache__, .venv, build, dist
```

In INI files, `exclude_patterns` under `[general]` is a comma-separated list.

## Detector Sections

| Section | Key settings |
|---------|--------------|
| `complexity` | `max_branches`, `max_nesting_depth`, `max_function_lines`, `max_arguments`, `max_local_variables`, `max_cyclomatic_complexity` |
| `performance` | `min_concatenations`, `min_duplicate_calls` |
| `duplication` | `min_duplicate_lines` (minimum 2), `similarity_threshold` (0.0–1.0) |
| `boolean_logic` | `max_boolean_operators` |
| `loops` | `enabled` only |
| `context_manager` | `enabled` only |
| `control_flow` | `enabled` only |
| `dict_operations` | `enabled` only |
| `comparisons` | `enabled` only |

Each section supports `enabled = true|false` to turn a detector on or off.

## Suppression Comments

Per-line suppressions are supported in source files:

```python
x = foo()  # pyrefactor: ignore C001
y = bar()  # pyrefactor: ignore
z = baz()  # noqa
```

See [RULES.md](RULES.md) for the full rule catalog and suppression syntax.

## CLI Overrides

The CLI does not override individual detector thresholds. Use `--config` to point at a custom file, or `--min-severity` to filter reported issues without changing detection.

Use `--fail-on-parse-errors` when integrating PyRefactor into CI: by default, syntax and parse errors are reported but do not affect the exit code; with this flag, any parse error causes exit code `1`.

## Related Documentation

- [RULES.md](RULES.md) — rule IDs, severities, and examples
- [README.md](../README.md) — installation, usage, and CI integration
