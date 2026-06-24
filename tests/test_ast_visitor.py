"""Tests for AST visitor helper functions."""

import ast

from pyrefactor.ast_visitor import (
    calculate_cyclomatic_complexity,
    count_branches,
    count_nesting_depth,
    node_lineno,
)


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
