.PHONY: help lint format typecheck test test-unit test-gtk test-e2e test-all test-parallel test-timeout install clean

help:
	@echo "Slate Development Commands"
	@echo "=========================="
	@echo "make install         - Install dependencies"
	@echo "make lint            - Run ruff linter"
	@echo "make format          - Format code with ruff"
	@echo "make typecheck       - Run mypy type checker"
	@echo "make test            - Run unit tests with coverage"
	@echo "make test-unit       - Run unit tests (no display required)"
	@echo "make test-gtk        - Run GTK integration tests"
	@echo "make test-e2e        - Run E2E smoke tests"
	@echo "make test-all        - Run all tests"
	@echo "make test-parallel   - Run tests in parallel"
	@echo "make test-timeout    - Run tests with timeout enforcement"
	@echo "make clean           - Remove build artifacts"

install:
	pip install -e ".[dev]"

install-test:
	pip install -e ".[test]"

lint:
	ruff check slate/
	ruff check tests/

format:
	ruff format slate/
	ruff format tests/

typecheck:
	mypy slate/

test:
	pytest tests/ --cov=slate --cov-report=term-missing --cov-fail-under=85

test-fast:
	pytest tests/services/ tests/core/ -v --tb=short

test-unit:
	pytest tests/services/ tests/core/ -v

test-gtk:
	xvfb-run pytest tests/ui/gtk/ -v --timeout=30

test-e2e:
	xvfb-run pytest tests/e2e/ -v --timeout=60

test-all:
	xvfb-run pytest tests/ -v

test-parallel:
	xvfb-run pytest tests/ -n auto

test-timeout:
	xvfb-run pytest tests/ --timeout=30

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete