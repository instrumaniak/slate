from __future__ import annotations

from unittest.mock import MagicMock


def test_app_main_handles_keyboard_interrupt(monkeypatch) -> None:
    """Ctrl+C should exit cleanly without a traceback."""
    from slate.ui import app as app_module

    fake_app = MagicMock()
    fake_app.run.side_effect = KeyboardInterrupt

    monkeypatch.setattr(app_module, "SlateApplication", lambda test_mode=False: fake_app)

    exit_code = app_module.main(test_mode=False)

    assert exit_code == 130
    fake_app.quit.assert_called_once_with()
