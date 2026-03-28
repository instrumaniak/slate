import pytest
from gi.repository import Gtk


@pytest.mark.timeout(30)
def test_side_panel_exists(gtk_app_activated):
    """Side panel should exist in the paned layout."""
    window = gtk_app_activated
    content = window.get_content()

    paned = content.get_first_child()
    while paned and not isinstance(paned, Gtk.Paned):
        paned = paned.get_next_sibling()

    assert paned is not None

    side_panel = paned.get_start_child()
    assert side_panel is not None


@pytest.mark.timeout(30)
def test_side_panel_visible_by_default(gtk_app_activated):
    """Side panel should be visible by default."""
    window = gtk_app_activated
    content = window.get_content()

    paned = content.get_first_child()
    while paned and not isinstance(paned, Gtk.Paned):
        paned = paned.get_next_sibling()

    side_panel = paned.get_start_child()

    assert side_panel.get_visible() is True


@pytest.mark.timeout(30)
def test_panel_toggle_exists(gtk_app_activated):
    """Toggle panel action should exist."""
    window = gtk_app_activated

    action = window.lookup_action("window.toggle_panel")
    assert action is not None
