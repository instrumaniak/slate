"""Main entry point for Slate."""

import os
import sys

from slate.ui.app import main as app_main
from slate.version import __version__


def main() -> int:
    """Application entry point."""
    if sys.version_info < (3, 10):
        print(
            f"Slate requires Python 3.10 or later. You are running Python "
            f"{sys.version_info.major}.{sys.version_info.minor}.",
            file=sys.stderr,
        )
        return 1

    if len(sys.argv) > 1:
        path_arg = sys.argv[1]
        if path_arg not in ("-v", "--version"):
            cli_path = os.path.expanduser(path_arg)
            if os.path.exists(cli_path):
                os.environ["SLATE_CLI_PATH"] = os.path.abspath(cli_path)

    return app_main()


if __name__ == "__main__":
    print(f"Slate v{__version__}")
    sys.exit(main())
