from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from slate.core.event_bus import EventBus
from slate.core.events import FileOpenedEvent, OpenFileRequestedEvent, TabClosedEvent

if TYPE_CHECKING:
    from slate.services.file_service import FileService

logger = logging.getLogger(__name__)


class TabManager:
    """Manages open tabs and emits FileOpenedEvent.

    TabManager is the ONLY component that creates editor tabs and emits FileOpenedEvent.
    Follows event ownership rules from project-context.md.

    Service ID for FileService: "file"
    """

    def __init__(self, file_service: "FileService") -> None:
        """Initialize TabManager.

        Args:
            file_service: FileService instance for reading files.
        """
        self._file_service = file_service
        self._tabs: dict[str, dict] = {}
        self._active_tab: str | None = None

        self._event_bus = EventBus()
        self._event_bus.subscribe(OpenFileRequestedEvent, self._on_open_file_requested)

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
            content = None

        tab = {
            "path": path,
            "content": content,
            "is_dirty": False,
            "is_error": content is None,
        }
        self._tabs[path] = tab
        self._active_tab = path

        self._event_bus.emit(FileOpenedEvent(path=path, content=content))

        return tab

    def close_tab(self, path: str) -> None:
        """Close a tab.

        Args:
            path: Path of the tab to close.
        """
        if path not in self._tabs:
            return

        del self._tabs[path]

        if self._active_tab == path:
            self._active_tab = next(iter(self._tabs), None)

        self._event_bus.emit(TabClosedEvent(path=path))

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

    def get_tab_list(self) -> list[str]:
        """Get list of all open tab paths in order.

        Returns:
            List of file paths for open tabs.
        """
        return list(self._tabs.keys())
