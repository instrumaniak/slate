---
stepsCompleted: [step-01-init, step-01b-complete, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain, step-06-functional-requirements, step-07-non-functional-requirements]
classification:
  projectType: desktop_app
  domain: developer_tool
  complexity: medium
  projectContext: brownfield
inputDocuments:
  - "product-brief-slate-2026-03-24.md"
  - "docs/slate-spec.md"
workflowType: 'prd'
date: 2026-03-24
documentCounts:
  productBriefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 1
---

# Product Requirements Document - Slate

**Author:** Raziur
**Date:** 2026-03-24

## Executive Summary

Slate is a lightweight, native Linux code editor built for the AI-assisted review workflow. Developers using AI coding agents now spend more time reviewing generated code than writing from scratch, yet every major editor still optimizes for writing. Slate flips that: it makes code reviewing a breeze.

The editor launches in under 2 seconds on Ubuntu/Linux by leveraging native system tools — `ripgrep` for search, system `git` for version control, GIO/inotify for file watching. Python orchestrates; the OS executes. No Electron. No JVM. No compile step. Just `slate .` and it's there.

Slate's plugin-first architecture means every core feature — file explorer, search, source control, preferences — is itself a plugin built on a public API. The same extension model available to built-in features is available to custom plugins. Add capabilities without destabilizing the foundation.

The UX is deliberately familiar: VSCode's activity bar, file explorer, search panel, source control panel — but native GTK4/Adwaita, inheriting system themes automatically. Developers feel at home immediately, then realize the editor disappears into the background and lets them focus on the code.

### What Makes This Special

Two equal pillars define Slate:

**Performance through native Linux tools.** Python's deep Linux system bindings replace pure-Python implementations wherever possible. `ripgrep` over `os.walk`. System `git` over reimplementations. GIO/inotify over polling. The result: sub-2-second cold start, zero-friction navigation, and an editor that stays out of the way during review sessions.

**Plugin-first extensibility.** Core features ARE plugins. The `AbstractPlugin` API, `PluginContext`, and `HostUIBridge` contract ensure every panel, action, and keybinding is registered through a consistent extension model. Future features — LSP, terminal, split panes — drop in without touching the shell. The editor grows with the user.

**Core insight:** Existing editors optimize for code *writing*. AI agents shifted the developer's primary activity to code *reviewing*. No tool was designed for that workflow — fast access to diffs, search, and file navigation without touching the terminal. Slate is.

## Project Classification

| Field | Value |
|-------|-------|
| **Project Type** | Desktop App (Linux) |
| **Domain** | Developer Tool |
| **Complexity** | Medium |
| **Project Context** | Brownfield (existing docs, greenfield implementation) |

## Success Criteria

### User Success

1. **Instant availability:** Slate launches in under 2 seconds on a modern Linux machine. Cold start from `slate .` to interactive window.
2. **Zero context-switching during review:** Complete a full review cycle (open file → navigate to diff → review → stage → commit) without switching to another editor or terminal.
3. **Daily driver adoption:** Slate becomes the primary tool for code review and minor edits, used at least 5 days per week.
4. **Navigation friction elimination:** Open files, search across project, and navigate diffs without perceptible lag or loading states.
5. **Zero-config theming:** Editor inherits system GTK4/Adwaita theme on first launch — light/dark mode switches automatically with no configuration.

### Business Success

1. **Personal productivity:** Reduce time spent on editor startup and navigation friction by 50%+ compared to VSCode.
2. **Architectural quality:** Maintain 90%+ test coverage on core and service layers. Prove the layered architecture is testable and maintainable.
3. **Plugin ecosystem proof:** Ship 4 core plugins (Explorer, Search, Source Control, Preferences) all using the same public API — no internal shortcuts.

### Technical Success

1. **Performance:** Sub-2-second cold start. No perceptible lag in file navigation, search, or diff viewing.
2. **Reliability:** Zero crashes during a week of daily use.
3. **Test coverage:** 90%+ line coverage on `core/` and `services/` layers. 85%+ on non-widget plugin logic.
4. **Native integration:** GTK4/Adwaita theme inheritance, GIO/inotify file watching, system git integration — no abstraction layers fighting the OS.

