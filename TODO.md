# Flatland — World Simulation TODO

The Sphere model: The Sphere (God) sets **laws** from Spaceland, never touches individual creatures. Everything else emerges.
Legend: [P0] foundational · [P1] core Flatland identity · [P2] flavor/observability · `- [ ]` open · `- [x]` done · *parked* = decided, not pending

> **Active backlog only.** Completed roadmaps §F–§BD (632 items: 573 §F–§BA + 14 §BC + 12 §AZ + 33 §BD) → [`docs/roadmap-archive.md`](docs/roadmap-archive.md) (all 14 BC + 12 AZ + 33 BD archived 2026-08-31, symbols kept, anchors stripped). This file tracks the **0 open (all 18 Morphological Physics Evolution & Density-Dependent Soft-Cap Damping done 2026-08-31) + 8 parked** items that remain.

---

## Open work — 0 items (Morphological Physics Evolution & Density-Dependent Soft-Cap Damping — ✅ Done 18/18)

### Project Status & Architectural Context
- **Completed**:
  1. Micro Elman RNN Inference Engine ($16 \to 12 \to 7$), Continuous NumPy SoA Buffers, 2D Spatial Hash Grid, Multi-rate Loop (60 Hz physics / 15 Hz inference).
  2. Extinction Safeguards Engine (Tier 1 relief, Tier 2 biological emergency, Tier 3 spontaneous genesis).
- **Current Objectives**:
  1. **Geometric Physics & Morphological Evolution**: Implement polar polygon genomes $(r_i, \phi_i)$ with $K \in [3, 24]$ vertices, governed by **Morphological Annealing** $\lambda(g)$ and Abbott canonical templates.
  2. **Density-Dependent Soft-Cap Damping**: Eliminate hard population limits by introducing non-linear homeostatic damping ($\xi(N)$) on fertility rates, birth energy costs, reproduction cooldowns, metabolic stress, and resource strain.
- **Runtime Target**: Python 3.10+ / NumPy (Vectorized batch execution, zero-allocation runtime).

---

### Phase 1: Morphological Genome & SoA Memory Expansion (`agent_soa.py`) — ✅ Done (KMAX 24)
- [x] [P0] **1.1 Expand Structure of Arrays (SoA) Buffers for Geometry** — `agent_soa.py` `KMAX 24` (migrated from 64, `physical_traits` alias)
  - [x] Add `morph_radii`: `np.ndarray((N, 24), dtype=np.float32)` (Vertex radial distances $r_i \in [0.2, 2.5]$).
  - [x] Add `morph_angles`: `np.ndarray((N, 24), dtype=np.float32)` (Monotonically sorted polar angles $\phi_i \in [0, 2\pi)$).
  - [x] Add `morph_k`: `np.ndarray((N,), dtype=np.int32)` (Active vertex count per agent, $3 \le K \le 24$).
  - [x] Add `physical_traits`: `np.ndarray((N, 6), dtype=np.float32)`:
    - Slot 0: `area` ($A$) via Shoelace formula.
    - Slot 1: `perimeter` ($P$) via Euclidean edge summation.
    - Slot 2: `rotational_inertia` ($I_{zz}$) around centroid.
    - Slot 3: `min_vertex_angle` ($\theta_{\min}$) sharpest interior vertex.
    - Slot 4: `asymmetry_index` ($\sigma_r^2 / \bar{r}$) irregularity indicator.
    - Slot 5: `kinetic_damage_mult` ($D_{\text{mult}}$).
  - [x] Add `reproduction_role`: `np.ndarray((N,), dtype=np.int8)` ($+1$: Brood carrier / high-investment, $-1$: Mobile fertilizer / low-investment).

---

