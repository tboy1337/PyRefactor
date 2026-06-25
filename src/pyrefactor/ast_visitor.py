"""Base AST visitor framework for PyRefactor detectors."""

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union

from .config import Config
from .models import Issue, Severity

_NOQA_RULES_PATTERN = re.compile(
    r"#\s*noqa(?::\s*(?P<rules>[^\s#]+))?",
    re.IGNORECASE,
)

# Number of source lines above an issue line to check for suppression comments.
SUPPRESSION_LOOKBACK = 1


def node_lineno(node: ast.AST) -> int | None:
    """Return a valid 1-based line number for an AST node, or None."""
    lineno = getattr(node, "lineno", None)
    return lineno if isinstance(lineno, int) and lineno >= 1 else None


def node_col_offset(node: ast.AST) -> int:
    """Return the column offset for an AST node."""
    col = getattr(node, "col_offset", 0)
    return col if isinstance(col, int) else 0


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Build a map of child AST nodes to their parent nodes."""
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    return parent_map


def collect_store_names(target: ast.AST) -> set[str]:
    """Collect variable names assigned via an assignment target."""
    names: set[str] = set()
    if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            names.update(collect_store_names(element))
    elif isinstance(target, ast.Starred):
        names.update(collect_store_names(target.value))
    return names


@dataclass
class FunctionMetrics:
    """Metrics collected from a single AST traversal of a function."""

    local_vars: set[str]
    branches: int
    max_nesting: int
    cyclomatic_complexity: int


class FunctionMetricsVisitor(ast.NodeVisitor):
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

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track tuple and multi-target assignments."""
        for target in node.targets:
            self.local_vars.update(collect_store_names(target))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Track annotated assignments."""
        if node.target is not None:
            self.local_vars.update(collect_store_names(node.target))
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Count for loops and track loop target variables."""
        self.local_vars.update(collect_store_names(node.target))
        self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Count async for loops and track loop target variables."""
        self.local_vars.update(collect_store_names(node.target))
        self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_If(self, node: ast.If) -> None:
        """Count if branches, nesting, and cyclomatic complexity."""
        self.branches += 1
        if node.orelse:
            if not (len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If)):
                self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_While(self, node: ast.While) -> None:
        """Count while loops."""
        self.branches += 1
        self._increment_complexity_and_visit_nested(node)

    def visit_With(self, node: ast.With) -> None:
        """Count with statements and track context manager targets."""
        for item in node.items:
            if item.optional_vars is not None:
                self.local_vars.update(collect_store_names(item.optional_vars))
        self._increment_complexity_and_visit_nested(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Count async with statements and track context manager targets."""
        for item in node.items:
            if item.optional_vars is not None:
                self.local_vars.update(collect_store_names(item.optional_vars))
        self._increment_complexity_and_visit_nested(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Count try blocks."""
        self._increment_complexity_and_visit_nested(node)

    def visit_TryStar(self, node: ast.TryStar) -> None:
        """Count try* blocks."""
        self._increment_complexity_and_visit_nested(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Count match/case branches."""
        self.branches += len(node.cases)
        self.complexity += len(node.cases)
        self._increment_complexity_and_visit_nested(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Count exception handlers and track exception target variables."""
        if isinstance(node.name, str):
            self.local_vars.add(node.name)
        elif node.name is not None:
            self.local_vars.update(collect_store_names(node.name))
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


def collect_function_metrics(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> FunctionMetrics:
    """Collect complexity metrics for a function in a single AST pass."""
    visitor = FunctionMetricsVisitor(node)
    visitor.visit(node)
    return visitor.collect()


def calculate_cyclomatic_complexity(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
) -> int:
    """Calculate cyclomatic complexity of a function."""
    return collect_function_metrics(node).cyclomatic_complexity


def count_nesting_depth(node: ast.AST) -> int:
    """Calculate maximum nesting depth in a node."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return collect_function_metrics(node).max_nesting
    visitor = FunctionMetricsVisitor(node)
    visitor.visit(node)
    return visitor.max_depth


def count_branches(node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> int:
    """Count the number of branches in a function."""
    return collect_function_metrics(node).branches


class BaseDetector(ast.NodeVisitor, ABC):
    """Base class for all detectors."""

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize detector with configuration and source context."""
        self.config = config
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: list[Issue] = []
        self.analysis_warnings: list[str] = []
        self.current_function: Union[ast.FunctionDef, ast.AsyncFunctionDef, None] = None
        self.shared_parent_map: dict[ast.AST, ast.AST] | None = None

    @abstractmethod
    def get_detector_name(self) -> str:
        """Return the name of this detector."""

    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the detector's list."""
        self.issues.append(issue)

    def report_issue(
        self,
        node: ast.AST,
        *,
        severity: Severity,
        rule_id: str,
        message: str,
        suggestion: str,
    ) -> None:
        """Create and add an issue when the node has a valid line number."""
        if self.is_suppressed(node, rule_id):
            return
        line = node_lineno(node)
        if line is None:
            return
        snippet = self.get_source_line(line).strip()
        self.add_issue(
            Issue(
                file=self.file_path,
                line=line,
                column=node_col_offset(node),
                severity=severity,
                rule_id=rule_id,
                message=message,
                suggestion=suggestion,
                code_snippet=snippet or None,
            )
        )

    def get_source_line(self, line: int) -> str:
        """Get a specific source line (1-indexed)."""
        if 1 <= line <= len(self.source_lines):
            return self.source_lines[line - 1]
        return ""

    def get_source_snippet(self, start_line: int, end_line: int) -> str:
        """Get a snippet of source code."""
        if start_line < 1 or end_line > len(self.source_lines):
            return ""
        return "\n".join(self.source_lines[start_line - 1 : end_line])

    def is_suppressed(self, node: ast.AST, rule_id: str | None = None) -> bool:
        """Check if a node has a suppression comment."""
        lineno = node_lineno(node)
        if lineno is None:
            return False

        for offset in range(SUPPRESSION_LOOKBACK + 1):
            check_line = lineno - offset
            if check_line < 1:
                break
            line = self.get_source_line(check_line)
            if self._line_suppresses(line, rule_id):
                return True

        return False

    @staticmethod
    def _parse_suppression_rules(text: str, *, split_pattern: str) -> set[str]:
        """Parse rule IDs from a suppression comment suffix."""
        return {
            token.strip().upper()
            for token in re.split(split_pattern, text)
            if token.strip()
        }

    @staticmethod
    def _rule_set_suppresses(specified_rules: set[str], rule_id: str | None) -> bool:
        """Return whether the rule set suppresses the given rule."""
        if not specified_rules:
            return True
        return rule_id is not None and rule_id.upper() in specified_rules

    @staticmethod
    def _line_suppresses(line: str, rule_id: str | None) -> bool:
        """Return True when a source line suppresses the given rule."""
        noqa_match = _NOQA_RULES_PATTERN.search(line)
        if noqa_match is not None:
            rules_text = noqa_match.group("rules")
            if rules_text is None:
                return True
            specified_rules = BaseDetector._parse_suppression_rules(
                rules_text, split_pattern=r"[,;\s]+"
            )
            return BaseDetector._rule_set_suppresses(specified_rules, rule_id)

        marker = "# pyrefactor: ignore"
        if marker not in line:
            return False

        suffix = line.split(marker, 1)[1].strip()
        if not suffix:
            return True

        specified_rules = BaseDetector._parse_suppression_rules(
            suffix.replace(",", " "), split_pattern=r"\s+"
        )
        return BaseDetector._rule_set_suppresses(specified_rules, rule_id)

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run the detector on an AST and return issues found."""
        self.issues = []
        self.analysis_warnings = []
        self.visit(tree)
        return self.issues
