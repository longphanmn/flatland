"""Living guide — backend-rendered docs that always match the running code.

No Vite dependency. Renders markdown to HTML with a minimal template + nav.
Auto-generates GodLaws table and API reference from the live OpenAPI schema.
"""

import re
import html
from pathlib import Path
from typing import Any

from .config import Config
from .protocol import GodLaws


def _md_to_html(md: str) -> str:
    """Tiny markdown → HTML: headings, bold, italic, code, links, lists, paragraphs."""
    # Escape first, then selectively unescape markdown constructs
    lines = md.split("\n")
    out: list[str] = []
    in_code = False
    in_ul = False
    in_ol = False

    def inline(s: str) -> str:
        # escape html
        s = html.escape(s)
        # code `x`
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        # bold **x** or __x__
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", s)
        # italic *x* or _x_
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        # links [text](url)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            continue
        # headings
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            lvl = len(m.group(1))
            text = inline(m.group(2).strip())
            slug = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(f'<h{lvl} id="{slug}">{text}</h{lvl}>')
            continue
        # unordered list
        if re.match(r"^[-*]\s+", line):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            if in_ol:
                out.append("</ol>")
                in_ol = False
            txt = inline(re.sub(r"^[-*]\s+", "", line))
            out.append(f"<li>{txt}</li>")
            continue
        # ordered list
        if re.match(r"^\d+\.\s+", line):
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            if in_ul:
                out.append("</ul>")
                in_ul = False
            txt = inline(re.sub(r"^\d+\.\s+", "", line))
            out.append(f"<li>{txt}</li>")
            continue
        # paragraph
        if in_ul or in_ol:
            # close lists if next line is paragraph
            pass
        out.append(f"<p>{inline(line)}</p>")

    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


def _god_laws_table() -> str:
    """Auto-generated table of every GodLaws field with type/range/default."""
    cfg = Config()
    rows = []
    for name, field in GodLaws.model_fields.items():
        ann = str(field.annotation)
        # extract range from field metadata
        ge = getattr(field, "ge", None)
        le = getattr(field, "le", None)
        gt = getattr(field, "gt", None)
        # use json_schema_extra or field constraints
        # Pydantic v2 stores in metadata
        constraints = []
        for m in getattr(field, "metadata", []):
            if hasattr(m, "ge") and m.ge is not None:
                constraints.append(f"≥{m.ge}")
            if hasattr(m, "le") and m.le is not None:
                constraints.append(f"≤{m.le}")
            if hasattr(m, "gt") and m.gt is not None:
                constraints.append(f">{m.gt}")
        # fallback: check field description
        default = getattr(cfg, name, None) if hasattr(cfg, name) else None
        typ = ann.replace("Optional", "").replace("[", "").replace("]", "").strip(" |None")
        rows.append(
            f"<tr><td><code>{html.escape(name)}</code></td>"
            f"<td>{html.escape(typ)}</td>"
            f"<td>{html.escape(', '.join(constraints) or '—')}</td>"
            f"<td>{html.escape(str(default))}</td></tr>"
        )
    header = "<tr><th>Law</th><th>Type</th><th>Range</th><th>Default</th></tr>"
    return f"<table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"


def _api_table(app: Any) -> str:
    """Auto-generated API table from live routes + OpenAPI schema."""
    rows = []
    for route in app.routes:
        # FastAPI routes have path and methods
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if not path or path.startswith("/guide") or path.startswith("/openapi") or path.startswith("/docs") or path.startswith("/redoc"):
            # include /guide itself for completeness but skip swagger internal
            if path.startswith("/guide"):
                pass
            else:
                continue
        if methods:
            for m in sorted(methods):
                if m in ("HEAD", "OPTIONS"):
                    continue
                rows.append(f"<tr><td><code>{html.escape(m)} {html.escape(path)}</code></td>"
                            f"<td>{html.escape(getattr(route, 'name', ''))}</td></tr>")
        else:
            rows.append(f"<tr><td><code>{html.escape(path)}</code></td><td></td></tr>")
    # ensure every REST route is listed: deduplicate
    rows = sorted(set(rows))
    header = "<tr><th>Route</th><th>Name</th></tr>"
    return f"<table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"


