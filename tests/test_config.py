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
        """Test loading from nonexistent file raises an error."""
        config_file = tmp_path / "nonexistent.ini"

        with pytest.raises(ValueError, match="Configuration file not found"):
            Config.from_file(config_file)

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

    def test_load_from_toml(self, tmp_path: Path) -> None:
        """Test loading control flow settings from TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor.control_flow]
enabled = false
""")

        config = Config.from_toml_file(config_file)

        assert config.control_flow.enabled is False


class TestDictOperationsConfig:
    """Tests for DictOperationsConfig."""

    def test_default_values(self) -> None:
        """Test default dict operations config values."""
        config = DictOperationsConfig()

        assert config.enabled is True

    def test_load_from_toml(self, tmp_path: Path) -> None:
        """Test loading dict operations settings from TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor.dict_operations]
enabled = false
""")

        config = Config.from_toml_file(config_file)

        assert config.dict_operations.enabled is False

    def test_load_from_ini(self, tmp_path: Path) -> None:
        """Test loading dict operations settings from INI."""
        config_file = tmp_path / "pyrefactor.ini"
        config_file.write_text("""
[dict_operations]
enabled = false
""")

        config = Config.from_ini_file(config_file)

        assert config.dict_operations.enabled is False


class TestComparisonsConfig:
    """Tests for ComparisonsConfig."""

    def test_default_values(self) -> None:
        """Test default comparisons config values."""
        config = ComparisonsConfig()

        assert config.enabled is True

    def test_load_from_toml(self, tmp_path: Path) -> None:
        """Test loading comparisons settings from TOML."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor.comparisons]
enabled = false
""")

        config = Config.from_toml_file(config_file)

        assert config.comparisons.enabled is False

    def test_exclude_patterns_from_comma_separated_string(self, tmp_path: Path) -> None:
        """Test exclude_patterns can be loaded from a comma-separated TOML string."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor]
exclude_patterns = "build, dist, vendor"
""")

        config = Config.from_toml_file(config_file)

        assert config.exclude_patterns == ["build", "dist", "vendor"]

    def test_load_nonexistent_toml_file(self, tmp_path: Path) -> None:
        """Test loading from nonexistent TOML file raises an error."""
        config_file = tmp_path / "nonexistent.toml"

        with pytest.raises(ValueError, match="Configuration file not found"):
            Config.from_file(config_file)

    def test_validate_rejects_negative_max_branches(self) -> None:
        """Test validation rejects negative complexity thresholds."""
        config = Config()
        config.complexity.max_branches = -1

        with pytest.raises(ValueError, match="complexity.max_branches"):
            config.validate()

    def test_validate_rejects_invalid_similarity_threshold(self) -> None:
        """Test validation rejects similarity threshold outside 0.0-1.0."""
        config = Config()
        config.duplication.similarity_threshold = 1.5

        with pytest.raises(ValueError, match="similarity_threshold"):
            config.validate()

    def test_validate_rejects_min_duplicate_lines_below_two(self) -> None:
        """Test validation rejects min_duplicate_lines below 2."""
        config = Config()
        config.duplication.min_duplicate_lines = 1

        with pytest.raises(ValueError, match="min_duplicate_lines"):
            config.validate()

    def test_validate_rejects_zero_max_boolean_operators(self) -> None:
        """Test validation rejects max_boolean_operators below 1."""
        config = Config()
        config.boolean_logic.max_boolean_operators = 0

        with pytest.raises(ValueError, match="max_boolean_operators"):
            config.validate()

    def test_validate_rejects_negative_min_concatenations(self) -> None:
        """Test validation rejects negative performance.min_concatenations."""
        config = Config()
        config.performance.min_concatenations = -1

        with pytest.raises(ValueError, match="performance.min_concatenations"):
            config.validate()

    def test_validate_rejects_negative_min_duplicate_calls(self) -> None:
        """Test validation rejects negative performance.min_duplicate_calls."""
        config = Config()
        config.performance.min_duplicate_calls = -1

        with pytest.raises(ValueError, match="performance.min_duplicate_calls"):
            config.validate()

    def test_toml_load_rejects_invalid_threshold(self, tmp_path: Path) -> None:
        """Test loading invalid threshold from TOML raises ValueError."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("""
[tool.pyrefactor.duplication]
similarity_threshold = 2.0
""")

        with pytest.raises(ValueError, match="similarity_threshold"):
            Config.from_toml_file(config_file)
