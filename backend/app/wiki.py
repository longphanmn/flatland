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

The world self-balances for 1000+ days at 500–800 head when tuned to Goldilocks balance.

## Presets

- **balance** ⚖️ (Default) — The Goldilocks condition: 220 food, carrying 600, max 800 pop. All 15+ simulation mechanics active in gentle, harmonious proportions (mild war, rare predation, mild plagues, gentle winters, and thriving multi-generational clans).
- **sustainable** 🌿 — 1000-day gentle: 450 food, carrying 2200, rare war/predation, calm society. Multi-generational flourishing.
- **chaos** 🔥 — 320 food, carrying 800, max 1200: famine, predators, wars, plagues, fires, schism. Stress test.
- **extinction** 💀 — 100 food, carrying 250, max 400: 0.3 winter, high decay. Extinction in days.
- **boom** 🚀 — 650 food, carrying 3500, max 5000: massive population boom scale test for low-end hardware (e.g. Intel N150).

Use: `curl -X POST localhost:8000/api/presets/balance?reset=true` or God panel buttons.
"""

PERFORMANCE_MD = """
# Performance & Scale — 1000+ head @ 60 FPS

- **Zero-Allocation Spatial Hash**: Pre-allocated 1D bucket list in `world.py` eliminates tuple allocations and dictionary re-hashing per tick; `query_radius` uses squared-distance early-exit without `math.hypot`.
- **Fast Mate Discovery**: `simulation.py:_reproduce` queries nearby partners via the spatial index in $O(1)$ instead of $O(N^2)$ nested roster scans.
- **Snapshot Caching**: Static terrain and rocks are pre-cached, eliminating redundant dictionary list copies on every broadcast frame.
- **Batched Canvas 2D Rendering**: `CanvasRenderer.tsx` batches drawing passes by caste, plant variant, and house primitives with inline trigonometric vertex transforms, completely eliminating per-creature `ctx.save()` / `ctx.restore()` overhead (draw calls reduced from 20,000+ to ~30-50).
- **Dynamic Level of Detail (LOD)**: Zoom-dependent rendering skips fine-grained glyph text and ripples when zoomed out, maintaining a solid 60 FPS even with dense populations.
- **Decoupled React State**: High-frequency simulation snapshots stream directly into mutable refs at 60 FPS for canvas rendering, while React virtual DOM reconciliation (HUD stats, charts) is throttled to ~6 Hz to keep the main browser thread light and responsive.

See `world.py:38`, `simulation.py:2680`, `CanvasRenderer.tsx:370`, `App.tsx:230`.
"""

WIKI_OVERVIEW_MD = """
# Flatland Wiki & Encyclopedia

> **Developed by [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Built and refined using **OpenCode** and **Antigravity** · Inspired by **Edwin A. Abbott's *Flatland: A Romance of Many Dimensions*** (1884).

Flatland is an autonomous 2D artificial life and world simulation of geometric castes (Soldier, Artisan, Gentleman, Professional, Noble, Priest, and Woman) plus apex predators and wild herbivores. Creatures explore, forage, farm, master skills, establish multi-generational clan settlements, and evolve across generations under immutable natural laws.

### Core Architecture & Systems
- **The God Model**: God sets global **laws of nature** (carrying capacity, food growth, metabolism, disease, climate) but never intervenes in individual lives. All behavior is emergent.
- **Autonomous Evolution & Culture**: 6 heritable personality archetypes (`brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder`), craftable tools (spears, baskets, herb poultices, chieftain crowns), 4 mastery skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿), earned dynamic titles, oral lore passed from elders to youth in houses, and live thought bubbles.
- **Realistic Energy & Metabolism**: Infant low metabolism ($0.45\times$ energy decay), combat stamina expenditure, and autonomous field food reserve management via baskets.
- **Settlements & Diplomacy**: Walled houses with creature-sized doors, multi-house clan territories, settlement food larders, mutual coalitions, tributary pacts, and schisms.
- **Real-Time Synchronization**: Deterministic fixed-rate engine loop streaming state over WebSocket (`/ws`) at ~30–60 FPS with durable SQLite historical chronicle storage.

### Endpoints & Interfaces
- **Live World UI**: `http://localhost:5173` (interactive 60 FPS HTML5 canvas with real-time HUD and controls).
- **Terminal UI**: Textual TUI (`cd backend && uv run python -m tui`) with camera tracking and filterable chronicle.
- **REST API & Swagger**: `GET /api/state`, `POST /api/laws`, `GET /api/presets`, `GET /api/history` at `/docs`.
- **Living Guide & Wiki**: `/guide` (backend HTML) and `/wiki` (interactive documentation).
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
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flatland — Living Wiki — World Simulation by Long Phan (long@minhnhan.in)</title>
<meta name="description" content="Official living wiki and system encyclopedia for Flatland: 2D autonomous World Simulation by Long Phan (long@minhnhan.in).">
<meta name="keywords" content="Flatland, World Simulation, Wiki, Presets, Simulation Mechanics, Long Phan, long@minhnhan.in, Artificial Life">
<meta name="author" content="Long Phan <long@minhnhan.in>">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://world.minhnhan.in/wiki">
<meta property="og:title" content="Flatland — Living Wiki | World Simulation by Long Phan">
<meta property="og:description" content="Official living wiki, presets, and mechanics documentation for Flatland World Simulation by Long Phan (long@minhnhan.in).">
<meta property="og:url" content="https://world.minhnhan.in/wiki">
<meta property="og:type" content="article">
<style>
:root{{color-scheme:dark}}
*{{box-sizing:border-box}}
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:0;color:#c9d1d9;background:#0d1117;line-height:1.6}}
a{{color:#58a6ff;text-decoration:none}} a:hover{{text-decoration:underline}}
pre{{background:#161b22;padding:12px;overflow:auto;border-radius:6px;border:1px solid #30363d;font-size:13px}}
code{{background:#161b22;padding:1px 4px;border-radius:3px;font-size:0.9em;border:1px solid #21262d;color:#e6edf3}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px;display:block;overflow-x:auto;-webkit-overflow-scrolling:touch}} th,td{{border:1px solid #30363d;padding:8px 10px;text-align:left;white-space:nowrap}} th{{background:#161b22;color:#e6edf3;position:sticky;top:0}} td{{background:#0d1117}}
h1{{border-bottom:1px solid #21262d;padding-bottom:8px;color:#e6edf3;font-size:22px}} h2{{margin-top:32px;color:#e6edf3;font-size:18px;border-left:3px solid #e3b341;padding-left:8px}} h3{{color:#e6edf3;font-size:15px}}
.search{{width:100%;padding:8px 10px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#e6edf3;margin:8px 0;font-size:14px}}
.badge{{display:inline-block;padding:3px 8px;border-radius:10px;font-size:11px;border:1px solid #30363d;background:#161b22;color:#8b949e;margin:2px}}
.layout{{display:grid;grid-template-columns:260px 1fr;min-height:100vh}}
nav{{background:#010409;border-right:1px solid #21262d;padding:16px;overflow:auto;position:sticky;top:0;height:100vh}}
main{{padding:24px;max-width:960px;overflow:auto}}
.card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px;margin:8px 0}}
@media(max-width:800px){{
  .layout{{grid-template-columns:1fr}}
  nav{{position:relative;height:auto;border-right:none;border-bottom:1px solid #21262d;}}
  main{{padding:16px}}
  table{{font-size:12px}}
}}
</style></head><body>
<div class="layout">
<nav>
<h3 style="margin:0 0 12px;color:#e6edf3">📖 Flatland Wiki</h3>
<input id="q" class="search" placeholder="Search laws, routes, docs… ( / )" oninput="filterWiki(this.value)">
<ul style="list-style:none;padding:0;margin:8px 0">{nav}</ul>
<p style="font-size:13px"><a href="/docs">Swagger /docs</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/guide">Guide</a></p>
<p style="font-size:13px"><a href="/api/wiki">JSON</a> · <a href="/">← Live world</a></p>
<div class="card" style="margin-top:12px;font-size:12px;color:#8b949e">Presets: <a href="#" onclick="applyPreset('sustainable');return false">🌿 sustainable</a> · <a href="#" onclick="applyPreset('chaos');return false">🔥 chaos</a> · <a href="#" onclick="applyPreset('extinction');return false">💀 extinction</a></div>
<div class="card" style="margin-top:12px;font-size:12px;color:#8b949e;border-color:#1f6feb">Developed by<br/><strong>Long Phan</strong><br/><a href="mailto:long@minhnhan.in">long@minhnhan.in</a><br/><a href="https://minhnhan.in">minhnhan.in</a> · <a href="https://world.minhnhan.in">world.minhnhan.in</a><br/><small style="color:#8b949e;display:block;margin-top:4px">Built with OpenCode & Antigravity<br/>Inspired by Edwin A. Abbott</small></div>
</nav>
<main>
<div class="card" style="position:sticky;top:0;z-index:2;display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:-24px -24px 16px -24px;padding:12px 16px;border-radius:0;border-left:none;border-right:none;border-top:none"><span class="badge">{laws} laws</span><span class="badge">{routes} routes</span><span class="badge">{presets} presets</span><span style="margin-left:auto;font-size:12px;color:#8b949e">God sets laws, never a life · <a href="/guide">Guide</a></span></div>
{content}
<hr/><p style="font-size:12px;color:#8b949e">Generated from live code — <code>Config</code> defaults + <code>GodLaws</code> + <code>app.routes</code>. See <a href="/guide">/guide</a> for minimal guide. · Developed by <strong>Long Phan</strong> — <a href="mailto:long@minhnhan.in">long@minhnhan.in</a> · <a href="https://minhnhan.in">minhnhan.in</a> · Built with OpenCode & Antigravity</p>
</main>
</div>
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
    "max_clans": "society granularity: -1 = one clan per house; N ≥ 1 clusters founders into N spatial clans (applies at reset)",
    "trespass_decay": "relation points lost per tick a rival trespasses inside territory",
    "house_decay_ticks": "abandoned house ticks before crumbling to ruin (2400 = 2 seasons)",
    "energy_decay_per_tick": "how fast all life burns without eating (0.025) — winter/rain adds 0.03 exposure if roofless",
    "energy_from_food": "base energy from a mature plant (32) — berry 48, mushroom 24, grass 32, poison 8",
    "perceive_radius": "base sight (20) — each caste scales it (Woman 0.8×, Priest 1.35×), night 0.6×, fog 0.6×, Eye totem 1.25×",
    "food_giveup_ticks": "a meal blocked by rock/wall is abandoned this many ticks (240) — the hungry give up and seek food elsewhere; 0 = never give up",
    "lifespan_mult": "scales every caste’s natural lifespan",
    "door_clearance": "doorways scale with the largest creature × this (1.5)",
    "house_min_size": "applies to houses built after the next reset (6)",
    "house_max_size": "applies to houses built after the next reset (10)",
    "adult_age": "creatures must be this many ticks old to mate (200)",
    "birth_rate": "chance per eligible pair per tick, before fertility (0.35)",
    "sex_ratio": "probability a child is a son (polygons ascend; daughters are lines)",
    "mutation_rate": "chance a son’s side count deviates ±1 from inheritance (0.05)",
    "euthanasia_threshold": "irregular children at/above this are consumed at adulthood, below it demoted (0.7)",
    "carrying_capacity": "above this population, fertility fades gradually (−1 scales with map area; 80 per 200×200)",
    "max_population": "hard cap — no births beyond (−1 scales with map area; 140 per 200×200)",
    "house_capacity": "beds in an 8×8 hall (12) — scales with floor area, so a small hut cannot hold a whole clan; overflow spills to the nearest roof with space",
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
    "knowledge_ttl": "ticks a learned fact stays in memory before it fades (600) — food spots, danger zones, enemy clans, safe homes",
    "knowledge_share_rate": "chance/tick to broadcast the freshest fact to clan-mates (0.05) — rumors arrive at half confidence per hop",
    "help_radius": "clan-mates rally to a help call within this range (12); defenders near the attacker soften its blows",
    "defense_weight": "damage reduction per defender mobbing the attacker (0.5)",
    "winter_food_mult": "winter bounty × winter_food_mult (0.7 gentle, 0.5 harsh, 0.3 extinction) — lean season target = food_count × winter_food_mult",
    "schism_threshold": "fraction unhappy (starving/homeless) to split (0.4)",
    "schism_min_pop": "minimum clan population to consider schism (4)",
    "coalition_threshold": "relation score at which a leader may fold another clan into a coalition (40) — strike one member and every mate turns on you",
    "coalition_min_size": "smallest viable coalition; smaller or soured blocs dissolve (2)",
    "larder_capacity": "energy a clan store at the settlement can hold (300) — surplus deposited, famine withdraws",
    "aid_rate": "chance/tick a full-bellied ally tops up a starving ally's larder (0.05)",
    "food_lifespan_ticks": "ticks a mature plant lives before it withers (9000) — mushroom 0.4×, grass ×1, berry 1.5×, poisonous 3×; withered plants fertilise the soil",
    "cannibalism_hunger_ratio": "only creatures below this energy fraction may eat the living (0.15) — sated/hungry never do",
    "cannibalism_energy": "energy gained per desperate kill (45) — the victim leaves a partial corpse",
    "kin_stigma": "relation hit between a kin-eater's outcast band and their former clan (40) — they become rivals",
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
