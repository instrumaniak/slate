---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "prd.md"
  - "ux-design-specification.md"
  - "docs/slate-spec.md"
workflowType: 'architecture'
project_name: Slate
user_name: Raziur
date: 2026-03-24
lastStep: 8
status: 'complete'
completedAt: '2026-03-24'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
Slate comprises 28 functional requirements across 6 domains:
- **Editor Core** (4 FRs): File opening with syntax highlighting, tab management (open, close, reorder, save), dirty indicators, save/discard guards
- **File Operations** (7 FRs): Folder/file opening via CLI, file explorer tree with lazy loading, file create/rename/delete, project-wide search with ripgrep, find & replace
- **Source Control** (5 FRs): Git status with change badges, inline diff viewing, stage/unstage checkboxes, commit workflow, branch switching
- **Plugin System** (6 FRs): AbstractPlugin API, panel registration, action/keybinding registration, dialogs, EventBus communication — all using public API
- **Theme & Appearance** (3 FRs): Light/dark/system toggle, editor color schemes, GTK4/Adwaita theme inheritance
- **Preferences** (3 FRs): Font/tab/indentation config, display toggles, config persistence

**Non-Functional Requirements:**
- **Performance:** Sub-2-second cold start, zero perceptible lag (<100ms) on all interactions
- **Reliability:** Zero crashes during week of daily use, zero terminal interruptions during review cycles
- **Quality:** 90%+ line coverage on core/services, 85%+ on plugin logic
- **Integration:** GTK4/Adwaita native theme, GIO/inotify file watching, system git/ripgrep
- **Extensibility:** All 4 core plugins (Explorer, Search, Source Control, Preferences) use only public API

### Scale & Complexity

- **Primary domain:** Desktop application (Linux) — Developer tool
- **Complexity level:** Medium
- **Estimated architectural components:** 15-20 distinct components (editor core, file service, git service, search service, config service, theme service, plugin system, 4 core plugins, UI components)

### Technical Constraints & Dependencies

- **Platform:** Linux only (Ubuntu 22.04+)
- **Runtime:** Python 3.10+, PyGObject >= 3.44
- **UI Framework:** GTK4, GtkSourceView 5, Adwaita
- **System dependencies:** git, ripgrep (via subprocess)
- **Config storage:** ~/.config/slate/config.ini
- **No Electron, no JVM, no compile step**

### Cross-Cutting Concerns Identified

1. **Plugin Architecture:** All features (including core) use AbstractPlugin API — must ensure public API is complete and stable
2. **Event-Driven Communication:** EventBus for plugin-to-plugin and plugin-to-host communication
3. **Native Tool Integration:** Strategy pattern for git/ripgrep — must handle missing tools gracefully
4. **Testability:** Layered architecture (Core → Service → UI → Plugin) enables 90%+ coverage requirement
5. **Theme System:** Must inherit GTK4/Adwaita while allowing custom editor color schemes

## Starter Template Evaluation

### Primary Technology Domain

**Python Desktop Application (Linux)** — Based on project requirements:
- Python 3.10+ with PyGObject for GTK4 bindings
- Native Linux tool integration (git, ripgrep)
- No Electron, no compile step — pure Python + GTK4

### Starter Options Considered

**Option 1: No Standard Starter**
- Python GTK4 apps don't have a standard scaffolding ecosystem like web frameworks
- Must build project structure from scratch or use examples as reference

**Option 2: Manual Project Initialization**
- Project initialization via standard Python packaging (pyproject.toml or setup.py)
- Structure defined by `docs/slate-spec.md` layered architecture

### Selected Approach: Manual Project Foundation

**Rationale for Selection:**
- No existing starter templates for Python GTK4 editor projects
- Your `docs/slate-spec.md` already defines complete architecture (layered: Core → Service → UI → Plugin)
- Project structure should follow the architecture specification directly

**Initialization Approach:**

The project initialization should be the first implementation story, creating:
- Python package structure following the layered architecture
- `pyproject.toml` for modern Python packaging
- Basic GTK4 window with the layered structure in place

