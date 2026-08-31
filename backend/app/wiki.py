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
# Sustainability — Multi-Generational Balance

The world self-balances across hundreds of days and multi-generational dynastic flourishing under tuned ecological and social equilibrium.

## Curated Presets

- **balance** ⚖️ (Default) — Goldilocks harmony tuned for **200–350 inhabitants** with 240 food, carrying capacity 350 (max 500), gentle wars, rare predation, agriculture, and flourishing multi-generational clans.
- **sustainable** 🌿 — 1000-day prosperous peace: abundant food (360), carrying capacity 450 (max 600), rich granaries, harvest festivals, and banquets.
- **theocracy** 🔮 — Age of the Sphere: sacred avatars, glowing temples, avatar miracles, 3D epiphanies, holy synods, and divine tithes.
- **warlords** ⚔️ — Clash of clans: imperial conquests, granary raids, house takeovers, territorial expansion, and defensive coalitions.
- **chaos** 🔥 — High predator ratio, lethal wars, wildfires, earthquakes, frequent plagues, and fast seasonal turnover.
- **extinction** 💀 — Severe famine (120 food), harsh winter (0.30×), high exposure decay, testing societal resilience under collapse.
- **boom** 🚀 — High reproduction, 500 food, carrying capacity 800 (max 1000) for monumental metropolis testing.

Use: `curl -X POST localhost:8000/api/presets/balance?reset=true` or use The Sphere (God Panel) preset selector.
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
- **The Sphere (God Model)**: The Sphere (God) sets global **laws of nature** (carrying capacity, food growth, metabolism, disease, climate) from Spaceland, never intervening in individual lives. Configured via a dedicated **🎯 Presets** selector and 6 streamlined **⚖️ Macro Domains** with live search and dual sliders. Organisms navigate continuously via 16-sensor raycasts and Micro-RNN neural actuators.
- **Botanical Ecology & Functional Nutrition**: 6 diverse plant species (`grass`, `grain`, `berry`, `medicinal_herb`, `mushroom`, `poisonous`) with distinct caloric densities, decay clocks, infection remedy effects, and targeted health-based foraging preferences.

- **Cognitive Agency & Clan Social Intelligence**: Multi-objective utility AI replaces rigid if/else trees (evaluating survival, duty, traits, and kin needs); spatial waypoint mental maps; tactical soldier phalanxes, line kiting maneuvers, interpersonal trust-based buddy pairing, autonomous clan task boards (dynamic labor division), governance archetypes (Monarchy, Theocracy, Junta, Republic), adaptive bylaws (winter rationing, martial law), calculated Casus Belli, inter-clan trade caravans, and annual autumn harvest festivals.
- **Autonomous Evolution & Culture**: 6 heritable personality archetypes (`brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder`), craftable tools (spears, baskets, herb poultices, chieftain crowns), 4 mastery skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿), earned dynamic titles, oral lore passed from elders to youth in houses, and live thought bubbles.
- **Realistic Energy & Metabolism**: Infant low metabolism ($0.45\\times$ energy decay), combat stamina expenditure, and autonomous field food reserve management via baskets.
- **Settlements & Diplomacy**: Walled houses with creature-sized doors, multi-house clan territories, settlement food larders, mutual coalitions, tributary pacts, and schisms.
- **Geometric Physics & Morphological Evolution (K∈[3,24])**: Polar genomes $(r_i,\\phi_i)$ $K\\in[3,24]$ (`KMAX 24`, `morphology_engine.py`) with SoA `physical_traits` trait baking ($A,P,I_{zz},\\theta_{\\min},asym,D_{mult}$) and SAT narrowphase (broadphase $r_{\\max}$ + circle fallback $K\\ge24$ & $asym<0.05$ + edge normals); annealing $\\lambda(g)$ blends Abbott templates → free evolution, energetic asymmetry, neural courtship, and extinction safeguards ($\\eta(N)$, Tier1/2/3 genesis, mercy).
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
<div class="card" style="margin-top:12px;font-size:12px;color:#8b949e">Presets: <a href="#" onclick="applyPreset('balance');return false">⚖️ balance</a> · <a href="#" onclick="applyPreset('sustainable');return false">🌿 sustainable</a> · <a href="#" onclick="applyPreset('theocracy');return false">🔮 theocracy</a> · <a href="#" onclick="applyPreset('warlords');return false">⚔️ warlords</a> · <a href="#" onclick="applyPreset('chaos');return false">🔥 chaos</a> · <a href="#" onclick="applyPreset('extinction');return false">💀 extinction</a> · <a href="#" onclick="applyPreset('boom');return false">🚀 boom</a></div>
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
    roadmap_md = f"# Roadmap\n\nSee `TODO.md` (active) + `docs/roadmap-archive.md` (completed) — {len(sections)} sections + {len(GodLaws.model_fields)} laws + {len(app.routes)} routes + {len(PRESETS)} presets. Wiki extends Guide with presets, sustainability & playground."
    content_parts.append(f'<section id="roadmap">{_md_to_html(roadmap_md)}</section>')
    nav_items.append('<li><a href="#roadmap">Roadmap</a></li>')

    nav_html = "\n".join(nav_items)
    content_html = "\n<hr/>\n".join(content_parts)
    return WIKI_TEMPLATE.format(nav=nav_html, content=content_html, laws=len(GodLaws.model_fields), routes=len(app.routes), presets=len(PRESETS))


