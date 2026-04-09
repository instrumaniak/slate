from __future__ import annotations

from unittest.mock import MagicMock

from gi.repository import Gtk


def test_show_notification_uses_existing_overlay(monkeypatch) -> None:
    """show_notification should mount SlateToast on the window overlay."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._toast = None
    window._overlay = Gtk.Overlay()

    created = {}

    class DummyToast:
        def __init__(self, received_overlay) -> None:
            created["overlay"] = received_overlay

        def show(self, message: str, duration: int) -> None:
            created["message"] = message
            created["duration"] = duration

    monkeypatch.setattr("slate.ui.toast.SlateToast", DummyToast)

    window.show_notification("Copied: file.txt", 2000)

    assert created["overlay"] is window._overlay
    assert created["message"] == "Copied: file.txt"
    assert created["duration"] == 2


def test_on_save_file_persists_active_editor_content() -> None:
    """Save action should write active editor content and clear dirty state."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    editor_view = MagicMock()
    editor_view.get_content.return_value = "updated content"
    editor_view.mark_clean = MagicMock()

    tab_manager = MagicMock()
    tab_manager.get_active_tab.return_value = "/tmp/test.txt"
    tab_manager.get_tabs.return_value = {"/tmp/test.txt": {"editor_view": editor_view}}
    tab_manager.save_tab = MagicMock()

    tab_bar = MagicMock()

    window._tab_manager = tab_manager
    window._tab_bar = tab_bar

    window._on_save_file()

    tab_manager.save_tab.assert_called_once_with("/tmp/test.txt", "updated content")
    editor_view.mark_clean.assert_called_once_with()
    tab_bar.set_dirty.assert_called_once_with("/tmp/test.txt", False)


def test_register_shortcuts_binds_each_action_to_its_own_callback(monkeypatch) -> None:
    """Shortcut actions should call their matching callbacks, not the last loop callback."""
    from slate.ui.main_window import SlateWindow

    created_actions = {}

    class DummyAction:
        def __init__(self, name: str) -> None:
            self.name = name
            self._activate = None

        def connect(self, signal_name: str, callback) -> None:
            assert signal_name == "activate"
            self._activate = callback

        def trigger(self) -> None:
            assert self._activate is not None
            self._activate(self, None)

    class DummyController:
        def set_scope(self, _scope) -> None:
            pass

        def add_shortcut(self, _shortcut) -> None:
            pass

    def new_action(name: str, _param) -> DummyAction:
        action = DummyAction(name)
        created_actions[name] = action
        return action

    monkeypatch.setattr("slate.ui.main_window.Gio.SimpleAction.new", new_action)
    monkeypatch.setattr(
        "slate.ui.main_window.Gtk.ShortcutController.new", lambda: DummyController()
    )
    monkeypatch.setattr("slate.ui.main_window.Gtk.ShortcutTrigger.parse_string", lambda key: key)
    monkeypatch.setattr("slate.ui.main_window.Gtk.NamedAction.new", lambda action: action)
    monkeypatch.setattr(
        "slate.ui.main_window.Gtk.Shortcut.new", lambda trigger, action: (trigger, action)
    )

    window = SlateWindow.__new__(SlateWindow)
    window._test_mode = False
    window.add_action = MagicMock()
    window.add_controller = MagicMock()
    window._on_new_tab = MagicMock()
    window._on_close_tab = MagicMock()
    window._on_save_file = MagicMock()
    window._on_open_file = MagicMock()
    window._on_toggle_panel = MagicMock()
    window._on_undo = MagicMock()
    window._on_redo = MagicMock()
    window._on_next_tab = MagicMock()
    window._on_explorer_focus = MagicMock()

    window._register_shortcuts()

    created_actions["save_file"].trigger()
    window._on_save_file.assert_called_once_with()
    window._on_explorer_focus.assert_not_called()


