"""E2E driver - reusable accessibility queries."""

from typing import Any

from dogtail.predicate import GenericPredicate


def find_application(root: Any, name: str = "Slate") -> Any:
    """Find application by accessible name.

    Args:
        root: The accessible root node.
        name: Application name to find.

    Returns:
        The application node.

    Raises:
        LookupError: If application not found.
    """
    app = root.findChild(GenericPredicate(name=name, roleName="application"))
    if not app:
        raise LookupError(f"Application '{name}' not found in accessibility tree")
    return app


def find_window(app: Any, name: str | None = None) -> Any:
    """Find main window/frame under application.

    Args:
        app: The application node.
        name: Optional window name to match.

    Returns:
        The window node.

    Raises:
        LookupError: If window not found.
    """
    try:
        if name:
            window = app.findChild(GenericPredicate(name=name, roleName="window"))
        else:
            window = app.findChild(GenericPredicate(roleName="window"))
    except Exception:
        window = None

    if not window:
        try:
            if name:
                window = app.findChild(GenericPredicate(name=name, roleName="frame"))
            else:
                window = app.findChild(GenericPredicate(roleName="frame"))
        except Exception:
            window = None

    if not window:
        raise LookupError(f"Window '{name}' not found")
    return window


def find_toolbar(window: Any) -> Any:
    """Find toolbar (HeaderBar) in window.

    Args:
        window: The window node.

    Returns:
        The toolbar node.

    Raises:
        LookupError: If toolbar not found.
    """
    toolbar = window.findChild(GenericPredicate(roleName="toolbar"))
    if toolbar:
        return toolbar
    raise LookupError("Toolbar (HeaderBar) not found")


def find_activity_bar(window: Any, name: str = "slate-activity-bar") -> Any:
    """Find activity bar by accessible name.

    Args:
        window: The window node.
        name: Activity bar accessible name.

    Returns:
        The activity bar node.

    Raises:
        LookupError: If activity bar not found.
    """
    bar = window.findChild(GenericPredicate(name=name))
    if not bar:
        raise LookupError(f"Activity bar '{name}' not found")
    return bar


def find_buttons(parent: Any, role: str = "push button") -> list[Any]:
    """Find all buttons of given role under parent.

    Args:
        parent: The parent node.
        role: The button role to find (default: push button).

    Returns:
        List of button nodes.
    """
    return parent.findChildren(GenericPredicate(roleName=role))


def find_button_by_name(parent: Any, name: str) -> Any:
    """Find button by accessible name.

    Args:
        parent: The parent node.
        name: Button name to find.

    Returns:
        The button node.

    Raises:
        LookupError: If button not found.
    """
    button = parent.findChild(GenericPredicate(name=name, roleName="push button"))
    if not button:
        raise LookupError(f"Button '{name}' not found")
    return button


def find_side_panel(window: Any, name: str = "slate-side-panel") -> Any:
    """Find side panel by accessible name.

    Args:
        window: The window node.
        name: Panel accessible name.

    Returns:
        The panel node.

    Raises:
        LookupError: If panel not found.
    """
    panel = window.findChild(GenericPredicate(name=name))
    if not panel:
        raise LookupError(f"Side panel '{name}' not found")
    return panel


def find_tab_bar(window: Any, name: str = "slate-tab-bar") -> Any:
    """Find tab bar by accessible name.

    Args:
        window: The window node.
        name: Tab bar accessible name.

    Returns:
        The tab bar node.

    Raises:
        LookupError: If tab bar not found.
    """
    tab_bar = window.findChild(GenericPredicate(name=name))
    if not tab_bar:
        raise LookupError(f"Tab bar '{name}' not found")
    return tab_bar


def find_editor_area(window: Any, name: str = "slate-editor-area") -> Any:
    """Find editor area by accessible name.

    Args:
        window: The window node.
        name: Editor area accessible name.

    Returns:
        The editor area node.

    Raises:
        LookupError: If editor area not found.
    """
    editor = window.findChild(GenericPredicate(name=name))
    if not editor:
        raise LookupError(f"Editor area '{name}' not found")
    return editor


def find_by_role(parent: Any, role: str) -> Any:
    """Find first child node by role.

    Args:
        parent: The parent node.
        role: The role to find.

    Returns:
        The node.

    Raises:
        LookupError: If no node with given role found.
    """
    node = parent.findChild(GenericPredicate(roleName=role))
    if not node:
        raise LookupError(f"Node with role '{role}' not found")
    return node
