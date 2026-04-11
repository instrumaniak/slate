# Story 3.3: Source Control — Inline Diff Viewing

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to click a changed file and see its diff inline in the editor,
So that I can review changes without opening a separate tool.

## Acceptance Criteria

1. **Given** the Source Control panel shows changed files, **when** I click a changed file, a read-only diff tab opens in the editor area
2. **And** the diff tab shows "~ filename (diff)" as the tab label
3. **And** the diff uses GtkSourceView with "diff" language for syntax highlighting
4. **And** staged diffs use `git diff --cached`, unstaged use `git diff`
5. **And** the diff tab is distinct from normal file tabs for the same path
6. **And** clicking another changed file replaces the diff tab or opens a new one

## Tasks / Subtasks

- [ ] Task 1: Wire file click to diff tab opening (AC: 1, 5, 6)
  - [ ] Subtask 1.1: Add click handler in SourceControlPanel for file list items
  - [ ] Subtask 1.2: Connect file click to diff tab request event or direct call
  - [ ] Subtask 1.3: Handle multiple changed files (replace vs new tab)

- [ ] Task 2: Open diff tab in editor area (AC: 1, 2, 5)
  - [ ] Subtask 2.1: Use TabManager to open read-only diff tab
  - [ ] Subtask 2.2: Set tab label format "~ filename (diff)"
  - [ ] DiffView for rendering already exists (Story 3.1) - integrate it
  - [ ] Subtask 2.3: Make diff tab distinct from normal file tabs

- [ ] Task 3: Fetch diff content (AC: 4)
  - [ ] Subtask 3.1: Use GitService.get_diff(path, staged=False) for unstaged
  - [ ] Subtask 3.2: Use GitService.get_diff(path, staged=True) for staged
  - [ ] Subtask 3.3: Pass diff content to DiffView

- [ ] Task 4: Configure diff syntax highlighting (AC: 3)
  - [ ] Subtask 4.1: Set GtkSourceView language to "diff"
  - [ ] Subtask 4.2: Ensure diff language is available

- [ ] Task 5: Tests
  - [ ] Subtask 5.1: Test file click opens diff tab
  - [ ] Subtask 5.2: Test tab label format "~ filename (diff)"
  - [ ] Subtask 5.3: Test staged vs unstaged diff fetching
  - [ ] Subtask 5.4: Test diff tab is read-only
  - [ ] Subtask 5.5: Test multiple file clicks replace diff content
  - [ ] Subtask 5.6: Test syntax highlighting with "diff" language

## Dev Notes

### Relevant Architecture Patterns and Constraints

**Layer Architecture (STRICT):** Source Control panel is in `slate/ui/panels/source_control_panel.py`. Git operations must go through GitService. Opening tabs must go through TabManager. No direct git calls from UI layer. [Source: architecture.md#Layer Architecture, project-context.md#Critical Implementation Rules]

**Event Ownership Rules:** UI triggers requests; TabManager handles tab creation. SourceControlPanel should emit OpenDiffRequestedEvent or call TabManager directly to open diff tab. DiffView renders content, doesn't create tabs. [Source: project-context.md#Event Ownership Rules]

**DiffView Integration:** DiffView component exists from Story 3.1 in `slate/ui/editor/diff_view.py`. Reuse it for rendering diff content in the tab. [Source: implementation-artifacts/3-1-diff-view-component.md]

**GitService API:**
- `GitService.get_diff(path, staged=False)` returns diff string for unstaged changes
- `GitService.get_diff(path, staged=True)` returns diff string for staged changes
- [Source: implementation-artifacts/3-2-source-control-git-status-file-listing.md]

### Project Structure Notes

- Source Control Panel: `slate/ui/panels/source_control_panel.py`
- Source Control Plugin: `slate/plugins/core/source_control.py`
- DiffView: `slate/ui/editor/diff_view.py`
- Tab logic in MainWindow/Tab management
- Follow SourceControlPanel patterns from Story 3.2 for panel structure
- Follow DiffView patterns from Story 3.1 for diff rendering

### References

- Epic 3 Story 3.3 requirements: _bmad-output/planning-artifacts/epics.md#Story-3.3
- Story 3.1 (DiffView): _bmad-output/implementation-artifacts/3-1-diff-view-component.md
- Story 3.2 (Git Status): _bmad-output/implementation-artifacts/3-2-source-control-git-status-file-listing.md
- Architecture: _bmad-output/planning-artifacts/architecture.md#Layer Architecture
- UX: _bmad-output/planning-artifacts/ux-design-specification.md#Source-Control-Panel

### Previous Story Intelligence (Story 3.2)

- SourceControlPanel provides file listing with status badges (M yellow, A green, D red, R blue)
- Branch dropdown header with switching logic
- Panel refresh on GitStatusChangedEvent
- Error states handled for missing git
- File click handler should wire to diff viewing (this story)
- Activity badge updates on refresh

### Previous Story Intelligence (Story 3.1)

- DiffView widget exists at `slate/ui/editor/diff_view.py`
- DiffView renders unified diff format
- Green background (#2ea04320) for additions, red (#f8514920) for deletions
- Line numbers for old/new content
- "No changes" message for empty diff
- View mode toggle (unified/split) exists
- Performance: renders in under 100ms
- Task 3 integration was NOT completed - this story completes it

### Git Intelligence Summary

Recent commits show:
- SourceControlPanel file list implementation (Story 3.2)
- GitService API for status and diff
- Panel sync with MainWindow via FolderOpenedEvent
- Status badge colors defined: M #f6c177, A #a0e57c, D #e06c75, R #61afef
- Pattern: use existing components rather than reimplementing

### Implementation Details from Codebase Review

**GitService API:**
```python
# From Story 3.2 dev notes
GitService.get_diff(path, staged=False)  # returns diff string
GitService.get_diff(path, staged=True)   # returns staged diff (git diff --cached)
```

**DiffView usage:**
```python
# DiffView constructor pattern
diff_view = DiffView()
diff_view.set_diff(diff_content)  # Set diff string to render
```

**Tab Opening Pattern:**
```python
# From TabManager / MainWindow patterns
# Tab label format: "~ {filename} (diff)"
# Read-only property: view.set_editable(False)
# Language: source_view.get_buffer().set_language(lang) where lang = "diff"
```

**SourceControlPanel file item click:**
```python
# Should connect to _on_file_clicked handler
# Check file status to determine staged vs unstaged
# Call GitService.get_diff() and open tab
```

## Dev Agent Record

### Agent Model Used

_TBD during implementation_

### Completion Notes List

_TBD during implementation_

### File List

**New Files:**
- (None expected - reuse existing components)

**Modified Files:**
- `slate/ui/panels/source_control_panel.py` - Add file click handler
- `slate/ui/main_window.py` or `slate/ui/editor/diff_view.py` - Wire to TabManager
- Potentially `slate/core/events.py` - Add OpenDiffRequestedEvent if needed