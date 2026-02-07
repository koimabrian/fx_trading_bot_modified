"""Configuration manager singleton for centralized config loading.

Eliminates duplicate yaml.safe_load() calls across 8 files.
Provides singleton pattern with automatic caching.
"""

from pathlib import Path
from typing import Dict

import yaml


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


class ConfigManager:
    """Singleton config manager to eliminate duplication.

    Usage:
        from src.utils.config_manager import ConfigManager
        config = ConfigManager.get_config()

    Benefits:
        - Single source of truth for config
        - Automatic caching (loads once, reuses)
        - Consistent error handling
        - Easy to test and mock
    """

    _instance = None
    _config = None
    _config_path = "src/config/config.yaml"

    @classmethod
    def get_config(cls) -> Dict:
        """Get configuration dictionary (singleton with caching).

        Returns:
            Configuration dictionary from YAML file

        Raises:
            ConfigError: If config file not found or invalid YAML
        """
        if cls._config is None:
            cls._config = cls._load_config()
        return cls._config

    @classmethod
    def _load_config(cls) -> Dict:
        """Load and parse configuration file.

        Returns:
            Configuration dictionary

        Raises:
            ConfigError: If file not found or YAML parsing fails
        """
        try:
            config_path = Path(cls._config_path)
            if not config_path.exists():
                raise ConfigError(f"Configuration file not found: {cls._config_path}")

            with open(cls._config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            if config is None:
                raise ConfigError(
                    f"Configuration file is empty or invalid: {cls._config_path}"
                )

            from src.utils.logging_factory import LoggingFactory
            logger = LoggingFactory.get_logger(__name__)
            logger.debug(f"Configuration loaded from {cls._config_path}")
            return config

        except FileNotFoundError as e:
            raise ConfigError(
                f"Configuration file not found: {cls._config_path}"
            ) from e
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse configuration YAML: {e}") from e
        except Exception as e:
            raise ConfigError(f"Unexpected error loading configuration: {e}") from e

    @classmethod
    def reload_config(cls) -> Dict:
        """Force reload configuration from file.

        Useful for testing or if config file changes during runtime.

        Returns:
            Configuration dictionary
        """
        cls._config = None
        from src.utils.logging_factory import LoggingFactory
        logger = LoggingFactory.get_logger(__name__)
        logger.info("Configuration cache cleared, reloading from file")
        return cls.get_config()

    @classmethod
    def get_nested(cls, key_path: str, default=None):
        """Get nested config value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "live_trading.aggressive_mode")
            default: Default value if key not found

        Returns:
            Config value or default

        Example:
            aggressive = ConfigManager.get_nested("live_trading.aggressive_mode", False)
        """
        config = cls.get_config()
        keys = key_path.split(".")
        value = config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    @classmethod
    def get_section(cls, section: str) -> Dict:
        """Get a specific section of config.

        Args:
            section: Config section name

        Returns:
            Config section as dictionary

        Example:
            live_config = ConfigManager.get_section("live_trading")
        """
        return cls.get_config().get(section, {})
