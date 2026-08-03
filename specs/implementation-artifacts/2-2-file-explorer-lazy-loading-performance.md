# Story 2.2: File Explorer — Lazy Loading & Performance

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want the file tree to load folders lazily without scanning the entire project,
So that large projects open instantly without lag.

## Acceptance Criteria

1. **Given** the file tree is loaded, **when** I expand a folder, only that folder's contents are loaded (no recursive scan) — already implemented in Story 2.1, must be verified
2. **And** expanding 100+ subfolders does not cause perceptible lag (<100ms per folder on standard development hardware: 4+ CPU cores, SSD storage) — performance test required
3. **And** file/folder icons match the system GTK theme (via `Gio.content_type_get_icon`) — already implemented in Story 2.1, must be verified
4. **And** the explorer re-loads when `FolderOpenedEvent` is emitted — already implemented in Story 2.1, must be verified
5. **And** hidden files (dot-prefixed, e.g. `.env`, `.gitignore`) are hidden by default; toggle available in panel header menu via `Gtk.PopoverMenu`

**AC 5 Visual Specifications:**
- **Toggle appearance**: Checkmark icon (✓) when hidden files are shown, no icon when hidden
- **Menu label**: "Show Hidden Files" (static text, icon indicates state)
- **Default state**: Toggle OFF (hidden files NOT shown), no checkmark icon
- **Active state**: Toggle ON (hidden files shown), checkmark icon displayed
- **Animation**: None required (instant toggle)
- **Visual feedback**: Tree reloads immediately when toggle clicked (progress indicator optional)

## Tasks / Subtasks

- [x] Task 1: Verify existing lazy loading implementation (AC: 1, 3, 4)
  - [x] Subtask 1.1: Read `slate/ui/panels/file_explorer_tree.py` — verify `_on_create_child_model` only loads children on expand (not recursive)
    - [x] **Verification**: Lazy loading verified: Only loads on expand [PASS]
  - [x] Subtask 1.2: Verify `Gio.content_type_get_icon` is used for file icons (not hardcoded icon names)
    - [x] **Verification**: Icons verified: Uses system theme [PASS]
  - [x] Subtask 1.3: Verify `FolderOpenedEvent` subscription triggers `load_folder()` reload
    - [x] **Verification**: Event subscription verified: Reloads on FolderOpenedEvent [PASS]
  - [x] Subtask 1.4: If any of the above are broken, **create bug tickets rather than fixing in this story** — this story is for verification and new functionality only

- [x] Task 2: Implement hidden files toggle (AC: 5)
  - [x] Subtask 2.1: Add `show_hidden_files: bool` config key to `DEFAULT_CONFIG` in `ConfigService` under section `plugin.file_explorer`
  - [x] Subtask 2.2: Add `_show_hidden_files: bool` field to `FileExplorerTree` — default from `ConfigService` or `False`
  - [x] Subtask 2.3: Filter dot-prefixed entries in `_create_list_model_for_dir` when `_show_hidden_files` is `False`
  - [x] Subtask 2.4: Add panel header menu with `Gtk.PopoverMenu` containing "Show Hidden Files" toggle action
  - [x] Subtask 2.5: Toggling "Show Hidden Files" reloads the tree and persists the preference via `ConfigService`
  - [x] Subtask 2.6: Register action `"explorer.toggle_hidden_files"` in `FileExplorerPlugin`

- [x] Task 3: Implement performance tests (AC: 2)
  - [x] Subtask 3.1: Create `tests/ui/panels/test_file_explorer_performance.py`
  - [x] Subtask 3.2: Test: create temp directory with 100+ subfolders, measure tree expansion time — must be <100ms per folder
  - [x] Subtask 3.3: Test: verify `_on_create_child_model` is called only once per expanded folder (no redundant scans)
  - [x] Subtask 3.4: Test: verify initial tree load does NOT recursively scan subdirectories

- [x] Task 4: Add hidden files unit tests (AC: 5)
  - [x] Subtask 4.1: Test: dot-prefixed files not shown when `show_hidden_files=False`
  - [x] Subtask 4.2: Test: dot-prefixed files shown when `show_hidden_files=True`
  - [x] Subtask 4.3: Test: toggle action changes visibility and reloads tree
  - [x] Subtask 4.4: Test: preference persists across sessions via `ConfigService`
  - [x] Subtask 4.5: Test: `.git` directory always excluded regardless of hidden files setting

