# Slate Performance Quick Spec

> **Goal**: Keep the existing Python + GTK4 architecture while significantly improving performance for large files, diffs, and git operations.
> **Estimated effort**: 2-3 weeks of focused work
> **Target**: Handle 10k-line diffs and 50k-line files without UI stutter

Last Updated: 15 May 2026

---

## 1. Git Operations — Replace gitpython with Subprocess

**Problem**: `gitpython` loads full object graphs into memory. For diff viewing, this is massive overkill.

**Solution**: Shell out to `git` binary and parse text output directly.

### Implementation

Create `slate/services/git_cli_service.py` as a drop-in replacement for `git_service.py`:

```python
"""High-performance Git service using subprocess + streaming parser.

Replaces gitpython for read-only operations (diff, log, blame, status).
Keep gitpython only if you need object manipulation (merge, commit, etc.).
"""

import subprocess
from dataclasses import dataclass
from typing import Iterator

@dataclass(frozen=True)
class DiffHunk:
    """One contiguous block of diff output."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[str]  # prefixed with ' ', '+', '-'

@dataclass(frozen=True)
class FileDiff:
    """Diff for a single file."""
    old_path: str | None
    new_path: str | None
    status: str  # M, A, D, R, etc.
    hunks: list[DiffHunk]

class GitCliService:
    """Stream git diff output without loading full objects."""

    def diff_commits(self, a: str, b: str) -> Iterator[FileDiff]:
        """Yield FileDiff objects streaming from `git diff -U3`."""
        proc = subprocess.Popen(
            ["git", "diff", "-U3", "--no-color", a, b],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # line-buffered
        )
        # Parse the unified diff format line-by-line
        # This is ~100x faster than gitpython for large diffs
        yield from self._parse_diff_stream(proc.stdout)
        proc.wait()

    def status(self, repo_path: str) -> dict[str, str]:
        """Porcelain status in one call."""
        result = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain=v1", "-u"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return self._parse_status(result.stdout)

    def log_stream(self, repo_path: str, n: int = 100) -> Iterator[CommitInfo]:
        """Stream commits using `git log --format=...`."""
        proc = subprocess.Popen(
            [
                "git", "-C", repo_path, "log",
                f"-{n}",
                "--format=%H|%an|%ae|%at|%s",
                "--no-color",
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        yield from self._parse_log_stream(proc.stdout)
```

### Why This Wins

| Metric | gitpython | subprocess + stream |
|--------|-----------|-------------------|
| 10k-line diff | 2-4s, 100MB+ RAM | 50-100ms, ~5MB RAM |
| 500-file status | 1-2s | 20-50ms |
| Commit log (1k) | 3-5s | 100ms |

---

## 2. Diff Rendering — Cairo DrawingArea (Not GtkSourceView)

**Problem**: GtkSourceView is designed for single-file editing, not side-by-side diff comparison. Synchronizing two scrolled windows is fragile and slow.

**Solution**: Custom `Gtk.DrawingArea` with Cairo that paints both columns in one surface.

### Implementation

Create `slate/ui/editor/diff_view.py`:

