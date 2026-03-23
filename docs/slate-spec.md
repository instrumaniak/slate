# Slate — Lightweight GTK4 Code Editor
## Project Specification v2.0

---

## 1. Overview

**Slate** is a lightweight, fast-loading code editor for Ubuntu/Linux desktops. It is built with Python and GTK4, leveraging Python's deep Linux system integration for native performance. Its UX is deliberately VSCode-like — a vertical activity bar on the left switches between panels (Explorer, Search, Source Control) — but it loads in a fraction of the time and stays out of the way.

The editor is built on a **first-class plugin system from day one**. Core features (file explorer, search, source control) are themselves plugins. This means every panel, every service contribution, and every keybinding is registered through a consistent plugin API — making the extension model natural and easy to grow.

---

## 2. Goals & Non-Goals

### Goals
- Launch in under 2 seconds on a modern Linux machine
- VSCode-like activity bar UX: icon strip on left switches panel views
- Feel native — inherit system GTK4/Adwaita theme including light/dark mode automatically
- Provide curated, high-quality editor theming with live switching and consistent plugin styling
- Plugin system from day one — core features ARE plugins
- Ship four core plugins: File Explorer, Search, Source Control (Git), Preferences
- Syntax highlighting for common languages via GtkSourceView (zero extra deps)
- Leverage Python's native Linux integration: GIO, inotify via GLib, gitpython, os/mmap for search
- Maintain strong automated test coverage for core workflows and plugin isolation

### Non-Goals (v1)
- Language server protocol (LSP) / autocomplete
- Terminal emulator panel
- Remote SSH editing
- Vim/Emacs key binding modes
- Third-party plugin marketplace or dynamic loading from the internet

---

## 3. Architecture & Design Principles

This section is **mandatory** for the implementing agent. Every module must be built against these principles so future features — LSP, split panes, remote files, additional plugins — can be added without rewriting existing code.

---

### 3.1 Layered Architecture

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

- **Core layer**: Plain Python dataclasses, ABCs, event bus, plugin API contracts. Zero GTK. Zero I/O.
- **Service layer**: File I/O, git operations, config, search. Depends only on core. Zero GTK.
- **UI layer**: GTK widgets and window layout. Calls services; listens to event bus. Never calls `gitpython` or `open()` directly.
- **Plugin layer**: Each plugin is a self-contained package depending only on core ABCs. Plugins contribute activity bar icons, panel widgets, actions, and keybindings through `PluginContext`.

---

### 3.2 Plugin System Architecture

This is the most important architectural decision. **Read carefully.**

#### Plugin Contract

`core/plugin_api.py` must remain pure Python. It defines serializable metadata and opaque factory callbacks, but it does **not** import GTK, Gio, or any `gi` module.

Every plugin implements `AbstractPlugin` from `core/plugin_api.py`:

```python
# core/plugin_api.py
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

UiActionCallback = Callable[[], None]
WidgetFactory = Callable[[], object]     # host expects a Gtk.Widget at runtime
DialogPresenter = Callable[[object], None]  # host passes the active Gtk.Window

@dataclass(frozen=True)
class ActivityBarItem:
    plugin_id: str
    icon_name: str       # XDG symbolic icon e.g. "folder-symbolic"
    tooltip: str
    order: int           # lower = higher in bar
    supports_badge: bool = False

@dataclass(frozen=True)
class PanelHeaderAction:
    action_id: str
    icon_name: str
    tooltip: str

@dataclass(frozen=True)
class PanelSpec:
    plugin_id: str
    title: str
    widget_factory: WidgetFactory
    header_actions: list[PanelHeaderAction] = field(default_factory=list)

@dataclass(frozen=True)
class ActionSpec:
    action_name: str     # namespaced: "search.focus"
    callback: UiActionCallback
    label: str
    accelerator: str | None = None

@dataclass(frozen=True)
class MenuItem:
    menu: str            # "file" | "edit" | "view" | "go"
    label: str
    action_name: str
    accelerator: str | None = None

@dataclass(frozen=True)
class DialogSpec:
    dialog_id: str
    presenter: DialogPresenter
    single_instance: bool = True

class HostUIBridge(Protocol):
    def register_action(self, spec: ActionSpec) -> None: ...
    def register_panel(self, panel: PanelSpec, *, activity_item: ActivityBarItem) -> None: ...
    def register_dialog(self, spec: DialogSpec) -> None: ...
    def set_activity_badge(self, plugin_id: str, badge_text: str | None) -> None: ...
    def set_panel_header_actions(self, plugin_id: str, actions: list[PanelHeaderAction]) -> None: ...
    def show_dialog(self, dialog_id: str) -> None: ...
    def activate_panel(self, plugin_id: str) -> None: ...

class PluginContext:
    """The ONLY host interface available to plugins."""
    def get_service(self, service_id: str) -> object: ...
    def get_event_bus(self) -> "EventBus": ...
    def get_config(self, plugin_id: str) -> dict: ...
    def set_config(self, plugin_id: str, data: dict) -> None: ...
    def get_ui(self) -> HostUIBridge: ...

Service IDs reserved by the host shell:
- `"file"` → `FileService`
- `"git"` → `GitService`
- `"search"` → `SearchService`
- `"config"` → `ConfigService`
- `"theme"` → `ThemeService`
- `"tabs"` → `TabQueryService` (read-only tab/document query API exposed by `TabManager`)

class AbstractPlugin(ABC):
    id: str          # unique snake_case e.g. "file_explorer"
    name: str
    version: str = "1.0.0"

    @abstractmethod
    def activate(self, context: PluginContext) -> None:
        """
        Register actions, panels, dialogs, and event subscriptions.
        Called once during startup after the host UI bridge exists.
        """

    def deactivate(self) -> None:
        """Clean up subscriptions. Called on shutdown or disable."""
```

#### PluginManager

`PluginManager` lives in the service layer. It has no GTK imports and manages lifecycle only.

```python
# services/plugin_manager.py
class PluginManager:
    def __init__(self, context: PluginContext): ...
    def register(self, plugin: AbstractPlugin) -> None: ...
    def activate_all(self) -> None: ...
    def deactivate_all(self) -> None: ...
    def get_plugin(self, plugin_id: str) -> AbstractPlugin | None: ...
    def get_activity_bar_items(self) -> list[ActivityBarItem]:
        """Returns sorted items registered by plugins during activation."""
```

#### Core Plugins (shipped by default)

| Plugin ID | Class | Activity Bar Icon | Panel |
|---|---|---|---|
| `file_explorer` | `FileExplorerPlugin` | `folder-symbolic` | Folder tree |
| `search` | `SearchPlugin` | `system-search-symbolic` | Search/replace UI |
| `source_control` | `SourceControlPlugin` | `vcs-changed-symbolic` | Git status/stage/commit |
| `preferences` | `PreferencesPlugin` | *(none — opens dialog)* | — |

All four live in `slate/plugins/core/`. Future plugins drop into `slate/plugins/` with no changes to the shell.

#### Plugin Communication Rules
- Plugins communicate with each other **only** via the `EventBus` or by fetching a shared service via `context.get_service(id)`.
- Plugins never hold direct references to other plugin objects.
- Plugins never import from `slate/ui/`. They may import GTK directly inside plugin modules, but the host boundary remains `PluginContext` + `HostUIBridge`.
- Cross-cutting runtime concerns such as theme resolution are **services**, not plugins. User-facing controls for those services may be exposed by plugins (e.g. Preferences), but ownership of policy stays outside the plugin layer.

Plugin registration rules:
- `activate()` may subscribe to events and register actions/panels/dialogs only. It must not immediately show windows, mutate tab state, or emit startup open events as side effects.
- Panel widgets and dialogs are created lazily through registered factories/presenters. The host shell owns insertion into the layout, parenting, single-instance behavior, and disposal.
- `ActivityBarItem.supports_badge = true` means the plugin may later call `context.get_ui().set_activity_badge(plugin_id, text)`.
- Side-panel header actions are host-owned chrome. Plugins declare them through `PanelSpec.header_actions` and may update them later with `set_panel_header_actions()`.

#### LSP Readiness (required, even though LSP is out of scope for v1)
- LSP remains a backlog item for v1. Do **not** implement language server management, diagnostics UI, symbol indexing, hover, or completion in the initial release.
- The architecture must remain ready for a future `lsp_client` plugin + service pair:
  - editor/tab abstractions must not assume all intelligence comes from local syntax highlighting only
  - document state and file-open events must stay available through services/event bus, not direct widget references
  - future language intelligence must fit as a service-layer orchestration component with plugin/UI consumers
- Reserve the event bus as the integration boundary for future editor intelligence events such as diagnostics, symbol refresh, and definition navigation requests. These event types do not need to ship in v1, but no current design may block them.

---

### 3.3 SOLID Principles

#### S — Single Responsibility

| Class | Single Responsibility |
|---|---|
| `FileService` | Read/write files from disk |
| `GitService` | All git operations |
| `SearchService` | In-project text search |
| `ConfigService` | Read/write config.ini |
| `ThemeService` | Resolve shell/editor theme state and apply theme policy |
| `LanguageDetector` | Map file extension → GtkSource.Language |
| `TabManager` | Manage open tab state |
| `EditorView` | Render one GtkSource.View widget |
| `ActivityBar` | Render icon strip; emit panel-switch signals |
| `SidePanel` | Swap plugin panel widgets in and out |
| `PluginManager` | Load, activate, deactivate plugins |

#### O — Open/Closed
- New panels: implement `AbstractPlugin` — zero changes to `ActivityBar` or `SidePanel`.
- `FileService` targets `AbstractFileBackend`. SSH backend = new file, no surgery.
- `GitService` targets `AbstractVCSBackend`. Mercurial = new backend only.
- `SearchService` targets `AbstractSearchBackend`. Swap `os.walk` for ripgrep = new class only.
- `ThemeService` owns theme policy. Preferences remains a control surface, not the theme owner.

#### L — Liskov Substitution
- All `AbstractPlugin` implementations are valid substitutes: the shell activates them through the same `PluginContext` and consumes the same registered panel/action/dialog contributions.
- All `AbstractFileBackend` implementations raise the same typed exceptions.

#### I — Interface Segregation
- A plugin may register only the contribution types it needs. For example, `PreferencesPlugin` registers an action + dialog and no side panel; `FileExplorerPlugin` registers a panel + actions.
- `AbstractFileBackend` is split into `ReadableBackend` and `WritableBackend`. Read-only backends implement only `ReadableBackend`.

#### D — Dependency Inversion
- `ActivityBar` depends on `list[ActivityBarItem]` (core dataclass), not on any plugin.
- `SourceControlPlugin` depends on `AbstractVCSBackend`, injected via `context.get_service()`.
- `PreferencesPlugin` depends on `ThemeService` and `ConfigService`, injected via `context.get_service()`.
- `SlateWindow` depends on `PluginManager` and `TabManager`, both injected. It never instantiates plugins or services.

---

### 3.4 Design Patterns

#### Event Bus (Observer) — decoupled cross-plugin communication

The typed `EventBus` is the **only** sideways communication channel. No module holds a direct reference to another module's objects.

```python
# core/events.py
@dataclass
class OpenFileRequestedEvent:
    path: str
    line: int | None = None
    column: int | None = None
    focus: bool = True

@dataclass
class OpenDiffRequestedEvent:
    path: str
    staged: bool

@dataclass
class FileOpenedEvent:
    path: str

@dataclass
class FileSavedEvent:
    path: str

@dataclass
class FolderChangedEvent:
    path: str | None

@dataclass
class ActivePanelChangedEvent:
    plugin_id: str

@dataclass
class GitStatusChangedEvent:
    pass

@dataclass
class SearchResultsReadyEvent:
    query: "SearchQuery"
    results: list["SearchResult"]

@dataclass
class ThemeChangedEvent:
    color_mode: str          # "system" | "light" | "dark"
    resolved_is_dark: bool
    editor_scheme: str
```

`FileService` emits `FileSavedEvent` after saving. `SourceControlPlugin` subscribes and refreshes. `FileService` knows nothing about git.

Event ownership rules:
- UI actions, plugins, and startup code emit **request events** such as `OpenFileRequestedEvent` and `OpenDiffRequestedEvent`
- `TabManager` is the only component that turns open requests into editor tabs
- `TabManager` emits `FileOpenedEvent` only after the target tab/view exists and has become the active editor
- services emit state/result events (`FileSavedEvent`, `SearchResultsReadyEvent`, `GitStatusChangedEvent`) but do not create or focus tabs
- plugins may subscribe to result events and request navigation, but they must not emit `FileOpenedEvent` directly

#### Command Pattern — app-level commands and undo/redo

Slate has two distinct undo systems and they must not be conflated:
- text editing undo/redo is owned by each `GtkSource.Buffer`
- `CommandHistory` is only for app-level operations outside the editor buffer, such as stage/unstage and future refactor actions

