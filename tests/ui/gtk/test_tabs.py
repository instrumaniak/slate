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


@pytest.mark.timeout(30)
def test_tab_bar_has_fixed_context_menu_button(gtk_app_activated):
    """The overflow button is outside the horizontally scrolling tab strip."""
    from gi.repository import Gtk

    from slate.ui.editor.tab_bar import TabBar

    tab_bar = TabBar()

    assert isinstance(tab_bar._menu_button, Gtk.MenuButton)
    assert tab_bar._menu_button.get_icon_name() == "view-more-symbolic"
    assert tab_bar._menu_button.get_parent() is tab_bar
    assert tab_bar._scrolled.get_parent() is tab_bar


@pytest.mark.timeout(30)
def test_close_all_menu_action_emits_signal(gtk_app_activated):
    """The popover's action should emit the TabBar close-all signal."""
    from slate.ui.editor.tab_bar import TabBar

    tab_bar = TabBar()
    emitted = []
    tab_bar.connect("close-all-requested", lambda *_args: emitted.append(True))

    tab_bar._close_all_button.emit("clicked")

    assert emitted == [True]


@pytest.mark.timeout(30)
def test_tab_bar_scrolls_natural_tab_width_and_styles_only_active_tab(gtk_app_activated):
    """Long labels remain in the scrollable strip and active styling is exclusive."""
    from gi.repository import Gtk

    from slate.ui.editor.tab_bar import TabBar

    tab_bar = TabBar()
    long_path = "/tmp/this-is-a-very-long-filename-that-must-remain-scrollable.py"
    tab_bar.add_tab(long_path, long_path.rsplit("/", 1)[-1])
    tab_bar.add_tab("/tmp/short.py", "short.py")
    tab_bar.set_active(long_path)

    horizontal, vertical = tab_bar._scrolled.get_policy()
    assert horizontal == Gtk.PolicyType.AUTOMATIC
    assert vertical == Gtk.PolicyType.NEVER
    assert tab_bar._tab_labels[long_path].get_max_width_chars() == -1
    assert "active" in tab_bar._tabs[long_path].get_css_classes()
    assert "active" not in tab_bar._tabs["/tmp/short.py"].get_css_classes()
    assert "border-radius: 6px 6px 0 0;" in tab_bar._tab_css
    assert "border-bottom-left-radius" not in tab_bar._tab_css
    assert "border-bottom-right-radius" not in tab_bar._tab_css
