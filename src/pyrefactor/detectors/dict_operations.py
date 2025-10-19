"""Dictionary operations detector for PyRefactor."""

import ast
from typing import cast

from ..ast_visitor import BaseDetector
from ..models import Issue, Severity


class DictOperationsDetector(BaseDetector):
    """Detects inefficient or non-idiomatic dictionary operations."""

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "dict_operations"

    def _create_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> Issue:
        """Create an Issue object for dictionary operation issues."""
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
        """Check for dict.get() opportunities."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Pattern: if key in dict: x = dict[key] else: x = default
        self._check_dict_get_pattern(node)

        self.generic_visit(node)

    def _check_dict_get_pattern(self, node: ast.If) -> None:
        """Check for pattern that could use dict.get()."""
        # Validate basic structure
        if not self._is_valid_dict_get_structure(node):
            return

        # Extract and validate components
        components = self._extract_dict_get_components(node)
        if not components:
            return

        var_name, key_name, dict_name, default_val = components

        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.LOW,
                rule_id="R006",
                message="Consider using dict.get() instead of if/else for key lookup",
                suggestion=f"Use '{var_name} = {dict_name}.get({key_name}, {default_val})' "
                f"instead of if/else block",
            )
        )

    def _is_valid_dict_get_structure(self, node: ast.If) -> bool:
        """Check if node has the basic structure for dict.get() refactoring."""
        # Check if condition is "key in dict"
        if not isinstance(node.test, ast.Compare):
            return False

        if len(node.test.ops) != 1 or not isinstance(node.test.ops[0], ast.In):
            return False

        # Must have both if and else branches with single assignments
        if not node.orelse or len(node.body) != 1 or len(node.orelse) != 1:
            return False

        if_stmt = node.body[0]
        else_stmt = node.orelse[0]

        return isinstance(if_stmt, ast.Assign) and isinstance(else_stmt, ast.Assign)

    def _extract_dict_get_components(
        self, node: ast.If
    ) -> tuple[str, str, str, str] | None:
        """Extract variable names and values for dict.get() suggestion."""
        if_stmt = node.body[0]
        else_stmt = node.orelse[0]

        # Validate assignments
        if not (
            isinstance(if_stmt, ast.Assign)
            and isinstance(else_stmt, ast.Assign)
            and len(if_stmt.targets) == 1
            and len(else_stmt.targets) == 1
            and isinstance(if_stmt.targets[0], ast.Name)
            and isinstance(else_stmt.targets[0], ast.Name)
        ):
            return None

        # Both should assign to the same variable
        if if_stmt.targets[0].id != else_stmt.targets[0].id:
            return None

        # Validate if-body is dict[key] access
        if not isinstance(if_stmt.value, ast.Subscript):
            return None

        # Extract names from condition
        key_name = node.test.left
        dict_name = node.test.comparators[0]

        if not isinstance(key_name, ast.Name) or not isinstance(dict_name, ast.Name):
            return None

        # Verify if_stmt accesses dict[key]
        if not (
            isinstance(if_stmt.value.value, ast.Name)
            and if_stmt.value.value.id == dict_name.id
            and isinstance(if_stmt.value.slice, ast.Name)
            and if_stmt.value.slice.id == key_name.id
        ):
            return None

        var_name = if_stmt.targets[0].id
        default_val = ast.unparse(else_stmt.value) if hasattr(ast, "unparse") else "..."

        return (var_name, key_name.id, dict_name.id, default_val)

    def visit_For(self, node: ast.For) -> None:
        """Check for dictionary iteration improvements."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for .keys() that should be removed
        self._check_unnecessary_keys(node)

        # Check for .items() opportunity
        self._check_dict_items_opportunity(node)

        self.generic_visit(node)

    def _check_unnecessary_keys(self, node: ast.For) -> None:
        """Check for unnecessary .keys() in for loop."""
        # Pattern: for key in dict.keys()
        if not isinstance(node.iter, ast.Call):
            return

        if not isinstance(node.iter.func, ast.Attribute):
            return

        if node.iter.func.attr != "keys":
            return

        dict_name = self._get_name(node.iter.func.value)
        if not dict_name:
            return

        target_name = self._get_target_name(node.target)
        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.INFO,
                rule_id="R009",
                message="Unnecessary .keys() call when iterating dictionary",
                suggestion=f"Use 'for {target_name} in {dict_name}:' "
                f"instead of 'for {target_name} in {dict_name}.keys():'",
            )
        )

    def _check_dict_items_opportunity(self, node: ast.For) -> None:
        """Check if loop iterates keys but also accesses values."""
        # Pattern: for key in dict: ... dict[key] ...
        if not isinstance(node.target, ast.Name):
            return

        # Get the iterable name
        iter_name = self._get_name(node.iter)
        if not iter_name:
            return

        key_name = node.target.id

        # Check if body contains dict[key] accesses
        if self._has_dict_key_access(node.body, iter_name, key_name):
            self.add_issue(
                self._create_issue(
                    node,
                    severity=Severity.MEDIUM,
                    rule_id="R007",
                    message="Consider using .items() to access both keys and values",
                    suggestion=f"Use 'for {key_name}, value in {iter_name}.items():' "
                    f"to avoid repeated dict lookups",
                )
            )

    def _has_dict_key_access(
        self, body: list[ast.stmt], dict_name: str, key_name: str
    ) -> bool:
        """Check if body contains dict[key] access pattern."""
        for stmt in body:
            for child in ast.walk(stmt):
                if self._is_dict_key_subscript(child, dict_name, key_name):
                    return True
        return False

    def _is_dict_key_subscript(
        self, node: ast.AST, dict_name: str, key_name: str
    ) -> bool:
        """Check if node is a dict[key] subscript."""
        return (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == dict_name
            and isinstance(node.slice, ast.Name)
            and node.slice.id == key_name
        )

    def visit_Call(self, node: ast.Call) -> None:
        """Check for dict comprehension opportunities."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Pattern: dict([(k, v) for ...]) or dict([...])
        self._check_dict_comprehension(node)

        self.generic_visit(node)

    def _check_dict_comprehension(self, node: ast.Call) -> None:
        """Check if dict() call can be replaced with dict comprehension."""
        if not (isinstance(node.func, ast.Name) and node.func.id == "dict"):
            return

        if not node.args:
            return

        arg = node.args[0]

        # Check if it's a list comprehension with tuples
        if not isinstance(arg, ast.ListComp):
            return

        if not (isinstance(arg.elt, ast.Tuple) and len(arg.elt.elts) == 2):
            return

        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.LOW,
                rule_id="R010",
                message="Consider using dictionary comprehension instead of dict()",
                suggestion="Use '{k: v for ...}' instead of 'dict([(k, v) for ...])' "
                "for better readability and performance",
            )
        )

    def _get_name(self, node: ast.AST) -> str | None:
        """Extract the name from a node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _get_target_name(self, node: ast.AST) -> str:
        """Get the target name from a for loop target."""
        if isinstance(node, ast.Name):
            return node.id
        return "item"
