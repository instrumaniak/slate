# Proposal: Remove libadwaita — Pure GTK4 Migration

**Project:** Slate
**Author:** Raziur
**Date:** 2026-03-28
**Status:** Draft — Ready for review
**Priority:** High

---

## 1. Problem Statement

Slate currently depends on libadwaita (`gir1.2-adw-1`) for its window shell, header bar, and theme detection. Older versions of libadwaita cause incompatibilities and bugs that waste development time on library-version issues rather than building features. We need broad GTK4 compatibility across Ubuntu 22.04+ systems without requiring libadwaita.

## 2. Decision

**Remove all libadwaita dependency. Use pure GTK4 only.**

Target floor: **Ubuntu 22.04** (GTK 4.6.9, PyGObject 3.42.1)

Everything in this project — code, specs, story specs, architecture docs — must be compliant with pure GTK4. No Adwaita widgets, no Adwaita imports, no references to `gir1.2-adw-1`.

## 3. System Validation Results

All replacements were verified by running live tests on the target system:

| Component | Version | Status |
|---|---|---|
| GTK4 | 4.6.9 | Verified |
| PyGObject | 3.42.1 | Verified |
| Ubuntu | 22.04 | Target floor |

### Widget Availability Verified

| Widget | GTK 4.6 | GTK 4.10+ | Status on 22.04 |
|---|---|---|---|
| `Gtk.Application` | Yes | Yes | Available |
| `Gtk.ApplicationWindow` | Yes | Yes | Available |
| `Gtk.HeaderBar` | Yes | Yes | Available |
| `Gtk.MessageDialog` | Yes | Yes | Available |
| `Gtk.Dialog` | Yes | Yes | Available |
| `Gtk.Switch` | Yes | Yes | Available |
| `Gtk.SpinButton` | Yes | Yes | Available |
| `Gtk.ComboBoxText` | Yes | Yes | Available |
| `Gtk.Notebook` | Yes | Yes | Available |
| `Gtk.FontButton` | Yes | Yes | Available |
| `Gtk.Revealer` | Yes | Yes | Available |
| `Gtk.Overlay` | Yes | Yes | Available |
| `Gtk.Settings` | Yes | Yes | Available |
| `Gtk.ListBox` | Yes | Yes | Available |
| `Gtk.ListBoxRow` | Yes | Yes | Available |
| `Gtk.InfoBar` | Yes | Deprecated | Available but deprecated |
| `Gtk.FontDialogButton` | No | Yes | **NOT available** |
| `Gtk.Inscription` | No | Yes | **NOT available** |

## 4. Complete Widget Mapping Table

This is the single source of truth for all Adwaita widget replacements. Covers both currently implemented and planned (future) widgets.

### 4.1 Core Application Shell

| Adwaita Widget | GTK4 Replacement | API Differences |
|---|---|---|
| `Adw.Application` | `Gtk.Application` | Direct replacement. Same constructor, same flags. Adw.Application auto-loads Adwaita CSS theme; Gtk.Application uses system GTK theme instead. |
| `Adw.ApplicationWindow` | `Gtk.ApplicationWindow` | `set_content(child)` becomes `set_child(child)`. All other methods identical. |
| `Adw.HeaderBar()` | `Gtk.HeaderBar()` | `set_show_start_title_buttons(bool)` and `set_show_end_title_buttons(bool)` do NOT exist. Use `set_show_title_buttons(bool)` + `set_decoration_layout(string)` to control button placement. |

#### HeaderBar Button Control

**Current Adw code:**
```python
header.set_show_start_title_buttons(False)
header.set_show_end_title_buttons(True)
```

**GTK4 equivalent:**
```python
header.set_show_title_buttons(True)
header.set_decoration_layout(":minimize,maximize,close")
#  ^ empty left = no start buttons, right = standard close/min/max
```

### 4.2 Theme Detection

| Adwaita Widget | GTK4 Replacement | API Differences |
|---|---|---|
| `Adw.StyleManager.get_default()` | `Gtk.Settings.get_default()` | Simpler API. One property instead of object + method chain. |
| `Adw.ColorScheme.PREFER_DARK` | Boolean property check | Direct boolean, no enum. |
| `style_manager.get_color_scheme()` | `settings.get_property("gtk-application-prefer-dark-theme")` | Returns `True` for dark, `False` for light. |

#### Current code (theme_service.py):