LAW_HINTS_MD = {
    # Global Topology
    "boundary": "World border topology: wrap (seamless toroidal loop) vs clamp (solid collision walls).",

    # 1. Ecology & Survival
    "food_count": "Living food plants maintained across the world (summer ×1.2, winter ×0.5).",
    "energy_max": "Maximum metabolic energy capacity an organism can store (10–500).",
    "energy_decay_per_tick": "Baseline metabolic burn rate per tick without food (0.025).",
    "energy_from_food": "Base energy yield from harvesting a mature plant (berry 48, grass 32, mushroom 24, poison 8).",
    "plant_variants_enabled": "Master switch enabling botanical biodiversity across 6 distinct functional plant species.",
    "plant_growth_rate": "How fast sprouted plants mature into harvestable food (0.045).",
    "plant_spread_rate": "Probability per tick that a mature plant drops seeds into adjacent fertile ground (0.006).",
    "nutrient_cycle_rate": "Acceleration of plant growth near decomposing corpses (0.65) — death nourishes new life.",
    "poison_rate": "Probability a new wild sprout is poisonous (-30 HP damage on ingestion).",
    "food_decay_enabled": "Enables mature plants to naturally wither over time and fertilize the living soil.",
    "food_lifespan_ticks": "Ticks a mature plant lives before naturally withering into the living soil grid (8000).",
    "agriculture_enabled": "Enables seed gathering, cultivated farm plots (2× growth, 2.5× yield), irrigation furrows, and tending.",
    "granaries_enabled": "Enables communal settlement granaries to stockpile grain and berries against winter.",
    "granary_capacity": "Units of food a settlement granary can store (400) — feasts fire at ≥80% capacity.",

    # 2. Biology & Evolution
    "perceive_radius": "Base perception sight radius (16) — scaled by caste (Woman 0.8×, Priest 1.35×), night (0.6×), and fog (0.6×).",
    "eat_radius": "Physical contact distance required to consume a plant, corpse, or prey item (1.4).",
    "hungry_ratio": "Energy threshold (≤35%) feeding normalized energy into neural network input slot 0 to trigger foraging.",
    "starving_ratio": "Severe energy threshold (≤15%) triggering desperation sprint and pulsing survival distress.",
    "steer_turn": "Maximum heading angular turn agility per tick, scaled by creature moment of inertia Izz.",
    "birth_enabled": "Master switch enabling reproduction, mating, and generational ascendance.",
    "lifespan_mult": "Multiplier scaling all caste lifespans (Woman: 4,800 ticks → Priest: 9,000 ticks).",
    "adult_age": "Ticks required for an infant/juvenile to mature into a sexually fertile adult (220).",
    "birth_rate": "Base reproduction probability per eligible adult mating pair per tick (0.28).",
    "carrying_capacity": "Population density threshold above which fertility gradually fades (-1 = auto).",
    "max_population": "Hard global population cap preventing any new births until density declines (-1 = auto).",
    "mutation_rate": "Probability a newborn son deviates ±1 side from classical caste inheritance (0.05).",
    "sex_ratio": "Probability a newborn child is a son (ascending polygon) vs daughter (agile line) (0.50).",
    "max_sides": "Upper limit on regular polygon vertex ascendance (up to Priest / Circle status) (24).",
    "euthanasia_threshold": "Irregularity threshold; deformed infants exceeding this are consumed at adulthood (0.70).",
    "mutation_sigma": "Gaussian mutation standard deviation (σ) applied to genome weights during crossover (0.08).",
    "crossover_rate": "Probability of uniform 50/50 parental genome blending during sexual reproduction (0.50).",
    "morphology_annealing_enabled": "Master switch for geometric physics — polar (r,φ) annealing, SAT polygon collision, and trait baking.",
    "annealing_decay_generations": "Generations over which polar morphology annealing decays from Abbott templates to free evolution (150).",
    "disease_enabled": "Master switch for infectious pathogen outbreaks and contagion transmission.",
    "disease_outbreak_rate": "Spontaneous plague outbreak probability per tick during crowded conditions (0.00006).",
    "disease_rate": "Contagion transmission probability per tick within contact range (0.035).",
    "disease_energy_drain": "Metabolic energy drained per tick from actively infected creatures (0.05).",
    "disease_lethality": "Direct health (HP) damage dealt per tick to actively diseased creatures (0.18).",

    # 3. Climate & Sky
    "weather_enabled": "Master switch for dynamic meteorological cycles (sun, rain, fog, storms).",
    "sleep_enabled": "Enables diurnal sleep cycles, house resting, and oral lore transfer after dark.",
    "day_length": "Total duration in ticks of a single diurnal day/night cycle (1200).",
    "season_length": "Duration in ticks of each season (Spring, Summer, Autumn, Winter) (12000).",
    "winter_food_mult": "Winter seasonal food abundance multiplier (0.70 gentle, 0.50 harsh, 0.30 extinction).",
    "night_sight_mult": "Perception radius multiplier during night ticks for non-nocturnal castes (0.60).",
    "weather_change_rate": "Frequency of meteorological transitions between clear, rain, fog, and storm (0.002).",
    "weather_sickness_enabled": "Enables exposure chill and hypothermia when caught unsheltered in wet or freezing weather.",
    "chill_drain": "Direct health drain per tick when chilled outdoors without shelter (0.18).",
    "shelter_enabled": "Master switch for house claiming, door navigation, and roof protection.",
    "exposure_drain": "Health and energy drain per tick when outdoors during harsh weather (0.025).",
    "house_capacity": "Bed capacity inside a settlement hall (12); excess members sleep outdoors.",
    "house_decay_ticks": "Ticks before an abandoned, roofless house crumbles into ruins (10000).",
    "rest_recovery_mult": "Health regeneration multiplier when sleeping indoors under a roof (2.0).",

    # 4. Society, Warfare & Trade
    "territory_enabled": "Enables clan boundary markings, territory defence, and trespass penalties.",
    "territory_radius": "Radius of clan territorial influence around settlement houses (16).",
    "trespass_decay": "Diplomatic relation points lost per tick when a rival clan enters marked territory (0.15).",
    "max_clans": "Maximum number of sovereign clans spawned during world initialization (-1 = auto).",
    "totems_enabled": "Enables Sacred Avatar totem blessings for each clan settlement.",
    "succession_enabled": "Enables dynamic governance leadership transfers on chieftain death.",
    "communication_enabled": "Enables vocalizations, alarm chirps, peace hums, and emotional thought bubbles.",
    "knowledge_enabled": "Enables spatial memory, waypoint mapping, and rumor broadcasting among kin.",
    "schism_enabled": "Enables internal clan fractures when members starve or lack shelter.",
    "schism_threshold": "Dissatisfaction fraction (hunger, homelessness) triggering a factional clan schism (0.40).",
    "war_enabled": "Enables inter-clan warfare, tactical raids, and territorial conquest.",
    "attack_damage": "Base damage dealt by soldiers and warriors in inter-clan battles (32.0).",
    "predation_enabled": "Enables carnivorous predator-prey ecology and hunting dynamics.",
    "predator_ratio": "Fraction of population spawned as predatory carnivores hunting prey (0.02).",
    "hunt_radius": "Aggro detection radius within which carnivores and war parties acquire targets (16.0).",
    "bite_damage": "Combat damage dealt per carnivore attack or predatory strike (28.0).",
    "energy_from_prey": "Caloric energy extracted from slaying and eating a prey creature (45.0).",
    "fear_radius": "Distance at which herbivores and vulnerable castes detect threats and execute evasion (12.0).",
    "coalitions_enabled": "Enables mutual defensive alliances and diplomatic treaties between friendly clans.",
    "coalition_threshold": "Diplomatic trust score required for two friendly clans to form a defensive coalition (40).",
    "leader_decisions_enabled": "Enables chieftain governance bylaws (rationing, martial law, war declarations).",
    "resource_sharing_enabled": "Enables communal settlement larders and altruistic basket food sharing.",
    "larder_capacity": "Energy capacity of settlement communal food stores where surplus is shared (300).",
    "cannibalism_enabled": "Enables desperate consumption of the living during extreme starvation.",
    "eat_kin_enabled": "Allows consumption of deceased or weak clanmates at the cost of tribal exile and feuds.",
    "cannibalism_energy": "Energy gained by starving creatures resorting to eating fallen kin or rivals (45.0).",

    # 5. Theology & Sacred Avatars
    "theology_enabled": "Enables the 8 Sacred Avatars, shrines, temples, miracles, and divine tithes.",
    "tithe_rate": "Fraction of energy devout worshippers offer at shrines each dawn & dusk to build clan faith (0.04).",
    "temple_faith_cost": "Faith points required to consecrate a glowing Temple of the Sphere (400.0).",
    "age_enabled": "Enables historical epoch progression (Golden Age, Ice Age, Age of Chaos, Age of Plague).",
    "age_length": "Duration in ticks per world historical epoch (50000).",
    "culture_enabled": "Enables traditions, governance archetypes, and cultural diffusion.",
    "culture_spread_rate": "Rate at which allied clans sharing borders adopt common cultural traits and beliefs (0.0005).",

    # 6. World Physics & Disasters
    "rivers_enabled": "Enables water channels, fords, water currents, bridges, and dams.",
    "river_count": "Number of procedural river channels carved across the terrain at world generation (2).",
    "relief_enabled": "Enables topographical elevation, slope inertia, cliffs, and road packing.",
    "structural_enabled": "Enables weather wear on buildings, builder repairs, and roof collapse into rubble.",
    "earthquake_enabled": "Enables seismic tremors that shake terrain and damage weakened structures.",
    "earthquake_rate": "Frequency of seismic quakes that crack buildings and shake terrain (0.00008).",
    "lightning_enabled": "Enables real lightning strikes during storms that ignite fires and damage creatures.",
    "lightning_strike_rate": "Frequency of deadly electrical arc strikes during thunder storms (0.0015).",
    "wildfire_enabled": "Enables combustive flame propagation across dense vegetation and forests.",
    "fire_rate": "Probability per tick that a mature plant ignites during dry spells or lightning strikes (0.00008).",
    "disaster_enabled": "Enables cataclysmic meteors, floods, and natural world disturbances.",
    "disaster_rate": "Stochastic probability of catastrophic environmental disasters (0.0003).",
    "anomaly_count": "Number of mysterious spatial anomaly zones altering local physics (3).",
    "door_clearance": "Width multiplier for house doorways relative to the largest creature size (1.5).",
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

