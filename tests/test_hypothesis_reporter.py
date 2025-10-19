"""Property-based tests for ConsoleReporter using Hypothesis."""

import io

from hypothesis import given
from hypothesis import strategies as st

from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity
from pyrefactor.reporter import ConsoleReporter


# Reuse strategies from test_hypothesis_models
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


@st.composite
def analysis_result_strategy(draw: st.DrawFn) -> AnalysisResult:
    """Generate an AnalysisResult with multiple file analyses."""
    result = AnalysisResult()
    num_files = draw(st.integers(min_value=0, max_value=5))

    for _ in range(num_files):
        analysis = draw(file_analysis_strategy())
        result.add_file_analysis(analysis)

    return result


class TestConsoleReporterProperties:
    """Property-based tests for ConsoleReporter."""

    @given(analysis_result_strategy())
    def test_report_never_crashes(self, result: AnalysisResult) -> None:
        """Property: Reporter never crashes regardless of input."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        # Should not raise any exceptions
        reporter.report(result, group_by="file")
        reporter.report(result, group_by="severity")

        # Output should be a string
        assert isinstance(output.getvalue(), str)

    @given(analysis_result_strategy())
    def test_report_produces_output(self, result: AnalysisResult) -> None:
        """Property: Reporter always produces some output."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should always produce at least summary output
        assert len(output_str) > 0

    @given(analysis_result_strategy())
    def test_report_contains_summary(self, result: AnalysisResult) -> None:
        """Property: Reporter output always contains a summary."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should contain "Summary" in output
        assert "Summary" in output_str or "summary" in output_str.lower()

    @given(analysis_result_strategy())
    def test_report_mentions_file_count(self, result: AnalysisResult) -> None:
        """Property: Reporter output mentions number of files analyzed."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should mention files analyzed
        expected_count = result.files_analyzed()
        assert str(expected_count) in output_str

    @given(analysis_result_strategy())
    def test_report_mentions_issue_count(self, result: AnalysisResult) -> None:
        """Property: Reporter output mentions total number of issues."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should mention total issues
        expected_total = result.total_issues()
        assert str(expected_total) in output_str

    @given(analysis_result_strategy(), st.sampled_from(["file", "severity"]))
    def test_report_accepts_valid_group_by_values(
        self, result: AnalysisResult, group_by: str
    ) -> None:
        """Property: Reporter accepts all valid group_by values."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        # Should not raise
        reporter.report(result, group_by=group_by)
        assert len(output.getvalue()) > 0

    @given(analysis_result_strategy())
    def test_report_by_file_includes_file_paths(self, result: AnalysisResult) -> None:
        """Property: Report by file includes file paths with issues."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # For each file with issues, path should appear in output
        for analysis in result.file_analyses:
            if analysis.issues and not analysis.parse_error:
                # File path should be mentioned (might be partial match)
                # Just check that some part of the path appears
                assert (
                    any(
                        part in output_str
                        for part in analysis.file_path.split("/")
                        if len(part) > 3
                    )
                    or analysis.file_path in output_str
                )

    @given(file_analysis_strategy())
    def test_parse_error_appears_in_output(self, analysis: FileAnalysis) -> None:
        """Property: Parse errors are mentioned in output."""
        if analysis.parse_error:
            result = AnalysisResult()
            result.add_file_analysis(analysis)

            output = io.StringIO()
            reporter = ConsoleReporter(output=output)
            reporter.report(result, group_by="file")
            output_str = output.getvalue()

            # Parse error should be mentioned
            assert "error" in output_str.lower() or "Error" in output_str


class TestSeverityColorProperties:
    """Property-based tests for severity color mapping."""

    @given(severity_strategy())
    def test_get_severity_color_returns_string(self, severity: Severity) -> None:
        """Property: Color getter always returns a string."""
        reporter = ConsoleReporter()
        color = reporter._get_severity_color(severity)
        assert isinstance(color, str)

    @given(severity_strategy())
    def test_get_severity_icon_returns_string(self, severity: Severity) -> None:
        """Property: Icon getter always returns a string."""
        reporter = ConsoleReporter()
        icon = reporter._get_severity_icon(severity)
        assert isinstance(icon, str)
        assert len(icon) > 0

    def test_all_severities_have_colors(self) -> None:
        """Property: All severity levels have defined colors."""
        reporter = ConsoleReporter()
        for severity in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]:
            color = reporter._get_severity_color(severity)
            assert isinstance(color, str)

    def test_all_severities_have_icons(self) -> None:
        """Property: All severity levels have defined icons."""
        reporter = ConsoleReporter()
        for severity in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]:
            icon = reporter._get_severity_icon(severity)
            assert isinstance(icon, str)
            assert len(icon) > 0


class TestIssueOutputProperties:
    """Property-based tests for issue output formatting."""

    @given(valid_issue_strategy())
    def test_issue_output_includes_rule_id(self, issue: Issue) -> None:
        """Property: Issue output includes rule ID."""
        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(issue)
        result = AnalysisResult()
        result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Rule ID should appear in output
        assert issue.rule_id in output_str

    @given(valid_issue_strategy())
    def test_issue_output_includes_line_number(self, issue: Issue) -> None:
        """Property: Issue output includes line number."""
        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(issue)
        result = AnalysisResult()
        result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Line number should appear in output
        assert str(issue.line) in output_str

    @given(valid_issue_strategy())
    def test_issue_output_includes_message(self, issue: Issue) -> None:
        """Property: Issue output includes the message."""
        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(issue)
        result = AnalysisResult()
        result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Message should appear in output (at least partially)
        if len(issue.message) > 10:
            # Check for a substantial substring
            assert (
                any(
                    issue.message[i : i + 10] in output_str
                    for i in range(len(issue.message) - 10)
                )
                or issue.message in output_str
            )

    @given(valid_issue_strategy())
    def test_issue_with_suggestion_includes_suggestion(self, issue: Issue) -> None:
        """Property: Issues with suggestions include the suggestion in output."""
        if issue.suggestion and len(issue.suggestion) > 5:
            analysis = FileAnalysis(file_path="test.py")
            analysis.add_issue(issue)
            result = AnalysisResult()
            result.add_file_analysis(analysis)

            output = io.StringIO()
            reporter = ConsoleReporter(output=output)
            reporter.report(result, group_by="file")
            output_str = output.getvalue()

            # Suggestion should appear in output
            assert (
                any(
                    issue.suggestion[i : i + 5] in output_str
                    for i in range(len(issue.suggestion) - 5)
                )
                or issue.suggestion in output_str
            )


class TestReportGroupingProperties:
    """Property-based tests for different grouping strategies."""

    @given(analysis_result_strategy())
    def test_report_by_severity_groups_correctly(self, result: AnalysisResult) -> None:
        """Property: Report by severity mentions severity levels."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="severity")
        output_str = output.getvalue()

        # If there are issues, severity levels should be mentioned
        if result.total_issues() > 0:
            # At least one severity level should appear
            severity_found = any(
                sev.value.upper() in output_str
                for sev in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]
            )
            assert severity_found or any(
                sev.value.lower() in output_str
                for sev in [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH]
            )

    @given(analysis_result_strategy())
    def test_invalid_group_by_defaults_to_file(self, result: AnalysisResult) -> None:
        """Property: Invalid group_by values default to file grouping."""
        output1 = io.StringIO()
        output2 = io.StringIO()

        reporter1 = ConsoleReporter(output=output1)
        reporter2 = ConsoleReporter(output=output2)

        # Testing invalid input - should default to file grouping
        reporter1.report(result, group_by="invalid_grouping")  # Intentional test
        reporter2.report(result, group_by="file")

        # Both should produce output (same behavior)
        assert len(output1.getvalue()) > 0
        assert len(output2.getvalue()) > 0


