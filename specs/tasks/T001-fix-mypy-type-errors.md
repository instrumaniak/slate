# T001: Fix All 99 Mypy Type Errors

## Goal

Fix all 99 pre-existing mypy errors across the codebase to achieve strict type safety. The errors span 19 files and include missing type annotations, GTK stubs gaps, EventBus contravariance issues, None-narrowing problems, stale `type: ignore` comments, and real code bugs.

> **Verification note (2026-08-02):** Spec count corrected from 95 to 99. `pygobject-stubs 2.17.0` now provides typed stubs for `gi.repository` imports, so 4 previously-needed `# type: ignore[import-untyped]` comments are now flagged as `[unused-ignore]`: `file_service.py:310` (file was missing from this spec entirely) and `theme_service.py:145, 170, 211`. `theme_service.py` was updated from 1 → 4 errors. All other line references in Steps 1-18 were verified against current mypy output and match exactly.

## Depends On

- `pygobject-stubs==2.17.0` must be installed (`pip install pygobject-stubs --no-deps`)

## Phase: 0

## Critical: True

## Spec References

- Mypy config: `pyproject.toml` lines 123-137 (`[tool.mypy]`)
- Architecture: `AGENTS.md` (layer rules: core → services → ui → plugins)

## Files to Create/Modify

### Source files (19 files to modify)

- `slate/ui/editor/tab_manager.py` — 6 errors
- `slate/ui/editor/tab_bar.py` — 8 errors
- `slate/ui/editor/diff_navigator.py` — 2 errors
- `slate/ui/editor/editor_factory.py` — 4 errors
- `slate/ui/editor/editor_view.py` — 8 errors
- `slate/ui/editor/diff_view.py` — 10 errors
- `slate/ui/actions.py` — 3 errors
- `slate/ui/toast.py` — 1 error
- `slate/ui/panels/source_control_panel.py` — 10 errors
- `slate/ui/panels/file_explorer_tree.py` — 10 errors
- `slate/ui/dialogs/save_discard_dialog.py` — 9 errors
- `slate/ui/main_window.py` — 9 errors
- `slate/ui/app.py` — 8 errors
- `slate/services/theme_service.py` — 4 errors
- `slate/services/file_service.py` — 1 error
- `slate/__main__.py` — 3 errors
- `slate/plugins/core/source_control.py` — 2 errors
- `slate/plugins/core/file_explorer.py` — 1 error
- `slate/core/plugin_api.py` — add `event_bus` abstract property

## Implementation Steps

### Step 1: `slate/ui/editor/tab_manager.py` (6 errors)

| Line | Error | Fix |
|------|-------|-----|
| 52 | `dict` missing type args | `dict[str, dict[str, Any]]` |
| 56 | `Callable` missing type args | `Callable[[str, str], str] \| None` |
| 59 | subscribe handler contravariance | Widen `_on_open_file_requested(event: BaseEvent)` + `assert isinstance(event, OpenFileRequestedEvent)` at top of handler body. Add `BaseEvent` to imports from `slate.core.events`. |
| 73 | `dict` missing type args | `dict[str, Any]` |
| 122 | `dict` missing type args | `dict[str, Any]` |
| 190 | `dict` missing type args | `dict[str, dict[str, Any]]` |

### Step 2: `slate/ui/editor/tab_bar.py` (8 errors)

| Line | Error | Fix |
|------|-------|-----|
| 16 | `= None` after Module inferred | `Gtk = None  # type: ignore[assignment]` (also GObject, Pango) |
| 36 | `dict` missing type args | `dict[str, Gtk.ToggleButton]` |
| 37 | `dict` missing type args | `dict[str, Gtk.Label]` |
| 38 | `dict` missing type args | `dict[str, Gtk.Label]` |
| 40 | `list` missing type args | `list[str]` |
| 92 | untyped `load_from_data` | `# type: ignore[no-untyped-call]` |
| 217 | `list` missing type args | `list[str]` |
| 254 | `list` missing type args | `list[str]` |

### Step 3: `slate/ui/editor/diff_navigator.py` (2 errors)

