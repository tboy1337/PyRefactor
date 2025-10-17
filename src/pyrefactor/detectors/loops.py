"""Loop optimization detector for PyRefactor."""

import ast

from ..ast_visitor import BaseDetector
from ..models import Issue, Severity


class IndexTracker(ast.NodeVisitor):
    """Track manual index increments in loops."""

    def __init__(self) -> None:
        self.manual_indices: set[str] = set()

    def visit_AugAssign(self, aug_node: ast.AugAssign) -> None:
        """Track += 1 operations on variables."""
        if (
            isinstance(aug_node.target, ast.Name)
            and isinstance(aug_node.op, ast.Add)
            and isinstance(aug_node.value, ast.Constant)
            and aug_node.value.value == 1
        ):
            self.manual_indices.add(aug_node.target.id)


class InvariantChecker(ast.NodeVisitor):
    """Check for loop-invariant computations."""

    # Methods that are potentially expensive when called repeatedly in loops
    EXPENSIVE_METHODS = frozenset(
        {"compile", "search", "match", "split", "findall", "sub"}
    )

    def __init__(self, var_name: str) -> None:
        self.var_name = var_name
        self.invariant_calls: list[ast.Call] = []

    def visit_Call(self, call_node: ast.Call) -> None:
        """Check if call depends on loop variable."""
        if not self._depends_on_var(call_node):
            # Check if it's a potentially expensive call
            if isinstance(call_node.func, ast.Attribute):
                if call_node.func.attr in self.EXPENSIVE_METHODS:
                    self.invariant_calls.append(call_node)
        self.generic_visit(call_node)

    def _depends_on_var(self, node: ast.AST) -> bool:
        """Check if node uses the loop variable."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id == self.var_name:
                return True
        return False


class LoopsDetector(BaseDetector):
    """Detects loop optimization opportunities."""

    # Minimum nesting level to trigger nested loop optimization warning
    MIN_NESTED_LOOPS_FOR_WARNING = 2

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "loops"

    def visit_For(self, node: ast.For) -> None:
        """Check for loop optimization opportunities."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for range(len()) pattern
        self._check_range_len_pattern(node)

        # Check for manual index tracking
        self._check_manual_index_tracking(node)

        # Check for nested loops that might benefit from dict lookup
        self._check_nested_loop_optimization(node)

        # Check for loop invariant code
        self._check_loop_invariants(node)

        self.generic_visit(node)

    def _check_range_len_pattern(self, node: ast.For) -> None:
        """Check for range(len(x)) that should use enumerate."""
        if not isinstance(node.iter, ast.Call):
            return

        if not isinstance(node.iter.func, ast.Name):
            return

        if node.iter.func.id != "range":
            return

        if not node.iter.args:
            return

        # Check if argument is len(something)
        first_arg = node.iter.args[0]
        if not isinstance(first_arg, ast.Call):
            return

        if not (isinstance(first_arg.func, ast.Name) and first_arg.func.id == "len"):
            return

        if not first_arg.args:
            return

        collection = first_arg.args[0]
        if not self._loop_body_accesses_collection(node, collection):
            return

        self.add_issue(
            Issue(
                file=self.file_path,
                line=node.lineno,
                column=node.col_offset,
                severity=Severity.LOW,
                rule_id="L001",
                message="Use enumerate() instead of range(len())",
                suggestion="Replace 'for i in range(len(items)):' with 'for i, item in enumerate(items):'",
            )
        )

    def _check_manual_index_tracking(self, node: ast.For) -> None:
        """Check for manual index variable incrementation."""
        tracker = IndexTracker()
        for stmt in node.body:
            tracker.visit(stmt)

        if tracker.manual_indices:
            self.add_issue(
                Issue(
                    file=self.file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    severity=Severity.INFO,
                    rule_id="L002",
                    message=f"Manual index tracking detected: {', '.join(tracker.manual_indices)}",
                    suggestion="Use enumerate() to track indices automatically",
                )
            )

    def _check_nested_loop_optimization(self, node: ast.For) -> None:
        """Check for nested loops that might benefit from preprocessing."""
        # Use a visitor to count nested loops more efficiently
        nested_loop_count = self._count_nested_loops(node)

        if nested_loop_count > self.MIN_NESTED_LOOPS_FOR_WARNING:
            # Check if inner loop is doing lookups
            if self._has_comparison_in_loops(node):
                self.add_issue(
                    Issue(
                        file=self.file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        severity=Severity.MEDIUM,
                        rule_id="L003",
                        message="Nested loops with comparisons detected",
                        suggestion="Consider using a dictionary or set for O(1) lookups instead of nested iteration",
                    )
                )

    def _count_nested_loops(self, node: ast.For) -> int:
        """Count the number of nested for loops."""
        count = 1  # Current loop
        for child in node.body:
            if isinstance(child, ast.For):
                count += self._count_nested_loops(child)
        return count

    def _has_comparison_in_loops(self, node: ast.For) -> bool:
        """Check if there are comparisons in nested loops."""
        for child in node.body:
            if isinstance(child, ast.Compare):
                return True
            if isinstance(child, ast.For):
                if self._has_comparison_in_loops(child):
                    return True
            # Check other compound statements
            for grandchild in ast.walk(child):
                if isinstance(grandchild, ast.Compare):
                    return True
        return False

    def _check_loop_invariants(self, node: ast.For) -> None:
        """Check for loop-invariant code that could be hoisted."""
        # Look for expensive operations that don't depend on loop variable
        loop_var = node.target
        if not isinstance(loop_var, ast.Name):
            return

        loop_var_name = loop_var.id
        checker = InvariantChecker(loop_var_name)
        for stmt in node.body:
            checker.visit(stmt)

        if checker.invariant_calls:
            self.add_issue(
                Issue(
                    file=self.file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    severity=Severity.MEDIUM,
                    rule_id="L004",
                    message="Loop-invariant code detected inside loop",
                    suggestion="Move computations that don't depend on loop variable outside the loop",
                )
            )

    def _loop_body_accesses_collection(
        self, loop_node: ast.For, collection: ast.AST
    ) -> bool:
        """Check if loop body accesses the collection by index."""
        if not isinstance(loop_node.target, ast.Name):
            return False

        index_var = loop_node.target.id
        collection_dump = ast.dump(collection)

        # More efficient: iterate through body statements only once
        for stmt in loop_node.body:
            for node in ast.walk(stmt):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Name)
                    and node.slice.id == index_var
                    and ast.dump(node.value) == collection_dump
                ):
                    return True
        return False

    def visit_While(self, node: ast.While) -> None:
        """Check while loops for optimization opportunities."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Could add while-loop specific checks here
        self.generic_visit(node)
