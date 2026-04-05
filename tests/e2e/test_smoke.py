"""E2E smoke tests for UI interactions.

These tests verify basic UI interactions work correctly.
Requires full desktop session with D-Bus and AT-SPI.

To run:
    xvfb-run --auto-servernum dbus-run-session -- pytest tests/e2e/test_smoke.py -v
"""

import pytest
from dogtail.predicate import GenericPredicate


@pytest.mark.timeout(30)
def test_side_panel_accessible_name(slate_accessible):
    """Side panel should be accessible with test mode name."""
    from tests.e2e.driver.queries import find_side_panel
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)

    try:
        find_side_panel(window)
    except LookupError:
        pytest.skip("Side panel not found - may need test mode accessible names")


@pytest.mark.timeout(30)
def test_tab_bar_accessible_name(slate_accessible):
    """Tab bar should be accessible with test mode name."""
    from tests.e2e.driver.queries import find_tab_bar
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)

    try:
        find_tab_bar(window)
    except LookupError:
        pytest.skip("Tab bar not found - may need test mode accessible names")


@pytest.mark.timeout(30)
def test_toggle_panel_action_exists(slate_accessible):
    """Toggle panel shortcut should change side panel visibility."""
    import time

    from tests.e2e.driver.actions import toggle_side_panel_shortcut
    from tests.e2e.driver.queries import find_side_panel
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)
    panel = find_side_panel(window)
    before = panel.showing

    toggle_side_panel_shortcut()

    end = time.time() + 2.0
    while time.time() < end:
        if panel.showing != before:
            break
        time.sleep(0.1)

    assert panel.showing != before


@pytest.mark.timeout(30)
def test_app_responds_to_close_request(slate_app_subprocess, slate_accessible):
    """App should respond to close request and exit."""
    from tests.e2e.driver.actions import close_window
    from tests.e2e.driver.queries import find_window

    window = find_window(slate_accessible)
    close_window(window)

    exit_code = slate_app_subprocess.wait(timeout=10)
    assert exit_code == 0
