"""Tests for SourceControlPanel — git status display and branch management."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from slate.ui.panels.source_control_panel import SourceControlPanel, FileStatusItem


class MockGitService:
    """Mock GitService for testing."""

    def __init__(self) -> None:
        self.status_data: list[dict[str, str]] = []
        self.branches_data: list[Any] = []
        self.switch_branch_called = False
        self.switch_branch_path: str | None = None
        self.switch_branch_name: str | None = None

    def get_status(self, repo_path: str) -> list[dict[str, str]]:
        return self.status_data

    def get_branches(self, repo_path: str) -> list[Any]:
        return self.branches_data

    def switch_branch(self, repo_path: str, branch_name: str) -> None:
        self.switch_branch_called = True
        self.switch_branch_path = repo_path
        self.switch_branch_name = branch_name


class MockHostBridge:
    """Mock HostUIBridge for testing."""

    def __init__(self) -> None:
        self.set_activity_badge_calls: list[tuple[str, str]] = []

    def set_activity_badge(self, plugin_id: str, badge_text: str) -> None:
        self.set_activity_badge_calls.append((plugin_id, badge_text))


class TestSourceControlPanel:
    """Test SourceControlPanel functionality."""

    def test_create_status_badge_colors(self) -> None:
        """Status badges should have correct colors for M/A/D/R status codes."""
        panel = SourceControlPanel()

        # Test status color mapping
        assert panel._get_status_color("M") == "#f6c177"  # yellow
        assert panel._get_status_color("A") == "#a0e57c"  # green
        assert panel._get_status_color("D") == "#e06c75"  # red
        assert panel._get_status_color("R") == "#61afef"  # blue
        assert panel._get_status_color("?") == "#cccccc"  # gray for untracked
        assert panel._get_status_color("X") == "#cccccc"  # default gray

    def test_refresh_status_with_git_data(self) -> None:
        """Panel should display git status data correctly."""
        git_service = MockGitService()
        git_service.status_data = [
            {"path": "file1.py", "status": "M"},
            {"path": "file2.py", "status": "A"},
            {"path": "file3.py", "status": "D"},
        ]

        # Mock branch data
        from slate.core.models import BranchInfo

        git_service.branches_data = [
            BranchInfo(name="main", is_current=True, is_remote=False, last_commit="abc123"),
            BranchInfo(name="feature", is_current=False, is_remote=False, last_commit="def456"),
        ]

        panel = SourceControlPanel(git_service=git_service)
        panel.set_current_path("/test/path")
        panel.refresh_status()

        # Verify status items were added
        assert panel._status_store.get_n_items() == 3

        # Verify first item
        item = panel._status_store.get_item(0)
        assert isinstance(item, FileStatusItem)
        assert item.path == "file1.py"
        assert item.status == "M"

    def test_refresh_status_with_missing_git(self) -> None:
        """Panel should show error when git is not available."""
        git_service = MockGitService()

        # Simulate RuntimeError for missing git
        def raise_runtime_error(repo_path: str) -> list[dict[str, str]]:
            raise RuntimeError("git is not installed")

        git_service.get_status = raise_runtime_error

        panel = SourceControlPanel(git_service=git_service)
        panel.set_current_path("/test/path")
        panel.refresh_status()

        # Verify error label is shown
        assert panel._error_label.get_visible() is True
        # Check for user-friendly error message with install instructions
        assert "Git" in panel._error_label.get_text()
        assert "install" in panel._error_label.get_text().lower()

    def test_branch_dropdown_population(self) -> None:
        """Branch dropdown should populate with branch data."""
        git_service = MockGitService()

        # Mock branch data
        from slate.core.models import BranchInfo

        git_service.branches_data = [
            BranchInfo(name="main", is_current=True, is_remote=False, last_commit="abc123"),
            BranchInfo(name="feature", is_current=False, is_remote=False, last_commit="def456"),
        ]

        panel = SourceControlPanel(git_service=git_service)
        panel.set_current_path("/test/path")
        panel.refresh_status()

        # Verify dropdown was populated
        # Note: Actual dropdown testing would require GTK initialization
        # For now, just verify the update method was called
        assert panel._branches == git_service.branches_data

    def test_activity_badge_updates(self) -> None:
        """Activity badge should update with change count."""
        git_service = MockGitService()
        git_service.status_data = [
            {"path": "file1.py", "status": "M"},
            {"path": "file2.py", "status": "A"},
        ]

        host_bridge = MockHostBridge()

        panel = SourceControlPanel(git_service=git_service, host_bridge=host_bridge)
        panel.set_current_path("/test/path")
        panel.refresh_status()

        # Verify activity badge was set (may be called multiple times)
        assert len(host_bridge.set_activity_badge_calls) >= 1
        # Check that at least one call has the correct count
        assert ("source_control", "2") in host_bridge.set_activity_badge_calls

    def test_show_error_and_hide_error(self) -> None:
        """Error label should show and hide messages."""
        panel = SourceControlPanel()

        # Show error
        panel._show_error("Test error message")
        assert panel._error_label.get_visible() is True
        assert panel._error_label.get_text() == "Test error message"

        # Hide error
        panel._hide_error()
        assert panel._error_label.get_visible() is False

    def test_file_status_item_creation(self) -> None:
        """FileStatusItem should store path and status."""
        item = FileStatusItem(path="/test/path/file.py", status="M", display_path="file.py")

        assert item.path == "/test/path/file.py"
        assert item.status == "M"
        assert item.display_path == "file.py"

        # Test without display_path
        item2 = FileStatusItem(path="/test/path/file2.py", status="A")
        assert item2.path == "/test/path/file2.py"
        assert item2.status == "A"
        # display_path defaults to path if not provided
        assert item2.display_path == "/test/path/file2.py"
