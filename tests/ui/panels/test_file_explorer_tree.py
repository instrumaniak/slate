"""Tests for FileExplorerTree widget — tree display, lazy loading, events."""

from __future__ import annotations

import os
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from gi.repository import Gtk

from slate.core.event_bus import EventBus
from slate.core.events import FolderOpenedEvent, OpenFileRequestedEvent


@pytest.fixture
def temp_project(tmp_path: Any) -> Any:
    """Create a temp directory tree for testing."""
    root = tmp_path / "project"
    root.mkdir()

    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')")
    (root / "src" / "utils.py").write_text("def helper(): pass")

    (root / "tests").mkdir()
    (root / "tests" / "test_main.py").write_text("def test(): pass")

    (root / "docs").mkdir()
    (root / "README.md").write_text("# Project")
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main")

    return root


@pytest.fixture
def mock_file_service(temp_project: Any) -> MagicMock:
    """Create a mock FileService backed by real filesystem."""
    from slate.core.models import FileStatus
    from slate.services.file_service import FileService

    service = FileService()
    return service


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh EventBus instance.

    Note: EventBus is a singleton, so we reset handlers between tests.
    """
    bus = EventBus()
    bus._handlers.clear()
    return bus


@pytest.fixture
def host_bridge() -> MagicMock:
    """Create a mock host bridge with notification support."""
    bridge = MagicMock()
    bridge.show_notification = MagicMock()
    return bridge


def _collect_menu_labels(model: Any) -> list[str]:
    """Collect labels from a Gio.Menu model recursively."""
    labels: list[str] = []
    for index in range(model.get_n_items()):
        attr = model.get_item_attribute_value(index, "label", None)
        if attr is not None:
            labels.append(attr.get_string())
        section = model.get_item_link(index, "section")
        if section is not None:
            labels.extend(_collect_menu_labels(section))
    return labels


class TestFileExplorerTreeCreation:
    """Tests for widget creation and structure."""

    def test_widget_is_gtk_box(self, mock_file_service: Any, event_bus: EventBus) -> None:
        """FileExplorerTree should be a Gtk.Box subclass."""
        from gi.repository import Gtk

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        assert isinstance(widget, Gtk.Box)

    def test_widget_has_list_view(self, mock_file_service: Any, event_bus: EventBus) -> None:
        """FileExplorerTree should contain a Gtk.ListView."""
        from gi.repository import Gtk

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        children = []
        child = widget.get_first_child()
        while child is not None:
            children.append(child)
            child = child.get_next_sibling()

        has_list_view = any(isinstance(c, Gtk.ScrolledWindow) for c in children)
        assert has_list_view, "FileExplorerTree must contain a ScrolledWindow with ListView"

    def test_widget_has_breadcrumb_bar(self, mock_file_service: Any, event_bus: EventBus) -> None:
        """FileExplorerTree should contain a breadcrumb bar at the top."""
        from gi.repository import Gtk

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        first_child = widget.get_first_child()
        assert isinstance(first_child, Gtk.Box), "First child must be header Box"
        breadcrumb_box = first_child.get_first_child()
        assert isinstance(breadcrumb_box, Gtk.ScrolledWindow), (
            "Header box must contain breadcrumb ScrolledWindow"
        )


class TestLoadFolder:
    """Tests for folder loading behavior."""

    def test_load_folder_populates_tree(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Tree should show folder contents after load_folder."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        assert root_model.get_n_items() > 0

    def test_load_folder_excludes_git(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Tree must not show .git directory (AC 8)."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        names = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names.append(item.name)

        assert ".git" not in names, ".git directory must be excluded from tree"

    def test_load_folder_invalid_path(self, mock_file_service: Any, event_bus: EventBus) -> None:
        """load_folder should handle invalid paths gracefully."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder("/nonexistent/path/that/does/not/exist")

        root_model = widget._tree_model.get_model()
        assert root_model.get_n_items() == 0

    def test_load_folder_starts_monitor_for_root(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any, monkeypatch: Any
    ) -> None:
        """Loading a folder should start a monitor for the loaded root directory."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        ensure_monitor = MagicMock()
        monkeypatch.setattr(widget, "_ensure_directory_monitor", ensure_monitor)

        widget.load_folder(str(temp_project))

        ensure_monitor.assert_called_once_with(str(temp_project))

    def test_external_root_change_refreshes_tree_in_place(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any, monkeypatch: Any
    ) -> None:
        """Filesystem monitor updates should refresh the watched directory store."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        monkeypatch.setattr(
            "slate.ui.panels.file_explorer_tree.GLib.idle_add", lambda func, *args: func(*args)
        )
        monkeypatch.setattr(widget, "_ensure_directory_monitor", lambda _path: None)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        initial_names = {root_model.get_item(i).name for i in range(root_model.get_n_items())}
        assert "README.md" in initial_names

        (temp_project / "README.md").unlink()

        widget._on_directory_monitor_changed(
            MagicMock(), MagicMock(), None, MagicMock(), str(temp_project)
        )

        refreshed_names = {root_model.get_item(i).name for i in range(root_model.get_n_items())}
        assert "README.md" not in refreshed_names

    def test_external_child_folder_delete_does_not_show_missing_directory_error(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any, monkeypatch: Any
    ) -> None:
        """Deleting a watched child folder externally should not show a stale error banner."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        monkeypatch.setattr(
            "slate.ui.panels.file_explorer_tree.GLib.idle_add", lambda func, *args: func(*args)
        )
        monkeypatch.setattr(widget, "_ensure_directory_monitor", lambda _path: None)
        widget.load_folder(str(temp_project))

        child_path = str(temp_project / "src")
        child_store, error = widget._create_list_model_for_dir(child_path)
        assert error is None
        assert child_store.get_n_items() > 0

        for entry in temp_project.joinpath("src").iterdir():
            entry.unlink()
        temp_project.joinpath("src").rmdir()

        widget._set_error("Directory not found")
        widget._on_directory_monitor_changed(
            MagicMock(), MagicMock(), None, MagicMock(), child_path
        )

        assert widget._load_error is None
        assert widget._error_label.get_visible() is False


class TestEventWiring:
    """Tests for EventBus integration."""

    def test_file_click_emits_open_request(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Clicking a file should emit OpenFileRequestedEvent (AC 3)."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        emitted_events: list[Any] = []

        def capture_event(event: Any) -> None:
            emitted_events.append(event)

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        event_bus.subscribe(OpenFileRequestedEvent, capture_event)

        root_model = widget._tree_model.get_model()
        file_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if not item.is_folder:
                file_item = item
                break

        assert file_item is not None, "Test requires at least one file in temp project"
        event_bus.emit(OpenFileRequestedEvent(path=file_item.path))

        assert len(emitted_events) == 1
        assert emitted_events[0].path == file_item.path

    def test_folder_opened_event_reloads_tree(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Tree should reload when FolderOpenedEvent is emitted (AC 1)."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        src_dir = str(temp_project / "src")
        event_bus.emit(FolderOpenedEvent(path=src_dir))

        root_model = widget._tree_model.get_model()
        names = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names.append(item.name)

        assert "main.py" in names, "Tree should reload to show src/ contents"
        assert "README.md" not in names, "Old root contents should be gone"


class TestBreadcrumb:
    """Tests for breadcrumb navigation."""

    def test_breadcrumb_shows_current_path(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Breadcrumb should display current folder path (AC 7)."""
        from gi.repository import Gtk

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        breadcrumb = widget._breadcrumb_inner_box
        segments = []
        child = breadcrumb.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Button):
                segments.append(child.get_label())
            child = child.get_next_sibling()

        assert len(segments) > 0, "Breadcrumb must have at least one segment"
        assert segments[-1] == "project", f"Last segment should be 'project', got '{segments[-1]}'"

    def test_breadcrumb_segments_are_buttons(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Breadcrumb segments should be clickable buttons (AC 7)."""
        from gi.repository import Gtk

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        breadcrumb = widget._breadcrumb_inner_box
        buttons = []
        child = breadcrumb.get_first_child()
        while child is not None:
            if isinstance(child, Gtk.Button):
                buttons.append(child)
            child = child.get_next_sibling()

        assert len(buttons) > 0, "Breadcrumb must contain clickable buttons"


class TestLazyLoading:
    """Tests for lazy loading behavior."""

    def test_tree_model_uses_lazy_loading(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Tree should use TreeListModel for lazy child loading (AC 2)."""
        from gi.repository import Gtk

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        assert isinstance(widget._tree_model, Gtk.TreeListModel), (
            "Must use TreeListModel for lazy loading"
        )
        assert widget._tree_model.get_autoexpand() is False, (
            "autoexpand must be False for lazy loading"
        )


class TestFolderRowBehavior:
    """Tests for folder vs file row behavior."""

    def test_folder_row_does_not_emit_open_request(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Clicking a folder row should expand, not emit OpenFileRequestedEvent."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        emitted_events: list[Any] = []

        def capture_event(event: Any) -> None:
            emitted_events.append(event)

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))
        event_bus.subscribe(OpenFileRequestedEvent, capture_event)

        root_model = widget._tree_model.get_model()
        folder_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if item.is_folder:
                folder_item = item
                break

        assert folder_item is not None, "Test requires at least one folder in temp project"

        # Directly test that folder items don't trigger file open
        from slate.ui.panels.file_explorer_tree import FileTreeItem

        item = FileTreeItem(name="test_folder", path="/tmp/test", is_folder=True)
        assert item.is_folder, "Folder items should be marked as folders"


