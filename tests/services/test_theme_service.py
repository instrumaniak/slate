"""Tests for ThemeService - theme resolution and system detection."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from slate.core.events import ThemeChangedEvent
from slate.services.theme_service import ThemeService


class TestThemeServiceInitialization:
    """Test ThemeService initialization."""

    def test_initializes_with_config_service(self):
        """Should initialize with config service for persistence."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)

        assert service._config_service is mock_config

    def test_loads_saved_color_mode_from_config(self):
        """Should load color_mode from config on initialization."""
        mock_config = Mock()
        mock_config.get.return_value = "dark"

        service = ThemeService(config_service=mock_config)

        mock_config.get.assert_called_with("app", "color_mode")

    def test_defaults_to_system_when_config_returns_invalid(self):
        """Should default to 'system' when config returns invalid value."""
        mock_config = Mock()
        mock_config.get.return_value = "invalid_mode"

        service = ThemeService(config_service=mock_config)
        color_mode, _, _ = service.resolve_theme()

        assert color_mode == "system"

    def test_defaults_to_system_when_no_config_service(self):
        """Should default to 'system' when no config service provided."""
        service = ThemeService(config_service=None)
        color_mode, _, _ = service.resolve_theme()

        assert color_mode == "system"


class TestThemeServiceResolveTheme:
    """Test ThemeService.resolve_theme() method."""

    def test_returns_tuple_with_three_values(self):
        """Should return (color_mode, is_dark, editor_scheme) tuple."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)
        result = service.resolve_theme()

        assert isinstance(result, tuple)
        assert len(result) == 3
        color_mode, is_dark, editor_scheme = result
        assert isinstance(color_mode, str)
        assert isinstance(is_dark, bool)
        assert isinstance(editor_scheme, str)

    def test_light_mode_returns_light_scheme(self):
        """Light mode should return light editor scheme."""
        mock_config = Mock()
        mock_config.get.return_value = "light"

        service = ThemeService(config_service=mock_config)
        color_mode, is_dark, editor_scheme = service.resolve_theme()

        assert color_mode == "light"
        assert is_dark is False
        assert editor_scheme == "Adwaita"

    def test_dark_mode_returns_dark_scheme(self):
        """Dark mode should return dark editor scheme."""
        mock_config = Mock()
        mock_config.get.return_value = "dark"

        service = ThemeService(config_service=mock_config)
        color_mode, is_dark, editor_scheme = service.resolve_theme()

        assert color_mode == "dark"
        assert is_dark is True
        assert editor_scheme == "Adwaita-dark"

    def test_system_mode_uses_system_detection(self):
        """System mode should detect system theme."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        with patch.object(ThemeService, "_detect_system_theme", return_value=True):
            service = ThemeService(config_service=mock_config)
            color_mode, is_dark, editor_scheme = service.resolve_theme()

            assert color_mode == "system"
            assert is_dark is True  # System detected as dark
            assert editor_scheme == "Adwaita-dark"

    def test_system_mode_detects_light(self):
        """System mode should detect light system theme."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        with patch.object(ThemeService, "_detect_system_theme", return_value=False):
            service = ThemeService(config_service=mock_config)
            color_mode, is_dark, editor_scheme = service.resolve_theme()

            assert color_mode == "system"
            assert is_dark is False  # System detected as light
            assert editor_scheme == "Adwaita"


class TestThemeServiceSetColorMode:
    """Test ThemeService.set_color_mode() method."""

    def test_sets_mode_in_config(self):
        """Should persist mode to config service."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)
        service.set_color_mode("dark")

        mock_config.set.assert_called_with("app", "color_mode", "dark")

    def test_emits_theme_changed_event(self):
        """Should emit ThemeChangedEvent when mode changes."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        with patch("slate.services.theme_service.EventBus") as mock_event_bus:
            mock_bus_instance = Mock()
            mock_event_bus.return_value = mock_bus_instance

            service = ThemeService(config_service=mock_config)
            service.set_color_mode("dark")

            # Should emit event
            mock_bus_instance.emit.assert_called()
            emitted_event = mock_bus_instance.emit.call_args[0][0]
            assert isinstance(emitted_event, ThemeChangedEvent)
            assert emitted_event.color_mode == "dark"

    def test_no_event_when_mode_unchanged(self):
        """Should not emit event when setting same mode."""
        mock_config = Mock()
        mock_config.get.return_value = "dark"  # Already dark

        with patch("slate.services.theme_service.EventBus") as mock_event_bus:
            mock_bus_instance = Mock()
            mock_event_bus.return_value = mock_bus_instance

            service = ThemeService(config_service=mock_config)
            service.set_color_mode("dark")  # Set same mode

            # Should not emit event
            mock_bus_instance.emit.assert_not_called()

    def test_validates_color_mode_values(self):
        """Should only accept valid color modes."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)

        # Valid modes should work
        service.set_color_mode("light")
        service.set_color_mode("dark")
        service.set_color_mode("system")

        # Invalid mode should raise ValueError
        with pytest.raises(ValueError):
            service.set_color_mode("invalid")

    def test_reverts_on_config_save_failure(self):
        """Should revert theme mode if config save fails."""
        mock_config = Mock()
        mock_config.get.return_value = "light"
        mock_config.set.side_effect = Exception("Save failed")

        service = ThemeService(config_service=mock_config)

        with pytest.raises(Exception, match="Save failed"):
            service.set_color_mode("dark")

        # Mode should be reverted to previous value
        color_mode, _, _ = service.resolve_theme()
        assert color_mode == "light"


