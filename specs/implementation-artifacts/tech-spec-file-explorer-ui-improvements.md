---
title: 'File Explorer UI Improvements'
slug: 'file-explorer-ui-improvements'
created: '2026-04-07'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['Python 3.10+', 'GTK4', 'PyGObject', 'GtkSourceView 5']
files_to_modify:
  - 'slate/ui/panels/file_explorer_tree.py'
  - 'slate/ui/main_window.py'
code_patterns:
  - 'EventBus for cross-component communication'
  - 'Plugin system with lazy widget creation'
  - 'TabManager for tab state management'
test_patterns:
  - 'pytest in tests/'
  - 'temp_dir, temp_git_repo fixtures'
---

# Overview

## Problem Statement
4 UX issues with File Explorer:
1. Breadcrumb at top of file explorer - unwanted visual clutter
2. Opening single file via CLI doesn't show parent folder in file explorer
3. No way to toggle file explorer visibility via activity bar icon click (only drag resize)
4. Activity bar and side panel have same background - no visual differentiation

## Solution
Remove breadcrumb widget, add parent folder navigation on single file open, implement toggle behavior on activity bar icon click, add distinct CSS styling for activity bar background.

## Scope
- In: File explorer tree, main window, activity bar styling
- Out: Search panel, source control panel, other plugins

---

# Context for Development

## Codebase Patterns
- EventBus for cross-component communication (NOT GTK signals)
- Plugin system with lazy widget creation
- TabManager owns tab state, emits FileOpenedEvent
- Services use lazy GTK imports inside methods
- Config stored in ~/.config/slate/config.ini

## Files to Reference
- `slate/ui/panels/file_explorer_tree.py` - breadcrumb built in `_build_breadcrumb()` (lines 692-710), added to header at line 717
- `slate/ui/main_window.py` - `open_file_on_startup()` handles CLI file open (lines 337-351), `_on_activity_bar_item_clicked()` handles panel switching (lines 251-260)

## Technical Decisions
- Remove breadcrumb entirely vs adding toggle - user explicitly wants removal
- Auto-navigate to parent folder on single file open - show file's context
- Toggle behavior - if file explorer already shown, hide it; otherwise show it
- Activity bar distinct background - use headerbar color pattern from Adwaita

---

# Implementation Plan

## Tasks

- [ ] Task 1: Remove breadcrumb from File Explorer
  - File: `slate/ui/panels/file_explorer_tree.py`
  - Action: Remove `_breadcrumb_box` from `_build_header()` method (line 717), delete `_build_breadcrumb()` method (lines 692-710), delete `_update_breadcrumb()` method (lines 769-797), delete `_on_breadcrumb_clicked()` method (lines 799-801)
  - Notes: Keep tree navigation as replacement - users can expand folders to navigate

- [ ] Task 2: Auto-navigate to file's parent folder when opening single file via CLI
  - File: `slate/ui/main_window.py`
  - Action: In `open_file_on_startup()` (line 345-351), change `_side_panel.set_visible(False)` to call `_load_folder_in_explorer(os.path.dirname(path))` after opening the file tab
  - Notes: Handle edge case - if file at root (no parent), just show panel without loading

- [ ] Task 3: Toggle File Explorer visibility via activity bar icon click
  - File: `slate/ui/main_window.py`
  - Action: Modify `_on_activity_bar_item_clicked()` (lines 251-260) to check if current panel is already file_explorer - if yes, toggle visibility instead of always showing
  - Notes: Use existing `_on_toggle_panel()` logic pattern

- [ ] Task 4: Add distinct background color for activity bar vs side panel
  - File: `slate/ui/main_window.py`
  - Action: Change activity bar CSS class from "toolbar" to "toolbar activity-bar" or add custom CSS provider with distinct background
  - Notes: Use Adwaita headerbar background for activity bar, sidebar background for side panel

---

# Acceptance Criteria

- [ ] AC1: Given File Explorer is open, when breadcrumb bar is removed, then only tree view is visible with no path display
- [ ] AC2: Given Slate is opened with a single file via CLI (e.g., `slate /path/to/file.py`), when the file opens in a tab, then the File Explorer shows the parent folder with the file visible/highlighted
- [ ] AC3: Given File Explorer panel is visible, when user clicks the Explorer icon in activity bar, then the panel hides (toggle behavior)
- [ ] AC4: Given File Explorer panel is hidden, when user clicks the Explorer icon in activity bar, then the panel shows (toggle behavior)
- [ ] AC5: Given activity bar and side panel are displayed, when viewed, then activity bar has visually distinct background color from side panel
- [ ] AC6: Given file is at filesystem root (e.g., `/file.py`), when opened via CLI, then File Explorer shows the panel without error (graceful handling)

---

# Dependencies

- No external libraries needed
- Uses existing GTK4 CSS classes
- No new services or plugins required

---

# Testing Strategy

- Unit tests: Add tests for `open_file_on_startup` behavior in `tests/ui/test_main_window.py`
- Integration: Manual test of all 4 scenarios
- Edge case: Root-level file open

---

# Notes

- Breadcrumb removal is intentional - tree expansion provides navigation alternative
- Activity bar color differentiation follows VSCode pattern
- Toggle behavior change is minor - first click now toggles vs always shows (more intuitive)