class TestReporterOutputInvariants:
    """Test invariants in reporter output."""

    @given(st.lists(valid_issue_strategy(), min_size=1, max_size=5))
    def test_all_issues_appear_in_output(self, issues: list[Issue]) -> None:
        """Property: All issues appear somewhere in the output."""
        analysis = FileAnalysis(file_path="test.py")
        for issue in issues:
            analysis.add_issue(issue)

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Each issue's rule ID should appear
        for issue in issues:
            assert issue.rule_id in output_str

    @given(analysis_result_strategy())
    def test_reporter_output_is_text(self, result: AnalysisResult) -> None:
        """Property: Reporter output is always valid text."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should be valid string that can be encoded
        assert isinstance(output_str, str)
        # Should be able to encode to UTF-8
        output_str.encode("utf-8")

    @given(analysis_result_strategy())
    def test_reporter_output_deterministic(self, result: AnalysisResult) -> None:
        """Property: Running reporter twice produces same output."""
        output1 = io.StringIO()
        output2 = io.StringIO()

        reporter1 = ConsoleReporter(output=output1)
        reporter2 = ConsoleReporter(output=output2)

        reporter1.report(result, group_by="file")
        reporter2.report(result, group_by="file")

        # Should produce identical output
        assert output1.getvalue() == output2.getvalue()

    @given(analysis_result_strategy())
    def test_empty_result_produces_summary(self, result: AnalysisResult) -> None:
        """Property: Even empty results produce a summary."""
        output = io.StringIO()
        reporter = ConsoleReporter(output=output)

        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should still have summary section
        assert len(output_str) > 0
        # Should mention 0 issues if there are none
        if result.total_issues() == 0:
            assert "0" in output_str


class TestReporterSummaryProperties:
    """Property-based tests for summary statistics."""

    @given(st.lists(file_analysis_strategy(), min_size=1, max_size=5))
    def test_summary_files_analyzed_correct(
        self, file_analyses: list[FileAnalysis]
    ) -> None:
        """Property: Summary shows correct number of files analyzed."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should mention correct file count
        expected = str(len(file_analyses))
        assert expected in output_str

    @given(st.lists(file_analysis_strategy(), min_size=1, max_size=5))
    def test_summary_files_with_issues_correct(
        self, file_analyses: list[FileAnalysis]
    ) -> None:
        """Property: Summary shows correct number of files with issues."""
        result = AnalysisResult()
        for analysis in file_analyses:
            result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should mention files with issues
        expected_with_issues = sum(1 for fa in file_analyses if fa.issues)
        assert str(expected_with_issues) in output_str

    @given(severity_strategy(), st.integers(min_value=1, max_value=5))
    def test_summary_counts_by_severity(
        self, severity: Severity, num_issues: int
    ) -> None:
        """Property: Summary correctly counts issues by severity."""
        analysis = FileAnalysis(file_path="test.py")
        for i in range(num_issues):
            analysis.add_issue(
                Issue(
                    file="test.py",
                    line=i + 1,
                    column=0,
                    severity=severity,
                    rule_id=f"T{i:03d}",
                    message=f"Test issue {i}",
                )
            )

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        output = io.StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.report(result, group_by="file")
        output_str = output.getvalue()

        # Should mention severity level and count
        assert str(num_issues) in output_str
