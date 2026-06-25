"""JSON reporter for PyRefactor analysis results."""

from __future__ import annotations

import json
import sys
from collections import Counter
from typing import TextIO

from ._version import get_version
from .models import AnalysisResult, FileAnalysis, Issue


def _issue_to_dict(issue: Issue) -> dict[str, object]:
    """Serialize a single issue to a JSON-friendly dict."""
    payload: dict[str, object] = {
        "line": issue.line,
        "column": issue.column,
        "severity": issue.severity.value,
        "rule_id": issue.rule_id,
        "message": issue.message,
    }
    if issue.suggestion is not None:
        payload["suggestion"] = issue.suggestion
    if issue.code_snippet is not None:
        payload["code_snippet"] = issue.code_snippet
    if issue.end_line is not None:
        payload["end_line"] = issue.end_line
    return payload


def _file_to_dict(analysis: FileAnalysis) -> dict[str, object]:
    """Serialize a file analysis to a JSON-friendly dict."""
    return {
        "path": analysis.file_path,
        "lines_of_code": analysis.lines_of_code,
        "issues": [_issue_to_dict(issue) for issue in analysis.issues],
        "warnings": list(analysis.warnings),
        "parse_error": analysis.parse_error,
    }


def _build_summary(result: AnalysisResult) -> dict[str, object]:
    """Build summary counts for the analysis result."""
    issues = result.get_all_issues()
    severity_counts = Counter(issue.severity.value for issue in issues)
    rule_counts = Counter(issue.rule_id for issue in issues)
    return {
        "total_issues": len(issues),
        "files_analyzed": result.files_analyzed(),
        "files_with_issues": result.files_with_issues(),
        "by_severity": dict(sorted(severity_counts.items())),
        "by_rule": dict(sorted(rule_counts.items())),
    }


def build_report_payload(result: AnalysisResult) -> dict[str, object]:
    """Build the full JSON-serializable report payload."""
    return {
        "version": get_version(),
        "summary": _build_summary(result),
        "files": [_file_to_dict(analysis) for analysis in result.file_analyses],
        "excluded_file_count": result.excluded_file_count,
    }


class JsonReporter:
    """Reports analysis results as structured JSON."""

    def __init__(self, output: TextIO | None = None) -> None:
        """Initialize the JSON reporter."""
        self.output: TextIO = output or sys.stdout

    def report(self, result: AnalysisResult) -> None:
        """Write the analysis result as formatted JSON."""
        payload = build_report_payload(result)
        json.dump(payload, self.output, indent=2)
        self.output.write("\n")
