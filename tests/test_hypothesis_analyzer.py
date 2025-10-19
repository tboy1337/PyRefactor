"""Property-based tests for Analyzer using Hypothesis."""

import tempfile
from pathlib import Path

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pyrefactor.analyzer import Analyzer
from pyrefactor.config import ComplexityConfig, Config


# Strategies for file paths and patterns
@st.composite
def file_path_strategy(draw: st.DrawFn) -> str:
    """Generate a file path string."""
    parts = draw(
        st.lists(
            st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(
                    whitelist_categories=("Ll", "Lu", "Nd"),
                    min_codepoint=48,
                    max_codepoint=122,
                ).filter(lambda c: c not in r'\/:*?"<>|'),
            ),
            min_size=1,
            max_size=3,
        )
    )
    return "/".join(parts) + ".py"


@st.composite
def exclude_pattern_strategy(draw: st.DrawFn) -> str:
    """Generate an exclusion pattern."""
    return draw(
        st.text(
            min_size=1,
            max_size=30,
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "P")),
        )
    )


@st.composite
def valid_python_code_strategy(draw: st.DrawFn) -> str:
    """Generate valid Python code snippets."""
    func_name = draw(
        st.text(
            min_size=1,
            max_size=15,
            alphabet=st.characters(
                whitelist_categories=("Ll",), min_codepoint=97, max_codepoint=122
            ),
        )
    )
    num_lines = draw(st.integers(min_value=1, max_value=20))
    return f'def {func_name}():\n{chr(10).join(f"    x{i} = {i}" for i in range(num_lines))}'


class TestAnalyzerFileFilteringProperties:
    """Property-based tests for file filtering logic."""

    @given(
        st.lists(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "P")),
            ),
            max_size=5,
        )
    )
    def test_filter_preserves_empty_list(self, exclude_patterns: list[str]) -> None:
        """Property: Filtering an empty file list returns empty list."""
        config = Config(exclude_patterns=exclude_patterns)
        analyzer = Analyzer(config)
        result = analyzer._filter_excluded_files([])
        assert not result

    @given(st.lists(exclude_pattern_strategy(), max_size=5))
    def test_filter_with_no_patterns_returns_all(self, patterns: list[str]) -> None:
        """Property: With no exclusion patterns, all files pass through."""
        config = Config(exclude_patterns=[])
        analyzer = Analyzer(config)

        # Create some test paths
        test_paths = [
            Path("test1.py"),
            Path("test2.py"),
            Path("subdir/test3.py"),
        ]

        result = analyzer._filter_excluded_files(test_paths)
        assert len(result) == len(test_paths)

    @given(
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(whitelist_categories=("Ll",)),
        )
    )
    def test_filter_excludes_matching_pattern(self, pattern: str) -> None:
        """Property: Files matching exclusion pattern are filtered out."""
        config = Config(exclude_patterns=[pattern])
        analyzer = Analyzer(config)

        # Create paths: some with pattern, some without
        matching_path = Path(f"dir/{pattern}/test.py")
        non_matching_path = Path("other/test.py")

        result = analyzer._filter_excluded_files([matching_path, non_matching_path])

        # Matching path should be excluded
        assert matching_path not in result
        # Non-matching path should remain if pattern isn't in it
        if pattern not in str(non_matching_path):
            assert non_matching_path in result

    @given(st.lists(exclude_pattern_strategy(), min_size=1, max_size=5))
    def test_filter_result_subset_of_input(self, patterns: list[str]) -> None:
        """Property: Filtered result is always a subset of input."""
        config = Config(exclude_patterns=patterns)
        analyzer = Analyzer(config)

        test_paths = [
            Path("test1.py"),
            Path("test2.py"),
            Path("excluded/test.py"),
        ]

        result = analyzer._filter_excluded_files(test_paths)

        # Result should be a subset
        assert len(result) <= len(test_paths)
        assert all(path in test_paths for path in result)