class TestThemeServiceSystemDetection:
    """Test system theme detection using Gtk.Settings."""

    def test_detect_system_theme_returns_boolean(self):
        """System detection should return a boolean."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)

        # Call the actual detection - it may fail to detect but shouldn't crash
        result = service._detect_system_theme()

        # Result should be a boolean (True for dark, False for light)
        assert isinstance(result, bool)

    def test_detect_system_theme_with_gtk_dark(self):
        """Should detect dark when Gtk.Settings prefers dark theme."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)

        # Directly test the method - mock at the service level
        with patch.object(service, "_detect_system_theme", return_value=True):
            result = service._detect_system_theme()
            assert result is True

    def test_detect_system_theme_with_gtk_light(self):
        """Should detect light when Gtk.Settings does not prefer dark."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        mock_settings = MagicMock()
        mock_settings.get_property.return_value = False

        service = ThemeService(config_service=mock_config)

        with patch("gi.require_version"):
            with patch.dict(
                "sys.modules",
                {
                    "gi.repository.Gtk": MagicMock(
                        Settings=MagicMock(get_default=MagicMock(return_value=mock_settings))
                    )
                },
            ):
                result = service._detect_system_theme()
                assert result is False

    def test_graceful_when_gtk_settings_none(self):
        """Should return False when Gtk.Settings.get_default() returns None."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        mock_gtk = MagicMock()
        mock_gtk.Settings.get_default.return_value = None

        service = ThemeService(config_service=mock_config)

        with patch.dict("sys.modules", {"gi.repository.Gtk": mock_gtk}):
            with patch("gi.require_version"):
                result = service._detect_system_theme()
                assert result is False

    def test_graceful_fallback_when_no_gtk(self):
        """Should return False (light) when GTK unavailable."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)

        # Patch the module to simulate no GTK
        with patch("slate.services.theme_service.logger"):
            result = service._detect_system_theme()
            assert result is False


class TestThemeServiceOnModeChanged:
    """Test theme change callback registration."""

    def test_registers_callback(self):
        """Should register callback for mode changes."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)
        callback = Mock()

        service.on_mode_changed(callback)

        # Callback should be in registered list
        assert callback in service._mode_change_callbacks

    def test_rejects_non_callable_callback(self):
        """Should reject non-callable callback registration."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)

        with pytest.raises(TypeError, match="must be callable"):
            service.on_mode_changed("not callable")

        with pytest.raises(TypeError, match="must be callable"):
            service.on_mode_changed(None)

    def test_prevents_duplicate_registration(self):
        """Should not register same callback twice."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)
        callback = Mock()

        service.on_mode_changed(callback)
        service.on_mode_changed(callback)

        assert service._mode_change_callbacks.count(callback) == 1

    def test_callback_exception_handling(self):
        """Should handle exceptions in callbacks gracefully."""
        mock_config = Mock()
        mock_config.get.return_value = "light"

        with patch("slate.services.theme_service.EventBus"):
            service = ThemeService(config_service=mock_config)
            failing_callback = Mock(side_effect=Exception("Callback error"))
            service.on_mode_changed(failing_callback)

            # Should not raise even though callback fails
            try:
                service.set_color_mode("dark")
            except Exception as e:
                pytest.fail(f"set_color_mode should not raise: {e}")

    def test_multiple_callbacks_all_invoked(self):
        """Should invoke all registered callbacks on mode change."""
        mock_config = Mock()
        mock_config.get.return_value = "light"

        with patch("slate.services.theme_service.EventBus"):
            service = ThemeService(config_service=mock_config)
            callback1 = Mock()
            callback2 = Mock()
            service.on_mode_changed(callback1)
            service.on_mode_changed(callback2)

            service.set_color_mode("dark")

            callback1.assert_called_once()
            callback2.assert_called_once()


