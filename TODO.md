# Flatland — World Simulation TODO

The Sphere model: The Sphere (God) sets **laws** from Spaceland, never touches individual creatures. Everything else emerges.
Legend: [P0] foundational · [P1] core Flatland identity · [P2] flavor/observability · `- [ ]` open · `- [x]` done · *parked* = decided, not pending

> **Active backlog only.** Completed roadmaps §F–§BA (573 items) → [`docs/roadmap-archive.md`](docs/roadmap-archive.md) (anchors stripped — all were stale after repeated rewrites; symbols kept). This file tracks the **27 open (13 AZ/BA + 14 BC) + 8 parked** items that remain.

---

## Open work — 27 items (13 AZ/BA + 14 BC; verified 2026-08-30, BC added 2026-08-30)

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

### BC. Geometric Physics & Morphological Evolution Engine [P1–P2] — 14 open

> Supersedes `BA 6.4`. Project status: Micro Elman RNN `16→12→7`, SoA buffers, spatial hash grid, 60 Hz physics / 15 Hz NN loop **completed**. Current objective: Physics-based morphological evolution with polar genome $(r_i,\phi_i)$, $K\in[3,64]$ (user-confirmed `K>24` beyond `PRIEST_SIDES 24` `entities.py:6` / `max_sides 64` `protocol.py:249`), governed by **Morphological Annealing** $\lambda(g)$ live-synced with **⚖ God Laws**. Runtime `Python 3.10+ / NumPy` vectorized batch, zero-alloc tick. **BC is feature work** — not under `AZ` behaviour-preserving scope rule; changes laws, births, traits, collisions. Determinism re-blessed via `BA 6.3/7.4` parked item `TODO.md:77`.

#### Verification gate (BC)

- `pytest backend/tests` green; `test_determinism_golden.py` re-blessed with `morphology_annealing_enabled=false` default (bit-identical when disabled)
- `test_scale_benchmarks.py:41` ms/tick recorded before/after; BC.6.3 must stay `<4.0ms/2000` agents SAT
- `tracemalloc` flat 500/1500/3000; `EXPLAIN QUERY PLAN` unchanged

#### BC.1 SoA Memory Expansion `agent_soa.py:20` — 1 open

- [ ] [P1] **1.1 Expand SoA buffers for polygon geometry** — add to `AgentSoA` `agent_soa.py:26` (with list fallback `agent_soa.py:40` when `HAS_NUMPY False`):
  - `morph_radii: np.ndarray((N,64),f32)` $r_i\in[0.2,2.5]$; `morph_angles: np.ndarray((N,64),f32)` monotone $\phi_i\in[0,2\pi)$; `morph_k: np.ndarray((N,),i32)` $3\le K\le64$ (K>24 confirmed; `PRIEST_SIDES 24` `entities.py:6` becomes threshold `K>=24→Priest`, not cap; supports `K=32,48,64` ultra-circles)
  - `morph_traits: np.ndarray((N,6),f32)` (rename from `physical_traits` to avoid `stats[4]` `agent_soa.py:31`): `[0] area $A$, [1] perimeter $P$, [2] $I_{zz}$, [3] $\theta_{\min}$, [4] asymmetry $\sigma_r^2/\bar r$, [5] $D_{\text{mult}}$`
  - `reproduction_role: np.ndarray((N,),i8)` `+1` high-invest / `-1` low-invest — derived lazily from `median(A)` per birth batch, not at `add_agent` `agent_soa.py:60`
  - Update `add_agent`/`remove_at` `agent_soa.py:60/90` swap-with-last; memory `1500*64*2*4≈768KB` (< genome `1.7MB`); flag `morphology_annealing_enabled` `false` default keeps AZ hash.

#### BC.2 Geometric Physics & Trait Baking `morphology.py` (new) — 2 open

- [ ] [P1] **2.1 Polar geometric formulations — vectorized batch, zero-alloc** — implement in `backend/app/morphology.py` (snake, not `morphology_engine.py`; repo style `agent_soa.py`):
  - `compute_polygon_vertices(r,φ,k)->(x,y)` polar→local cart
  - `compute_shoelace_area(x,y,k)->A` $A=\frac12|\sum x_i y_{i+1}-x_{i+1}y_i|$
  - `compute_perimeter(x,y,k)->P` $\sum\sqrt{(Δx)^2+(Δy)^2}$
  - `compute_moment_of_inertia(x,y,k)->I_{zz}$` centroid $I_{zz}$
  - `compute_min_vertex_angle(x,y,k)->θ_{\min}$` $\min \arccos(u·v/|u||v|)$
  - `compute_asymmetry_index(r,k)->σ_r^2/\bar r`
  - Batch `N` agents with NumPy `f32`, not per-agent Python loop; caps keep `BC.6.3` budget.