Every app-level mutating action is a `Command` object with `execute()` and optionally `undo()`.

```python
# core/commands.py
class AbstractCommand(ABC):
    @abstractmethod
    def execute(self) -> None: ...
    def undo(self) -> None: ...  # base: no-op

class SaveFileCommand(AbstractCommand):
    def __init__(self, file_service, path, content): ...
    def execute(self): self.file_service.write(self.path, self.content)

class StageFileCommand(AbstractCommand):
    def __init__(self, git_service, path): ...
    def execute(self): self.git_service.stage(self.path)
    def undo(self): self.git_service.unstage(self.path)
```

Keyboard routing rules:
- when the active editor buffer has focus, `Ctrl+Z` / `Ctrl+Y` invoke buffer-local undo/redo
- when no editor buffer is focused, `Ctrl+Z` / `Ctrl+Y` target `CommandHistory`
- `SaveFileCommand` is executable but not undoable in v1
- Replace All in files is implemented as a service operation with a confirmation step; it does not participate in `CommandHistory` in v1

#### Factory Pattern — editor tab construction

`EditorViewFactory` centralises all GtkSourceView configuration:

```python
# ui/editor/editor_factory.py
class EditorViewFactory:
    def __init__(self, config_service, theme_service, language_detector): ...
    def create(self, path: str | None) -> EditorView:
        # Applies: font, tab width, line numbers, highlight line, colour scheme, language
        # Returns fully configured, ready-to-insert widget
```

`EditorViewFactory` must use `ThemeService` for the resolved editor scheme rather than reading theme keys directly from config.

Preference changes call `EditorView.apply_config()` on all open views for editor settings. Theme changes call `EditorView.apply_theme()` on all open views based on `ThemeChangedEvent`.

#### Strategy Pattern — search and language backends

- `AbstractSearchBackend.search(query, folder) -> list[SearchResult]`  
  Default: `NativeSearchBackend` using `os.walk` + `mmap`. Future: ripgrep subprocess.
- `AbstractLanguageDetector.detect(path) -> GtkSource.Language | None`  
  Default: `GtkSource.LanguageManager`. Future: tree-sitter.

Swap either = new class only. Zero changes to callers.

#### Service Pattern — central theme resolution

Theme behavior is a cross-cutting concern and must not be split across random widgets.

`ThemeService` owns:
- app color mode resolution: `system | light | dark`
- editor scheme resolution for light/dark modes
- explicit-vs-auto editor theme behavior
- startup theme bootstrap from persisted config before the first window is presented
- emitting `ThemeChangedEvent`

GTK/libadwaita runtime application stays in the UI layer via a small helper such as `ui/theme_manager.py`, but the policy and config rules live in the service layer.

#### Minimal Service APIs (implementation contract)

The following APIs are the minimum required public surface for v1. Implementers may add private helpers, but they must not bypass these ownership boundaries.

```python
# services/search_service.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class SearchQuery:
    text: str
    folder: str
    glob: str | None = None
    match_case: bool = False
    whole_word: bool = False
    regex: bool = False
    include_hidden: bool = False

@dataclass(frozen=True)
class ReplaceRequest:
    query: SearchQuery
    replacement: str
    target_paths: list[str] | None = None
    dirty_paths: set[str] = field(default_factory=set)

@dataclass(frozen=True)
class ReplaceSummary:
    files_changed: int
    replacements_made: int
    skipped_dirty_paths: list[str]
    failed_paths: list[str]

class SearchService:
    def search(self, query: SearchQuery) -> None: ...
    def replace_all(self, request: ReplaceRequest) -> ReplaceSummary: ...
```

`SearchService` rules:
- `search()` runs asynchronously and emits `SearchResultsReadyEvent(query=<full SearchQuery>, results=...)`
- `replace_all()` is synchronous from the caller's perspective and returns a structured `ReplaceSummary`
- replace operations modify on-disk files only; they never mutate editor widgets directly
- `dirty_paths` must be skipped rather than overwritten silently
- unreadable/binary/failed files are skipped and returned in `failed_paths`; partial success is allowed and must be surfaced to the user
- if `target_paths` is `None`, replace applies to the current full result set for `query`

```python
# services/config_service.py
class ConfigService:
    def load(self) -> None: ...
    def save(self) -> None: ...

    def get_editor_settings(self) -> dict: ...
    def update_editor_settings(self, data: dict) -> None: ...

    def get_app_state(self) -> dict: ...
    def update_app_state(self, data: dict) -> None: ...

    def get_plugin_config(self, plugin_id: str) -> dict: ...
    def update_plugin_config(self, plugin_id: str, data: dict) -> None: ...
```

`ConfigService` rules:
- owns raw `config.ini` parsing, defaults, and persistence only
- returns plain Python dictionaries for v1; no GTK objects and no theme-resolution logic
- merges partial updates into existing sections instead of replacing unrelated keys
- is the persistence backend used by `PluginContext.get_config()` / `set_config()`

```python
# services/theme_service.py
class ThemeService:
    def __init__(self, config_service, event_bus): ...

    def get_color_mode(self) -> str: ...             # "system" | "light" | "dark"
    def set_color_mode(self, mode: str) -> None: ...

    def get_theme_mode(self) -> str: ...             # "auto" | "explicit"
    def set_theme_mode(self, mode: str) -> None: ...

    def get_scheme_preferences(self) -> dict: ...
    def set_scheme_preferences(
        self,
        *,
        light_scheme: str | None = None,
        dark_scheme: str | None = None,
        explicit_scheme: str | None = None,
    ) -> None: ...

    def resolve_editor_scheme(self, *, system_is_dark: bool | None = None) -> str: ...
    def get_theme_state(self, *, system_is_dark: bool | None = None) -> dict: ...
    def emit_theme_changed(self, *, system_is_dark: bool | None = None) -> None: ...
```

`ThemeService` rules:
- owns theme preference reads/writes and resolved editor-scheme selection
- persists all theme-related config through `ConfigService`
- exposes only serializable state to callers; GTK runtime objects remain in `ui/theme_manager.py`
- `set_color_mode`, `set_theme_mode`, and `set_scheme_preferences` must persist config and emit `ThemeChangedEvent`
- `resolve_editor_scheme()` is the single source of truth for editor theming decisions used by `EditorViewFactory` and live theme updates

