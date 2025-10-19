"""Context manager detector for PyRefactor."""

import ast
from typing import cast

from ..ast_visitor import BaseDetector
from ..config import Config
from ..models import Issue, Severity

# Functions that return context managers and should be used with 'with'
CONTEXT_MANAGER_FUNCS = frozenset(
    {
        "open",
        "file",
        "urlopen",
        "NamedTemporaryFile",
        "SpooledTemporaryFile",
        "TemporaryDirectory",
        "TemporaryFile",
        "ZipFile",
        "PyZipFile",
        "TarFile",
        "Popen",
        "Pool",
    }
)

# Methods that return context managers
CONTEXT_MANAGER_METHODS = frozenset({"open", "acquire", "start"})


class ContextManagerDetector(BaseDetector):
    """Detects resource-allocating operations that should use 'with' statements."""

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize context manager detector."""
        super().__init__(config, file_path, source_lines)
        self.resource_assignments: dict[str, ast.Assign | ast.AnnAssign] = {}
        self.used_in_with: set[str] = set()
        self.parent_map: dict[ast.AST, ast.AST] = {}

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run the detector on an AST and return issues found."""
        # Build parent map once for the entire tree
        self._build_parent_map(tree)
        self.visit(tree)
        return self.issues

    def _build_parent_map(self, tree: ast.AST) -> None:
        """Build a map of child -> parent for the entire tree."""
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                self.parent_map[child] = parent

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "context_manager"

    def _create_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> Issue:
        """Create an Issue object for context manager issues."""
        return Issue(
            file=self.file_path,
            line=cast(int, getattr(node, "lineno", 0)),
            column=cast(int, getattr(node, "col_offset", 0)),
            severity=severity,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def _is_context_manager_call(self, node: ast.Call) -> bool:
        """Check if a call returns a context manager."""
        # Check for direct function calls (e.g., open(), file())
        if isinstance(node.func, ast.Name):
            return node.func.id in CONTEXT_MANAGER_FUNCS

        # Check for method calls (e.g., lock.acquire(), Path.open())
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in CONTEXT_MANAGER_METHODS

        return False

    def _is_used_in_return(self, node: ast.Call) -> bool:
        """Check if the call is part of a return statement."""
        current = self.parent_map.get(node)
        while current:
            if isinstance(current, ast.Return):
                return True
            # Stop at function boundaries
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            current = self.parent_map.get(current)
        return False

    def _is_used_in_with_context(self, node: ast.Call) -> bool:
        """Check if the call is already used in a 'with' statement."""
        current = self.parent_map.get(node)
        while current:
            if isinstance(current, ast.With):
                return True
            # Stop at function boundaries
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            current = self.parent_map.get(current)
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for resource-allocating assignments."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check if the value is a context manager call
        if isinstance(node.value, ast.Call) and self._is_context_manager_call(
            node.value
        ):
            self._check_and_report_context_manager(node, node.value)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Check for context manager calls used as statements without assignment."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check if the expression contains a context manager call (could be chained)
        cm_call = self._find_context_manager_call(node.value)
        if cm_call:
            self._check_and_report_context_manager(node, cm_call)

        self.generic_visit(node)

    def _check_and_report_context_manager(
        self, node: ast.AST, cm_call: ast.Call
    ) -> None:
        """Check and report if a context manager call should use 'with' statement."""
        # Skip if already in a with statement
        if self._is_used_in_with_context(cm_call):
            return

        # Skip if this is in a return statement or being passed
        if self._is_used_in_return(cm_call):
            return

        # Get the function name for a better error message
        func_name = self._get_func_name(cm_call)

        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.HIGH,
                rule_id="R001",
                message=f"Resource-allocating operation '{func_name}' should use 'with' statement",
                suggestion=f"Use 'with {func_name}(...) as resource:' to ensure proper resource cleanup",
            )
        )

    def _find_context_manager_call(self, node: ast.AST) -> ast.Call | None:
        """Find a context manager call in an expression tree."""
        if isinstance(node, ast.Call) and self._is_context_manager_call(node):
            return node

        # Check nested calls (e.g., open(...).read())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # Check the object being called
            if isinstance(node.func.value, ast.Call) and self._is_context_manager_call(
                node.func.value
            ):
                return node.func.value

        return None

    def _get_func_name(self, call: ast.Call) -> str:
        """Extract the function name from a call node."""
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return "unknown"
