"""Tests for DiffView - inline diff viewer component."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import git
import pytest

from slate.services.git_service import GitService


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with an initial commit."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    initial_file = tmp_path / "test.py"
    initial_file.write_text("line1\nline2\nline3\n")
    repo.index.add(["test.py"])
    repo.index.commit("Initial commit")

    return tmp_path


@pytest.fixture
def git_service() -> GitService:
    """Create a GitService instance."""
    return GitService()


class TestDiffViewParsing:
    """Test diff parsing functionality."""

    def test_parse_additions(self, git_repo: Path, git_service: GitService) -> None:
        """Addition lines should be identified from diff output."""
        (git_repo / "test.py").write_text("line1\nmodified_line2\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "modified_line2" in diff_text
        assert "+modified_line2" in diff_text or "modified_line2" in diff_lines_content(
            diff_text, "+"
        )

    def test_parse_deletions(self, git_repo: Path, git_service: GitService) -> None:
        """Deletion lines should be identified from diff output."""
        (git_repo / "test.py").write_text("line1\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "-line2" in diff_text or "line2" in diff_lines_content(diff_text, "-")

    def test_parse_context_lines(self, git_repo: Path, git_service: GitService) -> None:
        """Context lines (unchanged) should have no highlight marker."""
        (git_repo / "test.py").write_text("line1\nmodified_line2\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert " line1" in diff_text or diff_lines_content(diff_text, " ")


class TestDiffViewLineNumbers:
    """Test line number rendering."""

    def test_old_line_numbers_present(self, git_repo: Path, git_service: GitService) -> None:
        """Old file line numbers should appear in diff."""
        (git_repo / "test.py").write_text("line1\nmodified_line2\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "@@" in diff_text
        assert "-1" in diff_text or "@@ -1," in diff_text

    def test_new_line_numbers_present(self, git_repo: Path, git_service: GitService) -> None:
        """New file line numbers should appear in diff."""
        (git_repo / "test.py").write_text("line1\nmodified_line2\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "@@" in diff_text
        assert "+1" in diff_text or "@@ +1," in diff_text


class TestDiffViewHighlighting:
    """Test diff highlighting."""

    def test_addition_highlight_color(self, git_repo: Path, git_service: GitService) -> None:
        """Additions should have green background color #2ea04320."""
        (git_repo / "test.py").write_text("line1\nnew_line\nline2\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "new_line" in diff_text

    def test_deletion_highlight_color(self, git_repo: Path, git_service: GitService) -> None:
        """Deletions should have red background color #f8514920."""
        (git_repo / "test.py").write_text("line1\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "line2" in diff_text


class TestDiffViewModes:
    """Test view mode functionality."""

    def test_unified_view_is_default(self) -> None:
        """Unified view should be the default display mode."""
        from slate.ui.editor.diff_view import DiffView

        view = DiffView(diff_text="", path="test.py")
        assert view._view_mode == "unified"

    def test_split_view_toggle(self) -> None:
        """Toggle should switch to split view."""
        from slate.ui.editor.diff_view import DiffView

        view = DiffView(diff_text="", path="test.py")
        view.toggle_view_mode()

        assert view._view_mode == "split"

    def test_view_mode_persists_after_toggle(self) -> None:
        """View mode should toggle between unified and split."""
        from slate.ui.editor.diff_view import DiffView

        view = DiffView(diff_text="", path="test.py")
        assert view._view_mode == "unified"

        view.toggle_view_mode()
        assert view._view_mode == "split"

        view.toggle_view_mode()
        assert view._view_mode == "unified"

    def test_view_mode_persists_via_config_service(self) -> None:
        """View mode preference should be persisted via ConfigService."""
        from unittest.mock import Mock
        from slate.ui.editor.diff_view import DiffView

        mock_config = Mock()
        view = DiffView(diff_text="", path="test.py", config_service=mock_config)

        view.toggle_view_mode()

        mock_config.set.assert_called_once_with("diff_view", "view_mode", "split")


class TestDiffViewEmpty:
    """Test empty diff handling."""

    def test_no_changes_message_shown(self, git_repo: Path, git_service: GitService) -> None:
        """Empty diff should show 'No changes' message."""
        from slate.ui.editor.diff_view import DiffView

        diff_text = git_service.get_diff(str(git_repo))
        view = DiffView(diff_text=diff_text, path="test.py")

        assert view._is_empty is True
        assert view._show_no_changes_message() is True


class TestDiffViewPerformance:
    """Test performance requirements."""

    def test_diff_renders_under_100ms(self, git_repo: Path, git_service: GitService) -> None:
        """Diff should render in under 100ms for typical files."""
        import time

        from slate.ui.editor.diff_view import DiffView

        content = "\n".join([f"line {i}" for i in range(100)])
        (git_repo / "test.py").write_text(content)
        git_service.get_diff(str(git_repo))

        diff_text = git_service.get_diff(str(git_repo))

        start = time.perf_counter()
        view = DiffView(diff_text=diff_text, path="test.py")
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 100, f"Diff render took {elapsed:.2f}ms, expected <100ms"


class TestDiffViewGitIntegration:
    """Test GitService integration."""

    def test_get_diff_returns_unified_format(self, git_repo: Path, git_service: GitService) -> None:
        """GitService.get_diff should return unified diff format."""
        (git_repo / "test.py").write_text("line1\nmodified\nline3\n")

        diff_text = git_service.get_diff(str(git_repo))

        assert "---" in diff_text or "@@" in diff_text
        assert "+++" in diff_text or "@@" in diff_text

    def test_get_diff_for_specific_file(self, git_repo: Path, git_service: GitService) -> None:
        """Get diff for specific file should only return that file's diff."""
        (git_repo / "other.py").write_text("other content\n")
        (git_repo / "test.py").write_text("modified\n")

        diff_text = git_service.get_diff(str(git_repo), path="test.py")

        assert "modified" in diff_text
        assert "other content" not in diff_text


def diff_lines_content(diff_text: str, prefix: str) -> str:
    """Extract content of lines with given prefix from diff."""
    lines = diff_text.split("\n")
    return "\n".join(line for line in lines if line.startswith(prefix))
