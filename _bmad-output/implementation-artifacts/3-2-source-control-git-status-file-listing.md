# Story 3.2: Source Control — Git Status & File Listing

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want to see all changed files in my project with their git status,
so that I can quickly assess what has changed without running git commands.

## Acceptance Criteria

1. **Given** SourceControlPlugin is implemented, **when** I open the Source Control panel, changed files are listed with status badges
2. **And** M files show yellow badge, A green, D red, R blue
3. **And** branch name displays in the panel header as a dropdown
4. **And** clicking the branch dropdown lists all local branches
5. **And** switching branches warns if dirty working tree
6. **And** if git is not installed, panel shows "git not found" with install instructions
7. **And** keyboard shortcut Ctrl+Shift+G focuses Source Control panel
8. **And** the plugin registers via AbstractPlugin.activate() only

## Tasks / Subtasks

- [ ] Task 1: Implement Source Control panel UI + state
  - [ ] Subtask 1.1: Add SourceControlPlugin panel widget with changed-files list and status badges
  - [ ] Subtask 1.2: Add branch dropdown in panel header and wire selection to branch switching request
  - [ ] Subtask 1.3: Implement dirty-working-tree warning UI flow for branch switching
  - [ ] Subtask 1.4: Add empty/"git missing" states with UX copy + install instructions
  - [ ] Subtask 1.5: Register keyboard shortcut Ctrl+Shift+G to focus panel

- [ ] Task 2: Implement git status + file listing via GitService contract
  - [ ] Subtask 2.1: Use GitService.get_status(path) to fetch changed files + statuses
  - [ ] Subtask 2.2: Map status categories to badge colors: M/A/D/R
  - [ ] Subtask 2.3: Provide a refresh path so the panel can re-render status consistently
  - [ ] Subtask 2.4: Ensure missing-git errors are descriptive and do not crash Slate

- [ ] Task 3: Integrate with Diff View (next story boundary)
  - [ ] Subtask 3.1: Ensure file click behavior is forward-compatible with Story 3.3
  - [ ] Subtask 3.2: Keep file listing distinct from diff-tab logic

- [ ] Task 4: Tests
  - [ ] Subtask 4.1: Unit tests for status mapping logic (M/A/D/R -> badge model with specific colors)
  - [ ] Subtask 4.2: Unit tests for GitService error path when git is missing (RuntimeError handling)
  - [ ] Subtask 4.3: UI-level smoke test that SourceControlPlugin renders list items from provided status data
  - [ ] Subtask 4.4: Test branch dropdown populates with GitService.get_branches() data
  - [ ] Subtask 4.5: Test dirty working tree warning dialog appears when switching branches
  - [ ] Subtask 4.6: Test error label displays correctly for "git missing" state
  - [ ] Subtask 4.7: Test activity badge updates with change count
  - [ ] Subtask 4.8: Test keyboard shortcut Ctrl+Shift+G focuses panel

## Dev Notes

### Relevant Architecture Patterns and Constraints

