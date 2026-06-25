"""Tests for JSON reporter."""

import json
from io import StringIO
from typing import cast

from pyrefactor.json_reporter import JsonReporter, build_report_payload
from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity


class TestJsonReporter:
    """Tests for JsonReporter."""

    def test_build_report_payload_structure(self) -> None:
        """Test JSON payload contains expected top-level keys."""
        result = AnalysisResult()
        analysis = FileAnalysis(file_path="sample.py", lines_of_code=10)
        analysis.add_issue(
            Issue(
                file="sample.py",
                line=3,
                column=4,
                severity=Severity.MEDIUM,
                rule_id="C001",
                message="Function too long",
                suggestion="Split the function",
                code_snippet="def foo():",
                end_line=20,
            )
        )
        analysis.add_warning("Detector duplication failed: example")
        result.add_file_analysis(analysis)
        result.excluded_file_count = 2

        payload = build_report_payload(result)
        summary = cast(dict[str, object], payload["summary"])

        assert payload["version"]
        assert summary["total_issues"] == 1
        assert summary["files_analyzed"] == 1
        assert cast(dict[str, int], summary["by_severity"])["medium"] == 1
        assert cast(dict[str, int], summary["by_rule"])["C001"] == 1
        assert payload["excluded_file_count"] == 2
        files = cast(list[dict[str, object]], payload["files"])
        assert len(files) == 1
        file_entry = files[0]
        assert file_entry["path"] == "sample.py"
        assert file_entry["warnings"] == ["Detector duplication failed: example"]
        issues_list = cast(list[dict[str, object]], file_entry["issues"])
        issue_entry = issues_list[0]
        assert issue_entry["rule_id"] == "C001"
        assert issue_entry["end_line"] == 20

    def test_report_writes_valid_json(self) -> None:
        """Test JsonReporter writes parseable JSON to the output stream."""
        result = AnalysisResult()
        result.add_file_analysis(FileAnalysis(file_path="clean.py"))

        buffer = StringIO()
        JsonReporter(output=buffer).report(result)

        parsed = json.loads(buffer.getvalue())
        assert parsed["summary"]["total_issues"] == 0
        assert parsed["files"][0]["path"] == "clean.py"

    def test_build_report_payload_includes_parse_error(self) -> None:
        """Test JSON payload serializes parse_error on file entries."""
        result = AnalysisResult()
        analysis = FileAnalysis(
            file_path="broken.py",
            parse_error="Syntax error: invalid syntax",
        )
        result.add_file_analysis(analysis)

        payload = build_report_payload(result)
        files = cast(list[dict[str, object]], payload["files"])
        file_entry = files[0]

        assert file_entry["parse_error"] == "Syntax error: invalid syntax"
        assert file_entry["issues"] == []

    def test_build_report_payload_omits_optional_issue_fields(self) -> None:
        """Test JSON payload omits optional issue fields when unset."""
        result = AnalysisResult()
        analysis = FileAnalysis(file_path="sample.py")
        analysis.add_issue(
            Issue(
                file="sample.py",
                line=1,
                column=0,
                severity=Severity.LOW,
                rule_id="T001",
                message="Example",
            )
        )
        result.add_file_analysis(analysis)

        payload = build_report_payload(result)
        files = cast(list[dict[str, object]], payload["files"])
        issues_list = cast(list[dict[str, object]], files[0]["issues"])
        issue_entry = issues_list[0]

        assert "suggestion" not in issue_entry
        assert "code_snippet" not in issue_entry
        assert "end_line" not in issue_entry
