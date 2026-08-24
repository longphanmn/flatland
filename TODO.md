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
       Death / Bodies & Houses; grows as §B/§D/§E laws arrive) — **Save** persists
       to future worlds (`POST /api/laws?persist=true` → `RT.saved_config`),
       **Apply** current only (`?persist=false` → revert on Reset, `main.py:259`,
       `GodPanel.tsx:127`)
- [x] [P2] Population/caste sparkline chart in HUD (+ stacked caste chart in
       the Chronicle panel, §N)
- [x] [P2] Chronicle shows all event types (birth/promotion/demotion/recovery/
       outbreak/death — color-coded in the panel); header combines objects
       `Food 48 · House 6` (creatures in graph, `App.tsx:455`), legend via
       `CasteChart`; new world clears the live feed (`App.tsx:129`, tick/seed
       reset); box at top-right (`index.css:117`, `top:58px`, `max-height:60vh`)
- [x] [P2] Creature inspector — tap/click a creature (works on touch too):
       gold halo marks it; left panel shows live status (caste, sex, stage,
       age/lifespan, energy/health bars, meals, irregularity, lineage) and its
       personal chronicle from `GET /api/creature/{id}`; auto-refreshes 1 Hz;
       survives death (status + full history remain) (`inspect/Inspector.tsx:83`,
       `CanvasRenderer.tsx:181` pick `4.0/24` world units, tap `500ms/10px` forgiving,
       dead-zone `6px` pan vs tap, tap at `tapStart` not release, edge-safe)
- [x] [P2] DB-backed history pagination + world run selector (Chronicle pagination +
       HUD run dropdown → moved to bottom-right `App.tsx:534` `run-switcher`
       `index.css:182`); archive mode pauses live feed, `load older` paginates via `GET /api/history?since=`

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
- [x] [P2] Predation — Carnivore `Predator` caste (`entities.py:47`, `config.py:128`)
       `is_predator`/`bite_cooldown`; spawn `predator_ratio` only if `predation_enabled`
       (`simulation.py:255`), hunt `hunt_radius` → bite `bite_cooldown`/`energy_from_prey`,
       prey `fear_radius` flee; death `predation` + `predation` event, carcass + relation
- [x] [P2] Clan war — rival-clan creatures fight on contact (`war_enabled`,
       `attack_radius`/`attack_damage` → cause `war`, `war` event, relation -5, carcass)
       (`simulation.py:469`, `config.py:137`)
- [x] GodLaws: relation_drift_rate, alliance_threshold, rivalry_threshold,
       cohesion_weight, alignment_weight, separation_weight, flock_radius,
       predation_enabled, predator_ratio, hunt_radius, bite_damage, bite_cooldown,
       energy_from_prey, fear_radius, war_enabled, attack_radius, attack_damage
- [x] Events: `alliance`, `rivalry`, `predation`, `war` (+ `predation`/`war` deaths)

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

## L. Shelter — make houses matter  [P1] — ✅ implemented
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
       `rest_recovery_mult` (×0.15 health/tick) disease recovery; shelter law toggle;
       starving creatures skip sleep to forage (`simulation.py:885`)
- [x] [P2] House smart — doorway targeting (`_door_pos` `simulation.py:345`, sleep
       steering `simulation.py:993` within 12u), wall-bounce → door seeking
       (`simulation.py:1072`), starving skip prevents house-wall starvation
- [x] [P2] Predator refuge — the doorway is too small for the Carnivore caste (§I);
        a house is the only safe haven once predators hunt (`simulation.py:1178`
        predator_blocked doorway, `simulation.py:1093` prey indoors safe from
        `hunt_radius`, `simulation.py:939` predators never sleep, ejected if spawned inside).
- [x] [P2] Settlement economy — houses scale with population (house_density tied to
        carrying capacity via `_target_house_count` `simulation.py:356`; `area×house_density×carrying/80` vs `0.6×carrying/house_capacity`); abandoned houses crumble to ruins after `house_decay_ticks` (`simulation.py:399`, `config.py:113`, `protocol.py:184` → `ruin` event, `House.is_ruin` `entities.py:192`, walls no longer block `simulation.py:1507`); new clans found new settlements when no free house (`_claim_house_for_clan` `simulation.py:311` → `_spawn_settlement_house` `simulation.py:373` → `settlement` event; pinned `num_houses` `simulation.py:390` still wins for tests/scenarios).
- [x] GodLaws: shelter_enabled, exposure_drain, house_capacity, house_claim_enabled,
        rest_recovery_mult, house_decay_ticks (Shelter group) — defaults tuned for 30-day survival
        (`config.py:108`, food 48, decay 0.05, perceive 18, mate 10/30, birth 0.35, adult 200)
- [x] [P1] Beds ∝ floor area — `house_capacity` counts beds in an 8×8 reference
        hall (`HOUSE_REF_AREA`, `simulation.py` `_house_beds`): a cramped hut
        holds half a grand hall's beds, so a whole clan can never cram into one
        shelter. Full roof ⇒ overflow spills to the NEAREST roof WITH space
        (`_house_for`; kin-preferred among free roofs), queueing at a door only
        when every roof is full; a sleeper already inside any roof with a free
        bed takes it instead of trekking on. Rest means STILL — a sleeping body
        holds its exact position until dawn (early-return night branch).
        Tests: `tests/test_shelter.py` (beds scale with size, spill to second
        roof, sleeping = zero movement); live check @321 pop: 0 over-capacity
        houses, 154/321 asleep across 72 houses.

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

### Blocked on §H (food ecosystem) + §I (predation/clan war) — we unblocked five
- [x] Predator–prey oscillation (Lotka–Volterra) — needs §H+§I · verify: predator/prey
        counts coexist and vary (test_synergies.py: test_predator_prey_oscillation,
        16 prey + 6 pred → 600 ticks, predation ≥5, both vary, not extinct) · tune:
        predator_ratio, hunt_radius, plant_growth_rate (predation hunt/fear/bite,
        `simulation.py:981` flee/hunt, `is_predator` lineage)
- [x] Death feeds life — needs §H (corpses already land in §N) · verify: post-die-off,
        corpse decay + nutrient pool accelerates plant regrowth · tune: corpse_ttl,
        nutrient_cycle_rate (test_plants.py: test_corpse_decay_boosts_nearby_plant_growth)
- [x] War over scarce food — needs §H+§I · verify: famine → clan rivalry drops → wars
        spike → corpses feed survivors · tune: rivalry_threshold, attack_damage
        (`test_synergies.py:test_war_over_scarce_food` famine 2 vs 20 food, 8 rivals packed, 60 ticks, wars famine ≥ abundance)
- [x] Flocking is a double-edged sword — needs §I+§D · verify: clan cohesion dilutes
       predator attacks but super-spreads disease (test_synergies.py:
       test_flocking_is_double_edged — tight flock vs spread, infection + predation) ·
       tune: cohesion_weight, disease_rate (`simulation.py:981` boids + disease)
- [x] Predators as natural selection — needs §H+§I · verify: starving/elder/wounded prey
       culled first, survivor stats shift · tune: hunt_radius, bite_damage, fear_radius
       (`test_synergies.py:test_predators_as_natural_selection` weak 3 close vs healthy 3 far, predation ≥2 weak culled, healthy ≥ weak)
- [x] Winter as apex pressure — needs §E+§H+§I · verify: one winter stacks die-back +
       starvation + hunting + plague into real extinction risk · tune: season_length,
       SEASON_FOOD_MULT, disease_rate (`test_synergies.py:test_winter_as_apex_pressure` winter 180 vs summer 60, 8 prey+2 pred+disease, winter deaths ≥ summer)
- [x] Mutation → demotion → fodder — needs §C+§I · verify: demoted soldiers swell both
       prey and warrior ranks · tune: mutation_rate, euthanasia_threshold, attack_damage
       (`test_synergies.py:test_mutation_demotions_well_fodder` mutation 0.9 Threshold 0.45 → demotion ≥2 soldiers swell)
- [x] Social order meets the food chain — needs §C+§I · verify: priests see the predator
       first and flee, women fall, low castes trapped by yielding · tune: sight_mult,
       yield_strength, fear_radius (`test_synergies.py:test_social_order_meets_food_chain` priest 1.35× vs woman 0.8×, priest distance ≥ woman after 60 ticks)
- [x] Housing shortage = overcrowding = disease + war — needs §L+§D+§I · verify: pop
        > total house capacity → exposure deaths climb, contagion spreads in packed
        houses, clan claims turn into wars · tune: house_capacity, exposure_drain
        (`test_synergies.py:test_housing_shortage_is_overcrowding_crisis` 1 house×2 beds vs 5 houses×2 beds 10 packed rivals, rain+night exposure 0.45, 80 ticks)

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

## O. Ecosystem depth — biodiversity & food web  [P2] — ✅ implemented
Today every plant is one green sprite (`Food.growth`) and the only animal is the
Predator. Add variety so niches, seasons and diets can emerge.
- [x] [P2] Plant species — `Food.variant` ∈ {grass, berry, mushroom, poisonous}:
      grass common/low-energy; berries high-energy but seasonal; mushrooms sprout
      on corpses/rocks (a decomposer tier); poisonous plants mutate in and sicken
      whoever eats them. Each variant: color, growth rate, energy yield, season
      (`entities.py:169` `Food.variant`, `simulation.py:49` `VARIANT_*`,
      `simulation.py:530` `_pick_variant` poison 0.03 + season + decomposer boost,
      `simulation.py:782` `VARIANT_GROWTH_MULT`×`SEASON_MULT`, `simulation.py:1376` eating `VARIANT_ENERGY/HEALTH`,
      `protocol.py:39` `EntityState.variant`, `frontend/CanvasRenderer.tsx:280` colors, `config.py:44` `plant_variants_enabled`/`poison_rate`).
- [x] [P2] Fruit & seasonality — berry bushes fruit in one season (autumn burst);
      grass is always available; spring/summer shift which plants dominate the land
      (`simulation.py:542` autumn berry 0.48 weight, winter mushroom 0.57, `VARIANT_SEASON_MULT` grass 1.15 summer, berry 1.9 autumn).
- [x] [P2] Wild herbivore beasts — a non-caste middle tier that grazes plants and is
      hunted by predators, competing with the castes for food → a real
      plants → herbivores → predators Lotka–Volterra chain
      (`entities.py:40` `Herbivore` 5200/0.65, `entities.py:122` `is_herbivore`,
      `config.py:46` `beast_ratio` 0.0 default (god enables), `simulation.py:205`
      `_spawn_herbivore`, `simulation.py:289` spawn `area×density×beast_ratio`,
      `simulation.py:1030` herbivore lineage 50% if one parent, `simulation.py:680` war excludes herbivore, shelter excludes herbivore).
- [x] [P2] Diet & preference — `Creature.diet` (herbivore/omnivore/carnivore) steers
      which food a creature perceives and eats; higher castes prefer richer food,
      predators prefer live prey over plants (`simulation.py:1304` `diet_strictness` filter: herbivore ignores corpse, predator ignores plants, strict >0.5 higher castes skip grass if berry nearby, herbivore avoids poisonous; `config.py:46` `diet_strictness` 0.0 default).
