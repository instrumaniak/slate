---
project_name: 'Slate'
user_name: 'Raziur'
date: '2026-03-24'
sections_completed:
  - technology_stack
  - language_rules
  - framework_rules
  - testing_rules
  - quality_rules
  - workflow_rules
  - anti_patterns
status: 'complete'
rule_count: 45
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

| Layer | Choice | Version |
|---|---|---|
| Language | Python | 3.10+ |
| GUI Toolkit | GTK4 via PyGObject | >= 3.44 |
| UI Framework | GTK4 | GTK4 built-in |
| Syntax Highlighting | GtkSourceView 5 | GTK4 built-in |
| File Watching | Gio.FileMonitor | GTK4 built-in |
| Git | gitpython | >= 3.1 |
| In-project Search | ripgrep | system binary |
| Config | configparser | stdlib |
| Linter | ruff | latest stable |
| Type Checker | mypy | latest stable |
| Test Framework | pytest | >= 7.0 |
| Test Coverage | pytest-cov | >= 4.0 |

**System Dependencies (apt):**
```
python3 python3-gi python3-gi-cairo
gir1.2-gtk-4.0 gir1.2-gtksource-5
ripgrep git
```

---

## Critical Don't-Miss Rules

**Anti-Patterns to Avoid:**
- ❌ Never import GTK at module level in `core/` or `services/`
- ❌ Never call `gitpython` or `open()` directly from UI layer
- ❌ Never hold direct references to other plugin objects
- ❌ Never emit `FileOpenedEvent` directly — only `TabManager` does this
- ❌ Never show windows or mutate tab state in plugin `activate()`
- ❌ Never read/write config.ini directly from plugins — use `PluginContext`
- ❌ Never configure `GtkSource.View` directly — use `EditorViewFactory`
- ❌ Never use GTK signals for cross-component communication — use `EventBus`

**Edge Cases to Handle:**
- Plugin activation failure → skip plugin, log to stderr, app continues
- Startup with CLI file path → do NOT restore `last_folder`
- Startup with saved `active_panel` that no longer exists → fall back to `file_explorer`
- Open-file request for path already open in dirty tab → reuse existing tab
- Diff-tab open followed by normal file open for same path → distinct tabs

**Performance Gotchas:**
- Search runs on thread pool — never block UI thread
- File watching via `Gio.FileMonitor` — no polling
- Panel widgets created lazily — not during `activate()`

---

## Development Workflow Rules

**Implementation Sequence:**
1. Project foundation (pyproject.toml, directory structure)
2. Core layer (interfaces, event bus, plugin API contracts)
3. Services layer (file, git, search, config, theme services)
4. UI layer (main window, activity bar, tab management)
5. Plugin system and core plugins
6. Integration and testing

**Layer Import Rules (STRICT):**
- `core/` → no imports from `services/`, `ui/`, or `plugins/`
- `services/` → imports only from `core/`
- `ui/` → imports from `core/` and `services/`
- `plugins/` → imports only from `core/`

**Cross-Component Dependencies:**
- EventBus must exist before Plugin System
- ConfigService must exist before ThemeService
- FileService must exist before File Explorer plugin
- GitService must exist before Source Control plugin
- SearchService must exist before Search plugin

---

## Code Quality & Style Rules

- ruff for linting + formatting (replaces flake8, isort, black)
- mypy for type checking
- Run `ruff check .` and `ruff format .` before commits
- Run `mypy slate/` to verify types
- Module files: `snake_case.py`; Classes: `PascalCase`; Functions: `snake_case()`
- Plugin IDs: `snake_case` (e.g., `file_explorer`)
- Event classes: `PascalCase` + `Event` suffix (e.g., `FileOpenedEvent`)
- Action names: namespaced dots (e.g., `search.focus`)
- Config sections: dot notation (e.g., `plugin.file_explorer`)
- One class per file preferred for services
- Related dataclasses in `core/models.py` and `core/events.py`
- ABCs in `core/interfaces/`; Plugin API contracts in `core/plugin_api.py`
- Docstrings for all public classes and methods
- ABC methods have docstrings defining contracts
- No comments unless explaining non-obvious "why"

---

## Testing Rules

