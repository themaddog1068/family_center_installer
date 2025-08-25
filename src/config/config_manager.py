"""Configuration manager for the Family Center application."""

import json
import os
from pathlib import Path
from typing import Any

from src.config.environment import get_environment_config


class ConfigManager:
    """Manages application configuration loading and validation using JSON files like the original."""

    def __init__(self, config_path: str = "config/config.json", env: str = None):
        """Initialize the configuration manager.

        Args:
            config_path: Path to the base JSON configuration file
            env: Optional environment string. If not provided, uses ENV environment variable.
        """
        self.config_path = config_path
        self.env_config = get_environment_config(env, config_dir=Path("config"))
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from JSON files, merging default and environment-specific configs."""
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

        self.config = self._deep_merge(base_config, env_config)
        self._validate_config()

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Recursively merge two dictionaries."""
        result = base.copy()
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        required_sections = ["google_drive", "slideshow", "display", "logging"]
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")

        # Validate media paths
        media_path = self.config["google_drive"]["local_media_path"]
        if not os.path.exists(media_path):
            os.makedirs(media_path, exist_ok=True)

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
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def reload(self) -> None:
        """Reload configuration from file."""
        self.load_config()

    def to_dict(self) -> dict[str, Any]:
        """Convert the configuration to a dictionary.

        Returns:
            The configuration as a dictionary.
        """
        return self.config

    def save_config(self) -> None:
        """Save the current configuration to the JSON file."""
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2, sort_keys=False)

    def set_config(self, new_config: dict[str, Any]) -> None:
        """Replace the current config dict and validate it."""
        self.config = new_config
        self._validate_config()
