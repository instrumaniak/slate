"""Configuration service for Slate - handles config persistence via configparser.

Zero GTK imports at module level - pure Python implementation.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
from configparser import ConfigParser
from configparser import Error as ConfigParserError
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# DEFAULT_CONFIG per PRD specification (architecture.md lines 175-208)
# All values must be strings for configparser compatibility
DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "editor": {
        "font": "Monospace 13",
        "tab_width": "4",
        "insert_spaces": "true",
        "show_line_numbers": "true",
        "highlight_current_line": "true",
        "word_wrap": "false",
        "auto_indent": "true",
        "theme_mode": "auto",
        "light_scheme": "Adwaita",
        "dark_scheme": "Adwaita-dark",
        "explicit_scheme": "Adwaita",
    },
    "app": {
        "color_mode": "system",
        "last_folder": "",
        "active_panel": "",
        "side_panel_width": "220",
        "side_panel_visible": "true",
        "window_width": "1200",
        "window_height": "800",
        "window_maximized": "false",
    },
    "plugin.search": {
        "include_hidden": "false",
        "last_glob_filter": "",
    },
    "plugin.source_control": {
        "auto_refresh": "true",
    },
    "plugin.file_explorer": {
        "show_hidden_files": "false",
    },
}

# Reserved characters that could cause INI injection or parsing issues
_INVALID_SECTION_CHARS: Final[set[str]] = set("[]\n\r")
_INVALID_KEY_CHARS: Final[set[str]] = set("=:\n\r")
_INVALID_VALUE_CHARS: Final[set[str]] = set("\n\r")


class ConfigService:
    """Service for managing configuration persistence.

    Handles loading, saving, and accessing configuration values stored
    in ~/.config/slate/config.ini. Creates default config if file is missing.

    Zero GTK imports - uses only stdlib (configparser, pathlib).

    Service ID: "config" (for PluginContext.get_service())
    """

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize ConfigService.

        Args:
            config_path: Optional custom config file path. Defaults to ~/.config/slate/config.ini

        Raises:
            ValueError: If config_path contains path traversal sequences.
        """
        if config_path is None:
            try:
                home = Path.home()
            except RuntimeError:
                # HOME env var not set - use fallback
                home = Path(os.environ.get("HOME", os.path.expanduser("~")))
                if not home or home == Path("."):
                    home = Path(tempfile.gettempdir()) / "slate-config"
            self._config_path = home / ".config" / "slate" / "config.ini"
        else:
            # Validate path to prevent traversal attacks
            path_obj = Path(config_path)
            if not path_obj.is_absolute():
                raise ValueError(f"Invalid config path (must be absolute): {config_path}")
            # Resolve to check for path traversal
            try:
                resolved = path_obj.resolve()
                # Check if resolved path is within reasonable bounds
                # (allow any absolute path, but check for traversal patterns)
                if ".." in str(path_obj):
                    raise ValueError(
                        f"Invalid config path (path traversal detected): {config_path}"
                    )
                self._config_path = resolved
            except (OSError, ValueError) as e:
                raise ValueError(f"Invalid config path: {config_path}") from e

        self._config = ConfigParser(interpolation=None)
        self._lock = threading.RLock()
        self._load_config()

    def _load_config(self) -> None:
        """Load config from disk or create with defaults if missing."""
        with self._lock:
            config_loaded = False
            backup_path = None

            # Ensure config directory exists
            try:
                self._config_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to create config directory {self._config_path.parent}: {e}")
                raise

            if self._config_path.exists():
                # Backup existing config before any modifications
                try:
                    backup_path = self._config_path.with_suffix(".ini.backup")
                    shutil.copy2(self._config_path, backup_path)
                except (OSError, PermissionError) as e:
                    logger.warning(f"Failed to create config backup: {e}")

                # Read existing config
                try:
                    self._config.read(self._config_path, encoding="utf-8")
                    config_loaded = True
                except (ConfigParserError, OSError) as e:
                    logger.warning(f"Failed to read config file {self._config_path}: {e}")
                    # Try to restore from backup if available
                    if backup_path and backup_path.exists():
                        try:
                            self._config.read(backup_path, encoding="utf-8")
                            config_loaded = True
                            logger.info("Restored config from backup")
                        except (ConfigParserError, OSError) as e2:
                            logger.error(f"Failed to restore from backup: {e2}")

            # Merge with defaults (adds any missing sections/keys)
            self._ensure_defaults()

            # Save merged config back to disk (creates file if it was missing or corrupted)
            if not config_loaded or self._config_path.stat().st_size == 0:
                self._save_config()

    def _ensure_defaults(self) -> None:
        """Ensure all DEFAULT_CONFIG sections and keys exist in config."""
        for section, keys in DEFAULT_CONFIG.items():
            if not self._config.has_section(section):
                self._config.add_section(section)
            for key, value in keys.items():
                if not self._config.has_option(section, key):
                    self._config.set(section, key, value)

    def _save_config(self) -> None:
        """Save current config to disk atomically with proper permissions."""
        with self._lock:
            # Write to temp file in same directory (atomic rename)
            temp_path = self._config_path.with_suffix(".ini.tmp")
            try:
                # Write to temp file with restricted permissions from the start
                fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        self._config.write(f)
                except:
                    os.close(fd)
                    raise

                # Atomic rename (overwrites existing)
                os.replace(temp_path, self._config_path)

            except PermissionError as e:
                logger.error(f"Permission denied writing config to {self._config_path}: {e}")
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
                raise
            except OSError as e:
                logger.error(f"Failed to write config to {self._config_path}: {e}")
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink()
                raise

    def _validate_input(self, section: str, key: str, value: str | None = None) -> None:
        """Validate section, key, and value to prevent INI injection.

        Raises:
            ValueError: If any input contains invalid characters.
        """
        if not section or not isinstance(section, str):
            raise ValueError(f"Section must be a non-empty string, got {type(section).__name__}")
        if any(c in section for c in _INVALID_SECTION_CHARS):
            raise ValueError(f"Section contains invalid characters: {section!r}")

        if not key or not isinstance(key, str):
            raise ValueError(f"Key must be a non-empty string, got {type(key).__name__}")
        if any(c in key for c in _INVALID_KEY_CHARS):
            raise ValueError(f"Key contains invalid characters: {key!r}")

        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"Value must be a string, got {type(value).__name__}")
            if any(c in value for c in _INVALID_VALUE_CHARS):
                raise ValueError(f"Value contains invalid characters: {value!r}")

    def get(self, section: str, key: str) -> str | None:
        """Get a configuration value.

        Args:
            section: Config section (e.g., "editor", "app").
            key: Configuration key within the section.

        Returns:
            The configuration value as a string, or None if not found.
        """
        self._validate_input(section, key)

        with self._lock:
            try:
                return self._config.get(section, key)
            except (ConfigParserError, KeyError):
                return None

    def set(self, section: str, key: str, value: str) -> None:
        """Set a configuration value and persist immediately.

        Args:
            section: Config section. Will be created if it doesn't exist.
            key: Configuration key.
            value: Value to set.

        Raises:
            ValueError: If section, key, or value contains invalid characters.
            OSError: If unable to write to config file.
        """
        self._validate_input(section, key, value)

        with self._lock:
            if not self._config.has_section(section):
                self._config.add_section(section)

            self._config.set(section, key, value)
            self._save_config()

    def get_all(self) -> dict[str, dict[str, str]]:
        """Get all configuration as a nested dictionary.

        Returns:
            Dictionary mapping section names to dictionaries of key-value pairs.
            Includes both regular sections and any default section values.
        """
        with self._lock:
            result: dict[str, dict[str, str]] = {}

            # Include default section if present
            if self._config.defaults():
                result["DEFAULT"] = dict(self._config.defaults())

            # Include all regular sections
            for section_name in self._config.sections():
                result[section_name] = dict(self._config.items(section_name))

            return result
