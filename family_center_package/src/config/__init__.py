import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional, Union

from src.core.utils import load_config, save_config
from src.utils.config import ConfigError

from .environment import get_environment_config
from .logging_config import setup_logging


class Config:
    """Main configuration manager for the application."""

    def __init__(self, env: str | None = None):
        """
        Initialize configuration manager.

        Args:
            env: Optional environment string. If not provided, uses ENV environment variable.
        """
        config_dir_env = os.environ.get("FAMILY_CENTER_CONFIG_DIR")
        config_dir = Path(config_dir_env) if config_dir_env else None
        self.env_config = get_environment_config(env, config_dir=config_dir)
        self._config_data: dict[str, Any] = {}
        self._load_config()
        self._setup_logging()

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Recursively merge two dictionaries."""
        result = base.copy()
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def _load_config(self) -> None:
        """Load configuration from JSON file, merging default and environment-specific configs."""
        config_dir = self.env_config.config_dir
        env = self.env_config.environment.value
        default_path = config_dir / "config.json"
        env_path = config_dir / f"config.{env}.json"

        base_config = {}
        env_config = {}

        if default_path.exists():
            with open(default_path) as f:
                base_config = json.load(f)
        if env_path.exists():
            with open(env_path) as f:
                env_config = json.load(f)

        self._config_data = self._deep_merge(base_config, env_config)
        print(f"DEBUG: Loaded config (merged): base={default_path}, env={env_path}")
        if not self._config_data:
            print(f"DEBUG: No config data loaded from {default_path} or {env_path}")

    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        log_file = Path("logs") / f"family_center_{self.env_config.environment}.log"
        setup_logging(self.env_config, log_file)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value. Supports nested keys using dot notation.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def __getitem__(self, key: str) -> Any:
        """
        Get configuration value using dictionary syntax.

        Args:
            key: Configuration key

        Returns:
            Configuration value

        Raises:
            KeyError: If key is not found
        """
        if key not in self._config_data:
            raise KeyError(f"Configuration key '{key}' not found")
        return self._config_data[key]

    @property
    def environment(self) -> str:
        """Get current environment name."""
        return self.env_config.environment

    @property
    def debug(self) -> bool:
        """Get debug mode status."""
        return self.env_config.debug

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config_data[key] = value

    def delete(self, key: str) -> None:
        """Delete a configuration key.

        Args:
            key: Configuration key to delete
        """
        if key in self._config_data:
            del self._config_data[key]

    def clear(self) -> None:
        """Clear all configuration data."""
        self._config_data.clear()

    def load(self, config_path: str) -> None:
        """Load configuration from a file.

        Args:
            config_path: Path to the configuration file
        """
        self._config_data = load_config(config_path)

    def save(self, config_path: str) -> None:
        """Save configuration to a file.

        Args:
            config_path: Path where to save the configuration
        """
        save_config(self._config_data, config_path)

    def validate(
        self,
        schema: dict[str, Any],
        required_keys: list[str] | None = None,
        optional_keys: list[str] | None = None,
    ) -> bool:
        """Validate the configuration against a schema.

        Args:
            schema: Dictionary mapping keys to their expected types or validation functions
            required_keys: List of required configuration keys
            optional_keys: List of optional configuration keys

        Returns:
            bool: True if the configuration is valid, False otherwise

        Raises:
            ConfigError: If a required key is missing, an invalid optional key is provided, or the schema is empty
            TypeError: If a value has the wrong type
            ValueError: If a value fails validation
        """
        # Handle empty schema
        if not schema:
            if required_keys:
                raise ConfigError("Schema is empty but required keys are specified")
            return True

        # Check required keys in schema and config data
        if required_keys:
            for key in required_keys:
                if key not in schema:
                    raise ConfigError(f"Required key '{key}' not found in schema")
                if key not in self._config_data:
                    raise ConfigError(f"Required key '{key}' missing from config data")

        # Check optional keys
        if optional_keys:
            for key in optional_keys:
                if key not in schema:
                    raise ConfigError(f"Optional key '{key}' not found in schema")

        # Validate values against schema
        for key, expected_type in schema.items():
            if key not in self._config_data:
                if required_keys and key in required_keys:
                    raise ConfigError(f"Required key '{key}' missing from config data")
                continue

            value = self._config_data[key]
            if isinstance(expected_type, type):
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Value for key '{key}' has wrong type. Expected {expected_type}, got {type(value)}"
                    )
            elif callable(expected_type):
                if not expected_type(value):
                    raise ValueError(f"Value for key '{key}' failed validation")
            elif isinstance(expected_type, dict):
                if not isinstance(value, dict):
                    raise TypeError(
                        f"Value for key '{key}' has wrong type. Expected dict, got {type(value)}"
                    )
                # Recursively validate nested schema
                nested_config = Config()
                nested_config._config_data = value
                nested_config.validate(
                    expected_type, required_keys=None, optional_keys=None
                )
            elif isinstance(expected_type, list):
                if not isinstance(value, list):
                    raise TypeError(
                        f"Value for key '{key}' has wrong type. Expected list, got {type(value)}"
                    )
                # Validate list items
                item_type = expected_type[0]
                for i, item in enumerate(value):
                    if isinstance(item_type, type):
                        if not isinstance(item, item_type):
                            raise TypeError(
                                f"Item {i} in list '{key}' has wrong type. Expected {item_type}, got {type(item)}"
                            )
                    elif callable(item_type):
                        if not item_type(item):
                            raise ValueError(
                                f"Item {i} in list '{key}' failed validation"
                            )

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary.

        Returns:
            The configuration as a dictionary.
        """
        return self._config_data
