# Story 2.3: File Explorer — Context Menu & File Operations

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to create, rename, and delete files and folders from the explorer,
So that I can manage my project without switching to the terminal.

## Acceptance Criteria

1. **Given** the file explorer tree is visible, **when** I secondary-click a file (mouse right-click or touchpad secondary click), context menu shows: Open, Rename (inline), Delete (confirm), Copy Relative Path, Copy Absolute Path
2. **And** when I secondary-click a folder, context menu shows: New File, New Folder, Rename, Delete
3. **And** file/folder create, rename, delete operations work via FileService
4. **And** rename uses inline editing (no separate dialog) — label toggles to Gtk.Entry via Gtk.Stack, pre-filled with current name, all text selected for immediate replacement
5. **And** delete shows confirmation dialog before removing — for non-empty folders, dialog shows immediate child count: "This folder contains X items. Delete anyway?"
6. **And** context menus use `Gtk.PopoverMenu` + `Gio.Menu` and inherit the system GTK4 theme (no custom CSS)
7. **And** copy path operations show a UI-layer notification: direct `SlateToast` or `HostUIBridge.show_notification()` backed by `SlateToast`, message `Copied: /path/to/file`, 2s auto-dismiss per UX-DR11
8. **And** new file/folder inline input appears as the first row in the folder, pre-filled with default name ("untitled" for files, "New Folder" for folders), all text selected
9. **And** rename validates filename — rejects invalid characters (/, \0) with inline error, does not allow overwriting existing names

## Tasks / Subtasks

- [ ] Task 1: Implement context menu actions for files (AC: 1, 3, 6, 7)
  - [ ] Subtask 1.1: Add secondary-click handling to FileExplorerTree using GTK4 event controllers (`Gtk.GestureClick` configured for `Gdk.BUTTON_SECONDARY`); use `Gtk.GestureLongPress` only if touch press-and-hold support is added separately
  - [ ] Subtask 1.2: Create context menu popover with menu items: Open, Rename, Delete, Copy Relative Path, Copy Absolute Path — use `Gtk.PopoverMenu` with `Gio.Menu`, inherit the system GTK4 theme
  - [ ] Subtask 1.3: Implement "Open" action — emit OpenFileRequestedEvent (already exists in Story 2.1)
  - [ ] Subtask 1.4: Implement "Copy Relative Path" — copy the path relative to the currently loaded explorer root via GTK4 clipboard APIs (`widget.get_clipboard()` or `Gdk.Display.get_clipboard()` + `Gdk.Clipboard.set_text(...)`), then show a UI-layer notification (`SlateToast` or `HostUIBridge.show_notification()`) with `Copied: <path>` for 2s
  - [ ] Subtask 1.5: Implement "Copy Absolute Path" — copy the absolute path via GTK4 clipboard APIs (`widget.get_clipboard()` or `Gdk.Display.get_clipboard()` + `Gdk.Clipboard.set_text(...)`), then show a UI-layer notification (`SlateToast` or `HostUIBridge.show_notification()`) with `Copied: <path>` for 2s

- [ ] Task 2: Implement inline rename (AC: 4, 9)
  - [ ] Subtask 2.1: Use Gtk.Stack in row widget to toggle between label and Gtk.Entry — do NOT swap widgets dynamically (SignalListItemFactory pattern makes this fragile)
  - [ ] Subtask 2.2: On "Rename" action: switch Stack to entry, pre-fill with current name, select all text, grab focus
  - [ ] Subtask 2.3: On Enter key: validate filename (reject empty names, `/`, `\0`, and sibling name collisions), call FileService.rename(), emit FolderOpenedEvent for the parent directory, restore label
  - [ ] Subtask 2.4: On Escape key: cancel rename, restore label
  - [ ] Subtask 2.5: On invalid filename: show inline error (red border on entry + tooltip), keep the row in edit mode until valid input is entered or Escape is pressed

- [ ] Task 3: Implement delete with confirmation (AC: 5)
  - [ ] Subtask 3.1: Show Gtk.MessageDialog with confirmation before delete — title: "Delete [name]?", body: "This action cannot be undone."
  - [ ] Subtask 3.2: For non-empty folders: body text changes to "This folder contains X items. Delete anyway?" — count immediate children in FileService before showing dialog
  - [ ] Subtask 3.3: Call FileService.delete_file() or delete_folder() on confirm
  - [ ] Subtask 3.4: Emit FolderOpenedEvent with the affected directory path to refresh tree after successful delete
  - [ ] Subtask 3.5: On Cancel: close dialog, no action, tree unchanged