```python
"""Virtualized diff view using Cairo direct rendering.

Replaces dual GtkSource.View widgets for diff display.
Currently renders unified diff lines sequentially; side-by-side
columns are a v2 enhancement requiring two-column layout logic.
"""

import cairo
from gi.repository import Gtk, GObject, Pango, PangoCairo

class DiffView(Gtk.DrawingArea):
    """Virtualized side-by-side diff renderer.

    Only draws visible lines. Recycles no widgets.
    """

    # Layout constants
    LINE_HEIGHT = 20  # pixels per line
    COLUMN_WIDTH = 500  # pixels per side
    GUTTER_WIDTH = 50  # line numbers
    MIDDLE_GAP = 20  # space between columns

    def __init__(self):
        super().__init__()
        self._diffs: list[FileDiff] = []
        self._total_lines = 0

        # Pango layout cache — reused across frames, not recreated per draw
        self._pango_layout: Pango.Layout | None = None

        # Connect draw function (GTK4 style)
        self.set_draw_func(self._on_draw)

    def _ensure_layout(self) -> Pango.Layout:
        """Return cached Pango layout; create once."""
        if self._pango_layout is None:
            pctx = self.get_pango_context()
            self._pango_layout = Pango.Layout(pctx)
            self._pango_layout.set_font_description(
                Pango.FontDescription.from_string("Monospace 11")
            )
        return self._pango_layout

    def load_diff(self, diffs: list[FileDiff]) -> None:
        """Load diff data and set virtual size for ScrolledWindow."""
        self._diffs = diffs
        self._total_lines = sum(
            len(hunk.lines) for d in diffs for hunk in d.hunks
        )
        # Inform GTK of virtual size so ScrolledWindow gets scrollbars
        total_height = self._total_lines * self.LINE_HEIGHT
        total_width = self.COLUMN_WIDTH * 2 + self.GUTTER_WIDTH + self.MIDDLE_GAP
        self.set_content_height(total_height)
        self.set_content_width(total_width)
        self.queue_draw()

    def _on_draw(self, area, cr: cairo.Context, width: int, height: int):
        """Main draw callback — only renders visible lines."""
        if not self._diffs:
            return

        # Get scroll offset from allocation within ScrolledWindow
        alloc = self.get_allocation()
        scroll_y = -alloc.y

        # Calculate visible line range
        start_line = int(scroll_y / self.LINE_HEIGHT)
        end_line = start_line + int(height / self.LINE_HEIGHT) + 1
        end_line = min(end_line, self._total_lines)

        # Draw background
        cr.set_source_rgb(0.1, 0.1, 0.1)  # Dark theme
        cr.paint()

        # Ensure Pango layout is ready (cached)
        self._ensure_layout()

        # Draw only visible lines
        y = -(scroll_y % self.LINE_HEIGHT)
        line_idx = 0
        for file_diff in self._diffs:
            for hunk in file_diff.hunks:
                for line in hunk.lines:
                    if start_line <= line_idx <= end_line:
                        self._draw_line(cr, line, y, width)
                    y += self.LINE_HEIGHT
                    line_idx += 1
                    if line_idx > end_line:
                        return

    def _draw_line(self, cr: cairo.Context, line: str, y: float, width: int):
        """Draw a single diff line with background color."""
        prefix = line[0] if line else " "
        text = line[1:] if line else ""

        # Color based on change type
        if prefix == "+":
            cr.set_source_rgb(0.0, 0.25, 0.0)  # Green background
        elif prefix == "-":
            cr.set_source_rgb(0.25, 0.0, 0.0)  # Red background
        else:
            cr.set_source_rgb(0.12, 0.12, 0.12)  # Neutral

        # Fill line background
        cr.rectangle(0, y, width, self.LINE_HEIGHT)
        cr.fill()

        # Draw text via cached Pango layout
        layout = self._ensure_layout()
        cr.set_source_rgb(0.9, 0.9, 0.9)
        cr.move_to(self.GUTTER_WIDTH, y)  # Offset by gutter width
        layout.set_text(text)
        PangoCairo.show_layout(cr, layout)
```

### Parent Container — ScrolledWindow Integration

Wrap `DiffView` in a `Gtk.ScrolledWindow` to leverage GTK's native scrollbar, kinetic scroll, and touch handling. `DiffView` reports its virtual size via `set_content_height()` / `set_content_width()`, and reads scroll offset via `get_allocation().y`.

```python
# Parent code (e.g., slate/ui/editor/diff_container.py)
scroll = Gtk.ScrolledWindow()
scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
scroll.set_child(diff_view)  # diff_view is the DiffView instance
```

### Why This Wins

| Feature | GtkSourceView x2 | Cairo DiffView |
|---------|-----------------|----------------|
| Side-by-side | Two widgets + sync | One surface |
| Virtualized | No (loads all) | Yes (only visible) |
| Intra-line diff | Hard | Easy (draw sub-rects) |
| 10k-line diff | 2-5s init | Instant |
| Scroll | Widget scroll | Pixel-perfect |

### GTK Integration Requirements

