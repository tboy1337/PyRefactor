"""Performance anti-pattern detector for PyRefactor."""

import ast
from typing import Optional, Union, cast

from ..ast_visitor import BaseDetector
from ..config import Config
from ..models import Issue, Severity


class PerformanceDetector(BaseDetector):
    """Detects performance anti-patterns in code."""

    # Type hint patterns for heuristic type detection
    TYPE_HINTS: dict[str, list[str]] = {
        "string": ["str", "text", "message", "name"],
        "list": ["list", "items", "results", "array", "collection"],
        "dict": ["dict", "map", "cache", "mapping"],
    }

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize performance detector."""
        super().__init__(config, file_path, source_lines)
        self.in_loop = False
        self.loop_stack: list[ast.AST] = []

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "performance"

    def _create_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> Issue:
        """Create an Issue object for performance-related issues."""
        return Issue(
            file=self.file_path,
            line=cast(int, getattr(node, "lineno", 0)),
            column=cast(int, getattr(node, "col_offset", 0)),
            severity=severity,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def _visit_loop(self, node: Union[ast.For, ast.While]) -> None:
        """Consolidated method to track loop entry and exit."""
        self.loop_stack.append(node)
        self.in_loop = True
        self.generic_visit(node)
        self.loop_stack.pop()
        self.in_loop = bool(self.loop_stack)

    def visit_For(self, node: ast.For) -> None:
        """Track when we're inside a for loop."""
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        """Track when we're inside a while loop."""
        self._visit_loop(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Check for inefficient augmented assignments in loops."""
        if not self.in_loop or self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for string concatenation with +=
        if not isinstance(node.op, ast.Add):
            self.generic_visit(node)
            return

        if self._matches_type_hint(node.target, "string"):
            self.add_issue(
                self._create_issue(
                    node,
                    severity=Severity.MEDIUM,
                    rule_id="P001",
                    message="String concatenation in loop using += is inefficient",
                    suggestion="Use str.join() with a list or io.StringIO for better performance",
                )
            )
        # Check for list concatenation with +=
        elif self._matches_type_hint(node.target, "list"):
            self.add_issue(
                self._create_issue(
                    node,
                    severity=Severity.LOW,
                    rule_id="P002",
                    message="List concatenation in loop using += may be inefficient",
                    suggestion="Use list.extend() or list comprehension for better performance",
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for inefficient function calls."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        self._check_dict_keys_usage(node)
        self._check_redundant_list_conversion(node)
        self._check_len_usage(node)

        self.generic_visit(node)

    def _check_dict_keys_usage(self, node: ast.Call) -> None:
        """Check for unnecessary dict.keys() in membership tests."""
        if not isinstance(node.func, ast.Attribute):
            return

        if node.func.attr != "keys":
            return

        if not self._matches_type_hint(node.func.value, "dict"):
            return

        parent: Optional[ast.AST] = getattr(node, "_parent", None)
        if not isinstance(parent, ast.Compare):
            return

        if not parent.ops or not isinstance(parent.ops[0], ast.In):
            return

        self.add_issue(  # pyrefactor: ignore
            self._create_issue(
                node,
                severity=Severity.INFO,
                rule_id="P003",
                message="Unnecessary dict.keys() call in membership test",
                suggestion="Use 'key in dict' instead of 'key in dict.keys()'",
            )
        )

    def _check_redundant_list_conversion(self, node: ast.Call) -> None:
        """Check for redundant list() conversions of list comprehensions."""
        if not isinstance(node.func, ast.Name):
            return

        if node.func.id != "list":
            return

        if not node.args or not isinstance(node.args[0], ast.ListComp):
            return
        # pyrefactor: ignore
        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.INFO,
                rule_id="P004",
                message="Redundant list() conversion of list comprehension",
                suggestion="List comprehensions already return lists; remove list() wrapper",
            )
        )

    def _check_len_usage(self, node: ast.Call) -> None:  # pyrefactor: ignore
        """Check for len() calls and their usage patterns."""
        if not isinstance(node.func, ast.Name):
            return

        if node.func.id != "len":
            return

        self._check_len_comparison(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for inefficient comparisons."""
        # Store parent reference for nested checks
        self._set_parent_refs(node)
        self.generic_visit(node)

    def _set_parent_refs(self, node: ast.AST) -> None:
        """Set parent references on all children of a node for upward traversal."""
        for child in ast.walk(node):
            setattr(child, "_parent", node)

    def _check_len_comparison(self, len_call: ast.Call) -> None:
        """Check for inefficient len() comparison patterns.

        Detects patterns like:
        - len(x) > 0 (should use truthiness)
        - len(x) == 0 (should use 'not x')
        """
        len_parent: Optional[ast.AST] = getattr(len_call, "_parent", None)
        if not isinstance(len_parent, ast.Compare):
            return

        if not len_parent.ops or not len_parent.comparators:
            return

        # Check if comparing with 0
        has_zero_comp = any(
            isinstance(comp, ast.Constant) and comp.value == 0
            for comp in len_parent.comparators
        )
        if not has_zero_comp:
            return

        # Check for > or >= operators
        if any(isinstance(op, (ast.Gt, ast.GtE)) for op in len_parent.ops):
            self._add_len_issue(  # pyrefactor: ignore
                len_call,
                "P005",
                "Use truthiness instead of len() > 0",
                "Use 'if container:' instead of 'if len(container) > 0:'",
            )
        # Check for == or != operators
        elif any(isinstance(op, (ast.Eq, ast.NotEq)) for op in len_parent.ops):
            self._add_len_issue(  # pyrefactor: ignore
                len_call,
                "P006",
                "Use truthiness instead of len() == 0",
                "Use 'if not container:' instead of 'if len(container) == 0:'",
            )

    def _add_len_issue(
        self, len_call: ast.Call, rule_id: str, message: str, suggestion: str
    ) -> None:
        """Add an issue for len() usage patterns."""
        self.add_issue(
            self._create_issue(
                len_call,
                severity=Severity.INFO,
                rule_id=rule_id,
                message=message,
                suggestion=suggestion,
            )
        )

    def _matches_type_hint(
        self, node: ast.AST, type_name: str
    ) -> bool:  # pyrefactor: ignore
        """Check if a node likely matches a given type based on naming heuristics.

        Args:
            node: AST node to check
            type_name: Type to check for ('string', 'list', or 'dict')

        Returns:
            True if the node name matches type hints, False otherwise
        """
        if not isinstance(node, ast.Name):
            return False

        name_lower = node.id.lower()
        hints = self.TYPE_HINTS.get(type_name, [])

        # Check if any hint appears in the variable name
        return any(hint in name_lower for hint in hints) or (
            type_name == "list" and name_lower.endswith("s")
        )

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Check for list comprehension opportunities."""
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for inefficient assignments."""
        # Store parent references for nested analysis
        self._set_parent_refs(node)
        self.generic_visit(node)