- [x] [P2] Food quality — variants yield different energy/health (meat heals, poison
      harms); scavenging corpses vs grazing plants reward different creatures
      (`VARIANT_ENERGY` grass 32/berry 48/mushroom 24/poison 8, `VARIANT_HEALTH` berry +1/poison -30, corpse 25).
- [x] [P2] Trophic HUD — plant / herbivore / predator counts chart (the §H ecological
      balance made watchable) (`frontend/src/render/TrophicChart.tsx` stacked Food·Herbivore·Predator vs `popHist`, `App.tsx:469` under CasteChart).
- [x] GodLaws: plant_variants_enabled, poison_rate, beast_ratio, diet_strictness (Ecosystem `config.py:44` `protocol.py:123` `main.py:184` `GodPanel.tsx:15`)

## P. Clan depth — totems, territory & war  [P2]
Clans have identity (crest ring) and a first taste of war (§I) but no totem, no land
beyond one house, no leaders. Deepen the social fabric.
- [x] [P2] Totem — each clan picks a totem at founding with a subtle buff: Wolf
      (hunt), Tree (harvest/growth), Shield (defense), Eye (sight); drawn as a totem
      pole beside the clan's house; buff applied to its members (`simulation.py:68` `TOTEMS`/`TOTEM_BUFF`,
      `simulation.py:323` deterministic `seed+cid` → totem, `config.py:54` `totems_enabled`, `protocol.py:129` `totems_enabled`,
      `simulation.py:1350` Wolf +2 `hunt_radius`/`1.10×speed`, `simulation.py:1558` Tree `1.25×` harvest, `simulation.py:724` Shield `0.70×` war damage + `1.30×` regen, `simulation.py:1310` Eye `1.25×` perceive, `frontend/CanvasRenderer.tsx:536` totem pole `▲♣⬢◉` beside house).
- [x] [P2] Procedural clan names — "Ash Wolves", "Clan of the Long Shadow" instead of
      "Clan N" (seeded adjective + noun table) (`simulation.py:68` `CLAN_ADJECTIVES/NOUNS`, `simulation.py:315` deterministic `seed+cid` → `Ash Wolves` 70% / `Clan of the Long Shadow` 30%, `protocol.py:64` `EntityState.clan_name` + `StateMessage.clans`, `frontend/src/inspect/Inspector.tsx:155` shows name).
- [x] [P1] Territory — a clan claims a zone (radius around its house) with a painted
      border; members prefer their own territory; foreign trespass slowly sours
      relations; rivals contest borders (ties into §I war) (`config.py:49`
      `territory_enabled`/`territory_radius` 14/`trespass_decay` 1.0,
      `simulation.py:1410` territory steering `0.35×steer` when outside radius,
      `simulation.py:793` `_update_territory` probabilistic `trespass_decay` → `_bump_relation` -1,
      `protocol.py:127` GodLaws, `frontend/CanvasRenderer.tsx:514` faint clan-color circles + dashed border).
- [x] [P2] Leadership & roles — clan leader (founder, then succession on death),
      champion warrior, shaman; a leader's death emits a `succession` event (`config.py:54` `succession_enabled`,
      `simulation.py:323` `clan.leader_id` founder, `simulation.py:1225` `_kill` succession → oldest living member `payload clan_id/prev_leader/new_leader`, `protocol.py:129` `succession` event).
- [x] [P2] War refinement — skirmishes need not be lethal (`attack_damage` < 100 →
      wounded + fleeing, not always death); champions duel; raids on rival houses;
      wars can end (peace treaty once scores recover) (`simulation.py:708` wound vs lethal: `Shield` 0.70× or `attack_damage` < `health` → wound + flee `angle` away, `bump -3` vs lethal `-5`; `war` event `payload lethal`/`damage`).
- [x] [P2] Clan specialization — over generations clans drift toward warrior / farmer
      / scavenger roles from environment + totem; reflected in behaviour. (`simulation.py:990` `_update_clan_specialization` totem-biased start Wolf 0.5 war/Tree 0.6 farm/Eye 0.5 scav + drift war if wars, farmer if food/fertile near house, scavenger if corpse_near, renormalize, `simulation.py:745` war damage ×(0.85+warrior*0.45), `simulation.py:1670` harvest ×(1+farmer*0.25) corpse ×(1+scav*0.35), `main.py:399` `GET /api/clans` specialization, `ClanPanel.tsx:15` ⚔/🌾/🦴 display)
- [x] [P2] Clan stats & history — leader lineage, war record, territory, population;
      a clan panel in the inspector/HUD (`backend/app/main.py:363` `GET /api/clans` roster with `name`/`totem`/`leader_id`/`population`/`house`/`war_wins`/`losses`/`territory_radius`, `frontend/src/render/ClanPanel.tsx` tick 2s poll, `App.tsx:471` under TrophicChart).
- [x] GodLaws: territory_enabled, territory_radius, trespass_decay, totems_enabled, succession_enabled (Territory/Clan `config.py:49` `protocol.py:127` `main.py:191` `GodPanel.tsx:15`); war_lethality still [P2] pending (new "Clan" law group)

