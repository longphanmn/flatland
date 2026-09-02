# Flatland — World Simulation TODO

The Sphere model: The Sphere (God) sets **laws** from Spaceland, never touches individual creatures. Everything else emerges.
Legend: [P0] foundational · [P1] core Flatland identity · [P2] flavor/observability · `- [ ]` open · `- [x]` done · *parked* = decided, not pending

> **Active backlog only.** Completed roadmaps §F–§BF (647 items) → [`docs/roadmap-archive.md`](docs/roadmap-archive.md). This file tracks the **22 open items across §BG (Mutational Shape & Visual Phenotypes) & §BH (Next-Gen Mutation Engine & Neuroevolution) + 8 parked**.

---

## §BG Mutational Shape & Visual Phenotypes — Open (12 items)

### Phase 1: Dynamic Mutated Geometry & Razor Isosceles (Canvas2D & SVG) [P0]
- [ ] [P0] **BG-1 True Isosceles Soldier razor apex** — Render Soldiers with their true `iso_angle` ($\theta_{\text{iso}} \in [10^\circ, 59.5^\circ]$) pointing forward along velocity heading in `renderCore.ts` and `CreatureAvatar.tsx` instead of equilateral triangles.
- [ ] [P0] **BG-2 Dynamic mutated polygon geometry** — Procedurally reconstruct and render irregular, asymmetric polygons on canvas using `(sides, irregularity, seed, id)` with vertex radii offsets and angular jitter.
- [ ] [P0] **BG-3 Line caste (Woman) variable thickness & taper** — Render Women with variable tip sharpness and mid-span taper reflecting perimeter and metabolic genes.
- [ ] [P0] **BG-4 Topological aberration rendering** — Render non-standard vertex counts ($K \in [3,24]$, e.g., 7-sided noble, 11-sided aberration) with accurate vertex distribution.

### Phase 2: Visual Mutational Phenotypes & Accents [P1]
- [ ] [P1] **BG-5 Blade Glint (Kinetic Pierce Accent)** — Render a highlighted neon glint on the creature's sharpest interior vertex ($\theta_{\min}$) scaled by attack damage.
- [ ] [P1] **BG-6 Heavy Inertia Armor** — Render double-layered perimeter strokes and darker fill opacity for creatures with high rotational inertia $I_{zz}$ and large Shoelace area $A$.
- [ ] [P1] **BG-7 Speciation chromatic aberration** — Add iridescent dual-tone edge accents as $\lambda(g) \to 0$ (high generational divergence from Abbott orthodoxy).
- [ ] [P1] **BG-8 Elder lineage nucleus** — Render an internal inscribed geometric core or ancestral glyph inside high-generation elders and clan chiefs.

### Phase 3: Inspector Polar Radar & Biomechanical Dossier [P1]
- [ ] [P1] **BG-9 Polar Morphology Radar in Inspector** — Interactive SVG radar overlay in `Inspector.tsx` showing the creature's mutated polygon against the ghosted orthodox Abbott template.
- [ ] [P1] **BG-10 Biomechanical trait HUD** — Display live computed metrics: Sharpness Index ($\theta_{\min}$), Irregularity score ($\sigma_r^2/\bar{r}$), Rotational Inertia ($I_{zz}$), and Shoelace Area ($A$).

### Phase 4: Mutation Lab Lineage Tree & Morphospace [P2]
- [ ] [P2] **BG-11 Morphological Phylogeny Tree** — Visual ancestral drift tree in `MutationLab.tsx` showing geometric evolution from founding Platonic solids to aberrant polyforms.
- [ ] [P2] **BG-12 Morphospace 2D Scatterplot** — Interactive Area vs. Sharpness scatterplot in Mutation Lab visualizing emergent sub-species clusters.

---

## §BH Next-Gen Evolutionary Mutation Engine & Neuroevolution — Open (10 items)

> **Context**: Decouples evolution from rigid template decay so populations continue speciation even at $\lambda=0.00$. Integrates true two-parent polar crossover, macro-mutations, stress mutagenesis, real-time NN weight evolution (295 weights), and emergent behavioral niches. See `mutation_evolution_brainstorm.md` for full design.

