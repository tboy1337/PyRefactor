"""Base AST visitor framework for PyRefactor detectors."""

import ast
from abc import ABC, abstractmethod

from .config import Config
from .models import Issue


class BaseDetector(ast.NodeVisitor, ABC):
    """Base class for all detectors."""

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize detector with configuration and source context."""
        self.config = config
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: list[Issue] = []
        self.current_function: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        self.nesting_level = 0

    @abstractmethod
    def get_detector_name(self) -> str:
        """Return the name of this detector."""

    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the detector's list."""
        self.issues.append(issue)

    def get_source_line(self, line: int) -> str:
        """Get a specific source line (1-indexed)."""
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def get_source_snippet(self, start_line: int, end_line: int) -> str:
        """Get a snippet of source code."""
        if start_line < 1 or end_line > len(self.source_lines):
            return ""
        return "\n".join(self.source_lines[start_line - 1 : end_line])

    def is_suppressed(self, node: ast.AST) -> bool:
        """Check if a node has a suppression comment."""
        if not hasattr(node, "lineno"):
            return False

        lineno: int = node.lineno
        line = self.get_source_line(lineno)
        # Check for suppression comments
        if "# pyrefactor: ignore" in line or "# noqa" in line:
            return True

        # Check previous line for suppression
        if lineno > 1:
            prev_line = self.get_source_line(lineno - 1)
            if "# pyrefactor: ignore" in prev_line or "# noqa" in prev_line:
                return True

        return False

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run the detector on an AST and return issues found."""
        self.visit(tree)
        return self.issues


def calculate_cyclomatic_complexity(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    """Calculate cyclomatic complexity of a function."""
    complexity = 1  # Base complexity

    class ComplexityVisitor(ast.NodeVisitor):
        """Visitor to count decision points."""

        def __init__(self) -> None:
            self.complexity = 0

        def visit_If(self, node: ast.If) -> None:
            """Count if statements."""
            self.complexity += 1
            self.generic_visit(node)

        def visit_For(self, node: ast.For) -> None:
            """Count for loops."""
            self.complexity += 1
            self.generic_visit(node)

        def visit_While(self, node: ast.While) -> None:
            """Count while loops."""
            self.complexity += 1
            self.generic_visit(node)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            """Count except handlers."""
            self.complexity += 1
            self.generic_visit(node)

        def visit_With(self, node: ast.With) -> None:
            """Count with statements."""
            self.complexity += 1
            self.generic_visit(node)

        def visit_Assert(self, node: ast.Assert) -> None:
            """Count assertions."""
            self.complexity += 1
            self.generic_visit(node)

        def visit_BoolOp(self, node: ast.BoolOp) -> None:
            """Count boolean operations (and/or)."""
            if isinstance(node.op, ast.And):
                self.complexity += len(node.values) - 1
            elif isinstance(node.op, ast.Or):
                self.complexity += len(node.values) - 1
            self.generic_visit(node)

    visitor = ComplexityVisitor()
    visitor.visit(node)
    return complexity + visitor.complexity


def count_nesting_depth(node: ast.AST) -> int:
    """Calculate maximum nesting depth in a node."""

    class NestingVisitor(ast.NodeVisitor):
        """Visitor to track nesting depth."""

        def __init__(self) -> None:
            self.current_depth = 0
            self.max_depth = 0

        def visit_If(self, node: ast.If) -> None:
            """Track if nesting."""
            self._visit_nested(node)

        def visit_For(self, node: ast.For) -> None:
            """Track for loop nesting."""
            self._visit_nested(node)

        def visit_While(self, node: ast.While) -> None:
            """Track while loop nesting."""
            self._visit_nested(node)

        def visit_With(self, node: ast.With) -> None:
            """Track with statement nesting."""
            self._visit_nested(node)

        def visit_Try(self, node: ast.Try) -> None:
            """Track try block nesting."""
            self._visit_nested(node)

        def _visit_nested(self, node: ast.AST) -> None:
            """Visit a nested structure."""
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

    visitor = NestingVisitor()
    visitor.visit(node)
    return visitor.max_depth


def count_branches(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count the number of branches in a function."""

    class BranchVisitor(ast.NodeVisitor):
        """Visitor to count branches."""

        def __init__(self) -> None:
            self.branches = 0

        def visit_If(self, node: ast.If) -> None:
            """Count if/elif branches."""
            self.branches += 1
            if node.orelse:
                # Check if else contains another if (elif)
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    pass  # Will be counted when we visit that node
                else:
                    self.branches += 1  # else branch
            self.generic_visit(node)

        def visit_For(self, node: ast.For) -> None:
            """Count for loops as branches."""
            self.branches += 1
            self.generic_visit(node)

        def visit_While(self, node: ast.While) -> None:
            """Count while loops as branches."""
            self.branches += 1
            self.generic_visit(node)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            """Count exception handlers."""
            self.branches += 1
            self.generic_visit(node)

    visitor = BranchVisitor()
    visitor.visit(node)
    return visitor.branches