### Phase 2: Geometric Physics Engine & Trait Baking (`morphology_engine.py`) — ✅ Done
- [x] [P0] **2.1 Implement Polar Geometric Formulations** — `morphology_engine.py` `KMAX 24` vectorized batch
  - [x] `compute_polygon_vertices(r, phi, k) -> (x, y)`: Convert polar arrays to local Cartesian coordinates.
  - [x] `compute_shoelace_area(x, y, k) -> float`: Calculate enclosed 2D area $A = \frac{1}{2} \left|\sum (x_i y_{i+1} - x_{i+1} y_i)\right|$.
  - [x] `compute_perimeter(x, y, k) -> float`: Calculate boundary perimeter $P = \sum \sqrt{(x_{i+1}-x_i)^2 + (y_{i+1}-y_i)^2}$.
  - [x] `compute_moment_of_inertia(x, y, k) -> float`: Calculate polar moment of inertia $I_{zz}$ around centroid for steering resistance.
  - [x] `compute_min_vertex_angle(x, y, k) -> float`: Find sharpest interior tip angle $\theta_{\min} = \min_i \arccos\left(\frac{\vec{u}_i \cdot \vec{v}_i}{\|\vec{u}_i\| \|\vec{v}_i\|}\right)$.
  - [x] `compute_asymmetry_index(r, k) -> float`: Calculate variance of vertex distances from centroid.
- [x] [P1] **2.2 Implement Trait Baking on Birth (`bake_physical_traits`)** — `morphology_engine.py` + `simulation.py` observer
  - [x] *Energy Capacity*: $E_{\max} = \text{god\_laws.energy\_max} \times \text{clamp}\left(\frac{A}{A_{\text{ref}}}, 0.5, 2.5\right)$.
  - [x] *Metabolic Burn Rate*: $\text{decay} = \text{god\_laws.effective\_energy\_decay} \times \text{clamp}\left(\frac{P}{P_{\text{ref}}}, 0.7, 2.0\right)$.
  - [x] *Kinetic Piercing Damage*: $\text{Damage} = \text{god\_laws.attack\_damage} \times \max\left(0, \frac{\cos\theta_{\min} - \cos 60^\circ}{1 - \cos 60^\circ}\right)$.
  - [x] *Steering Resistance*: Scale angular turn velocity $\Delta\theta = \text{steer\_output} \times \left(\frac{\text{god\_laws.steer\_turn}}{1.0 + I_{zz} / I_{\text{ref}}}\right)$.
  - [x] *Euthanasia Evaluation*: If $\text{asymmetry} > \text{god\_laws.euthanasia\_threshold}$ and `safeguard_morph_mercy` is false, flag agent for societal absorption.

---

### Phase 3: Morphological Annealing & Abbott Caste Bridge (`evolution_manager.py`) — ✅ Done
- [x] [P1] **3.1 Define Canonical Abbott Caste Templates** — `evolution_manager.py` `K ∈ [3,24]`
  - [x] Template `Woman/Line`: $K=3$, $r = [1.8, 0.2, 0.2]$, $\phi = [0, \pi - 0.08, \pi + 0.08]$ (Tip angle $\theta < 10^\circ$, area $A \approx 0$).
  - [x] Template `Soldier/Isosceles`: $K=3$, $r = [1.5, 0.8, 0.8]$, $\phi = [0, 2.4, 3.88]$ ($\theta \approx 30^\circ$).
  - [x] Template `Tradesman/Equilateral`: $K=3$, $r = [1.0, 1.0, 1.0]$, $\phi = [0, \frac{2\pi}{3}, \frac{4\pi}{3}]$.
  - [x] Template `Noble/Square & Polygon`: $K=4..12$, regular $K$-gons ($r_i = 1.0, \phi_i = \frac{2\pi i}{K}$).
  - [x] Template `Priest/Circle`: $K=24$, regular 24-gon ($r_i = 1.0, \phi_i = \frac{2\pi i}{24}$).
- [x] [P0] **3.2 Implement Annealing Schedule ($\lambda(g)$)** — `evolution_manager.py` `lambda_for_generation`
  - [x] Calculate dynamic annealing factor:
    $$\lambda(g) = \begin{cases} 
      \text{god\_laws.morph\_lambda\_override}, & \text{if } \text{override} \ge 0 \\
      \text{clamp}\left(1.0 - \frac{g - g_{\text{start}}}{g_{\text{decay}}}, 0.0, 1.0\right), & \text{otherwise}
    \end{cases}$$
