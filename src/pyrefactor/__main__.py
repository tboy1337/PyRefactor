"""CLI entry point for PyRefactor."""

import argparse
import logging
import sys
from pathlib import Path

from .analyzer import Analyzer
from .config import Config
from .models import AnalysisResult, Severity
from .reporter import ConsoleReporter

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class Args:
    """Type-safe argument namespace."""

    paths: list[Path]
    config: Path | None
    group_by: str
    min_severity: str
    jobs: int
    verbose: bool
    version: bool


def parse_arguments() -> Args:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="PyRefactor - A Python refactoring and optimization linter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pyrefactor myfile.py              Analyze a single file
  pyrefactor src/                   Analyze all Python files in directory
  pyrefactor file1.py file2.py      Analyze multiple files
  pyrefactor --config custom.toml . Analyze with custom config

Exit Codes:
  0 - No issues or only INFO/LOW severity issues
  1 - MEDIUM or HIGH severity issues found
  2 - Error during analysis
        """,
    )

    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Python files or directories to analyze",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to configuration file (default: pyproject.toml)",
    )

    parser.add_argument(
        "-g",
        "--group-by",
        choices=["file", "severity"],
        default="file",
        help="Group output by file or severity (default: file)",
    )

    parser.add_argument(
        "--min-severity",
        choices=["info", "low", "medium", "high"],
        default="info",
        help="Minimum severity level to report (default: info)",
    )

    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=4,
        help="Number of parallel jobs (default: 4)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    namespace = parser.parse_args()
    # Convert to our typed class
    args = Args()
    args.paths = namespace.paths
    args.config = namespace.config
    args.group_by = namespace.group_by
    args.min_severity = namespace.min_severity
    args.jobs = namespace.jobs
    args.verbose = namespace.verbose
    args.version = namespace.version
    return args


def _handle_version(args: Args) -> int | None:
    """Handle version flag. Returns exit code if version flag is set, None otherwise."""
    if args.version:
        version = "1.0.0"
        print(f"PyRefactor version {version}")
        return 0
    return None


def _configure_logging(args: Args) -> None:
    """Configure logging based on command line arguments."""
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)


def _load_config(args: Args) -> Config | None:
    """Load configuration. Returns Config or None on error."""
    try:
        config = Config.load(args.config)
        logger.info("Loaded configuration: %s", config)
        return config
    except Exception as e:
        logger.error("Error loading configuration: %s", e)
        return None


def _validate_paths(args: Args) -> list[Path] | None:
    """Validate paths from arguments. Returns list of paths or None on error."""
    paths: list[Path] = []
    for path in args.paths:
        if not path.exists():
            logger.error("Path does not exist: %s", path)
            return None
        paths.append(path)
    return paths


def _analyze_files_safely(
    analyzer: Analyzer, paths: list[Path]
) -> AnalysisResult | None:
    """Analyze files and handle errors. Returns result or None on error."""
    try:
        logger.info("Analyzing %d path(s)...", len(paths))
        return analyzer.analyze_files(paths)
    except Exception as e:
        logger.error("Error during analysis: %s", e)
        return None


def _get_min_severity(severity_str: str) -> Severity:
    """Get Severity enum from string."""
    severity_map: dict[str, Severity] = {
        "info": Severity.INFO,
        "low": Severity.LOW,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
    }
    return severity_map[severity_str]


def _filter_by_severity(result: AnalysisResult, min_severity: Severity) -> None:
    """Filter issues by minimum severity in-place."""
    for file_analysis in result.file_analyses:
        file_analysis.issues = [
            issue for issue in file_analysis.issues if issue.severity >= min_severity
        ]


def _has_critical_issues(result: AnalysisResult) -> bool:
    """Check if result has HIGH or MEDIUM severity issues."""
    return any(
        issue.severity in (Severity.HIGH, Severity.MEDIUM)
        for issue in result.get_all_issues()
    )


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Handle version
    version_exit = _handle_version(args)
    if version_exit is not None:
        return version_exit

    # Check if paths were provided
    if not args.paths:
        logger.error("No paths provided")
        return 2

    # Configure logging
    _configure_logging(args)

    # Load configuration
    config = _load_config(args)
    if config is None:
        return 2

    # Validate paths
    paths = _validate_paths(args)
    if paths is None:
        return 2

    # Create analyzer and analyze files
    analyzer = Analyzer(config)
    result = _analyze_files_safely(analyzer, paths)
    if result is None:
        return 2

    # Filter by minimum severity
    min_severity = _get_min_severity(args.min_severity)
    _filter_by_severity(result, min_severity)

    # Report results
    reporter = ConsoleReporter()
    reporter.report(result, group_by=args.group_by)

    # Determine exit code
    return 1 if _has_critical_issues(result) else 0


if __name__ == "__main__":
    sys.exit(main())
