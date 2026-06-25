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
from .json_reporter import JsonReporter
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
    output_format: str
    min_severity: str
    jobs: int
    verbose: bool
    version: bool
    fail_on_parse_errors: bool


# Class-level constant for severity mapping to avoid recreation
SEVERITY_MAP: dict[str, Severity] = {
    "info": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
}


SEVERITY_CHOICES: tuple[str, ...] = ("info", "low", "medium", "high")
GROUP_BY_CHOICES: tuple[str, ...] = ("file", "severity")
FORMAT_CHOICES: tuple[str, ...] = ("text", "json")


def _add_core_arguments(parser: argparse.ArgumentParser) -> None:
    """Add path, config, and output arguments."""
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
        help="Group text output by file or severity (default: file)",
    )
    parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default="text",
        dest="output_format",
        help="Output format: text (default) or json",
    )
    parser.add_argument(
        "--min-severity",
        choices=SEVERITY_CHOICES,
        default="info",
        help=(
            "Minimum severity level to report and to use for exit codes "
            "(default: info)"
        ),
    )


def _add_execution_arguments(parser: argparse.ArgumentParser) -> None:
    """Add runtime behavior arguments."""
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
    parser.add_argument(
        "--fail-on-parse-errors",
        action="store_true",
        help="Exit with code 1 when any file has a syntax or parse error",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")


def _add_parser_arguments(parser: argparse.ArgumentParser) -> None:
    """Add all arguments to the parser."""
    _add_core_arguments(parser)
    _add_execution_arguments(parser)


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
  0 - No issues at or above --min-severity (or parse errors without --fail-on-parse-errors)
  1 - Issues at or above --min-severity found (or parse errors with --fail-on-parse-errors)
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
        output_format=cast(str, namespace.output_format),
        min_severity=cast(str, namespace.min_severity),
        jobs=cast(int, namespace.jobs),
        verbose=cast(bool, namespace.verbose),
        version=cast(bool, namespace.version),
        fail_on_parse_errors=cast(bool, namespace.fail_on_parse_errors),
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


def _determine_exit_code(result: AnalysisResult, *, fail_on_parse_errors: bool) -> int:
    """Return the CLI exit code for an analysis result."""
    if any(issue for issue in result.get_all_issues()):
        return 1
    if fail_on_parse_errors and _has_parse_errors(result):
        return 1
    return 0


def _has_parse_errors(result: AnalysisResult) -> bool:
    """Check if any analyzed file has a parse error."""
    return any(analysis.parse_error is not None for analysis in result.file_analyses)


def _handle_empty_analysis_result(result: AnalysisResult) -> int:
    """Log and return the exit code for an empty analysis run."""
    if result.excluded_file_count > 0:
        logger.error(
            "All %d Python file(s) were excluded by configuration patterns",
            result.excluded_file_count,
        )
    else:
        logger.error("No Python files found to analyze")
    return 2


def _report_results(args: Args, result: AnalysisResult) -> AnalysisResult:
    """Filter and print analysis results."""
    min_severity = _get_min_severity(args.min_severity)
    filtered_result = result.filtered(min_severity)
    if args.output_format == "json":
        JsonReporter().report(filtered_result)
    else:
        ConsoleReporter().report(filtered_result, group_by=args.group_by)
    return filtered_result


def _run_analysis(
    args: Args, config: Config, paths: list[Path]
) -> AnalysisResult | None:
    """Run analysis and return results, or None on orchestration failure."""
    if args.jobs < 1:
        logger.warning("--jobs must be at least 1; using 1 worker")
    max_workers = max(1, args.jobs)
    analyzer = Analyzer(config)
    return _analyze_files_safely(analyzer, paths, max_workers, verbose=args.verbose)


def _prepare_cli_run(args: Args) -> tuple[Config, list[Path]] | int:
    """Validate CLI inputs and return config/paths or an exit code."""
    if not args.paths:
        logger.error("No paths provided")
        return 2

    _configure_logging(args)

    config = _load_config(args)
    if config is None:
        return 2

    paths = _validate_paths(args)
    if paths is None:
        return 2

    return config, paths


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    version_exit = _handle_version(args)
    if version_exit is not None:
        return version_exit

    prepared = _prepare_cli_run(args)
    if isinstance(prepared, int):
        return prepared

    config, paths = prepared
    result = _run_analysis(args, config, paths)
    if result is None:
        return 2
    if result.files_analyzed() == 0:
        return _handle_empty_analysis_result(result)

    filtered_result = _report_results(args, result)
    return _determine_exit_code(
        filtered_result, fail_on_parse_errors=args.fail_on_parse_errors
    )


if __name__ == "__main__":
    sys.exit(main())
