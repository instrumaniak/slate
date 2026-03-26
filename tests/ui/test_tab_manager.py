"""Tests for TabManager - tab lifecycle management."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock

from slate.ui.editor.tab_manager import TabManager


class TestTabManagerBasics:
    """Test TabManager core functionality."""

    def test_takes_file_service_on_init(self):
        """TabManager should accept FileService in constructor."""
        mock_file_service = Mock()
        tm = TabManager(file_service=mock_file_service)
        assert tm is not None

    def test_opens_tab_reads_file_content(self):
        """Opening a tab should read file via FileService."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "file content"

        tm = TabManager(file_service=mock_file_service)
        tab = tm.open_tab("/test/path.py")

        mock_file_service.read_file.assert_called_once_with("/test/path.py")
        assert tab["path"] == "/test/path.py"
        assert tab["content"] == "file content"
        assert tab["is_dirty"] is False

    def test_duplicate_tab_returns_existing(self):
        """Opening same path should return existing tab."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tab1 = tm.open_tab("/test/file.py")
        tab2 = tm.open_tab("/test/file.py")

        assert mock_file_service.read_file.call_count == 1
        assert tab1 is tab2

    def test_close_tab_removes_from_tabs(self):
        """Closing a tab should remove it from tracking."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file.py")

        tm.close_tab("/test/file.py")

        tabs = tm.get_tabs()
        assert "/test/file.py" not in tabs

    def test_mark_dirty_sets_dirty_flag(self):
        """Marking dirty should set is_dirty to True."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file.py")

        tm.mark_dirty("/test/file.py")

        tabs = tm.get_tabs()
        assert tabs["/test/file.py"]["is_dirty"] is True

    def test_mark_clean_sets_dirty_flag(self):
        """Marking clean should set is_dirty to False."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file.py")
        tm.mark_dirty("/test/file.py")

        tm.mark_clean("/test/file.py")

        tabs = tm.get_tabs()
        assert tabs["/test/file.py"]["is_dirty"] is False

    def test_get_tab_list_returns_paths(self):
        """get_tab_list should return all open paths."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file1.py")
        tm.open_tab("/test/file2.py")

        tab_list = tm.get_tab_list()

        assert len(tab_list) == 2
        assert "/test/file1.py" in tab_list
        assert "/test/file2.py" in tab_list
