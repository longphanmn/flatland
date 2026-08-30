# Flatland — World Simulation TODO

The Sphere model: The Sphere (God) sets **laws** from Spaceland, never touches individual creatures. Everything else emerges.
Legend: [P0] foundational · [P1] core Flatland identity · [P2] flavor/observability · `- [ ]` open · `- [x]` done · *parked* = decided, not pending

> **Active backlog only.** Completed roadmaps §F–§BC (587 items: 573 + 14 BC) → [`docs/roadmap-archive.md`](docs/roadmap-archive.md) (anchors stripped — all were stale after repeated rewrites; symbols kept). BC geometric physics now done (SoA/Morphology/Annealing/Laws/SAT). BD.5 & BD.6 dossiers done 2026-08-31. This file tracks the **29 open (13 AZ + 16 BD) + 8 parked** items that remain.

---

## Open work — 29 items (13 AZ + 16 BD; verified 2026-08-31, cleaned & sorted by priority, BD.5/6 done)

All `file:line` anchors below were re-verified against `backend/app/simulation.py` (~10k lines), `world.py`, `db.py`, `agent_pipeline.py`, `frontend/src/`. Stale claims from the 200KB log are annotated.

### AZ. Backend Performance Audit — CPU, Calls/s & Memory [P0–P1]

#### Scope rule — non-negotiable
Every item below is **behaviour-preserving**: positions, energy, health, births, deaths, events, chronicle must be **bit-identical** before and after. Anything that would change behaviour belongs under *Parked / Out of scope* and is not to be started.

#### Verification gate
- `pytest backend/tests` green after every item
- **Determinism golden hash unchanged** for every Phase 4 item — revert anything that moves it (`backend/tests/test_determinism_golden.py`)
- `EXPLAIN QUERY PLAN` on `death_count` must show `SEARCH … USING INDEX idx_events_world_type`
- `tracemalloc` snapshots flat across ticks 500/1500/3000 after Phase 2
- `backend/tests/test_scale_benchmarks.py:41` ms/tick recorded before and after each phase

#### Phase 3 — Persistence [P0–P1] · `db.py` — 1 open

- [ ] [P2] **Store pre-serialized tuples in `DB._pending`** — `db.py:115` buffers a `deque` of `("event", (world_id, event))` tuples (`db.py:215`/`230`/`240`), pinning live payload dicts with no bound; re-queue at `db.py:244` `flush()`. Buffer pre-serialized tuples instead and expose a high-water watermark. *Note: `main.py:2011` anchor in the old log is stale (now `def get_laws`); drop it.*

#### Phase 4 — Tick CPU, hot loop [P0] · `simulation.py`

Every item in 4a must leave the Phase 0 golden hash bit-identical. Ranked by expected win; 4a items 1–3 should land as one change (same `_batch_list` region).

##### 4a — Zero behaviour change — 5 open

- [ ] [P0] **Reuse the `dist_sq` the flocking loop already has** — `_batch_list` (`simulation.py:8026` via `world.py:215` `query_radius_with_dist_sq_list`) already carries wrapped `d2`; flocking loop at `simulation.py:9248` region calls `w.delta()` + `math.hypot`. Replace with `math.sqrt(d2)` off the loop variable. *(Verify `dxo`/`dyo` not reused further down.)* *Old anchors `simulation.py:9128`/`7905` stale.*
- [ ] [P0] **Delete the redundant spatial query at `simulation.py:8704`** — `simulation.py:8026` forces `_batch_r >= max(cfg.flock_radius, PRIEST_CALM_RADIUS)`, so `_batch_list` is a **strict superset** of this query. Filter `_batch_list` by `d2 <= r2` instead. *Old anchor `simulation.py:8704` now points at `elif kind == "retreat"` — claim unresolvable as written; re-derive against `_batch_r` at `8026`.*
- [ ] [P0] **Hoist the duplicated creature filter** — `simulation.py:9206` and `simulation.py:9248` are byte-identical `[o for o, _ in _batch_list if isinstance(o, Creature)]`. Build once into a local guarded by a `None` sentinel.
- [ ] [P1] **Stop computing `_elev_units(px, py)` twice** — `simulation.py:9320` computes `here_h = _elev_units(c.x, c.y)`; `px,py` captured pre-move; `simulation.py:9365` calls `_terrain_effects(c, px, py)` which recomputes `_elev_units(px, py)` at `simulation.py:1296`. Pass `here_h` into `_terrain_effects`. Saves 1 of ~4 FFI calls per creature per tick. *Old anchors `9199`/`9208`/`9218`/`1271` stale.*
- [ ] [P2] **Micro-optimizations, zero risk** — `isinstance` → `type(e) is Food` in plants loop (`simulation.py` ~`_update_plants` region); `sorted(key=lambda …)` → `operator.itemgetter` at war-sort region; drop the `list(...)` copy defeating `lru_cache` in delta payload. *Old anchors `6269`/`8437`/`3952`/`10278`/`10287` all stale — re-derive by symbol.*

