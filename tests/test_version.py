"""Tests for version resolution."""

import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

from pyrefactor._version import _fallback_version, get_version


def _pyproject_version() -> str:
    """Read [project].version from the repository pyproject.toml."""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        data = tomllib.load(pyproject_file)
    project = data.get("project")
    if not isinstance(project, dict):
        raise AssertionError("Missing [project] table in pyproject.toml")
    version_value = project.get("version")
    if not isinstance(version_value, str):
        raise AssertionError("Missing project.version in pyproject.toml")
    return version_value


class TestVersion:
    """Tests for package version helpers."""

    def test_get_version_matches_pyproject(self) -> None:
        """Runtime version matches the single source of truth in pyproject.toml."""
        assert get_version() == _pyproject_version()

    def test_get_version_returns_string(self) -> None:
        """Installed or fallback version is a non-empty string."""
        version = get_version()
        assert isinstance(version, str)
        assert version != ""

    def test_fallback_version_reads_pyproject(self) -> None:
        """Fallback parser reads version from pyproject.toml."""
        _fallback_version.cache_clear()
        assert _fallback_version() == _pyproject_version()

    def test_get_version_uses_fallback_when_not_installed(self) -> None:
        """Fallback is used when the distribution is not installed."""
        _fallback_version.cache_clear()
        with patch(
            "pyrefactor._version.version",
            side_effect=PackageNotFoundError("pyrefactor"),
        ):
            assert get_version() == _pyproject_version()
