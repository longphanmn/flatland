# God Laws — Flatland Simulation Reference

> **Developed by [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Built and refined using **OpenCode** and **Antigravity** · Developed from the core concepts of **Edwin A. Abbott's *Flatland***.

In Flatland, God (The Sphere) sets **universal laws of nature**, never intervening in individual lives. Every law has a specified range, default value, and ecological effect. Laws can be adjusted live via the in-app **⚖ God** drawer or programmatically via `POST /api/laws`.

---

## God Panel Layout & Navigation

The God Panel is organized into two primary top-level sections:
1. **`🎯 Presets` (Curated Worlds)**: Instant one-click simulation profiles (`⚖️ Balance`, `🌿 Sustainable`, `🔮 Theocracy`, `⚔️ Warlords`, `🔥 Chaos`, `💀 Extinction`, `🚀 Boom`) with Live Apply and World Reset options.
2. **`⚖️ Laws of Nature` (Macro Domains)**: Direct fine-tuning across 6 high-level ecological domains with real-time baseline comparison, search, modified-only filtering, interactive `?` hints, and dual slider controls:
   - 🌿 **1. Ecology & Survival**: Food capacity, plant life cycles, foraging dynamics, agriculture & granaries.
   - 🧬 **2. Biology & Evolution**: Reproduction, mutation rates, life stages, disease virulence, Micro-RNN steering & morphology.
   - ☀️ **3. Climate & Sky**: Day/night cadence, seasons, temperature sickness, house shelter & rest recovery.
   - 🏰 **4. Society, Warfare & Trade**: Clan territories, diplomacy, coalitions, larders, predation & warfare.
   - 🔮 **5. Theology & Sacred Avatars**: Faith pools, shrines, temples, age cycles & cultural transmission.
   - ⚙️ **6. World Physics & Disasters**: Wildfires, disasters, rivers, relief, structural integrity, lightning & cosmology.

---

## 🌿 1. Ecology & Survival

Governs botanical regeneration, nutrition, harvesting, agriculture, and granary storage.

| Law Parameter | Type / Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `food_count` | 0–1000 | **240** | Target living food abundance across the world (winter reduces, summer boosts). |
| `energy_max` | 10–500 | **100.0** | Maximum metabolic energy capacity an organism can store before full saturation. |
| `energy_decay_per_tick` | 0–2.0 | **0.025** | Baseline metabolic burn rate per tick without food intake; shelter and infancy reduce decay. |
| `energy_from_food` | 0–100 | **32.0** | Base energy yield from harvesting a mature plant (berry: 48, grass: 32, mushroom: 24, poison: 8). |
| `plant_variants_enabled` | Boolean | **true** | Enables botanical diversity across 6 distinct functional plant species. |
| `plant_growth_rate` | 0–1.0 | **0.045** | How fast sprouted plants mature into harvestable food; seasons and rain accelerate growth. |
| `plant_spread_rate` | 0–1.0 | **0.006** | Probability per tick that a mature plant drops seeds into adjacent fertile ground. |
| `nutrient_cycle_rate` | 0–10.0 | **0.65** | Acceleration of plant growth near decomposing corpses (death nourishes new life). |
| `poison_rate` | 0–1.0 | **0.008** | Chance a new wild sprout is poisonous (-30 HP damage on ingestion). |
| `food_decay_enabled` | Boolean | **true** | Enables mature plants to naturally wither over time and fertilize the living soil. |
| `food_lifespan_ticks` | 100–100k | **8000** | Ticks a mature plant lives before naturally withering into the living soil grid. |
| `agriculture_enabled` | Boolean | **true** | Enables seed gathering, cultivated farm plots, irrigation furrows, and tending. |
| `granaries_enabled` | Boolean | **true** | Enables communal settlement granaries to stockpile grains and berries against winter. |
| `granary_capacity` | 0–2000 | **400.0** | Units of food a settlement granary can store; sated harvesters deposit grain and berries. |

---

## 🧬 2. Biology & Evolution

Governs sensory perception, physical movement, life stages, reproduction, genetics, pathology, and polar morphological evolution.

| Law Parameter | Type / Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `perceive_radius` | 1–40 | **16.0** | Base perception sight radius; scaled by caste (Woman 0.8×, Priest 1.35×), night (0.6×), and fog (0.6×). |
| `eat_radius` | 0.2–5.0 | **1.4** | Physical contact distance required to consume a plant, corpse, or prey item. |
| `hungry_ratio` | 0.05–1.0 | **0.35** | Energy threshold (≤ 35%) feeding normalized energy into neural network input slot 0 to trigger foraging. |
| `starving_ratio` | 0.01–1.0 | **0.15** | Severe energy threshold (≤ 15%) triggering desperation sprint and pulsing survival distress. |
| `steer_turn` | 0.05–2.0 | **0.45** | Maximum heading angular turn rate per tick, dynamically scaled by creature moment of inertia (Izz). |
| `birth_enabled` | Boolean | **true** | Master switch enabling reproduction, mating, and generational ascendance. |
| `lifespan_mult` | 0.05–5.0 | **1.0** | Multiplier scaling all caste lifespans (Woman: 4,800 ticks → Priest: 9,000 ticks). |
| `adult_age` | 0–5000 | **220** | Ticks required for an infant/juvenile to mature into a sexually fertile adult. |
| `birth_rate` | 0–1.0 | **0.28** | Base reproduction probability per eligible mating pair per tick when energy and adult age are met. |
| `carrying_capacity` | -1–5000 | **350** | Population density threshold above which fertility begins to gradually diminish (-1 = auto). |
| `max_population` | -1–8000 | **500** | Hard global population cap preventing any new births until density declines (-1 = auto). |
| `mutation_rate` | 0–1.0 | **0.05** | Probability a newborn son deviates ±1 side from classical caste inheritance. |
| `sex_ratio` | 0–1.0 | **0.50** | Probability a child is a son (ascending regular polygon) vs daughter (agile line). |
| `max_sides` | 3–64 | **24** | Upper limit on regular polygon vertex ascendance (up to Priest / Circle status). |
| `euthanasia_threshold` | 0.3–1.0 | **0.70** | Irregularity threshold; deformed infants exceeding this are consumed at adulthood. |
| `mutation_sigma` | 0–0.5 | **0.08** | Gaussian mutation standard deviation (σ) applied to genome weights during crossover. |
| `crossover_rate` | 0–1.0 | **0.50** | Probability of uniform 50/50 parental genome blending during sexual reproduction. |
| `morphology_annealing_enabled` | Boolean | **false** | Enables polar genome evolution transitioning from Abbott templates to free morphology. |
| `annealing_decay_generations` | 10–1000 | **150** | Generations over which polar morphology annealing decays from Abbott templates to free evolution. |
| `safeguard_enabled` | Boolean | **true** | Master switch for extinction safeguards: negative-feedback relief scaling ($\eta$) and Tier 3 Genesis miracles. |
| `safeguard_critical_pop` | 2–50 | **12** | Emergency population floor ($K_{crit}$); dropping to or below this triggers Tier 3 Genesis miracles from The Sphere. |
| `safeguard_relief_ratio` | 0.05–0.50 | **0.30** | Carrying capacity threshold ratio ($K_{safe} = K_{cap} \times \text{ratio}$) activating Tier 1/2 homeostatic relief. |
| `safeguard_genesis_batch` | 1–20 | **6** | Number of pristine regular polygon beings created per Tier 3 Genesis miracle. |
| `safeguard_morph_mercy` | Boolean | **true** | Suspends euthanasia of irregular infants during low-population relief states ($\eta > 0.30$). |
| `soft_cap_enabled` | Boolean | **true** | Master switch for non-linear density-dependent damping ($\xi$) when population overshoots carrying capacity. |
| `damping_steepness` | 1.0–20.0 | **6.0** | Non-linear birth suppression steepness ($1 / (1 + \text{steepness} \cdot \xi^2)$) under overpopulation. |
| `crowding_stress_mult` | 0.0–1.0 | **0.35** | Multiplier scaling metabolic energy decay under crowding stress ($1 + \text{mult} \cdot \xi$). |
| `resource_strain_mult` | 0.0–2.0 | **1.2** | Multiplier scaling plant growth & spread slowdown under overpopulation resource strain ($1 / (1 + \text{mult} \cdot \xi)$). |
| `disease_enabled` | Boolean | **true** | Master switch for infectious pathogen outbreaks and transmission. |
| `disease_outbreak_rate` | 0–0.05 | **0.00006** | Spontaneous plague outbreak probability per tick during crowded or unsanitary conditions. |
| `disease_rate` | 0–1.0 | **0.035** | Transmission rate of contagion when in close contact with an infected organism. |
| `disease_energy_drain` | 0–2.0 | **0.05** | Metabolic energy drained per tick from infected creatures. |
| `disease_lethality` | 0–1.0 | **0.18** | Direct health (HP) damage dealt per tick to actively diseased creatures. |

### 🧮 Mathematical Feedback Formulations

#### 1. Density Soft-Cap Damping ($\xi$)
When population $N$ exceeds carrying capacity $K_{cap}$, the overshoot ratio is defined as:
$$\xi(N) = \max\left(0, \frac{N - K_{cap}}{K_{cap}}\right)$$

Homeostatic damping modulates world dynamics continuously:
- **Effective Birth Rate**: $R_{birth} = \frac{R_0}{1 + \text{damping\_steepness} \cdot \xi^2}$
- **Metabolic Stress**: $M_{decay} = M_0 \cdot (1 + \text{crowding\_stress\_mult} \cdot \xi)$
- **Plant Growth**: $G_{plant} = \frac{G_0}{1 + \text{resource\_strain\_mult} \cdot \xi}$

#### 2. Extinction Safeguards ($\eta$)
When population $N$ falls below $K_{safe} = K_{cap} \times \text{safeguard\_relief\_ratio}$, emergency relief severity is computed as:
$$\eta(N) = \text{clamp}\left(\frac{K_{safe} - N}{K_{safe} - K_{crit}}, 0, 1\right)$$

- **Tier 1 ($\eta \in (0, 0.5]$)**: Metabolic decay discounted up to 40%, plant growth accelerated up to 60%, maternal energy subsidy halved.
- **Tier 2 ($\eta \in (0.5, 1.0)$)**: Severe famine relief, reproductive cooldown halved, infant euthanasia suspended (`safeguard_morph_mercy`).
- **Tier 3 ($\eta \ge 1.0$ or $N \le K_{crit}$)**: The Sphere intervenes directly with a Genesis Miracle, spawning `safeguard_genesis_batch` regular beings.

---

## ☀️ 3. Climate & Sky

Governs day/night cycles, seasons, weather dynamics, exposure penalties, and house shelter benefits.

| Law Parameter | Type / Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `weather_enabled` | Boolean | **true** | Master switch for dynamic meteorological cycles (sun, rain, fog, storms). |
| `sleep_enabled` | Boolean | **true** | Enables diurnal sleep cycles, house resting, and oral lore transfer. |
| `day_length` | 4–20000 | **1200** | Total duration in ticks of a single diurnal day/night cycle. |
| `season_length` | 4–100000 | **12000** | Duration in ticks of each season (Spring, Summer, Autumn, Winter). |
| `winter_food_mult` | 0.1–1.5 | **0.70** | Winter food abundance multiplier (0.70 gentle, 0.50 harsh, 0.30 extinction collapse). |
| `night_sight_mult` | 0.05–2.0 | **0.60** | Perception radius multiplier during night ticks for non-nocturnal castes. |
| `weather_change_rate` | 0–1.0 | **0.002** | Frequency of meteorological transitions between clear, rain, fog, and storm. |
| `weather_sickness_enabled` | Boolean | **false** | Enables exposure chill and hypothermia when caught unsheltered in rain or winter. |
| `chill_drain` | 0–5.0 | **0.18** | Direct health drain per tick when chilled outdoors without shelter. |
| `shelter_enabled` | Boolean | **true** | Master switch for house claiming, door navigation, and roof protection. |
| `exposure_drain` | 0–2.0 | **0.025** | Health and energy drain per tick when outdoors during harsh storms, heavy rain, or freezing winter. |
| `house_capacity` | 1–20 | **12** | Bed capacity inside a settlement hall; excess members sleep outdoors or search for other roofs. |
| `house_decay_ticks` | 100–100k | **10000** | Ticks before an abandoned, roofless house crumbles into ruins. |
| `rest_recovery_mult` | 0.5–5.0 | **2.0** | Health regeneration multiplier when sleeping indoors under a roof. |

---

## 🏰 4. Society, Warfare & Trade

Governs sovereign clans, territorial claims, diplomacy, coalitions, larders, predation, and combat warfare.

| Law Parameter | Type / Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `territory_enabled` | Boolean | **true** | Enables clan boundary markings, territory defence, and trespass penalties. |
| `territory_radius` | 1–50 | **16.0** | Radius of clan territorial influence around settlement houses; trespass sours diplomacy. |
| `trespass_decay` | 0–5.0 | **0.15** | Diplomatic relation points lost per tick when a rival clan enters marked territory. |
| `max_clans` | -1–24 | **-1** | Maximum number of sovereign clans spawned during world initialization (-1 = auto). |
| `totems_enabled` | Boolean | **true** | Enables Sacred Avatar totem blessings for each clan settlement. |
| `succession_enabled` | Boolean | **true** | Enables dynamic governance leadership transfers on chieftain death. |
| `communication_enabled` | Boolean | **true** | Enables vocalizations, alarm chirps, peace hums, and emotional thought bubbles. |
| `knowledge_enabled` | Boolean | **true** | Enables spatial memory, waypoint mapping, and rumor broadcasting among kin. |
| `schism_enabled` | Boolean | **true** | Enables internal clan fractures when members starve or lack shelter. |
| `schism_threshold` | 0–1.0 | **0.40** | Dissatisfaction fraction (hunger, homelessness) triggering a factional clan schism. |
| `war_enabled` | Boolean | **true** | Enables inter-clan warfare, tactical raids, and territorial conquest. |
| `attack_damage` | 0–200 | **32.0** | Base damage dealt by soldiers and warriors in inter-clan battles. |
| `predation_enabled` | Boolean | **false** | Enables carnivorous predator-prey ecology and hunting dynamics. |
| `predator_ratio` | 0–1.0 | **0.02** | Fraction of population spawned as predatory carnivores hunting prey. |
| `hunt_radius` | 1–40 | **16.0** | Aggro detection radius within which carnivores and war parties acquire targets. |
| `bite_damage` | 0–200 | **28.0** | Combat damage dealt per carnivore attack or predatory strike. |
| `energy_from_prey` | 0–200 | **45.0** | Caloric energy extracted from slaying and eating a prey creature. |
| `fear_radius` | 1–40 | **12.0** | Distance at which herbivores and vulnerable castes detect threats and execute evasion. |
| `coalitions_enabled` | Boolean | **true** | Enables mutual defensive alliances and diplomatic treaties. |
| `coalition_threshold` | -100–100 | **40** | Diplomatic trust score required for two friendly clans to form a defensive coalition. |
| `leader_decisions_enabled` | Boolean | **true** | Enables chieftain governance bylaws (rationing, martial law, war declarations). |
| `resource_sharing_enabled` | Boolean | **true** | Enables communal larders and altruistic basket food sharing. |
| `larder_capacity` | 0–2000 | **300.0** | Energy storage capacity of each clan larder. |
| `cannibalism_enabled` | Boolean | **true** | Enables desperate consumption of the living during extreme starvation. |
| `eat_kin_enabled` | Boolean | **true** | Allows consumption of deceased or weak clanmates at the cost of tribal exile and feuds. |
| `cannibalism_energy` | 0–200 | **45.0** | Energy gained by starving creatures resorting to eating fallen kin or rivals. |

---

## 🔮 5. Theology & Sacred Avatars

Governs spiritual faith, shrines, temples, divine miracles, historical epochs, and cultural transmission.

| Law Parameter | Type / Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `theology_enabled` | Boolean | **true** | Enables the 8 Sacred Avatars, shrines, temples, miracles, and divine tithes. |
| `tithe_rate` | 0–1.0 | **0.04** | Fraction of energy devout worshippers offer at shrines each dawn & dusk to build clan faith. |
| `temple_faith_cost` | 0–100k | **400.0** | Faith points required to consecrate a glowing Temple of the Sphere. |
| `age_enabled` | Boolean | **true** | Enables historical epoch progression (Golden Age, Ice Age, Age of Chaos, Age of Plague). |
| `age_length` | 100–1M | **50000** | Duration in ticks per world historical epoch. |
| `culture_enabled` | Boolean | **false** | Enables traditions, governance archetypes, and cultural diffusion. |
| `culture_spread_rate` | 0–1.0 | **0.0005** | Rate at which allied clans sharing borders adopt common cultural traits and beliefs. |

### The 8 Sacred Avatars
| Avatar | Aspect | Blessing Aura |
|---|---|---|
| ⭕ Radiant Circle | Abundance | +30% harvest yield, +20% reproductive fertility |
| ⚡ Celestial Strike | Wrath & Justice | +25% warrior attack damage |
| 👁️ All-Seeing Vertex | Omniscience | +40% perception sight radius, nocturnal clarity |
| 🛡️ Indomitable Monolith | Permanence | −30% incoming damage, cold exposure resistance |
| 🌿 Sacred Spiral | Renewal | Medicinal herbs heal 2×, faster plague recovery, corpse composting |
| ⚖️ Cosmic Scales | Equilibrium | Reliable peace treaties, maintains bylaws even under famine |
| 🌀 Dimensional Rift | Ascent | Accelerated Isosceles ascendance, adaptive mutations, oral lore retention |
| 🕯️ Eternal Hearth | Sanctuary | Nighttime tranquility, reduced sleep energy decay |

---

## ⚙️ 6. World Physics & Disasters

Governs environmental terrain, hydrological rivers, structural wear, seismic activity, lightning, and wildfires.

| Law Parameter | Type / Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `boundary` | `wrap` / `clamp` | **`wrap`** | World topology: `wrap` (toroidal loop) vs `clamp` (solid boundary walls). |
| `rivers_enabled` | Boolean | **true** | Enables water channels, fords, water currents, bridges, and dams. |
| `river_count` | 0–8 | **2** | Number of procedural river channels carved across the terrain at world generation. |
| `relief_enabled` | Boolean | **true** | Enables topographical elevation, slope inertia, cliffs, and road packing. |
| `structural_enabled` | Boolean | **true** | Enables weather wear on buildings, builder repairs, and roof collapse into rubble. |
| `earthquake_enabled` | Boolean | **false** | Enables seismic tremors that shake terrain and damage weakened structures. |
| `earthquake_rate` | 0–0.001 | **0.00008** | Frequency of seismic quakes that crack buildings and shake terrain. |
| `lightning_enabled` | Boolean | **true** | Enables real lightning strikes during storms that ignite fires and damage creatures. |
| `lightning_strike_rate` | 0–0.02 | **0.0015** | Frequency of deadly electrical arc strikes during thunder storms. |
| `wildfire_enabled` | Boolean | **false** | Enables combustive flame propagation across dense vegetation and forests. |
| `fire_rate` | 0–0.05 | **0.00008** | Probability per tick that a mature plant ignites during dry spells or lightning strikes. |
| `disaster_enabled` | Boolean | **false** | Enables cataclysmic meteors, floods, and natural world disturbances. |
| `disaster_rate` | 0–0.05 | **0.0003** | Stochastic probability of catastrophic environmental disasters (meteors, deluges). |
| `anomaly_count` | 0–8 | **3** | Number of mysterious spatial anomaly zones altering local physics. |
| `door_clearance` | 1.0–4.0 | **1.5** | Width multiplier for house doorways relative to the largest creature size. |

---

## 🎯 7. Curated World Simulation Presets

Flatland ships with 7 hand-tuned ecological presets designed for diverse research and gameplay scenarios:

| Preset | Target Pop | Focus & Dynamics | Key Law Tuning |
|---|:---:|---|---|
| ⚖️ **Balance** *(Default)* | 200–350 | **Goldilocks Harmony**: Balanced ecosystem with agriculture, moderate border disputes, non-fatal skirmishes, survivable plagues, predators, bridges, and glowing shrines. | `food_count=240`, `carrying_capacity=350`, `max_pop=500`, `birth_rate=0.28`, `adult_age=220`, `predator_ratio=0.02`, `attack_damage=32.0` |
| 🌿 **Sustainable** | 300–500 | **1000-Day Prosperous Civilization**: High agricultural yields, full granaries, autumn banquets, non-lethal sparring, and stable multi-generational civilization. | `food_count=360`, `carrying_capacity=450`, `max_pop=600`, `birth_rate=0.30`, `adult_age=220`, `predator_ratio=0.01`, `banquets_enabled=true` |
| 🔮 **Theocracy** | 250–450 | **Age of the Sphere & Sacred Avatars**: High devotion, frequent tithes, glowing temples, avatar miracles, 3D epiphanies, and holy synods. | `food_count=300`, `carrying_capacity=400`, `max_pop=550`, `temple_faith_cost=200`, `tithe_rate=0.06` |
| ⚔️ **Warlords** | 150–350 | **Clash of Clans & Imperial Conquest**: Wide clan domains, frequent border skirmishes, granary raids, house takeovers, defensive coalitions, and martial succession. | `food_count=240`, `carrying_capacity=300`, `max_pop=450`, `attack_damage=48`, `trespass_decay=0.35` |
| 🔥 **Chaos** | 100–350 | **Total Turmoil**: High predator density, deadly wars, rapid 4-season shifts, wildfires, earthquakes, lightning strikes, and cannibalism under crisis. | `food_count=220`, `carrying_capacity=300`, `max_pop=450`, `predator_ratio=0.06`, `attack_damage=40`, `disease_outbreak_rate=0.0002`, `winter_food_mult=0.55` |
| 💀 **Extinction** | 30–180 | **Cataclysmic Collapse**: Severe food scarcity, freezing winters (0.3×), harsh exposure drain, rampant sickness, and desperate cannibalism survival. | `food_count=120`, `carrying_capacity=180`, `max_pop=300`, `winter_food_mult=0.30`, `exposure_drain=0.05`, `cannibalism_enabled=true` |
| 🚀 **Boom** | 600–1,000 | **Monumental Metropolis**: High food abundance, rapid maturation, dense granaries, extensive bridge networks, zero disease/war. | `food_count=500`, `carrying_capacity=800`, `max_pop=1000`, `birth_rate=0.45`, `adult_age=160` |

---

## 🔭 8. World History, Analytics & Observatory

The chronicle and telemetry systems record world dynamics in real time:

- **Genealogy Tracking**: Every birth and death is logged in SQLite (`flatworld.db`), recording parental lineage, caste ascension, cause of death, and generational depth.
- **Daily Narrative Digest**: Generated every 1,200 ticks (one Flatland day), summarizing births, deaths, battles, epidemics, miracles, and weather events.
- **Clan Dossiers**: Detailed sociological profiles tracking clan leadership, active bylaws, territory footprint, granary reserves, military strength, and diplomatic relations.
- **Observatory Telemetry**: Zero-allocation streaming telemetry monitoring biomass, Lotka-Volterra trophic cycles, Gini inequality, casualty breakdown, and morphological drift.

---

## 📖 9. God Passkey Authentication & REST API Reference

All God Laws can be inspected and adjusted programmatically:

```bash
# Fetch current live laws and active preset
curl -s http://localhost:8000/api/laws | jq .

# Mutate laws live (e.g. adjust food abundance and carrying capacity)
curl -X POST "http://localhost:8000/api/laws?persist=true"   -H "Content-Type: application/json"   -d '{"food_count": 300, "carrying_capacity": 400}'

# Apply a curated world preset live
curl -X POST "http://localhost:8000/api/presets/theocracy/apply"

# Apply preset and reset the world state
curl -X POST "http://localhost:8000/api/presets/chaos/apply-and-reset"

# Inspect living wiki documentation
curl -s http://localhost:8000/api/wiki | jq .
```
