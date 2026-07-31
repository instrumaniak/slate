from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("GtkSource", "5")
    from gi.repository import Gtk, GtkSource, Pango

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    GtkSource = Gtk = Pango = None


DEFAULT_EDITOR_SETTINGS = {
    "font": "Monospace 13",
    "tab_width": "4",
    "insert_spaces": "true",
    "show_line_numbers": "true",
    "highlight_current_line": "true",
    "word_wrap": "false",
    "auto_indent": "true",
}


def _setting_bool(settings: Mapping[str, str], key: str, default: bool) -> bool:
    value = settings.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _setting_int(settings: Mapping[str, str], key: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(settings.get(key, str(default))))
    except (TypeError, ValueError):
        return default


def apply_editor_settings(view, settings: Mapping[str, str] | None = None) -> None:
    """Apply persisted editor settings to a GtkSource.View instance."""
    if not GTK_AVAILABLE:
        return

    resolved = dict(DEFAULT_EDITOR_SETTINGS)
    if settings:
        resolved.update(settings)

    view.set_show_line_numbers(_setting_bool(resolved, "show_line_numbers", True))
    view.set_highlight_current_line(_setting_bool(resolved, "highlight_current_line", True))
    view.set_auto_indent(_setting_bool(resolved, "auto_indent", True))
    view.set_indent_width(_setting_int(resolved, "tab_width", 4, 1))
    view.set_tab_width(_setting_int(resolved, "tab_width", 4, 1))
    view.set_insert_spaces_instead_of_tabs(_setting_bool(resolved, "insert_spaces", True))
    view.set_wrap_mode(
        Gtk.WrapMode.WORD if _setting_bool(resolved, "word_wrap", False) else Gtk.WrapMode.NONE
    )

    font_description = Pango.FontDescription.from_string(
        resolved.get("font", DEFAULT_EDITOR_SETTINGS["font"])
    )
    family = font_description.get_family() or "Monospace"
    size = font_description.get_size() / Pango.SCALE
    if size <= 0:
        size = 13
    escaped_family = family.replace("\\", "\\\\").replace('"', '\\"')
    css = f'textview {{ font-family: "{escaped_family}"; font-size: {size:g}pt; }}'
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    view.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    view._slate_font_css_provider = provider


class EditorView(GtkSource.View if GTK_AVAILABLE else object):
    """Wrapper for syntax-highlighted editor view."""

    _gtk_available: bool = GTK_AVAILABLE

    def __init__(
        self,
        path: str,
        content: str,
        editor_scheme: str = "Adwaita",
        on_modified_changed: Callable[[bool], None] | None = None,
        editor_settings: Mapping[str, str] | None = None,
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

        self._setup_basic_properties(editor_settings)

    def _on_buffer_modified(self, buffer) -> None:
        """Handle buffer modified state change."""
        if self._on_modified_changed:
            self._on_modified_changed(buffer.get_modified())

    def _setup_basic_properties(self, settings: Mapping[str, str] | None = None) -> None:
        """Configure basic editor properties."""
        if not self._gtk_available:
            return

        apply_editor_settings(self, settings)

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
