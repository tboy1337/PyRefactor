"""Tests for CLI."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from pyrefactor.__main__ import (
    _determine_exit_code,
    _has_parse_errors,
    main,
    parse_arguments,
)
from pyrefactor.analyzer import Analyzer
from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity


class TestCLI:
    """Tests for CLI interface."""

    def test_parse_arguments_single_file(self) -> None:
        """Test parsing single file argument."""
        with patch.object(sys, "argv", ["pyrefactor", "test.py"]):
            args = parse_arguments()

            assert len(args.paths) == 1
            assert args.paths[0] == Path("test.py")

    def test_parse_arguments_multiple_files(self) -> None:
        """Test parsing multiple file arguments."""
        with patch.object(sys, "argv", ["pyrefactor", "file1.py", "file2.py"]):
            args = parse_arguments()

            assert len(args.paths) == 2

    def test_parse_arguments_directory(self) -> None:
        """Test parsing directory argument."""
        with patch.object(sys, "argv", ["pyrefactor", "src/"]):
            args = parse_arguments()

            assert len(args.paths) == 1
            assert args.paths[0] == Path("src/")

    def test_parse_arguments_with_config(self) -> None:
        """Test parsing with custom config."""
        with patch.object(
            sys, "argv", ["pyrefactor", "--config", "custom.toml", "test.py"]
        ):
            args = parse_arguments()

            assert args.config == Path("custom.toml")

    def test_parse_arguments_group_by(self) -> None:
        """Test parsing group-by option."""
        with patch.object(
            sys, "argv", ["pyrefactor", "--group-by", "severity", "test.py"]
        ):
            args = parse_arguments()

            assert args.group_by == "severity"

    def test_parse_arguments_min_severity(self) -> None:
        """Test parsing minimum severity option."""
        with patch.object(
            sys, "argv", ["pyrefactor", "--min-severity", "medium", "test.py"]
        ):
            args = parse_arguments()

            assert args.min_severity == "medium"

    def test_parse_arguments_verbose(self) -> None:
        """Test parsing verbose flag."""
        with patch.object(sys, "argv", ["pyrefactor", "-v", "test.py"]):
            args = parse_arguments()

            assert args.verbose is True

    def test_parse_arguments_jobs(self) -> None:
        """Test parsing jobs argument."""
        with patch.object(sys, "argv", ["pyrefactor", "-j", "8", "test.py"]):
            args = parse_arguments()

            assert args.jobs == 8

    def test_parse_arguments_fail_on_parse_errors(self) -> None:
        """Test parsing fail-on-parse-errors flag."""
        with patch.object(
            sys, "argv", ["pyrefactor", "--fail-on-parse-errors", "test.py"]
        ):
            args = parse_arguments()

            assert args.fail_on_parse_errors is True

    def test_module_entry_point_version(self) -> None:
        """Test pyrefactor module entry point via subprocess."""
        result = subprocess.run(
            [sys.executable, "-m", "pyrefactor", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0
        assert "PyRefactor version" in result.stdout


class TestCLIMain:
    """Tests for CLI main() execution."""

    def test_main_with_nonexistent_file(self) -> None:
        """Test main with nonexistent file."""
        with patch.object(sys, "argv", ["pyrefactor", "/nonexistent/file.py"]):
            exit_code = main()

            assert exit_code == 2

    def test_main_with_valid_file(self, temp_python_file: Path) -> None:
        """Test main with valid file."""
        with patch.object(sys, "argv", ["pyrefactor", str(temp_python_file)]):
            exit_code = main()

            # Should succeed with exit code 0 (no critical issues in simple file)
            assert exit_code == 0

    def test_main_with_issues(self, tmp_path: Path) -> None:
        """Test main with file containing issues."""
        file_path = tmp_path / "issues.py"
        code = "\n".join([f"    x = {i}" for i in range(60)])
        file_path.write_text(f"def long_func():\n{code}\n    return x")

        with patch.object(sys, "argv", ["pyrefactor", str(file_path)]):
            exit_code = main()

            # Should exit with code 1 (has MEDIUM severity issues)
            assert exit_code == 1

    def test_main_version(self) -> None:
        """Test version flag."""
        with patch.object(sys, "argv", ["pyrefactor", "--version"]):
            exit_code = main()

            assert exit_code == 0

    def test_main_with_directory(self, tmp_path: Path) -> None:
        """Test main with directory."""
        (tmp_path / "file1.py").write_text("def func(): pass")

        with patch.object(sys, "argv", ["pyrefactor", str(tmp_path)]):
            exit_code = main()

            assert exit_code == 0

    def test_main_with_min_severity_filter(self, tmp_path: Path) -> None:
        """Test main with minimum severity filter."""
        file_path = tmp_path / "test.py"
        file_path.write_text("if x == True:\n    pass")

        # With default settings, should show INFO issues
        with patch.object(sys, "argv", ["pyrefactor", str(file_path)]):
            exit_code = main()
            # Info issues don't cause non-zero exit
            assert exit_code == 0

        # With high minimum severity, should show nothing
        with patch.object(
            sys,
            "argv",
            ["pyrefactor", "--min-severity", "high", str(file_path)],
        ):
            exit_code = main()
            assert exit_code == 0

    def test_main_does_not_mutate_analysis_result(self, tmp_path: Path) -> None:
        """Test main leaves the original AnalysisResult issue lists unchanged."""
        file_path = tmp_path / "test.py"
        file_path.write_text("if x == True:\n    pass")

        original_result = AnalysisResult()
        file_analysis = FileAnalysis(file_path=str(file_path))
        file_analysis.add_issue(
            Issue(
                file=str(file_path),
                line=1,
                column=0,
                severity=Severity.INFO,
                rule_id="R011",
                message="info issue",
            )
        )
        file_analysis.add_issue(
            Issue(
                file=str(file_path),
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="C004",
                message="high issue",
            )
        )
        original_result.add_file_analysis(file_analysis)

        with patch.object(
            sys, "argv", ["pyrefactor", "--min-severity", "high", str(file_path)]
        ):
            with patch.object(Analyzer, "analyze_files", return_value=original_result):
                exit_code = main()

        assert exit_code == 1
        assert original_result.total_issues() == 2
        assert len(original_result.file_analyses[0].issues) == 2

    def test_main_with_missing_config(self, tmp_path: Path) -> None:
        """Test main exits with error when explicit config file is missing."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        missing_config = tmp_path / "missing.toml"

        with patch.object(
            sys,
            "argv",
            ["pyrefactor", "--config", str(missing_config), str(file_path)],
        ):
            exit_code = main()

            assert exit_code == 2

    def test_main_passes_jobs_to_analyzer(self, tmp_path: Path) -> None:
        """Test main forwards --jobs to Analyzer.analyze_files."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        with patch.object(sys, "argv", ["pyrefactor", "-j", "6", str(file_path)]):
            with patch.object(Analyzer, "analyze_files") as mock_analyze:
                result = AnalysisResult()
                result.add_file_analysis(FileAnalysis(file_path=str(file_path)))
                mock_analyze.return_value = result
                exit_code = main()

            assert exit_code == 0
            mock_analyze.assert_called_once()
            assert mock_analyze.call_args.kwargs["max_workers"] == 6

    def test_main_subprocess_clean_file(self, tmp_path: Path) -> None:
        """Test subprocess analyze exits 0 for clean file."""
        file_path = tmp_path / "clean.py"
        file_path.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")

        result = subprocess.run(
            [sys.executable, "-m", "pyrefactor", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 0

    def test_main_subprocess_file_with_issues(self, tmp_path: Path) -> None:
        """Test subprocess analyze exits 1 when medium/high issues exist."""
        file_path = tmp_path / "issues.py"
        code = "\n".join([f"    x = {i}" for i in range(60)])
        file_path.write_text(f"def long_func():\n{code}\n    return x\n")

        result = subprocess.run(
            [sys.executable, "-m", "pyrefactor", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

        assert result.returncode == 1
        assert "C001" in result.stdout

    def test_main_with_invalid_config(self, tmp_path: Path) -> None:
        """Test main with invalid config file."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        config_file = tmp_path / "invalid.toml"
        config_file.write_text("[[[[invalid toml")

        with patch.object(
            sys, "argv", ["pyrefactor", "--config", str(config_file), str(file_path)]
        ):
            exit_code = main()

            assert exit_code == 2

    def test_main_with_invalid_config_verbose(self, tmp_path: Path) -> None:
        """Test main logs verbose traceback for invalid config."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        config_file = tmp_path / "invalid.toml"
        config_file.write_text("[[[[invalid toml")

        with patch.object(
            sys,
            "argv",
            [
                "pyrefactor",
                "--verbose",
                "--config",
                str(config_file),
                str(file_path),
            ],
        ):
            exit_code = main()

            assert exit_code == 2

    def test_main_analysis_exception_verbose(self, tmp_path: Path) -> None:
        """Test main logs verbose traceback when analysis raises."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        with patch.object(sys, "argv", ["pyrefactor", "--verbose", str(file_path)]):
            with patch.object(
                Analyzer,
                "analyze_files",
                side_effect=RuntimeError("analysis failed"),
            ):
                exit_code = main()

            assert exit_code == 2

    def test_main_analysis_exception_non_verbose(self, tmp_path: Path) -> None:
        """Test main handles analysis errors without verbose logging."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        with patch.object(sys, "argv", ["pyrefactor", str(file_path)]):
            with patch.object(
                Analyzer,
                "analyze_files",
                side_effect=RuntimeError("analysis failed"),
            ):
                exit_code = main()

            assert exit_code == 2

    def test_main_with_analysis_error(self, tmp_path: Path) -> None:
        """Test main with analysis error."""
        file_path = tmp_path / "test.py"
        # Create a file with invalid Python syntax
        file_path.write_text("def func(:\n    pass")

        with patch.object(sys, "argv", ["pyrefactor", str(file_path)]):
            exit_code = main()

            # Syntax errors are handled gracefully without crashing
            assert exit_code == 0

    def test_main_with_syntax_error_and_fail_on_parse_errors(
        self, tmp_path: Path
    ) -> None:
        """Test --fail-on-parse-errors exits with code 1 for syntax errors."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(:\n    pass")

        with patch.object(
            sys, "argv", ["pyrefactor", "--fail-on-parse-errors", str(file_path)]
        ):
            exit_code = main()

            assert exit_code == 1

    def test_main_with_non_python_file(self, tmp_path: Path) -> None:
        """Test main exits with error when given a non-Python file."""
        text_file = tmp_path / "readme.txt"
        text_file.write_text("not python")

        with patch.object(sys, "argv", ["pyrefactor", str(text_file)]):
            exit_code = main()

            assert exit_code == 2

    def test_main_with_empty_directory(self, tmp_path: Path) -> None:
        """Test main exits with error when directory has no Python files."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch.object(sys, "argv", ["pyrefactor", str(empty_dir)]):
            exit_code = main()

            assert exit_code == 2

    def test_main_no_paths(self) -> None:
        """Test main exits with error when no paths are provided."""
        with patch.object(sys, "argv", ["pyrefactor"]):
            exit_code = main()

            assert exit_code == 2

    def test_main_with_verbose_flag(self, tmp_path: Path) -> None:
        """Test main with verbose flag."""
        file_path = tmp_path / "test.py"
        file_path.write_text("def func(): pass")

        with patch.object(sys, "argv", ["pyrefactor", "--verbose", str(file_path)]):
            exit_code = main()

            assert exit_code == 0

    def test_main_subprocess_group_by_severity(self, tmp_path: Path) -> None:
        """Test subprocess output groups issues by severity."""
        file_path = tmp_path / "issues.py"
        file_path.write_text("f = open('data.txt')\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pyrefactor",
                str(file_path),
                "--group-by",
                "severity",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 1
        assert "HIGH Severity Issues" in result.stdout

    def test_main_subprocess_jobs_zero_clamps_to_one(self, tmp_path: Path) -> None:
        """Test -j 0 is clamped to one worker and still analyzes files."""
        file_path = tmp_path / "clean.py"
        file_path.write_text("x = 1\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "pyrefactor", "-j", "0", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "Files analyzed: 1" in result.stdout
        assert "--jobs must be at least 1" in result.stderr

    def test_main_subprocess_pyproject_disables_detector(self, tmp_path: Path) -> None:
        """Test CLI discovers pyproject.toml and honors disabled detectors."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.pyrefactor.context_manager]
