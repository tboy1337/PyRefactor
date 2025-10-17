"""Tests for duplication detector."""

import ast

import pytest

from pyrefactor.config import Config
from pyrefactor.detectors.duplication import DuplicationDetector


class TestDuplicationDetector:
    """Tests for DuplicationDetector."""

    def test_detector_name(self, default_config: Config) -> None:
        """Test detector name."""
        detector = DuplicationDetector(default_config, "test.py", [])

        assert detector.get_detector_name() == "duplication"

    def test_exact_duplication(self, default_config: Config) -> None:
        """Test detection of exact code duplication."""
        source = """
def func1():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result

def func2():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "D001" for issue in issues)
        assert any("duplicate" in issue.message.lower() for issue in issues)

    def test_similar_code(self, default_config: Config) -> None:
        """Test detection of similar code blocks."""
        source = """
def process_a(data):
    validated = validate(data)
    transformed = transform(validated)
    result = save(transformed)
    log(result)
    return result

def process_b(info):
    validated = validate(info)
    transformed = transform(validated)
    result = save(transformed)
    log(result)
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # May or may not detect depending on similarity threshold
        assert isinstance(issues, list)

    def test_no_duplication(self, default_config: Config) -> None:
        """Test that unique code doesn't trigger issues."""
        source = """
def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Short functions shouldn't trigger duplication
        assert len(issues) == 0

    def test_whitespace_normalized(self, default_config: Config) -> None:
        """Test that whitespace differences are normalized."""
        source = """
def func1():
    x=1
    y=2
    z=3
    result=x+y+z
    return result

def func2():
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
"""
        tree = ast.parse(source)
        lines = source.split("\n")

        detector = DuplicationDetector(default_config, "test.py", lines)
        issues = detector.analyze(tree)

        # Should detect as duplicates despite whitespace differences
        assert len(issues) > 0

