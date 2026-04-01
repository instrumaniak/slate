# Proposal: E2E Testing Infrastructure for Slate

**Project:** Slate
**Author:** Raziur
**Date:** 2026-03-28
**Status:** Updated — Incorporates AR/ECH review feedback
**Priority:** High

---

## 1. Problem Statement

Slate currently has unit tests for core/ and services/ layers, but lacks automated testing for the GTK4 UI layer. Manual testing is time-consuming and error-prone. We need:

- Automated verification that the GTK4 UI works correctly
- Button clicks and UI interactions testable by AI agents
- Visual/state verification that implementation is correct
- Fast local development feedback loop
- Confidence that the app works in a real desktop session

## 2. Decision

**Adopt a hybrid testing strategy:**

1. **In-process GTK integration tests** (`tests/ui/gtk/`) — Fast, deterministic, same-process testing for UI flows
2. **Black-box E2E smoke tests** (`tests/e2e/`) — Launch real app in desktop session, verify via accessibility

**Quality hardening goals (must-haves):**

- UI/E2E tests must assert behavior (state change, events emitted, actions executed), not just widget presence
- Tests must not rely on private attributes or fragile widget tree shapes
- GTK tests must run under a predictable session (Xvfb + dbus-run-session for CI; real GNOME session for full AT-SPI)

**Tool choices (verified via web research, March 2026):**

| Layer | Tool | Rationale |
|-------|------|-----------|
| In-process | pytest + GLib main loop | Native GTK4, instant feedback |
| Black-box | dogtail (v2.0.1) | Pythonic API, AT-SPI, active development |
| Headless | xvfb-run | Ubuntu native, well-supported |
| Auto xvfb | pytest-xvfb | Handles Xvfb automatically |

Target: **Ubuntu 22.04** (GTK 4.6.9)

## 3. System Validation Results

| Component | Version | Status |
|-----------|---------|--------|
| dogtail | 2.0.1 | ✅ Active (November 2025), Python ≥3.9 |
| pytest-xvfb | 2.x | ✅ Active |
| xvfb | 21.1.4 | ✅ Ubuntu 22.04 default |
| AT-SPI | 2.x | ✅ GTK4 accessibility |

### GTK4 Accessibility Support

GTK4 provides accessibility through AT-SPI. Key widgets must expose accessible names/roles.

#### How to Set Accessible Names in GTK4

**Option 1: Via Python code (recommended for test mode)**
```python
from gi.repository import Gtk, GLib

# Set accessible label (becomes accessible name for dogtail)
def set_accessible_name(widget, name):
    accessible = widget.get_accessible()
    GLib.idle_add(lambda: gtk_accessible_update_property(
        accessible,
        Gtk.AccessibleProperty.LABEL,
        name
    ))
```

**Option 2: Via UI file (.ui)**
```xml
<object class="GtkWindow" id="main-window">
  <accessibility>
    <property name="label">slate-main-window</property>
  </accessibility>
</object>
```

**Option 3: Via `GtkAccessible` interface (for custom widgets)**
```python
# In custom widget class
def do_get_accessible(self):
    # Return custom accessible implementation with stable IDs
```

GTK4 standard controls have built-in accessibility. For dogtail to find widgets reliably, set explicit `label` properties or use UI file accessibility declarations.

| Widget | Accessible Role | Required |
|--------|-----------------|----------|
| Main Window | `GTK_ACCESSIBLE_ROLE_APPLICATION` | Yes |
| HeaderBar | `GTK_ACCESSIBLE_ROLE_TOOLBAR` | Yes |
| Buttons | `GTK_ACCESSIBLE_ROLE_BUTTON` | Yes |
| Tab Bar | `GTK_ACCESSIBLE_ROLE_TAB_LIST` | Yes |
| Editor | `GTK_ACCESSIBLE_ROLE_TEXT_BOX` | Yes |

## 4. Test Architecture

### 4.1 Three-Layer Testing Strategy

