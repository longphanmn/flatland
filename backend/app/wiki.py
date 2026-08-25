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
> Built and refined using **OpenCode** and **Antigravity** · Developed from the core ideas of **Edwin A. Abbott's *Flatland: A Romance of Many Dimensions*** (1884).

Flatland is an autonomous 2D artificial life and world simulation developed from the foundational mathematical and spatial ideas of Edwin A. Abbott's 1884 classic *Flatland*. 

### Design Philosophy
This project is **developed from the Flatland idea rather than mimicking the book literally**. It adopts Abbott's core premises — 2D planar constraints, geometric vertex hierarchies, atmospheric perception, and higher-dimensional observation — as a foundation to create a **living, evolutionary artificial life ecosystem that organically changes and expands over time**.

### Core Architecture & Systems
- **The Sphere (God Model)**: The Sphere (God) sets global **laws of nature** (carrying capacity, food growth, metabolism, disease, climate) from Spaceland, never intervening in individual lives. All behavior is 100% emergent.
- **Botanical Ecology & Functional Nutrition**: 6 diverse plant species (`grass`, `grain`, `berry`, `medicinal_herb`, `mushroom`, `poisonous`) with distinct caloric densities, decay clocks, infection remedy effects, and targeted health-based foraging preferences.

- **Cognitive Agency & Clan Social Intelligence**: Multi-objective utility AI replaces rigid if/else trees (evaluating survival, duty, traits, and kin needs); spatial waypoint mental maps; tactical soldier phalanxes, line kiting maneuvers, interpersonal trust-based buddy pairing, autonomous clan task boards (dynamic labor division), governance archetypes (Monarchy, Theocracy, Junta, Republic), adaptive bylaws (winter rationing, martial law), calculated Casus Belli, inter-clan trade caravans, and annual autumn harvest festivals.
- **Autonomous Evolution & Culture**: 6 heritable personality archetypes (`brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder`), craftable tools (spears, baskets, herb poultices, chieftain crowns), 4 mastery skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿), earned dynamic titles, oral lore passed from elders to youth in houses, and live thought bubbles.
- **Realistic Energy & Metabolism**: Infant low metabolism ($0.45\\times$ energy decay), combat stamina expenditure, and autonomous field food reserve management via baskets.
- **Settlements & Diplomacy**: Walled houses with creature-sized doors, multi-house clan territories, settlement food larders, mutual coalitions, tributary pacts, and schisms.
- **Real-Time Synchronization**: Deterministic fixed-rate engine loop streaming state over WebSocket (`/ws`) at ~30–60 FPS with durable SQLite historical chronicle storage.
"""






FLATLAND_BOOK_COMPARISON_MD = """
# Flatland: The Novella vs. The Simulation

A comparative study between **Edwin A. Abbott’s 1884 satirical classic *Flatland: A Romance of Many Dimensions*** and this autonomous artificial life simulation.

---

## 1. Caste, Geometry & Social Hierarchy

| Dimension | Abbott’s Book (*Flatland*, 1884) | Our Application (*Flatland Simulator*) |
| :--- | :--- | :--- |
| **Hierarchy Principle** | *"Configuration makes the man."* Social status is strictly determined by the number of sides and regularity of angles. | Entities inherit exact geometric castes based on vertex count (N-gons) and regularity. |
| **Women (Lines)** | Straight lines with no angular width. Because they are practically invisible head-on and razor-sharp, they are legally required to make a continuous "peace cry" and use dedicated side doors. | Rendered as 1D segments (`shape: 'line'`). Distinct agility, movement, and domestic shelter dynamics. |
| **Working Class / Soldiers** | Isosceles triangles with narrow, sharp vertex angles (dangerous, volatile, prone to rebellions). | **Soldiers** (`#ff7b72`): Sharp combatants with boosted attack, military discipline, and perimeter defense behavior. |
| **Artisans & Middle Class** | Equilateral triangles (3 equal sides) — stable and respectable tradespeople. | **Artisans** (3–4 sides, `#f2cc60`): Farmers, foragers, and builders responsible for harvesting and maintaining houses. |
| **Gentlemen & Professionals** | Squares (4 sides) and Pentagons (5 sides) — the middle/upper administrative classes. | **Gentlemen** (4 sides, `#ffa657`) and **Professionals** (5 sides, `#d2a8ff`): Administrative and specialized roles. |
| **Nobility** | Hexagons (6 sides) and higher polygons — aristocrats and statesmen. | **Nobles** (6–8 sides, `#79c0ff`): High influence and lineage priority. |
| **Priesthood (Circles)** | Polygons with so many sides (≥ 24 to hundreds) that their vertices are imperceptible, forming smooth circles. They govern religion, law, and morality. | **Priests** (≥ 24 sides, `#e6edf3`): Emit soothing auras, heal injured or infected clanmates, and resist disease. |


