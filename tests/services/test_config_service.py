"""Tests for ConfigService - configuration persistence and management."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from slate.services.config_service import DEFAULT_CONFIG, ConfigService


class TestConfigServiceInitialization:
    """Test ConfigService initialization and default config creation."""

    def test_creates_config_dir_when_missing(self):
        """Config directory should be created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            assert config_path.parent.exists()
            assert config_path.exists()

    def test_creates_config_with_defaults_when_file_missing(self):
        """Missing config file should be created with DEFAULT_CONFIG values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            # Verify file was created
            assert config_path.exists()

            # Verify defaults are present
            for section, keys in DEFAULT_CONFIG.items():
                for key, expected_value in keys.items():
                    actual_value = service.get(section, key)
                    assert actual_value == expected_value, f"{section}.{key} mismatch"

    def test_loads_existing_config_without_overwriting(self):
        """Existing config file should be loaded without modification."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"

            # Create a config file with custom values
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""[editor]
font = CustomFont 20
tab_width = 8

[app]
color_mode = dark
""")

            service = ConfigService(config_path=str(config_path))

            # Verify custom values are preserved
            assert service.get("editor", "font") == "CustomFont 20"
            assert service.get("editor", "tab_width") == "8"
            assert service.get("app", "color_mode") == "dark"

    def test_merges_partial_config_with_defaults(self):
        """Partial config should be merged with defaults, not overwrite entirely."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"

            # Create a partial config
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("""[editor]
font = PartialFont 14
""")

            service = ConfigService(config_path=str(config_path))

            # Custom value preserved
            assert service.get("editor", "font") == "PartialFont 14"

            # Default values still present for missing keys
            assert service.get("editor", "tab_width") == DEFAULT_CONFIG["editor"]["tab_width"]
            assert service.get("app", "color_mode") == DEFAULT_CONFIG["app"]["color_mode"]

    def test_handles_corrupted_config_with_backup(self):
        """Should use defaults when config is corrupted and backup is also corrupted."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"

            # Create a corrupted config
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("[INVALID\n")  # Malformed INI

            # Service should initialize with defaults
            service = ConfigService(config_path=str(config_path))

            # Should have defaults, not crash
            assert service.get("editor", "font") == DEFAULT_CONFIG["editor"]["font"]

    def test_restores_from_valid_backup_when_primary_is_corrupted(self):
        """Corrupted primary config should restore from a valid backup when available."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            backup_path = config_path.with_suffix(".ini.backup")

            config_path.write_text("[INVALID\n")
            backup_path.write_text("[app]\ncolor_mode = dark\n")

            with patch("slate.services.config_service.shutil.copy2", side_effect=OSError("copy")):
                service = ConfigService(config_path=str(config_path))

            assert service.get("app", "color_mode") == "dark"

    def test_uses_home_fallback_when_path_home_fails(self, monkeypatch):
        """When Path.home fails, ConfigService should fall back to HOME or tempdir."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            monkeypatch.setenv("HOME", tmp_dir)
            with patch(
                "slate.services.config_service.Path.home", side_effect=RuntimeError("no home")
            ):
                service = ConfigService(config_path=None)

            expected = Path(tmp_dir) / ".config" / "slate" / "config.ini"
            assert service._config_path == expected


class TestConfigServiceGet:
    """Test ConfigService.get() method."""

    def test_returns_existing_value(self):
        """Should return value for existing section/key."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            assert service.get("editor", "font") == "Monospace 13"
            assert service.get("app", "color_mode") == "system"

    def test_returns_none_for_missing_key(self):
        """Should return None for non-existent key."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            assert service.get("editor", "nonexistent_key") is None

    def test_returns_none_for_missing_section(self):
        """Should return None for non-existent section."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            assert service.get("nonexistent_section", "key") is None


