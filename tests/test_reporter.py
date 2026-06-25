"""Tests for reporter."""

import sys
from io import StringIO

from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity
from pyrefactor.reporter import ConsoleReporter


class TestConsoleReporter:
    """Tests for ConsoleReporter."""

    def test_reporter_creation(self) -> None:
        """Test creating a reporter."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        assert reporter.output == output

    def test_report_no_issues(self) -> None:
        """Test reporting with no issues."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        result = AnalysisResult()
        result.add_file_analysis(FileAnalysis(file_path="test.py"))

        reporter.report(result)

        output_text = output.getvalue()
        assert "Summary" in output_text
        assert "Files analyzed: 1" in output_text

    def test_report_with_issues(self) -> None:
        """Test reporting with issues."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(
            Issue(
                file="test.py",
                line=10,
                column=5,
                severity=Severity.HIGH,
                rule_id="C001",
                message="Test issue",
                suggestion="Fix this way",
            )
        )

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        reporter.report(result)

        output_text = output.getvalue()
        assert "test.py" in output_text
        assert "C001" in output_text
        assert "Test issue" in output_text
        assert "Fix this way" in output_text

    def test_report_by_severity(self) -> None:
        """Test reporting grouped by severity."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="C001",
                message="High issue",
            )
        )
        analysis.add_issue(
            Issue(
                file="test.py",
                line=2,
                column=0,
                severity=Severity.LOW,
                rule_id="C002",
                message="Low issue",
            )
        )

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        reporter.report(result, group_by="severity")

        output_text = output.getvalue()
        assert "HIGH" in output_text
        assert "LOW" in output_text

    def test_report_parse_error(self) -> None:
        """Test reporting parse errors."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis = FileAnalysis(
            file_path="broken.py", parse_error="Syntax error on line 5"
        )

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        reporter.report(result)

        output_text = output.getvalue()
        assert "broken.py" in output_text
        assert "Parse error" in output_text
        assert "Files with parse errors: 1" in output_text

    def test_lazy_colorama_initialization(self) -> None:
        """Test colorama is initialized on first reporter use."""
        from unittest.mock import patch

        import pyrefactor.reporter as reporter_module

        reporter_module._ColoramaInitializer._initialized = False
        with patch.object(reporter_module, "init") as mock_init:
            ConsoleReporter(output=StringIO())
            mock_init.assert_called_once_with(autoreset=True)

    def test_summary_statistics(self) -> None:
        """Test summary statistics."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis1 = FileAnalysis(file_path="test1.py")
        analysis1.add_issue(
            Issue(
                file="test1.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="C001",
                message="Issue 1",
            )
        )

        analysis2 = FileAnalysis(file_path="test2.py")
        analysis2.add_issue(
            Issue(
                file="test2.py",
                line=1,
                column=0,
                severity=Severity.MEDIUM,
                rule_id="C002",
                message="Issue 2",
            )
        )
        analysis2.add_issue(
            Issue(
                file="test2.py",
                line=2,
                column=0,
                severity=Severity.LOW,
                rule_id="C003",
                message="Issue 3",
            )
        )

        result = AnalysisResult()
        result.add_file_analysis(analysis1)
        result.add_file_analysis(analysis2)

        reporter.report(result)

        output_text = output.getvalue()
        assert "Files analyzed: 2" in output_text
        assert "Files with issues: 2" in output_text
        assert "Total issues: 3" in output_text
        assert "HIGH: 1" in output_text
        assert "MEDIUM: 1" in output_text
        assert "LOW: 1" in output_text

    def test_severity_color_and_icon(self) -> None:
        """Test private severity styling helpers."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        assert reporter._get_severity_color(Severity.HIGH)
        assert reporter._get_severity_icon(Severity.HIGH)

    def test_invalid_group_by_defaults_to_file(self) -> None:
        """Test unknown group_by falls back to file grouping."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.LOW,
                rule_id="C001",
                message="Issue",
            )
        )

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        reporter.report(result, group_by="invalid")
        output_text = output.getvalue()
        assert "test.py" in output_text

    def test_report_issue_with_code_snippet(self) -> None:
        """Test reporting issues that include code snippets."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.LOW,
                rule_id="C001",
                message="Issue with snippet",
                code_snippet="x = 1",
            )
        )

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        reporter.report(result)
        assert "x = 1" in output.getvalue()

    def test_stdout_utf8_fallback_uses_ascii_icons(self) -> None:
        """Test reporter falls back to ASCII icons when UTF-8 setup fails."""
        from unittest.mock import MagicMock, patch

        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = OSError("unsupported")
        del mock_stdout.buffer

        with patch("pyrefactor.reporter.sys.stdout", mock_stdout):
            reporter_stdout = ConsoleReporter(output=sys.stdout)
            assert reporter_stdout.use_unicode is False
