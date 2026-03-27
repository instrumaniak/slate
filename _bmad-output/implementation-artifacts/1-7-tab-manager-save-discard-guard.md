# Story 1.7: Tab Manager & Save/Discard Guard

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want a tab bar with dirty indicators and save protection,
So that I can manage multiple open files and never lose work.

## Acceptance Criteria

1. **Given** TabManager is implemented **when** I open a file, a tab appears with the filename
2. **And** dirty tabs show a dot indicator after the filename
3. **And** each tab has a close button (x)
4. **And** closing a dirty tab triggers save/discard dialog (Save/Don't Save/Cancel)
5. **And** Enter triggers Save, Escape triggers Cancel, focus trapped in dialog
6. **And** tabs are draggable for reordering
7. **And** Ctrl+Tab cycles to next tab, Ctrl+Shift+Tab to previous
8. **And** TabManager is the only component that creates/focuses editor views

## Tasks / Subtasks

- [ ] Task 1: Implement dirty indicator on tabs (AC: 2)
  - [ ] Track buffer modified state in TabState
  - [ ] Render dot indicator next to filename in TabBar
  - [ ] Update indicator on buffer changed signal
- [ ] Task 2: Implement close button on each tab (AC: 3)
  - [ ] Add close button widget to each tab in TabBar
  - [ ] Connect click signal to TabManager.close_tab()
- [ ] Task 3: Implement Save/Discard dialog for dirty tabs (AC: 4, 5)
  - [ ] Create `slate/ui/dialogs/save_discard_dialog.py`
  - [ ] Implement Adw.MessageDialog with 3 buttons (Save/Don't Save/Cancel)
  - [ ] Handle Enter=Save, Escape=Cancel keyboard handling
  - [ ] Implement focus trap within dialog
  - [ ] Integrate with TabManager.close_tab() flow
- [ ] Task 4: Implement tab drag-and-drop reordering (AC: 6)
  - [ ] Use Gtk.Reorderable on TabBar
  - [ ] Update TabManager internal state on reorder
  - [ ] Persist tab order to config if needed
- [ ] Task 5: Implement tab cycling with Ctrl+Tab (AC: 7)
  - [ ] Register Ctrl+Tab and Ctrl+Shift+Tab shortcuts in actions.py
  - [ ] Implement TabManager.cycle_next() and cycle_previous()
  - [ ] Handle focus transfer correctly

## Dev Notes

### Relevant Architecture Patterns and Constraints

**Layer Architecture (STRICT):** UI layer (`slate/ui/`) imports from core and services. All GTK code is in this layer. [Source: architecture.md#Layer Architecture]

**Event Ownership:** TabManager is the ONLY component that creates editor tabs and emits FileOpenedEvent. [Source: project-context.md#Event Ownership Rules]

**Dialog Pattern:** SaveDiscardDialog must use Adw.MessageDialog for GTK4/Adwaita consistency. [Source: ux-design-specification.md#UX-DR8]

### Previous Story Intelligence

**From Story 1.6 (Main Window & Editor View):**
- TabManager already exists at `slate/ui/editor/tab_manager.py`
- TabManager handles OpenFileRequestedEvent via EventBus
- TabManager emits FileOpenedEvent after tab creation
- TabBar widget exists at `slate/ui/editor/tab_bar.py`
- EditorView buffer can track modified state via `buffer.get_modified()`
- FileService registered with ID `"file"` provides `read_file()` and `write_file()`
- SaveDiscardDialog was noted as future work in Story 1.6 (file already referenced in architecture)

**Files Created in Story 1.6:**
- `slate/ui/editor/tab_manager.py` — TabManager (partial implementation)
- `slate/ui/editor/tab_bar.py` — TabBar widget
- `slate/ui/dialogs/save_discard_dialog.py` — referenced but may need full implementation

**Lessons Learned from Story 1.6:**
- EventBus subscription pattern works well for tab lifecycle
- EditorViewFactory singleton centralizes configuration
- TabManager must be composition root for tab creation

### Source Tree Components to Touch

**Files to Modify:**
- `slate/ui/editor/tab_manager.py` — Add dirty tracking, close dialog, cycle methods
- `slate/ui/editor/tab_bar.py` — Add dirty indicator, close buttons, drag support
- `slate/ui/actions.py` — Add Ctrl+Tab, Ctrl+Shift+Tab shortcuts

**Files to Create:**
- `slate/ui/dialogs/save_discard_dialog.py` — Save/Don't Save/Cancel dialog (if not complete)
- `tests/ui/test_tab_manager.py` — Expand tests for dirty state, dialog, cycling

**Core Layer Dependencies (read-only):**
- `slate/core/models.py` — TabState has `is_dirty: bool` field
- `slate/core/events.py` — OpenFileRequestedEvent, FileOpenedEvent, FileSavedEvent

**Service Dependencies:**
- `slate/services/file_service.py` — write_file() for save action

### Testing Standards Summary

- **Coverage Requirement:** UI layer smoke/integration tests only (not chasing percentage)
- **Test Location:** `tests/ui/` mirroring source structure
- **TabManager Tests:** Add tests for: dirty indicator, save dialog trigger, dialog response handling, tab cycling, drag reorder
- Run: `pytest tests/ui/`

## Project Structure Notes

- **Alignment:** Follows layered architecture — ui/ imports from core/ and services/
- **Naming:** Files snake_case, Classes PascalCase (TabManager, TabBar, SaveDiscardDialog)
- **Event Naming:** TabActivatedEvent, TabClosedEvent — PascalCase + Event suffix

## References

- **Epic 1 Definition:** `_bmad-output/planning-artifacts/epics.md#Story 1.7: Tab Manager & Save/Discard Guard`
- **Architecture Layer Rules:** `_bmad-output/planning-artifacts/architecture.md#Layer Architecture (Section 3.1) — MANDATORY`
- **Architecture Project Structure:** `_bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure`
- **Project Context Rules:** `_bmad-output/project-context.md` — especially event ownership
- **UX Design Spec:** `_bmad-output/planning-artifacts/ux-design-specification.md#UX-DR2` (Tab Bar), `#UX-DR8` (Save/Discard Dialog)
- **Previous Story 1.6:** `_bmad-output/implementation-artifacts/1-6-main-window-editor-view.md` — TabManager pattern

## Developer Context Section

### Critical Implementation Guardrails

**ANTI-PATTERNS TO AVOID:**
- ❌ Never create editor tabs outside TabManager (violates event ownership)
- ❌ Never emit FileOpenedEvent from dialogs or other components
- ❌ Never use GTK MessageDialog — use Adw.MessageDialog for GTK4/Adwaita
- ❌ Never skip focus trap in Save/Discard dialog (accessibility requirement)
- ❌ Never use hardcoded keyboard shortcuts — all via Gio.SimpleAction

**PERFORMANCE & RELIABILITY:**
- Tab switching <50ms target
- Dirty indicator update must be immediate (buffer changed signal)
- Dialog must not block other UI

**INTEGRATION POINTS:**
- TabManager.close_tab() checks buffer.get_modified()
- SaveDiscardDialog returns: "save" | "discard" | "cancel"
- FileService.write_file() called on "save" response
- TabBar reorder updates TabManager internal list

### Technical Requirements Deep Dive

**TabState Model (from core/models.py):**
```python
@dataclass
class TabState:
    path: str
    is_dirty: bool = False
    is_active: bool = False
```

**Dirty Indicator Display:**
- TabBar renders: `{filename}` + `•` (dot) when `is_dirty == True`
- Dot color: Use accent color from Adwaita theme

**Save/Discard Dialog Contract:**
```python
class SaveDiscardDialog(Adw.MessageDialog):
    def __init__(self, parent: Gtk.Window, filename: str):
        # Adw.MessageDialog with 3 buttons
        # Response: "save" | "discard" | "cancel"
    
    async def run(self) -> str:
        # Non-blocking with GLib.idle_add or await
```

**Tab Cycling:**
- Ctrl+Tab: Cycle to next tab (wrap around)
- Ctrl+Shift+Tab: Cycle to previous tab (wrap around)
- Must handle focus transfer to EditorView in target tab

**Tab Drag Reorder:**
- Use Gtk.DragSource on tabs
- Update TabManager._tabs list order
- Emit TabReorderedEvent if needed for state persistence

### Architecture Compliance Checklist

- [ ] TabManager is ONLY component creating/focusing editor tabs
- [ ] Dirty indicator shows on TabBar when buffer.get_modified() is True
- [ ] SaveDiscardDialog uses Adw.MessageDialog with 3 responses
- [ ] Enter key = Save, Escape key = Cancel in dialog
- [ ] Focus trapped in dialog (no Tab out)
- [ ] Ctrl+Tab cycles forward, Ctrl+Shift+Tab cycles backward
- [ ] Tabs draggable for reordering
- [ ] All shortcuts registered via Gio.SimpleAction

### Library/Framework Requirements

- **PyGObject >= 3.44** — GTK4 bindings
- **libadwaita (Adw)** — Adw.MessageDialog for save/discard dialog

### File Structure Requirements

```
slate/ui/
├── editor/
│   ├── tab_manager.py           # modify - add dirty tracking, close dialog, cycle
│   ├── tab_bar.py               # modify - add dirty indicator, close button, drag
│   └── __init__.py
├── dialogs/
│   ├── __init__.py
│   └── save_discard_dialog.py  # create or verify - Save/Don't Save/Cancel
└── actions.py                   # modify - add Ctrl+Tab shortcuts

tests/ui/
├── test_tab_manager.py          # modify - add dirty, dialog, cycle tests
└── __init__.py
```

**File Content Patterns (from project-context.md):**
- Use `from __future__ import annotations`
- Class docstrings describing responsibility
- Type hints for all public methods
- Private helper methods start with `_`
- Constants at module level (UPPER_SNAKE_CASE)
- No comments unless explaining non-obvious "why"

### Testing Requirements

**TabManager Tests Must Cover:**
- Dirty indicator: Open file, modify buffer, verify dot appears
- Save dialog: Close dirty tab, verify dialog appears
- Save action: Click Save, verify file written, tab closed
- Discard action: Click Don't Save, verify tab closed, no file written
- Cancel action: Click Cancel, verify tab remains open
- Tab cycling: Ctrl+Tab moves to next tab, wraps at end
- Tab reorder: Drag tab to new position, verify order changed

**TabBar Tests Must Cover:**
- Dirty dot renders when is_dirty=True
- Close button triggers close signal
- Drag handle enables reordering

**SaveDiscardDialog Tests Must Cover:**
- All three responses returned correctly
- Enter key triggers save
- Escape key triggers cancel
- Focus cannot leave dialog (accessibility)

## Dev Agent Record

### Agent Model Used

TBD (to be filled by dev agent)

### Debug Log References

TBD

### Completion Notes List

TBD

### File List

TBD

---

## Change Log

- **Date: 2026-03-27** - Story 1.7 context created
  - Comprehensive implementation guide for Tab Manager & Save/Discard Guard
  - Builds on Story 1.6 TabManager foundation
  - Includes dirty indicators, save/discard dialog, tab cycling, drag reorder
