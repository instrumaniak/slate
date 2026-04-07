"""Tests for FileExplorerPlugin — plugin activation and registration."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from slate.core.plugin_api import AbstractPlugin, PluginContext
from slate.plugins.core.file_explorer import FileExplorerPlugin


class MockHostBridge:
    """Mock HostUIBridge for testing plugin registration."""

    def __init__(self) -> None:
        self.registered_panels: list[dict[str, Any]] = []
        self.registered_actions: list[dict[str, Any]] = []

    def register_panel(
        self, plugin_id: str, panel_id: str, widget: Any, title: str, icon_name: str
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


class MockPluginContext(PluginContext):
    """Concrete PluginContext for testing FileExplorerPlugin."""

    def __init__(self) -> None:
        self._bridge = MockHostBridge()
        self._file_service = MagicMock()
        self._config_service = MagicMock()
        self._emitted_events: list[Any] = []

    @property
    def plugin_id(self) -> str:
        return "file_explorer"

    def get_service(self, service_id: str) -> Any:
        if service_id == "file":
            return self._file_service
        if service_id == "config":
            return self._config_service
        raise KeyError(f"Unknown service: {service_id}")

    def get_config(self, section: str, key: str) -> str:
        return ""

    def set_config(self, section: str, key: str, value: str) -> None:
        pass

    def emit(self, event: Any) -> None:
        self._emitted_events.append(event)

    @property
    def host_bridge(self) -> MockHostBridge:
        return self._bridge


@pytest.fixture
def plugin() -> FileExplorerPlugin:
    return FileExplorerPlugin()


@pytest.fixture
def context() -> MockPluginContext:
    return MockPluginContext()


def _activate_with_mock_panel(plugin: FileExplorerPlugin, context: MockPluginContext) -> None:
    """Activate plugin with mocked panel factory (no GTK required)."""
    mock_widget = MagicMock()
    with patch.object(plugin, "_panel_factory", return_value=lambda: mock_widget):
        plugin.activate(context)


class TestPluginIdentity:
    """Tests for plugin identity and basic structure."""

    def test_plugin_id_is_file_explorer(self, plugin: FileExplorerPlugin) -> None:
        """Plugin ID must be 'file_explorer' (AC 4)."""
        assert plugin.plugin_id == "file_explorer"

    def test_plugin_is_abstract_plugin_subclass(self, plugin: FileExplorerPlugin) -> None:
        """Plugin must extend AbstractPlugin (AC 4)."""
        assert isinstance(plugin, AbstractPlugin)


class TestPluginActivation:
    """Tests for plugin activation and registration."""

    def test_activate_registers_action(
        self, plugin: FileExplorerPlugin, context: MockPluginContext
    ) -> None:
        """Action 'explorer.focus' registered (AC 6)."""
        _activate_with_mock_panel(plugin, context)

        actions = context._bridge.registered_actions
        focus_actions = [a for a in actions if a["action_id"] == "explorer.focus"]
        assert len(focus_actions) == 1
        assert focus_actions[0]["plugin_id"] == "file_explorer"

    def test_activate_registers_keybinding(
        self, plugin: FileExplorerPlugin, context: MockPluginContext
    ) -> None:
        """Keybinding Ctrl+Shift+O bound to explorer.focus (AC 6)."""
        _activate_with_mock_panel(plugin, context)

        actions = context._bridge.registered_actions
        assert actions[0]["shortcut"] == "<Primary><Shift>O"

    def test_activate_gets_file_service(
        self, plugin: FileExplorerPlugin, context: MockPluginContext
    ) -> None:
        """Plugin uses context.get_service('file') (AC 4)."""
        _activate_with_mock_panel(plugin, context)
        assert plugin._file_service is context._file_service

    def test_get_panel_widget_lazy_creates(
        self, plugin: FileExplorerPlugin, context: MockPluginContext
    ) -> None:
        """get_panel_widget creates widget lazily on first access."""
        _activate_with_mock_panel(plugin, context)

        mock_widget = MagicMock()
        plugin._panel_factory = lambda: mock_widget
        widget = plugin.get_panel_widget()
        assert widget is mock_widget

    def test_get_panel_widget_caches(
        self, plugin: FileExplorerPlugin, context: MockPluginContext
    ) -> None:
        """get_panel_widget caches the widget after first creation."""
        _activate_with_mock_panel(plugin, context)

        mock_widget = MagicMock()
        plugin._panel_factory = lambda: mock_widget
        widget1 = plugin.get_panel_widget()
        widget2 = plugin.get_panel_widget()
        assert widget1 is widget2


class TestPluginApiCompliance:
    """Tests for architecture compliance."""

    def test_activate_uses_public_api_only(self) -> None:
        """Plugin file must not import from slate/ui/ at module level (AC 4).

        This is a code inspection test — verifies no direct UI imports.
        """
        import inspect

        source = inspect.getsource(FileExplorerPlugin)

        # Check module-level imports (before class definition)
        module_source = source.split("class FileExplorerPlugin")[0]
        assert "from slate.ui" not in module_source, (
            "Plugin must not import from slate.ui at module level"
        )
        assert "import slate.ui" not in module_source, (
            "Plugin must not import slate.ui at module level"
        )

    def test_plugin_does_not_emit_file_opened_event_directly(
        self, plugin: FileExplorerPlugin, context: MockPluginContext
    ) -> None:
        """Plugin must not emit FileOpenedEvent directly — only OpenFileRequestedEvent."""
        from slate.core.events import FileOpenedEvent

        _activate_with_mock_panel(plugin, context)

        for event in context._emitted_events:
            assert not isinstance(event, FileOpenedEvent), (
                "Plugin must not emit FileOpenedEvent directly"
            )
