"""File I/O service for Slate - handles file operations and directory monitoring.

Zero GTK imports at module level - pure Python with lazy GIO imports inside methods.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

from slate.core.event_bus import EventBus
from slate.core.events import FileSavedEvent
from slate.core.models import FileStatus

logger = logging.getLogger(__name__)


class FileService:
    """File I/O operations. Zero GTK at module level. Service ID: "file".

    Handles file reading, writing, directory listing, and directory monitoring.
    Uses GIO FileMonitor for zero-polling file watching (NFR-009).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._monitor: Any = None
        self._monitor_path: str | None = None

    def list_directory(self, path: str) -> list[FileStatus]:
        """List files and folders with metadata.

        Args:
            path: Directory path to list.

        Returns:
            List of FileStatus objects for each entry.

        Raises:
            FileNotFoundError: If path does not exist.
            NotADirectoryError: If path is not a directory.
            PermissionError: If path is not readable.
        """
        resolved = os.path.abspath(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Not a directory: {path}")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Permission denied: {path}")

        results: list[FileStatus] = []
        with self._lock:
            for entry in sorted(os.listdir(resolved)):
                entry_path = os.path.join(resolved, entry)
                try:
                    stat = os.stat(entry_path)
                    is_dir = os.path.isdir(entry_path)
                    results.append(
                        FileStatus(
                            path=entry_path,
                            is_dir=is_dir,
                            size=0 if is_dir else stat.st_size,
                            modified_time=stat.st_mtime,
                            is_dirty=False,
                        )
                    )
                except (OSError, PermissionError):
                    continue

        return results

    def read_file(self, path: str) -> str:
        """Read file contents.

        Args:
            path: File path to read.

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If file does not exist.
            PermissionError: If file is not readable.
        """
        resolved = os.path.abspath(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"File not found: {path}")
        if not os.path.isfile(resolved):
            raise IsADirectoryError(f"Path is a directory: {path}")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Permission denied: {path}")

        with open(resolved, encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        """Write content to file and emit FileSavedEvent.

        Creates parent directories if they don't exist.

        Args:
            path: File path to write.
            content: Content to write.

        Raises:
            PermissionError: If file is not writable.
            OSError: If write fails for other reasons.
        """
        resolved = os.path.abspath(path)
        parent = os.path.dirname(resolved)

        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create parent directories for {path}: {e}") from e

        with self._lock, open(resolved, "w", encoding="utf-8") as f:
            f.write(content)

        try:
            EventBus().emit(FileSavedEvent(path=resolved))
        except Exception as e:
            logger.warning(f"Failed to emit FileSavedEvent: {e}")

    def monitor_directory(self, path: str) -> Any:
        """Start GIO FileMonitor on a directory (inotify, zero polling).

        Uses lazy import of gi.repository.Gio inside method.

        Args:
            path: Directory path to monitor.

        Returns:
            The Gio.FileMonitor instance.

        Raises:
            FileNotFoundError: If path does not exist.
            NotADirectoryError: If path is not a directory.
            ImportError: If GIO is not available.
        """
        resolved = os.path.abspath(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Not a directory: {path}")

        with self._lock:
            if self._monitor is not None:
                self.stop_monitor()

            import gi

            gi.require_version("Gio", "2.0")
            from gi.repository import Gio  # type: ignore[import-untyped]

            gfile = Gio.File.new_for_path(resolved)
            monitor = gfile.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
            self._monitor = monitor
            self._monitor_path = resolved
            return monitor

    def stop_monitor(self) -> None:
        """Stop active file monitor if any."""
        with self._lock:
            if self._monitor is not None:
                try:
                    self._monitor.cancel()
                except Exception as e:
                    logger.warning(f"Failed to cancel file monitor: {e}")
                self._monitor = None
                self._monitor_path = None
