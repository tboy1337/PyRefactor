"""Complexity detector for PyRefactor."""

import ast
from dataclasses import dataclass
from typing import Optional, Union, cast

from ..ast_visitor import (
    BaseDetector,
    collect_function_metrics,
    node_col_offset,
    node_lineno,
)
from ..models import Issue, Severity


@dataclass
class IssueParams:
    """Parameters for creating a complexity issue."""

    severity: Severity
    rule_id: str
    message: str
    suggestion: str
    end_line: Optional[int] = None


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

    def _check_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check various complexity metrics for a function."""
        self._check_function_length(node)
        self._check_arguments(node)

        metrics = collect_function_metrics(node)
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
