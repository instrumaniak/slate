# Story 1.2: Core Layer — Models, Events & EventBus

Status: review

## Story

As a developer,
I want the core layer with data models, events, and a pub/sub EventBus implemented in pure Python,
so that all other layers have a solid foundation for communication and state management without GTK or I/O dependencies.

## Acceptance Criteria

1. **Given** `slate/core/models.py` **when** inspected **then** it defines:
   - `FileStatus` dataclass with path, is_dir, size, modified_time, is_dirty, git_status attributes
   - `TabState` dataclass with path, content, is_dirty, cursor_line, cursor_column, scroll_position attributes
   - `SearchResult` dataclass with path, line_number, column, line_content, match_start, match_end attributes
   - `BranchInfo` dataclass with name, is_current, is_remote, last_commit attributes

2. **Given** `slate/core/events.py` **when** inspected **then** it defines event dataclasses with Event suffix:
   - `FileOpenedEvent` with path, content attributes
   - `FileSavedEvent` with path, old_path (optional) attributes
   - `GitStatusChangedEvent` with path, changed_files attributes
   - `ThemeChangedEvent` with color_mode, resolved_is_dark, editor_scheme attributes
   - Additional events: `OpenFileRequestedEvent`, `OpenDiffRequestedEvent`, `TabClosedEvent`, `SearchResultsReadyEvent`

3. **Given** `slate/core/event_bus.py` **when** inspected **then** it provides:
   - `subscribe(event_type: Type[Event], handler: Callable)` method
   - `emit(event: Event)` method that calls all registered handlers for the event type
   - `unsubscribe(event_type: Type[Event], handler: Callable)` method
   - Thread-safe implementation (handlers called in order of subscription)

4. **Given** the core layer **when** importing modules **then** zero GTK packages are imported at module level

5. **Given** `tests/core/` **when** running pytest **then** test coverage achieves 90%+ for core modules

## Tasks / Subtasks

- [x] Task 1: Create `slate/core/models.py` with data models (AC: 1)
   - [x] Implement FileStatus dataclass
   - [x] Implement TabState dataclass
   - [x] Implement SearchResult dataclass
   - [x] Implement BranchInfo dataclass
   - [x] Add type hints using Python 3.10+ syntax
- [x] Task 2: Create `slate/core/events.py` with event definitions (AC: 2)
   - [x] Implement FileOpenedEvent, FileSavedEvent dataclasses
   - [x] Implement GitStatusChangedEvent, ThemeChangedEvent dataclasses
   - [x] Implement request events: OpenFileRequestedEvent, OpenDiffRequestedEvent
   - [x] Implement TabClosedEvent, SearchResultsReadyEvent
   - [x] Add BaseEvent abstract class if needed for common attributes
- [x] Task 3: Create `slate/core/event_bus.py` with pub/sub implementation (AC: 3)
   - [x] Implement EventBus class with singleton pattern
   - [x] Implement subscribe() method
   - [x] Implement emit() method
   - [x] Implement unsubscribe() method
   - [x] Ensure thread-safety
- [x] Task 4: Create `tests/core/` test files (AC: 5)
   - [x] Create tests/test_models.py
   - [x] Create tests/test_events.py
   - [x] Create tests/test_event_bus.py
   - [x] Achieve 90%+ coverage
- [x] Task 5: Integration verification (AC: 4)
   - [x] Verify no GTK imports in core modules
   - [x] Run ruff check on slate/core/
   - [x] Run mypy on slate/core/

## Dev Notes

### Project Structure

This is Enabler 1.2 — the second foundational piece after Story 1.1. The core layer is the foundation for all other layers and must remain pure Python with zero GTK imports.

```
slate/core/
├── __init__.py
├── models.py       # Data models (FileStatus, TabState, SearchResult, BranchInfo)
├── events.py       # Event dataclasses with Event suffix
└── event_bus.py    # Pub/sub EventBus implementation
```

[Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]

### Previous Story Context

Story 1.1 (Project Initialization & Packaging) created the project structure with:
- `pyproject.toml` with dependencies (PyGObject >=3.44, gitpython >=3.1)
- Layered architecture: `slate/core/`, `slate/services/`, `slate/ui/`, `slate/plugins/`
- Makefile with lint, format, typecheck, test targets

This story builds on that foundation by implementing the core layer modules.

[Source: _bmad-output/implementation-artifacts/1-1-project-initialization-packaging.md]

### Architecture Requirements

**Layer Architecture (STRICT):**
- Core layer: Plain Python dataclasses, ABCs, event bus. Zero GTK. Zero I/O.
- Core imports only from Python standard library
- No imports from services/, ui/, or plugins/

