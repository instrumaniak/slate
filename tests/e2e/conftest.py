import os
import subprocess
import sys
import time

import pytest


def _check_atspi_available():
    """Check if AT-SPI is available."""
    try:
        proc = subprocess.run(
            ["python3", "-c", "from dogtail.tree import root"],
            capture_output=True,
            timeout=5,
        )
        if proc.returncode != 0:
            return False
        return True
    except Exception:
        return False


def _check_dbus_session():
    """Check if running in a D-Bus session."""
    return os.environ.get("DBUS_SESSION_BUS_ADDRESS") is not None


def _check_display():
    """Check if DISPLAY is set."""
    return os.environ.get("DISPLAY") is not None


def _check_desktop_session():
    """Check if running under a real desktop session."""
    return bool(
        os.environ.get("XDG_CURRENT_DESKTOP")
        or os.environ.get("DESKTOP_SESSION")
        or os.environ.get("GNOME_DESKTOP_SESSION_ID")
    )


def _wait_for_ready(proc, timeout=10):
    """Poll stderr for SLATE_READY signal. Returns (ready, stderr_output)."""
    stderr_output = []
    start = time.time()
    while time.time() - start < timeout:
        import select

        if select.select([proc.stderr], [], [], 0.1)[0]:
            line = proc.stderr.readline()
            if line:
                decoded = line.decode("utf-8")
                stderr_output.append(decoded)
                if "SLATE_READY" in decoded:
                    return True, stderr_output

        if proc.poll() is not None:
            return False, stderr_output

    return False, stderr_output


@pytest.fixture(scope="session")
def xvfb_server():
    """Start Xvfb for headless testing."""
    yield


@pytest.fixture
def require_display():
    """Skip test if DISPLAY is not set."""
    if not _check_display():
        pytest.skip("DISPLAY not set - requires Xvfb or display server")


@pytest.fixture
def require_dbus():
    """Skip test if D-Bus session is not available."""
    if not _check_dbus_session():
        pytest.skip("D-Bus session not available - requires dbus-run-session")


@pytest.fixture
def require_atspi():
    """Skip test if AT-SPI is not available."""
    if not _check_atspi_available():
        pytest.skip("AT-SPI not available - requires desktop session with accessibility bus")
    if not _check_dbus_session():
        pytest.skip("D-Bus session required for AT-SPI")
    if not _check_desktop_session():
        pytest.skip("Desktop session not detected - AT-SPI tests require a real desktop")


@pytest.fixture
def slate_app_subprocess(require_display, require_dbus, require_atspi):
    """Launch Slate as subprocess for E2E testing."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"
    env.setdefault("GDK_BACKEND", "x11")

    if "DISPLAY" not in env:
        env["DISPLAY"] = ":99"

    proc = subprocess.Popen(
        [sys.executable, "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    ready, stderr_output = _wait_for_ready(proc, timeout=10)

    if not ready:
        if proc.poll() is not None:
            pytest.fail(f"Slate failed to start: {''.join(stderr_output)}")
        # Allow fallback readiness detection via AT-SPI in slate_accessible.

    time.sleep(0.5)
    proc._stderr_output = stderr_output  # type: ignore[attr-defined]

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture
def slate_accessible(slate_app_subprocess, require_atspi):
    """Get accessible root for Slate app."""
    try:
        from dogtail.predicate import GenericPredicate
        from dogtail.tree import root
    except ValueError as exc:
        pytest.skip(f"AT-SPI helper unavailable in this environment: {exc}")

    preferred_names = ["Slate", "slate", "com.slate.editor", "python3"]

    for _attempt in range(75):
        try:
            if hasattr(root, "refresh"):
                root.refresh()
            apps = root.findChildren(GenericPredicate(roleName="application"))
            for name in preferred_names:
                for app in apps:
                    if app.name == name:
                        return app
            # Fallback: find any application that owns a Slate frame/window.
            for app in apps:
                for child in getattr(app, "children", []):
                    if (
                        getattr(child, "roleName", None) in {"window", "frame"}
                        and child.name == "Slate"
                    ):
                        return app
        except Exception:
            pass
        time.sleep(0.2)

    try:
        apps = root.findChildren(GenericPredicate(roleName="application"))
        app_names = [app.name for app in apps]
        window_names = []
        for app in apps:
            for child in getattr(app, "children", []):
                if getattr(child, "roleName", None) in {"window", "frame"}:
                    window_names.append((app.name, child.name))
        print(f"AT-SPI applications: {app_names}")
        print(f"AT-SPI windows: {window_names}")
        print(
            f"Slate subprocess pid={slate_app_subprocess.pid} alive={slate_app_subprocess.poll() is None}"
        )
        stderr_output = getattr(slate_app_subprocess, "_stderr_output", [])
        if stderr_output:
            print(f"Slate stderr (last 5): {stderr_output[-5:]}")
    except Exception:
        pass

    pytest.fail(
        "Slate app not found in accessibility tree - AT-SPI may not be fully initialized. "
        "Run with: xvfb-run --auto-servernum dbus-run-session -- pytest tests/e2e/ -v"
    )
