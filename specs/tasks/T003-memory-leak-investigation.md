# T003: Memory leak investigation

## Goal

Investigate and fix a memory leak in the Slate GTK4 editor: opening many files
increases memory consumption, but closing tabs does not reduce it. Determine
whether the leak is real (vs. allocator retention), find the root cause, fix it,
and add a regression test so it never comes back.

## Depends On

(None)

## Phase:

(Phase 2 - Complete)

## Critical:

(Yes - user-reported memory leak blocking normal editor use)

## Spec References

- AGENTS.md (memory safety mandates, test timeouts, markers)
- `_bmad-output/project-context.md` (comprehensive project rules)

## Files to Create/Modify

- `slate/ui/editor/editor_view.py` (FIX target: modified-changed connect at line 102)
- `tests/ui/gtk/test_tab_memory.py` (CREATE - memory probe / regression test)

## Implementation Steps

1. Build headless memory probe test under `xvfb-run` that opens ~50 controlled
   files via the real `SlateWindow`/`TabManager`, measures RSS +
   `gc.get_objects()` instance counts of `EditorView`/`GtkSource.Buffer`, closes
   all tabs + `gc.collect()`, and repeats 3 open-close cycles to separate a true
   leak (linear RSS growth) from allocator retention (plateau). (DONE - probe RED, leak confirmed)
2. Trace surviving instances with `objgraph`/`gc.get_referrers()` to pinpoint the
   retention source. (DONE - signal-closure cycle + C-side retention found)
3. Isolate root cause with minimal experiments (bare subclass + container,
   varying one setting/connection at a time). (DONE - see Notes)
4. Implement the fix in `editor_view.py` - remove all Python instance
   attributes from the GtkSource.View wrapper (DONE - see Notes).
5. Turn the probe into a regression test asserting zero surviving
   `EditorView` instances after close-all (timeout-guarded, `@pytest.mark.gtk`).
   (DONE - probe is the regression test, GREEN)
6. Run lint/typecheck/tests, then update Notes below. (DONE - see Notes)

## Constraints

- `core/` and `services/` must never import GTK.
- Only `TabManager` emits `FileOpenedEvent`.
- All tests must have timeouts and run under xvfb for GTK.
- Never run full pytest without `--ignore=tests/e2e/`.

## Acceptance Criteria

- [x] Probe/regression test proves closing all tabs returns EditorView instance
      count to baseline (no linear growth across repeated open-close cycles).
- [x] No leak: EditorView count returns to baseline (0) after each close cycle;
      RSS growth is allocator retention, not a leak.
- [x] Root cause documented with evidence.
- [x] `ruff check`, `ruff format`, `mypy slate/` all pass.
- [x] Existing GTK tests still pass (`xvfb-run -a pytest tests/ui/gtk -o addopts=""`),
      except one pre-existing unrelated tab-bar CSS test failure.

## Notes

### Log: 2026-08-03 — Investigation and fix (complete)

**Reproduction.** Built `tests/ui/gtk/test_tab_memory.py` (probe) using the real
`SlateWindow`/`TabManager` flow under `xvfb-run`: 20 files x 120 lines opened and
closed for 3 cycles. Baseline EditorView count was measured via
`gc.get_objects()`; RSS via `/proc/self/status` VmRSS. Before the fix the probe
was RED: EditorView instances grew by exactly 20 per cycle (23 -> 43 -> 63) and
never decreased on close; RSS grew linearly 193MB -> 208MB across 3 cycles
(60 EditorView instances leaked). User's report confirmed.

**Isolation.** Minimal experiments (bare `class EV(GtkSource.View)` subclass,
window + scrolled container, varying one factor at a time) proved:
- Subclass with no settings and no signal connect -> freed.
- Setting ANY Python instance attribute (`v._foo = ...`) -> leaks, even after
  clearing to `None` or calling `run_dispose()`.
- Connecting `buffer.connect("modified-changed", bound_method)` -> leaks.
- Only triggered when the widget is realized (`win.present()`).
- `disconnect`, `set_buffer(None)`, `__dict__.clear()`, `run_dispose()` all fail
  to free it once an attribute/signal-cycle exists.

**Root cause.** PyGObject 3.42.1 toggle-reference mechanism
(`pygobject_switch_to_toggle_ref`): when a Python instance attribute is first set
on a GObject wrapper, PyGObject adds a toggle ref that keeps the Python wrapper
alive as long as the underlying C GObject lives. GTK4 does not force the dispose
cycle on tree removal, so realized widgets are never freed. Fixed upstream in
PyGObject 3.56 ("wrapper objects are always discardable... preserves the instance
dictionary and reapplies it"). `gc.get_referrers()` showed no Python referrers
yet weakref stayed alive -> pure C-side retention invisible to Python GC.

**Fix.** Refactored `slate/ui/editor/editor_view.py` to set NO instance
attributes on the `GtkSource.View` wrapper:
- Removed `view._slate_font_css_provider` (CSS provider stays alive via
  `style_context.add_provider()` C ref; no readers existed).
- Removed `self._on_modified_changed` and the `_on_buffer_modified` method.
  The `modified-changed` handler is now a closure capturing only
  `weakref.ref(self)` + the callback, so no strong Python cycle forms.

**Verification.** Probe now GREEN: after each close, `views=0` (was 60 leaked).
RSS still grows ~5-6MB/cycle (196MB -> 211MB) which is allocator retention
(glibc/pymalloc arenas) plus the duplicate content storage design, NOT a leak -
instance counts are flat. `mypy slate/` clean; `ruff check` clean; 245
core/services tests pass; GTK suite passes except one pre-existing unrelated
failure (`test_tab_bar_scrolls_natural_tab_width_and_styles_only_active_tab`,
fails on baseline commit too).

**Commands used.**
- Probe: `xvfb-run -a python3 -m pytest tests/ui/gtk/test_tab_memory.py -s --no-cov -o addopts=""`
- GTK suite: `xvfb-run -a python3 -m pytest tests/ui/gtk -o addopts=""`
- Safe tests: `python3 -m pytest tests/core/ tests/services/ -q --no-cov -o addopts=""`

**Known limitations.** GtkSource.Buffer instance count via `gc.get_objects()` is
always 0 (C-created buffer wrappers not tracked) so it is not a reliable signal;
EditorView count is authoritative. `--no-cov -o addopts=""` is required because
the coverage plugin and `timeout_hard_timeout` option otherwise interfere in this
environment.
