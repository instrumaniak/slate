"""Plugin lifecycle management for Slate.

This module provides the PluginManager class responsible for loading, activating,
deactivating, and managing plugin instances throughout the application lifecycle.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import NamedTuple

from slate.core.plugin_api import AbstractPlugin, ActivityBarItem, PluginContext

logger = logging.getLogger(__name__)


class ActivationResult(NamedTuple):
    """Result of attempting to activate a plugin."""

    plugin_id: str
    success: bool
    error: str | None


class PluginManager:
    """Manages plugin lifecycle: registration, activation, deactivation, and lookup.

    Plugins are registered by class (not instance) and activated on startup.
    Activation order follows registration order. Errors during activation are
    caught and logged; the application continues with remaining plugins.
    """

    def __init__(self, context: PluginContext | None = None) -> None:
        """Initialize PluginManager with optional context.

        Args:
            context: Optional PluginContext for plugin activation. Can be set later.
        """
        # Registry of plugin classes (not yet instantiated)
        self._plugin_classes: list[type[AbstractPlugin]] = []
        # Active plugin instances: {plugin_id: plugin_instance}
        self._active_plugins: dict[str, AbstractPlugin] = {}
        # The PluginContext instance used for all plugin activations
        self._context: PluginContext | None = context

    def register_plugin(self, plugin_class: type[AbstractPlugin]) -> None:
        """Register a plugin class for activation.

        Args:
            plugin_class: A subclass of AbstractPlugin (not an instance).

        Raises:
            ValueError: If a plugin class with the same plugin_id is already registered.
        """
        # Check for duplicate plugin_id
        new_plugin_id = plugin_class().plugin_id  # Temporary instantiation for ID check
        for existing_class in self._plugin_classes:
            existing_instance = existing_class()
            if existing_instance.plugin_id == new_plugin_id:
                raise ValueError(
                    f"Plugin class {plugin_class.__name__} has plugin_id '{new_plugin_id}' "
                    f"which is already registered by {existing_class.__name__}"
                )

        if plugin_class not in self._plugin_classes:
            self._plugin_classes.append(plugin_class)

    def load_plugin(self, plugin_class: type[AbstractPlugin]) -> ActivationResult:
        """Load and activate a single plugin.

        Args:
            plugin_class: A subclass of AbstractPlugin to load.

        Returns:
            ActivationResult indicating success or failure with error details.
        """
        if self._context is None:
            return ActivationResult(
                plugin_id="<unknown>", success=False, error="PluginContext not set on PluginManager"
            )

        try:
            plugin = plugin_class()
            plugin_id = plugin.plugin_id

            # Validate plugin_id is non-empty
            if not plugin_id:
                return ActivationResult(
                    plugin_id="", success=False, error="Plugin returned empty plugin_id"
                )

            # Check for duplicate plugin_id in active plugins
            if plugin_id in self._active_plugins:
                return ActivationResult(
                    plugin_id=plugin_id,
                    success=False,
                    error=f"Plugin with plugin_id '{plugin_id}' is already active",
                )

            plugin.activate(self._context)
            self._active_plugins[plugin_id] = plugin

            return ActivationResult(plugin_id=plugin_id, success=True, error=None)
        except Exception as e:
            plugin_id = "<unknown>"
            with suppress(Exception):
                plugin_id = plugin_class().plugin_id
            return ActivationResult(
                plugin_id=plugin_id,
                success=False,
                error=f"Failed to activate plugin {plugin_class.__name__}: {e}",
            )

    def activate_all(self) -> list[ActivationResult]:
        """Instantiate and activate all registered plugins in order.

        Plugins that fail to activate are logged and skipped. The application
        continues running normally even if some plugins fail.

        Returns:
            List of ActivationResult for each plugin attempted.
        """
        results: list[ActivationResult] = []
        for plugin_class in self._plugin_classes:
            result = self.load_plugin(plugin_class)
            results.append(result)
            if not result.success:
                logger.error(f"Failed to activate plugin {plugin_class.__name__}: {result.error}")
        return results

    def deactivate_all(self) -> None:
        """Call deactivate() on all active plugins during shutdown.

        Errors during deactivation are logged but do not stop the shutdown process.
        Clears the active plugins registry after deactivation.
        """
        for plugin in list(self._active_plugins.values()):
            try:
                plugin.deactivate()
            except Exception as e:
                logger.error(f"Failed to deactivate plugin {plugin.plugin_id}: {e}")
                # Continue deactivating other plugins
        # Clear active plugins after deactivation
        self._active_plugins.clear()

    def get_plugin(self, plugin_id: str) -> AbstractPlugin | None:
        """Get an active plugin instance by its plugin_id.

        Args:
            plugin_id: Unique identifier of the plugin.

        Returns:
            The plugin instance if active, or None if not found.
        """
        return self._active_plugins.get(plugin_id)

    def get_activity_bar_items(self) -> list[ActivityBarItem]:
        """Collect ActivityBarItem objects from all active plugins.

        Plugins may provide activity items via:
        - A method get_activity_bar_items() returning list[ActivityBarItem]
        - An attribute activity_items containing list[ActivityBarItem]

        Returns:
            A list of ActivityBarItem objects, sorted by priority (lowest first).
        """
        items: list[ActivityBarItem] = []
        for plugin in self._active_plugins.values():
            try:
                # Try method first
                if hasattr(plugin, "get_activity_bar_items"):
                    method = plugin.get_activity_bar_items
                    if callable(method):
                        plugin_items = method()
                        if isinstance(plugin_items, list):
                            items.extend(plugin_items)
                # Then try attribute
                elif hasattr(plugin, "activity_items"):
                    plugin_items = plugin.activity_items
                    if isinstance(plugin_items, list):
                        items.extend(plugin_items)
            except Exception as e:
                logger.error(f"Failed to get activity items from plugin {plugin.plugin_id}: {e}")
                # Continue with other plugins
        # Sort by priority (lowest first) - stable sort preserves plugin order for same priority
        return sorted(items, key=lambda item: getattr(item, "priority", 0))

    @property
    def context(self) -> PluginContext | None:
        """The plugin context used for activation (set by host)."""
        return self._context

    @context.setter
    def context(self, value: PluginContext) -> None:
        """Set the PluginContext before activation.

        Args:
            value: PluginContext instance. Must be a PluginContext subclass.

        Raises:
            TypeError: If value is not a PluginContext instance.
            RuntimeError: If context is changed after plugins are activated (stale context warning).
        """
        if not isinstance(value, PluginContext):
            raise TypeError(f"context must be a PluginContext instance, got {type(value).__name__}")

        # Warn if context is changed after activation (potential stale context)
        if self._active_plugins and value != self._context:
            logger.warning(
                "PluginContext changed after plugins were activated. "
                "Plugins may reference stale context. Consider re-activating plugins."
            )

        self._context = value
