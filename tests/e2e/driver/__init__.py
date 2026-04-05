"""E2E driver layer for Slate."""

from tests.e2e.driver.actions import (
    activate_menu_item,
    click,
    close_window,
    double_click,
    enter_text,
    select_all,
    toggle_button,
)
from tests.e2e.driver.app import launch_slate_app, terminate_slate_app
from tests.e2e.driver.queries import (
    find_application,
    find_button_by_name,
    find_buttons,
    find_editor_area,
    find_side_panel,
    find_tab_bar,
    find_toolbar,
    find_window,
)

__all__ = [
    "launch_slate_app",
    "terminate_slate_app",
    "find_application",
    "find_button_by_name",
    "find_buttons",
    "find_editor_area",
    "find_side_panel",
    "find_tab_bar",
    "find_toolbar",
    "find_window",
    "click",
    "close_window",
    "double_click",
    "enter_text",
    "select_all",
    "toggle_button",
    "activate_menu_item",
]
