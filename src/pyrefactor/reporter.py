"""Console reporter for PyRefactor."""

import io
import sys
from collections import defaultdict
from typing import BinaryIO, TextIO, cast

from colorama import Fore, Style, init

from .models import AnalysisResult, Issue, Severity


def _issue_line(issue: Issue) -> int:
    """Return the line number for sorting issues."""
    return issue.line


def _issue_file_line(issue: Issue) -> tuple[str, int]:
    """Return file and line for sorting issues."""
    return (issue.file, issue.line)


def _output_encoding(output: TextIO) -> str:
    """Return a usable encoding name for the output stream."""
    if isinstance(output, io.TextIOWrapper):
        wrapper_encoding = output.encoding
        if wrapper_encoding is not None:
            return wrapper_encoding
    return "ascii"


class _ColoramaInitializer:
    """One-time colorama initialization for console output."""

    _initialized = False

    @classmethod
    def ensure(cls) -> None:
        """Initialize colorama once on first reporter use."""
        if not cls._initialized:
            init(autoreset=True)
            cls._initialized = True


class ConsoleReporter:
    """Reporter that outputs results to console."""

    # Class-level constants for severity styling
    SEVERITY_COLORS: dict[Severity, str] = {
        Severity.HIGH: Fore.RED,
        Severity.MEDIUM: Fore.YELLOW,
        Severity.LOW: Fore.BLUE,
        Severity.INFO: Fore.CYAN,
    }

    SEVERITY_ICONS: dict[Severity, str] = {
        Severity.HIGH: "✗",
        Severity.MEDIUM: "⚠",
        Severity.LOW: "ℹ",
        Severity.INFO: "→",
    }

    # ASCII fallback icons for terminals that don't support Unicode
    ASCII_ICONS: dict[Severity, str] = {
        Severity.HIGH: "X",
        Severity.MEDIUM: "!",
        Severity.LOW: "i",
        Severity.INFO: ">",
    }

    def __init__(self, output: TextIO | None = None) -> None:
        """Initialize reporter with output stream."""
        _ColoramaInitializer.ensure()
        if output is None:
            stdout = sys.stdout
            try:
                if hasattr(stdout, "reconfigure"):
                    stdout.reconfigure(encoding="utf-8")
                    self.output = stdout
                    self.use_unicode = True
                else:
                    buffer = cast(BinaryIO, stdout.buffer)
                    self.output = io.TextIOWrapper(
                        buffer,
                        encoding="utf-8",
                        errors="replace",
                    )
                    self.use_unicode = True
            except (AttributeError, OSError):
                self.output = stdout
                self.use_unicode = False
        else:
            self.output = output
            self.use_unicode = True

    def report(self, result: AnalysisResult, group_by: str = "file") -> None:
        """Generate and print report."""
        if group_by == "file":
            self._report_by_file(result)
        elif group_by == "severity":
            self._report_by_severity(result)
        else:
            self._report_by_file(result)

        # Print summary
        self._print_summary(result)

    def _report_by_file(self, result: AnalysisResult) -> None:
        """Report issues grouped by file."""
        for analysis in result.file_analyses:
            if analysis.parse_error:
                self._print(f"\n{Fore.RED}✗ {analysis.file_path}{Style.RESET_ALL}")
                self._print(f"  Parse error: {analysis.parse_error}")
                continue

            if not analysis.issues and not analysis.warnings:
                continue

            # Print file header
            self._print(f"\n{Fore.CYAN}{analysis.file_path}{Style.RESET_ALL}")

            for warning in analysis.warnings:
                self._print(f"  {Fore.YELLOW}⚠ Warning: {warning}{Style.RESET_ALL}")

            if not analysis.issues:
                continue

            # Sort issues by line number
            sorted_issues = sorted(analysis.issues, key=_issue_line)

            # Print each issue
            for issue in sorted_issues:
                self._print_issue(issue)

    def _report_by_severity(self, result: AnalysisResult) -> None:
        """Report issues grouped by severity."""
        issues_by_severity: dict[Severity, list[Issue]] = defaultdict(list)

        for issue in result.get_all_issues():
            issues_by_severity[issue.severity].append(issue)

        # Print in order: HIGH, MEDIUM, LOW, INFO
        for severity in [Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            issues = issues_by_severity.get(severity, [])
            if not issues:
                continue

            color = self._get_severity_color(severity)
            self._print(
                f"\n{color}{severity.value.upper()} Severity Issues{Style.RESET_ALL}"
            )

            # Sort by file and line
            sorted_issues = sorted(issues, key=_issue_file_line)

            for issue in sorted_issues:
                self._print_issue(issue, include_file=True)

    def _print_issue(self, issue: Issue, include_file: bool = False) -> None:
        """Print a single issue."""
        # Severity indicator
        severity_color = self._get_severity_color(issue.severity)
        severity_icon = self._get_severity_icon(issue.severity)

        # Location
        location = f"{issue.line}:{issue.column}"
        if include_file:
            location = f"{issue.file}:{location}"

        # Print main issue line
        self._print(
            f"  {severity_color}{severity_icon} [{issue.rule_id}] "
            f"{location}{Style.RESET_ALL}"
        )
        self._print(f"    {issue.message}")

        # Print suggestion if available
        if issue.suggestion:
            self._print(f"    {Fore.GREEN}→ {issue.suggestion}{Style.RESET_ALL}")

        # Print code snippet if available
        if issue.code_snippet:
            self._print(
                f"    {Fore.LIGHTBLACK_EX}{issue.code_snippet}{Style.RESET_ALL}"
            )

    @staticmethod
    def _count_parse_errors(result: AnalysisResult) -> int:
        """Return the number of files with parse errors."""
        return sum(
            1 for analysis in result.file_analyses if analysis.parse_error is not None
        )

    @staticmethod
    def _count_warnings(result: AnalysisResult) -> int:
        """Return the total number of analysis warnings."""
        return sum(len(analysis.warnings) for analysis in result.file_analyses)

    def _print_summary(self, result: AnalysisResult) -> None:
        """Print summary statistics."""
        self._print(f"\n{Fore.YELLOW}{'=' * 70}{Style.RESET_ALL}")
        self._print(f"{Fore.YELLOW}Summary{Style.RESET_ALL}")
        self._print(f"{Fore.YELLOW}{'=' * 70}{Style.RESET_ALL}")

        total_issues = result.total_issues()
        files_analyzed = result.files_analyzed()
        files_with_issues = result.files_with_issues()
        files_with_parse_errors = self._count_parse_errors(result)
        total_warnings = self._count_warnings(result)

        self._print(f"\nFiles analyzed: {files_analyzed}")
        self._print(f"Files with issues: {files_with_issues}")
        if files_with_parse_errors > 0:
            self._print(f"Files with parse errors: {files_with_parse_errors}")
        if total_warnings > 0:
            self._print(f"Analysis warnings: {total_warnings}")
        self._print(f"Total issues: {total_issues}")

        if total_issues > 0:
            self._print("\nIssues by severity:")
            for severity in [
                Severity.HIGH,
                Severity.MEDIUM,
                Severity.LOW,
                Severity.INFO,
            ]:
                count = len(result.get_issues_by_severity(severity))
                if count > 0:
                    color = self._get_severity_color(severity)
                    self._print(
                        f"  {color}{severity.value.upper()}: {count}{Style.RESET_ALL}"
                    )

        # Exit code indicator
        if any(
            issue.severity in (Severity.HIGH, Severity.MEDIUM)
            for issue in result.get_all_issues()
        ):
            self._print(
                f"\n{Fore.RED}⚠ High or medium severity issues found{Style.RESET_ALL}"
            )

    def _get_severity_color(self, severity: Severity) -> str:
        """Get color for severity level."""
        return self.SEVERITY_COLORS.get(severity, "")

    def _get_severity_icon(self, severity: Severity) -> str:
        """Get icon for severity level."""
        if self.use_unicode:
            return self.SEVERITY_ICONS.get(severity, "•")
        return self.ASCII_ICONS.get(severity, "*")

    def _print(self, message: str) -> None:
        """Print a message to output."""
        try:
            print(message, file=self.output)
        except UnicodeEncodeError:
            encoding = _output_encoding(self.output)
            safe_message = message.encode(encoding, errors="replace").decode(encoding)
            print(safe_message, file=self.output)
