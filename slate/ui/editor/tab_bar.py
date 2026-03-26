from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GObject, Pango

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = GObject = Pango = None


class TabBar(Gtk.Box):
    """Tab bar widget for managing open tabs."""

    __gsignals__ = {
        "tab-close-requested": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "tab-selected": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self) -> None:
        """Initialize TabBar."""
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_homogeneous(False)
        self.set_spacing(0)

        self._tabs: dict = {}
        self._active_path: str | None = None
        self._tab_order: list = []

        if not GTK_AVAILABLE:
            logger.warning("GTK not available - TabBar is a placeholder")
            return

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self._scrolled.set_propagate_natural_width(True)
        self._scrolled.set_hexpand(True)

        self._tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._tab_box.set_spacing(0)

        self._scrolled.set_child(self._tab_box)
        self.append(self._scrolled)

        self.set_visible(False)

    def add_tab(self, path: str, label: str) -> None:
        """Add a new tab to the bar."""
        if not GTK_AVAILABLE:
            return

        if path in self._tabs:
            return

        tab_button = Gtk.ToggleButton()
        tab_button.set_css_classes(["flat"])

        label_widget = Gtk.Label(label=label)
        label_widget.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label_widget.set_max_width_chars(20)

        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.set_css_classes(["flat", "danger"])
        close_btn.set_valign(Gtk.Align.CENTER)
        close_btn.set_tooltip_text("Close tab")

        tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tab_content.set_spacing(8)
        tab_content.append(label_widget)
        tab_content.append(close_btn)

        tab_button.set_child(tab_content)

        click_controller = Gtk.GestureClick.new()
        click_controller.connect("pressed", lambda ctrl, n, x, y: self._handle_tab_close(path))
        close_btn.add_controller(click_controller)

        def on_toggled(_btn) -> None:
            if _btn.get_active():
                self._active_path = path
                self.emit("tab-selected", path)

        tab_button.connect("toggled", on_toggled)

        self._tab_box.append(tab_button)
        self._tabs[path] = tab_button
        self._tab_order.append(path)

        self.set_visible(True)

    def _handle_tab_close(self, path: str) -> None:
        """Handle tab close via click gesture."""
        self.emit("tab-close-requested", path)

    def remove_tab(self, path: str) -> None:
        """Remove a tab from the bar."""
        if not GTK_AVAILABLE:
            return

        if path not in self._tabs:
            return

        button = self._tabs[path]
        self._tab_box.remove(button)

        del self._tabs[path]
        self._tab_order.remove(path)

        if self._active_path == path:
            self._active_path = None

        if not self._tabs:
            self.set_visible(False)

    def set_active(self, path: str) -> None:
        """Set active tab."""
        if not GTK_AVAILABLE:
            return

        if path not in self._tabs:
            return

        for p, btn in self._tabs.items():
            btn.set_active(p == path)

        self._active_path = path

    def get_tabs(self) -> list:
        """Get list of tab paths in order."""
        return self._tab_order.copy()

    def get_active(self) -> str | None:
        """Get currently active tab path."""
        return self._active_path
