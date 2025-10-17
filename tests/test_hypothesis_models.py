"""Property-based tests for data models using Hypothesis."""

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity


# Custom strategies for our models
@st.composite
def severity_strategy(draw: st.DrawFn) -> Severity:
    """Generate a Severity enum value."""
    return draw(
        st.sampled_from([Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH])
    )


@st.composite
def valid_issue_strategy(draw: st.DrawFn) -> Issue:
    """Generate a valid Issue object."""
    line = draw(st.integers(min_value=1, max_value=1000))
    column = draw(st.integers(min_value=0, max_value=100))
    severity = draw(severity_strategy())
    file_path = draw(
        st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz_/")
    )
    rule_id = draw(
        st.text(
            min_size=1, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
    )
    message = draw(
        st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(min_codepoint=32, max_codepoint=126),
        )
    )
    suggestion = draw(
        st.one_of(
            st.none(),
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            ),
        )
    )
    code_snippet = draw(
        st.one_of(
            st.none(),
            st.text(
                max_size=100,
                alphabet=st.characters(min_codepoint=32, max_codepoint=126),
            ),
        )
    )
    end_line = draw(st.one_of(st.none(), st.integers(min_value=line, max_value=1000)))

    return Issue(
        file=file_path,
        line=line,
        column=column,
        severity=severity,
        rule_id=rule_id,
        message=message,
        suggestion=suggestion,
        code_snippet=code_snippet,
        end_line=end_line,
    )


@st.composite
def file_analysis_strategy(draw: st.DrawFn) -> FileAnalysis:
    """Generate a FileAnalysis object with random issues."""
    file_path = draw(
        st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz_/")
    )
    issues = draw(st.lists(valid_issue_strategy(), max_size=5))
    parse_error = draw(
        st.one_of(
            st.none(),
            st.text(
                max_size=50, alphabet=st.characters(min_codepoint=32, max_codepoint=126)
            ),
        )
    )
    lines_of_code = draw(st.integers(min_value=0, max_value=10000))

    analysis = FileAnalysis(
        file_path=file_path,
        parse_error=parse_error,
        lines_of_code=lines_of_code,
    )
    for issue in issues:
        analysis.add_issue(issue)

    return analysis


class TestSeverityProperties:
    """Property-based tests for Severity enum."""

    @given(severity_strategy())
    def test_severity_equal_to_itself(self, severity: Severity) -> None:
        """Property: A severity is always equal to itself."""
        assert severity == severity
        assert severity <= severity
        assert severity >= severity
        assert not severity < severity
        assert not severity > severity

    @given(severity_strategy(), severity_strategy())
    def test_severity_ordering_transitivity(self, s1: Severity, s2: Severity) -> None:
        """Property: Severity ordering is transitive."""
        # If s1 < s2, then s1 <= s2
        if s1 < s2:
            assert s1 <= s2
            assert s2 > s1
            assert s2 >= s1
            assert s1 != s2

    @given(severity_strategy(), severity_strategy())
    def test_severity_ordering_antisymmetry(self, s1: Severity, s2: Severity) -> None:
        """Property: If s1 <= s2 and s2 <= s1, then s1 == s2."""
        if s1 <= s2 and s2 <= s1:
            assert s1 == s2

    @given(severity_strategy(), severity_strategy(), severity_strategy())
    def test_severity_ordering_complete_transitivity(
        self, s1: Severity, s2: Severity, s3: Severity
    ) -> None:
        """Property: If s1 < s2 and s2 < s3, then s1 < s3."""
        if s1 < s2 and s2 < s3:
            assert s1 < s3

    @given(severity_strategy())
    def test_severity_has_string_value(self, severity: Severity) -> None:
        """Property: All severities have non-empty string values."""
        assert isinstance(severity.value, str)
        assert len(severity.value) > 0


