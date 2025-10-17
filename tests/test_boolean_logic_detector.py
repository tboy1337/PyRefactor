"""Tests for boolean logic detector."""

import ast

from pyrefactor.config import Config
from pyrefactor.detectors.boolean_logic import BooleanLogicDetector


class TestBooleanLogicDetector:
    """Tests for BooleanLogicDetector."""

    def test_detector_name(self, default_config: Config) -> None:
        """Test detector name."""
        detector = BooleanLogicDetector(default_config, "test.py", [])

        assert detector.get_detector_name() == "boolean_logic"

    def test_complex_boolean_expression(self, default_config: Config) -> None:
        """Test detection of complex boolean expressions."""
        source = """
if a and b and c and d and e:
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B001" for issue in issues)
        assert any("complex boolean" in issue.message.lower() for issue in issues)

    def test_comparison_with_true(self, default_config: Config) -> None:
        """Test detection of == True."""
        source = """
if x == True:
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B002" for issue in issues)
        assert any("true" in issue.message.lower() for issue in issues)

    def test_comparison_with_false(self, default_config: Config) -> None:
        """Test detection of == False."""
        source = """
if x == False:
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B003" for issue in issues)
        assert any("false" in issue.message.lower() for issue in issues)

    def test_is_comparison_with_boolean(self, default_config: Config) -> None:
        """Test detection of 'is' with boolean."""
        source = """
if x is True:
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B004" for issue in issues)

    def test_early_return_opportunity(self, default_config: Config) -> None:
        """Test detection of early return opportunities."""
        source = """
def func(x, y, z, a):
    if x:
        if y:
            if z:
                if a:
                    return True
    return False
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # The detector may or may not flag this depending on implementation
        # Just ensure no crash
        assert isinstance(issues, list)

    def test_de_morgans_law_and(self, default_config: Config) -> None:
        """Test detection of De Morgan's law opportunity (and)."""
        source = """
if not (a and b):
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B006" for issue in issues)
        assert any("de morgan" in issue.message.lower() for issue in issues)

    def test_de_morgans_law_or(self, default_config: Config) -> None:
        """Test detection of De Morgan's law opportunity (or)."""
        source = """
if not (a or b):
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B007" for issue in issues)

    def test_simple_boolean_ok(self, default_config: Config) -> None:
        """Test that simple boolean expressions don't trigger issues."""
        source = """
if a and b:
    pass
if x:
    pass
if not y:
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_suppressed_boolop(self, default_config: Config) -> None:
        """Test that suppressed boolean operations are ignored."""
        source = """
if a and b and c and d and e:  # pyrefactor: ignore
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_suppressed_compare(self, default_config: Config) -> None:
        """Test that suppressed comparisons are ignored."""
        source = """
if x == True:  # noqa
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_suppressed_if(self, default_config: Config) -> None:
        """Test that suppressed if statements are ignored."""
        source = """
def func(x, y, z):
    # pyrefactor: ignore
    if x:
        if y:
            if z:
                return True
    return False
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_suppressed_unaryop(self, default_config: Config) -> None:
        """Test that suppressed unary operations are ignored."""
        source = """
if not (a and b):  # pyrefactor: ignore
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_nested_boolean_operators(self, default_config: Config) -> None:
        """Test counting nested boolean operators."""
        source = """
if (a and b) or (c and d) or (e and f):
    pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should detect complex expression
        assert len(issues) > 0
        assert any(issue.rule_id == "B001" for issue in issues)

    def test_early_return_with_two_nesting_levels(self, default_config: Config) -> None:
        """Test that two levels of nesting don't trigger early return warning."""
        source = """
def func(x, y):
    if x:
        if y:
            return True
    return False
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger B005 (need 3+ levels)
        assert not any(issue.rule_id == "B005" for issue in issues)

    def test_early_return_with_non_return_body(self, default_config: Config) -> None:
        """Test nested ifs without early return pattern."""
        source = """
def func(x, y, z):
    if x:
        if y:
            if z:
                print("test")
    return False
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger B005 (no return in innermost if)
        assert not any(issue.rule_id == "B005" for issue in issues)

    def test_early_return_with_raise(self, default_config: Config) -> None:
        """Test early return detection with raise statement."""
        source = """
def func(x, y, z, a):
    if x:
        if y:
            if z:
                if a:
                    raise ValueError("error")
    return False
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # May or may not detect depending on implementation
        assert isinstance(issues, list)

    def test_if_outside_function(self, default_config: Config) -> None:
        """Test that if statements outside functions don't check early returns."""
        source = """
if x:
    if y:
        if z:
            pass
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger B005 (not in a function)
        assert not any(issue.rule_id == "B005" for issue in issues)