- [x] [P1] **3.3 Morphological Inheritance & Crossover Engine** — `evolution_manager.py` `child_morphology`
  - [x] Interpolate offspring morphology between canonical caste template and mutated parental genes:
    $$r_i^{(\text{child})} = \lambda(g) \cdot r_{i,\text{template}} + (1 - \lambda(g)) \cdot \text{clamp}\left(r_{i,\text{parent}} + \mathcal{N}(0, \sigma_r^2), r_{\min}, r_{\max}\right)$$
    $$\phi_i^{(\text{child})} = \lambda(g) \cdot \phi_{i,\text{template}} + (1 - \lambda(g)) \cdot \left(\phi_{i,\text{parent}} + \mathcal{N}(0, \sigma_\phi^2)\right)$$
  - [x] Sort $\phi_i$ with minimum angular clearance check ($\Delta\phi \ge \frac{2\pi}{K_{\max} \times 1.5}$) to avoid self-intersecting polygons.
  - [x] **Topological Drift**: With probability $P_{\text{topo}} = \text{god\_laws.topological\_mutation\_rate} \times (1 - \lambda(g))$:
    - Insert vertex on longest edge ($K \leftarrow \min(24, K + 1)$).
    - Merge closest pair of adjacent vertices ($K \leftarrow \max(3, K - 1)$).

---

### Phase 4: Density-Dependent Soft-Cap Damping Engine (`density_damping.py`) — ✅ Done (7/7)
- [x] [P0] **4.1 Implement Real-time Overpopulation Stress Index ($\xi(N)$)** — `density_damping.py` `compute_xi` 1 Hz (`density_damping.py:14` `xi=(N-Kcap)/Kcap` if `N>Kcap` and `soft_cap_enabled`)
  - [x] Run evaluation at 1 Hz: Compute active population count $N = \text{count}(\text{active\_mask})$.
  - [x] Calculate stress factor:
    $$\xi(N) = \begin{cases} 
      \frac{N - K_{\text{cap}}}{K_{\text{cap}}}, & \text{if } N > K_{\text{cap}} \text{ and } \text{soft\_cap\_enabled} \\
      0.0, & \text{otherwise}
    \end{cases}$$
- [x] [P0] **4.2 Apply 4 Multi-Channel Damping Equations** — `density_damping.py` `scales(xi)` + `simulation.py` integration (`simulation.py:7204` `density_damping.compute_xi` + `scales_for_xi`)
  - [x] **Channel 1 (Reproductive Suppression)**:
    - Effective birth probability: $\text{birth\_rate}_{\text{eff}} = \frac{\text{god\_laws.birth\_rate}}{1.0 + \text{god\_laws.damping\_steepness} \cdot \xi(N)^2}$.
    - Effective birth cost: $\text{birth\_cost}_{\text{eff}} = \text{god\_laws.birth\_energy\_cost} \times (1.0 + 1.5 \cdot \xi(N))$.
    - Effective cooldown: $\text{cooldown}_{\text{eff}} = \text{int}(\text{god\_laws.reproduction\_cooldown} \times (1.0 + 2.0 \cdot \xi(N)))$.
  - [x] **Channel 2 (Crowding Stress)**:
    - Effective metabolic drain: $\text{decay}_{\text{eff}} = \text{god\_laws.energy\_decay\_per\_tick} \times (1.0 + \text{god\_laws.crowding\_stress\_mult} \cdot \xi(N))$.
  - [x] **Channel 3 (Ecological Strain)**:
    - Effective plant growth: $\text{plant\_growth}_{\text{eff}} = \frac{\text{god\_laws.plant\_growth\_rate}}{1.0 + \text{god\_laws.resource\_strain\_mult} \cdot \xi(N)}$.
    - Effective seed spread: $\text{plant\_spread}_{\text{eff}} = \frac{\text{god\_laws.plant\_spread\_rate}}{1.0 + 2.0 \cdot \xi(N)}$.
  - [x] **Channel 4 (Social Friction & Pathogens)**:
    - Effective disease outbreak rate: $\text{disease\_outbreak}_{\text{eff}} = \text{god\_laws.disease\_outbreak\_rate} \times (1.0 + 3.0 \cdot \xi(N))$.
- [x] [P0] **4.3 Eliminate Hard-Cap Code Blocks** — `simulation.py` / `reproduction.py` (`simulation.py:7225` `room` soft `0.05` floor, `hard-cap removed` `pop>=max_pop` → `pop>=max_pop*3` safety, `birth_rate_eff` in `fert` check)

---

