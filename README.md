# Flatland — World Simulation

A 2D world simulation inspired by Edwin A. Abbott's *Flatland*: geometric beings
(soldiers, gentlemen, professionals, nobles, priests, women) wander a bounded
plane, seek food, shelter in houses through creature-sized doorways, and die of
starvation when deprived of food too long.

- **Life logic:** energy decays every tick; eating restores it. Low energy makes
  a creature `hungry` (notices food farther away), very low makes it `starving`
  (farther perception + faster movement, pulsing red marker). Energy at zero =
  death.
- **Aging:** creatures age each tick; each caste has a natural lifespan
  (women shortest → priests longest). Life stages — infant, juvenile, adult,
  elder — scale speed, sight and fertility (the young are small, dim-sighted
  and infertile; elders slow and half-fertile). Old age is a distinct death
  cause; the god law `Lifespan ×` scales all lifespans.
- **Sight Recognition:** higher castes perceive farther (priests 1.35×, women
  0.8× the base sight radius) — Flatland's class hierarchy as natural law.
- **Clans & genealogy:** the founding generation seeds one clan per caste;
  children inherit their mother's clan and wear its crest as a thin colored
  ring. Every birth/death is recorded in a `creatures` lineage table per world.
- **Irregularity:** mutation may deform a child (scored 0.3–1.0). At adulthood
  the world judges it: far from regular → painlessly consumed (`euthanasia`
  death); slightly irregular → demoted to the lowest regular order (Soldier).
- **Reproduction (Nature's Law):** adult polygons and women that meet (within
  `mate_radius`, well-fed) may beget children. Sons inherit one more side than
  their father (Square→Pentagon→…→Circle); isosceles sons instead creep +0.5°
  per generation, becoming Regular Artisans at 60°. Daughters are lines.
  Mutation may deviate a son's sides; higher castes are less fertile
  (Nature's Law), fertility fades as the world crowds past carrying capacity,
  and births stop at the hard population cap. Parents pay energy and cooldown.
  Every birth/promotion lands in the Chronicle and the database.
- **Houses:** square outlines with a doorway on the south wall; walls block
  movement but the door is passable. Door width scales with the largest
  creature's body size, so big castes need big doors.

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

**God screen** (`⚖ God` button): set the laws of nature and the world obeys —
food abundance (bounty/famine), energy metabolism, hunger thresholds,
perception, movement rules, door clearance, world edge. God never intervenes in
an individual creature's life:

```bash
curl localhost:8000/api/laws
curl -X POST localhost:8000/api/laws -H 'content-type: application/json' \
     -d '{"food_count": 5}'   # famine
```

## Configuration (env vars)

| Variable | Default | Description |
|---|---|---|
| `FLATWORLD_WIDTH` | `200` | World width (grid units) |
| `FLATWORLD_HEIGHT` | `200` | World height |
| `FLATWORLD_BOUNDARY` | `wrap` | `wrap` or `clamp` edge behaviour |
| `FLATWORLD_SEED` | `42` | RNG seed (same seed ⇒ identical simulation) |
| `FLATWORLD_TICK_RATE` | `10` | Initial ticks per second |

**World generation:** population and houses scale with map area (densities ×
area, ±25% jitter, Flatland social pyramid). **Reset** rolls a fresh random
seed — every reset is a brand-new world; the seed is shown in the HUD and
recorded with that world run in the database.

## Viewport & Chronicle

- **Zoom:** mouse wheel or pinch; **pan:** drag with mouse/finger; **Fit view**
  button resets the camera. Touch screens fully supported.
- **HUD** shows live counts: alive vs dead creatures.
- **Chronicle** panel (`Chronicle — Soldier 6 · Gentleman 4 · … · Food 24 · House 6` header with caste colors + stacked chart) records every event ("*Gentleman #3 died of starvation at tick 41*", births, promotions, demotions, recoveries); the full log also lives at `GET /api/history` and survives world resets. New world (Reset) clears the live feed; archive selector + `load older` paginates history.
- **Creature inspector:** tap any creature to open its dossier — live vitals
  (energy/health bars, stage, lineage) plus its personal history; a gold halo
  marks the selection.

## Persistence

The backend stores its chronicle in SQLite at `backend/flatland.db`
(override with `FLATWORLD_DB=/path/to.db`). Every world run gets a row in
`worlds`; deaths are written to `events` as they happen; every god-law change
is recorded in `law_changes`. History survives restarts and world resets.

```bash
curl localhost:8000/api/history?limit=100   # durable chronicle (paginated)
curl localhost:8000/api/worlds              # all recorded world runs
```

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
