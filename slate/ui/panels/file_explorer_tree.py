"""File Explorer tree widget — GTK4 ListView + TreeListModel with lazy loading."""

from __future__ import annotations

import logging
import os
import uuid
from typing import TYPE_CHECKING, Any, Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GObject, GLib, Gtk, Pango  # noqa: E402

from slate.core.events import FolderOpenedEvent, OpenFileRequestedEvent  # noqa: E402

if TYPE_CHECKING:
    from slate.core.event_bus import EventBus
    from slate.services.file_service import FileService
    from slate.services.config_service import ConfigService
    from slate.core.plugin_api import HostUIBridge

logger = logging.getLogger(__name__)


class FileTreeItem(GObject.Object):
    """Wrapper for tree node data used by Gtk.TreeListModel."""

    def __init__(
        self,
        name: str,
        path: str,
        is_folder: bool,
        temporary: bool = False,
        parent_path: str | None = None,
        create_kind: str | None = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.path = path
        self.is_folder = is_folder
        self.temporary = temporary
        self.parent_path = parent_path
        self.create_kind = create_kind


class FileExplorerTree(Gtk.Box):
    """Tree view widget for browsing project files with lazy loading.

    Uses Gtk.ListView + Gtk.TreeListModel (modern GTK4 stack).
    Gtk.TreeView is deprecated since GTK 4.10.
    """

    def __init__(
        self,
        file_service: FileService,
        event_bus: EventBus,
        config_service: ConfigService | None = None,
        host_bridge: HostUIBridge | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._file_service = file_service
        self._event_bus = event_bus
        self._config_service = config_service
        self._host_bridge = host_bridge
        self._root_path: str | None = None
        self._load_error: str | None = None
        self._directory_stores: dict[str, Gio.ListStore] = {}
        self._directory_monitors: dict[str, Gio.FileMonitor] = {}
        self._pending_refresh_paths: set[str] = set()
        self._row_widgets: dict[str, dict[str, Any]] = {}
        self._active_inline_item_path: str | None = None
        self._active_inline_mode: str | None = None
        self._edit_text_buffer: dict[str, str] = {}
        self._context_item: FileTreeItem | None = None
        self._last_context_item: FileTreeItem | None = None
        self._context_popover: Gtk.PopoverMenu | None = None
        self._widget_items: dict[Any, FileTreeItem] = {}

        self._show_hidden_files = False
        if config_service is not None:
            value = config_service.get("plugin.file_explorer", "show_hidden_files")
            self._show_hidden_files = value == "true"

        self._breadcrumb_box = self._build_breadcrumb()
        self._header_box = self._build_header()
        self.append(self._header_box)

        self._error_label = Gtk.Label()
        self._error_label.set_css_classes(["error-label"])
        self._error_label.set_xalign(0)
        self._error_label.set_hexpand(True)
        self._error_label.set_halign(Gtk.Align.FILL)
        self._error_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._error_label.set_single_line_mode(True)
        self._error_label.set_visible(False)
        self._error_label.set_margin_start(8)
        self._error_label.set_margin_end(8)
        self._error_label.set_margin_bottom(4)
        self.append(self._error_label)

        root_model, error = self._create_list_model_for_dir(None)
        self._tree_model = Gtk.TreeListModel.new(
            root_model,
            passthrough=False,
            autoexpand=False,
            create_func=self._on_create_child_model,
        )

        self._selection = Gtk.SingleSelection.new(self._tree_model)
        self._list_view = Gtk.ListView.new(self._selection)
        self._list_view.set_hexpand(True)
        self._list_view.set_vexpand(True)
        self._list_view.set_single_click_activate(True)
        self._list_view.set_factory(self._create_factory())
        self._list_view.connect("activate", self._on_row_activated)

        self._action_group = Gio.SimpleActionGroup()
        self._register_context_actions()
        self.insert_action_group("fileexplorer", self._action_group)

        self._gesture_click = Gtk.GestureClick()
        self._gesture_click.set_button(Gdk.BUTTON_SECONDARY)
        self._gesture_click.connect("pressed", self._on_secondary_click)
        self._list_view.add_controller(self._gesture_click)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self._list_view)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.append(scrolled)

        self._event_bus.subscribe(FolderOpenedEvent, self._on_folder_changed)
        self.connect("unrealize", self._on_unrealize)

    def _on_unrealize(self, widget: Gtk.Widget) -> None:
        """Clean up EventBus subscription when widget is destroyed."""
        self._event_bus.unsubscribe(FolderOpenedEvent, self._on_folder_changed)

        for monitor in self._directory_monitors.values():
            try:
                monitor.cancel()
            except Exception:
                pass
        self._directory_monitors.clear()
        self._pending_refresh_paths.clear()

    def _clear_directory_monitors(self) -> None:
        """Stop all active directory monitors owned by the explorer."""
        for monitor in self._directory_monitors.values():
            try:
                monitor.cancel()
            except Exception:
                pass
        self._directory_monitors.clear()
        self._pending_refresh_paths.clear()

    def _ensure_directory_monitor(self, path: str) -> None:
        """Start monitoring a loaded directory for external filesystem changes."""
        if not path or path in self._directory_monitors or not os.path.isdir(path):
            return

        try:
            gfile = Gio.File.new_for_path(path)
            monitor = gfile.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            monitor.connect("changed", self._on_directory_monitor_changed, path)
            self._directory_monitors[path] = monitor
        except Exception as exc:
            logger.warning(f"Failed to monitor directory {path}: {exc}")

    def _prune_directory_monitors(self) -> None:
        """Stop monitors for directories that are no longer valid or loaded."""
        active_paths = set(self._directory_stores)
        if self._root_path is not None:
            active_paths.add(self._root_path)

        stale_paths = [
            path
            for path in self._directory_monitors
            if path not in active_paths or not os.path.isdir(path)
        ]
        for path in stale_paths:
            monitor = self._directory_monitors.pop(path, None)
            if monitor is not None:
                try:
                    monitor.cancel()
                except Exception:
                    pass
            self._pending_refresh_paths.discard(path)

    def _schedule_directory_refresh(self, path: str) -> None:
        """Queue an in-place directory refresh on the GTK main loop."""
        if not path or path in self._pending_refresh_paths:
            return

        self._pending_refresh_paths.add(path)
        GLib.idle_add(self._refresh_directory_from_monitor, path)

    def _refresh_directory_from_monitor(self, path: str) -> bool:
        """Refresh a monitored directory and clear pending state."""
        self._pending_refresh_paths.discard(path)
        return self._refresh_directory(path)

    def _on_directory_monitor_changed(
        self,
        _monitor: Gio.FileMonitor,
        _file: Gio.File,
        _other_file: Gio.File | None,
        _event_type: Gio.FileMonitorEvent,
        watched_path: str,
    ) -> None:
        """Refresh the watched directory after external filesystem changes."""
        self._schedule_directory_refresh(watched_path)

    def _register_context_actions(self) -> None:
        """Register action handlers used by the popover context menus."""

        actions: dict[str, Callable[[], None]] = {
            "open": self._action_open,
            "rename": self._action_rename,
            "delete": self._action_delete,
            "copy_relative_path": self._action_copy_relative_path,
            "copy_absolute_path": self._action_copy_absolute_path,
            "new_file": self._action_new_file,
            "new_folder": self._action_new_folder,
        }

        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _param, cb=callback: cb())
            self._action_group.add_action(action)

    def _build_file_menu_model(self) -> Gio.Menu:
        """Build the file context menu model."""
        menu = Gio.Menu()
        menu.append("Open", "fileexplorer.open")
        menu.append("Rename", "fileexplorer.rename")
        menu.append("Delete", "fileexplorer.delete")

        copy_section = Gio.Menu()
        copy_section.append("Copy Relative Path", "fileexplorer.copy_relative_path")
        copy_section.append("Copy Absolute Path", "fileexplorer.copy_absolute_path")
        menu.append_section(None, copy_section)
        return menu

    def _build_folder_menu_model(self) -> Gio.Menu:
        """Build the folder context menu model."""
        menu = Gio.Menu()
        menu.append("New File", "fileexplorer.new_file")
        menu.append("New Folder", "fileexplorer.new_folder")
        menu.append("Rename", "fileexplorer.rename")
        menu.append("Delete", "fileexplorer.delete")
        return menu

    def _on_secondary_click(
        self, _gesture: Gtk.GestureClick, _n_press: int, x: float, y: float
    ) -> None:
        """Show a context menu for the currently selected item."""
        item = self._get_context_item_at_point(x, y) or self._get_context_item()
        if item is None:
            return

        self._select_item(item)

        if self._context_popover is not None:
            try:
                self._context_popover.popdown()
                self._context_popover.unparent()
            except Exception:
                pass

        model = self._build_folder_menu_model() if item.is_folder else self._build_file_menu_model()
        popover = Gtk.PopoverMenu.new_from_model(model)
        popover.set_parent(self._list_view)
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.connect("closed", self._on_context_popover_closed)
        popover.popup()
        self._context_item = item
        self._last_context_item = item
        self._context_popover = popover

    def _on_context_popover_closed(self, _popover: Gtk.PopoverMenu) -> None:
        """Clear active context state when the popover closes."""
        self._context_item = None
        self._context_popover = None

    def _get_item_for_widget(self, widget: Gtk.Widget | None) -> FileTreeItem | None:
        """Walk up the widget tree to find the bound file item."""
        current = widget
        while current is not None:
            item = self._widget_items.get(current)
            if item is not None:
                return item
            current = current.get_parent()
        return None

    def _get_context_item_at_point(self, x: float, y: float) -> FileTreeItem | None:
        """Resolve the tree item under the pointer coordinates."""
        try:
            picked = self._list_view.pick(x, y, Gtk.PickFlags.DEFAULT)
        except Exception:
            return None
        if picked is None:
            return None
        return self._get_item_for_widget(picked)

    def _get_selected_tree_item(self) -> FileTreeItem | None:
        """Return the currently selected FileTreeItem, if any."""
        selected = self._selection.get_selected_item()
        if selected is None or not isinstance(selected, Gtk.TreeListRow):
            return None
        tree_item = selected.get_item()
        if isinstance(tree_item, FileTreeItem):
            return tree_item
        return None

    def _get_context_item(self) -> FileTreeItem | None:
        """Return the active context item or the selection."""
        if self._context_item is not None:
            return self._context_item
        if self._last_context_item is not None:
            return self._last_context_item
        return self._get_selected_tree_item()

    def _consume_context_item(self) -> FileTreeItem | None:
        """Return the current action target and clear transient context state."""
        item = self._get_context_item()
        self._context_item = None
        self._last_context_item = None
        return item

    def _find_item_position(self, target: FileTreeItem) -> int | None:
        """Return the current TreeListModel position for a file tree item."""
        for position in range(self._tree_model.get_n_items()):
            row = self._tree_model.get_item(position)
            if not isinstance(row, Gtk.TreeListRow):
                continue
            item = row.get_item()
            if item is target:
                return position
        return None

    def _select_item(self, item: FileTreeItem) -> None:
        """Sync list selection with a specific tree item."""
        position = self._find_item_position(item)
        if position is not None:
            self._selection.set_selected(position)

    def _notify(self, message: str, timeout_ms: int = 2000) -> None:
        """Send a UI-layer notification if a host bridge exists."""
        if self._host_bridge is not None and hasattr(self._host_bridge, "show_notification"):
            self._host_bridge.show_notification(message, timeout_ms)

    def _copy_path_to_clipboard(self, path: str) -> None:
        """Copy text to the GTK clipboard."""
        try:
            clipboard = self.get_clipboard()
        except Exception:
            display = Gdk.Display.get_default()
            clipboard = display.get_clipboard() if display is not None else None

        if clipboard is not None:
            clipboard.set_content(Gdk.ContentProvider.new_for_value(path))
        self._notify(f"Copied: {path}", 2000)

    def _resolve_context_path(self) -> str | None:
        """Return the filesystem path for the active item."""
        item = self._get_context_item()
        if item is None:
            return None
        return item.path

    def _resolve_relative_path(self, path: str) -> str:
        """Return path relative to the loaded explorer root."""
        if self._root_path is None:
            return path
        return os.path.relpath(path, self._root_path)

    def _validate_name(
        self, parent_path: str, name: str, current_path: str | None = None
    ) -> str | None:
        """Validate a filename or folder name for inline operations."""
        if name is None:
            return "Name cannot be empty"

        candidate = name.strip()
        if not candidate:
            return "Name cannot be empty"
        if "/" in candidate or "\x00" in candidate:
            return "Name cannot contain / or null bytes"

        target = os.path.abspath(os.path.join(parent_path, candidate))
        if current_path is not None and os.path.abspath(current_path) == target:
            return None
        if os.path.exists(target):
            return "An item with that name already exists"
        return None

    def _set_entry_error(self, entry: Gtk.Entry, message: str) -> None:
        """Show an inline validation error on an entry."""
        entry.add_css_class("error")
        entry.set_tooltip_text(message)

    def _clear_entry_error(self, entry: Gtk.Entry) -> None:
        """Clear an inline validation error from an entry."""
        entry.remove_css_class("error")
        entry.set_tooltip_text(None)

    def _sync_row_widgets(self, path: str) -> None:
        """Refresh the visible state for a row, if it is currently bound."""
        widgets = self._row_widgets.get(path)
        if widgets is None:
            return

        entry = widgets["entry"]
        stack = widgets["stack"]
        label = widgets["label"]
        item = widgets.get("item")
        if not isinstance(item, FileTreeItem):
            return

        if item.temporary or self._active_inline_item_path == item.path:
            stack.set_visible_child(entry)
            if item.path in self._edit_text_buffer:
                entry.set_text(self._edit_text_buffer[item.path])
            else:
                entry.set_text(item.name)
            entry.select_region(0, -1)
            entry.grab_focus()
        else:
            stack.set_visible_child(label)
            label.set_text(item.name)

    def _start_inline_rename(self, item: FileTreeItem) -> None:
        """Switch a row into inline rename mode."""
        self._active_inline_item_path = item.path
        self._active_inline_mode = "rename"
        self._edit_text_buffer[item.path] = item.name
        self._sync_row_widgets(item.path)

    def _start_inline_create(self, parent_path: str, is_folder: bool) -> None:
        """Insert a temporary row for new file/folder creation."""
        default_name = "New Folder" if is_folder else "untitled"
        temp_path = os.path.join(parent_path, f".slate-temp-{uuid.uuid4().hex}")
        store, _ = self._create_list_model_for_dir(parent_path)
        item = FileTreeItem(
            name=default_name,
            path=temp_path,
            is_folder=is_folder,
            temporary=True,
            parent_path=parent_path,
            create_kind="folder" if is_folder else "file",
        )
        store.insert(0, item)
        self._active_inline_item_path = item.path
        self._active_inline_mode = "create"
        self._edit_text_buffer[item.path] = default_name

    def _cancel_inline_edit(self, item: FileTreeItem, path: str | None = None) -> None:
        """Cancel inline edit mode for a row."""
        item_path = path or item.path
        self._edit_text_buffer.pop(item_path, None)
        if self._active_inline_item_path == item_path:
            self._active_inline_item_path = None
            self._active_inline_mode = None

        if item.temporary and item.parent_path is not None:
            store = self._directory_stores.get(item.parent_path)
            if store is not None:
                for index in range(store.get_n_items()):
                    candidate = store.get_item(index)
                    if isinstance(candidate, FileTreeItem) and candidate.path == item.path:
                        store.remove(index)
                        break

        self._sync_row_widgets(item.path)

    def _commit_inline_edit(self, item: FileTreeItem, entry: Gtk.Entry) -> None:
        """Commit an inline create or rename operation."""
        parent_path = item.parent_path or os.path.dirname(item.path)
        new_name = entry.get_text()
        current_path = None if item.temporary else item.path
        error = self._validate_name(parent_path, new_name, current_path=current_path)
        if error is not None:
            self._set_entry_error(entry, error)
            self._edit_text_buffer[item.path] = new_name
            return

        self._clear_entry_error(entry)

        try:
            old_path = item.path
            if item.temporary and item.create_kind == "folder":
                self._file_service.create_folder(parent_path, new_name.strip())
            elif item.temporary:
                self._file_service.create_file(parent_path, new_name.strip())
            else:
                new_path = self._file_service.rename(item.path, new_name.strip())
                item.path = new_path
                item.name = new_name.strip()
                widgets = self._row_widgets.pop(old_path, None)
                if widgets is not None:
                    widgets["item"] = item
                    self._row_widgets[new_path] = widgets
                self._edit_text_buffer.pop(old_path, None)
        except Exception as exc:
            self._set_entry_error(entry, str(exc))
            self._edit_text_buffer[item.path] = new_name
            return

        self._cancel_inline_edit(item, path=old_path if not item.temporary else item.path)
        GLib.idle_add(self._refresh_directory, parent_path)

    def _refresh_directory(self, path: str) -> bool:
        """Refresh a loaded directory in place."""
        if not path:
            return False

        _store, error = self._create_list_model_for_dir(path)
        if error and path != self._root_path and not os.path.exists(path):
            self._clear_error()
        elif error:
            self._set_error(error)
        else:
            self._clear_error()
        self._prune_directory_monitors()
        return False

    def _focus_inline_entry(self, entry: Gtk.Entry, path: str) -> bool:
        """Focus the inline entry after GTK has allocated the row."""
        if self._active_inline_item_path != path and path not in self._edit_text_buffer:
            return False

        try:
            entry.grab_focus()
            entry.select_region(0, -1)
        except Exception:
            return False
        return False

    def _delete_item(self, item: FileTreeItem) -> None:
        """Delete a file or folder after confirmation."""
        parent_path = os.path.dirname(item.path)
        is_folder = item.is_folder
        body = "This action cannot be undone."
        if is_folder:
            child_count = self._file_service.count_immediate_children(item.path)
            if child_count > 0:
                body = f"This folder contains {child_count} items. Delete anyway?"

        dialog = Gtk.Dialog()
        root = self.get_root()
        if isinstance(root, Gtk.Window):
            dialog.set_transient_for(root)
        dialog.set_modal(True)
        dialog.set_title(f"Delete {item.name}?")
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        delete_button = dialog.add_button("Delete", Gtk.ResponseType.OK)
        delete_button.add_css_class("destructive-action")
        dialog.set_default_response(Gtk.ResponseType.OK)

        content_area = dialog.get_content_area()
        title_label = Gtk.Label(label=f"Delete {item.name}?")
        title_label.set_xalign(0)
        title_label.set_margin_top(8)
        title_label.set_margin_bottom(8)
        title_label.set_margin_start(16)
        title_label.set_margin_end(16)
        content_area.append(title_label)

        body_label = Gtk.Label(label=body)
        body_label.set_wrap(True)
        body_label.set_xalign(0)
        body_label.set_margin_bottom(16)
        body_label.set_margin_start(16)
        body_label.set_margin_end(16)
        content_area.append(body_label)

        def on_response(response_dialog: Gtk.Dialog, response_id: int) -> None:
            response_dialog.hide()
            if response_id != Gtk.ResponseType.OK:
                return
            try:
                if is_folder:
                    self._file_service.delete_folder(item.path)
                else:
                    self._file_service.delete_file(item.path)
            except Exception as exc:
                logger.warning(f"Failed to delete {item.path}: {exc}")
                return

            GLib.idle_add(self._refresh_directory, parent_path)

        dialog.connect("response", on_response)
        dialog.present()

    def _action_open(self) -> None:
        """Open the active item."""
        item = self._consume_context_item()
        if item is not None and not item.is_folder:
            self._event_bus.emit(OpenFileRequestedEvent(path=item.path))

    def _action_rename(self) -> None:
        """Begin inline rename for the active item."""
        item = self._consume_context_item()
        if item is not None and not item.temporary:
            self._start_inline_rename(item)

    def _action_delete(self) -> None:
        """Delete the active item after confirmation."""
        item = self._consume_context_item()
        if item is not None and not item.temporary:
            self._delete_item(item)

    def _action_copy_relative_path(self) -> None:
        """Copy the active item's relative path."""
        item = self._consume_context_item()
        if item is None:
            return
        self._copy_path_to_clipboard(self._resolve_relative_path(item.path))

    def _action_copy_absolute_path(self) -> None:
        """Copy the active item's absolute path."""
        item = self._consume_context_item()
        if item is None:
            return
        self._copy_path_to_clipboard(item.path)

    def _action_new_file(self) -> None:
        """Insert an inline new-file row under the active folder."""
        item = self._consume_context_item()
        if item is None:
            return
        parent_path = item.path if item.is_folder else os.path.dirname(item.path)
        self._start_inline_create(parent_path, is_folder=False)

    def _action_new_folder(self) -> None:
        """Insert an inline new-folder row under the active folder."""
        item = self._consume_context_item()
        if item is None:
            return
        parent_path = item.path if item.is_folder else os.path.dirname(item.path)
        self._start_inline_create(parent_path, is_folder=True)

    def load_folder(self, path: str) -> None:
        """Load a folder as the tree root."""
        if not os.path.isdir(path):
            logger.warning(f"Cannot load folder: {path} is not a directory")
            self._set_error(f"Cannot open: {path} is not a directory")
            return

        self._root_path = os.path.abspath(path)
        self._clear_error()
        self._context_item = None
        self._last_context_item = None
        if self._context_popover is not None:
            try:
                self._context_popover.popdown()
                self._context_popover.unparent()
            except Exception:
                pass
        self._context_popover = None
        self._active_inline_item_path = None
        self._active_inline_mode = None
        self._edit_text_buffer.clear()
        self._directory_stores.clear()
        self._clear_directory_monitors()
        self._row_widgets.clear()
        self._widget_items.clear()

        root_model, error = self._create_list_model_for_dir(self._root_path)
        if error:
            self._set_error(error)
        else:
            self._clear_error()

        new_tree_model = Gtk.TreeListModel.new(
            root_model,
            passthrough=False,
            autoexpand=False,
            create_func=self._on_create_child_model,
        )
        self._tree_model = new_tree_model
        self._selection.set_model(new_tree_model)
        self._update_breadcrumb(path)

    def _build_breadcrumb(self) -> Gtk.ScrolledWindow:
        """Create scrollable breadcrumb bar at top of panel."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scrolled.set_max_content_height(28)
        scrolled.set_min_content_height(28)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_css_classes(["breadcrumb-bar"])
        box.set_hexpand(False)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        scrolled.set_child(box)

        self._breadcrumb_inner_box = box
        return scrolled

    def _build_header(self) -> Gtk.Box:
        """Create header with breadcrumb bar and menu button."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header_box.set_hexpand(True)

        header_box.append(self._breadcrumb_box)

        menu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        menu_box.set_hexpand(True)
        menu_box.set_margin_start(8)
        menu_box.set_margin_end(4)
        menu_box.set_margin_top(2)
        menu_box.set_margin_bottom(2)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        menu_box.append(spacer)

        self._menu_button = Gtk.MenuButton()
        self._menu_button.set_icon_name("view-more-symbolic")
        self._menu_button.set_tooltip_text("View options")
        self._menu_button.set_css_classes(["flat"])

        popover = Gtk.Popover()
        self._menu_button.set_popover(popover)

        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        popover_box.set_margin_start(12)
        popover_box.set_margin_end(12)
        popover_box.set_margin_top(8)
        popover_box.set_margin_bottom(8)

        self._hidden_check = Gtk.CheckButton(label="Show Hidden Files")
        self._hidden_check.set_active(self._show_hidden_files)
        self._hidden_check.connect("toggled", self._on_hidden_check_toggled)
        popover_box.append(self._hidden_check)

        popover.set_child(popover_box)

        menu_box.append(self._menu_button)
        header_box.append(menu_box)

        return header_box

    def _on_hidden_check_toggled(self, check_button: Gtk.CheckButton) -> None:
        """Handle checkbox toggle."""
        self._show_hidden_files = check_button.get_active()
        if self._root_path is not None:
            self.load_folder(self._root_path)

        if self._config_service is not None:
            value = "true" if self._show_hidden_files else "false"
            try:
                self._config_service.set("plugin.file_explorer", "show_hidden_files", value)
            except Exception as e:
                logger.warning(f"Failed to persist hidden files preference: {e}")

    def _update_breadcrumb(self, path: str) -> None:
        """Update breadcrumb bar to show current folder path."""
        inner_box = self._breadcrumb_inner_box
        child = inner_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            inner_box.remove(child)
            child = next_child

        parts: list[tuple[str, str]] = []
        current = os.path.abspath(path)
        while True:
            parts.append((os.path.basename(current), current))
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        parts.reverse()

        for i, (name, full_path) in enumerate(parts):
            if i > 0:
                sep = Gtk.Label(label="›")
                sep.set_opacity(0.6)
                inner_box.append(sep)

            btn = Gtk.Button(label=name or "/")
            btn.set_css_classes(["breadcrumb-segment", "flat"])
            btn.connect("clicked", lambda _w, p=full_path: self._on_breadcrumb_clicked(p))
            inner_box.append(btn)

    def _on_breadcrumb_clicked(self, path: str) -> None:
        """Handle breadcrumb segment click — navigate to parent directory."""
        self.load_folder(path)

    def _set_error(self, message: str) -> None:
        """Show error message in the UI."""
        self._load_error = message
        self._error_label.set_text(message)
        self._error_label.set_visible(True)

    def _clear_error(self) -> None:
        """Hide error message."""
        self._load_error = None
        self._error_label.set_visible(False)

    def _on_create_child_model(self, item: Any) -> Gio.ListStore | None:
        """Create child model lazily when a folder row is expanded."""
        if not isinstance(item, FileTreeItem):
            return None
        if not item.is_folder:
            return None
        store, _error = self._create_list_model_for_dir(item.path)
        return store

    def _create_list_model_for_dir(self, dir_path: str | None) -> tuple[Gio.ListStore, str | None]:
        """Create a ListStore with items from a directory. Returns (store, error)."""
        store = self._directory_stores.get(dir_path or "")
        if store is None:
            store = Gio.ListStore.new(FileTreeItem)
            if dir_path is not None:
                self._directory_stores[dir_path] = store
        else:
            while store.get_n_items() > 0:
                store.remove(0)

        if dir_path is None:
            return store, None

        self._ensure_directory_monitor(dir_path)

        try:
            entries = self._file_service.list_directory(dir_path)
        except PermissionError:
            return store, f"Permission denied: {dir_path}"
        except FileNotFoundError:
            return store, f"Directory not found: {dir_path}"
        except NotADirectoryError:
            return store, f"Not a directory: {dir_path}"
        except Exception:
            logger.warning(f"Cannot list directory {dir_path}")
            return store, f"Cannot read: {dir_path}"

        for entry in entries:
            basename = os.path.basename(entry.path)
            if basename == ".git":
                continue
            if not self._show_hidden_files and basename.startswith("."):
                continue
            store.append(
                FileTreeItem(
                    name=basename,
                    path=entry.path,
                    is_folder=entry.is_dir,
                )
            )

        return store, None

    def _create_factory(self) -> Gtk.SignalListItemFactory:
        """Create factory that binds tree items to row widgets."""
        factory = Gtk.SignalListItemFactory()

        def setup(_factory: Any, list_item: Any) -> None:
            box = Gtk.Box(spacing=4)
            expander = Gtk.TreeExpander()
            icon = Gtk.Image()
            stack = Gtk.Stack()
            stack.set_hexpand(True)

            label = Gtk.Label(xalign=0)
            label.set_hexpand(True)
            label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END

            entry = Gtk.Entry()
            entry.set_hexpand(True)

            stack.add_named(label, "label")
            stack.add_named(entry, "entry")
            box.append(icon)
            box.append(stack)
            expander.set_child(box)
            list_item.set_child(expander)

            list_item._slate_widgets = {
                "box": box,
                "expander": expander,
                "icon": icon,
                "stack": stack,
                "label": label,
                "entry": entry,
            }

            def on_entry_changed(changed_entry: Gtk.Entry) -> None:
                row = list_item.get_item()
                if not isinstance(row, Gtk.TreeListRow):
                    return
                item = row.get_item()
                if not isinstance(item, FileTreeItem):
                    return
                if self._active_inline_item_path == item.path or item.temporary:
                    self._edit_text_buffer[item.path] = changed_entry.get_text()

            def on_entry_activate(activated_entry: Gtk.Entry) -> None:
                row = list_item.get_item()
                if not isinstance(row, Gtk.TreeListRow):
                    return
                item = row.get_item()
                if isinstance(item, FileTreeItem):
                    self._commit_inline_edit(item, activated_entry)

            def on_key_pressed(
                _controller: Gtk.EventControllerKey,
                keyval: int,
                _keycode: int,
                _state: int,
            ) -> bool:
                if keyval != Gdk.KEY_Escape:
                    return False
                row = list_item.get_item()
                if not isinstance(row, Gtk.TreeListRow):
                    return False
                item = row.get_item()
                if isinstance(item, FileTreeItem):
                    self._cancel_inline_edit(item)
                return True

            entry.connect("changed", on_entry_changed)
            entry.connect("activate", on_entry_activate)
            controller = Gtk.EventControllerKey.new()
            controller.connect("key-pressed", on_key_pressed)
            entry.add_controller(controller)

        def bind(_factory: Any, list_item: Any) -> None:
            widgets = getattr(list_item, "_slate_widgets", None)
            if not isinstance(widgets, dict):
                return

            expander = widgets.get("expander")
            if expander is None:
                return
            if list_item.get_child() is None:
                list_item.set_child(expander)

            row = list_item.get_item()
            if not isinstance(row, Gtk.TreeListRow):
                return
            expander.set_list_row(row)
            item = row.get_item()
            if not isinstance(item, FileTreeItem):
                return
            box = expander.get_child()
            if box is None:
                return
            icon = box.get_first_child()
            if icon is None:
                return
            stack = icon.get_next_sibling()
            if stack is None:
                return
            label = widgets["label"]
            entry = widgets["entry"]
            widgets["item"] = item
            self._row_widgets[item.path] = widgets
            self._widget_items[box] = item
            self._widget_items[expander] = item
            self._widget_items[stack] = item
            self._widget_items[label] = item
            self._widget_items[entry] = item

            label.set_text(item.name)
            entry.set_text(self._edit_text_buffer.get(item.path, item.name))
            entry.set_hexpand(True)
            label.set_hexpand(True)
            label.set_ellipsize(3)
            label.set_css_classes(["file-tree-label", "truncate"])
            if item.is_folder:
                icon.set_from_icon_name("folder-symbolic")
            else:
                try:
                    gicon = Gio.content_type_get_icon(Gio.content_type_guess(item.name, None)[0])
                    icon.set_from_gicon(gicon)
                except Exception:
                    icon.set_from_icon_name("text-x-generic-symbolic")

            if item.temporary or self._active_inline_item_path == item.path:
                stack.set_visible_child_name("entry")
                GLib.idle_add(self._focus_inline_entry, entry, item.path)
            else:
                stack.set_visible_child_name("label")

        def unbind(_factory: Any, list_item: Any) -> None:
            row = list_item.get_item()
            if isinstance(row, Gtk.TreeListRow):
                item = row.get_item()
                if isinstance(item, FileTreeItem):
                    self._row_widgets.pop(item.path, None)

            widgets = getattr(list_item, "_slate_widgets", None)
            if isinstance(widgets, dict):
                for key in ("box", "expander", "icon", "stack", "label", "entry"):
                    widget = widgets.get(key)
                    self._widget_items.pop(widget, None)
                widgets.pop("item", None)

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        factory.connect("unbind", unbind)
        return factory

    def _on_row_activated(self, _list_view: Gtk.ListView, _position: int) -> None:
        """Handle file/folder activation — open file or expand/collapse folder."""
        item = self._selection.get_selected_item()
        if item is None:
            return
        if not isinstance(item, Gtk.TreeListRow):
            return
        tree_item = item.get_item()
        if tree_item and tree_item.is_folder:
            item.set_expanded(not item.get_expanded())
        elif tree_item:
            self._event_bus.emit(OpenFileRequestedEvent(path=tree_item.path))

    def _on_folder_changed(self, event: FolderOpenedEvent) -> None:
        """Reload tree root when folder changes."""
        if os.path.isdir(event.path):
            self.load_folder(event.path)

    def _on_file_open_request(self, event: OpenFileRequestedEvent) -> None:
        """Handle file open request from event bus."""
        pass

    def toggle_hidden_files(self) -> None:
        """Toggle hidden files visibility and reload the tree."""
        self._show_hidden_files = not self._show_hidden_files
        if self._root_path is not None:
            self.load_folder(self._root_path)

        if self._config_service is not None:
            value = "true" if self._show_hidden_files else "false"
            try:
                self._config_service.set("plugin.file_explorer", "show_hidden_files", value)
            except Exception as e:
                logger.warning(f"Failed to persist hidden files preference: {e}")