# Static markdown sections (How the world works etc)
HOW_IT_WORKS_MD = """
# How the world works

**God model:** god sets *laws*, never touches individual creatures. Everything else emerges.

## The deterministic tick
`s = Simulation(Config(seed))` → `s.step()` is fully deterministic (one `random.Random` per world). Same seed ⇒ same world. Tick loop (`simulation.py:539` `simulation.py:335`) order: weather → plants → rebuild index → creatures → disease → war → reproduce → relations → food law → corpses → settlements → tick+=1. Snapshots are pushed over WebSocket `state` every tick.

## Life cycle & stages (§A)
Creature.age ticks + caste-based lifespan (Woman 4800 → Priest 9000). Stage by `age/lifespan`: infant <15%, juvenile <30%, adult <75%, else elder. Stage scales speed & sight (infant 0.6×, elder 0.85×) and fertility (elder ×0.5). Death causes: `starvation`, `old_age`, `euthanasia`, `disease`.

## Nature's Law inheritance (§B)
Sex: polygons male, lines female (`entities.py:137`). Sons `sides = father.sides+1` capped at `max_sides` (24→Priest); daughters lines. Mutation `mutation_rate` ±1 side → `irregularity` 0.3–1.0. Isosceles triangles: `iso_angle+0.5°` per generation, `≥60°` promotes Soldier→Artisan. Fertility: per-caste table × crowding `carrying_capacity`/`max_population`.

## Irregularity & caste (§C)
Mutated children's `irregularity` judged at `adult_age`: `≥euthanasia_threshold` → consumed (`euthanasia`), else demoted to Soldier. `CASTE_TRAITS` (`entities.py:39`) gives lifespan/speed/sight_mult/fertility.

## Disease (§D)
`disease_enabled`, `disease_outbreak_rate` starts new `disease_id`, spreads within `disease_radius` at `disease_rate` (winter ×1.5), drains `disease_energy_drain` + health `2×disease_lethality`, recovers `recovery_rate`. Disabling freezes instantly.

## Environment (§E)
Clock from tick: `time_of_day` (`day_length` cycle, starts sunrise), `day`, `season` (`season_length`). Night `night_sight_mult`, fog `fog_sight_mult` stack. `SEASON_FOOD_MULT` spring 1.0/summer 1.2/autumn 1.0/winter 0.5; spring ×1.25 birth, winter ×1.5 disease. Weather FSM clear/rain/fog/storm at `weather_change_rate`: rain/storm `rain_speed_mult`, storm `storm_wander_bonus`.

## Clans & social order (§C/I)
Founding generation seeds one clan per caste (`simulation.py:244`), children inherit mother's `clan_id`. Clan crest color on snapshot. Relations −100..+100 drift `relation_drift_rate` →0, threshold `alliance_threshold`/`rivalry_threshold` → `alliance`/`rivalry` events; shared feeding within `flock_radius` `+2`. Boids `cohesion_weight`/`alignment_weight`/`separation_weight` blended after food-seeking; social yielding `YIELD_RADIUS` 2.5.

## Food economy (§H/N)
`Food` is a living plant `growth` 0.15→1.0 (`plant_growth_rate`), spreads `plant_spread_rate` within `SPREAD_RADIUS` 6.0 if below seasonal bounty `food_count×SEASON_FOOD_MULT`. Winter die-back removes youngest first. Death leaves `Corpse` (`corpse_ttl`, `corpse_energy`) edible like food; decay boosts nearby plants `NUTRIENT_BOOST×nutrient_cycle_rate` within `NUTRIENT_RADIUS`.

## Shelter (§L/N)
Houses (`entities.py:184`) squares with doorway; walls block except door — doorway too small for Carnivore predators (§L refuge, `simulation.py:1178` `predator_blocked`) so houses are the only safe haven once predators hunt; any predator that spawns inside is ejected to the doorstep. Exposure `exposure_drain` outdoors in rain/storm or night unless `indoors`. `house_capacity` beds per house re-contested every tick in id order; overflow sleeps outside. `sleep_enabled` night → seek house (`_house_for` prefers own clan's settlement if `house_claim_enabled`; predators never seek shelter), `sleeping` halves hunger `sleep_energy_mult` + health `+0.15×rest_recovery_mult`. Clan claim: each clan's settlement house shows crest (`House.clan_color`). Settlement economy (§L): target houses `area×house_density×carrying/80` vs `0.6×carrying/house_capacity` (`simulation.py:356` `_target_house_count`), growth via `_spawn_settlement_house` (`simulation.py:373`) and `_update_settlements` (`simulation.py:390`) after corpses each tick; abandoned houses (unclaimed or clan extinct) idle `house_decay_ticks` (`config.py:113`) then crumble to `is_ruin` (`entities.py:192`) → `ruin` event, walls no longer block (`simulation.py:1507`); new clans found a new settlement if no free house (`simulation.py:311`); pinned `num_houses` (`simulation.py:423`) still wins for tests/scenarios.
"""

