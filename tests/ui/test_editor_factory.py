"""Tests for EditorViewFactory."""

from __future__ import annotations

from slate.ui.editor.editor_factory import EditorViewFactory


class TestEditorViewFactoryLanguageDetection:
    """Test language detection from file extensions."""

    def test_detect_python(self):
        """Should detect Python files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/file.py") == "python"

    def test_detect_javascript(self):
        """Should detect JavaScript files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/script.js") == "javascript"

    def test_detect_typescript(self):
        """Should detect TypeScript files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/app.ts") == "typescript"
        assert factory.detect_language("/path/to/app.tsx") == "typescript"

    def test_detect_rust(self):
        """Should detect Rust files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/main.rs") == "rust"

    def test_detect_html(self):
        """Should detect HTML files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/index.html") == "html"
        assert factory.detect_language("/path/to/index.htm") == "html"

    def test_detect_json(self):
        """Should detect JSON files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/config.json") == "json"

    def test_detect_markdown(self):
        """Should detect Markdown files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/readme.md") == "markdown"

    def test_detect_shell(self):
        """Should detect Shell script files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/script.sh") == "shell"
        assert factory.detect_language("/path/to/script.bash") == "shell"

    def test_detect_go(self):
        """Should detect Go files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/main.go") == "go"

    def test_detect_java(self):
        """Should detect Java files."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/Main.java") == "java"

    def test_empty_path_returns_none(self):
        """Empty path should return None."""
        factory = EditorViewFactory()
        assert factory.detect_language("") is None

    def test_no_extension_returns_none(self):
        """File with no extension should return None."""
        factory = EditorViewFactory()
        assert factory.detect_language("/path/to/Makefile") is None


class TestEditorViewFactorySingleton:
    """Test singleton pattern."""

    def test_same_instance_returned(self):
        """Factory should return same instance."""
        factory1 = EditorViewFactory()
        factory2 = EditorViewFactory()
        assert factory1 is factory2


class TestEditorViewFactoryBufferFallback:
    """Test buffer creation when language is unknown."""

    def test_unknown_language_falls_back_to_plain_buffer(self):
        factory = EditorViewFactory()
        buffer = factory.create_buffer("content", language_id="does-not-exist")

        assert buffer is not None
