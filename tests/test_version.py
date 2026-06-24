"""Tests for version resolution."""

import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import patch

import pytest

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

    def test_fallback_version_matches_repository_pyproject(self) -> None:
        """Fallback version matches pyproject.toml without requiring a fresh install."""
        _fallback_version.cache_clear()
        with patch(
            "pyrefactor._version.version",
            side_effect=PackageNotFoundError("pyrefactor"),
        ):
            assert get_version() == _pyproject_version()

    def test_get_version_uses_package_metadata(self) -> None:
        """Installed version comes from package metadata when available."""
        expected = "2.3.4"
        with patch("pyrefactor._version.version", return_value=expected):
            assert get_version() == expected

    def test_get_version_returns_string(self) -> None:
        """Installed or fallback version is a non-empty string."""
        version = get_version()
        assert isinstance(version, str)
        assert version != ""

    def test_fallback_version_reads_pyproject(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Fallback parser reads version from pyproject.toml."""
        _fallback_version.cache_clear()
        fake_pkg = tmp_path / "src" / "pyrefactor"
        fake_pkg.mkdir(parents=True)
        monkeypatch.setattr(
            "pyrefactor._version.__file__", str(fake_pkg / "_version.py")
        )
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('version = "9.9.9"\n', encoding="utf-8")
        assert _fallback_version() == "9.9.9"

    def test_fallback_version_unknown_without_pyproject(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Fallback returns unknown when pyproject.toml is missing."""
        _fallback_version.cache_clear()
        fake_pkg = tmp_path / "src" / "pyrefactor"
        fake_pkg.mkdir(parents=True)
        monkeypatch.setattr(
            "pyrefactor._version.__file__", str(fake_pkg / "_version.py")
        )
        assert _fallback_version() == "unknown"

    def test_fallback_version_unknown_when_pyproject_has_no_version(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Fallback returns unknown when pyproject.toml has no version line."""
        _fallback_version.cache_clear()
        fake_pkg = tmp_path / "src" / "pyrefactor"
        fake_pkg.mkdir(parents=True)
        monkeypatch.setattr(
            "pyrefactor._version.__file__", str(fake_pkg / "_version.py")
        )
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'x'\n", encoding="utf-8")
        assert _fallback_version() == "unknown"

    def test_get_version_uses_fallback_when_not_installed(self) -> None:
        """Fallback is used when the distribution is not installed."""
        _fallback_version.cache_clear()
        with patch(
            "pyrefactor._version.version",
            side_effect=PackageNotFoundError("pyrefactor"),
        ):
            assert get_version() == _pyproject_version()

    def test_pyproject_path_uses_bundled_meipass(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Frozen executables read version from bundled pyproject.toml."""
        from pyrefactor._version import _pyproject_path

        bundled = tmp_path / "pyproject.toml"
        bundled.write_text('version = "8.8.8"\n', encoding="utf-8")
        monkeypatch.setattr("pyrefactor._version.sys.frozen", True, raising=False)
        monkeypatch.setattr(
            "pyrefactor._version.sys._MEIPASS", str(tmp_path), raising=False
        )

        assert _pyproject_path() == bundled
        _fallback_version.cache_clear()
        assert _fallback_version() == "8.8.8"
