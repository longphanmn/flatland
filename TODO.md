# Flatland — World Simulation TODO

God model: god sets **laws**, never touches individual creatures. Everything else emerges.
Legend: [P0] foundational · [P1] core Flatland identity · [P2] flavor/observability

## F. Infrastructure — Database  [P0]
- [x] ~~SQLite via SQLAlchemy 2.0 + aiosqlite~~ → **stdlib `sqlite3`** behind a thin
      repository interface (`app/db.py`); file `flatworld.db` (env `FLATWORLD_DB`).
      Decision: local single-writer file needs no ORM/async driver yet; swap later
      without touching callers.
- [x] Tables: `worlds`, `events`, `law_changes`; `snapshots` deferred (replay is P2)
- [x] Writes are tiny batched inserts from the tick loop (WAL mode, thread-safe);
      measured cost per tick ≈ 0 — dedicated writer task unnecessary so far
- [x] Chronicle + law history survive server restart; `reset` closes the old
      `worlds` row and opens a new one
- [x] Endpoints: `GET /api/history?since=&limit=` (paginated), `GET /api/worlds`
- [x] Genealogy table (`creatures`): births write lineage rows (clan,
      generation, parents, born tick); deaths close them; founders get
      minimal rows on death

## A. Life cycle
- [x] [P0] Age & lifespan — Creature.age (ticks) + caste-based lifespan
      (Woman shortest → Priest longest); death cause `old_age`;
      god law `lifespan_mult`; snapshot exposes age/lifespan + dead_by_cause
- [x] [P1] Life stages — infant/juvenile/adult/elder by fraction of lifespan
      (<15/<30/<75%); stage multiplies speed & sight (infant 0.6², juvenile
      0.85², elder 0.85×0.9) and fertility (elder ×0.5, young infertile);
      `stage` in snapshot; renderer scales bodies (infant 0.55×) and fades elders
- [x] [P0] Death-cause chronicle — HistoryEvent.cause ∈
      {starvation, old_age, …}; HUD "dead" chip shows per-cause breakdown
      (tooltip); counts tracked in sim and persisted via DB events

## B. Reproduction & inheritance  [P1] — ✅ implemented
- [x] Sex model — males = polygons (sides ≥ 3), females = lines (women);
      `Creature.sex` derived from shape
- [x] Mating — adult male + adult female within `mate_radius`, both energy ≥
      `mate_energy_min`, not in cooldown → rng-gated by `birth_rate` ×
      caste fertilities × crowding factor
- [x] Offspring — `sex_ratio` decides son vs daughter; child spawns near
      mother; both parents pay `birth_energy_cost` + `reproduction_cooldown`
- [x] Lineage — Creature.generation/.born_tick/.mother_id/.father_id;
      birth payload persisted in DB events (genealogy graph still [P2])
- [x] Law of Nature — son sides = father.sides + 1, capped at `max_sides`;
      daughters are lines
- [x] Mutation — `mutation_rate` chance of ±1 side deviation
- [x] Isosceles rule — triangle sons stay triangles: iso_angle +0.5° per
      generation; reaching 60° promotes Soldier → Artisan (`promotion` event)