### Measurable Outcomes

| Outcome | Target | Timeframe |
|---------|--------|-----------|
| Cold-start time | < 2 seconds | v1 launch |
| Terminal interruptions per review session | 0 | Ongoing |
| Core + service test coverage | ≥ 90% | v1 launch |
| Core plugins shipped | 4 | v1 launch |
| Editor crash rate | 0 in a week of daily use | Ongoing |
| Custom plugin written using public API | ≥ 1 | First month post-launch |

## Product Scope

### MVP - Minimum Viable Product

- GtkSourceView editor with syntax highlighting for common languages
- Tab management: open, close, reorder, dirty indicators, save/discard guard
- Plugin system: `AbstractPlugin`, `PluginContext`, `HostUIBridge`, event bus
- Four core plugins: File Explorer, Search, Source Control, Preferences
- GTK4/Adwaita native theme inheritance
- CLI: `slate .`, `slate /path/to/folder`, `slate /path/to/file`
- 90%+ test coverage on core and service layers
- Sub-2-second cold start

### Growth Features (Post-MVP)

- LSP client plugin for code completion and diagnostics
- Terminal plugin for integrated shell
- Split editor panes for side-by-side editing
- Third-party plugin loading from `~/.config/slate/plugins/`
- Git log and blame viewer
- Remote/SSH file backend

### Vision (Future)

- Full extensible plugin ecosystem
- Community-driven plugin contributions
- Multi-workspace root support
- Outline plugin for symbol navigation

## User Journeys

### Journey 1: Raziur — The Daily Review Workflow (Primary User)

**Opening Scene:** It's Monday morning. You've got an AI agent that just generated 200 lines of refactoring across 8 files. In VSCode, you'd wait 8 seconds for it to load, then fumble through file navigation. Today is different.

**Rising Action:** You type `slate .` in the terminal. Before your finger leaves the Enter key, the editor is open. File explorer shows your project. The Source Control panel already has 8 files with badges showing changes. You click the first file — a diff tab opens instantly. Green additions, red deletions. You stage it with a checkbox. Next file. Stage. Next. The editor never lags, never loads, never makes you wait.

**Climax:** You finish reviewing all 8 files, write a commit message, hit Commit. Done. You never touched the terminal. You never opened another editor. The entire review session took 3 minutes instead of 8.

**Resolution:** Slate has become invisible — exactly what an editor should be. You focus on the code, not the tool. The AI agent generated the code; you reviewed it. The workflow is seamless.

**Capabilities revealed:** Fast startup, file explorer, source control panel with diff viewer, stage/unstage checkboxes, commit workflow, zero terminal interruptions.

---

### Journey 2: Raziur — The Quick Edit (Primary User, Edge Case)

**Opening Scene:** You're in the terminal and need to fix a typo in a config file. In VSCode, you'd wait 8 seconds. In Vim, you'd struggle with navigation. Today, you type `slate config.yaml`.

**Rising Action:** The file opens instantly. You see syntax highlighting. You fix the typo, hit Ctrl+S. Done. Close the tab. Back to terminal.

**Climax:** The entire interruption lasted 15 seconds. No context switching. No waiting. No "where was I?" moment.

**Resolution:** Slate earned its place as your default editor for quick edits too — not just reviews. The sub-2-second launch means even micro-edits don't break flow.

**Capabilities revealed:** CLI single-file opening, instant launch, syntax highlighting, save, minimal friction for small tasks.

---

### Journey 3: Raziur — Extending the Tool (Primary User, Plugin Journey)

**Opening Scene:** You've been using Slate for a month. The core plugins work great, but you want a custom workflow — maybe a plugin that integrates with your specific AI agent's output format.

**Rising Action:** You open the plugin API docs. `AbstractPlugin`, `PluginContext`, `HostUIBridge` — the same interfaces the core plugins use. You create a new plugin, register a panel and an action. The plugin loads alongside the built-in ones. No core changes. No instability.

**Climax:** Your custom plugin shows a panel in the activity bar. It reads AI agent output, formats it, and lets you navigate changes. The plugin system works exactly as designed — extensibility without compromise.

**Resolution:** You've proven the plugin-first architecture. The editor grows with you. Future features don't require forking or patching — they just drop in.

**Capabilities revealed:** Plugin API, `AbstractPlugin` interface, `PluginContext` service access, `HostUIBridge` panel/action registration, plugin isolation, extensibility without core modification.

### Journey Requirements Summary

| Journey | Key Capabilities Required |
|---------|---------------------------|
| Daily Review | Fast startup, file explorer, source control panel, diff viewer, stage/unstage, commit, zero terminal interruptions |
| Quick Edit | CLI single-file opening, instant launch, syntax highlighting, save |
| Plugin Extension | Plugin API, `AbstractPlugin`, `PluginContext`, `HostUIBridge`, plugin isolation, extensibility |
| Theme Inheritance | GTK4/Adwaita system theme, light/dark auto-switching, zero-config |
| Navigation | File search (`ripgrep`), project-wide navigation, diff navigation without lag |

## Domain-Specific Requirements

### Linux System Integration Constraints

Slate bets on the OS, not abstracting away from it. Performance comes from native tools, not pure-Python reimplementations.

**Required System Packages (apt):**
```
python3  python3-gi  python3-gi-cairo
gir1.2-gtk-4.0  gir1.2-gtksource-5
```

**Required External Tools:**
- `git` — system git binary for VCS operations
- `ripgrep` — for project-wide file search

**Python Requirements:**
- Python 3.10+ (type hints, `match` statements, modern typing)
- PyGObject >= 3.44 (GTK4 bindings)
- gitpython >= 3.1 (Pythonic git wrapper)

### Graceful Degradation

Missing dependencies must fail with actionable messages, not crashes:

| Missing Dependency | Behavior |
|-------------------|----------|
| `ripgrep` | Search panel shows install instructions (`sudo apt install ripgrep`) |
| `git` | Source Control panel shows "git not installed" with install instructions |
| GTK4 system packages | Clear error on startup: missing system packages, with `apt install` command |
| Python version too old | Explicit check in `main.py` with version requirement message |

### Platform Scope

- **Target:** Ubuntu/Linux (22.04+)
- **No cross-platform:** v1 is Linux-only — no Windows, no macOS
- **Theme:** GTK4/Adwaita theme inheritance depends on system having Adwaita themes installed
- **Icons:** XDG symbolic icons require standard icon theme

### Integration Requirements

- **File watching:** GIO `FileMonitor` (native inotify, no polling)
- **Git operations:** System `git` binary via gitpython — no reimplemented git logic
- **Search:** `ripgrep` binary via subprocess — no `os.walk` fallback in v1
- **Syntax highlighting:** GtkSourceView 5 language definitions — bundled with system package

## Functional Requirements

### Editor Core

| ID | Requirement | Source |
|----|-------------|--------|
| FR-001 | Users can open files with syntax highlighting for Python, JavaScript, TypeScript, Rust, HTML, CSS, JSON, Markdown, Shell, Go, and Java | Journey 2, MVP |
| FR-002 | Users can open, close, reorder, and save tabs | Journey 1, MVP |
| FR-003 | Users receive a save/discard guard when closing tabs with unsaved changes | MVP |
| FR-004 | Users can see dirty indicators on tabs with unsaved changes | Journey 1, MVP |

### File Operations

| ID | Requirement | Source |
|----|-------------|--------|
| FR-005 | Users can open the editor on a folder via `slate .` | Journey 1, MVP |
| FR-006 | Users can open the editor on a specific path via `slate /path` | Journey 2, MVP |
| FR-007 | Users can browse project files in a folder tree with lazy loading | Journey 1, File Explorer |
| FR-008 | Users can create, rename, and delete files/folders via context menu | File Explorer |
| FR-009 | Users can search across project files with case, whole-word, and regex options | Journey 1, Search |
| FR-010 | Users can find and replace across files with glob filter support | Search |
| FR-011 | Users receive warnings before replacing in dirty files | Search |

