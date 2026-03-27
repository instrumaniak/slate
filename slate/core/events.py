"""Core event definitions - Pure Python, zero GTK."""

from __future__ import annotations

from dataclasses import dataclass

from slate.core.models import SearchResult


@dataclass
class BaseEvent:
    """Base class for all events."""

    pass


@dataclass
class FileOpenedEvent(BaseEvent):
    """Emitted when a file is opened."""

    path: str
    content: str


@dataclass
class FileSavedEvent(BaseEvent):
    """Emitted when a file is saved."""

    path: str
    old_path: str | None = None


@dataclass
class GitStatusChangedEvent(BaseEvent):
    """Emitted when Git status changes."""

    path: str
    changed_files: list[str]


@dataclass
class ThemeChangedEvent(BaseEvent):
    """Emitted when theme changes."""

    color_mode: str
    resolved_is_dark: bool
    editor_scheme: str


@dataclass
class OpenFileRequestedEvent(BaseEvent):
    """Request to open a file (from UI/Plugins)."""

    path: str


@dataclass
class OpenDiffRequestedEvent(BaseEvent):
    """Request to open diff view (from UI/Plugins)."""

    path: str
    is_staged: bool


@dataclass
class TabClosedEvent(BaseEvent):
    """Emitted when a tab is closed."""

    path: str


@dataclass
class TabActivatedEvent(BaseEvent):
    """Emitted when a tab is activated via cycle or selection."""

    path: str


@dataclass
class SearchResultsReadyEvent(BaseEvent):
    """Emitted when search results are ready."""

    query: str
    results: list[SearchResult]
