"""Code duplication detector for PyRefactor."""

import ast
import hashlib
import tokenize
from io import StringIO

from ..ast_visitor import BaseDetector
from ..config import Config
from ..models import Issue, Severity


class DuplicationDetector(BaseDetector):
    """Detects code duplication."""

    def __init__(self, config: Config, file_path: str, source_lines: list[str]) -> None:
        """Initialize duplication detector."""
        super().__init__(config, file_path, source_lines)  # type: ignore[misc]
        self.code_blocks: dict[str, list[tuple[int, int, str]]] = {}
        self.checked = False

    def get_detector_name(self) -> str:
        """Return the name of this detector."""
        return "duplication"

    def analyze(self, tree: ast.AST) -> list[Issue]:
        """Run duplication detection on the entire file."""
        # First, extract all code blocks
        self._extract_code_blocks()

        # Then find duplicates
        self._find_duplicates()

        return self.issues

    def _extract_code_blocks(self) -> None:
        """Extract code blocks for comparison."""
        min_lines = self.config.duplication.min_duplicate_lines
        total_lines = len(self.source_lines)

        # Extract sliding windows of code
        for start in range(total_lines):
            for length in range(min_lines, min(20, total_lines - start + 1)):
                end = start + length
                if end > total_lines:
                    break

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

                self.code_blocks[code_hash].append(
                    (start + 1, end, code_block)
                )  # +1 for 1-indexed lines

    def _find_duplicates(self) -> None:
        """Find and report duplicate code blocks."""
        for _, occurrences in self.code_blocks.items():
            if len(occurrences) > 1:
                # Sort by line number
                occurrences.sort(key=lambda x: x[0])

                # Report each duplicate (except the first occurrence)
                first_start, first_end, first_code = occurrences[0]

                for start, end, code in occurrences[1:]:
                    # Check similarity
                    similarity = self._calculate_similarity(first_code, code)
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

    def _is_meaningful_block(self, code: str) -> bool:
        """Check if a code block is meaningful (not just whitespace/comments)."""
        lines = code.strip().split("\n")
        meaningful_lines = 0

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                meaningful_lines += 1

        return meaningful_lines >= self.config.duplication.min_duplicate_lines

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison by tokenizing and removing literals."""
        try:
            tokens = tokenize.generate_tokens(StringIO(code).readline)
            normalized_tokens: list[str] = []

            for token in tokens:
                if token.type == tokenize.NAME:
                    normalized_tokens.append(token.string)
                elif token.type == tokenize.OP:
                    normalized_tokens.append(token.string)
                elif token.type in (tokenize.NUMBER, tokenize.STRING):
                    # Replace literals with placeholders
                    normalized_tokens.append("LITERAL")
                elif token.type == tokenize.NEWLINE:
                    normalized_tokens.append("\n")

            return " ".join(normalized_tokens)
        except tokenize.TokenError:
            return ""

    def _calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code blocks."""
        # Simple token-based similarity
        tokens1 = set(self._normalize_code(code1).split())
        tokens2 = set(self._normalize_code(code2).split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def visit(self, node: ast.AST) -> None:
        """Override visit to prevent default traversal."""
        # Duplication detection works at file level, not node level
        ...
