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
def func(x, y, z):
    if x:
        if y:
            if z:
                return True
    return False
"""
        tree = ast.parse(source)

        detector = BooleanLogicDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "B005" for issue in issues)
        assert any("nested" in issue.message.lower() for issue in issues)

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
