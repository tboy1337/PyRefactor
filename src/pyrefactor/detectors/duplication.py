"""Code duplication detector for PyRefactor."""

import ast
import hashlib
import tokenize
from io import StringIO
from typing import Optional, cast

from ..ast_visitor import BaseDetector
from ..config import Config
from ..models import Issue, Severity


class _ExclusionVisitor(ast.NodeVisitor):
    """AST visitor to identify line ranges to exclude from duplication detection."""

    def __init__(self) -> None:
        """Initialize exclusion visitor."""
        self.ranges: list[tuple[int, int]] = []

    def _add_node_range(self, node: ast.AST) -> None:
        """Add node's line range to exclusions if available."""
        if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
            return
        lineno = cast(int, getattr(node, "lineno"))
        end_lineno = cast(Optional[int], getattr(node, "end_lineno"))
        if end_lineno is None:
            return
        self.ranges.append((lineno, end_lineno))

    def visit_Set(self, node: ast.Set) -> None:
        """Visit set literal and add its range to exclusions."""
        self._add_node_range(node)
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        """Visit list literal and add its range to exclusions."""
        self._add_node_range(node)
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        """Visit dict literal and add its range to exclusions."""
        self._add_node_range(node)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        """Visit tuple literal and add its range to exclusions."""
        self._add_node_range(node)
        self.generic_visit(node)

    def _add_docstring_range(self, node: ast.AST) -> None:
        """Check if node has a docstring and add to exclusions."""
        if not hasattr(node, "body"):
            return
        body = cast(list[ast.stmt], getattr(node, "body"))
        if not body:
            return

        # Only these node types are supported by ast.get_docstring
        if isinstance(
            node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module)
        ):
            docstring_text = ast.get_docstring(node, clean=False)
            if not docstring_text:
                return

        first_stmt = body[0]
        if not isinstance(first_stmt, ast.Expr):
            return
        if not isinstance(first_stmt.value, ast.Constant):
            return
        if not isinstance(first_stmt.value.value, str):
            return

        self._add_node_range(first_stmt)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function and exclude its docstring."""
        self._add_docstring_range(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function and exclude its docstring."""
        self._add_docstring_range(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class and exclude its docstring."""
        self._add_docstring_range(node)
        self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> None:
        """Visit module and exclude its docstring."""
        self._add_docstring_range(node)
        self.generic_visit(node)


class DuplicationDetector(BaseDetector):
    """Detects code duplication."""

    # Maximum block size to analyze (prevents excessive memory usage)
    MAX_BLOCK_SIZE = 20

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize duplication detector."""
        super().__init__(config, file_path, source_lines)
        self.code_blocks: dict[str, list[tuple[int, int, str, str]]] = {}
        self.checked = False
        self.excluded_ranges: list[tuple[int, int]] = []

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "duplication"

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run duplication detection on the entire file."""
        # First, identify exclusion zones (data structures and docstrings)
        self._identify_excluded_ranges(tree)

        # Then, extract all code blocks
        self._extract_code_blocks()

        # Finally, find duplicates
        self._find_duplicates()

        return self.issues

    def _identify_excluded_ranges(self, tree: ast.AST) -> None:
        """Identify line ranges that should be excluded from duplication detection.

        This includes:
        - Data structure literals (Set, List, Dict, Tuple)
        - Docstrings (first string in functions/classes/modules)

        Args:
            tree: The AST of the source file
        """
        visitor = _ExclusionVisitor()
        visitor.visit(tree)
        self.excluded_ranges = visitor.ranges

    def _is_in_excluded_range(self, start_line: int, end_line: int) -> bool:
        """Check if a line range overlaps with any excluded range.

        Args:
            start_line: Start line of the range (1-indexed)
            end_line: End line of the range (1-indexed)

        Returns:
            True if the range overlaps with any excluded range
        """
        for excluded_start, excluded_end in self.excluded_ranges:
            # Check if there's any overlap
            if end_line >= excluded_start and start_line <= excluded_end:
                return True
        return False

    def _extract_code_blocks(self) -> None:
        """Extract code blocks for comparison."""
        min_lines = self.config.duplication.min_duplicate_lines
        total_lines = len(self.source_lines)

        # Extract sliding windows of code with optimized range
        for start in range(total_lines):
            max_length = min(self.MAX_BLOCK_SIZE, total_lines - start)
            for length in range(min_lines, max_length + 1):
                end = start + length
                if end > total_lines:
                    break

                # Skip blocks that are in excluded ranges (data structures, docstrings)
                if self._is_in_excluded_range(start + 1, end):
                    continue

                # Get the code block
                code_block = "\n".join(self.source_lines[start:end])

                # Skip if block is mostly whitespace or comments
                if not self._is_meaningful_block(code_block):
                    continue

                # Normalize the code for comparison
                normalized = self._normalize_code(code_block)
                if not normalized:
                    continue

                # Hash the normalized code
                code_hash = hashlib.md5(normalized.encode()).hexdigest()

                if code_hash not in self.code_blocks:
                    self.code_blocks[code_hash] = []

                # Store normalized code along with block to avoid re-normalization
                self.code_blocks[code_hash].append(
                    (start + 1, end, code_block, normalized)
                )  # +1 for 1-indexed lines

    def _find_duplicates(self) -> None:
        """Find and report duplicate code blocks."""
        reported_ranges: list[tuple[int, int]] = []

        for _, occurrences in self.code_blocks.items():
            if len(occurrences) <= 1:
                continue

            # Sort by line number
            sorted_occurrences = sorted(
                occurrences, key=lambda item: item[0]  # type: ignore[misc]
            )

            # Report each duplicate (except the first occurrence)
            first_start, first_end, _, first_normalized = sorted_occurrences[0]

            for start, end, _, normalized in sorted_occurrences[1:]:
                # Check for suppression comments
                if self._is_block_suppressed(start):
                    continue

                # Skip if this range overlaps with first occurrence or already reported ranges
                if self._overlaps_with_reported(start, end, reported_ranges):
                    continue
                if self._overlaps_with_reported(start, end, [(first_start, first_end)]):
                    continue

                # Check similarity using already-normalized code
                similarity = self._calculate_similarity_from_normalized(
                    first_normalized, normalized
                )
                threshold = self.config.duplication.similarity_threshold

                if similarity >= threshold:
                    self.add_issue(
                        Issue(
                            file=self.file_path,
                            line=start,
                            column=0,
                            severity=Severity.MEDIUM,
                            rule_id="D001",
                            message=f"Duplicate code block (lines {start}-{end}) similar to lines {first_start}-{first_end}",
                            suggestion="Extract duplicated code to a reusable function or method",
                            end_line=end,
                        )
                    )
                    reported_ranges.append((start, end))

    def _is_block_suppressed(self, line: int) -> bool:
        """Check if a code block has a suppression comment.

        Args:
            line: The line number to check

        Returns:
            True if the line has a suppression comment
        """
        if line < 1 or line > len(self.source_lines):
            return False

        # Check a range of lines before the block (up to 3 lines back)
        for offset in range(4):
            check_line = line - offset
            if check_line < 1:
                break
            current_line = self.source_lines[check_line - 1]
            if "# pyrefactor: ignore" in current_line or "# noqa" in current_line:
                return True

        return False

    def _overlaps_with_reported(  # pyrefactor: ignore
        self, start: int, end: int, reported: list[tuple[int, int]]
    ) -> bool:
        """Check if a range overlaps with any already reported range.

        Args:
            start: Start line of the range
            end: End line of the range
            reported: List of already reported ranges

        Returns:
            True if the range overlaps with any reported range
        """
        for reported_start, reported_end in reported:
            # Check for any overlap (using De Morgan's law simplification)
            if end >= reported_start and start <= reported_end:
                return True
        return False

    def _is_meaningful_block(self, code: str) -> bool:
        """Check if a code block is meaningful (not just whitespace/comments)."""
        lines = code.strip().split("\n")
        meaningful_lines = sum(
            1
            for line in lines
            if (stripped := line.strip()) and not stripped.startswith("#")
        )

        return meaningful_lines >= self.config.duplication.min_duplicate_lines

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison by tokenizing and removing literals."""
        try:
            tokens = tokenize.generate_tokens(StringIO(code).readline)
            normalized_tokens = [self._normalize_token(token) for token in tokens]
            # Filter out None values
            return " ".join(token for token in normalized_tokens if token)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # Return empty string for code blocks that can't be tokenized
            # (e.g., incomplete blocks with inconsistent indentation)
            return ""

    def _normalize_token(
        self, token: tokenize.TokenInfo
    ) -> Optional[str]:  # pyrefactor: ignore
        """Normalize a single token for comparison.

        Args:
            token: Token to normalize

        Returns:
            Normalized token string or None if token should be skipped
        """
        if token.type == tokenize.NAME:
            return token.string
        if token.type == tokenize.OP:
            return token.string
        if token.type in (tokenize.NUMBER, tokenize.STRING):
            return "LITERAL"
        if token.type == tokenize.NEWLINE:
            return "\n"
        return None

    def _calculate_similarity_from_normalized(  # pyrefactor: ignore
        self, normalized1: str, normalized2: str
    ) -> float:
        """Calculate similarity between two already-normalized code blocks.

        Args:
            normalized1: First normalized code block
            normalized2: Second normalized code block

        Returns:
            Similarity score between 0.0 and 1.0
        """
        tokens1 = set(normalized1.split())
        tokens2 = set(normalized2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def visit(self, node: ast.AST) -> None:
        """Override visit to prevent default traversal."""
        # Duplication detection works at file level, not node level
        ...
