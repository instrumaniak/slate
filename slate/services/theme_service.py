"""Theme service for Slate - handles theme resolution and system detection.

Zero GTK imports at module level - lazy imports inside methods only.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from slate.core.event_bus import EventBus
from slate.core.events import ThemeChangedEvent

if TYPE_CHECKING:
    from slate.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class ThemeService:
    """Service for managing theme resolution and system theme detection.

    Handles:
    - Color mode resolution (light/dark/system)
    - System theme detection via GTK/Adwaita
    - Editor color scheme mapping
    - Theme change event emission

    Zero GTK imports at module level - lazy imports inside methods only
    for system theme detection.

    Service ID: "theme" (for PluginContext.get_service())
    """

    def __init__(self, config_service: "ConfigService" | None = None) -> None:
        """Initialize ThemeService.

        Args:
            config_service: ConfigService instance for persistence.
                          Expected to provide get(section, key) and set(section, key, value).
        """
        self._config_service = config_service
        self._mode_change_callbacks: list[Callable[[str, bool, str], None]] = []
        self._lock = threading.RLock()

        # Load saved color mode from config
        self._current_color_mode = self._load_color_mode()

    def _load_color_mode(self) -> str:
        """Load color mode from config service."""
        if self._config_service is None:
            return "system"

        try:
            saved_mode = self._config_service.get("app", "color_mode")
            if saved_mode in ("light", "dark", "system"):
                return saved_mode
        except Exception as e:
            logger.warning(f"Failed to load color mode from config: {e}")

        return "system"

    def resolve_theme(self) -> tuple[str, bool, str]:
        """Resolve current theme to color mode, dark flag, and editor scheme.

        Returns:
            Tuple of (color_mode, is_dark, editor_scheme)
            - color_mode: "light" | "dark" | "system"
            - is_dark: True if resolved theme is dark
            - editor_scheme: GtkSourceView scheme ID ("Adwaita" or "Adwaita-dark")
        """
        with self._lock:
            color_mode = self._current_color_mode

            if color_mode == "system":
                is_dark = self._detect_system_theme()
            elif color_mode == "dark":
                is_dark = True
            else:  # light
                is_dark = False

            editor_scheme = "Adwaita-dark" if is_dark else "Adwaita"

            return (color_mode, is_dark, editor_scheme)

    def _detect_system_theme(self) -> bool:
        """Detect if system prefers dark theme.

        Uses lazy imports to avoid GTK at module level.
        First tries Adwaita StyleManager, falls back to Gtk.Settings.

        Returns:
            True if system prefers dark theme, False otherwise.
        """
        try:
            # Try Adwaita first (modern GTK4 approach)
            import gi

            gi.require_version("Adw", "1")
            from gi.repository import Adw  # type: ignore[import-untyped]

            style_manager = Adw.StyleManager.get_default()
            if style_manager is None:
                raise RuntimeError("Adw.StyleManager.get_default() returned None")

            color_scheme = style_manager.get_color_scheme()

            # Adw.ColorScheme enum values:
            # 0 = DEFAULT, 1 = PREFER_DARK, 2 = PREFER_LIGHT
            return bool(color_scheme == Adw.ColorScheme.PREFER_DARK)
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.debug(f"Adwaita theme detection failed: {e}")

        try:
            # Fallback to Gtk.Settings
            import gi

            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk  # type: ignore[import-untyped]

            settings = Gtk.Settings.get_default()
            if settings is None:
                logger.debug("Gtk.Settings.get_default() returned None")
                return False

            return bool(settings.get_property("gtk-application-prefer-dark-theme"))
        except (ImportError, AttributeError) as e:
            logger.debug(f"GTK theme detection failed: {e}")

        # Default to light if unable to detect
        return False

    def set_color_mode(self, mode: str) -> None:
        """Set color mode and persist to config.

        Args:
            mode: One of "light", "dark", "system"

        Raises:
            ValueError: If mode is not one of the valid options.
        """
        if mode not in ("light", "dark", "system"):
            raise ValueError(f"Invalid color mode: {mode!r}. Must be 'light', 'dark', or 'system'")

        with self._lock:
            # Check if mode actually changed
            if mode == self._current_color_mode:
                return

            # Update current mode first
            self._current_color_mode = mode

            # Persist to config BEFORE emitting event
            if self._config_service is not None:
                try:
                    self._config_service.set("app", "color_mode", mode)
                except Exception as e:
                    logger.error(f"Failed to persist color mode to config: {e}")
                    # Revert to previous mode on persistence failure
                    self._current_color_mode = self._load_color_mode()
                    raise

            # Now emit event (only after successful persistence)
            color_mode, is_dark, editor_scheme = self.resolve_theme()
            event = ThemeChangedEvent(
                color_mode=color_mode, resolved_is_dark=is_dark, editor_scheme=editor_scheme
            )
            try:
                EventBus().emit(event)
            except Exception as e:
                logger.error(f"Failed to emit ThemeChangedEvent: {e}")

            # Notify registered callbacks
            for callback in list(
                self._mode_change_callbacks
            ):  # Copy list to avoid modification during iteration
                try:
                    callback(color_mode, is_dark, editor_scheme)
                except Exception as e:
                    logger.warning(f"Theme change callback failed: {e}")

    def on_mode_changed(self, callback: Callable[[str, bool, str], None]) -> None:
        """Register callback for theme mode changes.

        Args:
            callback: Function to call when theme changes.
                     Signature: (color_mode, is_dark, editor_scheme) -> None

        Raises:
            TypeError: If callback is not callable.
        """
        if not callable(callback):
            raise TypeError(f"Callback must be callable, got {type(callback).__name__}")

        with self._lock:
            # Prevent duplicate registration
            if callback not in self._mode_change_callbacks:
                self._mode_change_callbacks.append(callback)

    def remove_mode_changed_callback(self, callback: Callable[[str, bool, str], None]) -> bool:
        """Unregister a previously registered callback.

        Args:
            callback: The callback function to remove.

        Returns:
            True if callback was found and removed, False otherwise.
        """
        with self._lock:
            if callback in self._mode_change_callbacks:
                self._mode_change_callbacks.remove(callback)
                return True
            return False