```python
import gi
gi.require_version("Adw", "1")
from gi.repository import Adw

style_manager = Adw.StyleManager.get_default()
color_scheme = style_manager.get_color_scheme()
is_dark = bool(color_scheme == Adw.ColorScheme.PREFER_DARK)
```

#### GTK4 replacement:

```python
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

settings = Gtk.Settings.get_default()
is_dark = bool(settings.get_property("gtk-application-prefer-dark-theme"))
```

#### Live theme change detection:

```python
# GTK4 supports live detection via notify signal
settings = Gtk.Settings.get_default()
settings.connect("notify::gtk-application-prefer-dark-theme", on_theme_changed)
```

### 4.3 Dialogs

| Adwaita Widget | GTK4 Replacement | API Differences |
|---|---|---|
| `Adw.MessageDialog` | `Gtk.MessageDialog` | Same concept. `add_button()`, `set_default_response()`, `get_widget_for_response()` all work. Note: `format_secondary_text()` is GTK3-only — add a label manually to content area. |
| `Adw.AlertDialog` | `Gtk.MessageDialog` | Same as above. Adw.AlertDialog is libadwaita 1.5+ only anyway. |

#### Save/Discard/Cancel dialog pattern:

```python
dialog = Gtk.MessageDialog(
    message_type=Gtk.MessageType.QUESTION,
    buttons=Gtk.ButtonsType.NONE,
    text="Save changes to 'file.py'?"
)
dialog.set_transient_for(parent)
dialog.set_modal(True)
dialog.add_button("Don't Save", Gtk.ResponseType.NO)
dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
dialog.add_button("Save", Gtk.ResponseType.YES)

save_btn = dialog.get_widget_for_response(Gtk.ResponseType.YES)
save_btn.add_css_class("suggested-action")

# Add body text (GTK4 way — no format_secondary_text)
content_area = dialog.get_content_area()
label = Gtk.Label(label="Your changes will be lost if you don't save them.")
label.set_margin_top(8)
label.set_margin_bottom(16)
label.set_margin_start(16)
label.set_margin_end(16)
content_area.append(label)

dialog.set_default_response(Gtk.ResponseType.YES)
```

### 4.4 Preferences Window

| Adwaita Widget | GTK4 Replacement | API Differences |
|---|---|---|
| `Adw.PreferencesWindow` | `Gtk.Dialog` + `Gtk.Notebook` | No built-in preferences layout. Build with a Notebook (tabs) containing ListBox rows. |
| `Adw.SpinRow` | `Gtk.Box` with `Gtk.Label` + `Gtk.SpinButton` | Manual row layout. Wrap in a ListBoxRow for consistent spacing. |
| `Adw.SwitchRow` | `Gtk.Box` with `Gtk.Label` + `Gtk.Switch` | Manual row layout. Wrap in a ListBoxRow. |
| `Adw.ComboRow` | `Gtk.Box` with `Gtk.Label` + `Gtk.ComboBoxText` | Manual row layout. Wrap in a ListBoxRow. |

#### Preferences dialog structure:

```python
dialog = Gtk.Dialog(title="Preferences")
dialog.set_transient_for(parent)
dialog.set_modal(True)
dialog.set_default_size(600, 500)

notebook = Gtk.Notebook()

# Page 1: Editor
editor_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
editor_page.set_margin_top(12)
editor_page.set_margin_bottom(12)
editor_page.set_margin_start(12)
editor_page.set_margin_end(12)

# Tab Width row
tab_width_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
tab_width_label = Gtk.Label(label="Tab Width")
tab_width_label.set_hexpand(True)
tab_width_label.set_xalign(0)
adj = Gtk.Adjustment(value=4, lower=1, upper=8, step_increment=1)
tab_width_spin = Gtk.SpinButton(adjustment=adj)
tab_width_row.append(tab_width_label)
tab_width_row.append(tab_width_spin)
editor_page.append(tab_width_row)

# Insert Spaces row
spaces_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
spaces_label = Gtk.Label(label="Insert Spaces")
spaces_label.set_hexpand(True)
spaces_label.set_xalign(0)
spaces_switch = Gtk.Switch()
spaces_row.append(spaces_label)
spaces_row.append(spaces_switch)
editor_page.append(spaces_row)

notebook.append_page(editor_page, Gtk.Label(label="Editor"))

# Page 2: Appearance (similar pattern with ComboBoxText for theme selection)
# ...

dialog.get_content_area().append(notebook)
```

