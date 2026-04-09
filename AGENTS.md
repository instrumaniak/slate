# Slate - GTK4 Code Editor

Context7 MCP enabled for library docs (see global `~/.config/opencode/AGENTS.md`)

## Agent Workflow

### Task Management
- Break complex tasks into smaller steps and track with `todowrite`
- Create todo items with `status: in_progress`, `pending`, or `completed`
- Keep one todo `in_progress` at a time — complete before starting new

### Research & Verification
- Use `websearch` or `codesearch` when uncertain about libraries, APIs, or patterns
- Verify findings by checking existing code in `slate/`, `tests/`, or `pyproject.toml`
- Check system dependencies: `dpkg -l | grep -E "python3-gi|gtk|gtksource"` before assuming packages missing
- Cross-reference with Context7 MCP for framework-specific questions

### Subagent Delegation
- Use `task` tool for parallel work on independent files/components
- Never delegate overlapping file changes to multiple subagents simultaneously
- Before delegating: verify which files the subagent will modify to avoid conflicts
- Combine related file changes in single agent to maintain context

### Quality & Performance
- Run `ruff check` + `ruff format` after every code change
- Run `mypy slate/` before considering work complete
- Test at least one logical path end-to-end (not just unit tests)
- For multi-file changes: verify lint/typecheck pass before moving on

## Commands

```bash
# Development setup
pip install -e ".[dev]"

# Lint & format
ruff check slate/ tests/
ruff format .

# Type check
mypy slate/

# Test (requires GUI display or xvfb)
pytest tests/ --cov=slate --cov-report=term-missing --cov-fail-under=85

# Run app
slate                    # open empty editor
slate /path/to/file      # open file on startup
```

## Architecture

```
slate/
├── core/       # Dataclasses, EventBus, plugin API (ZERO GTK imports)
├── services/   # FileService, GitService, ConfigService (lazy GTK imports)
├── ui/         # GTK4 widgets, main window, editor (direct GTK)
└── plugins/    # File explorer, source control (depends only on core)
```

**Layer rules**: `core` → `services` → `ui` → `plugins`. Lower layers never import from higher.

## Critical Anti-Patterns

- ❌ Never `from gi.repository import Gtk` at module level in `core/` or `services/`
- ❌ Never call `gitpython` or `open()` from UI layer — use services
- ❌ Never emit `FileOpenedEvent` directly — only `TabManager` does this
- ❌ Never show windows or mutate tabs in plugin `activate()`
- ❌ Never use GTK signals for cross-component communication — use `EventBus`
- ❌ Never configure `GtkSource.View` directly — use `EditorViewFactory`

## Testing

- `core/` and `services/`: 90%+ coverage required
- `ui/`: smoke/integration tests only (no widget coverage chase)
- Use `temp_dir`, `temp_git_repo` fixtures over excessive mocking
- GTK tests need `pytest-xvfb` or display server

## System Dependencies

```bash
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-gtksource-5 git ripgrep
```

## Key Files

- Entry: `slate/main.py` → `slate/ui/app.py`
- Config: `~/.config/slate/config.ini`
- Tests mirror source: `tests/core/`, `tests/services/`, `tests/ui/`, `tests/plugins/`

## Reference

Comprehensive rules: `_bmad-output/project-context.md`