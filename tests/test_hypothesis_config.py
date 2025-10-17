"""Property-based tests for configuration using Hypothesis."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyrefactor.config import (
    BooleanLogicConfig,
    ComplexityConfig,
    Config,
    DuplicationConfig,
    LoopsConfig,
    PerformanceConfig,
)


# Strategies for config objects
@st.composite
def complexity_config_strategy(draw: st.DrawFn) -> ComplexityConfig:
    """Generate a ComplexityConfig with valid values."""
    return ComplexityConfig(
        max_branches=draw(st.integers(min_value=1, max_value=100)),
        max_nesting_depth=draw(st.integers(min_value=1, max_value=20)),
        max_function_lines=draw(st.integers(min_value=1, max_value=1000)),
        max_arguments=draw(st.integers(min_value=0, max_value=50)),
        max_local_variables=draw(st.integers(min_value=1, max_value=100)),
        max_cyclomatic_complexity=draw(st.integers(min_value=1, max_value=100)),
    )


@st.composite
def performance_config_strategy(draw: st.DrawFn) -> PerformanceConfig:
    """Generate a PerformanceConfig."""
    return PerformanceConfig(enabled=draw(st.booleans()))


@st.composite
def duplication_config_strategy(draw: st.DrawFn) -> DuplicationConfig:
    """Generate a DuplicationConfig with valid values."""
    return DuplicationConfig(
        enabled=draw(st.booleans()),
        min_duplicate_lines=draw(st.integers(min_value=1, max_value=100)),
        similarity_threshold=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


@st.composite
def boolean_logic_config_strategy(draw: st.DrawFn) -> BooleanLogicConfig:
    """Generate a BooleanLogicConfig with valid values."""
    return BooleanLogicConfig(
        enabled=draw(st.booleans()),
        max_boolean_operators=draw(st.integers(min_value=1, max_value=20)),
    )


@st.composite
def loops_config_strategy(draw: st.DrawFn) -> LoopsConfig:
    """Generate a LoopsConfig."""
    return LoopsConfig(enabled=draw(st.booleans()))


@st.composite
def config_strategy(draw: st.DrawFn) -> Config:
    """Generate a Config with valid values."""
    return Config(
        complexity=draw(complexity_config_strategy()),
        performance=draw(performance_config_strategy()),
        duplication=draw(duplication_config_strategy()),
        boolean_logic=draw(boolean_logic_config_strategy()),
        loops=draw(loops_config_strategy()),
        exclude_patterns=draw(st.lists(st.text(min_size=1, max_size=50), max_size=10)),
    )


class TestComplexityConfigProperties:
    """Property-based tests for ComplexityConfig."""

    @given(complexity_config_strategy())
    def test_complexity_config_all_values_positive(
        self, config: ComplexityConfig
    ) -> None:
        """Property: All complexity thresholds are positive."""
        assert config.max_branches > 0
        assert config.max_nesting_depth > 0
        assert config.max_function_lines > 0
        assert config.max_arguments >= 0  # Can be 0 for no args allowed
        assert config.max_local_variables > 0
        assert config.max_cyclomatic_complexity > 0

    @given(
        st.integers(min_value=1, max_value=100),
        st.integers(min_value=1, max_value=20),
    )
    def test_complexity_config_can_be_created_with_valid_values(
        self, max_branches: int, max_nesting: int
    ) -> None:
        """Property: ComplexityConfig can be created with any positive values."""
        config = ComplexityConfig(
            max_branches=max_branches, max_nesting_depth=max_nesting
        )
        assert config.max_branches == max_branches
        assert config.max_nesting_depth == max_nesting


class TestDuplicationConfigProperties:
    """Property-based tests for DuplicationConfig."""

    @given(duplication_config_strategy())
    def test_duplication_config_threshold_in_range(
        self, config: DuplicationConfig
    ) -> None:
        """Property: Similarity threshold is always between 0 and 1."""
        assert 0.0 <= config.similarity_threshold <= 1.0

    @given(duplication_config_strategy())
    def test_duplication_config_min_lines_positive(
        self, config: DuplicationConfig
    ) -> None:
        """Property: Minimum duplicate lines is always positive."""
        assert config.min_duplicate_lines > 0

    @given(st.booleans(), st.integers(min_value=1, max_value=100))
    def test_duplication_config_enabled_can_be_toggled(
        self, enabled: bool, min_lines: int
    ) -> None:
        """Property: Duplication detection can be enabled or disabled."""
        config = DuplicationConfig(enabled=enabled, min_duplicate_lines=min_lines)
        assert config.enabled == enabled


class TestBooleanLogicConfigProperties:
    """Property-based tests for BooleanLogicConfig."""

    @given(boolean_logic_config_strategy())
    def test_boolean_logic_max_operators_positive(
        self, config: BooleanLogicConfig
    ) -> None:
        """Property: Maximum boolean operators is always positive."""
        assert config.max_boolean_operators > 0

    @given(st.booleans())
    def test_boolean_logic_can_be_toggled(self, enabled: bool) -> None:
        """Property: Boolean logic detection can be enabled or disabled."""
        config = BooleanLogicConfig(enabled=enabled)
        assert config.enabled == enabled


class TestPerformanceConfigProperties:
    """Property-based tests for PerformanceConfig."""

    @given(st.booleans())
    def test_performance_config_can_be_toggled(self, enabled: bool) -> None:
        """Property: Performance detection can be enabled or disabled."""
        config = PerformanceConfig(enabled=enabled)
        assert config.enabled == enabled


class TestLoopsConfigProperties:
    """Property-based tests for LoopsConfig."""

    @given(st.booleans())
    def test_loops_config_can_be_toggled(self, enabled: bool) -> None:
        """Property: Loops detection can be enabled or disabled."""
        config = LoopsConfig(enabled=enabled)
        assert config.enabled == enabled


class TestConfigProperties:
    """Property-based tests for main Config class."""

    @given(config_strategy())
    def test_config_has_all_subconfigs(self, config: Config) -> None:
        """Property: Config always has all required sub-configurations."""
        assert isinstance(config.complexity, ComplexityConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert isinstance(config.duplication, DuplicationConfig)
        assert isinstance(config.boolean_logic, BooleanLogicConfig)
        assert isinstance(config.loops, LoopsConfig)
        assert isinstance(config.exclude_patterns, list)

    @given(config_strategy())
    def test_config_exclude_patterns_is_list_of_strings(self, config: Config) -> None:
        """Property: Exclude patterns is always a list of strings."""
        assert all(isinstance(pattern, str) for pattern in config.exclude_patterns)

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10))
    def test_config_exclude_patterns_preserved(self, patterns: list[str]) -> None:
        """Property: Exclude patterns are preserved when set."""
        config = Config(exclude_patterns=patterns)
        assert config.exclude_patterns == patterns

    def test_config_default_creation(self) -> None:
        """Property: Config can be created with all defaults."""
        config = Config()
        assert isinstance(config.complexity, ComplexityConfig)
        assert isinstance(config.performance, PerformanceConfig)
        assert config.exclude_patterns == []

    @given(config_strategy())
    def test_config_complexity_thresholds_consistent(self, config: Config) -> None:
        """Property: Complexity config in Config maintains valid thresholds."""
        # All thresholds should be positive
        assert config.complexity.max_branches > 0
        assert config.complexity.max_nesting_depth > 0
        assert config.complexity.max_function_lines > 0


class TestConfigLoadingInvariants:
    """Test invariants for config loading."""

    def test_config_load_without_file_returns_defaults(self) -> None:
        """Property: Loading config without file returns default values."""
        config = Config.load(None)
        default_config = Config()

        assert config.complexity.max_branches == default_config.complexity.max_branches
        assert (
            config.complexity.max_nesting_depth
            == default_config.complexity.max_nesting_depth
        )

    @given(
        st.integers(min_value=1, max_value=50),
        st.integers(min_value=1, max_value=10),
    )
    def test_config_from_toml_with_valid_values(
        self, max_branches: int, max_nesting: int
    ) -> None:
        """Property: Config can be loaded from TOML with valid values."""
        toml_content = f"""