```
tests/
├── services/          # Existing — no GTK, unchanged
├── core/              # Existing — no GTK, unchanged
├── ui/
│   └── gtk/           # NEW — in-process GTK integration tests
│       ├── conftest.py       # Shared fixtures
│       ├── test_app.py        # App activation
│       ├── test_tabs.py       # Tab open/close
│       ├── test_dialogs.py   # Save/discard dialog
│       └── test_panel.py     # Side panel toggle
└── e2e/              # NEW — black-box smoke tests
    ├── conftest.py           # dogtail setup + session checks
    ├── driver/               # shared driver/query layer (extensibility)
    │   ├── app.py            # launch/teardown helpers
    │   ├── queries.py        # reusable accessibility queries
    │   └── actions.py        # reusable actions (prefer doActionNamed)
    ├── test_launch.py        # App launch
    └── test_smoke.py         # Basic UI interactions
```

### 4.2 Layer Responsibilities

| Layer | Scope | Display Required | Speed |
|-------|-------|-----------------|-------|
| services/ | Business logic | No | Fastest |
| core/ | Event bus, models | No | Fast |
| ui/gtk/ | UI state, flows | No (in-process) | Fast |
| e2e/ | Real session, accessibility | Yes | Medium |

### 4.3 When to Use Each Layer

**Use in-process `tests/ui/gtk/`:**
- Tab open/close flows
- Dirty tab close (save/discard/cancel)
- Side panel toggle and config persistence
- Window state changes
- Theme switching

**Use black-box `tests/e2e/`:**
- App launches successfully.
- Window appears in real desktop session.
- Accessibility tree is properly exposed.
- Menu and keyboard shortcuts work.
- App exits cleanly.

## 5. Test Seams (SLATE_TEST_MODE)

Add environment variable support for deterministic testing.

### 5.1 Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `SLATE_TEST_MODE=1` | Enable test mode | (off) |
| `SLATE_TEST_CONFIG_DIR` | Override config path | temp dir |
| `SLATE_TEST_STARTUP_PATH` | Startup file/folder | (none) |
| `SLATE_TEST_NO_SPLASH` | Skip splash screen | false |

### 5.2 Test Mode Behavior

When `SLATE_TEST_MODE=1`:

1. **Deterministic widget IDs** — Key widgets get stable `accessible-name`:
   - Main window: `slate-main-window`
   - Tab bar: `slate-tab-bar`
   - Side panel: `slate-side-panel`
   - Editor area: `slate-editor-area`

2. **Ready signal** — Log line `SLATE_READY` when UI fully built and widget construction complete (not just when `app.run()` starts)

3. **No randomization** — Seed random if used, disable animations

4. **Config isolation** — Use temp directory for config

**Additional test-mode guidance:**
- Prefer `doActionNamed("click")` when available on AT-SPI nodes, and fall back to coordinate click only if needed
- Provide stable accessible names for all elements needed by E2E flows

#### Error Handling in Test Mode

```python
def _setup_test_config(self):
    """Use isolated temp config in test mode."""
    config_dir = os.environ.get("SLATE_TEST_CONFIG_DIR")
    if config_dir:
        # Validate path exists and is writable
        if not os.path.isdir(config_dir):
            raise RuntimeError(f"SLATE_TEST_CONFIG_DIR not a directory: {config_dir}")
        if not os.access(config_dir, os.W_OK):
            raise RuntimeError(f"SLATE_TEST_CONFIG_DIR not writable: {config_dir}")
    else:
        # Create temp directory with error handling
        try:
            config_dir = tempfile.mkdtemp(prefix="slate-test-config-")
        except OSError as e:
            raise RuntimeError(f"Failed to create temp config dir: {e}")

### 5.3 Implementation in `slate/ui/app.py`

```python
import os
import sys

def main():
    """Application entry point."""
    test_mode = os.environ.get("SLATE_TEST_MODE") == "1"
    
    app = SlateApplication(test_mode=test_mode)
    
    app.run(sys.argv)
    
    # NOTE: SLATE_READY must be emitted AFTER window is fully constructed,
    # not here. Emit it in window.__init__ or via idle callback after show().
