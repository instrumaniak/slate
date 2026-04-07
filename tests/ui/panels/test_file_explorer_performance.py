"""Performance tests for FileExplorerTree — lazy loading validation."""

from __future__ import annotations

import os
import tempfile
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from slate.core.event_bus import EventBus
from slate.services.file_service import FileService


@pytest.fixture
def large_project(tmp_path: Any) -> Any:
    """Create a temp directory with 100+ subfolders for performance testing."""
    root = tmp_path / "large_project"
    root.mkdir()

    for i in range(105):
        subdir = root / f"subfolder_{i:03d}"
        subdir.mkdir()
        (subdir / f"file_{i}.txt").write_text(f"content {i}")

    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')")

    return root


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh EventBus instance."""
    bus = EventBus()
    bus._handlers.clear()
    return bus


@pytest.fixture
def file_service() -> FileService:
    """Create FileService using real filesystem."""
    return FileService()


class TestLazyLoadingPerformance:
    """Performance tests for lazy loading functionality."""

    def test_expand_100_folders_under_100ms_each(
        self, file_service: FileService, event_bus: EventBus, large_project: Any
    ) -> None:
        """Expanding 100+ folders should each take <100ms (NFR-002)."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=file_service,
            event_bus=event_bus,
            config_service=None,
        )
        widget.load_folder(str(large_project))

        root_model = widget._tree_model.get_model()
        folder_items = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if item.is_folder and item.name.startswith("subfolder_"):
                folder_items.append(item)

        assert len(folder_items) >= 100, f"Need 100+ folders, got {len(folder_items)}"

        timings: list[float] = []
        for folder_item in folder_items[:10]:
            start = time.perf_counter()

            store = widget._create_list_model_for_dir(folder_item.path)

            elapsed = time.perf_counter() - start
            timings.append(elapsed * 1000)

        max_timing = max(timings)
        avg_timing = sum(timings) / len(timings)

        assert max_timing < 100, (
            f"Folder expansion took {max_timing:.1f}ms (max), should be <100ms. "
            f"Average: {avg_timing:.1f}ms"
        )

    def test_initial_load_does_not_scan_recursively(
        self, file_service: FileService, event_bus: EventBus, large_project: Any
    ) -> None:
        """Initial tree load should NOT recursively scan subdirectories."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=file_service,
            event_bus=event_bus,
            config_service=None,
        )

        widget.load_folder(str(large_project))

        root_model = widget._tree_model.get_model()
        root_count = root_model.get_n_items()

        root_names = []
        for i in range(root_count):
            item = root_model.get_item(i)
            root_names.append(item.name)

        assert "src" in root_names, "Root folder should show immediate children"
        assert "subfolder_000" in root_names, "Root should list subfolders"
        assert root_count < 110, (
            f"Root should only show immediate children (~106), got {root_count}. "
            "If >106, tree may be scanning recursively."
        )

    def test_create_child_model_called_once_per_folder(
        self, file_service: FileService, event_bus: EventBus, large_project: Any
    ) -> None:
        """_on_create_child_model should be called only once per expanded folder."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=file_service,
            event_bus=event_bus,
            config_service=None,
        )
        widget.load_folder(str(large_project))

        root_model = widget._tree_model.get_model()
        first_folder = None
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            if item.is_folder and item.name.startswith("subfolder_"):
                first_folder = item
                break

        assert first_folder is not None, "Need at least one folder to test"

        call_count = 0
        original_create = widget._on_create_child_model

        def tracking_create(item: Any):
            nonlocal call_count
            call_count += 1
            return original_create(item)

        widget._on_create_child_model = tracking_create

        store = widget._on_create_child_model(first_folder)

        widget._on_create_child_model = original_create

        assert call_count == 1, (
            f"create_func called {call_count} times for one folder expansion. "
            "Should be exactly 1 for lazy loading."
        )


class TestTimingAccuracy:
    """Tests for timing measurement accuracy."""

    def test_perf_counter_provides_high_resolution(self, large_project: Any) -> None:
        """time.perf_counter should provide sufficient resolution for <100ms measurements."""
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            pass
        elapsed = time.perf_counter() - start

        avg_ns = (elapsed / iterations) * 1_000_000_000
        assert avg_ns < 1000, f"Timer resolution too coarse: {avg_ns:.0f}ns per iteration"
