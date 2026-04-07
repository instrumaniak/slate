"""Tests for FileService - file I/O operations and directory monitoring."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from slate.core.event_bus import EventBus
from slate.core.events import FileSavedEvent
from slate.core.models import FileStatus
from slate.services.file_service import FileService


class TestFileServiceListDirectory:
    """Test FileService.list_directory()."""

    def test_list_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory should return empty list."""
        service = FileService()
        result = service.list_directory(str(tmp_path))
        assert result == []

    def test_list_directory_with_files(self, tmp_path: Path) -> None:
        """Directory with files should return FileStatus list."""
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "file2.py").write_text("world")

        service = FileService()
        result = service.list_directory(str(tmp_path))

        assert len(result) == 2
        names = [os.path.basename(r.path) for r in result]
        assert "file1.txt" in names
        assert "file2.py" in names

    def test_list_directory_with_subdirs(self, tmp_path: Path) -> None:
        """Directory with subdirectories should mark them as is_dir."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("content")

        service = FileService()
        result = service.list_directory(str(tmp_path))

        dirs = [r for r in result if r.is_dir]
        files = [r for r in result if not r.is_dir]
        assert len(dirs) == 1
        assert len(files) == 1
        assert os.path.basename(dirs[0].path) == "subdir"
        assert os.path.basename(files[0].path) == "file.txt"

    def test_list_directory_returns_file_status(self, tmp_path: Path) -> None:
        """Each entry should be a FileStatus with correct fields."""
        (tmp_path / "test.txt").write_text("hello world")

        service = FileService()
        result = service.list_directory(str(tmp_path))

        assert len(result) == 1
        entry = result[0]
        assert isinstance(entry, FileStatus)
        assert entry.is_dir is False
        assert entry.size == 11
        assert entry.modified_time > 0
        assert entry.is_dirty is False

    def test_list_directory_sorted(self, tmp_path: Path) -> None:
        """Entries should be sorted alphabetically."""
        (tmp_path / "zebra.txt").write_text("")
        (tmp_path / "apple.txt").write_text("")
        (tmp_path / "banana.txt").write_text("")

        service = FileService()
        result = service.list_directory(str(tmp_path))

        names = [os.path.basename(r.path) for r in result]
        assert names == sorted(names)

    def test_list_directory_nonexistent_raises(self) -> None:
        """Non-existent directory should raise FileNotFoundError."""
        service = FileService()
        with pytest.raises(FileNotFoundError):
            service.list_directory("/nonexistent/path")

    def test_list_directory_file_path_raises(self, tmp_path: Path) -> None:
        """File path should raise NotADirectoryError."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        service = FileService()
        with pytest.raises(NotADirectoryError):
            service.list_directory(str(file_path))

    def test_list_directory_permission_denied(self, tmp_path: Path) -> None:
        """Unreadable directory should raise PermissionError."""
        dir_path = tmp_path / "noaccess"
        dir_path.mkdir()
        dir_path.chmod(0o000)

        try:
            service = FileService()
            with pytest.raises(PermissionError):
                service.list_directory(str(dir_path))
        finally:
            dir_path.chmod(0o755)


class TestFileServiceReadFile:
    """Test FileService.read_file()."""

    def test_read_existing_file(self, tmp_path: Path) -> None:
        """Should return file contents."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world")

        service = FileService()
        content = service.read_file(str(file_path))

        assert content == "hello world"

    def test_read_utf8_file(self, tmp_path: Path) -> None:
        """Should handle UTF-8 content."""
        file_path = tmp_path / "unicode.txt"
        file_path.write_text("Hello \u4e16\u754c", encoding="utf-8")

        service = FileService()
        content = service.read_file(str(file_path))

        assert content == "Hello \u4e16\u754c"

    def test_read_nonexistent_raises(self) -> None:
        """Non-existent file should raise FileNotFoundError."""
        service = FileService()
        with pytest.raises(FileNotFoundError):
            service.read_file("/nonexistent/file.txt")

    def test_read_directory_raises(self, tmp_path: Path) -> None:
        """Directory path should raise IsADirectoryError."""
        service = FileService()
        with pytest.raises(IsADirectoryError):
            service.read_file(str(tmp_path))

    def test_read_empty_file(self, tmp_path: Path) -> None:
        """Empty file should return empty string."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("")

        service = FileService()
        assert service.read_file(str(file_path)) == ""

    def test_read_permission_denied(self, tmp_path: Path) -> None:
        """Permission denied should raise PermissionError."""
        file_path = tmp_path / "secret.txt"
        file_path.write_text("secret")
        file_path.chmod(0o000)

        try:
            service = FileService()
            with pytest.raises(PermissionError):
                service.read_file(str(file_path))
        finally:
            file_path.chmod(0o644)


