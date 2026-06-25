"""Main analyzer orchestrator for PyRefactor."""

import ast
import concurrent.futures
import fnmatch
import logging
import os
from pathlib import Path, PurePosixPath

from .ast_visitor import BaseDetector, build_parent_map
from .config import Config
from .detectors import (
    BooleanLogicDetector,
    ComparisonsDetector,
    ComplexityDetector,
    ContextManagerDetector,
    ControlFlowDetector,
    DictOperationsDetector,
    DuplicationDetector,
    LoopsDetector,
    PerformanceDetector,
)
from .models import AnalysisResult, FileAnalysis

logger = logging.getLogger(__name__)

# Maximum file size to read for analysis (10 MB)
MAX_FILE_BYTES = 10 * 1024 * 1024

_ANALYSIS_ERRORS = (
    OSError,
    RecursionError,
    MemoryError,
    ValueError,
    TypeError,
    AttributeError,
)


def _iter_python_files(root: Path) -> list[Path]:
    """Collect .py files under root without following directory symlinks."""
    python_files: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for filename in filenames:
            if filename.endswith(".py"):
                python_files.append(Path(dirpath) / filename)
    return python_files


def _path_matches_exclude_pattern(
    posix_path: PurePosixPath, posix_str: str, file_name: str, pattern: str
) -> bool:
    """Return True when a file path matches an exclude pattern."""
    normalized = pattern.replace("\\", "/")
    if posix_path.match(normalized):
        return True
    if fnmatch.fnmatch(posix_str, normalized):
        return True
    return fnmatch.fnmatch(file_name, normalized)