```python
# ui/editor/tab_manager.py
class TabManager:
    def __init__(self, factory, file_service, event_bus): ...

    def new_tab(self) -> None: ...
    def open_file(
        self,
        path: str,
        *,
        line: int | None = None,
        column: int | None = None,
        focus: bool = True,
    ) -> None: ...

    def open_diff(self, path: str, *, staged: bool) -> None: ...
    def get_active_tab(self) -> "TabState | None": ...
    def get_open_tabs(self) -> list["TabState"]: ...
    def get_dirty_paths(self) -> set[str]: ...
    def close_tab(self, tab_id: str) -> bool: ...
    def save_active_tab(self) -> None: ...
    def save_active_tab_as(self, path: str) -> None: ...
```

`TabManager` rules:
- subscribes to `OpenFileRequestedEvent` and `OpenDiffRequestedEvent` on the event bus
- is the only owner of tab creation, reuse, activation, close behavior, and tab-state bookkeeping
- owns untitled-tab creation for `Ctrl+T`; untitled tabs have no path until the first successful Save As
- reuses an existing normal file tab for the same path; diff tabs are tracked separately and are not reused as normal file tabs
- emits `FileOpenedEvent` only after a file tab becomes active
- owns cursor placement and scroll positioning for line/column navigation after open
- never reads config directly; window/sidebar/session restore remains outside `TabManager`

```python
# services/tab_query_service.py
class TabQueryService:
    def get_open_tabs(self) -> list["TabState"]: ...
    def get_dirty_paths(self) -> set[str]: ...
    def is_path_dirty(self, path: str) -> bool: ...
```

`TabManager` must implement `TabQueryService` so plugins can query dirty/open path state without touching GTK widgets.

#### Repository Pattern — git data access

`GitRepository` wraps all `gitpython` calls. Nothing else in the codebase touches `gitpython`:

```python
# services/git_repository.py
class GitRepository:
    def get_status(self) -> list[FileStatus]: ...
    def stage(self, path: str) -> None: ...
    def unstage(self, path: str) -> None: ...
    def commit(self, message: str) -> None: ...
    def get_diff(self, path: str, staged: bool) -> str: ...
    def list_branches(self) -> list[str]: ...
    def checkout_branch(self, name: str) -> None: ...
    def get_current_branch(self) -> str: ...
```

---

### 3.5 Directory Structure

```
slate/
├── main.py                              ← entry point; creates SlateApplication
├── requirements.txt
│
├── core/                                ← pure Python; zero GTK; zero I/O
│   ├── plugin_api.py                    ← AbstractPlugin, PluginContext, ActionSpec, PanelSpec
│   ├── events.py                        ← all typed event dataclasses
│   ├── event_bus.py                     ← EventBus implementation
│   ├── commands.py                      ← AbstractCommand, CommandHistory
│   ├── models.py                        ← FileStatus, TabState, SearchResult, BranchInfo
│   ├── exceptions.py                    ← typed exception hierarchy
│   └── interfaces/
│       ├── file_backend.py              ← ReadableBackend, WritableBackend ABCs
│       ├── vcs_backend.py               ← AbstractVCSBackend ABC
│       ├── language_detector.py         ← AbstractLanguageDetector ABC
│       └── search_backend.py            ← AbstractSearchBackend ABC
│
├── services/                            ← business logic; zero GTK
│   ├── plugin_manager.py                ← PluginManager
│   ├── file_service.py                  ← file read/write; emits FileSaved/FileOpened
│   ├── git_service.py                   ← git orchestration; emits GitStatusChanged
│   ├── git_repository.py                ← gitpython wrapper (Repository pattern)
│   ├── search_service.py                ← search orchestration; emits SearchResultsReady
│   ├── tab_query_service.py             ← read-only tab/document query interface
│   ├── config_service.py                ← reads/writes config.ini
│   ├── theme_service.py                 ← theme policy + scheme resolution
│   ├── local_file_backend.py            ← ReadableBackend + WritableBackend impl
│   ├── native_search_backend.py         ← os.walk + mmap (Strategy impl)
│   └── language_detector.py             ← GtkSource.LanguageManager (Strategy impl)
│
├── ui/                                  ← GTK widgets; depends on services + core only
│   ├── app.py                           ← Adw.Application; composition root; all DI wiring
│   ├── theme_manager.py                 ← applies ThemeService state to Adw/Gtk CSS providers
│   ├── window.py                        ← SlateWindow; layout skeleton only
│   ├── plugin_host.py                   ← HostUIBridge implementation for panels/actions/dialogs
│   ├── activity_bar.py                  ← vertical icon strip widget
│   ├── side_panel.py                    ← Gtk.Stack that swaps plugin panel widgets
│   ├── editor/
│   │   ├── editor_view.py               ← single GtkSource.View wrapper
│   │   ├── editor_factory.py            ← EditorViewFactory (Factory pattern)
│   │   └── tab_manager.py               ← GtkNotebook + TabState management
│   ├── dialogs/
│   │   └── about.py
│   └── actions.py                       ← Gio.SimpleAction registration + keybindings
│
└── plugins/
    └── core/                            ← core plugins shipped with Slate
        ├── __init__.py                  ← exports all four core plugins
        ├── file_explorer/
        │   ├── __init__.py              ← FileExplorerPlugin(AbstractPlugin)
        │   └── widgets.py               ← FileTreeView, context menus
        ├── search/
        │   ├── __init__.py              ← SearchPlugin(AbstractPlugin)
        │   └── widgets.py               ← SearchPanel, ResultsList
        ├── source_control/
        │   ├── __init__.py              ← SourceControlPlugin(AbstractPlugin)
        │   └── widgets.py               ← ChangedFilesList, DiffView, CommitBar
        └── preferences/
            ├── __init__.py              ← PreferencesPlugin(AbstractPlugin)
            └── dialog.py                ← Adw.PreferencesWindow
```

---

### 3.6 Dependency Injection — Composition Root

All wiring happens in `ui/app.py`. No class instantiates its own dependencies.