class TestFileServiceWriteFile:
    """Test FileService.write_file()."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """Should create file with given content."""
        file_path = tmp_path / "new.txt"
        service = FileService()
        service.write_file(str(file_path), "hello")

        assert file_path.read_text() == "hello"

    def test_write_overwrites_existing(self, tmp_path: Path) -> None:
        """Should overwrite existing file."""
        file_path = tmp_path / "existing.txt"
        file_path.write_text("old")

        service = FileService()
        service.write_file(str(file_path), "new")

        assert file_path.read_text() == "new"

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        file_path = tmp_path / "a" / "b" / "c" / "file.txt"

        service = FileService()
        service.write_file(str(file_path), "deep")

        assert file_path.read_text() == "deep"
        assert file_path.parent.exists()

    def test_write_emits_file_saved_event(self, tmp_path: Path) -> None:
        """Should emit FileSavedEvent after write."""
        file_path = tmp_path / "event_test.txt"
        service = FileService()

        events: list[FileSavedEvent] = []

        def handler(event: FileSavedEvent) -> None:
            events.append(event)

        bus = EventBus()
        bus.subscribe(FileSavedEvent, handler)

        try:
            service.write_file(str(file_path), "content")

            assert len(events) == 1
            assert events[0].path == str(file_path.resolve())
        finally:
            bus.unsubscribe(FileSavedEvent, handler)

    def test_write_utf8_content(self, tmp_path: Path) -> None:
        """Should write UTF-8 content correctly."""
        file_path = tmp_path / "unicode.txt"

        service = FileService()
        service.write_file(str(file_path), "Hello \u4e16\u754c")

        assert file_path.read_text(encoding="utf-8") == "Hello \u4e16\u754c"

    def test_write_permission_denied(self, tmp_path: Path) -> None:
        """Writing to read-only directory should raise error."""
        dir_path = tmp_path / "readonly"
        dir_path.mkdir()
        dir_path.chmod(0o555)

        try:
            service = FileService()
            with pytest.raises((PermissionError, OSError)):
                service.write_file(str(dir_path / "file.txt"), "content")
        finally:
            dir_path.chmod(0o755)


class TestFileServiceMonitor:
    """Test FileService monitor_directory and stop_monitor."""

    def test_stop_monitor_without_start(self) -> None:
        """stop_monitor should be safe to call without starting a monitor."""
        service = FileService()
        service.stop_monitor()  # Should not raise

    def test_monitor_nonexistent_raises(self) -> None:
        """monitor_directory on non-existent path should raise FileNotFoundError."""
        service = FileService()
        with pytest.raises(FileNotFoundError):
            service.monitor_directory("/nonexistent/path")

    def test_monitor_file_path_raises(self, tmp_path: Path) -> None:
        """monitor_directory on a file should raise NotADirectoryError."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")

        service = FileService()
        with pytest.raises(NotADirectoryError):
            service.monitor_directory(str(file_path))

    def test_monitor_gio_unavailable(self, tmp_path: Path) -> None:
        """monitor_directory should raise ImportError when GIO is not available."""
        from unittest.mock import patch

        service = FileService()

        with patch.dict("sys.modules", {"gi": None, "gi.repository": None}):
            with pytest.raises(ImportError):
                service.monitor_directory(str(tmp_path))

    def test_monitor_replaces_existing(self, tmp_path: Path) -> None:
        """Starting a new monitor should cancel the previous one."""
        try:
            import gi

            gi.require_version("Gio", "2.0")
            from gi.repository import Gio  # noqa: F401
        except (ImportError, ValueError):
            pytest.skip("GIO not available")

        service = FileService()
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        dir2 = tmp_path / "dir2"
        dir2.mkdir()

        monitor1 = service.monitor_directory(str(dir1))
        monitor2 = service.monitor_directory(str(dir2))

        assert monitor2 is not None
        assert service._monitor is monitor2
        service.stop_monitor()

    def test_stop_monitor_cancels_active(self, tmp_path: Path) -> None:
        """stop_monitor should cancel an active monitor."""
        try:
            import gi

            gi.require_version("Gio", "2.0")
            from gi.repository import Gio  # noqa: F401
        except (ImportError, ValueError):
            pytest.skip("GIO not available")

        service = FileService()
        monitor = service.monitor_directory(str(tmp_path))
        assert service._monitor is not None

        service.stop_monitor()
        assert service._monitor is None
        assert service._monitor_path is None

    def test_monitor_success(self, tmp_path: Path) -> None:
        """monitor_directory should return a FileMonitor on success."""
        try:
            import gi

            gi.require_version("Gio", "2.0")
            from gi.repository import Gio  # noqa: F401
        except (ImportError, ValueError):
            pytest.skip("GIO not available")

        service = FileService()
        monitor = service.monitor_directory(str(tmp_path))

        assert monitor is not None
        assert service._monitor is monitor
        assert service._monitor_path == str(tmp_path.resolve())
        service.stop_monitor()


