"""Core layer - Pure Python, zero GTK."""

from slate.core.event_bus import EventBus
from slate.core.events import (
    BaseEvent,
    FileOpenedEvent,
    FileSavedEvent,
    GitStatusChangedEvent,
    OpenDiffRequestedEvent,
    OpenFileRequestedEvent,
    SearchResultsReadyEvent,
    TabClosedEvent,
    ThemeChangedEvent,
)
from slate.core.models import (
    BranchInfo,
    FileStatus,
    SearchResult,
    TabState,
)

__all__ = [
    "BranchInfo",
    "FileStatus",
    "SearchResult",
    "TabState",
    "BaseEvent",
    "FileOpenedEvent",
    "FileSavedEvent",
    "GitStatusChangedEvent",
    "OpenDiffRequestedEvent",
    "OpenFileRequestedEvent",
    "SearchResultsReadyEvent",
    "TabClosedEvent",
    "ThemeChangedEvent",
    "EventBus",
]