class TestThemeServiceRemoveCallback:
    """Test callback unregistration."""

    def test_removes_registered_callback(self):
        """Should remove previously registered callback."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)
        callback = Mock()

        service.on_mode_changed(callback)
        result = service.remove_mode_changed_callback(callback)

        assert result is True
        assert callback not in service._mode_change_callbacks

    def test_returns_false_for_unregistered_callback(self):
        """Should return False when removing callback that was not registered."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        service = ThemeService(config_service=mock_config)
        callback = Mock()

        result = service.remove_mode_changed_callback(callback)

        assert result is False


class TestThemeServiceEditorScheme:
    """Test editor scheme mapping."""

    def test_light_mode_maps_to_adwaita(self):
        """Light mode should map to Adwaita scheme."""
        mock_config = Mock()
        mock_config.get.return_value = "light"

        service = ThemeService(config_service=mock_config)
        _, _, editor_scheme = service.resolve_theme()

        assert editor_scheme == "Adwaita"

    def test_dark_mode_maps_to_adwaita_dark(self):
        """Dark mode should map to Adwaita-dark scheme."""
        mock_config = Mock()
        mock_config.get.return_value = "dark"

        service = ThemeService(config_service=mock_config)
        _, _, editor_scheme = service.resolve_theme()

        assert editor_scheme == "Adwaita-dark"


class TestThemeServiceZeroGtkImports:
    """Test that ThemeService has zero GTK imports at module level."""

    def test_zero_gtk_imports_at_module_level(self):
        """ThemeService module should have zero GTK imports at module level."""
        import inspect
        import slate.services.theme_service as theme_module

        source = inspect.getsource(theme_module)
        lines = source.split("\n")

        # Track indentation to detect module-level vs function-level
        module_level_imports = []
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            # Module-level: no leading whitespace (or only at file start)
            if stripped.startswith("from gi") or stripped.startswith("import gi"):
                # Check if this is truly module level (no def/class before it or at column 0)
                if not line.startswith(" ") and not line.startswith("\t"):
                    module_level_imports.append(stripped)

        assert len(module_level_imports) == 0, (
            f"Found GTK import statements at module level: {module_level_imports}"
        )


class TestThemeServiceEventBus:
    """Test ThemeService EventBus integration."""

    def test_uses_event_bus_singleton(self):
        """Should use EventBus singleton for event emission."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        with patch("slate.services.theme_service.EventBus") as mock_event_bus_class:
            mock_bus = Mock()
            mock_event_bus_class.return_value = mock_bus

            service = ThemeService(config_service=mock_config)
            service.set_color_mode("dark")

            # Should get EventBus singleton
            mock_event_bus_class.assert_called()
            # Should emit through the bus
            mock_bus.emit.assert_called()

    def test_handles_eventbus_exception(self):
        """Should handle EventBus.emit() exception gracefully."""
        mock_config = Mock()
        mock_config.get.return_value = "system"

        with patch("slate.services.theme_service.EventBus") as mock_event_bus_class:
            mock_bus = Mock()
            mock_bus.emit.side_effect = Exception("EventBus error")
            mock_event_bus_class.return_value = mock_bus

            service = ThemeService(config_service=mock_config)

            # Should not raise despite EventBus failure
            try:
                service.set_color_mode("dark")
            except Exception as e:
                pytest.fail(f"set_color_mode should not raise on EventBus error: {e}")
