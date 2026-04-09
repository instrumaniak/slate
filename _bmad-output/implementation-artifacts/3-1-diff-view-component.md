# Story 3.1: Diff View Component

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want an inline diff viewer for changed files,
So that I can review changes with clear visual indicators.

## Acceptance Criteria

1. **Given** DiffView is implemented, **when** I open a changed file from Source Control, **then** the diff shows line numbers (old/new)
2. **And** additions have green background highlighting
3. **And** deletions have red background highlighting
4. **And** unified view is the default display mode
5. **And** diff renders in under 100ms for typical files
6. **And** "No changes" message shows when file has no diff

## Tasks / Subtasks

- [x] Task 1: Implement DiffView widget with unified diff rendering (AC: 1, 2, 3, 4, 5, 6)
  - [x] Subtask 1.1: Create `slate/ui/editor/diff_view.py` with DiffView widget class
  - [x] Subtask 1.2: Implement diff line parsing from git diff output (unified format)
  - [x] Subtask 1.3: Add line numbers for both old and new content
  - [x] Subtask 1.4: Style additions with green background (#2ea04320 at 12% opacity for subtle look)
  - [x] Subtask 1.5: Style deletions with red background (#f8514920 at 12% opacity for subtle look)
  - [x] Subtask 1.6: Set unified view as default display mode
  - [x] Subtask 1.7: Show "No changes" message when diff is empty
  - [x] Subtask 1.8: Ensure diff renders in under 100ms (profile and optimize)

- [x] Task 2: Add view mode toggle (unified/split) (AC: 4)
  - [x] Subtask 2.1: Add toggle button in DiffView header for unified/split view
  - [x] Subtask 2.2: Implement split view rendering (side-by-side)
  - [x] Subtask 2.3: Persist user's view mode preference via ConfigService

- [ ] Task 3: Integrate with SourceControlPlugin (AC: 1)
  - [ ] Subtask 3.1: Wire DiffView into SourceControlPlugin when file is clicked
  - [ ] Subtask 3.2: Use GitService.get_diff(path) to get diff content
  - [ ] Subtask 3.3: Handle staged vs unstaged diff via `git diff --cached` and `git diff`
  - [ ] Subtask 3.4: Open diff in read-only tab with "~ filename (diff)" label format

- [x] Task 4: Write tests (AC: 1-6)
  - [x] Subtask 4.1: Test diff parsing correctly identifies additions, deletions, context
  - [x] Subtask 4.2: Test line numbers render correctly for old and new
  - [x] Subtask 4.3: Test green highlighting on additions
  - [x] Subtask 4.4: Test red highlighting on deletions
  - [x] Subtask 4.5: Test unified view is default
  - [x] Subtask 4.6: Test split view toggle
  - [x] Subtask 4.7: Test "No changes" message for empty diff
  - [x] Subtask 4.8: Test diff renders in under 100ms (performance test)

## Dev Notes

### Relevant Architecture Patterns and Constraints

**Layer Architecture (STRICT):** DiffView is a UI layer component (`slate/ui/editor/diff_view.py`). It receives diff data from GitService and renders it using GTK4 widgets. It must NOT call git directly — only GitService does that. [Source: architecture.md#Layer Architecture, project-context.md#Critical Implementation Rules]

**Diff View Location:** According to the architecture, DiffView is in `slate/ui/editor/diff_view.py`. This is a NEW file to create. [Source: architecture.md#Complete Project Directory Structure]

**Performance Requirement:** Diff renders in under 100ms for typical files. This is a hard NFR (NFR-002). Profile during implementation; do not optimize prematurely but do not ignore. [Source: epics.md#Story 3.1 AC5]

**Source Control Integration:** DiffView is opened from SourceControlPlugin when user clicks a changed file. The diff tab is distinct from normal file tabs — it shows "~ filename (diff)" as tab label and is read-only. [Source: epics.md#Story 3.3]

**GitService Contract:** GitService.get_diff(path) returns diff text. Use `git diff` for unstaged and `git diff --cached` for staged. [Source: architecture.md#Service Boundaries]

**Event Ownership Rules:** DiffView emits no events directly. SourceControlPlugin subscribes to GitStatusChangedEvent and handles navigation. DiffView receives data through constructor/setter, not events. [Source: project-context.md#Event Ownership Rules]

**Previous Story Intelligence (Story 2.3):**
- File operations use Gtk.PopoverMenu + Gio.Menu pattern
- Notifications use SlateToast or HostUIBridge.show_notification()
- Events follow FolderOpenedEvent pattern for tree refresh
- UI uses GTK4 widgets with proper accessibility

**Previous Story Intelligence (Story 2.2):**
- FileExplorerTree uses modern GTK4 stack (ListView + TreeListModel)
- Performance is critical — lazy loading prevents UI lag
- 289+ tests passing with established patterns

### Source Tree Components to Touch

**Files to Create:**
- `slate/ui/editor/diff_view.py` — NEW DiffView widget

**Files to Modify:**
- `slate/plugins/core/source_control.py` — Wire DiffView into click handler
- `slate/services/git_service.py` — May need to verify get_diff() contract

**Files to Reference (read-only):**
- `slate/ui/editor/editor_view.py` — For tab/buffer pattern reference
- `slate/ui/editor/tab_manager.py` — For how tabs are created
- `slate/ui/panels/source_control_panel.py` — For panel structure
- `slate/services/git_service.py` — For get_diff() contract

### Diff View Anatomy (from UX)

**Structure:**
```
DiffView
├── Header (view mode toggle: unified/split)
├── LineNumbers (old | new)
├── DiffContent
│   ├── Addition lines (green background)
│   ├── Deletion lines (red background)
│   └── Context lines (no highlight)
└── Footer (file path info)
```

**Styling:**
- Addition highlighting: green background (#2ea04320 at ~12% opacity)
- Deletion highlighting: red background (#f8514920 at ~12% opacity)
- Line numbers: monospace, right-aligned, muted color
- Use GTK4 CSS classes where possible, custom CSS overlay for diff-specific styling

**Performance:**
- Target: <100ms render for typical files
- Use GtkSourceView with "diff" language for syntax highlighting
- Consider virtualized list for large diffs

### Diff Tab Format

When opened from Source Control:
- Tab label: "~ filename (diff)" (e.g., "~ main.py (diff)")
- Tab is read-only (no editing)
- Distinct from normal file tabs for the same path

### Testing Standards Summary

**Coverage Requirements:**
- UI layer: smoke/integration tests only
- GitService: 90%+ line coverage (if modified)

**Test Patterns:**
- Use temp git repos with staged/unstaged changes
- Test diff parsing with various git diff outputs
- Test view toggle preserves preference
- Performance test: measure render time, assert <100ms

**Test Commands:**
- `pytest tests/` — Run all tests
- `pytest tests/ui/editor/test_diff_view.py -v` — Run diff view tests

### Project Structure Notes

**Alignment with unified project structure:**
- DiffView in `slate/ui/editor/diff_view.py` (matches architecture spec)
- SourceControlPlugin modification in `slate/plugins/core/source_control.py`
- Tests in `tests/ui/editor/test_diff_view.py`

**Directory structure:**
```
slate/
├── ui/editor/
│   ├── diff_view.py              # NEW: DiffView widget
│   ├── editor_view.py            # Reference: tab/buffer pattern
│   └── tab_manager.py            # Reference: tab creation
├── plugins/core/
│   └── source_control.py         # MODIFY: wire DiffView
├── services/
│   └── git_service.py           # READ: get_diff() contract
tests/
├── ui/editor/
│   └── test_diff_view.py         # NEW: DiffView tests
```

### References

- **Epic 3 Definition:** `_bmad-output/planning-artifacts/epics.md#Epic 3: Source Control & Code Review`
- **Story 3.1:** `_bmad-output/planning-artifacts/epics.md#Story 3.1: Diff View Component`
- **Story 3.3:** `_bmad-output/planning-artifacts/epics.md#Story 3.3: Source Control — Inline Diff Viewing`
- **Architecture Layer Rules:** `_bmad-output/planning-artifacts/architecture.md#Layer Architecture`
- **Architecture Service Boundaries:** `_bmad-output/planning-artifacts/architecture.md#Service Boundaries`
- **UX Diff View:** `_bmad-output/planning-artifacts/ux-design-specification.md#4. Diff View`
- **UX Diff States:** `_bmad-output/planning-artifacts/ux-design-specification.md#Diff View States`
- **Project Context Rules:** `_bmad-output/project-context.md`
- **Previous Story 2.3:** `_bmad-output/implementation-artifacts/2-3-file-explorer-context-menu-file-operations.md`

## Developer Context Section

### Critical Implementation Guardrails

**ANTI-PATTERNS TO AVOID:**
- ❌ Never call git directly from DiffView — use GitService.get_diff()
- ❌ Never make diff tabs editable — DiffView is read-only
- ❌ Never block UI thread for diff computation — use threading if needed for large diffs
- ❌ Never use hardcoded colors — use CSS variables or theme-aware colors
- ❌ Never skip performance testing — 100ms is a hard requirement
- ❌ Never use plain TextView for diff — use GtkSourceView with "diff" language for proper highlighting
- ✅ Always show "~ filename (diff)" as tab label for diff tabs
- ✅ Always use GitService.get_diff() for git diff content
- ✅ Always render in under 100ms for typical files
- ✅ Always show "No changes" for empty diff
- ✅ Always use unified view as default, allow toggle to split

**DIFF VIEW REQUIREMENTS:**
- Parse unified diff format from git output
- Display line numbers for both old (left) and new (right)
- Highlight additions with green background
- Highlight deletions with red background
- Support unified view (default) and split view toggle
- Show "No changes" message when diff is empty
- Render in under 100ms

**INTEGRATION REQUIREMENTS:**
- DiffView opened when user clicks changed file in SourceControlPanel
- Uses GitService.get_diff(path) for content
- Uses `git diff --cached` for staged, `git diff` for unstaged
- Diff tab label format: "~ filename (diff)"
- Diff tab is read-only

**PERFORMANCE REQUIREMENTS:**
- Diff render time < 100ms for typical files (NFR-002)
- Profile during development; optimize if needed
- Consider virtualized list for very large diffs

### Architecture Compliance Checklist

- [ ] DiffView created in `slate/ui/editor/diff_view.py`
- [ ] Uses GitService.get_diff() for git diff content (not direct git calls)
- [ ] Shows line numbers for old and new content
- [ ] Additions have green background highlighting
- [ ] Deletions have red background highlighting
- [ ] Unified view is default display mode
- [ ] Split view toggle works and persists preference
- [ ] "No changes" message shows for empty diff
- [ ] Diff renders in under 100ms for typical files
- [ ] Diff tab labeled as "~ filename (diff)"
- [ ] Diff tab is read-only
- [ ] Uses GtkSourceView with "diff" language
- [ ] Follows layer architecture (UI only, GitService for git ops)

### Library/Framework Requirements

- **GTK4 GtkSourceView** — For diff rendering with "diff" language highlighting
- **GTK4 Gtk.TextTag** — For addition/deletion highlighting
- **GTK4 Gtk.Box** — Vertical layout for unified view
- **GTK4 Gtk.Paned** — Horizontal split for split view
- **GTK4 Gtk.ToggleButton** — View mode toggle
- **GitService.get_diff(path: str, staged: bool = False)** — Get diff text from git

### File Structure Requirements

```
slate/
├── ui/editor/
│   └── diff_view.py              # NEW: DiffView widget
├── plugins/core/
│   └── source_control.py         # MODIFY: wire DiffView on file click
tests/
├── ui/editor/
│   └── test_diff_view.py         # NEW: DiffView tests
```

### Testing Requirements

**Tests to Add:**

**Widget Tests (`tests/ui/editor/test_diff_view.py`):**
- `test_diff_view_parses_additions` — verify addition lines get correct styling
- `test_diff_view_parses_deletions` — verify deletion lines get correct styling
- `test_diff_view_parses_context` — verify context lines have no highlight
- `test_line_numbers_old_and_new` — verify line numbers render for both sides
- `test_unified_view_is_default` — verify default is unified
- `test_split_view_toggle` — verify toggle switches to split view
- `test_view_mode_persists` — verify preference saved via ConfigService
- `test_no_changes_message` — verify "No changes" shown for empty diff
- `test_performance_under_100ms` — verify render time < 100ms

**Integration Tests (if applicable):**
- `test_diff_view_opens_from_source_control` — verify clicking file opens diff tab
- `test_diff_tab_label_format` — verify "~ filename (diff)" label
- `test_staged_vs_unstaged_diff` — verify correct git command used

---

## Dev Agent Record

### Agent Model Used

minimax-m2.7

### Debug Log References

### Completion Notes List

**2026-04-09: Task 1, 2 & 4 Completed**
- Implemented DiffView widget with unified diff rendering
- DiffParser class parses unified git diff format
- Line numbers displayed for both old and new content (format: "old new")
- Additions highlighted with green background (#2ea04320)
- Deletions highlighted with red background (#f8514920)
- Unified view is default, split view toggle implemented
- "No changes" message shown for empty diffs
- Performance test confirms <100ms render time
- GTK fallback mode when GTK not available
- View mode preference persists via ConfigService (diff_view.view_mode)
- 15 tests passing covering all core functionality

**Task 3 Notes (Integration - BLOCKED)**
- SourceControlPlugin does not exist yet - part of Stories 3.2/3.3
- Integration will be completed when SourceControlPlugin is created
- DiffView is ready for integration - accepts diff_text, path, config_service parameters

### File List

 - `slate/ui/editor/diff_view.py` — NEW
 - `slate/services/config_service.py` — MODIFY (added diff_view section)
 - `slate/services/git_service.py` — READ
 - `tests/ui/editor/test_diff_view.py` — NEW
 - `tests/services/test_config_service.py` — MODIFY (updated expected config)

## Change Log

- 2026-04-09: Initial implementation - Created DiffView widget with unified/split diff rendering, line numbers, syntax highlighting, view mode toggle with ConfigService persistence, 15 tests added. All 381 tests pass. Ready for review.
- 2026-04-09: SourceControlPlugin integration deferred to Stories 3.2/3.3 - DiffView ready for wiring when plugin is created.
