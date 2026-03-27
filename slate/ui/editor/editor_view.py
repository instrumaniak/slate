from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("GtkSource", "5")
    from gi.repository import GtkSource, Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    GtkSource = Gtk = None


class EditorView(GtkSource.View if GTK_AVAILABLE else object):
    """Wrapper for syntax-highlighted editor view."""

    _gtk_available: bool = GTK_AVAILABLE

    def __init__(
        self,
        path: str,
        content: str,
        editor_scheme: str = "Adwaita",
        on_modified_changed: Callable[[bool], None] | None = None,
    ) -> None:
        """Initialize EditorView."""
        if not EditorView._gtk_available:
            logger.warning("GTK not available - EditorView is a placeholder")
            self._path = path
            self._content = content or ""
            self._buffer = None
            return

        self._on_modified_changed = on_modified_changed

        from slate.ui.editor.editor_factory import EditorViewFactory

        factory = EditorViewFactory()
        language_id = factory.detect_language(path)

        buffer = factory.create_buffer(content, language_id)
        super().__init__(buffer=buffer)

        buffer.connect("modified-changed", self._on_buffer_modified)
        factory.apply_scheme(buffer, editor_scheme)

        self._setup_basic_properties()

    def _on_buffer_modified(self, buffer) -> None:
        """Handle buffer modified state change."""
        if self._on_modified_changed:
            self._on_modified_changed(buffer.get_modified())

    def _setup_basic_properties(self) -> None:
        """Configure basic editor properties."""
        if not self._gtk_available:
            return

        self.set_show_line_numbers(True)
        self.set_highlight_current_line(True)
        self.set_auto_indent(True)
        if hasattr(self, "set_indent_width"):
            self.set_indent_width(4)
        if hasattr(self, "set_tab_width"):
            self.set_tab_width(4)
        if hasattr(self, "set_insert_spaces"):
            self.set_insert_spaces(True)
        if hasattr(self, "set_wrap_mode"):
            self.set_wrap_mode(Gtk.WrapMode.NONE)

    def get_content(self) -> str:
        """Get current editor content."""
        if not EditorView._gtk_available:
            return self._content

        buffer = self.get_buffer()
        return buffer.get_text(
            buffer.get_start_iter(),
            buffer.get_end_iter(),
            include_hidden_chars=True,
        )

    def set_content(self, content: str) -> None:
        """Set editor content."""
        self._content = content
        if not EditorView._gtk_available:
            return

        buffer = self.get_buffer()
        buffer.set_text(content)

    def get_language(self) -> str | None:
        """Get current buffer language ID."""
        if not EditorView._gtk_available:
            return None

        buffer = self.get_buffer()
        lang = buffer.get_language()
        if lang:
            return lang.get_id()
        return None

    def can_undo(self) -> bool:
        """Check if buffer can undo."""
        if not EditorView._gtk_available:
            return False

        return self.get_buffer().can_undo()

    def can_redo(self) -> bool:
        """Check if buffer can redo."""
        if not EditorView._gtk_available:
            return False

        return self.get_buffer().can_redo()

    def undo(self) -> None:
        """Perform undo on buffer."""
        if EditorView._gtk_available:
            self.get_buffer().undo()

    def redo(self) -> None:
        """Perform redo on buffer."""
        if EditorView._gtk_available:
            self.get_buffer().redo()

    def is_dirty(self) -> bool:
        """Check if buffer has unsaved changes."""
        if not EditorView._gtk_available:
            return False

        return self.get_buffer().get_modified()

    def mark_clean(self) -> None:
        """Mark buffer as having no unsaved changes."""
        if EditorView._gtk_available:
            self.get_buffer().set_modified(False)
