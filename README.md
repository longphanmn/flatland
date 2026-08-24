# Flatland — 2D Autonomous World Simulation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React: 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6.svg)](https://www.typescriptlang.org/)

**Flatland** is an autonomous 2D artificial life and ecosystem simulation developed from the foundational ideas of **Edwin A. Abbott's 1884 classic *Flatland: A Romance of Many Dimensions***. Rather than rigidly mimicking or reenacting the 19th-century novella, this project takes Flatland's core geometric premises — 2D spatial existence, vertex-based caste hierarchy, atmospheric perception, and higher-dimensional observation — and transforms them into a **living, autonomous evolutionary world that dynamically changes and expands over time**.

> **Developed by [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Built and refined using **OpenCode** and **Antigravity**.  
> Developed from the core mathematical and spatial ideas of **Edwin A. Abbott** (1884).

---

## 🏛️ Design Philosophy: Evolution from Flatland

1. **Developed from the Idea, Not a Literal Mimic**: The simulation embraces Abbott's fundamental concepts — 2D geometric constraints, line and polygon dynamics, generational side inheritance, and the perspective of a 3D observer (the Sphere / God Model) — while freely diverging from Victorian social satire to build an authentic artificial life ecosystem.
2. **Living & Changing Over Time**: The world evolves dynamically across seasons, generations, and historical ages. Organisms develop heritable personalities, master distinct craft disciplines, form tribal coalitions, exchange oral traditions, and manage domestic economies.
3. **Immutable Natural Laws**: God governs exclusively through universal laws of nature (metabolism, carrying capacity, climate volatility, disease), leaving all individual outcomes to 100% emergent behavior.


### 1. The God Model: Laws over Fates
In Flatland, God sets the **laws of nature** but never touches an individual life. God cannot kill, heal, or move a single creature; the simulation advances deterministically under physical and biological rules.
- **God Panel (`⚖ God`)**: Adjust carrying capacity, food growth, energy metabolism, weather volatility, disease virulence, or clan aggression in real-time.
- **Curated World Presets**:
  - **⚖️ Balance (Default)**: Goldilocks harmony tuned for **500–800 inhabitants** with 220 food, carrying capacity 600 (max 800), gentle wars, rare predation, and flourishing multi-generational clans.
  - **🌿 Sustainable**: Abundant food (450), carrying capacity 2200 (max 3000), low conflict, 1000-day peace.
  - **🔥 Chaos**: High predator ratio, lethal wars, wildfires, frequent plagues, and fast seasonal turnover.
  - **💀 Extinction**: Famine (100 food), harsh winter (0.3×), high decay, testing societal resilience under collapse.
  - **🚀 Boom**: High reproduction, 650 food, carrying capacity 3500 (max 5000) for high-scale performance testing.

### 2. Biology, Castes & Nature's Law
- **Geometric Hierarchy**: Higher side counts perceive farther and live longer (Women shortest → Isosceles Soldiers → Equilateral Artisans → Squares/Pentagons → Polygons → Priests/Circles longest).
- **Heritability & Ascendance**:
  - Sons inherit one more side than their father ($n+1$), ascending the societal ladder across generations.
  - Isosceles triangles creep $+0.5^\circ$ per generation, promoting to regular Equilateral Artisans at $60^\circ$.
  - Daughters inherit the line form of their mother.
  - Mutations may deviate a child's side count, producing irregularity judged at adulthood.
- **Energy Metabolism & Life Stages**:
  - Four distinct life stages: **Infant**, **Juvenile**, **Adult**, and **Elder**.
  - Infants burn 55% less energy per tick (`0.45×`); elders move and see with reduced vigor.
  - Hunger activates enhanced foraging sight; extreme starvation triggers desperate speed and pulsing indicators.

### 3. Autonomous Evolution, Skills & Oral Lore
Evolution emerges 100% autonomously without artificial intervention:
- **Personality Archetypes**: Genetic heritability (65%) for traits including `brave`, `cautious`, `altruistic`, `greedy`, `explorer`, and `builder`. Altruistic creatures feed starving kin using basket reserves.
- **Dynamic Equipment & Tools**:
  - **Spears**: $+20\%$ combat damage and strike reach for Soldiers and Apex Predators.
  - **Baskets**: Carry up to 3 food units for field meals while roaming or depositing into settlement larders.
  - **Herb Poultices**: $+25\text{ HP}$ healing and infection remedies for Priests.
  - **Chieftain Crown**: Adorns the leader of each settlement house.
- **Skill Mastery Matrix**: Four masterable disciplines (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿) unlocking earned titles (*the Slayer*, *the Fearless Champion*, *the Grand Harvester*, *the Wise Shaman*, *the Pathfinder*).
- **Oral Lore in Houses**: Resting elders teach their highest skill mastery to sleeping youth indoors.
- **Thought Bubbles**: Real-time floating emote indicators (`🍖`, `❤️`, `⚔️`, `🌿`, `🏆`, `💤`, `🧺`, `😱`).
- **Cognitive Agency & Tactical Intelligence**: Multi-objective utility AI scoring replaces rigid if/else trees (evaluating survival, duty, traits, and kin needs); spatial waypoint mental maps (`home`, `rich_food`, `danger`, `patrol`); tactical soldier phalanxes, line kiting maneuvers, and interpersonal trust-based buddy pairing.


### 4. Settlements, Clans & Diplomacy
- **Settlement Houses**: Square walled halls with creature-sized doorways; houses block outside elements and wild carnivores.
- **Territory & Clan Banners**: Foundational houses establish spatial clans with distinct banner colors, procedurally generated clan names, and totems (Wolf, Bear, Tree, Shield, Eye, Stag, Owl, etc.).
- **Division of Labor & Task Board**: Dynamic macro priorities (`balanced`, `food_security`, `defense`, `quarantine_healing`) boost harvester (2.0×) and guard (2.5×) action weights.
- **Governance Archetypes & Succession**: Distinct institutional models (`Monarchy` royal dynasty, `Theocracy` priest succession, `Junta` combat mastery, `Republic` council of elders).
- **Dynamic Bylaws**: Automated policies including winter food rationing (<35 energy threshold) and wartime martial law curfews.
- **Resource Sharing & Larders**: Settlements maintain food larders where sated members deposit surplus and hungry kin withdraw.
- **Diplomacy & Politics**: Emergent alliances, defensive coalitions, tributary pacts, schisms, and territorial rivalries.


### 5. Environment & Ecosystem
- **Dynamic Seasons & Day/Night**: Spring blossoms, summer abundance, autumn harvests, and winter lean periods.
- **Weather & Disasters**: Rain, fog, thunderstorms with lightning wildfires, and exposure sickness for unsheltered creatures.
- **Biodiversity**: Distinct plant varieties (Grass, Berry Bushes, Mushrooms, and Poisonous Sprouts) and nutrient recycling from fallen corpses.

---

## Quickstart

### Prerequisites
- **Python 3.12+** (with [`uv`](https://docs.astral.sh/uv/) recommended)
- **Node.js 18+** & **npm**

### One-Line Launch
```bash
./run.sh          # Starts FastAPI backend (:8000) and Vite frontend (:5173)
./run.sh tui      # Launches terminal client attached to local backend
```

- **Web UI**: [http://localhost:5173](http://localhost:5173)
- **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Living Wiki**: [http://localhost:8000/wiki](http://localhost:8000/wiki)
- **Living Guide**: [http://localhost:8000/guide](http://localhost:8000/guide)

---

## Manual Installation & Commands

### Backend Setup
```bash
cd backend
uv sync                                        # Create venv and install dependencies
uv run pytest -v                               # Run comprehensive test suite
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install                                    # Install frontend dependencies
npm run dev                                    # Start Vite development server
npm run build                                  # TypeScript compile & production bundle
```

---

## Terminal TUI Client

Flatland includes a complete terminal client powered by **Textual** (`backend/tui/`) that connects to any running world over WebSocket:

```bash
./run.sh tui                                   # Connect to localhost:8000
./run.sh tui ws://<remote-host>:8000/ws        # Connect to a remote server
```

### TUI Keybindings:
| Key | Action |
|:---:|---|
| `Space` | Pause / Resume simulation |
| `S` | Single step forward (1 tick) |
| `R` | Reset world with new procedural seed |
| `F` | Fit camera to entire world |
| `W` | Follow/track currently selected creature |
| `T` | Filter Chronicle log categories |
| `+/-` | Zoom in / Zoom out |
| `H / J / K / L` or Arrows | Pan camera view |
| `Enter` or `I` | Open detailed Creature Inspector dossier |
| `C` | Open Clan Details modal |
| `G` | Open God Laws configuration screen |
| `1` – `9` | Adjust simulation tick speed |
| `?` | Show interactive help |
| `Q` | Quit terminal client |

---

## Architecture & Codebase Map

```
ws/
├── backend/
│   ├── app/
│   │   ├── config.py       # Configuration dataclass & default environment values
│   │   ├── entities.py     # Creature castes, traits, food variants, and houses
│   │   ├── world.py        # Entity spatial hash index & wrap-aware proximity queries
│   │   ├── simulation.py   # Deterministic step pipeline: perceive, steer, eat, reproduce
│   │   ├── protocol.py     # Pydantic schemas shared between backend & frontend
│   │   ├── db.py           # SQLite persistence for worlds, events, and lineage
│   │   ├── guide.py        # Backend-rendered HTML Living Guide
│   │   ├── wiki.py         # Living Wiki & API documentation
│   │   └── main.py         # FastAPI app, WebSocket broadcaster, and REST endpoints
│   ├── tui/                # Textual terminal client
│   └── tests/              # Pytest test suite (231+ automated tests)
└── frontend/
    └── src/
        ├── render/
        │   ├── CanvasRenderer.tsx  # High-performance 60 FPS batched HTML5 Canvas renderer
        │   ├── ClanPanel.tsx       # Live clan settlements, totems, and war records
        │   ├── ChronicleFeed.tsx   # Filterable, scrollable real-time event log
        │   ├── PlotsPanel.tsx      # Multi-metric population and caste sparklines
        │   └── Collapsible.tsx     # Dynamic flex collapsible accordion component
        ├── god/
        │   └── GodPanel.tsx        # Interactive Laws of Nature control drawer
        ├── inspect/
        │   └── Inspector.tsx       # Creature dossier, vitals, inventory & family tree
        ├── wiki/
        │   └── Wiki.tsx            # In-app interactive wiki & API playground
        └── App.tsx                 # Main application layout, HUD, and WebSocket synchronization
```

---

## Performance & Scale

- **Zero-Allocation Spatial Hash**: Pre-allocated 1D bucket list in `world.py` eliminates tuple allocations and dictionary re-hashing per tick; neighbor lookups use squared-distance early-exits.
- **Dedicated Engine Thread**: Simulation runs on a dedicated high-priority tick loop (`SimEngine` in `main.py`), completely isolating mathematical simulation advancement from asynchronous HTTP/WebSocket I/O.
- **Batched Canvas 2D Rendering**: `CanvasRenderer.tsx` batches drawing passes by caste, plant variant, and house primitives with inline trigonometric vertex transforms, reducing draw calls from over 20,000 to ~30–50.
- **Decoupled React State**: High-frequency snapshot data streams directly into mutable refs for canvas rendering at 60 FPS, while React DOM reconciliation for HUD chips and panels is throttled to ~6 Hz to keep the browser responsive.

---

## Authors & Attribution

- **Developed by**: **[Long Phan](mailto:long@minhnhan.in)**  
  Email: [long@minhnhan.in](mailto:long@minhnhan.in)  
  Website: [https://minhnhan.in](https://minhnhan.in)  
  Live World: [https://world.minhnhan.in](https://world.minhnhan.in)
- **AI Tooling & Development**: Built and engineered with **OpenCode** and **Antigravity**.
- **Literary Source**: Based on the mathematical concept and social commentary of ***Flatland: A Romance of Many Dimensions*** by **Edwin A. Abbott** (1884).

---

## License

This project is open source and available under the [MIT License](LICENSE). See [LICENSE.md](LICENSE.md) for the full license text.