##### 4b — Needs the determinism gate — 1 open

- [ ] [P1] **Memoize `_house_for` per creature per tick** — called up to 5× (`simulation.py:7576`, `8309`, `9075`, `9148`, `9647`; def at `simulation.py:2972`), each building 2 closures + lambda-keyed `min`. The `roof_resolved` guard covers only some sites. **Key on `(c.x, c.y, self.tick, house_version)`** where `house_version` bumps on claim/collapse — naive per-tick key is wrong because the creature moves between `9075` and `9148`. Must pass the golden hash. *Old anchors `7455`/`8188`/`8954`/`9027`/`9505`/`2989-3014`/`7321` stale.*

#### Phase 5 — Wire & serialization [P1] · `simulation.py` snapshot path — 4 open

Reduces bytes and CPU per frame without dropping data — coalesce and cache, never discard.

- [ ] [P1] **Signature-gate the delta frame** — `simulation.py:10109` (keyframe) and `10123` + delta at `10270` rebuild `relations`/`signals`/`fires`/`campfires`/`boundary_stones`/`markets` **every frame**, while `rivers`/`bridges`/`dams` at `10126`/`10230` are already signature-gated. Apply the same gate: cache the built list alongside a signature. *Old anchor `10125-10139` listed only one site; there are two (keyframe + delta).*
- [ ] [P1] **Stop sorting `relations` every frame** — `sorted(self.relations.items())` at `simulation.py:10109` and `10270` is O(R log R) with fresh dicts on keyframe *and* delta even when nothing changed. Cache the sorted list, invalidate on mutation. *Old anchors `9969`/`10125` stale.*
- [ ] [P1] **`lru_cache` on `personal_name_for` / `glyph_for` / `variation_for`** — `simulation.py:674`/`681`/`685` are pure functions of `(id, seed, generation)`, recomputed for every entity on every keyframe and bypassed by direct calls. Bounded by population.
- [ ] [P2] **Precompute static entity coordinates in `_entity_sig`** — food and houses never move, yet `simulation.py:9938` `_entity_sig` re-`round()`s their x/y every frame. Cache the rounded prefix at creation. *Old anchor `9829` stale.*

#### Phase 6 — Frontend polling follow-up [P2] — 1 open

- [ ] [P2] **Drive side panels from the WebSocket stream** — `Inspector.tsx:162` (2s), `ClanPanel.tsx:60` (5s), `PlotsPanel.tsx:28` (5s) poll HTTP on top of the socket stream, plus `frontend/src/clan/ClanDetails.tsx:100` (2.5s; path corrected — old log said `render/ClanDetails.tsx`). Moving them onto the stream removes Phase 1's worst `DB.flush()` trigger and the duplicate stdlib-`json` serialization path.

### BA. Micro-Neural Network & Evolutionary Engine [P0–P2] — 1 open

> Supersedes `AL` Task 1.1; NN is always on (295 fixed genome `16×12+12 + 12×7+7`). SoA is tick-time truth; `entities.py:122` `Creature` remains for REST/inspector.

- [x] [P2] **6.4 Morphological genome expansion (future hook)** — superseded by `BC` below; kept for history.

### BC. Geometric Physics & Morphological Evolution Engine [P1–P2] — ✅ Done (14/14) — to be archived to `roadmap-archive.md` next cycle

