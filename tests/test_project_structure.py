"""Tests for project structure."""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def test_root_has_pyproject_toml():
    """AC1: Root contains pyproject.toml."""
    root = get_project_root()
    assert (root / "pyproject.toml").exists(), "pyproject.toml must exist at root"


def test_slate_package_directory():
    """AC1: Root contains slate/ package directory."""
    root = get_project_root()
    slate_dir = root / "slate"
    assert slate_dir.is_dir(), "slate/ must be a directory"
    assert (slate_dir / "__init__.py").exists(), "slate/__init__.py must exist"


def test_tests_directory():
    """AC1: Root contains tests/ directory."""
    root = get_project_root()
    assert (root / "tests").is_dir(), "tests/ directory must exist"


def test_scripts_directory():
    """AC1: Root contains scripts/ directory."""
    root = get_project_root()
    assert (root / "scripts").is_dir(), "scripts/ directory must exist"


def test_docs_directory():
    """AC1: Root contains docs/ directory."""
    root = get_project_root()
    assert (root / "docs").is_dir(), "docs/ directory must exist"


def test_data_schemes_directory():
    """AC1: Root contains data/schemes/ directory."""
    root = get_project_root()
    schemes_dir = root / "data" / "schemes"
    assert schemes_dir.is_dir(), "data/schemes/ directory must exist"


def test_layered_architecture():
    """AC3: Package follows layered architecture."""
    root = get_project_root()
    slate = root / "slate"

    assert (slate / "core").is_dir(), "slate/core/ must exist"
    assert (slate / "services").is_dir(), "slate/services/ must exist"
    assert (slate / "ui").is_dir(), "slate/ui/ must exist"
    assert (slate / "plugins").is_dir(), "slate/plugins/ must exist"
    assert (slate / "plugins" / "core").is_dir(), "slate/plugins/core/ must exist"


def test_entry_point():
    """AC4: python -m slate imports without errors."""
    import subprocess

    result = subprocess.run(
        ["python3", "-c", "from slate.ui.app import main; from slate.version import __version__"],
        capture_output=True,
        text=True,
        cwd=get_project_root(),
        timeout=5,
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"


def test_cli_entry_point():
    """AC5: CLI entry point configured in pyproject.toml."""
    root = get_project_root()
    pyproject = root / "pyproject.toml"
    content = pyproject.read_text()
    assert "[project.scripts]" in content
    assert 'slate = "slate.main:main"' in content
