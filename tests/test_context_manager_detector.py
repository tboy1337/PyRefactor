"""Tests for context manager detector."""

import ast

import pytest

from pyrefactor.config import Config
from pyrefactor.detectors.context_manager import ContextManagerDetector
from pyrefactor.models import Severity


@pytest.fixture
def detector() -> ContextManagerDetector:
    """Create a context manager detector instance."""
    config = Config()
    return ContextManagerDetector(config, "test.py", [])


def test_open_without_with(detector: ContextManagerDetector) -> None:
    """Test detection of open() without with statement."""
    code = """
f = open('file.txt')
data = f.read()
f.close()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"
    assert issues[0].severity == Severity.HIGH
    assert "open" in issues[0].message.lower()
    assert "with" in issues[0].suggestion.lower()


def test_open_with_with_statement(detector: ContextManagerDetector) -> None:
    """Test that open() with 'with' statement is not flagged."""
    code = """
with open('file.txt') as f:
    data = f.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_open_in_return(detector: ContextManagerDetector) -> None:
    """Test that open() in return statement is not flagged."""
    code = """
def get_file():
    return open('file.txt')
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should not flag - returning the context manager is valid
    assert len(issues) == 0


def test_multiple_resource_allocations(detector: ContextManagerDetector) -> None:
    """Test detection of multiple resource allocations."""
    code = """
f1 = open('file1.txt')
f2 = open('file2.txt')
data = f1.read() + f2.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 2
    assert all(issue.rule_id == "R001" for issue in issues)


def test_method_call_acquire(detector: ContextManagerDetector) -> None:
    """Test detection of lock.acquire() without with statement."""
    code = """
import threading
lock = threading.Lock()
lock.acquire()
try:
    # critical section
    pass
finally:
    lock.release()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"
    assert "acquire" in issues[0].message.lower()


def test_suppression_comment(detector: ContextManagerDetector) -> None:
    """Test that suppression comments are respected."""
    code = """
# pyrefactor: ignore
f = open('file.txt')
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_urlopen_without_with(detector: ContextManagerDetector) -> None:
    """Test detection of urlopen() without with statement."""
    code = """
from urllib.request import urlopen
response = urlopen('http://example.com')
data = response.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"


def test_expr_statement_open(detector: ContextManagerDetector) -> None:
    """Test detection of open() as expression statement."""
    code = """
open('file.txt').read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"


def test_popen_without_with(detector: ContextManagerDetector) -> None:
    """Test detection of Popen() without with statement."""
    code = """
from subprocess import Popen
proc = Popen(['ls', '-l'])
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"
    assert "Popen" in issues[0].message


def test_nested_with_statements(detector: ContextManagerDetector) -> None:
    """Test that nested with statements are not flagged."""
    code = """
with open('file1.txt') as f1:
    with open('file2.txt') as f2:
        data = f1.read() + f2.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_multiple_with_items(detector: ContextManagerDetector) -> None:
    """Test that multiple items in with statement are not flagged."""
    code = """
with open('file1.txt') as f1, open('file2.txt') as f2:
    data = f1.read() + f2.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0
