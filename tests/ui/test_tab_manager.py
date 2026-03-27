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


class TestTabManagerCloseDialog:
    """Test save/discard dialog integration."""

    def test_close_clean_tab_no_dialog(self):
        """Closing clean tab should not trigger dialog."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file.py")

        result = tm.close_tab("/test/file.py")

        assert result is True
        mock_file_service.write_file.assert_not_called()

    def test_close_dirty_tab_triggers_dialog(self):
        """Closing dirty tab should trigger dialog callback."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        dialog_callback = Mock(return_value="cancel")

        tm = TabManager(file_service=mock_file_service)
        tm.set_close_dialog_callback(dialog_callback)
        tm.open_tab("/test/file.py")
        tm.mark_dirty("/test/file.py")

        tm.close_tab("/test/file.py")

        dialog_callback.assert_called_once()

    def test_close_dirty_tab_save_action(self):
        """Save action should write file and close tab."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        dialog_callback = Mock(return_value="save")

        tm = TabManager(file_service=mock_file_service)
        tm.set_close_dialog_callback(dialog_callback)
        tm.open_tab("/test/file.py")
        tm.mark_dirty("/test/file.py")

        result = tm.close_tab("/test/file.py")

        assert result is True
        mock_file_service.write_file.assert_called_once_with("/test/file.py", "content")
        assert "/test/file.py" not in tm.get_tabs()

    def test_close_dirty_tab_discard_action(self):
        """Discard action should close tab without saving."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        dialog_callback = Mock(return_value="discard")

        tm = TabManager(file_service=mock_file_service)
        tm.set_close_dialog_callback(dialog_callback)
        tm.open_tab("/test/file.py")
        tm.mark_dirty("/test/file.py")

        result = tm.close_tab("/test/file.py")

        assert result is True
        mock_file_service.write_file.assert_not_called()
        assert "/test/file.py" not in tm.get_tabs()

    def test_close_dirty_tab_cancel_action(self):
        """Cancel action should keep tab open."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        dialog_callback = Mock(return_value="cancel")

        tm = TabManager(file_service=mock_file_service)
        tm.set_close_dialog_callback(dialog_callback)
        tm.open_tab("/test/file.py")
        tm.mark_dirty("/test/file.py")

        result = tm.close_tab("/test/file.py")

        assert result is False
        assert "/test/file.py" in tm.get_tabs()


class TestTabManagerCycling:
    """Test tab cycling functionality."""

    def test_cycle_next_wraps_around(self):
        """Cycling next from last tab should wrap to first."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file1.py")
        tm.open_tab("/test/file2.py")
        tm.open_tab("/test/file3.py")

        tm.set_active_tab("/test/file3.py")

        next_path = tm.cycle_next()

        assert next_path == "/test/file1.py"

    def test_cycle_previous_wraps_around(self):
        """Cycling previous from first tab should wrap to last."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file1.py")
        tm.open_tab("/test/file2.py")
        tm.open_tab("/test/file3.py")

        tm.set_active_tab("/test/file1.py")

        prev_path = tm.cycle_previous()

        assert prev_path == "/test/file3.py"

    def test_cycle_next_returns_none_with_no_tabs(self):
        """Cycle next with no tabs should return None."""
        mock_file_service = Mock()

        tm = TabManager(file_service=mock_file_service)

        result = tm.cycle_next()

        assert result is None

    def test_cycle_updates_active_tab(self):
        """Cycle should update active tab."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file1.py")
        tm.open_tab("/test/file2.py")

        assert tm.get_active_tab() == "/test/file2.py"

        tm.cycle_next()

        assert tm.get_active_tab() == "/test/file1.py"


class TestTabManagerReorder:
    """Test tab reordering."""

    def test_reorder_tabs_changes_order(self):
        """Reorder tabs should change tab order."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file1.py")
        tm.open_tab("/test/file2.py")
        tm.open_tab("/test/file3.py")

        tm.reorder_tabs(["/test/file3.py", "/test/file1.py", "/test/file2.py"])

        assert tm.get_tab_list() == ["/test/file3.py", "/test/file1.py", "/test/file2.py"]

    def test_reorder_tabs_ignores_invalid_order(self):
        """Reorder with invalid tabs should be ignored."""
        mock_file_service = Mock()
        mock_file_service.read_file.return_value = "content"

        tm = TabManager(file_service=mock_file_service)
        tm.open_tab("/test/file1.py")
        tm.open_tab("/test/file2.py")

        tm.reorder_tabs(["/test/file1.py", "/test/nonexistent.py"])

        assert tm.get_tab_list() == ["/test/file1.py", "/test/file2.py"]
