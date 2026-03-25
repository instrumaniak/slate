"""Tests for services module initialization and service registration."""

from __future__ import annotations

import pytest

from slate.services import ConfigService, ThemeService, get_config_service, get_theme_service


class TestServiceRegistration:
    """Test service registration and singleton pattern."""

    def test_get_config_service_returns_singleton(self):
        """get_config_service should return same instance on multiple calls."""
        service1 = get_config_service()
        service2 = get_config_service()

        assert service1 is service2
        assert isinstance(service1, ConfigService)

    def test_get_theme_service_returns_singleton(self):
        """get_theme_service should return same instance on multiple calls."""
        service1 = get_theme_service()
        service2 = get_theme_service()

        assert service1 is service2
        assert isinstance(service1, ThemeService)

    def test_theme_service_uses_config_service(self):
        """ThemeService singleton should use ConfigService singleton."""
        config_service = get_config_service()
        theme_service = get_theme_service()

        # Theme service should reference the same config service
        assert theme_service._config_service is config_service

    def test_services_are_exported(self):
        """All service classes should be exported from module."""
        from slate import services

        assert hasattr(services, "ConfigService")
        assert hasattr(services, "ThemeService")
        assert hasattr(services, "get_config_service")
        assert hasattr(services, "get_theme_service")


class TestServiceExports:
    """Test module exports."""

    def test_all_exports_defined(self):
        """__all__ should define exported names."""
        from slate.services import __all__

        assert "ConfigService" in __all__
        assert "ThemeService" in __all__
        assert "get_config_service" in __all__
        assert "get_theme_service" in __all__