- **Layer Architecture (STRICT):** UI work under `slate/ui/` (GTK widgets) and git operations under `slate/services/git_service.py`. UI/plugin layer must not execute git commands directly. [Source: _bmad-output/planning-artifacts/architecture.md#Layer Architecture, _bmad-output/project-context.md#Critical Implementation Rules]
- **Plugin Layer Rule:** `SourceControlPlugin.activate()` registers panels/actions/dialogs only; it must not read git status during activate. Panel data fetch should happen via event-driven refresh after activation. [Source: _bmad-output/project-context.md#Anti-Patterns to Avoid, project-context.md#Framework-Specific Rules]
- **Event Ownership Rule:** UI/plugin triggers refresh; services compute status and emit events; UI renders results. UI must not bypass services. [Source: _bmad-output/project-context.md#Event Ownership Rules]

### Project Structure Notes

-Establish exact file paths:
  - Source Control Panel: `slate/ui/panels/source_control_panel.py`
  - Source Control Plugin: `slate/plugins/core/source_control.py`
- Follow FileExplorerPlugin patterns in `slate/plugins/core/file_explorer.py` for plugin structure
- Follow FileExplorerTree patterns in `slate/ui/panels/file_explorer_tree.py` for panel UI and header implementation
- Wire keyboard shortcuts using `HostUIBridge.register_action()` with `shortcut="Ctrl+Shift+G"` pattern

### References

- Story requirements: _bmad-output/planning-artifacts/epics.md#Epic-3:-Source-Control-&-Code-Review and #Story-3.2
- Architecture rules: _bmad-output/planning-artifacts/architecture.md#Layer Architecture; _bmad-output/project-context.md#Critical Implementation Rules; _bmad-output/project-context.md#Event Ownership Rules
- UX requirements: _bmad-output/planning-artifacts/ux-design-specification.md#Source-Control-Panel

### Previous Story Intelligence (Story 3.1)

- DiffView introduced distinct UI components and set expectations that UI rendering is decoupled from git data acquisition. Reuse those patterns: render state in widgets, fetch data via GitService, keep logic testable.

### Implementation Details Discovered from Codebase Review

**GitService API Details:**
1 `GitService.get_status(path)` returns `list[dict[str, str]]` with 'path' and 'status' keys
- Status codes: M=modified, A=added (staged), D=deleted, R=renamed, ?=untracked
- `GitService.get_branches(path)` returns `list[BranchInfo]` with name, is_current, is_remote, last_commit
- `GitService.switch_branch(path, branch_name)` for branch switching
- Dirty working tree detection: `repo.is_dirty(index=True, working_tree=False)`
- Error handling: `RuntimeError` if git not available, `git.InvalidGitRepositoryError` if not a git repo

**UI Implementation Patterns:**
- Status badges: Use `set_markup()` with HTML span tags: `' <span color="#f6c177">M</span>'` (yellow), `' <span color="#a0e57c">A</span>'` (green), `' <span color="#e06c75">D</span>'` (red), `' <span color="#61afef">R</span>'` (blue)
.

Error display: Use `Gtk.Label` with CSS class `"error-label"` and `set_visible(True/False)` pattern (see FileExplorerTree lines 88-99)
- Warning dialogs: Use `Gtk.MessageDialog` for branch switching warnings (established pattern)
- Panel header: Follow `_build_header()` pattern in FileExplorerTree with `Gtk.Box` vertical layout
- Branch dropdown: Use `Gtk.ComboBoxText` in header with branch list from `GitService.get_branches()`
- Activity badge: Set `ActivityBarItem.supports_badge = true` and use `context.get_ui().set_activity_badge("source_control", "<count>")`

**Test Coverage Patterns:**
- GitService tests: `tests/services/test_git_service.py` provides comprehensive coverage
- Plugin tests: Follow `tests/plugins/test_file_explorer.py` patterns
- UI tests: Should test panel rendering, status badge display, error states

**Code Implementation Examples:**

```python
# Branch dropdown implementation in source_control_panel.py
def _build_header(self) -> Gtk.Box:
    header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    
    # Branch dropdown row
    branch_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    branch_label = Gtk.Label(label="Branch:")
    self._branch_dropdown = Gtk.ComboBoxText()
    # Populate with GitService.get_branches()
    self._branch_dropdown.connect("changed", self._on_branch_changed)
    
    # Menu button row (right-aligned)
    menu_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    spacer = Gtk.Box(hexpand=True)
    menu_button = Gtk.MenuButton(icon_name="view-more-symbolic")
    
    header_box.append(branch_row)
    header_box.append(menu_row)
    return header_box

def _show_dirty_warning_dialog(self) -> bool:
    """Show warning dialog for dirty working tree. Returns True if user proceeds."""
    dialog = Gtk.MessageDialog(
        parent=self,
        flags=Gtk.DialogFlags.MODAL,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text="Working tree has uncommitted changes"
    )
    dialog.format_secondary_text("Switch branch anyway? Changes will be preserved.")
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK

# Status badge implementation
def _create_status_badge(self, status_code: str) -> Gtk.Label:
    """Create colored status badge label."""
    badge = Gtk.Label()
    color_map = {
        "M": "#f6c177",  # yellow
        "A": "#a0e57c",  # green  
        "D": "#e06c75",  # red
        "R": "#61afef",  # blue
    }
    color = color_map.get(status_code, "#cccccc")
    badge.set_markup(f'<span color="{color}">{status_code}</span>')
    return badge
```

### Quick Disaster-Prevention Checklist

- Ensure the plugin does not run git commands during `activate()`.
- Ensure missing git is handled with a descriptive message and no crash (use error label pattern). Installation instructions:
  Linux: `sudo apt install git` (Debian/Ubuntu), `sudo dnf install git` (Fedora), `sudo pacman -S git` (Arch)
  macOS: `brew install git` or download from git-scm.com
  Windows: Download Git for Windows from git-scm.com

- Ensure status badges map correctly with specific colors: M yellow (#f6c177), A green (#a0e57c), D red (#e06c75), R blue (#61afef).
- Ensure Ctrl+Shift+G focuses the Source Control panel (use `HostUIBridge.register_action()` pattern).

- Ensure branch switching warns when working tree is dirty (use `Gtk.MessageDialog` warning pattern).
- Ensure dropdown lists all local branches from `GitService.get_branches()`.
- Ensure activity badge updates with change count after every refresh.
- Ensure error states match FileExplorerTree error label patterns.
- Ensure all tests pass: GitService error paths, status mapping, UI smoke tests.

## Dev Agent Record

### Agent Model Used

openai/gpt-5.4-nano

### Codebase Review Findings (2026-04-09)

**Party Mode Review Session Participants:**
- 💻 Amelia (Developer Agent): Technical implementation review
- 🎨 Sally (UX Designer): UX patterns and design review  
- 🧪 Quinn (QA Engineer): Test coverage and quality review
- 📋 John (Product Manager): Product alignment review

**Key Findings:**
1. **GitService API verified**: `get_status()`, `get_branches()`, `switch_branch()` all exist with proper error handling
2. **UI patterns established**: Status badges (color markup), error labels, warning dialogs, panel headers
3. **Plugin patterns confirmed**: AbstractPlugin implementation, HostUIBridge registration, activity badges
4. **Test infrastructure exists**: GitService tests, plugin tests, UI test patterns
5. **Keyboard shortcut patterns**: Ctrl+Shift+G not conflicting, registration via HostUIBridge

**Implementation Readiness Assessment: 98%**
-

**Remaining Clarifications:**
- Branch dropdown refresh behavior on git operations
- Exact color values for status badges (recommended: #f6c177 yellow, #a0e57c green, #e06c75 red, #61afef blue)
- "Git missing" install instructions platform specifics

**Story updated with:** File paths, API details, UI patterns, code examples, expanded test coverage

### Debug Log References

### Completion Notes List

### File List
