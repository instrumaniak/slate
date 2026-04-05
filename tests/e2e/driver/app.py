"""E2E driver - application launch and teardown helpers."""

import os
import subprocess
import sys
import time


def launch_slate_app(
    test_mode: bool = True,
    display: str | None = None,
    timeout: int = 10,
    config_dir: str | None = None,
) -> tuple[subprocess.Popen, list[str]]:
    """Launch Slate application as subprocess.

    Args:
        test_mode: Enable test mode with deterministic behavior.
        display: DISPLAY to use (None for auto).
        timeout: Seconds to wait for SLATE_READY signal.
        config_dir: Optional config directory override.

    Returns:
        Tuple of (subprocess.Popen, stderr_output).

    Raises:
        RuntimeError: If app fails to start or SLATE_READY not received.
    """
    env = os.environ.copy()

    if test_mode:
        env["SLATE_TEST_MODE"] = "1"

    if config_dir:
        env["SLATE_TEST_CONFIG_DIR"] = config_dir

    if display:
        env["DISPLAY"] = display
    elif "DISPLAY" not in env:
        env["DISPLAY"] = ":99"

    proc = subprocess.Popen(
        [sys.executable, "-m", "slate"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    ready, stderr_output = _wait_for_ready(proc, timeout=timeout)

    if not ready:
        if proc.poll() is not None:
            raise RuntimeError(f"Slate failed to start: {''.join(stderr_output)}")
        else:
            raise RuntimeError(
                f"SLATE_READY not received within {timeout}s. Stderr: {''.join(stderr_output)}"
            )

    time.sleep(0.5)

    return proc, stderr_output


def _wait_for_ready(proc: subprocess.Popen, timeout: int = 10) -> tuple[bool, list[str]]:
    """Poll stderr for SLATE_READY signal.

    Args:
        proc: The subprocess to monitor.
        timeout: Maximum seconds to wait.

    Returns:
        Tuple of (ready, stderr_output).
    """
    stderr_output = []
    start = time.time()

    while time.time() - start < timeout:
        import select

        if select.select([proc.stderr], [], [], 0.1)[0]:
            line = proc.stderr.readline()
            if line:
                decoded = line.decode("utf-8")
                stderr_output.append(decoded)
                if "SLATE_READY" in decoded:
                    return True, stderr_output

        if proc.poll() is not None:
            return False, stderr_output

    return False, stderr_output


def terminate_slate_app(proc: subprocess.Popen, timeout: int = 5) -> None:
    """Terminate Slate application gracefully.

    Args:
        proc: The subprocess to terminate.
        timeout: Seconds to wait before SIGKILL.
    """
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
