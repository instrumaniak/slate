# T002: Centralize GTK Dependency Checks

## Goal

Verify all GTK4/GtkSource5/GDK/Pango/cairo dependencies exactly once at startup
(fail-fast with an actionable message), then remove the duplicated per-file
fallback scaffolding so `slate.ui` modules import GTK unconditionally. Reduce
`# type: ignore` count from 27 to ~0-4, all with specific error codes and a
comment. Fix a real runtime bug (EditorView.can_undo/can_redo calling
non-existent GtkSource methods) and delete dead code (actions.py
`register_window_shortcuts`, zero callers).

## Depends On

- T001 complete (mypy slate/ = 0, tests passing)
- `pygobject-stubs==2.17.0` (latest on PyPI; gaps are not fixable via stub upgrade)

## Phase:

0

## Critical:

True

## Spec References

- mypy: `pyproject.toml` `[tool.mypy]` strict=true
- Layer rules: AGENTS.md (core -> services -> ui -> plugins)
- Stub gaps: `/home/raziur/.local/lib/python3.10/site-packages/gi-stubs/Gtk.pyi`
  (line 8884 `load_from_data` untyped `# FIXME`; `Gtk.Dialog.run` removed in GTK4
  stubs; GBoxed ctors `Pango.Layout`/`Gdk.Rectangle` untyped)

## Files to Create/Modify

### Create
- `slate/services/environment_check.py` — `check_environment() -> None`
- `tests/services/test_environment_check.py`

### Modify
- `slate/main.py`, `slate/__main__.py` — call check_environment() before app import
- `slate/ui/app.py` — remove lines 12-23 incomplete guard + `GTK_AVAILABLE`
- `slate/ui/editor/tab_bar.py`, `editor_view.py`, `editor_factory.py`,
  `diff_navigator.py`, `diff_view.py`, `slate/ui/dialogs/save_discard_dialog.py`
  — remove try/except fallback + `GTK_AVAILABLE` guards + conditional base classes
- `slate/ui/actions.py` — delete dead `register_window_shortcuts`
- `slate/ui/panels/source_control_panel.py` — `Gtk.Dialog.run` via Protocol cast
- `slate/ui/editor/editor_view.py` — fix can_undo/can_redo; cast get_text/get_id/get_modified
- `slate/ui/editor/diff_navigator.py` — retype signal param to `Gtk.SingleSelection`
- `tests/test_main.py` (GTK4 availability test), `tests/ui/editor/test_diff_view.py` (`_gtk_available` line)

## Implementation Steps

### Step 1: environment_check.py
`check_environment() -> None`: inside function, `import gi`;
`gi.require_version("Gtk","4.0")`; `gi.require_version("GtkSource","5")`;
`from gi.repository import Gio, Gdk, Pango, PangoCairo, GLib, GObject`;
`import cairo`; `Gdk.Display.get_default() is not None`. On failure print which
lib is missing (python3-gi, gir1.2-gtk-4.0, gir1.2-gtksource-5, python3-gi-cairo)
and `sys.exit(1)`. No module-level GTK imports (keeps services layer GTK-free).

### Step 2: Wire entry points
- `slate/main.py`: move `from slate.ui.app import main as app_main` into `main()`
  (lazy), call `check_environment()` first.
- `slate/__main__.py`: call `check_environment()` at top of `main()`.

### Step 3: app.py
Delete lines 12-23 guard + `GTK_AVAILABLE`; keep unconditional
`gi.require_version("Gtk","4.0"); gi.require_version("GtkSource","5");
from gi.repository import Gio, Gtk`.

### Step 4: Remove scaffolding in 6 ui files
Delete try/except fallback blocks (removes 8 `[assignment]` ignores), conditional
base classes -> plain `class X(Gtk.Box)` (removes 4 `[misc]` ignores), all
`GTK_AVAILABLE`/`_gtk_available` guards (~30 sites) and `_gtk_available` class
attrs. Keep the real code paths. `diff_view.py` `import cairo` unconditional.

### Step 5: Stub-gap fixes
- editor_view.py: `can_undo()`/`can_redo()` -> `get_can_undo()`/`get_can_redo()`
  (runtime bug; removes 2 `[no-any-return]`).
