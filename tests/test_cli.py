"""Tests for CLI."""

import sys
from pathlib import Path
from unittest.mock import patch

from pyrefactor.__main__ import main, parse_arguments


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