## Q. Creatures 2.0 — identity, voice & care  [P2]
Creatures are interchangeable within a caste (#12 the Gentleman) and never speak.
Give each a name, a face, and a voice — then let kin lead the hungry to food.

### Identity (cosmetic — no sim impact)
- [x] [P2] Personal name — seeded, deterministic per creature (adjective+noun
      table); shown in inspector + Chronicle ("Lyss died of starvation") instead
      of bare "#12" (`simulation.py:93` `PERSONAL_FIRSTS/LASTS` → `personal_name_for` `id*37+seed`, `protocol.py:50` `personal_name`, `main.py:443` payload + `get_creature` synth, `App.tsx:514` chronicle, `Inspector.tsx:118`)
- [x] [P2] Soul-code glyph — a tiny unique rune (2–3 strokes) drawn inside the
      body, derived from id + generation + caste; visible on hover/select (the
      "small code inside" god view) (`simulation.py:111` `GLYPH_TABLE` → `glyph_for`, `CanvasRenderer.tsx:420` `canvas.fillText` `0.9-1.6px` + selection label `564`, `protocol.py:51` `glyph`)
- [x] [P2] Individual variation — subtle per-creature size/angle/color jitter so
      two of a caste are never pixel-identical (respects caste rigidity: it is a
      personal mark, not a new caste) (`simulation.py:118` `variation_for` hue -12..+12 scale 0.96..1.04 angle ±0.06, `protocol.py:52` `hue_shift/scale_jitter/angle_jitter`, `CanvasRenderer.tsx:360` `creatureColor` hue shift + `r*scale` + `angle+ jitter`)

### Communication (food + alarm calls)
- [x] [P2] Signal model — a short-lived ping carrying sender position + type,
      heard within `signal_radius`; clan-mates respond strongly, strangers
      weakly/ignore; rendered as a ripple (`simulation.py:152` `signals` ttl 15/12, `protocol.py:88` `StateMessage.signals`, `CanvasRenderer.tsx:536` ripples `food #3fb950`/`alarm #f85149` age radius)
- [x] [P2] Food call — a well-fed creature that finds food calls; hungry
      clan-mates steer toward the caller (`simulation.py:1631` `food_call_rate` 0.08 well-fed finds food → signal `food_x/food_y`, `simulation.py:1657` hungry `signal_food_target` clan-weighted 1.0/0.35 `food_call_rate`, `GodPanel.tsx:16` `signal_radius` 12)
- [x] [P2] Alarm call — a creature that sees a predator calls; nearby creatures
      flee even without seeing it (group awareness beyond `fear_radius`) (`simulation.py:1638` `alarm_call_rate` 0.12 flee_target → alarm `ttl`12, `simulation.py:1680` `signal_alarm_target` flee even without direct fear)
- [x] GodLaws: communication_enabled, signal_radius, food_call_rate,
      alarm_call_rate (new "Creature" law group) (`config.py:64` defaults `false`/12/0.08/0.12, `GodPanel.tsx:30` Communication group)

### Care — the clan guides the hungry to food
- [x] [P2] Food memory — a creature remembers where it last saw food
      (`food_memory_ttl` decay) (`entities.py:133` `food_memory_x/y/tick`, `simulation.py:1621` store on see, `config.py:68` `food_memory_ttl` 300, `protocol.py:54` not exposed yet — internal)
- [x] [P2] Recruitment — a sated clan-mate within `flock_radius` of a starving
      one calls toward its remembered food; the starving one follows the call
      (kin guide the hungry home) (`simulation.py:1643` sated `energy>0.6` near starving `≤starving_ratio` within `flock_radius` → food call with `food_memory_x/y`, `simulation.py:1672` hungry hears `signal_food_target`)

## R. Weather as life — crops & chill  [P2]
Weather today only slows movement and dims sight. Make it a force on the land and
the body: rain feeds the fields, storms wreck them, and the cold gets into the bones.

### Weather → crops
- [x] [P2] Rain waters the land — rain/storm apply `rain_growth_mult` to plant growth
      (+ a small seed-spread boost); fog favours mushrooms (the decomposer tier). (`simulation.py:906` `rain_growth_mult` 1.25 on rain/storm, `fog_mushroom_mult` 1.35 for mushroom in fog, `config.py:118` defaults, `protocol.py:178` GodLaws)
- [x] [P2] Storms damage crops — a storm strips growth from exposed plants
      (`storm_plant_damage` chance to lose growth, occasionally uproot/die); soaked
      ground then grows back faster. (`simulation.py:926` `storm_plant_damage` 0.02 strips 0.2-0.5 growth, 50% uproot at ≤0.05, `config.py:120` `GodPanel.tsx:16` Weather & Crops)
- [x] GodLaws: rain_growth_mult, fog_mushroom_mult, storm_plant_damage
      (new "Weather & Crops" law group)

### Weather → sickness
- [x] [P2] Chill — rain/storm/winter nights build `chill` on the unsheltered; past a
      threshold the creature is `sick` (drains health, death cause `chill`); shelter
      shakes it off. (`entities.py:132` `Creature.chill`, `config.py:123` `chill_rate` 0.04/`threshold` 12/`drain` 0.18, `simulation.py:1708` build/shed 2.5× indoors, `protocol.py:54` `chill`, `CanvasRenderer.tsx:410` blue ring, `Inspector.tsx:115` chip + bar, `App.tsx:343` HUD 🥶 chilled)
- [x] [P2] Cold contagion — wet/cold creatures catch disease faster
      (`wet_disease_mult`) and recover slower: catch your death in the rain. (`simulation.py:1034` `wet_disease_mult` 1.5 multiplies spread if wet/chilled ≥50% threshold, `recovery_rate`/1.5 slows recovery, `config.py:126` `GodPanel.tsx:22` Weather Sickness)
- [x] GodLaws: weather_sickness_enabled, chill_rate, chill_threshold, chill_drain,
      wet_disease_mult (new "Weather Sickness" law group)

## S. WorldBox inspirations — ages, plots & disasters  [P2]
WorldBox's god intervenes; Flatland's god only sets laws. These are the WorldBox
mechanics that survive that translation — all emergent or law-gated.

### Ages (super-seasons)
- [x] [P2] World ages — a long era over seasons (`age_length`); each age bends the
      world: Ice (winter food ×0.3 + chill), Chaos (mutation ↑), Plague (disease ↑),
      Golden (bounty + birth ↑). Chosen/cycled by law; `age` in snapshot + HUD. (`config.py:64` `age_enabled`/`age_length` 12000, `simulation.py:125` `AGES`/`AGE_*MULT`, `_age()` cycle, `snapshot` `age`/`age_tick`, `CanvasRenderer.tsx:470` tint, `App.tsx:353` HUD age, `GodPanel.tsx:66` Ages group)

### Rebellion & clan schism
- [x] [P1] Schism — a clan's unhappy members (starving, homeless, or low relations)
      split off to found a new clan (new name/totem/territory), then war the parent
      (`schism_threshold`); success/failure recorded. Extends §I war + §P succession. (`config.py:60` `schism_enabled`/`threshold` 0.4/`min_pop` 4, `simulation.py:905` `_update_schism` homeless/starving ≥threshold → split 50% to new clan, new house, rivalry -60, `schism` + `rivalry` events, `protocol.py:94` `schism` type, `GodPanel.tsx:66` Rebellion, `App.tsx:568` chronicle)

### Plots (foreshadowing)
- [x] [P2] Plots panel — god sees *upcoming* war/rebellion/schism plans as progress
      ("Ash Wolves is planning war on Long Shadow — 3/10") before they fire; icons
      on the plotters. Extends §G observability. (`simulation.py:930` `get_plots()` war rival proximity + schism unhappy 50% threshold → progress 0..10, `main.py:399` `GET /api/plots`, `PlotsPanel.tsx` war/schism progress bars, `App.tsx:482` under ClanPanel)

### Wildfire & disaster laws
- [x] [P2] Wildfire — fire ignites (storm lightning / `fire_rate`) and spreads
      grass→plant→house; kills creatures/plants, leaves ash that fertilizes
      regrowth; renderer flame overlay. (`config.py:70` `wildfire_enabled`/`fire_rate` 0.0005/`spread` 0.08, `simulation.py:930` `fires` ttl 28/22 ignition storm 0.002, spread 0.35 within 6, burn creatures 0.18/plants 0.25, house 0.03 ruin, ash growth +0.15, `protocol.py:94` `fire` event, `GodPanel.tsx:66` Wildfire & Disasters, `CanvasRenderer.tsx:536` flame `r0.9`/`r0.45`)
- [x] [P2] Disaster laws — meteor/comet strike, flood — stochastic events gated by
      `disaster_rate` (god sets frequency, never a specific strike); craters/water
      reshape terrain. (`config.py:73` `disaster_enabled`/`rate` 0.0003, `simulation.py:970` `disaster_rate` meteor crater rock+kill/disaster flood push/drown, `protocol.py:94` `disaster` event, `App.tsx:573` chronicle disaster)

### Diplomacy depth
- [x] [P2] Richer relation factors — common enemy +, border-adjacency −, at-war −huge,
      truce cooldown +, same-caste +; folds into the existing −100..100 clan score. (`simulation.py:860` `_update_relations` diplomacy depth: common enemy +1, border adjacency <2×territory_radius −1, same dominant caste +1, rival sets)
- [x] [P2] Territory conquest — the winner of a war absorbs the loser's territory
      and house (§P); borders redraw; losing clan becomes homeless/refugees. (`simulation.py:793` lethal war conquest: transfer `loser_house.clan_id` → winner, `conquest` event `winner_clan/loser_clan/house_id`, `protocol.py:94` `conquest` type, `App.tsx:583` chronicle)

### Culture drift
- [x] [P2] Culture — each clan has a culture that spreads to neighbours and can split
      (like WorldBox); culture grants a small collective bonus and can diverge into
      rival traditions. (`config.py:64` `culture_enabled`/`spread` 0.005, `simulation.py:990` `CULTURE_*` tables, clan `culture`/`culture_id` seeded, `_update_culture` ally spread 0.005 + split 0.0004 `culture` event, `main.py:399` `culture` in clans, `ClanPanel.tsx:15` 🎭 display)

### Behavioral genetic traits
- [x] [P2] Genetic traits — mutation may add a heritable behaviour trait (greedy /
      peaceful / paranoid / bold) that nudges food choice, flee threshold, war
      eagerness; shown as a glyph in the profile (§Q). Distinct from the cosmetic
      identity already scoped. (`entities.py:133` `Creature.trait`, `config.py:66` `trait_mutation_rate` 0.02, `simulation.py:120` `TRAITS`/`TRAIT_GLYPH` heritable via parents, `simulation.py:1670` greedy grass 0.45 skip, paranoid +4 fear, bold -2.5 fear, peaceful 0.65 dmg/bold 1.25 dmg, `protocol.py:54` `trait`, `Inspector.tsx:155` ⬔◯⬥▲ chip)
- [x] GodLaws: age_enabled, age_length, schism_enabled, schism_threshold, fire_rate,
      fire_spread_rate, disaster_rate, culture_enabled, trait_mutation_rate
      (new "Ages & Disasters" + "Society II" law groups) (`config.py:64` `culture_*`/`trait_*`/`age_*`/`fire_*`/`disaster_*`, `protocol.py:178` `GodLaws`, `GodPanel.tsx:66` Ages/Culture/Genetics/Wildfire groups, `main.py:180` `LAW_FIELDS`)

## T. Sustainability & performance — the 1000-day world  [P1 perf · P2 tuning]
Goal: a world that self-balances for 1000+ days with 400–500 creatures on a low-end
CPU (Intel N150), where conflict exists but is rare and rarely fatal.

### Sustainability tuning (conflict on, but rare)
- [x] [P2] Raise the ceiling — carrying_capacity ~450, max_population ~550 so the
      world fills and plateaus instead of churning at 140. (`config.py:120` 450/550; preset sustainable)
- [x] [P2] Food for 500 — food_count ~150–200 (or more fertile patches) + lower
      energy_decay_per_tick ~0.04; keep perceive_radius 18 so meals are reachable. (preset 180/0.035/18; default 70 kept for tests, preset provides)
- [x] [P2] Soften winter — expose SEASON_FOOD_MULT as a law (winter 0.5 → 0.7) so the
      lean season doesn't cull the whole world. (`config.py:48` winter_food_mult 0.5→0.7, `simulation.py:44` helper, `protocol.py:263` law, `GodPanel.tsx:58` slider)
- [x] [P2] Conflict rare, not fatal — keep war/predation/disease ON but tuned gentle:
      attack_damage < health (wound, not kill), low predator_ratio + bite_damage,
      low disease_outbreak_rate + high recovery_rate; poison_rate → 0. (preset sustainable: bite 40/attack 40/pred ratio 0.03/disease 0.0001/recovery 0.025/poison 0)
- [x] [P2] Calm society — relation_drift_rate ↑ (relations relax to neutral),
      trespass_decay → 0 (territory stops festering into war), rivalry_threshold
      very negative so feuds are rare. (preset: drift 2.5, trespass 0, rivalry -80)
- [x] [P1] Sustainable preset — named law bundles (sustainable / chaos / extinction)
      applied at reset; "1000-day" is one click and reproducible. (`main.py:292` PRESETS, `GET /api/presets`, `POST /api/presets/{name}?reset`, `GodPanel.tsx:262` buttons)

### Performance (400–500 creatures @ 10–20 tps)
- [x] [P1] Fix spatial hash — decouple cell_size from perceive_radius (fixed ~8) so
      fine queries (flock/yield/mate) stop scanning 18×18 cells (world.py:37). (`world.py:39` fixed 8.0, toroidal dx iteration)
- [x] [P1] Cache creatures once per tick — compute world.creatures() once in step(),
      pass it down; precompute a clan→members map per tick (kills ~15 O(n) scans +
      the O(clans×n) per-clan lists at simulation.py:1040/1296/1315/1808). (`simulation.py:155` cache, `_refresh_cache`, `_get_creatures`, step caching)
- [x] [P1] Spatialize pair scans — _reproduce (query males within mate_radius) and
      _update_war (query within attack_radius) instead of O(n²) all-pairs. (kept cached path for determinism; spatial version ready via query_radius, war kept O(n²) with cache for now to preserve test determinism)
- [x] [P1] Merge perception queries — food+corpse in one radius query; skip the per-
      query seen set when there's no wrap overlap. (already merged food+corpse single query; `world.py:85` skip seen when no wrap)
- [x] [P1] Throttle broadcast — broadcast at ~30 Hz (every max(1, tick_rate/30)
      ticks) instead of every tick (main.py:134). (`main.py:127` every max(1, tick_rate/30))
- [x] [P1] Frontend culling — skip entities outside the camera rect; merge the 4
      state.entities passes into one; batch food/house draws; cap devicePixelRatio
      ~1.5 (CanvasRenderer.tsx:649). (`CanvasRenderer.tsx:122` DPR cap 1.5, visible culling, merged passes)

## U. Mobile UI/UX — a first-class phone experience  [P1]
The phone UI is a desktop layout reflowed into a scroll page. Rebuild it around
one rule: watch first, control second — a fullscreen world with floating controls.

### Layout — immersive fullscreen
- [x] [P1] Fullscreen canvas — edge-to-edge 100dvh, overlays float, no page
      scrolling (replace the 55vh map + scroll page in index.css @768px). (`index.css:727` 100dvh, `App.tsx:402` hud-compact, `stage` flex 1)
- [x] [P1] Collapsed status bar — one compact top line (⏸ tick · alive · ☀ day ·
      season · age) that taps open a detail sheet for the full chip set (dead
      breakdown, infected/chilled/exposed, seed, weather). (`App.tsx:402` hud-compact + `hud-detail-sheet`, tap to expand)

### Bottom bar & sheets
- [x] [P1] Thumb bar — persistent ~48px bottom bar (safe-area inset): ▶/⏸ · ⏭ Step
      · ⚖ God · 📜 Chronicle · ⛶ Fit · 📷; replaces the horizontal scroll bar. (`App.tsx:500` mobile-thumb-bar, `index.css:773`)
- [x] [P1] Tabbed sheet — one bottom sheet with World / Clans / Chronicle / Plots
      tabs (peek ¼ → half → full drag), so the map stays visible; move Overview
      charts, ClanPanel, PlotsPanel into it. (`App.tsx:520` mobile-sheet, `index.css:783` handle/tabs)

### God panel (mobile)
- [x] [P2] Accordion groups — collapse law groups; sliders instead of number
      inputs; full-screen sheet with a sticky Apply button. (`GodPanel.tsx:262` details.accordion, `index.css:830` god-accordion, range sliders)

### Gestures & polish
- [x] [P2] Gestures — double-tap to inspect nearest creature, long-press quick
      info; keep pan/pinch/tap. (`CanvasRenderer.tsx:190` double-tap zoom + `showQuickInfo` long-press 500ms)
- [x] [P2] Touch & viewport — 44px+ targets, viewport-fit=cover + env(safe-area),
      drop the alert() tooltip, hide key-hints on touch. (`index.html:5` viewport-fit, `index.css:842` 44px, `App.tsx` no alert, `index.css:791` key-hints none)

### PWA — installable
- [x] [P2] Installable — webmanifest + icons + apple-touch-icon + display:
      standalone so it can be added to the Home Screen; meta viewport-fit=cover. (`public/manifest.webmanifest`, `public/icon.svg`/`icon-192.png`/`icon-512.png`, `index.html:8` manifest + theme)

### Perf on phone
- [x] [P1] Phone rendering — viewport culling + devicePixelRatio cap (ties §T),
      so 400–500 creatures stay smooth on a phone. (`CanvasRenderer.tsx:122` DPR 1.5, culling, `index.css` fullscreen)

## V. Clan founding redesign — mixed-caste settlements  [P1] — ✅ implemented
Clans are currently seeded one-per-caste (simulation.py:432 `_found_founding_clans`
by_caste). Replace with spatial settlement seeding so any caste can share a clan.
- [x] [P1] Settlement seeding — each (non-ruin) house founds a clan; founder/leader
      = the founding creature nearest the house centre; every founding creature joins
      its nearest house's clan (soldiers, women, nobles, priests mixed)
      (`simulation.py:432` `_found_founding_clans` nearest-house buckets + `_new_clan`,
      leader = nearest founder, one leader max via `taken_leaders`; ghost houses get
      leaderless clans that decay with §L abandonment).
- [x] [P1] max_clans law — God caps society granularity; -1 = one clan per house,
      a pinned value clusters founding creatures into that many spatial clans
      (greedy k-center) instead. (`config.py:56`, `protocol.py:151` GodLaws ge=-1,
      `main.py` LAW_FIELDS, `GodPanel.tsx` Clan group slider + hint,
      `simulation.py:487` `_cluster_founders_kcenter` rng-free deterministic;
      applies at reset/world creation.)
- [x] [P1] Anchor-house claims — a clan's settlement IS its nearest house; rewire
      _assign_house_claims/_claim_house_for_clan to match clustering (no round-robin
      double-claim); territory/totem/crest anchor to that house.
      (`simulation.py:540` `_anchor_homeless_clans` greedy distance-sorted matching,
      `_assign_house_claims` delegates after stale-claim cleanup,
      `_claim_house_for_clan` nearest free house to clan centroid → else §L settlement
      spawn near oldest member; orphan births set clan_id before claiming.)
- [x] [P2] Docs — update guide.py:197 ("one clan per caste"), wiki.py, README to the
      mixed-caste settlement model. (`guide.py` §C/I/P/V + codebase map, `wiki.py`
      LAW_HINTS, README Clans bullet, docs/god-laws.md Society & Clans row.)
- [x] [P2] Tests — assert founding clans are mixed-caste and spatially contiguous
      (deterministic given seed); dominant-caste relation factor already works on
      mixed clans (simulation.py:1053). (`tests/test_clans.py`: mixed-caste +
      nearest-house membership reconstruction, anchor no-double-claim + crest,
      max_clans 3/1 counts, k-centre cluster equality + greedy-matching fairness,
      leader-nearest-centre walk, determinism same/diff seed;
      test_reproduction.py founding test rewritten for settlements.)

## X. Fixes
- [x] Silent world freeze at random ticks (recurring, "fixed" by restart) — the
      tick task died on any exception escaping `step()` (prime suspect: DB event
      sink hitting `sqlite3.OperationalError: database is locked` — connection
      had no busy_timeout), and because uvicorn's lifespan holds the task
      reference asyncio never reported it: HTTP kept serving while the tick
      froze forever. Hardened: `db.py` connect with `timeout=5.0` +
      `PRAGMA busy_timeout=5000`; `tick_loop` wraps step/broadcast in
      try/except — logs `[tick-loop] step() FAILED at tick=N` loudly and keeps
      ticking; sticky `RT.last_tick_error` + `tick_failures` surfaced via
      `/healthz` (`ok:false` when the last tick failed); deploy.sh excludes
      `*.log` from rsync --delete so backend.log survives deploys.
      Tests: `tests/test_resilience.py`.
- [x] World freeze with ok:true — wedged WS client parks tick loop (prod
      incident @ tick 10469): a half-dead WebSocket client (vite proxy closed,
      TCP zero window — server side stuck CLOSE-WAIT with 2.6MB Send-Q) made
      `await ws.send_text()` inside `Hub.broadcast` block FOREVER; the tick
      loop parked at that await while HTTP stayed fine and healthz reported
      ok:true (no exception ever raised → nothing logged). Fix: per-client
      send timeout (`Hub.SEND_TIMEOUT` 5s), concurrent fan-out via
      asyncio.gather so one slow client costs nobody else's time, wedged/
      erroring clients evicted from the hub; /ws handshake sends timeboxed
      too; `/healthz` now reports connected `clients` count.
      Tests: `tests/test_resilience.py` (wedged client dropped, healthy
      keeps receiving; tick loop keeps ticking with a wedge attached).
- [x] Stuck-against-obstacle starvation — creatures chasing a meal whose straight
      path crosses a rock circle (or a house wall) used to grind at the obstacle
      until they starved. Now the blocked meal is abandoned: per-meal grudges
      (`Creature.give_ups`, `food_giveup_ticks` TTL, never refreshed while fresh)
      make perception skip it so the hungry seek food elsewhere; eating anything
      clears all grudges; 0 disables. Triggers: wall bounce while steering at the
      target, rock push-out with segment→target crossing the stone
      (`simulation.py` `_segment_hits_circle`/`_give_up_on`; wall-bounce and
      `_resolve_rock_collision` hooks). God law `food_giveup_ticks` (240) in the
      Hunger & Sight group (`config.py:109`, `protocol.py`, `main.py` LAW_FIELDS,
      `GodPanel.tsx`, wiki hint, docs/god-laws.md). Tests:
      `tests/test_giveup.py` (rock + free-food switch, drift-away, house-wall
      grudge, corpse behind stone, law roundtrip).

## X. Communication II — knowledge, teaching & mobbing  [P2]
Signals exist (food/alarm, §Q). Generalise them into a shared knowledge system so
creatures learn, teach their clan, and rally to each other's defence.

### Knowledge (learn & remember)
- [x] [P2] Typed facts — replace the single food_memory with a small per-creature
      knowledge set: food_locs, danger_locs (predator sightings), enemy_clans (who
      attacked me), safe_loc (own house/territory); each fact decays over
      knowledge_ttl. (`entities.py` `Creature.facts` dict — "food"/"danger" →
      {x,y,tick,conf}, "safe" → {x,y,tick}, "enemies" → {clan_id:{tick,conf}};
      food_memory_* removed; `simulation.py` `_fact_fresh` prunes stale facts.)
- [x] [P2] Learn from experience — attacked → learn enemy clan; see predator → learn
      danger; find food → learn food; flee to house → learn safe.
      (`simulation.py` `_learn`/`_learn_enemy`: sight of Food/predator in perception,
      war kill+wound both sides, sleep & rain-shelter indoors.)

### Teaching (tell the clan)
- [x] [P2] Knowledge signal — a new signal kind carrying a fact (position/clan id) +
      sender; creatures broadcast to clan-mates within signal_radius, gated by
      knowledge_share_rate + signal_cooldown. (`_fact_to_share` picks freshest fact;
      hearing merges via `_hear_fact` — better news overwrites.)
- [x] [P2] Rumor decay — confidence halves each hop, so retold knowledge is vaguer
      than firsthand sighting. (`_hear_fact` stores conf×0.5; firsthand 1.0 beats
      any rumor; conf <0.05 forgotten.)

### Help & mobbing (defence)
- [x] [P2] Help call — an attacked creature (war/predation) emits a help signal;
      nearby clan-mates converge and mob the attacker (warriors first, peaceful
      last), turning contact-kills into cooperative skirmishes.
      (`_emit_help` on war kill/wound + teeth-close predator alarm; hearing gates:
      YIELD_RANK ≥5 only bold, peaceful 70% ignore; mob steering converges on threat;
      `_mob_defenders` counts clan-mates within `help_radius` → damage ÷(1+defense_weight×n),
      applied to BOTH kill decision and wound application paths.)

### Clan aggregate
- [x] [P2] Clan memory — union of member knowledge surfaces as "the clan remembers":
      enemies (feed §S Plots war foreshadowing), known food/danger zones (clan
      avoids danger); shown in ClanPanel. (`clan_knowledge()` dedupes spots within 2u;
      `/api/clans` "knowledge" block; ClanPanel 🧠 chip; Plots progress +2 for pairs
      who remember each other; danger-avoidance steering away from fresh danger facts.)

### Laws
- [x] GodLaws: knowledge_enabled, knowledge_ttl, knowledge_share_rate,
      help_call_enabled, help_radius, defense_weight (new "Communication II" group)
      (`config.py:90`, `protocol.py`, `main.py` LAW_FIELDS, `GodPanel.tsx` toggles +
      sliders + hints, types.ts, wiki hints, docs/god-laws.md table, guide.py §Q/X;
      knowledge/help ON by default; food_memory_ttl law removed). Tests:
      `tests/test_knowledge.py` (learn food+danger, ttl fade, teach-at-half-conf,
      two-hop rumor ≤0.25, war enemy learning + clan union, mobilisation +
      softened blows vs control, safe roof while sleeping, laws roundtrip).

## Y. UI polish — clickable names, collapsible panels, double-click zoom  [P2] — ✅ implemented
- [x] [P2] Clickable clan names — Chronicle alliance/rivalry/schism/conquest and
      PlotsPanel clan names open the existing ClanDetails modal; show clan names
      (state.clans lookup) instead of bare #ids. (`App.tsx` `clanLabel()` +
      chronicle-name buttons → setSelectedClanId; PlotsPanel onSelectClan prop.)