### 4.5 Toast / In-App Notifications

| Adwaita Widget | GTK4 Replacement | API Differences |
|---|---|---|
| `Adw.Toast` | `Gtk.Overlay` + `Gtk.Revealer` + `app-notification` CSS class | No built-in widget. Must compose from existing widgets. GTK4 provides the `app-notification` CSS class natively — no custom CSS needed. |

Note: `Gtk.InfoBar` is deprecated since GTK 4.10. Do not use it. Use the Overlay+Revealer pattern.

#### Toast architecture:

```
Gtk.Overlay (container — wraps main window content)
  ├── [child] Main content (existing content_box)
  └── [overlay] Gtk.Revealer (positioned at top-center)
                  └── Gtk.Box (css: "app-notification")
                        ├── Gtk.Label (message text)
                        ├── Gtk.Button (optional action, e.g. "Undo")
                        └── Gtk.Button (close icon: "window-close-symbolic")
```

#### Implementation:

```python
class SlateToast:
    """In-app notification using pure GTK4.

    Uses Gtk.Overlay + Gtk.Revealer + GTK4's built-in
    'app-notification' CSS class. No custom CSS required.
    """

    def __init__(self, overlay: Gtk.Overlay) -> None:
        self._revealer = Gtk.Revealer()
        self._revealer.set_halign(Gtk.Align.CENTER)
        self._revealer.set_valign(Gtk.Align.START)
        self._revealer.set_margin_top(12)
        self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        self._box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._box.add_css_class("app-notification")

        self._label = Gtk.Label()
        self._box.append(self._label)

        self._close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")
        self._close_btn.add_css_class("flat")
        self._close_btn.connect("clicked", lambda *_: self.dismiss())
        self._box.append(self._close_btn)

        self._revealer.set_child(self._box)
        overlay.add_overlay(self._revealer)

    def show(self, message: str, duration: int = 3) -> None:
        """Show a toast message for duration seconds."""
        self._label.set_label(message)
        self._revealer.set_revealed(True)
        from gi.repository import GLib
        GLib.timeout_add_seconds(duration, self._dismiss_timeout)

    def show_with_action(self, message: str, action_label: str,
                         callback, duration: int = 5) -> None:
        """Show a toast with an action button."""
        # Remove old action button if exists
        for child in list(self._box):
            if child != self._label and child != self._close_btn:
                self._box.remove(child)

        action_btn = Gtk.Button(label=action_label)
        action_btn.add_css_class("flat")
        action_btn.connect("clicked", lambda *_: (callback(), self.dismiss()))
        # Insert before close button
        self._box.insert_child_after(action_btn, self._label)

        self.show(message, duration)

    def dismiss(self) -> None:
        self._revealer.set_revealed(False)

    def _dismiss_timeout(self) -> bool:
        self._revealer.set_revealed(False)
        return False  # Don't repeat
```

#### Window integration:

```python
# In _setup_main_layout:
overlay = Gtk.Overlay()
content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
# ... build all content into content_box ...
overlay.set_child(content_box)

self._toast = SlateToast(overlay)
self.set_child(overlay)  # was set_content in Adw
```

### 4.6 Font Selection

| Adwaita Widget | GTK4 Replacement | API Differences |
|---|---|---|
| `Gtk.FontDialogButton` (GTK 4.10+) | `Gtk.FontButton` | Different API. `get_font()` returns Pango font string. `get_font_family()` and `get_font_size()` for programmatic access. |

### 4.7 CSS Classes

All GTK4 built-in CSS classes remain valid. The following are confirmed available:

| CSS Class | Purpose |
|---|---|
| `suggested-action` | Primary action button styling |
| `destructive-action` | Destructive/danger button styling |
| `flat` | Flat (no background) button |
| `pill` | Pill-shaped button |
| `accent` | Accent color |
| `success` | Green success state |
| `warning` | Yellow warning state |
| `error` | Red error state |
| `app-notification` | Toast/notification bar styling |
| `sidebar` | Sidebar panel styling |
| `toolbar` | Toolbar/activity bar styling |
| `title` | Title label styling |
| `heading` | Heading label styling |
| `dim-label` | Muted/dimmed label |
| `caption` | Small caption text |
| `monospace` | Monospace font |

## 5. Source Code Changes

### 5.1 `slate/ui/app.py`

**Current:**
```python
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Adw, Gio

class SlateApplication(Adw.Application):
    def _on_activate(self, app: Adw.Application) -> None:
```

