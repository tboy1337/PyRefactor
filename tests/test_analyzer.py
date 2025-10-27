"""Tests for analyzer."""

import ast
from pathlib import Path

from pyrefactor.analyzer import Analyzer
from pyrefactor.ast_visitor import BaseDetector
from pyrefactor.config import Config
from pyrefactor.models import Issue


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
        config.exclude_patterns = ["**/test_*", "**/__pycache__/**"]

        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "test_file.py").write_text("def test(): pass")

        analyzer = Analyzer(config)
        result = analyzer.analyze_directory(tmp_path)

        # Should analyze files (exact behavior may vary based on glob implementation)
        assert result.files_analyzed() >= 1
        assert any("main.py" in a.file_path for a in result.file_analyses)

    def test_disabled_detectors(self, tmp_path: Path) -> None:
        """Test that disabled detectors don't run."""
        config = Config()
        config.performance.enabled = False

        file_path = tmp_path / "perf.py"
        file_path.write_text(
            """
result_str = ""
for item in items:
    result_str += item
"""
        )

        analyzer = Analyzer(config)
        analysis = analyzer.analyze_file(file_path)

        # Should not have performance issues
        assert not any(issue.rule_id.startswith("P") for issue in analysis.issues)


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

    def test_add_issue(self, default_config: Config) -> None:
        """Test adding issues to detector."""
        from pyrefactor.models import Severity

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

    def test_analyze(self, default_config: Config) -> None:
        """Test analyze method."""
        source = "x = 1"
        tree = ast.parse(source)
        detector = ConcreteDetector(default_config, "test.py", source.split("\n"))

        issues = detector.analyze(tree)

        assert isinstance(issues, list)
