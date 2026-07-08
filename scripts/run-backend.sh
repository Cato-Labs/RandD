#!/usr/bin/env bash
set -euo pipefail

# Navigate to the backend directory
cd "$(dirname "$0")/../backend"

echo "Checking Python environment..."
# Detect python executable
if command -v python3 &>/dev/null; then
  PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
  PYTHON_CMD="python"
else
  echo "Error: Python is not installed. Please install Python." >&2
  exit 1
fi

# Ensure venv exists
if [ ! -d "venv" ]; then
  echo "Creating virtual environment at backend/venv..."
  $PYTHON_CMD -m venv venv
fi

# Activate venv and check dependencies
if [ ! -f "venv/.installed" ] || [ "requirements.txt" -nt "venv/.installed" ]; then
  echo "Installing/updating backend dependencies from requirements.txt..."
  venv/bin/pip install --upgrade pip
  venv/bin/pip install -r requirements.txt
  touch venv/.installed
  echo "Backend dependencies installed successfully."
fi

echo "Starting backend FastAPI server..."
exec venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