### Source Control

| ID | Requirement | Source |
|----|-------------|--------|
| FR-012 | Users can view git status with file change badges | Journey 1, Source Control |
| FR-013 | Users can view diffs for changed files inline | Journey 1, Source Control |
| FR-014 | Users can stage and unstage files via checkboxes | Journey 1, Source Control |
| FR-015 | Users can commit staged changes with a message | Journey 1, Source Control |
| FR-016 | Users can switch branches from the source control panel | Source Control |

### Plugin System

| ID | Requirement | Source |
|----|-------------|--------|
| FR-017 | Users can register custom plugins via the `AbstractPlugin` API | Journey 3, MVP |
| FR-018 | Plugins can register panels in the activity bar | Journey 3, MVP |
| FR-019 | Plugins can register actions and keybindings | Journey 3, MVP |
| FR-020 | Plugins can register dialogs | MVP |
| FR-021 | Plugins communicate only via EventBus or shared services | Journey 3, MVP |
| FR-022 | Built-in plugins use the same API as custom plugins | Journey 3, MVP |

### Theme and Appearance

| ID | Requirement | Source |
|----|-------------|--------|
| FR-023 | Users can toggle between light, dark, and system theme modes | Preferences |
| FR-024 | Users can select editor color schemes with live preview | Preferences |
| FR-025 | Editor inherits system GTK4/Adwaita theme on first launch | Journey 1, MVP |

### Preferences

| ID | Requirement | Source |
|----|-------------|--------|
| FR-026 | Users can configure editor font, tab width, and indentation | Preferences |
| FR-027 | Users can toggle line numbers, current line highlight, and word wrap | Preferences |
| FR-028 | Settings persist across sessions in `~/.config/slate/config.ini` | Preferences |

---

## Non-Functional Requirements

### Performance

| ID | Requirement | Measurement Method | Source |
|----|-------------|-------------------|--------|
| NFR-001 | Cold start time from `slate .` to interactive window shall be under 2 seconds | Stopwatch from CLI invocation to window ready | Success Criteria |
| NFR-002 | File navigation, search, and diff viewing shall have no perceptible lag (>100ms) | User observation during review sessions | Success Criteria |
| NFR-003 | Startup time shall be 50%+ faster than VSCode (baseline 5-10 seconds) | Side-by-side timing comparison | Business Success |

### Reliability

| ID | Requirement | Measurement Method | Source |
|----|-------------|-------------------|--------|
| NFR-004 | Zero crashes during a week of daily use (5+ days/week) | Crash log monitoring over 7-day period | Success Criteria |
| NFR-005 | Zero terminal interruptions during a complete review cycle (open → diff → stage → commit) | User observation during review sessions | Success Criteria |

### Quality

| ID | Requirement | Measurement Method | Source |
|----|-------------|-------------------|--------|
| NFR-006 | Core and service layers shall maintain ≥90% line coverage | pytest-cov or equivalent coverage tool | Success Criteria |
| NFR-007 | Plugin logic (non-widget) shall maintain ≥85% line coverage | pytest-cov or equivalent coverage tool | Success Criteria |

### Integration

| ID | Requirement | Measurement Method | Source |
|----|-------------|-------------------|--------|
| NFR-008 | Editor shall inherit system GTK4/Adwaita theme including light/dark mode automatically | Visual verification on GNOME desktop with theme switching | Success Criteria |
| NFR-009 | File watching shall use native GIO/inotify with zero polling | Code inspection of FileService.monitor() | Domain Requirements |

### Extensibility

| ID | Requirement | Measurement Method | Source |
|----|-------------|-------------------|--------|
| NFR-010 | All 4 core plugins (Explorer, Search, Source Control, Preferences) shall use public API only | Code inspection - no internal imports from plugins | Success Criteria |
| NFR-011 | At least one custom plugin shall be written using the public API within first month post-launch | Plugin existence verification | Measurable Outcomes |

---

### Risk Mitigations

