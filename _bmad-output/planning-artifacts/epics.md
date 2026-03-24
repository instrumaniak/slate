---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments:
  - "prd.md"
  - "architecture.md"
  - "ux-design-specification.md"
---

# Slate - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Slate, decomposing the requirements from the PRD, UX Design Specification, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-001: Users can open files with syntax highlighting for Python, JavaScript, TypeScript, Rust, HTML, CSS, JSON, Markdown, Shell, Go, and Java | Source: Journey 2, MVP
FR-002: Users can open, close, reorder, and save tabs | Source: Journey 1, MVP
FR-003: Users receive a save/discard guard when closing tabs with unsaved changes | Source: MVP
FR-004: Users can see dirty indicators on tabs with unsaved changes | Source: Journey 1, MVP
FR-005: Users can open the editor on a folder via `slate .` | Source: Journey 1, MVP
FR-006: Users can open the editor on a specific path via `slate /path` | Source: Journey 2, MVP
FR-007: Users can browse project files in a folder tree with lazy loading | Source: Journey 1, File Explorer
FR-008: Users can create, rename, and delete files/folders via context menu | Source: File Explorer
FR-009: Users can search across project files with case, whole-word, and regex options | Source: Journey 1, Search
FR-010: Users can find and replace across files with glob filter support | Source: Search
FR-011: Users receive warnings before replacing in dirty files | Source: Search
FR-012: Users can view git status with file change badges | Source: Journey 1, Source Control
FR-013: Users can view diffs for changed files inline | Source: Journey 1, Source Control
FR-014: Users can stage and unstage files via checkboxes | Source: Journey 1, Source Control
FR-015: Users can commit staged changes with a message | Source: Journey 1, Source Control
FR-016: Users can switch branches from the source control panel | Source: Source Control
FR-017: Users can register custom plugins via the `AbstractPlugin` API | Source: Journey 3, MVP
FR-018: Plugins can register panels in the activity bar | Source: Journey 3, MVP
FR-019: Plugins can register actions and keybindings | Source: Journey 3, MVP
FR-020: Plugins can register dialogs | Source: MVP
FR-021: Plugins communicate only via EventBus or shared services | Source: Journey 3, MVP
FR-022: Built-in plugins use the same API as custom plugins | Source: Journey 3, MVP
FR-023: Users can toggle between light, dark, and system theme modes | Source: Preferences
FR-024: Users can select editor color schemes with live preview | Source: Preferences
FR-025: Editor inherits system GTK4/Adwaita theme on first launch | Source: Journey 1, MVP
FR-026: Users can configure editor font, tab width, and indentation | Source: Preferences
FR-027: Users can toggle line numbers, current line highlight, and word wrap | Source: Preferences
FR-028: Settings persist across sessions in `~/.config/slate/config.ini` | Source: Preferences

### NonFunctional Requirements

NFR-001: Cold start time from `slate .` to interactive window shall be under 2 seconds | Method: Stopwatch from CLI invocation to window ready
NFR-002: File navigation, search, and diff viewing shall have no perceptible lag (>100ms) | Method: User observation during review sessions
NFR-003: Startup time shall be 50%+ faster than VSCode (baseline 5-10 seconds) | Method: Side-by-side timing comparison
NFR-004: Zero crashes during a week of daily use (5+ days/week) | Method: Crash log monitoring over 7-day period
NFR-005: Zero terminal interruptions during a complete review cycle | Method: User observation during review sessions
NFR-006: Core and service layers shall maintain >=90% line coverage | Method: pytest-cov or equivalent
NFR-007: Plugin logic (non-widget) shall maintain >=85% line coverage | Method: pytest-cov or equivalent
NFR-008: Editor shall inherit system GTK4/Adwaita theme including light/dark mode automatically | Method: Visual verification on GNOME
NFR-009: File watching shall use native GIO/inotify with zero polling | Method: Code inspection of FileService.monitor()
NFR-010: All 4 core plugins shall use public API only | Method: Code inspection - no internal imports from plugins
NFR-011: At least one custom plugin shall be written using the public API within first month post-launch | Method: Plugin existence verification

### Additional Requirements

