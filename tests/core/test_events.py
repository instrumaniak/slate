"""Tests for core event definitions."""

from __future__ import annotations

import pytest
from dataclasses import is_dataclass
from abc import ABC


class TestBaseEvent:
    """Test BaseEvent if it exists."""

    def test_base_event_is_dataclass(self):
        """BaseEvent should be a dataclass."""
        from slate.core.events import BaseEvent

        assert is_dataclass(BaseEvent)


class TestFileOpenedEvent:
    """Test FileOpenedEvent."""

    def test_file_opened_event_is_dataclass(self):
        """FileOpenedEvent should be a dataclass."""
        from slate.core.events import FileOpenedEvent

        assert is_dataclass(FileOpenedEvent)

    def test_file_opened_event_creation(self):
        """FileOpenedEvent should be creatable with required attributes."""
        from slate.core.events import FileOpenedEvent

        event = FileOpenedEvent(path="/test/file.py", content="print('hello')")
        assert event.path == "/test/file.py"
        assert event.content == "print('hello')"


class TestFileSavedEvent:
    """Test FileSavedEvent."""

    def test_file_saved_event_is_dataclass(self):
        """FileSavedEvent should be a dataclass."""
        from slate.core.events import FileSavedEvent

        assert is_dataclass(FileSavedEvent)

    def test_file_saved_event_creation(self):
        """FileSavedEvent should be creatable with required attributes."""
        from slate.core.events import FileSavedEvent

        event = FileSavedEvent(path="/test/file.py")
        assert event.path == "/test/file.py"
        assert event.old_path is None

    def test_file_saved_event_with_old_path(self):
        """FileSavedEvent should handle old_path optional attribute."""
        from slate.core.events import FileSavedEvent

        event = FileSavedEvent(path="/test/file_new.py", old_path="/test/file_old.py")
        assert event.path == "/test/file_new.py"
        assert event.old_path == "/test/file_old.py"


class TestGitStatusChangedEvent:
    """Test GitStatusChangedEvent."""

    def test_git_status_changed_event_is_dataclass(self):
        """GitStatusChangedEvent should be a dataclass."""
        from slate.core.events import GitStatusChangedEvent

        assert is_dataclass(GitStatusChangedEvent)

    def test_git_status_changed_event_creation(self):
        """GitStatusChangedEvent should be creatable with required attributes."""
        from slate.core.events import GitStatusChangedEvent

        event = GitStatusChangedEvent(path="/test", changed_files=["file1.py", "file2.py"])
        assert event.path == "/test"
        assert event.changed_files == ["file1.py", "file2.py"]


class TestThemeChangedEvent:
    """Test ThemeChangedEvent."""

    def test_theme_changed_event_is_dataclass(self):
        """ThemeChangedEvent should be a dataclass."""
        from slate.core.events import ThemeChangedEvent

        assert is_dataclass(ThemeChangedEvent)

    def test_theme_changed_event_creation(self):
        """ThemeChangedEvent should be creatable with required attributes."""
        from slate.core.events import ThemeChangedEvent

        event = ThemeChangedEvent(color_mode="dark", resolved_is_dark=True, editor_scheme="monokai")
        assert event.color_mode == "dark"
        assert event.resolved_is_dark is True
        assert event.editor_scheme == "monokai"


class TestRequestEvents:
    """Test request events."""

    def test_open_file_requested_event_is_dataclass(self):
        """OpenFileRequestedEvent should be a dataclass."""
        from slate.core.events import OpenFileRequestedEvent

        assert is_dataclass(OpenFileRequestedEvent)

    def test_open_file_requested_event_creation(self):
        """OpenFileRequestedEvent should be creatable."""
        from slate.core.events import OpenFileRequestedEvent

        event = OpenFileRequestedEvent(path="/test/file.py")
        assert event.path == "/test/file.py"

    def test_open_diff_requested_event_is_dataclass(self):
        """OpenDiffRequestedEvent should be a dataclass."""
        from slate.core.events import OpenDiffRequestedEvent

        assert is_dataclass(OpenDiffRequestedEvent)

    def test_open_diff_requested_event_creation(self):
        """OpenDiffRequestedEvent should be creatable."""
        from slate.core.events import OpenDiffRequestedEvent

        event = OpenDiffRequestedEvent(path="/test", is_staged=False)
        assert event.path == "/test"
        assert event.is_staged is False

    def test_open_diff_requested_event_staged(self):
        """OpenDiffRequestedEvent should handle staged parameter."""
        from slate.core.events import OpenDiffRequestedEvent

        event = OpenDiffRequestedEvent(path="/test", is_staged=True)
        assert event.is_staged is True


class TestTabClosedEvent:
    """Test TabClosedEvent."""

    def test_tab_closed_event_is_dataclass(self):
        """TabClosedEvent should be a dataclass."""
        from slate.core.events import TabClosedEvent

        assert is_dataclass(TabClosedEvent)

    def test_tab_closed_event_creation(self):
        """TabClosedEvent should be creatable."""
        from slate.core.events import TabClosedEvent

        event = TabClosedEvent(path="/test/file.py")
        assert event.path == "/test/file.py"


class TestSearchResultsReadyEvent:
    """Test SearchResultsReadyEvent."""

    def test_search_results_ready_event_is_dataclass(self):
        """SearchResultsReadyEvent should be a dataclass."""
        from slate.core.events import SearchResultsReadyEvent

        assert is_dataclass(SearchResultsReadyEvent)

    def test_search_results_ready_event_creation(self):
        """SearchResultsReadyEvent should be creatable."""
        from slate.core.events import SearchResultsReadyEvent

        event = SearchResultsReadyEvent(query="def ", results=[])
        assert event.query == "def "
        assert event.results == []

    def test_search_results_ready_event_with_results(self):
        """SearchResultsReadyEvent should handle results."""
        from slate.core.events import SearchResultsReadyEvent
        from slate.core.models import SearchResult

        results = [
            SearchResult(
                path="/test/file.py",
                line_number=10,
                column=0,
                line_content="def hello():",
                match_start=0,
                match_end=3,
            )
        ]
        event = SearchResultsReadyEvent(query="def ", results=results)
        assert len(event.results) == 1
