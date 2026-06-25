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
    """Lock.acquire() is not a context manager and should not be flagged."""
    code = """
import threading
lock = threading.Lock()
lock.acquire()
try:
    pass
finally:
    lock.release()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


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


def test_path_open_method(detector: ContextManagerDetector) -> None:
    """Test detection of Path.open() without with statement."""
    code = """
from pathlib import Path
handle = Path("file.txt").open()
handle.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"
    assert "open" in issues[0].message.lower()


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


def test_detector_name(detector: ContextManagerDetector) -> None:
    """Test detector name."""
    assert detector.get_detector_name() == "context_manager"


def test_open_in_with_context(detector: ContextManagerDetector) -> None:
    """Test that open() already in with context is not flagged."""
    code = """
with open('file.txt') as f:
    data = f.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_non_context_manager_attribute_call(detector: ContextManagerDetector) -> None:
    """Test that non-context-manager attribute calls are not flagged."""
    code = """
obj = MyClass()
result = obj.process()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_expr_with_suppression(detector: ContextManagerDetector) -> None:
    """Test Expr statement with suppression."""
    code = """
# pyrefactor: ignore
open('file.txt').read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_open_in_return_not_flagged(detector: ContextManagerDetector) -> None:
    """Test open() used in return context is not flagged."""
    code = """
def read_file():
    return open('file.txt')
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_zipfile_without_with(detector: ContextManagerDetector) -> None:
    """Test detection of ZipFile() without with statement."""
    code = """
from zipfile import ZipFile
archive = ZipFile('data.zip')
archive.read('entry.txt')
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"
    assert "ZipFile" in issues[0].message


def test_unknown_call_target_not_flagged(detector: ContextManagerDetector) -> None:
    """Test calls with non-name/non-attribute func are not flagged."""
    code = """
(get_opener())('http://example.com')
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_path_open_method_call(detector: ContextManagerDetector) -> None:
    """Test Path.open() without with is flagged."""
    code = """
from pathlib import Path

def read_data():
    f = Path('file.txt').open()
    return f.read()
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R001"
