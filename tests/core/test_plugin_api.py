"""Tests for plugin API contracts (AbstractPlugin, PluginContext, HostUIBridge, ActivityBarItem)."""

import pytest
from abc import ABC, abstractmethod
from dataclasses import dataclass, FrozenInstanceError
from typing import Any, Callable

# Import the actual module once implemented
# from slate.core.plugin_api import AbstractPlugin, PluginContext, HostUIBridge, ActivityBarItem


# ==================== AbstractPlugin Tests ====================


def test_abstract_plugin_cannot_be_instantiated():
    """AbstractPlugin should not be directly instantiable."""
    from slate.core.plugin_api import AbstractPlugin

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AbstractPlugin()


def test_concrete_plugin_must_implement_activate():
    """Concrete plugin subclass must implement activate method."""
    from slate.core.plugin_api import AbstractPlugin

    class IncompletePlugin(AbstractPlugin):
        plugin_id = "test"
        # Missing activate() implementation

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompletePlugin()


def test_concrete_plugin_with_activate_can_be_instantiated():
    """Concrete plugin with activate() should instantiate successfully."""
    from slate.core.plugin_api import AbstractPlugin, PluginContext

    class TestPlugin(AbstractPlugin):
        @property
        def plugin_id(self) -> str:
            return "test_plugin"

        def activate(self, context: PluginContext) -> None:
            self.activated = True
            self.context = context

    plugin = TestPlugin()
    assert plugin.plugin_id == "test_plugin"


def test_abstract_plugin_has_deactivate_optional():
    """AbstractPlugin should have optional deactivate method (not abstract)."""
    from slate.core.plugin_api import AbstractPlugin, PluginContext

    class MinimalPlugin(AbstractPlugin):
        @property
        def plugin_id(self) -> str:
            return "minimal"

        def activate(self, context: PluginContext) -> None:
            pass

    plugin = MinimalPlugin()
    # deactivate should exist (even if not overridden)
    assert hasattr(plugin, "deactivate")


# ==================== PluginContext Tests ====================


def test_plugin_context_cannot_be_instantiated():
    """PluginContext should not be directly instantiable (it's an ABC)."""
    from slate.core.plugin_api import PluginContext

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        PluginContext()


def test_plugin_context_is_abstract():
    """PluginContext should be an ABC with abstract methods."""
    from slate.core.plugin_api import PluginContext
    import inspect

    # Check that PluginContext is abstract
    assert hasattr(PluginContext, "__abstractmethods__")
    assert len(PluginContext.__abstractmethods__) > 0


def test_plugin_context_has_required_abstract_methods():
    """PluginContext should have all required abstract methods."""
    from slate.core.plugin_api import PluginContext
    import inspect

    required_methods = {
        "get_service",
        "get_config",
        "set_config",
        "emit",
        "plugin_id",
        "host_bridge",
    }

    abstract_methods = set()
    for name, method in inspect.getmembers(PluginContext, predicate=inspect.isfunction):
        if getattr(method, "__isabstractmethod__", False):
            abstract_methods.add(name)

    # Also check abstract properties
    for name in ["plugin_id", "host_bridge"]:
        if isinstance(getattr(PluginContext, name, None), property):
            abstract_methods.add(name)

    assert required_methods.issubset(abstract_methods)


# ==================== HostUIBridge Tests ====================


def test_host_ui_bridge_cannot_be_instantiated():
    """HostUIBridge should not be directly instantiable."""
    from slate.core.plugin_api import HostUIBridge

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        HostUIBridge()


def test_host_ui_bridge_has_abstract_methods():
    """HostUIBridge should have abstract methods: register_panel, register_action, register_dialog."""
    from slate.core.plugin_api import HostUIBridge
    import inspect

    abstract_methods = []
    for name, method in inspect.getmembers(HostUIBridge, predicate=inspect.isfunction):
        if getattr(method, "__isabstractmethod__", False):
            abstract_methods.append(name)

    expected_abstract = {"register_panel", "register_action", "register_dialog"}
    assert expected_abstract.issubset(set(abstract_methods))


def test_host_ui_bridge_register_panel_signature():
    """register_panel should accept plugin_id, panel_id, widget, title, icon_name."""
    from slate.core.plugin_api import HostUIBridge
    import inspect

    sig = inspect.signature(HostUIBridge.register_panel)
    params = list(sig.parameters.keys())
    expected = ["self", "plugin_id", "panel_id", "widget", "title", "icon_name"]
    assert params == expected


def test_host_ui_bridge_register_action_signature():
    """register_action should accept plugin_id, action_id, callback, shortcut."""
    from slate.core.plugin_api import HostUIBridge
    import inspect

    sig = inspect.signature(HostUIBridge.register_action)
    params = list(sig.parameters.keys())
    expected = ["self", "plugin_id", "action_id", "callback", "shortcut"]
    # shortcut may be optional
    assert params[:4] == ["self", "plugin_id", "action_id", "callback"]
    assert "shortcut" in params


def test_host_ui_bridge_register_dialog_signature():
    """register_dialog should accept plugin_id, dialog_id, factory."""
    from slate.core.plugin_api import HostUIBridge
    import inspect

    sig = inspect.signature(HostUIBridge.register_dialog)
    params = list(sig.parameters.keys())
    expected = ["self", "plugin_id", "dialog_id", "factory"]
    assert params == expected


def test_host_ui_bridge_show_notification_exists():
    """HostUIBridge should have show_notification method."""
    from slate.core.plugin_api import HostUIBridge
    import inspect

    assert hasattr(HostUIBridge, "show_notification")
    # Should not be abstract (concrete implementation provided by host)
    # We expect it to be implemented, not abstract
    method = getattr(HostUIBridge, "show_notification")
    is_abstract = getattr(method, "__isabstractmethod__", False)
    assert not is_abstract, "show_notification should be implemented, not abstract"


# ==================== ActivityBarItem Tests ====================


def test_activity_bar_item_creation():
    """ActivityBarItem should be created with required fields."""
    from slate.core.plugin_api import ActivityBarItem

    item = ActivityBarItem(plugin_id="test", icon_name="folder", title="Test")
    assert item.plugin_id == "test"
    assert item.icon_name == "folder"
    assert item.title == "Test"
    assert item.priority == 0  # default


def test_activity_bar_item_with_priority():
    """ActivityBarItem should accept custom priority."""
    from slate.core.plugin_api import ActivityBarItem

    item = ActivityBarItem(plugin_id="test", icon_name="folder", title="Test", priority=10)
    assert item.priority == 10


def test_activity_bar_item_frozen():
    """ActivityBarItem should be frozen (immutable)."""
    from slate.core.plugin_api import ActivityBarItem

    item = ActivityBarItem(plugin_id="test", icon_name="folder", title="Test")
    with pytest.raises(FrozenInstanceError):
        item.plugin_id = "changed"


def test_activity_bar_item_fields_type_hints():
    """ActivityBarItem should have proper type hints."""
    from slate.core.plugin_api import ActivityBarItem
    import dataclasses

    fields = {f.name: f.type for f in dataclasses.fields(ActivityBarItem)}
    assert "plugin_id" in fields
    assert "icon_name" in fields
    assert "title" in fields
    assert "priority" in fields
