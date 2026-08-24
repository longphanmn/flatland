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
- **Clans & genealogy:** every non-ruin house founds a clan and the founding
  generation joins the clan of its nearest house — castes mix inside
  settlements (the `Max clans` law pins how many spatial clans arise).
  Children inherit their mother's clan and wear its crest as a thin colored
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
- **Autonomous Evolution:** 100% emergent, zero god intervention.
  - **Personality archetypes:** `brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder` with 65% genetic heritability. Altruistic beings feed starving kin with basket food.
  - **Dynamic Tools & Equipment:** Spears (+20% war damage & reach for Soldiers/Predators), Baskets (carry up to 3 food units for field meals or clan larder deposits), Herb Poultices (+25 HP healing & infection cure for Priests), and Chieftain Crowns for clan leaders.
  - **Skill Mastery & Titles:** 4 tracked skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿) unlock dynamic titles (*the Slayer*, *the Fearless Champion*, *the Grand Harvester*, *the Wise Shaman*, *the Pathfinder*).
  - **Oral Lore in Houses:** Resting elders transmit mastery XP to sleeping infants and juveniles.
  - **Animated Thought Bubbles:** Real-time floating mood balloons (`🍖`, `❤️`, `⚔️`, `🌿`, `🏆`, `💤`, `🧺`, `😱`) above creature heads.
- **Energy & Stage Metabolism:**
  - **Stage-aware metabolism:** Born infants burn 55% less energy per tick (`0.45x`), juveniles burn 25% less (`0.75x`), adults standard (`1.0x`), elders `0.85x`.
  - **Combat stamina:** Clashing in battle drains stamina (winner -6, loser -10); creatures with <20% energy strike with 30% reduced damage.
  - **Field food reserves:** Hungry creatures (<45 energy) carry food in baskets and eat autonomously while roaming. Full creatures (>85% energy) never eat or destroy food plants.
- **Houses & Settlements:** Square outlines with creature-sized doorways; walls block movement. Clans expand across multiple houses, with the leader residing in the primary **Main House** marked by a golden crown.

- **Backend:** Python 3.12 · FastAPI · deterministic fixed-tick loop over WebSocket
- **Frontend:** React 18 + Vite + TypeScript · HTML5 Canvas renderer
- **Terminal client:** Textual TUI (`backend/tui/`) — watch/control the live world from the shell

## Quickstart

```bash
./run.sh          # web UI (backend :8000 + frontend :5173)
./run.sh tui      # terminal client only — attaches to a running world
```

- Frontend: http://localhost:5173 (open this)
- Backend API: http://localhost:8000/docs
- Living Guide: http://localhost:8000/guide
- Living Wiki: http://localhost:8000/wiki

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

## Terminal TUI

A Textual client that watches/controls a running world over the same `/ws` +
REST API — no browser, and **no server of its own**: it never starts a
backend, it attaches to one that is already up (local machine, LAN box or
production). Several TUIs can watch the same world at once.

```bash
./run.sh tui                                        # attach to localhost:8000
./run.sh tui ws://192.168.1.21:8000/ws              # attach to another host
cd backend && FLATWORLD_WS=ws://host:8000/ws uv run -m tui
uv run textual serve -m tui.serve                   # optional: TUI in the browser
```

If the world is down the TUI keeps reconnecting until it's back.

Half-block char-grid world renderer (creatures wear their soul-code glyph in
caste colors with floating emote thoughts and tool marks, houses are clan-colored boxes with doors, plants/corpses/fires/
signals all drawn), HUD with selection dossier, color-coded Chronicle with category filtering, Clans table, Plots progress,
population sparkline — plus god-laws form (`g`) posting to `/api/laws`.

Keys: `space` pause · `s` step · `r` reset · `f` fit · `w` follow creature · `t` log filter · `+/-` zoom (wheel too) ·
`hjkl`/arrows pan · click select · `enter`/`i` inspect · `c` clan · `g` god laws ·
`o` older events · `1-9` speed · `?` help · `q` quit.

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
     -H "X-God-Key: $KEY" \
     -d '{"food_count": 5}'   # famine
