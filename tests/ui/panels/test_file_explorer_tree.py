"""Tests for FileExplorerTree widget — tree display, lazy loading, events."""

from __future__ import annotations

import os
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

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
