"""Package version resolution."""

import sys
import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import cast

_PACKAGE_NAME = "pyrefactor"
_FALLBACK_VERSION_CACHE: dict[str, str] = {}


def _cached_fallback_version(value: str | None = None) -> str:
    """Read or store the cached fallback version string."""
    if value is not None:
        _FALLBACK_VERSION_CACHE["value"] = value
        return value
    cached = _FALLBACK_VERSION_CACHE.get("value")
    if cached is not None:
        return cached
    return "unknown"


def _clear_fallback_version_cache() -> None:
    """Clear cached fallback version (used by tests)."""
    _FALLBACK_VERSION_CACHE.clear()


def _is_frozen_runtime() -> bool:
    """Return True when running inside a frozen PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def _bundled_pyproject_path() -> Path | None:
    """Return bundled pyproject.toml path for frozen executables."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not isinstance(meipass, str):
        return None
    bundled = Path(meipass) / "pyproject.toml"
    return bundled if bundled.is_file() else None


def _pyproject_path() -> Path:
    """Return the pyproject.toml path for version fallback."""
    if _is_frozen_runtime():
        bundled = _bundled_pyproject_path()
        if bundled is not None:
            return bundled
    return Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


def _read_project_version(data: dict[str, object]) -> str | None:
    """Extract project.version from parsed TOML data."""
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    version_value = cast(object, project.get("version"))
    if isinstance(version_value, str) and version_value:
        return version_value
    return None


def _fallback_version() -> str:
    """Read version from pyproject.toml when the package is not installed."""
    cached = _FALLBACK_VERSION_CACHE.get("value")
    if cached is not None:
        return cached

    pyproject = _pyproject_path()
    if not pyproject.is_file():
        return _cached_fallback_version("unknown")
    try:
        data = cast(
            dict[str, object], tomllib.loads(pyproject.read_text(encoding="utf-8"))
        )
    except tomllib.TOMLDecodeError:
        return _cached_fallback_version("unknown")

    resolved = _read_project_version(data) or "unknown"
    return _cached_fallback_version(resolved)


def get_version() -> str:
    """Return the installed package version, falling back to pyproject.toml."""
    try:
        return version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return _fallback_version()