### Phase 5: Energetic Reproduction Asymmetry & Integration (`reproduction.py` + `simulation.py`) — ✅ Done
- [x] [P1] **5.1 Energetic Reproduction Roles (Anisogamy)** — `simulation.py` median $A$ (Tier1 `reproduction_role` via `physical_traits` `area` median)
  - [x] Assign reproductive roles based on median body area:
    - *Brood Carrier* ($A \ge A_{\text{median}}$): Invests $35\text{--}50\%$ of $E_{\max}$ into offspring tissue creation.
    - *Mobile Fertilizer* ($A < A_{\text{median}}$): Invests $5\text{--}10\%$ of $E_{\max}$ for genetic transfer.
- [x] [P1] **5.2 Neural Courtship & Mating Execution** — `simulation.py` `social > 0.5` gated, `safeguard_eta` scaled `vertex/angle sigma` when $\eta>0$
  - [x] Trigger mating when two agents are within `god_laws.mate_radius` (effective `*1+η`), both possess `energy > mate_energy_min_effective` (`*1-0.5η`), and both exhibit neural output `social_action > 0.5`.
  - [x] Allow piercing/predatory phenotypes to clash via SAT impulses before mating rights.

---

### Phase 6: God Laws Schema, Presets & Live Observer (`protocol.py`, `config.py`, `main.py`) — ⏳ Open (4 tasks, morphology done, soft-cap pending)
- [x] [P0] **6.1 Add Morphology & Safeguard Parameters to God Laws API** — `protocol.py` `GodLaws` 7 morph + 5 safeguard (12 total) + `safeguard_engine` done, `safeguard_morph_mercy` gate at euthanasia
  - [x] `morphology_annealing_enabled` (bool, default `false`).
  - [x] `annealing_start_generation` (int, default `50`, range `0–1000`).
  - [x] `annealing_decay_generations` (int, default `150`, range `1–5000`).
  - [x] `morph_lambda_override` (float, default `-1.0`, range `[-1.0, 1.0]`).
  - [x] `vertex_mutation_std` (float, default `0.05`, range `[0.0, 0.5]`).
  - [x] `angle_mutation_std` (float, default `0.02`, range `[0.0, 0.5]`).
  - [x] `topological_mutation_rate` (float, default `0.01`, range `[0.0, 0.2]`).
  - [x] `safeguard_enabled` (bool, default `true`).
  - [x] `safeguard_critical_pop` (int, default `12`, range `2–50`).
  - [x] `safeguard_relief_ratio` (float, default `0.30`, range `[0.05, 0.5]`).
  - [x] `safeguard_genesis_batch` (int, default `6`, range `1–20`).
  - [x] `safeguard_morph_mercy` (bool, default `true`).
- [x] [P0] **6.1b Add Soft-Cap Parameters to God Laws API** — `protocol.py` `GodLaws` 4 new (`soft_cap_enabled` true, `damping_steepness` 6.0, `crowding_stress_mult` 0.35, `resource_strain_mult` 1.2) + `config.py` `Config`
  - [x] `soft_cap_enabled` (bool, default `true`).
  - [x] `damping_steepness` (float, default `6.0`, range `[1.0, 20.0]`).
  - [x] `crowding_stress_mult` (float, default `0.35`, range `[0.0, 1.0]`).
  - [x] `resource_strain_mult` (float, default `1.2`, range `[0.0, 2.0]`).
- [x] [P1] **6.2 Update Simulation Presets for Dynamic Equilibrium** — `main.py` `PRESETS` 7× (`Theocracy` 4.0, `Chaos` 10.0 + 0/10, `Sustainable` 8.0/0.2, `Boom` 800/3.0)
  - [x] `Theocracy`: `morph_lambda_override = 1.0`, `damping_steepness = 4.0` (Abbott castes, stable theological population).
  - [x] `Chaos`: `annealing_start_generation = 0`, `annealing_decay_generations = 10`, `topological_mutation_rate = 0.05`, `damping_steepness = 10.0` (High volatility, rapid boom/bust cycles).
  - [x] `Sustainable`: `damping_steepness = 8.0`, `crowding_stress_mult = 0.2` (Gentle stabilization at carrying capacity).
  - [x] `Boom`: `carrying_capacity = 800`, `damping_steepness = 3.0` (Large metropolis capacity before damping engages).
- [x] [P1] **6.3 Real-time Law Mutation Observer** — `simulation.py` `on_law_change` re-bakes `physical_traits` (already for morphology/safeguard) + `main.py` `apply_laws` handles `soft_cap` damping scales via `density_damping` 1 Hz (no re-bake needed, scales computed on fly)

---

