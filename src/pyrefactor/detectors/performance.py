"""Performance anti-pattern detector for PyRefactor."""

import ast
from collections import Counter
from collections.abc import Callable
from typing import Optional

from ..ast_visitor import BaseDetector, build_parent_map
from ..config import Config
from ..models import Issue, Severity


class _LoopBodyCallCounter(ast.NodeVisitor):
    """Count identical call expressions in a loop body."""

    def __init__(self, suppressed: set[ast.AST]) -> None:
        self.suppressed = suppressed
        self.call_counts: Counter[str] = Counter()
        self.call_nodes: dict[str, ast.Call] = {}
        self._nested_function_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Skip counting calls inside nested function definitions."""
        self._nested_function_depth += 1
        self.generic_visit(node)
        self._nested_function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Skip counting calls inside nested async function definitions."""
        self._nested_function_depth += 1
        self.generic_visit(node)
        self._nested_function_depth -= 1

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Skip counting calls inside lambda expressions."""
        self._nested_function_depth += 1
        self.generic_visit(node)
        self._nested_function_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        """Record call expressions at the loop body scope."""
        if self._nested_function_depth == 0 and node not in self.suppressed:
            signature = ast.dump(node, annotate_fields=False)
            self.call_counts[signature] += 1
            self.call_nodes.setdefault(signature, node)
        self.generic_visit(node)


class _LoopBodyConcatCounter(ast.NodeVisitor):
    """Count string += operations in a loop body."""

    def __init__(
        self,
        suppressed: set[ast.AST],
        matches_string: Callable[[ast.AST, str], bool],
    ) -> None:
        self.suppressed = suppressed
        self.matches_string = matches_string
        self.count = 0
        self.last_node: Optional[ast.AugAssign] = None
        self._nested_function_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Skip counting concatenations inside nested function definitions."""
        self._nested_function_depth += 1
        self.generic_visit(node)
        self._nested_function_depth -= 1

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Skip counting concatenations inside nested async functions."""
        self._nested_function_depth += 1
        self.generic_visit(node)
        self._nested_function_depth -= 1

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Skip counting concatenations inside lambda expressions."""
        self._nested_function_depth += 1
        self.generic_visit(node)
        self._nested_function_depth -= 1

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Count string += operations at the loop body scope."""
        if (
            self._nested_function_depth == 0
            and node not in self.suppressed
            and isinstance(node.op, ast.Add)
            and self.matches_string(node.target, "string")
        ):
            self.count += 1
            self.last_node = node
        self.generic_visit(node)


class PerformanceDetector(BaseDetector):
    """Detects performance anti-patterns in code."""

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
        self.parent_map: dict[ast.AST, ast.AST] = {}
        self.suppressed_nodes: set[ast.AST] = set()

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "performance"

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run the detector on an AST and return issues found."""
        self.parent_map = build_parent_map(tree)
        self.suppressed_nodes = self._collect_suppressed_nodes(tree)
        self.visit(tree)
        return self.issues

    def _collect_suppressed_nodes(self, tree: ast.AST) -> set[ast.AST]:
        """Collect AST nodes that have suppression comments."""
        suppressed: set[ast.AST] = set()
        for node in ast.walk(tree):
            if self.is_suppressed(node):
                suppressed.add(node)
        return suppressed

    def _visit_loop(self, node: ast.For | ast.While) -> None:
        """Track loop entry, analyze body, then exit."""
        self.loop_stack.append(node)
        self.in_loop = True
        self.generic_visit(node)
        self._check_loop_performance(node)
        self.loop_stack.pop()
        self.in_loop = bool(self.loop_stack)

    def visit_For(self, node: ast.For) -> None:
        """Track when we're inside a for loop."""
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        """Track when we're inside a while loop."""
        self._visit_loop(node)

    def _check_loop_performance(self, loop_node: ast.For | ast.While) -> None:
        """Check loop body for concatenation and duplicate call patterns."""
        self._check_string_concatenations(loop_node)
        self._check_duplicate_calls(loop_node)

    def _check_string_concatenations(self, loop_node: ast.For | ast.While) -> None:
        """Report P001 when string += count meets threshold."""
        counter = _LoopBodyConcatCounter(
            self.suppressed_nodes,
            self._matches_type_hint,
        )
        counter.visit(loop_node)
        min_concat = self.config.performance.min_concatenations
        if counter.count >= min_concat and counter.last_node is not None:
            self.report_issue(
                counter.last_node,
                severity=Severity.MEDIUM,
                rule_id="P001",
                message=(
                    f"String concatenation in loop using += "
                    f"({counter.count} times) is inefficient"
                ),
                suggestion=(
                    "Use str.join() with a list or io.StringIO for better performance"
                ),
            )

    def _check_duplicate_calls(self, loop_node: ast.For | ast.While) -> None:
        """Report P007 when identical calls repeat within a loop body."""
        counter = _LoopBodyCallCounter(self.suppressed_nodes)
        counter.visit(loop_node)
        min_calls = self.config.performance.min_duplicate_calls
        for signature, count in counter.call_counts.items():
            if count >= min_calls:
                call_node = counter.call_nodes[signature]
                self.report_issue(
                    call_node,
                    severity=Severity.MEDIUM,
                    rule_id="P007",
                    message=(
                        f"Repeated identical call in loop ({count} times); "
                        "consider caching the result"
                    ),
                    suggestion=(
                        "Assign the call result to a variable before the loop "
                        "or cache it on first use inside the loop"
                    ),
                )

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Check for inefficient augmented assignments in loops."""
        if not self.in_loop or self.is_suppressed(node):
            self.generic_visit(node)
            return

        if not isinstance(node.op, ast.Add):
            self.generic_visit(node)
            return

        if self._matches_type_hint(node.target, "list"):
            self.report_issue(
                node,
                severity=Severity.LOW,
                rule_id="P002",
                message="List concatenation in loop using += may be inefficient",
                suggestion="Use list.extend() or list comprehension for better performance",
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

        parent: Optional[ast.AST] = self.parent_map.get(node)
        if not isinstance(parent, ast.Compare):
            return

        if not parent.ops or not isinstance(parent.ops[0], ast.In):
            return

        self.report_issue(
            node,
            severity=Severity.INFO,
            rule_id="P003",
            message="Unnecessary dict.keys() call in membership test",
            suggestion="Use 'key in dict' instead of 'key in dict.keys()'",
        )

    def _check_redundant_list_conversion(self, node: ast.Call) -> None:
        """Check for redundant list() conversions of list comprehensions."""
        if not isinstance(node.func, ast.Name):
            return

        if node.func.id != "list":
            return

        if not node.args or not isinstance(node.args[0], ast.ListComp):
            return

        self.report_issue(
            node,
            severity=Severity.INFO,
            rule_id="P004",
            message="Redundant list() conversion of list comprehension",
            suggestion="List comprehensions already return lists; remove list() wrapper",
        )

    def _check_len_usage(self, node: ast.Call) -> None:
        """Check for len() calls and their usage patterns."""
        if not isinstance(node.func, ast.Name):
            return

        if node.func.id != "len":
            return

        self._check_len_comparison(node)

    def _check_len_comparison(self, len_call: ast.Call) -> None:
        """Check for inefficient len() comparison patterns."""
        len_parent: Optional[ast.AST] = self.parent_map.get(len_call)
        if not isinstance(len_parent, ast.Compare):
            return

        if not len_parent.ops or not len_parent.comparators:
            return

        has_zero_comp = any(
            isinstance(comp, ast.Constant) and comp.value == 0
            for comp in len_parent.comparators
        )
        if not has_zero_comp:
            return

        if any(isinstance(op, (ast.Gt, ast.GtE)) for op in len_parent.ops):
            self._add_len_issue(
                len_call,
                "P005",
                "Use truthiness instead of len() > 0",
                "Use 'if container:' instead of 'if len(container) > 0:'",
            )
        elif any(isinstance(op, (ast.Eq, ast.NotEq)) for op in len_parent.ops):
            self._add_len_issue(
                len_call,
                "P006",
                "Use truthiness instead of len() == 0",
                "Use 'if not container:' instead of 'if len(container) == 0:'",
            )

    def _add_len_issue(
        self, len_call: ast.Call, rule_id: str, message: str, suggestion: str
    ) -> None:
        """Add an issue for len() usage patterns."""
        self.report_issue(
            len_call,
            severity=Severity.INFO,
            rule_id=rule_id,
            message=message,
            suggestion=suggestion,
        )

    def _matches_type_hint(self, node: ast.AST, type_name: str) -> bool:
        """Check if a node likely matches a given type based on naming heuristics."""
        if not isinstance(node, ast.Name):
            return False

        name_lower = node.id.lower()
        hints = self.TYPE_HINTS.get(type_name, [])

        return any(hint in name_lower for hint in hints) or (
            type_name == "list" and name_lower.endswith("s")
        )
