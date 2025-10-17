"""Main analyzer orchestrator for PyRefactor."""

import ast
import concurrent.futures
import logging
from pathlib import Path

from .ast_visitor import BaseDetector
from .config import Config
from .detectors import (
    BooleanLogicDetector,
    ComplexityDetector,
    DuplicationDetector,
    LoopsDetector,
    PerformanceDetector,
)
from .models import AnalysisResult, FileAnalysis

logger = logging.getLogger(__name__)


class Analyzer:
    """Main analyzer that orchestrates all detectors."""

    def __init__(self, config: Config) -> None:
        """Initialize analyzer with configuration."""
        self.config = config

    def _create_detectors(
        self, file_path: str, source_lines: list[str]
    ) -> list[BaseDetector]:
        """Create all enabled detectors for a file.

        Factory method to consolidate detector initialization and reduce duplication.
        """
        detectors: list[BaseDetector] = []

        # Complexity detector (always enabled)
        detectors.append(ComplexityDetector(self.config, file_path, source_lines))

        # Conditionally enabled detectors
        detector_configs = [
            (self.config.performance.enabled, PerformanceDetector),
            (self.config.boolean_logic.enabled, BooleanLogicDetector),
            (self.config.loops.enabled, LoopsDetector),
            (self.config.duplication.enabled, DuplicationDetector),
        ]

        for enabled, detector_class in detector_configs:
            if enabled:
                detectors.append(detector_class(self.config, file_path, source_lines))

        return detectors

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single Python file."""
        analysis = FileAnalysis(file_path=str(file_path))

        try:
            # Read the file
            source_code = file_path.read_text(encoding="utf-8")
            source_lines = source_code.splitlines()
            analysis.lines_of_code = len(source_lines)

            # Parse the AST
            try:
                tree = ast.parse(source_code, filename=str(file_path))
            except SyntaxError as e:
                analysis.parse_error = f"Syntax error: {e}"
                return analysis

            # Create and run all enabled detectors
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

        # Find all Python files
        python_files = list(directory.rglob("*.py"))

        # Filter excluded patterns
        python_files = self._filter_excluded_files(python_files)

        if not python_files:
            logger.warning("No Python files found in %s", directory)
            return result

        # Analyze files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
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

    def analyze_files(self, file_paths: list[Path]) -> AnalysisResult:
        """Analyze a list of Python files."""
        result = AnalysisResult()

        for file_path in file_paths:
            if file_path.is_file():
                analysis = self.analyze_file(file_path)
                result.add_file_analysis(analysis)
            elif file_path.is_dir():
                dir_result = self.analyze_directory(file_path)
                for analysis in dir_result.file_analyses:
                    result.add_file_analysis(analysis)

        return result

    def _filter_excluded_files(self, files: list[Path]) -> list[Path]:
        """Filter out files matching exclusion patterns."""
        if not self.config.exclude_patterns:
            return files

        return [
            file_path
            for file_path in files
            if not any(
                pattern in str(file_path) for pattern in self.config.exclude_patterns
            )
        ]
