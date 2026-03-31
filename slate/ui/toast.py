from __future__ import annotations

from gi.repository import GLib, Gtk


class SlateToast:
    """In-app notification using pure GTK4.

    Uses Gtk.Overlay + Gtk.Revealer + GTK4's built-in
    'app-notification' CSS class. No custom CSS required.
    """

    def __init__(self, overlay: Gtk.Overlay) -> None:
        self._revealer = Gtk.Revealer()
        self._revealer.set_halign(Gtk.Align.CENTER)
        self._revealer.set_valign(Gtk.Align.START)
        self._revealer.set_margin_top(12)
        self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._box.add_css_class("app-notification")

        self._label = Gtk.Label()
        self._box.append(self._label)

        self._close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")
        self._close_btn.add_css_class("flat")
        self._close_btn.connect("clicked", lambda *_: self.dismiss())
        self._box.append(self._close_btn)

        self._revealer.set_child(self._box)
        overlay.add_overlay(self._revealer)

        self._dismiss_timer_id: int | None = None

    def show(self, message: str, duration: int = 3) -> None:
        """Show a toast message for duration seconds."""
        if self._dismiss_timer_id is not None:
            GLib.source_remove(self._dismiss_timer_id)
            self._dismiss_timer_id = None

        self._label.set_label(message)
        self._revealer.set_revealed(True)
        self._dismiss_timer_id = GLib.timeout_add_seconds(duration, self._dismiss_timeout)

    def show_with_action(
        self, message: str, action_label: str, callback, duration: int = 5
    ) -> None:
        """Show a toast with an action button."""
        for child in list(self._box):
            if child is not self._label and child is not self._close_btn:
                self._box.remove(child)

        action_btn = Gtk.Button(label=action_label)
        action_btn.add_css_class("flat")
        action_btn.connect("clicked", lambda *_: (callback(), self.dismiss()))
        self._box.insert_child_after(action_btn, self._label)

        self.show(message, duration)

    def dismiss(self) -> None:
        self._revealer.set_revealed(False)

    def _dismiss_timeout(self) -> bool:
        self._revealer.set_revealed(False)
        return False
