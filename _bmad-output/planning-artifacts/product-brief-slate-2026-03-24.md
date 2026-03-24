---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments: ["docs/slate-spec.md"]
date: 2026-03-24
author: Raziur
---

# Product Brief: Slate

## Executive Summary

Slate is a lightweight, fast-loading code editor for Ubuntu/Linux desktops, built with Python and GTK4. It delivers a VSCode-like UX — activity bar, file explorer, search, source control — but launches in under 2 seconds and stays out of the way. Designed as a personal tool first, Slate is built on a first-class plugin system from day one, where core features themselves are plugins, making it trivially extensible by the developer who uses it most: its creator.

---

## Core Vision

### Problem Statement

Developers using AI coding agents now read and review significantly more code than they write. Existing editors fall into two camps: VSCode offers excellent UX but suffers from slow startup times (5–10+ seconds cold start), while Zed delivers performance but leaves UX gaps — particularly around file management, search, and source control workflows. Neither tool is designed for the "AI-assisted review" workflow where fast access to diffs, search, and file navigation is critical.

### Problem Impact

When reviewing AI-generated code changes, every second of editor startup or navigation friction compounds across dozens of review sessions per day. Slow editors break flow state during code review. Missing UX features force developers back to the terminal for git operations. The result: context switching, frustration, and a tool that fights the developer instead of serving them.

### Why Existing Solutions Fall Short

- **VSCode**: Loved for its UX (activity bar, panels, keybindings) but Electron-based and slow to launch. Over-featured for review-focused workflows.
- **Zed**: Blazing fast (Rust-based), but lacks a robust file explorer, integrated search/replace, and source control panel comparable to VSCode.
- **Vim/Emacs**: Fast and powerful, but require significant investment in muscle memory and configuration. Not everyone's workflow.

None of these tools are designed with the AI coding agent workflow in mind — where the primary activity is reading, reviewing diffs, and navigating code rather than writing it from scratch.

### Proposed Solution

Slate is a Python/GTK4 code editor that combines VSCode's familiar UX patterns with near-instant startup performance. It ships with four core plugins (File Explorer, Search, Source Control, Preferences) that are themselves built on a first-class plugin API — meaning every feature is extensible and the editor grows with its user. Native Linux integration via GTK4/Adwaita means it inherits system themes automatically and feels truly native.

### Key Differentiators

1. **Plugin-first architecture**: Core features ARE plugins. The same API that ships the built-in panels is available for custom extensions — no artificial internal/external distinction.
2. **Sub-2-second launch**: Python + GTK4 + native system libraries. No Electron, no JVM, no Rust compile step. Just open and go.
3. **Diff-centric workflow**: First-class source control panel with inline diff viewing, stage/unstage checkboxes, and commit workflow — optimized for reviewing AI-generated changes.
4. **Personal by design**: Built by a developer for their own workflow. The "make it mine" philosophy means the editor adapts to the user, not the other way around.
5. **Native Linux integration**: Inherits GTK4/Adwaita themes, uses GIO/inotify for file watching, leverages system git — no abstraction layers fighting the OS.

## Target Users

### Primary Users

**Persona: Raziur — The AI-Augmented Developer**

- **Context**: Software developer on Ubuntu/Linux who has embraced AI coding agents (Copilot, Cursor, Claude, etc.) as a core part of their workflow. Spends the majority of editing time reading and reviewing AI-generated code rather than writing from scratch.
- **Current Pain**: VSCode is their daily driver for UX familiarity but suffers from slow cold starts (5–10+ seconds). Zed is tempting for speed but lacks the file explorer, search, and source control panel they rely on. Terminal-based git workflows break flow during review sessions.
- **Motivation**: Wants an editor that opens instantly, feels native on Linux, and has the exact UX they need — nothing more, nothing less. Values the ability to modify and extend the tool to match their evolving workflow.
- **Success Vision**: Open Slate in under 2 seconds, navigate to a changed file, review the diff side-by-side, stage/unstage with a click, commit — all without touching the terminal. The editor disappears into the background and lets them focus on the code.

### Secondary Users

**Persona: Linux-First Developers Seeking Lightweight Alternatives**

- **Context**: Developers on Ubuntu/Linux desktops who want a fast, native-feeling code editor. May not use AI agents as heavily, but values quick startup and VSCode-like familiarity without the Electron overhead.
- **Current Pain**: VSCode feels bloated for quick edits. Vim/Emacs require too much configuration investment. Zed is fast but unfamiliar.
- **Motivation**: Wants something that "just works" on Linux, inherits their system theme, and doesn't require a PhD to configure.
- **Success Vision**: A code editor that feels like it was built for their OS, launches instantly, and has the panels and keybindings they already know from VSCode.

### User Journey

1. **Discovery**: Developer frustrated with VSCode's startup time finds Slate on GitHub. The "under 2 seconds" and "plugin-first" pitch catches their attention.
2. **Onboarding**: Clone, install dependencies, run `slate .` from any terminal to open the editor on the current directory. System theme inherited automatically. File explorer shows their project. Feels familiar immediately.
3. **Core Usage**: Opens files via Ctrl+O or file explorer. Searches with Ctrl+Shift+F. Reviews diffs in the Source Control panel. Stages, commits, all from the UI.
4. **Aha Moment**: First time they run `slate .` and it's *just there* — no loading spinner, no "Setting up..." — they realize this is how an editor should feel.
5. **Long-term**: Starts customizing: tweaks editor settings, explores the plugin API, eventually writes a small plugin for their specific workflow. The editor becomes truly theirs.

