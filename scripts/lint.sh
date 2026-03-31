#!/bin/bash
# Run linting with ruff for Slate

set -e

echo "Running ruff lint on Slate..."
ruff check slate/ tests/
echo "Lint passed!"
