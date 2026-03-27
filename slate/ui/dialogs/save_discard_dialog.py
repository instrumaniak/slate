from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, GLib, Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Adw = Gtk = GLib = None


class SaveDiscardDialog:
    """Save/Don't Save/Cancel dialog for dirty tabs.

    Uses Adw.MessageDialog for GTK4/Adwaita consistency.
    Returns: "save" | "discard" | "cancel"
    """

    def __init__(self, parent: Gtk.Window, filename: str) -> None:
        """Initialize SaveDiscardDialog.

        Args:
            parent: Parent window for the dialog.
            filename: Name of the file being closed.
        """
        if not GTK_AVAILABLE:
            logger.warning("GTK not available - SaveDiscardDialog is a placeholder")
            self._dialog = None
            return

        self._parent = parent
        self._filename = filename
        self._result: str | None = None
        self._response_map = {
            "save": "save",
            "discard": "discard",
            "cancel": "cancel",
        }

        self._dialog = Adw.MessageDialog.new(
            parent,
            f"Save changes to '{filename}'?",
            "Your changes will be lost if you don't save them.",
        )

        self._dialog.add_button("Don't Save", "discard")
        self._dialog.add_button("Cancel", "cancel")
        save_button = self._dialog.add_button("Save", "save")
        save_button.set_css_classes(["suggested-action"])

        self._dialog.connect("response", self._on_response)
        self._setup_keyboard_handling()

    def _setup_keyboard_handling(self) -> None:
        """Setup keyboard handling for Enter=Save, Escape=Cancel."""
        if not GTK_AVAILABLE:
            return

        controller = Gtk.EventControllerKey.new()
        controller.connect("key-pressed", self._on_key_pressed)
        self._dialog.add_controller(controller)

    def _on_key_pressed(
        self, controller: Gtk.EventControllerKey, keyval: int, keycode: int, modifier: int
    ) -> bool:
        """Handle key presses for Enter and Escape.

        Args:
            controller: The event controller.
            keyval: The key value.
            keycode: The key code.
            modifier: Modifier keys.

        Returns:
            True if the key was handled.
        """
        from gi.repository import Gdk

        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            self._dialog.response("save")
            return True
        elif keyval == Gdk.KEY_Escape:
            self._dialog.response("cancel")
            return True
        return False

    def _on_response(self, dialog: Adw.MessageDialog, response: str) -> None:
        """Handle dialog response.

        Args:
            dialog: The message dialog.
            response: The response ID.
        """
        self._result = self._response_map.get(response, "cancel")
        self._dialog.hide()

    def run(self) -> str:
        """Run the dialog synchronously.

        Returns:
            "save", "discard", or "cancel"
        """
        if not GTK_AVAILABLE:
            return "cancel"

        self._dialog.present()
        while self._result is None:
            pass

        return self._result

    async def run_async(self) -> str:
        """Run the dialog asynchronously.

        Returns:
            "save", "discard", or "cancel"
        """
        if not GTK_AVAILABLE:
            return "cancel"

        self._dialog.present()

        while self._result is None:
            await asyncio.sleep(0.05)

        return self._result
