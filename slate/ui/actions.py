from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi.repository import Gtk


def register_window_shortcuts(window: Gtk.Window, tab_manager=None) -> None:
    """Register application-wide keyboard shortcuts.

    Args:
        window: The window to register shortcuts for.
        tab_manager: Optional TabManager instance for tab cycling.
    """
    from gi.repository import Gio

    shortcuts = [
        ("new_tab", "t"),
        ("close_tab", "w"),
        ("save_file", "s"),
        ("open_file", "o"),
        ("toggle_panel", "b"),
        ("undo", "z"),
        ("redo", "y"),
    ]

    for action_name, _key in shortcuts:
        action = Gio.SimpleAction.new(f"window.{action_name}", None)
        action.connect("activate", lambda _, _a=action_name: _handle_action(_a, window))
        window.add_action(action)

    if tab_manager:
        tab_cycle_next = Gio.SimpleAction.new("window.cycle_tab_next", None)
        tab_cycle_next.connect("activate", lambda *_: tab_manager.cycle_next())
        window.add_action(tab_cycle_next)

        tab_cycle_prev = Gio.SimpleAction.new("window.cycle_tab_prev", None)
        tab_cycle_prev.connect("activate", lambda *_: tab_manager.cycle_previous())
        window.add_action(tab_cycle_prev)


def _handle_action(action_name: str, window: Gtk.Window) -> None:
    """Handle registered shortcut action.

    Args:
        action_name: Name of the action.
        window: Window for context.
    """
    pass
