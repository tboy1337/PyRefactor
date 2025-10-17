"""Performance anti-pattern detector for PyRefactor."""

import ast

from ..ast_visitor import BaseDetector
from ..config import Config
from ..models import Issue, Severity


class PerformanceDetector(BaseDetector):
    """Detects performance anti-patterns in code."""

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize performance detector."""
        super().__init__(config, file_path, source_lines)  # type: ignore[misc]
        self.in_loop = False
        self.loop_stack: list[ast.AST] = []

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "performance"

    def visit_For(self, node: ast.For) -> None:
        """Track when we're inside a loop."""
        self.loop_stack.append(node)
        self.in_loop = True
        self.generic_visit(node)
        self.loop_stack.pop()
        self.in_loop = len(self.loop_stack) > 0

    def visit_While(self, node: ast.While) -> None:
        """Track when we're inside a while loop."""
        self.loop_stack.append(node)
        self.in_loop = True
        self.generic_visit(node)
        self.loop_stack.pop()
        self.in_loop = len(self.loop_stack) > 0

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Check for inefficient augmented assignments in loops."""
        if self.in_loop and not self.is_suppressed(node):
            # Check for string concatenation with +=
            if isinstance(node.op, ast.Add):
                if self._is_string_operation(node.target):
                    self.add_issue(
                        Issue(
                            file=self.file_path,
                            line=node.lineno,
                            column=node.col_offset,
                            severity=Severity.MEDIUM,
                            rule_id="P001",
                            message="String concatenation in loop using += is inefficient",
                            suggestion="Use str.join() with a list or io.StringIO for better performance",
                        )
                    )
                # Check for list concatenation with +=
                elif self._is_list_operation(node.target):
                    self.add_issue(
                        Issue(
                            file=self.file_path,
                            line=node.lineno,
                            column=node.col_offset,
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

        # Check for dict.keys() in membership test
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "keys" and self._is_dict_type(node.func.value):
                parent = getattr(node, "_parent", None)
                if isinstance(parent, ast.Compare) and isinstance(
                    parent.ops[0], ast.In
                ):
                    self.add_issue(
                        Issue(
                            file=self.file_path,
                            line=node.lineno,
                            column=node.col_offset,
                            severity=Severity.INFO,
                            rule_id="P003",
                            message="Unnecessary dict.keys() call in membership test",
                            suggestion="Use 'key in dict' instead of 'key in dict.keys()'",
                        )
                    )

        # Check for redundant list() conversions
        if isinstance(node.func, ast.Name) and node.func.id == "list":
            if node.args and isinstance(node.args[0], ast.ListComp):
                self.add_issue(
                    Issue(
                        file=self.file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        severity=Severity.INFO,
                        rule_id="P004",
                        message="Redundant list() conversion of list comprehension",
                        suggestion="List comprehensions already return lists; remove list() wrapper",
                    )
                )

        # Check for len() > 0 comparison
        if isinstance(node.func, ast.Name) and node.func.id == "len":
            parent = getattr(node, "_parent", None)
            if isinstance(parent, ast.Compare):
                if any(isinstance(op, (ast.Gt, ast.GtE)) for op in parent.ops):
                    if any(
                        isinstance(comp, ast.Constant) and comp.value == 0
                        for comp in parent.comparators
                    ):
                        self.add_issue(
                            Issue(
                                file=self.file_path,
                                line=node.lineno,
                                column=node.col_offset,
                                severity=Severity.INFO,
                                rule_id="P005",
                                message="Use truthiness instead of len() > 0",
                                suggestion="Use 'if container:' instead of 'if len(container) > 0:'",
                            )
                        )
                elif any(isinstance(op, (ast.Eq, ast.NotEq)) for op in parent.ops):
                    if any(
                        isinstance(comp, ast.Constant) and comp.value == 0
                        for comp in parent.comparators
                    ):
                        self.add_issue(
                            Issue(
                                file=self.file_path,
                                line=node.lineno,
                                column=node.col_offset,
                                severity=Severity.INFO,
                                rule_id="P006",
                                message="Use truthiness instead of len() == 0",
                                suggestion="Use 'if not container:' instead of 'if len(container) == 0:'",
                            )
                        )

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for inefficient comparisons."""
        # Store parent reference for nested checks
        for child in ast.walk(node):
            setattr(child, "_parent", node)
        self.generic_visit(node)

    def _is_string_operation(self, node: ast.AST) -> bool:
        """Check if a node likely operates on strings."""
        # This is a heuristic; we can't always determine types
        if isinstance(node, ast.Name):
            return "str" in node.id.lower() or "text" in node.id.lower()
        return False

    def _is_list_operation(self, node: ast.AST) -> bool:
        """Check if a node likely operates on lists."""
        if isinstance(node, ast.Name):
            name = node.id.lower()
            return (
                "list" in name
                or "items" in name
                or "results" in name
                or name.endswith("s")
            )
        return False

    def _is_dict_type(self, node: ast.AST) -> bool:
        """Check if a node likely represents a dict."""
        if isinstance(node, ast.Name):
            name = node.id.lower()
            return "dict" in name or "map" in name or "cache" in name
        return False

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """Check for list comprehension opportunities."""
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for inefficient assignments."""
        # Store parent references for nested analysis
        for child in ast.walk(node):
            setattr(child, "_parent", node)
        self.generic_visit(node)

