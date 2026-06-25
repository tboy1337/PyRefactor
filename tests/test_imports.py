"""Smoke tests for the public pyrefactor API."""


def test_public_api_imports() -> None:
    """Public exports are importable and version is a non-empty string."""
    from pyrefactor import (
        AnalysisResult,
        Analyzer,
        Config,
        ConsoleReporter,
        FileAnalysis,
        Issue,
        JsonReporter,
        Severity,
        __version__,
    )

    assert isinstance(__version__, str)
    assert __version__ != ""
    assert Analyzer is not None
    assert Config is not None
    assert ConsoleReporter is not None
    assert JsonReporter is not None
    assert AnalysisResult is not None
    assert FileAnalysis is not None
    assert Issue is not None
    assert Severity is not None
