# Flatland — World Simulation

A 2D world simulation inspired by Edwin A. Abbott's *Flatland*: geometric beings
(soldiers, gentlemen, professionals, nobles, priests, women) wander a bounded
plane, seek food, collide with houses, and starve without energy.

- **Backend:** Python 3.12 · FastAPI · deterministic fixed-tick loop over WebSocket
- **Frontend:** React 18 + Vite + TypeScript · HTML5 Canvas renderer

## Quickstart

```bash
./run.sh
```

- Frontend: http://localhost:5173 (open this)
- Backend API: http://localhost:8000/docs

The script installs dependencies on first run, starts both servers with live
reload, and shuts them down cleanly on Ctrl-C.

## Manual commands

Backend:

```bash
cd backend
uv sync                                  # create venv, install deps
uv run pytest -q                         # run tests
uv run uvicorn app.main:app --reload --port 8000
```

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev                              # dev server with /ws + /api proxy
npm run build                            # type-check + production build
```

## Controls

Pause / Resume / Step (single tick) / Reset / ticks-per-second — available from
the web UI, or programmatically:

```bash
curl -X POST localhost:8000/api/control -H 'content-type: application/json' \
     -d '{"action": "pause"}'
curl localhost:8000/api/state
```

## Configuration (env vars)

| Variable | Default | Description |
|---|---|---|
| `FLATWORLD_WIDTH` | `100` | World width (grid units) |
| `FLATWORLD_HEIGHT` | `100` | World height |
| `FLATWORLD_BOUNDARY` | `wrap` | `wrap` or `clamp` edge behaviour |
| `FLATWORLD_SEED` | `42` | RNG seed (same seed ⇒ identical simulation) |
| `FLATWORLD_TICK_RATE` | `10` | Initial ticks per second |

## Architecture

```
backend/app/
├── config.py       # all tunables (geometry, population, behaviour)
├── entities.py     # Creature castes (Flatland), Food, House
├── world.py        # entity registry + spatial hash, wrap-aware queries
├── simulation.py   # deterministic step(): perceive→steer→move→eat→metabolize
├── protocol.py     # pydantic wire schemas (shared contract with frontend)
└── main.py         # FastAPI: WS broadcast hub, control actions, REST helpers
frontend/src/
├── types.ts        # TS mirror of protocol.py
├── websocket.ts    # reconnecting WS client
├── render/CanvasRenderer.tsx  # rAF loop drawing latest snapshot
└── App.tsx         # HUD (tick/population/seed) + controls
```

Protocol: server pushes `{type:"hello"}` then `{type:"state"}` snapshots every
tick; clients send `{action:"pause"|"resume"|"step"|"reset"|"set_speed", value}`.

## Roadmap hooks already in place

- Dimensionality is isolated to `config`/`world` (add a z-axis without redesign)
- Snapshot protocol is versioned by shape; swap full snapshots for diffs later
- Deterministic seeded RNG per tick ⇒ future replay/record support
