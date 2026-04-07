from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from slate.services.config_service import ConfigService
    from slate.services.theme_service import ThemeService

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

logger = logging.getLogger(__name__)


def create_main_window(app, config_service, theme_service, plugin_manager, test_mode: bool = False):
    """Factory function to create main window.

    Args:
        app: The application instance.
        config_service: The config service.
        theme_service: The theme service.
        plugin_manager: The plugin manager for activity bar items.
        test_mode: If True, set accessible names for testing.
    """
    return SlateWindow(app, config_service, theme_service, plugin_manager, test_mode=test_mode)


class SlateWindow(Gtk.ApplicationWindow):
    """Main application window with GTK4."""

    def __init__(
        self,
        app: Gtk.Application,
        config_service: ConfigService,
        theme_service: ThemeService,
        plugin_manager,
        test_mode: bool = False,
    ) -> None:
        """Initialize SlateWindow.

        Args:
            app: The application instance.
            config_service: The config service.
            theme_service: The theme service.
            plugin_manager: The plugin manager for activity bar items.
            test_mode: If True, set accessible names for testing.
        """
        super().__init__(application=app)

        self._test_mode = test_mode

        self.set_decorated(True)

        if self._test_mode:
            self._set_accessible_names()

        self._config_service = config_service
        self._theme_service = theme_service
        self._plugin_manager = plugin_manager
        self._editor_scheme = "Adwaita"  # Default until theme is resolved
        self._overlay = Gtk.Overlay()
        self._toast = None

        from slate.services import get_file_service

        file_service = get_file_service()

        from slate.ui.editor.tab_manager import TabManager

        self._tab_manager = TabManager(file_service)
        self._tab_manager.set_close_dialog_callback(self._show_close_dialog)

        from slate.core.event_bus import EventBus
        from slate.core.events import FileOpenedEvent

        self._event_bus = EventBus()
        self._event_bus.subscribe(FileOpenedEvent, self._on_file_opened)

        self._setup_window_geometry()
        self._apply_theme()
        self._setup_main_layout()
        self._register_shortcuts()
        self._register_theme_callback()

        self.connect("close-request", self._on_close_request)

    def _set_accessible_names(self) -> None:
        """Set accessible names for test automation."""
        try:
            from gi.repository import GLib

            def apply() -> bool:
                Gtk.Accessible.update_property(
                    self,
                    [Gtk.AccessibleProperty.LABEL],
                    ["Slate"],
                )
                return False

            GLib.idle_add(apply)
        except (AttributeError, TypeError):
            pass

    def _try_set_accessible_name(self, widget, name: str) -> None:
        """Try to set accessible name on a widget, silently fail if not supported."""
        try:
            from gi.repository import GLib

            def apply() -> bool:
                Gtk.Accessible.update_property(
                    widget,
                    [Gtk.AccessibleProperty.LABEL],
                    [name],
                )
                return False

            GLib.idle_add(apply)
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
            _, _, self._editor_scheme = self._theme_service.resolve_theme()
            logger.debug(f"Resolved editor scheme: {self._editor_scheme}")
        except Exception as e:
            logger.warning(f"Failed to resolve theme: {e}")
            self._editor_scheme = "Adwaita"

    def _register_theme_callback(self) -> None:
        """Register callback for live theme changes."""

        def on_theme_changed(color_mode: str, is_dark: bool, editor_scheme: str) -> None:
            self._editor_scheme = editor_scheme
            self._update_editor_schemes(editor_scheme)

        self._theme_service.on_mode_changed(on_theme_changed)

    def _update_editor_schemes(self, editor_scheme: str) -> None:
        """Update color scheme for all open editor views."""
        for tab in self._tab_manager.get_tabs().values():
            if "editor_view" in tab and tab["editor_view"]:
                buffer = tab["editor_view"].get_buffer()
                if buffer:
                    from slate.ui.editor.editor_factory import EditorViewFactory

                    factory = EditorViewFactory()
                    factory.apply_scheme(buffer, editor_scheme)

    def _setup_main_layout(self) -> None:
        """Set up main window layout with activity bar, side panel, editor."""
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)

        self.set_title("Slate")

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

        self.set_child(content_box)

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
        if self._test_mode:
            self._try_set_accessible_name(activity_bar, "slate-activity-bar")
        self._activity_bar_box = activity_bar
        self._refresh_activity_bar()
        return activity_bar

    def _refresh_activity_bar(self) -> None:
        """Refresh activity bar with current plugin items."""
        if not hasattr(self, "_activity_bar_box"):
            return
        activity_bar = self._activity_bar_box
        child = activity_bar.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            activity_bar.remove(child)
            child = next_child

        items = []
        if self._plugin_manager is not None:
            items = list(self._plugin_manager.get_activity_bar_items())

        if items:
            for item in items:
                btn = Gtk.Button()
                btn.set_icon_name(item.icon_name)
                btn.set_tooltip_text(item.title)
                btn.set_css_classes(["flat"])
                btn.connect(
                    "clicked", lambda _w, p=item.plugin_id: self._on_activity_bar_item_clicked(p)
                )
                activity_bar.append(btn)
        elif self._test_mode:
            test_btn = Gtk.Button(label="Test")
            self._try_set_accessible_name(test_btn, "slate-test-activity")
            activity_bar.append(test_btn)

            quit_btn = Gtk.Button(label="Quit")
            quit_btn.set_css_classes(["flat"])
            quit_btn.connect("clicked", lambda *_: self._on_quit_app())
            self._try_set_accessible_name(quit_btn, "slate-quit-app")
            activity_bar.append(quit_btn)

    def _on_activity_bar_item_clicked(self, plugin_id: str) -> None:
        """Handle activity bar item click - show the corresponding panel."""
        plugin = self._plugin_manager.get_plugin(plugin_id)
        if plugin and hasattr(plugin, "get_panel_widget"):
            widget = plugin.get_panel_widget()
            if widget:
                child = self._side_panel.get_first_child()
                if child is not None:
                    self._side_panel.remove(child)
                self._side_panel.append(widget)

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

        self._overlay.set_child(editor_area)
        return self._overlay

    def _on_tab_selected(self, tab_bar, path: str) -> None:
        """Handle tab selection."""
        self._tab_manager.set_active_tab(path)
        self._update_editor_for_tab(path)

    def _on_tab_close_requested(self, tab_bar, path: str) -> None:
        """Handle tab close request."""
        tab = self._tab_manager.get_tabs().get(path)
        if tab is not None:
            editor_view = tab.get("editor_view")
            if editor_view is not None:
                self._tab_manager.set_tab_content(path, editor_view.get_content())

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

    def open_file_on_startup(self, path: str, is_folder: bool = False) -> None:
        """Open a file on application startup."""
        logger.debug(f"Opening file on startup: {path}, is_folder: {is_folder}")

        if is_folder:
            self._paned.set_visible(True)
            self._side_panel.set_visible(True)
            self._load_folder_in_explorer(path)
        else:
            self._paned.set_visible(True)
            self._side_panel.set_visible(False)
            tab = self._tab_manager.open_tab(path)
            self._tab_bar.add_tab(path, path.split("/")[-1])
            self._tab_bar.set_active(path)
            self._create_editor_view_for_tab(path, tab)

    def _load_folder_in_explorer(self, path: str) -> None:
        """Load a folder into the file explorer panel."""
        from slate.core.event_bus import EventBus
        from slate.core.events import FolderOpenedEvent

        plugin = self._plugin_manager.get_plugin("file_explorer")
        if plugin and hasattr(plugin, "get_panel_widget"):
            widget = plugin.get_panel_widget()
            if widget:
                child = self._side_panel.get_first_child()
                if child is not None and child != widget:
                    self._side_panel.remove(child)
                if child != widget:
                    self._side_panel.append(widget)
                if hasattr(widget, "load_folder"):
                    widget.load_folder(path)
                return

        event_bus = EventBus()
        event_bus.emit(FolderOpenedEvent(path=path))

    def _create_editor_view_for_tab(self, path: str, tab: dict) -> None:
        """Create EditorView for a tab and store it."""
        from slate.ui.editor.editor_view import EditorView

        editor_view = EditorView(
            path=path,
            content=tab.get("content", ""),
            editor_scheme=self._editor_scheme,
            on_modified_changed=lambda dirty, p=path: self._on_editor_modified(p, dirty),
        )

        tab["editor_view"] = editor_view

        if editor_view:
            self._editor_scroll.set_child(editor_view)

    def _on_file_opened(self, event) -> None:
        """Handle FileOpenedEvent - update tab bar and show editor."""
        path = event.path
        tab = self._tab_manager.get_tabs().get(path)
        if tab:
            if path not in self._tab_bar.get_tabs():
                self._tab_bar.add_tab(path, path.split("/")[-1])
            self._tab_bar.set_active(path)
            if "editor_view" not in tab:
                self._create_editor_view_for_tab(path, tab)
            self._update_editor_for_tab(path)

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
        shortcuts = [
            ("new_tab", "t", self._on_new_tab),
            ("close_tab", "w", self._on_close_tab),
            ("save_file", "s", self._on_save_file),
            ("open_file", "o", self._on_open_file),
            ("toggle_panel", "b", self._on_toggle_panel),
            ("undo", "z", self._on_undo),
            ("redo", "y", self._on_redo),
            ("next_tab", "Tab", self._on_next_tab),
            ("explorer_focus", "o", self._on_explorer_focus),
        ]
        if self._test_mode:
            shortcuts.append(("quit_app", "q", self._on_quit_app))

        for action_name, _key, callback in shortcuts:
            action = Gio.SimpleAction.new(action_name, None)
            action.connect("activate", lambda *_args, cb=callback: cb())
            self.add_action(action)

        shortcut_controller = Gtk.ShortcutController.new()
        shortcut_controller.set_scope(Gtk.ShortcutScope.GLOBAL)

        shortcuts_to_bind = {
            "<Primary><Shift>O": "win.explorer_focus",
            "<Primary>t": "win.new_tab",
            "<Primary>w": "win.close_tab",
            "<Primary>s": "win.save_file",
            "<Primary>o": "win.open_file",
            "<Primary>b": "win.toggle_panel",
            "<Primary>z": "win.undo",
            "<Primary>y": "win.redo",
            "Tab": "win.next_tab",
        }
        if self._test_mode:
            shortcuts_to_bind["<Primary>q"] = "win.quit_app"

        for key, action in shortcuts_to_bind.items():
            try:
                trigger = Gtk.ShortcutTrigger.parse_string(key)
                shortcut = Gtk.Shortcut.new(trigger, Gtk.NamedAction.new(action))
                shortcut_controller.add_shortcut(shortcut)
            except Exception as e:
                logger.warning(f"Failed to parse shortcut {key}: {e}")

        self.add_controller(shortcut_controller)

    def _on_new_tab(self) -> None:
        logger.debug("Keyboard shortcut: new tab")

    def _on_close_tab(self) -> None:
        logger.debug("Keyboard shortcut: close tab")

    def _on_save_file(self) -> None:
        path = self._tab_manager.get_active_tab()
        if path is None:
            return

        tab = self._tab_manager.get_tabs().get(path)
        if tab is None:
            return

        editor_view = tab.get("editor_view")
        if editor_view is None:
            return

        content = editor_view.get_content()
        self._tab_manager.save_tab(path, content)
        editor_view.mark_clean()
        self._tab_bar.set_dirty(path, False)

    def _on_open_file(self) -> None:
        logger.debug("Keyboard shortcut: open file")

    def _on_toggle_panel(self) -> None:
        visible = self._paned.get_visible()
        self._paned.set_visible(not visible)

        if self._config_service:
            self._config_service.set("app", "side_panel_visible", str(not visible).lower())

    def _on_quit_app(self) -> None:
        app = self.get_application()
        if app is not None:
            app.quit()
        else:
            self.close()

    def get_tab_state(self) -> dict[str, Any]:
        """Get read-only tab state for testing."""
        return {
            "paths": self._tab_manager.get_tab_list(),
            "active": self._tab_manager.get_active_tab(),
        }

    def has_tab_bar(self) -> bool:
        """Return True if the tab bar widget is available."""
        return self._tab_bar is not None

    def register_panel(
        self, plugin_id: str, panel_id: str, widget: Any, title: str, icon_name: str
    ) -> None:
        """HostUIBridge: Register a panel widget."""
        pass

    def register_action(
        self,
        plugin_id: str,
        action_id: str,
        callback: Callable[..., Any],
        shortcut: str | None = None,
    ) -> None:
        """HostUIBridge: Register an action."""
        pass

    def register_dialog(self, plugin_id: str, dialog_id: str, factory: Callable[..., Any]) -> None:
        """HostUIBridge: Register a dialog."""
        pass

    def show_notification(self, message: str, timeout_ms: int = 3000) -> None:
        """HostUIBridge: Show a toast notification."""
        from slate.ui.toast import SlateToast

        if self._toast is None:
            self._overlay = Gtk.Overlay()
            self._toast = SlateToast(self._overlay)

        duration = max(1, round(timeout_ms / 1000))
        self._toast.show(message, duration=duration)

    def _on_undo(self) -> None:
        logger.debug("Keyboard shortcut: undo")

    def _on_redo(self) -> None:
        logger.debug("Keyboard shortcut: redo")

    def _on_next_tab(self) -> None:
        logger.debug("Keyboard shortcut: next tab")

    def _on_explorer_focus(self) -> None:
        """Focus the file explorer panel."""
        logger.debug("Keyboard shortcut: explorer focus")
        plugin = self._plugin_manager.get_plugin("file_explorer")
        if plugin and hasattr(plugin, "get_panel_widget"):
            widget = plugin.get_panel_widget()
            if widget:
                child = self._side_panel.get_first_child()
                if child is not None:
                    self._side_panel.remove(child)
                self._side_panel.append(widget)
                if hasattr(widget, "grab_focus"):
                    widget.grab_focus()

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

    def _on_close_request(self, *args) -> None:
        self.save_geometry()
        if self._test_mode:
            return False

        dirty_tabs = [
            path for path, tab in self._tab_manager.get_tabs().items() if tab.get("is_dirty", False)
        ]
        if not dirty_tabs:
            return

        for path in dirty_tabs:
            filename = os.path.basename(path)
            result = self._show_close_dialog(filename, path)
            if result == "cancel":
                return
            if result == "save":
                tab = self._tab_manager.get_tabs().get(path, {})
                content = tab.get("content", "")
                from slate.services import get_file_service

                file_service = get_file_service()
                try:
                    file_service.write_file(path, content)
                except Exception as e:
                    logger.error(f"Failed to save file {path}: {e}")
                    return

    def close(self) -> None:
        self.save_geometry()
        super().close()
