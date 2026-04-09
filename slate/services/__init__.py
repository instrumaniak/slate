"""Services layer - Business logic, zero GTK.

This module exports the core services for the Slate editor.
Services are registered with the service registry for PluginContext access.
"""

import threading

from slate.services.config_service import DEFAULT_CONFIG, ConfigService
from slate.services.file_service import FileService
from slate.services.git_service import GitService
from slate.services.plugin_manager import PluginManager
from slate.services.theme_service import ThemeService

__all__ = [
    "ConfigService",
    "DEFAULT_CONFIG",
    "FileService",
    "GitService",
    "PluginManager",
    "ThemeService",
    "get_config_service",
    "get_file_service",
    "get_git_service",
    "get_plugin_manager",
    "get_theme_service",
]

# Service instances (lazy initialization)
_config_service: ConfigService | None = None
_theme_service: ThemeService | None = None
_file_service: FileService | None = None
_git_service: GitService | None = None

# Locks for thread-safe singleton initialization
_config_lock = threading.Lock()
_theme_lock = threading.Lock()
_file_lock = threading.Lock()
_git_lock = threading.Lock()


def get_config_service() -> ConfigService:
    """Get or create the ConfigService singleton.

    Returns:
        The ConfigService instance.
    """
    global _config_service
    if _config_service is None:
        with _config_lock:
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
        with _theme_lock:
            if _theme_service is None:
                _theme_service = ThemeService(config_service=get_config_service())
    return _theme_service


def get_file_service() -> FileService:
    """Get or create the FileService singleton.

    Returns:
        The FileService instance.
    """
    global _file_service
    if _file_service is None:
        with _file_lock:
            if _file_service is None:
                _file_service = FileService()
    return _file_service


def get_git_service() -> GitService:
    """Get or create the GitService singleton.

    Returns:
        The GitService instance.
    """
    global _git_service
    if _git_service is None:
        with _git_lock:
            if _git_service is None:
                _git_service = GitService()
    return _git_service


_plugin_manager: PluginManager | None = None
_plugin_manager_lock = threading.Lock()


def get_plugin_manager() -> PluginManager:
    """Get or create the PluginManager singleton.

    Returns:
        The PluginManager instance.
    """
    global _plugin_manager
    if _plugin_manager is None:
        with _plugin_manager_lock:
            if _plugin_manager is None:
                _plugin_manager = PluginManager()
                _plugin_manager.register_plugin(
                    __import__(
                        "slate.plugins.core.file_explorer", fromlist=["FileExplorerPlugin"]
                    ).FileExplorerPlugin
                )
                _plugin_manager.register_plugin(
                    __import__(
                        "slate.plugins.core.source_control", fromlist=["SourceControlPlugin"]
                    ).SourceControlPlugin
                )
    return _plugin_manager
