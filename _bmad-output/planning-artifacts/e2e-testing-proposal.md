# Proposal: E2E Testing Infrastructure for Slate

**Project:** Slate
**Author:** Raziur
**Date:** 2026-03-28
**Status:** Draft — Ready for review
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
| dogtail | 2.0.1 | ✅ Active (Nov 2025), Python >=3.9 |
| pytest-xvfb | 2.x | ✅ Active |
| xvfb | 21.1.4 | ✅ Ubuntu 22.04 default |
| AT-SPI | 2.x | ✅ GTK4 accessibility |

### GTK4 Accessibility Support

GTK4 provides accessibility through AT-SPI. Key widgets must expose accessible names/roles:

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
    ├── conftest.py           # dogtail setup
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
- App launches successfully
- Window appears in real desktop session
- Accessibility tree is properly exposed
- Menu/keyboard shortcuts work
- App exits cleanly

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

2. **Ready signal** — Log line `SLATE_READY` when UI fully built

3. **No randomization** — Seed random if used, disable animations

4. **Config isolation** — Use temp directory for config

### 5.3 Implementation in `slate/ui/app.py`

```python
import os

def main():
    """Application entry point."""
    test_mode = os.environ.get("SLATE_TEST_MODE") == "1"
    
    app = SlateApplication(test_mode=test_mode)
    
    if test_mode:
        print("SLATE_READY", file=sys.stderr)
    
    app.run(sys.argv)
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
            # Use provided path
            pass
        else:
            # Create temp directory
            pass
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
    
    yield window
    
    # Cleanup
    for window in gtk_app.get_windows():
        window.close()

def wait_for(condition, timeout=1.0, interval=0.01):
    """Wait for condition to be true, return True if successful."""
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
    
    # Get tab manager from window
    tab_manager = window._tab_manager
    
    # Initial state: no tabs
    assert tab_manager.get_n_tabs() == 0
    
    # Simulate opening a file (via actions)
    # ... trigger file open action ...
    
    pump_main_loop(0.5)
    
    # Should have one tab now
    assert tab_manager.get_n_tabs() == 1
```

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

@pytest.fixture
def slate_app_subprocess():
    """Launch Slate as subprocess for E2E testing."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"
    env["DISPLAY"] = os.environ.get("DISPLAY", ":99")
    
    proc = subprocess.Popen(
        ["python", "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for ready signal
    stderr_output = []
    def read_stderr():
        while True:
            line = proc.stderr.readline()
            if not line:
                break
            decoded = line.decode("utf-8")
            stderr_output.append(decoded)
            if "SLATE_READY" in decoded:
                break
    
    # Give it time to start
    time.sleep(2)
    
    # Check if process is still running
    if proc.poll() is not None:
        pytest.fail(f"Slate failed to start: {''.join(stderr_output)}")
    
    yield proc
    
    # Cleanup
    proc.terminate()
    proc.wait(timeout=5)

@pytest.fixture
def slate_accessible(slate_app_subprocess):
    """Get accessible root for Slate app."""
    # Wait for app to appear in accessibility tree
    time.sleep(1)
    
    # Find Slate window
    for _ in range(10):
        try:
            app = root.findChild(
                GenericPredicate(name="Slate", roleName="application")
            )
            if app:
                return app
        except:
            pass
        time.sleep(0.5)
    
    pytest.fail("Slate app not found in accessibility tree")
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

def test_app_exits_cleanly(slate_app_subprocess):
    """App should exit without hanging."""
    # Close app via accessibility
    # ... find and click close button ...
    
    # Wait for process to exit
    exit_code = slate_app_subprocess.wait(timeout=5)
    
    assert exit_code == 0
```

## 8. Dependencies

### 8.1 Python Packages

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
test-gtk = [
    "pytest>=7.0",
    "pytest-xvfb>=2.0",
]
test-e2e = [
    "dogtail>=2.0",
]
test = [
    "pytest>=7.0",
    "pytest-xvfb>=2.0",
    "dogtail>=2.0",
]
```

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
.PHONY: test-unit test-gtk test-e2e test-all

test-unit:
	pytest tests/services/ tests/core/ -v

test-gtk:
	pytest tests/ui/gtk/ -v

test-e2e:
	xvfb-run pytest tests/e2e/ -v

test-all:
	pytest tests/ -v --ignore=tests/e2e/
	xvfb-run pytest tests/e2e/ -v

test: test-unit test-gtk
```

## 10. Implementation Order

1. **Proposal** (this document) — done
2. **Code changes** — add SLATE_TEST_MODE to app.py
3. **Dependencies** — add dogtail, pytest-xvfb to pyproject.toml
4. **Install script** — add system packages
5. **Test structure** — create directories and conftest.py
6. **In-process tests** — write 3-5 GTK integration tests
7. **E2E tests** — write 2-3 smoke tests
8. **Verify** — run all tests locally

## 11. What We Gain

| Benefit | Details |
|---------|--------|
| **Automated UI testing** | No more manual button clicking to verify fixes |
| **Fast feedback loop** | In-process tests run in <1s |
| **AI-agent friendly** | dogtail API is readable, button clicks work |
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

## 13. Full File Change Summary

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
| `tests/e2e/test_launch.py` | Launch tests |
| `tests/e2e/test_smoke.py` | Smoke tests |

### Modified Files

| File | Changes |
|------|---------|
| `slate/ui/app.py` | Add test_mode parameter, SLATE_READY signal |
| `pyproject.toml` | Add test-gtk, test-e2e dependencies |
| `scripts/install-deps.sh` | Add xvfb, at-spi2-core, dogtail |
| `Makefile` | Add test-unit, test-gtk, test-e2e, test-all targets |

### No Changes Required

| File | Reason |
|------|--------|
| `tests/services/*` | Already working, no GTK |
| `tests/core/*` | Already working, no GTK |
| `slate/ui/main_window.py` | Works as-is |
| `slate/ui/editor/*` | Works as-is |

---

## 14. References

- dogtail: https://pypi.org/project/dogtail/
- pytest-xvfb: https://github.com/The-Compiler/pytest-xvfb
- GTK4 Accessibility: https://docs.gtk.org/gtk4/section-accessibility.html
- AT-SPI Python: https://gnome.pages.gitlab.gnome.org/at-spi2-core/devel-docs/atspi-python-stack.html
- Ubuntu accessibility: https://documentation.ubuntu.com/desktop/en/latest/explanation/accessibility-stack/

---

*End of proposal.*
