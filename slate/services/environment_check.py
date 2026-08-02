"""Centralized runtime dependency check for Slate's GTK requirements.

Slate requires GTK4, GtkSource5, and several companion libraries to do anything
useful. This module verifies them all in exactly one place at startup so
individual modules do not need to repeat try/except import scaffolding.

Zero GTK imports at module level - all verification happens inside
:func:`check_environment` (lazy) to keep the services layer GTK-free.
"""

from __future__ import annotations

import sys

_INSTALL_HINT = (
    "Install them with: sudo apt install python3-gi gir1.2-gtk-4.0 "
    "gir1.2-gtksource-5 python3-gi-cairo"
)


def _missing_library(package: str) -> None:
    """Print an actionable error and exit with a non-zero status."""
    print(f"Slate requires the {package} package.", file=sys.stderr)
    print(_INSTALL_HINT, file=sys.stderr)
    sys.exit(1)


def check_environment() -> None:
    """Verify all required GTK libraries are importable and a display exists.

    Checks, in order:
    - python3-gi (the ``gi`` module)
    - GTK4 (``gi.require_version("Gtk", "4.0")``)
    - GtkSource5 (``gi.require_version("GtkSource", "5")``)
    - Gio, Gdk, Pango, PangoCairo, GLib, GObject repositories
    - cairo bindings (python3-gi-cairo)
    - a running display server (``Gtk.init_check()``)

    Exits with a non-zero status and an actionable message if any dependency is
    missing. Returns ``None`` when everything is present.
    """
    try:
        import gi
    except ImportError:
        _missing_library("python3-gi")

    try:
        gi.require_version("Gtk", "4.0")
    except (ValueError, AttributeError):
        _missing_library("GTK4 (gir1.2-gtk-4.0)")

    try:
        gi.require_version("Gdk", "4.0")
    except (ValueError, AttributeError):
        _missing_library("GDK4 (gir1.2-gdk-4.0)")

    try:
        gi.require_version("GtkSource", "5")
    except (ValueError, AttributeError):
        _missing_library("GtkSource5 (gir1.2-gtksource-5)")

    try:
        from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango, PangoCairo  # noqa: F401
    except (ImportError, ValueError):
        _missing_library("GTK/GDK/Pango introspection data")

    try:
        import cairo  # noqa: F401
    except ImportError:
        _missing_library("python3-gi-cairo")

    if not Gtk.init_check():
        _missing_library("a display server (run under X11/Wayland or xvfb-run)")