```python
# ui/app.py — composition root
class SlateApplication(Adw.Application):
    def do_activate(self):
        # Core
        event_bus    = EventBus()

        # Services
        config       = ConfigService()
        file_svc     = FileService(LocalFileBackend(), event_bus)
        lang_det     = GtkSourceLanguageDetector()
        git_repo     = GitRepository()
        git_svc      = GitService(git_repo, event_bus)
        search_svc   = SearchService(NativeSearchBackend(), event_bus)
        theme_svc    = ThemeService(config, event_bus)

        # UI skeleton + host bridge
        theme_mgr = ThemeManager(theme_svc)
        theme_mgr.apply_initial_state()
        factory  = EditorViewFactory(config, theme_svc, lang_det)
        tab_mgr  = TabManager(factory, file_svc, event_bus)

        window = SlateWindow(
            application=self,
            tab_manager=tab_mgr,
            config=config,
            event_bus=event_bus,
        )
        host_ui = PluginHostBridge(window)

        # Plugin context (service registry + bus + config + host UI)
        service_registry = {
            "file": file_svc, "git": git_svc,
            "search": search_svc, "config": config,
            "theme": theme_svc, "tabs": tab_mgr,
        }
        plugin_ctx = PluginContext(service_registry, event_bus, config, host_ui)

        # Plugin manager
        plugin_mgr = PluginManager(plugin_ctx)
        plugin_mgr.register(FileExplorerPlugin())
        plugin_mgr.register(SearchPlugin())
        plugin_mgr.register(SourceControlPlugin())
        plugin_mgr.register(PreferencesPlugin())
        plugin_mgr.activate_all()
        window.attach_plugin_manager(plugin_mgr)
        window.attach_plugin_host(host_ui)

        window.restore_window_state()
        window.restore_sidebar_state()
        window.restore_startup_context()   # folder/file from argv or persisted app state
        window.present()
```

Startup order requirements:
1. load config
2. create `ThemeService` and apply initial theme state before presenting any window
3. create window/editor infrastructure and `HostUIBridge`
4. activate plugins and let them register actions/panels/dialogs against the host bridge
5. restore window geometry/sidebar state
6. resolve startup context from CLI args first, otherwise persisted app state
7. only restore `last_folder` when no CLI file/folder argument is provided
8. never auto-restore editor tabs in v1

Startup/opening responsibility rules:
- CLI handling converts a startup file path into `OpenFileRequestedEvent`
- CLI handling converts a startup folder path into `FolderChangedEvent`
- `SlateWindow` or top-level actions may trigger requests, but tab creation still flows through `TabManager`

---

### 3.7 Error Handling Strategy

- Services raise typed exceptions from `core/exceptions.py`:
  `SlateFileNotFoundError`, `SlatePermissionError`, `GitNotARepoError`, `GitOperationError`, `GitDirtyWorkingTreeError`, `SearchBackendError`
- UI layer catches at the boundary → `Adw.AlertDialog`. Services never show UI.
- Plugins show their own errors inline (e.g. "Not a git repository" label in Source Control panel).
- Plugin `activate()` calls are wrapped in try/except — a failing plugin is skipped with a stderr log; the app continues.

---

### 3.8 Testability

The core and service layers have zero GTK imports. All business logic is testable with plain `pytest`. This is a hard requirement, not a nice-to-have.

Required testing standard:
- `core/` and `services/` must maintain **90%+** line coverage
- non-widget plugin logic must maintain **85%+** line coverage
- `ui/` is validated with smoke/integration tests for critical flows; do not chase superficial percentage at the expense of brittle GTK tests
- no feature is complete without tests for: normal path, failure path, and one regression-prone edge case
- every bug fix should add a regression test when feasible

Mandatory test layers:
- **Unit tests**: `EventBus`, `CommandHistory`, `FileService`, `SearchService`, `GitService`, `ConfigService`, `ThemeService`, `PluginManager`
- **Contract tests**: file backend, search backend, VCS backend, plugin contribution/activation behavior, event request/result ownership rules
- **Integration tests**: open/edit/save flow, search results navigation, git stage/unstage/commit flow, preferences live-update flow, startup restore of config and active panel, CLI startup file/folder opening
- **Plugin isolation tests**: one failing plugin must not crash startup; plugin actions and contributions remain isolated
- **UI smoke tests**: main window creation, activity bar population, side panel switching, preferences dialog open, editor tab creation

Mandatory event/open-flow scenarios:
- emitting `OpenFileRequestedEvent(path)` creates or focuses exactly one normal editor tab for that file
- emitting `OpenFileRequestedEvent(path, line, column)` positions the cursor and scroll state correctly after open
- repeated open requests for an already-open file reuse the existing tab instead of creating duplicates
- emitting `OpenDiffRequestedEvent(path, staged)` creates a read-only diff tab that is distinct from the normal file tab for the same path
- `TabManager` emits `FileOpenedEvent(path)` only after the tab is active and ready
- `Ctrl+O`, file explorer activation, search result activation, and CLI file startup all reach the editor through the same request-event path
- opening a file must not implicitly change the current folder root
- opening a folder emits `FolderChangedEvent` and updates explorer/source-control state without creating editor tabs by itself
- startup with a CLI file path must not restore `last_folder`; startup with a CLI folder path must prefer that folder over persisted state
- startup with no CLI path and a persisted `last_folder` must restore folder/sidebar state but still avoid tab restoration in v1

Required regression-prone cases:
- open-file request for a path already open in a dirty tab
- search result navigation into a file that is already open on another line
- diff-tab open followed by normal file open for the same path
- plugin emits an open request before another plugin finishes refreshing panel state
- startup restore with a saved `active_panel` that no longer exists

```python
def test_stage_file():
    mock_repo = MockVCSBackend()
    svc = GitService(mock_repo, EventBus())
    svc.stage("src/main.py")
    assert "src/main.py" in mock_repo.staged_files

def test_plugin_registers_activity_bar_item():
    host_ui = MockHostUIBridge()
    ctx = MockPluginContext(ui=host_ui)
    pm = PluginManager(ctx)
    pm.register(FileExplorerPlugin())
    pm.activate_all()
    assert any(i.plugin_id == "file_explorer" for i in host_ui.activity_items)
```

No GTK initialisation required for any service, core, or plugin-logic test.

Tests should prefer temporary directories and real temporary git repositories for service-level integration over excessive mocking. Mock only at explicit external boundaries or when injecting failure paths.

For file-opening tests, use event-bus-driven fixtures rather than calling notebook APIs directly. The test target is the contract that callers emit requests and `TabManager` owns tab creation/focus behavior.

---

## 4. Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.10+ | Fast development; deep Linux system integration |
| GUI Toolkit | GTK4 via PyGObject (`gi.repository.Gtk`) | Native theme inheritance; system library |
| HIG Shell | libadwaita (`gi.repository.Adw`) | Automatic Adwaita theme; dark mode API |
| Syntax Highlighting | GtkSourceView 5 (`gi.repository.GtkSource`) | GTK-native; zero extra deps |
| File Watching | `Gio.FileMonitor` | Native inotify; no polling |
| Git | `gitpython` (PyPI) + system `git` binary | Pythonic; leverages installed git |
| In-project Search | Python `os.walk` + `mmap` (stdlib) | Native; zero deps; fast on Linux |
| Config | Python `configparser` | Standard library; zero deps |

