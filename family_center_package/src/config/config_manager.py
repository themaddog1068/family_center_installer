"""Configuration manager for the Family Center application."""

import os
from typing import Any

import yaml


class ConfigManager:
    """Manages application configuration loading and validation."""

    def __init__(self, config_path: str = "src/config/config.yaml"):
        """Initialize the configuration manager.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            self._validate_config()
        except FileNotFoundError as err:
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}"
            ) from err
        except yaml.YAMLError as err:
            raise ValueError(f"Error parsing YAML configuration: {str(err)}") from err

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

    def get(self, section: str, key: str | None = None) -> Any:
        """Get configuration value.

        Args:
            section: Configuration section name
            key: Optional key within the section

        Returns:
            Configuration value or section
        """
        if section not in self.config:
            raise KeyError(f"Configuration section not found: {section}")

        if key is None:
            return self.config[section]

        if key not in self.config[section]:
            raise KeyError(f"Configuration key not found: {section}.{key}")

        return self.config[section][key]

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
        """Save the current configuration to the YAML file."""
        import yaml

        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.config, f, sort_keys=False, allow_unicode=True)

    def set_config(self, new_config: dict[str, Any]) -> None:
        """Replace the current config dict and validate it."""
        self.config = new_config
        self._validate_config()
