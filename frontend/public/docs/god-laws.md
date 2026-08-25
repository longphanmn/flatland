# God Laws — Flatland Simulation Reference

> **Developed by [Long Phan](mailto:long@minhnhan.in)** ([long@minhnhan.in](mailto:long@minhnhan.in) · [minhnhan.in](https://minhnhan.in) · [world.minhnhan.in](https://world.minhnhan.in))  
> Built and refined using **OpenCode** and **Antigravity** · Developed from the core concepts of **Edwin A. Abbott's *Flatland***.


In Flatland, God sets **laws**, never touches individual lives. Every law has a specified range, default value, and ecological effect. Laws can be adjusted live via the in-app **⚖ God** drawer or programmatically via `POST /api/laws`.

---

## 1. Food & Energy

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `food_count` | 0–1000 | **220** | Target living food abundance across the world (winter reduces, summer boosts). |
| `energy_max` | 10–500 | **100** | Maximum energy capacity an organism can store. |
| `energy_decay_per_tick` | 0–2.0 | **0.025** | Baseline metabolic burn rate per tick without food intake. |
| `energy_from_food` | 0–100 | **32** | Energy yield from harvesting a mature plant (Berry: 48, Grass: 32, Mushroom: 24). |

---

## 2. Ecosystem & Biodiversity

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `plant_growth_rate` | 0–1.0 | **0.045** | Maturation speed of newly sprouted plants. |
| `plant_spread_rate` | 0–1.0 | **0.006** | Probability that a mature plant drops seed into adjacent fertile soil per tick. |
| `nutrient_cycle_rate` | 0–10.0 | **0.65** | Acceleration of plant growth near decomposing corpses (death nourishes life). |
| `poison_rate` | 0–1.0 | **0.008** | Probability that a new sprout is poisonous (-30 HP on consumption). |
| `beast_ratio` | 0–1.0 | **0.0** | Proportion of wild herbivores in the creature population. |
| `diet_strictness` | 0–1.0 | **0.0** | Dietary preference filter (0 = omnivorous, 1 = strict herbivore/carnivore). |

---

## 3. Perception, Hunger & Movement

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `hungry_ratio` | 0.05–1.0 | **0.35** | Energy threshold ($\le 35\%$) triggering heightened search sight ($1.3\times$). |
| `starving_ratio` | 0.01–1.0 | **0.15** | Energy threshold ($\le 15\%$) triggering desperate sprint ($1.35\times$) and pulsing halo. |
| `perceive_radius` | 1–40 | **16.0** | Base perception distance (Woman $0.8\times$, Priest $1.35\times$, Night $0.6\times$, Fog $0.6\times$). |
| `eat_radius` | 0.2–5.0 | **1.4** | Contact distance required to consume a plant or corpse. |
| `hungry_perceive_mult` | 1.0–3.0 | **1.3** | Perception multiplier when hungry. |
| `desperate_perceive_mult` | 1.0–3.0 | **1.6** | Perception multiplier when starving. |
| `desperate_speed_mult` | 1.0–3.0 | **1.35** | Speed boost multiplier when starving. |
| `food_giveup_ticks` | 0–100000 | **240** | Ticks after which an obstructed meal behind walls is abandoned. |
| `wander_turn` | 0–2.0 | **0.35** | Maximum heading turn angle per step while wandering (radians). |
| `steer_turn` | 0–2.0 | **0.45** | Maximum heading turn angle per step when homing toward food. |

---

## 4. Life Span, Inheritance & Reproduction

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `lifespan_mult` | 0.05–5.0 | **1.0** | Multiplier scaling all caste lifespans (Woman: 4,800 ticks $\rightarrow$ Priest: 9,000 ticks). |
| `adult_age` | 0–5000 | **220** | Ticks required for a juvenile to mature into a fertile adult. |
| `mate_radius` | 0.5–30 | **10.0** | Maximum distance between prospective parents for mating. |
| `mate_energy_min` | 0–200 | **30.0** | Minimum energy reserve required by both parents to initiate reproduction. |
| `birth_rate` | 0–1.0 | **0.28** | Reproduction probability per tick per eligible adult pair. |
| `sex_ratio` | 0–1.0 | **0.50** | Probability that a newborn is a son (polygons gain sides; daughters are lines). |
| `mutation_rate` | 0–1.0 | **0.05** | Probability that a son's side count deviates $\pm 1$ side. |
| `max_sides` | 3–64 | **24** | Maximum side count cap (= Circle / Priest caste). |
| `birth_energy_cost` | 0–100 | **20.0** | Energy invested by each parent upon successful birth. |
| `reproduction_cooldown`| 0–3000 | **200** | Ticks parents must wait before becoming eligible to mate again. |
| `carrying_capacity` | 2–10000 | **600** | Soft population cap: reproduction fertility gradually fades above this threshold. |
| `max_population` | 2–15000 | **800** | Hard population cap: births halt completely beyond this number. |
| `euthanasia_threshold` | 0.3–1.0 | **0.70** | Irregularity threshold where mutated adults are judged and absorbed. |

---

## 5. Epidemics & Health

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `disease_enabled` | Boolean | **true** | Master switch for infectious pathogen outbreaks and transmission. |
| `disease_outbreak_rate` | 0–0.05 | **0.00006** | Probability per tick of a spontaneous new outbreak starting. |
| `disease_rate` | 0–1.0 | **0.035** | Contagion transmission probability per tick within contact range. |
| `disease_radius` | 0.5–20 | **3.0** | Contagion transmission radius around an infected host. |
| `disease_energy_drain` | 0–2.0 | **0.05** | Additional metabolic energy loss per tick while sick. |
| `recovery_rate` | 0–1.0 | **0.03** | Natural recovery probability per tick for infected creatures. |
| `disease_lethality` | 0–1.0 | **0.18** | Direct health drain rate scaling infection severity. |

---

## 6. Climate, Seasons & Sky

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `day_length` | 4–20000 | **1200** | Ticks per complete day/night cycle. |
| `season_length` | 4–100000 | **12000** | Ticks per season (10 days/season; 4-season annual cycle). |
| `winter_food_mult` | 0.1–1.5 | **0.70** | Seasonal food abundance factor during winter. |
| `night_sight_mult` | 0.05–2.0 | **0.60** | Perception radius multiplier during night hours. |
| `weather_change_rate` | 0–1.0 | **0.002** | Probability per tick of atmospheric weather shifting. |
| `fog_sight_mult` | 0.05–2.0 | **0.60** | Perception multiplier during dense fog. |
| `rain_speed_mult` | 0.1–2.0 | **0.85** | Movement speed multiplier in rain and storms. |
| `storm_wander_bonus` | 0–3.2 | **0.35** | Heading turbulence during severe thunderstorms. |
| `rain_growth_mult` | 0.5–3.0 | **1.25** | Plant growth acceleration during rainfall. |
| `fog_mushroom_mult` | 0.5–3.0 | **1.35** | Mushroom growth boost during fog. |
| `storm_plant_damage` | 0–1.0 | **0.02** | Probability of crop stripping by gale winds. |
| `chill_rate` | 0–1.0 | **0.04** | Rate of exposure chill accumulation when unsheltered in rain or winter. |
| `chill_threshold` | 1–100 | **12** | Chill level causing hypothermia sickness. |
| `chill_drain` | 0–5.0 | **0.18** | Health drain per tick while experiencing hypothermia. |

---

## 7. Settlements, Houses & Shelter

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `exposure_drain` | 0–2.0 | **0.025** | Energy loss per tick when outdoors during inclement weather. |
| `house_capacity` | 1–20 | **12** | Bed capacity per standard 8×8 hall (scales with size, capped at 16 beds max). |

| `rest_recovery_mult` | 0.5–5.0 | **2.0** | Health regeneration speed multiplier while sleeping indoors. |
| `door_clearance` | 1.0–4.0 | **1.5** | Doorway width relative to creature size (blocks oversized predators). |

---

## 8. Diplomacy, Clans & Warfare

| Law Parameter | Range | Default | Ecological Effect & Hint |
|---|:---:|:---:|---|
| `war_enabled` | Boolean | **true** | Enables territorial disputes and clan conflicts. |
| `attack_damage` | 0–200 | **32.0** | Combat damage dealt per weapon strike in war. |
| `predation_enabled` | Boolean | **true** | Enables carnivore hunting of herbivores and weaker polygons. |
| `predator_ratio` | 0–1.0 | **0.02** | Ratio of apex predators in the overall population. |
| `bite_damage` | 0–200 | **28.0** | Damage dealt per predator bite. |
| `bite_cooldown` | 0–100 | **15** | Ticks between consecutive predator attacks. |
| `fear_radius` | 1–40 | **12.0** | Distance at which prey flee from approaching predators. |
| `relation_drift_rate` | 0–10.0 | **2.2** | Rate at which clan diplomatic relations drift toward neutral peace. |
| `rivalry_threshold` | -100–100 | **-80** | Diplomatic score below which clans consider each other enemies. |
| `alliance_threshold` | -100–100 | **60** | Diplomatic score above which clans form mutual alliances. |
| `trespass_decay` | 0–5.0 | **0.15** | Relationship point penalty per tick when entering rival territory. |
| `schism_enabled` | Boolean | **true** | Enables discontented clan members to break away and form new clans. |
| `schism_threshold` | 0–1.0 | **0.60** | Dissatisfaction threshold triggering a clan schism. |
| `schism_min_pop` | 2–100 | **8** | Minimum clan population required before a schism can occur. |

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

## 12. Communication, Language & Diplomacy

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

*Maintained and developed by **Long Phan** ([long@minhnhan.in](mailto:long@minhnhan.in)) · [https://minhnhan.in](https://minhnhan.in) · World [https://world.minhnhan.in](https://world.minhnhan.in)*
