"""Tests for complexity detector."""

import ast

import pytest

from pyrefactor.config import Config
from pyrefactor.detectors.complexity import ComplexityDetector
from pyrefactor.models import Severity


class TestComplexityDetector:
    """Tests for ComplexityDetector."""

    def test_detector_name(self, default_config: Config) -> None:
        """Test detector name."""
        detector = ComplexityDetector(default_config, "test.py", [])

        assert detector.get_detector_name() == "complexity"

    def test_long_function(self, default_config: Config) -> None:
        """Test detection of long functions."""
        code = "\n".join([f"    x = {i}" for i in range(60)])
        source = f"def long_func():\n{code}\n    return x"
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C001" for issue in issues)
        assert any("too long" in issue.message.lower() for issue in issues)

    def test_too_many_arguments(self, default_config: Config) -> None:
        """Test detection of too many arguments."""
        source = "def many_args(a, b, c, d, e, f, g):\n    pass"
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C002" for issue in issues)
        assert any("too many arguments" in issue.message.lower() for issue in issues)

    def test_method_excludes_self(self, default_config: Config) -> None:
        """Test that 'self' is excluded from argument count."""
        source = """
class MyClass:
    def method(self, a, b, c, d, e):
        pass
"""
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger too many arguments (5 + self = 6, but self excluded)
        assert not any(issue.rule_id == "C002" for issue in issues)

    def test_too_many_local_variables(self, default_config: Config) -> None:
        """Test detection of too many local variables."""
        assignments = "\n".join([f"    var{i} = {i}" for i in range(20)])
        source = f"def many_vars():\n{assignments}\n    return var0"
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C003" for issue in issues)
        assert any("too many local variables" in issue.message.lower() for issue in issues)

    def test_too_many_branches(self, default_config: Config) -> None:
        """Test detection of too many branches."""
        source = """
def many_branches(x):
    if x == 1:
        return 1
    elif x == 2:
        return 2
    elif x == 3:
        return 3
    elif x == 4:
        return 4
    elif x == 5:
        return 5
    elif x == 6:
        return 6
    elif x == 7:
        return 7
    elif x == 8:
        return 8
    elif x == 9:
        return 9
    elif x == 10:
        return 10
    else:
        return 0
"""
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C004" for issue in issues)
        assert any("too many branches" in issue.message.lower() for issue in issues)

    def test_excessive_nesting(self, default_config: Config) -> None:
        """Test detection of excessive nesting."""
        source = """
def nested(x, y, z, w):
    if x:
        if y:
            if z:
                if w:
                    return True
    return False
"""
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C005" for issue in issues)
        assert any("nesting depth" in issue.message.lower() for issue in issues)

    def test_high_cyclomatic_complexity(self, default_config: Config) -> None:
        """Test detection of high cyclomatic complexity."""
        source = """
def complex(x, y):
    if x and y:
        if x > 0:
            if y > 0:
                for i in range(10):
                    if i > 5:
                        while i < 8:
                            if i == 7:
                                return True
                            i += 1
    return False
"""
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C006" for issue in issues)
        assert any("cyclomatic complexity" in issue.message.lower() for issue in issues)

    def test_suppression_comment(self, default_config: Config) -> None:
        """Test that suppression comments work."""
        source = """
def long_func():  # pyrefactor: ignore
"""
        source += "\n".join([f"    x = {i}" for i in range(60)])
        source += "\n    return x"

        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should be suppressed
        assert len(issues) == 0

    def test_async_function(self, default_config: Config) -> None:
        """Test detection works for async functions."""
        code = "\n".join([f"    x = {i}" for i in range(60)])
        source = f"async def long_func():\n{code}\n    return x"
        tree = ast.parse(source)

        detector = ComplexityDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "C001" for issue in issues)

