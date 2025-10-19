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


def test_detector_name(detector: ComparisonsDetector) -> None:
    """Test detector name."""
    assert detector.get_detector_name() == "comparisons"


def test_or_boolop_with_non_compare_values(detector: ComparisonsDetector) -> None:
    """Test OR boolop with non-compare values."""
    code = """
if x or y or z:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Non-compare values, should not flag
    assert not any(issue.rule_id == "R011" for issue in issues)


def test_or_boolop_with_multiple_ops_comparison(detector: ComparisonsDetector) -> None:
    """Test OR boolop with comparisons having multiple ops."""
    code = """
if x == 1 < 2 or y == 3:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Multiple ops in comparison, should not flag for 'in'
    assert not any(issue.rule_id == "R011" for issue in issues)


def test_or_boolop_non_name_left_operand(detector: ComparisonsDetector) -> None:
    """Test OR boolop with non-Name left operands (attributes)."""
    code = """
if obj.x == 1 or obj.x == 2:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Attributes are valid for 'in' suggestion too
    assert len(issues) == 1
    assert issues[0].rule_id == "R011"


def test_or_boolop_non_singleton_comparators(detector: ComparisonsDetector) -> None:
    """Test OR boolop with non-singleton comparators."""
    code = """
if x == [1, 2] or x == [3, 4]:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Lists are valid for 'in' suggestion (even if not ideal)
    assert len(issues) == 1
    assert issues[0].rule_id == "R011"


def test_and_boolop_with_non_compare_values(detector: ComparisonsDetector) -> None:
    """Test AND boolop with non-compare values."""
    code = """
if x and y and z:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Non-compare values, should not flag for chaining
    assert not any(issue.rule_id == "R012" for issue in issues)


def test_and_boolop_multiple_ops_in_comparison(detector: ComparisonsDetector) -> None:
    """Test AND boolop with comparisons having multiple ops."""
    code = """
if (a < b < c) and x < y:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Multiple ops in comparison, should not flag for additional chaining
    assert not any(issue.rule_id == "R012" for issue in issues)


def test_and_boolop_no_chainable_operators(detector: ComparisonsDetector) -> None:
    """Test AND boolop with non-chainable operators."""
    code = """
if a == b and c == d:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Non-chainable operators (==), should not flag
    assert not any(issue.rule_id == "R012" for issue in issues)


def test_and_boolop_non_name_comparators(detector: ComparisonsDetector) -> None:
    """Test AND boolop with non-Name comparators (attributes)."""
    code = """
if a < b.x and b.x < c:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Attributes are valid for chaining suggestion too
    assert len(issues) == 1
    assert issues[0].rule_id == "R012"


def test_compare_non_constant_comparator(detector: ComparisonsDetector) -> None:
    """Test comparison with non-constant comparator."""
    code = """
if x == y:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Non-constant comparator, should not flag singleton comparison
    assert not any(issue.rule_id == "R014" for issue in issues)


def test_compare_constant_non_singleton(detector: ComparisonsDetector) -> None:
    """Test comparison with constant non-singleton."""
    code = """
if x == 42:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Non-singleton constant (42), should not flag
    assert not any(issue.rule_id == "R014" for issue in issues)


def test_compare_with_is_non_singleton(detector: ComparisonsDetector) -> None:
    """Test 'is' comparison with non-singleton."""
    code = """
if x is 42:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Using 'is' with non-singleton, should not flag (already correct usage)
    assert not any(issue.rule_id == "R014" for issue in issues)


def test_compare_not_eq_singleton(detector: ComparisonsDetector) -> None:
    """Test != comparison with singleton."""
    code = """
if x != False:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Should flag != with singleton
    assert len(issues) == 1
    assert issues[0].rule_id == "R014"


def test_compare_type_not_call(detector: ComparisonsDetector) -> None:
    """Test comparison where left is not a call."""
    code = """
if x == int:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Left is not a call, should not flag type check
    assert not any(issue.rule_id == "R015" for issue in issues)


def test_compare_call_not_type(detector: ComparisonsDetector) -> None:
    """Test comparison where call is not type()."""
    code = """
if len(x) == 5:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Call is not type(), should not flag
    assert not any(issue.rule_id == "R015" for issue in issues)


def test_compare_type_with_non_name(detector: ComparisonsDetector) -> None:
    """Test type() comparison with non-Name comparator (attribute)."""
    code = """
if type(x) == obj.SomeType:
    pass
"""
    tree = ast.parse(code)
    detector.source_lines = code.splitlines()
    issues = detector.analyze(tree)

    # Attributes are valid for isinstance suggestion too
    assert len(issues) == 1
    assert issues[0].rule_id == "R015"
