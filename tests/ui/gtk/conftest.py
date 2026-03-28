import os
import tempfile
import pytest
from gi.repository import GLib


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
def gtk_app(isolated_env, tmp_path):
    """Create and return SlateApplication instance with unique ID."""
    import uuid
    from slate.ui.app import SlateApplication

    app_id = f"com.slate.editor.test-{uuid.uuid4().hex[:8]}"
    app = SlateApplication(test_mode=True, app_id=app_id)
    return app


@pytest.fixture
def gtk_app_activated(gtk_app):
    """Activate app and return main window."""
    gtk_app.register()

    gtk_app.activate()

    context = GLib.MainContext.default()
    window = None
    for _ in range(100):
        while context.iteration(False):
            pass
        windows = gtk_app.get_windows()
        if windows:
            window = windows[0]
            break

    if window is None:
        pytest.fail(
            "Window did not appear within 1 second timeout. "
            "Check that app.activate() properly creates the window."
        )

    yield window

    for w in gtk_app.get_windows():
        try:
            w.close()
        except Exception as e:
            import sys

            print(f"Warning: window.close() raised: {e}", file=sys.stderr)

    try:
        gtk_app.quit()
    except Exception:
        pass


def wait_for(condition, timeout=1.0, interval=0.01):
    """Wait for condition to be true, return True if successful.

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
