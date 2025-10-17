"""Data models for PyRefactor."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels for detected issues."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    def __lt__(self, other: "Severity") -> bool:
        """Compare severity levels."""
        order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]
        return order.index(self) < order.index(other)

    def __le__(self, other: "Severity") -> bool:
        """Compare severity levels (less than or equal)."""
        return self == other or self < other

    def __gt__(self, other: "Severity") -> bool:
        """Compare severity levels (greater than)."""
        order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]
        return order.index(self) > order.index(other)

    def __ge__(self, other: "Severity") -> bool:
        """Compare severity levels (greater than or equal)."""
        return self == other or self > other


@dataclass
class Issue:
    """Represents a detected refactoring or optimization opportunity."""

    file: str
    line: int
    column: int
    severity: Severity
    rule_id: str
    message: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    end_line: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate issue data."""
        if self.line < 1:
            raise ValueError("Line number must be positive")
        if self.column < 0:
            raise ValueError("Column number must be non-negative")


@dataclass
class FileAnalysis:
    """Results of analyzing a single file."""

    file_path: str
    issues: list[Issue] = field(default_factory=list)
    parse_error: Optional[str] = None
    lines_of_code: int = 0

    def add_issue(self, issue: Issue) -> None:
        """Add an issue to the analysis results."""
        self.issues.append(issue)

    def get_issues_by_severity(self, severity: Severity) -> list[Issue]:
        """Get all issues matching a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def has_errors(self) -> bool:
        """Check if there are any high or medium severity issues."""
        return any(
            issue.severity in (Severity.HIGH, Severity.MEDIUM) for issue in self.issues
        )


@dataclass
class AnalysisResult:
    """Overall analysis results for multiple files."""

    file_analyses: list[FileAnalysis] = field(default_factory=list)

    def add_file_analysis(self, analysis: FileAnalysis) -> None:
        """Add a file analysis to the results."""
        self.file_analyses.append(analysis)

    def get_all_issues(self) -> list[Issue]:
        """Get all issues from all files."""
        issues: list[Issue] = []
        for analysis in self.file_analyses:
            issues.extend(analysis.issues)
        return issues

    def get_issues_by_severity(self, severity: Severity) -> list[Issue]:
        """Get all issues matching a specific severity."""
        return [issue for issue in self.get_all_issues() if issue.severity == severity]

    def total_issues(self) -> int:
        """Get total count of issues."""
        return len(self.get_all_issues())

    def files_analyzed(self) -> int:
        """Get count of files analyzed."""
        return len(self.file_analyses)

    def files_with_issues(self) -> int:
        """Get count of files that have issues."""
        return sum(1 for analysis in self.file_analyses if analysis.issues)
