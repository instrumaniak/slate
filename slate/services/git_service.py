"""Git service for Slate - handles Git operations via gitpython.

Zero GTK imports at module level - pure Python with gitpython.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from typing import TYPE_CHECKING

from slate.core.event_bus import EventBus
from slate.core.events import GitStatusChangedEvent
from slate.core.models import BranchInfo

if TYPE_CHECKING:
    from git import Repo

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    "M": "M",
    "A": "A",
    "D": "D",
    "R": "R",
}


def _check_git_available() -> None:
    """Check that git binary and gitpython are available.

    Raises:
        RuntimeError: If git is not installed or gitpython is unavailable.
    """
    try:
        import git  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "gitpython is required for GitService. Install it with: pip install gitpython"
        ) from e

    import shutil

    if shutil.which("git") is None:
        raise RuntimeError("Git is not installed. Install it with: sudo apt install git")


class GitService:
    """Git operations via gitpython. Zero GTK. Service ID: "git".

    Handles git status, diff, staging, committing, and branch management.
    Emits GitStatusChangedEvent after status-altering operations.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

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
        """Get changed files with status (M/A/D/R).

        Args:
            repo_path: Path to the git repository.

        Returns:
            List of dicts with 'path' and 'status' keys.

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            repo = self._get_repo(repo_path)
            results: list[dict[str, str]] = []

            # Modified files (staged and unstaged)
            diff_index = repo.index.diff(None)
            for diff_item in diff_index:
                path = diff_item.b_path or diff_item.a_path
                change_type = diff_item.change_type
                status = _STATUS_MAP.get(change_type, change_type)
                results.append({"path": path, "status": status})

            # Staged changes
            diff_staged = repo.index.diff("HEAD")
            for diff_item in diff_staged:
                path = diff_item.b_path or diff_item.a_path
                change_type = diff_item.change_type
                status = _STATUS_MAP.get(change_type, change_type)
                if not any(r["path"] == path for r in results):
                    results.append({"path": path, "status": status})

            # Untracked files
            for path in repo.untracked_files:
                if not any(r["path"] == path for r in results):
                    results.append({"path": path, "status": "A"})

            return results

    def get_diff(self, repo_path: str, path: str | None = None) -> str:
        """Get diff text.

        Args:
            repo_path: Path to the git repository.
            path: Optional specific file path to diff.

        Returns:
            Diff text as string.

        Raises:
            RuntimeError: If git is not available.
            git.InvalidGitRepositoryError: If path is not a git repo.
        """
        with self._lock:
            repo = self._get_repo(repo_path)

            if path is not None:
                return repo.git.diff("--", path)
            return repo.git.diff()

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
            repo = self._get_repo(repo_path)
            branches: list[BranchInfo] = []

            current_name = None
            with contextlib.suppress(TypeError):
                current_name = repo.active_branch.name

            for branch in repo.heads:
                last_commit = ""
                with contextlib.suppress(Exception):
                    last_commit = branch.commit.hexsha[:8]

                branches.append(
                    BranchInfo(
                        name=branch.name,
                        is_current=branch.name == current_name,
                        is_remote=False,
                        last_commit=last_commit,
                    )
                )

            return branches

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