- [ ] [P1] **2.2 Trait baking on birth `bake_physical_traits(id)`** — called from `simulation.py:6932 _birth` and on live `POST /api/laws` observer `main.py:2050` (queued rebake, not under `RT.lock` loop):
  - $E_{\max}=energy\_max·clamp(A/A_{ref},0.5,2.0)$ where $A_{ref}$ from Square Gentleman `RADIUS_BY_CASTE 1.15` `entities.py:8` (prevents `le 10000` `protocol.py:206` blow-up 190×)
  - $decay=energy\_decay\_per\_tick·clamp(P/P_{ref},0.7,1.8)$
  - $Damage=attack\_damage·max(0,(cosθ_{\min}-0.5)/0.5)$ `proposed` stacks with `TOTEM Strike 0.25` `simulation.py:594`
  - $Δθ=steer·(steer\_turn/(1+I_{zz}/I_{ref}))$ (`steer_turn 0.45` `config.py:135`; expose `I_{ref}` law if needed)
  - Map `asymmetry→Creature.irregularity` `entities.py:139` for existing `euthanasia_threshold 0.7` `config.py:159` / `simulation.py:7876` judgment (unify, not duplicate)

#### BC.3 Morphological Annealing & Abbott Caste Bridge `evolution_manager.py` (new) — 3 open

- [ ] [P2] **3.1 Abbott canonical templates** — align `entities.py:94 caste_name` ladder $K=3..64$, `shape line→Woman`, `Artisan iso≥60`, `Priest K>=24`: `Line/Woman K=3 r[1.8,0.2,0.2] φ[0,π±0.08]` (validate $θ<10°$ not self-intersecting), `Isosceles/Soldier K3 r[1.5,0.8,0.8] φ[0,2.4,3.88] θ≈30°`, `Equilateral K3 r1.0`, `Square K4`, `Polygon Noble K5..23`, `Circle/Priest K≥24 r1.0 φ=i·2π/K` plus `K=32,48,64` ultra-circles (K>24).

- [ ] [P2] **3.2 Annealing schedule $\lambda(g)$** — $g$ = `Creature.generation` `entities.py:134`:
    $$\lambda(g)=\begin{cases} morph\_lambda\_override & \text{if } \neq None \\ clamp(1-(g-g_{start})/g_{decay},0,1) & \text{else}\end{cases}$$
  where `morph_lambda_override: Optional[float]=None` `proposed 5.1` user-confirmed `Optional` (not `-1` sentinel), range `0.0..1.0` when set; `annealing_start_generation 50 0..1000`, `annealing_decay_generations 150 1..5000` `proposed 5.1`.

- [ ] [P2] **3.3 Inheritance & crossover + topological mutation** — interpolate
    $$r_i^{child}=λ·r_{template}+(1-λ)·clamp(r_{parent}+𝒩(0,σ_r^2),r_{min},r_{max})$$
    $$φ_i^{child}=λ·φ_{template}+(1-λ)·(φ_{parent}+𝒩(0,σ_φ^2))$$
  $\sigma_r$ `vertex_mutation_std 0.05 0..0.5`, $\sigma_φ$ `angle_mutation_std 0.02 0..0.5` `proposed 5.1`; sort $φ$ circularly to avoid bow-tie (not naive `argsort` breaking correspondence); topo $p=topological\_mutation\_rate·(1-λ)$ `0.01 0..0.2` add longest edge $K←min(KMAX,K+1)$ or remove closest angular neighbor $K←max(3,K-1)$; legacy `Creature.sides`→SoA converted on first tick; re-derive `caste_name` after.

#### BC.4 Energetic Asymmetry & Sexual Selection `simulation.py:6853` — 2 open

- [ ] [P2] **4.1 Energetic asymmetry** — median $A_{med}=median(morph_traits[:N,0])$ per birth batch $O(N\log N)$ (not per `eligible` `simulation.py:6876`); High $A≥med$ invest $35-50\%E_{\max}$, Low $A<med$ invest $5-10\%E_{\max}$ vs fixed `birth_energy_cost 20` `config.py:155` — needs balance pass vs `extinction` preset `food_count 120`.

- [ ] [P2] **4.2 Neural courtship & mate choice** — mate check `simulation.py:6884` female=`line`, `mate_radius 10` `config.py:149`, `mate_energy_min 30` `config.py:150`, `health≥50` `simulation.py:125` **plus** NN `social >0.5` from `outputs_buf[:,3]` `agent_soa.py:53` (`7 outputs thrust,steer,interact,social,vocal_amp,freq,recurrent`). **Gated behind `BA 8.1` hard switch** `TODO.md:80` (soft-gated `TODO Parked 9.2` `TODO.md:76`); do not wire until 8.1.

