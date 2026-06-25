"""Complexity detector for PyRefactor."""

import ast
from dataclasses import dataclass
from typing import Optional, Union, cast

from ..ast_visitor import BaseDetector, node_col_offset, node_lineno
from ..models import Issue, Severity


@dataclass
class IssueParams:
    """Parameters for creating a complexity issue."""

    severity: Severity
    rule_id: str
    message: str
    suggestion: str
    end_line: Optional[int] = None


@dataclass
class FunctionMetrics:
    """Metrics collected from a single AST traversal of a function."""

    local_vars: set[str]
    branches: int
    max_nesting: int
    cyclomatic_complexity: int


class _FunctionMetricsVisitor(ast.NodeVisitor):
    """Collect complexity metrics for a function in one AST pass."""

    def __init__(self, root: ast.AST) -> None:
        self.root = root
        self.local_vars: set[str] = set()
        self.branches = 0
        self.current_depth = 0
        self.max_depth = 0
        self.complexity = 1

    def _visit_if_root_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Traverse the root function only; skip nested functions."""
        self._visit_if_root_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Traverse the root async function only; skip nested functions."""
        self._visit_if_root_function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Do not count metrics inside nested classes."""

    def visit_Name(self, name_node: ast.Name) -> None:
        """Track variable assignments."""
        if isinstance(name_node.ctx, ast.Store):
            self.local_vars.add(name_node.id)
        self.generic_visit(name_node)

    def visit_If(self, node: ast.If) -> None:
        """Count if branches, nesting, and cyclomatic complexity."""
        self.branches += 1
        if node.orelse:
            if not (len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)):
                self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_For(self, node: ast.For) -> None:
        """Count for loops."""
        self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Count async for loops."""
        self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_While(self, node: ast.While) -> None:
        """Count while loops."""
        self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_With(self, node: ast.With) -> None:
        """Count with statements."""
        self._increment_complexity_and_visit_nested(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Count try blocks."""
        self._increment_complexity_and_visit_nested(node)

    def visit_TryStar(self, node: ast.TryStar) -> None:
        """Count try* blocks and handlers."""
        self.branches += len(node.handlers)
        self.complexity += len(node.handlers)
        self._increment_complexity_and_visit_nested(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Count match/case branches."""
        self.branches += len(node.cases)
        self.complexity += len(node.cases)
        self._increment_complexity_and_visit_nested(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Count exception handlers."""
        self.branches += 1
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """Count assertions."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Count boolean operations."""
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def _increment_complexity_and_visit_nested(self, node: ast.AST) -> None:
        """Increment cyclomatic complexity and nesting, then visit children."""
        self.complexity += 1
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1

    def collect(self) -> FunctionMetrics:
        """Return collected metrics after visiting the root function."""
        return FunctionMetrics(
            local_vars=self.local_vars,
            branches=self.branches,
            max_nesting=self.max_depth,
            cyclomatic_complexity=self.complexity,
        )


class ComplexityDetector(BaseDetector):
    """Detects complexity issues in code."""

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "complexity"

    def _create_issue(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        params: IssueParams,
    ) -> Issue:
        """Create an Issue object for function-related complexity issues."""
        line = node_lineno(node)
        if line is None:
            raise ValueError("Function node has no valid line number")
        snippet = self.get_source_line(line).strip()
        return Issue(
            file=self.file_path,
            line=line,
            column=node_col_offset(node),
            severity=params.severity,
            rule_id=params.rule_id,
            message=params.message,
            suggestion=params.suggestion,
            end_line=params.end_line,
            code_snippet=snippet or None,
        )

    def _add_issue_if_not_suppressed(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        params: IssueParams,
    ) -> None:
        """Add a complexity issue unless the rule is suppressed."""
        if self.is_suppressed(node, params.rule_id):
            return
        self.add_issue(self._create_issue(node, params))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function complexity."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function complexity."""
        self._check_function(node)
        self.generic_visit(node)

    def _collect_metrics(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> FunctionMetrics:
        """Collect all complexity metrics in a single AST traversal."""
        visitor = _FunctionMetricsVisitor(node)
        visitor.visit(node)
        return visitor.collect()

    def _check_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check various complexity metrics for a function."""
        self._check_function_length(node)
        self._check_arguments(node)

        metrics = self._collect_metrics(node)
        self._check_local_variables(node, metrics.local_vars)
        self._check_branches(node, metrics.branches)
        self._check_nesting_depth(node, metrics.max_nesting)
        self._check_cyclomatic_complexity(node, metrics.cyclomatic_complexity)

    def _check_function_length(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check if function is too long."""
        if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
            return

        end_lineno = cast(Optional[int], getattr(node, "end_lineno", None))
        if end_lineno is None:
            return

        function_lines = end_lineno - node.lineno + 1
        max_lines = self.config.complexity.max_function_lines

        if function_lines > max_lines:
            self._add_issue_if_not_suppressed(
                node,
                IssueParams(
                    severity=Severity.MEDIUM,
                    rule_id="C001",
                    message=f"Function '{node.name}' is too long ({function_lines} lines, max {max_lines})",
                    suggestion="Consider breaking this function into smaller, more focused functions",
                    end_line=end_lineno,
                ),
            )

    def _check_arguments(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check if function has too many arguments."""
        args = node.args
        total_args = (
            len(args.args)
            + len(args.posonlyargs)
            + len(args.kwonlyargs)
            + (1 if args.vararg else 0)
            + (1 if args.kwarg else 0)
        )

        if args.args and args.args[0].arg in ("self", "cls"):
            total_args -= 1

        max_args = self.config.complexity.max_arguments

        if total_args > max_args:
            self._add_issue_if_not_suppressed(
                node,
                IssueParams(
                    severity=Severity.MEDIUM,
                    rule_id="C002",
                    message=f"Function '{node.name}' has too many arguments ({total_args}, max {max_args})",
                    suggestion="Consider using a configuration object or dataclass to group related parameters",
                ),
            )

    def _check_local_variables(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        local_vars: set[str],
    ) -> None:
        """Check if function has too many local variables."""
        max_vars = self.config.complexity.max_local_variables

        if len(local_vars) > max_vars:
            self._add_issue_if_not_suppressed(
                node,
                IssueParams(
                    severity=Severity.LOW,
                    rule_id="C003",
                    message=f"Function '{node.name}' has too many local variables ({len(local_vars)}, max {max_vars})",
                    suggestion="Consider extracting functionality into helper functions or classes",
                ),
            )

    def _check_branches(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        branches: int,
    ) -> None:
        """Check if function has too many branches."""
        max_branches = self.config.complexity.max_branches

        if branches > max_branches:
            self._add_issue_if_not_suppressed(
                node,
                IssueParams(
                    severity=Severity.HIGH,
                    rule_id="C004",
                    message=f"Function '{node.name}' has too many branches ({branches}, max {max_branches})",
                    suggestion="Refactor using helper functions, guard clauses, or dictionary dispatch patterns",
                ),
            )

    def _check_nesting_depth(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        nesting: int,
    ) -> None:
        """Check if function has excessive nesting."""
        max_nesting = self.config.complexity.max_nesting_depth

        if nesting > max_nesting:
            self._add_issue_if_not_suppressed(
                node,
                IssueParams(
                    severity=Severity.HIGH,
                    rule_id="C005",
                    message=f"Function '{node.name}' has excessive nesting depth ({nesting}, max {max_nesting})",
                    suggestion="Use early returns, guard clauses, or extract nested logic to separate functions",
                ),
            )

    def _check_cyclomatic_complexity(
        self,
        node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
        complexity: int,
    ) -> None:
        """Check cyclomatic complexity."""
        max_complexity = self.config.complexity.max_cyclomatic_complexity

        if complexity > max_complexity:
            self._add_issue_if_not_suppressed(
                node,
                IssueParams(
                    severity=Severity.MEDIUM,
                    rule_id="C006",
                    message=f"Function '{node.name}' has high cyclomatic complexity ({complexity}, max {max_complexity})",
                    suggestion="Simplify the function by reducing decision points or extracting logic",
                ),
            )
