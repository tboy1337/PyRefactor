"""Configuration management for PyRefactor."""

import configparser
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Union


@dataclass
class ComplexityConfig:
    """Configuration for complexity detector."""

    enabled: bool = True
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
    min_concatenations: int = 3
    min_duplicate_calls: int = 3


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
    def _parse_complexity_config(
        config: configparser.ConfigParser,
    ) -> dict[str, Union[int, bool]]:
        """Extract complexity configuration from config parser."""
        complexity_dict: dict[str, Union[int, bool]] = {}
        if config.has_section("complexity"):
            if config.has_option("complexity", "enabled"):
                complexity_dict["enabled"] = config.getboolean("complexity", "enabled")
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
    def _parse_performance_config(
        config: configparser.ConfigParser,
    ) -> dict[str, Union[int, bool]]:
        """Extract performance configuration from config parser."""
        performance_dict: dict[str, Union[int, bool]] = {}
        if config.has_section("performance"):
            if config.has_option("performance", "enabled"):
                performance_dict["enabled"] = config.getboolean(
                    "performance", "enabled"
                )
            if config.has_option("performance", "min_concatenations"):
                performance_dict["min_concatenations"] = config.getint(
                    "performance", "min_concatenations"
                )
            if config.has_option("performance", "min_duplicate_calls"):
                performance_dict["min_duplicate_calls"] = config.getint(
                    "performance", "min_duplicate_calls"
                )
        return performance_dict

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
            exclude_list = [
                pattern.strip()
                for pattern in patterns_str.split(",")
                if pattern.strip()
            ]
        return exclude_list

    @staticmethod
    def _coerce_section(
        section: dict[str, Any], field_types: Mapping[str, type[object]]
    ) -> dict[str, Any]:
        """Coerce TOML section values to expected Python types."""
        result: dict[str, Any] = {}
        for key, expected_type in field_types.items():
            if key not in section:
                continue
            value = section[key]
            if expected_type is bool:
                result[key] = bool(value)
            elif expected_type is int:
                result[key] = int(value)
            elif expected_type is float:
                result[key] = float(value)
            elif expected_type is list:
                if isinstance(value, list):
                    result[key] = [str(item) for item in value]
                elif isinstance(value, str):
                    result[key] = [
                        pattern.strip()
                        for pattern in value.split(",")
                        if pattern.strip()
                    ]
        return result

    @classmethod
    def from_toml_data(cls, data: dict[str, Any]) -> "Config":
        """Load configuration from parsed TOML [tool.pyrefactor] data."""
        tool_section = data.get("tool", {})
        pyrefactor = tool_section.get("pyrefactor", {})
        if not isinstance(pyrefactor, dict):
            raise ValueError("Invalid [tool.pyrefactor] section in configuration")

        complexity_fields = {
            "enabled": bool,
            "max_branches": int,
            "max_nesting_depth": int,
            "max_function_lines": int,
            "max_arguments": int,
            "max_local_variables": int,
            "max_cyclomatic_complexity": int,
        }
        performance_fields = {
            "enabled": bool,
            "min_concatenations": int,
            "min_duplicate_calls": int,
        }
        duplication_fields = {
            "enabled": bool,
            "min_duplicate_lines": int,
            "similarity_threshold": float,
        }
        boolean_fields = {"enabled": bool, "max_boolean_operators": int}
        enabled_only = {"enabled": bool}

        complexity_section = pyrefactor.get("complexity", {})
        duplication_section = pyrefactor.get("duplication", {})
        boolean_section = pyrefactor.get("boolean_logic", {})

        exclude_patterns: list[str] = []
        raw_exclude = pyrefactor.get("exclude_patterns")
        if isinstance(raw_exclude, list):
            exclude_patterns = [str(pattern) for pattern in raw_exclude]
        elif isinstance(raw_exclude, str):
            exclude_patterns = [
                pattern.strip() for pattern in raw_exclude.split(",") if pattern.strip()
            ]

        return cls(
            complexity=ComplexityConfig(
                **cls._coerce_section(
                    complexity_section if isinstance(complexity_section, dict) else {},
                    complexity_fields,
                )
            ),
            performance=PerformanceConfig(
                **cls._coerce_section(
                    (
                        pyrefactor.get("performance", {})
                        if isinstance(pyrefactor.get("performance"), dict)
                        else {}
                    ),
                    performance_fields,
                )
            ),
            duplication=DuplicationConfig(
                **cls._coerce_section(
                    (
                        duplication_section
                        if isinstance(duplication_section, dict)
                        else {}
                    ),
                    duplication_fields,
                )
            ),
            boolean_logic=BooleanLogicConfig(
                **cls._coerce_section(
                    boolean_section if isinstance(boolean_section, dict) else {},
                    boolean_fields,
                )
            ),
            loops=LoopsConfig(
                **cls._coerce_section(
                    (
                        pyrefactor.get("loops", {})
                        if isinstance(pyrefactor.get("loops"), dict)
                        else {}
                    ),
                    enabled_only,
                )
            ),
            context_manager=ContextManagerConfig(
                **cls._coerce_section(
                    (
                        pyrefactor.get("context_manager", {})
                        if isinstance(pyrefactor.get("context_manager"), dict)
                        else {}
                    ),
                    enabled_only,
                )
            ),
            control_flow=ControlFlowConfig(
                **cls._coerce_section(
                    (
                        pyrefactor.get("control_flow", {})
                        if isinstance(pyrefactor.get("control_flow"), dict)
                        else {}
                    ),
                    enabled_only,
                )
            ),
            dict_operations=DictOperationsConfig(
                **cls._coerce_section(
                    (
                        pyrefactor.get("dict_operations", {})
                        if isinstance(pyrefactor.get("dict_operations"), dict)
                        else {}
                    ),
                    enabled_only,
                )
            ),
            comparisons=ComparisonsConfig(
                **cls._coerce_section(
                    (
                        pyrefactor.get("comparisons", {})
                        if isinstance(pyrefactor.get("comparisons"), dict)
                        else {}
                    ),
                    enabled_only,
                )
            ),
            exclude_patterns=exclude_patterns,
        )

    @staticmethod
    def _has_pyrefactor_config(data: dict[str, Any]) -> bool:
        """Return True when parsed TOML contains a non-empty [tool.pyrefactor] table."""
        tool_section = data.get("tool")
        if not isinstance(tool_section, dict):
            return False
        pyrefactor = tool_section.get("pyrefactor")
        return isinstance(pyrefactor, dict) and bool(pyrefactor)

    @classmethod
    def from_toml_file(cls, config_path: Path) -> "Config":
        """Load configuration from a TOML file."""
        try:
            with config_path.open("rb") as config_file:
                data = tomllib.load(config_file)
            return cls.from_toml_data(data)
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}") from e

    @classmethod
    def from_ini_file(cls, config_path: Path) -> "Config":
        """Load configuration from an INI file."""
        if not config_path.is_file():
            return cls()

        try:
            parser = configparser.ConfigParser()
            parser.read(config_path, encoding="utf-8")

            return cls(
                complexity=ComplexityConfig(**cls._parse_complexity_config(parser)),  # type: ignore[arg-type]
                performance=PerformanceConfig(**cls._parse_performance_config(parser)),  # type: ignore[arg-type]
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
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}") from e

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from a TOML or INI file."""
        suffix = config_path.suffix.lower()
        if suffix in {".toml", ".tml"}:
            return cls.from_toml_file(config_path)
        return cls.from_ini_file(config_path)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from file or use defaults."""
        if config_path is not None:
            return cls.from_file(config_path)

        pyproject = Path("pyproject.toml")
        if pyproject.is_file():
            with pyproject.open("rb") as config_file:
                data = tomllib.load(config_file)
            if cls._has_pyrefactor_config(data):
                return cls.from_toml_data(data)

        ini_file = Path("pyrefactor.ini")
        if ini_file.exists():
            return cls.from_ini_file(ini_file)

        return cls()
