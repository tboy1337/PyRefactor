"""Loop optimization detector for PyRefactor."""

import ast
from typing import Optional

from ..ast_visitor import BaseDetector
from ..models import Severity

_LoopNode = ast.For | ast.AsyncFor | ast.While


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


class WhileInvariantChecker(ast.NodeVisitor):
    """Check for loop-invariant computations in while loops."""

    def __init__(self, condition_names: set[str]) -> None:
        self.condition_names = condition_names
        self.invariant_calls: list[ast.Call] = []

    def visit_Call(self, call_node: ast.Call) -> None:
        """Check if call depends on while-condition variables."""
        if not self._depends_on_condition_names(call_node):
            if isinstance(call_node.func, ast.Attribute):
                if call_node.func.attr in InvariantChecker.EXPENSIVE_METHODS:
                    self.invariant_calls.append(call_node)
        self.generic_visit(call_node)

    def _depends_on_condition_names(self, node: ast.AST) -> bool:
        """Check if node uses any name from the while condition."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in self.condition_names:
                return True
        return False


class LoopsDetector(BaseDetector):
    """Detects loop optimization opportunities."""

    # Minimum nesting level to trigger nested loop optimization warning
    MIN_NESTED_LOOPS_FOR_WARNING = 2

    _MEDIUM_LOOP_ISSUES: dict[str, tuple[str, str]] = {
        "L003": (
            "Nested loops with comparisons detected",
            "Consider using a dictionary or set for O(1) lookups instead of nested iteration",
        ),
        "L004": (
            "Loop-invariant code detected inside loop",
            "Move computations that don't depend on loop variable outside the loop",
        ),
    }

    def _emit_medium_loop_issue(self, node: _LoopNode, rule_id: str) -> None:
        """Report a medium-severity loop issue by rule ID."""
        message, suggestion = self._MEDIUM_LOOP_ISSUES[rule_id]
        self._report_loop_issue(
            node,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "loops"

    def _report_loop_issue(
        self,
        node: _LoopNode,
        *,
        rule_id: str,
        message: str,
        suggestion: str,
        severity: Severity = Severity.MEDIUM,
    ) -> None:
        """Report a loop optimization issue."""
        self.report_issue(
            node,
            severity=severity,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def visit_For(self, node: ast.For) -> None:
        """Check for loop optimization opportunities."""
        self._visit_for_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Check async for loops for optimization opportunities."""
        self._visit_for_loop(node)

    def _visit_for_loop(self, node: ast.For | ast.AsyncFor) -> None:
        """Run loop checks shared by for and async for."""
        self._check_range_len_pattern(node)
        self._check_manual_index_tracking(node)
        self._check_nested_loop_optimization(node)
        self._check_loop_invariants(node)

        self.generic_visit(node)

    def _check_range_len_pattern(self, node: ast.For | ast.AsyncFor) -> None:
        """Check for range(len(x)) that should use enumerate."""
        # Validate the basic pattern structure
        if not self._is_range_len_call(node):
            return

        # Extract the collection being iterated
        collection = self._extract_collection_from_range_len(node)
        if collection is None:
            return

        # Check if the loop body actually uses indexed access
        if not self._loop_body_accesses_collection(node, collection):
            return

        self.report_issue(
            node,
            severity=Severity.LOW,
            rule_id="L001",
            message="Use enumerate() instead of range(len())",
            suggestion="Replace 'for i in range(len(items)):' with 'for i, item in enumerate(items):'",
        )

    def _is_range_len_call(self, node: ast.For | ast.AsyncFor) -> bool:
        """Check if the loop uses range(len(...)) pattern."""
        if not isinstance(node.iter, ast.Call):
            return False

        if not isinstance(node.iter.func, ast.Name):
            return False

        return node.iter.func.id == "range" and bool(node.iter.args)

    def _extract_collection_from_range_len(
        self, node: ast.For | ast.AsyncFor
    ) -> Optional[ast.AST]:
        """Extract the collection from a range(len(...)) call."""
        if not isinstance(node.iter, ast.Call) or not node.iter.args:
            return None

        first_arg = node.iter.args[0]
        if not isinstance(first_arg, ast.Call):
            return None

        if not isinstance(first_arg.func, ast.Name) or first_arg.func.id != "len":
            return None

        if not first_arg.args:
            return None

        return first_arg.args[0]

    def _check_manual_index_tracking(self, node: _LoopNode) -> None:
        """Check for manual index variable incrementation."""
        tracker = IndexTracker()
        for stmt in node.body:
            tracker.visit(stmt)

        if tracker.manual_indices:
            self.report_issue(
                node,
                severity=Severity.INFO,
                rule_id="L002",
                message=f"Manual index tracking detected: {', '.join(tracker.manual_indices)}",
                suggestion="Use enumerate() to track indices automatically",
            )

    def _check_nested_loop_optimization(self, node: _LoopNode) -> None:
        """Check for nested loops that might benefit from preprocessing."""
        nested_loop_depth = self._max_nested_loop_depth(node)

        if nested_loop_depth > self.MIN_NESTED_LOOPS_FOR_WARNING:
            if self._has_lookup_in_loop_body(node.body):
                self._emit_medium_loop_issue(node, "L003")

    def _max_nested_loop_depth(self, node: _LoopNode, depth: int = 1) -> int:
        """Return the maximum nesting depth of loops under node."""
        max_depth = depth
        for stmt in node.body:
            max_depth = max(max_depth, self._loop_depth_in_scope(stmt, depth + 1))
        return max_depth

    def _loop_depth_in_scope(self, node: ast.AST, depth: int) -> int:
        """Count nested loop depth within a statement, excluding nested functions."""
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return self._max_nested_loop_depth(node, depth)
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
        ):
            return 0
        max_found = 0
        for child in ast.iter_child_nodes(node):
            max_found = max(max_found, self._loop_depth_in_scope(child, depth))
        return max_found

    def _has_lookup_in_loop_body(self, body: list[ast.stmt]) -> bool:
        """Check if nested loops contain membership or subscript lookups."""
        for child in body:
            if self._contains_lookup_pattern(child):
                return True
            if isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
                if self._has_lookup_in_loop_body(child.body):
                    return True
        return False

    def _contains_lookup_pattern(self, stmt: ast.stmt) -> bool:
        """Return True when a statement contains membership or subscript lookups."""
        for child in ast.walk(stmt):
            if isinstance(child, ast.Compare) and any(
                isinstance(op, (ast.In, ast.NotIn)) for op in child.ops
            ):
                return True
            if isinstance(child, ast.Subscript):
                return True
        return False

    def _check_loop_invariants(self, node: ast.For | ast.AsyncFor) -> None:
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
            self._emit_medium_loop_issue(node, "L004")

    @staticmethod
    def _collect_name_ids(node: ast.AST) -> set[str]:
        """Collect variable names referenced in an expression."""
        names: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.add(child.id)
        return names

    def _check_while_loop_invariants(self, node: ast.While) -> None:
        """Check for loop-invariant expensive calls in while loops."""
        condition_names = self._collect_name_ids(node.test)
        checker = WhileInvariantChecker(condition_names)
        for stmt in node.body:
            checker.visit(stmt)

        if checker.invariant_calls:
            self._emit_medium_loop_issue(node, "L004")

    def _loop_body_accesses_collection(
        self, loop_node: ast.For | ast.AsyncFor, collection: ast.AST
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
        self._check_manual_index_tracking(node)
        self._check_nested_loop_optimization(node)
        self._check_while_loop_invariants(node)
        self.generic_visit(node)