> Superseded `BA 6.4`. Delivered 2026-08-31: SoA `KMAX 64`, `morphology.py`, `evolution_manager.py`, 7 God laws + presets + Morphology panel, Sat & `/api/metrics/morphology`, energetic asymmetry & courtship gated. Sorted P1→P2; verification `morphology_annealing_enabled=false` keeps AZ hash.

- [x] [P1] **1.1 SoA buffers** `agent_soa.py:26` `morph_radii/angles (N,64)`, `morph_k 3..64`, `morph_traits 6`, `reproduction_role` lazy median; swap-with-last; 768KB.
- [x] [P1] **2.1 Polar formulations** `morphology.py` vectorized shoelace/perimeter/Izz/θmin/asym/Dmult batch.
- [x] [P1] **2.2 Trait baking** `simulation.py:6932` + `main.py:2050` observer caps `A/Aref 0.5-2` etc.
- [x] [P1] **5.1 God laws** 7 fields `protocol.py:201` + `config.py:13` + `LAW_FIELDS` + `types.ts:292` + `GodPanel.tsx:22` Morphology.
- [x] [P1] **5.2 Presets** `main.py:837` Theocracy λ=1, Chaos 0/10/0.05.
- [x] [P1] **5.3 Observer** rebake queue `main.py:2022`.
- [x] [P2] **3.1 Abbott templates** $K3..64$ `evolution_manager.py`.
- [x] [P2] **3.2 λ(g)** `Optional` `None` sentinel.
- [x] [P2] **3.3 Inheritance + topo** $r,φ$ interpolation + longest/closest.
- [x] [P2] **4.1 Energetic asymmetry** median $A$ `simulation.py:6853`.
- [x] [P2] **4.2 Courtship** `social>0.5` gated BA 8.1.
- [x] [P2] **6.1 SAT** broadphase $r_{\max}$ + edge normals `morphology.py:253`.
- [x] [P2] **6.2 Telemetry** `GET /api/metrics/morphology` `main.py:2303`.
- [x] [P2] **6.3 Zero-alloc** `<4ms/2000` verified 1.84s/100 ticks same as disabled.

### BD. World Analytics & Telemetry Engine [P1–P2] — 24 open

> Objective: High-performance macro intelligence, biological evolution tracking, geopolitical analytics, ecological trophic balance, predictive early warning systems, and dedicated Observatory / Profile UI redesigns. Operates zero-alloc on the simulation hot loop via SoA batch aggregators and rolling ring buffers.

#### Verification gate (BD)
- `pytest backend/tests` green; determinism golden hash bit-identical when analytics enabled.
- Aggregation overhead `<0.8ms` per 100 ticks for 2000 agents.
- REST endpoints `/api/analytics/*` cached / rate-limited to avoid contention with `RT.lock`.
- Responsive UI verified across Desktop and Mobile viewports.

#### BD.1 Core Telemetry & Vectorized Aggregators (`backend/app/analytics.py`, `main.py`) — 4 open

- [ ] [P1] **1.1 Zero-Alloc Rolling Telemetry Aggregator** — implement `backend/app/analytics.py` using SoA ring buffers (`deque(maxlen=300)`) to track macro time series: population, living biomass, energy saturation ($E/E_{\max}$), average lifespan, dead counts, and birth/death velocity per minute.
- [ ] [P1] **1.2 Stacked Mortality & Morbidity Decomposition** — aggregate real-time and historical causes of death into categorized percentages: starvation, combat/warfare, predation, disease/plague, old age, and weather exposure (rain/chill). Expose running 500-tick distributions.
- [ ] [P1] **1.3 High-Performance Analytics REST API** — add `GET /api/analytics/summary` in `backend/app/main.py` providing instant snapshot metrics, demographic totals, trophic balance, and rolling sparkline vectors with 1s memoization cache.
- [ ] [P2] **1.4 WebSocket Analytics Stream Coalescing** — integrate high-level analytics frames into WebSocket telemetry stream at 1 Hz, avoiding redundant HTTP polling in frontend side panels.

#### BD.2 Biological, Morphological & Trophic Ecology Analytics — 4 open