---

## 2. The "Law of Nature" & Generational Ascent

- **In the Book**:
  - Abbott establishes the **"Law of Upward Development"**: A male child of a regular polygon almost always inherits **one more side** than his father (e.g., a Square fathers a Pentagon, whose son becomes a Hexagon), lifting the lineage toward circular Priesthood over generations.
  - Rare **"Irregulars"** (whose sides/angles do not match) are viewed as societal threats and sent to state institutions or executed.
- **In the App**:
  - **Generational Evolution**: Offspring inherit ancestral traits with a probabilistic side increment (`sides += 1`), simulating the gradual generational ascent toward circular perfection.
  - **Irregularity & Demotion**: Entities that develop genetic irregularity or undergo trauma have their irregularity tracked and are judged/demoted or marked with distinct visual indicators.
  - **Dynastic Lineage**: The Family Tree tracks mother, father, and generational pedigree across decades of world history.

---

## 3. Sight Recognition, Weather & Perception

- **In the Book**:
  - In a 2D world, all inhabitants look like flat lines from the edge!
  - In the **Foggy South**, Flatlanders rely on **"Sight Recognition"** — judging the angle and distance of an approaching polygon by how quickly its edges fade into the atmospheric fog.
  - In the **Clear North**, they must rely on **"Feeling"** (touching vertices with fingertips).
- **In the App**:
  - **Dynamic Weather Engine**: Simulates **Clear**, **Fog**, **Rain**, and **Storm** states.
  - **Atmospheric Vision**: Fog and storms dynamically restrict creature vision radii (`sight_radius`), forcing entities to rely on local spatial queries and nearby auditory alarms (`signals`).
  - **Day/Night & Lighting**: The ambient illuminance curves shift through dawn, noon, dusk, and pitch-black night, restricting wandering and driving creatures into their shelters.

---

## 4. Housing, Settlements & Territorial Architecture

- **In the Book**:
  - Houses are strictly pentagonal or hexagonal, with specific entrances: a smaller rear entrance for lines (women) and a main entrance for polygons.