def test_close_requested_syncs_live_editor_content_before_save() -> None:
    """Closing a dirty tab should snapshot the live editor buffer before TabManager saves it."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    editor_view = MagicMock()
    editor_view.get_content.return_value = "edited content"

    tab_manager = MagicMock()
    tab_manager.get_tabs.side_effect = [
        {"/tmp/test.txt": {"editor_view": editor_view}},
        {},
        {},
    ]
    tab_manager.close_tab.return_value = True

    window._tab_manager = tab_manager
    window._editor_scroll = MagicMock()
    window._tab_bar = MagicMock()

    window._on_tab_close_requested(MagicMock(), "/tmp/test.txt")

    tab_manager.set_tab_content.assert_called_once_with("/tmp/test.txt", "edited content")
    tab_manager.close_tab.assert_called_once_with("/tmp/test.txt")


def test_open_file_on_startup_loads_parent_folder_for_single_file(monkeypatch) -> None:
    """Opening a single CLI file should load its parent folder in the explorer."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._paned = MagicMock()
    window._side_panel = MagicMock()
    window._tab_manager = MagicMock()
    window._tab_bar = MagicMock()
    window._create_editor_view_for_tab = MagicMock()
    window._load_folder_in_explorer = MagicMock()
    window._tab_manager.open_tab.return_value = {
        "content": "print('hello')",
        "is_error": False,
    }

    file_path = "/tmp/project/src/main.py"
    monkeypatch.setattr(
        "slate.ui.main_window.os.path.isdir", lambda path: path == "/tmp/project/src"
    )

    window.open_file_on_startup(file_path, is_folder=False)

    window._paned.set_visible.assert_called_once_with(True)
    window._tab_manager.open_tab.assert_called_once_with(file_path)
    window._tab_bar.add_tab.assert_called_once_with(file_path, "main.py")
    window._tab_bar.set_active.assert_called_once_with(file_path)
    window._create_editor_view_for_tab.assert_called_once()
    window._side_panel.set_visible.assert_called_once_with(True)
    window._load_folder_in_explorer.assert_called_once_with("/tmp/project/src")


def test_open_file_on_startup_handles_root_level_file_without_error(monkeypatch) -> None:
    """Root-level file startup should not fail when no loadable parent folder is found."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._paned = MagicMock()
    window._side_panel = MagicMock()
    window._tab_manager = MagicMock()
    window._tab_bar = MagicMock()
    window._create_editor_view_for_tab = MagicMock()
    window._load_folder_in_explorer = MagicMock()
    window._tab_manager.open_tab.return_value = {
        "content": "print('hello')",
        "is_error": False,
    }

    file_path = "/file.py"
    monkeypatch.setattr("slate.ui.main_window.os.path.isdir", lambda path: True)

    window.open_file_on_startup(file_path, is_folder=False)

    window._side_panel.set_visible.assert_called_once_with(True)
    window._load_folder_in_explorer.assert_not_called()


def test_activity_bar_item_click_toggles_file_explorer_visibility() -> None:
    """Clicking the explorer activity-bar item should toggle the side panel."""
    from slate.ui.main_window import SlateWindow

    explorer_widget = MagicMock()
    plugin = MagicMock()
    plugin.get_panel_widget.return_value = explorer_widget

    plugin_manager = MagicMock()
    plugin_manager.get_plugin.return_value = plugin

    window = SlateWindow.__new__(SlateWindow)
    window._plugin_manager = plugin_manager
    window._side_panel = MagicMock()
    window._paned = MagicMock()
    window._config_service = MagicMock()
    window._activity_bar = MagicMock()

    window._side_panel.get_first_child.return_value = explorer_widget
    window._paned.get_visible.return_value = True
    window._side_panel.get_visible.return_value = True

    window._on_activity_bar_item_clicked("file_explorer")

    window._side_panel.set_visible.assert_called_once_with(False)
    window._config_service.set.assert_called_once_with("app", "side_panel_visible", "false")
    window._side_panel.append.assert_not_called()


def test_activity_bar_item_click_shows_hidden_file_explorer() -> None:
    """Clicking the explorer activity-bar item should show the panel when hidden."""
    from slate.ui.main_window import SlateWindow

    explorer_widget = MagicMock()
    plugin = MagicMock()
    plugin.get_panel_widget.return_value = explorer_widget

    plugin_manager = MagicMock()
    plugin_manager.get_plugin.return_value = plugin

    window = SlateWindow.__new__(SlateWindow)
    window._plugin_manager = plugin_manager
    window._side_panel = MagicMock()
    window._paned = MagicMock()
    window._config_service = MagicMock()
    window._activity_bar = MagicMock()

    window._side_panel.get_first_child.return_value = None
    window._side_panel.get_visible.return_value = False

    window._on_activity_bar_item_clicked("file_explorer")

    window._side_panel.set_visible.assert_called_once_with(True)
    window._side_panel.append.assert_called_once_with(explorer_widget)
    window._config_service.set.assert_called_once_with("app", "side_panel_visible", "true")


def test_activity_bar_uses_distinct_css_class(monkeypatch) -> None:
    """Activity bar should use its own CSS hook separate from the sidebar."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._test_mode = False
    window._refresh_activity_bar = MagicMock()

    activity_bar = window._create_activity_bar()

    assert activity_bar.get_css_classes() == ["toolbar", "activity-bar"]


