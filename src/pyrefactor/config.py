"""Configuration management for PyRefactor."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


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
        """Load configuration from a TOML file."""
        try:
            with open(config_path, "rb") as f:
                data: dict[str, Any] = tomllib.load(f)  # type: ignore[misc]

            # Extract pyrefactor configuration
            tool_section: dict[str, Any] = data.get("tool", {})  # type: ignore[assignment,misc]
            pyrefactor_config: dict[str, Any] = tool_section.get("pyrefactor", {})  # type: ignore[assignment,misc]

            complexity_dict: dict[str, Any] = pyrefactor_config.get("complexity", {})  # type: ignore[assignment,misc]
            performance_dict: dict[str, Any] = pyrefactor_config.get("performance", {})  # type: ignore[assignment,misc]
            duplication_dict: dict[str, Any] = pyrefactor_config.get("duplication", {})  # type: ignore[assignment,misc]
            boolean_dict: dict[str, Any] = pyrefactor_config.get("boolean_logic", {})  # type: ignore[assignment,misc]
            loops_dict: dict[str, Any] = pyrefactor_config.get("loops", {})  # type: ignore[assignment,misc]
            exclude_list: list[str] = pyrefactor_config.get("exclude_patterns", [])  # type: ignore[assignment,misc]

            return cls(
                complexity=ComplexityConfig(**complexity_dict),  # type: ignore[arg-type,misc]
                performance=PerformanceConfig(**performance_dict),  # type: ignore[arg-type,misc]
                duplication=DuplicationConfig(**duplication_dict),  # type: ignore[arg-type,misc]
                boolean_logic=BooleanLogicConfig(**boolean_dict),  # type: ignore[arg-type,misc]
                loops=LoopsConfig(**loops_dict),  # type: ignore[arg-type,misc]
                exclude_patterns=exclude_list,
            )
        except FileNotFoundError:
            return cls()
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}") from e

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file or use defaults."""
        if config_path:
            return cls.from_file(config_path)

        # Try to find pyproject.toml in current directory
        pyproject = Path("pyproject.toml")
        if pyproject.exists():
            return cls.from_file(pyproject)

        return cls()
