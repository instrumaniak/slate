"""Unified diff format parser for Slate.

Parses unified diff output into structured FileDiff and DiffHunk objects.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiffHunk:
    """One contiguous block of diff output."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FileDiff:
    """Diff for a single file."""

    old_path: str | None
    new_path: str | None
    status: str  # M, A, D, R, C, etc.
    hunks: list[DiffHunk] = field(default_factory=list)
    is_binary: bool = False


_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _strip_path_prefix(path: str, prefix: str) -> str | None:
    path = path.strip()
    with suppress(ValueError, IndexError):
        path = shlex.split(path)[0]
    if path == "/dev/null":
        return None
    return path[2:] if path.startswith(prefix) else path


def _git_header_paths(line: str) -> tuple[str | None, str | None]:
    try:
        parts = shlex.split(line, posix=True)
    except ValueError:
        parts = line.split()
    if len(parts) < 4:
        return None, None
    return _strip_path_prefix(parts[2], "a/"), _strip_path_prefix(parts[3], "b/")


class DiffParser:
    """Parses unified diff format text or streams into FileDiff structures."""

    @staticmethod
    def parse_diff_stream(lines: Iterable[str]) -> Iterator[FileDiff]:
        """Stream FileDiff objects from diff lines.

        Args:
            lines: Iterable yielding raw diff lines.

        Yields:
            FileDiff objects.
        """
        current_old_path: str | None = None
        current_new_path: str | None = None
        current_status: str = "M"
        is_binary = False
        hunks: list[DiffHunk] = []

        current_hunk_old_start = 0
        current_hunk_old_count = 0
        current_hunk_new_start = 0
        current_hunk_new_count = 0
        current_hunk_lines: list[str] = []
        in_hunk = False

        def flush_file() -> FileDiff | None:
            nonlocal current_old_path, current_new_path, current_status, is_binary, hunks
            nonlocal in_hunk, current_hunk_lines
            if in_hunk:
                hunks.append(
                    DiffHunk(
                        old_start=current_hunk_old_start,
                        old_count=current_hunk_old_count,
                        new_start=current_hunk_new_start,
                        new_count=current_hunk_new_count,
                        lines=current_hunk_lines,
                    )
                )
                in_hunk = False
                current_hunk_lines = []

            if current_old_path is not None or current_new_path is not None or hunks or is_binary:
                file_diff = FileDiff(
                    old_path=current_old_path,
                    new_path=current_new_path or current_old_path,
                    status=current_status,
                    hunks=hunks,
                    is_binary=is_binary,
                )
                current_old_path = None
                current_new_path = None
                current_status = "M"
                is_binary = False
                hunks = []
                return file_diff
            return None

        for raw_line in lines:
            line = raw_line.rstrip("\r\n")

            if line.startswith("diff --git"):
                diff = flush_file()
                if diff is not None:
                    yield diff
                # Extract paths from `diff --git a/file b/file`
                current_old_path, current_new_path = _git_header_paths(line)
                continue

            if line.startswith("new file mode"):
                current_status = "A"
                continue
            if line.startswith("deleted file mode"):
                current_status = "D"
                continue
            if line.startswith("similarity index"):
                current_status = "R"
                continue
            if line.startswith("Binary files"):
                is_binary = True
                continue
            if line.startswith("GIT binary patch"):
                is_binary = True
                continue

            if line.startswith("--- "):
                path_str = line[4:].split("\t", 1)[0]
                current_old_path = _strip_path_prefix(path_str, "a/")
                continue
            if line.startswith("+++ "):
                path_str = line[4:].split("\t", 1)[0]
                current_new_path = _strip_path_prefix(path_str, "b/")
                continue

            if line.startswith("@@"):
                if in_hunk:
                    hunks.append(
                        DiffHunk(
                            old_start=current_hunk_old_start,
                            old_count=current_hunk_old_count,
                            new_start=current_hunk_new_start,
                            new_count=current_hunk_new_count,
                            lines=current_hunk_lines,
                        )
                    )
                    current_hunk_lines = []

                match = _HUNK_HEADER_RE.match(line)
                if match:
                    current_hunk_old_start = int(match.group(1))
                    current_hunk_old_count = int(match.group(2)) if match.group(2) else 1
                    current_hunk_new_start = int(match.group(3))
                    current_hunk_new_count = int(match.group(4)) if match.group(4) else 1
                    in_hunk = True
                continue

            if in_hunk:
                if (
                    line.startswith("+")
                    or line.startswith("-")
                    or line.startswith(" ")
                    or line.startswith("\\ No newline at end of file")
                ):
                    current_hunk_lines.append(line)
                else:
                    # Context line without prefix
                    current_hunk_lines.append(" " + line)

        final_diff = flush_file()
        if final_diff is not None:
            yield final_diff

    @classmethod
    def parse_diff_text(cls, diff_text: str) -> list[FileDiff]:
        """Parse unified diff text string into list of FileDiffs.

        Args:
            diff_text: Raw diff text string.

        Returns:
            List of FileDiff objects.
        """
        if not diff_text or not diff_text.strip():
            return []
        return list(cls.parse_diff_stream(diff_text.splitlines()))