### System Dependencies (apt)
```
python3  python3-gi  python3-gi-cairo
gir1.2-gtk-4.0  gir1.2-gtksource-5  gir1.2-adw-1
```

### Python Dependencies (requirements.txt)
```
gitpython>=3.1
PyGObject>=3.44
```

---

## 5. Entry Point

```
python main.py                    → blank window; restores last folder if configured
python main.py /path/to/folder    → loads folder in file explorer panel
python main.py /path/to/file.py   → opens single file in editor; no sidebar folder
```

`main.py` only creates `SlateApplication` and calls `run()`. All wiring is in `ui/app.py`.

---

## 6. UI Layout

### 6.1 Overall Structure

```
┌──────────────────────────────────────────────────────────────────────┐
│  Slate                                        [🌙]  [⚙]  [_][□][×] │  ← Adw.HeaderBar
├────┬───────────┬─────────────────────────────────────────────────────┤
│    │           │  main.py ×  │  index.html ×  │  main.rs ×  │  [+]  │  ← GtkNotebook tabs
│ 📁 │           ├─────────────────────────────────────────────────────┤
│    │  SIDE     │                                                      │
│ 🔍 │  PANEL    │                                                      │
│    │  (active  │              GtkSource.View (editor area)            │
│ 🌿 │   plugin  │                                                      │
│    │   widget) │                                                      │
│ ⚙  │           │                                                      │
│    │           │                                                      │
└────┴───────────┴─────────────────────────────────────────────────────┘
  ↑        ↑
Activity  Side Panel
Bar       (220px default,
(48px)    resizable,
          collapsible)
```

### 6.2 Activity Bar (`ui/activity_bar.py`)

- Fixed vertical strip, 48px wide, far left — mirrors VSCode
- One `Gtk.ToggleButton` per plugin that returns an `ActivityBarItem`, ordered by `item.order`
- XDG symbolic icons (e.g. `folder-symbolic`, `system-search-symbolic`, `vcs-changed-symbolic`)
- Clicking an icon: activates that panel, OR collapses the side panel if already active
- Active icon: 2px left-edge accent bar (CSS class `active-panel-indicator`)
- `ActivityBar` receives `list[ActivityBarItem]` from `PluginManager` — has no knowledge of concrete plugins
- Numeric badges are rendered only for items with `supports_badge = true`; badge state is pushed by the host bridge
- Emits `ActivePanelChangedEvent` on the event bus when the user switches panels

### 6.3 Side Panel (`ui/side_panel.py`)

- `Gtk.Stack` that swaps in registered plugin panel widgets created from `PanelSpec.widget_factory`
- Width: 220px default; resizable via `Gtk.Paned`; minimum 150px
- Panel header bar: plugin name label + optional action buttons from `PanelSpec.header_actions`
- Collapsible: clicking the active activity bar button again hides the panel (`Ctrl+B` toggles)
- Persists width and last active `plugin_id` across sessions
- On startup, restored `active_panel` is used only if `side_panel_visible = true`; otherwise the panel stays collapsed
- If a configured `active_panel` no longer exists, fall back to `file_explorer` when a folder is loaded, otherwise leave the panel hidden

### 6.4 Editor Area (`ui/editor/`)

- `Gtk.Notebook` with scrollable, reorderable tabs
- Tab label: filename; dirty = `● filename`; read-only = `🔒 filename`
- Each tab contains one `EditorView` inside `Gtk.ScrolledWindow`

### 6.5 Header Bar

- `Adw.HeaderBar` — no traditional menu bar; clean look
- Left: app icon + "Slate"
- Right: dark mode cycle button (🌙/☀/⊙) + preferences button (⚙)
- All file/edit actions via keyboard shortcuts only in v1

---

## 7. Core Plugins — Feature Specification

### 7.1 File Explorer Plugin (`file_explorer`)

**Activity bar:** `folder-symbolic`, order 10  
**Panel header:** current folder name + `[Open Folder]` button

- Single root folder; set via `Ctrl+Shift+O` or panel button
- `Gtk.TreeView` populated lazily (expand on click)
- File icons via `Gio.content_type_get_icon`
- Hidden files hidden by default; toggle in panel header menu
- Last folder persisted in config; restored on launch

**File context menu:** Open · Rename (inline) · Delete (confirm) · Copy Relative Path · Copy Absolute Path  
**Folder context menu:** New File · New Folder · Rename · Delete

**Keybinding contributed:** `Ctrl+Shift+O` → open folder  
**Events subscribed:** `FolderChangedEvent`  
**Events emitted:** `FolderChangedEvent`, `OpenFileRequestedEvent`

Opening behavior:
- activating a file row emits `OpenFileRequestedEvent(path=<selected file>)`
- activating a folder row expands/collapses it; it does not open a tab
- choosing a new root folder emits `FolderChangedEvent(path=<folder>)`

---

### 7.2 Search Plugin (`search`)

**Activity bar:** `system-search-symbolic`, order 20  
**Panel header:** "Search"

#### Find in Files
- `Gtk.SearchEntry` at panel top
- Option toggles: Match Case · Whole Word · Regex
- File glob filter entry (e.g. `*.py`)
- Results: `Gtk.TreeView` grouped by file
  - File row: `filename  (N matches)`
  - Match row: `  line_num: ...line content...` with match bolded
- Clicking a result: emits `OpenFileRequestedEvent(path, line, column)` so the editor opens the file, scrolls to the match, and highlights it
- Search runs on `Enter` (not live) to avoid disk hammering

#### Find & Replace
- Toggle in panel header switches to replace mode
- Replace `Gtk.Entry` appears below search
- Replace · Replace All (with confirmation)

Replace semantics for v1:
- replace operations act on files on disk, not directly on editor widgets
- before `Replace All`, the plugin queries `TabQueryService.get_dirty_paths()` and passes those paths into `SearchService.replace_all()`
- dirty open files are skipped and shown in the completion summary instead of being overwritten
- `Replace All` applies only to the current confirmed search query/options/folder/glob combination; changing the query invalidates the old result set
- after successful replacements, any currently open clean tab for a changed file must be reloaded or refreshed through the existing file-monitor/reload path

