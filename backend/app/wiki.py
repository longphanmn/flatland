"""Wiki — richer living docs than /guide, with presets, sustainability & API playground.

Backend-rendered HTML at /wiki and JSON at /api/wiki. Frontend Wiki.tsx fetches the JSON.
"""

import html
import re
from typing import Any

from .config import Config
from .protocol import GodLaws
from .guide import _api_table, _god_laws_table, _md_to_html, CODEBASE_MAP_MD, CONFIG_OPS_MD, DATA_MODEL_MD, HOW_IT_WORKS_MD

# Reuse guide helpers but add wiki-specific sections


SUSTAINABILITY_MD = """
# Sustainability — the 1000-day world

The world self-balances for 1000+ days at 400–500 head when tuned gentle.

## Defaults vs Presets

- **Defaults** (what you get on fresh boot): `food_count=70`, `season_length=14400` (12 days), `house_capacity=12`, `winter_food_mult=0.5` (harsh). Survives ~48 days deterministic seed 42.
- **Sustainable preset** (`POST /api/presets/sustainable?reset=true`): `food 70`, `winter 0.7` (soft lean), `carrying 450`/`max 550` (plateau not churn), `predation`/`war`/`disease` ON but gentle (bite/attack 40 wound not kill, pred ratio 0.03, outbreak 0.0001, recovery 0.025, poison 0), `drift 2.5`/`rivalry -80`/`trespass 0` (calm society). Apply via God panel → Presets.

## Presets

- **sustainable** 🌿 — 1000-day gentle, rare war, wound not kill. One click 1000-day.
- **chaos** 🔥 — famine, predators, wars, plagues, fires, schism. Stress test.
- **extinction** 💀 — 30 food, 0.3 winter, high decay. Extinction in days.

Use: `curl -X POST localhost:8000/api/presets/sustainable?reset=true` or God panel buttons.
"""

PERFORMANCE_MD = """
# Performance — 500 head @ 10–20 tps on N150

- **World**: fixed `cell_size=8.0` (was `max(4,perceive)`), toroidal wrap handling for correct edge queries.
- **Simulation**: per-tick cache ` _cached_creatures` + ` _clan_members` (was 15 O(n) scans), live pop filter, throttled broadcast ~30 Hz.
- **Frontend**: DPR capped 1.5, culled off-screen (visible bounds), merged 4 entity passes →1, batched draws.

See `world.py:32`, `simulation.py:155`, `main.py:127`, `CanvasRenderer.tsx:122`.
"""

WIKI_OVERVIEW_MD = """
# Flatland Wiki

A 2D world of geometric castes (Soldier, Artisan, Gentleman, Professional, Noble, Priest, Woman) plus predators/herbivores. Creatures wander, eat, shelter, age, mate, and die. God sets **laws**, never touches a life — everything else emerges.

- **Live world**: `GET /api/state` + WebSocket `/ws` (`hello` → `state` every tick, throttled ~30 Hz)
- **God laws**: `GET /api/laws` / `POST /api/laws?persist` — see God laws table
- **Presets**: `GET /api/presets` / `POST /api/presets/{sustainable|chaos|extinction}?reset`
- **History**: `GET /api/history?since&limit`, `GET /api/worlds`, `GET /api/clans`, `GET /api/plots`
- **Guide**: `/guide` (backend HTML) and `/wiki` (this page)
- **Interactive docs**: `/docs` (Swagger) + `/openapi.json`
"""


def _presets_table() -> str:
    from .main import PRESETS  # late import to avoid cycle
    rows = []
    for name, laws in PRESETS.items():
        preview = ", ".join(f"{k}={v}" for k, v in list(laws.items())[:6])
        if len(laws) > 6:
            preview += f" … +{len(laws)-6} more"
        rows.append(f"<tr><td><code>{html.escape(name)}</code></td><td>{html.escape(preview)}</td><td><code>POST /api/presets/{html.escape(name)}?reset=true</code></td></tr>")
    header = "<tr><th>Preset</th><th>Key laws</th><th>Apply</th></tr>"
    return f"<table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"


def _curl_examples() -> str:
    return _md_to_html("""
## Curl playground

```bash
# laws
curl localhost:8000/api/laws
curl -X POST localhost:8000/api/laws -H 'content-type: application/json' -d '{"food_count": 90}' 

# presets (1000-day one click)
curl -X POST localhost:8000/api/presets/sustainable?reset=true
curl -X POST localhost:8000/api/presets/chaos
curl -X POST localhost:8000/api/presets/extinction?reset=true

# state & history
curl localhost:8000/api/state | jq .tick
curl localhost:8000/api/history?limit=5 | jq
curl localhost:8000/api/worlds | jq
curl localhost:8000/api/clans | jq

# control
curl -X POST localhost:8000/api/control -H 'content-type: application/json' -d '{"action":"pause"}'
curl -X POST localhost:8000/api/control -d '{"action":"reset"}'

# websocket (live)
# ws://localhost:8000/ws  → {"type":"hello"} then {"type":"state"} throttled ~30Hz
# send {"action":"pause"} / {"action":"set_speed","value":20}
```
""")


WIKI_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flatland — Wiki</title>
<style>
:root{{color-scheme:dark}}
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;color:#c9d1d9;background:#0d1117}}
nav{{position:fixed;top:0;left:0;width:260px;height:100vh;overflow:auto;background:#010409;border-right:1px solid #21262d;padding:16px}}
main{{margin-left:260px;padding:24px;max-width:960px}}
a{{color:#58a6ff;text-decoration:none}} a:hover{{text-decoration:underline}}
pre{{background:#161b22;padding:12px;overflow:auto;border-radius:6px;border:1px solid #30363d}}
code{{background:#161b22;padding:1px 4px;border-radius:3px;font-size:0.9em;border:1px solid #21262d}}
table{{border-collapse:collapse;width:100%;margin:12px 0}} th,td{{border:1px solid #30363d;padding:6px 8px;text-align:left;font-size:0.9em}} th{{background:#161b22;color:#e6edf3}}
h1{{border-bottom:1px solid #21262d;padding-bottom:6px;color:#e6edf3}} h2{{margin-top:28px;color:#e6edf3}} h3{{color:#e6edf3}}
.search{{width:100%;padding:8px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;margin:8px 0}}
.badge{{display:inline-block;padding:2px 6px;border-radius:10px;font-size:11px;border:1px solid #30363d;background:#161b22;color:#8b949e;margin-left:6px}}
@media(max-width:800px){{nav{{position:relative;width:auto;height:auto}} main{{margin-left:0}} table{{display:block;overflow-x:auto; -webkit-overflow-scrolling:touch}}}}
</style></head><body>
<nav>
<h3>Flatland Wiki</h3>
<input id="q" class="search" placeholder="Search laws, routes, docs… ( / )" oninput="filterWiki(this.value)">
<ul style="list-style:none;padding:0;margin:8px 0">{nav}</ul>
<p><a href="/docs">Swagger /docs</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/guide">Guide</a></p>
<p><a href="/api/wiki">JSON</a> · <a href="/">← Live world</a></p>
<div style="margin-top:12px;font-size:12px;color:#8b949e">Presets: <a href="#" onclick="applyPreset('sustainable');return false">sustainable</a> · <a href="#" onclick="applyPreset('chaos');return false">chaos</a> · <a href="#" onclick="applyPreset('extinction');return false">extinction</a></div>
</nav>
<main>
<div style="position:sticky;top:0;background:#0d1117;padding:8px 0;z-index:2;border-bottom:1px solid #21262d;margin:-24px -24px 16px -24px;padding-left:24px;display:flex;gap:12px;align-items:center"><span class="badge">{laws} laws</span><span class="badge">{routes} routes</span><span class="badge">{presets} presets</span><span style="margin-left:auto;font-size:12px;color:#8b949e">God sets laws, never a life · <a href="/guide">Guide</a></span></div>
{content}
<hr/><p style="font-size:12px;color:#8b949e">Generated from live code — <code>Config</code> defaults + <code>GodLaws</code> + <code>app.routes</code>. See <a href="/guide">/guide</a> for minimal guide.</p>
</main>
<script>
function filterWiki(q){{
  q=q.toLowerCase();
  document.querySelectorAll('main section, main h1, main h2, main table tr, main p, main li').forEach(el=>{{
    if(!q){{ el.style.display=''; return; }}
    const txt=(el.textContent||'').toLowerCase();
    // only hide rows/sections that don't match, keep headers
    if(el.tagName==='TR' || el.tagName==='LI' || el.tagName==='P') el.style.display = txt.includes(q) ? '' : 'none';
  }});
  document.querySelectorAll('main section').forEach(sec=>{{
    const vis = [...sec.querySelectorAll('tr, li, p')].some(e=>e.style.display!=='none');
    // keep section visible if any child matches or title matches
    const title=(sec.querySelector('h1,h2')?.textContent||'').toLowerCase();
    sec.style.display = (vis || title.includes(q) || !q) ? '' : 'none';
  }});
}}
document.addEventListener('keydown',e=>{{ if(e.key==='/'){{ e.preventDefault(); document.getElementById('q')?.focus(); }}}});
async function applyPreset(name){{ const r=await fetch('/api/presets/'+name+'?persist=true',{{method:'POST'}}); const j=await r.json(); alert(name+' preset applied: '+JSON.stringify(j.laws).slice(0,200)); }}
</script>
</body></html>
"""


def build_wiki_html(app: Any) -> str:
    from .main import PRESETS
    api_html = _md_to_html("# API reference\n\nLive routes from `app.routes` + Swagger at [/docs](/docs). Try `curl` examples below.") + _api_table(app) + _curl_examples()
    laws_html = _md_to_html("# God laws\n\nEvery `GodLaws` field — type/range/default. Set via `POST /api/laws` or presets.") + _god_laws_table()
    presets_html = _md_to_html("# Presets — one-click worlds\n\nSustainable is the 1000-day gentle world. Apply via God panel or `POST /api/presets/{name}?reset`.") + _presets_table()
    sections = [
        ("overview", "Overview", _md_to_html(WIKI_OVERVIEW_MD)),
        ("quickstart", "Quickstart", _md_to_html(CONFIG_OPS_MD.split("## Run & deploy")[0])),
        ("how-the-world-works", "How the world works", _md_to_html(HOW_IT_WORKS_MD)),
        ("sustainability", "Sustainability", _md_to_html(SUSTAINABILITY_MD)),
        ("performance", "Performance", _md_to_html(PERFORMANCE_MD)),
        ("codebase-map", "Codebase map", _md_to_html(CODEBASE_MAP_MD)),
        ("data-model-protocol", "Data model & protocol", _md_to_html(DATA_MODEL_MD)),
        ("god-laws", "God laws", laws_html),
        ("presets", "Presets", presets_html),
        ("api-reference", "API reference", api_html),
        ("configuration-ops", "Configuration & ops", _md_to_html(CONFIG_OPS_MD)),
    ]
    nav_items = []
    content_parts = []
    for slug, title, body in sections:
        nav_items.append(f'<li><a href="#{slug}">{html.escape(title)}</a></li>')
        content_parts.append(f'<section id="{slug}">{body}</section>')
    # roadmap
    roadmap_md = f"# Roadmap\n\nSee `TODO.md` — {len(sections)} sections + {len(GodLaws.model_fields)} laws + {len(app.routes)} routes + {len(PRESETS)} presets. Wiki extends Guide with presets, sustainability & playground."
    content_parts.append(f'<section id="roadmap">{_md_to_html(roadmap_md)}</section>')
    nav_items.append('<li><a href="#roadmap">Roadmap</a></li>')

    nav_html = "\n".join(nav_items)
    content_html = "\n<hr/>\n".join(content_parts)
    return WIKI_TEMPLATE.format(nav=nav_html, content=content_html, laws=len(GodLaws.model_fields), routes=len(app.routes), presets=len(PRESETS))


LAW_HINTS_MD = {
    "food_count": "the world keeps this much food alive — bounty or famine (winter ×0.5, summer ×1.2)",
    "plant_growth_rate": "how fast plants mature (0.05) — berry 0.65×, mushroom 0.85×, poison 0.6×, season multiplies",
    "plant_spread_rate": "chance a mature plant seeds a nearby sprout each tick",
    "nutrient_cycle_rate": "corpse decay boost to nearby plants (0.65) — death feeds life",
    "poison_rate": "chance a new sprout is poisonous (0.01) — 1% sicken, berry heals +1, poison -30 health",
    "beast_ratio": "wild herbivores as fraction of creature density — grazers that feed predators",
    "diet_strictness": "0 omnivore, 1 strict — herbivore ignores meat, predator ignores plants",
    "territory_radius": "clan territory circle radius around house (14) — members steer home, trespass sours relations",
    "trespass_decay": "relation points lost per tick a rival trespasses inside territory",
    "house_decay_ticks": "abandoned house ticks before crumbling to ruin (2400 = 2 seasons)",
    "energy_decay_per_tick": "how fast all life burns without eating (0.025) — winter/rain adds 0.03 exposure if roofless",
    "energy_from_food": "base energy from a mature plant (32) — berry 48, mushroom 24, grass 32, poison 8",
    "perceive_radius": "base sight (20) — each caste scales it (Woman 0.8×, Priest 1.35×), night 0.6×, fog 0.6×, Eye totem 1.25×",
    "lifespan_mult": "scales every caste’s natural lifespan",
    "door_clearance": "doorways scale with the largest creature × this (1.5)",
    "house_min_size": "applies to houses built after the next reset (6)",
    "house_max_size": "applies to houses built after the next reset (10)",
    "adult_age": "creatures must be this many ticks old to mate (200)",
    "birth_rate": "chance per eligible pair per tick, before fertility (0.35)",
    "sex_ratio": "probability a child is a son (polygons ascend; daughters are lines)",
    "mutation_rate": "chance a son’s side count deviates ±1 from inheritance (0.05)",
    "euthanasia_threshold": "irregular children at/above this are consumed at adulthood, below it demoted (0.7)",
    "carrying_capacity": "above this population, fertility fades gradually (80)",
    "max_population": "hard cap — no births beyond (140)",
    "house_capacity": "beds per house (8) — overflow sleeps outside and suffers exposure",
    "exposure_drain": "energy lost per tick outdoors in rain/storm/night (0.03)",
    "rest_recovery_mult": "health regen multiplier when sleeping indoors (2.0)",
    "rain_growth_mult": "rain/storm boost to plant growth (1.25) — soaked ground regrows faster",
    "fog_mushroom_mult": "fog boost to mushroom growth (1.35) — the decomposer tier loves mist",
    "storm_plant_damage": "chance a storm strips growth from exposed plants (0.02) — occasionally uproots",
    "chill_rate": "chill built per tick unsheltered in rain/storm/winter night (0.04)",
    "chill_threshold": "chill at which creature sickens (12) — shelter sheds 2.5× faster",
    "chill_drain": "health drain per tick when chilled (0.18) — death cause chill",
    "wet_disease_mult": "wet/cold catch disease faster and recover slower (1.5×)",
    "age_length": "ticks per age (12000 = 5 seasons) — Golden×1.25 food, Ice×0.55 food + chill, Chaos×1.8 mutation, Plague×1.8 disease",
    "culture_spread_rate": "allied clans within territory adopt same culture with this chance/tick (0.005)",
    "trait_mutation_rate": "chance mutation adds heritable trait greedy/peaceful/paranoid/bold (0.02) — bold war, paranoid flee, greedy food",
    "fire_rate": "chance a random mature plant ignites each tick (0.0005) — storm lightning raises to 0.002",
    "fire_spread_rate": "spread to neighboring plants within 6 (0.08) — kills creatures/plants, ash fertilizes",
    "disaster_rate": "meteor/flood stochastic gated by this per tick (0.0003) — crater/water reshapes terrain",
    "signal_radius": "heard within this range (12) — clan-mates respond strongly, strangers weakly",
    "food_call_rate": "well-fed finds food → calls with this chance/tick (0.08)",
    "alarm_call_rate": "sees predator → alarm call chance/tick (0.12)",
    "food_memory_ttl": "ticks a creature remembers last food position (300)",
    "winter_food_mult": "winter bounty × winter_food_mult (0.7 gentle, 0.5 harsh, 0.3 extinction) — lean season target = food_count × winter_food_mult",
    "schism_threshold": "fraction unhappy (starving/homeless) to split (0.4)",
    "schism_min_pop": "minimum clan population to consider schism (4)",
}

def get_wiki_json(app: Any) -> dict:
    from .main import PRESETS
    return {
        "overview": WIKI_OVERVIEW_MD,
        "sustainability": SUSTAINABILITY_MD,
        "performance": PERFORMANCE_MD,
        "how_it_works": HOW_IT_WORKS_MD,
        "codebase_map": CODEBASE_MAP_MD,
        "data_model": DATA_MODEL_MD,
        "config_ops": CONFIG_OPS_MD,
        "laws": list(GodLaws.model_fields.keys()),
        "routes": [getattr(r, "path", "") for r in app.routes],
        "presets": PRESETS,
        "law_details": {name: {"type": str(f.annotation), "default": getattr(Config(), name, None) if hasattr(Config(), name) else None, "hint": LAW_HINTS_MD.get(name, "")} for name, f in GodLaws.model_fields.items()},
    }
