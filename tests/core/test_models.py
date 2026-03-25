"""Tests for core data models."""

from __future__ import annotations

import pytest
from dataclasses import is_dataclass


class TestFileStatus:
    """Test FileStatus dataclass."""

    def test_file_status_is_dataclass(self):
        """FileStatus should be a dataclass."""
        from slate.core.models import FileStatus

        assert is_dataclass(FileStatus)

    def test_file_status_creation(self):
        """FileStatus should be creatable with required attributes."""
        from slate.core.models import FileStatus

        fs = FileStatus(
            path="/test/file.py",
            is_dir=False,
            size=1024,
            modified_time=1234567890.0,
            is_dirty=False,
            git_status="modified",
        )
        assert fs.path == "/test/file.py"
        assert fs.is_dir is False
        assert fs.size == 1024
        assert fs.modified_time == 1234567890.0
        assert fs.is_dirty is False
        assert fs.git_status == "modified"

    def test_file_status_dir_creation(self):
        """FileStatus should handle directory creation."""
        from slate.core.models import FileStatus

        fs = FileStatus(
            path="/test/dir",
            is_dir=True,
            size=0,
            modified_time=1234567890.0,
            is_dirty=False,
            git_status=None,
        )
        assert fs.is_dir is True
        assert fs.git_status is None


class TestTabState:
    """Test TabState dataclass."""

    def test_tab_state_is_dataclass(self):
        """TabState should be a dataclass."""
        from slate.core.models import TabState

        assert is_dataclass(TabState)

    def test_tab_state_creation(self):
        """TabState should be creatable with required attributes."""
        from slate.core.models import TabState

        ts = TabState(
            path="/test/file.py",
            content="print('hello')",
            is_dirty=False,
            cursor_line=1,
            cursor_column=0,
            scroll_position=0,
        )
        assert ts.path == "/test/file.py"
        assert ts.content == "print('hello')"
        assert ts.is_dirty is False
        assert ts.cursor_line == 1
        assert ts.cursor_column == 0
        assert ts.scroll_position == 0


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_search_result_is_dataclass(self):
        """SearchResult should be a dataclass."""
        from slate.core.models import SearchResult

        assert is_dataclass(SearchResult)

    def test_search_result_creation(self):
        """SearchResult should be creatable with required attributes."""
        from slate.core.models import SearchResult

        sr = SearchResult(
            path="/test/file.py",
            line_number=42,
            column=10,
            line_content="def hello():",
            match_start=4,
            match_end=9,
        )
        assert sr.path == "/test/file.py"
        assert sr.line_number == 42
        assert sr.column == 10
        assert sr.line_content == "def hello():"
        assert sr.match_start == 4
        assert sr.match_end == 9


class TestBranchInfo:
    """Test BranchInfo dataclass."""

    def test_branch_info_is_dataclass(self):
        """BranchInfo should be a dataclass."""
        from slate.core.models import BranchInfo

        assert is_dataclass(BranchInfo)

    def test_branch_info_creation(self):
        """BranchInfo should be creatable with required attributes."""
        from slate.core.models import BranchInfo

        bi = BranchInfo(name="main", is_current=True, is_remote=False, last_commit="abc123")
        assert bi.name == "main"
        assert bi.is_current is True
        assert bi.is_remote is False
        assert bi.last_commit == "abc123"

    def test_branch_info_remote_creation(self):
        """BranchInfo should handle remote branch creation."""
        from slate.core.models import BranchInfo

        bi = BranchInfo(name="origin/main", is_current=False, is_remote=True, last_commit="def456")
        assert bi.is_remote is True
        assert bi.is_current is False
