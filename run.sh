#!/usr/bin/env bash
# Flatland launcher.
#   ./run.sh                  backend (:8000) + web UI (:5173) — full stack
#   ./run.sh tui [ws-url] [god-passkey]
#                             terminal TUI ONLY — attaches to an already-running
#                             world, never starts any server
#                             (default url ws://localhost:8000/ws, env FLATWORLD_WS)
#                             The passkey (3rd arg or FLATWORLD_GOD_KEY) is sent
#                             with every control/laws call — no prompt, ever.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

MODE="${1:-}"

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# ---------------------------------------------------------------- tui: pure frontend
# The TUI is a plain client of the /ws + REST API. It must never spawn a
# backend — it attaches to one that is already running, local or remote.
if [ "$MODE" = "tui" ]; then
  WS_URL="${2:-${FLATWORLD_WS:-ws://localhost:8000/ws}}"
  export FLATWORLD_WS="$WS_URL"
  # God passkey: 3rd arg wins, else the env var. The server rejects control
  # calls without it — there is no auth bypass, just no interactive prompt.
  if [ -n "${3:-}" ]; then export FLATWORLD_GOD_KEY="$3"; fi
  HTTP_BASE="$(printf '%s' "$WS_URL" | sed -E 's~^wss://~https://~; s~^ws://~http://~; s~(/api)?/ws$~~')"

  command -v uv >/dev/null || { echo "Error: uv not found (brew install uv)." >&2; exit 1; }
  cd "$ROOT/backend"
  [ -d .venv ] || uv sync --quiet

  echo "[tui] attaching to $WS_URL (no server will be started)"
  if command -v curl >/dev/null 2>&1 && curl -sf --max-time 3 "$HTTP_BASE/healthz" >/dev/null 2>&1; then
    echo "[tui] world is live"
  else
    echo "[tui] note: nothing answering at $HTTP_BASE yet — start it with ./run.sh," >&2
    echo "      or point at another host: ./run.sh tui ws://host:8000/ws" >&2
    echo "      (the TUI keeps retrying in the meantime)" >&2
  fi
  echo "[tui] keys: space pause · s step · r reset · f fit · a ascii/blocks · +/- zoom · hjkl pan · enter inspect · g laws · ? help · q quit"
  echo "[tui] auth: pass FLATWORLD_GOD_KEY (or 3rd arg) to control the world; without it, viewing works"
  exec uv run -m tui
fi

# ------------------------------------------------------------ default: full stack
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

echo "[backend] installing deps + starting on :8000 (0.0.0.0)"
cd "$ROOT/backend"
[ -d .venv ] || uv sync --quiet
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
PIDS+=("$!")

echo "[frontend] installing deps + starting on :5173 (0.0.0.0)"
cd "$ROOT/frontend"
[ -d node_modules ] || npm install --silent
npm run dev -- --host 0.0.0.0 --port 5173 &
PIDS+=("$!")

echo ""
echo "  World UI : http://localhost:5173  (or http://\$(ipconfig getifaddr en0 2>/dev/null || echo 192.168.1.21):5173 on LAN)"
echo "  API docs : http://localhost:8000/docs"
echo "  Remote   : http://192.168.1.21:5173 (if deployed)"
echo "  Terminal : ./run.sh tui   (attach a TUI to this world)"
echo ""
wait
