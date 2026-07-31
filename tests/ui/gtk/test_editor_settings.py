"""GTK API contract tests for editor font and indentation settings."""

from __future__ import annotations

import pytest


@pytest.mark.timeout(30)
def test_installed_gtksource_view_exposes_editor_settings_api() -> None:
    """The installed GtkSourceView version must expose the APIs we call."""
    from gi.repository import GtkSource

    assert hasattr(GtkSource.View, "set_tab_width")
    assert hasattr(GtkSource.View, "set_indent_width")
    assert hasattr(GtkSource.View, "set_insert_spaces_instead_of_tabs")
    assert not hasattr(GtkSource.View, "set_insert_spaces")
