"""PyRefactor - A Python refactoring and optimization linter."""

from pyrefactor._version import get_version
from pyrefactor.analyzer import Analyzer
from pyrefactor.config import Config
from pyrefactor.models import AnalysisResult, FileAnalysis, Issue, Severity
from pyrefactor.reporter import ConsoleReporter

__version__ = get_version()

__all__ = [
    "Analyzer",
    "AnalysisResult",
    "Config",
    "ConsoleReporter",
    "FileAnalysis",
    "Issue",
    "Severity",
    "__version__",
]
