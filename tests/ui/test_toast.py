from __future__ import annotations


def test_toast_uses_reveal_child_api(monkeypatch) -> None:
    """Toast should use GTK4's reveal-child API."""
    from slate.ui.toast import SlateToast

    class DummyRevealer:
        def __init__(self) -> None:
            self.reveal_child = None

        def set_halign(self, _value) -> None:
            pass

        def set_valign(self, _value) -> None:
            pass

        def set_margin_top(self, _value) -> None:
            pass

        def set_transition_type(self, _value) -> None:
            pass

        def set_child(self, _child) -> None:
            pass

        def set_reveal_child(self, value: bool) -> None:
            self.reveal_child = value

    class DummyBox:
        def __init__(self, *args, **kwargs) -> None:
            self.children = []

        def add_css_class(self, _name: str) -> None:
            pass

        def append(self, child) -> None:
            self.children.append(child)

        def insert_child_after(self, child, _sibling) -> None:
            self.children.append(child)

        def remove(self, child) -> None:
            self.children.remove(child)

        def __iter__(self):
            return iter(self.children)

    class DummyLabel:
        def set_label(self, _message: str) -> None:
            pass

    class DummyButton:
        @classmethod
        def new_from_icon_name(cls, _name: str):
            return cls()

        def add_css_class(self, _name: str) -> None:
            pass

        def connect(self, _signal: str, _callback) -> None:
            pass

    class DummyOverlay:
        def add_overlay(self, _widget) -> None:
            pass

    monkeypatch.setattr("slate.ui.toast.Gtk.Revealer", DummyRevealer)
    monkeypatch.setattr("slate.ui.toast.Gtk.Box", DummyBox)
    monkeypatch.setattr("slate.ui.toast.Gtk.Label", DummyLabel)
    monkeypatch.setattr("slate.ui.toast.Gtk.Button", DummyButton)
    monkeypatch.setattr("slate.ui.toast.Gtk.Overlay", DummyOverlay)
    monkeypatch.setattr("slate.ui.toast.GLib.timeout_add_seconds", lambda *_args: 1)

    toast = SlateToast(DummyOverlay())
    toast.show("hello", duration=1)

    assert toast._revealer.reveal_child is True


def test_toast_clears_dismiss_timer_after_timeout(monkeypatch) -> None:
    from slate.ui.toast import SlateToast

    remove_calls = []

    class DummyRevealer:
        def __init__(self) -> None:
            self.reveal_child = None

        def set_halign(self, _value) -> None:
            pass

        def set_valign(self, _value) -> None:
            pass

        def set_margin_top(self, _value) -> None:
            pass

        def set_transition_type(self, _value) -> None:
            pass

        def set_child(self, _child) -> None:
            pass

        def set_reveal_child(self, value: bool) -> None:
            self.reveal_child = value

    class DummyBox:
        def __init__(self, *args, **kwargs) -> None:
            self.children = []

        def add_css_class(self, _name: str) -> None:
            pass

        def append(self, child) -> None:
            self.children.append(child)

        def insert_child_after(self, child, _sibling) -> None:
            self.children.append(child)

        def remove(self, child) -> None:
            self.children.remove(child)

        def __iter__(self):
            return iter(self.children)

    class DummyLabel:
        def set_label(self, _message: str) -> None:
            pass

    class DummyButton:
        @classmethod
        def new_from_icon_name(cls, _name: str):
            return cls()

        def add_css_class(self, _name: str) -> None:
            pass

        def connect(self, _signal: str, _callback) -> None:
            pass

    class DummyOverlay:
        def add_overlay(self, _widget) -> None:
            pass

    monkeypatch.setattr("slate.ui.toast.Gtk.Revealer", DummyRevealer)
    monkeypatch.setattr("slate.ui.toast.Gtk.Box", DummyBox)
    monkeypatch.setattr("slate.ui.toast.Gtk.Label", DummyLabel)
    monkeypatch.setattr("slate.ui.toast.Gtk.Button", DummyButton)
    monkeypatch.setattr("slate.ui.toast.Gtk.Overlay", DummyOverlay)
    monkeypatch.setattr(
        "slate.ui.toast.GLib.timeout_add_seconds",
        lambda *_args: 504,
    )
    monkeypatch.setattr(
        "slate.ui.toast.GLib.source_remove",
        lambda source_id: remove_calls.append(source_id),
    )

    toast = SlateToast(DummyOverlay())
    toast.show("hello", duration=1)
    assert toast._dismiss_timer_id == 504

    toast._dismiss_timeout()

    assert toast._dismiss_timer_id is None
    assert remove_calls == []
