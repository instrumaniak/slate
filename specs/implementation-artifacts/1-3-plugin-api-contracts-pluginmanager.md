# Story 1.3: Plugin API Contracts & PluginManager

Status: review

## Story

As a developer,
I want a well-defined plugin extension interface with lifecycle management,
so that plugins can register panels, actions, and dialogs without touching core code, and so that Slate can load and manage plugins reliably.

## Acceptance Criteria

1. **Given** `slate/core/plugin_api.py` **when** inspected **then** it defines:
   - `AbstractPlugin` abstract base class with abstract `activate(context)` method
   - `PluginContext` class providing `get_service(service_id)`, `get_config(section, key)`, `set_config(section, key, value)`, and `emit(event)` methods
   - `HostUIBridge` abstract class with `register_panel()`, `register_action()`, `register_dialog()` abstract methods
   - `ActivityBarItem` dataclass with plugin_id, icon_name, title, priority attributes
   - Zero GTK imports at module level

2. **Given** `slate/services/plugin_manager.py` **when** inspected **then** it provides:
   - `PluginManager` class with plugin lifecycle management
   - `load_plugin(plugin_class)` method that instantiates and activates plugins
   - `activate_all()` method that activates all registered plugins in order
   - `deactivate_all()` method that calls deactivate on all active plugins during shutdown
   - `get_plugin(plugin_id)` method returning plugin instance or None
   - `get_activity_bar_items()` returning sorted list of ActivityBarItem from all plugins
   - Graceful error handling: plugin activation failures are caught, logged, and don't crash Slate

3. **Given** a plugin implementation **when** it inherits from `AbstractPlugin` **then** it:
   - Must implement `activate(self, context: PluginContext)` method
   - Can optionally implement `deactivate(self)` method
   - Has access to services via `context.get_service(service_id)`
   - Has access to config via `context.get_config()` and `context.set_config()`
   - Can emit events via `context.emit(event)`
   - Can register UI elements via `context.host_bridge` methods

4. **Given** the plugin system **when** error conditions occur **then**:
   - Syntax errors in plugin files are caught and logged without crashing
   - Import failures are caught and logged with descriptive error messages
   - Runtime exceptions in `activate()` are caught, plugin is skipped, Slate continues
   - Runtime exceptions after activation are caught by host bridge and logged

5. **Given** `tests/core/test_plugin_api.py` and `tests/services/test_plugin_manager.py` **when** running pytest **then** coverage achieves 90%+ for both modules

## Tasks / Subtasks

- [x] Task 1: Create `slate/core/plugin_api.py` with AbstractPlugin, PluginContext, HostUIBridge (AC: 1)
   - [x] Define AbstractPlugin ABC with abstract activate(context) method
   - [x] Define PluginContext dataclass with service registry, config access, event emission
   - [x] Define HostUIBridge ABC with register_panel(), register_action(), register_dialog()
   - [x] Define ActivityBarItem dataclass
   - [x] Add comprehensive type hints
   - [x] Verify zero GTK imports

- [x] Task 2: Create `slate/services/plugin_manager.py` with lifecycle management (AC: 2)
   - [x] Implement PluginManager class
   - [x] Implement plugin registration and storage
   - [x] Implement activate_all() with ordered activation
   - [x] Implement deactivate_all() for graceful shutdown
   - [x] Implement get_plugin() for plugin lookup
   - [x] Implement get_activity_bar_items() for activity bar population
   - [x] Add comprehensive error handling

- [x] Task 3: Create test files for plugin API and manager (AC: 5)
   - [x] Create `tests/core/test_plugin_api.py` with ABC validation tests
   - [x] Create `tests/services/test_plugin_manager.py` with lifecycle tests
   - [x] Create test fixtures for mock plugins
   - [x] Test error handling scenarios
   - [x] Achieve 90%+ coverage

- [x] Task 4: Verify architecture compliance (AC: 1, 3, 4)
   - [x] Confirm zero GTK imports in core/plugin_api.py
   - [x] Run ruff check on new files
   - [x] Run mypy type checking
   - [x] Verify layered architecture compliance

## Dev Notes

### Project Structure

