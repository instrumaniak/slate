"""Plugin API contracts for Slate.

This module defines the core plugin system interfaces:
- AbstractPlugin: Base class all plugins must inherit from
- PluginContext: Context provided to plugins during activation
- HostUIBridge: Bridge for plugins to register UI elements with the host
- ActivityBarItem: Data structure for activity bar entries
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# ==================== AbstractPlugin ====================


class AbstractPlugin(ABC):
    """Abstract base class that all plugins must inherit from.

    Plugins are instantiated and activated by the PluginManager during startup.

    Activity bar support:
    - Plugins can optionally implement get_activity_bar_items() -> list[ActivityBarItem]
    - Or provide an activity_items attribute of type list[ActivityBarItem]
    """

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for this plugin (snake_case)."""
        ...

    @abstractmethod
    def activate(self, context: PluginContext) -> None:
        """Called when the plugin is activated.

        Plugins should register panels, actions, dialogs, and subscribe to events here.

        Args:
            context: The plugin context providing access to services, config, and host bridge.
        """
        ...

    def deactivate(self) -> None:
        """Called when the plugin is being deactivated.

        Override this to cleanup resources (unsubscribe from events, stop threads, etc.).
        The default implementation does nothing.

        Note: Plugins holding resources (file handles, sockets, threads) SHOULD override
        this method to properly clean up.
        """
        pass  # Intentional no-op for plugins that don't need cleanup


# ==================== PluginContext ====================


class PluginContext(ABC):
    """Context object provided to a plugin during activation.

    Gives plugins access to:
    - Services via get_service()
    - Configuration via get_config()/set_config()
    - Event bus via emit()
    - Host UI bridge via host_bridge property
    """

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for this plugin (snake_case)."""
        ...

    @abstractmethod
    def get_service(self, service_id: str) -> Any:
        """Get a service instance by its registered ID.

        Args:
            service_id: String identifier (e.g., "file", "git", "config").

        Returns:
            The service instance.

        Raises:
            KeyError: If no service is registered with the given ID.
        """
        ...

    @abstractmethod
    def get_config(self, section: str, key: str) -> str:
        """Get a configuration value.

        Args:
            section: Config section (e.g., "plugin.file_explorer").
            key: Configuration key within the section.

        Returns:
            The configuration value as a string, or empty string if not found.
        """
        ...

    @abstractmethod
    def set_config(self, section: str, key: str, value: str) -> None:
        """Set a configuration value.

        Args:
            section: Config section.
            key: Configuration key.
            value: Value to set.
        """
        ...

    @abstractmethod
    def emit(self, event: Any) -> None:
        """Emit an event to the global EventBus.

        All other plugins and services can subscribe to and receive these events.

        Args:
            event: An event object (typically from slate.core.events).
        """
        ...

    @property
    @abstractmethod
    def host_bridge(self) -> HostUIBridge:
        """Get the host UI bridge for registering panels, actions, and dialogs."""
        ...


# ==================== HostUIBridge ====================


class HostUIBridge(ABC):
    """Abstract bridge that the host application implements.

    Plugins use this bridge to register UI elements (panels, actions, dialogs)
    without directly depending on the host's UI layer.
    """

    @abstractmethod
    def register_panel(
        self, plugin_id: str, panel_id: str, widget: Any, title: str, icon_name: str
    ) -> None:
        """Register a panel widget in the side panel area.

        Args:
            plugin_id: ID of the plugin registering the panel.
            panel_id: Unique ID for this panel within the plugin.
            widget: The GTK widget to display in the panel (lazy import allowed).
            title: Panel title for display.
            icon_name: Icon name from the icon theme.
        """
        ...

    @abstractmethod
    def register_action(
        self, plugin_id: str, action_id: str, callback: Callable, shortcut: str | None = None
    ) -> None:
        """Register an application-level action (menu item or keyboard shortcut).

        Args:
            plugin_id: ID of the plugin registering the action.
            action_id: Unique action identifier (namespaced with dots, e.g., "search.focus").
            callback: Callable to invoke when action is activated.
            shortcut: Optional keyboard shortcut string (e.g., "<Ctrl>F").
        """
        ...

    @abstractmethod
    def register_dialog(self, plugin_id: str, dialog_id: str, factory: Callable[..., Any]) -> None:
        """Register a dialog factory.

        Args:
            plugin_id: ID of the plugin registering the dialog.
            dialog_id: Unique identifier for this dialog.
            factory: Callable that returns a GTK dialog widget when invoked.
        """
        ...

    def show_notification(self, message: str, timeout_ms: int = 3000) -> None:
        """Show a toast notification to the user.

        This is a convenience method provided by the host. Plugins can call this
        directly on the HostUIBridge instance.

        Args:
            message: Notification text.
            timeout_ms: Time in milliseconds before the notification auto-dismisses.
        """
        pass  # Host implementation provides this; plugins can call without error if not implemented


# ==================== ActivityBarItem ====================


@dataclass(frozen=True)
class ActivityBarItem:
    """Data item representing an activity bar entry for a plugin.

    These are returned by PluginManager.get_activity_bar_items() and used by
    the UI to populate the activity bar (side pane with plugin icons).
    """

    plugin_id: str
    icon_name: str
    title: str
    priority: int = 0
