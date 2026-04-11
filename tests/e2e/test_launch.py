"""E2E tests for app launch."""

import pytest


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_launches_successfully(slate_app_subprocess):
    """App should launch without crashing."""
    proc = slate_app_subprocess
    assert proc.poll() is None


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_has_window(slate_accessible):
    """App should have a visible window in accessibility tree."""
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)
    assert window is not None


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_window_has_title(slate_accessible):
    """Window should have title 'Slate'."""
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)
    assert window.name == "Slate"


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_has_toolbar(slate_accessible):
    """Window should have an activity bar."""
    from tests.e2e.driver.queries import find_activity_bar, find_window

    window = find_window(slate_accessible)
    activity_bar = find_activity_bar(window)
    assert activity_bar is not None


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_toolbar_has_window_controls(slate_accessible):
    """Activity bar should expose at least one control button."""
    from tests.e2e.driver.queries import find_activity_bar, find_buttons, find_window

    window = find_window(slate_accessible)
    activity_bar = find_activity_bar(window)
    buttons = find_buttons(activity_bar)
    assert len(buttons) >= 1


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_exits_cleanly(slate_app_subprocess, slate_accessible):
    """App should exit when window is closed."""
    from tests.e2e.driver.actions import close_window
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)
    close_window(window)

    proc = slate_app_subprocess
    try:
        exit_code = proc.wait(timeout=10)
    except Exception:
        proc.terminate()
        exit_code = proc.wait(timeout=5)
    assert exit_code == 0