This is Enabler 1.3 — the third foundational piece that enables the plugin system. It builds directly on Enabler 1.2 (Core Layer with EventBus).

```
slate/core/
├── __init__.py
├── models.py
├── events.py
├── event_bus.py
└── plugin_api.py       # NEW: AbstractPlugin, PluginContext, HostUIBridge

slate/services/
├── __init__.py
└── plugin_manager.py   # NEW: Plugin lifecycle management
```

### Previous Story Context

Story 1.2 (Core Layer — Models, Events & EventBus) created:
- `slate/core/models.py` with FileStatus, TabState, SearchResult, BranchInfo
- `slate/core/events.py` with FileOpenedEvent, FileSavedEvent, etc.
- `slate/core/event_bus.py` with subscribe(), emit(), unsubscribe()
- `tests/core/` with 38 passing tests achieving 90%+ coverage

This story builds on that foundation by:
- Using EventBus for plugin communication via `context.emit()`
- Using events for plugin-to-plugin and plugin-to-host communication
- Implementing the plugin API contracts that services and UI will implement

### Architecture Requirements

**Layer Architecture (STRICT):**

```
┌──────────────────────────────────────────────────────────┐
│            Plugin Layer   (slate/plugins/)               │  Core + future plugins
├──────────────────────────────────────────────────────────┤
│              UI Layer     (slate/ui/)                    │  GTK widgets, layout
├──────────────────────────────────────────────────────────┤
│           Service Layer   (slate/services/)              │  PluginManager, services
├──────────────────────────────────────────────────────────┤
│             Core Layer    (slate/core/)                  │  plugin_api.py — pure Python
└──────────────────────────────────────────────────────────┘
```

**Rules:**
- `slate/core/plugin_api.py`: ABCs and dataclasses only. Zero GTK. Zero I/O.
- `slate/services/plugin_manager.py`: Business logic. Imports only from core/. Zero GTK.
- Plugin implementations will be in `slate/plugins/core/` and will use only the public API from `slate/core/plugin_api.py`

**Naming Conventions:**

| Element | Pattern | Example |
|---------|---------|---------|
| Abstract base class | Abstract + PascalCase | `AbstractPlugin`, `HostUIBridge` |
| Context class | PascalCase | `PluginContext` |
| Dataclass | PascalCase | `ActivityBarItem` |
| Methods | snake_case | `activate()`, `get_service()` |
| Plugin IDs | snake_case | `file_explorer`, `source_control` |
| Service IDs | quoted string | `"file"`, `"git"`, `"config"` |

**Plugin ID Registry (from Architecture):**
| Plugin | ID |
|--------|-----|
| File Explorer | `file_explorer` |
| Source Control | `source_control` |
| Search | `search` |
| Preferences | `preferences` |

**Service ID Registry (from Architecture):**
| Service | ID |
|---------|-----|
| FileService | `"file"` |
| GitService | `"git"` |
| SearchService | `"search"` |
| ConfigService | `"config"` |
| ThemeService | `"theme"` |
| TabQueryService | `"tabs"` |

### Plugin API Design

**AbstractPlugin Interface:**

```python
class AbstractPlugin(ABC):
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique plugin identifier (snake_case)."""
        ...
    
    @abstractmethod
    def activate(self, context: PluginContext) -> None:
        """Called when plugin is activated. Register panels/actions here."""
        ...
    
    def deactivate(self) -> None:
        """Called when plugin is deactivated. Cleanup resources here."""
        ...
```

**PluginContext Interface:**

```python
@dataclass(frozen=True)
class PluginContext:
    """Context passed to plugins during activation."""
    plugin_id: str
    
    def get_service(self, service_id: str) -> Any:
        """Get service by ID. Returns service instance or raises KeyError."""
        ...
    
    def get_config(self, section: str, key: str) -> str:
        """Get config value. Returns string value or empty string if not found."""
        ...
    
    def set_config(self, section: str, key: str, value: str) -> None:
        """Set config value. Persists to config file."""
        ...
    
    def emit(self, event: Event) -> None:
        """Emit event to EventBus."""
        ...
    
    @property
    def host_bridge(self) -> HostUIBridge:
        """Access to host UI for registering panels/actions/dialogs."""
        ...
```

