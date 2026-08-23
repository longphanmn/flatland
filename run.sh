#!/usr/bin/env bash
# Start the Flatland world simulation: backend (FastAPI :8000) + frontend (Vite :5173).
# `./run.sh tui` starts only the backend plus the Textual terminal client.
# Installs dependencies on first run. Ctrl-C shuts both down.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

TUI_MODE="${1:-}"

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
for port in 8000 5173; do
  if port_busy "$port"; then
    echo "Error: port $port is already in use." >&2
    exit 1
  fi
done

command -v uv >/dev/null || { echo "Error: uv not found (brew install uv)." >&2; exit 1; }
if [ "$TUI_MODE" != "tui" ]; then
  command -v npm >/dev/null || { echo "Error: npm not found." >&2; exit 1; }
fi

PIDS=()
cleanup() {
  echo ""
  echo "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "[backend] installing deps + starting on :8000 (0.0.0.0)"
cd "$ROOT/backend"
[ -d .venv ] || uv sync --quiet
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
PIDS+=("$!")

if [ "$TUI_MODE" = "tui" ]; then
  echo "[tui] starting terminal client (FLATWORLD_WS=${FLATWORLD_WS:-ws://localhost:8000/ws})"
  echo "      keys: space pause · s step · r reset · f fit · +/- zoom · hjkl pan · enter inspect · g laws · ? help · q quit"
  sleep 1  # let the backend bind first
  uv run -m tui
  exit 0
fi

echo "[frontend] installing deps + starting on :5173 (0.0.0.0)"
cd "$ROOT/frontend"
[ -d node_modules ] || npm install --silent
npm run dev -- --host 0.0.0.0 --port 5173 &
PIDS+=("$!")

echo ""
echo "  World UI : http://localhost:5173  (or http://\$(ipconfig getifaddr en0 2>/dev/null || echo 192.168.1.21):5173 on LAN)"
echo "  API docs : http://localhost:8000/docs"
echo "  Remote   : http://192.168.1.21:5173 (if deployed)"
echo ""
wait
