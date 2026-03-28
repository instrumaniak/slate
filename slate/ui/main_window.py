from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slate.services.config_service import ConfigService
    from slate.services.theme_service import ThemeService

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk

logger = logging.getLogger(__name__)


def create_main_window(app, config_service, theme_service, test_mode: bool = False):
    """Factory function to create main window.

    Args:
        app: The application instance.
        config_service: The config service.
        theme_service: The theme service.
        test_mode: If True, set accessible names for testing.
    """
    return SlateWindow(app, config_service, theme_service, test_mode=test_mode)


class SlateWindow(Adw.ApplicationWindow):
    """Main application window with GTK4/Adwaita."""

    def __init__(
        self,
        app: Adw.Application,
        config_service: ConfigService,
        theme_service: ThemeService,
        test_mode: bool = False,
    ) -> None:
        """Initialize SlateWindow.

        Args:
            app: The application instance.
            config_service: The config service.
            theme_service: The theme service.
            test_mode: If True, set accessible names for testing.
        """
        super().__init__(application=app)

        self._test_mode = test_mode

        self.set_decorated(True)

        if self._test_mode:
            self._set_accessible_names()

        self._config_service = config_service
        self._theme_service = theme_service

        from slate.services import get_file_service

        file_service = get_file_service()

        from slate.ui.editor.tab_manager import TabManager

        self._tab_manager = TabManager(file_service)
        self._tab_manager.set_close_dialog_callback(self._show_close_dialog)

        self._setup_window_geometry()
        self._apply_theme()
        self._setup_main_layout()
        self._register_shortcuts()

    def _set_accessible_names(self) -> None:
        """Set accessible names for test automation."""
        try:
            accessible = self.get_accessible()
            if accessible:
                accessible.set_name("slate-main-window")
        except (AttributeError, TypeError):
            pass

    def _try_set_accessible_name(self, widget, name: str) -> None:
        """Try to set accessible name on a widget, silently fail if not supported."""
        try:
            accessible = widget.get_accessible()
            if accessible:
                accessible.set_name(name)
        except (AttributeError, TypeError):
            pass

    def _setup_window_geometry(self) -> None:
        """Load and apply window dimensions from config."""
        try:
            width = int(self._config_service.get("app", "window_width") or "1200")
            height = int(self._config_service.get("app", "window_height") or "800")
            maximized = self._config_service.get("app", "window_maximized") == "true"

            self.set_default_size(width, height)
            if maximized:
                self.maximize()

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to load window geometry: {e}")
            self.set_default_size(1200, 800)

    def _apply_theme(self) -> None:
        """Apply theme before window presentation."""
        try:
            _, _, editor_scheme = self._theme_service.resolve_theme()
            logger.debug(f"Resolved editor scheme: {editor_scheme}")
        except Exception as e:
            logger.warning(f"Failed to resolve theme: {e}")

    def _setup_main_layout(self) -> None:
        """Set up main window layout with activity bar, side panel, editor."""
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)

        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(True)

        if self._test_mode:
            self._try_set_accessible_name(header, "slate-headerbar")

        title_label = Gtk.Label(label="Slate")
        title_label.set_css_classes(["title"])
        header.set_title_widget(title_label)

        content_box.append(header)

        self._activity_bar = self._create_activity_bar()
        content_box.append(self._activity_bar)

        self._paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        try:
            side_panel_width = int(self._config_service.get("app", "side_panel_width") or "220")
        except (ValueError, TypeError):
            side_panel_width = 220
        self._paned.set_position(side_panel_width)

        self._side_panel = self._create_side_panel()
        self._paned.set_start_child(self._side_panel)

        self._editor_area = self._create_editor_area()
        self._paned.set_end_child(self._editor_area)

        content_box.append(self._paned)

        self.set_content(content_box)

        try:
            show_panel = self._config_service.get("app", "side_panel_visible") == "true"
            self._paned.set_visible(show_panel)
        except Exception:
            pass

    def _create_activity_bar(self) -> Gtk.Box:
        """Create activity bar with panel navigation."""
        activity_bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        activity_bar.set_size_request(48, -1)
        activity_bar.set_css_classes(["toolbar"])

        return activity_bar

    def _create_side_panel(self) -> Gtk.Box:
        """Create side panel container."""
        side_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side_panel.set_hexpand(False)
        side_panel.set_css_classes(["sidebar"])

        if self._test_mode:
            self._try_set_accessible_name(side_panel, "slate-side-panel")

        placeholder = Gtk.Label(label="Side Panel\n(Future: File Explorer)")
        placeholder.set_vexpand(True)
        side_panel.append(placeholder)

        return side_panel

    def _create_editor_area(self) -> Gtk.Box:
        """Create main editor area with tab bar."""
        from slate.ui.editor.tab_bar import TabBar

        editor_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        editor_area.set_hexpand(True)
        editor_area.set_vexpand(True)

        if self._test_mode:
            self._try_set_accessible_name(editor_area, "slate-editor-area")

        self._tab_bar = TabBar()
        self._tab_bar.connect("tab-selected", self._on_tab_selected)
        self._tab_bar.connect("tab-close-requested", self._on_tab_close_requested)

        if self._test_mode:
            self._try_set_accessible_name(self._tab_bar, "slate-tab-bar")

        editor_area.append(self._tab_bar)

        self._editor_scroll = Gtk.ScrolledWindow()
        self._editor_scroll.set_hexpand(True)
        self._editor_scroll.set_vexpand(True)
        self._editor_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        editor_area.append(self._editor_scroll)

        return editor_area

    def _on_tab_selected(self, tab_bar, path: str) -> None:
        """Handle tab selection."""
        self._tab_manager.set_active_tab(path)
        self._update_editor_for_tab(path)

    def _on_tab_close_requested(self, tab_bar, path: str) -> None:
        """Handle tab close request."""
        closed = self._tab_manager.close_tab(path)
        if closed:
            tab = self._tab_manager.get_tabs().get(path, {})
            editor_view = tab.pop("editor_view", None)
            if editor_view and self._editor_scroll.get_child() is editor_view:
                self._editor_scroll.set_child(None)
            self._tab_bar.remove_tab(path)

            if not self._tab_manager.get_tabs():
                self._editor_scroll.set_child(None)

    def _update_editor_for_tab(self, path: str) -> None:
        """Update editor container to show the selected tab's editor."""
        tab = self._tab_manager.get_tabs().get(path)
        if tab and "editor_view" in tab:
            self._editor_scroll.set_child(tab["editor_view"])

    def open_file_on_startup(self, path: str) -> None:
        """Open a file on application startup."""
        logger.debug(f"Opening file on startup: {path}")

        tab = self._tab_manager.open_tab(path)
        self._tab_bar.add_tab(path, path.split("/")[-1])
        self._tab_bar.set_active(path)

        self._create_editor_view_for_tab(path, tab)

    def _create_editor_view_for_tab(self, path: str, tab: dict) -> None:
        """Create EditorView for a tab and store it."""
        from slate.ui.editor.editor_view import EditorView

        editor_view = EditorView(
            path=path,
            content=tab.get("content", ""),
            on_modified_changed=lambda dirty, p=path: self._on_editor_modified(p, dirty),
        )

        tab["editor_view"] = editor_view

        if editor_view:
            self._editor_scroll.set_child(editor_view)

    def _on_editor_modified(self, path: str, is_dirty: bool) -> None:
        """Handle editor buffer modified state change."""
        if is_dirty:
            self._tab_manager.mark_dirty(path)
        else:
            self._tab_manager.mark_clean(path)
        self._tab_bar.set_dirty(path, is_dirty)

    def _show_close_dialog(self, filename: str, path: str) -> str:
        """Show save/discard dialog for a dirty tab.

        Returns:
            "save", "discard", or "cancel"
        """
        from slate.ui.dialogs.save_discard_dialog import SaveDiscardDialog

        dialog = SaveDiscardDialog(self, filename)
        return dialog.run()

    def _register_shortcuts(self) -> None:
        # Register Gio.SimpleAction shortcuts (no ShortcutController to avoid
        # interfering with editor focus/click behaviour)
        shortcuts = [
            ("new_tab", "t", self._on_new_tab),
            ("close_tab", "w", self._on_close_tab),
            ("save_file", "s", self._on_save_file),
            ("open_file", "o", self._on_open_file),
            ("toggle_panel", "b", self._on_toggle_panel),
            ("undo", "z", self._on_undo),
            ("redo", "y", self._on_redo),
            ("next_tab", "Tab", self._on_next_tab),
        ]

        for action_name, _key, callback in shortcuts:
            action = Gio.SimpleAction.new(f"window.{action_name}", None)
            action.connect("activate", lambda *_: callback())
            self.add_action(action)

    def _on_new_tab(self) -> None:
        logger.debug("Keyboard shortcut: new tab")

    def _on_close_tab(self) -> None:
        logger.debug("Keyboard shortcut: close tab")

    def _on_save_file(self) -> None:
        logger.debug("Keyboard shortcut: save file")

    def _on_open_file(self) -> None:
        logger.debug("Keyboard shortcut: open file")

    def _on_toggle_panel(self) -> None:
        visible = self._paned.get_visible()
        self._paned.set_visible(not visible)

        if self._config_service:
            self._config_service.set("app", "side_panel_visible", str(not visible).lower())

    def _on_undo(self) -> None:
        logger.debug("Keyboard shortcut: undo")

    def _on_redo(self) -> None:
        logger.debug("Keyboard shortcut: redo")

    def _on_next_tab(self) -> None:
        logger.debug("Keyboard shortcut: next tab")

    def save_geometry(self) -> None:
        if self._config_service is None:
            return

        try:
            width, height = self.get_default_size()
            maximized = self.is_maximized()

            self._config_service.set("app", "window_width", str(width))
            self._config_service.set("app", "window_height", str(height))
            self._config_service.set("app", "window_maximized", str(maximized).lower())

        except Exception as e:
            logger.error(f"Failed to save window geometry: {e}")

    def close(self) -> None:
        self.save_geometry()
        super().close()