| Line | Error | Fix |
|------|-------|-----|
| 26 | `= None` after Module | `Gtk = None  # type: ignore[assignment]` |
| 29 | Invalid conditional base class | Change to `class DiffNavigator(Gtk.Box):  # type: ignore[misc]` |

### Step 4: `slate/ui/editor/editor_factory.py` (4 errors)

| Line | Error | Fix |
|------|-------|-----|
| 17 | `= None` after Module | `GtkSource = None  # type: ignore[assignment]` |
| 58, 71 | Cannot determine `_language_manager` type | Add class-level declaration: `_language_manager: GtkSource.LanguageManager \| None = None  # type: ignore[has-type]` |
| 91 | untyped call to `_get_language_manager` | Add return type: `def _get_language_manager(self) -> GtkSource.LanguageManager \| None:` |

### Step 5: `slate/ui/editor/editor_view.py` (8 errors)

| Line | Error | Fix |
|------|-------|-----|
| 17 | `= None` after Module | `GtkSource: Any = None` / `Gtk: Any = None` / `Pango: Any = None` (add `from typing import Any` if needed) |
| 74 | untyped `load_from_data` | `# type: ignore[no-untyped-call]` |
| 79 | Invalid conditional base class | `# type: ignore[misc]` |
| 133 | Returning Any as str | `# type: ignore[no-any-return]` |
| 156 | Returning Any as str\|None | `# type: ignore[no-any-return]` |
| 164, 171 | Returning Any as bool | `# type: ignore[no-any-return]` on each |
| 188 | Returning Any as bool | `# type: ignore[no-any-return]` |

### Step 6: `slate/ui/editor/diff_view.py` (10 errors)

| Line | Error | Fix |
|------|-------|-----|
| 31-34 | `= None` after Module | `# type: ignore[assignment]` on each line |
| 145 | Invalid conditional base class | `# type: ignore[misc]` |
| 188 | `Pango.Layout` missing `context` param | `# type: ignore[call-arg]` |
| 240 | Invalid conditional base class | `# type: ignore[misc]` |
| 448 | Returns None but typed `View` | Change return type to `GtkSource.View \| None` |
| 546-547 | `TextTag \| None` assigned to `TextTag` | Add `assert addition_tag is not None` and `assert deletion_tag is not None` after the lookup calls |

### Step 7: `slate/ui/actions.py` (3 errors)

| Line | Error | Fix |
|------|-------|-----|
| 31, 36, 40 | `Window` has no `add_action` | `# type: ignore[attr-defined]` on each (lives on Gio.ActionMap interface, not in Gtk.Window stubs) |

### Step 8: `slate/ui/toast.py` (1 error)

| Line | Error | Fix |
|------|-------|-----|
| 56 | `dismiss()` return consumed in tuple | Extract to helper method: `def _on_action_clicked(self, callback): callback(); self.dismiss()` then connect with `lambda *_: self._on_action_clicked(callback)` |

### Step 9: `slate/ui/panels/source_control_panel.py` (10 errors)

| Line | Error | Fix |
|------|-------|-----|
| 107-108 | subscribe contravariance | Widen `_on_git_status_changed(self, event: BaseEvent)` + `assert isinstance(event, GitStatusChangedEvent)`. Add `BaseEvent` to imports. |
| 114-115 | unsubscribe contravariance | Same handler fix as above covers both subscribe and unsubscribe |
| 295 (2 errors) | `SelectionModel` has no `get_selected_item` / `get_item` | Add `isinstance(model, Gtk.SingleSelection)` guard after the None check (covers both errors) |
| 306 | `EventBus \| None` has no `emit` | Add `self._event_bus` to the existing `if` condition on line 299 |
| 334 | `Root` not `Window` | `isinstance(parent, Gtk.Window)` guard |
| 352 | `Dialog.run` removed from stubs | `# type: ignore[attr-defined]` (deprecated in GTK 4.10) |
| 354 | Returning Any as bool | `return bool(response == Gtk.ResponseType.OK)` |

### Step 10: `slate/ui/panels/file_explorer_tree.py` (10 errors)

