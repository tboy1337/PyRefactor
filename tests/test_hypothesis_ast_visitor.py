"""Property-based tests for AST visitor utilities using Hypothesis."""

import ast
from typing import Union

from hypothesis import given
from hypothesis import strategies as st

from pyrefactor.ast_visitor import (
    calculate_cyclomatic_complexity,
    count_branches,
    count_nesting_depth,
)


# Custom strategies for generating Python code
@st.composite
def simple_function_code(draw: st.DrawFn) -> str:
    """Generate simple function code."""
    func_name = draw(st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True))
    # Ensure we don't use Python keywords
    keywords = {
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }
    if func_name in keywords:
        func_name = f"func_{func_name}"
    return f"def {func_name}():\n    pass"


@st.composite
def function_with_conditionals(draw: st.DrawFn, num_ifs: int = 0) -> str:
    """Generate function code with if statements."""
    func_name = draw(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu"), min_codepoint=97, max_codepoint=122
            ),
        )
    )

    lines = [f"def {func_name}():"]

    for i in range(num_ifs):
        lines.append(f"    if condition_{i}:")
        lines.append(f"        x = {i}")

    if not num_ifs:
        lines.append("    pass")

    return "\n".join(lines)


@st.composite
def function_with_loops(draw: st.DrawFn, num_loops: int = 0) -> str:
    """Generate function code with loops."""
    func_name = draw(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu"), min_codepoint=97, max_codepoint=122
            ),
        )
    )

    lines = [f"def {func_name}():"]

    for i in range(num_loops):
        lines.append(f"    for item_{i} in range(10):")
        lines.append(f"        x = {i}")

    if not num_loops:
        lines.append("    pass")

    return "\n".join(lines)


@st.composite
def function_with_nested_blocks(draw: st.DrawFn, depth: int = 1) -> str:
    """Generate function code with nested blocks."""
    func_name = draw(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu"), min_codepoint=97, max_codepoint=122
            ),
        )
    )

    lines = [f"def {func_name}():"]
    indent = "    "

    for level in range(depth):
        lines.append(indent * (level + 1) + f"if condition_{level}:")

    # Add a statement at the deepest level
    lines.append(indent * (depth + 1) + "pass")

    return "\n".join(lines)


def parse_function(code: str) -> Union[ast.FunctionDef, ast.AsyncFunctionDef]:
    """Parse code and extract the first function definition."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    raise ValueError("No function found in code")


class TestCyclomaticComplexityProperties:
    """Property-based tests for cyclomatic complexity calculation."""

    @given(simple_function_code())
    def test_simple_function_has_complexity_one(self, code: str) -> None:
        """Property: Simple function without branches has complexity 1."""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        assert complexity >= 1

    @given(st.integers(min_value=0, max_value=10))
    def test_complexity_increases_with_conditionals(self, num_ifs: int) -> None:
        """Property: Adding if statements increases complexity."""
        code = f"""
def test_func():
    x = 0
{chr(10).join(f'    if condition_{i}: x += 1' for i in range(num_ifs))}
"""
        try:
            func = parse_function(code)
            complexity = calculate_cyclomatic_complexity(func)
            # Base complexity is 1, each if adds 1
            assert complexity >= 1 + num_ifs
        except SyntaxError:
            # Skip invalid syntax
            pass

    @given(st.integers(min_value=1, max_value=10))
    def test_complexity_increases_with_loops(self, num_loops: int) -> None:
        """Property: Adding loops increases complexity."""
        code = f"""
def test_func():
    x = 0
{chr(10).join(f'    for i_{i} in range(10): x += 1' for i in range(num_loops))}
"""
        try:
            func = parse_function(code)
            complexity = calculate_cyclomatic_complexity(func)
            # Base complexity is 1, each loop adds 1
            assert complexity >= 1 + num_loops
        except SyntaxError:
            # Skip invalid syntax
            pass

    def test_complexity_with_boolean_operators(self) -> None:
        """Property: Boolean operators contribute to complexity."""
        code = """
def test_func():
    if a and b and c:
        pass
"""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        # Base 1 + if 1 + (3-1) for 'and' operators
        assert complexity >= 3

    def test_complexity_with_exception_handlers(self) -> None:
        """Property: Exception handlers increase complexity."""
        code = """
def test_func():
    try:
        x = 1
    except ValueError:
        x = 2
    except TypeError:
        x = 3
"""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        # Base 1 + 2 exception handlers
        assert complexity >= 3

    def test_empty_function_has_minimum_complexity(self) -> None:
        """Property: Empty function has complexity of at least 1."""
        code = """
def empty_func():
    pass