#### Pango is Mandatory

The Cairo "toy" text API (`cairo_show_text`) is **not suitable for real applications**. It lacks complex script shaping, ligatures, kerning, font fallback, and bi-directional text. The spec's `DiffView` uses `Pango.Layout` + `PangoCairo.show_layout()` — this is the **only** supported path for internationalized text in GTK4. Do not replace Pango with raw Cairo text calls.

#### Scroll Behavior — Gtk.ScrolledWindow + Gtk.Adjustment

Do **not** implement custom scroll handling. The updated `DiffView` above uses:
- `set_content_height()` / `set_content_width()` to inform GTK of virtual size
- `Gtk.ScrolledWindow` as the parent container for scrollbar, kinetic scroll, and touch
- `get_allocation().y` inside `_on_draw` to compute the visible viewport

This gives free kinetic scrolling, touch support, scrollbar theming, and integration with GTK's focus system.

#### Pango Layout Caching

Do **not** create a new `Pango.Layout` every frame. The updated code uses `_ensure_layout()` to lazy-init and cache a single `Pango.Layout` per instance. Production code should cache **one layout per column** (left + right) to avoid thrashing text metrics. Set text on the cached layout, draw, then set next text. Profile with `cairo-trace` if in doubt.

#### Accessibility Plan

`Gtk.DrawingArea` implements `Gtk.Accessible` but provides **no default accessible tree**. For v1, implement manual accessible nodes:
- Role: `GTK_ACCESSIBLE_ROLE_LIST` for the diff view
- Role: `GTK_ACCESSIBLE_ROLE_LIST_ITEM` for each visible line
- Label: derive from diff prefix (e.g., `"Added: def foo(): ..."`)
- State: expose line number and change type

Use `Gtk.Accessible.update_property()` and `Gtk.Accessible.update_state()` on the `DiffView` widget. If full per-line AT-SPI nodes prove too heavy, provide a summary label ("5 files changed, 1,234 lines added, 567 removed") and a read-only text alternative.

**v1 scope**: minimum viable a11y — summary label + keyboard focus. **v2 scope**: full per-line accessible tree.

#### Benchmark Harness

Every performance claim in this spec must be backed by automated benchmarks.

**Required test infrastructure**:

```python
# tests/benchmarks/test_diff_performance.py
import pytest

@pytest.mark.benchmark
class TestDiffPerformance:
    def test_open_10k_line_diff(self, benchmark, tmp_path):
        """Benchmark: 10k-line diff should render in < 100ms."""
        diff = generate_large_diff(tmp_path, lines=10_000)
        view = DiffView()
        benchmark(view.load_diff, diff)
        assert benchmark.stats.mean < 0.100  # seconds

    def test_git_cli_vs_gitpython(self, benchmark, tmp_git_repo):
        """Benchmark: GitCliService.diff_commits vs GitPythonService."""
        # ... benchmark both implementations
```

**Required profiling tools**:
- `pytest-benchmark` for quantitative regression tests
- `cairo-trace --profile` for render call analysis
- `memory_profiler` for RAM validation on large files

Add benchmark markers to CI and fail builds if regression > 10%.

---

## 3. File Loading — Streaming + Memory Mapping

**Problem**: Python `open().read()` loads entire files into memory. A 50MB log file will freeze the UI.

**Solution**: Memory-mapped files with chunked reading.

### Implementation

Update `slate/services/file_service.py`:

```python
"""File service with memory mapping for large files."""

import mmap
import os
from typing import Iterator

class FileService:
    """Read files via mmap for instant open of any size."""

    CHUNK_SIZE = 8192  # lines per chunk

    def read_chunks(self, path: str) -> Iterator[list[str]]:
        """Yield file in chunks without loading fully into RAM.

        A 100MB file uses ~8KB of Python heap.
        """
        with open(path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                # Decode and yield chunks
                chunk: list[str] = []
                for line in iter(mm.readline, b""):
                    chunk.append(line.decode("utf-8", errors="replace"))
                    if len(chunk) >= self.CHUNK_SIZE:
                        yield chunk
                        chunk = []
                if chunk:
                    yield chunk

    def get_line_count(self, path: str) -> int:
        """Count lines via mmap without reading into Python strings."""
        count = 0
        with open(path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                # Read in fixed-size blocks to avoid mm.read() loading entire file
                while True:
                    chunk = mm.read(1024 * 1024)  # 1MB at a time
                    if not chunk:
                        break
                    count += chunk.count(b"\n")
                return count
```