**Architectural Decisions Provided by Project Foundation:**

**Language & Runtime:**
- Python 3.10+ with type hints
- PyGObject for GTK4 bindings

**Dependencies Management:**
- pyproject.toml with pip/packaging backend
- System packages documented for apt install

**Testing Framework:**
- pytest (standard for Python)
- pytest-cov for coverage (90%+ requirement)

**Code Organization:**
- Following slate-spec.md: `slate/core/`, `slate/services/`, `slate/ui/`, `slate/plugins/`
- Test structure mirroring source: `tests/core/`, `tests/services/`, etc.

**Development Experience:**
- GTK4 requires system packages, not pip-installable
- Development requires local GTK4 environment setup

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Code quality tools selection
- Event bus implementation approach

**Important Decisions (Shape Architecture):**
- Git & search integration strategy
- Configuration file format

**Deferred Decisions (Post-MVP):**
- LSP client (post-MVP)
- Terminal plugin (post-MVP)
- Third-party plugin loading (post-MVP)

### Code Quality Tools

| Decision | Choice | Version | Rationale |
|----------|--------|---------|------------|
| Linter | **ruff** | Latest stable | Fast, modern, Rust-based; replaces multiple tools |
| Type Checker | **mypy** | Latest stable | Industry standard for Python type checking |
| Code Formatter | **ruff format** | Latest stable | Built into ruff, consistent with linter |

**Affects:** All layers (core, services, ui, plugins)
**Rationale:** Fast linting + proven type checking. Matches "boring technology" principle — tools that ship successfully and are widely used.

### Event Bus Implementation

| Decision | Choice | Rationale |
|----------|--------|-----------|
| EventBus | **Custom implementation** | Minimal dependencies, full control, matches simplicity principle |

**Affects:** Plugin system, service-to-service communication
**Rationale:** Keeps dependencies minimal. Pub/sub pattern is straightforward to implement. No need for external library for this scope.

### Git & Search Integration

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Git operations | **gitpython** | As specified in PRD |
| Search | **subprocess + ripgrep** | As specified in PRD |
| Graceful degradation | **Yes** | Handlers for missing tools with install instructions |

**Affects:** GitService, SearchService, Source Control plugin, Search plugin
**Rationale:** Native tool integration is foundational to the performance requirements. Graceful degradation ensures usability when tools are missing.

### Configuration Format

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Config storage | **configparser (INI)** | Matches PRD specification (~/.config/slate/config.ini) |

**Affects:** ConfigService, Preferences plugin
**Rationale:** Direct match to PRD. Standard library, no additional dependencies.

**DEFAULT_CONFIG (from spec, line 1129):**
```python
DEFAULT_CONFIG = {
    "editor": {
        "font": "Monospace 13",
        "tab_width": "4",
        "insert_spaces": "true",
        "show_line_numbers": "true",
        "highlight_current_line": "true",
        "word_wrap": "false",
        "auto_indent": "true",
        "theme_mode": "auto",
        "light_scheme": "Adwaita",
        "dark_scheme": "Adwaita-dark",
        "explicit_scheme": "Adwaita",
    },
    "app": {
        "color_mode": "system",
        "last_folder": "",
        "active_panel": "",
        "side_panel_width": "220",
        "side_panel_visible": "true",
        "window_width": "1200",
        "window_height": "800",
        "window_maximized": "false",
    },
    "plugin.search": {
        "include_hidden": "false",
        "last_glob_filter": "",
    },
    "plugin.source_control": {
        "auto_refresh": "true",
    },
}
```

### Dependency Summary

**Python Dependencies (pyproject.toml):**
```
PyGObject >= 3.44
gitpython >= 3.1
pytest >= 7.0
pytest-cov >= 4.0
ruff (dev)
mypy (dev)
```

**System Dependencies (apt):**
```
python3-gi python3-gi-cairo
gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1
git ripgrep
```

### Decision Impact Analysis

