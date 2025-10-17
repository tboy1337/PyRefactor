"""CLI entry point for PyRefactor."""

import argparse
import logging
import sys
from pathlib import Path

from .analyzer import Analyzer
from .config import Config
from .models import Severity
from .reporter import ConsoleReporter

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
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
    version_flag: bool = args.version
    if version_flag:
        version = "1.0.0"
        print(f"PyRefactor version {version}")
        return 0

    # Configure logging
    verbose_flag: bool = args.verbose
    if verbose_flag:
        logging.getLogger().setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    # Load configuration
    try:
        config_path: Path | None = args.config
        config = Config.load(config_path)
        logger.info("Loaded configuration: %s", config)
    except Exception as e:
        logger.error("Error loading configuration: %s", e)
        return 2

    # Validate paths
    paths: list[Path] = []
    arg_paths: list[Path] = args.paths
    for path in arg_paths:
        if not path.exists():
            logger.error("Path does not exist: %s", path)
            return 2
        paths.append(path)

    # Create analyzer
    analyzer = Analyzer(config)

    # Analyze files
    try:
        logger.info("Analyzing %d path(s)...", len(paths))
        result = analyzer.analyze_files(paths)
    except Exception as e:
        logger.error("Error during analysis: %s", e)
        return 2

    # Filter by minimum severity
    min_severity_map: dict[str, Severity] = {
        "info": Severity.INFO,
        "low": Severity.LOW,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
    }
    min_severity_str: str = args.min_severity
    min_severity = min_severity_map[min_severity_str]

    # Filter issues
    for file_analysis in result.file_analyses:
        file_analysis.issues = [
            issue for issue in file_analysis.issues if issue.severity >= min_severity
        ]

    # Report results
    reporter = ConsoleReporter()
    group_by_arg: str = args.group_by
    reporter.report(result, group_by=group_by_arg)

    # Determine exit code
    has_critical_issues = any(
        issue.severity in (Severity.HIGH, Severity.MEDIUM)
        for issue in result.get_all_issues()
    )

    return 1 if has_critical_issues else 0


if __name__ == "__main__":
    sys.exit(main())