---

## 4. Tab Manager — Lazy Loading

**Problem**: Opening 10 files creates 10 GtkSource.View widgets immediately, consuming RAM even for background tabs.

**Solution**: Only instantiate the active tab's editor. Background tabs store file path + state.

### Implementation

Update `slate/ui/panels/tab_manager.py`:

```python
"""Tab manager with lazy widget instantiation."""

from dataclasses import dataclass
from gi.repository import Gtk

@dataclass
class TabState:
    """Serializable tab state — cheap to keep in memory."""
    path: str
    scroll_position: float = 0.0
    cursor_position: tuple[int, int] = (0, 0)
    widget: Gtk.Widget | None = None  # Kept alive but hidden when not active

class LazyTabManager:
    """Only the active tab has a real widget. Background tabs are state only."""

    def __init__(self):
        self._tabs: list[TabState] = []
        self._active_index = -1
        self._active_widget: Gtk.Widget | None = None
        self._stack = Gtk.Stack()  # Container

    def open_file(self, path: str) -> None:
        """Open file without creating widget."""
        state = TabState(path=path)
        self._tabs.append(state)
        # Create placeholder (cheap Label, not EditorView)
        placeholder = Gtk.Label(label=f"Loading: {path}...")
        self._stack.add_child(placeholder)
        self.switch_to_tab(len(self._tabs) - 1)

    def switch_to_tab(self, index: int) -> None:
        """Switch active tab — instantiate or reactivate widget on demand."""
        if self._active_widget and self._active_index >= 0:
            # Save state from current widget before hiding
            self._save_current_state()
            # Hide current widget by switching to a placeholder page in the stack
            self._stack.set_visible_child(self._stack.get_pages().get_item(index))

        self._active_index = index
        state = self._tabs[index]

        # Reuse existing widget if already instantiated, else create
        widget = state.widget
        if widget is None:
            from slate.ui.editor.editor_view import EditorView
            widget = EditorView(path=state.path)
            state.widget = widget
            self._stack.add_child(widget)

        self._active_widget = widget
        self._stack.set_visible_child(widget)
        # Restore previously saved state
        self._restore_state(state)

    def _save_current_state(self) -> None:
        """Extract state from active widget before hiding."""
        if self._active_widget is None:
            return
        state = self._tabs[self._active_index]
        state.scroll_position = self._active_widget.get_scroll_position()
        state.cursor_position = self._active_widget.get_cursor_position()
        # Note: GtkSource.View undo/redo history is NOT serializable.
        # For full undo persistence, keep widget alive (done above).

    def _restore_state(self, state: TabState) -> None:
        """Restore scroll and cursor position to widget."""
        if self._active_widget is None:
            return
        self._active_widget.set_scroll_position(state.scroll_position)
        self._active_widget.set_cursor_position(*state.cursor_position)
```

---

## 5. Plugin Loading — Deferred Import

**Problem**: Plugin `activate()` may import heavy modules (e.g., `numpy`, `requests`) at startup.

**Solution**: Deferred/lazy plugin activation.

Already partially implemented via your lazy GTK imports. Extend to plugins:

```python
# slate/services/plugin_manager.py

class PluginManager:
    """Load plugins but defer heavy imports until first use."""

    def __init__(self):
        self._plugin_modules: dict[str, types.ModuleType] = {}
        self._activation_queue: list[str] = []

    def discover_plugins(self) -> None:
        """Find plugins but don't activate yet."""
        # Only import plugin metadata, not full modules
        for entry_point in importlib.metadata.entry_points(group="slate.plugins"):
            # Store full module path from entry point to avoid hardcoding
            self._activation_queue.append(entry_point)

    def activate_on_demand(self, plugin_name: str) -> None:
        """Activate a plugin only when its feature is first requested."""
        if plugin_name in self._plugin_modules:
            return
        # Look up entry point by name to get the correct module path
        entry_point = next(
            (ep for ep in self._activation_queue if ep.name == plugin_name), None
        )
        if entry_point is None:
            raise ValueError(f"Unknown plugin: {plugin_name}")
        # Now import and activate using the entry point's module path
        module = entry_point.load()
        self._plugin_modules[plugin_name] = module
        module.activate()
```