**Implementation Sequence:**
1. Project foundation (pyproject.toml, directory structure)
2. Core layer (interfaces, event bus, plugin API contracts)
3. Services layer (file, git, search, config, theme services)
4. UI layer (main window, activity bar, tab management)
5. Plugin system and core plugins
6. Integration and testing

**Cross-Component Dependencies:**
- EventBus must exist before Plugin System (plugins communicate via events)
- ConfigService must exist before ThemeService (theme preferences)
- FileService must exist before File Explorer plugin (file operations)
- GitService must exist before Source Control plugin (git operations)
- SearchService must exist before Search plugin (search operations)

## Implementation Patterns & Consistency Rules

_Source of Truth: `docs/slate-spec.md` Sections 3.1 - 3.4_

### Pattern Categories Defined

**Source:** These patterns are derived directly from `docs/slate-spec.md` as the authoritative source.

### Layer Architecture (Section 3.1) — MANDATORY

The codebase is split into four strict layers. **Lower layers never import from higher layers.**

```
┌──────────────────────────────────────────────────────────┐
│            Plugin Layer   (slate/plugins/)               │  Core + future plugins
├──────────────────────────────────────────────────────────┤
│              UI Layer     (slate/ui/)                    │  GTK widgets, layout, event handlers
├──────────────────────────────────────────────────────────┤
│           Service Layer   (slate/services/)              │  Business logic — NO GTK imports
├──────────────────────────────────────────────────────────┤
│             Core Layer    (slate/core/)                  │  Models, ABCs, event bus — pure Python
└──────────────────────────────────────────────────────────┘
```

**Rules:**
- **Core layer**: Plain Python dataclasses, ABCs, event bus, plugin API contracts. Zero GTK. Zero I/O.
- **Service layer**: File I/O, git operations, config, search. Depends only on core. Zero GTK.
- **UI layer**: GTK widgets and window layout. Calls services; listens to event bus. Never calls `gitpython` or `open()` directly.
- **Plugin layer**: Each plugin is a self-contained package depending only on core ABCs.

### Naming Patterns

| Element | Pattern | Example |
|---------|---------|---------|
| Module files | snake_case | `file_service.py`, `event_bus.py` |
| Classes | PascalCase | `FileService`, `EventBus`, `AbstractPlugin` |
| Functions | snake_case | `get_file()`, `list_directory()` |
| Plugin IDs | snake_case | `file_explorer`, `source_control`, `search` |
| Service IDs | quoted string | `"file"`, `"git"`, `"search"` |
| Action names | namespaced dots | `search.focus`, `file.open` |
| Event classes | Pascal + Event suffix | `FileOpenedEvent`, `GitStatusChangedEvent` |
| Config sections | dot notation | `plugin.file_explorer`, `editor` |

### Event System Patterns (Section 3.4)

Events are defined as dataclasses in `core/events.py`:

```python
@dataclass
class FileOpenedEvent:
    path: str

@dataclass
class FileSavedEvent:
    path: str

@dataclass
class GitStatusChangedEvent:
    pass

@dataclass
class ThemeChangedEvent:
    color_mode: str          # "system" | "light" | "dark"
    resolved_is_dark: bool
    editor_scheme: str
```

**Event Ownership Rules (from spec):**
- UI actions, plugins, and startup code emit **request events** such as `OpenFileRequestedEvent` and `OpenDiffRequestedEvent`
- `TabManager` is the only component that turns open requests into editor tabs
- `TabManager` emits `FileOpenedEvent` only after the target tab/view exists
- services emit state/result events (`FileSavedEvent`, `SearchResultsReadyEvent`, `GitStatusChangedEvent`) but do not create or focus tabs

### Plugin API Patterns (Section 3.2)

- **Plugin IDs**: snake_case (`file_explorer`, `search`, `source_control`, `preferences`)
- **Activity bar icons**: XDG symbolic names (`folder-symbolic`, `system-search-symbolic`, `vcs-changed-symbolic`)
- **Activation**: `activate()` registers actions/panels/dialogs only. Must NOT immediately show windows or emit startup events.
- **Communication**: Via EventBus or `context.get_service()`. Never hold direct references to other plugin objects.