| Risk | Mitigation |
|------|------------|
| User missing `ripgrep` | Graceful fallback with install instructions |
| User missing GTK4 packages | Clear error with `apt install` command on startup |
| Python version mismatch | Explicit version check in entry point |
| Adwaita theme not installed | Fall back to default GTK4 theme |

---

## Architecture Traceability

This PRD is complemented by `docs/slate-spec.md` which provides detailed technical architecture.

### Traceability Map

| PRD Section | Architecture Spec Section |
|-------------|-------------------------|
| Editor Core (FR-001 to FR-004) | Section 8: Editor — Core Behaviour |
| File Operations (FR-005 to FR-011) | Section 7.1: File Explorer Plugin |
| Source Control (FR-012 to FR-016) | Section 7.3: Source Control Plugin |
| Plugin System (FR-017 to FR-022) | Section 3.2: Plugin System Architecture |
| Theme & Preferences (FR-023 to FR-028) | Section 7.4: Preferences Plugin, Section 9: Theme & Appearance |
| Performance (NFR-001 to NFR-003) | Section 3.8: Testability, Technology Stack |
| Integration (NFR-008, NFR-009) | Section 3.4: Design Patterns (Event Bus) |

### Implementation Guidance

The architecture spec provides:
- Layered architecture: Core → Service → UI → Plugin (Section 3.1)
- SOLID principles for all module design (Section 3.3)
- Design patterns: Event Bus, Command, Factory, Strategy (Section 3.4)
- Service API contracts for FileService, GitService, SearchService, ConfigService, ThemeService (Section 3.4)
- Plugin API contract: AbstractPlugin, PluginContext, HostUIBridge (Section 3.2)
- Data models: FileStatus, TabState, SearchResult, BranchInfo (Section 3.4)
- Test requirements: 90%+ coverage on core/services, 85%+ on plugin logic (Section 3.8)

---

## Keyboard Shortcuts

### Core Editor Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | New empty tab |
| `Ctrl+W` | Close current tab |
| `Ctrl+S` | Save active tab |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+O` | Open file |
| `Ctrl+Z` | Undo (buffer-level when editor focused) |
| `Ctrl+Y` | Redo (buffer-level when editor focused) |

### Navigation Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+B` | Toggle side panel |

### Plugin Panel Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+O` | Open folder (File Explorer) |
| `Ctrl+Shift+F` | Focus Search panel |
| `Ctrl+H` | Focus Search panel in replace mode |
| `Ctrl+Shift+G` | Focus Source Control panel |
| `Ctrl+,` | Open Preferences |

---

## Startup Behavior

### CLI Invocation

| Command | Behavior |
|---------|----------|
| `slate` | Blank window; restore last_folder if configured |
| `slate .` | Load current folder in File Explorer; show side panel |
| `slate /path/to/folder` | Load folder in File Explorer; show side panel |
| `slate /path/to/file` | Open single file in editor; no sidebar folder |

**Installation:** Run `chmod +x slate` then `sudo cp slate /usr/local/bin/` for system-wide access.

### Startup Precedence Rules

1. **CLI path always wins** over persisted `last_folder`
2. If CLI path is a folder: load folder, show side panel, prefer `file_explorer` as active panel
3. If CLI path is a file: open file in editor tab, do NOT auto-load `last_folder`
4. If no CLI path and `last_folder` exists: load folder, restore sidebar visibility and active panel
5. If no CLI path and no `last_folder`: start with blank window

### Window Restoration

| State | Restored From |
|-------|---------------|
| Window dimensions | `app.window_width`, `app.window_height` |
| Window maximized | `app.window_maximized` |
| Side panel width | `app.side_panel_width` |
| Side panel visible | `app.side_panel_visible` |
| Active panel | `app.active_panel` (restored after plugins activate) |
| **Tabs** | **NOT restored in v1** |

### Startup Sequence

1. Load config from `~/.config/slate/config.ini`
2. Create `ThemeService` and apply initial theme state before window presentation
3. Create window/editor infrastructure and `HostUIBridge`
4. Activate plugins and register actions/panels/dialogs
5. Restore window geometry/sidebar state
6. Resolve startup context from CLI args, otherwise persisted app state
7. Present window
