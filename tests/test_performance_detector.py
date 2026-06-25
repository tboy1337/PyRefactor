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
    result_str += item
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

    def test_async_for_string_concatenation(self, default_config: Config) -> None:
        """Test detection of string concatenation in async for loop."""
        source = """
async def process(items):
    result_str = ""
    async for item in items:
        result_str += item
        result_str += item
        result_str += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P001" for issue in issues)

    def test_async_for_duplicate_calls(self, default_config: Config) -> None:
        """Test detection of duplicate calls in async for loop."""
        source = """
async def process(items):
    async for item in items:
        expensive_compute(item)
        expensive_compute(item)
        expensive_compute(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P007" for issue in issues)

    def test_while_loop_tracking(self, default_config: Config) -> None:
        """Test that while loops are tracked for performance issues."""
        source = """
result_str = ""
while condition:
    result_str += "text"
    result_str += "more"
    result_str += "data"
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) > 0
        assert any(issue.rule_id == "P001" for issue in issues)

    def test_dict_keys_membership_owned_by_dict_detector(
        self, default_config: Config
    ) -> None:
        """dict.keys() membership is reported as R009 by the dict detector, not performance."""
        source = """
if key in my_dict.keys():
    pass
"""
        tree = ast.parse(source)
        source_lines = source.split("\n")

        perf = PerformanceDetector(default_config, "test.py", source_lines)
        perf_issues = perf.analyze(tree)
        assert not perf_issues

        from pyrefactor.detectors.dict_operations import DictOperationsDetector

        dict_detector = DictOperationsDetector(default_config, "test.py", source_lines)
        dict_issues = dict_detector.analyze(tree)
        assert any(issue.rule_id == "R009" for issue in dict_issues)

    def test_call_suppression(self, default_config: Config) -> None:
        """Test suppression of call warnings."""
        source = """
result = list([x for x in range(10)])  # pyrefactor: ignore
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0

    def test_non_string_augassign(self, default_config: Config) -> None:
        """Test that non-string augassign doesn't trigger string warning."""
        source = """
result = 0
for item in items:
    result += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger P001 (not a string operation)
        assert not any(issue.rule_id == "P001" for issue in issues)

    def test_non_list_augassign(self, default_config: Config) -> None:
        """Test that non-list augassign doesn't trigger list warning."""
        source = """
result = 0
for item in items:
    result += 1
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should not trigger P002 (not a list operation)
        assert not any(issue.rule_id == "P002" for issue in issues)

    def test_non_dict_keys_not_reported_by_performance(
        self, default_config: Config
    ) -> None:
        """Performance detector does not flag arbitrary .keys() membership."""
        source = """
if key in something.keys():
    pass
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert len(issues) == 0


class TestPerformanceLoopPatterns:
    """Tests for loop-scoped performance patterns (P001 threshold, P007)."""

    def test_nested_loops(self, default_config: Config) -> None:
        """Test that nested loops are tracked correctly."""
        source = """
result_str = ""
for i in range(10):
    for j in range(10):
        result_str += str(i)
        result_str += str(j)
        result_str += "x"
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        # Should detect string concatenation in nested loop
        assert len(issues) > 0
        assert any(issue.rule_id == "P001" for issue in issues)

    def test_string_concatenation_below_threshold(self, default_config: Config) -> None:
        """Test P001 not reported when concatenations are below threshold."""
        source = """
result_str = ""
for item in items:
    result_str += item
    result_str += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P001" for issue in issues)

    def test_string_concatenation_custom_threshold(self) -> None:
        """Test P001 with custom min_concatenations."""
        config = Config()
        config.performance.min_concatenations = 2
        source = """
result_str = ""
for item in items:
    result_str += item
    result_str += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert any(issue.rule_id == "P001" for issue in issues)

    def test_duplicate_calls_in_loop(self, default_config: Config) -> None:
        """Test P007 detection of repeated identical calls in loop."""
        source = """
for item in items:
    value = expensive_compute(item)
    other = expensive_compute(item)
    total = expensive_compute(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert any(issue.rule_id == "P007" for issue in issues)
        assert any("cache" in issue.suggestion.lower() for issue in issues)

    def test_duplicate_calls_below_threshold(self, default_config: Config) -> None:
        """Test P007 not reported when duplicate calls are below threshold."""
        source = """
for item in items:
    value = expensive_compute(item)
    other = expensive_compute(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P007" for issue in issues)

    def test_status_variable_not_treated_as_list(self, default_config: Config) -> None:
        """Test variables ending in 's' but not list-like do not trigger P002."""
        source = """
for item in items:
    status += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P002" for issue in issues)

    def test_analyze_is_idempotent(self, default_config: Config) -> None:
        """Test calling analyze() twice on the same detector resets state."""
        source = """
for item in items:
    text += str(item)
    text += str(item)
    text += str(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        first = detector.analyze(tree)
        second = detector.analyze(tree)

        assert len(first) == len(second)
        assert {issue.rule_id for issue in first} == {issue.rule_id for issue in second}

    def test_duplicate_calls_custom_threshold(self) -> None:
        """Test P007 with custom min_duplicate_calls."""
        config = Config()
        config.performance.min_duplicate_calls = 2
        source = """
for item in items:
    value = expensive_compute(item)
    other = expensive_compute(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert any(issue.rule_id == "P007" for issue in issues)

    def test_duplicate_calls_not_in_nested_function(
        self, default_config: Config
    ) -> None:
        """Test P007 ignores repeated calls inside nested functions."""
        source = """
for item in items:
    def helper():
        expensive_compute(item)
        expensive_compute(item)
        expensive_compute(item)
    helper()
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P007" for issue in issues)

    def test_nested_async_function_calls_ignored(self, default_config: Config) -> None:
        """Test P007 ignores repeated calls inside nested async functions."""
        source = """
for item in items:
    async def helper():
        expensive_compute(item)
        expensive_compute(item)
        expensive_compute(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P007" for issue in issues)

    def test_string_concatenation_tracks_string_initializer(
        self, default_config: Config
    ) -> None:
        """Test P001 detects += on variables initialized with string constants."""
        source = """
def build():
    buffer = ""
    for item in items:
        buffer += item
        buffer += item
        buffer += item
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert any(issue.rule_id == "P001" for issue in issues)

    def test_p001_suppression_does_not_suppress_p007(
        self, default_config: Config
    ) -> None:
        """Test rule-specific P001 suppression does not suppress P007."""
        source = """
for item in items:
    text += str(item)  # pyrefactor: ignore P001
    expensive_compute(item)
    expensive_compute(item)
    expensive_compute(item)
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P001" for issue in issues)
        assert any(issue.rule_id == "P007" for issue in issues)

    def test_nested_lambda_calls_ignored(self, default_config: Config) -> None:
        """Test P007 ignores repeated calls inside lambda expressions."""
        source = """
for item in items:
    handler = lambda: expensive_compute(item) or expensive_compute(item) or expensive_compute(item)
    handler()
"""
        tree = ast.parse(source)

        detector = PerformanceDetector(default_config, "test.py", source.split("\n"))
        issues = detector.analyze(tree)

        assert not any(issue.rule_id == "P007" for issue in issues)
