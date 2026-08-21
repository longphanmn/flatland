#!/usr/bin/env bash
# Start the Flatland world simulation: backend (FastAPI :8000) + frontend (Vite :5173).
# Installs dependencies on first run. Ctrl-C shuts both down.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
for port in 8000 5173; do
  if port_busy "$port"; then
    echo "Error: port $port is already in use." >&2
    exit 1
  fi
done

command -v uv >/dev/null || { echo "Error: uv not found (brew install uv)." >&2; exit 1; }
command -v npm >/dev/null || { echo "Error: npm not found." >&2; exit 1; }

PIDS=()
cleanup() {
  echo ""
  echo "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "[backend] installing deps + starting on :8000"
cd "$ROOT/backend"
[ -d .venv ] || uv sync --quiet
uv run uvicorn app.main:app --reload --port 8000 &
PIDS+=("$!")

echo "[frontend] installing deps + starting on :5173"
cd "$ROOT/frontend"
[ -d node_modules ] || npm install --silent
npm run dev &
PIDS+=("$!")

echo ""
echo "  World UI : http://localhost:5173"
echo "  API docs : http://localhost:8000/docs"
echo ""
wait