- `tests/` mirrors source structure: `tests/core/`, `tests/services/`, `tests/ui/`, `tests/plugins/`
- `core/` and `services/`: **90%+** line coverage (hard requirement)
- Non-widget plugin logic: **85%+** line coverage
- `ui/`: smoke/integration tests only — don't chase superficial percentage
- No GTK initialization for any service, core, or plugin-logic test
- Prefer temporary directories and real temp git repos over excessive mocking
- Mock only at explicit external boundaries or when injecting failure paths
- For file-opening tests, use event-bus-driven fixtures — not notebook APIs directly
- Every feature needs: normal path test, failure path test, one regression-prone edge case
- Every bug fix adds a regression test when feasible
- Plugin activation failure isolation is tested and enforced
- Common fixtures in `tests/conftest.py`: `temp_dir`, `temp_git_repo`, `mock_event_bus`, `mock_config_service`
- Run: `pytest tests/ --cov=slate --cov-report=term-missing`

---

## Framework-Specific Rules (GTK4/PyGObject)

- UI layer uses `Gtk`, `GtkSource`, `Gio`, `Adw` directly
- Service layer uses lazy imports inside methods only (keeps GTK-free at import time)
- `EditorView` wraps `GtkSource.View` — never configure `GtkSource.View` directly elsewhere
- `SlateApplication(Gtk.Application)` is the composition root — all DI wiring in `ui/app.py`
- Theme applied before window is presented (startup order requirement)
- Cross-component communication via `EventBus` — NOT GTK signals
- GTK signals used only within UI layer for widget interactions
- `Gio.SimpleAction` for keyboard shortcuts — registered in `ui/actions.py`
- Plugins register `WidgetFactory` callbacks returning `Gtk.Widget` at runtime
- Host shell owns widget insertion, parenting, single-instance behavior, and disposal
- `EditorViewFactory` must use `ThemeService.resolve_editor_scheme()` — not read theme keys directly

---

## Language-Specific Rules

- Python 3.10+ with modern type hints (`str | None`, `list[str]`)
- Use `from __future__ import annotations` for forward references in dataclasses
- All public methods must have type annotations
- Lazy GTK imports inside methods (not at module level) in service layer
- `from gi.repository import Gtk, GtkSource, Gio, Adw` only in UI layer or inside methods
- Core layer: zero GTK imports at any level
- Typed exceptions hierarchy in `core/exceptions.py` — services raise, UI catches
- Plugin `activate()` wrapped in try/except — failing plugins are skipped with stderr log
- Search runs on `GLib.ThreadPool` threads — UI stays responsive
- EventBus is thread-safe with `threading.RLock`
- File monitoring via `Gio.FileMonitor` callbacks

---

## Critical Implementation Rules

### 1. Layer Architecture (MANDATORY)

The codebase is split into four strict layers. **Lower layers never import from higher layers.**

```
┌──────────────────────────────────────────────────────────┐
│            Plugin Layer   (slate/plugins/)               │
├──────────────────────────────────────────────────────────┤
│              UI Layer     (slate/ui/)                    │
├──────────────────────────────────────────────────────────┤
│           Service Layer   (slate/services/)              │
├──────────────────────────────────────────────────────────┤
│             Core Layer    (slate/core/)                  │
└──────────────────────────────────────────────────────────┘
```

**Rules:**
- **Core layer**: Plain Python dataclasses, ABCs, event bus, plugin API contracts. Zero GTK. Zero I/O.
- **Service layer**: File I/O, git operations, config, search. Depends only on core. Zero GTK.
- **UI layer**: GTK widgets and window layout. Calls services; listens to event bus. Never calls `gitpython` or `open()` directly.
- **Plugin layer**: Each plugin is a self-contained package depending only on core ABCs.

### 2. GTK Import Strategy

GTK imports should be lazy (inside functions) where possible to keep the service layer importable without GTK at module load time.

```python
# In service layer - use lazy imports
def detect(self, path: str):
    from gi.repository import GtkSource  # Lazy import inside method
    # ... rest of implementation
```

### 3. Event Ownership Rules

- UI actions, plugins, and startup code emit **request events** (`OpenFileRequestedEvent`, `OpenDiffRequestedEvent`)
- `TabManager` is the only component that turns open requests into editor tabs
- `TabManager` emits `FileOpenedEvent` only after the target tab/view exists
- Services emit state/result events (`FileSavedEvent`, `SearchResultsReadyEvent`, `GitStatusChangedEvent`) but do not create or focus tabs
- Plugins may subscribe to result events and request navigation, but they must not emit `FileOpenedEvent` directly

### 4. Plugin Communication Rules

- Plugins communicate with each other **only** via the `EventBus` or by fetching a shared service via `context.get_service(id)`
- Plugins never hold direct references to other plugin objects
- Plugins never import from `slate/ui/`
- Cross-cutting runtime concerns such as theme resolution are **services**, not plugins

