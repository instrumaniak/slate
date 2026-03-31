"""Entry point for python -m slate."""

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with path attribute.
    """
    parser = argparse.ArgumentParser(
        prog="slate",
        description="A modern code editor",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="File or folder to open. Defaults to last opened folder.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser.parse_args()


def resolve_path(path_arg):
    """Resolve CLI path argument to absolute path.

    Args:
        path_arg: Path string from CLI or None.

    Returns:
        str | None: Resolved absolute path or None.
    """
    if not path_arg:
        return None

    path = os.path.expanduser(path_arg)

    try:
        if not os.path.exists(path):
            return None
        if os.path.islink(path) and not os.path.exists(path):
            logger.warning(f"Broken symlink: {path}")
            return None
    except PermissionError:
        logger.warning(f"Permission denied: {path}")
        return None

    return os.path.abspath(path)


def main():
    """Entry point for python -m slate."""
    args = parse_args()

    if len(sys.argv) > 2:
        logger.warning(f"Ignoring extra arguments: {sys.argv[2:]}")

    cli_path = resolve_path(args.path)

    from slate.ui.app import main as app_main

    if cli_path:
        os.environ["SLATE_CLI_PATH"] = cli_path

    return app_main()


if __name__ == "__main__":
    sys.exit(main())
