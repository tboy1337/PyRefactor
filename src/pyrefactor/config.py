"""Configuration management for PyRefactor."""

import configparser
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, TypeVar, Union

_ConfigT = TypeVar("_ConfigT")

logger = logging.getLogger(__name__)

_COMPLEXITY_TOML_FIELDS: dict[str, type[object]] = {
    "enabled": bool,
    "max_branches": int,
    "max_nesting_depth": int,
    "max_function_lines": int,
    "max_arguments": int,
    "max_local_variables": int,
    "max_cyclomatic_complexity": int,
}
_PERFORMANCE_TOML_FIELDS: dict[str, type[object]] = {
    "enabled": bool,
    "min_concatenations": int,
    "min_duplicate_calls": int,
}
_DUPLICATION_TOML_FIELDS: dict[str, type[object]] = {
    "enabled": bool,
    "min_duplicate_lines": int,
    "similarity_threshold": float,
}
_BOOLEAN_TOML_FIELDS: dict[str, type[object]] = {
    "enabled": bool,
    "max_boolean_operators": int,
}
_ENABLED_ONLY_TOML_FIELDS: dict[str, type[object]] = {"enabled": bool}


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

    def validate(self) -> None:
        """Validate configuration values and raise ValueError on invalid settings."""
        complexity_fields = {
            "complexity.max_branches": self.complexity.max_branches,
            "complexity.max_nesting_depth": self.complexity.max_nesting_depth,
            "complexity.max_function_lines": self.complexity.max_function_lines,
            "complexity.max_arguments": self.complexity.max_arguments,
            "complexity.max_local_variables": self.complexity.max_local_variables,
            "complexity.max_cyclomatic_complexity": (
                self.complexity.max_cyclomatic_complexity
            ),
        }
        for name, value in complexity_fields.items():
            if value < 1:
                raise ValueError(f"{name} must be >= 1, got {value}")

        if self.performance.min_concatenations < 0:
            raise ValueError(
                "performance.min_concatenations must be >= 0, "
                f"got {self.performance.min_concatenations}"
            )
        if self.performance.min_duplicate_calls < 0:
            raise ValueError(
                "performance.min_duplicate_calls must be >= 0, "
                f"got {self.performance.min_duplicate_calls}"
            )

        if self.duplication.min_duplicate_lines < 2:
            raise ValueError(
                "duplication.min_duplicate_lines must be >= 2, "
                f"got {self.duplication.min_duplicate_lines}"
            )
        threshold = self.duplication.similarity_threshold
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                "duplication.similarity_threshold must be between 0.0 and 1.0, "
                f"got {threshold}"
            )

        if self.boolean_logic.max_boolean_operators < 1:
            raise ValueError(
                "boolean_logic.max_boolean_operators must be >= 1, "
                f"got {self.boolean_logic.max_boolean_operators}"
            )

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
    def _complexity_config_from_ini(
        parser: configparser.ConfigParser,
    ) -> ComplexityConfig:
        """Build ComplexityConfig from INI parser data."""
        defaults = ComplexityConfig()
        parsed = Config._parse_complexity_config(parser)
        return ComplexityConfig(
            enabled=bool(parsed.get("enabled", defaults.enabled)),
            max_branches=int(parsed.get("max_branches", defaults.max_branches)),
            max_nesting_depth=int(
                parsed.get("max_nesting_depth", defaults.max_nesting_depth)
            ),
            max_function_lines=int(
                parsed.get("max_function_lines", defaults.max_function_lines)
            ),
            max_arguments=int(parsed.get("max_arguments", defaults.max_arguments)),
            max_local_variables=int(
                parsed.get("max_local_variables", defaults.max_local_variables)
            ),
            max_cyclomatic_complexity=int(
                parsed.get(
                    "max_cyclomatic_complexity", defaults.max_cyclomatic_complexity
                )
            ),
        )

    @staticmethod
    def _performance_config_from_ini(
        parser: configparser.ConfigParser,
    ) -> PerformanceConfig:
        """Build PerformanceConfig from INI parser data."""
        defaults = PerformanceConfig()
        parsed = Config._parse_performance_config(parser)
        return PerformanceConfig(
            enabled=bool(parsed.get("enabled", defaults.enabled)),
            min_concatenations=int(
                parsed.get("min_concatenations", defaults.min_concatenations)
            ),
            min_duplicate_calls=int(
                parsed.get("min_duplicate_calls", defaults.min_duplicate_calls)
            ),
        )

    @staticmethod
    def _duplication_config_from_ini(
        parser: configparser.ConfigParser,
    ) -> DuplicationConfig:
        """Build DuplicationConfig from INI parser data."""
        defaults = DuplicationConfig()
        parsed = Config._parse_duplication_config(parser)
        return DuplicationConfig(
            enabled=bool(parsed.get("enabled", defaults.enabled)),
            min_duplicate_lines=int(
                parsed.get("min_duplicate_lines", defaults.min_duplicate_lines)
            ),
            similarity_threshold=float(
                parsed.get("similarity_threshold", defaults.similarity_threshold)
            ),
        )

    @staticmethod
    def _boolean_logic_config_from_ini(
        parser: configparser.ConfigParser,
    ) -> BooleanLogicConfig:
        """Build BooleanLogicConfig from INI parser data."""
        defaults = BooleanLogicConfig()
        parsed = Config._parse_boolean_logic_config(parser)
        return BooleanLogicConfig(
            enabled=bool(parsed.get("enabled", defaults.enabled)),
            max_boolean_operators=int(
                parsed.get("max_boolean_operators", defaults.max_boolean_operators)
            ),
        )

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
    def _coerce_list_value(value: object) -> list[str] | None:
        """Coerce a TOML value to a list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [pattern.strip() for pattern in value.split(",") if pattern.strip()]
        return None

    @staticmethod
    def _coerce_bool(value: object) -> bool | None:
        """Coerce a TOML or string value to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "1", "on"}:
                return True
            if normalized in {"false", "no", "0", "off"}:
                return False
        return None

    @staticmethod
    def _coerce_typed_value(
        expected_type: type[object], value: object
    ) -> object | None:
        """Coerce a single TOML value to the expected Python type."""
        if expected_type is bool:
            return Config._coerce_bool(value)
        if expected_type is list:
            return Config._coerce_list_value(value)
        if expected_type in (int, float) and isinstance(value, (int, float, str)):
            try:
                return expected_type(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_section(
        section: dict[str, Any],
        field_types: Mapping[str, type[object]],
        section_name: str = "config",
    ) -> dict[str, Any]:
        """Coerce TOML section values to expected Python types."""
        result: dict[str, Any] = {}
        for key, expected_type in field_types.items():
            if key not in section:
                continue
            raw_value = section[key]
            coerced = Config._coerce_typed_value(expected_type, raw_value)
            if coerced is not None:
                result[key] = coerced
            else:
                logger.warning(
                    "Ignoring invalid %s.%s value %r (expected %s)",
                    section_name,
                    key,
                    raw_value,
                    expected_type.__name__,
                )
        return result

    @staticmethod
    def _dict_section(pyrefactor: dict[str, Any], name: str) -> dict[str, Any]:
        """Return a detector subsection from parsed TOML, or an empty dict."""
        section = pyrefactor.get(name, {})
        return section if isinstance(section, dict) else {}

    @classmethod
    def _build_config_section(
        cls,
        pyrefactor: dict[str, Any],
        name: str,
        config_class: type[_ConfigT],
        field_types: Mapping[str, type[object]],
    ) -> _ConfigT:
        """Build a detector config dataclass from a TOML subsection."""
        return config_class(
            **cls._coerce_section(
                cls._dict_section(pyrefactor, name), field_types, section_name=name
            )
        )

    @staticmethod
    def _parse_toml_exclude_patterns(pyrefactor: dict[str, Any]) -> list[str]:
        """Parse exclude_patterns from a [tool.pyrefactor] table."""
        raw_exclude = pyrefactor.get("exclude_patterns")
        if isinstance(raw_exclude, list):
            return [str(pattern) for pattern in raw_exclude]
        if isinstance(raw_exclude, str):
            return [
                pattern.strip() for pattern in raw_exclude.split(",") if pattern.strip()
            ]
        return []

    @classmethod
    def from_toml_data(cls, data: dict[str, Any]) -> "Config":
        """Load configuration from parsed TOML [tool.pyrefactor] data."""
        tool_section = data.get("tool", {})
        pyrefactor = tool_section.get("pyrefactor", {})
        if not isinstance(pyrefactor, dict):
            raise ValueError("Invalid [tool.pyrefactor] section in configuration")

        config = cls(
            complexity=cls._build_config_section(
                pyrefactor, "complexity", ComplexityConfig, _COMPLEXITY_TOML_FIELDS
            ),
            performance=cls._build_config_section(
                pyrefactor, "performance", PerformanceConfig, _PERFORMANCE_TOML_FIELDS
            ),
            duplication=cls._build_config_section(
                pyrefactor, "duplication", DuplicationConfig, _DUPLICATION_TOML_FIELDS
            ),
            boolean_logic=cls._build_config_section(
                pyrefactor, "boolean_logic", BooleanLogicConfig, _BOOLEAN_TOML_FIELDS
            ),
            loops=cls._build_config_section(
                pyrefactor, "loops", LoopsConfig, _ENABLED_ONLY_TOML_FIELDS
            ),
            context_manager=cls._build_config_section(
                pyrefactor,
                "context_manager",
                ContextManagerConfig,
                _ENABLED_ONLY_TOML_FIELDS,
            ),
            control_flow=cls._build_config_section(
                pyrefactor, "control_flow", ControlFlowConfig, _ENABLED_ONLY_TOML_FIELDS
            ),
            dict_operations=cls._build_config_section(
                pyrefactor,
                "dict_operations",
                DictOperationsConfig,
                _ENABLED_ONLY_TOML_FIELDS,
            ),
            comparisons=cls._build_config_section(
                pyrefactor, "comparisons", ComparisonsConfig, _ENABLED_ONLY_TOML_FIELDS
            ),
            exclude_patterns=cls._parse_toml_exclude_patterns(pyrefactor),
        )
        config.validate()
        return config

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
        if not config_path.is_file():
            raise ValueError(f"Configuration file not found: {config_path}")

        try:
            with config_path.open("rb") as config_file:
                data = tomllib.load(config_file)
            return cls.from_toml_data(data)
        except (
            OSError,
            tomllib.TOMLDecodeError,
            ValueError,
            TypeError,
        ) as e:
            raise ValueError(f"Error loading configuration: {e}") from e

    @classmethod
    def from_ini_file(cls, config_path: Path) -> "Config":
        """Load configuration from an INI file."""
        if not config_path.is_file():
            raise ValueError(f"Configuration file not found: {config_path}")

        try:
            parser = configparser.ConfigParser()
            parser.read(config_path, encoding="utf-8")

            config = cls(
                complexity=cls._complexity_config_from_ini(parser),
                performance=cls._performance_config_from_ini(parser),
                duplication=cls._duplication_config_from_ini(parser),
                boolean_logic=cls._boolean_logic_config_from_ini(parser),
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
            config.validate()
            return config
        except (
            OSError,
            configparser.Error,
            ValueError,
            TypeError,
        ) as e:
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
            try:
                with pyproject.open("rb") as config_file:
                    data = tomllib.load(config_file)
            except (OSError, tomllib.TOMLDecodeError):
                logger.warning(
                    "Failed to read or parse %s; falling back to pyrefactor.ini or defaults",
                    pyproject,
                )
            else:
                if cls._has_pyrefactor_config(data):
                    return cls.from_toml_data(data)

        ini_file = Path("pyrefactor.ini")
        if ini_file.exists():
            return cls.from_ini_file(ini_file)

        config = cls()
        config.validate()
        return config
