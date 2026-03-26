from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("GtkSource", "5")
    from gi.repository import GtkSource

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    GtkSource = None


LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".json": "json",
    ".md": "markdown",
    ".sh": "shell",
    ".bash": "shell",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sql": "sql",
    ".php": "php",
    ".rb": "ruby",
    ".pl": "perl",
    ".lua": "lua",
}


class EditorViewFactory:
    """Factory for creating configured GtkSource.View instances."""

    _instance: "EditorViewFactory | None" = None

    def __new__(cls) -> "EditorViewFactory":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._language_manager = None
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance for testing."""
        cls._instance = None

    def _get_language_manager(self):
        """Lazy load the language manager."""
        if not GTK_AVAILABLE:
            return None

        if self._language_manager is None:
            self._language_manager = GtkSource.LanguageManager.get_default()
        return self._language_manager

    def detect_language(self, path: str) -> str | None:
        """Detect language from file path."""
        if not path:
            return None

        _, ext = os.path.splitext(path)
        ext = ext.lower()

        return LANGUAGE_MAP.get(ext)

    def create_buffer(self, content: str = "", language_id: str | None = None):
        """Create a configured source buffer."""
        if not GTK_AVAILABLE:
            return None

        if language_id:
            lang_manager = self._get_language_manager()
            language = lang_manager.get_language(language_id)
            buffer = GtkSource.Buffer.new_with_language(language)
        else:
            buffer = GtkSource.Buffer.new(None)

        if content:
            buffer.set_text(content)

        return buffer

    def apply_scheme(self, buffer, scheme: str) -> None:
        """Apply color scheme to buffer."""
        if not GTK_AVAILABLE:
            return

        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme_obj = style_manager.get_scheme(scheme)

        if scheme_obj:
            buffer.set_style_scheme(scheme_obj)
