"""File Explorer plugin — registers the explorer panel with the host application."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from slate.core.plugin_api import AbstractPlugin, PluginContext, ActivityBarItem

if TYPE_CHECKING:
    from slate.ui.panels.file_explorer_tree import FileExplorerTree

logger = logging.getLogger(__name__)


class FileExplorerPlugin(AbstractPlugin):
    """Plugin that provides a file tree panel for browsing project files."""

    def __init__(self) -> None:
        super().__init__()
        self._panel_widget: FileExplorerTree | None = None
        self._panel_factory: Callable[[], FileExplorerTree] | None = None

    @property
    def plugin_id(self) -> str:
        return "file_explorer"

    def get_activity_bar_items(self) -> list[ActivityBarItem]:
        """Return activity bar item for the file explorer."""
        return [
            ActivityBarItem(
                plugin_id=self.plugin_id,
                icon_name="folder-symbolic",
                title="Explorer",
                priority=0,
            )
        ]

    def activate(self, context: PluginContext) -> None:
        self._context = context
        self._file_service = context.get_service("file")
        if self._file_service is None:
            logger.error("Required 'file' service not found. FileExplorerPlugin cannot activate.")
            return

        self._panel_factory = self._create_panel_factory()

        bridge = context.host_bridge

        bridge.register_action(
            plugin_id=self.plugin_id,
            action_id="explorer.focus",
            callback=self._focus_panel,
            shortcut="<Primary><Shift>O",
        )

    def _create_panel_factory(self) -> Callable[[], FileExplorerTree]:
        """Create factory for lazy widget instantiation."""
        file_service = self._file_service

        def create_widget() -> FileExplorerTree:
            from slate.core.event_bus import EventBus
            from slate.ui.panels.file_explorer_tree import FileExplorerTree

            return FileExplorerTree(
                file_service=file_service,
                event_bus=EventBus(),
            )

        return create_widget

    def get_panel_widget(self) -> FileExplorerTree:
        """Return the panel widget for display in the side panel. Lazy create on first access."""
        if self._panel_widget is None and self._panel_factory is not None:
            try:
                self._panel_widget = self._panel_factory()
            except Exception as e:
                logger.error(f"Failed to create panel widget: {e}")
        return self._panel_widget

    def _focus_panel(self) -> None:
        """Focus the file explorer panel via host bridge."""
        bridge = getattr(self._context, "host_bridge", None)
        if bridge and hasattr(bridge, "focus_panel"):
            bridge.focus_panel(self.plugin_id)