| Line | Error | Fix |
|------|-------|-----|
| 69 | `ListStore` missing type args | `Gio.ListStore[FileTreeItem]` |
| 133, 138 | subscribe/unsubscribe contravariance | Widen `_on_folder_changed(self, event: BaseEvent)` + `assert isinstance(event, FolderOpenedEvent)`. Add `BaseEvent` to imports. |
| 275 | untyped `Gdk.Rectangle()` | `# type: ignore[no-untyped-call]` |
| 365 | `Clipboard \| None` assigned to `Clipboard` | Declare `clipboard: Gdk.Clipboard \| None = None` at top of method, restructure try/except |
| 756 | `ListStore` missing type args | `Gio.ListStore[FileTreeItem] \| None` |
| 765 | `ListStore` missing type args | `tuple[Gio.ListStore[FileTreeItem], str \| None]` |
| 822, 924 | int instead of EllipsizeMode | `Pango.EllipsizeMode.END` (both lines have same issue) |
| 968, 971 | `Object` has no `is_folder`/`path` | `isinstance(tree_item, FileTreeItem)` guard + early return |

### Step 11: `slate/ui/dialogs/save_discard_dialog.py` (9 errors)

| Line | Error | Fix |
|------|-------|-----|
| 17 | `= None` after Module | `Gtk = None  # type: ignore[assignment]` and `GLib = None  # type: ignore[assignment]` |
| 83 | `Dialog \| None` access | Add `if self._dialog is None: return` at top of `_setup_keyboard_handling` |
| 102, 105 | `Dialog \| None` access | Add `if self._dialog is None: return False` at top of `_on_key_pressed` |
| 116 | `int` not matching `ResponseType` key | Cast: `Gtk.ResponseType(response_id)` |
| 117 | `Dialog \| None` access | `if self._dialog is not None: self._dialog.hide()` |
| 131 | `Dialog \| None` access | `if self._dialog is not None: self._dialog.present()` |
| 149 | `Dialog \| None` access | `if self._dialog is not None: self._dialog.present()` |
| 156 | `Dialog \| None` access | `if self._dialog is not None: self._dialog.hide()` |

### Step 12: `slate/ui/main_window.py` (9 errors)

| Line | Error | Fix |
|------|-------|-----|
| 360 | Returns `Overlay` not `Box` | Change return type to `Gtk.Widget` |
| 501 | `dict` missing type args | `dict[str, Any]` |
| 520 | Lambda type inference | Simplify to `lambda dirty: self._on_editor_modified(path, dirty)` |
| 557 | `str \| None` where `str` needed | Add `if self._current_folder is None: return` guard before call |
| 673, 676 | Variable shadow (`action` reused) + downstream type error | Rename loop var from `action` to `action_name` (fixes both 673 assignment and 676 `NamedAction.new` type mismatch) |
| 762 | `SlateToast` assigned to `None` | Annotate: `self._toast: SlateToast \| None = None` in `__init__`. Add `SlateToast` to TYPE_CHECKING import block. |
| 765 | `None` has no `show` | Resolved by type annotation. Also add `if self._toast is not None:` guard. |
| 821 | Returns `bool` but typed `-> None` | Change `_on_close_request` return type to `bool`. Ensure all paths return bool. |

### Step 13: `slate/ui/app.py` (8 errors)

| Line | Error | Fix |
|------|-------|-----|
| 95 | `ConfigService` assigned to `None` | Annotate: `self._config_service: ConfigService \| None = None`. Add TYPE_CHECKING imports for ConfigService, ThemeService, SlateWindow. |
| 98 | `ThemeService` assigned to `None` | Annotate: `self._theme_service: ThemeService \| None = None` |
| 99 | `None` has no `resolve_theme` | Add `assert self._theme_service is not None` after assignment |
| 164 | untyped `AppPluginContext.__init__` | Add full type annotations to `__init__` parameters |
| 169, 177, 189, 191 | `None` has no attribute | Add `assert self._main_window is not None` and `assert self._config_service is not None` after their assignments |

### Step 14: `slate/services/theme_service.py` (4 errors)