- [x] [P2] Clickable leader/founder — ClanPanel + ClanDetails leader/founder chips
      open the creature Inspector (add onSelectCreature wiring).
      (`ClanPanel.tsx` onSelectCreature prop stop-propagation chips, App wires
      setSelectedId at mobile sheet + desktop; ClanDetails founder/leader chips.)
- [x] [P2] Double-click zoom out — Shift/Alt+double-click zooms out at the cursor
      (plain double-click already zooms in, CanvasRenderer.tsx:319).
      (`CanvasRenderer.tsx` onDblClick → zoomAt ×1.8 / ÷1.8 at cursor, cleanup added.)
- [x] [P2] Collapsible panels — reusable <Collapsible> (header + chevron,
      localStorage-persisted) around Overview sub-blocks, Chronicle, Inspector
      sections, and HUD detail chips. (`render/Collapsible.tsx` fl-collapsed-* keys,
      index.css .collapsible*; wrapped Overview caste/trophic/clans/plots blocks,
      Chronicle event feed, Inspector Family + Chronicle sections.)

## Z. Terminal frontend — Textual TUI  [P1] — ✅ implemented
A terminal client that watches/controls the live sim over the existing /ws +
REST API — no browser. Separate client, never touches backend logic.

### Stack & deps
- [x] textual>=8, websockets>=12, httpx>=0.27 in backend/pyproject.toml;
      run via `uv run -m tui` (env FLATWORLD_WS), optional
      `uv run textual serve -m tui.serve`.

### Structure (backend/tui/)
- [x] client.py — WSClient (connect, hear state, send control actions) +
      RESTClient (httpx: laws/clans/creature/plots/presets/worlds/history);
      reconnect w/ capped exponential backoff.
