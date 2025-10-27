"""Configuration management for PyRefactor."""

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union


@dataclass
class ComplexityConfig:
    """Configuration for complexity detector."""

    max_branches: int = 10
    max_nesting_depth: int = 3
    max_function_lines: int = 50
    max_arguments: int = 5
    max_local_variables: int = 15
    max_cyclomatic_complexity: int = 10


@dataclass
class PerformanceConfig:
    """Configuration for performance detector."""

    enabled: bool = True


@dataclass
class DuplicationConfig:
    """Configuration for duplication detector."""

    enabled: bool = True
    min_duplicate_lines: int = 5
    similarity_threshold: float = 0.85


@dataclass
class BooleanLogicConfig:
    """Configuration for boolean logic detector."""

    enabled: bool = True
    max_boolean_operators: int = 3


@dataclass
class LoopsConfig:
    """Configuration for loops detector."""

    enabled: bool = True


@dataclass
class ContextManagerConfig:
    """Configuration for context manager detector."""

    enabled: bool = True


@dataclass
class ControlFlowConfig:
    """Configuration for control flow detector."""

    enabled: bool = True


@dataclass
class DictOperationsConfig:
    """Configuration for dictionary operations detector."""

    enabled: bool = True


@dataclass
class ComparisonsConfig:
    """Configuration for comparisons detector."""

    enabled: bool = True


@dataclass
class Config:
    """Main configuration for PyRefactor."""

    complexity: ComplexityConfig = field(default_factory=ComplexityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    duplication: DuplicationConfig = field(default_factory=DuplicationConfig)
    boolean_logic: BooleanLogicConfig = field(default_factory=BooleanLogicConfig)
    loops: LoopsConfig = field(default_factory=LoopsConfig)
    context_manager: ContextManagerConfig = field(default_factory=ContextManagerConfig)
    control_flow: ControlFlowConfig = field(default_factory=ControlFlowConfig)
    dict_operations: DictOperationsConfig = field(default_factory=DictOperationsConfig)
    comparisons: ComparisonsConfig = field(default_factory=ComparisonsConfig)
    exclude_patterns: list[str] = field(default_factory=list)

    @staticmethod
    def _parse_complexity_config(config: configparser.ConfigParser) -> dict[str, int]:
        """Extract complexity configuration from config parser."""
        complexity_dict: dict[str, int] = {}
        if config.has_section("complexity"):
            for key in [
                "max_branches",
                "max_nesting_depth",
                "max_function_lines",
                "max_arguments",
                "max_local_variables",
                "max_cyclomatic_complexity",
            ]:
                if config.has_option("complexity", key):
                    complexity_dict[key] = config.getint("complexity", key)
        return complexity_dict

    @staticmethod
    def _parse_duplication_config(
        config: configparser.ConfigParser,
    ) -> dict[str, Union[int, float, bool]]:
        """Extract duplication configuration from config parser."""
        duplication_dict: dict[str, Union[int, float, bool]] = {}
        if config.has_section("duplication"):
            if config.has_option("duplication", "enabled"):
                duplication_dict["enabled"] = config.getboolean(
                    "duplication", "enabled"
                )
            if config.has_option("duplication", "min_duplicate_lines"):
                duplication_dict["min_duplicate_lines"] = config.getint(
                    "duplication", "min_duplicate_lines"
                )
            if config.has_option("duplication", "similarity_threshold"):
                duplication_dict["similarity_threshold"] = config.getfloat(
                    "duplication", "similarity_threshold"
                )
        return duplication_dict

    @staticmethod
    def _parse_boolean_logic_config(
        config: configparser.ConfigParser,
    ) -> dict[str, Union[int, bool]]:
        """Extract boolean logic configuration from config parser."""
        boolean_dict: dict[str, Union[int, bool]] = {}
        if config.has_section("boolean_logic"):
            if config.has_option("boolean_logic", "enabled"):
                boolean_dict["enabled"] = config.getboolean("boolean_logic", "enabled")
            if config.has_option("boolean_logic", "max_boolean_operators"):
                boolean_dict["max_boolean_operators"] = config.getint(
                    "boolean_logic", "max_boolean_operators"
                )
        return boolean_dict

    @staticmethod
    def _parse_enabled_flag(
        config: configparser.ConfigParser, section: str
    ) -> dict[str, bool]:
        """Extract simple enabled flag from a config section."""
        result: dict[str, bool] = {}
        if config.has_section(section) and config.has_option(section, "enabled"):
            result["enabled"] = config.getboolean(section, "enabled")
        return result

    @staticmethod
    def _parse_exclude_patterns(config: configparser.ConfigParser) -> list[str]:
        """Extract exclude patterns from config parser."""
        exclude_list: list[str] = []
        if config.has_section("general") and config.has_option(
            "general", "exclude_patterns"
        ):
            patterns_str = config.get("general", "exclude_patterns")
            # Parse comma-separated patterns
            exclude_list = [
                pattern.strip()
                for pattern in patterns_str.split(",")
                if pattern.strip()
            ]
        return exclude_list

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from an INI file.

        Technical note: This method works with dynamic INI data which mypy
        cannot fully type-check. Type ignores are used to suppress Any-related
        warnings while maintaining runtime safety through try-except handling.
        """
        try:
            parser = configparser.ConfigParser()
            parser.read(config_path, encoding="utf-8")

            return cls(
                complexity=ComplexityConfig(**cls._parse_complexity_config(parser)),
                performance=PerformanceConfig(
                    **cls._parse_enabled_flag(parser, "performance")
                ),
                duplication=DuplicationConfig(**cls._parse_duplication_config(parser)),  # type: ignore[arg-type]
                boolean_logic=BooleanLogicConfig(**cls._parse_boolean_logic_config(parser)),  # type: ignore[arg-type]
                loops=LoopsConfig(**cls._parse_enabled_flag(parser, "loops")),
                context_manager=ContextManagerConfig(
                    **cls._parse_enabled_flag(parser, "context_manager")
                ),
                control_flow=ControlFlowConfig(
                    **cls._parse_enabled_flag(parser, "control_flow")
                ),
                dict_operations=DictOperationsConfig(
                    **cls._parse_enabled_flag(parser, "dict_operations")
                ),
                comparisons=ComparisonsConfig(
                    **cls._parse_enabled_flag(parser, "comparisons")
                ),
                exclude_patterns=cls._parse_exclude_patterns(parser),
            )
        except FileNotFoundError:
            return cls()
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}") from e

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file or use defaults."""
        if config_path is not None:
            return cls.from_file(config_path)

        # Try to find pyrefactor.ini in current directory
        ini_file = Path("pyrefactor.ini")
        if ini_file.exists():
            return cls.from_file(ini_file)

        return cls()
