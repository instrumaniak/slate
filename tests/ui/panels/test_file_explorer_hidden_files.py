"""Tests for hidden files toggle functionality in FileExplorerTree."""

from __future__ import annotations

import os
import tempfile
from typing import Any
from unittest.mock import MagicMock

import pytest

from slate.core.event_bus import EventBus
from slate.services.config_service import ConfigService


@pytest.fixture
def temp_dir_with_hidden(tmp_path: Any) -> Any:
    """Create a temp directory with hidden files."""
    root = tmp_path / "project"
    root.mkdir()

    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('hello')")

    (root / ".env").write_text("SECRET=key")
    (root / ".gitignore").write_text("*.pyc")
    (root / ".hidden_dir").mkdir()
    (root / ".hidden_dir" / "secret.txt").write_text("hidden")

    (root / "visible.txt").write_text("visible")

    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("ref: refs/heads/main")

    return root


@pytest.fixture
def config_service(tmp_path: Any) -> ConfigService:
    """Create ConfigService with temp config."""
    config_path = tmp_path / "config.ini"
    return ConfigService(str(config_path))


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh EventBus instance."""
    bus = EventBus()
    bus._handlers.clear()
    return bus


@pytest.fixture
def mock_file_service() -> Any:
    """Create FileService using real filesystem."""
    from slate.services.file_service import FileService

    return FileService()


class TestHiddenFilesDefault:
    """Tests for hidden files filtering by default."""

    def test_hidden_files_not_shown_by_default(
        self, mock_file_service: Any, event_bus: EventBus, temp_dir_with_hidden: Any
    ) -> None:
        """Hidden files (dot-prefixed) should not be shown when toggle is off."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=None,
        )
        widget.load_folder(str(temp_dir_with_hidden))

        root_model = widget._tree_model.get_model()
        names = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names.append(item.name)

        assert ".env" not in names, ".env should be hidden by default"
        assert ".gitignore" not in names, ".gitignore should be hidden by default"
        assert ".hidden_dir" not in names, ".hidden_dir should be hidden by default"
        assert "visible.txt" in names, "visible files should be shown"
        assert "src" in names, "regular folders should be shown"

    def test_git_always_excluded_when_hidden_off(
        self, mock_file_service: Any, event_bus: EventBus, temp_dir_with_hidden: Any
    ) -> None:
        """.git must be excluded even when hidden files toggle is off."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=None,
        )
        widget.load_folder(str(temp_dir_with_hidden))

        root_model = widget._tree_model.get_model()
        names = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names.append(item.name)

        assert ".git" not in names, ".git must always be excluded"


class TestHiddenFilesToggle:
    """Tests for hidden files toggle functionality."""

    def test_hidden_files_shown_when_toggle_on(
        self, mock_file_service: Any, event_bus: EventBus, temp_dir_with_hidden: Any
    ) -> None:
        """Hidden files should be shown when toggle is on."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=None,
        )

        widget._show_hidden_files = True
        widget.load_folder(str(temp_dir_with_hidden))

        root_model = widget._tree_model.get_model()
        names = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names.append(item.name)

        assert ".env" in names, ".env should be shown when toggle is on"
        assert ".gitignore" in names, ".gitignore should be shown when toggle is on"
        assert ".hidden_dir" in names, ".hidden_dir should be shown when toggle is on"

    def test_git_always_excluded_when_hidden_on(
        self, mock_file_service: Any, event_bus: EventBus, temp_dir_with_hidden: Any
    ) -> None:
        """.git must be excluded even when hidden files toggle is on."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=None,
        )

        widget._show_hidden_files = True
        widget.load_folder(str(temp_dir_with_hidden))

        root_model = widget._tree_model.get_model()
        names = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names.append(item.name)

        assert ".git" not in names, ".git must always be excluded"


class TestTogglePersistence:
    """Tests for config persistence of hidden files toggle."""

    def test_config_service_has_default_hidden_files(self, config_service: ConfigService) -> None:
        """ConfigService should have default show_hidden_files=false."""
        value = config_service.get("plugin.file_explorer", "show_hidden_files")
        assert value == "false", "Default should be 'false'"

    def test_reads_config_on_init(
        self, mock_file_service: Any, event_bus: EventBus, config_service: ConfigService
    ) -> None:
        """FileExplorerTree should read config on initialization."""
        config_service.set("plugin.file_explorer", "show_hidden_files", "true")

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=config_service,
        )

        assert widget._show_hidden_files is True

    def test_persists_toggle_state(
        self, mock_file_service: Any, event_bus: EventBus, config_service: ConfigService
    ) -> None:
        """Toggle should persist state to config service."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=config_service,
        )

        widget.toggle_hidden_files()

        value = config_service.get("plugin.file_explorer", "show_hidden_files")
        assert value == "true", "Toggle should persist 'true'"

    def test_toggle_reloads_tree(
        self, mock_file_service: Any, event_bus: EventBus, temp_dir_with_hidden: Any
    ) -> None:
        """Toggling should reload the tree to reflect changes."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=None,
        )
        widget.load_folder(str(temp_dir_with_hidden))

        root_model = widget._tree_model.get_model()
        names_before = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names_before.append(item.name)

        assert ".env" not in names_before

        widget._show_hidden_files = True
        widget.load_folder(str(temp_dir_with_hidden))

        root_model = widget._tree_model.get_model()
        names_after = []
        for i in range(root_model.get_n_items()):
            item = root_model.get_item(i)
            names_after.append(item.name)

        assert ".env" in names_after, "Hidden files should appear after reload"


class TestInvalidConfig:
    """Tests for handling invalid config values."""

    def test_invalid_config_defaults_to_false(
        self, mock_file_service: Any, event_bus: EventBus, config_service: ConfigService
    ) -> None:
        """Invalid config value should default to False."""
        config_service.set("plugin.file_explorer", "show_hidden_files", "maybe")

        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=config_service,
        )

        assert widget._show_hidden_files is False, "Invalid value should default to False"

    def test_config_set_failure_logs_warning(
        self, mock_file_service: Any, event_bus: EventBus, config_service: ConfigService
    ) -> None:
        """Config set failure should log warning but not crash."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        widget = FileExplorerTree(
            file_service=mock_file_service,
            event_bus=event_bus,
            config_service=config_service,
        )

        widget._config_service = None
        widget.toggle_hidden_files()


class TestPermissionDenied:
    """Tests for graceful handling of permission errors."""

    def test_permission_denied_hidden_dir(
        self, mock_file_service: Any, event_bus: EventBus, tmp_path: Any
    ) -> None:
        """Should handle permission denied gracefully."""
        from slate.ui.panels.file_explorer_tree import FileExplorerTree

        root = tmp_path / "project"
        root.mkdir()

        hidden_dir = root / ".protected"
        hidden_dir.mkdir()
        (hidden_dir / "file.txt").write_text("content")

        try:
            hidden_dir.chmod(0o000)
        except Exception:
            pytest.skip("Cannot change permissions on this system")

        try:
            widget = FileExplorerTree(
                file_service=mock_file_service,
                event_bus=event_bus,
                config_service=None,
            )
            widget.load_folder(str(root))
        finally:
            try:
                hidden_dir.chmod(0o755)
            except Exception:
                pass
