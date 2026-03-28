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
def test_app_handles_disabled_accessibility():
    """App should start and exit cleanly when accessibility is disabled."""
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

    time.sleep(3)

    poll_result = proc.poll()
    assert poll_result is None, f"App exited prematurely with code {poll_result}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("App did not exit after SIGTERM")


@pytest.mark.timeout(30)
def test_app_exits_cleanly():
    """App should exit cleanly when terminated."""
    env = os.environ.copy()
    env["SLATE_TEST_MODE"] = "1"
    env["GTK_A11Y"] = "test"
    if "DISPLAY" not in env:
        env["DISPLAY"] = os.environ.get("DISPLAY", ":99")

    proc = subprocess.Popen(
        ["python3", "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(3)

    poll_result = proc.poll()
    assert poll_result is None, f"App exited prematurely with code {poll_result}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        pytest.fail("App did not exit after SIGTERM")