### GTK Import Strategy

The spec shows lazy imports to keep layers GTK-free at import time:

```python
# In service layer - use lazy imports
def detect(self, path: str):
    from gi.repository import GtkSource  # Lazy import inside method
    # ... rest of implementation
```

**Rule:** GTK imports should be lazy (inside functions) where possible to keep the service layer importable without GTK at module load time.

### Test Organization

Tests in separate `tests/` directory mirroring source structure:
- `tests/core/`, `tests/services/`, `tests/ui/`, `tests/plugins/`

### SOLID Principles (Section 3.3)

All code must follow SOLID principles as documented in the spec:
- **S**ingle Responsibility: Each class has one responsibility
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Subtypes must be substitutable
- **I**nterface Segregation: Many specific interfaces > one general interface
- **D**ependency Inversion: Depend on abstractions, not concretions

### Design Patterns Used

1. **Event Bus (Observer)** — Section 3.4
2. **Command Pattern** — For app-level undo/redo (separate from buffer undo)
3. **Factory Pattern** — `EditorViewFactory` centralizes GtkSourceView configuration
4. **Strategy Pattern** — Search backends, language detection backends
5. **Repository Pattern** — Git data access

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow the layered architecture (Core → Service → UI → Plugin)
- Use snake_case for files and functions, PascalCase for classes
- Define events as dataclasses with Event suffix
- Use lazy GTK imports in service layer
- Keep service layer zero-GTK at import time
- Implement interfaces from core in service layer
- Register plugins via AbstractPlugin API only

**Pattern Sources:**
- `docs/slate-spec.md` Section 3.1: Layered Architecture
- `docs/slate-spec.md` Section 3.2: Plugin System Architecture
- `docs/slate-spec.md` Section 3.3: SOLID Principles
- `docs/slate-spec.md` Section 3.4: Design Patterns

## Project Structure & Boundaries

### Complete Project Directory Structure