- [ ] Task 4: Implement context menu for folders (AC: 2, 3, 8)
  - [ ] Subtask 4.1: Create separate menu for folders: New File, New Folder, Rename, Delete
  - [ ] Subtask 4.2: Implement "New File" — insert new row as first item in folder with Gtk.Entry pre-filled "untitled", all text selected; on Enter: validate name, call FileService.create_file(parent_path, name), emit FolderOpenedEvent for the parent folder; on Escape: remove row
  - [ ] Subtask 4.3: Implement "New Folder" — insert new row as first item in folder with Gtk.Entry pre-filled "New Folder", all text selected; on Enter: validate name, call FileService.create_folder(parent_path, name), emit FolderOpenedEvent for the parent folder; on Escape: remove row
  - [ ] Subtask 4.4: Handle duplicate name or invalid input on create: show inline error on entry, do not create file/folder, keep the row in edit mode until fixed or Escape is pressed

- [ ] Task 5: Add FileService operations if not present (AC: 3)
  - [ ] Subtask 5.1: Read slate/services/file_service.py — check if create_file(), create_folder(), delete_file(), delete_folder(), rename() exist
  - [ ] Subtask 5.2: If missing, implement these methods with the following contracts:
    - `create_file(parent_path: str, name: str) -> str` — creates an empty file and returns the full path. Raises `FileExistsError` if name already exists. UI refreshes the parent folder after success.
    - `create_folder(parent_path: str, name: str) -> str` — creates a folder (non-recursive) and returns the full path. Raises `FileExistsError` if name already exists. UI refreshes the parent folder after success.
    - `delete_file(path: str) -> None` — removes a file. Raises `FileNotFoundError` if not found.
    - `delete_folder(path: str) -> None` — removes a folder recursively (`shutil.rmtree`). Raises `FileNotFoundError` if not found.
    - `rename(old_path: str, new_name: str) -> str` — renames a file/folder in the same directory and returns the new path. Raises `FileNotFoundError` if source missing, `FileExistsError` if target exists.
  - [ ] Subtask 5.3: Add a FileService helper for immediate child counting if needed so delete confirmation text stays out of the UI layer

- [ ] Task 6: Write tests (AC: 1-9)
  - [ ] Subtask 6.1: Test file context menu shows correct items
  - [ ] Subtask 6.2: Test folder context menu shows correct items
  - [ ] Subtask 6.3: Test inline rename commits on Enter, cancels on Escape
  - [ ] Subtask 6.4: Test delete confirmation dialog appears
  - [ ] Subtask 6.5: Test copy path operations copy correct path via GTK4 clipboard APIs, with relative paths rooted at the loaded explorer root
  - [ ] Subtask 6.6: Test new file/folder creation at folder level
  - [ ] Subtask 6.7: Test inline rename rejects invalid characters (/, \0, empty name)
  - [ ] Subtask 6.8: Test inline rename rejects duplicate name (file already exists in same directory)
 - [ ] Subtask 6.9: Test delete non-empty folder shows immediate child count in confirmation dialog
  - [ ] Subtask 6.10: Test new file/folder with duplicate name shows inline error, does not create
  - [ ] Subtask 6.11: Test copy path notification appears with correct message and 2s duration

## Dev Notes

### Relevant Architecture Patterns and Constraints

