# Story 1.1: Project Initialization & Packaging

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want a properly structured Python project with modern packaging,
so that all subsequent features have a solid foundation with correct dependencies and tooling.

## Acceptance Criteria

1. **Given** the repository root **when** I inspect the directory structure **then** it contains:
   - `pyproject.toml` at root
   - `slate/` package directory
   - `tests/` directory
   - `scripts/` directory
   - `docs/` directory
   - `data/schemes/` directory
2. **Given** `pyproject.toml` **when** inspected **then** it declares:
   - `Python >=3.10`
   - `PyGObject >=3.44`
   - `gitpython >=3.1`
   - `pytest`, `pytest-cov`, `ruff`, `mypy` as dev dependencies
3. **Given** the package structure **when** inspected **then** it follows layered architecture:
   - `slate/core/` — pure Python, zero GTK
   - `slate/services/` — business logic, zero GTK at module level
   - `slate/ui/` — GTK widgets
   - `slate/plugins/` — plugin packages
4. **Given** I run `python -m slate` **then** it runs without import errors (prints version or placeholder)
5. **Given** `pyproject.toml` **when** inspected **then** it includes CLI entry point configuration for `slate` command

## Tasks / Subtasks

- [x] Task 1: Create project directory structure (AC: 1, 3)
   - [x] Create `slate/` package with `__init__.py`
   - [x] Create `slate/core/` with `__init__.py`
   - [x] Create `slate/services/` with `__init__.py`
   - [x] Create `slate/ui/` with `__init__.py`
   - [x] Create `slate/plugins/` with `__init__.py`
   - [x] Create `slate/plugins/core/` with `__init__.py`
   - [x] Create `tests/` directory with `__init__.py`
   - [x] Create `scripts/` directory
   - [x] Create `docs/` directory
   - [x] Create `data/schemes/` directory
- [x] Task 2: Create `pyproject.toml` with dependencies (AC: 2, 5)
   - [x] Define project metadata (name, version, description)
   - [x] Set `python_requires >=3.10`
   - [x] Add runtime dependencies: `PyGObject>=3.44`, `gitpython>=3.1`
   - [x] Add dev dependencies: `pytest>=7.0`, `pytest-cov>=4.0`, `ruff`, `mypy`
   - [x] Configure `[project.scripts]` entry point: `slate = slate.main:main`
   - [x] Configure build system (hatchling or setuptools)
- [x] Task 3: Create `slate/version.py` module (AC: 4)
   - [x] Define `__version__ = "0.1.0"`
   - [x] Make importable from `slate/__init__.py`
- [x] Task 4: Create `slate/__main__.py` entry point (AC: 4)
   - [x] Implement `if __name__ == "__main__"` block
   - [x] Call `slate.main:main()`
- [x] Task 5: Create `slate/main.py` placeholder (AC: 4)
   - [x] Define `main()` function
   - [x] Print version on invocation
   - [x] Perform Python 3.10+ version check with clear error message
- [x] Task 6: Create `.gitignore` for Python project
   - [x] Exclude `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `*.egg-info/`
   - [x] Exclude `.venv/`, `venv/`, `*.pyc`
- [x] Task 7: Create `Makefile` with dev shortcuts (AC: implicit from architecture)
   - [x] `lint` target: `ruff check slate/`
   - [x] `format` target: `ruff format slate/`
   - [x] `typecheck` target: `mypy slate/`
   - [x] `test` target: `pytest tests/ --cov=slate`
- [x] Task 8: Create `scripts/install-deps.sh` for system packages
   - [x] Document apt dependencies: `python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1 git ripgrep`

## Dev Notes

### Project Structure

The project follows a strict layered architecture [Source: _bmad-output/planning-artifacts/architecture.md]:

```
slate/                          # Python package root
├── pyproject.toml              # Modern Python packaging
├── .gitignore
├── Makefile                    # Development shortcuts
├── slate/                      # Main package
│   ├── __init__.py
│   ├── __main__.py            # CLI entry: python -m slate
│   ├── main.py                # Application entry point
│   ├── version.py             # Version info
│   │
│   ├── core/                  # Layer 1: Pure Python, zero GTK
│   │   ├── __init__.py
│   │
│   ├── services/              # Layer 2: Business logic, zero GTK
│   │   ├── __init__.py
│   │
│   ├── ui/                    # Layer 3: GTK widgets
│   │   ├── __init__.py
│   │
│   └── plugins/               # Layer 4: Plugins
│       ├── __init__.py
│       └── core/
│           └── __init__.py
│
├── tests/
│   └── __init__.py
│
├── scripts/
├── docs/
└── data/
    └── schemes/
```

### Technology Stack

| Layer | Choice | Version |
|---|---|---|
| Language | Python | 3.10+ |
| GUI Toolkit | GTK4 via PyGObject | >= 3.44 |
| Git | gitpython | >= 3.1 |
| Linter | ruff | latest stable |
| Type Checker | mypy | latest stable |
| Test Framework | pytest | >= 7.0 |
| Test Coverage | pytest-cov | >= 4.0 |

[Source: _bmad-output/project-context.md#Technology Stack & Versions]

### Critical Rules

- **Layer Import Rules (STRICT):** `core/` cannot import from `services/`, `ui/`, or `plugins/`. `services/` imports only from `core/`. `ui/` imports from `core/` and `services/`. `plugins/` imports only from `core/`.
- **GTK Imports:** Never import GTK at module level in `core/` or `services/`. Use lazy imports inside methods where needed.
- **Naming:** Module files use `snake_case.py`. Classes use `PascalCase`. Functions use `snake_case()`.
- **Python 3.10+:** Use modern type hints (`str | None`, `list[str]`). Use `from __future__ import annotations` for forward references.

[Source: _bmad-output/project-context.md#Critical Implementation Rules]

### pyproject.toml Dependencies

**Runtime:**
```
PyGObject >= 3.44
gitpython >= 3.1
```

**Dev:**
```
pytest >= 7.0
pytest-cov >= 4.0
ruff
mypy
```

[Source: _bmad-output/planning-artifacts/architecture.md#Dependency Summary]

### System Dependencies (apt)

```
python3 python3-gi python3-gi-cairo
gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1
git ripgrep
```

[Source: _bmad-output/planning-artifacts/prd.md#Linux System Integration Constraints]

### Python Version Check

The `main.py` must include an explicit Python version check that shows a clear error message if Python < 3.10. This is a requirement from the PRD for graceful degradation.

[Source: _bmad-output/planning-artifacts/epics.md#Story 1.8 Acceptance Criteria]

### Project Structure Notes

- This is an **Enabler** story — it supports Story 1.6 (Main Window & Editor View) by providing the project foundation
- No existing project structure detected — this is greenfield implementation
- Manual project initialization (no standard starter template exists for Python GTK4 editor)
- Follow the architecture spec in `docs/slate-spec.md` directly

[Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]

## References

- [Epic 1 Definition: _bmad-output/planning-artifacts/epics.md#Epic 1: Editor Core & Project Startup]
- [Architecture Decisions: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [PRD Requirements: _bmad-output/planning-artifacts/prd.md#Domain-Specific Requirements]
- [Project Context Rules: _bmad-output/project-context.md#Critical Implementation Rules]
- [Layer Architecture: _bmad-output/planning-artifacts/architecture.md#Layer Architecture]

## Dev Agent Record

### Agent Model Used
Amelia (Developer Agent)

### Debug Log References
- Created project directory structure following layered architecture
- All __init__.py files created for proper Python package structure

### Completion Notes List
- ✅ Task 1: Created complete directory structure with all required packages and __init__.py files
- ✅ Task 2: Created pyproject.toml with Python 3.10+, PyGObject, gitpython, dev dependencies, CLI entry point
- ✅ Task 3: Created slate/version.py with __version__ = "0.1.0"
- ✅ Task 4: Created slate/__main__.py for `python -m slate` entry point
- ✅ Task 5: Created slate/main.py with main() function and Python 3.10+ version check
- ✅ Task 6: Verified .gitignore already covers all requirements
- ✅ Task 7: Created Makefile with lint, format, typecheck, test targets
- ✅ Task 8: Created scripts/install-deps.sh with apt dependencies documentation
- All 12 tests pass verifying AC compliance

### File List
- `pyproject.toml` (created)
- `Makefile` (created)
- `.gitignore` (verified - already existed)
- `slate/__init__.py` (created)
- `slate/__main__.py` (created)
- `slate/main.py` (created)
- `slate/version.py` (created)
- `slate/core/__init__.py` (created)
- `slate/services/__init__.py` (created)
- `slate/ui/__init__.py` (created)
- `slate/plugins/__init__.py` (created)
- `slate/plugins/core/__init__.py` (created)
- `tests/__init__.py` (created)
- `tests/test_project_structure.py` (created)
- `tests/test_pyproject_toml.py` (created)
- `scripts/install-deps.sh` (created)
