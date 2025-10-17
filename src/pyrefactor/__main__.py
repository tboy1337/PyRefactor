"""CLI entry point for PyRefactor."""

import argparse
import logging
import sys
from pathlib import Path
from typing import cast

from .analyzer import Analyzer
from .config import Config
from .models import Severity
from .reporter import ConsoleReporter

# Configure logging
logging.basicConfig(
    level=logging.WARNING, format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
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
        nargs="+",
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

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Handle version
    if args.version:
        from . import __version__

        print(f"PyRefactor version {__version__}")
        return 0

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    # Load configuration
    try:
        config = Config.load(args.config)  # type: ignore[misc]
        logger.info(f"Loaded configuration: {config}")  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")  # type: ignore[misc]
        return 2

    # Validate paths
    paths: list[Path] = []
    for path in args.paths:  # type: ignore[misc]
        if not path.exists():  # type: ignore[misc]
            logger.error(f"Path does not exist: {path}")  # type: ignore[misc]
            return 2
        paths.append(path)  # type: ignore[misc]

    # Create analyzer
    analyzer = Analyzer(config)

    # Analyze files
    try:
        logger.info(f"Analyzing {len(paths)} path(s)...")  # type: ignore[misc]
        result = analyzer.analyze_files(paths)  # type: ignore[misc]
    except Exception as e:
        logger.error(f"Error during analysis: {e}")  # type: ignore[misc]
        return 2

    # Filter by minimum severity
    min_severity_map: dict[str, Severity] = {  # type: ignore[misc]
        "info": Severity.INFO,
        "low": Severity.LOW,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
    }
    min_severity = min_severity_map[args.min_severity]  # type: ignore[misc]

    # Filter issues
    for file_analysis in result.file_analyses:  # type: ignore[misc]
        file_analysis.issues = [
            issue
            for issue in file_analysis.issues
            if not (issue.severity < min_severity)  # type: ignore[misc]
        ]

    # Report results
    reporter = ConsoleReporter()
    reporter.report(result, group_by=args.group_by)  # type: ignore[misc]

    # Determine exit code
    has_critical_issues = any(
        issue.severity in (Severity.HIGH, Severity.MEDIUM)
        for issue in result.get_all_issues()
    )

    return 1 if has_critical_issues else 0


if __name__ == "__main__":
    sys.exit(main())

