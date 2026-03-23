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
- Plugin system from day one — core features ARE plugins
- Ship four core plugins: File Explorer, Search, Source Control (Git), Preferences
- Syntax highlighting for common languages via GtkSourceView (zero extra deps)
- Leverage Python's native Linux integration: GIO, inotify via GLib, gitpython, os/mmap for search

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

Every plugin implements `AbstractPlugin` from `core/plugin_api.py`:

```python
# core/plugin_api.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio

@dataclass
class ActivityBarItem:
    plugin_id: str
    icon_name: str       # XDG symbolic icon e.g. "folder-symbolic"
    tooltip: str
    order: int           # lower = higher in bar

@dataclass
class KeyBinding:
    accelerator: str     # e.g. "<Control><Shift>f"
    action_name: str     # namespaced: "search.find-in-files"
    label: str

@dataclass
class MenuItem:
    menu: str            # "file" | "edit" | "view" | "go"
    label: str
    action_name: str
    accelerator: str | None = None

class PluginContext:
    """The ONLY interface between plugins and the host shell."""
    def get_service(self, service_id: str) -> object: ...
    def get_event_bus(self) -> "EventBus": ...
    def get_config(self, plugin_id: str) -> dict: ...
    def set_config(self, plugin_id: str, data: dict) -> None: ...
    def register_action(self, action: Gio.SimpleAction) -> None: ...

class AbstractPlugin(ABC):
    id: str          # unique snake_case e.g. "file_explorer"
    name: str
    version: str = "1.0.0"

    @abstractmethod
    def activate(self, context: PluginContext) -> None:
        """Wire up services and events. Called once on load."""

    def deactivate(self) -> None:
        """Clean up subscriptions. Called on shutdown or disable."""

    def get_activity_bar_item(self) -> ActivityBarItem | None:
        """Return metadata for activity bar icon. None = no icon."""
        return None

    def get_panel_widget(self) -> Gtk.Widget | None:
        """Widget shown in the side panel when this plugin is active."""
        return None

    def get_keybindings(self) -> list[KeyBinding]:
        return []

    def get_menu_items(self) -> list[MenuItem]:
        return []
```

#### PluginManager

`PluginManager` lives in the service layer — it has no GTK imports. It manages lifecycle only.

```python
# services/plugin_manager.py
class PluginManager:
    def __init__(self, context: PluginContext): ...
    def register(self, plugin: AbstractPlugin) -> None: ...
    def activate_all(self) -> None: ...
    def deactivate_all(self) -> None: ...
    def get_plugin(self, plugin_id: str) -> AbstractPlugin | None: ...
    def get_activity_bar_items(self) -> list[ActivityBarItem]:
        """Returns sorted items from all registered plugins."""
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
- Plugins never import from `slate/ui/`. They return `Gtk.Widget` instances; the shell places them.

---

### 3.3 SOLID Principles

#### S — Single Responsibility

| Class | Single Responsibility |
|---|---|
| `FileService` | Read/write files from disk |
| `GitService` | All git operations |
| `SearchService` | In-project text search |
| `ConfigService` | Read/write config.ini |
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

#### L — Liskov Substitution
- All `AbstractPlugin` implementations are valid substitutes: the shell calls `get_panel_widget()` without knowing the concrete type.
- All `AbstractFileBackend` implementations raise the same typed exceptions.

#### I — Interface Segregation
- `AbstractPlugin` methods (`get_panel_widget`, `get_keybindings`, `get_menu_items`) default to no-ops. A plugin contributing only a menu item does not implement panel methods.
- `AbstractFileBackend` is split into `ReadableBackend` and `WritableBackend`. Read-only backends implement only `ReadableBackend`.

#### D — Dependency Inversion
- `ActivityBar` depends on `list[ActivityBarItem]` (core dataclass), not on any plugin.
- `SourceControlPlugin` depends on `AbstractVCSBackend`, injected via `context.get_service()`.
- `SlateWindow` depends on `PluginManager` and `TabManager`, both injected. It never instantiates plugins or services.

---

### 3.4 Design Patterns

#### Event Bus (Observer) — decoupled cross-plugin communication

The typed `EventBus` is the **only** sideways communication channel. No module holds a direct reference to another module's objects.

```python
# core/events.py
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
    query: str
    results: list["SearchResult"]

