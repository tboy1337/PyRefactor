"""Tests for AST visitor helper functions."""

import ast

from pyrefactor.ast_visitor import (
    BaseDetector,
    build_parent_map,
    calculate_cyclomatic_complexity,
    count_branches,
    count_nesting_depth,
    node_col_offset,
    node_lineno,
)
from pyrefactor.config import Config


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