**Change to:**
```python
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, Gio

class SlateApplication(Gtk.Application):
    def _on_activate(self, app: Gtk.Application) -> None:
```

Also update error message from:
```
"Install: python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksource-5"
```
to:
```
"Install: python3-gi gir1.2-gtk-4.0 gir1.2-gtksource-5"
```

### 5.2 `slate/ui/main_window.py`

**Current (lines 14-16):**
```python
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio
```

**Change to:**
```python
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio
```

**Current (line 26):**
```python
class SlateWindow(Adw.ApplicationWindow):
```

**Change to:**
```python
class SlateWindow(Gtk.ApplicationWindow):
```

**Current (line 31):**
```python
    def __init__(self, app: Adw.Application, ...):
```

**Change to:**
```python
    def __init__(self, app: Gtk.Application, ...):
```

**Current (lines 86-93):**
```python
header = Adw.HeaderBar()
header.set_show_start_title_buttons(False)
header.set_show_end_title_buttons(True)

title_label = Gtk.Label(label="Slate")
title_label.set_css_classes(["title"])
header.set_title_widget(title_label)
```

**Change to:**
```python
header = Gtk.HeaderBar()
header.set_show_title_buttons(True)
header.set_decoration_layout(":minimize,maximize,close")

title_label = Gtk.Label(label="Slate")
title_label.add_css_class("title")
header.set_title_widget(title_label)
```

Note: `set_css_classes(["title"])` is also a good time to migrate to `add_css_class("title")` which is the more idiomatic GTK4 way (both work, but `add_css_class` is safer — adds without replacing).

**Current (line 114):**
```python
self.set_content(content_box)
```

**Change to:**
```python
# If adding toast support now:
overlay = Gtk.Overlay()
overlay.set_child(content_box)
self._toast = SlateToast(overlay)
self.set_child(overlay)

# OR if not adding toast yet (simpler):
self.set_child(content_box)
```

### 5.3 `slate/services/theme_service.py`

**Current `_detect_system_theme()` method (lines 88-133):**
```python
def _detect_system_theme(self) -> bool:
    try:
        import gi
        gi.require_version("Adw", "1")
        from gi.repository import Adw
        style_manager = Adw.StyleManager.get_default()
        if style_manager is None:
            raise RuntimeError("Adw.StyleManager.get_default() returned None")
        color_scheme = style_manager.get_color_scheme()
        return bool(color_scheme == Adw.ColorScheme.PREFER_DARK)
    except (ImportError, AttributeError, RuntimeError) as e:
        logger.debug(f"Adwaita theme detection failed: {e}")

    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        settings = Gtk.Settings.get_default()
        if settings is None:
            logger.debug("Gtk.Settings.get_default() returned None")
            return False
        return bool(settings.get_property("gtk-application-prefer-dark-theme"))
    except (ImportError, AttributeError) as e:
        logger.debug(f"GTK theme detection failed: {e}")

    return False
```

**Change to (simplified — GTK4 only, no fallback chain):**
```python
def _detect_system_theme(self) -> bool:
    """Detect if system prefers dark theme.

    Uses lazy import to avoid GTK at module level.
    Reads Gtk.Settings gtk-application-prefer-dark-theme property.
    Supports live theme change detection via notify signal.

    Returns:
        True if system prefers dark theme, False otherwise.
    """
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk  # type: ignore[import-untyped]

        settings = Gtk.Settings.get_default()
        if settings is None:
            logger.debug("Gtk.Settings.get_default() returned None")
            return False

        return bool(settings.get_property("gtk-application-prefer-dark-theme"))
    except (ImportError, AttributeError) as e:
        logger.debug(f"GTK theme detection failed: {e}")
        return False
```

Also update the module docstring — remove the reference to "First tries Adwaita StyleManager, falls back to Gtk.Settings."

### 5.4 `scripts/install-deps.sh`

**Current (line 18):**
```bash
    gir1.2-gtksource-5 \
    gir1.2-adw-1
```

**Change to:**
```bash
    gir1.2-gtksource-5
```

Remove the trailing backslash on the `gir1.2-gtksource-5` line since it's now the last item.

### 5.5 `slate/ui/dialogs/save_discard_dialog.py`

**No changes needed.** This file already uses pure GTK4 (`Gtk.Dialog`). Verified working.

## 6. Test Changes