- Project initialization: Manual project foundation (no standard starter for Python GTK4 editor)
- Python package structure following layered architecture: slate/core/, slate/services/, slate/ui/, slate/plugins/
- pyproject.toml for modern Python packaging
- ruff for linting and formatting (latest stable)
- mypy for type checking (latest stable)
- Custom EventBus implementation (pub/sub pattern, minimal dependencies)
- gitpython >= 3.1 for git operations
- subprocess + ripgrep for search (no os.walk fallback in v1)
- configparser (INI) for config storage at ~/.config/slate/config.ini
- pytest + pytest-cov for testing
- Graceful degradation for missing dependencies (ripgrep, git, GTK4 packages)
- Core layer: Plain Python dataclasses, ABCs, event bus, plugin API contracts. Zero GTK. Zero I/O.
- Service layer: File I/O, git operations, config, search. Depends only on core. Zero GTK.
- UI layer: GTK widgets and window layout. Calls services; listens to event bus.
- Plugin layer: Each plugin is a self-contained package depending only on core ABCs.
- Lazy GTK imports in service layer where possible
- Events defined as dataclasses with Event suffix (FileOpenedEvent, GitStatusChangedEvent, etc.)
- GitHub Actions CI workflow (.github/workflows/ci.yml)
- Makefile for development shortcuts
- Scripts: install-deps.sh, run-tests.sh, lint.sh
- System dependencies (apt): python3-gi, python3-gi-cairo, gir1.2-gtk-4.0, gir1.2-gtksource-5, gir1.2-adw-1, git, ripgrep
- Python 3.10+ required with explicit version check in main.py
- XDG symbolic icons for activity bar (folder-symbolic, system-search-symbolic, vcs-changed-symbolic)

### UX Design Requirements