CODEBASE_MAP_MD = """
# Codebase map

## Backend (`backend/app/`)
- `config.py:13` — `Config` dataclass: world geometry, densities, food, corpses, behaviour, life, reproduction, disease, environment, shelter, terrain, society, houses, chronicle. `from_env()` + `tick_interval`.
- `entities.py:1` — `CasteTraits`, `CASTE_TRAITS`, `YIELD_RANK`, `caste_name()`, `Creature` (shape/sides/caste/age/lifespan/health/infected/clan_id/sleeping...), `Food` (growth), `Corpse`, `House` (size/door/clan).
- `world.py:32` — `World` registry + uniform spatial hash (`cell_size`, `rebuild_index`), `delta`/`distance` wrap-aware, `query_radius`.
- `simulation.py:57` — `Simulation` deterministic tick: `CLAN_COLORS`, `STAGE_MULT`, `SEASONS`, `SEASON_FOOD_MULT`, `YIELD_RADIUS`, `SPREAD_RADIUS` etc. Methods: `_time_of_day`, `_is_night`, `_season`, `_update_weather`, `_inside_house`, `_spawn_initial`, `_found_clan`, `_assign_house_claims`, terrain, `step`, `_update_relations`, `_update_plants`, `_update_corpses`, `_infect`, `_reproduce`, `_birth`, `_kill`, `_update_creature`, `_enforce_food_law`, `snapshot`.
- `protocol.py:7` — Pydantic wire schemas: `ControlAction`, `ControlMessage`, `EntityState`, `StateMessage`, `HistoryEvent`, `HelloMessage`, `GodLaws`.
- `db.py:1` — `Database` stdlib `sqlite3` thin wrapper: `worlds`, `events`, `law_changes`, `creatures`, `snapshots`; WAL, thread-safe lock.
- `main.py:1` — FastAPI `app`, `Hub` broadcast, `RuntimeState`, `tick_loop`, `apply_control`, `hello_payload`, `LAW_FIELDS`, `get_laws`/`apply_laws`, WebSocket `/ws`, REST routes, `/guide`.

## Frontend (`frontend/src/`)
- `App.tsx` — HUD, controls, WebSocket hook, snapshot state, inspector.
- `render/CanvasRenderer.tsx` — rAF loop drawing snapshot (creatures, houses, food, terrain, night/weather).
- `god/GodPanel.tsx` — grouped law sliders/toggles (World/Food&Energy/Hunger&Sight/Movement/Life&Death/Bodies&Houses/Sky&Seasons/Disease/Shelter/Interaction).
- `inspect/Inspector.tsx` — creature dossier (vitals, lineage, family tree).
- `types.ts` — TS mirror of `protocol.py`.
- `websocket.ts` — reconnecting WS client.

## Data flow
`tick_loop` → `sim.step()` → `sim.snapshot()` → `HUB.broadcast` → `ws` → `CanvasRenderer` + `App` state. Client → `ControlMessage` → `apply_control` → `RT.config`/`RT.sim` → DB law_changes. Events → `DB.add_events` + genealogy.
"""

