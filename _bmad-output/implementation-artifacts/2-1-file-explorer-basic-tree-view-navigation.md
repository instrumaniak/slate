# Story 2.1: File Explorer — Basic Tree View & Navigation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a file tree showing my project structure,
So that I can browse and open files without leaving the editor.

## Acceptance Criteria

1. **Given** FileExplorerPlugin is implemented **when** I activate the Explorer panel, a tree view shows the loaded folder
2. **And** folders expand/collapse with lazy loading — children are loaded only when a folder row is expanded, not during initial tree render
3. **And** clicking a file opens it in a new tab via OpenFileRequestedEvent
4. **And** the plugin registers via AbstractPlugin.activate() only — no internal imports
5. **And** panel icon uses "folder-symbolic" XDG icon
6. **And** keyboard shortcut Ctrl+Shift+O opens folder
 7. **And** breadcrumb bar shows current folder path with clickable segments for quick parent navigation
 8. **And** `.git` directory is excluded from the tree (git internals should not be browsed or modified via the editor)


## Tasks / Subtasks

- [x] Task 0: Verify and create required event classes (AC: 3)
  - [x] Subtask 0.1: Read `slate/core/events.py` — check if `OpenFileRequestedEvent(path: str)` exists
  - [x] Subtask 0.2: Read `slate/core/events.py` — check if `FolderOpenedEvent(path: str)` exists
  - [x] Subtask 0.3: If either is missing, add the dataclass to `slate/core/events.py`
- [x] Task 1: Implement FileExplorerPlugin skeleton (AC: 4, 5)
  - [x] Subtask 1.1: Create `slate/plugins/core/file_explorer.py` with AbstractPlugin subclass
  - [x] Subtask 1.2: Implement activate(context) — register panel factory, action, keybinding
  - [x] Subtask 1.3: Register panel with ID "file_explorer", icon "folder-symbolic", label "Explorer"
  - [x] Subtask 1.4: Register action "explorer.focus" and keybinding Ctrl+Shift+O
- [x] Task 2: Implement FileExplorerTree widget using modern GTK4 stack (AC: 1, 2, 8)
  - [x] Subtask 2.1: Create `slate/ui/panels/file_explorer_tree.py` with `Gtk.ListView` + `Gtk.TreeListModel` widget
  - [x] Subtask 2.2: Implement lazy-loading tree model — use `Gtk.TreeListModel` with a create-model callback that loads children only when a node is expanded
  - [x] Subtask 2.3: Use `Gio.File` for directory listing with file/folder type detection
  - [x] Subtask 2.4: Use `Gtk.TreeExpander` for expand/collapse rows with folder-open/folder icons via `Gio.content_type_get_icon`
  - [x] Subtask 2.5: Use `Gtk.SignalListItemFactory` to bind model data to row widgets
  - [x] Subtask 2.6: Exclude `.git` directory from tree — do not load or display `.git` entries in any folder

- [x] Task 3: Wire file opening via EventBus (AC: 3)
  - [x] Subtask 3.1: On file activation (double-click or Enter key), emit `OpenFileRequestedEvent(path)`
  - [x] Subtask 3.2: Subscribe to `FolderOpenedEvent` to reload tree when folder changes
  - [x] Subtask 3.3: Ensure TabManager handles `OpenFileRequestedEvent` (already implemented in Story 1.7)
- [x] Task 4: Implement breadcrumb navigation (AC: 7)
  - [x] Subtask 4.1: Add `Gtk.Box` with `Gtk.Label` segments separated by "›" at top of panel
  - [x] Subtask 4.2: Each segment is a flat `Gtk.Button` — clicking navigates to that parent directory
- [x] Task 5: Verify panel container supports new panel type (AC: 1)
  - [x] Subtask 5.1: Read `slate/ui/panels/panel_container.py` — verify it accepts a generic `Gtk.Widget`
  - [x] Subtask 5.2: Modify only if panel container expects a specific widget type (e.g., TreeView)
