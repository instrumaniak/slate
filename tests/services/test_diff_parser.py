"""Tests for DiffParser - unified diff streaming parser."""

from __future__ import annotations

from slate.services.diff_parser import DiffParser


class TestDiffParser:
    """Test DiffParser functionality."""

    def test_parse_empty_diff(self) -> None:
        """Empty diff text should return empty list."""
        assert DiffParser.parse_diff_text("") == []
        assert DiffParser.parse_diff_text("   ") == []

    def test_parse_single_file_diff(self) -> None:
        """Parse standard single-file unified diff."""
        sample_diff = """diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,3 @@
 line1
-old_line
+new_line
 line3
"""
        result = DiffParser.parse_diff_text(sample_diff)
        assert len(result) == 1
        file_diff = result[0]
        assert file_diff.old_path == "test.py"
        assert file_diff.new_path == "test.py"
        assert file_diff.status == "M"
        assert len(file_diff.hunks) == 1

        hunk = file_diff.hunks[0]
        assert hunk.old_start == 1
        assert hunk.old_count == 3
        assert hunk.new_start == 1
        assert hunk.new_count == 3
        assert hunk.lines == [" line1", "-old_line", "+new_line", " line3"]

    def test_parse_new_file_diff(self) -> None:
        """Parse diff for a newly added file."""
        sample_diff = """diff --git a/new.txt b/new.txt
new file mode 100644
--- /dev/null
+++ b/new.txt
@@ -0,0 +1,2 @@
+hello
+world
"""
        result = DiffParser.parse_diff_text(sample_diff)
        assert len(result) == 1
        file_diff = result[0]
        assert file_diff.old_path is None
        assert file_diff.new_path == "new.txt"
        assert file_diff.status == "A"
        assert len(file_diff.hunks) == 1
        assert file_diff.hunks[0].lines == ["+hello", "+world"]

    def test_parse_deleted_file_diff(self) -> None:
        """Parse diff for a deleted file."""
        sample_diff = """diff --git a/old.txt b/old.txt
deleted file mode 100644
--- a/old.txt
+++ /dev/null
@@ -1,2 +0,0 @@
-hello
-world
"""
        result = DiffParser.parse_diff_text(sample_diff)
        assert len(result) == 1
        file_diff = result[0]
        assert file_diff.old_path == "old.txt"
        assert file_diff.new_path == "old.txt"
        assert file_diff.status == "D"
        assert len(file_diff.hunks) == 1
        assert file_diff.hunks[0].lines == ["-hello", "-world"]

    def test_parse_binary_diff(self) -> None:
        """Parse binary diff header."""
        sample_diff = """diff --git a/image.png b/image.png
Binary files a/image.png and b/image.png differ
"""
        result = DiffParser.parse_diff_text(sample_diff)
        assert len(result) == 1
        file_diff = result[0]
        assert file_diff.is_binary is True

    def test_parse_quoted_rename_and_no_newline_marker(self) -> None:
        """Quoted paths and extended headers should survive parsing."""
        sample_diff = """diff --git "a/old name.py" "b/new name.py"
similarity index 90%
rename from old name.py
rename to new name.py
--- "a/old name.py"
+++ "b/new name.py"
@@ -0,0 +1,0 @@
\\ No newline at end of file
"""
        result = DiffParser.parse_diff_text(sample_diff)
        assert len(result) == 1
        assert result[0].old_path == "old name.py"
        assert result[0].new_path == "new name.py"
        assert result[0].status == "R"
        assert result[0].hunks[0].old_count == 0
        assert result[0].hunks[0].lines == ["\\ No newline at end of file"]