DATA_MODEL_MD = """
# Data model & protocol

## Entities (in-memory)
- `Creature` (`entities.py:95`): `id`, `x`, `y`, `angle`, `shape` polygon|line, `sides`, `caste`, `radius`, `age`, `lifespan`, `stage` infant|juvenile|adult|elder, `irregularity`, `health` 0–100, `infected`, `sex` male|female, `mother_id`/`father_id`, `clan_id`/`clan_color`, `sleeping`/`indoors`, `generation`, `born_tick`, `energy`, `status` hungry/starving, `meals`.
- `Food` (`entities.py:158`): `x`, `y`, `growth` 0–1.
- `Corpse` (`entities.py:170`): `x`, `y`, `ttl`, `energy`.
- `House` (`entities.py:184`): `x`, `y`, `size`, `door_width`/`door_side`/`door_offset`, `clan_id`/`clan_color` (settlement), `is_ruin`/`abandoned_ticks`; ruin after `house_decay_ticks` (`config.py:113`), `settlement`/`ruin` events.
- Terrain: `fertile: [{x,y,r}]`, `rocks: [{x,y,r}]` in snapshot.

## Wire schemas (`protocol.py`)
- `EntityState` (`protocol.py:27`): `id`, `kind` creature|food|house|corpse, `x`/`y`/`angle`, plus optional fields above.
- `StateMessage` (`protocol.py:62`): `tick`, `seed`, `width`/`height`/`boundary`, `population`, `entities`, `creatures_alive`/`creatures_dead`/`dead_by_cause`, `infected_count`, `time_of_day`/`day`/`season`/`weather`, `terrain_fertile`/`terrain_rocks`, `relations`, `events`.
- `HistoryEvent` (`protocol.py:86`): `type` death|birth|promotion|demotion|outbreak|recovery|bloom|alliance|rivalry|predation|war|ruin|settlement, `tick`, `entity_id`, `caste`, `cause`, `x`/`y`, `payload` (parents/sides/generation/clan_id etc).
- `HelloMessage` (`protocol.py:99`): `seed`, `tick_rate`, `width`/`height`/`boundary`.
- `ControlMessage` (`protocol.py:22`): `action` pause|resume|step|reset|set_speed + `value`.

## WebSocket flow
Server → client: `{"type":"hello", ...}` then `{"type":"state", ...}` each tick. Client → server: `{"action":"pause"|"resume"|"step"|"reset"|"set_speed", "value":...}` (`main.py:270`).
"""

CONFIG_OPS_MD = """
# Configuration & ops

## Env vars (`FLATWORLD_*`)
| Variable | Default | Description |
|---|---|---|
| `FLATWORLD_WIDTH` | `200` | World width (grid units) |
| `FLATWORLD_HEIGHT` | `200` | World height |
| `FLATWORLD_BOUNDARY` | `wrap` | `wrap` or `clamp` |
| `FLATWORLD_SEED` | `42` | RNG seed |
| `FLATWORLD_TICK_RATE` | `10` | Ticks per second |
| `FLATWORLD_DB` | `backend/flatworld.db` | SQLite path |

## Persistence (`db.py:20`)
SQLite `flatworld.db` (WAL, thread lock). Tables:
- `worlds(id, seed, width, height, boundary, started_at, ended_at)`
- `events(id, world_id, tick, type, entity_id, caste, cause, x, y, payload, created_at)`
- `law_changes(id, world_id, tick, name, value, created_at)`
- `creatures(id, world_id, entity_id, caste, clan_id, generation, mother_id, father_id, born_tick, died_tick)`
- `snapshots(id, world_id, tick, payload, created_at)`

History survives restarts; `reset` closes old world row and opens new.

## Run & deploy
```bash
./run.sh
# or
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

## Tests
```bash
cd backend && uv run pytest -q
cd backend && uv run pytest tests/test_synergies.py -q
```
"""

GUIDE_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flatland — Living Guide</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#222;background:#fafafa}}
nav{{position:fixed;top:0;left:0;width:240px;height:100vh;overflow:auto;background:#fff;border-right:1px solid #e5e7eb;padding:16px}}
main{{margin-left:240px;padding:24px;max-width:900px}}
a{{color:#0a58ca;text-decoration:none}} a:hover{{text-decoration:underline}}
pre{{background:#f3f4f6;padding:12px;overflow:auto;border-radius:6px}}
code{{background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:0.9em}}
table{{border-collapse:collapse;width:100%;margin:12px 0}} th,td{{border:1px solid #e5e7eb;padding:6px 8px;text-align:left;font-size:0.9em}} th{{background:#f9fafb}}
h1{{border-bottom:2px solid #e5e7eb;padding-bottom:6px}} h2{{margin-top:28px;color:#111}}
@media(max-width:700px){{nav{{position:relative;width:auto;height:auto}} main{{margin-left:0}}}}
</style></head><body>
<nav><h3>Flatland Guide</h3><ul>{nav}</ul><p><a href="/docs">Swagger /docs</a> · <a href="/openapi.json">OpenAPI</a></p><p><a href="/guide?format=json">JSON</a></p></nav>
<main>{content}</main></body></html>
"""


def build_guide_html(app: Any) -> str:
    """Assemble full guide HTML with nav + all sections + auto tables."""
    api_html = _md_to_html("# API reference\n\nAuto-generated from live OpenAPI (`/openapi.json`).") + _api_table(app) + _md_to_html("\nInteractive docs at [/docs](/docs).\n")
    laws_html = _md_to_html("# God laws\n\nEvery law in `GodLaws` (`protocol.py:108`) with type/range/default. God sets via `POST /api/laws`.") + _god_laws_table()
    sections = [
        ("how-the-world-works", "How the world works", _md_to_html(HOW_IT_WORKS_MD)),
        ("codebase-map", "Codebase map", _md_to_html(CODEBASE_MAP_MD)),
        ("data-model-protocol", "Data model & protocol", _md_to_html(DATA_MODEL_MD)),
        ("api-reference", "API reference", api_html),
        ("god-laws", "God laws", laws_html),
        ("configuration-ops", "Configuration & ops", _md_to_html(CONFIG_OPS_MD)),
    ]

    nav_items = []
    content_parts = []
    for slug, title, html_body in sections:
        nav_items.append(f'<li><a href="#{slug}">{html.escape(title)}</a></li>')
        content_parts.append(f'<section id="{slug}">{html_body}</section>')

    # Add roadmap linking back to TODO.md
    roadmap_md = f"# Roadmap\n\nSee [TODO.md](../TODO.md) for full task list. This guide is auto-generated; `#{len(sections)}` sections + `{len(GodLaws.model_fields)}` laws + `{len(app.routes)}` routes."
    content_parts.append(f'<section id="roadmap">{_md_to_html(roadmap_md)}</section>')
    nav_items.append('<li><a href="#roadmap">Roadmap</a></li>')

    nav_html = "\n".join(nav_items)
    content_html = "\n<hr/>\n".join(content_parts)
    return GUIDE_TEMPLATE.format(nav=nav_html, content=content_html)

