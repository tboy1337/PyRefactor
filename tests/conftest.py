"""Pytest configuration and fixtures."""

import ast
from pathlib import Path
from typing import Any

import pytest

from pyrefactor.config import Config


@pytest.fixture
def default_config() -> Config:
    """Provide default configuration."""
    return Config()


@pytest.fixture
def sample_code() -> str:
    """Provide sample code for testing."""
    return """
def example_function(x, y):
    if x > 0:
        if y > 0:
            if x + y > 10:
                return True
    return False
"""


@pytest.fixture
def complex_function() -> str:
    """Provide complex function for testing."""
    return """
def complex_func(a, b, c, d, e, f, g):
    result = []
    temp1 = 0
    temp2 = 0
    temp3 = 0
    temp4 = 0
    temp5 = 0
    temp6 = 0
    temp7 = 0
    temp8 = 0
    temp9 = 0
    temp10 = 0
    temp11 = 0
    temp12 = 0
    temp13 = 0
    temp14 = 0
    temp15 = 0
    temp16 = 0

    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
    elif f:
        return 2
    elif g:
        return 3
    else:
        return 4

    for i in range(10):
        if i > 5:
            result.append(i)

    return result
"""


@pytest.fixture
def temp_python_file(tmp_path: Path) -> Path:
    """Create a temporary Python file."""
    file_path = tmp_path / "test_file.py"
    file_path.write_text(
        """
def test_function():
    x = 1
    return x
"""
    )
    return file_path


@pytest.fixture
def parse_code() -> Any:
    """Provide a function to parse Python code."""

    def _parse(code: str) -> ast.Module:
        return ast.parse(code)

    return _parse
