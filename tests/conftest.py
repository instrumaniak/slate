import gc

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "gtk: marks tests requiring GTK display")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests")


def pytest_sessionfinish(session, exitstatus):
    gc.collect()
    gc.collect()
    gc.collect()


def pytest_runtest_teardown(item, nextitem):
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def memory_limit_guard():
    import resource

    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    if soft == resource.RLIM_INFINITY:
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, hard))

    yield

    gc.collect()
    gc.collect()
    gc.collect()


@pytest.fixture(autouse=True)
def cleanup_slate_processes():
    """Kill any orphan slate processes after each test."""
    yield

    import os

    for child in os.listdir("/proc"):
        if child.isdigit():
            try:
                with open(f"/proc/{child}/cmdline", "rb") as f:
                    cmdline = f.read()
                    if b"slate" in cmdline or b"SlateApplication" in cmdline:
                        try:
                            os.kill(int(child), 9)
                        except (ProcessLookupError, PermissionError):
                            pass
            except (FileNotFoundError, PermissionError):
                pass
