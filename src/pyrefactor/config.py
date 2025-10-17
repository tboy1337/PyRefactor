"""Configuration management for PyRefactor."""

import tomllib
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
        """Load configuration from a TOML file.

        Technical note: This method works with dynamic TOML data which mypy
        cannot fully type-check. Type ignores are used to suppress Any-related
        warnings while maintaining runtime safety through try-except handling.
        """
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)  # type: ignore[misc]

            # Extract pyrefactor configuration
            tool_section = data.get("tool", {})  # type: ignore[misc,var-annotated]
            pyrefactor_config = tool_section.get("pyrefactor", {})  # type: ignore[misc,var-annotated]

            complexity_dict = pyrefactor_config.get("complexity", {})  # type: ignore[misc,var-annotated]
            performance_dict = pyrefactor_config.get("performance", {})  # type: ignore[misc,var-annotated]
            duplication_dict = pyrefactor_config.get("duplication", {})  # type: ignore[misc,var-annotated]
            boolean_dict = pyrefactor_config.get("boolean_logic", {})  # type: ignore[misc,var-annotated]
            loops_dict = pyrefactor_config.get("loops", {})  # type: ignore[misc,var-annotated]
            exclude_list = pyrefactor_config.get("exclude_patterns", [])  # type: ignore[misc,var-annotated]

            return cls(
                complexity=ComplexityConfig(**complexity_dict),  # type: ignore[misc]
                performance=PerformanceConfig(**performance_dict),  # type: ignore[misc]
                duplication=DuplicationConfig(**duplication_dict),  # type: ignore[misc]
                boolean_logic=BooleanLogicConfig(**boolean_dict),  # type: ignore[misc]
                loops=LoopsConfig(**loops_dict),  # type: ignore[misc]
                exclude_patterns=exclude_list,  # type: ignore[misc]
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

        # Try to find pyproject.toml in current directory
        pyproject = Path("pyproject.toml")
        if pyproject.exists():
            return cls.from_file(pyproject)

        return cls()
