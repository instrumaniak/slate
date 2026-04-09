"""Source Control plugin — registers the source control panel with the host application."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from slate.core.plugin_api import AbstractPlugin, ActivityBarItem, PluginContext

if TYPE_CHECKING:
    from slate.ui.panels.source_control_panel import SourceControlPanel

logger = logging.getLogger(__name__)


class SourceControlPlugin(AbstractPlugin):
    """Plugin that provides a source control panel for git status and branch management."""

    def __init__(self) -> None:
        super().__init__()
        self._panel_widget: SourceControlPanel | None = None
        self._panel_factory: Callable[[], SourceControlPanel] | None = None

    @property
    def plugin_id(self) -> str:
        return "source_control"

    def get_activity_bar_items(self) -> list[ActivityBarItem]:
        """Return activity bar item for the source control panel."""
        return [
            ActivityBarItem(
                plugin_id=self.plugin_id,
                icon_name="org.gnome.gitg-symbolic",
                title="Source Control",
                priority=10,
            )
        ]

    def activate(self, context: PluginContext) -> None:
        self._context = context
        self._git_service = context.get_service("git")
        if self._git_service is None:
            logger.error("Required 'git' service not found. SourceControlPlugin cannot activate.")
            return

        self._panel_factory = self._create_panel_factory()

        bridge = context.host_bridge

        # Register keyboard shortcut Ctrl+Shift+G
        bridge.register_action(
            plugin_id=self.plugin_id,
            action_id="focus_source_control",
            callback=self._focus_panel,
            shortcut="<Ctrl><Shift>G",
        )

    def _create_panel_factory(self) -> Callable[[], SourceControlPanel]:
        """Create factory function for the source control panel."""
        from slate.ui.panels.source_control_panel import SourceControlPanel

        def factory() -> SourceControlPanel:
            return SourceControlPanel(
                git_service=self._git_service,
                event_bus=self._context.event_bus,
                host_bridge=self._context.host_bridge,
            )

        return factory

    def get_panel_widget(self) -> SourceControlPanel:
        """Return the panel widget for display in the side panel. Lazy create on first access."""
        if self._panel_widget is None and self._panel_factory is not None:
            self._panel_widget = self._panel_factory()
        return self._panel_widget

    def _focus_panel(self) -> None:
        """Focus the source control panel."""
        if self._context and self._context.host_bridge:
            self._context.host_bridge.focus_panel(self.plugin_id)