- [x] Task 5: Update existing tests for hidden files awareness
  - [x] Subtask 5.1: Update `tests/ui/panels/test_file_explorer_tree.py` — existing tests should account for hidden files filtering
  - [x] Subtask 5.2: **Migration strategy:** If tests create dot-prefixed files, either (a) remove those files from test setup, or (b) explicitly set `show_hidden_files=True` in test ConfigService
  - [x] Subtask 5.3: Add `ConfigService` parameter to all FileExplorerTree instantiations in existing tests
  - [x] Subtask 5.4: Ensure all existing tests still pass with new hidden files logic

## Dev Notes

### Verification vs Implementation Policy

**AC 1, 3, 4 (Story 2.1 Verification):**
These acceptance criteria require verification of existing functionality from Story 2.1. **Verification failures should NOT be fixed in this story.** Instead:
1. Document the failure with specific details (what's broken, expected vs actual)
2. Create a bug ticket for the failing verification
3. Do NOT block this story on verification failures
4. The dev agent should focus on NEW functionality (hidden files toggle + performance tests)

This policy prevents scope creep and keeps Story 2.2 focused on its primary goals.

**AC 2, 5 (New Implementation):**
These are the actual implementation targets for this story:
- AC 2: Performance tests with <100ms threshold
- AC 5: Hidden files toggle with config persistence

**Task 1 Verification Exit Criteria:**
For each verification subtask (1.1, 1.2, 1.3), document findings as follows:
- **PASS**: No action needed, proceed with story implementation
- **FAIL**: Document specific failure in story comments, create bug ticket with reference to this story, continue with story implementation

**Example Bug Ticket Format:**
```
Bug: [Component] - [Brief description]
Found during Story 2.2 verification
Expected: [Expected behavior]
Actual: [Actual behavior]
Story Reference: Story 2.2, Task 1, Subtask 1.x
```

**Layer Architecture (STRICT):** This story modifies the UI layer (`slate/ui/panels/file_explorer_tree.py`) and adds config to the Service layer (`slate/services/config_service.py`). The plugin layer (`slate/plugins/core/file_explorer.py`) registers the new toggle action. No cross-layer violations. [Source: architecture.md#Layer Architecture, project-context.md#Critical Implementation Rules]

**ConfigService Integration:**
- Add `plugin.file_explorer` section to `DEFAULT_CONFIG` with key `show_hidden_files = "false"`
- `FileExplorerTree` should receive `ConfigService` reference (or read from config at construction)
- Toggle persists via `config_service.set("plugin.file_explorer", "show_hidden_files", "true")`
- [Source: architecture.md#Configuration Format, project-context.md#Configuration Rules]

**Event Ownership:**
- `FolderOpenedEvent` triggers tree reload — already implemented
- No new events needed for this story
- [Source: architecture.md#Event System Patterns, project-context.md#Event Ownership Rules]

**Plugin Action Registration:**
- New action `"explorer.toggle_hidden_files"` registered in `FileExplorerPlugin.activate()`
- Action callback toggles visibility and reloads tree
- [Source: architecture.md#Plugin API Patterns]

### Previous Story Intelligence

**From Story 2.1 (File Explorer — Basic Tree View & Navigation):**
- FileExplorerTree uses `Gtk.ListView` + `Gtk.TreeListModel` + `Gtk.TreeExpander` (modern GTK4 stack)
- Lazy loading already implemented via `create_func` callback on `TreeListModel`
- Icons use `Gio.content_type_get_icon` for system-themed icons
- `.git` directory excluded from tree
- Breadcrumb navigation implemented
- `FolderOpenedEvent` subscription triggers tree reload
- 289 tests passing (267 existing + 22 new from Story 2.1)
- Plugin uses `EventBus()` singleton directly (no `event_bus` property on `PluginContext`)

**Key Implementation Details from Story 2.1:**
- `FileExplorerTree.__init__` takes `file_service` and `event_bus` parameters
- `_create_list_model_for_dir` returns `(Gio.ListStore, str | None)` — tuple of store and optional error
- `_on_create_child_model` is the lazy loading callback — only called when folder row is expanded
- FileTreeItem wraps tree node data: `name`, `path`, `is_folder`
- Panel widget created lazily via factory callback in plugin

**Files Established in Story 2.1:**
- `slate/plugins/core/file_explorer.py` — FileExplorerPlugin
- `slate/ui/panels/file_explorer_tree.py` — FileExplorerTree widget
- `slate/core/events.py` — FolderOpenedEvent (added), OpenFileRequestedEvent (already existed)
- `tests/plugins/test_file_explorer.py` — 9 plugin tests
- `tests/ui/panels/test_file_explorer_tree.py` — 13 widget tests

**Lessons Learned:**
- `Gtk.TreeListModel.new()` uses `create_func` keyword (not `create_model_func`) on GTK 4.6.9
- `Gtk.Button.set_flat()` not available on GTK 4.6.9 — used CSS class "flat" instead
- Plugin uses `EventBus()` singleton directly

### Source Tree Components to Touch

**Files to Modify:**
- `slate/services/config_service.py` — Add `plugin.file_explorer` section to `DEFAULT_CONFIG`
- `slate/ui/panels/file_explorer_tree.py` — Add hidden files filtering, panel header menu with toggle
- `slate/plugins/core/file_explorer.py` — Register `"explorer.toggle_hidden_files"` action

**Files to Create:**
- `tests/ui/panels/test_file_explorer_performance.py` — Performance tests for lazy loading
- `tests/ui/panels/test_file_explorer_hidden_files.py` — Hidden files toggle tests

**Files to Update:**
- `tests/ui/panels/test_file_explorer_tree.py` — Update existing tests for hidden files awareness

**Existing Files to Reference (read-only):**
- `slate/core/events.py` — Event definitions
- `slate/services/file_service.py` — FileService.list_directory()
- `slate/core/plugin_api.py` — AbstractPlugin interface

### Testing Standards Summary

**Coverage Requirements:**
- Plugin logic (non-widget): **85%+** line coverage
- Service layer: **90%+** line coverage (ConfigService change)
- UI layer: smoke/integration tests only — don't chase superficial percentage
- Performance tests: real directory operations, not mocked

**Test Commands:**
- `pytest tests/` — Run all tests
- `pytest tests/ui/panels/test_file_explorer_performance.py -v` — Run performance tests
- `pytest tests/ --cov=slate --cov-report=term-missing` — Run with coverage

**Performance Test Approach:**
- Use `time.perf_counter()` for timing measurements
- Create real temp directories with 100+ subfolders
- Measure individual folder expansion time, not total tree load
- Target: <100ms per folder expansion (NFR-002: no perceptible lag)

**Performance Test Failure Handling:**
If performance tests fail intermittently on CI:
1. Run test locally 10 times to confirm hardware-specific issue
2. If local passes consistently but CI fails, document in test comments
3. Use `@pytest.mark.skipif` with environment detection for CI runners below spec
4. Document hardware requirements in test file docstring

**Flakiness Mitigation:**
- Use `tempfile.TemporaryDirectory()` for isolation
- Run each timing test 5 times, use median value (not average to avoid outliers)
- Clear filesystem cache between runs if possible (`sync && echo 3 > /proc/sys/vm/drop_cache` on Linux)

### Project Structure Notes

**Alignment with established patterns:**
- Config section: `plugin.file_explorer` (matches naming convention)
- Action ID: `explorer.toggle_hidden_files` (matches namespaced dot pattern)
- Test files mirror source: `tests/ui/panels/test_file_explorer_*.py`
- Hidden files filtering happens in `_create_list_model_for_dir` (single point of control)

**Directory structure:**
```
slate/
├── services/
│   └── config_service.py           # MODIFY: add plugin.file_explorer section
├── ui/
│   └── panels/
│       └── file_explorer_tree.py   # MODIFY: hidden files filter + header menu
└── plugins/
    └── core/
        └── file_explorer.py        # MODIFY: register toggle action
tests/
└── ui/
    └── panels/
        ├── test_file_explorer_tree.py          # UPDATE: hidden files awareness
        ├── test_file_explorer_performance.py   # CREATE: performance tests
        └── test_file_explorer_hidden_files.py  # CREATE: hidden files toggle tests
```

### References

- **Epic 2 Definition:** `_bmad-output/planning-artifacts/epics.md#Story 2.2: File Explorer — Lazy Loading & Performance`
- **Architecture Layer Rules:** `_bmad-output/planning-artifacts/architecture.md#Layer Architecture (Section 3.1) — MANDATORY`
- **Architecture Config Format:** `_bmad-output/planning-artifacts/architecture.md#Configuration Format`
- **Architecture Plugin Patterns:** `_bmad-output/planning-artifacts/architecture.md#Plugin API Patterns (Section 3.2)`
- **UX File Explorer Tree:** `_bmad-output/planning-artifacts/ux-design-specification.md#3. File Explorer Tree`
- **UX Loading States:** `_bmad-output/planning-artifacts/ux-design-specification.md#Loading States`
- **Project Context Rules:** `_bmad-output/project-context.md`
- **Previous Story 2.1:** `_bmad-output/implementation-artifacts/2-1-file-explorer-basic-tree-view-navigation.md`
- **NFR-002 (Responsiveness):** `_bmad-output/planning-artifacts/epics.md#NFR-002`

## Developer Context Section

### Critical Implementation Guardrails

**ANTI-PATTERNS TO AVOID:**
- ❌ Never scan entire directory tree on plugin activation — lazy load only
- ❌ Never import from `slate/ui/` inside the plugin file
- ❌ Never use `os.walk` for directory listing — use `FileService.list_directory()`
- ❌ Never block UI thread during directory listing — already handled by lazy loading
- ❌ Never hardcode hidden files logic — use `ConfigService` for persistence
- ❌ Never show hidden files BY DEFAULT — UX spec says hidden by default (toggle to show)
- ✅ Always filter dot-prefixed entries when `show_hidden_files=False`
- ✅ Always persist toggle state via `ConfigService.set()`
- ✅ Always use `Gtk.PopoverMenu` for panel header menu (matches system theme)
- ✅ Always keep `.git` excluded regardless of hidden files setting

**GIT EXCLUSION SPECIFICATION:**
The `.git` directory is ALWAYS excluded from the file explorer tree, independent of the hidden files toggle:
- When `show_hidden_files=False`: `.git` is excluded (along with all other dot-prefixed files)
- When `show_hidden_files=True`: `.git` is STILL excluded (it's always treated as hidden, even when showing hidden files)
- This is intentional — users should not interact with the git internals directory
- If user needs to access `.git` contents, they should use terminal or system file manager

**PERFORMANCE REQUIREMENTS:**
- Tree expansion must be instant (<100ms) — lazy load only the expanded folder
- Do NOT recursively scan subdirectories on initial load
- Use `Gio.content_type_get_icon` for file/folder icons (matches system theme)
- Panel widget creation is LAZY — only when user clicks the explorer icon
- Performance test: 100+ subfolders, each expansion <100ms

**HIDDEN FILES LOGIC:**
```python
# In _create_list_model_for_dir:
for entry in entries:
    basename = os.path.basename(entry.path)
    if basename == ".git":
        continue  # Always exclude .git
    if not self._show_hidden_files and basename.startswith("."):
        continue  # Filter hidden files when toggle is off
    store.append(FileTreeItem(...))
```

**TREE RELOAD STRATEGY:**
When hidden files toggle changes, use **Strategy A (Full reload)** for simplicity in this story:
- Clear the tree model and reload from root
- Expansion state will be reset (acceptable trade-off)
- Future stories may implement incremental refresh for better UX
- This ensures consistency and avoids partial state bugs

**PANEL HEADER MENU PATTERN:**
```python
# Add a menu button to the panel header (Gtk.PopoverMenu)
# Menu items:
#   - "Show Hidden Files" (toggle action)
# The menu button should be a small gear/settings icon in the panel header
```

**CONFIG PERSISTENCE:**
```python
# In ConfigService DEFAULT_CONFIG:
"plugin.file_explorer": {
    "show_hidden_files": "false",
}

# In FileExplorerTree:
# Read: config_service.get("plugin.file_explorer", "show_hidden_files") == "true"
# Write: config_service.set("plugin.file_explorer", "show_hidden_files", "true")
```

**CONFIG ERROR HANDLING:**
- If `ConfigService.get()` returns invalid value (not "true" or "false"), default to "false"
- If `ConfigService.set()` fails (disk full, permission denied), log error with `logger.warning()` but don't crash
- Failed persistence should not prevent toggle from working in current session

### Technical Requirements Deep Dive

**Hidden Files Toggle Implementation:**

The `FileExplorerTree` widget needs to:
1. Accept a `ConfigService` reference (or read config at construction)
2. Filter dot-prefixed entries in `_create_list_model_for_dir` based on `_show_hidden_files`
3. Provide a panel header menu with "Show Hidden Files" toggle
4. Persist toggle state via `ConfigService`

**Panel Header Menu:**
- Use `Gtk.MenuButton` with `Gtk.PopoverMenu`
- Icon: `open-menu-symbolic` or `emblem-system-symbolic`
- Single menu item: "Show Hidden Files" with checkmark toggle
- **Position: Top-right corner of the panel header, aligned with the breadcrumb bar (to the right of breadcrumb segments, or in a separate header row if space is constrained)**
- **Menu lifecycle: Create on first click (lazy initialization) to avoid unnecessary widget creation**
- **Accessibility: Menu button must have tooltip "View options"**
- **Keyboard shortcut: Alt+V opens the panel header menu (menu scope only, not a global shortcut)**

**Performance Testing:**
- Create temp directory with 100+ subfolders (use `tempfile.TemporaryDirectory`)
- Each subfolder should contain a few files to simulate real project
- Measure time from folder expansion start to children rendered
- Target: <100ms per folder (NFR-002)
- Use `time.perf_counter()` for accurate timing

**FileExplorerTree Constructor Change:**
```python
def __init__(
    self,
    file_service: FileService,
    event_bus: EventBus,
    config_service: ConfigService | None = None,
) -> None:
```

**Breaking Change — Call Sites to Update:**
- `slate/plugins/core/file_explorer.py` — FileExplorerPlugin.create_panel_widget() — pass ConfigService instance
- `tests/ui/panels/test_file_explorer_tree.py` — All FileExplorerTree instantiations — pass ConfigService or None
- `tests/ui/panels/test_file_explorer_hidden_files.py` — New tests — pass ConfigService
- `tests/ui/panels/test_file_explorer_performance.py` — New tests — pass ConfigService or None

If `config_service` is `None`, default to `show_hidden_files=False` (no persistence).

### Architecture Compliance Checklist

- [ ] Lazy loading verified: `_on_create_child_model` only called on folder expand
- [ ] Icons verified: `Gio.content_type_get_icon` used for file icons
- [ ] `FolderOpenedEvent` subscription verified: triggers `load_folder()` reload
- [ ] Hidden files filtered by default (dot-prefixed entries excluded)
- [ ] Toggle persists via `ConfigService.set("plugin.file_explorer", "show_hidden_files", ...)`
- [ ] `.git` always excluded regardless of hidden files setting
- [ ] Panel header menu uses `Gtk.PopoverMenu` (matches system theme)
- [ ] Action `"explorer.toggle_hidden_files"` registered in plugin
- [ ] Performance test: 100+ subfolders expand <100ms each
- [ ] All existing tests pass with new hidden files logic
- [ ] ConfigService `DEFAULT_CONFIG` updated with `plugin.file_explorer` section

### Library/Framework Requirements

- **PyGObject >= 3.42** — GTK4 bindings (installed: 3.42.1)
- **Gtk >= 4.6** — GTK4 toolkit (installed: 4.6.9)
- **Gtk.MenuButton** — Button that shows popover menu
- **Gtk.PopoverMenu** — Context menu following system theme
- **Gio.ListStore** — List model for tree items
- **Gio.content_type_get_icon** — System-themed file/folder icons
- **time.perf_counter()** — High-resolution timing for performance tests

### File Structure Requirements

```
slate/
├── services/
│   └── config_service.py           # MODIFY: add plugin.file_explorer section
├── ui/
│   └── panels/
│       └── file_explorer_tree.py   # MODIFY: hidden files filter + header menu
└── plugins/
    └── core/
        └── file_explorer.py        # MODIFY: register toggle action
tests/
└── ui/
    └── panels/
        ├── test_file_explorer_tree.py          # UPDATE: hidden files awareness
        ├── test_file_explorer_performance.py   # CREATE: performance tests
        └── test_file_explorer_hidden_files.py  # CREATE: hidden files toggle tests
```

### Testing Requirements

**New Tests to Create:**

**Performance Tests (`tests/ui/panels/test_file_explorer_performance.py`):**
- `test_expand_100_folders_under_100ms_each` — create 100+ subfolders, measure each expansion
- `test_initial_load_does_not_scan_recursively` — verify only root folder contents loaded
- `test_create_child_model_called_once_per_folder` — verify no redundant scans

**Hidden Files Tests (`tests/ui/panels/test_file_explorer_hidden_files.py`):**
- `test_hidden_files_not_shown_by_default` — dot-prefixed files excluded when toggle off
- `test_hidden_files_shown_when_toggle_on` — dot-prefixed files included when toggle on
- `test_git_always_excluded` — `.git` never shown regardless of toggle
- `test_toggle_persists_via_config_service` — toggle state saved to config.ini
- `test_toggle_reloads_tree` — toggling visibility refreshes the tree
- `test_invalid_config_value_defaults_to_false` — invalid config value (e.g., "maybe") defaults to hidden
- `test_config_set_failure_logs_warning` — failed persistence logs warning but doesn't crash
- `test_permission_denied_on_hidden_files` — gracefully handle directory read permission errors

**Widget Tests Updates (`tests/ui/panels/test_file_explorer_tree.py`):**
- Update existing tests to account for hidden files filtering
- Ensure tests create temp directories without dot-prefixed files, or explicitly test with them

### Git Intelligence

**Recent Work Patterns (from Story 2.1 completion):**
- FileExplorerTree uses modern GTK4 stack (ListView + TreeListModel)
- 289 tests passing
- Lazy loading already implemented and working
- Icons use system theme via `Gio.content_type_get_icon`
- `.git` exclusion implemented
- Breadcrumb navigation working
- Plugin registration pattern established

**Code Patterns Established:**
- One class per file for services and plugins
- Type hints on all public methods
- Docstrings on all public classes and methods
- `from __future__ import annotations` for forward references
- Tests use temp directories and real file operations over mocking
- ConfigService uses atomic writes with temp file + rename

---

## Dev Agent Record

### Agent Model Used

opencode/qwen3.6-plus-free

### Debug Log References

### Completion Notes List

- Story context created for Story 2.2: File Explorer — Lazy Loading & Performance
- Builds on Story 2.1 foundation (all lazy loading, icons, event subscription already implemented)
- Main new work: hidden files toggle with config persistence + performance validation tests
- ConfigService needs `plugin.file_explorer` section added to DEFAULT_CONFIG
- FileExplorerTree needs ConfigService reference for reading/writing hidden files preference
- FileExplorerPlugin needs to register `"explorer.toggle_hidden_files"` action
- **IMPLEMENTATION COMPLETED:**
  - Task 2: Hidden files toggle fully implemented with panel header menu (Gtk.PopoverMenu)
  - Task 3: Performance tests created and passing (100 folders expand <100ms each)
  - Task 4: Hidden files unit tests created and passing (11 tests)
  - Task 5: Existing tests updated for hidden files awareness
  - Task 1: Lazy loading verified in existing implementation
- **304 tests passing** (no regressions)

### File List

- `slate/services/config_service.py` — Modified: added `plugin.file_explorer` section to DEFAULT_CONFIG
- `slate/ui/panels/file_explorer_tree.py` — Modified: added hidden files filter, header menu with toggle
- `slate/plugins/core/file_explorer.py` — Modified: register toggle action, pass ConfigService to widget
- `tests/ui/panels/test_file_explorer_tree.py` — Updated: fixed breadcrumb bar test for new structure
- `tests/ui/panels/test_file_explorer_performance.py` — Created: 4 performance tests
- `tests/ui/panels/test_file_explorer_hidden_files.py` — Created: 11 hidden files toggle tests
- `tests/services/test_config_service.py` — Updated: added plugin.file_explorer to expected sections
- `tests/plugins/test_file_explorer.py` — Updated: mock config service, updated action count assertions

---

## Change Log

- **Date: 2026-04-07** - Story 2.2 context created
  - Comprehensive implementation guide for File Explorer Lazy Loading & Performance
  - Builds on Story 2.1 foundation (lazy loading, icons, event subscription already working)
  - Main additions: hidden files toggle with config persistence, performance validation tests
  - Includes panel header menu with Gtk.PopoverMenu for "Show Hidden Files" toggle
  - Performance target: <100ms per folder expansion (NFR-002)
  - Config persistence via ConfigService under `plugin.file_explorer` section
- **Date: 2026-04-07** - Story 2.2 adversarial review findings fixed
  - Added Task 1 verification exit criteria with PASS/FAIL documentation format
  - Added AC 5 visual specifications (toggle appearance, icon states, animation)
  - Clarified keyboard shortcut scope: Alt+V is menu-only (not global)
  - Added performance test failure handling documentation and flakiness mitigation
  - Added detailed .git exclusion specification (always excluded, independent of toggle)
  - Updated test plan with verification notes and bug ticket format
- **Date: 2026-04-07** - Story 2.2 implementation complete
  - Hidden files toggle fully implemented with Gtk.PopoverMenu panel header
  - Config persistence via ConfigService under `plugin.file_explorer.show_hidden_files`
  - Performance tests created: 100+ folders expand in <100ms each
  - 15 new tests added (11 hidden files + 4 performance)
  - 304 tests passing, no regressions