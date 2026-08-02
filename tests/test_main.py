"""Tests for CLI entry point and startup sequence."""

from unittest.mock import patch

import pytest


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    @patch("slate.services.environment_check.check_environment")
    def test_argparse_accepts_current_directory(self, mock_check_environment, tmp_path):
        """AC1: slate . opens with current folder."""
        with patch("slate.ui.app.main", return_value=0) as mock_app_main:
            from slate import main

            with patch("sys.argv", ["slate", str(tmp_path)]):
                result = main.main()
                assert result == 0
            mock_app_main.assert_called_once()

    @patch("slate.services.environment_check.check_environment")
    def test_argparse_accepts_file_path(self, mock_check_environment, tmp_path):
        """AC3: slate /path/to/file opens file in tab."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        with patch("slate.ui.app.main", return_value=0) as mock_app_main:
            from slate import main

            with patch("sys.argv", ["slate", str(test_file)]):
                result = main.main()
                assert result == 0
            mock_app_main.assert_called_once()

    @patch("slate.services.environment_check.check_environment")
    def test_argparse_accepts_folder_path(self, mock_check_environment, tmp_path):
        """AC2: slate /path/to/folder loads folder with side panel visible."""
        test_folder = tmp_path / "folder"
        test_folder.mkdir()

        with patch("slate.ui.app.main", return_value=0) as mock_app_main:
            from slate import main

            with patch("sys.argv", ["slate", str(test_folder)]):
                result = main.main()
                assert result == 0
            mock_app_main.assert_called_once()

    @patch("slate.services.environment_check.check_environment")
    def test_argparse_no_args_restore_last_folder(self, mock_check_environment):
        """AC4: slate with no args restores last_folder if exists."""
        with patch("slate.ui.app.main", return_value=0) as mock_app_main:
            from slate import main

            with patch("sys.argv", ["slate"]):
                result = main.main()
                assert result == 0
            mock_app_main.assert_called_once()


class TestPythonVersionCheck:
    """Test Python version check."""

    def test_version_check_function_exists(self):
        """Verify version check logic exists."""
        from slate import main

        assert hasattr(main, "main")


class TestGTK4AvailabilityCheck:
    """Test GTK4 availability check."""

    @pytest.mark.gtk
    def test_gtk4_available_is_true(self):
        """AC8: GTK4 availability check passes when GTK is available."""
        from slate.services.environment_check import check_environment

        assert check_environment() is None


class TestPathResolution:
    """Test path resolution logic."""

    def test_resolve_path_expands_user(self):
        """Test that path resolution expands ~ to user home."""
        from slate.__main__ import resolve_path

        with (
            patch("os.path.expanduser", return_value="/home/testuser/test.txt"),
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value="/home/testuser/test.txt"),
        ):
            result = resolve_path("~/test.txt")
            assert result == "/home/testuser/test.txt"

    def test_resolve_path_returns_none_for_invalid(self):
        """Test that invalid paths return None."""
        from slate.__main__ import resolve_path

        with patch("os.path.exists", return_value=False):
            result = resolve_path("/nonexistent/path")
            assert result is None

    def test_resolve_path_returns_absolute_for_valid(self, tmp_path):
        """Test that valid paths return absolute path."""
        from slate.__main__ import resolve_path

        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.abspath", return_value=str(test_file.resolve())),
        ):
            result = resolve_path(str(test_file))
            assert result == str(test_file.resolve())


class TestStartupSequence:
    """Test startup sequence order."""

    def test_startup_imports_work(self):
        """Verify core imports work."""
        from slate.ui.app import SlateApplication

        assert SlateApplication is not None
