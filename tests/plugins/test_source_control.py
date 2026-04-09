"""Tests for SourceControlPlugin — plugin activation and registration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from slate.core.plugin_api import AbstractPlugin, PluginContext
from slate.plugins.core.source_control import SourceControlPlugin


class MockHostBridge:
    """Mock HostUIBridge for testing plugin registration."""

    def __init__(self) -> None:
        self.registered_panels: list[dict[str, Any]] = []
        self.registered_actions: list[dict[str, Any]] = []
        self.focused_panels: list[str] = []

    def register_panel(
        self,
        plugin_id: str,
        panel_id: str,
        widget: Any,
        title: str,
        icon_name: str,
    ) -> None:
        self.registered_panels.append(
            {
                "plugin_id": plugin_id,
                "panel_id": panel_id,
                "widget": widget,
                "title": title,
                "icon_name": icon_name,
            }
        )

    def register_action(
        self, plugin_id: str, action_id: str, callback: Any, shortcut: str | None = None
    ) -> None:
        self.registered_actions.append(
            {
                "plugin_id": plugin_id,
                "action_id": action_id,
                "callback": callback,
                "shortcut": shortcut,
            }
        )

    def register_dialog(self, plugin_id: str, dialog_id: str, factory: Any) -> None:
        pass

    def focus_panel(self, plugin_id: str) -> None:
        self.focused_panels.append(plugin_id)

    def set_activity_badge(self, plugin_id: str, badge_text: str) -> None:
        pass


class MockPluginContext(PluginContext):
    """Concrete PluginContext for testing SourceControlPlugin."""

    def __init__(self, services: dict[str, Any] | None = None) -> None:
        self._services = services or {}
        self._bridge = MockHostBridge()
        self._emitted_events: list[Any] = []
        self.event_bus = MagicMock()

    @property
    def plugin_id(self) -> str:
        return "source_control"

    @property
    def host_bridge(self):
        return self._bridge

    def get_service(self, service_name: str) -> Any:
        return self._services.get(service_name)

    def get_config(self, section: str, key: str) -> str:
        return ""

    def set_config(self, section: str, key: str, value: str) -> None:
        pass

    def emit(self, event: Any) -> None:
        self._emitted_events.append(event)


class TestSourceControlPlugin:
    """Test SourceControlPlugin activation and registration."""

    def test_plugin_is_abstractplugin_subclass(self) -> None:
        """SourceControlPlugin should inherit from AbstractPlugin."""
        plugin = SourceControlPlugin()
        assert isinstance(plugin, AbstractPlugin)

    def test_plugin_id(self) -> None:
        """Plugin ID should be 'source_control'."""
        plugin = SourceControlPlugin()
        assert plugin.plugin_id == "source_control"

    def test_activity_bar_items(self) -> None:
        """Plugin should return activity bar item with correct properties."""
        plugin = SourceControlPlugin()
        items = plugin.get_activity_bar_items()

        assert len(items) == 1
        item = items[0]
        assert item.plugin_id == "source_control"
        assert item.icon_name == "org.gnome.gitg-symbolic"
        assert item.title == "Source Control"
        assert item.priority == 10

    def test_activate_with_git_service(self) -> None:
        """Plugin should activate successfully when git service is available."""
        plugin = SourceControlPlugin()
        mock_git_service = MagicMock()
        context = MockPluginContext(services={"git": mock_git_service})

        plugin.activate(context)

        # Verify action registration (no panel registration needed)
        assert len(context.host_bridge.registered_actions) == 1
        action_reg = context.host_bridge.registered_actions[0]
        assert action_reg["plugin_id"] == "source_control"
        assert action_reg["action_id"] == "focus_source_control"
        assert action_reg["shortcut"] == "<Ctrl><Shift>G"

        # Verify panel factory was created
        assert plugin._panel_factory is not None

    def test_activate_without_git_service(self) -> None:
        """Plugin should not activate when git service is missing."""
        plugin = SourceControlPlugin()
        context = MockPluginContext(services={})  # No git service

        plugin.activate(context)

        # Verify no registrations were made
        assert len(context.host_bridge.registered_actions) == 0
        assert plugin._panel_factory is None

    def test_focus_panel_action(self) -> None:
        """Focus panel action should call host_bridge.focus_panel."""
        plugin = SourceControlPlugin()
        mock_git_service = MagicMock()
        context = MockPluginContext(services={"git": mock_git_service})

        plugin.activate(context)

        # Get the focus action callback
        action_reg = context.host_bridge.registered_actions[0]
        focus_callback = action_reg["callback"]

        # Call the focus action
        focus_callback()

        # Verify focus was called
        assert context.host_bridge.focused_panels == ["source_control"]

    def test_panel_factory_creates_sourcecontrolpanel(self) -> None:
        """Panel factory should create SourceControlPanel instances."""
        plugin = SourceControlPlugin()
        mock_git_service = MagicMock()
        context = MockPluginContext(services={"git": mock_git_service})

        plugin.activate(context)

        # Get the panel factory
        factory = plugin._panel_factory
        assert factory is not None

        # Create panel using factory
        panel = factory()

        # Verify panel type
        from slate.ui.panels.source_control_panel import SourceControlPanel

        assert isinstance(panel, SourceControlPanel)

        # Verify services were passed to panel
        assert panel._git_service == mock_git_service
        assert panel._event_bus == context.event_bus
        assert panel._host_bridge == context.host_bridge
