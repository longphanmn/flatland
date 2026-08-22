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

## Cross-system synergies (emergent depth)
- Winter + disease = famine/plague cascades · high mutation = irregularity purges ·
  overpopulation = lower fertility + higher disease spread · night + fog = blindness

## W. World generation  — ✅ implemented
- [x] Population & houses scale with map area: `creature_density`,
      `house_density` (per unit²) with ±`spawn_variance` jitter; Flatland
      social pyramid shares (soldiers/women many, nobles/priests few);
      explicit `num_*` overrides still win (scenarios/tests)
- [x] Reset rolls a fresh random seed — every reset is a new world, recorded
      (with its seed) in the DB and shown in the HUD; same seed ⇒ same world