class TestConfigServiceSet:
    """Test ConfigService.set() method."""

    def test_sets_value_and_persists(self):
        """Setting a value should persist to disk immediately."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            service.set("editor", "font", "NewFont 16")

            # Verify in-memory value
            assert service.get("editor", "font") == "NewFont 16"

            # Verify persisted to disk by loading a new instance
            service2 = ConfigService(config_path=str(config_path))
            assert service2.get("editor", "font") == "NewFont 16"

    def test_creates_section_if_missing(self):
        """Setting value in new section should create the section."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            service.set("new_section", "key", "value")

            assert service.get("new_section", "key") == "value"

    def test_updates_existing_value(self):
        """Setting existing key should update the value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            # Set initial value
            service.set("editor", "font", "InitialFont")
            assert service.get("editor", "font") == "InitialFont"

            # Update value
            service.set("editor", "font", "UpdatedFont")
            assert service.get("editor", "font") == "UpdatedFont"

    def test_preserves_other_sections_on_update(self):
        """Updating one section should not affect other sections."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            # Update editor section
            service.set("editor", "font", "UpdatedFont")

            # Verify app section unchanged
            assert service.get("app", "color_mode") == DEFAULT_CONFIG["app"]["color_mode"]
            assert service.get("app", "window_width") == DEFAULT_CONFIG["app"]["window_width"]


class TestConfigServiceValidation:
    """Test ConfigService input validation."""

    def test_rejects_empty_section(self):
        """Should reject empty section name."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            with pytest.raises(ValueError, match="Section must be a non-empty string"):
                service.get("", "key")

    def test_rejects_invalid_section_characters(self):
        """Should reject section with invalid characters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            with pytest.raises(ValueError, match="Section contains invalid characters"):
                service.set("[invalid]", "key", "value")

            with pytest.raises(ValueError, match="Section contains invalid characters"):
                service.set("section\n", "key", "value")

    def test_rejects_empty_key(self):
        """Should reject empty key name."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            with pytest.raises(ValueError, match="Key must be a non-empty string"):
                service.get("editor", "")

    def test_rejects_invalid_key_characters(self):
        """Should reject key with invalid characters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            with pytest.raises(ValueError, match="Key contains invalid characters"):
                service.set("editor", "key=val", "value")

            with pytest.raises(ValueError, match="Key contains invalid characters"):
                service.set("editor", "key\n", "value")

    def test_rejects_none_value(self):
        """Should reject None as value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            # ConfigParser raises TypeError for None before our validation
            with pytest.raises((ValueError, TypeError)):
                service.set("editor", "font", None)  # type: ignore

    def test_rejects_invalid_value_characters(self):
        """Should reject value with newline characters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            with pytest.raises(ValueError, match="Value contains invalid characters"):
                service.set("editor", "font", "value\nwith\nnewlines")


class TestConfigServicePathValidation:
    """Test ConfigService path validation."""

    def test_rejects_path_traversal(self):
        """Should reject paths with traversal sequences."""
        # Use an absolute path that contains traversal
        with tempfile.TemporaryDirectory() as tmp_dir:
            import os

            traversal_path = os.path.join(tmp_dir, "..", "..", "etc", "passwd")
            # Should raise ValueError for invalid path (either not absolute or traversal)
            with pytest.raises(ValueError):
                ConfigService(config_path=traversal_path)

    def test_rejects_relative_path(self):
        """Should reject relative paths."""
        with pytest.raises(ValueError, match="must be absolute"):
            ConfigService(config_path="config.ini")

    def test_accepts_absolute_path(self):
        """Should accept absolute paths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            # Should not raise
            service = ConfigService(config_path=str(config_path))
            assert service._config_path == config_path


class TestConfigServiceGetAll:
    """Test ConfigService.get_all() method."""

    def test_returns_all_config_as_dict(self):
        """Should return all configuration as nested dict."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            all_config = service.get_all()

            # Should be dict of dicts
            assert isinstance(all_config, dict)
            assert "editor" in all_config
            assert "app" in all_config

            # Check some values
            assert all_config["editor"]["font"] == "Monospace 13"
            assert all_config["app"]["color_mode"] == "system"

    def test_includes_custom_values(self):
        """Should include any custom values that were set."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            service.set("custom_section", "custom_key", "custom_value")

            all_config = service.get_all()
            assert all_config["custom_section"]["custom_key"] == "custom_value"


class TestConfigServiceSaveFailures:
    """Test error handling while persisting config."""

    def test_save_permission_error_cleans_temp_file(self) -> None:
        """Permission errors during save should bubble up and leave no temp file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            config_path.write_text("[app]\ncolor_mode = system\n")
            service = ConfigService(config_path=str(config_path))

            temp_path = config_path.with_suffix(".ini.tmp")
            with patch(
                "slate.services.config_service.os.open", side_effect=PermissionError("denied")
            ):
                with pytest.raises(PermissionError):
                    service.set("app", "color_mode", "dark")

            assert not temp_path.exists()


