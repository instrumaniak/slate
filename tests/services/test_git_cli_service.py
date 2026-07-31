"""Tests for GitCliService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from slate.services.git_cli_service import GitCliService


class TestGitCliService:
    """Test GitCliService functionality."""

    @pytest.mark.timeout(10)
    def test_status_parsing(self) -> None:
        """Git status porcelain output should be parsed correctly."""
        porcelain_output = """ M file1.py
A  file2.py
 D file3.py
?? untracked.py
 R old.py -> new.py
"""
        service = GitCliService()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = porcelain_output

        with patch("subprocess.run", return_value=mock_proc):
            status = service.status("/fake/repo")
            assert len(status) == 5
            paths = [s["path"] for s in status]
            assert "file1.py" in paths
            assert "file2.py" in paths
            assert "file3.py" in paths
            assert "untracked.py" in paths
            assert "new.py" in paths

    @pytest.mark.timeout(10)
    def test_diff_text(self) -> None:
        """Git diff command should produce output string."""
        service = GitCliService()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "diff content"

        with patch("subprocess.run", return_value=mock_proc):
            diff = service.diff_text("/fake/repo", staged=True)
            assert diff == "diff content"

    @pytest.mark.timeout(10)
    def test_get_branches(self) -> None:
        """Git branch list should parse current and non-current branches."""
        branch_output = """* main abc1234 [ahead 1] Commit msg
  feature def5678 Commit msg 2
"""
        service = GitCliService()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = branch_output

        with patch("subprocess.run", return_value=mock_proc):
            branches = service.get_branches("/fake/repo")
            assert len(branches) == 2
            assert branches[0].name == "main"
            assert branches[0].is_current is True
            assert branches[1].name == "feature"
            assert branches[1].is_current is False