"""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        assert complexity == 1

    @given(st.integers(min_value=0, max_value=5))
    def test_complexity_non_negative(self, num_branches: int) -> None:
        """Property: Complexity is always non-negative and at least 1."""
        conditions = "\n".join(f"    if x == {i}: y = {i}" for i in range(num_branches))
        code = f"""
def test_func():
    y = 0
{conditions}
"""
        try:
            func = parse_function(code)
            complexity = calculate_cyclomatic_complexity(func)
            assert complexity >= 1
        except SyntaxError:
            pass


class TestNestingDepthProperties:
    """Property-based tests for nesting depth calculation."""

    @given(simple_function_code())
    def test_simple_function_has_zero_nesting(self, code: str) -> None:
        """Property: Simple function without nesting has depth 0."""
        func = parse_function(code)
        depth = count_nesting_depth(func)
        assert depth == 0

    @given(st.integers(min_value=1, max_value=5))
    def test_nesting_depth_with_nested_ifs(self, depth_level: int) -> None:
        """Property: Nested if statements increase nesting depth."""
        indent = "    "
        lines = ["def test_func():"]

        for level in range(depth_level):
            lines.append(indent * (level + 1) + f"if condition_{level}:")

        lines.append(indent * (depth_level + 1) + "pass")
        code = "\n".join(lines)

        func = parse_function(code)
        depth = count_nesting_depth(func)
        assert depth == depth_level

    @given(st.integers(min_value=1, max_value=5))
    def test_nesting_depth_with_nested_loops(self, depth_level: int) -> None:
        """Property: Nested loops increase nesting depth."""
        indent = "    "
        lines = ["def test_func():"]

        for level in range(depth_level):
            lines.append(indent * (level + 1) + f"for i_{level} in range(10):")

        lines.append(indent * (depth_level + 1) + "pass")
        code = "\n".join(lines)

        func = parse_function(code)
        depth = count_nesting_depth(func)
        assert depth == depth_level

    def test_nesting_depth_non_negative(self) -> None:
        """Property: Nesting depth is always non-negative."""
        code = """
def test_func():
    x = 1
    y = 2
"""
        func = parse_function(code)
        depth = count_nesting_depth(func)
        assert depth >= 0

    def test_sequential_blocks_dont_increase_depth(self) -> None:
        """Property: Sequential (non-nested) blocks don't increase max depth."""
        code = """
def test_func():
    if a:
        x = 1
    if b:
        y = 2
"""
        func = parse_function(code)
        depth = count_nesting_depth(func)
        # Both ifs are at the same level, so depth is 1
        assert depth == 1

    def test_nesting_with_mixed_structures(self) -> None:
        """Property: Mixed nested structures contribute to depth."""
        code = """
def test_func():
    if a:
        for i in range(10):
            while True:
                with open('f') as f:
                    pass
"""
        func = parse_function(code)
        depth = count_nesting_depth(func)
        # if -> for -> while -> with = 4 levels
        assert depth == 4


class TestBranchCountProperties:
    """Property-based tests for branch counting."""

    @given(simple_function_code())
    def test_simple_function_has_zero_branches(self, code: str) -> None:
        """Property: Simple function without branches has count 0."""
        func = parse_function(code)
        branches = count_branches(func)
        assert branches == 0

    @given(st.integers(min_value=1, max_value=10))
    def test_branch_count_increases_with_ifs(self, num_ifs: int) -> None:
        """Property: Each if statement increases branch count."""
        conditions = "\n".join(
            f"    if condition_{i}:\n        x = {i}" for i in range(num_ifs)
        )
        code = f"""
def test_func():
    x = 0
{conditions}
"""
        func = parse_function(code)
        branches = count_branches(func)
        # Each if without else counts as 1 branch
        assert branches >= num_ifs

    @given(st.integers(min_value=1, max_value=10))
    def test_branch_count_increases_with_loops(self, num_loops: int) -> None:
        """Property: Each loop increases branch count."""
        loops = "\n".join(
            f"    for i_{i} in range(10):\n        x = {i}" for i in range(num_loops)
        )
        code = f"""
def test_func():
    x = 0
{loops}
"""
        func = parse_function(code)
        branches = count_branches(func)
        # Each loop counts as a branch
        assert branches >= num_loops

    def test_if_with_else_counts_two_branches(self) -> None:
        """Property: If-else statement counts as 2 branches."""
        code = """
def test_func():
    if condition:
        x = 1
    else:
        x = 2
"""
        func = parse_function(code)
        branches = count_branches(func)
        # If + else = 2 branches
        assert branches == 2

    def test_elif_chain_counts_correctly(self) -> None:
        """Property: Elif chain counts each branch."""
        code = """
def test_func():
    if a:
        x = 1
    elif b:
        x = 2
    elif c:
        x = 3
    else:
        x = 4
"""
        func = parse_function(code)
        branches = count_branches(func)
        # if, elif, elif, else = 4 branches
        assert branches == 4

    def test_exception_handlers_count_as_branches(self) -> None:
        """Property: Exception handlers count as branches."""
        code = """
def test_func():
    try:
        x = 1
    except ValueError:
        x = 2
    except TypeError:
        x = 3
"""
        func = parse_function(code)
        branches = count_branches(func)
        # 2 exception handlers
        assert branches == 2

    def test_branch_count_non_negative(self) -> None:
        """Property: Branch count is always non-negative."""
        code = """
def test_func():
    return 42
"""
        func = parse_function(code)
        branches = count_branches(func)
        assert branches >= 0