class TestFileServiceZeroGtk:
    """Test zero GTK imports at module level."""

    def test_no_gtk_imports_at_module_level(self) -> None:
        """FileService module should have zero GTK imports at module level."""
        import ast
        import inspect

        import slate.services.file_service as file_module

        # Parse AST to find GTK imports only at module level (not inside functions)
        source = inspect.getsource(file_module)
        tree = ast.parse(source)

        module_level_gtk_imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "gi" or alias.name.startswith("gi."):
                        module_level_gtk_imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "gi" or node.module.startswith("gi.")):
                    module_level_gtk_imports.append(f"from {node.module}")

        assert len(module_level_gtk_imports) == 0, (
            f"Found GTK imports at module level: {module_level_gtk_imports}"
        )


class TestFileServiceThreadSafety:
    """Test FileService thread safety."""

    def test_concurrent_writes(self, tmp_path: Path) -> None:
        """Concurrent writes should not corrupt files."""
        import threading

        service = FileService()
        errors: list[Exception] = []

        def writer(n: int) -> None:
            try:
                for i in range(10):
                    file_path = tmp_path / f"thread_{n}_{i}.txt"
                    service.write_file(str(file_path), f"content {n} {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent writes: {errors}"
        files = list(tmp_path.glob("thread_*_*.txt"))
        assert len(files) == 50


class TestFileServiceOperations:
    """Test create/delete/rename helpers."""

    def test_create_file_returns_path(self, tmp_path: Path) -> None:
        """create_file should create an empty file and return the full path."""
        service = FileService()
        created = service.create_file(str(tmp_path), "new.txt")

        assert created == str((tmp_path / "new.txt").resolve())
        assert (tmp_path / "new.txt").read_text() == ""

    def test_create_folder_returns_path(self, tmp_path: Path) -> None:
        """create_folder should create a folder and return the full path."""
        service = FileService()
        created = service.create_folder(str(tmp_path), "docs")

        assert created == str((tmp_path / "docs").resolve())
        assert (tmp_path / "docs").is_dir()

    def test_create_file_duplicate_raises(self, tmp_path: Path) -> None:
        """create_file should reject duplicate names."""
        (tmp_path / "dup.txt").write_text("content")
        service = FileService()

        with pytest.raises(FileExistsError):
            service.create_file(str(tmp_path), "dup.txt")

    def test_create_file_rejects_invalid_name(self, tmp_path: Path) -> None:
        """create_file should reject empty and path-like names."""
        service = FileService()

        with pytest.raises(ValueError):
            service.create_file(str(tmp_path), "")

        with pytest.raises(ValueError):
            service.create_file(str(tmp_path), "bad/name")

    def test_create_folder_duplicate_raises(self, tmp_path: Path) -> None:
        """create_folder should reject duplicate names."""
        (tmp_path / "docs").mkdir()
        service = FileService()

        with pytest.raises(FileExistsError):
            service.create_folder(str(tmp_path), "docs")

    def test_delete_file(self, tmp_path: Path) -> None:
        """delete_file should remove a file."""
        file_path = tmp_path / "remove.txt"
        file_path.write_text("content")

        service = FileService()
        service.delete_file(str(file_path))

        assert not file_path.exists()

    def test_delete_folder_recursive(self, tmp_path: Path) -> None:
        """delete_folder should remove nested content recursively."""
        folder = tmp_path / "folder"
        nested = folder / "nested"
        nested.mkdir(parents=True)
        (nested / "file.txt").write_text("content")

        service = FileService()
        service.delete_folder(str(folder))

        assert not folder.exists()

    def test_rename_file(self, tmp_path: Path) -> None:
        """rename should move a file within the same directory."""
        old_path = tmp_path / "old.txt"
        old_path.write_text("content")

        service = FileService()
        new_path = service.rename(str(old_path), "new.txt")

        assert new_path == str((tmp_path / "new.txt").resolve())
        assert not old_path.exists()
        assert (tmp_path / "new.txt").read_text() == "content"

    def test_rename_rejects_invalid_name(self, tmp_path: Path) -> None:
        """rename should reject invalid new names."""
        old_path = tmp_path / "old.txt"
        old_path.write_text("content")

        service = FileService()

        with pytest.raises(ValueError):
            service.rename(str(old_path), "bad/name")

    def test_rename_folder(self, tmp_path: Path) -> None:
        """rename should move a folder within the same parent."""
        old_folder = tmp_path / "old-folder"
        old_folder.mkdir()

        service = FileService()
        new_path = service.rename(str(old_folder), "new-folder")

        assert new_path == str((tmp_path / "new-folder").resolve())
        assert not old_folder.exists()
        assert (tmp_path / "new-folder").is_dir()

    def test_count_immediate_children(self, tmp_path: Path) -> None:
        """count_immediate_children should count only direct children."""
        (tmp_path / "a.txt").write_text("")
        nested = tmp_path / "nested"
        nested.mkdir()
        (nested / "b.txt").write_text("")

        service = FileService()

        assert service.count_immediate_children(str(tmp_path)) == 2
