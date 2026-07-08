#!/usr/bin/env bash
set -euo pipefail

echo "Checking for processes running on ports 8000 and 5173..."
PIDS=$(lsof -t -i:8000 -i:5173 2>/dev/null || true)

if [ -n "$PIDS" ]; then
  echo "Killing processes: $PIDS"
  kill -9 $PIDS 2>/dev/null || true
else
  echo "Ports 8000 and 5173 are clean."
fi
