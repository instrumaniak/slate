"""Tests for GitService - Git operations via gitpython."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import git
import pytest

from slate.core.event_bus import EventBus
from slate.core.events import GitStatusChangedEvent
from slate.core.models import BranchInfo
from slate.services.git_service import GitService


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with an initial commit."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    initial_file = tmp_path / "initial.txt"
    initial_file.write_text("initial content")
    repo.index.add(["initial.txt"])
    repo.index.commit("Initial commit")

    return tmp_path


@pytest.fixture
def git_repo_with_changes(git_repo: Path) -> Path:
    """Create a git repo with a modified file."""
    file_path = git_repo / "initial.txt"
    file_path.write_text("modified content")
    return git_repo


class TestGitServiceGetStatus:
    """Test GitService.get_status()."""

    def test_clean_repo(self, git_repo: Path) -> None:
        """Clean repo should return empty status."""
        service = GitService()
        status = service.get_status(str(git_repo))
        assert status == []

    def test_modified_file(self, git_repo: Path) -> None:
        """Modified file should appear as 'M'."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        status = service.get_status(str(git_repo))

        assert len(status) == 1
        assert status[0]["status"] == "M"
        assert status[0]["path"] == "initial.txt"

    def test_added_file(self, git_repo: Path) -> None:
        """Untracked file should appear as 'A'."""
        (git_repo / "new_file.txt").write_text("new content")

        service = GitService()
        status = service.get_status(str(git_repo))

        paths = [s["path"] for s in status]
        assert "new_file.txt" in paths
        new_entry = next(s for s in status if s["path"] == "new_file.txt")
        assert new_entry["status"] == "A"

    def test_deleted_file(self, git_repo: Path) -> None:
        """Deleted file should appear as 'D'."""
        (git_repo / "initial.txt").unlink()

        service = GitService()
        status = service.get_status(str(git_repo))

        assert len(status) == 1
        assert status[0]["status"] == "D"

    def test_non_git_directory_raises(self, tmp_path: Path) -> None:
        """Non-git directory should raise error."""
        service = GitService()
        with pytest.raises((git.InvalidGitRepositoryError, git.NoSuchPathError)):
            service.get_status(str(tmp_path))


class TestGitServiceGetDiff:
    """Test GitService.get_diff()."""

    def test_clean_repo_empty_diff(self, git_repo: Path) -> None:
        """Clean repo should return empty diff."""
        service = GitService()
        diff = service.get_diff(str(git_repo))
        assert diff == ""

    def test_modified_file_diff(self, git_repo: Path) -> None:
        """Modified file should produce diff."""
        (git_repo / "initial.txt").write_text("changed content")

        service = GitService()
        diff = service.get_diff(str(git_repo))

        assert "changed content" in diff

    def test_diff_specific_file(self, git_repo: Path) -> None:
        """Diff for specific file should only include that file."""
        (git_repo / "other.txt").write_text("other")
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        diff = service.get_diff(str(git_repo), path="initial.txt")

        assert "changed" in diff

    def test_diff_clean_repo_for_file(self, git_repo: Path) -> None:
        """Diff for unchanged file in clean repo should be empty."""
        service = GitService()
        diff = service.get_diff(str(git_repo), path="initial.txt")
        assert diff == ""