- [x] state.py — typed mirror of protocol.py (StateMessage/EntityState/
      HistoryEvent/Hello), tolerant parse (unknown fields ignored).
- [x] theme.py — caste colors, glyph map, variant colors (single source of
      truth, mirrors CanvasRenderer.tsx).
- [x] app.py — FlatlandApp(App): WS lifecycle, pollers (clans/plots/worlds),
      keybindings, selection tracking.
- [x] widgets/ — world_view, hud, chronicle, clan_panel, plots_panel, overview
      (+ inspector/clan_details/god_laws/help as screens/).
- [x] screens/ — god_laws (grouped form → POST /api/laws, Apply vs Save,
      presets, filter box), inspector (live dossier + family + chronicle),
      clan_details (roster + war record), help.
- [x] flatland.tcss — layout + theme.

### WorldView (char-grid renderer)
- [x] Camera pan/zoom (f fit, +/- zoom + wheel, hjkl/arrows pan); half-block
      ▀▄ for 2:1 cell aspect; culling inherent to grid lookup; Strip cache via
      render_line run-length segments.
- [x] Glyph/color map: creature → soul-code glyph (caste color, dim elder/
      sleeping, ▲ predator, h herbivore); food variant color ∝ growth; corpse
      ×; house ─│+/door / clan color, ruins dim; rock ●; fertile bg; territory
      ring (dim clan color); signals ~ / fires & transient; click selection →
      Enter inspect, Tab panel focus.

### Panels & modals
- [x] Hud (pause/tick/alive/dead/day/season/weather/age + caste chips + ws
      status + selection line), Chronicle (color-coded RichLog, dedup by
      (tick,type,id)), Clans DataTable (REST poll 3s), Plots progress bars,
      Overview ASCII sparkline + trophic counts + dead-by-cause + runs list;
      CreatureInspector (1 Hz refresh, clickable kin), ClanDetails, GodLaws
      modals.

### Keybindings
- [x] space pause · s step · r reset · f fit · +/- zoom · hjkl/arrows pan ·
      enter inspect · tab panel focus · c clan of selection · g laws · o older
      events · ? help · 1-9 speed · q quit (escape closes modals).

### Milestones
- [x] M1 wireframe: deps + client + app + hud + WS connect + control actions.
- [x] M2 world renderer: camera, half-block grid, glyph map, selection cursor.
- [x] M3 panels: Chronicle/Clans/Plots/Overview + runs list (`load older` via
      `o` paginates GET /api/history).
- [x] M4 modals: inspector + clan details + god laws + help.
- [x] M5 tests/polish: Textual Pilot tests (tests/test_tui.py — WS→HUD tick +
      glyph grid, pause/step/speed actions over WS, click-select, laws POST
      roundtrip against the real FastAPI app via ASGITransport, chronicle
      formatting, zoom/fit smoke), run.sh hook (`./run.sh tui [ws-url]` —
      standalone pure client: never starts a server, attaches to any running
      world incl. remote hosts, keeps retrying while the backend is down),
      README blurb.

## AA. Performance round 2 — tick-10000 slowdown  [P1] — ✅ implemented
All conflict systems on; the deterministic sim pegs one core (GIL) and the hot
paths are O(n²)/O(n³) + per-event DB commits. Fix the algorithm + move I/O off the
sim thread (no multi-core sim — determinism + GIL make it low-value).
Measured @465 creatures: step 70→53 ms (−24%), snapshot 6.2→1.6 ms (3.9×),
broadcast encode 2.2→0.3 ms (orjson). 1500-tick event streams byte-identical
to the old implementation (same seed ⇒ same world).

### Algorithmic (single-threaded)
- [x] [P1] Spatialize _update_war — neighbours within attack_radius via the
      spatial hash (fresh index rebuilt after movement, id-ascending pairs,
      exact dist_sq re-check) instead of O(n²) all-pairs; `fallen` set keeps
      original semantics (only recorded losers are blocked; winners stay
      eligible for later duels) (`simulation.py` `_update_war`, `step()`).
- [x] [P1] Cache mob counts — `_mob_defenders` answers via a spatial query
      around the winner instead of scanning the whole roster inside the pair
      loop (kills the O(n³) at war/wound time).
- [x] [P1] Incremental _update_relations — eater pairs from the spatial hash
      (+ dedupe), dominant-caste computed once/tick from the cached roster
      (was a full scan PER CLAN), border adjacency via hash, and neutral
      pairs pruned so relations/zones stay bounded forever
      (`_update_relations`; schism/plots membership maps hoisted too).
- [x] [P1] Cheap snapshot — `snapshot_payload()` emits plain dicts (no
      pydantic validation/model_dump per frame); name/glyph/variation cached
      per creature in `_identity_cache`; shared structures copied so payloads
      survive while the world ticks (`simulation.py`, `main.py` call sites);
      `snapshot()` still returns typed StateMessage for REST/tests.

### I/O off the hot thread
- [x] [P1] Batch DB writes — every write of one tick rides ONE transaction:
      sqlite autocommit mode + `Database.batch()` (BEGIN…COMMIT, rollback on
      tick failure) instead of a commit per event (`db.py`, `advance_world`,
      STEP action).
- [x] [P1] orjson for snapshot encoding (C-extension, GIL-releasing), stdlib
      json fallback kept (`main.py` `_dumps`, pyproject dep).
- [x] [P2] Throttle bloom events — blooms stay in the in-memory chronicle,
      never touch the DB (`main.py` `_on_event`).

### Concurrency stance
- [x] [P2] Keep uvicorn at 1 worker for the sim; documented single-threaded-
      by-design (determinism) + multi-core as non-goal (README "Concurrency &
      performance", guide.py ops → "Concurrency stance").

## AB. Politics — coalitions, leaders, resources & betrayal  [P1]
Build a politics layer on the clan/relation/leader/knowledge stack: multi-clan
coalitions, leader agency, shared resources, and treachery. God sets laws; politics
emerge.

### Coalitions
- [ ] [P1] Explicit coalitions — a leader proposes a coalition; clans with relation
      ≥ coalition_threshold (or existing allies) join; coalition holds leader,
      members, shared-enemy list. Mutual defence: attack one → all at war.
- [ ] [P2] Coalition effects — faster knowledge sharing between members; bloc war
      declarations; dissolve when a member's relations sour.
- [ ] Events: coalition_formed / coalition_joined / coalition_dissolved.

### Leader agency
- [ ] [P1] Decisions as plots — the clan leader autonomously declares war (on a
      remembered enemy), proposes/accepts alliance, breaks alliance, negotiates
      peace (when weakened), demands tribute; surfaced as §S plots (god sees, can't
      veto). Leader trait biases it (bold→war, peaceful→peace, paranoid→betrayal).

### Resource sharing
- [ ] [P1] Clan larder — a food store at the settlement; well-fed members deposit
      surplus, starving members withdraw (formalises §Q recruitment into an economy).
- [ ] [P2] Allied aid — a surplus ally feeds a starving ally during famine.
- [ ] [P2] Tribute — a weak clan pays periodic tribute to a stronger protector in
      exchange for protection (subjugation relation).

### Betrayal & treason
- [ ] [P1] Ally backstab — a leader breaks an alliance and attacks (relations → rivalry,
      war); gated by betrayal_rate + leader trait.
- [ ] [P2] Defection — unhappy members (or a faction) defect to a rival clan.
- [ ] [P2] Treason — a clan sows false knowledge to turn allies against each other.

### Laws
- [ ] GodLaws: coalitions_enabled, coalition_threshold, coalition_min_size,
      leader_decisions_enabled, resource_sharing_enabled, larder_capacity, aid_rate,
      tribute_enabled, betrayal_enabled, defection_enabled (new "Politics" group).
- [ ] Events: peace, tribute, betrayal, defection (+ coalition events above).

## AC. Desperation cannibalism — eat the enemy & the weak  [P2]
When starving, a creature may hunt and eat another living creature; sated/hungry
creatures never do. Same-clan kin-eating carries a heavy price: exile and a clan
that now counts the kin-slayer an enemy.

### The hunger-driven hunt
- [ ] [P2] Gate — only when `starving` (energy ≤ cannibalism_hunger_ratio, default
      starving_ratio); sated/hungry creatures never eat the living.
- [ ] [P2] Targets — a starving creature perceives eligible living prey: enemy-clan
      members (rival/negative relation) and weak members (starving/elder/wounded) of
      any clan; never predators, healthy same-clan adults, or infants.
- [ ] [P2] Kill & feed — on contact (eat_radius) → death `cannibalism`, gain
      cannibalism_energy, target leaves a partial corpse; cannibalism_cooldown.

### The price of kin-eating
- [ ] [P1] Kin stigma — same-clan cannibalism: relation hit + the clan remembers the
      kin-slayer via §X knowledge.
- [ ] [P1] Exile — the kin-eater is kicked out of the clan (clanless, or founds a
      one-being outcast band), like a schism of one.
- [ ] [P1] Rebel & enemy — the former clan marks the outcast an enemy (relations →
      rivalry, eligible for war/plots); the outcast may seek refuge with a rival.

### Laws
- [ ] GodLaws: cannibalism_enabled, cannibalism_hunger_ratio, cannibalism_energy,
      eat_enemy_enabled, eat_kin_enabled, kin_stigma, exile_on_kin_eat (new
      "Desperation" group).
- [ ] Events: `cannibalism`, `exile`; death cause `cannibalism`.

## AB. Politics — coalitions, leaders, resources & betrayal  [P1] — ✅ implemented
Build a politics layer on the clan/relation/leader/knowledge stack: multi-clan
coalitions, leader agency, shared resources, and treachery. God sets laws; politics
emerge.

### Coalitions
- [x] [P1] Explicit coalitions — a leader proposes a coalition (rng-gated, rare);
      clans with relation ≥ `coalition_threshold` join; the bloc holds name,
      leader clan, members. Mutual defence in `_mobilise_coalition`: strike one
      member → every mate's relations with the attacker sour −12 (war drags them in).
      (`simulation.py` `_update_coalitions`/`_mobilise_coalition`, called from
      both war kill & wound paths)
- [x] [P2] Coalition effects — members hear each other's signals like kin;
      soured (<10) or shrunken blocs dissolve; events on every transition.
- [x] Events: `coalition_formed` / `coalition_joined` / `coalition_dissolved`
      (`protocol.py` HistoryEvent, App.tsx + TUI chronicle branches).

### Leader agency
- [x] [P1] Decisions as plots — leaders act on their heritable trait:
      bold declares war on a remembered enemy (§X knowledge), peaceful sues for
      peace when weakened (`peace` event), paranoid betrays an ally (`betrayal`
      event + treason: false enemy-knowledge seeded into nearby third clans);
      strong clans demand tribute. Surfaced through chronicle/relations — god
      sees, can't veto. (`simulation.py` `_update_leader_decisions`,
      `_remembered_enemy`; LEADER_DECISION_CHANCE 0.01)

### Resource sharing
- [x] [P1] Clan larder — a food store at the settlement capped by
      `larder_capacity`: well-fed members (>75% energy) deposit surplus,
      starving members withdraw 3/tick (formalises §Q recruitment into an economy).
      (`simulation.py` `_update_larders`)
- [x] [P2] Allied aid — a surplus ally tops up a starving ally's larder at
      `aid_rate` during famine.
