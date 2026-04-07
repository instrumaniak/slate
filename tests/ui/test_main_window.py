from __future__ import annotations

from unittest.mock import MagicMock

from gi.repository import Gtk


def test_show_notification_uses_existing_overlay(monkeypatch) -> None:
    """show_notification should mount SlateToast on the window overlay."""
    from slate.ui.main_window import SlateWindow

    window = SlateWindow.__new__(SlateWindow)
    window._toast = None

    created = {}

    class DummyToast:
        def __init__(self, received_overlay) -> None:
            created["overlay"] = received_overlay

        def show(self, message: str, duration: int) -> None:
            created["message"] = message
            created["duration"] = duration

    monkeypatch.setattr("slate.ui.toast.SlateToast", DummyToast)

    window.show_notification("Copied: file.txt", 2000)

    assert isinstance(window._overlay, Gtk.Overlay)
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
