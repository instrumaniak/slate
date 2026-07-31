"""Opt-in bounded performance benchmarks.

Run separately with ``pytest tests/benchmarks --benchmark-only`` after installing
the optional pytest-benchmark dependency.
"""

from __future__ import annotations

import subprocess

import pytest

pytest.importorskip("pytest_benchmark")

from slate.services.diff_parser import DiffParser
from slate.services.file_service import FileService
from slate.services.git_cli_service import GitCliService


@pytest.mark.benchmark
@pytest.mark.timeout(60)
def test_parse_10k_line_diff(benchmark) -> None:
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,10000 +1,10000 @@\n" + (
        " context\n" * 10000
    )
    benchmark(DiffParser.parse_diff_text, diff)


@pytest.mark.benchmark
@pytest.mark.timeout(60)
def test_large_file_chunking(benchmark, tmp_path) -> None:
    path = tmp_path / "large.txt"
    path.write_text("line\n" * 10000)
    service = FileService()
    benchmark(lambda: list(service.read_chunks(str(path), chunk_size=1024)))


@pytest.mark.benchmark
@pytest.mark.timeout(60)
def test_git_cli_status(benchmark, tmp_path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    (tmp_path / "file.txt").write_text("content")
    service = GitCliService(timeout_seconds=5)
    benchmark(service.status, str(tmp_path))