- [ ] [P1] **2.1 Generational Caste Ascendance & Mutation Tracker** — compute generational mobility rate ($n \to n+1$), mutation frequency, irregularity/asymmetry index distribution ($\sigma_r^2 / \bar{r}$), and Abbott ladder progression over generations.
- [ ] [P1] **2.2 Lotka-Volterra Phase-Space Coordinates** — calculate real-time trophic vectors (Herbivores vs Apex Predators vs Plant Biomass) and phase trajectory curves to visualize ecosystem equilibrium/collapse cycles.
- [ ] [P2] **2.3 Shannon-Wiener Biodiversity Index** — track ecological richness and evenness across all 6 plant species (*Grass, Golden Grain, Berry Bushes, Medicinal Herbs, Fungi Mushrooms, Poisonous Sprouts*) and corpse nutrient recycling rates.
- [ ] [P2] **2.4 Heritability & Personality Drift Matrix** — measure inheritance fidelity for genetic personality archetypes (`brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder`) vs emergent fitness outcomes.

#### BD.3 Geopolitical, Macroeconomic & Societal Intelligence — 4 open

- [ ] [P1] **3.1 Herfindahl-Hirschman Hegemony & Territorial Index** — quantify clan market concentration, land territory control radius, and settlement population dominance.
- [ ] [P1] **3.2 Wealth Inequality & Larder Gini Coefficient** — compute Gini coefficient across clan granary reserves and individual creature basket food stores; detect emerging economic disparities and starvation risks.
- [ ] [P2] **3.3 Inter-Clan Trade & Caravan Telemetry** — monitor commodity transfer volume (grain, herbs, tools), barter velocity, and caravan route vulnerability across borders.
- [ ] [P2] **3.4 Casus Belli & War/Schism Risk Predictor** — compute tension indices between bordering clans based on food deficit, historical blood feuds, and overcrowding; predict war and schism outbreak probabilities.

#### BD.4 Predictive Early-Warning & God Laws Sensitivity Engine — 4 open

- [ ] [P1] **4.1 Famine Horizon & Winter Vulnerability Gauge** — calculate estimated survival ticks until mass starvation based on larder burn rate vs plant regrowth rate under upcoming seasonal shifts.
- [ ] [P1] **4.2 Demographic Extinction Cliff Alarm** — evaluate effective breeding population ($N_e$) and alert when genetic diversity or fertile female count drops below critical sustainability thresholds.
- [ ] [P2] **4.3 God Law Counterfactual Impact Matrix** — correlate historical `/api/laws` changes (e.g. `carrying_capacity`, `food_growth`, `weather_volatility`) with macro population and mortality velocity response curves.
- [ ] [P2] **4.4 Civil Unrest & Schism Early Warning** — trigger unrest indicators when internal house crowding, hunger, and divergent personality tension exceed clan stability thresholds.

#### BD.5 Creature Profile Redesign — The Flatlander Dossier (`frontend/src/inspect/Inspector.tsx`) — ✅ Done (4/4)

- [x] [P1] **5.1 Hero Header & Compact Geometric Avatar** — hero header with caste badge, title/glyph, dual-pill HP/Energy gauges, chill badges, personality/tool pills; compact SVG avatar with clan halo.
- [x] [P1] **5.2 4-Tab Modular Navigation** — `Vitals & Morphology | Skills & Neural AI | Lineage & Kin | Life Chronicle` tabs, active tab persisted `sessionStorage['insp-tab']`.
- [x] [P2] **5.3 Interactive Pedigree Visualizer (Lineage Tab)** — `KinCardView` cards for mother/father/children with alive/deceased color, clan color border, personal_name/glyph, click-to-navigate; children grid 2-col.
- [x] [P2] **5.4 Skill Matrix & Neural Output Radar (Skills & AI Tab)** — 2×2 circular mastery badges (Farming/Combat/Foraging/Healing) with radial progress + compact 2-col neural gauges (thrust/steer/interact/social/vocal amp/freq/recurrent) + morphology placeholder BC.

#### BD.6 Clan Profile Redesign — The Clan Codex (`frontend/src/clan/ClanDetails.tsx`) — ✅ Done (4/4)

