"""CLI entry point for PyRefactor."""

import argparse
import logging
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, cast

from . import __version__
from .analyzer import Analyzer
from .config import Config
from .models import AnalysisResult, Severity
from .reporter import ConsoleReporter

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Args:
    """Type-safe argument namespace."""

    paths: list[Path]
    config: Optional[Path]
    group_by: str
    min_severity: str
    jobs: int
    verbose: bool
    version: bool


# Class-level constant for severity mapping to avoid recreation
SEVERITY_MAP: dict[str, Severity] = {
    "info": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
}


SEVERITY_CHOICES: tuple[str, ...] = ("info", "low", "medium", "high")
GROUP_BY_CHOICES: tuple[str, ...] = ("file", "severity")


def _add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Add all arguments to the parser."""
    parser.add_argument(
        "paths", nargs="*", type=Path, help="Python files or directories to analyze"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help=(
            "Path to configuration file; when omitted, auto-discover "
            "pyproject.toml ([tool.pyrefactor]), then pyrefactor.ini, then defaults"
        ),
    )
    parser.add_argument(
        "-g",
        "--group-by",
        choices=GROUP_BY_CHOICES,
        default="file",
        help="Group output by file or severity (default: file)",
    )
    parser.add_argument(
        "--min-severity",
        choices=SEVERITY_CHOICES,
        default="info",
        help="Minimum severity level to report (default: info)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=4,
        help="Number of parallel jobs (default: 4, minimum 1)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
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
  0 - No MEDIUM/HIGH issues (INFO/LOW only, or parse errors reported without failing)
  1 - MEDIUM or HIGH severity issues found
  2 - Configuration, path, or orchestration error (invalid paths, no Python files)
        """,
    )
    _add_parser_arguments(parser)
    return parser


def parse_arguments() -> Args:
    """Parse command line arguments."""
    parser = _create_argument_parser()
    namespace = parser.parse_args()
    return Args(
        paths=cast(list[Path], namespace.paths),
        config=cast(Optional[Path], namespace.config),
        group_by=cast(str, namespace.group_by),
        min_severity=cast(str, namespace.min_severity),
        jobs=cast(int, namespace.jobs),
        verbose=cast(bool, namespace.verbose),
        version=cast(bool, namespace.version),
    )


def _handle_version(args: Args) -> Optional[int]:
    """Handle version flag. Returns exit code if version flag is set, None otherwise."""
    if args.version:
        print(f"PyRefactor version {__version__}")
        return 0
    return None


def _configure_logging(args: Args) -> None:
    """Configure logging based on command line arguments."""
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)


def _load_config(args: Args) -> Optional[Config]:
    """Load configuration. Returns Config or None on error."""
    try:
        config = Config.load(args.config)
        logger.info("Loaded configuration: %s", config)
        return config
    except (ValueError, OSError, tomllib.TOMLDecodeError) as e:
        if args.verbose:
            logger.error("Error loading configuration: %s", e, exc_info=True)
        else:
            logger.error("Error loading configuration: %s", e)
        return None


def _validate_paths(args: Args) -> Optional[list[Path]]:
    """Validate paths from arguments. Returns list of paths or None on error."""
    paths: list[Path] = []
    for path in args.paths:
        if not path.exists():
            logger.error("Path does not exist: %s", path)
            return None
        paths.append(path)
    return paths


def _analyze_files_safely(
    analyzer: Analyzer, paths: list[Path], max_workers: int, *, verbose: bool = False
) -> Optional[AnalysisResult]:
    """Analyze files and handle errors. Returns result or None on error."""
    try:
        logger.info("Analyzing %d path(s)...", len(paths))
        return analyzer.analyze_files(paths, max_workers=max_workers)
    except (OSError, RuntimeError) as e:
        if verbose:
            logger.error("Error during analysis: %s", e, exc_info=True)
        else:
            logger.error("Error during analysis: %s", e)
        return None


def _get_min_severity(severity_str: str) -> Severity:
    """Get Severity enum from string."""
    return SEVERITY_MAP[severity_str]


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
    max_workers = max(1, args.jobs)
    analyzer = Analyzer(config)
    result = _analyze_files_safely(analyzer, paths, max_workers, verbose=args.verbose)
    if result is None or result.files_analyzed() == 0:
        if result is not None:
            logger.error("No Python files found to analyze")
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