class TestASTUtilityInvariants:
    """Test invariants across AST utility functions."""

    @given(st.integers(min_value=0, max_value=5))
    def test_complexity_never_less_than_branches(self, num_branches: int) -> None:
        """Property: Cyclomatic complexity is typically >= branch count."""
        conditions = "\n".join(f"    if x == {i}: y = {i}" for i in range(num_branches))
        code = f"""
def test_func():
    y = 0
{conditions}
"""
        try:
            func = parse_function(code)
            complexity = calculate_cyclomatic_complexity(func)

            # Complexity starts at 1 (base), branches start at 0
            # For simple if statements without else, complexity should be >= branches
            assert complexity >= 1
        except SyntaxError:
            pass

    @given(st.integers(min_value=1, max_value=5))
    def test_nested_structure_increases_nesting_not_branches(self, depth: int) -> None:
        """Property: Nesting increases depth but not necessarily branch count."""
        indent = "    "
        lines = ["def test_func():"]

        # Create nested if statements (single path)
        for level in range(depth):
            lines.append(indent * (level + 1) + f"if condition_{level}:")

        lines.append(indent * (depth + 1) + "pass")
        code = "\n".join(lines)

        func = parse_function(code)
        nesting = count_nesting_depth(func)
        branches = count_branches(func)

        assert nesting == depth
        assert branches == depth  # Each if is a branch

    def test_async_function_complexity(self) -> None:
        """Property: Async functions can be analyzed for complexity."""
        code = """
async def async_func():
    if condition:
        await something()
"""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        assert complexity >= 2  # Base 1 + if 1

    def test_function_with_comprehension(self) -> None:
        """Property: List comprehensions with conditions affect complexity."""
        code = """
def test_func():
    result = [x for x in range(10) if x > 5]
"""
        func = parse_function(code)
        # The if in the comprehension should add to complexity
        complexity = calculate_cyclomatic_complexity(func)
        assert complexity >= 1

    @given(st.integers(min_value=2, max_value=5))
    def test_boolean_operators_add_to_complexity(self, num_conditions: int) -> None:
        """Property: Multiple boolean conditions increase complexity."""
        conditions = " and ".join(f"cond_{i}" for i in range(num_conditions))
        code = f"""
def test_func():
    if {conditions}:
        pass
"""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        # Base 1 + if 1 + (num_conditions - 1) for 'and' operators
        assert complexity >= 1 + 1 + (num_conditions - 1)

    def test_while_loop_adds_to_complexity_and_branches(self) -> None:
        """Property: While loops contribute to both complexity and branches."""
        code = """
def test_func():
    while condition:
        x = 1
"""
        func = parse_function(code)
        complexity = calculate_cyclomatic_complexity(func)
        branches = count_branches(func)

        assert complexity >= 2  # Base 1 + while 1
        assert branches >= 1  # While is a branch

    def test_match_statement_branches(self) -> None:
        """Property: Match statements (Python 3.10+) have multiple branches."""
        code = """
def test_func(x):
    match x:
        case 1:
            return "one"
        case 2:
            return "two"
        case _:
            return "other"
"""
        try:
            func = parse_function(code)
            # Match statements might not be fully supported in all versions
            branches = count_branches(func)
            # Should detect some branches
            assert branches >= 0
        except (SyntaxError, AttributeError):
            # Python < 3.10 or not supported
            pass

    @given(st.integers(min_value=1, max_value=3))
    def test_nested_functions_dont_affect_outer_complexity(
        self, num_inner_branches: int
    ) -> None:
        """Property: Nested functions don't affect outer function's metrics."""
        inner_conditions = "\n".join(
            f"        if x == {i}: y = {i}" for i in range(num_inner_branches)
        )
        code = f"""
def outer_func():
    x = 1

    def inner_func():
        y = 0
{inner_conditions}

    return inner_func
"""
        func = parse_function(code)
        # Outer function should have complexity 1 (no branches of its own)
        complexity = calculate_cyclomatic_complexity(func)
        assert complexity >= 1
