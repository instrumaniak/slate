from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib, Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = GLib = None


class SaveDiscardDialog:
    """Save/Don't Save/Cancel dialog for dirty tabs.

    Uses Gtk.Dialog for broad GTK4 compatibility.
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
        self._main_loop: GLib.MainLoop | None = None

        self._response_map = {
            Gtk.ResponseType.YES: "save",
            Gtk.ResponseType.NO: "discard",
            Gtk.ResponseType.CANCEL: "cancel",
        }

        self._dialog = Gtk.Dialog()
        self._dialog.set_transient_for(parent)
        self._dialog.set_modal(True)
        self._dialog.set_title(f"Save changes to '{filename}'?")
        self._dialog.set_default_size(400, -1)
        self._dialog.add_button("Don't Save", Gtk.ResponseType.NO)
        self._dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self._dialog.add_button("Save", Gtk.ResponseType.YES)

        save_btn = self._dialog.get_widget_for_response(Gtk.ResponseType.YES)
        if save_btn:
            save_btn.set_css_classes(["suggested-action"])

        self._dialog.set_default_response(Gtk.ResponseType.YES)

        content_area = self._dialog.get_content_area()
        label = Gtk.Label(label="Your changes will be lost if you don't save them.")
        label.set_margin_top(8)
        label.set_margin_bottom(16)
        label.set_margin_start(16)
        label.set_margin_end(16)
        content_area.append(label)

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
            self._dialog.response(Gtk.ResponseType.YES)
            return True
        elif keyval == Gdk.KEY_Escape:
            self._dialog.response(Gtk.ResponseType.CANCEL)
            return True
        return False

    def _on_response(self, dialog: Gtk.Dialog, response_id: int) -> None:
        """Handle dialog response.

        Args:
            dialog: The dialog.
            response_id: The response type.
        """
        self._result = self._response_map.get(response_id, "cancel")
        self._dialog.hide()
        if self._main_loop and self._main_loop.is_running():
            self._main_loop.quit()

    def run(self) -> str:
        """Run the dialog synchronously using a nested GLib main loop.

        Returns:
            "save", "discard", or "cancel"
        """
        if not GTK_AVAILABLE:
            return "cancel"

        self._main_loop = GLib.MainLoop.new(None, False)
        self._dialog.present()
        self._main_loop.run()
        self._main_loop = None

        return self._result or "cancel"

    async def run_async(self, timeout: float = 120.0) -> str:
        """Run the dialog asynchronously with a timeout.

        Args:
            timeout: Maximum seconds to wait for a response.

        Returns:
            "save", "discard", or "cancel"
        """
        if not GTK_AVAILABLE:
            return "cancel"

        self._dialog.present()
        elapsed = 0.0
        while self._result is None:
            await asyncio.sleep(0.05)
            elapsed += 0.05
            if elapsed >= timeout:
                logger.warning("SaveDiscardDialog timed out after %.1fs", timeout)
                self._dialog.hide()
                return "cancel"

        return self._result