| Line | Error | Fix |
|------|-------|-----|
| 145 | Unused `# type: ignore[import-untyped]` | Delete stale `# type: ignore[import-untyped]` on `from gi.repository import Gtk` (now typed via pygobject-stubs) |
| 170 | Unused `# type: ignore[import-untyped]` | Delete stale `# type: ignore[import-untyped]` on `from gi.repository import Gtk` |
| 211 | Unused `# type: ignore[import-untyped]` | Delete stale `# type: ignore[import-untyped]` on `from gi.repository import Gtk` |
| 215 | `disconnect()` void return captured | Remove `success = ` — just call `settings.disconnect(self._theme_watcher_id)` directly |

### Step 14b: `slate/services/file_service.py` (1 error)

| Line | Error | Fix |
|------|-------|-----|
| 310 | Unused `# type: ignore[import-untyped]` | Delete stale `# type: ignore[import-untyped]` on `from gi.repository import Gio` (now typed via pygobject-stubs) |

### Step 15: `slate/__main__.py` (3 errors)

| Line | Error | Fix |
|------|-------|-----|
| 65, 70, 81 | Calls to untyped functions | Add return type annotations: `def parse_args() -> argparse.Namespace:`, `def resolve_path(path_arg: str \| None) -> str \| None:`, `def main() -> int:` |

### Step 16: `slate/core/plugin_api.py` + `slate/plugins/core/source_control.py` (2 errors)

| File | Line | Error | Fix |
|------|------|-------|-----|
| `plugin_api.py` | N/A | Missing `event_bus` property | Add abstract property: `@property @abstractmethod def event_bus(self) -> "EventBus": ...` with TYPE_CHECKING import |
| `source_control.py` | 66 | `PluginContext` has no `event_bus` | Resolved by adding abstract property to `PluginContext` |
| `source_control.py` | 76 | Returns `Panel \| None` typed as `Panel` | Change return type to `SourceControlPanel \| None` |

### Step 17: `slate/plugins/core/file_explorer.py` (1 error)

| Line | Error | Fix |
|------|-------|-----|
| 91 | Returns `Panel \| None` typed as `Panel` | Change return type to `FileExplorerTree \| None` |

### Step 18: Run verification

```bash
# Type check
python3 -m mypy slate/

# Lint
ruff check slate/ tests/
ruff format --check .

# Safe tests
pytest tests/core/ tests/services/ -v
```

## Constraints

- All `# type: ignore` comments must use **specific error codes** (e.g., `[assignment]`, not bare `# type: ignore`)
- Never use bare `# type: ignore` — always specify the error code
- Do not change runtime behavior — only type annotations, guards, and targeted suppressions
- Follow existing code conventions (lazy imports in services/, TYPE_CHECKING guards in ui/)
- The `core/` layer must remain GTK-free — never add GTK imports there

## Acceptance Criteria

- [ ] `python3 -m mypy slate/` reports 0 errors
- [ ] `ruff check slate/ tests/` passes (no new errors)
- [ ] `pytest tests/core/ tests/services/ -v` passes
- [ ] All `# type: ignore` comments include specific error codes
- [ ] No bare `# type: ignore` comments added

## Notes

- 99 errors total across 18 files
- ~25 are missing type annotations (real improvements)
- ~10 are GTK fallback `None = Module` pattern (targeted suppressions)
- ~8 are EventBus subscribe/unsubscribe contravariance (real code fixes)
- ~5 are conditional base classes (targeted suppressions)
- ~14 are None attribute access (add guards/asserts)
- ~12 are GTK stubs gaps (targeted suppressions)
- 4 are stale `# type: ignore[import-untyped]` comments (delete; became unused after pygobject-stubs installed)
- ~15 are real code fixes (return types, variable shadowing, void return capture)
- ~6 are missing function annotations

### Code review remarks (2026-08-02)

- The 2 surviving `# type: ignore` suppressions (`editor_view.py:45`,
  `file_explorer_tree.py:275`) were given explanatory comments during the T002
  review; both carry specific error codes per the constraints.
- `slate/__main__.py` (typed in Step 15) was later adjusted so
  `check_environment()` runs after `parse_args()`, keeping
  `python -m slate --version` functional on headless/GTK-less machines. See
  T002 notes for details.
