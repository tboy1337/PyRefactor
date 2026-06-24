# PyRefactor Rule Catalog

This document lists every rule ID emitted by PyRefactor detectors, grouped by category.

## Complexity (C001–C006)

| Rule | Severity | Description |
|------|----------|-------------|
| C001 | MEDIUM | Function exceeds maximum line count |
| C002 | MEDIUM | Function has too many parameters |
| C003 | LOW | Function has too many local variables |
| C004 | MEDIUM | Function has too many branches |
| C005 | MEDIUM | Function exceeds maximum nesting depth |
| C006 | MEDIUM | Function exceeds maximum cyclomatic complexity |

Configurable thresholds live under `[tool.pyrefactor.complexity]` or `[complexity]` in `pyrefactor.ini`.

## Performance (P001–P007)

| Rule | Severity | Description |
|------|----------|-------------|
| P001 | MEDIUM | Repeated string `+=` concatenation inside a loop |
| P002 | LOW | List `+=` concatenation inside a loop |
| P004 | INFO | Redundant `list()` around a list comprehension |
| P005 | INFO | Use truthiness instead of `len(x) > 0` |
| P006 | INFO | Use truthiness instead of `len(x) == 0` |
| P007 | MEDIUM | Repeated identical call expressions inside a loop |

P001 uses naming heuristics and tracks variables initialized with string constants. P003 was removed; dict `.keys()` membership is covered by R009.

## Boolean Logic (B001, B004–B007)

| Rule | Severity | Description |
|------|----------|-------------|
| B001 | MEDIUM | Boolean expression has too many `and`/`or` operators |
| B004 | LOW | Compare singleton booleans with `is` / `is not` |
| B005 | MEDIUM | Nested `if` can be flattened into a guard clause |
| B006 | LOW | De Morgan simplification opportunity (`not (a and b)`) |
| B007 | LOW | De Morgan simplification opportunity (`not (a or b)`) |

B002/B003 are intentionally not used; boolean `== True`/`== False` checks are reported as R015 by the comparisons detector.

## Loops (L001–L004)

| Rule | Severity | Description |
|------|----------|-------------|
| L001 | LOW | `for i in range(len(seq))` should use `enumerate()` |
| L002 | LOW | Manual index increment pattern (`i += 1`) |
| L003 | MEDIUM | Deeply nested loops with comparisons |
| L004 | MEDIUM | Loop-invariant expensive call inside loop body |

## Duplication (D001)

| Rule | Severity | Description |
|------|----------|-------------|
| D001 | MEDIUM | Similar duplicate code block detected in the same file |

## Context Manager (R001)

| Rule | Severity | Description |
|------|----------|-------------|
| R001 | HIGH | Resource-allocating call should use a `with` statement |

Covers `open`, `urlopen`, `ZipFile`, `Popen`, `Path.open()`, and related APIs.

## Control Flow (R002–R005)

| Rule | Severity | Description |
|------|----------|-------------|
| R002 | MEDIUM | Unnecessary `else`/`elif` after `return` |
| R003 | MEDIUM | Unnecessary `else`/`elif` after `raise` |
| R004 | MEDIUM | Unnecessary `else`/`elif` after `break` |
| R005 | MEDIUM | Unnecessary `else`/`elif` after `continue` |

## Dictionary Operations (R006, R007, R009, R010)

| Rule | Severity | Description |
|------|----------|-------------|
| R006 | LOW | `if key in d: x = d[key] else: x = default` should use `.get()` |
| R007 | LOW | Unnecessary `.keys()` in a `for` loop |
| R009 | LOW | Unnecessary `.keys()` in a membership test |
| R010 | LOW | `dict([...])` should be a dict comprehension |

R008 is reserved and not currently implemented.

## Comparisons (R011–R016)

| Rule | Severity | Description |
|------|----------|-------------|
| R011 | LOW | Multiple `==` comparisons can use `in` |
| R012 | LOW | Separate comparisons can be chained (`a < b and b < c`) |
| R013 | LOW | Multiple `isinstance` checks can be combined |
| R014 | MEDIUM | Compare `None` with `is` / `is not`, not `==` / `!=` |
| R015 | INFO | Redundant comparison with `True` or `False` |
| R016 | MEDIUM | Prefer `isinstance()` over `type() ==` |

## Suppression

Suppress a finding on the same line or the line above:

```python
x = 1  # pyrefactor: ignore
x = 1  # pyrefactor: ignore R001
x = 1  # pyrefactor: ignore R001, R002
# pyrefactor: ignore
y = 2
```

`# noqa` is also accepted (suppresses all rules on that line).

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No MEDIUM/HIGH issues (after severity filter) |
| 1 | One or more MEDIUM/HIGH issues found |
| 2 | Configuration, path, or analysis error (including no Python files to analyze) |
