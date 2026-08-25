#!/usr/bin/env bash
set -euo pipefail

SERVER="root@192.168.1.21"
REMOTE_DIR="~/app/fl"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ./deploy.sh [--clear-db] — --clear-db wipes the production SQLite database
# before the backend starts (fresh chronicle; god passkey must be re-enrolled).
CLEAR_DB=0
for arg in "$@"; do
  case "$arg" in
    --clear-db) CLEAR_DB=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

echo "[deploy] Ensuring remote directory $REMOTE_DIR"
ssh "$SERVER" "mkdir -p $REMOTE_DIR"

echo "[deploy] Syncing project to $SERVER:$REMOTE_DIR"
# Detect what changed for smart restart (preserve world if only frontend).
# Compare against the last DEPLOYED commit (marker stored on the server), not
# HEAD~1 — several local commits between deploys would otherwise look "unchanged".
BACKEND_CHANGED=0
FRONTEND_CHANGED=0
DEPLOYED_REF="$(ssh "$SERVER" "cat $REMOTE_DIR/.deployed-commit 2>/dev/null || true")"
if [ -n "$DEPLOYED_REF" ] && git cat-file -e "$DEPLOYED_REF" 2>/dev/null; then
  DIFF_BASE="$DEPLOYED_REF"
else
  DIFF_BASE="HEAD~1"  # legacy best-effort fallback
fi
if git diff --name-only "$DIFF_BASE" HEAD 2>/dev/null | grep -q "^backend/"; then BACKEND_CHANGED=1; fi
if git diff --name-only "$DIFF_BASE" HEAD 2>/dev/null | grep -q "^frontend/"; then FRONTEND_CHANGED=1; fi
# also check uncommitted changes
if git status --porcelain 2>/dev/null | grep -q "^.M backend/"; then BACKEND_CHANGED=1; fi
if git status --porcelain 2>/dev/null | grep -q "^.M frontend/"; then FRONTEND_CHANGED=1; fi
# fallback: if we can't detect, assume frontend-only to preserve world
if [ "$BACKEND_CHANGED" = 0 ] && [ "$FRONTEND_CHANGED" = 0 ]; then
  echo "[deploy] No backend/frontend changes detected, assuming frontend-only (preserve world)"
  FRONTEND_CHANGED=1
fi
echo "[deploy] Backend changed: $BACKEND_CHANGED, Frontend changed: $FRONTEND_CHANGED (world preserved if backend unchanged)"

# Use rsync if available, otherwise fallback to scp
if command -v rsync >/dev/null 2>&1; then
  rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    --exclude 'dist' \
    --exclude '.DS_Store' \
    --exclude 'deploy.sh' \
    --exclude '.deployed-commit' \
    --exclude '*.log' \
    --exclude 'backend/flatworld.db' \
    --exclude 'backend/flatworld.db-*' \
    --exclude '**/flatworld.db*' \
    --exclude 'backend/app/_flatland_core.so' \
    --exclude 'backend/app/_flatland_core.dylib' \
    --exclude '*.so' \
    --exclude '*.dylib' \
    "$LOCAL_DIR"/ "$SERVER:$REMOTE_DIR"/
else
  echo "[deploy] rsync not found, using tar+scp"
  tar -czf /tmp/fl-deploy.tgz \
    --exclude='.git' --exclude='.venv' --exclude='node_modules' \
    --exclude='__pycache__' --exclude='.pytest_cache' --exclude='dist' \
    --exclude='*.log' --exclude='*.so' --exclude='*.dylib' \
    -C "$LOCAL_DIR" backend frontend run.sh README.md TODO.md
  scp /tmp/fl-deploy.tgz "$SERVER:/tmp/"
  ssh "$SERVER" "mkdir -p $REMOTE_DIR && tar -xzf /tmp/fl-deploy.tgz -C $REMOTE_DIR --strip-components=1 2>/dev/null || tar -xzf /tmp/fl-deploy.tgz -C $REMOTE_DIR && rm /tmp/fl-deploy.tgz"
fi

echo "[deploy] Installing deps and (re)starting server in background"
ssh "$SERVER" bash << REMOTE
set -euo pipefail
cd ~/app/fl
BACKEND_CHANGED=$BACKEND_CHANGED
FRONTEND_CHANGED=$FRONTEND_CHANGED
CLEAR_DB=$CLEAR_DB
echo "[remote] Backend changed: \$BACKEND_CHANGED, Frontend changed: \$FRONTEND_CHANGED, Clear DB: \$CLEAR_DB"

