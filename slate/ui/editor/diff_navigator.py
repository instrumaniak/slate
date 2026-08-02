"""DiffNavigator sidebar widget for Slate.

Displays file list and hunk list for easy navigation within diffs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

if TYPE_CHECKING:
    from slate.services.diff_parser import FileDiff

logger = logging.getLogger(__name__)


class DiffNavigator(Gtk.Box):
    """Sidebar widget showing file list and hunk list for diff navigation."""

    def __init__(
        self,
        diffs: list[FileDiff] | None = None,
        on_hunk_selected: Callable[[int, int], None] | None = None,
    ) -> None:
        """Initialize DiffNavigator.

        Args:
            diffs: List of FileDiff objects.
            on_hunk_selected: Callback(file_index, hunk_index) when user selects a hunk.
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._diffs = diffs or []
        self._on_hunk_selected = on_hunk_selected

        self._list_store = Gtk.StringList()
        self._list_view = Gtk.ListView()
        self._item_indices: list[tuple[int, int] | None] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up navigator UI list."""
        label = Gtk.Label(label="Diff Navigation")
        label.set_xalign(0)
        label.set_margin_start(6)
        label.set_margin_top(6)
        self.append(label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        self._update_items()
        scrolled.set_child(self._list_view)
        self.append(scrolled)

    def set_diffs(self, diffs: list[FileDiff]) -> None:
        """Set new diff data and update list.

        Args:
            diffs: List of FileDiff objects.
        """
        self._diffs = diffs
        self._update_items()

    def _update_items(self) -> None:
        """Populate list view items."""
        items: list[str] = []
        item_indices: list[tuple[int, int] | None] = []
        for file_idx, f_diff in enumerate(self._diffs):
            path_display = f_diff.new_path or f_diff.old_path or "Unknown"
            items.append(f"[{f_diff.status}] {path_display}")
            item_indices.append(None)
            for hunk_idx, hunk in enumerate(f_diff.hunks):
                items.append(f"   @@ -{hunk.old_start} +{hunk.new_start} @@")
                item_indices.append((file_idx, hunk_idx))

        self._list_store = Gtk.StringList.new(items)
        selection = Gtk.SingleSelection.new(self._list_store)
        self._item_indices = item_indices
        selection.connect("selection-changed", self._on_selection_changed)
        self._list_view.set_model(selection)

    def _on_selection_changed(
        self, selection: Gtk.SingleSelection, _position: int, _n_items: int
    ) -> None:
        position = selection.get_selected()
        if position < 0 or position >= len(self._item_indices):
            return
        item = self._item_indices[position]
        if item is not None and self._on_hunk_selected:
            self._on_hunk_selected(*item)

    def select_hunk(self, file_index: int, hunk_index: int) -> None:
        """Select a hunk programmatically and invoke the callback."""
        if not (0 <= file_index < len(self._diffs)):
            return
        if not (0 <= hunk_index < len(self._diffs[file_index].hunks)):
            return
        if self._on_hunk_selected:
            self._on_hunk_selected(file_index, hunk_index)
