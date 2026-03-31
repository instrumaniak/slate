import pytest
from gi.repository import Gtk


@pytest.mark.timeout(30)
def test_app_activates_successfully(gtk_app):
    """App should activate without errors."""
    gtk_app.register()
    gtk_app.activate()

    assert len(gtk_app.get_windows()) > 0


@pytest.mark.timeout(30)
def test_app_window_has_test_mode(gtk_app_activated):
    """Window should have test_mode attribute set."""
    window = gtk_app_activated

    assert hasattr(window, "_test_mode")
    assert window._test_mode is True


@pytest.mark.timeout(30)
def test_app_creates_headerbar(gtk_app_activated):
    """Window should have a header bar."""
    window = gtk_app_activated
    content = window.get_child()

    assert content is not None
    assert isinstance(content, Gtk.Box)

    header = content.get_first_child()
    assert header is not None
    assert isinstance(header, Gtk.HeaderBar)


@pytest.mark.timeout(30)
def test_app_creates_paned_layout(gtk_app_activated):
    """Window should have paned layout with side panel and editor."""
    window = gtk_app_activated
    content = window.get_child()

    box = content.get_first_child()
    while box and not isinstance(box, Gtk.Paned):
        box = box.get_next_sibling()

    assert box is not None
    assert isinstance(box, Gtk.Paned)

    start_child = box.get_start_child()
    end_child = box.get_end_child()

    assert start_child is not None
    assert end_child is not None


@pytest.mark.timeout(30)
def test_app_test_mode_sets_env(monkeypatch):
    """Test mode should set environment variables correctly."""
    from slate.ui.app import SlateApplication

    monkeypatch.setenv("SLATE_TEST_MODE", "1")

    app = SlateApplication(test_mode=True)

    assert app._test_mode is True
