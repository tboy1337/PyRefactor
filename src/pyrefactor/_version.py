"""Package version resolution."""

import sys
import tomllib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PACKAGE_NAME = "pyrefactor"


def _pyproject_path() -> Path:
    """Return the pyproject.toml path for version fallback."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass) / "pyproject.toml"
            if bundled.is_file():
                return bundled
    return Path(__file__).resolve().parent.parent.parent / "pyproject.toml"


@lru_cache(maxsize=1)
def _fallback_version() -> str:
    """Read version from pyproject.toml when the package is not installed."""
    pyproject = _pyproject_path()
    if not pyproject.is_file():
        return "unknown"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return "unknown"
    project = data.get("project")
    if not isinstance(project, dict):
        return "unknown"
    version_value = project.get("version")
    if isinstance(version_value, str) and version_value:
        return version_value
    return "unknown"


def get_version() -> str:
    """Return the installed package version, falling back to pyproject.toml."""
    try:
        return version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return _fallback_version()
