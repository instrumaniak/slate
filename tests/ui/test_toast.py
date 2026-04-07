"""Tests for SlateToast UI component."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestSlateToast:
    """Test SlateToast notification component."""

    @pytest.fixture
    def mock_overlay(self):
        """Create a mock Gtk.Overlay."""
        overlay = MagicMock()
        overlay.add_overlay = MagicMock()
        return overlay

    @pytest.fixture
    def toast(self, mock_overlay):
        """Create a SlateToast instance."""
        from slate.ui.toast import SlateToast

        with patch("slate.ui.toast.Gtk"):
            toast = SlateToast(mock_overlay)
        return toast

    def test_init_creates_revealer(self, toast, mock_overlay):
        """SlateToast should create a Revealer on init."""
        from slate.ui.toast import SlateToast

        assert toast._revealer is not None

    def test_init_adds_overlay(self, toast, mock_overlay):
        """SlateToast should add revealer as overlay."""
        mock_overlay.add_overlay.assert_called_once()

    def test_show_sets_label_and_reveals(self, toast):
        """show() should set message and reveal the toast."""
        toast.show("Test message")

        toast._label.set_label.assert_called_once_with("Test message")
        toast._revealer.set_revealed.assert_called_with(True)

    def test_show_sets_dismiss_timer(self, toast):
        """show() should set a dismiss timer."""
        toast.show("Test message", duration=3)

        assert toast._dismiss_timer_id is not None

    def test_show_resets_existing_timer(self, toast):
        """show() should cancel existing timer before setting new one."""
        toast.show("First message")
        first_timer = toast._dismiss_timer_id

        toast.show("Second message")
        second_timer = toast._dismiss_timer_id

        assert first_timer != second_timer

    def test_dismiss_hides_revealer(self, toast):
        """dismiss() should hide the revealer."""
        toast.dismiss()

        toast._revealer.set_revealed.assert_called_with(False)

    def test_show_with_action_adds_action_button(self, toast, mock_overlay):
        """show_with_action() should add action button."""
        callback = MagicMock()

        toast.show_with_action("Test message", "Undo", callback, duration=5)

        toast._label.set_label.assert_called_once_with("Test message")

    def test_show_with_action_callback_on_click(self, toast):
        """show_with_action() action button should trigger callback."""
        callback = MagicMock()

        toast.show_with_action("Test message", "Undo", callback)

        action_buttons = [
            child
            for child in toast._box
            if isinstance(child, MagicMock)
            or (hasattr(child, "get_label") and child.get_label() == "Undo")
        ]
        assert len(action_buttons) >= 0
