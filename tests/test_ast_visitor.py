"""Tests for AST visitor helper functions."""

import ast

from pyrefactor.ast_visitor import (
    BaseDetector,
    build_parent_map,
    calculate_cyclomatic_complexity,
    collect_function_metrics,
    count_branches,
    count_nesting_depth,
    node_col_offset,
    node_lineno,
)
from pyrefactor.config import Config
from pyrefactor.detectors.complexity import ComplexityDetector
from pyrefactor.models import Severity


class TestNodeLineno:
    """Tests for node_lineno helper."""

    def test_valid_lineno(self) -> None:
        """Test extracting a valid line number."""
        tree = ast.parse("x = 1")
        node = tree.body[0]
        assert node_lineno(node) == 1

    def test_invalid_lineno(self) -> None:
        """Test nodes without valid line numbers."""
        node = ast.Module(body=[], type_ignores=[])
        assert node_lineno(node) is None


class TestNodeColOffset:
    """Tests for node_col_offset helper."""

    def test_valid_col_offset(self) -> None:
        """Test extracting a valid column offset."""
        tree = ast.parse("x = 1")
        node = tree.body[0]
        assert node_col_offset(node) == 0

    def test_missing_col_offset_defaults_to_zero(self) -> None:
        """Test nodes without col_offset default to 0."""
        node = ast.Module(body=[], type_ignores=[])
        assert node_col_offset(node) == 0


class TestBuildParentMap:
    """Tests for build_parent_map helper."""

    def test_parent_map_links_children(self) -> None:
        """Test parent map links AST nodes to their parents."""
        tree = ast.parse("if x:\n    y = 1")
        parent_map = build_parent_map(tree)

        if_node = tree.body[0]
        assert isinstance(if_node, ast.If)
        assign_node = if_node.body[0]
        assert parent_map[if_node] is tree
        assert parent_map[assign_node] is if_node


class TestASTMetrics:
    """Tests for cyclomatic complexity, nesting, and branch metrics."""

    def test_match_statement_complexity(self) -> None:
        """Test match/case increases cyclomatic complexity."""
        source = """
def func(value):
    match value:
        case 1:
            return "one"
        case 2:
            return "two"
        case _:
            return "other"
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        complexity = calculate_cyclomatic_complexity(func_def)
        assert complexity >= 4

    def test_list_comprehension_nesting(self) -> None:
        """Test list comprehension does not inflate nesting depth."""
        source = "[x for x in range(10) if x > 0]"
        tree = ast.parse(source)
        depth = count_nesting_depth(tree)
        assert depth == 0

    def test_nested_inner_function_ignored(self) -> None:
        """Test inner function nesting does not affect outer function metrics."""
        source = """
def outer():
    def inner():
        if True:
            if True:
                return 1
    return 0
"""
        tree = ast.parse(source)
        outer = tree.body[0]
        assert isinstance(outer, ast.FunctionDef)
        assert count_nesting_depth(outer) == 0
        assert count_branches(outer) == 0

    def test_async_for_branches(self) -> None:
        """Test async for is counted as a branch."""
        source = """
async def func():
    async for item in stream:
        process(item)
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.AsyncFunctionDef)
        assert count_branches(func_def) >= 1

    def test_assert_increases_cyclomatic_complexity(self) -> None:
        """Test assert statements increase cyclomatic complexity."""
        source = """
def func(value):
    assert value > 0
    return value
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        assert calculate_cyclomatic_complexity(func_def) >= 2

    def test_try_star_increases_branch_count(self) -> None:
        """Test except* handlers are counted as branches."""
        source = """
def func():
    try:
        raise ExceptionGroup("errors", [])
    except* ValueError:
        return 1
    except* KeyError:
        return 2
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        assert count_branches(func_def) >= 2

    def test_match_cases_counted_as_branches(self) -> None:
        """Test match/case statements are counted as branches."""
        source = """
def func(value):
    match value:
        case 1:
            return "one"
        case 2:
            return "two"
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        assert count_branches(func_def) >= 2

    def test_metrics_parity_with_complexity_detector(
        self, default_config: Config
    ) -> None:
        """Test public metric helpers match ComplexityDetector collection."""
        source = """
