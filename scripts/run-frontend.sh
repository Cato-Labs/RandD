#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Ensure frontend dependencies are installed
echo "Checking frontend dependencies..."
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  cd "$ROOT_DIR/frontend"
  npm install
  echo "Frontend dependencies installed successfully."
fi

# Wait for the backend FastAPI server to be up
echo "Waiting for backend API to be ready..."
cd "$ROOT_DIR"
# Run wait-on using the local node_modules binary
npx wait-on -t 30000 http-get://localhost:8000/api/models
echo "Backend is ready. Starting frontend Vite dev server..."

# Start the frontend dev server
cd "$ROOT_DIR/frontend"
exec npm run dev
