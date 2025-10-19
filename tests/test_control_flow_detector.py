"""Tests for control flow detector."""

import ast

import pytest

from pyrefactor.config import Config
from pyrefactor.detectors.control_flow import ControlFlowDetector
from pyrefactor.models import Severity


@pytest.fixture
def detector() -> ControlFlowDetector:
    """Create a control flow detector instance."""
    config = Config()
    return ControlFlowDetector(config, "test.py", [])


def test_else_after_return(detector: ControlFlowDetector) -> None:
    """Test detection of unnecessary else after return."""
    code = """
def func(x):
    if x > 0:
        return True
    else:
        return False
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R002"
    assert issues[0].severity == Severity.MEDIUM
    assert "return" in issues[0].message.lower()
    assert "else" in issues[0].message.lower()


def test_elif_after_return(detector: ControlFlowDetector) -> None:
    """Test detection of unnecessary elif after return."""
    code = """
def func(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R002"
    assert "elif" in issues[0].message.lower()


def test_no_else_no_issue(detector: ControlFlowDetector) -> None:
    """Test that if without else is not flagged."""
    code = """
def func(x):
    if x > 0:
        return True
    return False
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_else_after_raise(detector: ControlFlowDetector) -> None:
    """Test detection of unnecessary else after raise."""
    code = """
def func(x):
    if x < 0:
        raise ValueError("Negative value")
    else:
        return x * 2
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R003"
    assert "raise" in issues[0].message.lower()


def test_else_after_break(detector: ControlFlowDetector) -> None:
    """Test detection of unnecessary else after break."""
    code = """
def func():
    for i in range(10):
        if i > 5:
            break
        else:
            print(i)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R004"
    assert "break" in issues[0].message.lower()


def test_else_after_continue(detector: ControlFlowDetector) -> None:
    """Test detection of unnecessary else after continue."""
    code = """
def func():
    for i in range(10):
        if i % 2 == 0:
            continue
        else:
            print(i)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R005"
    assert "continue" in issues[0].message.lower()


def test_nested_if_all_return(detector: ControlFlowDetector) -> None:
    """Test nested if statements where all branches return."""
    code = """
def func(x, y):
    if x > 0:
        if y > 0:
            return 1
        else:
            return 2
    else:
        return 0
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should flag the outer else (inner if/else both return, then outer else is unnecessary)
    assert len(issues) >= 1
    assert any(issue.rule_id == "R002" for issue in issues)


def test_else_needed_not_all_return(detector: ControlFlowDetector) -> None:
    """Test that else is not flagged if if-body doesn't always return."""
    code = """
def func(x):
    if x > 0:
        print("positive")
    else:
        return False
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_try_except_with_returns(detector: ControlFlowDetector) -> None:
    """Test try/except blocks with returns."""
    code = """
def func():
    try:
        return do_something()
    except Exception:
        return None
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # No else clause, so no issue
    assert len(issues) == 0


def test_suppression_comment(detector: ControlFlowDetector) -> None:
    """Test that suppression comments are respected."""
    code = """
def func(x):
    # pyrefactor: ignore
    if x > 0:
        return True
    else:
        return False
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_complex_control_flow(detector: ControlFlowDetector) -> None:
    """Test complex control flow with multiple returns."""
    code = """
def func(x, y, z):
    if x > 0:
        return "positive x"
    else:
        if y > 0:
            return "positive y"
        else:
            if z > 0:
                return "positive z"
            else:
                return "all negative"
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should flag multiple unnecessary else clauses
    assert len(issues) >= 1
    assert all(issue.rule_id == "R002" for issue in issues)


def test_else_with_non_terminating_code(detector: ControlFlowDetector) -> None:
    """Test that else with non-terminating code in if is not flagged."""
    code = """
def func(x):
    if x > 0:
        x = x + 1
    else:
        return x
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0