UX-DR1: Activity Bar - 48px wide vertical bar with icon buttons (32x32), active indicator, tab navigation, arrow keys, tooltips | P0
UX-DR2: Tab Bar - 35px height bar with filename + dirty indicator (dot) + close button, draggable reordering, Ctrl+Tab cycling | P0
UX-DR3: File Explorer Tree - Tree view with expand/collapse, folder/file icons, 16px indentation, context menu, filter input, breadcrumbs | P0
UX-DR4: Diff View - Split/unified view toggle, line numbers, addition/deletion highlighting (green/red), stage checkbox per file | P1
UX-DR5: Source Control Panel - Branch name header, changed files list with status badges (M/A/D/R), inline diff, commit bar | P0
UX-DR6: Search Panel - Search input with case/regex/whole-word options, replace toggle (Ctrl+H), results list grouped by file | P1
UX-DR7: Commit Bar - Multi-line TextView, character count, Commit button (enabled only when staged + message), Ctrl+Enter submit | P1
UX-DR8: Save/Discard Dialog - Three buttons (Save/Don't Save/Cancel), Enter=Save, Escape=Cancel, focus trap | P0
UX-DR9: GTK4/Adwaita Design System - System theme inheritance, Adwaita CSS classes, custom CSS overlay for editor theming | P0
UX-DR10: Keyboard Shortcuts - VSCode-compatible shortcuts, tooltips show shortcuts, all actions keyboard accessible | P0
UX-DR11: Feedback Patterns - Toast notifications (commit success, save, errors), state indicators (dirty dot, stage checkbox, spinner) | P1
UX-DR12: Accessibility - WCAG 2.1 AA, GNOME accessibility, screen reader (Orca), high contrast mode, focus indicators, 44x44px touch targets | P1
UX-DR13: Color System - Platform-inherited GTK4/Adwaita colors, GtkSourceView style schemes (monokai, solarized, dracula), accent follows system | P1
UX-DR14: Empty States - Icon + message + action for empty folders, clean git, no search results, no files open | P2
UX-DR15: Loading States - Instant (<100ms no indicator), Fast (skeleton/spinner), Slow (progress + cancel >2s) | P2
UX-DR16: Responsive Layout - Minimum 800x600, default 1200x800, side panel resizable (200px-50%), Ctrl+B toggle | P1
UX-DR17: GNOME System Integration - Respect high contrast, reduced motion, screen reader state via Gtk.Settings | P1

### FR Coverage Map

FR-001: Epic 1 - Editor Core (syntax highlighting)
FR-002: Epic 1 - Editor Core (tab management)
FR-003: Epic 1 - Editor Core (save/discard guard)
FR-004: Epic 1 - Editor Core (dirty indicators)
FR-005: Epic 1 - Editor Core (CLI folder opening)
FR-006: Epic 1 - Editor Core (CLI file opening)
FR-007: Epic 2 - File Explorer (folder tree with lazy loading)
FR-008: Epic 2 - File Explorer (create/rename/delete)
FR-009: Epic 4 - Search & Replace (project-wide search)
FR-010: Epic 4 - Search & Replace (find & replace with glob)
FR-011: Epic 4 - Search & Replace (dirty file warning)
FR-012: Epic 3 - Source Control (git status badges)
FR-013: Epic 3 - Source Control (inline diff viewing)
FR-014: Epic 3 - Source Control (stage/unstage checkboxes)
FR-015: Epic 3 - Source Control (commit workflow)
FR-016: Epic 3 - Source Control (branch switching)
FR-017: Epic 6 - Plugin Extensibility (AbstractPlugin API)
FR-018: Epic 6 - Plugin Extensibility (panel registration)
FR-019: Epic 6 - Plugin Extensibility (action/keybinding registration)
FR-020: Epic 6 - Plugin Extensibility (dialog registration)
FR-021: Epic 6 - Plugin Extensibility (EventBus communication)
FR-022: Epic 6 - Plugin Extensibility (same API for built-in)
FR-023: Epic 5 - Theme & Preferences (light/dark/system toggle)
FR-024: Epic 5 - Theme & Preferences (editor color schemes)
FR-025: Epic 1 - Editor Core (system theme on first launch)
FR-026: Epic 5 - Theme & Preferences (font/tab/indent config)
FR-027: Epic 5 - Theme & Preferences (display toggles)
FR-028: Epic 5 - Theme & Preferences (config persistence)

## Epic List

### Epic 1: Editor Core & Project Startup
Users can launch Slate from the CLI, open files and folders, edit with syntax highlighting, manage tabs, and save — the complete foundation for all other features.
**FRs covered:** FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-025

### Epic 2: File Explorer & Project Navigation
Users can browse their project in a folder tree, navigate directories, and create/rename/delete files — no more switching to the file manager.
**FRs covered:** FR-007, FR-008

### Epic 3: Source Control & Code Review
Users can view git changes, review inline diffs, stage/unstage files, commit, and switch branches — the complete review workflow without touching the terminal.
**FRs covered:** FR-012, FR-013, FR-014, FR-015, FR-016

### Epic 4: Search & Replace
Users can search across their entire project with ripgrep-powered results and find/replace with powerful filters and glob support.
**FRs covered:** FR-009, FR-010, FR-011

### Epic 5: Theme & Preferences
Users can customize editor appearance, font, display options, and theme mode with settings persisting across sessions.
**FRs covered:** FR-023, FR-024, FR-026, FR-027, FR-028

### Epic 6: Plugin Extensibility
Users and developers can extend Slate with custom plugins using the public API — register panels, actions, keybindings, and dialogs without touching core code.
**FRs covered:** FR-017, FR-018, FR-019, FR-020, FR-021, FR-022

---

## Epic 1: Editor Core & Project Startup

Users can launch Slate from the CLI, open files and folders, edit with syntax highlighting, manage tabs, and save — the complete foundation for all other features.

### Story 1.1: Project Initialization & Packaging

As a developer,
I want a properly structured Python project with pyproject.toml and directory layout,
So that I have a clean foundation to build all layers on top of.

**Acceptance Criteria:**

**Given** the repository root
**When** I inspect the directory structure
**Then** it contains pyproject.toml, slate/ package, tests/ directory, scripts/, docs/, and data/schemes/
**And** pyproject.toml declares Python >=3.10, PyGObject >=3.44, gitpython >=3.1 as dependencies
**And** dev dependencies include pytest, pytest-cov, ruff, mypy
**And** `python -m slate` runs without import errors (prints version or placeholder)

### Story 1.2: Core Layer — Models, Events & EventBus

As a developer,
I want data models, event definitions, and a pub/sub EventBus in slate/core/,
So that all layers share consistent data structures and communicate without coupling.

**Acceptance Criteria:**

**Given** the core layer is implemented
**When** I inspect slate/core/models.py
**Then** it defines FileStatus, TabState, SearchResult, BranchInfo as dataclasses
**And** slate/core/events.py defines FileOpenedEvent, FileSavedEvent, GitStatusChangedEvent, ThemeChangedEvent as dataclasses with Event suffix
**And** slate/core/event_bus.py provides subscribe(event_type, handler), emit(event), and unsubscribe
**And** all core modules import zero GTK packages
**And** tests in tests/core/ achieve 90%+ coverage

### Story 1.3: Plugin API Contracts & PluginManager

As a developer,
I want AbstractPlugin, PluginContext, HostUIBridge, and a PluginManager,
So that all plugins (built-in and custom) have a consistent extension interface and lifecycle.

**Acceptance Criteria:**

**Given** the plugin API is implemented
**When** I inspect slate/core/plugin_api.py
**Then** AbstractPlugin has an abstract activate(context) method
**And** PluginContext provides get_service(service_id), get_config(section, key), set_config(section, key, value), and emit(event)
**And** HostUIBridge provides register_panel(), register_action(), register_dialog() methods
**And** PluginManager loads plugins, calls activate(context), and catches plugin errors gracefully
**And** the API has zero GTK imports
**And** tests in tests/core/ and tests/services/ validate the contracts

### Story 1.4: Services Layer — ConfigService & ThemeService

As a user,
I want my preferences saved and the editor to match my system theme,
So that settings persist and the editor feels native on first launch.

**Acceptance Criteria:**

**Given** ConfigService is implemented
**When** I set a config value, it persists to ~/.config/slate/config.ini
**And** DEFAULT_CONFIG provides sensible defaults matching the PRD specification
**And** missing config file creates one with defaults on first run
**And** the service has zero GTK imports (uses configparser from stdlib)
**Given** ThemeService is implemented
**When** resolve_theme() is called, it returns (color_mode, is_dark, editor_scheme)
**And** ThemeChangedEvent is emitted on mode changes
**And** the service has zero GTK imports at module level (lazy import for system detection)
**And** tests in tests/services/ achieve 90%+ coverage for both services

### Story 1.5: Services Layer — FileService & GitService

As a user,
I want instant file operations and live git status,
So that the editor never lags when reading files or checking version control.

**Acceptance Criteria:**

**Given** FileService is implemented
**When** I call list_directory(path) it returns files and folders with metadata
**And** read_file(path) returns file contents
**And** write_file(path, content) writes and emits FileSavedEvent
**And** monitor_directory(path) starts GIO FileMonitor (inotify, zero polling)
**Given** GitService is implemented
**When** I call get_status(path) it returns changed files with status (M/A/D/R)
**And** get_diff(path) returns the diff text
**And** stage_file/unstage_file update the git index
**And** commit(message) creates a commit with staged changes
**And** get_branches()/switch_branch() manage branches
**And** GitStatusChangedEvent is emitted after status-altering operations
**And** if git is not installed, methods raise descriptive errors (not crashes)
**And** both services have zero GTK imports at module level
**And** tests in tests/services/ achieve 90%+ coverage

### Story 1.6: Main Window & Editor View

As a user,
I want a native GTK4/Adwaita window with a GtkSourceView editor,
So that I can open, edit, and save files with syntax highlighting.

**Acceptance Criteria:**

**Given** the main window is implemented
**When** I run `slate /path/to/file` the file opens with syntax highlighting
**And** syntax highlighting works for: Python, JavaScript, TypeScript, Rust, HTML, CSS, JSON, Markdown, Shell, Go, Java
**And** the window uses GTK4/Adwaita with system theme inheritance
**And** window dimensions restore from config (app.window_width, app.window_height)
**And** ThemeService initializes before window presentation (no theme flash)
**And** all PRD keyboard shortcuts are registered (Ctrl+T, Ctrl+W, Ctrl+S, Ctrl+O, Ctrl+Z, Ctrl+Y, Ctrl+Tab, Ctrl+Shift+Tab, Ctrl+B)
**And** startup time is under 2 seconds from CLI invocation

### Story 1.7: Tab Manager & Save/Discard Guard

As a user,
I want a tab bar with dirty indicators and save protection,
So that I can manage multiple open files and never lose work.

**Acceptance Criteria:**

**Given** TabManager is implemented
**When** I open a file, a tab appears with the filename
**And** dirty tabs show a dot indicator after the filename
**And** each tab has a close button (x)
**And** closing a dirty tab triggers save/discard dialog (Save/Don't Save/Cancel)
**And** Enter triggers Save, Escape triggers Cancel, focus trapped in dialog
**And** tabs are draggable for reordering
**And** Ctrl+Tab cycles to next tab, Ctrl+Shift+Tab to previous
**And** TabManager is the only component that creates/focuses editor views

### Story 1.8: CLI Entry Point & Startup Sequence

As a user,
I want to launch Slate from the terminal with `slate .` or `slate /path`,
So that I can open projects and files instantly.

**Acceptance Criteria:**

**Given** the CLI entry point is implemented
**When** I run `slate .` the editor opens with the current folder loaded
**When** I run `slate /path/to/folder` the folder loads with side panel visible
**When** I run `slate /path/to/file` the file opens in editor tab (no sidebar)
**When** I run `slate` with no args and last_folder exists, it restores that folder
**When** I run `slate` with no args and no last_folder, blank window appears
**And** CLI path always wins over persisted last_folder
**And** Python version is checked with clear error if <3.10
**And** missing GTK4 packages show clear error with apt install command
**And** startup sequence follows PRD: config → theme → window → plugins → restore → resolve CLI → present

### Story 1.9: Development Tooling & CI

As a developer,
I want linting, type checking, testing, and CI configured,
So that code quality is enforced from the first commit.

**Acceptance Criteria:**

**Given** the tooling is configured
**When** I run `ruff check slate/` it passes without errors
**When** I run `mypy slate/` it passes without errors
**When** I run `pytest tests/` all existing tests pass
**And** Makefile provides targets: lint, typecheck, test, format
**And** .github/workflows/ci.yml runs lint + typecheck + test on push
**And** scripts/install-deps.sh installs system packages via apt
**And** .gitignore excludes __pycache__, .mypy_cache, .pytest_cache, *.egg-info

---

## Epic 2: File Explorer & Project Navigation

Users can browse their project in a folder tree, navigate directories, and create/rename/delete files — no more switching to the file manager.

### Story 2.1: File Explorer Plugin

As a user,
I want a file tree showing my project structure,
So that I can browse and open files without leaving the editor.

**Acceptance Criteria:**

**Given** FileExplorerPlugin is implemented
**When** I activate the Explorer panel, a tree view shows the loaded folder
**And** folders expand/collapse with lazy loading (no full tree scan)
**And** clicking a file opens it in a new tab via OpenFileRequestedEvent
**And** right-click shows context menu with Create File, Create Folder, Rename, Delete
**And** file/folder operations (create, rename, delete) work via FileService
**And** the plugin registers via AbstractPlugin.activate() only — no internal imports
**And** panel icon uses "folder-symbolic" XDG icon
**And** keyboard shortcut Ctrl+Shift+O opens folder
**And** the explorer shows file/folder icons matching system theme
**And** breadcrumb path shows current folder location

---

## Epic 3: Source Control & Code Review

Users can view git changes, review inline diffs, stage/unstage files, commit, and switch branches — the complete review workflow without touching the terminal.

### Story 3.1: Diff View Component

As a user,
I want an inline diff viewer for changed files,
So that I can review changes with clear visual indicators.

**Acceptance Criteria:**

**Given** DiffView is implemented
**When** I open a changed file from Source Control
**Then** the diff shows line numbers (old/new)
**And** additions have green background highlighting
**And** deletions have red background highlighting
**And** unified view is the default display mode
**And** diff renders in under 100ms for typical files
**And** "No changes" message shows when file has no diff

### Story 3.2: Source Control Plugin

As a user,
I want a source control panel with git status, diffs, staging, and commit,
So that I can complete full review sessions without touching the terminal.

**Acceptance Criteria:**

**Given** SourceControlPlugin is implemented
**When** I open the Source Control panel, changed files are listed with status badges
**And** M files show yellow badge, A green, D red, R blue
**And** clicking a file opens an inline diff via DiffView
**And** each file has a stage/unstage checkbox
**And** staged count badge updates immediately on toggle
**And** commit bar shows: multi-line message input + Commit button
**And** Commit button is disabled until staged files exist AND message is entered
**And** Ctrl+Enter submits the commit
**And** successful commit shows toast notification and clears the panel
**And** branch name displays in the panel header
**And** clicking branch opens branch switcher
**And** if git is not installed, panel shows "git not found" with install instructions
**And** the plugin registers via AbstractPlugin.activate() only
**And** keyboard shortcut Ctrl+Shift+G focuses Source Control panel

---

## Epic 4: Search & Replace

Users can search across their entire project with ripgrep-powered results and find/replace with powerful filters and glob support.

### Story 4.1: SearchService — Project Search via ripgrep

As a user,
I want fast project-wide search using ripgrep,
So that finding code across my project is instant.

**Acceptance Criteria:**

**Given** SearchService is implemented
**When** I call search(query, path, case_sensitive=False, whole_word=False, regex=False, glob=None)
**Then** it returns a list of SearchResult(path, line, column, content, match_length)
**And** search uses subprocess + ripgrep binary (no os.walk fallback)
**And** SearchResultsReadyEvent is emitted with results
**And** if ripgrep is not installed, search raises a descriptive error with install instructions
**And** the service has zero GTK imports at module level
**And** tests in tests/services/test_search_service.py achieve 90%+ coverage

### Story 4.2: Search Plugin

As a user,
I want a search panel with case/regex/whole-word options and replace,
So that I can find and replace code across my entire project.

**Acceptance Criteria:**

**Given** SearchPlugin is implemented
**When** I open the Search panel, a search input with options is shown
**And** typing a query and pressing Enter triggers SearchService.search()
**And** results display grouped by file with file:line:content format
**And** clicking a result opens the file at that line
**And** options include: Case Sensitive, Whole Word, Regex toggles
**And** Ctrl+Shift+F focuses the search panel
**And** Ctrl+H toggles replace mode with replace input
**And** replace applies changes with confirmation for dirty files (FR-011)
**And** glob filter option is available
**And** if ripgrep is missing, panel shows install instructions (not a crash)
**And** the plugin registers via AbstractPlugin.activate() only

---

## Epic 5: Theme & Preferences

Users can customize editor appearance, font, display options, and theme mode with settings persisting across sessions.

### Story 5.1: Preferences Plugin

As a user,
I want a preferences panel where I can configure editor settings,
So that I can customize font, theme, and display options.

**Acceptance Criteria:**

**Given** PreferencesPlugin is implemented
**When** I open Preferences (Ctrl+,), grouped settings are displayed
**And** editor font, tab width, indentation are configurable
**And** line numbers, current line highlight, word wrap are toggleable
**And** theme mode (light/dark/system) is selectable
**And** editor color scheme is selectable with live preview
**And** changes apply immediately (live preview for theme)
**And** settings persist to ~/.config/slate/config.ini via ConfigService
**And** the plugin registers via AbstractPlugin.activate() only
**And** keyboard shortcut Ctrl+, opens Preferences

---

## Epic 6: Plugin Extensibility

Users and developers can extend Slate with custom plugins using the public API — register panels, actions, keybindings, and dialogs without touching core code.

### Story 6.1: Plugin Developer Experience & Documentation

As a developer,
I want clear documentation and a working example of the plugin API,
So that I can build custom plugins confidently.

**Acceptance Criteria:**

**Given** the plugin API is public
**When** I read the plugin documentation in docs/api/plugins.md
**Then** it covers AbstractPlugin, PluginContext, and HostUIBridge with examples
**And** all 4 core plugins (Explorer, Search, Source Control, Preferences) use only the public API — code inspection confirms no internal imports
**And** at least one custom plugin can be written and loaded within an hour using the docs
**And** plugin errors (syntax, API misuse) are caught, logged, and shown to the user without crashing Slate
