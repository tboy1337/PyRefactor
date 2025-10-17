"""Tests for data models."""

import pytest

from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_ordering(self) -> None:
        """Test severity level ordering."""
        assert Severity.INFO < Severity.LOW
        assert Severity.LOW < Severity.MEDIUM
        assert Severity.MEDIUM < Severity.HIGH

    def test_severity_values(self) -> None:
        """Test severity values."""
        assert Severity.INFO.value == "info"
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"


class TestIssue:
    """Tests for Issue model."""

    def test_issue_creation(self) -> None:
        """Test creating an issue."""
        issue = Issue(
            file="test.py",
            line=10,
            column=5,
            severity=Severity.MEDIUM,
            rule_id="C001",
            message="Test issue",
        )

        assert issue.file == "test.py"
        assert issue.line == 10
        assert issue.column == 5
        assert issue.severity == Severity.MEDIUM
        assert issue.rule_id == "C001"
        assert issue.message == "Test issue"

    def test_issue_with_suggestion(self) -> None:
        """Test issue with suggestion."""
        issue = Issue(
            file="test.py",
            line=1,
            column=0,
            severity=Severity.LOW,
            rule_id="C002",
            message="Test",
            suggestion="Do this instead",
        )

        assert issue.suggestion == "Do this instead"

    def test_issue_invalid_line(self) -> None:
        """Test that invalid line numbers raise errors."""
        with pytest.raises(ValueError, match="Line number must be positive"):
            Issue(
                file="test.py",
                line=0,
                column=0,
                severity=Severity.INFO,
                rule_id="T001",
                message="Test",
            )

    def test_issue_invalid_column(self) -> None:
        """Test that invalid column numbers raise errors."""
        with pytest.raises(ValueError, match="Column number must be non-negative"):
            Issue(
                file="test.py",
                line=1,
                column=-1,
                severity=Severity.INFO,
                rule_id="T001",
                message="Test",
            )


class TestFileAnalysis:
    """Tests for FileAnalysis model."""

    def test_file_analysis_creation(self) -> None:
        """Test creating a file analysis."""
        analysis = FileAnalysis(file_path="test.py")

        assert analysis.file_path == "test.py"
        assert not analysis.issues
        assert analysis.parse_error is None
        assert analysis.lines_of_code == 0

    def test_add_issue(self) -> None:
        """Test adding issues to analysis."""
        analysis = FileAnalysis(file_path="test.py")
        issue = Issue(
            file="test.py",
            line=1,
            column=0,
            severity=Severity.INFO,
            rule_id="T001",
            message="Test",
        )

        analysis.add_issue(issue)

        assert len(analysis.issues) == 1
        assert analysis.issues[0] == issue

    def test_get_issues_by_severity(self) -> None:
        """Test filtering issues by severity."""
        analysis = FileAnalysis(file_path="test.py")

        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="T001",
                message="High",
            )
        )
        analysis.add_issue(
            Issue(
                file="test.py",
                line=2,
                column=0,
                severity=Severity.LOW,
                rule_id="T002",
                message="Low",
            )
        )

        high_issues = analysis.get_issues_by_severity(Severity.HIGH)
        assert len(high_issues) == 1
        assert high_issues[0].severity == Severity.HIGH

    def test_has_errors(self) -> None:
        """Test checking for critical issues."""
        analysis = FileAnalysis(file_path="test.py")

        assert not analysis.has_errors()

        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.INFO,
                rule_id="T001",
                message="Info",
            )
        )

        assert not analysis.has_errors()

        analysis.add_issue(
            Issue(
                file="test.py",
                line=2,
                column=0,
                severity=Severity.HIGH,
                rule_id="T002",
                message="High",
            )
        )

        assert analysis.has_errors()


class TestAnalysisResult:
    """Tests for AnalysisResult model."""

    def test_analysis_result_creation(self) -> None:
        """Test creating analysis result."""
        result = AnalysisResult()

        assert not result.file_analyses

    def test_add_file_analysis(self) -> None:
        """Test adding file analyses."""
        result = AnalysisResult()
        analysis = FileAnalysis(file_path="test.py")

        result.add_file_analysis(analysis)

        assert len(result.file_analyses) == 1
        assert result.file_analyses[0] == analysis

    def test_get_all_issues(self) -> None:
        """Test getting all issues across files."""
        result = AnalysisResult()

        analysis1 = FileAnalysis(file_path="test1.py")
        analysis1.add_issue(
            Issue(
                file="test1.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="T001",
                message="Issue 1",
            )
        )

        analysis2 = FileAnalysis(file_path="test2.py")
        analysis2.add_issue(
            Issue(
                file="test2.py",
                line=1,
                column=0,
                severity=Severity.LOW,
                rule_id="T002",
                message="Issue 2",
            )
        )

        result.add_file_analysis(analysis1)
        result.add_file_analysis(analysis2)

        all_issues = result.get_all_issues()
        assert len(all_issues) == 2

    def test_total_issues(self) -> None:
        """Test counting total issues."""
        result = AnalysisResult()

        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="T001",
                message="Issue 1",
            )
        )
        analysis.add_issue(
            Issue(
                file="test.py",
                line=2,
                column=0,
                severity=Severity.LOW,
                rule_id="T002",
                message="Issue 2",
            )
        )

        result.add_file_analysis(analysis)

        assert result.total_issues() == 2

    def test_files_analyzed(self) -> None:
        """Test counting files analyzed."""
        result = AnalysisResult()

        result.add_file_analysis(FileAnalysis(file_path="test1.py"))
        result.add_file_analysis(FileAnalysis(file_path="test2.py"))

        assert result.files_analyzed() == 2

    def test_files_with_issues(self) -> None:
        """Test counting files with issues."""
        result = AnalysisResult()

        analysis1 = FileAnalysis(file_path="test1.py")
        analysis1.add_issue(
            Issue(
                file="test1.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="T001",
                message="Issue",
            )
        )

        analysis2 = FileAnalysis(file_path="test2.py")

        result.add_file_analysis(analysis1)
        result.add_file_analysis(analysis2)

        assert result.files_with_issues() == 1
