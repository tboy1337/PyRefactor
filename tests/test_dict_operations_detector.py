"""Tests for dictionary operations detector."""

import ast

import pytest

from pyrefactor.config import Config
from pyrefactor.detectors.dict_operations import DictOperationsDetector
from pyrefactor.models import Severity


@pytest.fixture
def detector() -> DictOperationsDetector:
    """Create a dictionary operations detector instance."""
    config = Config()
    return DictOperationsDetector(config, "test.py", [])


def test_dict_get_opportunity(detector: DictOperationsDetector) -> None:
    """Test detection of dict.get() opportunity."""
    code = """
if key in my_dict:
    value = my_dict[key]
else:
    value = default_value
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R006"
    assert issues[0].severity == Severity.LOW
    assert "dict.get" in issues[0].message.lower()


def test_dict_get_already_used(detector: DictOperationsDetector) -> None:
    """Test that dict.get() is not flagged when already used."""
    code = """
value = my_dict.get(key, default_value)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_unnecessary_keys_in_for_loop(detector: DictOperationsDetector) -> None:
    """Test detection of unnecessary .keys() in for loop."""
    code = """
for key in my_dict.keys():
    print(key)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R009"
    assert issues[0].severity == Severity.INFO
    assert ".keys()" in issues[0].message


def test_iterating_dict_directly(detector: DictOperationsDetector) -> None:
    """Test that iterating dict directly is not flagged."""
    code = """
for key in my_dict:
    print(key)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_dict_items_opportunity(detector: DictOperationsDetector) -> None:
    """Test detection of opportunity to use .items()."""
    code = """
for key in my_dict:
    value = my_dict[key]
    print(key, value)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R007"
    assert issues[0].severity == Severity.MEDIUM
    assert ".items()" in issues[0].suggestion


def test_dict_items_already_used(detector: DictOperationsDetector) -> None:
    """Test that .items() is not flagged when already used."""
    code = """
for key, value in my_dict.items():
    print(key, value)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_dict_comprehension_opportunity(detector: DictOperationsDetector) -> None:
    """Test detection of dict comprehension opportunity."""
    code = """
result = dict([(k, v) for k, v in items])
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 1
    assert issues[0].rule_id == "R010"
    assert issues[0].severity == Severity.LOW
    assert "comprehension" in issues[0].message.lower()


def test_dict_comprehension_already_used(detector: DictOperationsDetector) -> None:
    """Test that dict comprehension is not flagged when already used."""
    code = """
result = {k: v for k, v in items}
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_dict_call_without_list_comp(detector: DictOperationsDetector) -> None:
    """Test that dict() call without list comp is not flagged."""
    code = """
result = dict(key1=value1, key2=value2)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_multiple_dict_issues(detector: DictOperationsDetector) -> None:
    """Test detection of multiple dict operation issues."""
    code = """
# Unnecessary .keys()
for key in my_dict.keys():
    # Should use .items()
    value = my_dict[key]
    print(key, value)

# Dict comprehension opportunity
result = dict([(k, v*2) for k, v in items])
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) >= 2
    rule_ids = {issue.rule_id for issue in issues}
    assert "R009" in rule_ids or "R007" in rule_ids or "R010" in rule_ids


def test_suppression_comment(detector: DictOperationsDetector) -> None:
    """Test that suppression comments are respected."""
    code = """
# pyrefactor: ignore
for key in my_dict.keys():
    print(key)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_dict_get_pattern_mismatch(detector: DictOperationsDetector) -> None:
    """Test that mismatched patterns don't trigger dict.get suggestion."""
    code = """
if key in my_dict:
    value = other_dict[key]
else:
    value = default_value
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should not flag because accessing different dict
    assert len(issues) == 0


def test_dict_iteration_no_indexing(detector: DictOperationsDetector) -> None:
    """Test that dict iteration without indexing is not flagged."""
    code = """
for key in my_dict:
    print(key)
    do_something_else(key)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    assert len(issues) == 0


def test_nested_loop_dict_access(detector: DictOperationsDetector) -> None:
    """Test dict access in nested loops."""
    code = """
for key in my_dict:
    for item in my_dict[key]:
        print(item)
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should suggest .items()
    assert len(issues) == 1
    assert issues[0].rule_id == "R007"
