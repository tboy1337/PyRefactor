"""Configuration management for PyRefactor."""

import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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
class Config:
    """Main configuration for PyRefactor."""

    complexity: ComplexityConfig = field(default_factory=ComplexityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    duplication: DuplicationConfig = field(default_factory=DuplicationConfig)
    boolean_logic: BooleanLogicConfig = field(default_factory=BooleanLogicConfig)
    loops: LoopsConfig = field(default_factory=LoopsConfig)
    exclude_patterns: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from an INI file.

        Technical note: This method works with dynamic INI data which mypy
        cannot fully type-check. Type ignores are used to suppress Any-related
        warnings while maintaining runtime safety through try-except handling.
        """
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding="utf-8")

            # Extract complexity configuration
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

            # Extract performance configuration
            performance_dict: dict[str, bool] = {}
            if config.has_section("performance"):
                if config.has_option("performance", "enabled"):
                    performance_dict["enabled"] = config.getboolean(
                        "performance", "enabled"
                    )

            # Extract duplication configuration
            duplication_dict: dict[str, int | float | bool] = {}
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

            # Extract boolean logic configuration
            boolean_dict: dict[str, int | bool] = {}
            if config.has_section("boolean_logic"):
                if config.has_option("boolean_logic", "enabled"):
                    boolean_dict["enabled"] = config.getboolean(
                        "boolean_logic", "enabled"
                    )
                if config.has_option("boolean_logic", "max_boolean_operators"):
                    boolean_dict["max_boolean_operators"] = config.getint(
                        "boolean_logic", "max_boolean_operators"
                    )

            # Extract loops configuration
            loops_dict: dict[str, bool] = {}
            if config.has_section("loops"):
                if config.has_option("loops", "enabled"):
                    loops_dict["enabled"] = config.getboolean("loops", "enabled")

            # Extract exclude patterns
            exclude_list: list[str] = []
            if config.has_section("general"):
                if config.has_option("general", "exclude_patterns"):
                    patterns_str = config.get("general", "exclude_patterns")
                    # Parse comma-separated patterns
                    exclude_list = [
                        pattern.strip()
                        for pattern in patterns_str.split(",")
                        if pattern.strip()
                    ]

            return cls(
                complexity=ComplexityConfig(**complexity_dict),
                performance=PerformanceConfig(**performance_dict),
                duplication=DuplicationConfig(**duplication_dict),  # type: ignore[arg-type]
                boolean_logic=BooleanLogicConfig(**boolean_dict),  # type: ignore[arg-type]
                loops=LoopsConfig(**loops_dict),
                exclude_patterns=exclude_list,
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