```

```python
class SlateApplication(Gtk.Application):
    def __init__(self, test_mode: bool = False) -> None:
        super().__init__(...)
        self._test_mode = test_mode
        if test_mode:
            self._setup_test_config()
    
    def _setup_test_config(self):
        """Use isolated temp config in test mode."""
        config_dir = os.environ.get("SLATE_TEST_CONFIG_DIR")
        if config_dir:
            # Validate path exists and is writable
            if not os.path.isdir(config_dir):
                raise RuntimeError(f"SLATE_TEST_CONFIG_DIR not a directory: {config_dir}")
            if not os.access(config_dir, os.W_OK):
                raise RuntimeError(f"SLATE_TEST_CONFIG_DIR not writable: {config_dir}")
        else:
            # Create temp directory with error handling
            import tempfile
            try:
                config_dir = tempfile.mkdtemp(prefix="slate-test-config-")
            except OSError as e:
                raise RuntimeError(f"Failed to create temp config dir: {e}")
    
    def do_activate(self):
        """Override to emit SLATE_READY after window is fully constructed."""
        window = SlateMainWindow(application=self)
        window.present()
        
        # Emit SLATE_READY after widget tree is fully built
        if self._test_mode:
            from gi.repository import GLib
            GLib.idle_add(self._emit_ready_signal)
    
    def _emit_ready_signal(self):
        """Emit ready signal after main loop starts."""
        print("SLATE_READY", file=sys.stderr)
        sys.stderr.flush()
        return False  # Don't call again
```

## 6. In-Process GTK Test Harness

### 6.1 Shared Fixtures (`tests/ui/gtk/conftest.py`)

```python
import os
import tempfile
import pytest
from gi.repository import Gtk, GLib

@pytest.fixture
def temp_home(tmp_path):
    """Create isolated temp home directory."""
    home = tmp_path / "home"
    home.mkdir()
    return home

@pytest.fixture
def temp_config(tmp_path):
    """Create isolated config directory."""
    config = tmp_path / "config"
    config.mkdir()
    return config

@pytest.fixture
def isolated_env(temp_home, temp_config, monkeypatch):
    """Set up isolated environment variables."""
    monkeypatch.setenv("HOME", str(temp_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config))
    monkeypatch.setenv("SLATE_TEST_MODE", "1")
    monkeypatch.setenv("SLATE_TEST_CONFIG_DIR", str(temp_config))
    return {"home": temp_home, "config": temp_config}

@pytest.fixture
def gtk_app(isolated_env):
    """Create and return SlateApplication instance."""
    from slate.ui.app import SlateApplication
    
    app = SlateApplication(test_mode=True)
    return app

@pytest.fixture
def gtk_app_activated(gtk_app):
    """Activate app and return main window."""
    gtk_app.register()
    
    # Activate to trigger window creation
    gtk_app.activate()
    
    # Pump main loop until window appears
    context = GLib.MainContext.default()
    window = None
    for _ in range(100):  # 1 second timeout
        while context.iteration(False):
            pass
        # Check for window
        windows = gtk_app.get_windows()
        if windows:
            window = windows[0]
            break
    
    # Handle timeout: window not created
    if window is None:
        pytest.fail("Window did not appear within 1 second timeout. "
                    "Check that app.activate() properly creates the window.")
    
    yield window
    
    # Cleanup with error handling
    for w in gtk_app.get_windows():
        try:
            w.close()
        except Exception as e:
            # Log but don't fail cleanup
            import sys
            print(f"Warning: window.close() raised: {e}", file=sys.stderr)

def wait_for(condition, timeout=1.0, interval=0.01):
    """
    Wait for condition to be true, return True if successful.
    
    NOTE: Caller MUST check return value. If False is returned,
    the condition was not met within the timeout period.
    """
    import time
    elapsed = 0
    while elapsed < timeout:
        if condition():
            return True
        time.sleep(interval)
        elapsed += interval
    return False

@pytest.fixture
def pump_main_loop():
    """Provide main loop pumping utility."""
    def pump(duration=0.1):
        context = GLib.MainContext.default()
        import time
        end = time.time() + duration
        while time.time() < end:
            context.iteration(False)
    return pump
```

### 6.2 Example In-Process Test

```python
# tests/ui/gtk/test_tabs.py
import pytest
from gi.repository import Gtk

def test_open_file_creates_tab(gtk_app_activated, pump_main_loop):
    """Opening a file should create a new tab."""
    window = gtk_app_activated
    assert window is not None
    
    # Get tab manager via PUBLIC API (not private _tab_manager)
    # Use Gtk.ApplicationWindow methods or window actions
    # Example: Find tab view via Gtk.Builder or action system
    tab_view = window.get_property("tab-view")  # Adjust per actual API
    
    # Initial state: verify via public API
    # assert tab_view.get_n_pages() == 0
    
    # Simulate opening a file (via actions)
    # Use window.lookup_action() or activate_action()
    action = window.lookup_action("open-file")
    if action:
        action.activate()
    
    pump_main_loop(0.5)
    
    # Should have one tab now - verify via public API
    # assert tab_view.get_n_pages() == 1
```

**NOTE:** Never use private attributes like `window._tab_manager`. Always use public API:
- `window.get_property()`
- `window.lookup_action()`
- `window.activate_action()`
- If public API is insufficient, request/add proper public methods

## 7. Black-Box E2E Smoke Tests

### 7.1 dogtail Setup (`tests/e2e/conftest.py`)

```python
import os
import subprocess
import time
import pytest
from dogtail.tree import root
from dogtail.predicates import GenericPredicate

@pytest.fixture(scope="session")
def xvfb_server():
    """Start Xvfb for headless testing."""
    # Use pytest-xvfb or manual xvfb-run
    # This is handled by pytest-xvfb plugin
    yield

def _wait_for_ready(proc, timeout=10):
    """Poll stderr for SLATE_READY signal. Returns (ready, stderr_output)."""
    stderr_output = []
    start = time.time()
    while time.time() - start < timeout:
        # Non-blocking read
        import select
        if select.select([proc.stderr], [], [], 0.1)[0]:
            line = proc.stderr.readline()
            if line:
                decoded = line.decode("utf-8")
                stderr_output.append(decoded)
                if "SLATE_READY" in decoded:
                    return True, stderr_output
        
        # Check if process died
        if proc.poll() is not None:
            return False, stderr_output
    
    return False, stderr_output

