"""Complexity detector for PyRefactor."""

import ast
from dataclasses import dataclass
from typing import Optional, Union

from ..ast_visitor import (
    BaseDetector,
    calculate_cyclomatic_complexity,
    count_branches,
    count_nesting_depth,
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


class LocalVarVisitor(ast.NodeVisitor):
    """Visitor to count local variables in a function."""

    def __init__(self) -> None:
        self.vars: set[str] = set()

    def visit_Name(self, name_node: ast.Name) -> None:
        """Track variable assignments."""
        if isinstance(name_node.ctx, ast.Store):
            self.vars.add(name_node.id)

    def visit_FunctionDef(self, func_node: ast.FunctionDef) -> None:
        """Don't descend into nested functions."""
        ...

    def visit_AsyncFunctionDef(self, func_node: ast.AsyncFunctionDef) -> None:
        """Don't descend into nested async functions."""
        ...


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
        return Issue(
            file=self.file_path,
            line=node.lineno,
            column=node.col_offset,
            severity=params.severity,
            rule_id=params.rule_id,
            message=params.message,
            suggestion=params.suggestion,
            end_line=params.end_line,
        )

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
        """Check various complexity metrics for a function.

        Runs all complexity checks efficiently by minimizing redundant AST traversals.
        """
        if self.is_suppressed(node):
            return

        # Save current function context
        old_function = self.current_function
        self.current_function = node

        # Group checks that don't require AST traversal
        self._check_function_length(node)
        self._check_arguments(node)

        # Checks requiring AST traversal - could be combined in future optimization
        self._check_local_variables(node)
        self._check_branches(node)
        self._check_nesting_depth(node)
        self._check_cyclomatic_complexity(node)

        # Restore function context
        self.current_function = old_function

    def _check_function_length(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check if function is too long."""
        if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
            return

        if node.end_lineno is None:
            return

        function_lines = node.end_lineno - node.lineno + 1
        max_lines = self.config.complexity.max_function_lines

        if function_lines > max_lines:
            self.add_issue(
                self._create_issue(
                    node,
                    IssueParams(
                        severity=Severity.MEDIUM,
                        rule_id="C001",
                        message=f"Function '{node.name}' is too long ({function_lines} lines, max {max_lines})",
                        suggestion="Consider breaking this function into smaller, more focused functions",
                        end_line=node.end_lineno,
                    ),
                )
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

        # Exclude 'self' and 'cls' for methods
        if args.args and args.args[0].arg in ("self", "cls"):
            total_args -= 1

        max_args = self.config.complexity.max_arguments

        if total_args > max_args:
            self.add_issue(
                self._create_issue(
                    node,
                    IssueParams(
                        severity=Severity.MEDIUM,
                        rule_id="C002",
                        message=f"Function '{node.name}' has too many arguments ({total_args}, max {max_args})",
                        suggestion="Consider using a configuration object or dataclass to group related parameters",
                    ),
                )
            )

    def _check_local_variables(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check if function has too many local variables."""
        visitor = LocalVarVisitor()
        visitor.visit(node)
        local_vars = visitor.vars

        max_vars = self.config.complexity.max_local_variables

        if len(local_vars) > max_vars:
            self.add_issue(
                self._create_issue(
                    node,
                    IssueParams(
                        severity=Severity.LOW,
                        rule_id="C003",
                        message=f"Function '{node.name}' has too many local variables ({len(local_vars)}, max {max_vars})",
                        suggestion="Consider extracting functionality into helper functions or classes",
                    ),
                )
            )

    def _check_branches(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check if function has too many branches."""
        branches = count_branches(node)
        max_branches = self.config.complexity.max_branches

        if branches > max_branches:
            self.add_issue(
                self._create_issue(
                    node,
                    IssueParams(
                        severity=Severity.HIGH,
                        rule_id="C004",
                        message=f"Function '{node.name}' has too many branches ({branches}, max {max_branches})",
                        suggestion="Refactor using helper functions, guard clauses, or dictionary dispatch patterns",
                    ),
                )
            )

    def _check_nesting_depth(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check if function has excessive nesting."""
        nesting = count_nesting_depth(node)
        max_nesting = self.config.complexity.max_nesting_depth

        if nesting > max_nesting:
            self.add_issue(
                self._create_issue(
                    node,
                    IssueParams(
                        severity=Severity.HIGH,
                        rule_id="C005",
                        message=f"Function '{node.name}' has excessive nesting depth ({nesting}, max {max_nesting})",
                        suggestion="Use early returns, guard clauses, or extract nested logic to separate functions",
                    ),
                )
            )

    def _check_cyclomatic_complexity(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Check cyclomatic complexity."""
        complexity = calculate_cyclomatic_complexity(node)
        max_complexity = self.config.complexity.max_cyclomatic_complexity

        if complexity > max_complexity:
            self.add_issue(
                self._create_issue(
                    node,
                    IssueParams(
                        severity=Severity.MEDIUM,
                        rule_id="C006",
                        message=f"Function '{node.name}' has high cyclomatic complexity ({complexity}, max {max_complexity})",
                        suggestion="Simplify the function by reducing decision points or extracting logic",
                    ),
                )
            )
