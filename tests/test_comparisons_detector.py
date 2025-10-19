"""Tests for comparisons detector."""

import ast

import pytest

from pyrefactor.config import Config
from pyrefactor.detectors.comparisons import ComparisonsDetector
from pyrefactor.models import Severity


@pytest.fixture
def detector() -> ComparisonsDetector:
    """Create a comparisons detector instance."""
    config = Config()
    return ComparisonsDetector(config, "test.py", [])


def test_consider_using_in(detector: ComparisonsDetector) -> None:
    """Test detection of multiple == comparisons that could use 'in'."""
    code = """
if x == 1 or x == 2 or x == 3:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R011"
    assert issues[0].severity == Severity.LOW
    assert "in" in issues[0].suggestion.lower()


def test_using_in_already(detector: ComparisonsDetector) -> None:
    """Test that 'in' operator is not flagged."""
    code = """
if x in (1, 2, 3):
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_chained_comparison_opportunity(detector: ComparisonsDetector) -> None:
    """Test detection of chainable comparisons."""
    code = """
if a < b and b < c:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R012"
    assert issues[0].severity == Severity.LOW
    assert "chain" in issues[0].message.lower()


def test_chained_comparison_already_used(detector: ComparisonsDetector) -> None:
    """Test that chained comparisons are not flagged."""
    code = """
if a < b < c:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_singleton_comparison_none(detector: ComparisonsDetector) -> None:
    """Test detection of == with None instead of is."""
    code = """
if x == None:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R014"
    assert issues[0].severity == Severity.MEDIUM
    assert "is" in issues[0].suggestion.lower()


def test_singleton_comparison_is_none(detector: ComparisonsDetector) -> None:
    """Test that 'is None' is not flagged."""
    code = """
if x is None:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_singleton_comparison_true(detector: ComparisonsDetector) -> None:
    """Test detection of comparison with True."""
    code = """
if x == True:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R014"
    assert issues[0].severity == Severity.INFO
    assert "True" in issues[0].message


def test_singleton_comparison_false(detector: ComparisonsDetector) -> None:
    """Test detection of comparison with False."""
    code = """
if x == False:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R014"
    assert "not" in issues[0].suggestion.lower()


def test_unidiomatic_typecheck(detector: ComparisonsDetector) -> None:
    """Test detection of type() == instead of isinstance()."""
    code = """
if type(x) == int:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R015"
    assert issues[0].severity == Severity.MEDIUM
    assert "isinstance" in issues[0].suggestion.lower()


def test_isinstance_is_idiomatic(detector: ComparisonsDetector) -> None:
    """Test that isinstance() is not flagged."""
    code = """
if isinstance(x, int):
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_type_is_comparison(detector: ComparisonsDetector) -> None:
    """Test detection of type() is instead of isinstance()."""
    code = """
if type(x) is int:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R015"
    assert "isinstance" in issues[0].suggestion.lower()


def test_multiple_comparison_issues(detector: ComparisonsDetector) -> None:
    """Test detection of multiple comparison issues."""
    code = """
if x == 1 or x == 2:
    pass

if type(y) == str:
    pass

if z == None:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) >= 3
    rule_ids = {issue.rule_id for issue in issues}
    assert "R011" in rule_ids or "R014" in rule_ids or "R015" in rule_ids


def test_suppression_comment(detector: ComparisonsDetector) -> None:
    """Test that suppression comments are respected."""
    code = """
# pyrefactor: ignore
if x == None:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_complex_chained_comparison(detector: ComparisonsDetector) -> None:
    """Test complex chained comparison pattern."""
    code = """
if x < y and y < z and z < w:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should detect at least one chainable pair
    assert len(issues) >= 1
    assert issues[0].rule_id == "R012"


def test_not_equal_none(detector: ComparisonsDetector) -> None:
    """Test detection of != with None instead of is not."""
    code = """
if x != None:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R014"
    assert "is not" in issues[0].suggestion.lower()


def test_single_or_comparison(detector: ComparisonsDetector) -> None:
    """Test that single comparison in or is not flagged."""
    code = """
if x == 1 or y == 2:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Different variables, should not flag
    assert len(issues) == 0


def test_mixed_comparison_ops(detector: ComparisonsDetector) -> None:
    """Test that mixed operators are not flagged for 'in' suggestion."""
    code = """
if x == 1 or x > 2:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Mixed operators (== and >), should not flag for 'in'
    assert len(issues) == 0
