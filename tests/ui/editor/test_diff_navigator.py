"""Tests for DiffNavigator widget."""

from __future__ import annotations

from slate.services.diff_parser import DiffHunk, FileDiff
from slate.ui.editor.diff_navigator import DiffNavigator


class TestDiffNavigator:
    """Test DiffNavigator component."""

    def test_navigator_initialization(self) -> None:
        """DiffNavigator should accept FileDiff objects."""
        diffs = [
            FileDiff(
                old_path="old.py",
                new_path="new.py",
                status="M",
                hunks=[DiffHunk(old_start=1, old_count=2, new_start=1, new_count=2, lines=["+a"])],
            )
        ]
        nav = DiffNavigator(diffs=diffs)
        assert len(nav._diffs) == 1

    def test_set_diffs(self) -> None:
        """set_diffs should update internal data."""
        nav = DiffNavigator()
        assert len(nav._diffs) == 0

        diffs = [FileDiff(old_path="a.py", new_path="a.py", status="A")]
        nav.set_diffs(diffs)
        assert len(nav._diffs) == 1
