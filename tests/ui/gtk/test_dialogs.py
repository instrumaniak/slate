import pytest
from gi.repository import Gtk


@pytest.mark.timeout(30)
def test_save_discard_dialog_can_be_created(gtk_app_activated):
    """Save discard dialog should be creatable."""
    from slate.ui.dialogs.save_discard_dialog import SaveDiscardDialog

    window = gtk_app_activated
    dialog = SaveDiscardDialog(window, "test.txt")

    assert dialog is not None


@pytest.mark.timeout(30)
def test_editor_area_exists(gtk_app_activated):
    """Editor area should exist in the paned layout."""
    window = gtk_app_activated

    paned = window.get_content().get_first_child()
    while paned and not isinstance(paned, Gtk.Paned):
        paned = paned.get_next_sibling()

    editor_area = paned.get_end_child()

    assert editor_area is not None