**HostUIBridge Interface:**

```python
class HostUIBridge(ABC):
    """Bridge for plugins to register UI elements. Implemented by UI layer."""
    
    @abstractmethod
    def register_panel(
        self, 
        plugin_id: str, 
        panel_id: str, 
        widget: Any,  # GTK widget - lazy import
        title: str,
        icon_name: str
    ) -> None:
        """Register a panel in the side panel area."""
        ...
    
    @abstractmethod
    def register_action(
        self,
        plugin_id: str,
        action_id: str,
        callback: Callable,
        shortcut: str | None = None
    ) -> None:
        """Register an action with optional keyboard shortcut."""
        ...
    
    @abstractmethod
    def register_dialog(
        self,
        plugin_id: str,
        dialog_id: str,
        factory: Callable[..., Any]  # Returns GTK dialog widget
    ) -> None:
        """Register a dialog factory."""
        ...
    
    @abstractmethod
    def show_notification(
        self,
        message: str,
        timeout_ms: int = 3000
    ) -> None:
        """Show toast notification."""
        ...
```

**ActivityBarItem Dataclass:**

```python
@dataclass(frozen=True)
class ActivityBarItem:
    """Item to display in the activity bar."""
    plugin_id: str
    icon_name: str       # XDG symbolic icon name
    title: str
    priority: int = 0    # Lower = earlier in list
```

### PluginManager Implementation

**Plugin Lifecycle:**

```
Plugin Class → Instantiation → activate(context) → Active Plugin → deactivate() → Cleanup
                    ↓
            (on error: log, skip, continue)
```

**PluginManager Responsibilities:**

1. **Registration**: Store plugin classes before activation
2. **Ordered Activation**: Activate plugins in priority order
3. **Error Handling**: Catch and log activation failures without crashing
4. **Lifecycle Management**: Track active plugins, support deactivation
5. **Service Discovery**: Provide `get_activity_bar_items()` for UI layer
6. **Plugin Lookup**: `get_plugin(plugin_id)` returns instance or None

**Error Handling Strategy:**

```python
# In activate_all()
for plugin_class in self._plugin_classes:
    try:
        plugin = plugin_class()
        context = self._create_context(plugin.plugin_id)
        plugin.activate(context)
        self._active_plugins[plugin.plugin_id] = plugin
    except Exception as e:
        logger.error(f"Failed to activate plugin {plugin_class.__name__}: {e}")
        # Continue with next plugin - don't crash Slate
```

### Critical Implementation Rules

1. **Zero GTK in Core**: `slate/core/plugin_api.py` must have zero GTK imports
2. **Zero GTK at Module Level**: `slate/services/plugin_manager.py` should avoid GTK imports at module level
3. **Type Safety**: Use Python 3.10+ type hints (`str | None`, `list[str]`)
4. **Abstract Base Classes**: All interfaces must use `ABC` and `@abstractmethod`
5. **Thread Safety**: PluginManager may be called from multiple threads (use locks if needed)
6. **Graceful Degradation**: One failing plugin must not crash others or Slate
7. **No Direct Plugin References**: Plugins communicate via EventBus, not direct references

### Testing Requirements

**Test Coverage Targets:**
- `slate/core/plugin_api.py`: 90%+ line coverage
- `slate/services/plugin_manager.py`: 90%+ line coverage

**Test Scenarios:**

1. **Plugin API Tests** (`tests/core/test_plugin_api.py`):
   - AbstractPlugin cannot be instantiated directly
   - Concrete plugin must implement activate()
   - PluginContext dataclass creation and immutability
   - HostUIBridge ABC methods are abstract
   - ActivityBarItem dataclass fields

2. **Plugin Manager Tests** (`tests/services/test_plugin_manager.py`):
   - Plugin registration and storage
   - Successful activation with proper context
   - Activation failure handling (syntax error, import error, runtime error)
   - Ordered activation by priority
   - Deactivation calls cleanup
   - get_plugin() returns correct instance
   - get_activity_bar_items() returns sorted items
   - Multiple plugin activation

3. **Mock Implementations for Testing:**