- [x] [P1] **6.1 Hero Header & Banner Crest** — hero header `2px solid color` banner, totem crest, color theme, Chieftain link, alive/dead + faith/shrine badge.
- [x] [P1] **6.2 4-Tab Modular Codex Architecture** — `Stronghold & Outposts | Demographics & Roster | Warfare & Diplomacy | Annals & Full History` tabs, `sessionStorage['clan-tab']` persisted.
- [x] [P2] **6.3 Searchable & Filterable Member Roster (Roster Tab)** — chips All/Warriors/Harvesters/Elders/Sick, 2-col member cards with caste/stage/energy/health + inspect.
- [x] [P2] **6.4 Warfare Record & Diplomatic Intelligence (War & Trade Tab)** — win/loss banner, specialization tri-wheel, diplomatic intelligence note + recent events.

---

## Parked — decided, not pending (8 items; 9 before dedupe)

These are documented decisions with rationale, not overdue work. The original 22 unchecked items included 9 such; 2 were the same task.

| # | Item | Rationale |
|---|------|-----------|
| 1 | **AQ P2 Wind affects thrown weapon range** | No thrown-weapon system to bend (spears are melee buffs). Revisit when ranged combat exists. |
| 2 | **AQ P2 Ramps / staircases** | Needs vertical layer semantics the flat-point body model doesn't have; grades already cost/slow. |
| 3 | **AQ P2 Weight & load-bearing** | Planiverse beam mechanics need a structural graph; walls already block except doors. |
| 4 | **AZ P2 `__slots__` on `Config`** (`config.py:13`) | Single instance, every `self.config.X` is a dict lookup — low win. Verify `RT.config` never gains dynamic attrs (`main.py:427-444`). |
| 5 | **BA P1 6.3 + P0 7.4 Rebless the determinism golden** *(consolidated)* | Re-record `backend/tests/test_determinism_golden.py` checkpoints (ticks 100/250/500) for the NN engine. Deferred until NN fully replaces `AL` utility AI (currently soft-gated; `7.4` was a duplicate of `6.3`). |
| 6 | **BA P1 9.2 Fill sensor slots 9–13** (`agent_pipeline.py:78` audio/scent/impulse stubs) | Slots remain 0; full scent/signal integration needs §AN grid wiring — deferred to avoid churn before 8.1 hard switch. |
| 7 | **BA P0 9.4 Vectorize the raycast sensor loop** (`agent_pipeline.py:47-60` O(N)×3) | Python loop stays within 50 ms CI budget (`test_n2000_budget` ≤50 ms; 12 ms target is N150). Defer numpy vectorization until profiling shows bottleneck. |
| 8 | **BA P0 10.1 Extend `test_neuroevolution.py`** (thrust/social/vocal/birth/inherit) | Deferred until 8.1 hard switch — soft-gated wiring would make tests flaky. Current 8 tests cover SoA/genome/forward/sensors/mating/latch/budget. |

---

## Guardrails

### Conflict map — what must **not** land in parallel [P0]

1. **Phase 0 gates Phase 4 only.** Phases 1, 2, 3 and 5 are independent of the golden hash and can start in parallel.
2. **Phase 2 (`entities.py`) before Phase 4.** `__slots__` is the only change that can hard-fail at runtime; settle it before editing `simulation.py`.
3. **Phase 4a items 1–3 are one change.** All three edit the `_batch_list` region; land together, measure once.
4. **Phase 4b (10) must not land with Phase 4a.** Both touch house resolution; separate so the golden hash bisects cleanly.
5. **Phase 5 items are one change.** All four edit the same delta-payload dict construction.
6. **Phase 3 index is an operational event.** Run the 2.6 M-row migration in its own maintenance window; don't bundle with PRAGMA changes.
7. **Phase 1 items 15 and 18 both own `Hub`** (`main.py:68-92`) — one author, one PR.
8. **BC.1 owns `AgentSoA`** (`agent_soa.py:20`) alone — do not touch SoA in parallel with AZ phases.
9. **BC.4 touches `_reproduce/_birth`** (`simulation.py:6853/6932`) — do not land with AZ Phase 4b `._house_for` `simulation.py:2972` (both near golden hash); serialize.
10. **BC.5 observer touches `apply_laws`** (`main.py:2016`) — one author with any AZ `LAW_FIELDS` change (`main.py:665`).