class Analyzer:
    """Main analyzer that orchestrates all detectors."""

    def __init__(self, config: Config) -> None:
        """Initialize analyzer with configuration."""
        self.config = config

    def _create_detectors(
        self, file_path: str, source_lines: list[str]
    ) -> list[BaseDetector]:
        """Create all enabled detectors for a file."""
        detectors: list[BaseDetector] = []

        if self.config.complexity.enabled:
            detectors.append(ComplexityDetector(self.config, file_path, source_lines))

        detector_configs = [
            (self.config.performance.enabled, PerformanceDetector),
            (self.config.boolean_logic.enabled, BooleanLogicDetector),
            (self.config.loops.enabled, LoopsDetector),
            (self.config.duplication.enabled, DuplicationDetector),
            (self.config.context_manager.enabled, ContextManagerDetector),
            (self.config.control_flow.enabled, ControlFlowDetector),
            (self.config.dict_operations.enabled, DictOperationsDetector),
            (self.config.comparisons.enabled, ComparisonsDetector),
        ]

        for enabled, detector_class in detector_configs:
            if enabled:
                detectors.append(detector_class(self.config, file_path, source_lines))

        return detectors

    def _read_source(self, file_path: Path) -> tuple[str, list[str]] | str:
        """Read source from a file, returning an error message on failure."""
        try:
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_BYTES:
                return (
                    f"File exceeds maximum size of {MAX_FILE_BYTES} bytes "
                    f"({file_size} bytes)"
                )

            source_code = file_path.read_text(encoding="utf-8")
            return source_code, source_code.splitlines()
        except UnicodeDecodeError:
            return "File is not valid UTF-8 text"
        except OSError as e:
            return f"Error reading file: {e}"

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single Python file."""
        analysis = FileAnalysis(file_path=str(file_path))

        try:
            read_result = self._read_source(file_path)
            if isinstance(read_result, str):
                analysis.parse_error = read_result
                return analysis

            source_code, source_lines = read_result
            analysis.lines_of_code = len(source_lines)

            try:
                tree = ast.parse(source_code, filename=str(file_path))
            except SyntaxError as e:
                analysis.parse_error = f"Syntax error: {e}"
                return analysis

            detectors = self._create_detectors(str(file_path), source_lines)
            self._run_detectors(detectors, tree, analysis, file_path)

        except _ANALYSIS_ERRORS as e:
            analysis.parse_error = f"Error analyzing file: {e}"
            logger.error("Error analyzing %s: %s", file_path, e)
        except Exception:
            analysis.parse_error = "Error analyzing file: unexpected error"
            logger.exception("Unexpected error analyzing %s", file_path)

        return analysis

    def _run_detectors(
        self,
        detectors: list[BaseDetector],
        tree: ast.Module,
        analysis: FileAnalysis,
        file_path: Path,
    ) -> None:
        """Run all detectors and collect issues."""
        parent_map = build_parent_map(tree)
        for detector in detectors:
            detector.shared_parent_map = parent_map
            try:
                issues = detector.analyze(tree)
                for issue in issues:
                    analysis.add_issue(issue)
                for warning in detector.analysis_warnings:
                    analysis.add_warning(warning)
            except (
                RecursionError,
                MemoryError,
                ValueError,
                TypeError,
                AttributeError,
            ) as e:
                detector_name = detector.get_detector_name()
                logger.error(
                    "Error running %s on %s: %s",
                    detector_name,
                    file_path,
                    e,
                )
                analysis.add_warning(f"Detector {detector_name} failed: {e}")
            except Exception as e:
                detector_name = detector.get_detector_name()
                logger.exception(
                    "Unexpected error running %s on %s",
                    detector_name,
                    file_path,
                )
                analysis.add_warning(f"Detector {detector_name} failed: {e}")

    def analyze_directory(
        self, directory: Path, max_workers: int = 4
    ) -> AnalysisResult:
        """Analyze all Python files in a directory."""
        result = AnalysisResult()

        if not directory.exists():
            logger.warning("Directory does not exist: %s", directory)
            return result

        if directory.is_file():
            logger.warning("Expected a directory but received a file: %s", directory)
            result.add_file_analysis(self.analyze_file(directory))
            return result

        python_files = _iter_python_files(directory)
        excluded_count = sum(1 for path in python_files if self._is_excluded(path))
        python_files = self._filter_excluded_files(python_files)
        result.excluded_file_count = excluded_count

        if not python_files:
            logger.warning("No Python files found in %s", directory)
            return result

        return self._analyze_paths_parallel(python_files, max_workers, result)

    def _collect_python_file(self, file_path: Path) -> tuple[Path | None, bool]:
        """Return a Python file path to analyze, or None if skipped.

        The bool is True when the file was excluded by configuration patterns.
        """
        if file_path.suffix != ".py":
            logger.warning("Skipping non-Python file: %s", file_path)
            return None, False
        if self._is_excluded(file_path):
            return None, True
        return file_path, False

    def _collect_directory_files(self, directory: Path) -> tuple[list[Path], int]:
        """Collect analyzable Python files from a directory.

        Returns the file list and the number of excluded files.
        """
        paths: list[Path] = []
        excluded_count = 0
        for path in _iter_python_files(directory):
            if self._is_excluded(path):
                excluded_count += 1
            else:
                paths.append(path)
        return paths, excluded_count

    def _collect_input_path(self, file_path: Path) -> tuple[list[Path], int]:
        """Collect analyzable paths from a single file or directory input."""
        if file_path.is_file():
            collected, excluded = self._collect_python_file(file_path)
            if excluded:
                return [], 1
            if collected is None:
                return [], 0
            return [collected], 0

        if file_path.is_dir():
            return self._collect_directory_files(file_path)

        logger.debug("Skipping path that is not a file or directory: %s", file_path)
        return [], 0

    def _collect_paths_to_analyze(
        self, file_paths: list[Path]
    ) -> tuple[list[Path], int]:
        """Expand files and directories into a flat list of Python files."""
        paths_to_analyze: list[Path] = []
        excluded_count = 0
        for file_path in file_paths:
            collected_paths, path_excluded = self._collect_input_path(file_path)
            paths_to_analyze.extend(collected_paths)
            excluded_count += path_excluded
        return paths_to_analyze, excluded_count

    def analyze_files(
        self, file_paths: list[Path], max_workers: int = 4
    ) -> AnalysisResult:
        """Analyze a list of Python files and directories."""
        result = AnalysisResult()
        paths_to_analyze, excluded_count = self._collect_paths_to_analyze(file_paths)
        result.excluded_file_count = excluded_count

        if not paths_to_analyze:
            return result

        return self._analyze_paths_parallel(paths_to_analyze, max_workers, result)

    def _analyze_paths_parallel(
        self,
        python_files: list[Path],
        max_workers: int,
        result: AnalysisResult,
    ) -> AnalysisResult:
        """Analyze multiple Python files in parallel."""
        workers = max(1, max_workers)

        if workers == 1 or len(python_files) == 1:
            for file_path in python_files:
                result.add_file_analysis(self.analyze_file(file_path))
            return result

        completed_analyses: list[FileAnalysis] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(self.analyze_file, file_path): file_path
                for file_path in python_files
            }

            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    completed_analyses.append(future.result())
                except _ANALYSIS_ERRORS as e:
                    logger.error("Error analyzing %s: %s", file_path, e)
                    completed_analyses.append(
                        FileAnalysis(
                            file_path=str(file_path),
                            parse_error=f"Analysis failed: {e}",
                        )
                    )
                except Exception:
                    logger.exception("Unexpected error analyzing %s", file_path)
                    completed_analyses.append(
                        FileAnalysis(
                            file_path=str(file_path),
                            parse_error="Analysis failed: unexpected error",
                        )
                    )

        completed_analyses.sort(key=lambda analysis: analysis.file_path)
        result.file_analyses.extend(completed_analyses)
        return result

    def _is_excluded(self, file_path: Path) -> bool:
        """Check if a file matches any exclusion pattern."""
        if not self.config.exclude_patterns:
            return False

        posix_path = PurePosixPath(file_path.as_posix())
        posix_str = posix_path.as_posix()
        file_name = file_path.name
        return any(
            _path_matches_exclude_pattern(posix_path, posix_str, file_name, pattern)
            for pattern in self.config.exclude_patterns
        )

    def _filter_excluded_files(self, files: list[Path]) -> list[Path]:
        """Filter out files matching exclusion patterns."""
        return [file_path for file_path in files if not self._is_excluded(file_path)]