```python
# Test fixtures
class MockPlugin(AbstractPlugin):
    @property
    def plugin_id(self) -> str:
        return "mock_plugin"
    
    def activate(self, context: PluginContext) -> None:
        self.context = context
        self.activated = True

class FailingPlugin(AbstractPlugin):
    @property
    def plugin_id(self) -> str:
        return "failing_plugin"
    
    def activate(self, context: PluginContext) -> None:
        raise RuntimeError("Plugin activation failed")
```

### Integration Points

**Upstream Dependencies:**
- `slate/core/event_bus.py` — PluginContext.emit() uses EventBus
- `slate/core/events.py` — Events emitted by plugins

**Downstream Dependencies:**
- Story 1.4 (Services Layer) — ConfigService, ThemeService will be accessed via PluginContext
- Story 1.6 (Main Window) — HostUIBridge will be implemented by UI layer
- Future plugins — Will inherit from AbstractPlugin

**Communication Patterns:**
- Plugins emit events via `context.emit(event)` → EventBus → Other plugins/Services/UI
- Plugins get services via `context.get_service(service_id)` → Service instances
- Plugins access config via `context.get_config()` / `set_config()` → ConfigService
- UI layer implements HostUIBridge → Plugins register panels/actions/dialogs

### Performance Considerations

- Plugin activation happens once at startup — optimize for clarity over speed
- get_activity_bar_items() may be called frequently — cache results
- Plugin lookup via get_plugin() should be O(1) — use dictionary
- Error handling must not block other plugins

### Future Extensibility

This plugin system design supports:
- Third-party plugins (future `slate/plugins/contrib/`)
- Plugin reloading (deactivate + activate cycle)
- Plugin dependencies (activate in dependency order)
- Plugin settings UI (via PreferencesPlugin)
- Plugin marketplace (external plugin loading)

## References

- [Epic 1 Definition: _bmad-output/planning-artifacts/epics.md#Epic 1: Editor Core & Project Startup]
- [Enabler 1.3 Details: _bmad-output/planning-artifacts/epics.md#Enabler 1.3: Plugin API Contracts & PluginManager]
- [Architecture Layer Architecture: _bmad-output/planning-artifacts/architecture.md#Layer Architecture]
- [Architecture Plugin API Patterns: _bmad-output/planning-artifacts/architecture.md#Plugin API Patterns]
- [Architecture Naming Patterns: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- [Architecture Service IDs: _bmad-output/planning-artifacts/architecture.md#Service IDs]
- [Previous Story 1.2: _bmad-output/implementation-artifacts/1-2-core-layer-models-events-eventbus.md]

## Dev Agent Record

### Agent Model Used

To be filled by dev agent

### Debug Log References

To be filled by dev agent

### Completion Notes List

- [x] AbstractPlugin ABC implemented with abstract plugin_id property and activate() method
- [x] PluginContext dataclass implemented with get_service(), get_config(), set_config(), emit(), host_bridge property
- [x] HostUIBridge ABC implemented with register_panel(), register_action(), register_dialog(), show_notification()
- [x] ActivityBarItem dataclass implemented with plugin_id, icon_name, title, priority (frozen)
- [x] PluginManager lifecycle management implemented with registration, activation, deactivation, lookup, activity bar collection
- [x] Error handling for plugin failures implemented (activation/deactivation failures caught and logged, app continues)
- [x] Test files created with 90%+ coverage (test_plugin_api.py: 19 tests, test_plugin_manager.py: 14 tests)
- [x] All ruff checks pass
- [x] All mypy checks pass
- [x] Zero GTK imports in core/plugin_api.py verified
- [x] Total test suite: 83 tests passing, 90% coverage overall

### File List

- slate/core/plugin_api.py (new)
- slate/services/plugin_manager.py (new)
- tests/core/test_plugin_api.py (new)
- tests/services/test_plugin_manager.py (new)
- pyproject.toml (updated - added ruff per-file-ignores for B027)

## Change Log

- 2026-03-25: Story created - Plugin API Contracts & PluginManager
- 2026-03-25: Story completed - All tasks done, 83 tests passing, 90% coverage
- 2026-03-25: Code review passed - 13 patches identified, fixes implemented
- 2026-03-25: Fix completion - All 89 tests passing, ruff + mypy checks clean
