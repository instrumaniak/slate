"""DiffView - Inline diff viewer widget for Slate.

Displays git diffs with unified/split view modes, syntax highlighting,
and proper line number display.
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("GtkSource", "5")
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, GtkSource

    GTK_AVAILABLE = True
except (ImportError, ValueError):
    GTK_AVAILABLE = False
    Gtk = None
    GtkSource = None

ADDITION_BG_COLOR = "#2ea04320"
DELETION_BG_COLOR = "#f8514920"
CONTEXT_BG_COLOR = "#00000000"

VALID_VIEW_MODES = frozenset({"unified", "split"})
DEFAULT_VIEW_MODE = "unified"


class DiffLineType:
    """Diff line type enumeration."""

    ADDITION = "+"
    DELETION = "-"
    CONTEXT = " "
    HEADER = "@"


class ParsedDiffLine:
    """Represents a single parsed diff line."""

    def __init__(
        self,
        line_type: str,
        content: str,
        old_line_num: int | None = None,
        new_line_num: int | None = None,
    ) -> None:
        self.line_type = line_type
        self.content = content
        self.old_line_num = old_line_num
        self.new_line_num = new_line_num


class DiffParser:
    """Parses unified git diff format into structured data."""

    @staticmethod
    def parse(diff_text: str) -> list[ParsedDiffLine]:
        """Parse unified diff text into structured lines.

        Args:
            diff_text: Raw git diff output in unified format.

        Returns:
            List of ParsedDiffLine objects.
        """
        if not diff_text or not diff_text.strip():
            return []

        lines = diff_text.split("\n")
        parsed_lines: list[ParsedDiffLine] = []

        old_line: int | None = None
        new_line: int | None = None

        for line in lines:
            if not line:
                continue

            if line.startswith("@@"):
                match = re.search(r"@@ -(\d+),?\d* \+(\d+),?\d* @@", line)
                if match:
                    old_line = int(match.group(1))
                    new_line = int(match.group(2))
                parsed_lines.append(ParsedDiffLine(line_type=DiffLineType.HEADER, content=line))
            elif line.startswith("+") and not line.startswith("+++"):
                parsed_lines.append(
                    ParsedDiffLine(
                        line_type=DiffLineType.ADDITION,
                        content=line[1:],
                        old_line_num=None,
                        new_line_num=new_line,
                    )
                )
                if new_line is not None:
                    new_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                parsed_lines.append(
                    ParsedDiffLine(
                        line_type=DiffLineType.DELETION,
                        content=line[1:],
                        old_line_num=old_line,
                        new_line_num=None,
                    )
                )
                if old_line is not None:
                    old_line += 1
            elif line.startswith(" ") or (
                not line.startswith("\\") and not line.startswith("diff")
            ):
                if line.startswith(" "):
                    content = line[1:]
                else:
                    content = line

                if content:
                    parsed_lines.append(
                        ParsedDiffLine(
                            line_type=DiffLineType.CONTEXT,
                            content=content,
                            old_line_num=old_line,
                            new_line_num=new_line,
                        )
                    )
                    if old_line is not None:
                        old_line += 1
                    if new_line is not None:
                        new_line += 1

        return parsed_lines


class DiffView(Gtk.Box if GTK_AVAILABLE else object):
    """Widget for displaying git diffs with syntax highlighting.

    Supports unified (default) and split view modes with proper
    line numbers and addition/deletion highlighting.
    """

    _gtk_available: bool = GTK_AVAILABLE

    def __init__(
        self,
        diff_text: str = "",
        path: str = "",
        view_mode: str = "unified",
        on_view_mode_changed: Callable[[str], None] | None = None,
        config_service=None,
    ) -> None:
        """Initialize DiffView.

        Args:
            diff_text: Raw git diff output.
            path: File path being diffed.
            view_mode: Initial view mode - "unified" or "split".
            on_view_mode_changed: Optional callback when view mode changes.
            config_service: Optional ConfigService instance for persisting view mode preference.
        """
        if not DiffView._gtk_available:
            logger.warning("GTK not available - DiffView is a placeholder")
            self._path = path
            self._diff_text = diff_text
            self._view_mode = view_mode
            self._is_empty = not diff_text or not diff_text.strip()
            self._config_service = None
            return

        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self._path = path
        self._diff_text = diff_text if diff_text is not None else ""
        normalized_mode = view_mode.lower().strip() if view_mode else ""
        self._view_mode = (
            normalized_mode if normalized_mode in VALID_VIEW_MODES else DEFAULT_VIEW_MODE
        )
        self._on_view_mode_changed = on_view_mode_changed
        self._config_service = config_service
        self._is_empty = not self._diff_text or not self._diff_text.strip()

        self._parsed_lines: list[ParsedDiffLine] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget UI structure."""
        if not self._gtk_available:
            return

        header = self._create_header()
        self.append(header)

        self._content_scrolled = Gtk.ScrolledWindow()
        self._content_scrolled.set_hexpand(True)
        self._content_scrolled.set_vexpand(True)

        if self._view_mode == "split":
            self._setup_split_view()
        else:
            self._setup_unified_view()

        self.append(self._content_scrolled)

        footer = self._create_footer()
        self.append(footer)

    def _create_header(self) -> Gtk.Widget:
        """Create the header with view mode toggle."""
        if not self._gtk_available:
            return Gtk.Box()

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_margin_start(6)
        header.set_margin_end(6)
        header.set_margin_top(6)
        header.set_margin_bottom(6)

        label = Gtk.Label()
        label.set_text("Unified" if self._view_mode == "unified" else "Split")
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        header.append(label)

        toggle = Gtk.ToggleButton(
            label="Split View" if self._view_mode == "unified" else "Unified View"
        )
        toggle.set_active(self._view_mode == "split")
        toggle.connect("toggled", self._on_view_mode_toggled)
        header.append(toggle)

        return header

    def _create_footer(self) -> Gtk.Widget:
        """Create the footer with file path info."""
        if not self._gtk_available:
            return Gtk.Box()

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        footer.set_margin_start(6)
        footer.set_margin_end(6)
        footer.set_margin_top(4)
        footer.set_margin_bottom(4)

        label = Gtk.Label()
        label.set_text(f"~ {self._path} (diff)" if self._path else "No changes")
        label.set_hexpand(True)
        label.set_halign(Gtk.Align.START)
        footer.append(label)

        return footer

    def _setup_unified_view(self) -> None:
        """Set up unified diff view (single column with line numbers)."""
        if not self._gtk_available:
            return

        source_view = self._create_source_view()
        buffer = source_view.get_buffer()

        if self._is_empty:
            no_changes = "No changes" if not self._path else f"No changes in {self._path}"
            buffer.set_text(no_changes)
        else:
            self._parsed_lines = DiffParser.parse(self._diff_text)
            text = self._format_unified_text()
            buffer.set_text(text)

        self._apply_diff_highlighting(buffer)
        self._content_scrolled.set_child(source_view)

    def _setup_split_view(self) -> None:
        """Set up split diff view (side-by-side old and new)."""
        if not self._gtk_available:
            return

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_hexpand(True)
        paned.set_vexpand(True)

        old_view = self._create_source_view()
        new_view = self._create_source_view()

        if self._is_empty:
            no_changes = "No changes"
            old_view.get_buffer().set_text(no_changes)
            new_view.get_buffer().set_text(no_changes)
        else:
            self._parsed_lines = DiffParser.parse(self._diff_text)
            old_text, new_text = self._format_split_text()
            old_view.get_buffer().set_text(old_text)
            new_view.get_buffer().set_text(new_text)
            self._apply_diff_highlighting(old_view.get_buffer())
            self._apply_diff_highlighting(new_view.get_buffer())

        old_scroll = Gtk.ScrolledWindow()
        old_scroll.set_child(old_view)
        old_scroll.set_size_request(300, -1)

        new_scroll = Gtk.ScrolledWindow()
        new_scroll.set_child(new_view)
        new_scroll.set_size_request(300, -1)

        paned.append(old_scroll)
        paned.append(new_scroll)

        self._content_scrolled.set_child(paned)

    def _create_source_view(self) -> GtkSource.View:
        """Create a GtkSourceView configured for diff display."""
        if not self._gtk_available:
            return None

        view = GtkSource.View()
        view.set_show_line_numbers(True)
        view.set_monospace(True)
        view.set_editable(False)
        view.set_wrap_mode(Gtk.WrapMode.NONE)

        if hasattr(view, "set_tab_width"):
            view.set_tab_width(4)
        if hasattr(view, "set_indent_width"):
            view.set_indent_width(4)

        return view

    def _format_unified_text(self) -> str:
        """Format parsed diff lines for unified view."""
        lines: list[str] = []

        for parsed in self._parsed_lines:
            if parsed.line_type == DiffLineType.HEADER:
                lines.append(parsed.content)
            elif parsed.line_type == DiffLineType.ADDITION:
                old_num = ""
                new_num = str(parsed.new_line_num) if parsed.new_line_num else ""
                lines.append(f"{old_num:>4} {new_num:>4} +{parsed.content}")
            elif parsed.line_type == DiffLineType.DELETION:
                old_num = str(parsed.old_line_num) if parsed.old_line_num else ""
                new_num = ""
                lines.append(f"{old_num:>4} {new_num:>4} -{parsed.content}")
            elif parsed.line_type == DiffLineType.CONTEXT:
                old_num = str(parsed.old_line_num) if parsed.old_line_num else ""
                new_num = str(parsed.new_line_num) if parsed.new_line_num else ""
                lines.append(f"{old_num:>4} {new_num:>4} {parsed.content}")

        return "\n".join(lines)

    def _format_split_text(self) -> tuple[str, str]:
        """Format parsed diff lines for split view (old and new columns)."""
        old_lines: list[str] = []
        new_lines: list[str] = []

        for parsed in self._parsed_lines:
            if parsed.line_type == DiffLineType.HEADER:
                old_lines.append(parsed.content)
                new_lines.append(parsed.content)
            elif parsed.line_type == DiffLineType.ADDITION:
                old_lines.append("")
                new_lines.append(
                    f"{parsed.new_line_num}: +{parsed.content}"
                    if parsed.new_line_num
                    else f"+{parsed.content}"
                )
            elif parsed.line_type == DiffLineType.DELETION:
                old_lines.append(
                    f"{parsed.old_line_num}: -{parsed.content}"
                    if parsed.old_line_num
                    else f"-{parsed.content}"
                )
                new_lines.append("")
            elif parsed.line_type == DiffLineType.CONTEXT:
                old_num = str(parsed.old_line_num) if parsed.old_line_num else ""
                new_num = str(parsed.new_line_num) if parsed.new_line_num else ""
                old_lines.append(f"{old_num}: {parsed.content}")
                new_lines.append(f"{new_num}: {parsed.content}")

        return "\n".join(old_lines), "\n".join(new_lines)

    def _apply_diff_highlighting(self, buffer: GtkSource.Buffer) -> None:
        """Apply syntax highlighting for additions and deletions."""
        if not self._gtk_available:
            return

        try:
            lang_manager = GtkSource.LanguageManager.get_default()
            language = lang_manager.get_language("diff")
            if language:
                buffer.set_language(language)
        except Exception as e:
            logger.debug(f"Could not set diff language: {e}")

        tag_table = buffer.get_tag_table()

        if not tag_table.lookup("addition"):
            addition_tag = Gtk.TextTag.new("addition")
            addition_tag.set_property("background", ADDITION_BG_COLOR)
            tag_table.add(addition_tag)

        if not tag_table.lookup("deletion"):
            deletion_tag = Gtk.TextTag.new("deletion")
            deletion_tag.set_property("background", DELETION_BG_COLOR)
            tag_table.add(deletion_tag)

        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, include_hidden_chars=True)

        addition_pattern = re.compile(r"^\+.*$", re.MULTILINE)
        deletion_pattern = re.compile(r"^-.*$", re.MULTILINE)

        addition_tag = tag_table.lookup("addition")
        deletion_tag = tag_table.lookup("deletion")

        for match in addition_pattern.finditer(text):
            start_iter = buffer.get_iter_at_offset(match.start())
            end_iter = buffer.get_iter_at_offset(match.end())
            buffer.apply_tag(addition_tag, start_iter, end_iter)

        for match in deletion_pattern.finditer(text):
            start_iter = buffer.get_iter_at_offset(match.start())
            end_iter = buffer.get_iter_at_offset(match.end())
            buffer.apply_tag(deletion_tag, start_iter, end_iter)

    def _on_view_mode_toggled(self, toggle: Gtk.ToggleButton) -> None:
        """Handle view mode toggle button."""
        if not self._gtk_available:
            return

        new_mode = "split" if toggle.get_active() else "unified"
        if new_mode != self._view_mode:
            self._view_mode = new_mode
            toggle.set_label("Unified View" if new_mode == "split" else "Split View")

            self.foreach(lambda child: self.remove(child))
            self._setup_ui()

            if self._on_view_mode_changed:
                self._on_view_mode_changed(new_mode)

    def toggle_view_mode(self) -> None:
        """Toggle between unified and split view modes."""
        self._view_mode = "split" if self._view_mode == "unified" else "unified"

        if self._config_service is not None:
            try:
                self._config_service.set("diff_view", "view_mode", self._view_mode)
            except Exception as e:
                logger.warning(f"Failed to persist view mode preference: {e}")

        if self._gtk_available and hasattr(self, "foreach"):
            self.foreach(lambda child: self.remove(child))
            self._setup_ui()

            if self._on_view_mode_changed:
                self._on_view_mode_changed(self._view_mode)

    def _show_no_changes_message(self) -> bool:
        """Check if 'No changes' message should be shown."""
        return self._is_empty

    @property
    def view_mode(self) -> str:
        """Get current view mode."""
        return self._view_mode

    @property
    def path(self) -> str:
        """Get the file path being diffed."""
        return self._path

    def set_diff_text(self, diff_text: str) -> None:
        """Set new diff text to display.

        Args:
            diff_text: Raw git diff output.
        """
        self._diff_text = diff_text if diff_text is not None else ""
        self._is_empty = not self._diff_text or not self._diff_text.strip()

        if self._gtk_available:
            self.foreach(lambda child: self.remove(child))
            self._setup_ui()