## Success Metrics

### User Success Metrics

1. **Startup Performance**: Slate launches in under 2 seconds on a modern Linux machine. Measured by cold-start time from `slate .` to interactive window.
2. **Review Workflow Efficiency**: Complete a file review cycle (open → navigate to diff → review → stage → commit) without touching the terminal. Success = zero terminal interruptions during a typical review session.
3. **Daily Adoption**: Slate becomes the default editor for daily code review work. Measured by usage frequency — used at least 5 days per week as the primary review tool.
4. **Plugin Extensibility**: The creator successfully builds at least one custom plugin within the first month using the public API. Proves the plugin system works for real use cases.
5. **Zero-Friction Theming**: Editor inherits system GTK4/Adwaita theme on first launch with no configuration required. Light/dark mode switches automatically.

### Business Objectives

1. **Personal Productivity**: Reduce time spent on editor startup and context switching during AI code review sessions by 50%+ compared to VSCode.
2. **Architectural Quality**: Maintain 90%+ test coverage on core and service layers. Prove that the layered architecture is testable and maintainable.
3. **Community Interest**: If open-sourced, achieve 100+ GitHub stars within 6 months — validating that the "fast VSCode-like editor for Linux" niche has demand.
4. **Plugin Ecosystem Proof**: Ship 4 core plugins that all use the same public API, demonstrating the extensibility model works without internal shortcuts.

### Key Performance Indicators

| KPI | Target | Timeframe |
|-----|--------|-----------|
| Cold-start time | < 2 seconds | v1 launch |
| Core + service test coverage | ≥ 90% | v1 launch |
| Core plugins shipped | 4 (Explorer, Search, Source Control, Preferences) | v1 launch |
| Terminal interruptions per review session | 0 | Ongoing |
| Editor crash rate | 0 in a week of daily use | Ongoing |
| Plugin written using public API | ≥ 1 | First month post-launch |

## MVP Scope

### Core Features

**Editor Core**
- GtkSourceView-based editor with syntax highlighting for Python, JS, TS, Rust, HTML, CSS, JSON, Markdown, Shell, Go, Java
- Tab management: open, close, reorder, dirty indicators, Save/Discard guard
- Editor settings: font, tab width, line numbers, word wrap, auto-indent
- Keyboard shortcuts matching VSCode conventions (Ctrl+T, Ctrl+W, Ctrl+S, Ctrl+O, etc.)

**Plugin System**
- First-class plugin API: `AbstractPlugin`, `PluginContext`, `HostUIBridge`
- Plugin registration for actions, panels, dialogs, and keybindings
- Event bus for decoupled plugin communication
- PluginManager for lifecycle management

**Four Core Plugins**
- **File Explorer**: Folder tree, lazy loading, context menus (open/rename/delete/new file/folder)
- **Search**: Find in files with case/whole-word/regex options, glob filter, find & replace with dirty-file safety
- **Source Control**: Git status with stage/unstage checkboxes, diff viewer, commit bar, branch switcher
- **Preferences**: Live editor and appearance settings, theme mode (auto/explicit), color scheme selection

**Theme & Appearance**
- GTK4/Adwaita native theme inheritance (light/dark/system)
- GtkSourceView editor scheme switching with live updates
- ThemeService as centralized theme policy owner

**Architecture**
- Four-layer architecture: Core → Service → UI → Plugin (strict dependency direction)
- Dependency injection composition root in `ui/app.py`
- Typed exception hierarchy
- Config persistence via `~/.config/slate/config.ini`
- File monitoring via GIO/inotify
- Git integration via gitpython

**CLI & Entry Point**
- `slate .` opens editor on current directory
- `slate /path/to/folder` loads folder in explorer
- `slate /path/to/file` opens single file in editor

**Quality**
- 90%+ test coverage on core and service layers
- Unit, contract, integration, and plugin isolation tests
- Startup under 2 seconds

### Out of Scope for MVP

| Feature | Rationale |
|---------|-----------|
| LSP / Autocomplete | Complex integration; architecture is LSP-ready but not implemented |
| Terminal Emulator | Separate plugin; not needed for review workflow |
| Remote SSH Editing | Requires new `AbstractFileBackend` implementation |
| Vim/Emacs Keybindings | Different UX paradigm; not aligned with VSCode-like approach |
| Third-Party Plugin Marketplace | Security and complexity concerns; local plugins only for v1 |
| Git Log / Blame Viewer | Extension of source control plugin; defer to v2 |
| Minimap | Nice-to-have; not critical for review workflow |
| Split Editor Panes | Significant UI complexity; defer |
| Multiple Workspace Roots | Single root is sufficient for v1 |

### MVP Success Criteria

- Cold-start launch under 2 seconds
- Complete a review session (open → diff → stage → commit) without terminal
- All 4 core plugins functional and using the public API
- 90%+ test coverage on core/service layers
- Zero crashes during a week of daily use

### Future Vision

**v2+ Capabilities:**
- `lsp_client` plugin + service for code completion and diagnostics
- Terminal plugin for integrated shell
- Split editor panes for side-by-side editing
- Third-party plugin loading from `~/.config/slate/plugins/`
- Git log and blame viewer
- Remote/SSH file backend
- Outline plugin for symbol navigation
