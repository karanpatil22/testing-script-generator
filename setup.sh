#!/usr/bin/env bash
# Set up a local virtual environment with Playwright and Chromium.
set -e
cd "$(dirname "$0")"

echo "==> Creating virtual environment (.venv)"
python3 -m venv .venv

echo "==> Upgrading pip"
.venv/bin/python -m pip install --upgrade pip

echo "==> Installing Playwright + pytest"
.venv/bin/python -m pip install playwright pytest pytest-playwright pytest-asyncio

echo "==> Installing Chromium browser"
.venv/bin/python -m playwright install chromium

echo ""
echo "Setup complete. Start the recorder with:  ./run.sh"
