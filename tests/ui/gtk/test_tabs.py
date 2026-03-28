import pytest
from gi.repository import Gtk


@pytest.mark.timeout(30)
def test_tab_bar_exists(gtk_app_activated):
    """Tab bar should exist in the editor area."""
    window = gtk_app_activated
    content = window.get_content()

    paned = content.get_first_child()
    while paned and not isinstance(paned, Gtk.Paned):
        paned = paned.get_next_sibling()

    assert paned is not None

    editor_area = paned.get_end_child()
    assert editor_area is not None

    tab_bar = editor_area.get_first_child()
    assert tab_bar is not None


@pytest.mark.timeout(30)
def test_tab_manager_exists(gtk_app_activated, pump_main_loop):
    """Tab manager should exist and be functional."""
    window = gtk_app_activated
    pump_main_loop(0.1)

    tab_manager = window._tab_manager
    assert tab_manager is not None
    tabs = tab_manager.get_tabs()
    assert isinstance(tabs, dict)