### 6.1 `tests/services/test_theme_service.py`

**Tests to remove or rewrite:**

| Test | Current | Action |
|---|---|---|
| `test_detect_system_theme_with_adw_prefer_dark` | Mocks Adw.StyleManager | Rewrite to mock Gtk.Settings |
| `test_detect_system_theme_with_adw_prefer_light` | Mocks Adw.StyleManager | Rewrite to mock Gtk.Settings |
| `test_detect_system_theme_fallback_to_gtk` | Tests Adw → Gtk fallback | Remove — no fallback chain anymore |
| `test_graceful_fallback_when_adw_style_manager_none` | Tests Adw returning None | Remove — Adw not used |
| `test_graceful_fallback_when_gtk_settings_none` | Tests Gtk fallback when Adw fails | Rewrite as single Gtk.Settings None test |
| `test_graceful_fallback_when_no_gtk` | Tests when everything fails | Keep — still valid |

**New/rewritten tests:**

```python
def test_detect_system_theme_with_gtk_dark(self):
    """Should detect dark when Gtk.Settings prefers dark theme."""
    mock_config = Mock()
    mock_config.get.return_value = "system"

    mock_settings = MagicMock()
    mock_settings.get_property.return_value = True

    service = ThemeService(config_service=mock_config)

    with patch("gi.require_version"):
        with patch.dict("sys.modules", {"gi.repository.Gtk": MagicMock(Settings=MagicMock(get_default=MagicMock(return_value=mock_settings)))}):
            result = service._detect_system_theme()
            assert result is True

def test_detect_system_theme_with_gtk_light(self):
    """Should detect light when Gtk.Settings does not prefer dark."""
    mock_config = Mock()
    mock_config.get.return_value = "system"

    mock_settings = MagicMock()
    mock_settings.get_property.return_value = False

    service = ThemeService(config_service=mock_config)

    with patch("gi.require_version"):
        with patch.dict("sys.modules", {"gi.repository.Gtk": MagicMock(Settings=MagicMock(get_default=MagicMock(return_value=mock_settings)))}):
            result = service._detect_system_theme()
            assert result is False

def test_graceful_when_gtk_settings_none(self):
    """Should return False when Gtk.Settings.get_default() returns None."""
    mock_config = Mock()
    mock_config.get.return_value = "system"

    service = ThemeService(config_service=mock_config)

    with patch("gi.require_version"):
        with patch.dict("sys.modules", {"gi.repository.Gtk": MagicMock(Settings=MagicMock(get_default=MagicMock(return_value=None)))}):
            result = service._detect_system_theme()
            assert result is False
```

## 7. Documentation Changes

Every file below must have all libadwaita references updated. Changes are listed per file.

### 7.1 `docs/slate-spec.md` (29 references)