@dataclass
class ThemeChangedEvent:
    is_dark: bool
```

`FileService` emits `FileSavedEvent` after saving. `SourceControlPlugin` subscribes and refreshes. `FileService` knows nothing about git.

#### Command Pattern — actions & undo/redo

Every mutating user action is a `Command` object with `execute()` and optionally `undo()`.

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

`Ctrl+Z` / `Ctrl+Y` pop a `CommandHistory` stack. Adding a new action = new `Command` subclass only.

#### Factory Pattern — editor tab construction

`EditorViewFactory` centralises all GtkSourceView configuration:

```python
# ui/editor/editor_factory.py
class EditorViewFactory:
    def __init__(self, config_service, language_detector): ...
    def create(self, path: str | None) -> EditorView:
        # Applies: font, tab width, line numbers, highlight line, colour scheme, language
        # Returns fully configured, ready-to-insert widget
```

Preference changes call `EditorView.apply_config()` on all open views — one place to update.

#### Strategy Pattern — search and language backends

- `AbstractSearchBackend.search(query, folder) -> list[SearchResult]`  
  Default: `NativeSearchBackend` using `os.walk` + `mmap`. Future: ripgrep subprocess.
- `AbstractLanguageDetector.detect(path) -> GtkSource.Language | None`  
  Default: `GtkSource.LanguageManager`. Future: tree-sitter.

Swap either = new class only. Zero changes to callers.

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
│   ├── plugin_api.py                    ← AbstractPlugin, PluginContext, ActivityBarItem, KeyBinding
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
│   ├── config_service.py                ← reads/writes config.ini
│   ├── local_file_backend.py            ← ReadableBackend + WritableBackend impl
│   ├── native_search_backend.py         ← os.walk + mmap (Strategy impl)
│   └── language_detector.py             ← GtkSource.LanguageManager (Strategy impl)
│
├── ui/                                  ← GTK widgets; depends on services + core only
│   ├── app.py                           ← Adw.Application; composition root; all DI wiring
│   ├── window.py                        ← SlateWindow; layout skeleton only
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

        # Plugin context (service registry + bus + config)
        service_registry = {
            "file": file_svc, "git": git_svc,
            "search": search_svc, "config": config,
        }
        plugin_ctx = PluginContext(service_registry, event_bus, config)

        # Plugin manager
        plugin_mgr = PluginManager(plugin_ctx)
        plugin_mgr.register(FileExplorerPlugin())
        plugin_mgr.register(SearchPlugin())
        plugin_mgr.register(SourceControlPlugin())
        plugin_mgr.register(PreferencesPlugin())
        plugin_mgr.activate_all()

        # UI
        factory  = EditorViewFactory(config, lang_det)
        tab_mgr  = TabManager(factory, file_svc, event_bus)

        window = SlateWindow(
            application=self,
            plugin_manager=plugin_mgr,
            tab_manager=tab_mgr,
            config=config,
            event_bus=event_bus,
        )
        window.present()
```

---

### 3.7 Error Handling Strategy

- Services raise typed exceptions from `core/exceptions.py`:
  `SlateFileNotFoundError`, `SlatePermissionError`, `GitNotARepoError`, `GitOperationError`, `GitDirtyWorkingTreeError`, `SearchBackendError`
- UI layer catches at the boundary → `Adw.AlertDialog`. Services never show UI.
- Plugins show their own errors inline (e.g. "Not a git repository" label in Source Control panel).
- Plugin `activate()` calls are wrapped in try/except — a failing plugin is skipped with a stderr log; the app continues.

---

### 3.8 Testability

The core and service layers have zero GTK imports. All business logic is testable with plain `pytest`:

