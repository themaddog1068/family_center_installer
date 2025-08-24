"""
Utility functions for the Python project.
"""

import json
import os
from pathlib import Path
from typing import Any


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dict containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        config_data = json.load(f)
        # Ensure we return a Dict[str, Any]
        if not isinstance(config_data, dict):
            raise ValueError(
                f"Configuration file must contain a JSON object, got {type(config_data)}"
            )
        return config_data


def save_config(config: dict[str, Any], config_path: str | Path) -> None:
    """Save configuration to a JSON file.

    Args:
        config: Configuration dictionary to save
        config_path: Path where to save the configuration
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_env_var(key: str, default: str | None = None) -> str | None:
    """Get environment variable with optional default.

    Args:
        key: Environment variable name
        default: Default value if variable not found

    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object of the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
