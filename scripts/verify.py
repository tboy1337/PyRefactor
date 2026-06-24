#!/usr/bin/env python3
"""Local verification pipeline for PyRefactor development.

Runs the full quality gate locally on Windows, macOS, and Linux using only
``sys.executable`` (no shell), so path and quoting behavior is consistent
across platforms.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
PACKAGE = SRC / "pyrefactor"
PYLINT_REPORT = ROOT / "pylint-report.txt"


def _python_module(*args: str) -> list[str]:
    """Build a ``python -m ...`` command without invoking a shell."""
    return [sys.executable, "-m", *args]


def _path(path: Path) -> str:
    """Return a path string safe to pass as a subprocess argument."""
    return str(path)


def _editable_install_target() -> str:
    """Return an absolute editable-install target with dev extras.

    Using an absolute path avoids platform/shell quirks with ``.[dev]`` when
    the working directory or shell metacharacters differ between OSes.
    """
    return f"{ROOT}[dev]"


def _ensure_project_root() -> None:
    """Fail fast when the script is not run from a PyRefactor checkout."""
    if not (ROOT / "pyproject.toml").is_file():
        print(f"ERROR: Expected pyproject.toml in {ROOT}", file=sys.stderr)
        sys.exit(2)


def run_step(
    name: str,
    command: list[str],
    *,
    optional: bool = False,
    cwd: Path = ROOT,
) -> bool:
    """Run a verification step and return True on success."""
    print(f"\n{'=' * 70}")
    print(f"STEP: {name}")
    print(f"CMD:  {' '.join(command)}")
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
    )
    if result.returncode != 0:
        label = "WARNING" if optional else "FAILED"
        print(f"\n[{label}] {name} (exit code {result.returncode})")
        return optional
    print(f"\n[OK] {name}")
    return True


def run_pylint() -> bool:
    """Run pylint and write the full report to ``pylint-report.txt``.

    Capturing output in Python avoids pylint ``--output`` path quirks on Windows
    and differences between pylint versions.
    """
    name = "Pylint static analysis"
    command = _python_module("pylint", _path(PACKAGE), "--output-format=text")
    print(f"\n{'=' * 70}")
    print(f"STEP: {name}")
    print(f"CMD:  {' '.join(command)}")
    print(f"REPORT: {PYLINT_REPORT}")
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report_body = (result.stdout or "") + (result.stderr or "")
    PYLINT_REPORT.write_text(report_body, encoding="utf-8", newline="\n")

    if result.returncode != 0:
        print(f"\n[FAILED] {name} (exit code {result.returncode})")
        if report_body.strip():
            tail = report_body.strip().splitlines()[-8:]
            print("Last pylint output:")
            for line in tail:
                print(f"  {line}")
        return False

    print(f"\n[OK] {name}")
    return True


def main() -> int:
    """Run the full local verification pipeline."""
    _ensure_project_root()
    failures: list[str] = []

    steps: list[tuple[str, list[str], bool]] = [
        (
            "Editable install with dev dependencies",
            _python_module("pip", "install", "-e", _editable_install_target()),
            False,
        ),
        (
            "Trailing whitespace cleanup (autopep8)",
            _python_module(
                "autopep8",
                "--in-place",
                "--recursive",
                "--select=W291,W293",
                _path(SRC),
                _path(TESTS),
            ),
            False,
        ),
        (
            "Black formatting",
            _python_module("black", "--check", _path(SRC), _path(TESTS)),
            False,
        ),
        (
            "Import sorting (isort)",
            _python_module("isort", "--check-only", _path(SRC), _path(TESTS)),
            False,
        ),
        (
            "Mypy type checking",
            _python_module("mypy", _path(SRC)),
            False,
        ),
        (
            "Bandit security scan",
            _python_module("bandit", "-r", _path(PACKAGE)),
            False,
        ),
        (
            "Safety dependency check",
            _python_module("safety", "check"),
            True,
        ),
        (
            "Pytest with coverage",
            _python_module("pytest"),
            False,
        ),
    ]

    for name, command, optional in steps[:5]:
        if not run_step(name, command, optional=optional):
            if not optional:
                failures.append(name)

    if not run_pylint():
        failures.append("Pylint static analysis")

    for name, command, optional in steps[5:]:
        if not run_step(name, command, optional=optional):
            if not optional:
                failures.append(name)

    print(f"\n{'=' * 70}")
    if failures:
        print("VERIFICATION FAILED")
        for failure in failures:
            print(f"  - {failure}")
        print("=" * 70)
        return 1

    print("VERIFICATION PASSED")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
