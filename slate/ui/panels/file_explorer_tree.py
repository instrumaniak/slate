"""File Explorer tree widget — GTK4 ListView + TreeListModel with lazy loading."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GObject, Gtk  # noqa: E402

from slate.core.events import FolderOpenedEvent, OpenFileRequestedEvent  # noqa: E402

if TYPE_CHECKING:
    from slate.core.event_bus import EventBus
    from slate.services.file_service import FileService

logger = logging.getLogger(__name__)


class FileTreeItem(GObject.Object):
    """Wrapper for tree node data used by Gtk.TreeListModel."""

    def __init__(self, name: str, path: str, is_folder: bool) -> None:
        super().__init__()
        self.name = name
        self.path = path
        self.is_folder = is_folder


class FileExplorerTree(Gtk.Box):
    """Tree view widget for browsing project files with lazy loading.

    Uses Gtk.ListView + Gtk.TreeListModel (modern GTK4 stack).
    Gtk.TreeView is deprecated since GTK 4.10.
    """

    def __init__(self, file_service: FileService, event_bus: EventBus) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._file_service = file_service
        self._event_bus = event_bus
        self._root_path: str | None = None
        self._load_error: str | None = None

        self._breadcrumb_box = self._build_breadcrumb()
        self.append(self._breadcrumb_box)

        self._error_label = Gtk.Label()
        self._error_label.set_css_classes(["error-label"])
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

    def load_folder(self, path: str) -> None:
        """Load a folder as the tree root."""
        if not os.path.isdir(path):
            logger.warning(f"Cannot load folder: {path} is not a directory")
            self._set_error(f"Cannot open: {path} is not a directory")
            return

        self._root_path = path
        self._clear_error()

        root_model, error = self._create_list_model_for_dir(path)
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
        store = Gio.ListStore.new(FileTreeItem)

        if dir_path is None:
            return store, None

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
            box = Gtk.Box(spacing=6)
            expander = Gtk.TreeExpander()
            icon = Gtk.Image()
            label = Gtk.Label(xalign=0)
            label.set_hexpand(True)
            label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            box.append(icon)
            box.append(label)
            expander.set_child(box)
            list_item.set_child(expander)

        def bind(_factory: Any, list_item: Any) -> None:
            expander = list_item.get_child()
            row = list_item.get_item()
            expander.set_list_row(row)
            item = row.get_item()
            if item is None:
                return
            box = expander.get_child()
            icon = box.get_first_child()
            label = icon.get_next_sibling()
            label.set_text(item.name)
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

        factory.connect("setup", setup)
        factory.connect("bind", bind)
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
        self.load_folder(event.path)

    def _on_file_open_request(self, event: OpenFileRequestedEvent) -> None:
        """Handle file open request from event bus."""
        pass
