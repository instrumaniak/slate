"""Git service for Slate - handles Git operations via gitpython.

Zero GTK imports at module level - pure Python with gitpython.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from slate.core.event_bus import EventBus
from slate.core.events import GitStatusChangedEvent
from slate.core.models import BranchInfo
from slate.services.git_cli_service import GitCliService

if TYPE_CHECKING:
    from git import Repo

logger = logging.getLogger(__name__)

# Status mapping for git change types
_STATUS_MAP = {
    "M": "M",  # Modified
    "A": "A",  # Added (staged)
    "D": "D",  # Deleted
    "R": "R",  # Renamed
}

# Untracked files status code
_UNTRACKED_STATUS = "?"

# Cache for git availability check
_git_available: bool | None = None
_git_available_lock = threading.Lock()


def _check_git_available() -> None:
    """Check that git binary and gitpython are available.

    This check is cached after the first call for performance.

    Raises:
        RuntimeError: If git is not installed or gitpython is unavailable.
    """
    global _git_available

    # Fast path: already checked and available
    if _git_available is True:
        return

    with _git_available_lock:
        # Double-check after acquiring lock
        if _git_available:
            return

        try:
            import git  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "gitpython is required for GitService. Install it with: pip install gitpython"
            ) from e

        import shutil

        if shutil.which("git") is None:
            raise RuntimeError("Git is not installed. Install it with: sudo apt install git")

        _git_available = True


class GitService:
    """Git operations via gitpython. Zero GTK. Service ID: "git".

    Handles git status, diff, staging, committing, and branch management.
    Emits GitStatusChangedEvent after status-altering operations.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cli_service = GitCliService()

    def _get_repo(self, repo_path: str) -> Repo:
        """Get a git Repo object for the given path.

        Args:
            repo_path: Path to the git repository.

        Returns:
            git.Repo object.

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        _check_git_available()
        import git

        return git.Repo(repo_path)

    def _emit_status_changed(self, repo_path: str) -> None:
        """Emit GitStatusChangedEvent for the given repo.

        Args:
            repo_path: Path to the git repository.
        """
        try:
            changed = self.get_status(repo_path)
            changed_files = [entry["path"] for entry in changed]
            EventBus().emit(GitStatusChangedEvent(path=repo_path, changed_files=changed_files))
        except Exception as e:
            logger.warning(f"Failed to emit GitStatusChangedEvent: {e}")

    def get_status(self, repo_path: str) -> list[dict[str, str]]:
        """Get changed files with status (M/A/D/R/?).

        Args:
            repo_path: Path to the git repository.

        Returns:
            List of dicts with 'path' and 'status' keys.
            Status codes: M=modified, A=added (staged), D=deleted, R=renamed, ?=untracked

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            self._get_repo(repo_path)
            return self._cli_service.status(repo_path)

    def get_diff(self, repo_path: str, path: str | None = None, staged: bool = False) -> str:
        """Get diff text.

        Args:
            repo_path: Path to the git repository.
            path: Optional specific file path to diff.
            staged: If True, return staged diff (git diff --cached).

        Returns:
            Diff text as string.

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            self._get_repo(repo_path)
            return self._cli_service.diff_text(repo_path, path=path, staged=staged)

    def stage_file(self, repo_path: str, path: str) -> None:
        """Stage a file (git add).

        Args:
            repo_path: Path to the git repository.
            path: File path to stage (relative to repo root).

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            repo = self._get_repo(repo_path)
            repo.index.add([path])
            self._emit_status_changed(repo_path)

    def unstage_file(self, repo_path: str, path: str) -> None:
        """Unstage a file (git restore --staged).

        Args:
            repo_path: Path to the git repository.
            path: File path to unstage (relative to repo root).

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            repo = self._get_repo(repo_path)
            repo.index.reset(paths=[path])
            self._emit_status_changed(repo_path)

    def commit(self, repo_path: str, message: str) -> str:
        """Create commit with staged changes.

        Args:
            repo_path: Path to the git repository.
            message: Commit message.

        Returns:
            Commit hash as hex string.

        Raises:
            RuntimeError: If git is not available.
            ValueError: If message is empty or no staged changes.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty")

        with self._lock:
            repo = self._get_repo(repo_path)

            # Check for staged changes
            diff_staged = repo.index.diff("HEAD")
            if not diff_staged and not repo.is_dirty(index=True, working_tree=False):
                raise ValueError("No staged changes to commit")

            commit = repo.index.commit(message)
            self._emit_status_changed(repo_path)
            return commit.hexsha

    def get_branches(self, repo_path: str) -> list[BranchInfo]:
        """List all local branches with current branch marked.

        Args:
            repo_path: Path to the git repository.

        Returns:
            List of BranchInfo objects.

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            self._get_repo(repo_path)
            return self._cli_service.get_branches(repo_path)

    def switch_branch(self, repo_path: str, branch_name: str) -> None:
        """Switch to a branch.

        Args:
            repo_path: Path to the git repository.
            branch_name: Name of the branch to switch to.

        Raises:
            RuntimeError: If git is not available.
            ValueError: If branch does not exist.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            repo = self._get_repo(repo_path)

            # Check branch exists
            branch_names = [h.name for h in repo.heads]
            if branch_name not in branch_names:
                raise ValueError(f"Branch '{branch_name}' not found. Available: {branch_names}")

            repo.heads[branch_name].checkout()
            self._emit_status_changed(repo_path)
