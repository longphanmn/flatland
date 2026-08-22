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
- [ ] Genealogy table (`creatures`) when reproduction lands (§B)

## A. Life cycle
- [x] [P0] Age & lifespan — Creature.age (ticks) + caste-based lifespan
      (Woman shortest → Priest longest); death cause `old_age`;
      god law `lifespan_mult`; snapshot exposes age/lifespan + dead_by_cause
- [ ] [P1] Life stages — infant/juvenile/adult/elder scale speed, sight, fertility;
      render size/alpha by stage; elder = faded outline, infant = small + dim
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
- [ ] [P1] Irregularity — mutation may mark child irregular (deviation value);
      below tolerance → demoted to lowest civil-servant caste;
      above `euthanasia_threshold` → killed at maturity (cause `euthanasia`)
- [x] [P0] Caste traits table — `CASTE_TRAITS` per caste: lifespan, speed,
      Sight Recognition (`sight_mult` applied to perception), fertility
      (reserved for §B); women see least, priests see farthest and are
      nearly sterile (Nature's Law)
- [ ] [P2] Peace-cry — women emit a visible ripple while moving (renderer effect)
- [ ] [P2] Social yielding — lower castes steer away from higher castes (repulsion)

## D. Health & disease  [P2]
- [ ] Creature.health (0–100) + .infected/.disease_id
- [ ] Outbreak — if `disease_enabled`, `disease_outbreak_rate`/tick starts a new
      `disease_id`; spreads to healthy neighbors within `disease_radius` at `disease_rate`
- [ ] Effect — infected lose `disease_energy_drain`/tick + health decay;
      recovery at `recovery_rate`, else death when health → 0 (cause `disease`)
- [ ] Season synergy — winter raises `disease_rate` (see §E)
- [ ] GodLaws: `disease_enabled, disease_outbreak_rate, disease_rate, disease_radius,
      disease_energy_drain, recovery_rate, disease_lethality`
- [ ] Events: `outbreak_start`, `disease_death`, `recovered`; HUD "infected N"
- [ ] Render — infected creatures tinted green / pulsing

## E. Environment — day/night, seasons, weather  [P2]
- [ ] WorldClock — `time_of_day` (0–1, cycle `day_length` ticks); `day` counter;
      `season` index over `season_length` ticks (4 seasons)
- [ ] Day/night — night applies `night_sight_mult` to perception; renderer dims sky
- [ ] Seasons — food law target = `food_count × season_food_mult`
      (spring 1.0, summer 1.2, autumn 1.0, winter 0.5); spring ↑ `birth_rate`,
      winter ↑ `disease_rate`
- [ ] Weather state machine — clear/rain/fog/storm; transitions at `weather_change_rate`
      - rain: `speed_mult` 0.85 · fog: sight × `fog_sight_mult` · storm: wander chaos
- [ ] GodLaws: `day_length, season_length, night_sight_mult, season_food_mults,
      weather_enabled, weather_change_rate, fog_sight_mult`
- [ ] Render — sky tint by time-of-day, season tint, rain particles, fog overlay
- [ ] HUD — day/season/time-of-day + weather icon + clock

## G. God-law & observability
- [x] [P0] Consolidate ALL new laws into GodLaws + God screen UI (grouped by
      section: World / Food & Energy / Hunger & Sight / Movement / Life &
      Death / Bodies & Houses; grows as §B/§D/§E laws arrive)
- [ ] [P2] Population/caste sparkline chart in HUD
- [ ] [P2] Chronicle shows all event types (birth/promotion/euthanasia/outbreak/death)
- [ ] [P2] Creature inspector — click/tap a creature to select it; side panel shows
      live status (caste, sex, age/lifespan, energy, hunger, generation, parents)
      plus its personal history from the chronicle/DB (born, promotions, meals,
      children, death); highlight selected entity on canvas
- [ ] [P2] DB-backed history pagination + world run selector

## Cross-system synergies (emergent depth)
- Winter + disease = famine/plague cascades · high mutation = irregularity purges ·
  overpopulation = lower fertility + higher disease spread · night + fog = blindness