class TestIssueProperties:
    """Property-based tests for Issue model."""

    @given(valid_issue_strategy())
    def test_issue_line_always_positive(self, issue: Issue) -> None:
        """Property: Issue line numbers are always positive."""
        assert issue.line >= 1

    @given(valid_issue_strategy())
    def test_issue_column_non_negative(self, issue: Issue) -> None:
        """Property: Issue column numbers are always non-negative."""
        assert issue.column >= 0

    @given(valid_issue_strategy())
    def test_issue_end_line_after_start(self, issue: Issue) -> None:
        """Property: If end_line is set, it's >= line."""
        if issue.end_line is not None:
            assert issue.end_line >= issue.line

    @given(
        st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        st.integers(max_value=0),
        st.integers(min_value=0, max_value=100),
    )
    def test_issue_invalid_line_raises_error(
        self, file_path: str, invalid_line: int, column: int
    ) -> None:
        """Property: Creating issue with line <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="Line number must be positive"):
            Issue(
                file=file_path,
                line=invalid_line,
                column=column,
                severity=Severity.INFO,
                rule_id="TEST",
                message="Test message",
            )

    @given(
        st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        st.integers(min_value=1, max_value=100),
        st.integers(max_value=-1),
    )
    def test_issue_invalid_column_raises_error(
        self, file_path: str, line: int, invalid_column: int
    ) -> None:
        """Property: Creating issue with column < 0 raises ValueError."""
        with pytest.raises(ValueError, match="Column number must be non-negative"):
            Issue(
                file=file_path,
                line=line,
                column=invalid_column,
                severity=Severity.INFO,
                rule_id="TEST",
                message="Test message",
            )

    @given(valid_issue_strategy())
    def test_issue_has_required_fields(self, issue: Issue) -> None:
        """Property: All issues have required non-empty fields."""
        assert len(issue.file) > 0
        assert len(issue.rule_id) > 0
        assert len(issue.message) > 0
        assert isinstance(issue.severity, Severity)


class TestFileAnalysisProperties:
    """Property-based tests for FileAnalysis model."""

    @given(file_analysis_strategy())
    def test_file_analysis_issues_count_consistent(
        self, analysis: FileAnalysis
    ) -> None:
        """Property: Issue count matches length of issues list."""
        assert len(analysis.issues) == len(analysis.issues)

    @given(file_analysis_strategy(), valid_issue_strategy())
    def test_add_issue_increases_count(
        self, analysis: FileAnalysis, new_issue: Issue
    ) -> None:
        """Property: Adding an issue increases the count by 1."""
        initial_count = len(analysis.issues)
        analysis.add_issue(new_issue)
        assert len(analysis.issues) == initial_count + 1

    @given(file_analysis_strategy(), severity_strategy())
    def test_get_issues_by_severity_filters_correctly(
        self, analysis: FileAnalysis, target_severity: Severity
    ) -> None:
        """Property: get_issues_by_severity returns only issues with that severity."""
        filtered = analysis.get_issues_by_severity(target_severity)
        assert all(issue.severity == target_severity for issue in filtered)
        # All issues with target severity should be in the filtered list
        expected_count = sum(
            1 for issue in analysis.issues if issue.severity == target_severity
        )
        assert len(filtered) == expected_count

    @given(file_analysis_strategy())
    def test_get_all_severities_returns_all_issues(
        self, analysis: FileAnalysis
    ) -> None:
        """Property: Getting issues for all severities returns all issues."""
        all_filtered: list[Issue] = []
        for severity in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]:
            all_filtered.extend(analysis.get_issues_by_severity(severity))

        # Each issue should appear exactly once
        assert len(all_filtered) == len(analysis.issues)

    @given(file_analysis_strategy())
    def test_has_errors_consistency(self, analysis: FileAnalysis) -> None:
        """Property: has_errors returns True iff there are HIGH or MEDIUM issues."""
        has_high_or_medium = any(
            issue.severity in (Severity.HIGH, Severity.MEDIUM)
            for issue in analysis.issues
        )
        assert analysis.has_errors() == has_high_or_medium

    @given(
        st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        st.integers(min_value=0, max_value=10000),
    )
    def test_file_analysis_lines_of_code_non_negative(
        self, file_path: str, loc: int
    ) -> None:
        """Property: Lines of code is always non-negative."""
        analysis = FileAnalysis(file_path=file_path, lines_of_code=loc)
        assert analysis.lines_of_code >= 0


class TestAnalysisResultProperties:
    """Property-based tests for AnalysisResult model."""

    @given(st.lists(file_analysis_strategy(), max_size=5))
    def test_total_issues_sum_of_all_file_issues(
        self, file_analyses: list[FileAnalysis]
    ) -> None:
        """Property: total_issues equals sum of issues in all files."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        expected_total = sum(len(analysis.issues) for analysis in file_analyses)
        assert result.total_issues() == expected_total

    @given(st.lists(file_analysis_strategy(), max_size=5))
    def test_files_analyzed_count(self, file_analyses: list[FileAnalysis]) -> None:
        """Property: files_analyzed equals number of file analyses added."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        assert result.files_analyzed() == len(file_analyses)

    @given(st.lists(file_analysis_strategy(), max_size=5))
    def test_files_with_issues_count(self, file_analyses: list[FileAnalysis]) -> None:
        """Property: files_with_issues counts only files with at least one issue."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        expected_count = sum(1 for analysis in file_analyses if analysis.issues)
        assert result.files_with_issues() == expected_count

    @given(st.lists(file_analysis_strategy(), max_size=5), severity_strategy())
    def test_get_issues_by_severity_across_files(
        self, file_analyses: list[FileAnalysis], target_severity: Severity
    ) -> None:
        """Property: get_issues_by_severity aggregates correctly across all files."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        filtered = result.get_issues_by_severity(target_severity)

        # All returned issues should have the target severity
        assert all(issue.severity == target_severity for issue in filtered)

        # Count should match sum of matching issues across all files
        expected_count = sum(
            sum(1 for issue in analysis.issues if issue.severity == target_severity)
            for analysis in file_analyses
        )
        assert len(filtered) == expected_count

    @given(st.lists(file_analysis_strategy(), max_size=5))
    def test_get_all_issues_aggregates_all(
        self, file_analyses: list[FileAnalysis]
    ) -> None:
        """Property: get_all_issues returns all issues from all files."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        all_issues = result.get_all_issues()

        # Total should match sum of all issues
        expected_total = sum(len(analysis.issues) for analysis in file_analyses)
        assert len(all_issues) == expected_total

    @given(file_analysis_strategy())
    def test_add_file_analysis_increases_count(self, analysis: FileAnalysis) -> None:
        """Property: Adding a file analysis increases count by 1."""
        result = AnalysisResult()
        initial_count = result.files_analyzed()

        result.add_file_analysis(analysis)

        assert result.files_analyzed() == initial_count + 1

    @given(st.lists(file_analysis_strategy(), min_size=1, max_size=10))
    def test_total_issues_never_exceeds_sum_of_issues(
        self, file_analyses: list[FileAnalysis]
    ) -> None:
        """Property: total_issues is exactly the sum, never more."""
        result = AnalysisResult()
        total_expected = 0

        for analysis in file_analyses:
            result.add_file_analysis(analysis)
            total_expected += len(analysis.issues)

        assert result.total_issues() == total_expected