### 5. Plugin Registration Rules

- `activate()` may subscribe to events and register actions/panels/dialogs only
- `activate()` must NOT immediately show windows, mutate tab state, or emit startup open events
- Panel widgets and dialogs are created lazily through registered factories/presenters
- The host shell owns insertion into the layout, parenting, single-instance behavior, and disposal

### 6. SOLID Principles Enforcement

- **Single Responsibility**: Each class has one responsibility (e.g., `FileService` owns file I/O only)
- **Open/Closed**: New panels = implement `AbstractPlugin` — zero changes to `ActivityBar` or `SidePanel`
- **Liskov Substitution**: All `AbstractPlugin` implementations are valid substitutes
- **Interface Segregation**: `AbstractFileBackend` is split into `ReadableBackend` and `WritableBackend`
- **Dependency Inversion**: Depend on abstractions (e.g., `AbstractVCSBackend`) not concretions

### 7. Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Module files | snake_case | `file_service.py` |
| Classes | PascalCase | `FileService`, `EventBus` |
| Functions | snake_case | `get_file()`, `list_directory()` |
| Plugin IDs | snake_case | `file_explorer`, `source_control` |
| Service IDs | quoted string | `"file"`, `"git"`, `"search"` |
| Action names | namespaced dots | `search.focus`, `file.open` |
| Event classes | Pascal + Event suffix | `FileOpenedEvent` |
| Config sections | dot notation | `plugin.file_explorer`, `editor` |

### 8. Testing Requirements

- `core/` and `services/` must maintain **90%+** line coverage
- Non-widget plugin logic must maintain **85%+** line coverage
- No feature is complete without tests for: normal path, failure path, and one regression-prone edge case
- Every bug fix should add a regression test when feasible
- Tests should prefer temporary directories and real temporary git repositories over excessive mocking
- No GTK initialisation required for any service, core, or plugin-logic test

### 9. Error Handling Strategy

- Services raise typed exceptions from `core/exceptions.py`
- UI layer catches at the boundary → `Gtk.MessageDialog`. Services never show UI.
- Plugins show their own errors inline
- Plugin `activate()` calls are wrapped in try/except — a failing plugin is skipped with a stderr log; the app continues

### 10. Configuration Rules

- Config file: `~/.config/slate/config.ini`
- Plugin config sections use `[plugin.<plugin_id>]`
- Each plugin reads/writes its own section via `PluginContext.get_config()` / `set_config()`
- Plugins never touch config.ini directly
- Theme config is owned by `ThemeService`
- `ConfigService` merges partial updates into existing sections instead of replacing unrelated keys

### 11. Startup Order Requirements

1. Load config
2. Create `ThemeService` and apply initial theme state before presenting any window
3. Create window/editor infrastructure and `HostUIBridge`
4. Activate plugins and let them register actions/panels/dialogs
5. Restore window geometry/sidebar state
6. Resolve startup context from CLI args first, otherwise persisted app state
7. Only restore `last_folder` when no CLI file/folder argument is provided
8. Never auto-restore editor tabs in v1

### 12. Design Patterns Used

1. **Event Bus (Observer)** — Decoupled cross-plugin communication
2. **Command Pattern** — App-level undo/redo (separate from buffer undo)
3. **Factory Pattern** — `EditorViewFactory` centralizes GtkSourceView configuration
4. **Strategy Pattern** — Search backends, language detection backends
5. **Repository Pattern** — Git data access

### 13. Composition Root Pattern

All dependency injection wiring happens in `ui/app.py`. No class instantiates its own dependencies. `SlateApplication.do_activate()` creates all services, wires them together, and injects them.

### 14. Command History Rules

- Text editing undo/redo is owned by each `GtkSource.Buffer`
- `CommandHistory` is only for app-level operations outside the editor buffer
- When the active editor buffer has focus, `Ctrl+Z` / `Ctrl+Y` invoke buffer-local undo/redo
- When no editor buffer is focused, `Ctrl+Z` / `Ctrl+Y` target `CommandHistory`
- `SaveFileCommand` is executable but not undoable in v1

### 15. Service IDs Reserved by Host Shell

| Service ID | Service |
|------------|---------|
| `"file"` | FileService |
| `"git"` | GitService |
| `"search"` | SearchService |
| `"config"` | ConfigService |
| `"theme"` | ThemeService |
| `"tabs"` | TabQueryService (read-only tab/document query API) |

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-03-24