def test_on_file_opened_shows_toast_for_error_tabs() -> None:
    """Failed file opens should notify the user instead of rendering error text."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._tab_manager = MagicMock()
    window._tab_bar = MagicMock()
    window._show_file_open_error = MagicMock()
    window._create_editor_view_for_tab = MagicMock()
    window._update_editor_for_tab = MagicMock()

    window._tab_manager.get_tabs.return_value = {
        "/home/raziur/Projects/rnd/ai-agentic-coding/slate/.coverage": {
            "content": "Error: failed to load file\nFile is not valid UTF-8: /home/raziur/Projects/rnd/ai-agentic-coding/slate/.coverage",
            "is_error": True,
        }
    }

    window._on_file_opened(
        MagicMock(path="/home/raziur/Projects/rnd/ai-agentic-coding/slate/.coverage")
    )

    window._show_file_open_error.assert_called_once()
    window._create_editor_view_for_tab.assert_called_once()
    window._update_editor_for_tab.assert_called_once()


def test_create_editor_view_for_error_tab_uses_placeholder() -> None:
    """Error tabs should render a centered placeholder instead of a text editor."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._editor_scroll = MagicMock()

    tab = {
        "content": "Error: failed to load file\nFile is not valid UTF-8: /tmp/.coverage",
        "is_error": True,
    }

    window._create_editor_view_for_tab("/tmp/.coverage", tab)

    assert tab["editor_view"].__class__.__name__ == "ErrorPlaceholder"
    window._editor_scroll.set_child.assert_called_once()


def test_close_requested_skips_content_sync_for_error_placeholder() -> None:
    """Closing an error tab should not call get_content on the placeholder widget."""
    from slate.ui.main_window import SlateWindow

    placeholder = MagicMock()
    del placeholder.get_content

    tab_manager = MagicMock()
    tab_manager.get_tabs.side_effect = [
        {"/tmp/.coverage": {"editor_view": placeholder}},
        {},
        {},
    ]
    tab_manager.close_tab.return_value = True

    window = SlateWindow.__new__(SlateWindow)
    window._tab_manager = tab_manager
    window._editor_scroll = MagicMock()
    window._tab_bar = MagicMock()

    window._on_tab_close_requested(MagicMock(), "/tmp/.coverage")

    tab_manager.set_tab_content.assert_not_called()
    tab_manager.close_tab.assert_called_once_with("/tmp/.coverage")
    window._tab_bar.remove_tab.assert_called_once_with("/tmp/.coverage")
