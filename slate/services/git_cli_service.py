"""High-performance Git service using subprocess + streaming parser.

Replaces gitpython for read-only status, diff, log, and branch operations.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
import threading
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass

from slate.core.models import BranchInfo
from slate.services.diff_parser import DiffParser, FileDiff

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitInfo:
    """Git commit information."""

    commit_hash: str
    author_name: str
    author_email: str
    timestamp: int
    message: str


class GitCliService:
    """Stream git diff, status, log output via git CLI binary."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds

    def status(self, repo_path: str) -> list[dict[str, str]]:
        """Get porcelain status (v1) in one fast call.

        Args:
            repo_path: Absolute path to git repo.

        Returns:
            List of dicts with 'path' and 'status' keys.
        """
        try:
            cmd = ["git", "-C", repo_path, "status", "--porcelain=v1", "-u"]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            if res.returncode != 0:
                logger.warning(f"git status returned non-zero code {res.returncode}: {res.stderr}")
                return []

            results: list[dict[str, str]] = []
            seen: set[str] = set()

            for line in res.stdout.splitlines():
                if len(line) < 3:
                    continue
                index_code = line[0]
                work_code = line[1]
                path = line[3:].strip()
                try:
                    path_parts = shlex.split(path)
                except ValueError:
                    path_parts = [path]
                if "->" in path_parts:
                    path = path_parts[path_parts.index("->") + 1]
                elif path_parts:
                    path = (
                        path_parts[-1] if index_code == "R" or work_code == "R" else path_parts[0]
                    )

                status_code = "M"
                if index_code == "?" or work_code == "?":
                    status_code = "?"
                elif index_code == "A" or work_code == "A":
                    status_code = "A"
                elif index_code == "D" or work_code == "D":
                    status_code = "D"
                elif index_code == "R" or work_code == "R":
                    status_code = "R"

                if path and path not in seen:
                    seen.add(path)
                    results.append({"path": path, "status": status_code})

            return results
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to run git status: {e}")
            return []

    def diff_text(self, repo_path: str, path: str | None = None, staged: bool = False) -> str:
        """Get raw diff text string via subprocess.

        Args:
            repo_path: Absolute path to git repo.
            path: Optional relative path to specific file.
            staged: True for cached/staged diff.

        Returns:
            Diff output text.
        """
        cmd = ["git", "-C", repo_path, "diff", "-U3", "--no-color"]
        if staged:
            cmd.append("--cached")
        if path:
            cmd.extend(("--", path))

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            if res.returncode != 0:
                logger.warning("git diff returned non-zero code %s: %s", res.returncode, res.stderr)
                return ""
            return res.stdout
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to get git diff: {e}")
            return ""

    def diff_commits(self, repo_path: str, a: str, b: str) -> list[FileDiff]:
        """Get FileDiff list comparing two commits/refs.

        Args:
            repo_path: Absolute path to git repo.
            a: First commit/ref.
            b: Second commit/ref.

        Returns:
            List of FileDiff objects.
        """
        cmd = ["git", "-C", repo_path, "diff", "-U3", "--no-color", a, b]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            return DiffParser.parse_diff_text(res.stdout)
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to compare commits {a}..{b}: {e}")
            return []

    def log_stream(self, repo_path: str, n: int = 100) -> Iterator[CommitInfo]:
        """Stream commits from git log.

        Args:
            repo_path: Absolute path to git repo.
            n: Number of commits to fetch.

        Yields:
            CommitInfo objects.
        """
        if n <= 0:
            return
        cmd = [
            "git",
            "-C",
            repo_path,
            "log",
            f"-{n}",
            "--format=%H|%an|%ae|%at|%s",
            "--no-color",
        ]
        proc = None
        timed_out = False
        watchdog = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            def terminate_if_running() -> None:
                nonlocal timed_out
                if proc is not None and proc.poll() is None:
                    timed_out = True
                    with suppress(OSError):
                        proc.kill()

            watchdog = threading.Timer(self._timeout, terminate_if_running)
            watchdog.daemon = True
            watchdog.start()
            if proc.stdout:
                for line in proc.stdout:
                    parts = line.strip().split("|", 4)
                    if len(parts) == 5:
                        yield CommitInfo(
                            commit_hash=parts[0],
                            author_name=parts[1],
                            author_email=parts[2],
                            timestamp=int(parts[3]) if parts[3].isdigit() else 0,
                            message=parts[4],
                        )
            proc.wait(timeout=self._timeout)
            if timed_out:
                raise subprocess.TimeoutExpired(cmd, self._timeout)
            if proc.returncode:
                logger.warning("git log returned non-zero code %s", proc.returncode)
        except (OSError, subprocess.TimeoutExpired, ValueError) as e:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.communicate()
            logger.error(f"Failed to fetch git log stream: {e}")
        finally:
            if watchdog is not None:
                watchdog.cancel()
            if proc is not None and proc.stdout is not None:
                proc.stdout.close()
            if proc is not None and proc.poll() is None:
                proc.terminate()

    def get_branches(self, repo_path: str) -> list[BranchInfo]:
        """List local branches with current branch marked.

        Args:
            repo_path: Absolute path to git repo.

        Returns:
            List of BranchInfo objects.
        """
        cmd = ["git", "-C", repo_path, "branch", "--no-color", "-v"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            branches: list[BranchInfo] = []
            for line in res.stdout.splitlines():
                if not line:
                    continue
                is_current = line.startswith("*")
                content = line[2:].strip()
                parts = content.split(None, 2)
                if not parts:
                    continue
                branch_name = parts[0]
                last_commit = parts[1][:8] if len(parts) > 1 else ""

                branches.append(
                    BranchInfo(
                        name=branch_name,
                        is_current=is_current,
                        is_remote=False,
                        last_commit=last_commit,
                    )
                )
            return branches
        except (OSError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to get branches via CLI: {e}")
            return []
