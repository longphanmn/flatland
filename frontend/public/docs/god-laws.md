# God Laws — Flatland Simulation Reference

> **Developed by [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Built and refined using **OpenCode** and **Antigravity** · Developed from the core concepts of **Edwin A. Abbott's *Flatland***.


In Flatland, God sets **laws**, never touches individual lives. Every law has a specified range, default value, and ecological effect. Laws can be adjusted live via the in-app **⚖ God** drawer or programmatically via `POST /api/laws`.

### God Panel Layout & Navigation
The God Panel is organized into two primary top-level sections:
1. **`🎯 Presets` (Curated Worlds)**: Instant one-click simulation profiles (`⚖️ Balance`, `🌿 Sustainable`, `🔮 Theocracy`, `⚔️ Warlords`, `🔥 Chaos`, `💀 Extinction`, `🚀 Boom`) with Live Apply and World Reset options.
2. **`⚖️ Laws of Nature` (Macro Domains)**: Direct fine-tuning across 6 high-level ecological domains with real-time baseline comparison, search, modified-only filtering, and dual slider controls:
   - 🌿 **Ecology & Survival**: Food capacity, plant life cycles, foraging dynamics, agriculture & granaries.
   - 🧬 **Biology & Evolution**: Reproduction, mutation rates, life stages, disease virulence, Micro-RNN steering & morphology.
   - ☀️ **Climate & Sky**: Day/night cadence, seasons, temperature sickness, house shelter & rest recovery.
   - 🏰 **Society, Warfare & Trade**: Clan territories, diplomacy, coalitions, larders, predation & warfare.
   - 🔮 **Theology & Sacred Avatars**: Faith pools, shrines, temples, age cycles & cultural transmission.
   - ⚙️ **World Physics & Disasters**: Wildfires, disasters, rivers, relief, structural integrity, lightning & cosmology.

---

## 1. Food & Energy

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `food_count` | 0–1000 | **240** | Target living food abundance across the world (winter reduces, summer boosts). |
| `energy_max` | 10–500 | **100** | Maximum energy capacity an organism can store. |
| `energy_decay_per_tick` | 0–2.0 | **0.025** | Baseline metabolic burn rate per tick without food intake. |
| `energy_from_food` | 0–100 | **32** | Energy yield from harvesting a mature plant (Berry: 48, Grass: 32, Mushroom: 24). |

---

## 2. Ecosystem & Biodiversity

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `plant_variants_enabled` | Boolean | **true** | Master switch for grass/berry/mushroom/poisonous diversity. |
| `plant_growth_rate` | 0–1.0 | **0.045** | Maturation speed of newly sprouted plants. |
| `plant_spread_rate` | 0–1.0 | **0.006** | Probability that a mature plant drops seed into adjacent fertile soil per tick. |
| `nutrient_cycle_rate` | 0–10.0 | **0.65** | Acceleration of plant growth near decomposing corpses (death nourishes life). |
| `poison_rate` | 0–1.0 | **0.008** | Probability that a new sprout is poisonous (-30 HP on consumption). |
| `food_decay_enabled` | Boolean | **true** | Enables mature plants to naturally wither and recycle nutrients into the soil. |
| `food_lifespan_ticks` | 100–100k | **8000** | Lifespan of a mature plant before withering. |
| `agriculture_enabled` | Boolean | **true** | Seeds, farm plots, tending, weeding & irrigation furrows. |
| `granaries_enabled` | Boolean | **true** | Dry roofed store at each settlement storing harvested grain and cured berries. |
| `granary_capacity` | 0–2000 | **400.0** | Storage capacity of each settlement granary. |

---

## 3. Perception, Hunger & Movement

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `perceive_radius` | 1–40 | **16.0** | Base perception distance (Woman $0.8\times$, Priest $1.35\times$, Night $0.6\times$, Fog $0.6\times$). |
| `eat_radius` | 0.2–5.0 | **1.4** | Contact distance required to consume a plant or corpse. |
| `hungry_ratio` | 0.05–1.0 | **0.35** | Energy threshold ($\le 35\%$) feeding normalized energy into neural network input slot 0. |
| `starving_ratio` | 0.01–1.0 | **0.15** | Energy threshold ($\le 15\%$) triggering desperate survival status and visual indicator. |
| `steer_turn` | 0.05–2.0 | **0.45** | Maximum heading turn agility per step scaled by creature moment of inertia $I_{zz}$. |

> [!NOTE]
> Perception, pursuit, obstacle evasion, and flocking dynamics are continuously computed by the 16-sensor Micro-RNN neural engine rather than rigid legacy heuristic multipliers.

---

## 4. Life Span, Inheritance & Reproduction

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `birth_enabled` | Boolean | **true** | Master switch for organism reproduction and lineage succession. |
| `lifespan_mult` | 0.05–5.0 | **1.0** | Multiplier scaling all caste lifespans (Woman: 4,800 ticks $\rightarrow$ Priest: 9,000 ticks). |
| `adult_age` | 0–5000 | **220** | Ticks required for a juvenile to mature into a fertile adult. |
| `birth_rate` | 0–1.0 | **0.28** | Reproduction probability per tick per eligible adult pair with social readiness $> 0.5$. |
| `carrying_capacity` | -1–5000 | **350** | Soft population cap: reproduction fertility gradually fades above this threshold. |
| `max_population` | -1–8000 | **500** | Hard population cap: births halt completely beyond this number. |
| `mutation_rate` | 0–1.0 | **0.05** | Probability that a son's side count deviates $\pm 1$ side. |
| `sex_ratio` | 0–1.0 | **0.50** | Probability that a newborn is a son (polygons gain sides; daughters are lines). |
| `max_sides` | 3–64 | **24** | Maximum side count cap (= Circle / Priest caste). |
| `euthanasia_threshold` | 0.3–1.0 | **0.70** | Irregularity threshold where mutated adults are judged and absorbed. |

---

## 5. Epidemics & Health

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `disease_enabled` | Boolean | **true** | Master switch for infectious pathogen outbreaks and transmission. |
| `disease_outbreak_rate` | 0–0.05 | **0.00006** | Probability per tick of a spontaneous new outbreak starting. |
| `disease_rate` | 0–1.0 | **0.035** | Contagion transmission probability per tick within contact range. |
| `disease_energy_drain` | 0–2.0 | **0.05** | Additional metabolic energy loss per tick while sick. |
| `disease_lethality` | 0–1.0 | **0.18** | Direct health drain rate scaling infection severity. |

---

## 6. Climate, Seasons & Sky

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `weather_enabled` | Boolean | **true** | Master switch for dynamic atmospheric weather and seasonal storms. |
| `sleep_enabled` | Boolean | **true** | Nighttime resting behavior in warm settlements. |
| `day_length` | 4–20000 | **1200** | Ticks per complete day/night cycle. |
| `season_length` | 4–100000 | **12000** | Ticks per season (10 days/season; 4-season annual cycle). |
| `winter_food_mult` | 0.1–1.5 | **0.70** | Seasonal food abundance factor during winter. |
| `night_sight_mult` | 0.05–2.0 | **0.60** | Perception radius multiplier during night hours. |
| `weather_change_rate` | 0–1.0 | **0.002** | Probability per tick of atmospheric weather shifting. |
| `weather_sickness_enabled` | Boolean | **false** | Enables hypothermia exposure when unsheltered during severe wet weather. |
| `chill_drain` | 0–5.0 | **0.18** | Health drain per tick while experiencing hypothermia. |

---

## 7. Settlements, Houses & Shelter

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `shelter_enabled` | Boolean | **true** | Master switch for house claiming, shelter warmth, and roof construction. |
| `exposure_drain` | 0–2.0 | **0.025** | Energy loss per tick when outdoors during inclement weather. |
| `house_capacity` | 1–20 | **12** | Bed capacity per standard settlement house. |
| `house_decay_ticks` | 100–100k | **10000** | Structural duration before untended buildings weather into ruins. |
| `rest_recovery_mult` | 0.5–5.0 | **2.0** | Health regeneration speed multiplier while sleeping indoors. |
| `door_clearance` | 1.0–4.0 | **1.5** | Doorway width relative to creature size (blocks oversized predators). |
| `rivers_enabled` | Boolean | **true** | River channels and bridges across the landscape. |
| `river_count` | 0–8 | **2** | Number of river channels generated at world creation. |
| `relief_enabled` | Boolean | **true** | Elevation height field: slopes burn energy, cliffs deal fall damage. |
| `structural_enabled` | Boolean | **true** | Structural integrity of buildings under storm weathering. |
| `earthquake_enabled` | Boolean | **false** | Rare seismic quakes that damage buildings and disturb terrain. |
| `earthquake_rate` | 0–0.001 | **0.00008** | Chance per tick an earthquake begins. |
| `lightning_enabled` | Boolean | **true** | Real thunderstorm lightning strikes causing fire and shockwaves. |
| `lightning_strike_rate` | 0–0.02 | **0.0015** | Chance per storm tick of a lightning bolt. |
| `anomaly_count` | 0–8 | **3** | Hidden zones of altered physical constants across the map. |
| `wildfire_enabled` | Boolean | **false** | Master switch for wildfires ignited by lightning. |
| `fire_rate` | 0–0.05 | **0.00008** | Lightning ignition probability per tick. |
| `disaster_rate` | 0–0.05 | **0.0003** | Stochastic environmental disasters (meteor impacts, floods). |

---

## 8. Diplomacy, Clans & Warfare

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `territory_enabled` | Boolean | **true** | Clans establish territorial boundaries around their settlements. |
| `territory_radius` | 1–50 | **16** | Radius of claimed settlement territory. |
| `trespass_decay` | 0–5.0 | **0.15** | Relationship point penalty per tick when entering rival territory. |
| `max_clans` | -1–24 | **-1** | Maximum active clan count (-1 = unconstrained). |
| `totems_enabled` | Boolean | **true** | Each clan bears one of the 8 Sacred Avatars of the Sphere. |
| `succession_enabled` | Boolean | **true** | Dynastic succession upon death of a clan leader. |
| `communication_enabled` | Boolean | **true** | Master switch for caste vocalizations, sound waves, and scent trails. |
| `knowledge_enabled` | Boolean | **true** | Clan members remember food and hazard coordinates and share memory. |
| `schism_enabled` | Boolean | **true** | Unhappy members split off to found rival breakaway clans. |
| `schism_threshold` | 0–1.0 | **0.40** | Dissatisfaction threshold triggering a clan schism. |
| `culture_enabled` | Boolean | **false** | Culture spread and traditions among allied settlements. |
| `culture_spread_rate` | 0–1.0 | **0.0005** | Rate of cultural diffusion to neighboring friendly clans. |
| `age_enabled` | Boolean | **true** | Macro-epoch world ages (Golden, Ice, Chaos, Plague). |
| `age_length` | 100–1M | **50000** | Duration in ticks per world age. |
| `war_enabled` | Boolean | **true** | Enables territorial disputes and armed clan conflicts. |
| `attack_damage` | 0–200 | **32.0** | Combat damage dealt per weapon strike in war. |
| `predation_enabled` | Boolean | **false** | Enables carnivore hunting of herbivores and weaker polygons. |
| `predator_ratio` | 0–1.0 | **0.02** | Ratio of apex predators in the overall population. |
| `hunt_radius` | 1–40 | **16.0** | Vision range for predator hunting. |
| `bite_damage` | 0–200 | **28.0** | Damage dealt per predator bite. |
| `energy_from_prey` | 0–200 | **45.0** | Energy restored per successful hunt. |
| `fear_radius` | 1–40 | **12.0** | Distance at which prey flee from approaching predators. |
| `coalitions_enabled` | Boolean | **true** | Allied clans form defensive coalitions and pacts. |
| `coalition_threshold` | -100–100 | **40** | Relation score required to form or maintain a coalition. |
| `leader_decisions_enabled` | Boolean | **true** | Clan leaders make strategic diplomatic decisions (peace, war, treaties). |
| `resource_sharing_enabled` | Boolean | **true** | Clan larders pool resources at settlements to withstand famine. |
| `larder_capacity` | 0–2000 | **300.0** | Energy storage capacity of each clan larder. |
| `cannibalism_enabled` | Boolean | **true** | Extreme famine allows starving creatures to consume fallen enemies. |
| `eat_kin_enabled` | Boolean | **true** | Permitted kin-cannibalism at the cost of immediate exile and stigma. |
| `cannibalism_energy` | 0–200 | **45.0** | Energy restored per desperate cannibalistic kill. |

---

## 9. Desperation, Cannibalism & Decay

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `cannibalism_enabled` | Boolean | **true** | Allows starving creatures to consume living prey under extreme famine. |
| `cannibalism_hunger_ratio` | 0–1.0 | **0.12** | Energy threshold ($\le 12\%$) below which creatures may resort to cannibalism. |
| `cannibalism_energy` | 0–1000 | **35.0** | Energy restored per desperate cannibalistic kill. |
| `eat_enemy_enabled` | Boolean | **true** | Permits consuming fallen enemies during desperate conditions. |
| `eat_kin_enabled` | Boolean | **true** | Permits consuming fallen kin (triggers social exile and outcast status). |
| `kin_stigma` | 0–100 | **35** | Diplomatic penalty incurred upon committing kin-cannibalism. |
| `exile_on_kin_eat` | Boolean | **true** | Casts out kin-eaters into solitary rogue bands. |
| `food_decay_enabled` | Boolean | **true** | Enables mature plants to naturally wither and recycle nutrients into the soil. |
| `food_lifespan_ticks` | 100–1M | **8000** | Lifespan of a mature plant before withering. |
| `wildfire_enabled` | Boolean | **true** | Enables thunderstorm lightning strikes to ignite spreading brushfires. |
| `fire_rate` | 0–0.05 | **0.00008** | Lightning ignition probability per tick. |
| `fire_spread_rate` | 0–1.0 | **0.035** | Spread speed of flames to adjacent vegetation. |

---

## 10. Unified Theology of the Sphere

Each clan bears one of the **8 Sacred Avatars** — 2D projections of the One True God, each with a distinct divine aspect:

| Avatar | Aspect | Blessing |
|---|---|---|
| ⭕ Radiant Circle | Abundance | +30% harvest, +20% fertility |
| ⚡ Celestial Strike | Wrath & Justice | +25% warrior damage |
| 👁️ All-Seeing Vertex | Omniscience | +40% sight, nocturnal clarity |
| 🛡️ Indomitable Monolith | Permanence | −30% damage, resists the cold |
| 🌿 Sacred Spiral | Renewal | herbs heal ×2, faster plague recovery, composts the dead |
| ⚖️ Cosmic Scales | Equilibrium | reliable peace; keeps the law even while starving |
| 🌀 Dimensional Rift | Ascent | rapid Isosceles promotion, adaptive mutations, elder lore |
| 🕯️ Eternal Hearth | Sanctuary | calm through the night |

Settled clans consecrate a **shrine** beside their main house; its aura mends the faithful while faith holds out.

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `theology_enabled` | Boolean | **true** | Master switch for shrines, tithes, miracles, law resonance, sermons and synods. |
| `tithe_rate` | 0–1.0 | **0.04** | Fraction of max energy offered at the shrine at dawn & dusk (priests tithe double); fills the clan faith pool. |
| `temple_faith_cost` | 0–100000 | **400.0** | Faith spent to raise the shrine into a glowing Temple whose blessing aura extends across all territory. |

Faith overflowing at the turn of a season works a **miracle** (food blooms around the shrine, the flock is mended). When God adjusts any law, every shrine emits harmonic **chimes** and priests deliver doctrinal **sermons** interpreting the change per their avatar's dogma. During crisis ages (Ice, Plague) priests convene in the **Great Synod**, warming relations between all clans under a sacred truce; and once in an age an elder priest may receive the **3D Epiphany** — beholding the true nature of the Sphere.

---

## 11. Food & Agriculture Ecosystem

Farmers glean **seed** from wild harvests and sow **cultivated plots** near the settlement — sown crops grow $2\times$ faster and yield $2.5\times$ more than wild weeds. Skilled hands weed toxic sprouts, tend beds against premature withering, and dig **irrigation furrows** beside fertile groves (frost- and storm-proof). Sated grain & berry harvests are laid by in a dry roofed **granary**; famine draws it down, an overflowing store feeds a **banquet** (morale, bonds, +30% fertility), starving war parties **raid** rival stores, and allied clans barter at neutral **markets**. Monocropping exhausts the living **soil grid**; corpses, withered plants, wildfire ash and farmer **compost** restore it.

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `agriculture_enabled` | Boolean | **true** | Seeds, farm plots, tending, weeding & irrigation furrows. |
| `granaries_enabled` | Boolean | **true** | Clan granaries storing grain & cured rations against winter. |
| `granary_capacity` | 0–100000 | **400.0** | Units one clan granary holds (feasts fire at ≥80% fill). |
| `soil_depletion_enabled` | Boolean | **true** | The soil fertility grid: monocropping exhausts it, death refills it. |
| `banquets_enabled` | Boolean | **true** | Overflowing granaries feed a feast — morale, bonds and babies. |

Caste gastronomy is Nature's table, not a law: priests and nobles demand refined grain and fruit, soldiers crave high-protein rations, and bread broken with strangers buys mutual non-aggression (**sacred hospitality**).

---

## 12. Micro-Neural Network & Evolutionary Engine (BA)

Every creature carries a **16→12→7 Elman RNN** with **295 `float32` weights** (`16×12+12 = 204` + `12×7+7 = 91`), recurrent `hidden_state` carried per agent — **always on** (295 fixed). Sensors (16): vitals (`energy/max`, `health/max`, `chill/max`), three raycasts ±35° (normalized distance + type `+1` food/ally, `0` wall, `-1` enemy), audio amplitude/frequency, food/danger scent, collision impulse, slope grade and hidden. Outputs (7): `thrust` (`sigmoid` → velocity + `ΔE=-thrust²×k`), `steer` (`tanh` → orientation), `interact` (consume/attack), `social` (mating readiness replaces §B gating `simulation.py:6750` when `>0.5`), `vocal_amp`/`vocal_freq`, `recurrent_out` (writes hidden). Physics runs at **60 Hz** every tick, inference at **`nn_inference_hz`** (default **15 Hz**, every 4th tick latched, zero-alloc `inputs_buf`/`outputs_buf`). Genomes init `N(0,0.5)` clipped `[-4,4]` (`mutation_sigma`/`crossover_rate`); mating via spatial query when `energy > mate_energy_min` and `social > 0.5`; uniform crossover 50/50 + Gaussian mutation `N(0,0.08²)` `p=0.03`. See `backend/app/spatial_grid.py`, `agent_soa.py`, `neural_engine.py`, `agent_pipeline.py`, `evolution.py`, `sim_loop.py`.

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `nn_inference_hz` | 1–60 | **15** | Inference frequency per second (60Hz physics, 15Hz brain, rest latched) — always on. |
| `mutation_sigma` | 0–0.5 | **0.08** | Gaussian mutation σ per gene on crossover. |
| `crossover_rate` | 0–1.0 | **0.5** | Uniform crossover rate (0.5 = 50/50 parent blend). |

---

## 13. Geometric Physics & Morphological Evolution (BC)

Polar-coordinate polygon genomes $(r_i,\phi_i)$, $K\in[3,64]$ (`PRIEST_SIDES 24` threshold, `max_sides 64`) governed by **Morphological Annealing** $\lambda(g)$ live-synced with ⚖ God Laws. Vectorized SoA buffers `morph_radii/morph_angles/morph_k/morph_traits (A,P,Izz,θmin,asym,Dmult)` + `reproduction_role`. Physics baked: $E_{\max}\cdot clamp(A/A_{ref},0.5,2)$, $decay\cdot clamp(P/P_{ref},0.7,1.8)$, $Damage\cdot max(0,(cosθ_{\min}-0.5)/0.5)$ stacked with Celestial Strike, $\Delta\theta=steer\cdot(steer\_turn/(1+I_{zz}/I_{ref}))$, $asymmetry\to irregularity$ for $euthanasia\_threshold$. Abbott templates per caste (Woman thin triangle, Soldier $30°$, Priest $K\ge24$ regular, ultra-circles 32/48/64) interpolated $r^{child}=λ·r_{template}+(1-λ)·clamp(r_{parent}+𝒩(σ_r))$ sorted $\phi$, topological $p=rate\cdot(1-λ)$ add longest edge / remove closest neighbor. Energetic asymmetry $median(A)$ → high $35-50\%$ vs low $5-10\%$ $E_{\max}$, SAT narrowphase broadphase $r_{\max}$ + edge normals, telemetry `/api/metrics/morphology`.

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `morphology_annealing_enabled` | Boolean | **false** | Master switch — off keeps classic `sides/irregularity` path (AZ hash); on enables polar annealing, trait baking & SAT. |
| `annealing_start_generation` | 0–1000 | **50** | Generation where $\lambda$ decays $1\to0$; before, children snap to Abbott templates. |
| `annealing_decay_generations` | 1–5000 | **150** | Generations to decay $\lambda$ $1\to0$; short = instant morph freedom. |
| `morph_lambda_override` | 0.0–1.0 or `None` | **None** (auto) | Force $\lambda$ $0..1$ (`None`=auto); $1$ freezes Abbott castes, $0$ pure parental. |
| `vertex_mutation_std` | 0.0–0.5 | **0.05** | Gaussian $\sigma_r$ per vertex radius $r_i$, clamped $[0.2,2.5]$. |
| `angle_mutation_std` | 0.0–0.5 | **0.02** | Gaussian $\sigma_\phi$ per angle $\phi_i$, sorted circularly to avoid bow-tie. |
| `topological_mutation_rate` | 0.0–0.2 | **0.01** | Add/remove vertex chance $p\cdot(1-\lambda)$, $K 3..64$. |

---

## 14. Communication, Language & Diplomacy

Every caste has a voice: the priest's sonorous **liturgy** calms panic; moving women hum the law-mandated **peace-hum** that parts crowds; engaging soldiers blow **war-chirps** that rally allies onto the flagged target; artisans chime **greeting gifts** from their baskets; touching vertices in peace builds trust, and an elder's blessing touch passes skill to the young. Foragers drop **scent trails** home from rich finds; violent deaths and ruins leave **danger scent** the young learn to shun. Peaceful leaders commission banner-carrying **emissaries** (+15 relations on delivery); clans raise **boundary stones** that ring warning chimes at trespassers; tribute rides to suzerain granaries in **couriers' panniers**; allied neighbours found **markets** at shared borders while peddler **caravans** carry goods and news between distant settlements; isolated clans drift apart in **dialect** (strangers understand each other less); and at each season turn a shrine priest proclaims the coming season — worshippers who heed the **omen** head home prepared.

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `vocalizations_enabled` | Boolean | **true** | Caste chants, peace-hums, war-chirps, chimes & tactile greetings. |
| `scent_enabled` | Boolean | **true** | Forager scent trails home + danger scent markers at violent ends and ruins. |
| `envoys_enabled` | Boolean | **true** | Peace emissaries to rival houses + boundary stones ringing at trespass. |
| `markets_enabled` | Boolean | **true** | Neutral trading posts between allies + travelling caravans. |
| `omens_enabled` | Boolean | **true** | Priests proclaim the turning season; hearers prepare. |
| `dialect_drift_enabled` | Boolean | **true** | Isolated clans drift apart in speech; cross-clan signals fade with distance. |

---

## 15. Curated World Simulation Presets

Flatland includes 7 balanced environmental presets applicable in real-time via `POST /api/presets/{name}` or the **⚖ God Panel** / **📖 Wiki**:

| Preset | Target Pop | Focus & Dynamics | Key Law Tuning |
|---|:---:|---|---|
| ⚖️ **Balance** *(Default)* | 200–350 | **Goldilocks Harmony**: Balanced ecosystem with agriculture, moderate border disputes, non-fatal skirmishes, survivable plagues, predators, bridges, and glowing shrines. | `food_count=320`, `carrying_capacity=400`, `max_pop=500`, `birth_rate=0.065`, `adult_age=350`, `predator_ratio=0.015`, `attack_damage=30.0` |
| 🌿 **Sustainable** | 300–500 | **1000-Day Prosperous Civilization**: High agricultural yields, full granaries, autumn banquets, non-lethal sparring, and stable multi-generational civilization. | `food_count=550`, `carrying_capacity=600`, `max_pop=700`, `birth_rate=0.08`, `adult_age=250`, `predator_ratio=0.008`, `banquets_enabled=true` |
| 🔮 **Theocracy** | 250–450 | **Age of the Sphere & Sacred Avatars**: High devotion, frequent tithes, glowing temples, avatar miracles, 3D epiphanies, and holy synods. | `food_count=400`, `carrying_capacity=500`, `max_pop=550`, `temple_faith_cost=150`, `tithe_rate=0.07`, `faith_cost=150` |
| ⚔️ **Warlords** | 150–350 | **Clash of Clans & Imperial Conquest**: Wide clan domains, frequent border skirmishes, granary raids, house takeovers, defensive coalitions, and martial succession. | `food_count=340`, `carrying_capacity=380`, `max_pop=500`, `attack_damage=60`, `trespass_decay=1.6`, `rivalry_threshold=-20` |
| 🔥 **Chaos** | 100–350 | **Total Turmoil**: High predator density, deadly wars, rapid 4-season shifts, wildfires, earthquakes, lightning strikes, and cannibalism under crisis. | `food_count=320`, `carrying_capacity=350`, `max_pop=500`, `predator_ratio=0.05`, `attack_damage=40`, `disease_outbreak_rate=0.0015`, `winter_food_mult=0.55` |
| 💀 **Extinction** | 30–180 | **Cataclysmic Collapse**: Severe food scarcity, freezing winters ($0.3\times$), harsh exposure drain, rampant sickness, and desperate cannibalism survival. | `food_count=120`, `carrying_capacity=180`, `max_pop=300`, `winter_food_mult=0.30`, `exposure_drain=0.08`, `cannibalism_enabled=true` |
| 🚀 **Boom** | 600–1,000 | **Monumental Metropolis**: High food abundance, rapid maturation, dense granaries, extensive bridge networks, zero disease/war. | `food_count=440`, `carrying_capacity=650`, `max_pop=850`, `birth_rate=0.18`, `adult_age=100`, `reproduction_cooldown=120` |

---

## 16. World History, Daily Digests & Clan Dossiers

- **Daily Chronicle Digest ($1\text{ Day} = 1200\text{ ticks}$)**:
  - Consolidates real-time events into narrative single-line daily summaries.
  - Generates seasonal descriptions (Spring Thaw, High Summer, Autumn Bounty, Deep Winter) combined with clan infrastructure milestones (boundary stones, bridge repairs, Sacred Sphere choral hymns, elder craft transmissions).
  - Highlights major conflicts with named clans (e.g. `⚔️ War: Clan of the River Roots vs Clan of the Silver Monolith (8 fallen)`), house takeovers, great synods, avatar epiphanies, and epidemic sweeps.
- **Clan Profiles & Lineage Dossiers**:
  - Live population count alongside cumulative deceased casualties (`💀 Dead`).
  - Recorded founding day (`🌱 Founded Day N`) and birth tick.
  - Detailed Main House residence coordinates and dedicated `👑 Leader Residence` badge.
  - Full clan milestone archive (`founded`, `leader_change`, `schism`, `temple_raised`, `war_declared`).
- **AI Story Prompt & Export**:
  - Export complete historical chronicles as rich structured prompts for Large Language Models or standalone Markdown/JSON dossiers.

---

## 17. World Analytics & Observatory (BD — read-only, no law)

`backend/app/analytics.py` (`AnalyticsEngine`, `TelemetryRing` 6000, `MortalityDecomposer` 500) runs **zero-alloc** outside the hot loop via SoA batch aggregators (`<0.8ms/100 ticks` for 2000 agents). It exposes:
- **Ring**: population, biomass, $E/E_{\max}$, avg lifespan, dead, birth/death velocity/min
- **Mortality**: stacked distribution (starvation/combat/predation/disease/old_age/chill)
- **Trophic**: Lotka-Volterra herbivores/predators/plant + phase trajectory, Shannon $H$, evenness, richness
- **Hegemony**: HHI clan concentration, territory dominance, Gini (larder + basket)
- **Warnings**: famine horizon ($larder/burn-regrowth$), $N_e$ extinction cliff (fertile♀), unrest (crowding+hunger+personality), casus belli tension

All `GET /api/analytics/*` are **1s memoised** + rate-limited (`_ANALYTICS_CACHE`) to avoid `RT.lock` contention. The WebSocket stream coalesces the summary at **1 Hz** (`main.py:346` `payload["analytics"]`) so side panels (`Inspector`, `ClanPanel`, `PlotsPanel`, `ClanDetails`) are driven from the stream with no `DB.flush()` or `json` overhead. The **🔭 Observatory** (`frontend/src/analytics/Observatory.tsx`, top-right `📊` next to `📖` Wiki, and `right-stack` `Overview` bottom) renders sparklines, trophic, hegemony, famine/unrest warnings, and `📖` Wiki. No new God laws — pure observability. Collapse the right panel via `▶` (persisted `sessionStorage['right-stack-collapsed']`) or expand via `◀`.

---

## 18. God Passkey Authentication & REST API

To protect running worlds from unauthorized intervention, all god-touching endpoints are guarded by SHA-256 passkey authentication:

| Endpoint | Method | Description |
|---|:---:|---|
| `/api/auth/status` | `GET` | Returns whether a god passkey has been enrolled (`{"configured": bool}`). |
| `/api/auth/setup` | `POST` | First-time enrollment of the master god passkey (`{"passkey": "..."}`). |
| `/api/auth/verify` | `POST` | Verifies a passkey candidate. |
| `/api/laws` | `GET` / `POST` | Reads or applies universal laws of nature (requires `X-God-Key` header if configured). |
| `/api/presets/{name}` | `POST` | Applies a named environmental preset (supports `?persist=true` and `&reset=true`). |
| `/api/control` | `POST` | Simulation control: `pause`, `resume`, `step`, `reset` (requires `X-God-Key`). |
| `/api/clans` | `GET` | Live clan settlements with alive population, dead counts, and founded days. |
| `/api/clans/{id}` | `GET` | Detailed clan dossier with member rosters, history events, and main house coordinates. |
| `/api/history` | `GET` | Paginated chronicle events with caste, cause, and clan metadata. |
| `/api/analytics/summary` | `GET` | **BD Analytics** — instant snapshot (ring, mortality, trophic, hegemony, famine, extinction) — 1s memoization, no `RT.lock` contention. |
| `/api/analytics/timeseries` | `GET` | Rolling `deque(6000)` sparklines (population, biomass, saturation) + mortality window. |
| `/api/analytics/trophic` | `GET` | Lotka-Volterra (herbivores/predators/plant) + Shannon biodiversity. |
| `/api/analytics/hegemony` | `GET` | HHI + Gini + territory dominance. |
| `/api/analytics/warnings` | `GET` | Famine horizon, extinction Ne, unrest & casus belli tensions. |
| `/api/metrics/morphology` | `GET` | BC Morphology telemetry (K, traits, SAT). |
| `/api/state` | `GET` | Full `StateMessage` snapshot (entities, clans, relations, rivers, etc.). |
| `/api/config` | `GET` | Current `Config` dump. |
| `/api/version` | `GET` | Version + `healthz` (`tick`, `paused`, `actual_tps`, `avg_tick_ms`). |

---

*Maintained and developed by **Long Phan** ([long@minhnhan.in](mailto:long@minhnhan.in)) · [https://minhnhan.in](https://minhnhan.in) · World [https://world.minhnhan.in](https://world.minhnhan.in)*
