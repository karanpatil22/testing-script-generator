#!/usr/bin/env bash
# Start the local recorder server (uses the .venv created by setup.sh).
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "No .venv found. Run ./setup.sh first."
  exit 1
fi

exec .venv/bin/python server.py
