# God Laws — Flatland

God sets **laws**, never touches a life. Each law has a range, default, and hint. Edit via **⚖ God** panel or `POST /api/laws`.

All laws are in `backend/app/config.py` and `protocol.py:GodLaws`. Presets: `sustainable` / `chaos` / `extinction` via `POST /api/presets/{name}`.

## Food & Energy

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `food_count` | 0–300 | 70 | the world keeps this much food alive — bounty or famine (winter ×0.5, summer ×1.2) |
| `energy_max` | 10–500 | 100 | max energy a creature can hold |
| `energy_decay_per_tick` | 0–2 | 0.025 | how fast all life burns without eating (0.025) — winter/rain adds 0.03 exposure if roofless |
| `energy_from_food` | 0–100 | 32 | base energy from a mature plant (32) — berry 48, mushroom 24, grass 32, poison 8 |

## Ecosystem

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `plant_growth_rate` | 0–1 | 0.05 | how fast plants mature (0.05) — berry 0.65×, mushroom 0.85×, poison 0.6×, season multiplies |
| `plant_spread_rate` | 0–1 | 0.006 | chance a mature plant seeds a nearby sprout each tick |
| `nutrient_cycle_rate` | 0–10 | 0.65 | corpse decay boost to nearby plants (0.65) — death feeds life |
| `poison_rate` | 0–1 | 0.01 | chance a new sprout is poisonous (0.01) — 1% sicken, berry heals +1, poison -30 health |
| `beast_ratio` | 0–1 | 0.0 | wild herbivores as fraction of creature density — grazers that feed predators |
| `diet_strictness` | 0–1 | 0.0 | 0 omnivore, 1 strict — herbivore ignores meat, predator ignores plants |

## Hunger & Sight

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `hungry_ratio` | 0.05–1 | 0.35 | energy ≤35% → hungry, sees 1.3× farther |
| `starving_ratio` | 0.01–1 | 0.15 | energy ≤15% → starving, sees 1.6× and moves 1.35×, pulsing red |
| `perceive_radius` | 1–40 | 20 | base sight (20) — Woman 0.8×, Priest 1.35×, night 0.6×, fog 0.6×, Eye totem 1.25× |
| `eat_radius` | 0.2–5 | 1.4 | distance to eat food/corpse |
| `hungry_perceive_mult` | 1–3 | 1.3 | hungry sight multiplier |
| `desperate_perceive_mult` | 1–3 | 1.6 | starving sight multiplier |
| `desperate_speed_mult` | 1–3 | 1.35 | starving speed multiplier |
| `food_giveup_ticks` | 0–100000 | 240 | a meal blocked by rock/wall is abandoned this many ticks — seek elsewhere; 0 = never give up |

## Movement

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `wander_turn` | 0–2 | 0.35 | max heading change when wandering (rad) |
| `steer_turn` | 0–2 | 0.45 | max heading change when steering to food |

## Life & Death

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `lifespan_mult` | 0.05–5 | 1.0 | scales every caste's natural lifespan (Woman 4800 → Priest 9000) |

## Reproduction

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `adult_age` | 0–5000 | 200 | ticks before a creature may mate |
| `mate_radius` | 0.5–30 | 10 | max distance between parents |
| `mate_energy_min` | 0–200 | 30 | both parents must hold this much energy |
| `birth_rate` | 0–1 | 0.35 | chance per eligible pair per tick (× fertility) |
| `sex_ratio` | 0–1 | 0.5 | probability a child is a son (polygons ascend) |
| `mutation_rate` | 0–1 | 0.05 | chance a son's side count deviates ±1 |
| `max_sides` | 3–64 | 24 | sons stop gaining sides here (= Circle) |
| `birth_energy_cost` | 0–100 | 20 | each parent pays |
| `reproduction_cooldown` | 0–3000 | 200 | ticks parents wait after birth |
| `carrying_capacity` | 2–2000 | 80 | soft cap: fertility fades above it |
| `max_population` | 2–5000 | 140 | hard cap: no births beyond it |
| `euthanasia_threshold` | 0.3–1 | 0.7 | irregular children ≥ this are consumed at adulthood, below demoted |

## Disease

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `disease_enabled` | bool | false | plagues walk the world; disabling freezes all sickness |
| `disease_outbreak_rate` | 0–0.05 | 0.0005 | chance/tick a new outbreak begins |
| `disease_rate` | 0–1 | 0.08 | spread chance per healthy neighbour per tick |
| `disease_radius` | 0.5–20 | 3.0 | contagion range |
| `disease_energy_drain` | 0–2 | 0.15 | extra energy loss while infected |
| `recovery_rate` | 0–1 | 0.01 | chance/tick an infected recovers |
| `disease_lethality` | 0–1 | 0.5 | scales how fast infection drains health |