#### Backend
- `SearchService` → `NativeSearchBackend` (Python `os.walk` + `mmap`)
- Runs on a `GLib.ThreadPool` thread — UI stays responsive
- Emits `SearchResultsReadyEvent`; panel subscribes and renders

**Keybindings contributed:**  
`Ctrl+Shift+F` → focus search panel  
`Ctrl+H` → focus search panel in replace mode
**Events subscribed:** `SearchResultsReadyEvent`  
**Events emitted:** `OpenFileRequestedEvent`

---

### 7.3 Source Control Plugin (`source_control`)

**Activity bar:** `vcs-changed-symbolic` with numeric badge (change count), order 30  
**Panel header:** "Source Control" · branch dropdown

Shows "Not a git repository" if the open folder has no `.git`.

#### Branch Switcher
- `Gtk.DropDown` at panel top; shows current branch
- Lists all local branches
- Switching: warns if dirty → `git checkout <branch>`

#### Changed Files List
- `Gtk.ListBox` — rows: `[checkbox]  icon  filename  badge`
- Badges: `M` modified · `A` added · `D` deleted · `?` untracked (colour coded)
- Checkbox = staged state; checking/unchecking calls `git add` / `git restore --staged`
- Emits `GitStatusChangedEvent` after each stage/unstage

#### Diff Viewer
- Clicking a changed file emits `OpenDiffRequestedEvent(path, staged)` and opens a **read-only diff tab** in the editor: `~ filename (diff)`
- GtkSourceView with `diff` language: green additions, red deletions
- Uses `git diff <path>` or `git diff --cached <path>` depending on staged state

#### Commit Bar
- `Gtk.TextView` (multi-line); first line = subject, blank line, body
- Character counter (72-char soft limit shown in yellow/red)
- `[Commit]` button: disabled unless staged files + non-empty message
- On commit: `git commit -m "..."` → clears message, refreshes panel, shows `Adw.Toast`

#### Auto-refresh
- Subscribes to `FileSavedEvent` → refreshes status
- `Gio.FileMonitor` on `.git/index` for instant badge update on external git ops
- Manual ↻ refresh button in panel header
- After every refresh, the plugin updates its activity badge through `context.get_ui().set_activity_badge("source_control", "<count>")`; `None` hides the badge

**Keybinding contributed:** `Ctrl+Shift+G` → focus source control panel  
**Events subscribed:** `FileSavedEvent`, `FolderChangedEvent`, `GitStatusChangedEvent`  
**Events emitted:** `OpenDiffRequestedEvent`

---

### 7.4 Preferences Plugin (`preferences`)

**Activity bar:** none — opens dialog  
Triggered by header bar ⚙ or `Ctrl+,`

This plugin is a **control surface** only. It does not own theme policy. Theme behavior is owned by `ThemeService`.

Registration contract:
- the plugin registers a dialog contribution with `dialog_id = "preferences.window"`
- the plugin registers an action `preferences.open`
- the header-bar ⚙ button and `Ctrl+,` both invoke `preferences.open`
- `preferences.open` calls `context.get_ui().show_dialog("preferences.window")`
- the host enforces single-instance presentation of the preferences window for the active main window

`Adw.PreferencesWindow` with two pages:

**Page 1 — Editor**

| Setting | Widget | Default |
|---|---|---|
| Font | `Gtk.FontDialogButton` | Monospace 13 |
| Tab Width | `Adw.SpinRow` (1–8) | 4 |
| Insert Spaces | `Adw.SwitchRow` | true |
| Show Line Numbers | `Adw.SwitchRow` | true |
| Highlight Current Line | `Adw.SwitchRow` | true |
| Word Wrap | `Adw.SwitchRow` | false |
| Auto-indent | `Adw.SwitchRow` | true |

**Page 2 — Appearance**

| Setting | Widget |
|---|---|
| Color Mode | `Adw.ComboRow` (System / Light / Dark) |
| Editor Theme Mode | `Adw.ComboRow` (Auto / Explicit) |
| Light Scheme | `Adw.ComboRow` (curated GtkSourceView light schemes) |
| Dark Scheme | `Adw.ComboRow` (curated GtkSourceView dark schemes) |
| Explicit Scheme | `Adw.ComboRow` (all installed GtkSourceView schemes; enabled only in Explicit mode) |

All changes apply live (no Apply button). Saves to config immediately.  
Color mode and scheme changes flow through `ThemeService`, which emits `ThemeChangedEvent` so all open `EditorView` instances update their scheme.

Theme rules:
- In `Auto` mode, the editor scheme follows the resolved shell mode using configured light/dark schemes
- In `Explicit` mode, the chosen editor scheme is preserved across shell mode changes
- Preferences should present a curated recommended list first; raw installed schemes may still be available for explicit selection

---

## 8. Editor — Core Behaviour

### 8.1 Tab Management
- `GtkNotebook`: scrollable, reorderable tabs
- Middle-click or × to close; dirty guard: `Adw.AlertDialog` (Save / Discard / Cancel)
- File changed on disk: `Gio.FileMonitor` triggers "Reload?" dialog on focus-in
- `Ctrl+B` collapses/restores side panel
- `Ctrl+T` creates a new untitled tab; first save must route through Save As
- `TabManager` is the only owner of open-tab state; plugins and services request file opens through services/events, not by touching notebook widgets directly
- `EditorView` must separate editor-setting updates from theme updates so theme changes do not overwrite unrelated editor preferences

Open flow contract:
- `Ctrl+O`, file explorer activation, search result activation, and CLI file launch all converge on `OpenFileRequestedEvent`
- `TabManager` handles `OpenFileRequestedEvent` by reusing an existing tab for the path when already open; otherwise it creates a new tab
- after opening, `TabManager` focuses the tab, positions the cursor if line/column were provided, and emits `FileOpenedEvent(path)`
- source control diff requests flow through `OpenDiffRequestedEvent`; `TabManager` creates read-only diff tabs that are distinct from normal file tabs
- request events are idempotent from the caller's perspective: callers request navigation/opening and do not need to know whether a tab already existed

### 8.2 Syntax Highlighting (GtkSource.LanguageManager)

| Language | Extensions |
|---|---|
| Python | `.py` `.pyw` |
| JavaScript | `.js` `.mjs` `.cjs` |
| TypeScript | `.ts` `.tsx` |
| Rust | `.rs` |
| HTML | `.html` `.htm` |
| CSS | `.css` `.scss` |
| JSON | `.json` |
| Markdown | `.md` |
| Shell | `.sh` `.bash` |
| Diff | *(used for diff viewer tabs)* |