| Line(s) | Current Text | Change To |
|---|---|---|
| ~976 | "GTK/libadwaita runtime application stays in the UI layer" | "GTK4 runtime application stays in the UI layer" |
| ~1465 | `Adw.Application; composition root` | `Gtk.Application; composition root` |
| ~1493 | `dialog.py ← Adw.PreferencesWindow` | `dialog.py ← Gtk.Dialog + Gtk.Notebook (Preferences)` |
| ~1504 | `class SlateApplication(Adw.Application)` | `class SlateApplication(Gtk.Application)` |
| ~1633 | "Updates Adw.Application color scheme" | "Updates Gtk.Settings color scheme" |
| ~1714 | `Adw.AlertDialog` | `Gtk.MessageDialog` |
| ~1887 | `libadwaita (gi.repository.Adw)` | `GTK4 (gi.repository.Gtk)` with updated description |
| ~1897 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |
| ~1972 | `class SlateApplication(Adw.Application)` | `class SlateApplication(Gtk.Application)` |
| ~2009 | `← Adw.HeaderBar` | `← Gtk.HeaderBar` |
| ~2057 | `Adw.HeaderBar` | `Gtk.HeaderBar` |
| ~2158 | `Adw.Toast` | `SlateToast (Gtk.Overlay + Gtk.Revealer)` |
| ~2186 | `Adw.PreferencesWindow with two pages` | `Preferences dialog: Gtk.Dialog with Gtk.Notebook tabs` |
| ~2193 | `Adw.SpinRow (1–8)` | `Gtk.SpinButton (1–8) in a labeled row` |
| ~2194 | `Adw.SwitchRow` | `Gtk.Switch in a labeled row` |
| ~2195 | `Adw.SwitchRow` | `Gtk.Switch in a labeled row` |
| ~2196 | `Adw.SwitchRow` | `Gtk.Switch in a labeled row` |
| ~2197 | `Adw.SwitchRow` | `Gtk.Switch in a labeled row` |
| ~2198 | `Adw.SwitchRow` | `Gtk.Switch in a labeled row` |
| ~2204 | `Adw.ComboRow (System / Light / Dark)` | `Gtk.ComboBoxText (System / Light / Dark) in a labeled row` |
| ~2205 | `Adw.ComboRow (Auto / Explicit)` | `Gtk.ComboBoxText (Auto / Explicit) in a labeled row` |
| ~2206 | `Adw.ComboRow` | `Gtk.ComboBoxText in a labeled row` |
| ~2207 | `Adw.ComboRow` | `Gtk.ComboBoxText in a labeled row` |
| ~2208 | `Adw.ComboRow` | `Gtk.ComboBoxText in a labeled row` |
| ~2224 | `Adw.AlertDialog (Save / Discard / Cancel)` | `Gtk.MessageDialog (Save / Discard / Cancel)` |
| ~2281 | `Adw.Application inherits system GTK4/Adwaita theme automatically — zero custom CSS on the chrome` | `Gtk.Application inherits system GTK4 theme automatically — app-specific accents use a small custom CSS layer` |
| ~2367 | `Adw.AlertDialog at the UI boundary` | `Gtk.MessageDialog at the UI boundary` |
| ~2369 | `Adw.Toast on commit error` | `SlateToast on commit error` |
| ~2370 | `Adw.AlertDialog (Save / Discard / Cancel)` | `Gtk.MessageDialog (Save / Discard / Cancel)` |

### 7.2 `_bmad-output/project-context.md` (4 references)

| Line | Current | Change To |
|---|---|---|
| 30 | `\| HIG Shell \| libadwaita (Adw) \| GTK4 built-in \|` | `\| UI Framework \| GTK4 \| GTK4 built-in \|` |
| 44 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |
| 144 | `SlateApplication(Adw.Application)` | `SlateApplication(Gtk.Application)` |
| 261 | `Adw.AlertDialog` | `Gtk.MessageDialog` |

### 7.3 `_bmad-output/planning-artifacts/architecture.md` (1 reference)

| Line | Current | Change To |
|---|---|---|
| 226 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |

Also update:
- Line ~50: `UI Framework: GTK4, GtkSourceView 5, Adwaita` → `UI Framework: GTK4, GtkSourceView 5`
- Line ~37: `Integration: GTK4/Adwaita native theme` → `Integration: GTK4 native theme`
- Line ~61: `Theme System: Must inherit GTK4/Adwaita` → `Theme System: Must inherit GTK4`

### 7.4 `_bmad-output/planning-artifacts/prd.md` (1 reference)

| Line | Current | Change To |
|---|---|---|
| 178 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |

### 7.5 `_bmad-output/planning-artifacts/epics.md` (3 references)

| Line | Current | Change To |
|---|---|---|
| 87 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |
| 540 | `Adw.PreferencesWindow` | `Gtk.Dialog with Gtk.Notebook (preferences)` |
| 627 | `Adw.Toast` | `SlateToast (in-app notification)` |

### 7.6 `_bmad-output/planning-artifacts/ux-design-specification.md` (16 references)

| Category | Lines | Changes |
|---|---|---|
| Framework references | 52, 149 | `GTK4/Adwaita` → `GTK4` |
| Theme inheritance | 59, 164, 169, 251, 253, 261, 849, 1014 | Remove `Adwaita`, keep `GTK4`. Theme detection via `Gtk.Settings` instead of Adwaita auto-inheritance. |
| CSS classes | 179, 186, 187 | Remove `Adwaita` mentions. GTK4 provides same CSS class system. |
| Platform design | 125 | `GTK4/Adwaita` → `GTK4` |
| Toast notifications | 418, 461, 660, 686, 720, 725, 727, 735, 814 | `Adw.Toast` / `GtkToast` → `SlateToast (Gtk.Overlay + Gtk.Revealer with app-notification CSS)` |
| Foundation components | 646 | `GTK4/Adwaita` → `GTK4` |

### 7.7 `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-24.md` (1 reference)

| Line | Current | Change To |
|---|---|---|
| 99 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |

### 7.8 `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-25.md` (1 reference)