**Layer Architecture (STRICT):** This story touches UI layer (`slate/ui/panels/file_explorer_tree.py`) and Service layer (`slate/services/file_service.py`). The file operations must use FileService methods — no direct os.* calls in UI layer. [Source: architecture.md#Layer Architecture, project-context.md#Critical Implementation Rules]

**Context Menu Pattern:**
- Use `Gtk.PopoverMenu` with `Gio.Menu` for context menus
- Menu items connect to callbacks in FileExplorerTree
- Trigger from GTK4 event controllers; use `Gtk.GestureClick` for secondary click
- Popover positioning uses `Gtk.Popover.set_pointing_to()` with event coordinates
- [Source: ux-design-specification.md#Context Menus]

**Inline Editing Pattern:**
- Use Gtk.Stack in the row widget to toggle between label and Gtk.Entry — do NOT swap widgets dynamically (SignalListItemFactory pattern makes this fragile)
- On "Rename": switch Stack visible child to entry, pre-fill with current name, select all text, grab focus
- On Enter: validate filename (reject empty names, `/`, `\0`, and sibling name collisions), call FileService.rename(), emit FolderOpenedEvent for the parent directory, switch back to label
- On Escape: cancel, switch back to label
- On invalid input: show red CSS class on entry + tooltip error, keep the row in edit mode until valid input is entered or Escape is pressed
- For new file/folder: insert row as first item in folder with Gtk.Entry pre-filled ("untitled" / "New Folder"), all text selected; on Enter validate, call FileService.create_file/create_folder(parent_path, name), emit FolderOpenedEvent for the parent folder; on Escape remove row

**Copy Path Feedback Pattern:**
- "Copy Relative Path" is relative to the currently loaded explorer root (`FileExplorerTree._root_path`)
- After copying path to clipboard, show a UI-layer notification: direct `SlateToast` or `HostUIBridge.show_notification()` backed by `SlateToast`
- Auto-dismiss after 2s per UX-DR11
- Toast display is owned by the UI layer; FileService never presents notifications

**Delete Confirmation Pattern:**
- For files: Gtk.MessageDialog — "Delete [name]?" / "This action cannot be undone."
- For non-empty folders: Gtk.MessageDialog — "Delete [name]?" / "This folder contains X items. Delete anyway?"
- Buttons: Delete (destructive, default), Cancel
- Count immediate children in FileService before showing dialog; do not use UI-side filesystem calls

**Context Menu Trigger Pattern:**
- Primary: `Gtk.GestureClick` with secondary button (`Gdk.BUTTON_SECONDARY`)
- Optional touch supplement: `Gtk.GestureLongPress` only for press-and-hold touch UX, not as a substitute for touchpad secondary click
- Popover positioning: `Gtk.Popover.set_pointing_to()` with `Gdk.Rectangle` from event coordinates

**Event Flow:**
```
User secondary-clicks tree item
  → FileExplorerTree captures `Gtk.GestureClick` secondary press (or optional touch long-press)
  → Show GtkPopoverMenu at cursor position
  → User clicks menu item
  → FileExplorerTree action handler executes operation
  → Call FileService method (create/rename/delete)
  → FileExplorerTree emits FolderOpenedEvent for the affected directory path after successful create/rename/delete
  → FileExplorerTree subscribes to FolderOpenedEvent → reload target must be validated as a real directory before reload
  → UI notification shown for copy path operations
```

### Previous Story Intelligence

**From Story 2.2 (Lazy Loading & Performance):**
- Story 2.2 is in "review" status (AC 1,3,4 verified, AC 2,5 implemented)
- FileExplorerTree already has: lazy loading, FolderOpenedEvent subscription, system theme icons
- Hidden files toggle implemented with ConfigService integration
- All 289+ tests passing

**From Story 2.1 (Basic Tree View):**
- FileExplorerPlugin uses AbstractPlugin.activate() only
- Panel registered with "folder-symbolic" icon
- Action "explorer.focus" registered with Ctrl+Shift+O
- FileExplorerTree widget uses Gtk.ListView + Gtk.TreeListModel + Gtk.TreeExpander
- OpenFileRequestedEvent used for file opening (not FileOpenedEvent)
- .git directory excluded from tree
- Breadcrumb navigation implemented

**Files Established:**
- `slate/plugins/core/file_explorer.py` — FileExplorerPlugin
- `slate/ui/panels/file_explorer_tree.py` — FileExplorerTree (modify this)
- `slate/services/file_service.py` — FileService (may need to add methods)
- `slate/core/events.py` — OpenFileRequestedEvent, FolderOpenedEvent

**Lessons Learned:**
- Use `Gtk.TreeListModel.new(create_func=...)` keyword arg (not `create_model_func`) on GTK 4.6.9
- Plugin uses EventBus() singleton directly
- HostUIBridge.register_action() supports shortcut parameter for keybinding

### Source Tree Components to Touch

**Files to Create:**
- None (all functionality added to existing files)

**Files to Modify:**
- `slate/ui/panels/file_explorer_tree.py` — Add context menu, inline rename, new file/folder, notification hook
- `slate/services/file_service.py` — Add create_file, create_folder, delete_file, delete_folder, rename methods if not present
- `slate/plugins/core/file_explorer.py` — Pass host notification capability into the panel widget if bridge-backed notifications are used
- `slate/ui/main_window.py` — Implement `HostUIBridge.show_notification()` if the story uses bridge-backed notifications instead of panel-owned `SlateToast`

**Existing Files to Reference (read-only):**
- `slate/core/plugin_api.py` — AbstractPlugin interface
- `slate/services/file_service.py` — FileService methods
- `slate/ui/panels/file_explorer_tree.py` — Current implementation
- `slate/ui/dialogs/save_discard_dialog.py` — Dialog pattern reference
- `slate/ui/toast.py` — `SlateToast` implementation

### Testing Standards Summary

**Coverage Requirements:**
- UI layer: smoke/integration tests only — don't chase superficial percentage
- Service layer: **90%+** line coverage

**Test Patterns:**
- Use temp directories for file operation tests
- Test inline rename: Enter commits, Escape cancels
- Test delete confirmation: OK deletes, Cancel aborts
- Test copy path: verify clipboard contents and that relative paths are rooted at the loaded explorer root
- Test notifications: verify either `SlateToast.show()` or `HostUIBridge.show_notification()` is invoked with 2s semantics, depending on implementation choice

**Test Commands:**
- `pytest tests/` — Run all tests
- `pytest tests/ui/panels/test_file_explorer_tree.py -v` — Run tree tests

### Project Structure Notes

**Alignment with unified project structure:**
- File operations in `slate/services/file_service.py` (matches architecture spec)
- Context menu UI in `slate/ui/panels/file_explorer_tree.py` (matches architecture spec)
- UI notification plumbing may be in `slate/ui/main_window.py` when routed through `HostUIBridge.show_notification()`
- Tests mirror source: `tests/services/` and `tests/ui/panels/`

**Directory structure:**
```
slate/
├── services/
│   └── file_service.py        # MAY NEED: create_file, create_folder, delete_file, delete_folder, rename
├── plugins/core/
│   └── file_explorer.py       # MAY NEED: pass host notification capability into panel
├── ui/
│   └── main_window.py         # MAY NEED: implement HostUIBridge.show_notification
├── ui/panels/
│   └── file_explorer_tree.py  # MODIFY: add context menu, inline rename, new file/folder, notification hook
tests/
├── services/
│   └── test_file_service.py  # MAY NEED: add tests for new methods
└── ui/panels/
    └── test_file_explorer_tree.py  # ADD: context menu tests
```

### References

- **Epic 2 Definition:** `_bmad-output/planning-artifacts/epics.md#Story 2.3: File Explorer — Context Menu & File Operations`
- **Architecture Layer Rules:** `_bmad-output/planning-artifacts/architecture.md#Layer Architecture`
- **Architecture Service Boundaries:** `_bmad-output/planning-artifacts/architecture.md#Service Boundaries`
- **UX Context Menus:** `_bmad-output/planning-artifacts/ux-design-specification.md#Context Menus (GtkPopover)`
- **UX File Explorer:** `_bmad-output/planning-artifacts/ux-design-specification.md#3. File Explorer Tree`
- **Previous Story 2.1:** `_bmad-output/implementation-artifacts/2-1-file-explorer-basic-tree-view-navigation.md`
- **Previous Story 2.2:** `_bmad-output/implementation-artifacts/2-2-file-explorer-lazy-loading-performance.md`
- **Project Context Rules:** `_bmad-output/project-context.md`

## Developer Context Section

### Critical Implementation Guardrails

**ANTI-PATTERNS TO AVOID:**
- ❌ Never use os.rename(), os.remove(), os.mkdir() directly in UI layer — use FileService methods
- ❌ Never show separate dialog for rename — use inline Gtk.Entry via Gtk.Stack toggle
- ❌ Never delete without confirmation dialog
- ❌ Never access FileService directly in plugin — use context.get_service("file")
- ❌ Never emit FileOpenedEvent directly — emit OpenFileRequestedEvent
- ❌ Never swap widgets dynamically in SignalListItemFactory rows — use Gtk.Stack to toggle visibility
- ❌ Never allow rename to invalid filenames (/, \0, empty) or duplicate sibling names
- ❌ Never delete non-empty folder without showing item count in confirmation
- ❌ Never copy path without UI notification feedback
- ❌ Never create file/folder with duplicate name — show inline error instead
- ✅ Always use `Gtk.PopoverMenu` + `Gio.Menu` for context menus (inherits system GTK4 theme, no custom CSS)
- ✅ Always call FileService for file operations
- ✅ Folder refresh events carry the directory path to reload, never the deleted/renamed file path
- ✅ `FileExplorerTree._on_folder_changed()` validates the target is a real directory before reloading before any refresh emitted by this story
- ✅ Copy path operations show notification "Copied: <path>" (2s auto-dismiss)
- ✅ Secondary click is handled via `Gtk.GestureClick`; optional `Gtk.GestureLongPress` support is additive for touch press-and-hold only
- ✅ Pre-fill new file as "untitled", new folder as "New Folder" — all text selected
- ✅ Insert new file/folder row as first item in folder

**FILE OPERATION REQUIREMENTS:**
- create_file(path, name) → creates empty file at path/name
- create_folder(path, name) → creates folder at path/name
- delete_file(path) → removes file, raises on failure
- delete_folder(path) → removes folder recursively, raises on failure
- rename(old_path, new_name) → renames file/folder to new name in same directory

**Implementation Note:**
- File operations are performed in FileService; UI only invokes service methods and emits/handles folder refresh events.
- Clipboard copy uses GTK4 `Gdk.Clipboard` via widget/display clipboard APIs.
- Relative path is resolved against the currently loaded explorer root.
- Delete count uses service-side folder inspection, not UI-side filesystem calls.
- Folder refresh events carry the directory to reload, never the deleted/renamed file path.
- `_on_folder_changed()` must validate that the target is a real directory before reloading; current implementation does not yet do this.

**CONTEXT MENU STRUCTURE:**
```
File menu:
├── Open
├── Rename
├── Delete
├── ─────────
├── Copy Relative Path
└── Copy Absolute Path

Folder menu:
├── New File
├── New Folder
├── Rename
└── Delete
```

**INLINE RENAME FLOW:**
1. User clicks "Rename" in context menu
2. Gtk.Stack switches from label to Gtk.Entry (same row, no widget swap)
3. Entry pre-filled with current name, all text selected, focus grabbed
4. User types new name
5. On Enter: validate (no /, \0, empty, no duplicate sibling), call FileService.rename(), emit FolderOpenedEvent for the parent directory, switch Stack back to label
6. On Escape: cancel, switch Stack back to label
7. On invalid input: add "error" CSS class to entry + tooltip, keep entry visible

**NEW FILE/FOLDER FLOW:**
1. User clicks "New File" or "New Folder" in folder context menu
2. New row inserted as first item in folder with Gtk.Entry visible
3. Pre-filled: "untitled" for files, "New Folder" for folders — all text selected
4. On Enter: validate (reject empty names, `/`, `\0`, and duplicate sibling names), call FileService.create_file/create_folder, emit FolderOpenedEvent for the parent folder
5. On Escape: remove the temporary row
6. On duplicate name: show inline error on entry, do not create

**DELETE CONFIRMATION:**
1. User clicks "Delete" in context menu
2. For files: Gtk.MessageDialog — "Delete [name]?" / "This action cannot be undone."
3. For non-empty folders: count immediate children in FileService, show "Delete [name]?" / "This folder contains X items. Delete anyway?"
4. Buttons: Delete (destructive, default), Cancel
5. On Delete: call FileService.delete_file() or delete_folder(), emit FolderOpenedEvent for the affected directory path, refresh tree
6. On Cancel: close dialog, no action

**COPY PATH FEEDBACK:**
1. User clicks "Copy Relative Path" or "Copy Absolute Path"
2. Relative path is computed against the currently loaded explorer root; absolute path uses the full filesystem path
3. Path copied to clipboard via GTK4 `Gdk.Clipboard`
4. UI notification appears: "Copied: /path/to/file" — 2s auto-dismiss

### Architecture Compliance Checklist

- [ ] Context menu shows correct items for files (Open, Rename, Delete, Copy Relative, Copy Absolute)
- [ ] Context menu shows correct items for folders (New File, New Folder, Rename, Delete)
- [ ] Rename uses inline editing with Gtk.Entry toggled via Gtk.Stack (not widget swap)
- [ ] Delete shows confirmation dialog — non-empty folders show immediate child count
- [ ] All file operations use FileService methods (no direct os.* in UI layer)
- [ ] FolderOpenedEvent emitted after create/rename/delete for the affected directory path
- [ ] Context menu uses Gtk.PopoverMenu with system GTK4 theme (no custom CSS)
- [ ] Copy path operations show notification "Copied: <path>" (2s auto-dismiss)
- [ ] New file/folder row inserted as first item in folder, pre-filled with default name
- [ ] Rename validates filename — rejects /, \0, empty, duplicate sibling names
- [ ] Context menu supports secondary click via `Gtk.GestureClick`; optional touch long-press support is additive, not a replacement
- [ ] FileService methods return/raise cleanly; UI owns refresh emission semantics
- [ ] Relative path copies are computed from the current explorer root
- [ ] Notification integration path is explicit: panel-owned `SlateToast` or host bridge `show_notification()`

### Library/Framework Requirements

- **GTK4 Gtk.PopoverMenu** — Context menu display
- **GTK4 Gtk.GestureClick** — Secondary-click trigger
- **GTK4 Gtk.MenuButton** — Alternative menu trigger
- **GTK4 Gtk.Entry** — Inline rename input
- **GTK4 Gtk.MessageDialog** — Delete confirmation
- **GTK4 Gdk.Clipboard** — Copy path to clipboard via widget/display clipboard APIs
- **Gio.Menu** — Menu model for popover
- **FileService** — create_file, create_folder, delete_file, delete_folder, rename methods
- **HostUIBridge.show_notification() / SlateToast** — UI notification path for copy feedback

### File Structure Requirements

```
slate/
├── services/
│   └── file_service.py          # MAY NEED: add create_file, create_folder, delete_file, delete_folder, rename
├── ui/panels/
│   └── file_explorer_tree.py    # MODIFY: context menu, inline rename, new file/folder
tests/
├── services/
│   └── test_file_service.py     # MAY NEED: new method tests
└── ui/panels/
    └── test_file_explorer_tree.py  # ADD: context menu tests
```

### Testing Requirements

**Tests to Add/Update:**

**Widget Tests (`tests/ui/panels/test_file_explorer_tree.py`):**
- `test_file_context_menu_items` — verify file menu shows correct items
- `test_folder_context_menu_items` — verify folder menu shows correct items
- `test_inline_rename_commits_on_enter` — verify rename commits with Enter
- `test_inline_rename_cancels_on_escape` — verify rename cancels with Escape
- `test_delete_confirmation_dialog` — verify dialog appears on delete
- `test_copy_relative_path` — verify relative path copied via GTK4 clipboard APIs
- `test_copy_relative_path_uses_explorer_root` — verify the relative path base is the loaded explorer root
- `test_copy_absolute_path` — verify absolute path copied via GTK4 clipboard APIs
- `test_new_file_creation` — verify new file created at folder level
- `test_new_folder_creation` — verify new folder created at folder level
- `test_tree_refreshes_after_delete` — verify tree updates after file removal
- `test_inline_rename_rejects_invalid_characters` — verify / and \0 rejected
- `test_inline_rename_rejects_duplicate_name` — verify rename to existing name fails
- `test_delete_non_empty_folder_shows_item_count` — verify dialog shows "contains X items"
- `test_new_file_duplicate_shows_error` — verify duplicate name shows inline error
- `test_copy_path_notification` — verify notification appears with "Copied: <path>"
- `test_context_menu_on_secondary_click` — verify secondary-click gesture triggers menu
- `test_context_menu_on_touch_long_press` — verify optional long-press gesture triggers menu if implemented

**Service Tests (`tests/services/test_file_service.py`):**
- `test_create_file` — verify file created with correct path
- `test_create_folder` — verify folder created with correct path
- `test_delete_file` — verify file removed
- `test_delete_folder` — verify folder recursively removed
- `test_rename_file` — verify file renamed correctly
- `test_rename_folder` — verify folder renamed correctly
- `test_rename_nonexistent_raises` — verify error on missing source
- `test_delete_nonexistent_raises` — verify error on missing target
- `test_create_file_duplicate_raises` — verify FileExistsError on duplicate
- `test_create_folder_duplicate_raises` — verify FileExistsError on duplicate
- `test_rename_to_existing_raises` — verify FileExistsError when target exists
- `test_create_file_returns_path` — verify file creation returns the full path
- `test_count_immediate_children` — verify delete confirmation helper counts only immediate children
- `test_delete_folder_with_contents` — verify non-empty folder deleted recursively

### Git Intelligence

**Recent Work Patterns:**
- Story 2.2 added hidden files toggle with ConfigService integration
- FileExplorerTree uses modern GTK4 stack (ListView + TreeListModel)
- 289+ tests passing with established patterns

**Code Patterns Established:**
- One class per file for services
- Type hints on all public methods
- Docstrings on all public classes and methods
- `from __future__ import annotations` for forward references
- Tests use temp directories over mocking

---

## Dev Agent Record

### Agent Model Used

minimax-m2.5-free

### Debug Log References

### Completion Notes List

### File List