```

## God passkey (auth)

God-touching endpoints — `POST /api/laws`, `POST /api/presets/{name}`,
`POST /api/control` and control messages over the WebSocket — require a
passkey. Viewing (`/ws`, `/api/state`, history, clans…) stays open.

- **First time** (no credential exists): any god call answers `409`, and the
  web UI asks you to **create** a passkey. Enroll directly with
  `POST /api/auth/setup {"passkey": …}` if you prefer.
- **After that**: every god call needs the key. The web UI remembers it in
  localStorage; REST callers send `X-God-Key: <passkey>`; WebSocket control
  messages carry `"key": "<passkey>"`.
- **Lost passkey?** Reset it from the server's command line — there is no web
  route for this:

  ```bash
  cd backend
  uv run python -m app.godkey reset <new-passkey>  # overwrite (or create)
  uv run python -m app.godkey clear                # forget → UI asks again on next visit
  ```

- **TUI / scripts**: no interactive auth, no bypass — pass the same key from
  the command line: `./run.sh tui ws://host:8000/ws <passkey>` or export
  `FLATWORLD_GOD_KEY=<passkey>`. Viewing works without it.
- `FLATWORLD_GOD_KEY` also seeds the server-side credential at boot (handy for
  headless deploys); only a PBKDF2 hash is stored, so clearing the database
  wipes the credential and the next visit enrolls again.

## Configuration (env vars)

| Variable | Default | Description |
|---|---|---|
| `FLATWORLD_WIDTH` | `400` | World width (grid units) |
| `FLATWORLD_HEIGHT` | `300` | World height |
| `FLATWORLD_BOUNDARY` | `wrap` | `wrap` or `clamp` edge behaviour |
| `FLATWORLD_SEED` | `42` | RNG seed (same seed ⇒ identical simulation) |
| `FLATWORLD_TICK_RATE` | `10` | Initial ticks per second |
| `FLATWORLD_GOD_KEY` | — | Seed/override the god passkey at boot |

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
backend/tui/        # terminal client (Textual) — pure /ws + REST consumer
├── state.py        # tolerant typed mirror of protocol.py
├── client.py       # WSClient (reconnect+backoff) + RESTClient (httpx)
├── theme.py        # caste colors, glyphs (single source of truth)
├── widgets/        # world_view (half-block renderer), hud, chronicle, …
└── screens/        # god_laws form, inspector, clan details, help
```

Protocol: server pushes `{type:"hello"}` then `{type:"state"}` snapshots every
tick; clients send `{action:"pause"|"resume"|"step"|"reset"|"set_speed", value}`.

## Concurrency & performance

The world is one deterministic, in-process state machine, so it advances on a
**dedicated engine thread** (`SimEngine` in `main.py`) instead of the asyncio
loop — HTTP/WebSocket load, JSON snapshot serialization and SQLite writes no
longer stall ticks, and vice versa. Every touch of the live simulation
(tick, control actions, law changes, state reads) crosses `RT.lock`, so REST
and WS clients never observe a half-advanced tick. The tick itself is kept
lean by algorithmic wins (broad-phase wall tests with cached house segments,
squared-distance threshold checks); multi-process workers are intentionally
*not* used — they would mean several disconnected worlds, and CPython's GIL
makes thread-level compute parallelism a wash for pure-Python simulation.
Performance round 2 keeps 400–500 creatures smooth: spatial-hash neighbour
queries for war pair discovery and mob counts, incremental clan relations
(eater pairs via the hash, one dominant-caste pass, neutral pairs pruned),
plain-dict snapshots with cached personal identity instead of pydantic
validation per frame, `orjson` broadcast encoding, and all of a tick's DB
writes committed together (`Database.batch()`).

## Roadmap hooks already in place

- Dimensionality is isolated to `config`/`world` (add a z-axis without redesign)
- Snapshot protocol is versioned by shape; swap full snapshots for diffs later
- Deterministic seeded RNG per tick ⇒ future replay/record support

## Developer

**Long Phan** — [long@minhnhan.in](mailto:long@minhnhan.in) — long@minhnhan.in

- Website: https://minhnhan.in · World: https://world.minhnhan.in
- Backend: `backend/` · Frontend: `frontend/` · Docs: `docs/` + `/wiki` & `/guide`
- License & contact: Long Phan <long@minhnhan.in>

> Flatland is designed, built and maintained by **Long Phan (long@minhnhan.in)**. For inquiries, deployments or collaboration, reach out via long@minhnhan.in.