#### BC.5 God Laws, Presets & Live Dispatch `protocol.py:201, config.py:13, main.py:665,2016, frontend/src/god/GodPanel.tsx:22` — 3 open

- [ ] [P1] **5.1 Add 7 morphological laws to God API** — `GodLaws` `protocol.py:201` `Optional[Field(ge,le)]` + `Config` `config.py:13` frozen dataclass + `LAW_FIELDS` `main.py:665` whitelist + `frontend/src/types.ts:292 GodLaws` mirror + `GodPanel.tsx:22 NUMBER_LAWS: LawSpec` `min/max/step/group` + `GodPanel.tsx:172 GROUP_ORDER` new group `Morphology` + `wiki.py:322 LAW_HINTS_MD` hint:
  `morphology_annealing_enabled bool true`, `annealing_start_generation int 50 0..1000`, `annealing_decay_generations int 150 1..5000`, `morph_lambda_override Optional[float] None 0..1`, `vertex_mutation_std 0.05 0..0.5`, `angle_mutation_std 0.02 0..0.5`, `topological_mutation_rate 0.01 0..0.2` `proposed 5.1`.

- [ ] [P1] **5.2 Update presets `main.py:837`** — 7 bundles: `Theocracy morph_lambda_override 1.0` freeze Abbott, `Chaos start0 decay10 rate0.05`, `Balance 50/150 default`, `Extinction β1.5 winter chill on P` `proposed 5.2` (`extinction` already `food 120 winter 0.30` `main.py:1400`-ish). Extend `detect_current_preset` `main.py:1996` beyond food/cap heuristic.

- [ ] [P1] **5.3 Real-time observer** — when `energy_max/attack_damage/energy_decay_per_tick` in `updates` `main.py:2022`, queue `rebake_all()` for `morph_traits` (not immediate `O(N)` under `RT.lock` `main.py:2035`); `RT.sim.on_law_change` `main.py:2050` pattern.

#### BC.6 Telemetry, Profiling & SAT Narrowphase — 3 open

- [ ] [P2] **6.1 SAT narrowphase** — Broadphase `r_max=max r_i` via `morph_radii` + existing `World.query_radius_with_dist_sq_list` `world.py:215` / `spatial_grid.py`; Narrowphase `K_a+K_b≤128` edge normals projection overlaps; Impulse $J$ + health deduction via contacting $D_{\text{mult}}$ `proposed 6.1`.

- [ ] [P2] **6.2 Telemetry `GET /api/metrics/morphology`** — mirrors `/api/perf/telemetry` `main.py:2152` with `_PROCSTAT_CACHE` `main.py:2177` style; expose live `mean λ`, `mean K`, `mean A`, `mean P`, `θ_{\min}$ histogram, `asymmetry%`, paired with frontend panel (reuse `TOOD Phase6` `TODO.md:55` polling note — prefer WS, not HTTP `2s` poll).

- [ ] [P2] **6.3 Zero-alloc & profiling** — verify trait baking + SAT for `2000` agents `<4.0ms` per physics tick `proposed 6.3` `test_scale_benchmarks.py:41` target CPU; `numpy` batch `f32`, no per-tick allocations; fails → Park like `BA 9.4` `TODO.md:79`.

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

§F Infrastructure — Database · §A Life cycle · §B Reproduction · §C Irregularity & caste · §D Health & disease · §E Environment · §G God-law & observability · §H Food ecosystem · §I Society · §J Creature profile · §K Documentation · §L Shelter · Cross-system synergies · §W World generation · §N New frontiers · §O Ecosystem depth · §P Clan depth · §Q Creatures 2.0 · §R Weather as life · §S WorldBox inspirations · §T Sustainability & performance · §U Mobile UI/UX · §V Clan founding redesign · §X Fixes · §X2 Communication II · §Y UI polish · §Z Terminal frontend · §AA Performance round 2 · §AB Politics · §AC Desperation cannibalism · §AD OS-log persistence · §AE Food decay · §AF Performance & Massive Scale · §AG Autonomous Evolution · §AH Energy Dynamics · §AI TUI Feature Parity · §AJ Next-Gen Performance (3 phases) · §AK Clan Lifecycle · §AL Creature Cognitive Agency · §AM Food & Agriculture · §AN Communication, Language & Diplomatic · §AO Nocturnal Perils · §AP Unified Theology · §AQ 2D Physics · §AR Creature Senses · §AS Clan Leader Importance · §AT Four Immediate Issues · §AU Performance Optimizations · §AV Frontend & TUI Performance · §AW Emergency 1–2 TPS · §AX High-Density 20 TPS · §AY Multi-Core Engine · §AY2 World Simulation Presets · §AZ Backend Performance Audit · §BA Micro-Neural Network · §BC Geometric Physics & Morphological Evolution

Full completed content → [`docs/roadmap-archive.md`](docs/roadmap-archive.md)
