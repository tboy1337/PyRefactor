"""Tests for performance detector."""

import ast

from pyrefactor.config import Config
from pyrefactor.detectors.performance import PerformanceDetector


class TestPerformanceDetector:
    """Tests for PerformanceDetector."""

    def test_detector_name(self, default_config: Config) -> None:
        """Test detector name."""
        detector = PerformanceDetector(default_config, "test.py", [])

        assert detector.get_detector_name() == "performance"

    def test_string_concatenation_in_loop(self, default_config: Config) -> None:
        """Test detection of string concatenation in loop."""
        source = """
result_str = ""
for item in items:
    result_str += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P001" for issue in issues)
        assert any("string concatenation" in issue.message.lower() for issue in issues)

    def test_list_concatenation_in_loop(self, default_config: Config) -> None:
        """Test detection of list concatenation in loop."""
        source = """
results = []
for item in items:
    results += [item]
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P002" for issue in issues)

    def test_len_greater_than_zero(self, default_config: Config) -> None:
        """Test detection of len() > 0 pattern."""
        source = """
if len(items) > 0:
    pass
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P005" for issue in issues)
        assert any("truthiness" in issue.message.lower() for issue in issues)

    def test_len_equals_zero(self, default_config: Config) -> None:
        """Test detection of len() == 0 pattern."""
        source = """
if len(items) == 0:
    pass
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P006" for issue in issues)

    def test_redundant_list_conversion(self, default_config: Config) -> None:
        """Test detection of redundant list() conversion."""
        source = """
result = list([x for x in range(10)])
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P004" for issue in issues)
        assert any("redundant" in issue.message.lower() for issue in issues)

    def test_no_issues_for_good_code(self, default_config: Config) -> None:
        """Test that good code doesn't trigger false positives."""
        source = """
result = [item for item in items if item > 0]
text = ", ".join(str_items)
if items:
    pass
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_suppression(self, default_config: Config) -> None:
        """Test suppression comments."""
        source = """
result_str = ""
for item in items:
    result_str += item  # pyrefactor: ignore
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0
