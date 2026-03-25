"""Tests for pyproject.toml configuration."""

import re
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_pyproject_content() -> str:
    """Read pyproject.toml content."""
    return (get_project_root() / "pyproject.toml").read_text()


def test_python_requires():
    """AC2: Python >=3.10 declared."""
    content = get_pyproject_content()
    assert "requires-python" in content
    assert ">=3.10" in content


def test_runtime_dependencies():
    """AC2: Runtime dependencies declared."""
    content = get_pyproject_content()
    assert "PyGObject" in content
    assert "gitpython" in content


def test_dev_dependencies():
    """AC2: Dev dependencies declared."""
    content = get_pyproject_content()
    assert "pytest" in content
    assert "pytest-cov" in content
    assert "ruff" in content
    assert "mypy" in content