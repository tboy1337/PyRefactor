"""Control flow simplification detector for PyRefactor."""

import ast
from typing import cast

from ..ast_visitor import BaseDetector
from ..models import Issue, Severity


class ControlFlowDetector(BaseDetector):
    """Detects unnecessary else/elif clauses after return/raise/break/continue."""

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "control_flow"

    def _create_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> Issue:
        """Create an Issue object for control flow issues."""
        return Issue(
            file=self.file_path,
            line=cast(int, getattr(node, "lineno", 0)),
            column=cast(int, getattr(node, "col_offset", 0)),
            severity=severity,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def visit_If(self, node: ast.If) -> None:
        """Check for unnecessary else clauses."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check if all paths in if/elif chain end with a terminating statement
        if node.orelse:
            # Check if if-body always terminates
            if_terminates = self._always_terminates(node.body)

            if if_terminates:
                # Determine what kind of termination
                terminator = self._get_terminator_type(node.body)

                if terminator == "return":
                    self._report_unnecessary_else(node, "R002", "return")
                elif terminator == "raise":
                    self._report_unnecessary_else(node, "R003", "raise")
                elif terminator == "break":
                    self._report_unnecessary_else(node, "R004", "break")
                elif terminator == "continue":
                    self._report_unnecessary_else(node, "R005", "continue")

        self.generic_visit(node)

    def _always_terminates(self, body: list[ast.stmt]) -> bool:
        """Check if a code block always terminates (return/raise/break/continue)."""
        if not body:
            return False

        # Check the last statement
        last_stmt = body[-1]

        # Direct terminating statements
        if isinstance(last_stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            return True

        # If statement - check if all branches terminate
        if isinstance(last_stmt, ast.If):
            # Must have an else clause to ensure all paths terminate
            if not last_stmt.orelse:
                return False

            # Check if both if and else terminate
            if_terminates = self._always_terminates(last_stmt.body)
            else_terminates = self._always_terminates(last_stmt.orelse)
            return if_terminates and else_terminates

        # Try statement - all branches must terminate
        if isinstance(last_stmt, ast.Try):
            try_terminates = self._always_terminates(last_stmt.body)
            handlers_terminate = all(
                self._always_terminates(handler.body) for handler in last_stmt.handlers
            )
            # If there's an else clause, it must also terminate
            else_terminates = (
                self._always_terminates(last_stmt.orelse) if last_stmt.orelse else True
            )
            # Finally doesn't affect termination
            return try_terminates and handlers_terminate and else_terminates

        return False

    def _get_terminator_type(self, body: list[ast.stmt]) -> str:
        """Get the type of terminator in a code block."""
        if not body:
            return ""

        last_stmt = body[-1]

        # Map statement types to their string names
        terminator_map = {
            ast.Return: "return",
            ast.Raise: "raise",
            ast.Break: "break",
            ast.Continue: "continue",
        }

        stmt_type = type(last_stmt)
        if stmt_type in terminator_map:
            return terminator_map[stmt_type]

        # Check nested structures
        if isinstance(last_stmt, ast.If):
            # Get terminator from if body (assuming we've already checked it terminates)
            return self._get_terminator_type(last_stmt.body)

        return ""

    def _report_unnecessary_else(
        self, node: ast.If, rule_id: str, terminator: str
    ) -> None:
        """Report an unnecessary else clause."""
        # Determine if it's an elif or else
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            clause_type = "elif"
        else:
            clause_type = "else"

        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.MEDIUM,
                rule_id=rule_id,
                message=f"Unnecessary '{clause_type}' after '{terminator}' statement",
                suggestion=f"Remove '{clause_type}' and unindent its body since the "
                f"preceding code always executes '{terminator}'",
            )
        )