### Phase 7: SAT Narrowphase Collision, Telemetry & Profiling — ✅ Done (7/7)
- [x] [P1] **7.1 Separating Axis Theorem (SAT) with Circle Approximation Fallback** — `morphology_engine.py` `sat_overlap` + `simulation.py` `r_max` broadphase, `K≥24 && asym<0.05` circle fallback (`simulation.py:5945` branch)
  - [x] *Broadphase*: Spatial Hash Grid query via Bounding Radius $r_{\max} = \max_i r_i$.
  - [x] *Circle Approximation*: If $K \ge 24$ and $\text{asymmetry} < 0.05$, use Circle-Polygon projection test (both circles distance check).
  - [x] *Polygon SAT*: For $K < 24$, test projection overlaps on edge normals.
  - [x] Apply collision impulse $J$ and deduct health based on tip sharpness $D_{\text{mult}}$.
- [x] [P1] **7.2 Telemetry API Endpoints (`/api/metrics`)** — `main.py` `GET /api/metrics/morphology` done; `GET /api/metrics/safeguards` done (`N,η,tier,miracles,mercy`); `GET /api/metrics/damping` done (`N,xi,birth_rate_eff,decay_eff`)
  - [x] `/api/metrics/morphology`: Return live $\bar{\lambda}$, mean vertices $\bar{K}$, mean area $\bar{A}$, mean perimeter $\bar{P}$, sharpness distribution, and asymmetry ratio.
  - [x] `/api/metrics/safeguards`: Return current active population $N$, relief factor $\eta(N)$, active safeguard tier, and miracle event counts.
  - [x] `/api/metrics/damping`: Return $N$, $\xi(N)$, and effective `birth_rate/decay` rates (soft-cap observability) — `main.py:2310` `get_damping_metrics`.
- [x] [P0] **7.3 Performance Verification** — `scripts/bench_morphology.py` (lazy bake 10 + 100 SAT + safeguard 1 Hz) `0.41ms` per tick avg (`<4ms` target) — `bake 2000` full is `57ms` but lazy is realistic (only new agents baked per tick).

---

## Parked — decided, not pending (8 items; 9 before dedupe)

These are documented decisions with rationale, not overdue work. The original 22 unchecked items included 9 such; 2 were the same task.

| # | Item | Rationale |
|---|------|-----------|
| 1 | **AQ P2 Wind affects thrown weapon range** | No thrown-weapon system to bend (spears are melee buffs). Revisit when ranged combat exists. |
| 2 | **AQ P2 Ramps / staircases** | Needs vertical layer semantics the flat-point body model doesn't have; grades already cost/slow. |
| 3 | **AQ P2 Weight & load-bearing** | Planiverse beam mechanics need a structural graph; walls already block except doors. |
| 4 | **AZ P2 `__slots__` on `Config`** | Single instance, every `self.config.X` is a dict lookup — low win. Verify `RT.config` never gains dynamic attrs. |
| 5 | **BA P1 6.3 + P0 7.4 Rebless the determinism golden** *(consolidated)* | Re-record `backend/tests/test_determinism_golden.py` checkpoints (ticks 100/250/500) for the NN engine. Deferred until NN fully replaces `AL` utility AI (currently soft-gated; `7.4` was a duplicate of `6.3`). |
| 6 | **BA P1 9.2 Fill sensor slots 9–13** | Slots remain 0; full scent/signal integration needs §AN grid wiring — deferred to avoid churn before 8.1 hard switch. |
| 7 | **BA P0 9.4 Vectorize the raycast sensor loop** | Python loop stays within 50 ms CI budget (`test_n2000_budget` ≤50 ms; 12 ms target is N150). Defer numpy vectorization until profiling shows bottleneck. |
| 8 | **BA P0 10.1 Extend `test_neuroevolution.py`** | Deferred until 8.1 hard switch — soft-gated wiring would make tests flaky. Current 8 tests cover SoA/genome/forward/sensors/mating/latch/budget. |

---

## Guardrails

