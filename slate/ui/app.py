from __future__ import annotations

import logging
import os
import signal
import sys
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

try:
    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("GtkSource", "5")
    from gi.repository import Gio, Gtk

    GTK_AVAILABLE = True
except (ImportError, ValueError) as e:
    print(f"Missing required GTK components: {e}", file=sys.stderr)
    print("Install: python3-gi gir1.2-gtk-4.0 gir1.2-gtksource-5", file=sys.stderr)
    sys.exit(1)


class SlateApplication(Gtk.Application):
    """Main application class - composition root.

    All dependency injection wiring happens here.
    """

    def __init__(self, test_mode: bool = False, app_id: str = "com.slate.editor") -> None:
        """Initialize SlateApplication.

        Args:
            test_mode: If True, enable test mode with deterministic IDs and
                      isolated temp config directory.
            app_id: Application ID (defaults to com.slate.editor, use unique ID for testing).
        """
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

        self._test_mode = test_mode
        self._config_service = None
        self._theme_service = None
        self._file_service = None
        self._main_window = None
        self._ready_emitted = False

        if self._test_mode:
            self._setup_test_config()

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)

        self.connect("activate", self._on_activate)

    def _setup_test_config(self) -> None:
        """Use isolated temp config in test mode."""
        config_dir = os.environ.get("SLATE_TEST_CONFIG_DIR")
        if config_dir:
            if not os.path.isdir(config_dir):
                raise RuntimeError(f"SLATE_TEST_CONFIG_DIR not a directory: {config_dir}")
            if not os.access(config_dir, os.W_OK):
                raise RuntimeError(f"SLATE_TEST_CONFIG_DIR not writable: {config_dir}")
            os.environ["XDG_CONFIG_HOME"] = config_dir
        else:
            config_dir = tempfile.mkdtemp(prefix="slate-test-config-")
            os.environ["XDG_CONFIG_HOME"] = config_dir

    def _emit_ready_signal(self) -> bool:
        """Emit ready signal after main loop starts."""
        if self._ready_emitted:
            return False
        self._ready_emitted = True
        print("SLATE_READY", file=sys.stderr)
        sys.stderr.flush()
        return False

    def _on_activate(self, app: Gtk.Application) -> None:
        """Handle application activation."""
        if self._main_window is not None:
            self._main_window.present()
            if self._test_mode:
                self._emit_ready_signal()
            return

        from slate.services import get_config_service, get_file_service, get_theme_service
        from slate.ui.main_window import create_main_window

        # Step 1: Load config
        self._config_service = get_config_service()

        # Step 2: Resolve theme before window creation
        self._theme_service = get_theme_service()
        self._theme_service.resolve_theme()

        # Step 3: Create window FIRST (provides HostUIBridge for plugins)
        from slate.services import get_plugin_manager

        plugin_manager = get_plugin_manager()
        self._main_window = create_main_window(
            app,
            self._config_service,
            self._theme_service,
            plugin_manager,
            test_mode=self._test_mode,
        )
        if self._test_mode:
            self._emit_ready_signal()

        # Step 4: Activate plugins AFTER window exists (so PluginContext can use HostUIBridge)
        from slate.core.plugin_api import PluginContext

        class AppPluginContext(PluginContext):
            """Concrete PluginContext that provides access to app services."""

            def __init__(self, config_service, theme_service, host_bridge):
                self._config_service = config_service
                self._theme_service = theme_service
                self._host_bridge = host_bridge

            @property
            def plugin_id(self) -> str:
                return "app"

            def get_service(self, service_id: str) -> Any:
                if service_id == "file":
                    return get_file_service()
                if service_id == "git":
                    from slate.services import get_git_service

                    return get_git_service()
                if service_id == "config":
                    return self._config_service
                if service_id == "theme":
                    return self._theme_service
                return None

            def get_config(self, section: str, key: str) -> str:
                return self._config_service.get(section, key) or ""

            def set_config(self, section: str, key: str, value: str) -> None:
                self._config_service.set(section, key, value)

            def emit(self, event: Any) -> None:
                from slate.core.event_bus import EventBus

                EventBus().emit(event)

            @property
            def host_bridge(self):
                return self._host_bridge

            @property
            def event_bus(self):
                from slate.core.event_bus import EventBus

                return EventBus()

        context = AppPluginContext(self._config_service, self._theme_service, self._main_window)
        plugin_manager.context = context

        try:
            plugin_manager.activate_all()
            self._main_window._refresh_activity_bar()
        except Exception as e:
            logger.warning(f"Plugin activation failed: {e}")

        # Step 5: Restore previous state (last_folder)
        cli_path = os.environ.get("SLATE_CLI_PATH")
        is_folder = False
        if not cli_path:
            last_folder = self._config_service.get("app", "last_folder")
            if last_folder and os.path.isdir(last_folder):
                cli_path = last_folder
                is_folder = True
        elif os.path.isdir(cli_path):
            is_folder = True
        elif os.path.isfile(cli_path):
            is_folder = False

        # Step 6: Resolve CLI argument (path to file/folder)
        # Step 7: Present window (after all setup)
        if cli_path:
            self._main_window.open_file_on_startup(cli_path, is_folder=is_folder)

        self._main_window.present()

        if self._test_mode:
            from gi.repository import GLib

            self._emit_ready_signal()
            GLib.idle_add(self._emit_ready_signal)

    def _process_cli_args(self) -> str | None:
        """Process command line arguments.

        Returns:
            Path to open on startup, or None.
        """
        if len(sys.argv) > 1:
            path = sys.argv[1]
            import os

            if os.path.exists(path):
                return path
        return None

    def get_main_window(self):
        """Get the main window instance."""
        return self._main_window


def main(test_mode: bool = False) -> int:
    """Application entry point.

    Args:
        test_mode: If True, enable test mode with deterministic behavior.
    """
    if sys.version_info < (3, 10):
        print(
            f"Slate requires Python 3.10 or later. You are running Python "
            f"{sys.version_info.major}.{sys.version_info.minor}.",
            file=sys.stderr,
        )
        return 1

    test_mode = test_mode or os.environ.get("SLATE_TEST_MODE") == "1"

    app = SlateApplication(test_mode=test_mode)
    app.register(None)
    if test_mode:
        signal.signal(signal.SIGTERM, lambda *_: app.quit())
        app.activate()

    try:
        return app.run(None)
    except KeyboardInterrupt:
        app.quit()
        return 130


if __name__ == "__main__":
    from slate.version import __version__

    print(f"Slate v{__version__}")
    sys.exit(main())
