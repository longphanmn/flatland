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
- [ ] Season synergy — winter raises `disease_rate` (lands with §E)
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
- [ ] [P2] Population/caste sparkline chart in HUD
- [x] [P2] Chronicle shows all event types (birth/promotion/demotion/recovery/
      outbreak/death — color-coded in the panel)
- [x] [P2] Creature inspector — tap/click a creature (works on touch too):
      gold halo marks it; left panel shows live status (caste, sex, stage,
      age/lifespan, energy/health bars, meals, irregularity, lineage) and its
      personal chronicle from `GET /api/creature/{id}`; auto-refreshes 1 Hz;
      survives death (status + full history remain)
- [ ] [P2] DB-backed history pagination + world run selector

## H. Food ecosystem & ecological balance  [P2]
- [ ] Plants replace inert food — `Plant` entity grows toward maturity
      (`plant_growth_rate`), spreads to nearby empty cells (`plant_spread_rate`,
      season-gated), dies back in winter (reuses `SEASON_FOOD_MULT`); rendered green,
      size ∝ growth; `food_count` law becomes the plant bounty target (name kept)
- [ ] Carcasses — every death leaves a `Carcass` decaying over
      `carcass_decay_ticks`; scavengers/predators eat it before it vanishes
- [ ] Nutrient cycle — decayed carcasses refill a nutrient pool that accelerates
      plant regrowth (`nutrient_cycle_rate`): death fertilises new life
- [ ] Ecological balance — track plant/prey/predator counts (trophic levels);
      boom–bust oscillation and collapse are expected, not bugs (Lotka–Volterra)
- [ ] GodLaws: plant_growth_rate, plant_spread_rate, plant_mature_size,
      carcass_decay_ticks, nutrient_cycle_rate (+ predator laws in §I)
- [ ] Events: `bloom` (plant reaches maturity), `carcass` (spawn/consumed)

## I. Society: clans, interaction & conflict
- [x] [P1] Clans (base identity) — landed in §C: one clan per caste at founding,
      children inherit mother's clan, clan crest ring + inspector + genealogy.
      What remains below is the *social* layer on top of that identity.
- [ ] [P1] Clan relations — pairwise score −100..+100 drifting toward 0; ally /
      neutral / rival thresholds; shared kills & feeding raise it, kills lower it
- [ ] [P2] Creature interaction (boids) — separation / cohesion / alignment
      steering blended after food-seeking (social yielding already landed in §C);
      "Interaction" law group
- [ ] [P2] Predation — a Carnivore predator caste with behaviour priority
      flee → hunt → forage → reproduce → rest; bite-on-contact kills prey (death
      cause `predation`), leaves a carcass, feeds the predator; prey flee within
      `fear_radius`
- [ ] [P2] Clan war — rival-clan creatures fight on contact (`attack_radius`,
      `attack_damage`); loser dies (cause `war`) → carcass + relation penalty
- [ ] GodLaws: predator_ratio, hunt_radius, bite_damage, bite_cooldown,
      energy_from_prey, fear_radius, war_enabled, attack_radius, attack_damage,
      relation_drift_rate, alliance_threshold, rivalry_threshold
- [ ] Events: `predation`, `war`, `attack`, `clan_founded`, `alliance`, `rivalry`

## J. Creature profile & genealogy  [P0]
- [x] Genealogy table — landed in §F (creatures rows: parents, caste, generation,
      clan, born/died ticks); what remains is surfacing it in the UI
- [ ] Expose lineage on the wire — `mother_id`/`father_id`/`sex` still live only on
      the Creature, not on `EntityState` (clan_id/meals are already sent); add them +
      a parents/children lookup to `/api/creature/{id}` and a `/tree` endpoint
- [ ] Profile UI — inspector already shows caste · sex · clan · age/lifespan ·
      energy/health · meals · stage; add a **status chip** (hungry/starving/sick/
      infected) and **clickable parent links** (`mother #12` / `father #8`) that open
      that creature's dossier, plus a compact family tree (parents above, children
      below) with click-to-navigate