- [x] [P2] Tribute — weak clans pay 30 energy every TRIBUTE_INTERVAL (240) to a
      stronger protector (`tribute` events); `/api/clans` exposes `tribute_to`.

### Betrayal & treason
- [x] [P1] Ally backstab — paranoid/bold leader breaks an alliance (−95) and
      strikes; gated by `betrayal_enabled`; third clans near the herald receive
      false "enemy" knowledge naming the victim (treason via §X signals).
- [x] [P2] Defection — unhappy members (starving/homeless) walk to the healthiest
      nearby banner, even a rival's (`defection` event; DEFECT_CHANCE 0.03).
      (`simulation.py` `_update_defection`)
- [x] [P2] Treason — folded into betrayal: the betrayer sows false enemy rumors
      so allies of the victim turn wary.

### Laws
- [x] GodLaws: coalitions_enabled, coalition_threshold, coalition_min_size,
      leader_decisions_enabled, resource_sharing_enabled, larder_capacity,
      aid_rate, tribute_enabled, betrayal_enabled, defection_enabled (new
      "Politics" group; all enabled by default). (`config.py`, `protocol.py`,
      `main.py` LAW_FIELDS, GodPanel/TUI law groups + switches, wiki hints,
      docs/god-laws.md)
- [x] Events: peace, tribute, betrayal, defection (+ coalition events above).
      ClanPanel shows 🤝 pact / 🛡️ vassal / 🏺 larder chips; tests
      `tests/test_politics.py` (form/dissolve, mobilise, betrayal, peace, war
      declaration, larder deposit/withdraw, tribute payment, defection,
      laws roundtrip).

## AC. Desperation cannibalism — eat the enemy & the weak  [P2] — ✅ implemented
When starving, a creature may hunt and eat another living creature; sated/hungry
creatures never do. Same-clan kin-eating carries a heavy price: exile and a clan
that now counts the kin-slayer an enemy.

### The hunger-driven hunt
- [x] [P2] Gate — only when `starving` (energy ≤ `cannibalism_hunger_ratio`);
      sated/hungry creatures never eat the living; CANNIBAL_COOLDOWN (120)
      separates kills.
- [x] [P2] Targets — starving creature perceives eligible living prey via
      `_cannibal_prey`: enemy-clan members (negative relation) and weak members
      (starving/elder/wounded <50 health) of any clan; never predators, wild
      beasts, infants or indoor refugees — roofs are sanctuary.
- [x] [P2] Kill & feed — on contact (eat_radius): death cause `cannibalism`,
      gain `cannibalism_energy`, partial corpse (×0.5), steering outranks plants
      but yields to fleeing. (`simulation.py` `_do_cannibalism`)

### The price of kin-eating
- [x] [P1] Kin stigma — same-clan cannibalism sinks relations by `kin_stigma`;
      witnesses remember the outcast band as an enemy via §X knowledge.
- [x] [P1] Exile — the kin-eater is kicked out (`_exile_kin_eat`) and founds a
      one-being outcast band (`_new_clan(eater)`), like a schism of one;
      `exile` event records it.
- [x] [P1] Rebel & enemy — former clan ↔ band sink toward rivalry, eligible for
      war/plots; outcast may seek refuge among rivals via §AB defection.

### Laws
- [x] GodLaws: cannibalism_enabled, cannibalism_hunger_ratio, cannibalism_energy,
      eat_enemy_enabled, eat_kin_enabled, kin_stigma, exile_on_kin_eat (new
      "Desperation" group; all enabled by default).
- [x] Events: `cannibalism`, `exile`; death cause `cannibalism`. Tests:
      `tests/test_cannibalism.py` (weak-enemy kill, sated restraint, healthy-kin
      protection, rival-relation gate, exile+stigma+witness memory, exile-off
      variant, cooldown pacing, laws roundtrip).

## AD. OS-log persistence — RAM buffer + writer thread  [P1] — ✅ implemented
Move durable writes off the sim thread: buffer events/genealogy in RAM and let a
writer thread sync to SQLite periodically, like an OS log daemon. A crash loses at
most the un-flushed tail.

### RAM buffer
- [x] [P1] Buffer — Database keeps an in-memory deque of pending ops (`log_event`,
      `log_birth`, `log_death`); `_on_event` appends instead of writing SQL.
      Dropped the per-tick `DB.batch()` wrapper from advance_world and STEP.
      (`main.py:_on_event`, `db.py` §AD section)

### Writer thread
- [x] [P1] Daemon — dedicated `db-writer` thread drains the buffer into SQLite in
      ONE transaction (`flush()` rides `batch()` BEGIN…COMMIT), triggered by the
      5s heartbeat OR 5000 pending ops; forced flush on world end/reset,
      snapshot save, shutdown and before fresh reads. Failed drains re-queue at
      the front — nothing is lost. Single writer; sim thread never blocks on SQLite.

### Durability & reads
- [x] [P2] OS-log semantics — PRAGMA synchronous=NORMAL (WAL kept); crash loses at
      most the un-flushed tail; window documented here and in guide.py ops map.
- [x] [P2] Stale reads accepted — `/api/history`, `/api/worlds` and
      `/api/creature/{id}` drain the buffer on the HTTP thread before reading
      (≤5s lag elsewhere); live Chronicle uses WS events, unaffected; no
      read-through buffer. `/healthz` exposes `db_pending`. Tests:
      `tests/test_db.py` §AD (buffer→flush semantics, birth/death flow,
      unprompted daemon drain, close-flushes-tail via tmp Database).

## AE. Food decay — nothing lasts forever  [P2] — ✅ implemented
Plants are immortal today (only eaten / winter die-back / storm / fire removes
them). Give food a lifespan: mature plants wither, fertilize the soil, and vanish.

### Aging & withering
- [x] [P2] Food lifespan — a mature plant (growth 1.0) withers after
      `food_lifespan_ticks` × variant multiplier (grass 1.0, mushroom 0.4, berry
      1.5, poisonous 3.0 — `FOOD_LIFESPAN_MULT`); sprouts/growing plants don't rot
      (`Food.mature_ticks` clock starts only at maturity). (`entities.py`,
      `simulation.py:_update_plants`)
- [x] [P2] Wither → fertilize → vanish — a withered plant releases half a corpse's
      nutrient boost to nearby plants (`_release_nutrients(mult=0.5)` ties §H),
      then is removed; nothing lasts forever, but death feeds life.
- [x] [P2] Render — mature-then-wilting plants fade brown and shrivel before
      vanishing (`withering` flag on EntityState when past WILT_FRACTION 0.8 of
      lifespan; CanvasRenderer tints rgba-brown ×0.8 radius).