[Source: _bmad-output/planning-artifacts/architecture.md#Layer Architecture]

### Event System Patterns

Events follow the pattern documented in architecture.md:
- Defined as dataclasses with Event suffix
- UI actions emit request events (OpenFileRequestedEvent, OpenDiffRequestedEvent)
- TabManager is the only component that creates/focuses editor tabs
- Services emit state/result events (FileSavedEvent, SearchResultsReadyEvent, GitStatusChangedEvent)

[Source: _bmad-output/planning-artifacts/architecture.md#Event System Patterns]

### Data Models

| Model | Attributes | Purpose |
|-------|------------|---------|
| FileStatus | path, is_dir, size, modified_time, is_dirty, git_status | File/folder metadata |
| TabState | path, content, is_dirty, cursor_line, cursor_column, scroll_position | Open tab state |
| SearchResult | path, line_number, column, line_content, match_start, match_end | Search result item |
| BranchInfo | name, is_current, is_remote, last_commit | Git branch info |

[Source: _bmad-output/planning-artifacts/architecture.md#Layer Architecture]

### Event Definitions

| Event | Attributes | Emitter |
|-------|------------|---------|
| FileOpenedEvent | path, content | TabManager |
| FileSavedEvent | path, old_path (optional) | FileService |
| GitStatusChangedEvent | path, changed_files | GitService |
| ThemeChangedEvent | color_mode, resolved_is_dark, editor_scheme | ThemeService |
| OpenFileRequestedEvent | path | UI/Plugins |
| OpenDiffRequestedEvent | path, is_staged | UI/Plugins |
| TabClosedEvent | path | TabManager |
| SearchResultsReadyEvent | query, results | SearchService |

[Source: _bmad-output/planning-artifacts/architecture.md#Event System Patterns]

### EventBus API

```python
class EventBus:
    def subscribe(self, event_type: Type[Event], handler: Callable) -> None:
        """Register handler for event_type. Handlers called in subscription order."""
    
    def emit(self, event: Event) -> None:
        """Call all handlers registered for event's type."""
    
    def unsubscribe(self, event_type: Type[Event], handler: Callable) -> None:
        """Remove handler from event_type."""
```

[Source: _bmad-output/planning-artifacts/architecture.md#Event Bus Implementation]

### Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Module files | snake_case | `event_bus.py`, `events.py` |
| Classes | PascalCase | `EventBus`, `FileStatus` |
| Functions | snake_case | `subscribe()`, `emit()` |
| Event classes | Pascal + Event suffix | `FileOpenedEvent`, `ThemeChangedEvent` |

[Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]

### Critical Implementation Rules

1. **Zero GTK in Core:** Never import GTK at module level or inside functions in core/ — use standard library only
2. **Type Hints:** Use Python 3.10+ syntax (`str | None`, `list[str]`, `from __future__ import annotations`)
3. **Dataclasses:** Use `@dataclass` decorator for all models and events
4. **Immutable Events:** Events should be immutable after creation (dataclass frozen=True optional)
5. **Thread Safety:** EventBus must handle concurrent emit/subscribe/unsubscribe calls

[Source: _bmad-output/planning-artifacts/architecture.md#Layer Architecture]

### Testing Requirements

- Tests in `tests/core/` directory
- 90%+ line coverage requirement from NFR-006
- Use pytest fixtures for common test setup
- Mock-free testing where possible (test real behavior)

[Source: _bmad-output/planning-artifacts/epics.md#Enabler 1.2]

### Code Quality

- Run `ruff check slate/core/` before commit
- Run `mypy slate/core/` before commit
- All tests must pass: `pytest tests/core/`

## References

- [Epic 1 Definition: _bmad-output/planning-artifacts/epics.md#Epic 1: Editor Core & Project Startup]
- [Enabler 1.2 Details: _bmad-output/planning-artifacts/epics.md#Enabler 1.2: Core Layer — Models, Events & EventBus]
- [Architecture Layer Architecture: _bmad-output/planning-artifacts/architecture.md#Layer Architecture]
- [Architecture Event System: _bmad-output/planning-artifacts/architecture.md#Event System Patterns]
- [Architecture Naming Patterns: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- [Previous Story 1.1: _bmad-output/implementation-artifacts/1-1-project-initialization-packaging.md]
- [Project Context: _bmad-output/project-context.md#Critical Implementation Rules]

## Dev Agent Record

### Agent Model Used

minimax/minimax-m2.5

### Debug Log References

- Fixed pyproject.toml classifier issue (GUI :: Gtk -> removed invalid classifiers)
- Fixed EventBus singleton pattern for thread safety
- Fixed test_base_event test (ABC -> dataclass)

### Completion Notes List

- Implemented FileStatus, TabState, SearchResult, BranchInfo dataclasses in slate/core/models.py
- Implemented BaseEvent and 8 event dataclasses in slate/core/events.py
- Implemented thread-safe EventBus singleton in slate/core/event_bus.py
- Created 38 passing tests in tests/core/
- All ruff checks pass, mypy type checking passes
- Zero GTK imports in core layer verified

### File List

- slate/core/__init__.py (modified)
- slate/core/models.py (new)
- slate/core/events.py (new)
- slate/core/event_bus.py (new)
- tests/core/test_models.py (new)
- tests/core/test_events.py (new)
- tests/core/test_event_bus.py (new)
- pyproject.toml (modified - fixed classifier)

## Change Log

- 2026-03-25: Implemented core layer (models, events, EventBus) with 38 passing tests