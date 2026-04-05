import pytest


@pytest.mark.timeout(30)
def test_tab_bar_exists(gtk_app_activated):
    """Tab bar should exist in the editor area."""
    window = gtk_app_activated
    assert window.has_tab_bar() is True


@pytest.mark.timeout(30)
def test_tab_manager_exists(gtk_app_activated, pump_main_loop):
    """Tab manager should exist and be functional."""
    window = gtk_app_activated
    pump_main_loop(0.1)

    tab_state = window.get_tab_state()
    assert isinstance(tab_state, dict)
    assert "paths" in tab_state
    assert "active" in tab_state
