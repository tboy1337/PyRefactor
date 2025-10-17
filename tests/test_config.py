"""Tests for configuration."""

from pathlib import Path

import pytest

from pyrefactor.config import (
    BooleanLogicConfig,
    ComplexityConfig,
    Config,
    DuplicationConfig,
    LoopsConfig,
    PerformanceConfig,
)


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = Config()

        assert config.complexity.max_branches == 10
        assert config.complexity.max_nesting_depth == 3
        assert config.complexity.max_function_lines == 50
        assert config.performance.enabled is True
        assert config.duplication.enabled is True
        assert config.boolean_logic.enabled is True
        assert config.loops.enabled is True

    def test_load_default(self) -> None:
        """Test loading with no config file."""
        config = Config.load()

        assert isinstance(config, Config)
        assert config.complexity.max_branches == 10

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Test loading from a TOML file."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.pyrefactor.complexity]
max_branches = 15
max_nesting_depth = 4

[tool.pyrefactor.performance]
enabled = false
""")

        config = Config.from_file(config_file)

        assert config.complexity.max_branches == 15
        assert config.complexity.max_nesting_depth == 4
        assert config.performance.enabled is False

    def test_load_invalid_file(self, tmp_path: Path) -> None:
        """Test loading from invalid config file."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text("invalid toml content {{{")

        with pytest.raises(ValueError, match="Error loading configuration"):
            Config.from_file(config_file)

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file."""
        config_file = tmp_path / "nonexistent.toml"

        config = Config.from_file(config_file)

        # Should return default config
        assert config.complexity.max_branches == 10


class TestComplexityConfig:
    """Tests for ComplexityConfig."""

    def test_default_values(self) -> None:
        """Test default complexity config values."""
        config = ComplexityConfig()

        assert config.max_branches == 10
        assert config.max_nesting_depth == 3
        assert config.max_function_lines == 50
        assert config.max_arguments == 5
        assert config.max_local_variables == 15
        assert config.max_cyclomatic_complexity == 10


class TestPerformanceConfig:
    """Tests for PerformanceConfig."""

    def test_default_values(self) -> None:
        """Test default performance config values."""
        config = PerformanceConfig()

        assert config.enabled is True


class TestDuplicationConfig:
    """Tests for DuplicationConfig."""

    def test_default_values(self) -> None:
        """Test default duplication config values."""
        config = DuplicationConfig()

        assert config.enabled is True
        assert config.min_duplicate_lines == 5
        assert config.similarity_threshold == 0.85


class TestBooleanLogicConfig:
    """Tests for BooleanLogicConfig."""

    def test_default_values(self) -> None:
        """Test default boolean logic config values."""
        config = BooleanLogicConfig()

        assert config.enabled is True
        assert config.max_boolean_operators == 3


class TestLoopsConfig:
    """Tests for LoopsConfig."""

    def test_default_values(self) -> None:
        """Test default loops config values."""
        config = LoopsConfig()

        assert config.enabled is True

