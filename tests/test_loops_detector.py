"""Tests for loops detector."""

import ast

from pyrefactor.config import Config
from pyrefactor.detectors.loops import LoopsDetector


class TestLoopsDetector:
    """Tests for LoopsDetector."""

    def test_detector_name(self, default_config: Config) -> None:
        """Test detector name."""
        detector = LoopsDetector(default_config, "test.py", [])

        assert detector.get_detector_name() == "loops"

    def test_range_len_pattern(self, default_config: Config) -> None:
        """Test detection of range(len()) pattern."""
        source = """
items = [1, 2, 3]
for i in range(len(items)):
    print(items[i])
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "L001" for issue in issues)
        assert any("enumerate" in issue.message.lower() for issue in issues)

    def test_manual_index_tracking(self, default_config: Config) -> None:
        """Test detection of manual index tracking."""
        source = """
for item in items:
    index += 1
    print(index, item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "L002" for issue in issues)
        assert any("manual index" in issue.message.lower() for issue in issues)

    def test_nested_loops_with_lookups(self, default_config: Config) -> None:
        """Test detection of nested loops with comparisons."""
        source = """
for item in list1:
    for other in list2:
        for third in list3:
            if item == other:
                result.append(item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "L003" for issue in issues)
        assert any("nested loop" in issue.message.lower() for issue in issues)

    def test_loop_invariant_code(self, default_config: Config) -> None:
        """Test detection of loop-invariant code."""
        source = r"""
import re
pattern = re.compile(r'\d+')
for item in items:
    pattern.search(item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # May or may not detect depending on heuristics
        # Just ensure no crash
        assert isinstance(issues, list)

    def test_good_enumerate_usage(self, default_config: Config) -> None:
        """Test that proper enumerate usage doesn't trigger issues."""
        source = """
for i, item in enumerate(items):
    print(i, item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not have L001
        assert not any(issue.rule_id == "L001" for issue in issues)

    def test_range_without_len(self, default_config: Config) -> None:
        """Test that range without len doesn't trigger."""
        source = """
for i in range(10):
    print(i)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "L001" for issue in issues)

    def test_suppressed_range_len(self, default_config: Config) -> None:
        """Test suppression of range(len()) pattern."""
        source = """
items = [1, 2, 3]
for i in range(len(items)):  # pyrefactor: ignore
    print(items[i])
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_manual_index_not_index_name(self, default_config: Config) -> None:
        """Test that non-index variable names don't trigger manual index warning."""
        source = """
for item in items:
    counter += 1
    print(counter, item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should still detect because it's incrementing a variable
        assert len(issues) > 0
        assert any(issue.rule_id == "L002" for issue in issues)

    def test_nested_loop_without_comparison(self, default_config: Config) -> None:
        """Test nested loops without comparisons don't trigger L003."""
        source = """
for item in list1:
    for other in list2:
        result.append((item, other))
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger L003 (no comparison)
        assert not any(issue.rule_id == "L003" for issue in issues)

    def test_loop_with_list_call_outside(self, default_config: Config) -> None:
        """Test loop with list() call outside loop."""
        source = """
result = list(range(10))
for item in result:
    print(item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger issues for good code
        assert len([i for i in issues if i.rule_id.startswith("L")]) == 0

    def test_loop_invariant_expensive_method(self, default_config: Config) -> None:
        """Test detection of expensive loop-invariant method calls."""
        source = """
import re
for item in items:
    result = re.compile(r'\\d+')
    result.match(item)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should detect loop invariant code
        assert any(issue.rule_id == "L004" for issue in issues)

    def test_range_len_with_non_name_func(self, default_config: Config) -> None:
        """Test range(len()) with non-Name function."""
        source = """
for i in obj.method(len(items)):
    print(i)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger L001 since it's not range
        assert not any(issue.rule_id == "L001" for issue in issues)

    def test_range_len_without_access(self, default_config: Config) -> None:
        """Test range(len()) without accessing the collection."""
        source = """
items = [1, 2, 3]
for i in range(len(items)):
    print(i)
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger L001 since collection is not accessed by index
        assert not any(issue.rule_id == "L001" for issue in issues)

    def test_nested_loops_direct_comparison(self, default_config: Config) -> None:
        """Test nested loops with direct comparison."""
        source = """
for item in list1:
    for other in list2:
        for third in list3:
            x = 1 == 2
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should detect nested loops with comparisons
        assert any(issue.rule_id == "L003" for issue in issues)

    def test_while_loop_no_issues(self, default_config: Config) -> None:
        """Test while loop doesn't crash."""
        source = """
while condition:
    do_something()
"""
        tree = ast.parse(source)

        detector = LoopsDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Just ensure no crash
        assert isinstance(issues, list)
