"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest

from pyrefactor.config import Config


@pytest.fixture
def default_config() -> Config:
    """Provide default configuration."""
    return Config()


@pytest.fixture
def temp_python_file(tmp_path: Path) -> Path:
    """Create a temporary Python file."""
    file_path = tmp_path / "test_file.py"
    file_path.write_text("""
def test_function():
    x = 1
    return x
""")
    return file_path