class TestModelInvariants:
    """Test invariants across model interactions."""

    @given(valid_issue_strategy())
    def test_issue_severity_comparable(self, issue: Issue) -> None:
        """Property: Issue severity is always comparable to other severities."""
        for severity in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]:
            # Should be able to compare without error
            _ = issue.severity == severity
            _ = issue.severity < severity or issue.severity >= severity

    @given(st.lists(valid_issue_strategy(), min_size=2, max_size=10))
    def test_issues_can_be_sorted_by_line(self, issues: list[Issue]) -> None:
        """Property: Issues can always be sorted by line number."""
        sorted_issues = sorted(issues, key=lambda x: (x.file, x.line, x.column))
        # Verify sorting worked
        for i in range(len(sorted_issues) - 1):
            current = sorted_issues[i]
            next_issue = sorted_issues[i + 1]
            # Should be ordered by file, then line, then column
            assert current.file < next_issue.file or (
                current.file == next_issue.file and current.line <= next_issue.line
            )

    @given(file_analysis_strategy())
    def test_file_analysis_immutable_file_path(self, analysis: FileAnalysis) -> None:
        """Property: File path in FileAnalysis doesn't change after creation."""
        original_path = analysis.file_path
        # Add some issues
        for _ in range(3):
            analysis.add_issue(
                Issue(
                    file=analysis.file_path,
                    line=1,
                    column=0,
                    severity=Severity.INFO,
                    rule_id="TEST",
                    message="Test",
                )
            )
        # Path should still be the same
        assert analysis.file_path == original_path

    @given(st.lists(file_analysis_strategy(), max_size=5))
    def test_analysis_result_order_preserved(
        self, file_analyses: list[FileAnalysis]
    ) -> None:
        """Property: AnalysisResult preserves order of added file analyses."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        # File paths should appear in the same order
        result_paths = [fa.file_path for fa in result.file_analyses]
        expected_paths = [fa.file_path for fa in file_analyses]
        assert result_paths == expected_paths
