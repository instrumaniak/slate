from __future__ import annotations

import logging
import os
import sys
import tempfile

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
        print("SLATE_READY", file=sys.stderr)
        sys.stderr.flush()
        return False

    def _on_activate(self, app: Gtk.Application) -> None:
        """Handle application activation."""
        from slate.services import get_config_service, get_file_service, get_theme_service
        from slate.ui.main_window import create_main_window

        self._config_service = get_config_service()
        self._theme_service = get_theme_service()
        self._file_service = get_file_service()

        self._theme_service.resolve_theme()

        cli_path = self._process_cli_args()

        self._main_window = create_main_window(
            app,
            self._config_service,
            self._theme_service,
            test_mode=self._test_mode,
        )

        if cli_path:
            self._main_window.open_file_on_startup(cli_path)

        self._main_window.present()

        if self._test_mode:
            from gi.repository import GLib

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

    return app.run(None)


if __name__ == "__main__":
    from slate.version import __version__

    print(f"Slate v{__version__}")
    sys.exit(main())