### 8.3 Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+T` | New empty tab |
| `Ctrl+W` | Close current tab |
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+O` | Open File |
| `Ctrl+Shift+O` | Open Folder |
| `Ctrl+,` | Preferences |
| `Ctrl+Shift+F` | Focus Search panel |
| `Ctrl+Shift+G` | Focus Source Control panel |
| `Ctrl+B` | Toggle Side Panel |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

All shortcuts registered as `Gio.SimpleAction` in `ui/actions.py`. Plugins add their own via `context.get_ui().register_action()`.

`Ctrl+O` opens a file chooser and emits `OpenFileRequestedEvent` for the selected file. It does not bypass `TabManager`.
`Ctrl+Z` / `Ctrl+Y` target the active `GtkSource.Buffer` when an editor has focus; otherwise they target app-level `CommandHistory`.

---

## 9. Theme & Appearance

- `Adw.Application` inherits system GTK4/Adwaita theme automatically — zero custom CSS on the chrome
- Theme handling is a dedicated subsystem, not a plugin. `ThemeService` owns theme policy; `PreferencesPlugin` only edits user preferences.
- Dark mode toggle cycles: System → Light → Dark → System via `ThemeService`, with UI application delegated to `ui/theme_manager.py`
- `ThemeService` emits `ThemeChangedEvent(color_mode, resolved_is_dark, editor_scheme)` → all open `EditorView` instances switch GtkSourceView scheme
- Default schemes: `"Adwaita"` (light) / `"Adwaita-dark"` (dark)
- In `Auto` editor theme mode, Slate switches between configured light/dark editor schemes automatically
- In `Explicit` editor theme mode, Slate preserves the chosen GtkSourceView scheme regardless of shell mode
- Slate may ship a small CSS layer for app-specific accents only: active panel indicator, git badges, diff/status accents, search match emphasis
- Plugin widgets should use shared Slate CSS classes/tokens for custom accents instead of hard-coded colours

---

## 10. Configuration

File: `~/.config/slate/config.ini`

```ini
[editor]
font = Monospace 13
tab_width = 4
insert_spaces = true
show_line_numbers = true
highlight_current_line = true
word_wrap = false
auto_indent = true
theme_mode = auto              ; auto | explicit
light_scheme = Adwaita
dark_scheme = Adwaita-dark
explicit_scheme = Adwaita

[app]
color_mode = system            ; system | light | dark
last_folder = /home/raziur/projects/myproject
active_panel = file_explorer   ; plugin_id of last active panel
side_panel_width = 220
side_panel_visible = true
window_width = 1200
window_height = 800
window_maximized = false

[plugin.search]
include_hidden = false
last_glob_filter =

[plugin.source_control]
auto_refresh = true
```

Plugin config sections use `[plugin.<plugin_id>]`. Each plugin reads/writes its own section via `PluginContext.get_config()` / `set_config()` — plugins never touch config.ini directly.

Theme config is owned by `ThemeService`. Plugins must not read/write theme keys directly except through the service API exposed in `PluginContext`.

---

## 11. Opening Behaviour

```
python main.py                    → blank window; restore last_folder if set
python main.py /path/to/folder    → load folder; file explorer panel opens
python main.py /path/to/file.py   → open file in editor; no folder loaded
```

Startup precedence rules:
- CLI path always wins over persisted `last_folder`
- if CLI path is a folder: load that folder, show side panel, and prefer `file_explorer` as the active panel unless the user explicitly switches afterward
- if CLI path is a file: open that file in an editor tab and do not auto-load `last_folder`
- if no CLI path is provided and `last_folder` exists: load it and restore sidebar visibility/active panel from config
- if no CLI path is provided and no `last_folder` exists: start with a blank window

File/folder opening rules:
- opening a folder replaces the current explorer root and emits `FolderChangedEvent`
- opening a file does not implicitly change the current folder root in v1
- single-file mode remains valid even when no project folder is loaded
- if a file is opened from search or explorer within the current folder, the folder root remains unchanged

Window restoration rules:
- restore `window_width`, `window_height`, and `window_maximized` before presenting the window
- restore `side_panel_width`, `side_panel_visible`, and `active_panel` after plugins are activated so referenced panels/actions exist
- tabs are not auto-restored in v1

---

## 12. Error Handling

| Situation | Handling |
|---|---|
| File not found / permission denied | `Adw.AlertDialog` at the UI boundary; service raises typed exception |
| Git not a repo | Inline "Not a git repository" label in Source Control panel |
| Git operation failure | Inline red status label in panel; `Adw.Toast` on commit error |
| Unsaved changes on quit | `Adw.AlertDialog` (Save / Discard / Cancel) |
| File changed on disk | `Gio.FileMonitor` → "File changed. Reload?" dialog on focus |
| Plugin activation failure | Logged to stderr; plugin skipped; app continues |

---

## 13. Packaging Notes (future .deb / GitHub release)

- App ID: `io.github.<username>.slate`
- Desktop entry: `slate.desktop` → `Exec=python3 /usr/lib/slate/main.py`
- Icon: `hicolor/scalable/apps/io.github.<username>.slate.svg`
- `requirements.txt`:
  ```
  gitpython>=3.1
  PyGObject>=3.44
  ```
- No virtualenv needed — system packages sufficient on Ubuntu 22.04+
- Future: Flatpak manifest with `python3-gi` as runtime; `.deb` with `python3-gi` as `Depends:`

---

## 14. Backlog (Out of Scope for v1)

- `lsp_client` plugin + service — LSP / code completion / diagnostics
  - must be implemented as a service-layer language-intelligence orchestration component plus plugin/UI consumers
  - must reuse event bus boundaries rather than direct editor-widget coupling
- `terminal` plugin — integrated terminal panel
- Git log / blame viewer — extension of `source_control` plugin
- Minimap
- Split editor panes
- Multiple workspace roots
- Remote/SSH backend — new `AbstractFileBackend` implementation
- Third-party plugin loading from `~/.config/slate/plugins/`
- `outline` plugin — symbol tree from GtkSourceView buffer

---

## 15. Quality Gates

The following are release requirements for v1:
- all core workflows ship with automated tests before the feature is considered complete
- plugin activation failure isolation is tested and enforced
- theme switching is verified for both shell mode changes and editor scheme changes
- startup/config restoration is covered by integration tests
- request-event-driven file opening, tab reuse, and diff-tab behavior are covered by automated tests
- test coverage thresholds from section 3.8 are enforced in CI
