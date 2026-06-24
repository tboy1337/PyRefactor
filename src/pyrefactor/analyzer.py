"""Main analyzer orchestrator for PyRefactor."""

import ast
import concurrent.futures
import fnmatch
import logging
from pathlib import Path, PurePosixPath

from .ast_visitor import BaseDetector
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

        except Exception as e:
            analysis.parse_error = f"Error analyzing file: {e}"
            logger.error("Error analyzing %s: %s", file_path, e)

        return analysis

    def _run_detectors(
        self,
        detectors: list[BaseDetector],
        tree: ast.Module,
        analysis: FileAnalysis,
        file_path: Path,
    ) -> None:
        """Run all detectors and collect issues."""
        for detector in detectors:
            try:
                issues = detector.analyze(tree)
                for issue in issues:
                    analysis.add_issue(issue)
            except Exception as e:
                logger.error(
                    "Error running %s on %s: %s",
                    detector.get_detector_name(),
                    file_path,
                    e,
                )

    def analyze_directory(
        self, directory: Path, max_workers: int = 4
    ) -> AnalysisResult:
        """Analyze all Python files in a directory."""
        result = AnalysisResult()

        python_files = list(directory.rglob("*.py"))
        python_files = self._filter_excluded_files(python_files)

        if not python_files:
            logger.warning("No Python files found in %s", directory)
            return result

        return self._analyze_paths_parallel(python_files, max_workers, result)

    def analyze_files(
        self, file_paths: list[Path], max_workers: int = 4
    ) -> AnalysisResult:
        """Analyze a list of Python files and directories."""
        result = AnalysisResult()
        paths_to_analyze: list[Path] = []

        for file_path in file_paths:
            if file_path.is_file():
                if file_path.suffix != ".py":
                    logger.warning("Skipping non-Python file: %s", file_path)
                elif not self._is_excluded(file_path):
                    paths_to_analyze.append(file_path)
            elif file_path.is_dir():
                python_files = [
                    path
                    for path in file_path.rglob("*.py")
                    if not self._is_excluded(path)
                ]
                paths_to_analyze.extend(python_files)

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

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(self.analyze_file, file_path): file_path
                for file_path in python_files
            }

            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    analysis = future.result()
                    result.add_file_analysis(analysis)
                except Exception as e:
                    logger.error("Error analyzing %s: %s", file_path, e)
                    result.add_file_analysis(
                        FileAnalysis(
                            file_path=str(file_path),
                            parse_error=f"Analysis failed: {e}",
                        )
                    )

        return result

    def _is_excluded(self, file_path: Path) -> bool:
        """Check if a file matches any exclusion pattern."""
        if not self.config.exclude_patterns:
            return False

        posix_path = PurePosixPath(file_path.as_posix())
        for pattern in self.config.exclude_patterns:
            normalized = pattern.replace("\\", "/")
            if posix_path.match(normalized):
                return True
            if fnmatch.fnmatch(posix_path.as_posix(), normalized):
                return True
            if fnmatch.fnmatch(file_path.name, normalized):
                return True
        return False

    def _filter_excluded_files(self, files: list[Path]) -> list[Path]:
        """Filter out files matching exclusion patterns."""
        return [file_path for file_path in files if not self._is_excluded(file_path)]