## K. Documentation — living guide  [P2]
Serve a full reference independent of the React game UI (backend-rendered, so it
always matches the running code). No Vite/frontend dependency.
- [ ] Backend serves the docs — FastAPI route(s) at `/guide` that render
      `docs/*.md` to HTML (stdlib `markdown` + a minimal template); nav sidebar;
      anchor links. Reachable at http://localhost:8000/guide
- [ ] "How the world works" — the God model (god sets laws, never touches a life),
      the deterministic fixed-tick loop, emergence; each system explained: life
      cycle & stages, Nature's Law inheritance (sides/sex/mutation), irregularity &
      caste judgement, disease, environment (day/night, seasons, weather), clans &
      social order, food economy
- [ ] Codebase map — module tour with file:line anchors: backend
      (config/entities/world/simulation/protocol/db/main) + frontend
      (App/CanvasRenderer/GodPanel/Inspector); data-flow diagram of the tick
- [ ] Data model & protocol — creature/caste/food/house/clan/genealogy entities;
      `EntityState`/`StateMessage`/`HistoryEvent` schemas; WebSocket message flow
      (hello → state snapshots, client control actions)
- [ ] API reference — auto-generated from the live OpenAPI schema (`/openapi.json`):
      every REST route, request/response model, control action, and every God law
      with type/range/default; link out to the interactive Swagger `/docs`
- [ ] Configuration & ops — env var table (`FLATWORLD_*`), persistence (SQLite
      `flatworld.db`, `worlds`/`events`/`law_changes`/`creatures` tables), run &
      deploy, test commands
- [ ] Anti-rot check — a small test asserts every `GodLaws` field and every REST
      route is mentioned in the docs, so the guide can't silently go stale; roadmap
      section links back to TODO.md

## Cross-system synergies (emergent depth)
- Winter + disease = famine/plague cascades · high mutation = irregularity purges ·
  overpopulation = lower fertility + higher disease spread · night + fog = blindness
- Predator–prey oscillation (Lotka–Volterra): predators over-hunt prey → prey crash →
  predator crash → plant overgrowth → prey recovery; tune to a stable limit cycle or
  a collapse
- Death feeds life: carcass decay → nutrient pool → plant regrowth — war, predation
  and euthanasia all become fertiliser; a purge or plague becomes a bloom
- War over scarce food: crowding past carrying capacity spikes clan rivalry →
  resource wars; war carcasses then feed the survivors (grim Malthusian loop)
- Flocking is a double-edged sword: clan cohesion clusters creatures → safety in
  numbers, but also amplifies disease spread and attracts predators; fog turns the
  cluster into an ambush
- Predators as natural selection: they cull the starving, elder and wounded first;
  fog + night turn hunters into invisible executioners; prey evolve flight
- Winter as apex pressure: plants die back, prey starve, predators hunt the
  desperate, disease spreads in the cold — the deepest extinction risk lands in a
  single season
- Mutation → irregularity → demotion → fodder: demoted soldiers swell the prey and
  warrior ranks, feeding both the food web and the war machine
- Social order meets the food chain: Sight Recognition decides who sees the predator
  first (priests flee, women fall); social yielding can trap a low caste between a
  predator and a higher caste's shadow

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
- [ ] [P2] Night rest — at night creatures seek the nearest house and sleep
      inside: movement stops, energy decay halves, health regenerates faster;
      they leave at sunrise; `sleeping` flag in snapshot + zzz renderer cue
- [ ] [P2] Terrain — seeded map features: fertile patches bias food spawns;
      rocky circles block movement (radial push-out); drawn under entities
- [x] [P2] Keyboard controls — space pause/resume · S step · R reset ·
          +/- zoom · F fit view (ignored while typing in inputs)
- [ ] [P2] Caste population chart — client-side history panel: stacked lines
          per caste over recent ticks next to the sparkline
- [ ] [P2] Snapshot album — 📷 button stores a frozen full-state photo into
          the DB `snapshots` table; album list lets you re-view any moment on
          the canvas without touching the live simulation
