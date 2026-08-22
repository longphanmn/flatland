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
- [ ] Predators as natural selection — needs §H+§I · verify: starving/elder/wounded prey
       culled first, survivor stats shift · tune: hunt_radius, bite_damage, fear_radius
       (predators hunt low-energy prey first via `hunt_radius` + `fear_radius` flee)
- [ ] Winter as apex pressure — needs §E+§H+§I · verify: one winter stacks die-back +
       starvation + hunting + plague into real extinction risk · tune: season_length,
       SEASON_FOOD_MULT, disease_rate
- [ ] Mutation → demotion → fodder — needs §C+§I · verify: demoted soldiers swell both
       prey and warrior ranks · tune: mutation_rate, euthanasia_threshold, attack_damage
- [ ] Social order meets the food chain — needs §C+§I · verify: priests see the predator
       first and flee, women fall, low castes trapped by yielding · tune: sight_mult,
       yield_strength, fear_radius
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
- [ ] [P2] Clan specialization — over generations clans drift toward warrior / farmer
      / scavenger roles from environment + totem; reflected in behaviour.
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
- [ ] [P2] Signal model — a short-lived ping carrying sender position + type,
      heard within `signal_radius`; clan-mates respond strongly, strangers
      weakly/ignore; rendered as a ripple
- [ ] [P2] Food call — a well-fed creature that finds food calls; hungry
      clan-mates steer toward the caller
- [ ] [P2] Alarm call — a creature that sees a predator calls; nearby creatures
      flee even without seeing it (group awareness beyond `fear_radius`)
- [ ] GodLaws: communication_enabled, signal_radius, food_call_rate,
      alarm_call_rate (new "Creature" law group)

### Care — the clan guides the hungry to food
- [ ] [P2] Food memory — a creature remembers where it last saw food
      (`food_memory_ttl` decay)
- [ ] [P2] Recruitment — a sated clan-mate within `flock_radius` of a starving
      one calls toward its remembered food; the starving one follows the call
      (kin guide the hungry home)

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
- [ ] [P2] World ages — a long era over seasons (`age_length`); each age bends the
      world: Ice (winter food ×0.3 + chill), Chaos (mutation ↑), Plague (disease ↑),
      Golden (bounty + birth ↑). Chosen/cycled by law; `age` in snapshot + HUD.

### Rebellion & clan schism
- [x] [P1] Schism — a clan's unhappy members (starving, homeless, or low relations)
      split off to found a new clan (new name/totem/territory), then war the parent
      (`schism_threshold`); success/failure recorded. Extends §I war + §P succession. (`config.py:60` `schism_enabled`/`threshold` 0.4/`min_pop` 4, `simulation.py:905` `_update_schism` homeless/starving ≥threshold → split 50% to new clan, new house, rivalry -60, `schism` + `rivalry` events, `protocol.py:94` `schism` type, `GodPanel.tsx:66` Rebellion, `App.tsx:568` chronicle)

### Plots (foreshadowing)
- [ ] [P2] Plots panel — god sees *upcoming* war/rebellion/schism plans as progress
      ("Ash Wolves is planning war on Long Shadow — 3/10") before they fire; icons
      on the plotters. Extends §G observability.

### Wildfire & disaster laws
- [ ] [P2] Wildfire — fire ignites (storm lightning / `fire_rate`) and spreads
      grass→plant→house; kills creatures/plants, leaves ash that fertilizes
      regrowth; renderer flame overlay.
- [ ] [P2] Disaster laws — meteor/comet strike, flood — stochastic events gated by
      `disaster_rate` (god sets frequency, never a specific strike); craters/water
      reshape terrain.

### Diplomacy depth
- [ ] [P2] Richer relation factors — common enemy +, border-adjacency −, at-war −huge,
      truce cooldown +, same-caste +; folds into the existing −100..100 clan score.
- [ ] [P2] Territory conquest — the winner of a war absorbs the loser's territory
      and house (§P); borders redraw; losing clan becomes homeless/refugees.

### Culture drift
- [ ] [P2] Culture — each clan has a culture that spreads to neighbours and can split
      (like WorldBox); culture grants a small collective bonus and can diverge into
      rival traditions.

### Behavioral genetic traits
- [ ] [P2] Genetic traits — mutation may add a heritable behaviour trait (greedy /
      peaceful / paranoid / bold) that nudges food choice, flee threshold, war
      eagerness; shown as a glyph in the profile (§Q). Distinct from the cosmetic
      identity already scoped.
- [ ] GodLaws: age_enabled, age_length, schism_enabled, schism_threshold, fire_rate,
      fire_spread_rate, disaster_rate, culture_enabled, trait_mutation_rate
      (new "Ages & Disasters" + "Society II" law groups)