- [x] Fertility law — per-caste fertility table × soft penalty above
      `carrying_capacity`; hard `max_population` cap
      (deviation: table embodies Nature's decay; no separate `fertility_decay`)
- [x] GodLaws: birth_enabled, adult_age, mate_radius, mate_energy_min,
      birth_rate, sex_ratio, mutation_rate, max_sides, birth_energy_cost,
      reproduction_cooldown, carrying_capacity, max_population
- [x] Events: birth (payload parents/sides/generation), promotion

## C. Irregularity, caste & social order
- [x] [P1] Family/clan identity — founding generation seeds one clan per caste;
      children inherit their mother's clan (orphans found new ones);
      `clan_id` + crest color on every creature snapshot; thin colored crest
      ring in the renderer; clan shown in the inspector; birth events carry
      clan_id; DB genealogy table records lineage per world (entity, caste,
      clan, generation, parents, born/died ticks)
- [x] [P1] Irregularity — mutated children score `irregularity` (0.3–1.0);
      at adulthood the world judges them: ≥ `euthanasia_threshold` → consumed
      (death cause `euthanasia`), below → demoted to Soldier (lowest regular
      order, `demotion` event); god law `Euthanasia ≥` in God panel
- [x] [P0] Caste traits table — `CASTE_TRAITS` per caste: lifespan, speed,
      Sight Recognition (`sight_mult` applied to perception), fertility
      (reserved for §B); women see least, priests see farthest and are
      nearly sterile (Nature's Law)
- [x] [P2] Peace-cry — women emit a periodic ripple while moving (Flatland law)
- [x] [P2] Social yielding — lower castes deflect away from higher castes
      within a small radius (deference as steering force)

## D. Health & disease  [P2] — ✅ implemented
- [x] Creature.health (0–100, regenerates when healthy) + .infected/.disease_id
- [x] Outbreak — if `disease_enabled`, `disease_outbreak_rate`/tick starts a new
      `disease_id`; spreads to healthy neighbours within `disease_radius` at
      `disease_rate`
- [x] Effect — infected lose `disease_energy_drain`/tick + health decays at
      2×`disease_lethality`; recovery at `recovery_rate`; death when health → 0
      (cause `disease`). Disabling the law freezes all sickness instantly.
- [x] Season synergy — winter raises `disease_rate` ×1.5 (outbreak & contagion, §E)
- [x] GodLaws: Plagues toggle + outbreak/rate/radius/drain/recovery/lethality
      in a "Disease" panel group
- [x] Events: `outbreak`, `recovery` (+ death cause `disease`); HUD "infected N"
- [x] Render — pulsing green ring on the infected

## E. Environment — day/night, seasons, weather  [P2] — ✅ implemented
- [x] WorldClock — derived from tick: `time_of_day` (0–1, `day_length` cycle,
      world starts at sunrise), `day` counter, `season` over `season_length`
- [x] Day/night — night applies `night_sight_mult`; renderer dims the sky
      (smooth sunrise→noon→midnight gradient)
- [x] Seasons — food target = `food_count × SEASON_FOOD_MULT`
      (spring 1.0, summer 1.2, autumn 1.0, winter 0.5); spring ×1.25
      `birth_rate`, winter ×1.5 outbreak + contagion
- [x] Weather state machine — clear/rain/fog/storm at `weather_change_rate`;
      rain/storm slow movement (`rain_speed_mult`), fog dims sight
      (`fog_sight_mult`), storms add wander chaos (`storm_wander_bonus`)
- [x] GodLaws: Sky & Seasons panel group (lengths, multipliers + Weather
      allowed toggle)
- [x] Render — night veil, season tint, rain streaks (heavier in storms),
      fog overlay
- [x] HUD — 🌙/☀ · day N · season · weather icon

## G. God-law & observability
- [x] [P0] Consolidate ALL new laws into GodLaws + God screen UI (grouped by
      section: World / Food & Energy / Hunger & Sight / Movement / Life &
      Death / Bodies & Houses; grows as §B/§D/§E laws arrive)
- [x] [P2] Population/caste sparkline chart in HUD (+ stacked caste chart in
       the Chronicle panel, §N)
- [x] [P2] Chronicle shows all event types (birth/promotion/demotion/recovery/
       outbreak/death — color-coded in the panel); header combines live
       population `Soldier 6 · Gentleman 4 · … · Food 24 · House 6` with caste
       colors (`App.tsx:461`), legend via `CasteChart`; new world clears the
       live feed (`App.tsx:129`, tick/seed reset detection)
- [x] [P2] Creature inspector — tap/click a creature (works on touch too):
       gold halo marks it; left panel shows live status (caste, sex, stage,
       age/lifespan, energy/health bars, meals, irregularity, lineage) and its
       personal chronicle from `GET /api/creature/{id}`; auto-refreshes 1 Hz;
       survives death (status + full history remain)
- [x] [P2] DB-backed history pagination + world run selector (landed with the
       Chronicle pagination + HUD run dropdown, commit 9fed747); archive mode
       pauses live feed, `load older` paginates via `GET /api/history?since=`

## H. Food ecosystem & ecological balance  [P2] — ✅ implemented
- [x] Plants replace inert food — `Food` is a living plant with `growth` 0.15→1.0
       (`plant_growth_rate`), spreads to nearby empty cells (`plant_spread_rate`,
       season-gated), dies back in winter (reuses `SEASON_FOOD_MULT`); rendered green,
       size ∝ growth; `food_count` law is the seasonal bounty target (name kept)
- [x] Carcasses — every death leaves a `Corpse` (`corpse_ttl`, `corpse_energy`);
       creatures scavenge them like food; decay → vanishes
- [x] Nutrient cycle — decayed corpses refill nutrient pool that accelerates
       nearby plant regrowth (`nutrient_cycle_rate` × `NUTRIENT_BOOST`): death fertilises new life
- [x] Ecological balance — plant counts oscillate with seasonal bounty; boom–bust via
       `SEASON_FOOD_MULT` + nutrient boost (Lotka–Volterra placeholder until §I predators)
- [x] GodLaws: plant_growth_rate, plant_spread_rate, nutrient_cycle_rate (plant_mature gated)
- [x] Events: `bloom` (plant reaches maturity)

## I. Society: clans, interaction & conflict
- [x] [P1] Clans (base identity) — landed in §C: one clan per caste at founding,
      children inherit mother's clan, clan crest ring + inspector + genealogy.
      What remains below is the *social* layer on top of that identity.
- [x] [P1] Clan relations — pairwise score −100..+100 drifting toward 0; ally /
       neutral / rival thresholds; shared feeding raises it (+2 within `flock_radius`),
       drift `relation_drift_rate` toward 0; `alliance`/`rivalry` events
- [x] [P2] Creature interaction (boids) — separation / cohesion / alignment
       steering blended after food-seeking (social yielding already landed in §C);
       "Interaction" law group (`cohesion_weight`, `alignment_weight`, `separation_weight`, `flock_radius`)
- [ ] [P2] Predation — a Carnivore predator caste with behaviour priority
      flee → hunt → forage → reproduce → rest; bite-on-contact kills prey (death
      cause `predation`), leaves a carcass, feeds the predator; prey flee within
      `fear_radius`
- [ ] [P2] Clan war — rival-clan creatures fight on contact (`attack_radius`,
      `attack_damage`); loser dies (cause `war`) → carcass + relation penalty
- [x] GodLaws (partial): relation_drift_rate, alliance_threshold, rivalry_threshold,
       cohesion_weight, alignment_weight, separation_weight, flock_radius
       (predator laws deferred: predator_ratio, hunt_radius, bite_damage, …)
- [x] Events (partial): `alliance`, `rivalry` (predation/war deferred to §I predation)

## J. Creature profile & genealogy  [P0] — ✅ implemented
- [x] Genealogy table — landed in §F (creatures rows: parents, caste, generation,
      clan, born/died ticks); surfaced via the profile below
- [x] Expose lineage on the wire — `mother_id`/`father_id`/`sex`/meals now on
      `EntityState`; `/api/creature/{id}` returns a `family` block (mother/
      father cards alive-or-dead via genealogy, living + recorded children)
- [x] Profile UI — status chips (hungry/starving/sick/asleep), clickable
      parent links († marks the dead) and a compact family tree: parents
      above, "you are here", children below; every node opens that dossier
      with click-to-navigate

## K. Documentation — living guide  [P2] — ✅ implemented
Serve a full reference independent of the React game UI (backend-rendered, so it
always matches the running code). No Vite/frontend dependency.
- [x] Backend serves the docs — FastAPI route(s) at `/guide` that render
       markdown to HTML (tiny `md_to_html` + minimal template); nav sidebar;
       anchor links. Reachable at http://localhost:8000/guide (`guide.py:307`)
- [x] "How the world works" — the God model (god sets laws, never touches a life),
       the deterministic fixed-tick loop, emergence; each system explained: life
       cycle & stages, Nature's Law inheritance (sides/sex/mutation), irregularity &
       caste judgement, disease, environment (day/night, seasons, weather), clans &
       social order, food economy (`guide.py:172`)
- [x] Codebase map — module tour with file:line anchors: backend
       (config/entities/world/simulation/protocol/db/main) + frontend
       (App/CanvasRenderer/GodPanel/Inspector); data-flow diagram of the tick (`guide.py:205`)
- [x] Data model & protocol — creature/caste/food/house/clan/genealogy entities;
       `EntityState`/`StateMessage`/`HistoryEvent` schemas; WebSocket message flow
       (hello → state snapshots, client control actions) (`guide.py:229`)
- [x] API reference — auto-generated from the live OpenAPI schema (`/openapi.json`):
       every REST route, request/response model, control action, and every God law
       with type/range/default; link out to the interactive Swagger `/docs` (`guide.py:144`)
- [x] Configuration & ops — env var table (`FLATWORLD_*`), persistence (SQLite
       `flatworld.db`, `worlds`/`events`/`law_changes`/`creatures` tables), run &
       deploy, test commands (`guide.py:246`)
- [x] Anti-rot check — `tests/test_guide.py`: asserts every `GodLaws` field and every REST
       route is mentioned in the docs, so the guide can't silently go stale; roadmap
       section links back to TODO.md (`guide.py:330`)

## L. Shelter — make houses matter  [P1] — ✅ backend delivered
Houses today are ~5 empty squares: walls block movement and creatures nap inside
after dark (§N night rest). Shelter should be scarce, contested and life-saving.
- [x] [P1] Exposure — rain/storm and winter nights drain `exposure_drain` energy on the
       open plain; being indoors cancels it. Shelter becomes survival, not convenience.
- [x] [P1] House capacity — each house shelters at most `house_capacity` creatures
       (∝ size); the overflow sleeps outside and suffers exposure. Five houses is a
       real housing shortage (beds re-contested every tick in id order).
- [x] [P1] Clan claim — each clan claims a house as its settlement (clan crest on
       the wall via `House.clan_id`/`clan_color`; members prefer own house via `_house_for`);
       founding clans claim distinct houses; new clans claim first free house; toggle via law
- [x] [P2] Rest & recovery — indoors: energy regen halved via `sleep_energy_mult` +
       `rest_recovery_mult` (×0.15 health/tick) disease recovery; shelter law toggle
- [ ] [P2] Predator refuge — the doorway is too small for the Carnivore caste (§I);
       a house is the only safe haven once predators hunt.
- [ ] [P2] Settlement economy — houses scale with population (house_density tied to
       carrying capacity); abandoned houses crumble to ruins; new clans found new ones.
- [x] GodLaws: shelter_enabled, exposure_drain, house_capacity, house_claim_enabled,
       rest_recovery_mult (Shelter group)

## Cross-system synergies (emergent depth)
Not features — acceptance criteria. Tick only after the behaviour is observable in a
live run (or a seeded test passes). `needs` = prerequisite systems; `verify` =
observable signal; `tune` = god laws that push it over the edge.

### Verifiable now (systems landed) — ✅ tested
- [x] Winter + disease = famine/plague cascades
       needs §D+§E · verify: winter → infected & starving spike together, deaths by
       starvation+disease climb · tune: season_length, disease_rate, food_count
- [x] High mutation = irregularity purges
       needs §B+§C · verify: mutation_rate↑ → euthanasia/demotion events surge at
       adulthood · tune: mutation_rate, euthanasia_threshold
- [x] Overpopulation = lower fertility + higher disease spread
       needs §B+§D · verify: pop past carrying_capacity → births fade, contagion rises
       · tune: carrying_capacity, max_population, disease_radius
- [x] Night + fog = blindness
       needs §E · verify: fog at night collapses sight (starving rate rises) · tune:
       night_sight_mult, fog_sight_mult
- [x] Seeded tests — backend/tests/test_synergies.py: one deterministic test per
       verifiable-now synergy (winter+plague, mutation→purge, overcrowd→fertility+
       disease, night+fog blindness), reusing the fixed-tick RNG pattern from
       test_disease.py / test_environment.py

### Blocked on §H (food ecosystem) + §I (predation/clan war)
- [ ] Predator–prey oscillation (Lotka–Volterra) — needs §H+§I · verify: predator/prey
      counts oscillate out of phase · tune: predator_ratio, hunt_radius, plant_growth_rate
- [x] Death feeds life — needs §H (corpses already land in §N) · verify: post-die-off,
       corpse decay + nutrient pool accelerates plant regrowth · tune: corpse_ttl,
       nutrient_cycle_rate (test_plants.py: test_corpse_decay_boosts_nearby_plant_growth)
- [ ] War over scarce food — needs §H+§I · verify: famine → clan rivalry drops → wars
      spike → corpses feed survivors · tune: rivalry_threshold, attack_damage
- [ ] Flocking is a double-edged sword — needs §I+§D · verify: clan cohesion dilutes
      predator attacks but super-spreads disease · tune: cohesion_weight, disease_rate
- [ ] Predators as natural selection — needs §H+§I · verify: starving/elder/wounded prey
      culled first, survivor stats shift · tune: hunt_radius, bite_damage, fear_radius
- [ ] Winter as apex pressure — needs §E+§H+§I · verify: one winter stacks die-back +
      starvation + hunting + plague into real extinction risk · tune: season_length,
      SEASON_FOOD_MULT, disease_rate
- [ ] Mutation → demotion → fodder — needs §C+§I · verify: demoted soldiers swell both
      prey and warrior ranks · tune: mutation_rate, euthanasia_threshold, attack_damage
- [ ] Social order meets the food chain — needs §C+§I · verify: priests see the predator
      first and flee, women fall, low castes trapped by yielding · tune: sight_mult,
      yield_strength, fear_radius
- [ ] Housing shortage = overcrowding = disease + war — needs §L+§D+§I · verify: pop
      > total house capacity → exposure deaths climb, contagion spreads in packed
      houses, clan claims turn into wars · tune: house_capacity, exposure_drain

## W. World generation  — ✅ implemented
- [x] Population & houses scale with map area: `creature_density`,
      `house_density` (per unit²) with ±`spawn_variance` jitter; Flatland
      social pyramid shares (soldiers/women many, nobles/priests few);
      explicit `num_*` overrides still win (scenarios/tests)
- [x] Reset rolls a fresh random seed — every reset is a new world, recorded
      (with its seed) in the DB and shown in the HUD; same seed ⇒ same world

## N. New frontiers — round two
- [x] [P1] Corpses & scavenging — death leaves a corpse (`corpse_energy`,
      fading cross renderer); creatures perceive and eat them like food;
      corpses decay after `corpse_ttl`; god laws: corpses toggle + ttl +
      energy; famine now has a second chance built in
- [x] [P2] Night rest — at night creatures head for the nearest house; those
      inside sleep (movement stops, hunger halved via `sleep_energy_mult`,
      health +0.3/tick, disease still bites); `sleeping` in snapshot with zzz
      renderer cue; Night rest toggle in the Sky & Seasons law group
- [x] [P2] Terrain — seeded fertile patches (food spawns there ~70% of the
      time via `fertile_food_bias`) and solid rock circles (radial push-out);
      auto-scaled by area or pinned; drawn under entities; in snapshot
- [x] [P2] Keyboard controls — space pause/resume · S step · R reset ·
          +/- zoom · F fit view (ignored while typing in inputs)
- [x] [P2] Caste population chart — stacked per-caste lines (caste colors)
      over the last ~240 ticks, inside the Chronicle panel
- [x] [P2] Snapshot album — 📷 freezes the full state into the DB
      `snapshots` table; Album lists them and clicking one re-renders that
      frozen moment on the canvas (banner to return to the living world)
