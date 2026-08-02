"""Tests for the centralized GTK dependency check."""

from __future__ import annotations

import builtins
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from slate.services import environment_check


def _install_gi_modules(monkeypatch, *, init_check_result: bool = True) -> None:
    """Install fake gi/gi.repository modules into sys.modules via monkeypatch.

    The pass-path of ``check_environment`` must be testable without a real GTK
    installation, so we substitute lightweight stand-ins for the whole gi stack.
    ``monkeypatch`` guarantees the fake modules are removed after each test so
    they never leak into subsequent tests.
    """
    gi_module = ModuleType("gi")
    gi_module.require_version = MagicMock()
    gi_module.repository = ModuleType("gi.repository")
    for name in ("Gdk", "Gio", "GLib", "GObject", "Gtk", "Pango", "PangoCairo"):
        if name == "Gtk":
            gtk_mock = MagicMock()
            gtk_mock.init_check.return_value = init_check_result
            setattr(gi_module.repository, name, gtk_mock)
        else:
            setattr(gi_module.repository, name, MagicMock())
    monkeypatch.setitem(sys.modules, "gi", gi_module)
    monkeypatch.setitem(sys.modules, "gi.repository", gi_module.repository)
    monkeypatch.setitem(sys.modules, "cairo", ModuleType("cairo"))


class TestCheckEnvironmentSuccess:
    """The pass path - all dependencies present and a display exists."""

    def test_returns_none_when_everything_present(self, monkeypatch) -> None:
        """Should return None when all libraries import and a display exists."""
        _install_gi_modules(monkeypatch, init_check_result=True)

        assert environment_check.check_environment() is None


class TestCheckEnvironmentFailures:
    """Each failure path should print a message and exit with status 1."""

    def test_missing_gi_exits(self, monkeypatch) -> None:
        """A missing ``gi`` module should abort startup."""
        real_import = builtins.__import__

        def fake_import(name: str, *args, **kwargs):
            if name == "gi":
                raise ImportError("no module named gi")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(SystemExit) as exc_info:
            environment_check.check_environment()
        assert exc_info.value.code == 1

    def test_require_version_failure_exits(self, monkeypatch) -> None:
        """A missing GIR namespace (require_version ValueError) should abort."""
        _install_gi_modules(monkeypatch)
        gi_module = sys.modules["gi"]
        gi_module.require_version.side_effect = ValueError("Gtk 4.0 not available")

        with pytest.raises(SystemExit) as exc_info:
            environment_check.check_environment()
        assert exc_info.value.code == 1

    def test_repository_import_failure_exits(self, monkeypatch) -> None:
        """A missing introspection repository should abort."""
        _install_gi_modules(monkeypatch)
        real_import = builtins.__import__

        def fake_import(name: str, *args, **kwargs):
            if name == "gi.repository":
                raise ImportError("no introspection data")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(SystemExit) as exc_info:
            environment_check.check_environment()
        assert exc_info.value.code == 1

    def test_missing_cairo_exits(self, monkeypatch) -> None:
        """A missing cairo module should abort."""
        _install_gi_modules(monkeypatch)
        monkeypatch.delitem(sys.modules, "cairo", raising=False)
        real_import = builtins.__import__

        def fake_import(name: str, *args, **kwargs):
            if name == "cairo":
                raise ImportError("no module named cairo")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(SystemExit) as exc_info:
            environment_check.check_environment()
        assert exc_info.value.code == 1

    def test_no_display_exits(self, monkeypatch) -> None:
        """A missing display server should abort."""
        _install_gi_modules(monkeypatch, init_check_result=False)

        with pytest.raises(SystemExit) as exc_info:
            environment_check.check_environment()
        assert exc_info.value.code == 1


class TestMissingLibrary:
    """Direct tests of the error-reporting helper."""

    def test_prints_actionable_message_and_exits(self, capsys) -> None:
        """Should print the package name, install hint, and exit code 1."""
        with pytest.raises(SystemExit) as exc_info:
            environment_check._missing_library("python3-gi")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "python3-gi" in captured.err
        assert "sudo apt install" in captured.err
