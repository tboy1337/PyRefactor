"""Boolean logic detector for PyRefactor."""

import ast
from typing import Union

from ..ast_visitor import BaseDetector
from ..models import Severity


class BooleanLogicDetector(BaseDetector):
    """Detects complex boolean logic that can be simplified."""

    MIN_NESTING_FOR_EARLY_RETURN = 3

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "boolean_logic"

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Check for complex boolean operations."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        operator_count = self._count_operators(node)
        max_operators = self.config.boolean_logic.max_boolean_operators

        if operator_count > max_operators:
            self.report_issue(
                node,
                severity=Severity.MEDIUM,
                rule_id="B001",
                message=(
                    f"Complex boolean expression with {operator_count} operators "
                    f"(max {max_operators})"
                ),
                suggestion="Extract boolean sub-expressions to named variables for clarity",
            )

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for redundant boolean comparisons."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(
                comparator.value, bool
            ):
                for op in node.ops:
                    if isinstance(op, ast.Is):
                        self.report_issue(
                            node,
                            severity=Severity.MEDIUM,
                            rule_id="B004",
                            message="Using 'is' for boolean comparison",
                            suggestion=(
                                "Use '==' for value comparison or use the boolean directly"
                            ),
                        )
                        break

        self.generic_visit(node)

    def visit_FunctionDef(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Track function context for early return detection."""
        old_function = self.current_function
        self.current_function = node
        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function context for early return detection."""
        self.visit_FunctionDef(node)

    def visit_If(self, node: ast.If) -> None:
        """Check for opportunities to use early returns."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        if self.current_function:
            self._check_early_return_opportunity(node)

        self.generic_visit(node)

    def _check_early_return_opportunity(self, node: ast.If) -> None:
        """Check if nested ifs could benefit from early returns."""
        nesting_count = 0
        current: ast.AST = node

        while isinstance(current, ast.If):
            nesting_count += 1
            if len(current.body) != 1:
                break

            first_stmt = current.body[0]
            if isinstance(first_stmt, ast.If):
                current = first_stmt
                continue

            if isinstance(first_stmt, (ast.Return, ast.Raise)):
                if nesting_count >= self.MIN_NESTING_FOR_EARLY_RETURN:
                    self.report_issue(
                        node,
                        severity=Severity.MEDIUM,
                        rule_id="B005",
                        message=(
                            f"Deeply nested if statements ({nesting_count} levels) "
                            "with early exit"
                        ),
                        suggestion="Use guard clauses with early returns to reduce nesting",
                    )
            break

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        """Check for De Morgan's law opportunities."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        if isinstance(node.op, ast.Not) and isinstance(node.operand, ast.BoolOp):
            if isinstance(node.operand.op, (ast.And, ast.Or)):
                rule_id, suggestion = (
                    ("B006", "Replace 'not (a and b)' with 'not a or not b'")
                    if isinstance(node.operand.op, ast.And)
                    else ("B007", "Replace 'not (a or b)' with 'not a and not b'")
                )
                self.report_issue(
                    node,
                    severity=Severity.INFO,
                    rule_id=rule_id,
                    message="Complex negation can be simplified using De Morgan's law",
                    suggestion=suggestion,
                )

        self.generic_visit(node)

    def _count_operators(self, node: ast.BoolOp) -> int:
        """Count the number of boolean operators in an expression."""
        total_count = 0
        stack = [node]

        while stack:
            current = stack.pop()
            if isinstance(current, ast.BoolOp):
                total_count += len(current.values) - 1
                stack.extend(v for v in current.values if isinstance(v, ast.BoolOp))

        return total_count
