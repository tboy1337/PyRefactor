"""Console reporter for PyRefactor."""

import sys
from collections import defaultdict
from typing import TextIO, cast

from colorama import Fore, Style, init  # type: ignore[import-untyped]

from .models import AnalysisResult, Issue, Severity

# Initialize colorama for cross-platform colored output
init(autoreset=True)  # type: ignore[no-untyped-call]


class ConsoleReporter:
    """Reporter that outputs results to console."""

    def __init__(self, output: TextIO = sys.stdout) -> None:
        """Initialize reporter with output stream."""
        self.output = output

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
                self._print_error(
                    f"\n{Fore.RED}✗ {analysis.file_path}{Style.RESET_ALL}"  # type: ignore[misc]
                )
                self._print_error(f"  Parse error: {analysis.parse_error}")
                continue

            if not analysis.issues:
                continue

            # Print file header
            self._print_header(f"\n{Fore.CYAN}{analysis.file_path}{Style.RESET_ALL}")  # type: ignore[misc]

            # Sort issues by line number
            sorted_issues = sorted(analysis.issues, key=lambda x: x.line)

            # Print each issue
            for issue in sorted_issues:
                self._print_issue(issue)

    def _report_by_severity(self, result: AnalysisResult) -> None:
        """Report issues grouped by severity."""
        issues_by_severity: dict[Severity, list[Issue]] = defaultdict(list)  # type: ignore[misc]

        for issue in result.get_all_issues():
            issues_by_severity[issue.severity].append(issue)

        # Print in order: HIGH, MEDIUM, LOW, INFO
        for severity in [Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            issues = issues_by_severity.get(severity, [])
            if not issues:
                continue

            color = self._get_severity_color(severity)
            self._print_header(
                f"\n{color}{severity.value.upper()} Severity Issues{Style.RESET_ALL}"  # type: ignore[misc]
            )

            # Sort by file and line
            sorted_issues = sorted(issues, key=lambda x: (x.file, x.line))

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
            f"  {severity_color}{severity_icon} [{issue.rule_id}] "  # type: ignore[misc]
            f"{location}{Style.RESET_ALL}"  # type: ignore[misc]
        )
        self._print(f"    {issue.message}")

        # Print suggestion if available
        if issue.suggestion:
            self._print(f"    {Fore.GREEN}→ {issue.suggestion}{Style.RESET_ALL}")  # type: ignore[misc]

        # Print code snippet if available
        if issue.code_snippet:
            self._print(f"    {Fore.LIGHTBLACK_EX}{issue.code_snippet}{Style.RESET_ALL}")  # type: ignore[misc]

    def _print_summary(self, result: AnalysisResult) -> None:
        """Print summary statistics."""
        self._print_header(f"\n{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")  # type: ignore[misc]
        self._print_header(f"{Fore.YELLOW}Summary{Style.RESET_ALL}")  # type: ignore[misc]
        self._print_header(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")  # type: ignore[misc]

        total_issues = result.total_issues()
        files_analyzed = result.files_analyzed()
        files_with_issues = result.files_with_issues()

        self._print(f"\nFiles analyzed: {files_analyzed}")
        self._print(f"Files with issues: {files_with_issues}")
        self._print(f"Total issues: {total_issues}")

        if total_issues > 0:
            self._print("\nIssues by severity:")
            for severity in [Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
                count = len(result.get_issues_by_severity(severity))
                if count > 0:
                    color = self._get_severity_color(severity)
                    self._print(
                        f"  {color}{severity.value.upper()}: {count}{Style.RESET_ALL}"  # type: ignore[misc]
                    )

        # Exit code indicator
        if any(
            issue.severity in (Severity.HIGH, Severity.MEDIUM)
            for issue in result.get_all_issues()
        ):
            self._print(
                f"\n{Fore.RED}⚠ High or medium severity issues found{Style.RESET_ALL}"  # type: ignore[misc]
            )

    def _get_severity_color(self, severity: Severity) -> str:
        """Get color for severity level."""
        colors: dict[Severity, str] = {  # type: ignore[misc]
            Severity.HIGH: Fore.RED,  # type: ignore[misc]
            Severity.MEDIUM: Fore.YELLOW,  # type: ignore[misc]
            Severity.LOW: Fore.BLUE,  # type: ignore[misc]
            Severity.INFO: Fore.CYAN,  # type: ignore[misc]
        }
        return cast(str, colors.get(severity, ""))  # type: ignore[misc]

    def _get_severity_icon(self, severity: Severity) -> str:
        """Get icon for severity level."""
        icons = {
            Severity.HIGH: "✗",
            Severity.MEDIUM: "⚠",
            Severity.LOW: "ℹ",
            Severity.INFO: "→",
        }
        return icons.get(severity, "•")

    def _print(self, message: str) -> None:
        """Print a message to output."""
        print(message, file=self.output)

    def _print_header(self, message: str) -> None:
        """Print a header message."""
        print(message, file=self.output)

    def _print_error(self, message: str) -> None:
        """Print an error message."""
        print(message, file=self.output)