## Sky & Seasons

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `day_length` | 4–20000 | 1200 | ticks per day cycle |
| `season_length` | 4–100000 | 2400 (now 14400 =12 days) | ticks per season; four seasons per year |
| `winter_food_mult` | 0.1–1.5 | 0.5 (0.7 gentle) | winter bounty × winter_food_mult — lean season target = food_count × winter_food_mult |
| `night_sight_mult` | 0.05–2 | 0.6 | sight scale during the night |
| `weather_change_rate` | 0–1 | 0.002 | chance/tick the weather turns |
| `fog_sight_mult` | 0.05–2 | 0.6 | sight scale in fog |
| `rain_speed_mult` | 0.1–2 | 0.85 | movement scale in rain/storm |
| `storm_wander_bonus` | 0–3.2 | 0.35 | extra heading chaos in storms |

## Weather & Crops

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `rain_growth_mult` | 0.5–3 | 1.25 | rain/storm boost to plant growth |
| `fog_mushroom_mult` | 0.5–3 | 1.35 | fog boost to mushroom growth |
| `storm_plant_damage` | 0–1 | 0.02 | chance storm strips growth from exposed plants |

## Weather Sickness

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `chill_rate` | 0–1 | 0.04 | chill built per tick unsheltered in rain/storm/winter night |
| `chill_threshold` | 1–100 | 12 | chill at which creature is sick |
| `chill_drain` | 0–5 | 0.18 | health drain per tick when chilled |
| `wet_disease_mult` | 1–5 | 1.5 | wet/cold catch disease faster, recover slower |

## Shelter

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `exposure_drain` | 0–2 | 0.03 | extra energy/tick outdoors in rain/storm or at night |
| `house_capacity` | 1–20 | 12 (was 8) | beds in an 8×8 hall — scales with floor area; overflow spills to the nearest roof with space, only queues outside when every roof is full |
| `rest_recovery_mult` | 0.5–5 | 2.0 | indoor sleeping health regen multiplier |
| `house_decay_ticks` | 100–100000 | 2400 | abandoned house ticks before crumbling to ruin |

## Territory

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `territory_radius` | 1–50 | 14 | radius of clan territory circle |
| `trespass_decay` | 0–5 | 0 (was 1.0) | relation points lost per tick per trespasser inside rival territory |

## Society & Clans

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `cohesion_weight` | 0–3 | 0 | pull toward same-clan flock centre |
| `alignment_weight` | 0–3 | 0 | match neighbours' heading |
| `separation_weight` | 0–3 | 0 | personal-space push from any neighbour |
| `flock_radius` | 1–40 | 6 | interaction perception range |
| `relation_drift_rate` | 0–10 | 1 (2.5 preset) | points/tick clan scores relax toward 0 |
| `alliance_threshold` | -100–100 | 50 | score at/above which two clans are allies |
| `rivalry_threshold` | -100–100 | -50 (-80 preset) | score at/below which two clans are rivals |
| `totems_enabled` | bool | true | each clan bears Wolf/Tree/Shield/Eye with buffs |
| `succession_enabled` | bool | true | leader succession on death emits succession event |
| `max_clans` | -1–64 | -1 | settlement granularity: -1 = one clan per house, N ≥ 1 clusters founders into N spatial clans (applies at reset) |

## Communication

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `signal_radius` | 3–40 | 12 | heard within this range |
| `food_call_rate` | 0–1 | 0.08 | well-fed finds food → calls with this chance/tick |
| `alarm_call_rate` | 0–1 | 0.12 | sees predator → alarm call chance/tick |
## Communication II — knowledge, teaching & mobbing (§X)

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `knowledge_enabled` | bool | true | creatures learn food spots, danger zones, enemy clans and safe homes from experience; the clan remembers |
| `knowledge_ttl` | 20–100000 | 600 | ticks a fact stays in memory before it fades |
| `knowledge_share_rate` | 0–1 | 0.05 | chance/tick to broadcast the freshest fact to clan-mates — rumors arrive at half confidence per hop |
| `help_call_enabled` | bool | true | an attacked creature calls its clan; warriors rally first and mob the attacker |
| `help_radius` | 2–60 | 12 | clan-mates rally within this range; defenders near the fight soften its blows |
| `defense_weight` | 0–5 | 0.5 | damage reduction per defender mobbing the attacker |