| Line | Current | Change To |
|---|---|---|
| 115 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |

### 7.9 `_bmad-output/implementation-artifacts/1-1-project-initialization-packaging.md` (2 references)

| Line | Current | Change To |
|---|---|---|
| 74 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |
| 161 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |

### 7.10 `_bmad-output/implementation-artifacts/1-4-services-layer-configservice-themeservice.md` (3 references)

| Line | Current | Change To |
|---|---|---|
| 281 | `Adw.StyleManager.get_default()` | `Gtk.Settings gtk-application-prefer-dark-theme` |
| 284 | `Adw.StyleManager provides color_scheme` | `Gtk.Settings provides gtk-application-prefer-dark-theme boolean` |
| 298 | `Adw.AlertDialog` | `Gtk.MessageDialog` |

### 7.11 `_bmad-output/implementation-artifacts/1-6-main-window-editor-view.md` (5 references)

| Line | Current | Change To |
|---|---|---|
| 171 | `class SlateWindow(Adw.ApplicationWindow)` | `class SlateWindow(Gtk.ApplicationWindow)` |
| 174 | `app: Adw.Application` | `app: Gtk.Application` |
| 241 | `Adw.ApplicationWindow` | `Gtk.ApplicationWindow` |
| 254 | `libadwaita (Adw) — GTK4/Adwaita window shell` | `GTK4 — native window shell` |
| 259 | `gir1.2-gtk-4.0 gir1.2-gtksource-5 gir1.2-adw-1` | `gir1.2-gtk-4.0 gir1.2-gtksource-5` |

### 7.12 `_bmad-output/implementation-artifacts/1-7-tab-manager-save-discard-guard.md` (8 references)

| Line | Current | Change To |
|---|---|---|
| 35 | `Implement Adw.MessageDialog with 3 buttons` | `Implement Gtk.MessageDialog with 3 buttons` |
| 56 | `Adw.MessageDialog for GTK4/Adwaita consistency` | `Gtk.MessageDialog for broad GTK4 compatibility` |
| 126 | `Never use GTK MessageDialog — use Adw.MessageDialog` | Remove this line entirely. `Gtk.MessageDialog` IS the correct widget. |
| 158 | `class SaveDiscardDialog(Adw.MessageDialog)` | `class SaveDiscardDialog` (wraps `Gtk.Dialog`, which is what the actual code does) |
| 160 | `# Adw.MessageDialog with 3 buttons` | `# Gtk.Dialog with 3 buttons` |
| 181 | `SaveDiscardDialog uses Adw.MessageDialog` | `SaveDiscardDialog uses Gtk.Dialog` |
| 191 | `libadwaita (Adw) — Adw.MessageDialog` | `GTK4 — Gtk.Dialog` |
| 256 | `Implemented SaveDiscardDialog with Adw.MessageDialog` | `Implemented SaveDiscardDialog with Gtk.Dialog` |

## 8. New File to Create

### `slate/ui/toast.py` — SlateToast widget

A new file should be created containing the `SlateToast` class described in Section 4.5. This file should be placed at `slate/ui/toast.py` following the existing project structure (`slate/ui/` contains all UI components).

The class signature:

```python
class SlateToast:
    """In-app notification using pure GTK4.

    Uses Gtk.Overlay + Gtk.Revealer + GTK4's built-in
    'app-notification' CSS class. No custom CSS required.
    """

    def __init__(self, overlay: Gtk.Overlay) -> None: ...
    def show(self, message: str, duration: int = 3) -> None: ...
    def show_with_action(self, message: str, action_label: str,
                         callback, duration: int = 5) -> None: ...
    def dismiss(self) -> None: ...
```

## 9. Implementation Order

Execute in this order to maintain consistency at each step:

1. **Proposal** (this document) — already done
2. **Specs & docs** — update all 12 files listed in Section 7
3. **New file** — create `slate/ui/toast.py`
4. **Source code** — modify `app.py`, `main_window.py`, `theme_service.py`
5. **Install script** — modify `install-deps.sh`
6. **Tests** — modify `test_theme_service.py`
7. **Run tests** — verify everything passes

Rationale: specs first so any developer or AI agent reading the docs sees the correct target state. Code second to match specs. Tests last to verify.

## 10. What We Lose