```python
def test_stage_file():
    mock_repo = MockVCSBackend()
    svc = GitService(mock_repo, EventBus())
    svc.stage("src/main.py")
    assert "src/main.py" in mock_repo.staged_files

def test_plugin_registers_activity_bar_item():
    ctx = MockPluginContext()
    pm = PluginManager(ctx)
    pm.register(FileExplorerPlugin())
    pm.activate_all()
    assert any(i.plugin_id == "file_explorer" for i in pm.get_activity_bar_items())
```

No GTK initialisation required for any service, core, or plugin-logic test.

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
- Emits `ActivePanelChangedEvent` on the event bus when the user switches panels

### 6.3 Side Panel (`ui/side_panel.py`)

- `Gtk.Stack` that swaps in plugin `get_panel_widget()` returns
- Width: 220px default; resizable via `Gtk.Paned`; minimum 150px
- Panel header bar: plugin name label + optional action buttons (plugin-provided)
- Collapsible: clicking the active activity bar button again hides the panel (`Ctrl+B` toggles)
- Persists width and last active `plugin_id` across sessions

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
- Clicking a result: opens file, scrolls to line, highlights match
- Search runs on `Enter` (not live) to avoid disk hammering

#### Find & Replace
- Toggle in panel header switches to replace mode
- Replace `Gtk.Entry` appears below search
- Replace · Replace All (with confirmation)

#### Backend
- `SearchService` → `NativeSearchBackend` (Python `os.walk` + `mmap`)
- Runs on a `GLib.ThreadPool` thread — UI stays responsive
- Emits `SearchResultsReadyEvent`; panel subscribes and renders

**Keybindings contributed:**  
`Ctrl+Shift+F` → focus search panel  
`Ctrl+H` → focus search panel in replace mode

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
- Clicking a changed file opens a **read-only diff tab** in the editor: `~ filename (diff)`
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

**Keybinding contributed:** `Ctrl+Shift+G` → focus source control panel

---

### 7.4 Preferences Plugin (`preferences`)

**Activity bar:** none — opens dialog  
Triggered by header bar ⚙ or `Ctrl+,`

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
| Source View Scheme | `Adw.ComboRow` (lists installed GtkSourceView schemes) |

All changes apply live (no Apply button). Saves to config immediately.  
Color mode change emits `ThemeChangedEvent` so all open `EditorView` instances update their scheme.

---

## 8. Editor — Core Behaviour

### 8.1 Tab Management
- `GtkNotebook`: scrollable, reorderable tabs
- Middle-click or × to close; dirty guard: `Adw.AlertDialog` (Save / Discard / Cancel)
- File changed on disk: `Gio.FileMonitor` triggers "Reload?" dialog on focus-in
- `Ctrl+B` collapses/restores side panel

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

All shortcuts registered as `Gio.SimpleAction` in `ui/actions.py`. Plugins add their own via `PluginContext.register_action()`.

---

## 9. Theme & Appearance

- `Adw.Application` inherits system GTK4/Adwaita theme automatically — zero custom CSS on the chrome
- Dark mode toggle cycles: System → Light → Dark → System via `Adw.StyleManager.set_color_scheme()`
- Emits `ThemeChangedEvent(is_dark)` → all `EditorView` instances switch GtkSourceView scheme
- Default schemes: `"Adwaita"` (light) / `"Adwaita-dark"` (dark); user can override in Preferences

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
color_scheme = Adwaita

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

---

## 11. Opening Behaviour

```
python main.py                    → blank window; restore last_folder if set
python main.py /path/to/folder    → load folder; file explorer panel opens
python main.py /path/to/file.py   → open file in editor; no folder loaded
```

On startup with restored folder: side panel opens to File Explorer. Tabs are not auto-restored in v1.

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

- `lsp_client` plugin — LSP / code completion / diagnostics
- `terminal` plugin — integrated terminal panel
- Git log / blame viewer — extension of `source_control` plugin
- Minimap
- Split editor panes
- Multiple workspace roots
- Remote/SSH backend — new `AbstractFileBackend` implementation
- Third-party plugin loading from `~/.config/slate/plugins/`
- `outline` plugin — symbol tree from GtkSourceView buffer
