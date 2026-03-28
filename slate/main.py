"""Main entry point for Slate."""

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

    print(f"Slate v{__version__}")
    return app_main()


if __name__ == "__main__":
    sys.exit(main())
