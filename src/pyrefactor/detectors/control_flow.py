"""Control flow simplification detector for PyRefactor."""

import ast

from ..ast_visitor import BaseDetector
from ..models import Severity


class ControlFlowDetector(BaseDetector):
    """Detects unnecessary else/elif clauses after return/raise/break/continue."""

    _TERMINATOR_RULES = {
        "return": "R002",
        "raise": "R003",
        "break": "R004",
        "continue": "R005",
    }

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "control_flow"

    def visit_If(self, node: ast.If) -> None:
        """Check for unnecessary else clauses."""
        self._check_unnecessary_else(node)
        self.generic_visit(node)

    def _check_unnecessary_else(self, node: ast.If) -> None:
        """Check if the else clause is unnecessary after a terminating statement."""
        # Early return if no else clause
        if not node.orelse:
            return

        # Check if if-body always terminates
        if not self._always_terminates(node.body):
            return

        # Determine what kind of termination
        terminator = self._get_terminator_type(node.body)

        # Report issue if we have a known terminator
        if terminator in self._TERMINATOR_RULES:
            self._report_unnecessary_else(
                node, self._TERMINATOR_RULES[terminator], terminator
            )

    def _always_terminates(self, body: list[ast.stmt]) -> bool:
        """Check if a code block always terminates (return/raise/break/continue)."""
        if not body:
            return False

        last_stmt = body[-1]
        if isinstance(last_stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
            return True
        if isinstance(last_stmt, ast.If):
            return self._if_always_terminates(last_stmt)
        if isinstance(last_stmt, ast.Try):
            return self._try_always_terminates(last_stmt)
        if isinstance(last_stmt, ast.Match):
            return self._match_always_terminates(last_stmt)
        return False

    def _if_always_terminates(self, node: ast.If) -> bool:
        """Check if an if/else always terminates on all paths."""
        if not node.orelse:
            return False
        return self._always_terminates(node.body) and self._always_terminates(
            node.orelse
        )

    def _try_always_terminates(self, node: ast.Try) -> bool:
        """Check if a try/except/else always terminates on all paths."""
        if node.finalbody:
            return False
        try_terminates = self._always_terminates(node.body)
        handlers_terminate = all(
            self._always_terminates(handler.body) for handler in node.handlers
        )
        else_terminates = self._always_terminates(node.orelse) if node.orelse else True
        return try_terminates and handlers_terminate and else_terminates

    def _match_always_terminates(self, node: ast.Match) -> bool:
        """Check if all match cases always terminate."""
        if not node.cases:
            return False
        return all(self._always_terminates(case.body) for case in node.cases)

    def _get_if_terminator_type(self, node: ast.If) -> str:
        """Get terminator type from an if/elif chain when all paths terminate."""
        if self._always_terminates(node.body):
            return self._get_terminator_type(node.body)
        elif_node = (
            node.orelse[0]
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)
            else None
        )
        if isinstance(elif_node, ast.If) and self._always_terminates(elif_node.body):
            return self._get_terminator_type(elif_node.body)
        return ""

    def _get_match_terminator_type(self, node: ast.Match) -> str:
        """Get terminator type from a match when all cases terminate."""
        if not node.cases:
            return ""
        return self._get_terminator_type(node.cases[0].body)

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
            return self._get_if_terminator_type(last_stmt)

        if isinstance(last_stmt, ast.Try):
            return self._get_try_terminator_type(last_stmt)

        if isinstance(last_stmt, ast.Match):
            return self._get_match_terminator_type(last_stmt)

        return ""

    def _get_try_terminator_type(self, node: ast.Try) -> str:
        """Get terminator type from a try when all paths terminate."""
        if not self._try_always_terminates(node):
            return ""
        terminator = self._get_terminator_type(node.body)
        if terminator:
            return terminator
        for handler in node.handlers:
            terminator = self._get_terminator_type(handler.body)
            if terminator:
                return terminator
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

        self.report_issue(
            node,
            severity=Severity.MEDIUM,
            rule_id=rule_id,
            message=f"Unnecessary '{clause_type}' after '{terminator}' statement",
            suggestion=f"Remove '{clause_type}' and unindent its body since the "
            f"preceding code always executes '{terminator}'",
        )
