from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import GObject, Gtk, Pango

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = GObject = Pango = None


class TabBar(Gtk.Box):
    """Tab bar widget for managing open tabs."""

    __gsignals__ = {
        "tab-close-requested": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "close-all-requested": (GObject.SignalFlags.RUN_LAST, None, ()),
        "tab-selected": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "tab-reordered": (GObject.SignalFlags.RUN_LAST, None, (object, int)),
    }

    def __init__(self) -> None:
        """Initialize TabBar."""
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_homogeneous(False)
        self.set_spacing(0)
        self.set_margin_top(2)

        self._tabs: dict = {}
        self._tab_labels: dict = {}
        self._tab_dirty_indicators: dict = {}
        self._active_path: str | None = None
        self._tab_order: list = []
        self._syncing_selection = False

        if not GTK_AVAILABLE:
            logger.warning("GTK not available - TabBar is a placeholder")
            return

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self._scrolled.set_propagate_natural_width(True)
        self._scrolled.set_hexpand(True)

        self._tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._tab_box.set_spacing(0)
        self._tab_box.set_hexpand(False)
        self._tab_box.set_halign(Gtk.Align.START)

        self._scrolled.set_child(self._tab_box)
        self.append(self._scrolled)

        self._menu_button = Gtk.MenuButton()
        self._menu_button.set_icon_name("view-more-symbolic")
        self._menu_button.set_tooltip_text("Tab options")
        self._menu_button.set_css_classes(["flat"])

        popover = Gtk.Popover()
        self._menu_button.set_popover(popover)
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        popover_box.set_margin_start(12)
        popover_box.set_margin_end(12)
        popover_box.set_margin_top(8)
        popover_box.set_margin_bottom(8)
        close_all_button = Gtk.Button(label="Close All Tabs")
        close_all_button.connect("clicked", self._on_close_all_clicked)
        popover_box.append(close_all_button)
        popover.set_child(popover_box)
        self._close_all_button = close_all_button
        self.append(self._menu_button)

        self._install_css()

        self.set_visible(False)

    def _install_css(self) -> None:
        """Install the tab shape and active-tab styling."""
        css = """
        .slate-tab.active {
            background-color: @view_bg_color;
            border-radius: 10px 10px 0 0;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        self.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._tab_css = css
        self._css_provider = provider

    def _on_close_all_clicked(self, _button: Gtk.Button) -> None:
        """Emit the close-all request from the popover action."""
        self.emit("close-all-requested")

    def add_tab(self, path: str, label: str, is_dirty: bool = False) -> None:
        """Add a new tab to the bar."""
        if not GTK_AVAILABLE:
            return

        if path in self._tabs:
            return

        tab_button = Gtk.ToggleButton()
        tab_button.set_css_classes(["flat", "slate-tab"])

        dirty_indicator = Gtk.Label(label="")
        if is_dirty:
            dirty_indicator.set_markup(' <span color="#3584e4">●</span>')
        self._tab_dirty_indicators[path] = dirty_indicator

        label_widget = Gtk.Label(label=label)
        label_widget.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label_widget.set_halign(Gtk.Align.START)
        self._tab_labels[path] = label_widget

        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.set_css_classes(["flat", "danger"])
        close_btn.set_valign(Gtk.Align.CENTER)
        close_btn.set_tooltip_text("Close tab")

        tab_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tab_content.set_spacing(4)
        tab_content.append(label_widget)
        tab_content.append(dirty_indicator)
        tab_content.append(close_btn)

        tab_button.set_child(tab_content)

        click_controller = Gtk.GestureClick.new()
        click_controller.connect("pressed", lambda ctrl, n, x, y: self._on_close_clicked(path))
        close_btn.add_controller(click_controller)

        def on_toggled(_btn) -> None:
            if self._syncing_selection:
                return
            if _btn.get_active():
                previous = self._active_path
                self._active_path = path
                self._set_button_states(path)
                if previous != path:
                    self.emit("tab-selected", path)
            elif self._active_path == path:
                self._set_button_states(path)

        tab_button.connect("toggled", on_toggled)

        self._tab_box.append(tab_button)
        self._tabs[path] = tab_button
        self._tab_order.append(path)

        self.set_visible(True)

    def _on_close_clicked(self, path: str) -> bool:
        """Handle close button click - consume event to prevent ToggleButton toggle."""
        self.emit("tab-close-requested", path)
        return True

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
        if path in self._tab_labels:
            del self._tab_labels[path]
        if path in self._tab_dirty_indicators:
            del self._tab_dirty_indicators[path]
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

        self._active_path = path
        self._set_button_states(path)

    def _set_button_states(self, active_path: str) -> None:
        """Synchronize button state without recursively handling toggles."""
        self._syncing_selection = True
        try:
            for p, btn in self._tabs.items():
                btn.set_active(p == active_path)
                if p == active_path:
                    btn.add_css_class("active")
                else:
                    btn.remove_css_class("active")
        finally:
            self._syncing_selection = False

    def get_tabs(self) -> list:
        """Get list of tab paths in order."""
        return self._tab_order.copy()

    def get_active(self) -> str | None:
        """Get currently active tab path."""
        return self._active_path

    def set_dirty(self, path: str, is_dirty: bool) -> None:
        """Update dirty indicator for a tab.

        Args:
            path: Path of the tab.
            is_dirty: Whether the tab has unsaved changes.
        """
        if path not in self._tab_dirty_indicators:
            return

        indicator = self._tab_dirty_indicators[path]
        if is_dirty:
            indicator.set_markup(' <span color="#3584e4">●</span>')
        else:
            indicator.set_markup("")

    def update_tab_label(self, path: str, label: str) -> None:
        """Update the label for an existing tab.

        Args:
            path: Path of the tab.
            label: New label text.
        """
        if path not in self._tab_labels:
            return

        label_widget = self._tab_labels[path]
        label_widget.set_text(label)

    def reorder_tabs(self, new_order: list) -> None:
        """Reorder tabs based on drag and drop.

        Args:
            new_order: New order of tab paths.
        """
        if set(new_order) != set(self._tab_order):
            logger.warning("Reorder request doesn't match existing tabs")
            return

        self._tab_order = new_order
        self.emit("tab-reordered", new_order, 0)