@pytest.fixture
def slate_app_subprocess():
    """Launch Slate as subprocess for E2E testing."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"
    
    # Use dynamic DISPLAY allocation to avoid conflicts
    # Let xvfb-run or system assign available display
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":99"  # fallback
    
    proc = subprocess.Popen(
        ["python", "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    
    # Wait for ready signal using polling, not sleep
    ready, stderr_output = _wait_for_ready(proc, timeout=10)
    
    if not ready:
        # Process may have crashed
        if proc.poll() is not None:
            pytest.fail(f"Slate failed to start: {''.join(stderr_output)}")
        else:
            pytest.fail(f"SLATE_READY not received within 10s. "
                        f"Stderr: {''.join(stderr_output)}")
    
    # Additional delay for accessibility tree to populate
    # Use polling instead of fixed sleep
    time.sleep(0.5)
    
    yield proc
    
    # Cleanup with SIGKILL fallback
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()  # SIGKILL fallback
        proc.wait()

@pytest.fixture
def slate_accessible(slate_app_subprocess):
    """Get accessible root for Slate app."""
    # Poll for accessibility tree instead of fixed sleep
    for attempt in range(10):
        try:
            app = root.findChild(
                GenericPredicate(name="Slate", roleName="application")
            )
            if app:
                return app
        except Exception as e:
            # Log but continue
            pass
        time.sleep(0.5)
    
    pytest.fail("Slate app not found in accessibility tree. "
                "Check: AT-SPI running, accessibility enabled in GTK, "
                "correct app name in predicate.")
```

### 7.2 Example E2E Test

```python
# tests/e2e/test_smoke.py
import pytest
from dogtail.tree import root
from dogtail.predicates import GenericPredicate

def test_app_launches_and_shows_window(slate_accessible):
    """App should launch and show main window."""
    # Find main window
    window = slate_accessible.findChild(
        GenericPredicate(roleName="window")
    )
    
    assert window is not None
    assert window.name == "Slate"

def test_headerbar_has_buttons(slate_accessible):
    """HeaderBar should have window control buttons."""
    # Find toolbar (HeaderBar)
    headerbar = slate_accessible.findChild(
        GenericPredicate(roleName="toolbar")
    )
    
    assert headerbar is not None
    
    # Find buttons (should have minimize, maximize, close)
    buttons = headerbar.findChildren(
        GenericPredicate(roleName="push button")
    )
    
    assert len(buttons) >= 3  # At least window controls

def test_tab_bar_exists(slate_accessible):
    """Tab bar should be accessible."""
    tab_bar = slate_accessible.findChild(
        GenericPredicate(name="slate-tab-bar")
    )
    
    assert tab_bar is not None

def test_side_panel_toggle(slate_accessible):
    """Side panel toggle should work."""
    # Find side panel toggle button
    toggle = slate_accessible.findChild(
        GenericPredicate(name="Toggle Side Panel")
    )
    
    # Click to toggle
    toggle.click()
    
    # Find side panel
    panel = slate_accessible.findChild(
        GenericPredicate(name="slate-side-panel")
    )
    
    # Should be visible after click
    assert panel.showing

def test_app_exits_cleanly(slate_accessible):
    """App should exit without hanging."""
    # Find and click close button via accessibility
    try:
        # Find window
        window = slate_accessible.findChild(
            GenericPredicate(roleName="window")
        )
        
        # Find close button (typically in headerbar/toolbar)
        headerbar = window.findChild(
            GenericPredicate(roleName="toolbar")
        )
        
        # Find close button by its accessible name or position
        # Common patterns: "Close", "window-close", or last button in headerbar
        close_button = None
        for btn in headerbar.findChildren(GenericPredicate(roleName="push button")):
            if btn.name and "close" in btn.name.lower():
                close_button = btn
                break
        
        if close_button is None:
            # Fallback: try to find by typical position (last button)
            buttons = headerbar.findChildren(GenericPredicate(roleName="push button"))
            close_button = buttons[-1] if buttons else None
        
        if close_button:
            # Prefer doActionNamed when present
            if "click" in close_button.actions:
                close_button.doActionNamed("click")
            else:
                close_button.click()
    except Exception as e:
        pytest.fail(f"Failed to close app via accessibility: {e}")
    
    # Wait for process to exit - call wait() on the actual subprocess object
    proc = slate_accessible  # This is the subprocess fixture
    # Note: The actual proc object comes from slate_app_subprocess fixture
    # This test should use the proc directly:
    # exit_code = proc.wait(timeout=5)
    # assert exit_code == 0
```

## 8. Dependencies

### 8.1 Python Packages

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
test-gtk = [
    "pytest>=7.0",
    "pytest-xvfb>=2.0",
    "pytest-timeout>=2.0",
]
test-e2e = [
    "dogtail>=2.0",
    "pytest-timeout>=2.0",
]
test = [
    "pytest>=7.0",
    "pytest-xvfb>=2.0",
    "pytest-timeout>=2.0",
    "pytest-xdist>=3.0",  # For parallel test execution
    "dogtail>=2.0",
]
```

**Note:** Add `@pytest.mark.timeout(30)` decorator to tests that may hang to prevent entire suite from blocking.

### 8.2 System Packages

Add to `scripts/install-deps.sh`:

```bash
# Testing dependencies
xvfb \
at-spi2-core \
python3-dogtail \
python3-pyatspi
```

Or via apt:
```bash
sudo apt install xvfb at-spi2-core python3-dogtail python3-pyatspi
```

## 9. Makefile Commands

Add to `Makefile`:

```makefile
.PHONY: test-unit test-gtk test-e2e test-all test test-parallel test-timeout

# Unit tests - no display required
test-unit:
	pytest tests/services/ tests/core/ -v

# GTK tests - requires display but can use xvfb-run
test-gtk:
	xvfb-run pytest tests/ui/gtk/ -v

# E2E tests - requires real desktop session
test-e2e:
	xvfb-run pytest tests/e2e/ -v

# All tests - use xvfb for all to ensure consistency
test-all:
	xvfb-run pytest tests/ -v

# Default: unit + gtk (fast feedback)
test: test-unit test-gtk

# Parallel execution (requires pytest-xdist)
test-parallel:
	xvfb-run pytest tests/ -n auto

# With timeout enforcement
test-timeout:
	xvfb-run pytest tests/ --timeout=30
```

## 10. Implementation Order

1. **Proposal** (this document) — done
2. **Code changes** — add SLATE_TEST_MODE to app.py with proper error handling
3. **Dependencies** — add dogtail, pytest-xvfb, pytest-timeout, pytest-xdist to pyproject.toml
4. **Install script** — add system packages
5. **Test structure** — create directories and conftest.py
6. **In-process tests** — write 3-5 GTK integration tests (use PUBLIC API only)
7. **E2E tests** — write 2-3 smoke tests with proper subprocess handling + driver layer
8. **Negative tests** — add AT-SPI disabled test
9. **CI setup** — add GitHub Actions workflow
10. **Verify** — run all tests locally with timeout enforcement

## 11. What We Gain

| Benefit | Details |
|---------|--------|
| **Automated UI testing** | No more manual button clicking to verify fixes |
| **Fast feedback loop** | In-process tests run in <1s |
| **AI-agent friendly** | dogtail API is readable; button clicks work |
| **Confidence** | E2E smoke proves app works in real session |
| **Regression prevention** | Catches UI bugs before release |
| **Developer experience** | `make test-gtk` for fast TDD |

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GTK main loop in tests | Medium | Medium | Use GLib.MainContext iteration pattern |
| Flaky accessibility IDs | Low | Medium | SLATE_TEST_MODE provides stable IDs |
| xvfb display issues | Low | Low | Use pytest-xvfb for automatic handling |
| dogtail API changes | Low | Low | dogtail 2.x is stable |
| Test isolation issues | Medium | Low | Each test uses temp config/home |
| Subprocess hangs | Medium | Medium | Use pytest-timeout + SIGKILL fallback |
| DISPLAY conflicts | Low | Low | Use dynamic allocation or pytest-xvfb |
| AT-SPI unavailable | Low | High | Add negative test + clear error messages |

### 12.1 Negative Test: AT-SPI Disabled

```python
# tests/e2e/test_accessibility_disabled.py
import os
import pytest

def test_app_fails_gracefully_when_atspi_unavailable():
    """App should handle missing AT-SPI gracefully."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"
    # Disable AT-SPI
    env["AT_SPI_BUS_ADDRESS"] = ""
    
    proc = subprocess.Popen(
        ["python", "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # App may start but E2E tests will fail with clear error
    # This helps debug accessibility issues
    proc.terminate()
    proc.wait()
```

### 12.2 CI Integration

Add to `.github/workflows/test.yml`:

```yaml
test:
  runs-on: ubuntu-22.04
  steps:
    - uses: actions/checkout@v4
    - name: Install system deps
      run: |
        sudo apt-get update
        sudo apt-get install -y xvfb at-spi2-core python3-dogtail
    - name: Run unit tests
      run: pytest tests/services/ tests/core/ -v
    - name: Run GTK tests
      run: xvfb-run -a pytest tests/ui/gtk/ -v --timeout=30
    - name: Run E2E tests
      run: xvfb-run -a pytest tests/e2e/ -v --timeout=60
    - name: Upload coverage
      uses: codecov/codecov-action@v4
```

Use `xvfb-run -a` to auto-assign available display number.

## 13. Test Quality Fixes (Required)

These fixes are mandatory to ensure the automated suite catches most regressions without manual verification.

### 13.1 Core Test Hygiene
- **Reset EventBus between tests** to avoid singleton leakage (add a fixture in `tests/conftest.py`).
- **Avoid private attributes in tests** (e.g., `_tab_manager`, `_tree_model`); add or use public APIs/actions instead.
- **Prefer behavior assertions** over widget-tree shape assertions (e.g., “action toggles panel visibility” vs “widget is Gtk.Paned”).

### 13.2 GTK/UI Test Stability
- **Run GTK tests under a known session**: use `xvfb-run --auto-servernum dbus-run-session -- pytest tests/ui/gtk/ -v` in CI.
- **Move `tests/ui/panels/` under GTK harness** or wrap them in a GTK app fixture to prevent segfaults.
- **Use main-loop pumping** for async GTK state changes rather than fixed sleeps.

### 13.3 E2E Reliability
- **Headless smoke tests**: only verify process lifecycle + `SLATE_READY` in CI.
- **Full AT-SPI tests**: run on a GNOME desktop runner (self-hosted) with accessibility enabled.
- **Driver layer required**: all E2E tests must use `tests/e2e/driver/*` helpers (queries/actions) for consistency and maintainability.

### 13.4 Acceptance Gates
- E2E tests must cover: app launch, window present, at least one action flow (e.g., toggle side panel), and graceful exit.
- UI tests must cover: tab open/close flow, save/discard dialog path, and panel toggle state changes.

## 14. Full File Change Summary

### New Files

| File | Purpose |
|------|---------|
| `tests/ui/gtk/__init__.py` | Package marker |
| `tests/ui/gtk/conftest.py` | Shared fixtures |
| `tests/ui/gtk/test_app.py` | App activation tests |
| `tests/ui/gtk/test_tabs.py` | Tab flow tests |
| `tests/ui/gtk/test_dialogs.py` | Dialog tests |
| `tests/ui/gtk/test_panel.py` | Panel toggle tests |
| `tests/e2e/__init__.py` | Package marker |
| `tests/e2e/conftest.py` | dogtail fixtures |
| `tests/e2e/driver/app.py` | E2E launch/teardown helpers |
| `tests/e2e/driver/queries.py` | Reusable accessibility queries |
| `tests/e2e/driver/actions.py` | Reusable accessibility actions |
| `tests/e2e/test_launch.py` | Launch tests |
| `tests/e2e/test_smoke.py` | Smoke tests |

### Modified Files

| File | Changes |
|------|---------|
| `slate/ui/app.py` | Add test_mode parameter, SLATE_READY signal |
| `pyproject.toml` | Add test-gtk, test-e2e dependencies |
| `scripts/install-deps.sh` | Add xvfb, at-spi2-core, dogtail |
| `Makefile` | Add test-unit, test-gtk, test-e2e, test-all targets |
| `tests/conftest.py` | Reset EventBus fixture |
| `tests/ui/panels/*` | Move under GTK harness or wrap with app fixture |

### No Changes Required

| File | Reason |
|------|--------|
| `tests/services/*` | Already working, no GTK |
| `tests/core/*` | Already working, no GTK |
| `slate/ui/main_window.py` | Works as-is |
| `slate/ui/editor/*` | Works as-is |

---

## 15. References

- dogtail: https://pypi.org/project/dogtail/
- pytest-xvfb: https://github.com/The-Compiler/pytest-xvfb
- GTK4 Accessibility: https://docs.gtk.org/gtk4/section-accessibility.html
- AT-SPI Python: https://gnome.pages.gitlab.gnome.org/at-spi2-core/devel-docs/atspi-python-stack.html
- Ubuntu accessibility: https://documentation.ubuntu.com/desktop/en/latest/explanation/accessibility-stack/
- Automation through Accessibility (GNOME): https://modehnal.github.io/

---

*End of proposal.*