enabled = false
""".strip() + "\n",
            encoding="utf-8",
        )
        file_path = tmp_path / "resource.py"
        file_path.write_text("f = open('data.txt')\n", encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "pyrefactor", str(file_path)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "R001" not in result.stdout
        assert "Files analyzed: 1" in result.stdout

    def test_main_subprocess_min_severity_medium(self, tmp_path: Path) -> None:
        """Test --min-severity medium filters low/info from exit code."""
        file_path = tmp_path / "low_only.py"
        file_path.write_text(
            "items = [1, 2, 3]\nfor i in range(len(items)):\n    print(items[i])\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pyrefactor",
                str(file_path),
                "--min-severity",
                "medium",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0


class TestCLIExitCodeHelpers:
    """Tests for CLI exit-code helper functions."""

    def test_has_parse_errors_true(self) -> None:
        """Test parse-error detection when a file failed to parse."""
        result = AnalysisResult()
        result.add_file_analysis(
            FileAnalysis(file_path="broken.py", parse_error="Syntax error")
        )

        assert _has_parse_errors(result) is True

    def test_has_parse_errors_false(self) -> None:
        """Test parse-error detection when all files parsed."""
        result = AnalysisResult()
        result.add_file_analysis(FileAnalysis(file_path="ok.py"))

        assert _has_parse_errors(result) is False

    def test_determine_exit_code_parse_errors_flag(self) -> None:
        """Test fail-on-parse-errors affects exit code without critical issues."""
        result = AnalysisResult()
        result.add_file_analysis(
            FileAnalysis(file_path="broken.py", parse_error="Syntax error")
        )

        assert _determine_exit_code(result, fail_on_parse_errors=False) == 0
        assert _determine_exit_code(result, fail_on_parse_errors=True) == 1

    def test_determine_exit_code_critical_issues(self) -> None:
        """Test critical issues always return exit code 1."""
        result = AnalysisResult()
        analysis = FileAnalysis(file_path="test.py")
        analysis.add_issue(
            Issue(
                file="test.py",
                line=1,
                column=0,
                severity=Severity.HIGH,
                rule_id="C001",
                message="Issue",
            )
        )
        result.add_file_analysis(analysis)

        assert _determine_exit_code(result, fail_on_parse_errors=False) == 1
        assert _determine_exit_code(result, fail_on_parse_errors=True) == 1
