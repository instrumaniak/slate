from __future__ import annotations

import logging
from collections.abc import Callable, Mapping

import gi

gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GtkSource, Pango  # noqa: E402

logger = logging.getLogger(__name__)


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


def apply_css(provider: Gtk.CssProvider, css: str) -> None:
    """Load a CSS string into a Gtk.CssProvider.

    Uses load_from_data instead of load_from_string, which only exists in
    GTK >= 4.8.
    """
    # load_from_data is untyped in pygobject-stubs (Gtk.pyi:8884 FIXME)
    provider.load_from_data(css.encode("utf-8"))  # type: ignore[no-untyped-call]


def apply_editor_settings(view, settings: Mapping[str, str] | None = None) -> None:
    """Apply persisted editor settings to a GtkSource.View instance."""
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
    apply_css(provider, css)
    view.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    view._slate_font_css_provider = provider


class EditorView(GtkSource.View):
    """Wrapper for syntax-highlighted editor view."""

    def __init__(
        self,
        path: str,
        content: str,
        editor_scheme: str = "Adwaita",
        on_modified_changed: Callable[[bool], None] | None = None,
        editor_settings: Mapping[str, str] | None = None,
    ) -> None:
        """Initialize EditorView."""
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
        apply_editor_settings(self, settings)

    def get_content(self) -> str:
        """Get current editor content."""
        buffer = self.get_buffer()
        return str(
            buffer.get_text(
                buffer.get_start_iter(),
                buffer.get_end_iter(),
                include_hidden_chars=True,
            )
        )

    def set_content(self, content: str) -> None:
        """Set editor content."""
        self.get_buffer().set_text(content)

    def get_language(self) -> str | None:
        """Get current buffer language ID."""
        buffer = self.get_buffer()
        lang = buffer.get_language()
        if lang:
            return str(lang.get_id())
        return None

    def can_undo(self) -> bool:
        """Check if buffer can undo."""
        return bool(self.get_buffer().get_can_undo())

    def can_redo(self) -> bool:
        """Check if buffer can redo."""
        return bool(self.get_buffer().get_can_redo())

    def undo(self) -> None:
        """Perform undo on buffer."""
        self.get_buffer().undo()

    def redo(self) -> None:
        """Perform redo on buffer."""
        self.get_buffer().redo()

    def is_dirty(self) -> bool:
        """Check if buffer has unsaved changes."""
        return bool(self.get_buffer().get_modified())

    def mark_clean(self) -> None:
        """Mark buffer as having no unsaved changes."""
        self.get_buffer().set_modified(False)
