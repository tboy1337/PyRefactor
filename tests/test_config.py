"""Tests for configuration."""

from pathlib import Path

import pytest

from pyrefactor.config import (
    BooleanLogicConfig,
    ComparisonsConfig,
    ComplexityConfig,
    Config,
    ContextManagerConfig,
    ControlFlowConfig,
    DictOperationsConfig,
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
        """Test loading from an INI file."""
        config_file = tmp_path / "pyrefactor.ini"
        config_file.write_text("""
[complexity]
max_branches = 15
max_nesting_depth = 4

[performance]
enabled = false
""")

        config = Config.from_file(config_file)

        assert config.complexity.max_branches == 15
        assert config.complexity.max_nesting_depth == 4
        assert config.performance.enabled is False

    def test_load_from_toml_file(self, tmp_path: Path) -> None:
        """Test loading from a TOML configuration file."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.pyrefactor]
exclude_patterns = ["build", "dist"]

[tool.pyrefactor.complexity]
max_branches = 12

[tool.pyrefactor.performance]
enabled = false
""")

        config = Config.from_toml_file(config_file)

        assert config.complexity.max_branches == 12
        assert config.performance.enabled is False
        assert config.exclude_patterns == ["build", "dist"]

    def test_load_empty_toml_file(self, tmp_path: Path) -> None:
        """Test loading from an empty TOML file uses defaults."""
        config_file = tmp_path / "empty.toml"
        config_file.write_text("")

        config = Config.from_toml_file(config_file)

        assert config.complexity.max_branches == 10
        assert config.performance.enabled is True

    def test_load_partial_toml_file(self, tmp_path: Path) -> None:
        """Test loading partial TOML configuration."""
        config_file = tmp_path / "partial.toml"
        config_file.write_text("""
[tool.pyrefactor.complexity]
max_arguments = 0
""")

        config = Config.from_toml_file(config_file)

        assert config.complexity.max_arguments == 0

    def test_load_explicit_none(self) -> None:
        """Test Config.load(None) returns defaults from discovery."""
        config = Config.load(None)
        assert isinstance(config, Config)

    def test_load_invalid_file(self, tmp_path: Path) -> None:
        """Test loading from invalid config file."""
        config_file = tmp_path / "invalid.ini"
        config_file.write_text("[complexity\nmax_branches = not_a_number")

        with pytest.raises(ValueError, match="Error loading configuration"):
            Config.from_file(config_file)

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file."""
        config_file = tmp_path / "nonexistent.ini"

        config = Config.from_file(config_file)

        # Should return default config
        assert config.complexity.max_branches == 10

    def test_load_ini_duplication_and_boolean_sections(self, tmp_path: Path) -> None:
        """Test loading duplication and boolean_logic INI sections."""
        config_file = tmp_path / "pyrefactor.ini"
        config_file.write_text("""
[duplication]
enabled = false
min_duplicate_lines = 8
similarity_threshold = 0.75

[boolean_logic]
enabled = true
max_boolean_operators = 5

[general]
exclude_patterns = tests/*, build/*
""")

        config = Config.from_ini_file(config_file)

        assert config.duplication.enabled is False
        assert config.duplication.min_duplicate_lines == 8
        assert config.duplication.similarity_threshold == 0.75
        assert config.boolean_logic.max_boolean_operators == 5
        assert config.exclude_patterns == ["tests/*", "build/*"]

    def test_from_toml_invalid_section_raises(self) -> None:
        """Test invalid tool.pyrefactor section raises ValueError."""
        with pytest.raises(ValueError, match="Invalid \\[tool.pyrefactor\\]"):
            Config.from_toml_data({"tool": {"pyrefactor": "invalid"}})

    def test_toml_exclude_patterns_as_string(self, tmp_path: Path) -> None:
        """Test comma-separated exclude_patterns string in TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor]
exclude_patterns = "build, dist, vendor"
""")

        config = Config.from_toml_file(config_file)
        assert config.exclude_patterns == ["build", "dist", "vendor"]

    def test_load_defaults_in_empty_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Config.load returns defaults when no config files exist."""
        monkeypatch.chdir(tmp_path)
        config = Config.load()
        assert config.complexity.max_cyclomatic_complexity == 10


class TestComplexityConfig:
    """Tests for ComplexityConfig."""

    def test_default_values(self) -> None:
        """Test default complexity config values."""
        config = ComplexityConfig()

        assert config.enabled is True
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
        assert config.min_concatenations == 3
        assert config.min_duplicate_calls == 3

    def test_load_performance_from_toml(self, tmp_path: Path) -> None:
        """Test loading performance thresholds from TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor.performance]
enabled = true
min_concatenations = 5
min_duplicate_calls = 4
""")

        config = Config.from_toml_file(config_file)

        assert config.performance.min_concatenations == 5
        assert config.performance.min_duplicate_calls == 4

    def test_load_performance_from_ini(self, tmp_path: Path) -> None:
        """Test loading performance thresholds from INI."""
        config_file = tmp_path / "pyrefactor.ini"
        config_file.write_text("""
[performance]
enabled = true
min_concatenations = 2
min_duplicate_calls = 2
""")

        config = Config.from_ini_file(config_file)

        assert config.performance.min_concatenations == 2
        assert config.performance.min_duplicate_calls == 2


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


class TestContextManagerConfig:
    """Tests for ContextManagerConfig."""

    def test_default_values(self) -> None:
        """Test default context manager config values."""
        config = ContextManagerConfig()

        assert config.enabled is True


class TestControlFlowConfig:
    """Tests for ControlFlowConfig."""

    def test_default_values(self) -> None:
        """Test default control flow config values."""
        config = ControlFlowConfig()

        assert config.enabled is True


class TestDictOperationsConfig:
    """Tests for DictOperationsConfig."""

    def test_default_values(self) -> None:
        """Test default dict operations config values."""
        config = DictOperationsConfig()

        assert config.enabled is True


class TestComparisonsConfig:
    """Tests for ComparisonsConfig."""

    def test_default_values(self) -> None:
        """Test default comparisons config values."""
        config = ComparisonsConfig()

        assert config.enabled is True
