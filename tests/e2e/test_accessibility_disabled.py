"""E2E tests that work in headless CI environments.

These tests verify basic app startup and shutdown without requiring AT-SPI.
Tests that require full AT-SPI (dogtail-based) should be run in a full
desktop environment.
"""

import os
import subprocess
import time

import pytest


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_starts_without_atspi(require_display):
    """App should attempt to start in headless environment."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"
    env["GTK_A11Y"] = "none"

    if "DISPLAY" not in env:
        env["DISPLAY"] = os.environ.get("DISPLAY", ":99")

    proc = subprocess.Popen(
        ["python3", "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)

    poll_result = proc.poll()
    assert poll_result is None, f"App exited prematurely with code {poll_result}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.mark.timeout(30)
@pytest.mark.slow
@pytest.mark.e2e
def test_app_exits_cleanly_with_sigterm(require_display):
    """App should exit cleanly when terminated with SIGTERM."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"

    if "DISPLAY" not in env:
        env["DISPLAY"] = os.environ.get("DISPLAY", ":99")

    proc = subprocess.Popen(
        ["python3", "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)

    poll_result = proc.poll()
    assert poll_result is None, f"App exited prematurely with code {poll_result}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("App did not exit after SIGTERM")