| Capability | Impact | Mitigation |
|---|---|---|
| `Adw.Application` auto-loads Adwaita CSS theme | App won't auto-inherit Adwaita visual style | GTK4 system theme still applies. A small custom CSS file can add app-specific accents (already planned in spec). |
| `Adw.PreferencesWindow` | No built-in preferences layout | Build with `Gtk.Dialog` + `Gtk.Notebook` + `Gtk.ListBox`. More manual but fully functional. |
| `Adw.SpinRow` / `Adw.SwitchRow` / `Adw.ComboRow` | No ready-made preference rows | Build with `Gtk.Box` + `Gtk.ListBoxRow`. Slightly more code but identical UX. |
| `Adw.Toast` | No built-in toast widget | Build `SlateToast` with `Gtk.Overlay` + `Gtk.Revealer`. GTK4 provides `app-notification` CSS class. |
| `Adw.AlertDialog` (libadwaita 1.5+) | No adaptive dialog | `Gtk.MessageDialog` works fine on all GTK4 versions. |
| Separate start/end title button control | Single boolean for both sides | `set_decoration_layout()` provides sufficient control. The current app only shows end buttons anyway. |

## 11. What We Gain

| Benefit | Details |
|---|---|
| **Broad compatibility** | Works on any system with GTK4 — no libadwaita version required |
| **No version chasing** | No more debugging Adwaita 1.2 vs 1.4 vs 1.6 incompatibilities |
| **Simpler dependency tree** | One fewer system package (`gir1.2-adw-1`) to install |
| **Ubuntu 22.04 floor** | GTK 4.6.9 — all chosen widgets available |
| **Smoother development** | No libadwaita API changes to track across versions |
| **Future-proof** | GTK4 is stable; libadwaita evolves faster and breaks more |

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Missing visual polish vs Adwaita | Medium | Low | A small CSS layer (already planned in spec) covers app-specific accents. System GTK theme handles the rest. |
| Toast implementation bugs | Low | Medium | Simple widget, fully tested pattern from GNOME community (Gaphor project). |
| Preferences dialog UX regression | Low | Low | `Gtk.Notebook` + `ListBox` is standard GTK4 pattern. Many apps use it. |
| GTK4 API deprecations in future | Very Low | Medium | All chosen widgets are core GTK4 — stable for the foreseeable future. |

## 13. Full File Change Summary

### Code Files (4 changes, 1 new)

| File | Action |
|---|---|
| `slate/ui/app.py` | Remove Adw imports, change base class |
| `slate/ui/main_window.py` | Remove Adw imports, change base class, fix HeaderBar, fix set_content → set_child |
| `slate/services/theme_service.py` | Simplify _detect_system_theme to Gtk.Settings only |
| `scripts/install-deps.sh` | Remove `gir1.2-adw-1` |
| `slate/ui/toast.py` | **NEW** — SlateToast widget |

### Test Files (1 change)

| File | Action |
|---|---|
| `tests/services/test_theme_service.py` | Rewrite Adw-mocking tests to use Gtk.Settings mocks |

### No Change Needed

| File | Reason |
|---|---|
| `slate/ui/dialogs/save_discard_dialog.py` | Already pure GTK4 |
| `slate/ui/editor/editor_view.py` | No Adw references |
| `slate/ui/editor/tab_bar.py` | No Adw references |
| `slate/ui/editor/tab_manager.py` | No Adw references |
| `pyproject.toml` | PyGObject covers GTK4 bindings |

### Documentation Files (12 changes)

| File | Adw References |
|---|---|
| `docs/slate-spec.md` | 29 |
| `_bmad-output/project-context.md` | 4 |
| `_bmad-output/planning-artifacts/architecture.md` | 1 |
| `_bmad-output/planning-artifacts/prd.md` | 1 |
| `_bmad-output/planning-artifacts/epics.md` | 3 |
| `_bmad-output/planning-artifacts/ux-design-specification.md` | 16 |
| `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-24.md` | 1 |
| `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-25.md` | 1 |
| `_bmad-output/implementation-artifacts/1-1-project-initialization-packaging.md` | 2 |
| `_bmad-output/implementation-artifacts/1-4-services-layer-configservice-themeservice.md` | 3 |
| `_bmad-output/implementation-artifacts/1-6-main-window-editor-view.md` | 5 |
| `_bmad-output/implementation-artifacts/1-7-tab-manager-save-discard-guard.md` | 8 |

**Total: 74 libadwaita references across 12 documentation files, 4 code files, 1 test file, 1 install script.**

---

*End of proposal.*