- [x] Task 6: Write tests (AC: 1-8)
  - [x] Subtask 6.1: Create `tests/plugins/test_file_explorer.py` — plugin activation test
  - [x] Subtask 6.2: Create `tests/ui/panels/test_file_explorer_tree.py` — tree widget tests
  - [x] Subtask 6.3: Test lazy loading: verify only expanded folder's contents are loaded
  - [x] Subtask 6.4: Test file click emits OpenFileRequestedEvent with correct path
  - [x] Subtask 6.5: Test FolderOpenedEvent triggers tree reload
  - [x] Subtask 6.6: Test plugin registration uses only public API (no internal imports)
  - [x] Subtask 6.7: Test `.git` directory is excluded from tree
  - [x] Subtask 6.8: Test clicking a folder row expands (does not emit OpenFileRequestedEvent)
  - [x] Subtask 6.9: Test breadcrumb segments are clickable and navigate to parent directory

## Dev Notes

### Relevant Architecture Patterns and Constraints

**Layer Architecture (STRICT):** This story touches Plugin layer (`slate/plugins/core/`) and UI layer (`slate/ui/panels/`). The plugin must NOT import from `slate/ui/` — it registers widget factories that the host shell calls at runtime. [Source: architecture.md#Layer Architecture, project-context.md#Critical Implementation Rules]

**Plugin Registration Pattern:**
- `activate(context)` must ONLY register actions/panels/dialogs via HostUIBridge
- Panel widgets are created LAZILY through registered factories — NOT during activate()
- Must NOT show windows, mutate tab state, or emit startup events during activation
- [Source: architecture.md#Plugin API Patterns, project-context.md#Plugin Registration Rules]

**Event Ownership:**
- FileExplorerPlugin emits `OpenFileRequestedEvent(path)` on file click
- TabManager (already implemented Story 1.7) handles the event and creates the tab
- Subscribe to `FolderOpenedEvent` to reload tree when folder changes
- [Source: architecture.md#Event System Patterns, project-context.md#Event Ownership Rules]

**Service Access:**
- Use `context.get_service("file")` to access FileService for directory listing
- Never hold direct references to other plugin objects
- [Source: architecture.md#Service Boundaries, project-context.md#Plugin Communication Rules]

### Previous Story Intelligence

**From Story 1.9 (Development Tooling & CI):**
- 267 tests passing, coverage at 86.42%
- CI active on push/PR to main and develop
- Ruff, mypy, pytest all configured
- Makefile targets: lint, typecheck, test, format

**From Story 1.8 (CLI Entry Point & Startup Sequence):**
- CLI path passed via `SLATE_CLI_PATH` environment variable
- Startup sequence: config → theme → window → plugins → restore → resolve CLI → present
- Plugins activate after window created

**From Story 1.7 (Tab Manager & Save/Discard Guard):**
- TabManager handles `OpenFileRequestedEvent` and creates editor tabs
- `FileService` registered with ID `"file"` provides file operations
- `ConfigService` handles config persistence at `~/.config/slate/config.ini`
- EventBus subscription pattern works for component communication

**Files Established in Previous Stories:**
- `slate/core/plugin_api.py` — AbstractPlugin, PluginContext, HostUIBridge
- `slate/core/events.py` — Event dataclasses (FileOpenedEvent, FileSavedEvent, etc.)
- `slate/core/event_bus.py` — EventBus with subscribe/emit/unsubscribe
- `slate/services/file_service.py` — FileService with list_directory, read_file, etc.
- `slate/services/plugin_manager.py` — PluginManager with ID caching
- `slate/ui/editor/tab_manager.py` — TabManager (handles OpenFileRequestedEvent)
- `slate/ui/actions.py` — Gio.SimpleAction registration for shortcuts
- `slate/ui/app.py` — SlateApplication composition root

**Lessons Learned:**
- GTK4 imports require special handling in mypy (gi.repository stubs)
- Lazy imports in service layer complicate type checking
- EventBus-driven architecture works well for decoupled communication
- Plugin activation failure must be caught and logged, app continues

### Source Tree Components to Touch

**Files to Create:**
- `slate/plugins/core/file_explorer.py` — FileExplorerPlugin (AbstractPlugin implementation)
- `slate/ui/panels/file_explorer_tree.py` — FileExplorerTree widget (Gtk.ListView + Gtk.TreeListModel wrapper)
- `tests/plugins/test_file_explorer.py` — Plugin activation and registration tests
- `tests/ui/panels/test_file_explorer_tree.py` — Tree widget tests

**Files to Modify:**
- `slate/core/events.py` — Add `OpenFileRequestedEvent` and/or `FolderOpenedEvent` if not present
- `slate/ui/panels/panel_container.py` — Verify/may need update to accept new panel widget type

**Existing Files to Reference (read-only):**
- `slate/core/plugin_api.py` — AbstractPlugin interface
- `slate/services/file_service.py` — FileService.list_directory() for tree data
- `slate/ui/editor/tab_manager.py` — OpenFileRequestedEvent handler

### Testing Standards Summary

**Coverage Requirements:**
- Plugin logic (non-widget): **85%+** line coverage
- UI layer: smoke/integration tests only — don't chase superficial percentage

**Test Patterns:**
- No GTK initialization for plugin logic tests
- Use temp directories for tree widget tests
- Prefer real file operations over excessive mocking
- Every feature needs: normal path, failure path, one regression-prone edge case

**Test Commands:**
- `pytest tests/` — Run all tests
- `pytest tests/plugins/test_file_explorer.py -v` — Run plugin tests
- `pytest tests/ --cov=slate --cov-report=term-missing` — Run with coverage

### Project Structure Notes

**Alignment with unified project structure:**
- Plugin lives in `slate/plugins/core/file_explorer.py` (matches architecture spec)
- UI widget lives in `slate/ui/panels/file_explorer_tree.py` (matches architecture spec)
- Tests mirror source: `tests/plugins/` and `tests/ui/panels/`
- Plugin ID: `"file_explorer"` (snake_case per naming convention)
- Panel icon: `"folder-symbolic"` (XDG symbolic icon per UX spec)

**Directory structure to establish:**
```
slate/
├── plugins/
│   └── core/
│       └── file_explorer.py          # CREATE
├── ui/
│   └── panels/
│       ├── panel_container.py        # verify/may modify
│       └── file_explorer_tree.py     # CREATE (ListView + TreeListModel)
tests/
├── plugins/
│   └── test_file_explorer.py         # CREATE
└── ui/
    └── panels/
        └── test_file_explorer_tree.py # CREATE
```

### References

- **Epic 2 Definition:** `_bmad-output/planning-artifacts/epics.md#Story 2.1: File Explorer — Basic Tree View & Navigation`
- **Architecture Layer Rules:** `_bmad-output/planning-artifacts/architecture.md#Layer Architecture (Section 3.1) — MANDATORY`
- **Architecture Plugin Patterns:** `_bmad-output/planning-artifacts/architecture.md#Plugin API Patterns (Section 3.2)`
- **Architecture Event Patterns:** `_bmad-output/planning-artifacts/architecture.md#Event System Patterns (Section 3.4)`
- **Architecture Project Structure:** `_bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure`
- **UX Activity Bar:** `_bmad-output/planning-artifacts/ux-design-specification.md#1. Activity Bar`
- **UX File Explorer Tree:** `_bmad-output/planning-artifacts/ux-design-specification.md#3. File Explorer Tree`
- **Project Context Rules:** `_bmad-output/project-context.md`
- **PRD Requirements:** `_bmad-output/planning-artifacts/prd.md#File Operations`
- **Previous Story 1.9:** `_bmad-output/implementation-artifacts/1-9-development-tooling-ci.md`
- **Previous Story 1.8:** `_bmad-output/implementation-artifacts/1-8-cli-entry-point-startup-sequence.md`
- **Previous Story 1.7:** `_bmad-output/implementation-artifacts/1-7-tab-manager-save-discard-guard.md`

## Developer Context Section

### Critical Implementation Guardrails

**ANTI-PATTERNS TO AVOID:**
- ❌ Never scan entire directory tree on plugin activation — lazy load only
- ❌ Never import from `slate/ui/` inside the plugin file
- ❌ Never emit `FileOpenedEvent` directly — emit `OpenFileRequestedEvent` and let TabManager handle it
- ❌ Never show the panel widget during `activate()` — register a factory only
- ❌ Never use `os.walk` for directory listing — use `Gio.File` or `FileService.list_directory()`
- ❌ Never hold direct reference to TabManager — communicate via EventBus only
- ❌ Never use `Gtk.TreeView` or `Gtk.TreeStore` — deprecated since GTK 4.10, removed in GTK 5
- ✅ Always use `Gtk.ListView` + `Gtk.TreeListModel` + `Gtk.TreeExpander` for tree display
- ✅ Always use `context.get_service("file")` for file operations
- ✅ Always register via `AbstractPlugin.activate()` only
- ✅ Always use XDG icon "folder-symbolic" for the panel

**PERFORMANCE REQUIREMENTS:**
- Tree expansion must be instant (<100ms) — lazy load only the expanded folder
- Do NOT recursively scan subdirectories on initial load
- Use `Gio.content_type_get_icon` for file/folder icons (matches system theme)
- Panel widget creation is LAZY — only when user clicks the explorer icon

**EVENT FLOW:**
```
User clicks file in tree
  → FileExplorerPlugin emits OpenFileRequestedEvent(path)
  → TabManager receives event (already implemented)
  → TabManager creates new editor tab
  → TabManager emits FileOpenedEvent(path)
  → Other components can subscribe to FileOpenedEvent
```

**PLUGIN ACTIVATION FLOW:**
```
SlateApplication.do_activate()
  → PluginManager.activate_plugin(file_explorer)
  → FileExplorerPlugin.activate(context)
    → context.get_service("file") → stores service reference
    → host_bridge.register_panel("file_explorer", factory_callback)
    → host_bridge.register_action("explorer.focus", callback)
    → host_bridge.register_keybinding("<Primary><Shift>O", "explorer.focus")
  → Returns (no UI shown yet)
```

### Technical Requirements Deep Dive

**FileExplorerPlugin Structure:**
```python
# slate/plugins/core/file_explorer.py
from slate.core.plugin_api import AbstractPlugin, PluginContext, HostUIBridge

class FileExplorerPlugin(AbstractPlugin):
    """Registers the file explorer panel with the host application."""
    
    @property
    def plugin_id(self) -> str:
        return "file_explorer"
    
    def activate(self, context: PluginContext) -> None:
        self._context = context
        self._file_service = context.get_service("file")
        bridge = context.host_bridge
        
        # Register panel factory (widget created lazily)
        bridge.register_panel(
            panel_id="file_explorer",
            icon_name="folder-symbolic",
            label="Explorer",
            factory=self._create_panel,
        )
        
        # Register action and keybinding
        bridge.register_action("explorer.focus", self._focus_panel)
        bridge.register_keybinding("<Primary><Shift>O", "explorer.focus")
    
    def _create_panel(self) -> Gtk.Widget:
        from slate.ui.panels.file_explorer_tree import FileExplorerTree
        return FileExplorerTree(file_service=self._file_service, event_bus=self._context.event_bus)
    
    def _focus_panel(self) -> None:
        # Host shell handles panel focus via registered action
        pass
```

**FileExplorerTree Widget Structure:**
```python
# slate/ui/panels/file_explorer_tree.py
from __future__ import annotations

from gi.repository import Gtk, Gio, GObject

from slate.core.events import OpenFileRequestedEvent, FolderOpenedEvent


class FileTreeItem(GObject.Object):
    """Wrapper for tree node data used by Gtk.TreeListModel."""
    
    def __init__(self, name: str, path: str, is_folder: bool) -> None:
        super().__init__()
        self.name = name
        self.path = path
        self.is_folder = is_folder


class FileExplorerTree(Gtk.Box):
    """Tree view widget for browsing project files with lazy loading.

    Uses Gtk.ListView + Gtk.TreeListModel (modern GTK4 stack).
    Gtk.TreeView is deprecated since GTK 4.10.
    """

    def __init__(self, file_service, event_bus) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._file_service = file_service
        self._event_bus = event_bus

        # Breadcrumb bar at top
        self._build_breadcrumb()

        # Build tree model with lazy child loading
        root_model = self._create_list_model_for_dir(None)
        self._tree_model = Gtk.TreeListModel.new(
            root_model,
            passthrough=False,
            autoexpand=False,
            create_model_func=self._on_create_child_model,
        )

        # Selection model
        self._selection = Gtk.SingleSelection.new(self._tree_model)

        # List view with tree expander
        self._list_view = Gtk.ListView.new(self._selection)
        self._list_view.set_factory(self._create_factory())
        self._list_view.connect("activate", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(self._list_view)
        self.append(scrolled)

        # Subscribe to folder change events
        self._event_bus.subscribe(FolderOpenedEvent, self._on_folder_changed)

    def load_folder(self, path: str) -> None:
        """Load the root folder into the tree."""
        ...

    def _on_create_child_model(self, item: FileTreeItem) -> Gio.ListModel | None:
        """Create child model lazily when a folder row is expanded."""
        if not item.is_folder:
            return None
        return self._create_list_model_for_dir(item.path)

    def _create_list_model_for_dir(self, dir_path: str | None) -> Gio.ListStore:
        """Create a ListStore with items from a directory."""
        store = Gio.ListStore.new(FileTreeItem)
        entries = self._file_service.list_directory(dir_path) if dir_path else []
        for entry in entries:
            if entry["name"] == ".git":
                continue
            store.append(FileTreeItem(
                name=entry["name"],
                path=entry["path"],
                is_folder=entry["is_dir"],
            ))
        return store

    def _create_factory(self) -> Gtk.SignalListItemFactory:
        """Create factory that binds tree items to row widgets."""
        factory = Gtk.SignalListItemFactory()

        def setup(factory, list_item):
            box = Gtk.Box(spacing=6)
            expander = Gtk.TreeExpander()
            icon = Gtk.Image()
            label = Gtk.Label(xalign=0)
            box.append(icon)
            box.append(label)
            expander.set_child(box)
            list_item.set_child(expander)

        def bind(factory, list_item):
            expander = list_item.get_child()
            row = list_item.get_item()
            expander.set_list_row(row)
            item = row.get_item()
            box = expander.get_child()
            icon = box.get_first_child()
            label = icon.get_next_sibling()
            if item.is_folder:
                icon.set_from_icon_name("folder-symbolic")
            else:
                gicon = Gio.content_type_get_icon(Gio.content_type_guess(item.name, None)[0])
                icon.set_from_gicon(gicon)
            label.set_text(item.name)

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        return factory

    def _on_row_activated(self, list_view, position) -> None:
        """Handle file activation — open file, expand folder."""
        item = self._selection.get_selected_item()
        if item is None:
            return
        tree_item = item.get_item()
        if not tree_item.is_folder:
            self._event_bus.emit(OpenFileRequestedEvent(path=tree_item.path))

    def _on_folder_changed(self, event: FolderOpenedEvent) -> None:
        """Reload tree root when folder changes."""
        ...
```

**Event Classes (verify these exist in core/events.py):**
- `OpenFileRequestedEvent(path: str)` — Request to open a file (emitted by plugins/UI)
- `FolderOpenedEvent(path: str)` — Notification that a folder was opened
- `FileOpenedEvent(path: str)` — Notification that a file tab was created (emitted by TabManager)

If `OpenFileRequestedEvent` or `FolderOpenedEvent` don't exist, add them to `slate/core/events.py`.

**Breadcrumb Pattern:**
- Use `Gtk.Box` with `Gtk.Label` segments separated by `Gtk.Separator` or "›" character
- Each segment is a `Gtk.Button` (flat/appearance-only) for click-to-navigate
- Shows current folder path: `home › raziur › projects › slate`

### Architecture Compliance Checklist

- [ ] FileExplorerPlugin extends AbstractPlugin
- [ ] activate() only registers — no UI shown, no windows mutated
- [ ] Panel widget created lazily via factory callback
- [ ] Panel icon uses "folder-symbolic" XDG icon
- [ ] Action "explorer.focus" registered with keybinding Ctrl+Shift+O
- [ ] Tree view uses Gtk.ListView + Gtk.TreeListModel — NO Gtk.TreeView or Gtk.TreeStore
- [ ] Lazy loading via TreeListModel create_model_func — no recursive directory scan
- [ ] File click emits OpenFileRequestedEvent (not FileOpenedEvent)
- [ ] `.git` directory excluded from tree
- [ ] Plugin uses context.get_service("file") — no direct FileService import
- [ ] Plugin file has zero imports from slate/ui/
- [ ] Breadcrumb shows current folder path with clickable segments
- [ ] OpenFileRequestedEvent and FolderOpenedEvent exist in core/events.py
- [ ] Tests cover: normal path, failure path, edge case
- [ ] Plugin tests achieve 85%+ coverage (non-widget logic)

### Library/Framework Requirements

- **PyGObject >= 3.42** — GTK4 bindings (installed: 3.42.1)
- **Gtk >= 4.6** — GTK4 toolkit (installed: 4.6.9)
- **Gtk.ListView** — Replaces deprecated Gtk.TreeView for list/tree display (GTK4 modern API)
- **Gtk.TreeListModel** — Hierarchical data model with built-in lazy child loading support
- **Gtk.TreeExpander** — Row widget providing expand/collapse for TreeListModel nodes
- **Gtk.SignalListItemFactory** — Factory for creating/binding row widgets to model items
- **Gio.File** — Directory listing and file type detection
- **Gio.content_type_get_icon** — System-themed file/folder icons

**Note:** `Gtk.TreeView` and `Gtk.TreeStore` are deprecated since GTK 4.10 and will be removed in GTK 5. This story uses the modern `ListView` + `TreeListModel` stack to avoid future migration cost. Both stacks are available on the current system (GTK 4.6.9).

### File Structure Requirements

```
slate/
├── core/
│   └── events.py                     # verify/add OpenFileRequestedEvent, FolderOpenedEvent
├── plugins/
│   └── core/
│       └── file_explorer.py          # CREATE — FileExplorerPlugin
├── ui/
│   └── panels/
│       ├── panel_container.py        # verify/update if needed
│       └── file_explorer_tree.py     # CREATE — FileExplorerTree widget (ListView + TreeListModel)
tests/
├── plugins/
│   └── test_file_explorer.py         # CREATE — Plugin tests
└── ui/
    └── panels/
        └── test_file_explorer_tree.py # CREATE — Widget tests
```

### Testing Requirements

**New Tests to Create:**

**Plugin Tests (`tests/plugins/test_file_explorer.py`):**
- `test_activate_registers_panel` — verify panel factory registered with correct ID/icon
- `test_activate_registers_action` — verify "explorer.focus" action registered
- `test_activate_registers_keybinding` — verify Ctrl+Shift+O bound to action
- `test_activate_uses_public_api_only` — code inspection: no imports from slate/ui/
- `test_activate_gets_file_service` — verify context.get_service("file") called
- `test_panel_factory_creates_widget` — verify factory returns FileExplorerTree instance

**Widget Tests (`tests/ui/panels/test_file_explorer_tree.py`):**
- `test_load_folder_populates_tree` — verify tree shows folder contents
- `test_lazy_loading_on_expand` — verify children loaded only on expand (TreeListModel callback)
- `test_file_click_emits_open_request` — verify OpenFileRequestedEvent emitted with correct path
- `test_folder_opened_event_reloads_tree` — verify tree reloads on FolderOpenedEvent
- `test_breadcrumb_shows_current_path` — verify breadcrumb displays folder path
- `test_breadcrumb_segments_clickable` — verify clicking a segment navigates to parent directory
- `test_missing_directory_shows_empty_state` — verify graceful handling of missing path
- `test_folder_row_does_not_emit_open_request` — clicking folder row expands, does not emit OpenFileRequestedEvent
- `test_git_directory_excluded` — verify `.git` directory is not shown in tree at any level

**Edge Cases:**
- `test_symlink_handling` — symlinks shown with appropriate icon
- `test_empty_directory_shows_no_children` — expanding empty folder shows nothing
- `test_deeply_nested_lazy_loading` — verify multi-level nesting loads correctly without full scan

### Git Intelligence

**Recent Work Patterns (from Epic 1 completion):**
- All Epic 1 stories (1.1-1.9) are complete and done
- 267 tests passing with established test patterns
- Plugin architecture proven with existing plugin skeleton
- EventBus communication pattern established and working
- FileService already implemented with list_directory capability

**Code Patterns Established:**
- One class per file for services and plugins
- Type hints on all public methods
- Docstrings on all public classes and methods
- `from __future__ import annotations` for forward references
- Tests use temp directories and real git repos over mocking

---

## Dev Agent Record

### Agent Model Used

opencode/mimo-v2-pro-free

### Debug Log References

### Completion Notes List

- Added `FolderOpenedEvent` to `slate/core/events.py` (was missing, needed for folder change notifications)
- `OpenFileRequestedEvent` already existed in events.py
- `Gtk.TreeListModel.new()` uses `create_func` keyword (not `create_model_func`) on GTK 4.6.9
- `Gtk.Button.set_flat()` not available on GTK 4.6.9 — used CSS class "flat" instead
- Panel container is a generic `Gtk.Box` — accepts any `Gtk.Widget`, no modification needed
- Plugin uses `EventBus()` singleton directly (no `event_bus` property on `PluginContext`)
- `HostUIBridge.register_action()` supports `shortcut` parameter — keybinding registered directly
- All 289 tests pass (267 existing + 22 new)

### File List

- `slate/core/events.py` — Added `FolderOpenedEvent` dataclass
- `slate/plugins/core/file_explorer.py` — Created: `FileExplorerPlugin` (AbstractPlugin)
- `slate/ui/panels/__init__.py` — Created: empty init for panels package
- `slate/ui/panels/file_explorer_tree.py` — Created: `FileExplorerTree` widget (ListView + TreeListModel)
- `tests/plugins/__init__.py` — Created: empty init
- `tests/plugins/test_file_explorer.py` — Created: 9 plugin tests
- `tests/ui/panels/__init__.py` — Created: empty init
- `tests/ui/panels/test_file_explorer_tree.py` — Created: 13 widget tests
- `tests/core/test_events.py` — Added: 2 FolderOpenedEvent tests

---

## Change Log

- **Date: 2026-04-01** - Story 2.1 corrected after review
  - Replaced deprecated Gtk.TreeView/TreeStore with modern Gtk.ListView + Gtk.TreeListModel + Gtk.TreeExpander
  - Added AC 8: `.git` directory excluded from tree (industry standard: VS Code, Sublime, Zed, JetBrains all hide it)
  - Clarified AC 2: lazy loading means children loaded only on expand, not during initial render
  - Clarified AC 7: breadcrumb segments are clickable for parent navigation
  - Added Task 0: verify/create OpenFileRequestedEvent and FolderOpenedEvent in core/events.py
  - Added Task 5: verify panel_container.py supports new widget type
  - Added Task 6 (renamed from 5): expanded test coverage for new widget stack, breadcrumbs, .git exclusion
  - Updated Library Requirements to document modern GTK4 widget stack
  - Updated anti-patterns: added prohibition on deprecated TreeView/TreeStore
  - Updated FileExplorerTree code example to use ListView + TreeListModel + TreeExpander
  - System verification: GTK 4.6.9, PyGObject 3.42.1 — modern stack available
- **Date: 2026-04-01** - Story 2.1 context created (original)
  - Comprehensive implementation guide for File Explorer Basic Tree View & Navigation
  - Builds on Epic 1 foundation (all stories 1.1-1.9 complete)
  - Includes plugin registration, lazy-loading tree, EventBus integration, breadcrumb navigation
  - First story in Epic 2 (File Explorer & Project Navigation)
