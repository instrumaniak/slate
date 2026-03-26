from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gi.repository import Gtk, Gio


def register_window_shortcuts(window: Gtk.Window) -> None:
    """Register application-wide keyboard shortcuts.

    Args:
        window: The window to register shortcuts for.
    """
    from gi.repository import Gtk, Gio

    shortcuts = [
        ("new_tab", "t"),
        ("close_tab", "w"),
        ("save_file", "s"),
        ("open_file", "o"),
        ("toggle_panel", "b"),
        ("undo", "z"),
        ("redo", "y"),
    ]

    for action_name, key in shortcuts:
        action = Gio.SimpleAction.new(f"window.{action_name}", None)
        action.connect("activate", lambda _, _a=action_name: _handle_action(_a, window))
        window.add_action(action)


def _handle_action(action_name: str, window: Gtk.Window) -> None:
    """Handle registered shortcut action.

    Args:
        action_name: Name of the action.
        window: Window for context.
    """
    pass
