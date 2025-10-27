"""Comparison improvements detector for PyRefactor."""

import ast
from typing import Optional, Tuple, cast

from ..ast_visitor import BaseDetector
from ..models import Issue, Severity

# Singleton values that should be compared with 'is' instead of '=='
SINGLETON_VALUES = frozenset({True, False, None})


class ComparisonsDetector(BaseDetector):
    """Detects non-idiomatic or inefficient comparison patterns."""

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "comparisons"

    def _create_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> Issue:
        """Create an Issue object for comparison issues."""
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
        """Check for patterns that could use 'in' operator or chained comparisons."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # Check for multiple equality comparisons
        if isinstance(node.op, ast.Or):
            self._check_consider_using_in(node)

        # Check for chainable comparisons
        if isinstance(node.op, ast.And):
            self._check_chained_comparison(node)

        self.generic_visit(node)

    def _check_consider_using_in(self, node: ast.BoolOp) -> None:
        """Check for pattern: x == a or x == b or x == c."""
        if not all(isinstance(val, ast.Compare) for val in node.values):
            return

        # Extract all comparisons
        comparisons: list[ast.Compare] = [cast(ast.Compare, val) for val in node.values]

        # All should be single == comparisons
        if not all(
            len(comp.ops) == 1 and isinstance(comp.ops[0], ast.Eq)
            for comp in comparisons
        ):
            return

        # All should compare the same left operand
        first_left = ast.dump(comparisons[0].left)
        if not all(ast.dump(comp.left) == first_left for comp in comparisons):
            return

        # We have x == a or x == b pattern
        if len(comparisons) >= 2:
            var_name = (
                ast.unparse(comparisons[0].left) if hasattr(ast, "unparse") else "x"
            )
            values = []
            for comp in comparisons:
                if comp.comparators:
                    val = (
                        ast.unparse(comp.comparators[0])
                        if hasattr(ast, "unparse")
                        else "value"
                    )
                    values.append(val)

            values_str = ", ".join(values)

            self.add_issue(
                self._create_issue(
                    node,
                    severity=Severity.LOW,
                    rule_id="R011",
                    message="Multiple equality comparisons can be simplified using 'in' operator",
                    suggestion=f"Use '{var_name} in ({values_str})' instead of multiple '==' comparisons. "
                    f"Use a set if values are hashable for O(1) lookup.",
                )
            )

    def _check_chained_comparison(self, node: ast.BoolOp) -> None:
        """Check for pattern: a < b and b < c that can be chained."""
        if len(node.values) < 2:
            return

        # Check pairs of comparisons
        for i in range(len(node.values) - 1):
            chain_info = self._try_extract_chainable_pair(
                node.values[i], node.values[i + 1]
            )
            if chain_info:
                self._report_chainable_comparison(node, chain_info)
                return  # Report once

    def _try_extract_chainable_pair(
        self, val1: ast.expr, val2: ast.expr
    ) -> Optional[Tuple[str, str, str, str, str]]:
        """Try to extract chainable comparison info from two values.

        Returns (left1_str, op1, mid_str, op2, right2_str) if chainable, else None.
        """
        # Both must be comparisons
        if not isinstance(val1, ast.Compare) or not isinstance(val2, ast.Compare):
            return None

        comp1 = val1
        comp2 = val2

        # Both should be single comparisons
        if len(comp1.ops) != 1 or len(comp2.ops) != 1:
            return None

        # Check if comp1's right operand matches comp2's left operand
        if not comp1.comparators:
            return None

        right1 = comp1.comparators[0]
        left2 = comp2.left

        # Check if they share a common operand
        if ast.dump(right1) != ast.dump(left2):
            return None

        # Get operator strings
        op1 = self._get_op_str(comp1.ops[0])
        op2 = self._get_op_str(comp2.ops[0])

        if not op1 or not op2:
            return None

        # Extract string representations
        left1_str = ast.unparse(comp1.left) if hasattr(ast, "unparse") else "a"
        mid_str = ast.unparse(right1) if hasattr(ast, "unparse") else "b"
        right2_str = (
            ast.unparse(comp2.comparators[0])
            if hasattr(ast, "unparse") and comp2.comparators
            else "c"
        )

        return (left1_str, op1, mid_str, op2, right2_str)

    def _report_chainable_comparison(
        self, node: ast.BoolOp, chain_info: Tuple[str, str, str, str, str]
    ) -> None:
        """Report a chainable comparison issue."""
        left1_str, op1, mid_str, op2, right2_str = chain_info
        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.LOW,
                rule_id="R012",
                message="Comparison can be chained for better readability",
                suggestion=f"Use '{left1_str} {op1} {mid_str} {op2} {right2_str}' "
                f"instead of separate comparisons",
            )
        )

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check for singleton comparisons and type checks."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        self._check_singleton_comparison(node)
        self._check_unidiomatic_typecheck(node)

        self.generic_visit(node)

    def _is_singleton_const(self, node: ast.AST) -> bool:
        """Check if node is a singleton constant (True, False, or None).

        Uses identity checking (is) like pylint to avoid false positives
        with values like 1 which equals True but is not the same object.
        """
        if not isinstance(node, ast.Constant):
            return False
        # Use identity check (is) not equality (==) to avoid issues with 1 == True
        return any(node.value is value for value in SINGLETON_VALUES)

    def _report_none_comparison(
        self, node: ast.Compare, checking_for_absence: bool
    ) -> None:
        """Report inappropriate None comparison."""
        correct_op = "is not" if checking_for_absence else "is"
        wrong_op = "!=" if checking_for_absence else "=="
        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.MEDIUM,
                rule_id="R014",
                message="Comparison with None should use 'is' or 'is not'",
                suggestion=f"Use '{correct_op}' instead of '{wrong_op}' when comparing with None",
            )
        )

    def _report_bool_comparison(
        self, node: ast.Compare, op: ast.cmpop, singleton_val: bool, other: ast.AST
    ) -> None:
        """Report redundant True/False comparison."""
        other_str = ast.unparse(other) if hasattr(ast, "unparse") else "expr"

        # Determine the suggested replacement
        suggestion = self._get_bool_comparison_suggestion(singleton_val, op, other_str)

        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.INFO,
                rule_id="R014",
                message=f"Redundant comparison with {singleton_val}",
                suggestion=suggestion,
            )
        )

    def _get_bool_comparison_suggestion(
        self, singleton_val: bool, op: ast.cmpop, other_str: str
    ) -> str:
        """Generate suggestion text for boolean comparison."""
        is_eq = isinstance(op, ast.Eq)

        if singleton_val:  # True
            if is_eq:
                return f"Use '{other_str}' directly instead of comparing with True"
            return f"Use 'not {other_str}' instead of '!= True'"

        # False
        if is_eq:
            return f"Use 'not {other_str}' instead of comparing with False"
        return f"Use '{other_str}' directly instead of '!= False'"

    def _check_singleton_comparison(self, node: ast.Compare) -> None:
        """Check for comparisons with True/False/None using == instead of is.

        Implementation based on pylint's comparison checker.
        """
        if len(node.ops) != 1:
            return

        op = node.ops[0]
        comparator = node.comparators[0] if node.comparators else None

        if not comparator or not isinstance(op, (ast.Eq, ast.NotEq)):
            return

        # Check if either side is a singleton constant
        if self._is_singleton_const(node.left):
            singleton = node.left
            other = comparator
        elif self._is_singleton_const(comparator):
            singleton = comparator
            other = node.left
        else:
            return

        # Get the singleton value
        if not isinstance(singleton, ast.Constant):
            return

        singleton_val = singleton.value
        checking_for_absence = isinstance(op, ast.NotEq)

        # Handle None comparisons
        if singleton_val is None:
            self._report_none_comparison(node, checking_for_absence)
        # Handle True/False comparisons (using isinstance for type checking)
        elif isinstance(singleton_val, bool):
            # Type narrowing: at this point singleton_val is bool
            self._report_bool_comparison(node, op, singleton_val, other)

    def _check_unidiomatic_typecheck(self, node: ast.Compare) -> None:
        """Check for type(x) == Y instead of isinstance(x, Y)."""
        if len(node.ops) != 1:
            return

        op = node.ops[0]
        if not isinstance(op, (ast.Eq, ast.Is)):
            return

        # Check for type(x) == Y or type(x) is Y
        if not isinstance(node.left, ast.Call):
            return

        # Early return if not a type() call with one argument
        if not isinstance(node.left.func, ast.Name):
            return
        if node.left.func.id != "type":
            return
        if len(node.left.args) != 1:
            return

        # At this point, node.left is a Call with args
        obj = ast.unparse(node.left.args[0]) if hasattr(ast, "unparse") else "obj"
        type_name = (
            ast.unparse(node.comparators[0])
            if hasattr(ast, "unparse") and node.comparators
            else "Type"
        )

        self.add_issue(
            self._create_issue(
                node,
                severity=Severity.MEDIUM,
                rule_id="R015",
                message="Use isinstance() for type checking instead of type() comparison",
                suggestion=f"Use 'isinstance({obj}, {type_name})' instead of 'type({obj}) == {type_name}'",
            )
        )

    def visit_Call(self, node: ast.Call) -> None:
        """Check for consecutive isinstance calls."""
        if self.is_suppressed(node):
            self.generic_visit(node)
            return

        # This would need to check the parent context for multiple isinstance calls
        # For now, we'll check in visit_BoolOp for the pattern

        self.generic_visit(node)

    def _get_op_str(self, op: ast.cmpop) -> Optional[str]:
        """Convert comparison operator to string."""
        op_map = {
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.Eq: "==",
            ast.NotEq: "!=",
        }
        return op_map.get(type(op))
