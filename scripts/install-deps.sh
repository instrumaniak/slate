#!/bin/bash
# Install system dependencies for Slate (Ubuntu/Debian)
# Run with: sudo ./scripts/install-deps.sh

set -e

echo "Installing system dependencies for Slate..."

# Python and GTK
apt-get update
apt-get install -y \
    python3 \
    python3-gi \
    python3-gi-cairo \
    python3-pip \
    gir1.2-gtk-4.0 \
    gir1.2-gtksource-5 \
    gir1.2-adw-1

# Development tools
apt-get install -y \
    git \
    ripgrep

# Python development packages
apt-get install -y \
    python3-dev \
    libgirepository1.0-dev \
    libcairo2-dev

echo "System dependencies installed successfully!"
echo ""
echo "To install Python dependencies, run:"
echo "  pip install -e .[dev]"
echo ""
echo "To verify the installation, run:"
echo "  python -m slate"