- **In the App**:
  - **Settlement Economy**: Houses are physical 2D structures with precise interior boundaries, oriented doors (`north`, `east`, `south`, `west`), and bed capacities.
  - **Single Main House Invariant**: Each clan establishes exactly **one Main House / HQ** (the Leader's residence) with surrounding outpost shelters.
  - **Shelter Dynamics**: Creatures seek refuge inside houses to sleep at night, protect against winter frostbite, heal from chills, and educate infant offspring.
  - **Doorway Entry & Exit Navigation**: Creatures calculate vector standoff waypoints to transition smoothly through doorway openings when entering shelter at dusk or exiting to forage and explore at dawn, preventing indoor wall trapping.


---

## 5. Clan Diplomacy, Totems & Autonomous Society

While Abbott’s book portrays a centralized Victorian government, our app layers an **evolutionary social simulation**:

- **Tribal Totems & Specialization**:
  - Clans worship distinct totems (🐺 Wolf, 🐻 Bear, 🦅 Eagle, 🦌 Stag, 🐍 Serpent, 🦉 Owl), shifting personality traits and societal balance between warriors, farmers, and scavengers.
- **Diplomacy, Tributes & War**:
  - Dynamic clan relations with wars, peace treaties, tribute subjugation, and schisms.
- **Personal Autonomy & Inventory**:
  - Independent personality archetypes (Brave, Cautious, Altruistic, Greedy, Explorer, Builder) with personal foraging baskets, tools (spears, crowns, herb poultices), and emergency self-preservation eating.

---

## 6. The Higher Dimension: The User as "The Sphere"

The most profound connection between the app and the book is the **role of the user**:

- In *Flatland*, the protagonist **A Square** is visited by **A Sphere** from the 3D *Spaceland*, who can look down from the Z-axis, see into locked rooms, view internal organs, and manipulate the 2D world with god-like omnipresence.
- **In our App**:
  - **You are the Sphere (God)**: As the observer on your screen, you look down on Flatland from Spaceland (the third dimension).
  - **The Sphere Panel**: You hold the power of The Sphere to alter the "Laws of Nature" in real-time — toggling famine, changing food growth multipliers, curing or spreading plagues, introducing winter freezes, or blessing clans with prosperity.

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
:root{{color-scheme:dark;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
*{{box-sizing:border-box}}
body{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;margin:0;color:#c9d1d9;background:#0b0f14;line-height:1.6}}
a{{color:#58a6ff;text-decoration:none}} a:hover{{text-decoration:underline}}
pre{{background:#161b22;padding:12px;overflow:auto;border-radius:6px;border:1px solid #30363d;font-size:13px;color:#e6edf3}}
code{{background:#161b22;padding:2px 5px;border-radius:4px;font-size:0.9em;border:1px solid #21262d;color:#ffa657}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:12px;display:block;overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid #30363d;border-radius:6px}}
th,td{{border:1px solid #21262d;padding:8px 10px;text-align:left;white-space:nowrap}}
th{{background:#161b22;color:#e6edf3;position:sticky;top:0;font-weight:600;border-bottom:1px solid #30363d}}
td{{background:#0d1117}}
tr:hover td{{background:#161b22}}
h1{{border-bottom:1px solid #21262d;padding-bottom:8px;color:#e6edf3;font-size:20px;letter-spacing:0.04em}}
h2{{margin-top:28px;color:#e6edf3;font-size:16px;border-left:3px solid #e3b341;padding-left:8px}}
h3{{color:#e6edf3;font-size:14px}}
.search{{width:100%;padding:8px 10px;border-radius:6px;border:1px solid #30363d;background:#161b22;color:#e6edf3;margin:8px 0;font-size:13px;font-family:inherit}}
.search:focus{{outline:none;border-color:#58a6ff}}
.badge{{display:inline-block;padding:3px 8px;border-radius:6px;font-size:11px;border:1px solid #30363d;background:#161b22;color:#8b949e;margin:2px}}
.layout{{display:grid;grid-template-columns:280px 1fr;min-height:100vh}}
nav{{background:#0d1117;border-right:1px solid #21262d;padding:16px;overflow-y:auto;position:sticky;top:0;height:100vh;scrollbar-width:thin}}
main{{padding:24px;max-width:980px;overflow-y:auto;background:#0b0f14}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin:8px 0}}
button{{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:4px 10px;border-radius:6px;font-family:inherit;font-size:12px;cursor:pointer}}
button:hover{{background:#30363d;color:#fff}}
hr{{border:0;border-top:1px solid #21262d;margin:20px 0}}
@media(max-width:800px){{
  .layout{{grid-template-columns:1fr}}
  nav{{position:relative;height:auto;border-right:none;border-bottom:1px solid #21262d}}
  main{{padding:16px}}
  table{{font-size:11px}}
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
<div class="card" style="position:sticky;top:0;z-index:2;display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:-24px -24px 16px -24px;padding:12px 16px;border-radius:0;border-left:none;border-right:none;border-top:none"><span class="badge">{laws} laws</span><span class="badge">{routes} routes</span><span class="badge">{presets} presets</span><span style="margin-left:auto;font-size:12px;color:#8b949e">The Sphere sets laws, never a life · <a href="/guide">Guide</a></span></div>
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
    laws_html = _md_to_html("# Laws of the Sphere\n\nEvery `GodLaws` field — type/range/default. Set via `POST /api/laws` or presets.") + _god_laws_table()
    presets_html = _md_to_html("# Presets — one-click worlds\n\nSustainable is the 1000-day gentle world. Apply via The Sphere panel or `POST /api/presets/{name}?reset`.") + _presets_table()
    sections = [
        ("overview", "Overview", _md_to_html(WIKI_OVERVIEW_MD)),
        ("book-comparison", "Flatland Book vs Simulation", _md_to_html(FLATLAND_BOOK_COMPARISON_MD)),
        ("quickstart", "Quickstart", _md_to_html(CONFIG_OPS_MD.split("## Run & deploy")[0])),
        ("how-the-world-works", "How the world works", _md_to_html(HOW_IT_WORKS_MD)),
        ("sustainability", "Sustainability", _md_to_html(SUSTAINABILITY_MD)),
        ("performance", "Performance", _md_to_html(PERFORMANCE_MD)),
        ("codebase-map", "Codebase map", _md_to_html(CODEBASE_MAP_MD)),
        ("data-model-protocol", "Data model & protocol", _md_to_html(DATA_MODEL_MD)),
        ("god-laws", "Laws of the Sphere", laws_html),
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
    "house_capacity": "beds in an 8×8 hall (12) — scales with floor area (small huts have fewer beds, max houses capped at 16 beds); overflow spills to the nearest roof with space",

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
    "theology_enabled": "the 8 Sacred Avatars of the Sphere: settled clans consecrate shrines, the devout tithe at dawn & dusk, faith works miracles, shrines chime when laws change, and high faith raises temples",
    "tithe_rate": "fraction of max energy offered at the shrine each dawn & dusk (0.04); priests tithe double — fills the clan faith pool",
    "temple_faith_cost": "clan faith spent to raise a shrine into a glowing Temple whose blessing aura covers all territory (400)",
    "cannibalism_hunger_ratio": "only creatures below this energy fraction may eat the living (0.15) — sated/hungry never do",
    "cannibalism_energy": "energy gained per desperate kill (45) — the victim leaves a partial corpse",
    "kin_stigma": "relation hit between a kin-eater's outcast band and their former clan (40) — they become rivals",
    # §AM agriculture
    "agriculture_enabled": "seed pouches from wild harvests, cultivated farm plots near the settlement (2× growth, 2.5× yield), weeding & tending, irrigation furrows by fertile groves",
    "granaries_enabled": "a dry roofed store: sated harvesters lay grain & cured berries by (35%), starving members withdraw, feasts burn a quarter",
    "granary_capacity": "units one clan granary holds (400) — feasts fire at ≥80% fill; raids & markets & caravans move it",
    "soil_depletion_enabled": "monocropping exhausts the living soil grid; corpses, withered plants and farmer compost restore it",
    "banquets_enabled": "granary ≥80% feeds a feast: energy, cheer, warmer relations and +30% fertility while it lasts",
    # §AN communication, language & diplomacy
    "vocalizations_enabled": "priest liturgy calms panic, women's peace-hum parts crowds, soldiers' war-chirps rally allies onto flagged targets, artisan chimes gift basket food, touching vertices builds trust",
    "scent_enabled": "foragers drop scent trails home from rich finds; violent deaths and ruins leave danger scent the young learn to avoid",
    "envoys_enabled": "peaceful leaders send banner-carrying emissaries to rival houses (+15 relations on delivery); clans raise boundary stones that ring warning chimes at trespassers",
    "markets_enabled": "allied neighbours found neutral trading posts at shared borders and barter surplus every 240 ticks; peddler caravans carry goods and news between distant settlements",
    "omens_enabled": "at each season turn a shrine priest proclaims what comes; worshippers who hear it head home prepared",
    "dialect_drift_enabled": "isolated clans drift apart in speech — strangers understand each other less the further their dialects split; allies converge on a shared tongue",
    # §AQ physics ecosystem
    "hearths_enabled": "kin buy hearth fuel from the clan larder; a lit hearth warms its roof past comfort through winter and night — unfed, the fire goes dark",
    "rivers_enabled": "horizontal channels cross the land: fords cost energy, the current sweeps infants and the wounded downstream, rain floods the banks and leaves fertile silt; builders span planks and raise dams",
    "river_count": "channel bands across the map at world creation (2) — applies to new worlds",
    "relief_enabled": "the land has height: uphill travel burns energy and slows the stride, cliffs deal fall damage, rain can slide steep slopes, and well-walked ground packs into fast roads that grow nothing",
    "structural_enabled": "storms and floodwater wear buildings down; builders near a roof mend it; a spent roof collapses to ruin",
    "rubble_blocking_enabled": "collapsed ruins leave rubble that bars the ground until builders clear the lot",
}

def get_wiki_json(app: Any) -> dict:
    from .main import PRESETS
    return {
        "overview": WIKI_OVERVIEW_MD,
        "book_comparison": FLATLAND_BOOK_COMPARISON_MD,
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