if [ "\$BACKEND_CHANGED" = "1" ]; then
  if [ "\$CLEAR_DB" = "1" ]; then
    echo "[remote] Clear DB: discarding world snapshot too — next start is a fresh world"
    rm -f ~/app/fl/snapshot.json ~/app/fl/snapshot.loaded
  else
    echo "[remote] Saving live world snapshot before restart (preserve tick/entities)"
    curl -s http://localhost:8000/api/state > ~/app/fl/snapshot.json 2>/dev/null && echo "[remote] snapshot saved tick=\$(python3 -c 'import json;print(json.load(open(\"/root/app/fl/snapshot.json\"))[\"tick\"])' 2>/dev/null || echo '?') entities=\$(python3 -c 'import json;print(len(json.load(open(\"/root/app/fl/snapshot.json\"))[\"entities\"]))' 2>/dev/null || echo '?')" || echo "[remote] snapshot save failed (fresh world)"
  fi
  echo "[remote] Killing backend (uvicorn) — will restore snapshot if present"
  pkill -f "uvicorn app.main:app" || true
  fuser -k 8000/tcp 2>/dev/null || true
  sleep 1
  if [ "\$CLEAR_DB" = "1" ]; then
    echo "[remote] Wiping production database (chronicle + god passkey)"
    rm -f ~/app/fl/backend/flatworld.db ~/app/fl/backend/flatworld.db-wal ~/app/fl/backend/flatworld.db-shm
  fi
else
  echo "[remote] Backend unchanged — preserving world (no restart)"
fi
if [ "\$FRONTEND_CHANGED" = "1" ]; then
  echo "[remote] Killing frontend (vite)"
  pkill -f "vite" || true
  pkill -f "npm.*dev" || true
  fuser -k 5173/tcp 2>/dev/null || true
else
  echo "[remote] Frontend unchanged — preserving frontend"
fi
sleep 2
export PATH="\$HOME/.local/bin:\$PATH"

if [ "$BACKEND_CHANGED" = "1" ]; then
  if ! command -v uv >/dev/null 2>&1; then
    echo "[remote] uv not found, please install uv"
    exit 1
  fi
  echo "[remote] [backend] sync deps"
  cd ~/app/fl/backend
  uv sync --quiet
  echo "[remote] [backend] compiling native core (M-4 OpenMP)"
  gcc -O3 -shared -fPIC -fopenmp -march=native -ffast-math -Wall app/flatland_core.c -o app/_flatland_core.so -lm 2>/dev/null || gcc -O3 -shared -fPIC -Wall -ffast-math app/flatland_core.c -o app/_flatland_core.so -lm 2>/dev/null || true
  ls -lh app/_flatland_core.so 2>/dev/null | awk '{print "[remote] native core:", \$9, \$5}' || true
  if nm -D app/_flatland_core.so 2>/dev/null | grep -q c_batch_update_creatures_omp; then echo "[remote] OpenMP kernel: OK (c_batch_update_creatures_omp)"; else echo "[remote] OpenMP kernel: serial fallback"; fi
  echo "[remote] Starting backend on 0.0.0.0:8000 (bg) — permessage-deflate off (AX P0)"
  nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --ws-per-message-deflate false > ~/app/fl/backend.log 2>&1 &
  echo "[remote] backend pid \$! log: ~/app/fl/backend.log"
  cd ~/app/fl
else
  echo "[remote] Skipping backend sync/start (unchanged, world preserved)"
fi

if [ "$FRONTEND_CHANGED" = "1" ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "[remote] npm not found, please install npm/node"
    exit 1
  fi
  echo "[remote] [frontend] install deps"
  cd ~/app/fl/frontend
  if [ ! -d node_modules ]; then
    npm install --silent
  else
    npm install --silent || true
  fi
  echo "[remote] Starting frontend on 0.0.0.0:5173 (bg)"
  nohup ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 > ~/app/fl/frontend.log 2>&1 &
  echo "[remote] frontend pid \$! log: ~/app/fl/frontend.log"
  cd ~/app/fl
else
  echo "[remote] Skipping frontend sync/start (unchanged)"
fi

sleep 3
echo "[remote] Checking ports"
ss -tulpn | grep -E '8000|5173' || ss -tlnp | grep -E '8000|5173' || netstat -tulpn 2>/dev/null | grep -E '8000|5173' || echo "ss/netstat not available, trying lsof"
lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null | head -n 5 || true
lsof -nP -iTCP:5173 -sTCP:LISTEN 2>/dev/null | head -n 5 || true

echo "[remote] Tail logs (last 20 lines)"
echo "--- backend.log ---"
tail -n 20 ~/app/fl/backend.log 2>/dev/null || true
echo "--- frontend.log ---"
tail -n 20 ~/app/fl/frontend.log 2>/dev/null || true

echo "[remote] Done. UI: http://192.168.1.21:5173  API: http://192.168.1.21:8000/docs"
REMOTE

echo "[deploy] Done"
# Remember what was deployed so the next run diffs against the right commit.
git rev-parse HEAD | ssh "$SERVER" "cat > $REMOTE_DIR/.deployed-commit"
echo "  Remote UI : http://192.168.1.21:5173"
echo "  Remote API: http://192.168.1.21:8000/docs"
echo "  Logs: ssh $SERVER 'tail -f ~/app/fl/backend.log ~/app/fl/frontend.log'"
