.PHONY: help lint format typecheck test install clean

help:
	@echo "Slate Development Commands"
	@echo "=========================="
	@echo "make install      - Install dependencies"
	@echo "make lint         - Run ruff linter"
	@echo "make format       - Format code with ruff"
	@echo "make typecheck    - Run mypy type checker"
	@echo "make test         - Run pytest with coverage"
	@echo "make clean        - Remove build artifacts"

install:
	pip install -e ".[dev]"

lint:
	ruff check slate/

format:
	ruff format slate/

typecheck:
	mypy slate/

test:
	pytest tests/ --cov=slate --cov-report=term-missing

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete