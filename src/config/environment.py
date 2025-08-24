from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Environment(str, Enum):
    """Environment types for the application."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentConfig(BaseModel):
    """Base configuration for all environments."""

    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    config_dir: Path = Field(default=Path("config"))

    class Config:
        """Pydantic model configuration."""

        use_enum_values = True


class DevelopmentConfig(EnvironmentConfig):
    """Development environment configuration."""

    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=True)
    log_level: str = Field(default="DEBUG")


class StagingConfig(EnvironmentConfig):
    """Staging environment configuration."""

    environment: Environment = Field(default=Environment.STAGING)
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")


class ProductionConfig(EnvironmentConfig):
    """Production environment configuration."""

    environment: Environment = Field(default=Environment.PRODUCTION)
    debug: bool = Field(default=False)
    log_level: str = Field(default="WARNING")


def get_environment_config(
    env: str | None = None, config_dir: Path | None = None
) -> EnvironmentConfig:
    """
    Get the appropriate configuration based on the environment.

    Args:
        env: Optional environment string. If not provided, uses ENV environment variable.
        config_dir: Optional Path to config directory.

    Returns:
        EnvironmentConfig: The appropriate configuration object.
    """
    if env is None:
        env = Environment.DEVELOPMENT

    print(
        f"DEBUG: get_environment_config called with env={env}, config_dir={config_dir}"
    )
    env_str = str(env).lower()
    config_map = {
        Environment.DEVELOPMENT.value: DevelopmentConfig,
        Environment.STAGING.value: StagingConfig,
        Environment.PRODUCTION.value: ProductionConfig,
    }
    config_class = config_map.get(env_str, DevelopmentConfig)
    if config_dir is not None:
        return config_class(config_dir=config_dir)
    return config_class()