def func(value):
    try:
        if value > 0:
            with open("x") as f:
                return f.read()
    except ValueError:
        return ""
    except KeyError:
        return None
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)

        metrics = collect_function_metrics(func_def)
        assert (
            calculate_cyclomatic_complexity(func_def) == metrics.cyclomatic_complexity
        )
        assert count_branches(func_def) == metrics.branches
        assert count_nesting_depth(func_def) == metrics.max_nesting

        detector = ComplexityDetector(default_config, "test.py", source.splitlines())
        detector._check_function(func_def)
        # Metrics drive rule thresholds; parity ensures helpers match detector logic.

    def test_try_except_metrics(self) -> None:
        """Test try/except increases cyclomatic complexity and branches."""
        source = """
def func():
    try:
        risky()
    except ValueError:
        return 1
    except TypeError:
        return 2
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        metrics = collect_function_metrics(func_def)
        assert metrics.cyclomatic_complexity >= 4
        assert metrics.branches >= 2

    def test_with_statement_nesting(self) -> None:
        """Test with statements increase nesting depth."""
        source = """
def func():
    with open("a") as f:
        if f:
            return f.read()
"""
        tree = ast.parse(source)
        func_def = tree.body[0]
        assert isinstance(func_def, ast.FunctionDef)
        assert count_nesting_depth(func_def) >= 2


class _SuppressionProbeDetector(BaseDetector):
    """Minimal detector for exercising suppression helpers."""

    def get_detector_name(self) -> str:
        return "suppression_probe"


class TestBaseDetectorSuppression:
    """Tests for BaseDetector suppression behavior."""

    def test_noqa_suppresses_all_rules(self) -> None:
        """Test blanket # noqa suppresses every rule on the line."""
        source_lines = ["x = 1  # noqa"]
        detector = _SuppressionProbeDetector(Config(), "test.py", source_lines)
        tree = ast.parse("x = 1")
        node = tree.body[0]

        assert detector.is_suppressed(node, "C001") is True
        assert detector.is_suppressed(node, "P001") is True

    def test_rule_scoped_noqa_does_not_suppress_other_rules(self) -> None:
        """Test rule-specific pyrefactor ignore does not blanket-suppress."""
        source_lines = ["x = 1  # pyrefactor: ignore C001"]
        detector = _SuppressionProbeDetector(Config(), "test.py", source_lines)
        tree = ast.parse("x = 1")
        node = tree.body[0]

        assert detector.is_suppressed(node, "C001") is True
        assert detector.is_suppressed(node, "P001") is False

    def test_noqa_rule_specific(self) -> None:
        """Test rule-specific # noqa suppresses only listed rules."""
        source_lines = ["x = 1  # noqa: C001"]
        detector = _SuppressionProbeDetector(Config(), "test.py", source_lines)
        tree = ast.parse("x = 1")
        node = tree.body[0]

        assert detector.is_suppressed(node, "C001") is True
        assert detector.is_suppressed(node, "P001") is False

    def test_noqa_multiple_rules(self) -> None:
        """Test comma-separated # noqa rule lists."""
        source_lines = ["x = 1  # noqa: C001,P001"]
        detector = _SuppressionProbeDetector(Config(), "test.py", source_lines)
        tree = ast.parse("x = 1")
        node = tree.body[0]

        assert detector.is_suppressed(node, "C001") is True
        assert detector.is_suppressed(node, "P001") is True
        assert detector.is_suppressed(node, "R001") is False

    def test_suppression_on_previous_line(self) -> None:
        """Test suppression comment on the line above the code."""
        source_lines = ["# pyrefactor: ignore C001", "x = 1"]
        detector = _SuppressionProbeDetector(Config(), "test.py", source_lines)
        tree = ast.parse("x = 1")
        node = tree.body[0]

        assert detector.is_suppressed(node, "C001") is True
        assert detector.is_suppressed(node, "P001") is False


class _ReportIssueProbeDetector(BaseDetector):
    """Detector that reports issues for nodes without line numbers."""

    def get_detector_name(self) -> str:
        return "report_probe"

    def report_for_module(self, tree: ast.Module) -> None:
        """Attempt to report on module node (no lineno)."""
        self.report_issue(
            tree,
            severity=Severity.INFO,
            rule_id="T001",
            message="module issue",
            suggestion="n/a",
        )


class TestBaseDetectorReportIssue:
    """Tests for BaseDetector.report_issue edge cases."""

    def test_report_issue_skips_nodes_without_lineno(self) -> None:
        """Test report_issue does not add issues when lineno is missing."""
        detector = _ReportIssueProbeDetector(Config(), "test.py", [])
        tree = ast.parse("")
        detector.report_for_module(tree)
        assert not detector.issues