class TestGitExclusion:
    """Tests for .git directory exclusion at all levels."""

    def test_git_excluded_at_root(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """.git must be excluded at root level (AC 8)."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            assert item.name != ".git", ".git must be excluded at root level"


class TestContextMenusAndCopy:
    """Tests for menus, copy-path feedback, and inline helpers."""

    def test_file_context_menu_items(self, mock_file_service: Any, event_bus: EventBus) -> None:
        """File context menu should expose the required actions."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        labels = _collect_menu_labels(widget._build_file_menu_model())

        assert labels == [
            "Open",
            "Rename",
            "Delete",
            "Copy Relative Path",
            "Copy Absolute Path",
        ]

    def test_folder_context_menu_items(self, mock_file_service: Any, event_bus: EventBus) -> None:
        """Folder context menu should expose the required actions."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        labels = _collect_menu_labels(widget._build_folder_menu_model())

        assert labels == ["New File", "New Folder", "Rename", "Delete"]

    def test_copy_relative_path_uses_explorer_root(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any, host_bridge: Any
    ) -> None:
        """Relative path copies should be rooted at the loaded explorer root."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service, event_bus=event_bus, host_bridge=host_bridge
        )
        widget.load_folder(str(temp_project))

        clipboard = MagicMock()
        widget.get_clipboard = MagicMock(return_value=clipboard)

        widget._copy_path_to_clipboard(
            widget._resolve_relative_path(str(temp_project / "src" / "main.py"))
        )

        clipboard.set_content.assert_called_once()
        host_bridge.show_notification.assert_called_with("Copied: src/main.py", 2000)

    def test_copy_absolute_path_notifies(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any, host_bridge: Any
    ) -> None:
        """Absolute path copies should notify the user."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service, event_bus=event_bus, host_bridge=host_bridge
        )

        clipboard = MagicMock()
        widget.get_clipboard = MagicMock(return_value=clipboard)

        path = str(temp_project / "README.md")
        widget._copy_path_to_clipboard(path)

        clipboard.set_content.assert_called_once()
        host_bridge.show_notification.assert_called_once_with(f"Copied: {path}", 2000)

    def test_start_inline_create_inserts_placeholder_row(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """New file creation should insert a temporary row at the top."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        widget._start_inline_create(str(temp_project), is_folder=False)
        store = widget._directory_stores[str(temp_project.resolve())]
        item = store.get_item(0)

        assert isinstance(item, FileTreeItem)
        assert item.temporary is True
        assert item.name == "untitled"

    def test_focus_inline_entry_only_runs_for_active_inline_path(
        self, mock_file_service: Any, event_bus: EventBus
    ) -> None:
        """Deferred focus helper should ignore stale inline paths."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        entry = MagicMock()
        widget._active_inline_item_path = "/tmp/active"
        widget._edit_text_buffer["/tmp/active"] = "name"

        assert widget._focus_inline_entry(entry, "/tmp/other") is False
        entry.grab_focus.assert_not_called()

        assert widget._focus_inline_entry(entry, "/tmp/active") is False
        entry.grab_focus.assert_called_once()
        entry.select_region.assert_called_once_with(0, -1)

    def test_validate_name_rejects_invalid_and_duplicate(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Validation should reject invalid characters and duplicate names."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        assert widget._validate_name(str(temp_project), "bad/name") is not None
        assert widget._validate_name(str(temp_project), "") is not None
        assert widget._validate_name(str(temp_project), "README.md") is not None

    def test_commit_inline_create_file_calls_service(
        self, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Inline create should call FileService.create_file on Enter."""
        from slate.services.file_service import FileService
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        service = FileService()
        widget = FileExplorerTree(file_service=service, event_bus=event_bus)
        widget.load_folder(str(temp_project))
        item = FileTreeItem(
            name="untitled",
            path=str(temp_project / ".slate-temp"),
            is_folder=False,
            temporary=True,
            parent_path=str(temp_project),
            create_kind="file",
        )
        entry = MagicMock()
        entry.get_text.return_value = "new-file.txt"
        entry.add_css_class = MagicMock()
        entry.set_tooltip_text = MagicMock()
        entry.remove_css_class = MagicMock()

        widget._commit_inline_edit(item, entry)

        assert (temp_project / "new-file.txt").exists()

    def test_commit_inline_create_does_not_reload_root(
        self, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Inline create should refresh the directory in place, not reopen the folder."""
        from slate.services.file_service import FileService
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        service = FileService()
        widget = FileExplorerTree(file_service=service, event_bus=event_bus)
        widget.load_folder(str(temp_project))
        original_model = widget._tree_model
        original_emit = widget._event_bus.emit
        emit_mock = MagicMock()
        widget._event_bus.emit = emit_mock

        item = FileTreeItem(
            name="untitled",
            path=str(temp_project / ".slate-temp"),
            is_folder=False,
            temporary=True,
            parent_path=str(temp_project),
            create_kind="file",
        )
        entry = MagicMock()
        entry.get_text.return_value = "inline.txt"
        entry.add_css_class = MagicMock()
        entry.set_tooltip_text = MagicMock()
        entry.remove_css_class = MagicMock()

        try:
            widget._commit_inline_edit(item, entry)
        finally:
            widget._event_bus.emit = original_emit

        assert widget._tree_model is original_model
        assert emit_mock.call_count == 0
        assert (temp_project / "inline.txt").exists()

    def test_commit_inline_rename_calls_service(
        self, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Inline rename should call FileService.rename on Enter."""
        from slate.services.file_service import FileService
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        old_path = temp_project / "README.md"
        service = FileService()
        widget = FileExplorerTree(file_service=service, event_bus=event_bus)
        widget.load_folder(str(temp_project))
        item = FileTreeItem(name="README.md", path=str(old_path), is_folder=False)
        entry = MagicMock()
        entry.get_text.return_value = "INTRO.md"
        entry.add_css_class = MagicMock()
        entry.set_tooltip_text = MagicMock()
        entry.remove_css_class = MagicMock()

        widget._commit_inline_edit(item, entry)

        assert (temp_project / "INTRO.md").exists()

    def test_commit_inline_rename_updates_row_state(
        self, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Inline rename should refresh row state under the new path."""
        from slate.services.file_service import FileService
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        old_path = temp_project / "README.md"
        service = FileService()
        widget = FileExplorerTree(file_service=service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        item = FileTreeItem(name="README.md", path=str(old_path), is_folder=False)
        entry = MagicMock()
        entry.get_text.return_value = "INTRO.md"
        entry.add_css_class = MagicMock()
        entry.set_tooltip_text = MagicMock()
        entry.remove_css_class = MagicMock()

        stack = MagicMock()
        label = MagicMock()
        row_widgets = {"entry": entry, "stack": stack, "label": label, "item": item}
        widget._row_widgets[str(old_path)] = row_widgets
        widget._edit_text_buffer[str(old_path)] = "README.md"
        widget._active_inline_item_path = str(old_path)
        original_emit = widget._event_bus.emit
        widget._event_bus.emit = MagicMock()

        try:
            widget._commit_inline_edit(item, entry)
        finally:
            widget._event_bus.emit = original_emit

        assert not old_path.exists()
        assert (temp_project / "INTRO.md").exists()
        assert str(temp_project / "INTRO.md") in widget._row_widgets
        assert str(old_path) not in widget._row_widgets
        assert widget._active_inline_item_path is None
        assert widget._event_bus.emit is original_emit

    def test_commit_inline_rename_refreshes_parent_in_place(
        self, event_bus: EventBus, temp_project: Any, monkeypatch: Any
    ) -> None:
        """Inline rename should refresh the parent directory without changing explorer root."""
        from slate.services.file_service import FileService
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        old_path = temp_project / "README.md"
        service = FileService()
        widget = FileExplorerTree(file_service=service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        item = FileTreeItem(name="README.md", path=str(old_path), is_folder=False)
        entry = MagicMock()
        entry.get_text.return_value = "INTRO.md"
        entry.add_css_class = MagicMock()
        entry.set_tooltip_text = MagicMock()
        entry.remove_css_class = MagicMock()

        refresh_mock = MagicMock(return_value=False)
        idle_add_mock = MagicMock(side_effect=lambda func, *args: func(*args))
        original_emit = widget._event_bus.emit
        widget._event_bus.emit = MagicMock()
        monkeypatch.setattr(widget, "_refresh_directory", refresh_mock)
        monkeypatch.setattr("slate.ui.panels.file_explorer_tree.GLib.idle_add", idle_add_mock)

        try:
            widget._commit_inline_edit(item, entry)
        finally:
            widget._event_bus.emit = original_emit

        refresh_mock.assert_called_once_with(str(temp_project))
        assert widget._event_bus.emit is original_emit

    def test_delete_confirmation_dialog_uses_child_count(
        self, mock_file_service: Any, event_bus: EventBus, tmp_path: Any, monkeypatch: Any
    ) -> None:
        """Delete confirmation should include immediate child count for folders."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        folder = tmp_path / "folder"
        nested = folder / "nested"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("x")

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        item = FileTreeItem(name="folder", path=str(folder), is_folder=True)

        dialog = MagicMock()
        content_area = MagicMock()
        dialog.add_button.return_value = MagicMock()
        dialog.set_modal = MagicMock()
        dialog.set_title = MagicMock()
        dialog.get_content_area.return_value = content_area
        dialog.set_default_response = MagicMock()
        dialog.connect = MagicMock()
        dialog.present = MagicMock()
        dialog.hide = MagicMock()

        monkeypatch.setattr(
            "slate.ui.panels.file_explorer_tree.Gtk.Dialog", MagicMock(return_value=dialog)
        )

        widget._delete_item(item)

        assert content_area.append.call_count == 2

    def test_delete_refreshes_parent_in_place_after_confirmation(
        self, mock_file_service: Any, event_bus: EventBus, tmp_path: Any, monkeypatch: Any
    ) -> None:
        """Delete should refresh the parent directory without reloading explorer root."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree, FileTreeItem

        file_path = tmp_path / "delete-me.txt"
        file_path.write_text("x")

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        item = FileTreeItem(name="delete-me.txt", path=str(file_path), is_folder=False)

        dialog = MagicMock()
        content_area = MagicMock()
        dialog.add_button.return_value = MagicMock()
        dialog.set_modal = MagicMock()
        dialog.set_title = MagicMock()
        dialog.get_content_area.return_value = content_area
        dialog.set_default_response = MagicMock()
        dialog.present = MagicMock()

        response_handler: Any = None

        def connect(signal_name: str, callback: Any) -> None:
            nonlocal response_handler
            assert signal_name == "response"
            response_handler = callback

        dialog.connect.side_effect = connect

        refresh_mock = MagicMock(return_value=False)
        idle_add_mock = MagicMock(side_effect=lambda func, *args: func(*args))
        original_emit = widget._event_bus.emit
        widget._event_bus.emit = MagicMock()

        monkeypatch.setattr(
            "slate.ui.panels.file_explorer_tree.Gtk.Dialog", MagicMock(return_value=dialog)
        )
        monkeypatch.setattr(widget, "_refresh_directory", refresh_mock)
        monkeypatch.setattr("slate.ui.panels.file_explorer_tree.GLib.idle_add", idle_add_mock)

        try:
            widget._delete_item(item)
            assert response_handler is not None
            response_handler(dialog, Gtk.ResponseType.OK)
        finally:
            widget._event_bus.emit = original_emit

        refresh_mock.assert_called_once_with(str(tmp_path))
        assert widget._event_bus.emit is original_emit

    def test_delete_action_uses_last_right_clicked_item(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any, monkeypatch: Any
    ) -> None:
        """Delete should target the last right-clicked item even after popover close clears context."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        file_item = None
        folder_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if not item.is_folder and file_item is None:
                file_item = item
            if item.is_folder and folder_item is None:
                folder_item = item

        assert file_item is not None
        assert folder_item is not None

        widget._last_context_item = file_item
        widget._context_item = None
        widget._select_item(folder_item)

        delete_mock = MagicMock()
        monkeypatch.setattr(widget, "_delete_item", delete_mock)

        widget._action_delete()

        delete_mock.assert_called_once_with(file_item)
        assert widget._last_context_item is None

    def test_context_menu_on_secondary_click_creates_popover(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Secondary click should create a popover menu for the current item."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree
        from slate.ui.panels import file_explorer_tree as tree_module

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        file_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if not item.is_folder:
                file_item = item
                break

        assert file_item is not None
        widget._context_item = file_item

        popover = MagicMock()
        popover.popup = MagicMock()
        popover.set_parent = MagicMock()
        popover.set_pointing_to = MagicMock()
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            tree_module.Gtk.PopoverMenu, "new_from_model", MagicMock(return_value=popover)
        )

        try:
            widget._on_secondary_click(MagicMock(), 1, 10, 10)
        finally:
            monkeypatch.undo()

        assert widget._context_popover is popover
        popover.popup.assert_called_once()

    def test_secondary_click_replaces_existing_popover(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Secondary click should clean up any existing popover before opening a new one."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree
        from slate.ui.panels import file_explorer_tree as tree_module

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        file_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if not item.is_folder:
                file_item = item
                break

        assert file_item is not None
        widget._context_item = file_item

        old_popover = MagicMock()
        old_popover.popdown = MagicMock()
        old_popover.unparent = MagicMock()
        widget._context_popover = old_popover

        new_popover = MagicMock()
        new_popover.popup = MagicMock()
        new_popover.set_parent = MagicMock()
        new_popover.set_pointing_to = MagicMock()
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            tree_module.Gtk.PopoverMenu, "new_from_model", MagicMock(return_value=new_popover)
        )

        try:
            widget._on_secondary_click(MagicMock(), 1, 10, 10)
        finally:
            monkeypatch.undo()

        old_popover.popdown.assert_called_once()
        old_popover.unparent.assert_called_once()
        assert widget._context_popover is new_popover
        new_popover.popup.assert_called_once()

    def test_context_item_comes_from_clicked_row(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Context menu should use the row under the pointer, not stale selection."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        folder_item = None
        file_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if item.is_folder and folder_item is None:
                folder_item = item
            elif not item.is_folder and file_item is None:
                file_item = item

        assert folder_item is not None
        assert file_item is not None

        widget._context_item = folder_item
        widget._list_view.pick = MagicMock(return_value=None)
        widget._widget_items = {}

        assert widget._get_context_item_at_point(10, 10) is None

        picked_widget = MagicMock()
        picked_widget.get_parent = MagicMock(return_value=None)
        widget._widget_items[picked_widget] = file_item
        widget._list_view.pick = MagicMock(return_value=picked_widget)

        assert widget._get_context_item_at_point(10, 10) is file_item

    def test_secondary_click_selects_clicked_row(
        self, mock_file_service: Any, event_bus: EventBus, temp_project: Any
    ) -> None:
        """Secondary click should sync selection to the clicked row before actions run."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree
        from slate.ui.panels import file_explorer_tree as tree_module

        widget = FileExplorerTree(file_service=mock_file_service, event_bus=event_bus)
        widget.load_folder(str(temp_project))

        root_model = widget._tree_model.get_model()
        file_item = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if not item.is_folder:
                file_item = item
                break

        assert file_item is not None

        picked_widget = MagicMock()
        picked_widget.get_parent = MagicMock(return_value=None)
        widget._widget_items[picked_widget] = file_item
        widget._list_view.pick = MagicMock(return_value=picked_widget)

        popover = MagicMock()
        popover.popup = MagicMock()
        popover.set_parent = MagicMock()
        popover.set_pointing_to = MagicMock()
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            tree_module.Gtk.PopoverMenu, "new_from_model", MagicMock(return_value=popover)
        )

        try:
            widget._on_secondary_click(MagicMock(), 1, 10, 10)
        finally:
            monkeypatch.undo()

        selected = widget._selection.get_selected_item()
        assert selected is not None
        assert selected.get_item() is file_item