```
slate/                          # Python package root
├── pyproject.toml              # Modern Python packaging
├── README.md                   # Project documentation
├── LICENSE                     # MIT license
├── CHANGELOG.md               # Version history
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI
├── requirements.txt            # pip dependencies (dev)
├── requirements-prod.txt       # Production deps only
├── Makefile                    # Development shortcuts
├── slate/                      # Main package
│   ├── __init__.py
│   ├── __main__.py            # CLI entry: python -m slate
│   ├── main.py                # Application entry point
│   ├── version.py             # Version info
│   │
│   ├── core/                  # Layer 1: Pure Python, zero GTK
│   │   ├── __init__.py
│   │   ├── event_bus.py       # EventBus implementation
│   │   ├── events.py          # Event dataclasses
│   │   ├── models.py          # Data models (FileStatus, TabState, etc.)
│   │   ├── commands.py        # Command pattern (undo/redo)
│   │   │
│   │   ├── interfaces/        # Abstract base classes
│   │   │   ├── __init__.py
│   │   │   ├── file_backend.py    # ReadableBackend, WritableBackend
│   │   │   ├── vcs_backend.py      # AbstractVCSBackend
│   │   │   ├── search_backend.py  # AbstractSearchBackend
│   │   │   └── language_detector.py
│   │   │
│   │   └── plugin_api.py     # AbstractPlugin, PluginContext, HostUIBridge
│   │
│   ├── services/              # Layer 2: Business logic, zero GTK
│   │   ├── __init__.py
│   │   ├── file_service.py    # File I/O operations
│   │   ├── git_service.py    # Git operations
│   │   ├── search_service.py # Search operations
│   │   ├── config_service.py # Config management
│   │   ├── theme_service.py  # Theme resolution
│   │   ├── plugin_manager.py  # Plugin lifecycle
│   │   │
│   │   ├── backends/          # Backend implementations
│   │   │   ├── __init__.py
│   │   │   ├── local_file_backend.py
│   │   │   ├── ripgrep_search_backend.py
│   │   │   └── git_repository.py
│   │   │
│   │   └── language_detector.py
│   │
│   ├── ui/                    # Layer 3: GTK widgets
│   │   ├── __init__.py
│   │   ├── main_window.py     # SlateWindow (main)
│   │   ├── activity_bar.py    # Panel navigation
│   │   ├── side_panel.py      # Panel container
│   │   ├── theme_manager.py   # GTK theme runtime
│   │   │
│   │   ├── editor/
│   │   │   ├── __init__.py
│   │   │   ├── editor_view.py      # EditorView (GtkSource.View wrapper)
│   │   │   ├── editor_factory.py   # EditorViewFactory
│   │   │   ├── tab_manager.py     # Tab management
│   │   │   ├── diff_view.py       # Diff viewer
│   │   │   └── tab_bar.py          # Tab bar widget
│   │   │
│   │   ├── panels/            # Built-in panels
│   │   │   ├── __init__.py
│   │   │   └── panel_container.py
│   │   │
│   │   └── dialogs/           # Built-in dialogs
│   │       ├── __init__.py
│   │       └── save_discard_dialog.py
│   │
│   └── plugins/               # Layer 4: Plugins
│       ├── __init__.py
│       ├── core/              # Core plugins (shipped)
│       │   ├── __init__.py
│       │   ├── file_explorer.py
│       │   ├── search.py
│       │   ├── source_control.py
│       │   └── preferences.py
│       │
│       └── contrib/           # Third-party plugins (future)
│           └── .gitkeep
│
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── conftest.py            # pytest fixtures
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── test_event_bus.py
│   │   ├── test_events.py
│   │   ├── test_models.py
│   │   └── test_commands.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_file_service.py
│   │   ├── test_git_service.py
│   │   ├── test_search_service.py
│   │   ├── test_config_service.py
│   │   └── test_theme_service.py
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── test_tab_manager.py
│   │   └── test_editor_factory.py
│   │
│   ├── plugins/
│   │   ├── __init__.py
│   │   └── test_plugin_api.py
│   │
│   └── fixtures/              # Test fixtures
│       ├── __init__.py
│       ├── sample_files/
│       └── sample_repos/
│
├── scripts/                  # Development scripts
│   ├── install-deps.sh        # Install system dependencies
│   ├── run-tests.sh          # Test runner
│   └── lint.sh               # Linter runner
│
├── docs/                     # Documentation
│   ├── api/                  # API documentation
│   │   ├── core.md
│   │   ├── services.md
│   │   └── plugins.md
│   ├── contributing.md
│   └── debugging.md
│
└── data/                     # Application data
    └── schemes/               # GtkSourceView color schemes
```

### Requirements to Structure Mapping

| FR Category | Primary Location | Supporting Files |
|-------------|-------------------|------------------|
| **Editor Core** | `slate/ui/editor/` | `editor_view.py`, `tab_manager.py`, `tab_bar.py` |
| **File Operations** | `slate/services/` + `slate/plugins/core/file_explorer.py` | `file_service.py`, `local_file_backend.py` |
| **Source Control** | `slate/services/git_service.py` + `slate/plugins/core/source_control.py` | `git_repository.py` |
| **Plugin System** | `slate/core/plugin_api.py` + `slate/services/plugin_manager.py` | `AbstractPlugin` interface |
| **Theme & Appearance** | `slate/services/theme_service.py` + `slate/ui/theme_manager.py` | Config in `config_service.py` |
| **Preferences** | `slate/plugins/core/preferences.py` | `config_service.py` |

### Architectural Boundaries

**Layer Boundaries:**
- `core/` → No imports from `services/`, `ui/`, or `plugins/`
- `services/` → Imports only from `core/`, no GTK imports
- `ui/` → Imports from `core/` and `services/`, contains all GTK code
- `plugins/` → Imports only from `core/`, communicates via EventBus

**Service Boundaries:**
- `FileService` owns file I/O only
- `GitService` owns git operations only
- `SearchService` owns search operations only
- `ConfigService` owns config persistence only
- `ThemeService` owns theme resolution only
- `TabQueryService` (exposed by TabManager) provides read-only tab state to plugins

