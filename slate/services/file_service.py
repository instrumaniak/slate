"""File I/O service for Slate - handles file operations and directory monitoring.

Zero GTK imports at module level - pure Python with lazy GIO imports inside methods.
"""

from __future__ import annotations

import logging
import os
import threading
import shutil
from typing import Any

from slate.core.event_bus import EventBus
from slate.core.events import FileSavedEvent
from slate.core.models import FileStatus

logger = logging.getLogger(__name__)


def _validate_path(path: str) -> str:
    """Validate path parameter and return absolute path.

    Args:
        path: Path to validate.

    Returns:
        Absolute path string.

    Raises:
        TypeError: If path is None.
        ValueError: If path contains null bytes.
    """
    if path is None:
        raise TypeError("path cannot be None")
    if "\x00" in path:
        raise ValueError("path cannot contain null bytes")
    return os.path.abspath(path)


class FileService:
    """File I/O operations. Zero GTK at module level. Service ID: "file".

    Handles file reading, writing, directory listing, and directory monitoring.
    Uses GIO FileMonitor for zero-polling file watching (NFR-009).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._monitor: Any = None
        self._monitor_path: str | None = None

    def _validate_child_name(self, name: str) -> str:
        """Validate a direct child name for create and rename operations."""
        if name is None:
            raise TypeError("name cannot be None")

        candidate = name.strip()
        if not candidate:
            raise ValueError("name cannot be empty")
        if "/" in candidate or "\x00" in candidate:
            raise ValueError("name cannot contain / or null bytes")

        return candidate

    def list_directory(self, path: str) -> list[FileStatus]:
        """List files and folders with metadata.

        Args:
            path: Directory path to list.

        Returns:
            List of FileStatus objects for each entry.

        Raises:
            TypeError: If path is None.
            ValueError: If path contains null bytes.
            FileNotFoundError: If path does not exist.
            NotADirectoryError: If path is not a directory.
            PermissionError: If path is not readable.
        """
        resolved = _validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Not a directory: {path}")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Permission denied: {path}")

        results: list[FileStatus] = []
        errors: list[tuple[str, Exception]] = []

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
                except (OSError, PermissionError) as e:
                    errors.append((entry, e))

        if errors:
            for entry, error in errors:
                logger.warning(f"Failed to stat entry '{entry}': {error}")

        return results

    def read_file(self, path: str) -> str:
        """Read file contents.

        Args:
            path: File path to read.

        Returns:
            File contents as string.

        Raises:
            TypeError: If path is None.
            ValueError: If path contains null bytes.
            FileNotFoundError: If file does not exist.
            IsADirectoryError: If path is a directory.
            PermissionError: If file is not readable.
            ValueError: If file is not valid UTF-8.
        """
        resolved = _validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"File not found: {path}")
        if not os.path.isfile(resolved):
            raise IsADirectoryError(f"Path is a directory: {path}")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Permission denied: {path}")

        try:
            with open(resolved, encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError as e:
            raise ValueError(f"File is not valid UTF-8: {path}") from e

    def write_file(self, path: str, content: str) -> None:
        """Write content to file and emit FileSavedEvent.

        Creates parent directories if they don't exist.

        Args:
            path: File path to write.
            content: Content to write.

        Raises:
            TypeError: If path or content is None.
            ValueError: If path contains null bytes or is a directory.
            PermissionError: If file is not writable.
            OSError: If write fails for other reasons.
        """
        if content is None:
            raise TypeError("content cannot be None")
        if not isinstance(content, str):
            raise TypeError(f"content must be str, got {type(content).__name__}")

        resolved = _validate_path(path)

        # Check if target is an existing directory
        if os.path.isdir(resolved):
            raise IsADirectoryError(f"Cannot write to directory: {path}")

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

    def create_file(self, parent_path: str, name: str) -> str:
        """Create an empty file inside a directory and return the full path."""
        candidate = self._validate_child_name(name)

        parent = _validate_path(parent_path)
        if not os.path.isdir(parent):
            raise NotADirectoryError(f"Not a directory: {parent_path}")

        target = os.path.abspath(os.path.join(parent, candidate))
        if os.path.exists(target):
            raise FileExistsError(f"File already exists: {target}")

        with self._lock:
            with open(target, "w", encoding="utf-8"):
                pass

        return target

    def create_folder(self, parent_path: str, name: str) -> str:
        """Create a folder inside a directory and return the full path."""
        candidate = self._validate_child_name(name)

        parent = _validate_path(parent_path)
        if not os.path.isdir(parent):
            raise NotADirectoryError(f"Not a directory: {parent_path}")

        target = os.path.abspath(os.path.join(parent, candidate))
        if os.path.exists(target):
            raise FileExistsError(f"Folder already exists: {target}")

        with self._lock:
            os.makedirs(target, exist_ok=False)

        return target

    def delete_file(self, path: str) -> None:
        """Delete a file from disk."""
        resolved = _validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"File not found: {path}")
        if not os.path.isfile(resolved):
            raise IsADirectoryError(f"Path is a directory: {path}")

        with self._lock:
            os.remove(resolved)

    def delete_folder(self, path: str) -> None:
        """Delete a folder recursively from disk."""
        resolved = _validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Folder not found: {path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Not a directory: {path}")

        with self._lock:
            shutil.rmtree(resolved)

    def rename(self, old_path: str, new_name: str) -> str:
        """Rename a file or folder within the same parent directory."""
        candidate = self._validate_child_name(new_name)

        resolved_old = _validate_path(old_path)
        if not os.path.exists(resolved_old):
            raise FileNotFoundError(f"Path not found: {old_path}")

        parent = os.path.dirname(resolved_old)
        target = os.path.abspath(os.path.join(parent, candidate))
        if target == resolved_old:
            return target
        if os.path.exists(target):
            raise FileExistsError(f"Target already exists: {target}")

        with self._lock:
            os.rename(resolved_old, target)

        return target

    def count_immediate_children(self, path: str) -> int:
        """Count immediate children of a directory."""
        resolved = _validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Not a directory: {path}")

        with self._lock:
            return sum(1 for _ in os.scandir(resolved))

    def monitor_directory(self, path: str) -> Any:
        """Start GIO FileMonitor on a directory (inotify, zero polling).

        Uses lazy import of gi.repository.Gio inside method.

        Args:
            path: Directory path to monitor.

        Returns:
            The Gio.FileMonitor instance.

        Raises:
            TypeError: If path is None.
            ValueError: If path contains null bytes.
            FileNotFoundError: If path does not exist.
            NotADirectoryError: If path is not a directory.
            ImportError: If GIO is not available.
            RuntimeError: If monitor creation fails.
        """
        resolved = _validate_path(path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Directory not found: {path}")
        if not os.path.isdir(resolved):
            raise NotADirectoryError(f"Not a directory: {path}")

        with self._lock:
            if self._monitor is not None:
                self.stop_monitor()

            try:
                import gi

                gi.require_version("Gio", "2.0")
                from gi.repository import Gio  # type: ignore[import-untyped]
            except ImportError as e:
                raise ImportError(
                    "GIO not available. Install GTK/GIO development libraries."
                ) from e

            try:
                gfile = Gio.File.new_for_path(resolved)
                monitor = gfile.monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
                self._monitor = monitor
                self._monitor_path = resolved
                return monitor
            except Exception as e:
                raise RuntimeError(f"Failed to create file monitor for {path}: {e}") from e

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