[tool.pyrefactor.complexity]
max_branches = {max_branches}
max_nesting_depth = {max_nesting}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = Config.from_file(temp_path)
            assert config.complexity.max_branches == max_branches
            assert config.complexity.max_nesting_depth == max_nesting
        finally:
            temp_path.unlink()

    def test_config_from_nonexistent_file_returns_defaults(self) -> None:
        """Property: Loading from non-existent file returns defaults."""
        config = Config.from_file(Path("/nonexistent/path/to/config.toml"))
        default_config = Config()

        # Should have default values
        assert config.complexity.max_branches == default_config.complexity.max_branches

    @given(st.booleans(), st.booleans(), st.booleans())
    def test_config_detector_toggles_independent(
        self, perf_enabled: bool, dup_enabled: bool, bool_enabled: bool
    ) -> None:
        """Property: Different detector enables can be set independently."""
        config = Config(
            performance=PerformanceConfig(enabled=perf_enabled),
            duplication=DuplicationConfig(enabled=dup_enabled),
            boolean_logic=BooleanLogicConfig(enabled=bool_enabled),
        )

        assert config.performance.enabled == perf_enabled
        assert config.duplication.enabled == dup_enabled
        assert config.boolean_logic.enabled == bool_enabled


class TestConfigBoundaryValues:
    """Test boundary values in configuration."""

    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_similarity_threshold_valid_range(self, threshold: float) -> None:
        """Property: Any float between 0 and 1 is valid for similarity threshold."""
        config = DuplicationConfig(similarity_threshold=threshold)
        assert 0.0 <= config.similarity_threshold <= 1.0

    @given(st.integers(min_value=1, max_value=1000))
    def test_function_lines_any_positive_value(self, max_lines: int) -> None:
        """Property: Any positive integer is valid for max function lines."""
        config = ComplexityConfig(max_function_lines=max_lines)
        assert config.max_function_lines == max_lines
        assert config.max_function_lines > 0

    @given(st.integers(min_value=0, max_value=50))
    def test_max_arguments_can_be_zero(self, max_args: int) -> None:
        """Property: Max arguments can be 0 (no arguments allowed)."""
        config = ComplexityConfig(max_arguments=max_args)
        assert config.max_arguments >= 0


