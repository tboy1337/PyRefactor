"""Boolean logic detector for PyRefactor."""

import ast
from typing import cast

from ..ast_visitor import BaseDetector
from ..models import Issue, Severity


class BooleanLogicDetector(BaseDetector):
    """Detects complex boolean logic that can be simplified."""

    # Minimum nesting level to trigger early return suggestion
    MIN_NESTING_FOR_EARLY_RETURN = 3

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "boolean_logic"

    def _create_issue(
        self,
        node: ast.AST,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> Issue:
        """Create an Issue object from common parameters."""
        return Issue(
            file=self.file_path,
            line=cast(int, getattr(node, "lineno", 0)),
            column=cast(int, getattr(node, "col_offset", 0)),
            severity=severity,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Check for complex boolean operations."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Count total operators in the expression
        operator_count = self._count_operators(node)
        max_operators = self.config.boolean_logic.max_boolean_operators

        if operator_count > max_operators:
            self.add_issue(
                self._create_issue(
                    node,
                    Severity.MEDIUM,
                    "B001",
                    f"Complex boolean expression with {operator_count} operators (max {max_operators})",
                    "Extract boolean sub-expressions to named variables for clarity",
                )
            )

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for redundant boolean comparisons."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for comparison with True/False
        for i, comparator in enumerate(node.comparators):
            self._check_boolean_comparison(node, i, comparator)

        self.generic_visit(node)

    def _check_boolean_comparison(
        self, node: ast.Compare, index: int, comparator: ast.expr
    ) -> None:
        """Check if a comparison involves a boolean constant.

        Args:
            node: The Compare node
            index: Index of the comparator
            comparator: The comparator expression
        """
        if not isinstance(comparator, ast.Constant):
            return

        if not isinstance(comparator.value, bool):
            return

        op = node.ops[index]
        if isinstance(op, ast.Eq):
            self._report_boolean_equality(node, comparator.value)
        elif isinstance(op, ast.Is):
            self._report_boolean_is(node)

    def _report_boolean_equality(self, node: ast.Compare, value: bool) -> None:
        """Report issues with boolean equality comparisons."""
        rule_id, message, suggestion = (
            (
                "B002",
                "Redundant comparison with True",
                "Remove '== True' and use the boolean expression directly",
            )
            if value
            else (
                "B003",
                "Redundant comparison with False",
                "Use 'not expr' instead of 'expr == False'",
            )
        )
        self.add_issue(
            self._create_issue(node, Severity.INFO, rule_id, message, suggestion)
        )

    def _report_boolean_is(self, node: ast.Compare) -> None:
        """Report issues with boolean 'is' comparisons."""
        self.add_issue(
            self._create_issue(
                node,
                Severity.MEDIUM,
                "B004",
                "Using 'is' for boolean comparison",
                "Use '==' for value comparison or use the boolean directly",
            )
        )

    def visit_If(self, node: ast.If) -> None:
        """Check for opportunities to use early returns."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for nested if statements that could use early returns
        if self.current_function:
            self._check_early_return_opportunity(node)

        self.generic_visit(node)

    def _check_early_return_opportunity(self, node: ast.If) -> None:
        """Check if nested ifs could benefit from early returns."""
        # Look for pattern: if x: if y: if z: return
        nesting_count = 0
        current: ast.AST = node

        while isinstance(current, ast.If):
            nesting_count += 1
            # Check if body contains only another If or a return
            if len(current.body) != 1:
                break

            first_stmt = current.body[0]
            if isinstance(first_stmt, ast.If):
                current = first_stmt
                continue

            if isinstance(first_stmt, (ast.Return, ast.Raise)):
                if nesting_count >= self.MIN_NESTING_FOR_EARLY_RETURN:
                    self.add_issue(
                        self._create_issue(
                            node,
                            Severity.MEDIUM,
                            "B005",
                            f"Deeply nested if statements ({nesting_count} levels) with early exit",
                            "Use guard clauses with early returns to reduce nesting",
                        )
                    )
            break

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        """Check for De Morgan's law opportunities."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for not (a and b) or not (a or b)
        if isinstance(node.op, ast.Not) and isinstance(node.operand, ast.BoolOp):
            if isinstance(node.operand.op, (ast.And, ast.Or)):
                rule_id, suggestion = (
                    ("B006", "Replace 'not (a and b)' with 'not a or not b'")
                    if isinstance(node.operand.op, ast.And)
                    else ("B007", "Replace 'not (a or b)' with 'not a and not b'")
                )
                self.add_issue(
                    self._create_issue(
                        node,
                        Severity.INFO,
                        rule_id,
                        "Complex negation can be simplified using De Morgan's law",
                        suggestion,
                    )
                )

        self.generic_visit(node)

    def _count_operators(self, node: ast.BoolOp) -> int:
        """Count the number of boolean operators in an expression.

        Uses iterative approach for better performance on deeply nested expressions.
        """
        total_count = 0
        stack = [node]

        while stack:
            current = stack.pop()
            if isinstance(current, ast.BoolOp):
                # n values require n-1 operators
                total_count += len(current.values) - 1
                # Add nested BoolOps to stack
                stack.extend(v for v in current.values if isinstance(v, ast.BoolOp))

        return total_count
