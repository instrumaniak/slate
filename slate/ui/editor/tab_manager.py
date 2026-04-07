from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING

from slate.core.event_bus import EventBus
from slate.core.events import (
    FileOpenedEvent,
    OpenFileRequestedEvent,
    TabActivatedEvent,
    TabClosedEvent,
)

if TYPE_CHECKING:
    from slate.services.file_service import FileService

logger = logging.getLogger(__name__)


class TabManager:
    """Manages open tabs and emits FileOpenedEvent.

    TabManager is the ONLY component that creates editor tabs and emits FileOpenedEvent.
    Follows event ownership rules from project-context.md.

    Service ID for FileService: "file"
    """

    def __init__(self, file_service: FileService) -> None:
        """Initialize TabManager.

        Args:
            file_service: FileService instance for reading files.
        """
        self._file_service = file_service
        self._tabs: dict[str, dict] = {}
        self._active_tab: str | None = None
        self._tab_order: list[str] = []
        self._close_dialog_callback: Callable | None = None

        self._event_bus = EventBus()
        self._event_bus.subscribe(OpenFileRequestedEvent, self._on_open_file_requested)

    def set_close_dialog_callback(self, callback: Callable[[str, str], str]) -> None:
        """Set callback for showing save/discard dialog.

        Args:
            callback: Function that takes (filename, path) and returns "save"|"discard"|"cancel"
        """
        self._close_dialog_callback = callback

    def _on_open_file_requested(self, event: OpenFileRequestedEvent) -> None:
        """Handle OpenFileRequestedEvent - create new tab."""
        self.open_tab(event.path)

    def open_tab(self, path: str) -> dict:
        """Open a file in a new tab.

        Args:
            path: Path to the file to open.

        Returns:
            Tab state dictionary.
        """
        if not path or not isinstance(path, str):
            logger.error(f"Invalid path provided: {path}")
            return {
                "path": path,
                "content": "Error: Invalid file path",
                "is_dirty": False,
                "is_error": True,
            }

        if path in self._tabs:
            self._active_tab = path
            return self._tabs[path]

        try:
            content = self._file_service.read_file(path)
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            content = f"Error: failed to load file\n{e}"

        tab = {
            "path": path,
            "content": content,
            "is_dirty": False,
            "is_error": content.startswith("Error:"),
        }
        self._tabs[path] = tab
        self._active_tab = path
        self._tab_order.append(path)

        self._event_bus.emit(FileOpenedEvent(path=path, content=content))

        return tab

    def close_tab(self, path: str) -> bool:
        """Close a tab.

        Args:
            path: Path of the tab to close.

        Returns:
            True if tab was closed, False if cancelled or not found.
        """
        if path not in self._tabs:
            return False

        tab = self._tabs[path]
        if tab.get("is_dirty", False) and self._close_dialog_callback:
            filename = os.path.basename(path)
            result = self._close_dialog_callback(filename, path)
            if result == "cancel":
                return False
            if result == "save":
                try:
                    content = tab.get("content", "")
                    self._file_service.write_file(path, content)
                    self.mark_clean(path)
                except Exception as e:
                    logger.error(f"Failed to save file {path}: {e}")
                    return False

        del self._tabs[path]
        if path in self._tab_order:
            self._tab_order.remove(path)

        if self._active_tab == path:
            self._active_tab = next(iter(self._tabs), None)

        self._event_bus.emit(TabClosedEvent(path=path))
        return True

    def get_tabs(self) -> dict[str, dict]:
        """Get all open tabs.

        Returns:
            Dictionary mapping paths to tab states.
        """
        return self._tabs.copy()

    def get_active_tab(self) -> str | None:
        """Get the currently active tab path.

        Returns:
            Path of active tab or None if no tabs open.
        """
        return self._active_tab

    def set_active_tab(self, path: str) -> None:
        """Set the active tab.

        Args:
            path: Path of tab to make active.
        """
        if path in self._tabs:
            self._active_tab = path

    def mark_dirty(self, path: str) -> None:
        """Mark a tab as having unsaved changes.

        Args:
            path: Path of the tab to mark dirty.
        """
        if path in self._tabs:
            self._tabs[path]["is_dirty"] = True

    def mark_clean(self, path: str) -> None:
        """Mark a tab as having no unsaved changes.

        Args:
            path: Path of the tab to mark clean.
        """
        if path in self._tabs:
            self._tabs[path]["is_dirty"] = False

    def set_tab_content(self, path: str, content: str) -> None:
        """Update stored content for an open tab."""
        if path in self._tabs:
            self._tabs[path]["content"] = content

    def save_tab(self, path: str, content: str) -> None:
        """Persist tab content and mark the tab clean."""
        if path not in self._tabs:
            raise KeyError(f"Tab not found: {path}")

        self._file_service.write_file(path, content)
        self._tabs[path]["content"] = content
        self.mark_clean(path)

    def get_tab_list(self) -> list[str]:
        """Get list of all open tab paths in order.

        Returns:
            List of file paths for open tabs.
        """
        return self._tab_order.copy() if self._tab_order else list(self._tabs.keys())

    def cycle_next(self) -> str | None:
        """Cycle to the next tab.

        Returns:
            Path of the newly active tab, or None if no tabs.
        """
        if not self._tab_order:
            return None

        current_index = (
            self._tab_order.index(self._active_tab) if self._active_tab in self._tab_order else -1
        )
        next_index = (current_index + 1) % len(self._tab_order)
        next_path = self._tab_order[next_index]
        self._active_tab = next_path
        self._event_bus.emit(TabActivatedEvent(path=next_path))
        return next_path

    def cycle_previous(self) -> str | None:
        """Cycle to the previous tab.

        Returns:
            Path of the newly active tab, or None if no tabs.
        """
        if not self._tab_order:
            return None

        current_index = (
            self._tab_order.index(self._active_tab) if self._active_tab in self._tab_order else -1
        )
        prev_index = (current_index - 1) % len(self._tab_order)
        prev_path = self._tab_order[prev_index]
        self._active_tab = prev_path
        self._event_bus.emit(TabActivatedEvent(path=prev_path))
        return prev_path

    def reorder_tabs(self, new_order: list[str]) -> None:
        """Reorder tabs.

        Args:
            new_order: New order of tab paths.
        """
        if len(new_order) != len(self._tabs) or set(new_order) != set(self._tabs.keys()):
            logger.warning("Reorder request doesn't match existing tabs")
            return

        self._tab_order = new_order