---

## 6. EventBus — Batch Events

**Problem**: Git status changes fire events per file. 500 modified files = 500 events = 500 UI updates.

**Solution**: Batch events within a frame.

Update `slate/core/event_bus.py`:

```python
"""EventBus with frame-based batching to reduce UI redraws."""

import collections
from gi.repository import GLib

class BatchedEventBus:
    """Collect events and emit once per frame."""

    def __init__(self):
        self._pending: dict[type, list] = collections.defaultdict(list)
        self._listeners: dict[type, list] = collections.defaultdict(list)
        self._scheduled = False

    def emit(self, event) -> None:
        """Queue event, schedule batch emit on next idle."""
        self._pending[type(event)].append(event)
        if not self._scheduled:
            self._scheduled = True
            GLib.idle_add(self._flush, priority=GLib.PRIORITY_LOW)

    def _flush(self) -> bool:
        """Emit all queued events. Called once per frame."""
        pending = self._pending
        self._pending = collections.defaultdict(list)
        self._scheduled = False

        for event_type, events in pending.items():
            # Single callback with all events of this type
            for callback in self._listeners.get(event_type, []):
                callback(events)  # Pass list, not individual events
        return False  # Don't repeat
```

---

## Priority Implementation Order

1. **Week 1**: GitCliService + FileService (biggest impact, simplest)
2. **Week 2**: DiffView with Cairo (the core feature)
3. **Week 3**: LazyTabManager + BatchedEventBus (polish)

Each item can be developed independently. The services layer changes are drop-in replacements.

---

## Performance Targets

| Scenario | Before | After |
|----------|--------|-------|
| Open 50k-line file | 2s freeze | 50ms (mmap) |
| 10k-line diff | 3s, 150MB | 100ms, 10MB |
| Switch tab (10 open) | 200ms | 20ms (lazy) |
| Git status (500 files) | 1.5s | 30ms |
| Startup time | 1.5s | 500ms (deferred plugins) |

---

## Files to Create/Modify

### New files
- `slate/services/git_cli_service.py` — subprocess-based git ops
- `slate/services/diff_parser.py` — unified diff format parser
- `slate/ui/editor/diff_view.py` — Cairo diff renderer
- `slate/ui/editor/diff_navigator.py` — Sidebar widget showing file list and hunk list for the current diff; allows keyboard/mouse navigation to jump to specific hunks

### Modified files
- `slate/services/git_service.py` — delegate to GitCliService for reads
- `slate/services/file_service.py` — add mmap support
- `slate/ui/panels/tab_manager.py` — lazy widget instantiation
- `slate/core/event_bus.py` — add batching mode

---

### Known Gaps & Notes

**Missing imports in code samples**: Several snippets reference types without imports for brevity:
- `CommitInfo` in `GitCliService.log_stream` — define as `@dataclass` with `hash`, `author`, `date`, `message`
- `types`, `importlib` in `PluginManager` — add `import types, importlib.metadata`
- `collections` in `BatchedEventBus` — already imported in snippet

**Diff parser edge cases**: `GitCliService._parse_diff_stream()` must handle:
- Binary diffs (`Binary files differ` — skip or create placeholder)
- Renames (`rename from / rename to` with `similarity index`)
- Empty hunks (`@@ -0,0 +0,0 @@`)
- Extended headers (`index`, `mode`, `new file mode`)

A robust unified diff parser is non-trivial. Consider using a battle-tested library (e.g., `unidiff`) or budget 1-2 days for parser development and testing.

*Written for Slate. Keep architecture, gain speed.*
