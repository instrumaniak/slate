"""E2E driver - reusable accessibility actions."""

from typing import Any

from dogtail.predicate import GenericPredicate
from dogtail.rawinput import keyCombo
import subprocess


def click(node: Any) -> None:
    """Click a node using preferred method.

    Prefers doActionNamed("click") when available, falls back to click().

    Args:
        node: The node to click.
    """
    if hasattr(node, "actions") and node.actions and "click" in node.actions:
        node.doActionNamed("click")
    else:
        node.click()


def double_click(node: Any) -> None:
    """Double-click a node.

    Args:
        node: The node to double-click.
    """
    if hasattr(node, "actions") and node.actions and "double click" in node.actions:
        node.doActionNamed("double click")
    else:
        node.click()
        node.click()


def toggle_button(node: Any) -> None:
    """Toggle a toggle button.

    Args:
        node: The toggle button node.
    """
    click(node)


def activate_menu_item(node: Any) -> None:
    """Activate a menu item.

    Args:
        node: The menu item node.
    """
    if hasattr(node, "doActionNamed"):
        try:
            node.doActionNamed("click")
        except Exception:
            node.click()
    else:
        node.click()


def close_window(window: Any) -> None:
    """Close a window by finding and clicking the close button.

    Args:
        window: The window node to close.
    """
    from dogtail.predicate import GenericPredicate

    if hasattr(window, "actions") and window.actions and "close" in window.actions:
        try:
            window.doActionNamed("close")
            return
        except Exception:
            pass

    try:
        toolbar = window.findChild(GenericPredicate(roleName="toolbar"))
    except Exception:
        toolbar = None
    if not toolbar:
        # Fallback to system close shortcut when no toolbar is exposed.
        if hasattr(window, "actions") and window.actions and "activate" in window.actions:
            try:
                window.doActionNamed("activate")
            except Exception:
                pass
        try:
            subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "com.slate.editor",
                    "--object-path",
                    "/com/slate/editor",
                    "--method",
                    "org.gtk.Actions.Activate",
                    "quit",
                    "[]",
                    "{}",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        try:
            quit_btn = window.findChild(GenericPredicate(name="slate-quit-app", roleName="push button"))
        except Exception:
            quit_btn = None
        if not quit_btn:
            try:
                quit_btn = window.findChild(GenericPredicate(name="Quit", roleName="push button"))
            except Exception:
                quit_btn = None
        if quit_btn:
            click(quit_btn)
            return
        keyCombo("<Control>q")
        keyCombo("<Alt>F4")
        return

    close_button = None
    for btn in toolbar.findChildren(GenericPredicate(roleName="push button")):
        if btn.name and "close" in btn.name.lower():
            close_button = btn
            break

    if close_button is None:
        buttons = toolbar.findChildren(GenericPredicate(roleName="push button"))
        close_button = buttons[-1] if buttons else None

    if close_button:
        click(close_button)
    else:
        if hasattr(window, "actions") and window.actions and "activate" in window.actions:
            try:
                window.doActionNamed("activate")
            except Exception:
                pass
        try:
            subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "com.slate.editor",
                    "--object-path",
                    "/com/slate/editor",
                    "--method",
                    "org.gtk.Actions.Activate",
                    "quit",
                    "[]",
                    "{}",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        try:
            quit_btn = window.findChild(GenericPredicate(name="slate-quit-app", roleName="push button"))
        except Exception:
            quit_btn = None
        if not quit_btn:
            try:
                quit_btn = window.findChild(GenericPredicate(name="Quit", roleName="push button"))
            except Exception:
                quit_btn = None
        if quit_btn:
            click(quit_btn)
            return
        keyCombo("<Control>q")
        keyCombo("<Alt>F4")


def enter_text(entry: Any, text: str) -> None:
    """Enter text into a text entry field.

    Args:
        entry: The entry node.
        text: The text to enter.
    """
    entry.text = text


def select_all(text_area: Any) -> None:
    """Select all text in a text area.

    Args:
        text_area: The text area node.
    """
    if hasattr(text_area, "actions") and "select all" in text_area.actions:
        text_area.doActionNamed("select all")
    else:
        from dogtail.tree import root

        ctrl_a = root.findChild(GenericPredicate(name="Select All", roleName="menu item"))
        if ctrl_a:
            ctrl_a.click()


def toggle_side_panel_shortcut() -> None:
    """Trigger the toggle side panel shortcut (Ctrl+B)."""
    keyCombo("<Control>b")
