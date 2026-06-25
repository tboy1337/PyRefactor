"""Tests for reporter."""

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from colorama import Fore

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

    def test_report_analysis_warnings(self) -> None:
        """Test reporting non-fatal analysis warnings."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)

        analysis = FileAnalysis(file_path="test.py")
        analysis.add_warning("Detector complexity failed: boom")

        result = AnalysisResult()
        result.add_file_analysis(analysis)

        reporter.report(result)

        output_text = output.getvalue()
        assert "test.py" in output_text
        assert "Warning: Detector complexity failed: boom" in output_text
        assert "Analysis warnings: 1" in output_text

    @pytest.mark.xdist_group(name="colorama")
    def test_lazy_colorama_initialization(self) -> None:
        """Test colorama is initialized on first reporter use."""
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

        assert reporter._get_severity_color(Severity.HIGH) == Fore.RED
        assert reporter._get_severity_icon(Severity.HIGH) == "✗"
        assert reporter._get_severity_icon(Severity.MEDIUM) == "⚠"

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

    def test_print_handles_unicode_encode_error(self) -> None:
        """Test reporter replaces unencodable output on narrow encodings."""
        from unittest.mock import MagicMock, patch

        narrow_stdout = MagicMock()
        narrow_stdout.encoding = "ascii"

        call_count = 0

        def _raise_once(message: str, *, file: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise UnicodeEncodeError("ascii", "x", 0, 1, "ordinal not in range")
            print(message, file=narrow_stdout)

        reporter = ConsoleReporter(output=narrow_stdout)
        with patch("pyrefactor.reporter.print", side_effect=_raise_once):
            reporter._print("test ⚠ message")

        assert call_count == 2

    def test_stdout_utf8_fallback_uses_ascii_icons(self) -> None:
        """Test reporter falls back to ASCII icons when UTF-8 setup fails."""
        mock_stdout = MagicMock()
        mock_stdout.reconfigure.side_effect = OSError("unsupported")
        del mock_stdout.buffer

        with patch("pyrefactor.reporter.sys.stdout", mock_stdout):
            reporter_stdout = ConsoleReporter()
            assert reporter_stdout.use_unicode is False

    def test_custom_output_does_not_reconfigure_stdout(self) -> None:
        """Test explicit output stream does not mutate sys.stdout."""
        output = StringIO()
        mock_stdout = MagicMock()
        mock_stdout.reconfigure = MagicMock()

        with patch("pyrefactor.reporter.sys.stdout", mock_stdout):
            reporter = ConsoleReporter(output=output)

        assert reporter.output is output
        mock_stdout.reconfigure.assert_not_called()

    def test_output_encoding_from_text_wrapper(self) -> None:
        """Test encoding detection for TextIOWrapper streams."""
        from io import BytesIO, TextIOWrapper

        from pyrefactor.reporter import _output_encoding

        buffer = BytesIO()
        wrapper = TextIOWrapper(buffer, encoding="utf-8")
        assert _output_encoding(wrapper) == "utf-8"

    def test_ascii_icon_fallback_for_missing_severity(self) -> None:
        """Test ASCII icon fallback when severity is not in the icon map."""
        output = StringIO()
        reporter = ConsoleReporter(output=output)
        reporter.use_unicode = False

        with patch.object(reporter, "ASCII_ICONS", {}):
            assert reporter._get_severity_icon(Severity.HIGH) == "*"