class TestGitServiceStageUnstage:
    """Test GitService.stage_file() and unstage_file()."""

    def test_stage_modified_file(self, git_repo: Path) -> None:
        """Staging a modified file should add it to index."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        service.stage_file(str(git_repo), "initial.txt")

        repo = git.Repo(git_repo)
        diff_staged = repo.index.diff("HEAD")
        assert any(d.b_path == "initial.txt" for d in diff_staged)

    def test_stage_emits_event(self, git_repo: Path) -> None:
        """Staging should emit GitStatusChangedEvent."""
        (git_repo / "initial.txt").write_text("changed")

        events: list[GitStatusChangedEvent] = []

        def handler(event: GitStatusChangedEvent) -> None:
            events.append(event)

        bus = EventBus()
        bus.subscribe(GitStatusChangedEvent, handler)

        try:
            service = GitService()
            service.stage_file(str(git_repo), "initial.txt")

            assert len(events) == 1
            assert events[0].path == str(git_repo)
        finally:
            bus.unsubscribe(GitStatusChangedEvent, handler)

    def test_unstage_file(self, git_repo: Path) -> None:
        """Unstaging should remove file from index."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        service.stage_file(str(git_repo), "initial.txt")
        service.unstage_file(str(git_repo), "initial.txt")

        repo = git.Repo(git_repo)
        diff_staged = repo.index.diff("HEAD")
        assert not any(d.b_path == "initial.txt" for d in diff_staged)

    def test_unstage_emits_event(self, git_repo: Path) -> None:
        """Unstaging should emit GitStatusChangedEvent."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        service.stage_file(str(git_repo), "initial.txt")

        events: list[GitStatusChangedEvent] = []

        def handler(event: GitStatusChangedEvent) -> None:
            events.append(event)

        bus = EventBus()
        bus.subscribe(GitStatusChangedEvent, handler)

        try:
            service.unstage_file(str(git_repo), "initial.txt")

            assert len(events) == 1
        finally:
            bus.unsubscribe(GitStatusChangedEvent, handler)


class TestGitServiceCommit:
    """Test GitService.commit()."""

    def test_commit_staged_changes(self, git_repo: Path) -> None:
        """Commit should create a new commit with staged changes."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        service.stage_file(str(git_repo), "initial.txt")
        commit_hash = service.commit(str(git_repo), "Test commit")

        assert len(commit_hash) == 40

        repo = git.Repo(git_repo)
        assert repo.head.commit.message == "Test commit"

    def test_commit_returns_hash(self, git_repo: Path) -> None:
        """Commit should return the commit hash."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        service.stage_file(str(git_repo), "initial.txt")
        commit_hash = service.commit(str(git_repo), "Test commit")

        repo = git.Repo(git_repo)
        assert commit_hash == repo.head.commit.hexsha

    def test_commit_emits_event(self, git_repo: Path) -> None:
        """Commit should emit GitStatusChangedEvent."""
        (git_repo / "initial.txt").write_text("changed")

        service = GitService()
        service.stage_file(str(git_repo), "initial.txt")

        events: list[GitStatusChangedEvent] = []

        def handler(event: GitStatusChangedEvent) -> None:
            events.append(event)

        bus = EventBus()
        bus.subscribe(GitStatusChangedEvent, handler)

        try:
            service.commit(str(git_repo), "Test commit")

            assert len(events) == 1
        finally:
            bus.unsubscribe(GitStatusChangedEvent, handler)

    def test_commit_empty_message_raises(self, git_repo: Path) -> None:
        """Empty commit message should raise ValueError."""
        service = GitService()
        with pytest.raises(ValueError, match="cannot be empty"):
            service.commit(str(git_repo), "")

    def test_commit_whitespace_message_raises(self, git_repo: Path) -> None:
        """Whitespace-only commit message should raise ValueError."""
        service = GitService()
        with pytest.raises(ValueError, match="cannot be empty"):
            service.commit(str(git_repo), "   ")

    def test_commit_no_staged_changes_raises(self, git_repo: Path) -> None:
        """Commit without staged changes should raise ValueError."""
        service = GitService()
        with pytest.raises(ValueError, match="No staged changes"):
            service.commit(str(git_repo), "Nothing to commit")


class TestGitServiceBranches:
    """Test GitService.get_branches() and switch_branch()."""

    def test_get_branches(self, git_repo: Path) -> None:
        """Should list branches with current branch marked."""
        service = GitService()
        branches = service.get_branches(str(git_repo))

        assert len(branches) >= 1
        current = [b for b in branches if b.is_current]
        assert len(current) == 1

    def test_get_branches_returns_branch_info(self, git_repo: Path) -> None:
        """Each branch should be a BranchInfo object."""
        service = GitService()
        branches = service.get_branches(str(git_repo))

        for branch in branches:
            assert isinstance(branch, BranchInfo)
            assert branch.name
            assert branch.is_remote is False

    def test_switch_branch(self, git_repo: Path) -> None:
        """Switching branch should update active branch."""
        repo = git.Repo(git_repo)
        repo.create_head("feature")

        service = GitService()
        service.switch_branch(str(git_repo), "feature")

        assert repo.active_branch.name == "feature"

    def test_switch_branch_emits_event(self, git_repo: Path) -> None:
        """Switching branch should emit GitStatusChangedEvent."""
        repo = git.Repo(git_repo)
        repo.create_head("feature")

        events: list[GitStatusChangedEvent] = []

        def handler(event: GitStatusChangedEvent) -> None:
            events.append(event)

        bus = EventBus()
        bus.subscribe(GitStatusChangedEvent, handler)

        try:
            service = GitService()
            service.switch_branch(str(git_repo), "feature")

            assert len(events) == 1
        finally:
            bus.unsubscribe(GitStatusChangedEvent, handler)

    def test_switch_nonexistent_branch_raises(self, git_repo: Path) -> None:
        """Switching to non-existent branch should raise ValueError."""
        service = GitService()
        with pytest.raises(ValueError, match="not found"):
            service.switch_branch(str(git_repo), "nonexistent")


class TestGitServiceZeroGtk:
    """Test zero GTK imports at module level."""

    def test_no_gtk_imports_at_module_level(self) -> None:
        """GitService module should have zero GTK imports at module level."""
        import ast
        import inspect

        import slate.services.git_service as git_module

        # Parse AST to find GTK imports only at module level (not inside functions)
        source = inspect.getsource(git_module)
        tree = ast.parse(source)

        module_level_gtk_imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "gi" or alias.name.startswith("gi."):
                        module_level_gtk_imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "gi" or node.module.startswith("gi.")):
                    module_level_gtk_imports.append(f"from {node.module}")

        assert len(module_level_gtk_imports) == 0, (
            f"Found GTK imports at module level: {module_level_gtk_imports}"
        )


class TestGitServiceThreadSafety:
    """Test GitService thread safety."""

    def test_concurrent_status_reads(self, git_repo: Path) -> None:
        """Concurrent status reads should not corrupt data."""
        import threading

        service = GitService()
        results: list[list[dict[str, str]]] = []
        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(20):
                    status = service.get_status(str(git_repo))
                    results.append(status)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent reads: {errors}"
        assert len(results) == 80
