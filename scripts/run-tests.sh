#!/bin/bash
# Run tests with coverage for Slate

set -e

echo "Running Slate tests with coverage..."
python3 -m pytest tests/ --cov=slate --cov-report=term-missing --cov-fail-under=85 -v