- `cast(str, ...)` on `get_text`, `lang.get_id()`; `cast(bool, ...)` on `get_modified`.
- actions.py: delete `register_window_shortcuts` (removes 3 `[attr-defined]`).
- diff_navigator.py: `_on_selection_changed(selection: object)` ->
  `Gtk.SingleSelection` (removes 1 `[attr-defined]`).
- source_control_panel.py: Protocol cast for `dialog.run() -> int`.
- tab_bar.py:92 + editor_view.py:74 `load_from_data`: one typed helper, or precise
  `# type: ignore[no-untyped-call]` with comment (stub Gtk.pyi:8884 FIXME).
- diff_view.py:188 `Pango.Layout(pctx)` / file_explorer_tree.py:275
  `Gdk.Rectangle()`: try clean cast/helper; else precise coded ignore with comment.

### Step 6: Tests
- tests/test_main.py: replace `app_module.GTK_AVAILABLE is True` with
  `check_environment()` returns None.
- tests/ui/editor/test_diff_view.py: drop `view._gtk_available = True`.
- Add tests/services/test_environment_check.py (mock gi imports; pass + failure paths).

### Step 7: Verification
- `python3 -m mypy slate/` -> 0 errors
- `ruff check slate/ tests/` -> no NEW violations (33 pre-existing baseline untouched)
- `ruff format --check` on changed files
- `pytest tests/core/ tests/services/ tests/plugins/ tests/ui/editor/` pass

## Constraints

- `# type: ignore` must be minimal (~0-4 remaining), always with specific codes + comment
- Do NOT change runtime behavior beyond removing now-guaranteed-false guards
- core/ layer stays GTK-free; services use lazy imports only
- Do NOT shadow pygobject-stubs with a local `stubs/` copy (would replace all typing)

## Acceptance Criteria

- [ ] `# type: ignore` count 27 -> ~0-4, all coded + commented
- [ ] single startup dependency check; all duplicated scaffolding removed
- [ ] mypy strict clean; no new ruff violations; tests pass
- [ ] EditorView.can_undo/can_redo no longer raise AttributeError

## Notes

### Post-implementation code review remarks (2026-08-02)

A code review of the T001+T002 working tree surfaced 4 issues beyond the main
task scope. All are resolved:

1. **`Gtk.Dialog.run()` cast is type-only, not a runtime fix** — Step 5's
   `_DialogRunProtocol` cast only satisfies mypy; on GTK 4.x `Gtk.Dialog.run`
   does not exist at runtime (`AttributeError`). `_show_dirty_warning_dialog()`
   in `source_control_panel.py` was rewritten to the `present()` + "response"
   signal + nested `GLib.MainLoop` pattern already used by
   `save_discard_dialog.run()`, and the `_DialogRunProtocol` class was deleted.
   Added unit tests for the CANCEL/OK response mapping and the dirty-tree
   branch-switch flow (blocked on cancel, proceeds on confirm).
2. **`slate --version` regressed to require GTK + a display** — Step 2 wired
   `check_environment()` before argument parsing, so `--version` exited 1
   headless. `__main__.py` now calls `check_environment()` *after*
   `parse_args()` (argparse `action="version"` exits 0 first), and
   `slate/main.py` (the `slate = "slate.main:main"` console-script entry)
   short-circuits `-v`/`--version` before the check. Verified exit 0 headless
   on both entry points.
3. **CLI unit tests now require a live display** — the Step 6 CLI tests call
   `main.main()`, which runs `check_environment()` → `Gtk.init_check()` and
   would `sys.exit(1)` headless. The 4 `TestCLIArgumentParsing` tests now patch
   `slate.services.environment_check.check_environment`;
   `TestGTK4AvailabilityCheck.test_gtk4_available_is_true` is marked
   `@pytest.mark.gtk` so headless runs exclude it (its logic is already covered
   by the mocked `tests/services/test_environment_check.py`).
4. **Two `# type: ignore`s lacked the mandated comment** — the constraint
   requires "specific codes + comment". Explanatory comments added at
   `editor_view.py:45` (`load_from_data` untyped, Gtk.pyi:8884 FIXME) and
   `file_explorer_tree.py:275` (`Gdk.Rectangle` GBoxed ctor untyped).
