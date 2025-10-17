"""Console reporter for PyRefactor."""

import io
import sys
from collections import defaultdict
from typing import TextIO

from colorama import Fore, Style, init

from .models import AnalysisResult, Issue, Severity

# Initialize colorama for cross-platform colored output
init(autoreset=True)


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

    def __init__(self, output: TextIO = sys.stdout) -> None:
        """Initialize reporter with output stream."""
        # Try to ensure UTF-8 encoding for Unicode symbols
        if output is sys.stdout:
            try:
                # Reconfigure stdout to use UTF-8 encoding
                if hasattr(sys.stdout, "reconfigure"):
                    # Python 3.7+ TextIOWrapper.reconfigure method
                    sys.stdout.reconfigure(encoding="utf-8")
                    self.output = sys.stdout
                    self.use_unicode = True
                else:
                    # Wrap stdout with UTF-8 text wrapper
                    self.output = io.TextIOWrapper(
                        sys.stdout.buffer,  # type: ignore[misc]
                        encoding="utf-8",
                        errors="replace",
                    )
                    self.use_unicode = True
            except (AttributeError, OSError):
                # Fall back to ASCII icons if UTF-8 is not available
                self.output = output
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

            if not analysis.issues:
                continue

            # Print file header
            self._print(f"\n{Fore.CYAN}{analysis.file_path}{Style.RESET_ALL}")

            # Sort issues by line number
            sorted_issues = sorted(
                analysis.issues, key=lambda issue: issue.line  # type: ignore[misc]
            )

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
            sorted_issues = sorted(
                issues, key=lambda issue: (issue.file, issue.line)  # type: ignore[misc]
            )

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

    def _print_summary(self, result: AnalysisResult) -> None:
        """Print summary statistics."""
        self._print(f"\n{Fore.YELLOW}{'=' * 70}{Style.RESET_ALL}")
        self._print(f"{Fore.YELLOW}Summary{Style.RESET_ALL}")
        self._print(f"{Fore.YELLOW}{'=' * 70}{Style.RESET_ALL}")

        total_issues = result.total_issues()
        files_analyzed = result.files_analyzed()
        files_with_issues = result.files_with_issues()

        self._print(f"\nFiles analyzed: {files_analyzed}")
        self._print(f"Files with issues: {files_with_issues}")
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
        print(message, file=self.output)