**Service IDs (for `context.get_service()`):**
| Service ID | Service |
|------------|---------|
| `"file"` | FileService |
| `"git"` | GitService |
| `"search"` | SearchService |
| `"config"` | ConfigService |
| `"theme"` | ThemeService |
| `"tabs"` | TabQueryService (read-only tab/document query API) |

**Plugin Boundaries:**
- Each plugin is self-contained in `slate/plugins/core/<plugin_name>.py`
- Plugins register via `AbstractPlugin.activate(PluginContext)`
- Plugins communicate via `EventBus` or `context.get_service()`

### Integration Points

**Internal Communication:**
- EventBus for decoupled communication between services and plugins
- Service injection via `PluginContext.get_service()`
- Config via `PluginContext.get_config()` / `set_config()`

**External Integrations:**
- `git` binary via gitpython
- `ripgrep` binary via subprocess
- GTK4/Adwaita via PyGObject
- File system via GIO/inotify

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- Python 3.10+ + PyGObject + GTK4 are fully compatible
- ruff + mypy work together for linting/type checking
- EventBus implementation is internal (no external dependencies to conflict)
- configparser is stdlib, no version conflicts
- gitpython + subprocess for ripgrep are both external but independent

**Pattern Consistency:**
- Layered architecture aligns with the spec (Section 3.1)
- Naming conventions (snake_case files, PascalCase classes) match spec examples
- Event patterns match spec's `core/events.py` structure
- Plugin API matches spec's `core/plugin_api.py` exactly

**Structure Alignment:**
- Project structure follows the 4-layer architecture exactly
- Service boundaries align with spec (FileService, GitService, etc.)
- Plugin locations match spec (`slate/plugins/core/`)

### Requirements Coverage Validation ✅

| FR Category | Architectural Support |
|-------------|----------------------|
| **Editor Core** | `slate/ui/editor/` — editor_view.py, tab_manager.py |
| **File Operations** | `slate/services/file_service.py` + FileExplorerPlugin |
| **Source Control** | `slate/services/git_service.py` + SourceControlPlugin |
| **Plugin System** | `slate/core/plugin_api.py` + plugin_manager.py |
| **Theme & Appearance** | theme_service.py + theme_manager.py |
| **Preferences** | ConfigService + PreferencesPlugin |

**NFR Coverage:**
- **Performance** (sub-2s startup): Native tool integration (ripgrep, gitpython, GIO)
- **Reliability**: Service layer isolation enables testing
- **Quality** (90% coverage): Testable layered architecture + pytest-cov

### Implementation Readiness ✅

**Decision Completeness:**
- All versions specified (PyGObject >= 3.44, gitpython >= 3.1)
- Implementation patterns documented with examples from spec
- Consistency rules enforced via documentation

**Structure Completeness:**
- Complete directory tree defined (68+ files/dirs)
- All integration points specified
- Component boundaries clearly defined

**Pattern Completeness:**
- All conflict points addressed (naming, layers, events, plugins)
- Communication patterns via EventBus documented
- Error handling via spec's Command pattern

### Gap Analysis Results

**Critical Gaps:** None found

**Important Gaps:** None found

**Nice-to-Have:**
- LSP integration prep (already reserved in spec as post-MVP)
- Terminal plugin (non-goal for v1)

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** ✅ READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Architecture directly derived from `docs/slate-spec.md` (authoritative source)
- Strict layered architecture ensures testability (90%+ coverage requirement)
- Plugin system with public API ensures extensibility
- Native tool integration addresses performance requirements

**Areas for Future Enhancement:**
- LSP client integration (post-MVP)
- Terminal plugin (post-MVP)
- Third-party plugin marketplace (post-MVP)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

**First Implementation Priority:**
1. Project foundation (pyproject.toml, directory structure)
2. Core layer (interfaces, event bus, plugin API contracts)
3. Services layer (file, git, search, config, theme services)
4. UI layer (main window, activity bar, tab management)
5. Plugin system and core plugins
6. Integration and testing