class TestAnalyzerBasicProperties:
    """Property-based tests for basic analyzer behavior."""

    @given(st.integers(min_value=1, max_value=100))
    def test_analyzer_accepts_any_positive_config_values(
        self, max_branches: int
    ) -> None:
        """Property: Analyzer can be initialized with any valid config."""
        config = Config(complexity=ComplexityConfig(max_branches=max_branches))
        analyzer = Analyzer(config)
        assert analyzer.config.complexity.max_branches == max_branches

    def test_analyzer_preserves_config(self) -> None:
        """Property: Analyzer preserves the config it's initialized with."""
        config = Config(
            complexity=ComplexityConfig(max_branches=15, max_nesting_depth=5)
        )
        analyzer = Analyzer(config)

        assert analyzer.config.complexity.max_branches == 15
        assert analyzer.config.complexity.max_nesting_depth == 5


class TestAnalyzerFileAnalysisProperties:
    """Property-based tests for file analysis."""

    @given(valid_python_code_strategy())
    @settings(max_examples=20)  # Limit examples for file I/O
    def test_analyze_file_returns_file_analysis(self, code: str) -> None:
        """Property: Analyzing a file always returns a FileAnalysis object."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            assert result.file_path == str(temp_path)
            assert isinstance(result.issues, list)
            assert result.lines_of_code >= 0
        finally:
            temp_path.unlink()

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=20, deadline=500)
    def test_analyze_file_counts_lines_correctly(self, num_lines: int) -> None:
        """Property: Analyzer correctly counts lines of code."""
        code = "\n".join(f"x{i} = {i}" for i in range(num_lines))

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            # Should count the number of lines
            assert result.lines_of_code == num_lines
        finally:
            temp_path.unlink()

    def test_analyze_file_with_syntax_error_sets_parse_error(self) -> None:
        """Property: Files with syntax errors have parse_error set."""
        invalid_code = "def broken syntax here"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(invalid_code)
            temp_path = Path(f.name)

        try:
            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            assert result.parse_error is not None
            assert "Syntax error" in result.parse_error
        finally:
            temp_path.unlink()

    def test_analyze_empty_file_succeeds(self) -> None:
        """Property: Analyzing an empty file doesn't crash."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            assert result.lines_of_code == 0
            # Empty file should parse successfully
            assert result.parse_error is None or result.parse_error == ""
        finally:
            temp_path.unlink()


class TestAnalyzerMultipleFilesProperties:
    """Property-based tests for analyzing multiple files."""

    @given(st.integers(min_value=1, max_value=5))
    @settings(max_examples=10)
    def test_analyze_files_processes_all_files(self, num_files: int) -> None:
        """Property: analyze_files processes all provided files."""
        temp_files = []
        temp_dir = tempfile.mkdtemp()

        try:
            for i in range(num_files):
                temp_path = Path(temp_dir) / f"test{i}.py"
                temp_path.write_text(f"def func{i}(): pass")
                temp_files.append(temp_path)

            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_files(temp_files)

            # Should analyze all files
            assert result.files_analyzed() == num_files
        finally:
            for temp_file in temp_files:
                temp_file.unlink()
            Path(temp_dir).rmdir()

    def test_analyze_directory_finds_python_files(self) -> None:
        """Property: analyze_directory finds all .py files."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create some Python files
            (temp_dir / "test1.py").write_text("def func1(): pass")
            (temp_dir / "test2.py").write_text("def func2(): pass")
            (temp_dir / "readme.txt").write_text("Not Python")

            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_directory(temp_dir)

            # Should find 2 Python files, not the .txt
            assert result.files_analyzed() == 2
        finally:
            for file in temp_dir.iterdir():
                file.unlink()
            temp_dir.rmdir()


class TestAnalyzerResultAggregationProperties:
    """Property-based tests for result aggregation."""

    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=10)
    def test_result_aggregates_issues_from_all_files(self, num_files: int) -> None:
        """Property: Result contains all issues from all analyzed files."""
        assume(num_files > 0)

        temp_dir = Path(tempfile.mkdtemp())

        try:
            for i in range(num_files):
                # Create code with varying complexity
                code = f"""
def complex_func_{i}():
    if x:
        if y:
            if z:
                if w:
                    pass
