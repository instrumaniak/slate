"""Core data models - Pure Python, zero GTK."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FileStatus:
    """Represents file/folder metadata."""

    path: str
    is_dir: bool
    size: int
    modified_time: float
    is_dirty: bool
    git_status: str | None = None


@dataclass
class TabState:
    """Represents the state of an open tab."""

    path: str
    content: str
    is_dirty: bool
    cursor_line: int
    cursor_column: int
    scroll_position: int


@dataclass
class SearchResult:
    """Represents a single search result."""

    path: str
    line_number: int
    column: int
    line_content: str
    match_start: int
    match_end: int


@dataclass
class BranchInfo:
    """Represents Git branch information."""

    name: str
    is_current: bool
    is_remote: bool
    last_commit: str
