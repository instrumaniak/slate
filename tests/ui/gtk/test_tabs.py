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


@pytest.mark.timeout(30)
def test_tab_bar_keeps_exactly_one_tab_selected(gtk_app_activated, pump_main_loop):
    """Selecting tabs must not leave multiple toggle buttons highlighted."""
    from slate.ui.editor.tab_bar import TabBar

    tab_bar = TabBar()
    tab_bar.add_tab("/tmp/one.py", "one.py")
    tab_bar.add_tab("/tmp/two.py", "two.py")
    tab_bar.add_tab("/tmp/three.py", "three.py")

    tab_bar.set_active("/tmp/one.py")
    tab_bar._tabs["/tmp/two.py"].set_active(True)
    pump_main_loop(0.05)

    active_buttons = [button for button in tab_bar._tabs.values() if button.get_active()]
    assert len(active_buttons) == 1
    assert tab_bar.get_active() == "/tmp/two.py"
    assert tab_bar._tabs["/tmp/two.py"].get_active() is True


@pytest.mark.timeout(30)
def test_tab_bar_programmatic_selection_clears_previous_button(gtk_app_activated):
    """Programmatic activation must use the same exclusive selection invariant."""
    from slate.ui.editor.tab_bar import TabBar

    tab_bar = TabBar()
    tab_bar.add_tab("/tmp/one.py", "one.py")
    tab_bar.add_tab("/tmp/two.py", "two.py")

    tab_bar.set_active("/tmp/one.py")
    tab_bar.set_active("/tmp/two.py")

    assert tab_bar._tabs["/tmp/one.py"].get_active() is False
    assert tab_bar._tabs["/tmp/two.py"].get_active() is True