class TestConfigServiceDefaults:
    """Test DEFAULT_CONFIG structure and values."""

    def test_default_config_has_all_required_sections(self):
        """DEFAULT_CONFIG should have editor, app, and plugin sections."""
        required_sections = {
            "editor",
            "app",
            "plugin.search",
            "plugin.source_control",
            "plugin.file_explorer",
        }
        assert required_sections.issubset(set(DEFAULT_CONFIG.keys()))

    def test_default_config_values_are_strings(self):
        """All DEFAULT_CONFIG values should be strings (for configparser)."""
        for section, keys in DEFAULT_CONFIG.items():
            for key, value in keys.items():
                assert isinstance(value, str), f"{section}.{key} must be string, got {type(value)}"

    def test_default_config_matches_prd_specification(self):
        """DEFAULT_CONFIG should match PRD specification exactly."""
        expected = {
            "editor": {
                "font": "Monospace 13",
                "tab_width": "4",
                "insert_spaces": "true",
                "show_line_numbers": "true",
                "highlight_current_line": "true",
                "word_wrap": "false",
                "auto_indent": "true",
                "theme_mode": "auto",
                "light_scheme": "Adwaita",
                "dark_scheme": "Adwaita-dark",
                "explicit_scheme": "Adwaita",
            },
            "app": {
                "color_mode": "system",
                "last_folder": "",
                "active_panel": "",
                "side_panel_width": "220",
                "side_panel_visible": "true",
                "window_width": "1200",
                "window_height": "800",
                "window_maximized": "false",
            },
            "plugin.search": {
                "include_hidden": "false",
                "last_glob_filter": "",
            },
            "plugin.source_control": {
                "auto_refresh": "true",
            },
            "plugin.file_explorer": {
                "show_hidden_files": "false",
            },
        }

        assert DEFAULT_CONFIG == expected


class TestConfigServiceEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_permission_error_gracefully(self):
        """Should handle file permission errors without crashing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            # Make file read-only
            config_path.chmod(0o444)

            try:
                # Attempt to write - may or may not raise depending on user permissions
                # (e.g., root user can still write to read-only files)
                service.set("editor", "font", "NewValue")
                # If we get here without exception, that's fine too (e.g., root user)
            except PermissionError:
                pass  # Expected behavior
            except OSError as e:
                if "Permission" in str(e):
                    pass  # Also acceptable
                else:
                    raise
            finally:
                # Restore permissions for cleanup
                config_path.chmod(0o644)

    def test_handles_empty_config_file(self):
        """Should handle empty config file gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("")

            service = ConfigService(config_path=str(config_path))

            # Should still provide defaults
            assert service.get("editor", "font") == DEFAULT_CONFIG["editor"]["font"]

    def test_zero_gtk_imports_at_module_level(self):
        """ConfigService module should have zero GTK imports at module level."""
        import inspect

        import slate.services.config_service as config_module

        source = inspect.getsource(config_module)
        lines = source.split("\n")
        gtk_imports = [
            line.strip()
            for line in lines
            if (
                line.strip().startswith("from gi")
                or line.strip().startswith("import gi")
                or "from gtk" in line.lower()
                or "import gtk" in line.lower()
            )
        ]
        assert len(gtk_imports) == 0, f"Found GTK import statements: {gtk_imports}"


class TestConfigServiceDefaultPath:
    """Test ConfigService default path behavior."""

    def test_uses_default_path_when_none_provided(self):
        """Should use ~/.config/slate/config.ini when no path provided."""
        expected_path = Path.home() / ".config" / "slate" / "config.ini"

        # Mock all file system operations to avoid creating real files
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_config_path = Path(tmp_dir) / "config.ini"

            # Patch the Path.home() to return our temp directory structure
            with patch.object(Path, "home", return_value=Path(tmp_dir)):
                service = ConfigService()

        # Verify the service initialized with expected default path structure
        assert service._config_path.name == "config.ini"
        assert service._config_path.parent.name == "slate"
        assert service._config_path.parent.parent.name == ".config"


class TestConfigServiceThreadSafety:
    """Test ConfigService thread safety."""

    def test_concurrent_reads_do_not_corrupt(self):
        """Concurrent reads should not corrupt data."""
        import threading

        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "config.ini"
            service = ConfigService(config_path=str(config_path))

            results = []

            def reader():
                for _ in range(100):
                    value = service.get("editor", "font")
                    results.append(value)

            threads = [threading.Thread(target=reader) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All reads should return the same valid value
            assert all(r == "Monospace 13" for r in results)