### Phase 1: Two-Parent Polar Crossover & Speciation at $\lambda=0$ [P0]
- [ ] [P0] **BH-1 Two-Parent Meiotic Polar Crossover** — Recombine polar sector arcs from Mother and Father in `evolution_manager.py` `child_morphology()` with vertex-count interpolation $K_{\text{child}} \in [K_{\text{mother}}, K_{\text{father}}]$.
- [ ] [P0] **BH-2 Macro-Mutation Spurts (5% chance at $\lambda=0$)** — Add discrete structural mutations: *Apex Weaponization* (stretching one vertex $+50\text{--}100\%$), *Facet Shielding* (flattening front edges), and *Radial Crystallization* (regularizing into star polyforms).
- [ ] [P0] **BH-3 Stress-Induced Mutagenesis** — Double morphological mutation variance ($\sigma_r \times (1 + 1.5 \cdot \text{stress})$) during famine ($\text{larder} < 50$) or severe epidemic outbreaks.

### Phase 2: Neural Network (NN) Genome Evolution (295 weights) [P0–P1]
- [ ] [P0] **BH-4 Real-time NN Genome Crossover on Birth** — Hook up `crossover_mutate` in `simulation.py` `_birth()` so every newborn inherits hybridized neural controller weights from both parents.
- [ ] [P1] **BH-5 Functional-Block NN Mutation Rates** — Apply block-specific mutation rates: Sensory $W_1$ ($p=0.03, \sigma=0.06$), Motor $W_2$ ($p=0.05, \sigma=0.10$), and Recurrent Memory $W_{\text{rec}}$ ($p=0.02, \sigma=0.04$).
- [ ] [P1] **BH-6 Behavioral Inversion Mutations (0.5% chance)** — Implement sensory sign-flip mutations (attraction $\leftrightarrow$ repulsion, daylight $\leftrightarrow$ night-forage preference).
- [ ] [P1] **BH-7 Neuro-Morphological Sensor Coupling** — Scale forward ray sensitivity by tip sharpness $\theta_{\min}$ and sensory cone span by body perimeter/area.

### Phase 3: Emergent Behavioral Archetypes & Observability [P1–P2]
- [ ] [P1] **BH-8 Nocturnal Forager & Sentry Policy Evolution** — Allow night-active mutants with chill tolerance to forage under darkness while diurnal creatures sleep.
- [ ] [P1] **BH-9 Behavioral Archetype Auto-Classifier** — Automatically classify and tag creature policies in UI (`[Apex Hunter]`, `[Nocturnal Forager]`, `[Granary Courier]`, `[Sentry Guard]`).
- [ ] [P2] **BH-10 Inspector NN Connectivity Heatmap** — Render interactive neural connectivity matrix ($16 \to 12 \to 7$) in `Inspector.tsx` showing active synaptic pathways.

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
1. **BH-1 Polar Crossover before BG-9 Inspector Radar** — Two-parent geometry structure must be stabilized before wireframe visualizer binds to it.
2. **BH-4 Live NN crossover on `_birth` before BH-5 block rates** — Base crossover wiring in `_birth` must exist before adding block-wise mutation rates.
3. **BG-1 Isosceles & BG-2 Mutated Polygons can land independently in frontend** without touching backend simulation loop.

---

## Archive index
§F Infrastructure — Database · §A Life cycle · §B Reproduction · §C Irregularity & caste · §D Health & disease · §E Environment · §G God-law & observability · §H Food ecosystem · §I Society · §J Creature profile · §K Documentation · §L Shelter · Cross-system synergies · §W World generation · §N New frontiers · §O Ecosystem depth · §P Clan depth · §Q Creatures 2.0 · §R Weather as life · §S WorldBox inspirations · §T Sustainability & performance · §U Mobile UI/UX · §V Clan founding redesign · §X Fixes · §X2 Communication II · §Y UI polish · §Z Terminal frontend · §AA Performance round 2 · §AB Politics · §AC Desperation cannibalism · §AD OS-log persistence · §AE Food decay · §AF Performance & Massive Scale · §AG Autonomous Evolution · §AH Energy Dynamics · §AI TUI Feature Parity · §AJ Next-Gen Performance (3 phases) · §AK Clan Lifecycle · §AL Creature Cognitive Agency · §AM Food & Agriculture · §AN Communication, Language & Diplomatic · §AO Nocturnal Perils · §AP Unified Theology · §AQ 2D Physics · §AR Creature Senses · §AS Clan Leader Importance · §AT Four Immediate Issues · §AU Performance Optimizations · §AV Frontend & TUI Performance · §AW Emergency 1–2 TPS · §AX High-Density 20 TPS · §AY Multi-Core Engine · §AY2 World Simulation Presets · §AZ Backend Performance Audit · §BA Micro-Neural Network · §BC Geometric Physics & Morphological Evolution · §BD World Analytics & Telemetry Engine · §BE Creature Movement AI Overhaul · §BF Early Population Boom Limiter

Full completed content → [`docs/roadmap-archive.md`](docs/roadmap-archive.md)
