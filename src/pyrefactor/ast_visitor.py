"""Base AST visitor framework for PyRefactor detectors."""

import ast
from abc import ABC, abstractmethod
from typing import Union

from .config import Config
from .models import Issue, Severity


def node_lineno(node: ast.AST) -> int | None:
    """Return a valid 1-based line number for an AST node, or None."""
    lineno = getattr(node, "lineno", None)
    return lineno if isinstance(lineno, int) and lineno >= 1 else None


def node_col_offset(node: ast.AST) -> int:
    """Return the column offset for an AST node."""
    col = getattr(node, "col_offset", 0)
    return col if isinstance(col, int) else 0


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Build a map of child AST nodes to their parent nodes."""
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    return parent_map


class BaseDetector(ast.NodeVisitor, ABC):
    """Base class for all detectors."""

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize detector with configuration and source context."""
        self.config = config
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: list[Issue] = []
        self.current_function: Union[ast.FunctionDef, ast.AsyncFunctionDef, None] = None

    @abstractmethod
    def get_detector_name(self) -> str:
        """Return the name of this detector."""

    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the detector's list."""
        self.issues.append(issue)

    def report_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> None:
        """Create and add an issue when the node has a valid line number."""
        if self.is_suppressed(node, rule_id):
            return
        line = node_lineno(node)
        if line is None:
            return
        snippet = self.get_source_line(line).strip()
        self.add_issue(
            Issue(
                file=self.file_path,
                line=line,
                column=node_col_offset(node),
                severity=severity,
                rule_id=rule_id,
                message=message,
                suggestion=suggestion,
                code_snippet=snippet or None,
            )
        )

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

    def is_suppressed(self, node: ast.AST, rule_id: str | None = None) -> bool:
        """Check if a node has a suppression comment."""
        lineno = node_lineno(node)
        if lineno is None:
            return False

        line = self.get_source_line(lineno)
        if self._line_suppresses(line, rule_id):
            return True

        if lineno > 1:
            prev_line = self.get_source_line(lineno - 1)
            if self._line_suppresses(prev_line, rule_id):
                return True

        return False

    @staticmethod
    def _line_suppresses(line: str, rule_id: str | None) -> bool:
        """Return True when a source line suppresses the given rule."""
        if "# noqa" in line:
            return True

        marker = "# pyrefactor: ignore"
        if marker not in line:
            return False

        suffix = line.split(marker, 1)[1].strip()
        if not suffix:
            return True

        specified_rules = {
            token.strip().upper()
            for token in suffix.replace(",", " ").split()
            if token.strip()
        }
        if not specified_rules:
            return True
        if rule_id is None:
            return False
        return rule_id.upper() in specified_rules

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run the detector on an AST and return issues found."""
        self.issues = []
        self.visit(tree)
        return self.issues


def calculate_cyclomatic_complexity(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> int:
    """Calculate cyclomatic complexity of a function."""

    class ComplexityVisitor(ast.NodeVisitor):
        """Visitor to count decision points."""

        def __init__(self) -> None:
            self.complexity = 1  # Base complexity

        def visit_If(self, node: ast.If) -> None:
            """Count if statements."""
            self._increment_and_visit(node)

        def visit_For(self, node: ast.For) -> None:
            """Count for loops."""
            self._increment_and_visit(node)

        def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
            """Count async for loops."""
            self._increment_and_visit(node)

        def visit_While(self, node: ast.While) -> None:
            """Count while loops."""
            self._increment_and_visit(node)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            """Count except handlers."""
            self._increment_and_visit(node)

        def visit_TryStar(self, node: ast.TryStar) -> None:
            """Count except* handlers in exception groups."""
            self.complexity += len(node.handlers)
            self.generic_visit(node)

        def visit_With(self, node: ast.With) -> None:
            """Count with statements."""
            self._increment_and_visit(node)

        def visit_Assert(self, node: ast.Assert) -> None:
            """Count assertions."""
            self._increment_and_visit(node)

        def visit_Match(self, node: ast.Match) -> None:
            """Count match/case statements."""
            self.complexity += len(node.cases)
            self.generic_visit(node)

        def visit_BoolOp(self, node: ast.BoolOp) -> None:
            """Count boolean operations (and/or)."""
            self.complexity += len(node.values) - 1
            self.generic_visit(node)

        def _increment_and_visit(self, node: ast.AST) -> None:
            """Increment complexity and continue visiting."""
            self.complexity += 1
            self.generic_visit(node)

    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity


def count_nesting_depth(node: ast.AST) -> int:
    """Calculate maximum nesting depth in a node."""

    class NestingVisitor(ast.NodeVisitor):
        """Visitor to track nesting depth."""

        def __init__(self, root: ast.AST) -> None:
            self.root = root
            self.current_depth = 0
            self.max_depth = 0

        def visit_If(self, node: ast.If) -> None:
            """Track if nesting."""
            self._visit_nested(node)

        def visit_For(self, node: ast.For) -> None:
            """Track for loop nesting."""
            self._visit_nested(node)

        def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
            """Track async for loop nesting."""
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

        def visit_TryStar(self, node: ast.TryStar) -> None:
            """Track try* block nesting."""
            self._visit_nested(node)

        def visit_Match(self, node: ast.Match) -> None:
            """Track match statement nesting."""
            self._visit_nested(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            """Traverse the root function only; skip nested functions."""
            if node is self.root:
                self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            """Traverse the root async function only; skip nested functions."""
            if node is self.root:
                self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            """Do not count nesting inside nested classes."""

        def _visit_nested(self, node: ast.AST) -> None:
            """Visit a nested structure."""
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

    visitor = NestingVisitor(node)
    visitor.visit(node)
    return visitor.max_depth


def count_branches(node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> int:
    """Count the number of branches in a function."""

    class BranchVisitor(ast.NodeVisitor):
        """Visitor to count branches."""

        def __init__(self, root: ast.AST) -> None:
            self.root = root
            self.branches = 0

        def visit_If(self, node: ast.If) -> None:
            """Count if/elif branches."""
            self.branches += 1
            if node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    pass
                else:
                    self.branches += 1
            self.generic_visit(node)

        def visit_For(self, node: ast.For) -> None:
            """Count for loops as branches."""
            self.branches += 1
            self.generic_visit(node)

        def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
            """Count async for loops as branches."""
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

        def visit_TryStar(self, node: ast.TryStar) -> None:
            """Count exception group handlers."""
            self.branches += len(node.handlers)
            self.generic_visit(node)

        def visit_Match(self, node: ast.Match) -> None:
            """Count match/case branches."""
            self.branches += len(node.cases)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            """Traverse the root function only; skip nested functions."""
            if node is self.root:
                self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            """Traverse the root async function only; skip nested functions."""
            if node is self.root:
                self.generic_visit(node)

    visitor = BranchVisitor(node)
    visitor.visit(node)
    return visitor.branches
