"""Additional configuration loading tests."""

from pathlib import Path

import pytest

from pyrefactor.config import Config


class TestConfigDiscovery:
    """Tests for configuration discovery and TOML loading."""

    def test_from_file_toml_suffix(self, tmp_path: Path) -> None:
        """Test from_file routes .toml files to the TOML loader."""
        config_file = tmp_path / "custom.toml"
        config_file.write_text(
            """
[tool.pyrefactor.complexity]
max_branches = 20
"""
        )

        config = Config.from_file(config_file)
        assert config.complexity.max_branches == 20

    def test_load_pyproject_discovery(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config.load discovers pyproject.toml in the working directory."""
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            """
[tool.pyrefactor]
exclude_patterns = ["vendor"]

[tool.pyrefactor.loops]
enabled = false
"""
        )

        config = Config.load()
        assert config.exclude_patterns == ["vendor"]
        assert config.loops.enabled is False

    def test_load_ini_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Config.load falls back to pyrefactor.ini."""
        monkeypatch.chdir(tmp_path)
        ini_file = tmp_path / "pyrefactor.ini"
        ini_file.write_text(
            """
[complexity]
max_branches = 7
"""
        )

        config = Config.load()
        assert config.complexity.max_branches == 7

    def test_invalid_toml_raises(self, tmp_path: Path) -> None:
        """Test invalid TOML raises ValueError."""
        config_file = tmp_path / "bad.toml"
        config_file.write_text("[[[invalid")

        with pytest.raises(ValueError, match="Error loading configuration"):
            Config.from_toml_file(config_file)
