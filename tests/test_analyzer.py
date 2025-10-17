"""Tests for analyzer."""

from pathlib import Path

from pyrefactor.analyzer import Analyzer
from pyrefactor.config import Config


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
        config.exclude_patterns = ["test_", "__pycache__"]

        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "test_file.py").write_text("def test(): pass")

        analyzer = Analyzer(config)
        result = analyzer.analyze_directory(tmp_path)

        # Should only analyze main.py, not test_file.py
        assert result.files_analyzed() == 1
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