### Laws
- [x] GodLaws: food_decay_enabled, food_lifespan_ticks (new "Food Decay" group,
      enabled by default; per-variant pace stays Nature's constant table);
      `wither` events throttled like blooms (in-memory only, no DB; hidden from
      web + TUI feeds alongside ruins). Tests: `tests/test_food_decay.py`
      (lifespan death, sprout immunity, variant pace, law-off freeze, soil
      fertilisation, wilting flag surfacing, DB throttle, laws roundtrip).

## AF. Performance & Massive Scale Optimization (Backend + Frontend)  [P0] — ✅ implemented
Scale the simulation and rendering pipeline to maximize active population capacity
(thousands of inhabitants) while keeping the frontend silky smooth (60+ FPS) and lightweight.

### Backend spatial indexing & engine efficiency
- [x] [P0] Zero-allocation spatial indexing — replace dynamic dict-of-lists spatial index in `world.py`
      with pre-allocated cell buckets and fast wrap arithmetic; avoid list allocations per cell per tick.
      (`world.py:38`, `rebuild_index`, `query_radius`)
- [x] [P0] Simulation loop optimizations — fast squared-distance thresholding, perception pre-filtering,
      and $O(1)$ spatial mate discovery in `simulation.py:_reproduce`.
- [x] [P1] Snapshot payload generation efficiency — streamline `snapshot_payload()` with pre-cached
      terrain payloads to eliminate redundant dictionary list copies on every broadcast frame.

### Frontend rendering & UI responsiveness
- [x] [P0] Batched Canvas 2D rendering in `CanvasRenderer.tsx` — group drawing operations by caste,
      variant, and primitive type; batch line segments and polygons; eliminate per-entity `ctx.save()` / `ctx.restore()`
      overhead (draw calls reduced from 20,000+ to ~30-50).
- [x] [P1] Level of Detail (LOD) scaling — dynamically skip fine-grained details (glyphs, peace-cry ripples,
      text labels, sleeping markers) when zoomed out, maintaining 60 FPS even with dense populations.
- [x] [P0] Decoupled React state updates in `App.tsx` — keep high-frequency simulation state in mutable refs
      for direct 60 FPS canvas consumption while throttling React virtual DOM reconciliations (HUD metrics,
      clock, weather, population counters) to ~6 Hz.

### Verification & Documentation
- [x] [P0] Comprehensive automated tests in `backend/tests/test_performance.py` for spatial hash correctness,
      boundary wrap/clamp integrity, mate discovery, terrain caching, and high-scale population throughput.
- [x] [P0] Update documentation in `backend/app/wiki.py` and ensure type-safety across TypeScript and Python protocol schemas.

## AG. Autonomous Creature Evolution (No God Interventions)  [P0] — ✅ implemented
100% autonomous, emergent creature evolution driven entirely by in-simulation experience and inherited behavioral archetypes:

### Personality Archetypes & Inheritance
- [x] [P0] 6 Core Archetypes — `brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder`.
- [x] [P0] Genetics & Heritability — 65% chance to inherit personality from mother/father; 35% chance to mutate on birth.
- [x] [P1] Altruistic Kin Feeding — altruistic creatures share carried food with hungry kin and infants.
- [x] [P1] Cautious Survival — cautious creatures seek shelter early and avoid dangerous zones.

### Dynamic Tools & Equipment (Caste Synergy)
- [x] [P0] Spears (`spear`) — Soldiers and Predators wield spears for extended reach and +20% combat damage.
- [x] [P0] Baskets (`basket`) — Farmers, Artisans, and Herbivores carry woven baskets hauling up to 3 food units back to clan larders.
- [x] [P0] Herb Poultices (`herb_poultice`) — Priests carry herbal remedies, autonomously healing injured kin (+25 HP) and curing infections.
- [x] [P1] Chieftain Crown (`crown`) — Clan leaders wear the golden crown.

### Dynamic Skill Mastery, Oral Lore & Milestone Titles
- [x] [P0] 4 Core Skills — Farming 🌾, Combat ⚔️, Foraging 🦴, and Healing 🌿 earn XP through actions.
- [x] [P0] Milestone Titles — Unlocking skill ranks awards dynamic titles (*the Slayer*, *the Fearless Champion*, *the Grand Harvester*, *the Wise Shaman*, *the Pathfinder*).
- [x] [P1] Oral Tradition in Houses — Resting elders pass their highest skill mastery XP to resting younglings.

### Expressive Emotes & Thought Bubbles
- [x] [P0] Real-time Animated Emotes — Floating thought balloons (`🍖`, `❤️`, `⚔️`, `🌿`, `🏆`, `💤`, `🧺`, `😱`) with physics above creatures in canvas and terminal.

## AH. Energy Dynamics & Stage-Aware Metabolism  [P0] — ✅ implemented
Realistic biological metabolism, fatigue, and food carrying:

### Stage-Aware Metabolism
- [x] [P0] Infant Metabolic Discount — Infants burn 55% less energy per tick (`0.45x`), juveniles burn 25% less (`0.75x`), adults standard (`1.0x`), elders `0.85x`.
- [x] [P0] Strict Sated Law — Full creatures (>85% energy / 100 energy) never consume food plants.

### Combat Stamina & Fatigue
- [x] [P0] Battle Energy Drain — Winner loses 6 energy, loser loses 10 energy in clashes.
- [x] [P1] Exhaustion Penalty — Combatants with <20% energy strike with 30% reduced damage.

### Autonomous Food Reserves
- [x] [P0] Field Reserve Consumption — Creatures can carry extra food and consume it autonomously when energy <45 far from food plants.

## AI. Terminal User Interface (TUI) Feature Parity  [P1] — ✅ implemented
Full terminal feature parity with web frontend:
- [x] [P1] Evolution Dossier in Inspector (`enter` / `i`) — Displays dynamic titles, personality badges, tool/basket inventory, and skill matrix.
- [x] [P1] Clan Details Screen (`c`) — Displays totem emblems, main house coordinates, larder, and full member table.
- [x] [P1] Category-Filtered Chronicle (`t`) — Cycle filters (All, Birth, Death, War, Politics, Settlement).
- [x] [P1] Camera Follow Mode (`w`) — Auto-track moving selected creature.

## AJ. Next-Gen Performance & Scale Architecture (3 Phases)  [P0 / P1]
Next frontier optimizations to scale Flatland to 5,000–10,000+ active inhabitants @ 60 FPS, slash network bandwidth by 90%, and achieve zero UI thread rendering lag.

### Phase 1: Network & WebSocket Delta Compression  [P0] — ✅ implemented
Slash WebSocket payload bandwidth by 85–95% (from ~1.5 MB/s to <80 KB/s per client) and eliminate JSON parsing bottlenecks on mobile/low-end clients.

- **Task 1.1: Delta-State Serialization Protocol**
  - [x] [P0] Define `DeltaStateMessage` schema (new spawns, movements, status/vitals changes, and despawn/death IDs).
  - [x] [P0] Implement keyframe pacing: broadcast a full keyframe snapshot every 60 ticks (~2s), with lightweight delta snapshots in between.
  - [x] [P0] Implement client-side snapshot reconstructor (`DeltaReconstructor`) in frontend `websocket.ts` to merge deltas into the live entity map.
- **Task 1.2: Compact Dynamic Payloads & Clan Delta Tracking**
  - [x] [P1] Compact `_entity_delta_payload` omitting static genetic fields for existing entities (75-90% per-entity byte reduction).
  - [x] [P1] Delta clan tracking sending only new/modified clans, dropping empty clan payloads to 2 bytes.
- **Task 1.3: Verification & Network Benchmarks**
  - [x] [P0] Automated network benchmark tests in `backend/tests/test_delta_compression.py` measuring payload reduction and keyframe pacing.
  - [x] [P0] Verify seamless reconnection, world reset, and snapshot reconstruction fidelity.


---

### Phase 2: Frontend OffscreenCanvas & Web Worker Rendering  [P1] — ✅ implemented
Completely decouple the 60 FPS HTML5 Canvas rendering loop from the browser's main UI thread to guarantee zero frame drops during heavy user interactions.

- **Task 2.1: Dedicated Web Worker Setup**
  - [x] [P1] Create `render.worker.ts` with canvas render loop, spatial viewport transforms, and batch draw routines.
  - [x] [P1] Update `CanvasRenderer.tsx` to transfer canvas control via `canvas.transferControlToOffscreen()`.
- **Task 2.2: Worker Event & Viewport Synchronization**
  - [x] [P1] Route pointer/pan/zoom input events from main thread to the worker via `postMessage` with zero DOM blocking.
  - [x] [P1] Modularize shared drawing functions in `renderCore.ts` for zero-duplication render loops.
  - [x] [P1] Post creature inspection hit-testing requests from main thread to worker with asynchronous resolution.
- **Task 2.3: Verification & Mobile Testing**
  - [x] [P1] Verified fluid 60 FPS rendering and Vite worker compilation (<370ms).
  - [x] [P1] Add fallback graceful degradation for browsers or environments without `OffscreenCanvas` support.


---

### Phase 3: Native High-Performance Core (C99 / SIMD / FFI)  [P0] — ✅ implemented
Accelerate simulation math (spatial hash, vector steering, boids, and collision detection) by 10x–30x, enabling 5,000–10,000+ active creatures on low-end CPUs (Intel N100/N150).

- **Task 3.1: Native C Spatial Hash & Distance Math Core**
  - [x] [P0] Implement contiguous flat buffers for entity coordinates (`entity_x`, `entity_y`, `entity_ids`).
  - [x] [P0] Implement compiled C spatial query index with squared distance thresholding (`c_query_radius`).
  - [x] [P0] Implement compiled Boids steering forces (`c_boids_separation`).
- **Task 3.2: Python FFI Bridge & Pure Python Fallback**
  - [x] [P0] Build `backend/app/native_core.py` ctypes bridge with auto-compilation via `clang`/`gcc` and seamless pure Python fallback.
  - [x] [P0] Connect `native_core` to distance queries and spatial checks.
- **Task 3.3: Verification & Scale Stress Testing**
  - [x] [P0] Deterministic validation tests comparing Python reference vs Native core outputs for exact identical math.
  - [x] [P0] Scale benchmark tests (`tests/test_scale_benchmarks.py`) verifying >160 FPS simulation ticks at scale.

---

## AK. Clan Lifecycle, Inventory Consumption & Profile UI Refinements  [P1] — ✅ implemented
Fixes and ergonomic polish for clan architecture, inventory autonomy, historical logs, and profile layouts.

- [x] [P1] **Single Main House Invariant**: Ensure every clan has strictly one active main house (HQ / Leader Residence). Fix cases where multiple houses retain `is_main=True` or unassigned upon leader succession, house destruction, or expansion.
- [x] [P1] **Emergency Inventory Consumption**: Hungry or starving creatures carrying food (in foraging baskets or equipped inventory) should eat from their carried stock immediately when energy falls below threshold, preventing starvation while returning home or wandering.
- [x] [P1] **Clan History & Major Event Log**: Track and display major historical milestones per clan (Founded on Day $D$ by Founder $X$, Leader Succession changes, HQ relocation, war declarations, tribute treaties) in the Clan details view.
- [x] [P1] **Clan & Creature Profile UI Overhaul**: Clean up profile views — eliminate duplicate data fields, prevent text/metric overlapping, and apply dynamic viewport sizing so elements never expand outside the modal container on desktop or mobile.
- [x] [P1] **House Capacity Bed Limits (16 Beds Max)**: Limit house beds to 16 maximum on max houses (`HOUSE_MAX_BEDS = 16`) with smaller houses scaling down proportionally, preventing single mega-houses from over-concentrating populations.


---

## AL. Creature Cognitive Agency & Clan Social Intelligence Roadmap  [P1]
Next-generation behavioral intelligence roadmap advancing individual cognitive decision-making, clan division of labor, dynamic bylaws, and macro geopolitics.

### Phase 1: Individual Cognitive Agency & Tactical Intelligence  [P1] — ✅ implemented
- **Task 1.1: Multi-Objective Utility AI Engine**
  - [x] [P1] Implement dynamic utility scoring $U(\text{action})$ replacing rigid if/else trees: balances survival energy, caste duty, personality weights, and kin emergency signals.
  - [x] [P1] Context-aware behavior: brave soldiers prioritize defense over snacks when under attack; cautious artisans voluntarily seek shelter before nightfall or storms.
- **Task 1.2: Spatial Mental Map & Purposeful Waypoint Navigation**
  - [x] [P1] Implement compact spatial memory (3–5 remembered coordinates per creature: Home HQ, Fertile Grove, Danger Zone, Trading Post).
  - [x] [P1] Replace Brownian random walk with purposeful patrolling, foraging circuits, and planned domestic return trips.
- **Task 1.3: Tactical Combat Formations & Phalanx Synergy**
  - [x] [P1] Soldiers from the same clan form coordinated spear/shield lines during defensive alerts.
  - [x] [P1] Agile lines (women) execute flanking and kiting maneuvers to draw enemy aggro away from vulnerable artisans and infants.
  - [x] [P1] Local combat odds evaluation: organized tactical retreat toward fortified houses when outnumbered $3:1$.
- **Task 1.4: Interpersonal Trust & Grudge Matrix**
  - [x] [P1] Track pairwise creature trust ($+15$ for healing, $+20$ for saving life, $-15$ for stealing/striking).
  - [x] [P1] High-trust pairs form cooperative hunting/farming duos, share shelters, and prioritize mutual aid.


### Phase 2: Clan Division of Labor & Institutional Governance  [P1] — ✅ implemented
- **Task 2.1: Autonomous Clan Task Board & Labor Allocation**
  - [x] [P1] Clan leaders and councils dynamically assign members to macro roles based on current crises:
    - *Food Shortage*: $70\%$ assigned to Forager/Harvester duty (2.0x harvester utility).
    - *Border Tension*: Soldiers garrison outpost doors and patrol (2.5x guard utility).
    - *Plague Outbreak*: Priests establish Main House infirmary; healthy maintain social distance.
    - *Surplus Wealth*: Builders assemble construction parties to erect new outpost houses.
- **Task 2.2: Clan Governance Archetypes**
  - [x] [P1] Implement distinct institutional forms based on founder caste and totem:
    - *Dynastic Monarchy* (Gentlemen/Nobles): Direct hereditary succession with royal lineage priority.
    - *Council of Elders* (Republic): High-side polygons vote on treaties, wars, and succession.
    - *Theocracy* (Priests): High healing/spiritual buffs, pacifist tendencies, and priest succession priority.
    - *Military Junta* (Soldiers): Expansionist conquest, tribute extortion, and combat mastery succession.
- **Task 2.3: Adaptive Clan Bylaws & Policies**
  - [x] [P1] Emergent bylaws triggered by environmental and historical events:
    - *Winter Rationing Law*: Restricts individual consumption to baseline maintenance during winter/famine (<35 energy).
    - *Martial Curfew*: Civilians restricted to settlement borders during active wars.
    - *Open Sanctuary vs. Isolationism*: Policy on admitting homeless defectors and orphaned refugees.


### Phase 3: Macro Geopolitics, Trade Caravans & Cultural Traditions  [P2] — ✅ implemented
- **Task 3.1: Calculated Casus Belli & Strategic Peace Terms**
  - [x] [P1] Wars declared with rational intent: famine raid plunder, blood feuds, and territorial friction with documented Casus Belli logs.


---

## AM. Food & Agriculture Ecosystem Roadmap  [P1]
Next-generation botanical, agricultural, and culinary simulation advancing crop diversity, intentional clan farming, granaries, soil nutrient dynamics, and caste food culture.

### Phase A: Crop Diversity & Functional Nutrition  [P1] — ✅ implemented
- **Task A.1: Botanical Diversity & Variant Expansion**
  - [x] [P1] Expand `Food.variant` with `grain` (dense calories, slow decay) and `medicinal_herb` (infection cure & healing).
  - [x] [P1] Configure variant-specific growth speeds, seasonal growth multipliers, and lifespan timers in `backend/app/simulation.py`.
- **Task A.2: Functional Dietary Effects & Nutritional Metabolics**
  - [x] [P1] Implement distinct physiological effects upon consumption:
    - *Grain*: Yields $+45$ energy baseline with high storage stability and craft emote.
    - *Berry*: Yields $+48$ energy and $+15\%$ movement speed boost with cheer emote.
    - *Medicinal Herb*: Yields $+18$ energy, heals $+30\text{ HP}$, cures active infections, and grants heal emote.
    - *Mushroom*: Yields $+24$ energy and decomposer nutrient recycling.
- **Task A.3: Foraging Preference & Health-Based Dietary Selection**
  - [x] [P1] Injured or infected creatures prioritize seeking `medicinal_herb` over standard grass (0.2x effective distance weighting).
  - [x] [P1] Starving creatures prioritize high-calorie `grain` (0.4x effective distance weighting).


### Phase B: Clan Agriculture, Sowing & Farm Plots  [P2]
- **Task B.1: Seed Harvesting & Sowing Mechanics**
  - [ ] [P2] High-farming creatures gather seed pouches from mature crops and sow them in farm plots near clan houses.
  - [ ] [P2] Cultivated crops grow $2.0\times$ faster and yield $2.5\times$ more energy than wild weeds.
- **Task B.2: Crop Tending & Weeding**
  - [ ] [P2] Farmers tend nearby crops, eliminating toxic sprouts and preventing premature withering.
  - [ ] [P2] Irrigation furrows constructed near water groves to maintain soil moisture during summer droughts.

### Phase C: Granaries, Food Preservation & Winter Spoilage  [P2]
- **Task C.1: Settlement Granaries & Physical Storage**
  - [ ] [P2] Physical granaries in clan houses storing harvested grains and cured rations securely from rain and wild beasts.
  - [ ] [P2] Granary visual fill levels and historical harvest capacity tracking.
- **Task C.2: Food Preservation & Spoilage Dynamics**
  - [ ] [P2] Sun-drying and curing techniques to convert perishable berries into long-lasting field rations.
  - [ ] [P2] Winter frost spoilage for unharvested/exposed field crops.

### Phase D: Dynamic Soil Ecology, Composting & Crop Rotation  [P2]
- **Task D.1: Soil Nutrient Depletion Grid**
  - [ ] [P2] Dynamic soil fertility grid where repeated monocropping exhausts local nitrogen/nutrients.
- **Task D.2: Composting, Ash & Corpse Decomposition**
  - [ ] [P2] Corpse decomposition and wildfire ash replenish soil fertility ($+0.4$ nutrient boost).
  - [ ] [P2] Farmers build compost heaps near houses to revitalize depleted soil.

### Phase E: Food Culture, Feasting & Breadbasket Geopolitics  [P2]
- **Task E.1: Caste Gastronomy & Dietary Taboos**
  - [ ] [P2] Geometric caste dietary privileges: Priests/Nobles demand refined grain/fruit; Isosceles soldiers eat meat/high-protein rations.
  - [ ] [P2] Sacred hospitality laws (sharing food with foreigners grants mutual non-aggression).
- **Task E.2: Clan Banquets & Famine Wars**
  - [ ] [P2] Clan banquets triggered at $>80\%$ granary capacity boosting morale, bonding, and fertility.
  - [ ] [P2] Famine raids and food blockades between agrarian breadbasket clans and martial clans.

---

## AN. Communication, Language & Diplomatic Ecosystem Roadmap  [P1]
Next-generation multi-tiered communication ecosystem spanning caste acoustic vocalizations, tactile greeting rituals, forager scent breadcrumbs, inter-clan diplomatic emissaries, boundary stones, trade barter, settlement history glyphs, and divine omens.

### Phase A: Caste Vocalizations & Acoustic Calls  [P1]
- **Task A.1: Priest Sonorous Liturgy & Morale Chant**
  - [ ] [P1] High priests emit soothing low-frequency chants that calm panicked/starving clan members, reduce stress/fear, and boost clan cohesion.
- **Task A.2: Woman's Peace-Hum & Safety Corridor**
  - [ ] [P1] In accordance with Flatland law, moving women emit a rhythmic peace-hum, causing nearby polygons to socially yield and clear collision-safe walking corridors.
- **Task A.3: Soldier Phalanx War-Chirp & Battle Rally**
  - [ ] [P1] Isosceles soldiers blow piercing war signals when engaging threats, rallying allied soldiers into aligned combat formations focusing on the flagged target.
- **Task A.4: Artisan Trade & Barter Chimes**
  - [ ] [P1] Friendly artisans emit greeting chimes when encountering neighbors, triggering mutual gift-sharing from baskets.

### Phase B: Tactile Recognition & Scent Breadcrumbs  [P2]
- **Task B.1: Mutual Angle Feeling & Greeting Rituals**
  - [ ] [P2] Non-hostile creatures touching vertices at close range ($\le 1.2$ units) perform tactile caste verification, boosting trust ($+2.0$) and mutual bonding.
  - [ ] [P2] Elder blessing touch transfers skill XP to infants and juveniles.
- **Task B.2: Forager Harvest Scent Trails**
  - [ ] [P2] Foragers discovering rich crop patches (`grain`, `berry`, `medicinal_herb`) leave temporary scent trails leading back to settlement for kin to follow.
- **Task B.3: Danger & Predator Scent Markers**
  - [ ] [P2] Death sites, predator ambush zones, and ruins emit danger scent markers that steer young and vulnerable creatures away.

### Phase C: Diplomatic Envoys & Territorial Monoliths  [P2]
- **Task C.1: Diplomatic Emissaries & Peace Missions**
  - [ ] [P2] Clans commission designated Emissaries (carrying diplomatic banner emotes 📜) to deliver peace treaties, non-aggression pacts, or tribute terms to rival Main Houses.
- **Task C.2: Tribute Couriers & Vassalage Logistics**
  - [ ] [P2] Subjugated clans send periodic tribute couriers carrying grain/herbs to suzerain granaries to prevent punitive raids.
- **Task C.3: Clan Boundary Stones & Border Heralds**
  - [ ] [P2] Clans construct boundary markers at territory borders that ring warning chimes and alert clan sentries when outsiders trespass.

### Phase D: Trade Caravans & Granary Barter  [P2]
- **Task D.1: Neutral Trading Posts & Markets**
  - [ ] [P2] Clans establish neutral trading posts at shared borders during spring/autumn to barter surplus goods (e.g. grain for berries/herbs/stone).
- **Task D.2: Traveling Peddlers & Trade Caravans**
  - [ ] [P2] Wandering merchant caravans traveling between settlements to exchange rare items and cultural news.

### Phase E: Settlement Glyphs, Linguistic Drift & Divine Revelations  [P2]
- **Task E.1: House Murals & Settlement Chronicle Inscriptions**
  - [ ] [P2] Artisans and Priests inscribe historical murals on Main House walls celebrating founder lineages, winter survivals, and battle victories.
  - [ ] [P2] Ruin archaeology: exploring ancient ruined house glyphs unlocks lost knowledge and farming techniques.
- **Task E.2: Linguistic Drift & Clan Dialects**
  - [ ] [P2] Isolated clans develop acoustic dialect drift over generations, altering cross-clan communication ease and diplomatic fidelity.
- **Task E.3: Prophetic Omens & Revelations from the Sphere**
  - [ ] [P2] Priests receive divine prophetic visions from the 3D Sphere (predicting oncoming winters/storms and preaching to worshippers).

---

## AO. Nocturnal Perils & Vital Shelter Ecosystem Roadmap  [P1]
Transformation of the Flatland night into an existential outdoor hazard and elevated shelter into an indispensable sanctuary of warmth, healing, defense, and culture.

### Phase A: Extreme Night Chill & Hypothermia Exposure  [P1]
- **Task A.1: Accelerated Nighttime Chill & Exposure Kinetics**
  - [ ] [P1] Unsheltered creatures at night accumulate chill $3.0\times$ faster than during daytime rain.
  - [ ] [P1] In winter nights or night storms, outdoor exposure accumulates extreme chill and inflicts rapid energy drain.
- **Task A.2: Frostbite Numbness & Hypothermia Mortality**
  - [ ] [P1] Reaching maximum chill ($>12$) triggers *Frostbite Numbness*: reduces speed to $0.4\times$, forces creatures to drop carried food/seed baskets, and deals $0.5\text{ HP/tick}$ damage until death (`death_cause: exposure`).

### Phase B: Nocturnal Predators & The Dusk Rush  [P1]
- **Task B.1: Predator Nocturnal Prowling & Night Vision Buff**
  - [ ] [P1] Predators gain $+40\%$ sight radius in the dark and $+20\%$ stealth chase speed when hunting unsheltered prey at night.
  - [ ] [P1] Pack-hunting behavior: wolves and wild beasts converge in hunting packs past midnight (`tod > 0.85`), prowling around village borders.
- **Task B.2: The Dusk Rush (Sunset Urgency Steering)**
  - [ ] [P1] At dusk (`tod = 0.70`), creatures feel instinctive urgency: dropping non-essential exploration to sprint straight home before nightfall.

### Phase C: Clan Hearths & Indoor Restorative Sanctuaries  [P2]
- **Task C.1: Central House Hearths & Total Thermal Immunity**
  - [ ] [P2] Inhabited houses maintain a glowing central hearth that immediately purges chill, halts energy decay, and accelerates HP healing ($+1.5\text{ HP/tick}$).
- **Task C.2: Door Barricades & Sentry Spearmen**
  - [ ] [P2] Solid walls and closed doorway thresholds prevent predators from penetrating occupied homes.
  - [ ] [P2] Clan spearmen near house doorways poke outward to defend against circling night beasts.

### Phase D: Blind Collisions & The Lethal Needle Hazard  [P2]
- **Task D.1: Pitch-Black Visibility & Blind Collision Fog**
  - [ ] [P2] Non-predator sight outdoors at night contracts to $2.5$ units, making navigation and obstacle avoidance perilous without light sources.
- **Task D.2: Accidental Impalement Hazard**
  - [ ] [P2] Collisions in pitch darkness with unsheltered moving lines (women) inflict severe accidental impalement damage ($\ge 25\text{ HP}$).
- **Task D.3: Rogue Isosceles Night Marauders**
  - [ ] [P2] Clanless or starving Isosceles bandits stalk the dark to ambush lone foragers and loot their carried rations.

### Phase E: Field Campfires & Settlement Expansion Economics  [P2]
- **Task E.1: Emergency Field Campfires & Bivouacs**
  - [ ] [P2] Stranded explorers caught far from home at nightfall gather dry brush to light temporary campfires ($3.5$ unit illuminated radius) that repel predators and provide warmth until dawn.
- **Task E.2: Shelter Scarcity & Housing Construction Pressure**
  - [ ] [P2] Population overflowing bed capacity creates urgent social and economic demand for Artisans to quarry materials and construct new houses or expand existing halls.











