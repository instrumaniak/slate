from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class ErrorPlaceholder(Gtk.Box):
    """Centered error state for tabs that failed to open."""

    def __init__(self, title: str, details: str) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_spacing(12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)

        icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        icon.add_css_class("error-placeholder-icon")
        icon.set_pixel_size(48)

        heading = Gtk.Label(label=title)
        heading.add_css_class("error-placeholder-title")
        heading.set_wrap(True)
        heading.set_justify(Gtk.Justification.CENTER)

        body = Gtk.Label(label=details)
        body.add_css_class("error-placeholder-body")
        body.set_wrap(True)
        body.set_justify(Gtk.Justification.CENTER)

        self.append(icon)
        self.append(heading)
        self.append(body)