### Conflict map — what must **not** land in parallel [P0]
1. **Phase 1 SoA (`agent_soa.py` `KMAX 24`) gates all** — `morphology_engine` + `evolution_manager` + `safeguard_engine` + `density_damping` + `simulation.py` trait baking all depend on SoA width; land Phase 1 first alone.
2. **Phase 2 `morphology_engine` before Phase 5 safeguards & Phase 4 damping** — trait slots `physical_traits` are read by `eta` mercy and `xi` damping; baking must exist.
3. **Phase 6 Laws before Phase 7 telemetry** — `GodLaws` 4 soft-cap fields must exist before `/api/metrics/damping` can expose `xi`.
4. **Phase 5 Tier 3 genesis & Phase 4 genesis both touch `world.add` + `soa.add_agent`** — do not land with Phase 5 `reproduction.py` `world.add` batch; serialize (now both completed, but new density damping also touches `world` via plant growth).
5. **Phase 3 `K∈[3,24]` clamp** — `evolution_manager` `K=round(lam*Tk+(1-lam)*Pk)` must clamp `3..24`, not `64`; verify with `agent_soa` capacity 24.
6. **BC archived vs new `K 24`** — old BC used `KMAX 64` ultra-circles `32/48/64`; new spec caps at `24` (Priest circle). Migration `K>24 → K=24` + shim `morph_traits` alias.

### Suggested order
**New spec: Phase 1 → Phase 2 → Phase 3 → Phase 6 (laws) → Phase 4 (damping, needs laws) → Phase 5 (safeguards + anisogamy, needs laws) → Phase 7 (SAT + metrics, needs laws + safeguards + damping).** Archive of old BC/AZ/BD already done, so no AZ/BC conflict.

### Out of scope — these change the laws of the world
Audited, quantified, and **deliberately excluded**. Do not start without revisiting the scope rule.
- **Prune `Creature.trust`** — O(N) per creature, O(N²) total, zero `trust.pop`/`del`. Excluded: capping changes who a creature trusts — a law change.
- **TTL-prune `Creature.give_ups`** — cleared only on successful meal. Forgetting is a behaviour change.
- **Stagger the plant symbiosis query** — one spatial query per growing plant per tick. Damping changes growth outcomes.
- **Throttle the temperature field** — staggering changes chill → mortality.
- **Partial `_refresh_cache`** — skipping house/clan sub-loops risks stale derived state.
- **Suppress `recovery` events from persistence** — 1.07 M rows, 41% of the 448 MB DB. Changes the visible chronicle.
- **Incremental `rebuild_index`** — needs `world.mark_moved()` dirty-set refactor.
- **Narrow `RT.lock` around `step()`** — biggest structural win but only safe via copy-on-write.
- **Wire up the native C core / add numpy** — `native_boids_forces` has zero call sites; `world.py` force-disables. Excluded: fast-math drift breaks determinism.
- **`parallel.py`** — fresh `ProcessPoolExecutor` per call with `chunksize=1`, ~800 pickle round-trips/tick. Dead code; delete or redesign.

---

## Archive index
§F Infrastructure — Database · §A Life cycle · §B Reproduction · §C Irregularity & caste · §D Health & disease · §E Environment · §G God-law & observability · §H Food ecosystem · §I Society · §J Creature profile · §K Documentation · §L Shelter · Cross-system synergies · §W World generation · §N New frontiers · §O Ecosystem depth · §P Clan depth · §Q Creatures 2.0 · §R Weather as life · §S WorldBox inspirations · §T Sustainability & performance · §U Mobile UI/UX · §V Clan founding redesign · §X Fixes · §X2 Communication II · §Y UI polish · §Z Terminal frontend · §AA Performance round 2 · §AB Politics · §AC Desperation cannibalism · §AD OS-log persistence · §AE Food decay · §AF Performance & Massive Scale · §AG Autonomous Evolution · §AH Energy Dynamics · §AI TUI Feature Parity · §AJ Next-Gen Performance (3 phases) · §AK Clan Lifecycle · §AL Creature Cognitive Agency · §AM Food & Agriculture · §AN Communication, Language & Diplomatic · §AO Nocturnal Perils · §AP Unified Theology · §AQ 2D Physics · §AR Creature Senses · §AS Clan Leader Importance · §AT Four Immediate Issues · §AU Performance Optimizations · §AV Frontend & TUI Performance · §AW Emergency 1–2 TPS · §AX High-Density 20 TPS · §AY Multi-Core Engine · §AY2 World Simulation Presets · §AZ Backend Performance Audit · §BA Micro-Neural Network · §BC Geometric Physics & Morphological Evolution · §BD World Analytics & Telemetry Engine

Full completed content → [`docs/roadmap-archive.md`](docs/roadmap-archive.md)
