"""Services layer - Business logic, zero GTK.

This module exports the core services for the Slate editor.
Services are registered with the service registry for PluginContext access.
"""

from slate.services.config_service import ConfigService, DEFAULT_CONFIG
from slate.services.theme_service import ThemeService

__all__ = [
    "ConfigService",
    "DEFAULT_CONFIG",
    "ThemeService",
    "get_config_service",
    "get_theme_service",
]

# Service instances (lazy initialization)
_config_service: ConfigService | None = None
_theme_service: ThemeService | None = None


def get_config_service() -> ConfigService:
    """Get or create the ConfigService singleton.

    Returns:
        The ConfigService instance.
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


def get_theme_service() -> ThemeService:
    """Get or create the ThemeService singleton.

    Returns:
        The ThemeService instance.
    """
    global _theme_service
    if _theme_service is None:
        _theme_service = ThemeService(config_service=get_config_service())
    return _theme_service
