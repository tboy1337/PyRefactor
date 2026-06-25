"""Tests for analyzer."""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from pyrefactor.analyzer import Analyzer
from pyrefactor.ast_visitor import BaseDetector
from pyrefactor.config import Config
from pyrefactor.models import Issue, Severity


class TestAnalyzer:
    """Tests for Analyzer."""

    def test_analyzer_creation(self, default_config: Config) -> None:
        """Test creating an analyzer."""
        analyzer = Analyzer(default_config)

        assert analyzer.config == default_config

    def test_analyze_simple_file(
        self, default_config: Config, temp_python_file: Path
    ) -> None:
        """Test analyzing a simple Python file."""
        analyzer = Analyzer(default_config)

        analysis = analyzer.analyze_file(temp_python_file)

        assert analysis.file_path == str(temp_python_file)
        assert analysis.parse_error is None
        assert analysis.lines_of_code > 0

    def test_analyze_file_with_issues(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test analyzing a file that has issues."""
        file_path = tmp_path / "complex.py"
        code = "\n".join([f"    x = {i}" for i in range(60)])
        file_path.write_text(f"def long_func():\n{code}\n    return x")

        analyzer = Analyzer(default_config)
        analysis = analyzer.analyze_file(file_path)

        assert len(analysis.issues) > 0

    def test_analyze_file_with_syntax_error(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test analyzing a file with syntax errors."""
        file_path = tmp_path / "invalid.py"
        file_path.write_text("def broken(\n    this is invalid")

        analyzer = Analyzer(default_config)
        analysis = analyzer.analyze_file(file_path)

        assert analysis.parse_error is not None
        assert "syntax error" in analysis.parse_error.lower()

    def test_analyze_directory(self, default_config: Config, tmp_path: Path) -> None:
        """Test analyzing a directory."""
        # Create multiple Python files
        (tmp_path / "file1.py").write_text("def func1(): pass")
        (tmp_path / "file2.py").write_text("def func2(): pass")
        (tmp_path / "file3.py").write_text("def func3(): pass")

        analyzer = Analyzer(default_config)
        result = analyzer.analyze_directory(tmp_path)

        assert result.files_analyzed() == 3

    def test_analyze_empty_directory(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test analyzing an empty directory."""
        analyzer = Analyzer(default_config)
        result = analyzer.analyze_directory(tmp_path)

        assert result.files_analyzed() == 0

    def test_analyze_files_list(self, default_config: Config, tmp_path: Path) -> None:
        """Test analyzing a list of files."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("def func1(): pass")
        file2.write_text("def func2(): pass")

        analyzer = Analyzer(default_config)
        result = analyzer.analyze_files([file1, file2])

        assert result.files_analyzed() == 2

    def test_analyze_mixed_paths(self, default_config: Config, tmp_path: Path) -> None:
        """Test analyzing mixed files and directories."""
        file1 = tmp_path / "file1.py"
        file1.write_text("def func1(): pass")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.py").write_text("def func2(): pass")

        analyzer = Analyzer(default_config)
        result = analyzer.analyze_files([file1, subdir])

        assert result.files_analyzed() == 2

    def test_excluded_patterns(self, tmp_path: Path) -> None:
        """Test that excluded patterns are filtered."""
        config = Config()
        config.exclude_patterns = ["test_*.py"]

        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "test_file.py").write_text("def test(): pass")

        analyzer = Analyzer(config)
        result = analyzer.analyze_directory(tmp_path)

        assert result.files_analyzed() == 1
        assert result.excluded_file_count == 1
        assert all("main.py" in a.file_path for a in result.file_analyses)
        assert not any("test_file.py" in a.file_path for a in result.file_analyses)

    def test_filter_excluded_files(self, tmp_path: Path) -> None:
        """Test _filter_excluded_files helper."""
        config = Config()
        config.exclude_patterns = ["**/tests/**"]
        analyzer = Analyzer(config)

        files = [
            tmp_path / "src" / "main.py",
            tmp_path / "tests" / "test_main.py",
        ]
        filtered = analyzer._filter_excluded_files(files)

        assert filtered == [files[0]]

    def test_analyze_empty_file(self, default_config: Config, tmp_path: Path) -> None:
        """Test analyzing an empty file."""
        file_path = tmp_path / "empty.py"
        file_path.write_text("")

        analyzer = Analyzer(default_config)
        analysis = analyzer.analyze_file(file_path)

        assert analysis.lines_of_code == 0
        assert analysis.parse_error is None

    def test_analyze_deterministic(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test that analyzing the same file twice yields the same results."""
        file_path = tmp_path / "sample.py"
        file_path.write_text("def func():\n    return 1\n")

        analyzer = Analyzer(default_config)
        first = analyzer.analyze_file(file_path)
        second = analyzer.analyze_file(file_path)

        assert len(first.issues) == len(second.issues)
        assert first.lines_of_code == second.lines_of_code

    def test_file_too_large(self, default_config: Config, tmp_path: Path) -> None:
        """Test that oversized files are rejected."""
        file_path = tmp_path / "large.py"
        file_path.write_bytes(b"x" * (10 * 1024 * 1024 + 1))

        analyzer = Analyzer(default_config)
        analysis = analyzer.analyze_file(file_path)

        assert analysis.parse_error is not None
        assert "maximum size" in analysis.parse_error.lower()

    def test_non_utf8_file(self, default_config: Config, tmp_path: Path) -> None:
        """Test handling of non-UTF-8 files."""
        file_path = tmp_path / "binary.py"
        file_path.write_bytes(b"\xff\xfe def func(): pass")

        analyzer = Analyzer(default_config)
        analysis = analyzer.analyze_file(file_path)

        assert analysis.parse_error is not None
        assert "utf-8" in analysis.parse_error.lower()

    def test_analyze_files_parallel(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test parallel analysis of multiple files."""
        files = []
        for index in range(4):
            file_path = tmp_path / f"module_{index}.py"
            file_path.write_text(f"def func_{index}():\n    return {index}\n")
            files.append(file_path)

        analyzer = Analyzer(default_config)
        result = analyzer.analyze_files(files, max_workers=4)

        assert result.files_analyzed() == 4

    def test_analyze_directory_with_workers(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test directory analysis respects max_workers."""
        for index in range(3):
            (tmp_path / f"file_{index}.py").write_text("def f(): pass")

        analyzer = Analyzer(default_config)
        result = analyzer.analyze_directory(tmp_path, max_workers=2)

        assert result.files_analyzed() == 3

    def test_disabled_detectors(self, tmp_path: Path) -> None:
        """Test that disabled detectors don't run."""
        config = Config()
        config.performance.enabled = False

        file_path = tmp_path / "perf.py"
        file_path.write_text("""
result_str = ""
for item in items:
    result_str += item
""")

        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        # Should not have performance issues
        assert not any(issue.rule_id.startswith("P") for issue in analysis.issues)

    def test_disabled_complexity_detector(self, tmp_path: Path) -> None:
        """Test that disabled complexity detector does not run."""
        config = Config()
        config.complexity.enabled = False

        file_path = tmp_path / "complex.py"
        code = "\n".join([f"    x = {i}" for i in range(60)])
        file_path.write_text(f"def long_func():\n{code}\n    return x")

        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        assert not any(issue.rule_id.startswith("C") for issue in analysis.issues)


class ConcreteDetector(BaseDetector):
    """Concrete detector for testing BaseDetector."""

    def get_detector_name(self) -> str:
        """Return detector name."""
        return "test_detector"


class TestBaseDetector:
    """Tests for BaseDetector base class."""

    def test_get_source_line_valid(self, default_config: Config) -> None:
        """Test getting a valid source line."""
        source_lines = ["line 1", "line 2", "line 3"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        assert detector.get_source_line(1) == "line 1"
        assert detector.get_source_line(2) == "line 2"
        assert detector.get_source_line(3) == "line 3"

    def test_get_source_line_invalid(self, default_config: Config) -> None:
        """Test getting an invalid source line."""
        source_lines = ["line 1", "line 2"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        assert detector.get_source_line(0) == ""
        assert detector.get_source_line(3) == ""
        assert detector.get_source_line(-1) == ""

    def test_get_source_snippet_valid(self, default_config: Config) -> None:
        """Test getting a valid source snippet."""
        source_lines = ["line 1", "line 2", "line 3", "line 4"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        snippet = detector.get_source_snippet(2, 3)
        assert snippet == "line 2\nline 3"

    def test_get_source_snippet_invalid(self, default_config: Config) -> None:
        """Test getting an invalid source snippet."""
        source_lines = ["line 1", "line 2"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        # Start line < 1
        assert detector.get_source_snippet(0, 2) == ""

        # End line > length
        assert detector.get_source_snippet(1, 10) == ""

    def test_is_suppressed_no_lineno(self, default_config: Config) -> None:
        """Test is_suppressed with node that has no lineno."""
        source_lines = ["line 1"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        # Create a node without lineno attribute
        node = ast.Module(body=[], type_ignores=[])

        assert detector.is_suppressed(node) is False

    def test_is_suppressed_previous_line(self, default_config: Config) -> None:
        """Test is_suppressed with suppression on previous line."""
        source_lines = ["# pyrefactor: ignore", "x = 1"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        source = "x = 1"
        tree = ast.parse(source)
        node = tree.body[0]
        node.lineno = 2

        assert detector.is_suppressed(node) is True

    def test_is_suppressed_rule_specific(self, default_config: Config) -> None:
        """Test rule-specific suppression ignores only matching rules."""
        source_lines = ["if x == True:  # pyrefactor: ignore B004", "    pass"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        tree = ast.parse("\n".join(source_lines))
        node = tree.body[0]

        assert detector.is_suppressed(node, "B004") is True
        assert detector.is_suppressed(node, "B001") is False

    def test_is_suppressed_blanket_ignore(self, default_config: Config) -> None:
        """Test blanket pyrefactor ignore suppresses all rules."""
        source_lines = ["if x == True:  # pyrefactor: ignore", "    pass"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)

        tree = ast.parse("\n".join(source_lines))
        node = tree.body[0]

        assert detector.is_suppressed(node, "B001") is True
        assert detector.is_suppressed(node, "C001") is True

    def test_analyze_clears_issues_on_rerun(self, default_config: Config) -> None:
        """Test analyze resets issues when run multiple times."""
        source = "x = 1"
        tree = ast.parse(source)
        detector = ConcreteDetector(default_config, "test.py", source.split("\n"))

        detector.issues.append(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.INFO,
                rule_id="T001",
                message="Stale issue",
            )
        )

        issues = detector.analyze(tree)

        assert issues == []
        assert detector.issues == []

    def test_add_issue(self, default_config: Config) -> None:
        """Test adding issues to detector."""
        detector = ConcreteDetector(default_config, "test.py", [])

        issue = Issue(
            file="test.py",
            line=1,
            column=0,
            severity=Severity.INFO,
            rule_id="T001",
            message="Test issue",
            suggestion="Fix it",
        )

        detector.add_issue(issue)

        assert len(detector.issues) == 1
        assert detector.issues[0] == issue

    def test_report_issue_populates_code_snippet(self, default_config: Config) -> None:
        """Test report_issue auto-populates code_snippet from source."""
        source_lines = ["if x == True:", "    pass"]
        detector = ConcreteDetector(default_config, "test.py", source_lines)
        tree = ast.parse("\n".join(source_lines))
        node = tree.body[0]

        detector.report_issue(
            node,
            severity=Severity.INFO,
            rule_id="T001",
            message="Test",
            suggestion="Fix",
        )

        assert len(detector.issues) == 1
        assert detector.issues[0].code_snippet == "if x == True:"

    def test_analyze(self, default_config: Config) -> None:
        """Test analyze method."""
        source = "x = 1"
        tree = ast.parse(source)
        detector = ConcreteDetector(default_config, "test.py", source.split("\n"))

        issues = detector.analyze(tree)

        assert issues == []


class TestAnalyzerEdgeCases:
    """Additional analyzer edge-case coverage."""

    def test_file_exceeds_max_size(
        self, default_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test analysis rejects files larger than the configured limit."""
        from pyrefactor import analyzer as analyzer_module

        large_file = tmp_path / "large.py"
        large_file.write_bytes(b"x = 1\n")
        monkeypatch.setattr(analyzer_module, "MAX_FILE_BYTES", 1)

        analysis = Analyzer(default_config).analyze_file(large_file)

        assert analysis.parse_error is not None
        assert "maximum size" in analysis.parse_error

    def test_exclusion_by_basename_pattern(self, tmp_path: Path) -> None:
        """Test exclusion patterns match file basenames."""
        config = Config()
        config.exclude_patterns = ["skip_*.py"]
        target = tmp_path / "skip_me.py"
        target.write_text("x = 1\n", encoding="utf-8")

        result = Analyzer(config).analyze_files([target])

        assert result.file_analyses == []

    def test_detector_failure_isolated(
        self, default_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test detector exceptions do not abort analysis."""
        from pyrefactor.detectors import complexity as complexity_module

        target = tmp_path / "sample.py"
        target.write_text("x = 1\n", encoding="utf-8")

        def _boom(_self: object, _tree: object) -> list[object]:
            raise AttributeError("detector failed")

        monkeypatch.setattr(
            complexity_module.ComplexityDetector,
            "analyze",
            _boom,
        )

        analysis = Analyzer(default_config).analyze_file(target)

        assert analysis.parse_error is None
        assert analysis.issues == []
        assert len(analysis.warnings) == 1
        assert "complexity failed" in analysis.warnings[0]

    def test_parallel_future_failure(
        self, default_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test thread pool failures are recorded as parse errors."""
        first = tmp_path / "first.py"
        second = tmp_path / "second.py"
        first.write_text("x = 1\n", encoding="utf-8")
        second.write_text("y = 2\n", encoding="utf-8")

        with patch.object(
            Analyzer,
            "analyze_file",
            side_effect=AttributeError("worker failed"),
        ):
            result = Analyzer(default_config).analyze_files(
                [first, second], max_workers=2
            )

        assert len(result.file_analyses) == 2
        assert all(
            analysis.parse_error == "Analysis failed: worker failed"
            for analysis in result.file_analyses
        )

    def test_symlink_outside_tree_not_followed(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test directory symlinks outside the tree are not traversed."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        inside_file = project_dir / "main.py"
        inside_file.write_text("x = 1\n", encoding="utf-8")

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        outside_file = outside_dir / "secret.py"
        outside_file.write_text("y = 2\n", encoding="utf-8")

        link_dir = project_dir / "linked_out"
        try:
            link_dir.symlink_to(outside_dir, target_is_directory=True)
        except OSError:
            pytest.skip("Platform does not support directory symlinks")

        result = Analyzer(default_config).analyze_directory(project_dir)
        analyzed_paths = {analysis.file_path for analysis in result.file_analyses}

        assert str(inside_file) in analyzed_paths
        assert str(outside_file) not in analyzed_paths

    def test_unexpected_analysis_error_is_recorded(
        self, default_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test unexpected errors during analysis are captured as parse errors."""
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n", encoding="utf-8")

        def _raise_unexpected(
            _self: Analyzer, _path: str, _lines: list[str]
        ) -> list[BaseDetector]:
            raise KeyError("unexpected")

        monkeypatch.setattr(Analyzer, "_create_detectors", _raise_unexpected)

        analysis = Analyzer(default_config).analyze_file(target)

        assert analysis.parse_error == "Error analyzing file: unexpected error"
        assert analysis.issues == []

    def test_parallel_unexpected_analysis_error_is_recorded(
        self, default_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test unexpected parallel worker failures are recorded."""
        first = tmp_path / "first.py"
        second = tmp_path / "second.py"
        first.write_text("x = 1\n", encoding="utf-8")
        second.write_text("y = 2\n", encoding="utf-8")

        def _raise_unexpected(_self: Analyzer, _path: Path) -> object:
            raise RuntimeError("worker boom")

        monkeypatch.setattr(Analyzer, "analyze_file", _raise_unexpected)

        result = Analyzer(default_config).analyze_files([first, second], max_workers=2)

        assert len(result.file_analyses) == 2
        assert all(
            analysis.parse_error == "Analysis failed: unexpected error"
            for analysis in result.file_analyses
        )

    def test_parallel_results_sorted_by_path(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test parallel analysis returns results sorted by file path."""
        files = []
        for name in ("c.py", "a.py", "b.py"):
            path = tmp_path / name
            path.write_text("x = 1\n", encoding="utf-8")
            files.append(path)

        result = Analyzer(default_config).analyze_files(files, max_workers=4)
        paths = [analysis.file_path for analysis in result.file_analyses]

        assert paths == sorted(paths)

    def test_detector_keyerror_isolated(
        self, default_config: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test KeyError in a detector becomes a warning, not a parse error."""
        from pyrefactor.detectors import complexity as complexity_module

        target = tmp_path / "sample.py"
        target.write_text("x = 1\n", encoding="utf-8")

        def _boom(_self: object, _tree: object) -> list[object]:
            raise KeyError("missing key")

        monkeypatch.setattr(
            complexity_module.ComplexityDetector,
            "analyze",
            _boom,
        )

        analysis = Analyzer(default_config).analyze_file(target)

        assert analysis.parse_error is None
        assert len(analysis.warnings) == 1
        assert "complexity failed" in analysis.warnings[0]

    def test_analyze_directory_missing_path(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test analyze_directory on missing path returns empty result."""
        missing = tmp_path / "missing"
        result = Analyzer(default_config).analyze_directory(missing)

        assert result.file_analyses == []

    def test_analyze_directory_file_path(
        self, default_config: Config, tmp_path: Path
    ) -> None:
        """Test analyze_directory delegates when given a file path."""
        target = tmp_path / "single.py"
        target.write_text("x = 1\n", encoding="utf-8")

        result = Analyzer(default_config).analyze_directory(target)

        assert len(result.file_analyses) == 1
        assert result.file_analyses[0].file_path == str(target)