class TestConfigTomlParsing:
    """Test TOML parsing invariants."""

    def test_empty_toml_uses_defaults(self) -> None:
        """Property: Empty TOML file uses default values."""
        toml_content = ""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = Config.from_file(temp_path)
            default_config = Config()
            assert (
                config.complexity.max_branches == default_config.complexity.max_branches
            )
        finally:
            temp_path.unlink()

    def test_partial_toml_preserves_unset_defaults(self) -> None:
        """Property: Partial TOML preserves defaults for unspecified values."""
        toml_content = """
[tool.pyrefactor.complexity]
max_branches = 20
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = Config.from_file(temp_path)
            default_config = Config()

            # Set value should be different
            assert config.complexity.max_branches == 20

            # Unset values should be defaults
            assert (
                config.complexity.max_nesting_depth
                == default_config.complexity.max_nesting_depth
            )
        finally:
            temp_path.unlink()

    def test_invalid_toml_raises_error(self) -> None:
        """Property: Invalid TOML content raises ValueError."""
        toml_content = "this is not valid { toml"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Error loading configuration"):
                Config.from_file(temp_path)
        finally:
            temp_path.unlink()

    @given(
        st.lists(
            st.text(
                min_size=1,
                max_size=30,
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-.*",
            ),
            min_size=1,
            max_size=5,
        )
    )
    def test_exclude_patterns_preserved_in_toml(self, patterns: list[str]) -> None:
        """Property: Exclude patterns are correctly loaded from TOML."""
        # Format patterns for TOML array - escape backslashes and quotes
        patterns_str = ", ".join(
            f'"{p.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34))}"'
            for p in patterns
        )
        toml_content = f"""
[tool.pyrefactor]
exclude_patterns = [{patterns_str}]
"""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".toml", delete=False
        ) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = Config.from_file(temp_path)
            assert config.exclude_patterns == patterns
        finally:
            temp_path.unlink()
