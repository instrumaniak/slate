import os
import subprocess
import time

import pytest


def _wait_for_ready(proc, timeout=10):
    """Poll stderr for SLATE_READY signal. Returns (ready, stderr_output)."""
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


@pytest.fixture(scope="session")
def xvfb_server():
    """Start Xvfb for headless testing."""
    yield