## Rebellion, Culture, Genetics, Wildfire

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `schism_enabled` | bool | false | unhappy members split to found new clan, then war parent |
| `schism_threshold` | 0–1 | 0.4 | fraction unhappy to trigger split |
| `schism_min_pop` | 2–100 | 4 | minimum clan population to consider schism |
| `age_enabled` | bool | false | long era bending world: Ice/Chaos/Plague/Golden |
| `age_length` | 100–1M | 12000 | ticks per age (5 seasons) |
| `culture_enabled` | bool | false | clan culture spreads/splits, grants bonus |
| `culture_spread_rate` | 0–1 | 0.005 | per tick ally culture spread |
| `trait_mutation_rate` | 0–1 | 0.02 | chance mutation adds heritable behaviour trait |
| `wildfire_enabled` | bool | false | fire ignites via storm lightning, spreads |
| `fire_rate` | 0–0.05 | 0.0005 | chance/tick to ignite random plant |
| `fire_spread_rate` | 0–1 | 0.08 | spread to neighboring plants |
| `disaster_enabled` | bool | false | meteor/flood stochastic |
| `disaster_rate` | 0–0.05 | 0.0003 | chance/tick for disaster |

## Predation & Clan War

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `predation_enabled` | bool | false | predators hunt prey |
| `predator_ratio` | 0–1 | 0.08 | fraction of spawn that are predators |
| `hunt_radius` | 1–40 | 8 | predator sight for prey |
| `bite_damage` | 0–200 | 100 (40 preset wound) | damage on bite (100 = instant kill) |
| `bite_cooldown` | 0–100 | 10 | ticks between bites |
| `energy_from_prey` | 0–200 | 40 | energy predator gains per kill |
| `fear_radius` | 1–40 | 10 | prey flee when predator within this range |
| `war_enabled` | bool | false | rival-clan combat enabled |
| `attack_radius` | 0.5–10 | 1.8 | distance for clan war engagement |
| `attack_damage` | 0–200 | 100 (40 preset wound) | damage per attack (100 = lethal) |

## Politics (§AB)

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `coalitions_enabled` | bool | true | allied clans form defensive blocs — strike one member and every mate turns on you |
| `coalition_threshold` | -100–100 | 40 | relation score at which a leader may fold another clan into a coalition |
| `coalition_min_size` | 2–16 | 2 | smallest viable coalition; smaller or soured blocs dissolve |
| `leader_decisions_enabled` | bool | true | leaders declare war on remembered enemies, sue for peace when weakened, demand tribute, betray allies (bold→war, peaceful→peace, paranoid→betrayal) |
| `resource_sharing_enabled` | bool | true | a food store at the settlement: well-fed members deposit surplus, starving members withdraw; allies aid each other in famine |
| `larder_capacity` | 0–5000 | 300 | energy a clan store can hold |
| `aid_rate` | 0–1 | 0.05 | chance/tick a full-bellied ally tops up a starving ally's larder |
| `tribute_enabled` | bool | true | weak clans pay periodic tribute from their larder to a stronger protector |
| `betrayal_enabled` | bool | true | a leader breaks an alliance and strikes; third clans are told the same tale (treason) |
| `defection_enabled` | bool | true | unhappy members (starving/homeless) walk to a healthier nearby banner, even a rival's |

## Desperation (§AC)

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `cannibalism_enabled` | bool | true | the starving may hunt and eat living creatures; sated/hungry never do; cooldown between kills |
| `cannibalism_hunger_ratio` | 0–1 | 0.15 | only creatures below this energy fraction may eat the living |
| `cannibalism_energy` | 0–1000 | 45 | energy gained per desperate kill — the victim leaves a partial corpse |
| `eat_enemy_enabled` | bool | true | enemy-clan members and the weak (starving/elder/wounded) of any clan are legitimate prey; never predators, infants or indoor refugees |
| `eat_kin_enabled` | bool | true | weak kin may be eaten too — at a terrible price |
| `kin_stigma` | 0–100 | 40 | relation hit between a kin-eater's outcast band and their former clan — they become rivals |
| `exile_on_kin_eat` | bool | true | the kin-eater is cast out and founds a one-being outcast band |

## Food Decay (§AE)

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `food_decay_enabled` | bool | true | mature plants wither after their lifespan, fertilise nearby soil, then vanish — nothing lasts forever |
| `food_lifespan_ticks` | 100–1M | 9000 | ticks a mature plant lives before it withers — mushroom 0.4×, grass ×1, berry 1.5×, poisonous 3× |

## Bodies & Houses

| Law | Range | Default | Hint |
|-----|-------|---------|------|
| `door_clearance` | 1–4 | 1.5 | door width = clearance × largest creature diameter |
| `house_min_size` | 4–30 | 6 | applies to houses built after next reset |
| `house_max_size` | 6–60 | 10 | applies to houses built after next reset |