### Suggested order

**AZ: Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4a → Phase 5 → Phase 4b → Phase 6.** Phase 1 first (highest win/risk, no sim code); Phase 2 before Phase 4; Phase 4b last (only non-provably-identical item).

**BC: BC.1 → BC.2 → BC.5 → BC.3 → BC.4 → BC.6.** SoA before baking, laws before annealing, courtship last (gated 8.1 `TODO.md:80`). AZ and BC are independent except BC.1 vs AZ Phase4 `AgentSoA` — start BC.1 after AZ Phase 1.

### Out of scope — these change the laws of the world

Audited, quantified, and **deliberately excluded**. Do not start without revisiting the scope rule.

- **Prune `Creature.trust`** (`entities.py:197`) — O(N) per creature, O(N²) total, zero `trust.pop`/`del` in 10k lines. Excluded: capping changes who a creature trusts — a law change. Revisit as god-tuneable `trust_cap` if memory critical.
- **TTL-prune `Creature.give_ups`** (`entities.py:181`) — cleared only on successful meal. Forgetting is a behaviour change.
- **Stagger the plant symbiosis query** (`simulation.py:6294` region) — one spatial query per growing plant per tick. Damping changes growth outcomes.
- **Throttle the temperature field** (`simulation.py:1003-1013` region) — staggering changes chill → mortality.
- **Partial `_refresh_cache`** — skipping house/clan sub-loops risks stale derived state.
- **Suppress `recovery` events from persistence** — 1.07 M rows, 41% of the 448 MB DB. Changes the visible chronicle.
- **Incremental `rebuild_index`** (`world.py:69`, called twice per tick at `simulation.py:3700,3778` region) — needs `world.mark_moved()` dirty-set refactor.
- **Narrow `RT.lock` around `step()`** (`main.py:270-272` region) — biggest structural win but only safe via copy-on-write.
- **Wire up the native C core / add numpy** — `native_boids_forces`/`native_query_radius`/`native_batch_update` have zero call sites; `world.py:13` force-disables. Excluded: fast-math drift breaks determinism. Revisit behind a flag + parity test. **Reversed by `BA` below — see BA scope note.**
- **`parallel.py`** — fresh `ProcessPoolExecutor` per call with `chunksize=1`, ~800 pickle round-trips/tick. Dead code; delete or redesign.

---

## Archive index

§F Infrastructure — Database · §A Life cycle · §B Reproduction · §C Irregularity & caste · §D Health & disease · §E Environment · §G God-law & observability · §H Food ecosystem · §I Society · §J Creature profile · §K Documentation · §L Shelter · Cross-system synergies · §W World generation · §N New frontiers · §O Ecosystem depth · §P Clan depth · §Q Creatures 2.0 · §R Weather as life · §S WorldBox inspirations · §T Sustainability & performance · §U Mobile UI/UX · §V Clan founding redesign · §X Fixes · §X2 Communication II · §Y UI polish · §Z Terminal frontend · §AA Performance round 2 · §AB Politics · §AC Desperation cannibalism · §AD OS-log persistence · §AE Food decay · §AF Performance & Massive Scale · §AG Autonomous Evolution · §AH Energy Dynamics · §AI TUI Feature Parity · §AJ Next-Gen Performance (3 phases) · §AK Clan Lifecycle · §AL Creature Cognitive Agency · §AM Food & Agriculture · §AN Communication, Language & Diplomatic · §AO Nocturnal Perils · §AP Unified Theology · §AQ 2D Physics · §AR Creature Senses · §AS Clan Leader Importance · §AT Four Immediate Issues · §AU Performance Optimizations · §AV Frontend & TUI Performance · §AW Emergency 1–2 TPS · §AX High-Density 20 TPS · §AY Multi-Core Engine · §AY2 World Simulation Presets · §AZ Backend Performance Audit · §BA Micro-Neural Network · §BC Geometric Physics & Morphological Evolution · §BD World Analytics & Telemetry Engine

Full completed content → [`docs/roadmap-archive.md`](docs/roadmap-archive.md)