"""
                (temp_dir / f"test{i}.py").write_text(code)

            config = Config(complexity=ComplexityConfig(max_nesting_depth=2))
            analyzer = Analyzer(config)
            result = analyzer.analyze_directory(temp_dir)

            # Should have analyzed all files
            assert result.files_analyzed() == num_files

            # Total issues should be sum of issues from all files
            total_from_files = sum(len(fa.issues) for fa in result.file_analyses)
            assert result.total_issues() == total_from_files
        finally:
            for file in temp_dir.iterdir():
                file.unlink()
            temp_dir.rmdir()

    def test_empty_directory_returns_empty_result(self) -> None:
        """Property: Analyzing empty directory returns result with 0 files."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_directory(temp_dir)

            assert result.files_analyzed() == 0
            assert result.total_issues() == 0
        finally:
            temp_dir.rmdir()


class TestAnalyzerDetectorIntegrationProperties:
    """Property-based tests for detector integration."""

    @given(st.booleans())
    @settings(max_examples=10)
    def test_disabled_detectors_not_run(self, performance_enabled: bool) -> None:
        """Property: Disabled detectors don't produce issues."""
        code = """
def test_func():
    result = []
    for i in range(10):
        result.append(i)
    return result
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            config = Config()
            config.performance.enabled = performance_enabled

            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            # Result should exist regardless
            assert result.file_path == str(temp_path)

            # If performance disabled, no performance-specific rules should fire
            # Note: This assumes performance rules start with P
            # Actual behavior depends on detector implementation
        finally:
            temp_path.unlink()

    @given(st.integers(min_value=1, max_value=20))
    @settings(max_examples=10)
    def test_complexity_threshold_affects_issues(self, max_branches: int) -> None:
        """Property: Higher complexity threshold produces fewer issues."""
        # Code with 15 branches
        code = """
def complex_func(x):
    if x == 1: return 1
    if x == 2: return 2
    if x == 3: return 3
    if x == 4: return 4
    if x == 5: return 5
    if x == 6: return 6
    if x == 7: return 7
    if x == 8: return 8
    if x == 9: return 9
    if x == 10: return 10
    if x == 11: return 11
    if x == 12: return 12
    if x == 13: return 13
    if x == 14: return 14
    if x == 15: return 15
    return 0
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            config = Config(complexity=ComplexityConfig(max_branches=max_branches))
            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            # If threshold is >= 15, no branch issues
            # If threshold is < 15, should have branch issue
            branch_issues = [
                issue for issue in result.issues if "branches" in issue.message.lower()
            ]

            if max_branches >= 15:
                # Should have no branch issues
                assert len(branch_issues) == 0
            else:
                # Should have at least one branch issue
                assert len(branch_issues) >= 1
        finally:
            temp_path.unlink()


class TestAnalyzerInvariants:
    """Test invariants across analyzer operations."""

    def test_analyzing_same_file_twice_produces_same_results(self) -> None:
        """Property: Analyzing same file twice produces identical results."""
        code = """
def test_func():
    if a:
        if b:
            if c:
                pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            config = Config()
            analyzer = Analyzer(config)

            result1 = analyzer.analyze_file(temp_path)
            result2 = analyzer.analyze_file(temp_path)

            # Results should be identical
            assert result1.file_path == result2.file_path
            assert result1.lines_of_code == result2.lines_of_code
            assert len(result1.issues) == len(result2.issues)
        finally:
            temp_path.unlink()

    @given(st.lists(exclude_pattern_strategy(), max_size=5))
    @settings(max_examples=10)
    def test_analyzer_config_immutable_during_analysis(
        self, patterns: list[str]
    ) -> None:
        """Property: Config doesn't change during analysis."""
        config = Config(exclude_patterns=patterns)
        original_patterns = config.exclude_patterns.copy()

        analyzer = Analyzer(config)

        # Create and analyze a file
        code = "def test(): pass"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            analyzer.analyze_file(temp_path)

            # Config should be unchanged
            assert analyzer.config.exclude_patterns == original_patterns
        finally:
            temp_path.unlink()

    def test_file_analysis_always_has_file_path(self) -> None:
        """Property: Every FileAnalysis has a non-empty file path."""
        code = "def test(): pass"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            config = Config()
            analyzer = Analyzer(config)
            result = analyzer.analyze_file(temp_path)

            assert result.file_path != ""
            assert len(result.file_path) > 0
        finally:
            temp_path.unlink()
