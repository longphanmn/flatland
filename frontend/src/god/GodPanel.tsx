import { useEffect, useState } from 'react'
import { godFetch } from './auth'
import type { GodLaws } from '../types'

type NumberLawKey = Exclude<keyof GodLaws, 'boundary'>
type BoolLawKey = {
  [K in NumberLawKey]: GodLaws[K] extends boolean | undefined ? K : never
}[NumberLawKey]

interface LawSpec {
  key: NumberLawKey
  label: string
  min: number
  max: number
  step: number
  group: string
  /** master law(s) that must be enabled for this row to show */
  gate?: BoolLawKey | BoolLawKey[]
}

const NUMBER_LAWS: LawSpec[] = [
  // Food & Energy — the economy of survival
  { key: 'food_count', label: 'Food abundance', min: 0, max: 1000, step: 5, group: 'Food & Energy' },
  { key: 'energy_max', label: 'Max energy', min: 10, max: 500, step: 5, group: 'Food & Energy' },
  { key: 'energy_decay_per_tick', label: 'Energy decay / tick', min: 0, max: 2, step: 0.01, group: 'Food & Energy' },
  { key: 'energy_from_food', label: 'Energy from food', min: 0, max: 100, step: 1, group: 'Food & Energy' },
  // Ecosystem — biodiversity of the meadow
  { key: 'plant_growth_rate', label: 'Plant growth / tick', min: 0, max: 1, step: 0.01, group: 'Ecosystem' },
  { key: 'plant_spread_rate', label: 'Plant spread chance', min: 0, max: 1, step: 0.005, group: 'Ecosystem' },
  { key: 'nutrient_cycle_rate', label: 'Nutrient cycle ×', min: 0, max: 10, step: 0.1, group: 'Ecosystem' },
  { key: 'poison_rate', label: 'Poison sprout chance', min: 0, max: 1, step: 0.01, group: 'Ecosystem', gate: 'plant_variants_enabled' },
  { key: 'beast_ratio', label: 'Herbivore ratio', min: 0, max: 1, step: 0.01, group: 'Ecosystem' },
  { key: 'diet_strictness', label: 'Diet strictness', min: 0, max: 1, step: 0.05, group: 'Ecosystem' },
  // Hunger & Sight — perception of the world
  { key: 'hungry_ratio', label: 'Hungry threshold', min: 0.05, max: 1, step: 0.05, group: 'Hunger & Sight' },
  { key: 'starving_ratio', label: 'Starving threshold', min: 0.01, max: 1, step: 0.01, group: 'Hunger & Sight' },
  { key: 'perceive_radius', label: 'Base sight radius', min: 1, max: 40, step: 0.5, group: 'Hunger & Sight' },
  { key: 'eat_radius', label: 'Eat radius', min: 0.2, max: 5, step: 0.1, group: 'Hunger & Sight' },
  { key: 'hungry_perceive_mult', label: 'Hungry sight ×', min: 1, max: 3, step: 0.1, group: 'Hunger & Sight' },
  { key: 'desperate_perceive_mult', label: 'Starving sight ×', min: 1, max: 3, step: 0.1, group: 'Hunger & Sight' },
  { key: 'desperate_speed_mult', label: 'Starving speed ×', min: 1, max: 3, step: 0.05, group: 'Hunger & Sight' },
  { key: 'food_giveup_ticks', label: 'Give-up ticks', min: 0, max: 2000, step: 10, group: 'Hunger & Sight' },
  // Movement — how bodies turn through the plane
  { key: 'wander_turn', label: 'Wander turn', min: 0, max: 2, step: 0.05, group: 'Movement' },
  { key: 'steer_turn', label: 'Steer turn', min: 0, max: 2, step: 0.05, group: 'Movement' },
  // Life & Death — the span of beings
  { key: 'lifespan_mult', label: 'Lifespan ×', min: 0.05, max: 5, step: 0.05, group: 'Life & Death' },
  // Reproduction — Nature's Law of lineage
  { key: 'adult_age', label: 'Adult age', min: 0, max: 5000, step: 50, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'mate_radius', label: 'Mate radius', min: 0.5, max: 30, step: 0.5, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'mate_energy_min', label: 'Mate energy ≥', min: 0, max: 200, step: 5, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'birth_rate', label: 'Birth rate', min: 0, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'sex_ratio', label: 'Son probability', min: 0, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'mutation_rate', label: 'Mutation rate', min: 0, max: 1, step: 0.01, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'euthanasia_threshold', label: 'Euthanasia ≥', min: 0.3, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  // Disease — plague and mercy
  { key: 'disease_outbreak_rate', label: 'Outbreak rate / tick', min: 0, max: 0.05, step: 0.0005, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_rate', label: 'Contagion chance', min: 0, max: 1, step: 0.01, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_radius', label: 'Contagion radius', min: 0.5, max: 20, step: 0.5, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_energy_drain', label: 'Energy drain / tick', min: 0, max: 2, step: 0.05, group: 'Disease', gate: 'disease_enabled' },
  { key: 'recovery_rate', label: 'Recovery chance / tick', min: 0, max: 1, step: 0.005, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_lethality', label: 'Lethality', min: 0, max: 1, step: 0.05, group: 'Disease', gate: 'disease_enabled' },
  // Sky & Seasons — the turning of the world
  { key: 'day_length', label: 'Day length (ticks)', min: 4, max: 20000, step: 4, group: 'Sky & Seasons' },
  { key: 'season_length', label: 'Season length (ticks)', min: 4, max: 100000, step: 10, group: 'Sky & Seasons' },
  { key: 'winter_food_mult', label: 'Winter food ×', min: 0.1, max: 1.5, step: 0.05, group: 'Sky & Seasons' },
  { key: 'night_sight_mult', label: 'Night sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'weather_change_rate', label: 'Weather turn chance', min: 0, max: 1, step: 0.001, group: 'Sky & Seasons', gate: 'weather_enabled' },
  { key: 'fog_sight_mult', label: 'Fog sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons', gate: 'weather_enabled' },
  { key: 'rain_speed_mult', label: 'Rain speed ×', min: 0.1, max: 2, step: 0.05, group: 'Sky & Seasons', gate: 'weather_enabled' },
  { key: 'storm_wander_bonus', label: 'Storm wander +', min: 0, max: 3.2, step: 0.05, group: 'Sky & Seasons', gate: 'weather_enabled' },
  // Weather & Crops — rain waters, fog favours mushrooms, storms damage (§R)
  { key: 'rain_growth_mult', label: 'Rain growth ×', min: 0.5, max: 3, step: 0.05, group: 'Weather & Crops', gate: 'weather_enabled' },
  { key: 'fog_mushroom_mult', label: 'Fog mushroom ×', min: 0.5, max: 3, step: 0.05, group: 'Weather & Crops', gate: 'weather_enabled' },
  { key: 'storm_plant_damage', label: 'Storm plant damage', min: 0, max: 1, step: 0.005, group: 'Weather & Crops', gate: 'weather_enabled' },
  // Weather Sickness — chill and wet contagion (§R)
  { key: 'chill_rate', label: 'Chill rate / tick', min: 0, max: 1, step: 0.005, group: 'Weather Sickness', gate: 'weather_sickness_enabled' },
  { key: 'chill_threshold', label: 'Chill threshold', min: 1, max: 100, step: 1, group: 'Weather Sickness', gate: 'weather_sickness_enabled' },
  { key: 'chill_drain', label: 'Chill drain / tick', min: 0, max: 5, step: 0.05, group: 'Weather Sickness', gate: 'weather_sickness_enabled' },
  { key: 'wet_disease_mult', label: 'Wet disease ×', min: 1, max: 5, step: 0.1, group: 'Weather Sickness', gate: 'weather_sickness_enabled' },
  // Shelter — roofs against the sky
  { key: 'exposure_drain', label: 'Exposure drain / tick', min: 0, max: 2, step: 0.05, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'house_capacity', label: 'House capacity', min: 1, max: 20, step: 1, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'rest_recovery_mult', label: 'Rest healing ×', min: 0.5, max: 5, step: 0.25, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'house_decay_ticks', label: 'House decay ticks', min: 100, max: 100000, step: 100, group: 'Shelter', gate: 'shelter_enabled' },
  // Territory — clan land and trespass
  { key: 'territory_radius', label: 'Territory radius', min: 1, max: 50, step: 1, group: 'Territory', gate: 'territory_enabled' },
  { key: 'trespass_decay', label: 'Trespass decay / tick', min: 0, max: 5, step: 0.05, group: 'Territory', gate: 'territory_enabled' },
  // Clan founding (§V) — settlements define clans
  { key: 'max_clans', label: 'Max clans', min: -1, max: 24, step: 1, group: 'Clan' },
  { key: 'max_sides', label: 'Max sides', min: 3, max: 64, step: 1, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'birth_energy_cost', label: 'Birth energy cost', min: 0, max: 100, step: 1, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'reproduction_cooldown', label: 'Cooldown ticks', min: 0, max: 3000, step: 10, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'carrying_capacity', label: 'Carrying capacity', min: -1, max: 5000, step: 25, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'max_population', label: 'Hard pop cap', min: -1, max: 8000, step: 25, group: 'Reproduction', gate: 'birth_enabled' },
  // Society — interaction & clan relations
  { key: 'cohesion_weight', label: 'Cohesion weight', min: 0, max: 3, step: 0.1, group: 'Interaction' },
  { key: 'alignment_weight', label: 'Alignment weight', min: 0, max: 3, step: 0.1, group: 'Interaction' },
  { key: 'separation_weight', label: 'Separation weight', min: 0, max: 3, step: 0.1, group: 'Interaction' },
  { key: 'flock_radius', label: 'Flock radius', min: 1, max: 40, step: 1, group: 'Interaction' },
  { key: 'relation_drift_rate', label: 'Relation drift / tick', min: 0, max: 10, step: 0.5, group: 'Interaction' },
  { key: 'alliance_threshold', label: 'Alliance threshold', min: -100, max: 100, step: 5, group: 'Interaction' },
  { key: 'rivalry_threshold', label: 'Rivalry threshold', min: -100, max: 100, step: 5, group: 'Interaction' },
  // Predation — hunters and prey
  { key: 'predator_ratio', label: 'Predator ratio', min: 0, max: 1, step: 0.01, group: 'Predation', gate: 'predation_enabled' },
  { key: 'hunt_radius', label: 'Hunt radius', min: 1, max: 40, step: 1, group: 'Predation', gate: 'predation_enabled' },
  { key: 'bite_damage', label: 'Bite damage', min: 0, max: 200, step: 10, group: 'Predation', gate: 'predation_enabled' },
  { key: 'bite_cooldown', label: 'Bite cooldown', min: 0, max: 100, step: 1, group: 'Predation', gate: 'predation_enabled' },
  { key: 'energy_from_prey', label: 'Energy from prey', min: 0, max: 200, step: 5, group: 'Predation', gate: 'predation_enabled' },
  { key: 'fear_radius', label: 'Fear radius', min: 1, max: 40, step: 1, group: 'Predation', gate: 'predation_enabled' },
  // Communication — clan calls (§Q)
  { key: 'signal_radius', label: 'Signal radius', min: 3, max: 40, step: 1, group: 'Communication', gate: 'communication_enabled' },
  { key: 'food_call_rate', label: 'Food call rate', min: 0, max: 1, step: 0.01, group: 'Communication', gate: 'communication_enabled' },
  { key: 'alarm_call_rate', label: 'Alarm call rate', min: 0, max: 1, step: 0.01, group: 'Communication', gate: 'communication_enabled' },
  // Communication II — knowledge, teaching & mobbing (§X)
  { key: 'knowledge_ttl', label: 'Knowledge TTL', min: 20, max: 100000, step: 10, group: 'Communication II', gate: 'knowledge_enabled' },
  { key: 'knowledge_share_rate', label: 'Share rate / tick', min: 0, max: 1, step: 0.01, group: 'Communication II', gate: 'knowledge_enabled' },
  { key: 'help_radius', label: 'Help radius', min: 2, max: 60, step: 1, group: 'Communication II', gate: ['knowledge_enabled', 'help_call_enabled'] },
  { key: 'defense_weight', label: 'Defense weight', min: 0, max: 5, step: 0.05, group: 'Communication II', gate: ['knowledge_enabled', 'help_call_enabled'] },
  // Rebellion — clan schism (§S)
  { key: 'schism_threshold', label: 'Schism threshold', min: 0, max: 1, step: 0.05, group: 'Rebellion', gate: 'schism_enabled' },
  { key: 'schism_min_pop', label: 'Schism min pop', min: 2, max: 100, step: 1, group: 'Rebellion', gate: 'schism_enabled' },
  // Ages — super-seasons (§S)
  { key: 'age_length', label: 'Age length (ticks)', min: 100, max: 1000000, step: 100, group: 'Ages', gate: 'age_enabled' },
  // Culture (§S)
  { key: 'culture_spread_rate', label: 'Culture spread / tick', min: 0, max: 1, step: 0.0005, group: 'Culture', gate: 'culture_enabled' },
  // Genetics — heritable traits (§S)
  { key: 'trait_mutation_rate', label: 'Trait mutation rate', min: 0, max: 1, step: 0.005, group: 'Genetics' },
  // Wildfire & Disasters (§S)
  { key: 'fire_rate', label: 'Fire ignite / tick', min: 0, max: 0.05, step: 0.0001, group: 'Wildfire & Disasters', gate: 'wildfire_enabled' },
  { key: 'fire_spread_rate', label: 'Fire spread / tick', min: 0, max: 1, step: 0.01, group: 'Wildfire & Disasters', gate: 'wildfire_enabled' },
  { key: 'disaster_rate', label: 'Disaster / tick', min: 0, max: 0.05, step: 0.0001, group: 'Wildfire & Disasters', gate: 'disaster_enabled' },
  // Clan war — rival blood
  { key: 'attack_radius', label: 'Attack radius', min: 0.5, max: 10, step: 0.1, group: 'Clan War', gate: 'war_enabled' },
  { key: 'attack_damage', label: 'Attack damage', min: 0, max: 200, step: 10, group: 'Clan War', gate: 'war_enabled' },
  // Politics — coalitions, leaders, resources, betrayal (§AB)
  { key: 'coalition_threshold', label: 'Coalition threshold', min: -100, max: 100, step: 5, group: 'Politics', gate: 'coalitions_enabled' },
  { key: 'coalition_min_size', label: 'Coalition min size', min: 2, max: 16, step: 1, group: 'Politics', gate: 'coalitions_enabled' },
  { key: 'larder_capacity', label: 'Larder capacity', min: 0, max: 2000, step: 25, group: 'Politics', gate: ['resource_sharing_enabled', 'tribute_enabled', 'aid_rate' as unknown as BoolLawKey] },
  { key: 'aid_rate', label: 'Allied aid chance', min: 0, max: 1, step: 0.01, group: 'Politics', gate: 'resource_sharing_enabled' },
  // Desperation — cannibalism (§AC)
  { key: 'cannibalism_hunger_ratio', label: 'Hunger threshold', min: 0.01, max: 0.6, step: 0.01, group: 'Desperation', gate: 'cannibalism_enabled' },
  { key: 'cannibalism_energy', label: 'Energy per kill', min: 0, max: 200, step: 5, group: 'Desperation', gate: 'cannibalism_enabled' },
  { key: 'kin_stigma', label: 'Kin stigma', min: 0, max: 100, step: 5, group: 'Desperation', gate: ['cannibalism_enabled', 'exile_on_kin_eat'] },
  // Food decay — nothing lasts forever (§AE)
  { key: 'food_lifespan_ticks', label: 'Food lifespan (ticks)', min: 100, max: 100000, step: 100, group: 'Food Decay', gate: 'food_decay_enabled' },
  // Unified Theology — shrines, tithes & faith (§AP)
  { key: 'tithe_rate', label: 'Tithe rate', min: 0, max: 0.5, step: 0.01, group: 'Theology', gate: 'theology_enabled' },
  { key: 'temple_faith_cost', label: 'Temple faith cost', min: 50, max: 5000, step: 50, group: 'Theology', gate: 'theology_enabled' },
  // Agriculture — sowing, granaries & the living soil (§AM)
  { key: 'granary_capacity', label: 'Granary capacity', min: 0, max: 2000, step: 25, group: 'Agriculture', gate: 'granaries_enabled' },
  // Bodies & Houses — geometry of the flat world
  { key: 'door_clearance', label: 'Door clearance ×', min: 1, max: 4, step: 0.1, group: 'Bodies & Houses' },
  { key: 'house_min_size', label: 'House min size', min: 4, max: 30, step: 1, group: 'Bodies & Houses' },
  { key: 'house_max_size', label: 'House max size', min: 6, max: 60, step: 1, group: 'Bodies & Houses' },
  // Rivers — channels, floods & crossings (§AQ PH-3)
  { key: 'river_count', label: 'River count', min: 0, max: 8, step: 1, group: 'Rivers', gate: 'rivers_enabled' },
  // Seismic & waves (§AQ PH-8)
  { key: 'earthquake_rate', label: 'Quake rate / tick', min: 0, max: 0.001, step: 0.00001, group: 'Seismic & Waves', gate: 'earthquake_enabled' },
  { key: 'signal_speed', label: 'News speed', min: 0, max: 40, step: 1, group: 'Seismic & Waves' },
  // Electrostatics (§AQ PH-9)
  { key: 'lightning_strike_rate', label: 'Bolt rate / storm tick', min: 0, max: 0.02, step: 0.0005, group: 'Electrostatics', gate: 'lightning_enabled' },
  // Cosmology (§AQ PH-10)
  { key: 'anomaly_count', label: 'Anomaly zones', min: 0, max: 8, step: 1, group: 'Cosmology' },
]

const GROUP_ORDER = [
  'Food & Energy',
  'Ecosystem',
  'Hunger & Sight',
  'Movement',
  'Life & Death',
  'Reproduction',
  'Disease',
  'Sky & Seasons',
  'Ages',
  'Culture',
  'Genetics',
  'Wildfire & Disasters',
  'Weather & Crops',
  'Weather Sickness',
  'Shelter',
  'Territory',
  'Clan',
  'Communication',
  'Communication II',
  'Language & Diplomacy',
  'Rebellion',
  'Interaction',
  'Predation',
  'Clan War',
  'Politics',
  'Desperation',
  'Food Decay',
  'Agriculture',
  'Theology',
  'Bodies & Houses',
  'Rivers',
  'Terrain',
  'Materials',
  'Seismic & Waves',
  'Electrostatics',
  'Cosmology',
]

// Backend Config defaults — switches render these until laws load.
const BOOL_DEFAULTS: Partial<Record<BoolLawKey, boolean>> = {
  birth_enabled: true,
  disease_enabled: false,
  weather_enabled: true,
  sleep_enabled: true,
  shelter_enabled: true,
  house_claim_enabled: true,
  hearths_enabled: true,
  territory_enabled: true,
  weather_sickness_enabled: false,
  communication_enabled: true,
  knowledge_enabled: true,
  help_call_enabled: true,
  wildfire_enabled: false,
  disaster_enabled: false,
  culture_enabled: false,
  age_enabled: true,
  schism_enabled: true,
  totems_enabled: true,
  succession_enabled: true,
  plant_variants_enabled: true,
  predation_enabled: false,
  war_enabled: true,
  coalitions_enabled: true,
  leader_decisions_enabled: true,
  resource_sharing_enabled: true,
  tribute_enabled: true,
  betrayal_enabled: true,
  defection_enabled: true,
  cannibalism_enabled: true,
  eat_enemy_enabled: true,
  eat_kin_enabled: true,
  exile_on_kin_eat: true,
  food_decay_enabled: true,
  theology_enabled: true,
  agriculture_enabled: true,
  granaries_enabled: true,
  soil_depletion_enabled: true,
  banquets_enabled: true,
  vocalizations_enabled: true,
  scent_enabled: true,
  envoys_enabled: true,
  markets_enabled: true,
  omens_enabled: true,
  dialect_drift_enabled: true,
  rivers_enabled: true,
  relief_enabled: true,
  structural_enabled: true,
  rubble_blocking_enabled: true,
  earthquake_enabled: false,
  lightning_enabled: true,
}

const LAW_HINTS: Partial<Record<NumberLawKey, string>> = {
  food_count: 'the world keeps this much food alive — bounty or famine (winter ×0.5, summer ×1.2)',
  plant_growth_rate: 'how fast plants mature (0.05) — berry 0.65×, mushroom 0.85×, poison 0.6×, season multiplies',
  plant_spread_rate: 'chance a mature plant seeds a nearby sprout each tick',
  nutrient_cycle_rate: 'corpse decay boost to nearby plants (0.65) — death feeds life',
  poison_rate: 'chance a new sprout is poisonous (0.01) — 1% sicken, berry heals +1, poison -30 health',
  beast_ratio: 'wild herbivores as fraction of creature density — grazers that feed predators',
  diet_strictness: '0 omnivore, 1 strict — herbivore ignores meat, predator ignores plants',
  territory_radius: 'clan territory circle radius around house (14) — members steer home, trespass sours relations',
  trespass_decay: 'relation points lost per tick a rival trespasses inside territory',
  house_decay_ticks: 'abandoned house ticks before crumbling to ruin (2400 = 2 seasons)',
  energy_decay_per_tick: 'how fast all life burns without eating (0.025) — winter/rain adds 0.03 exposure if roofless',
  energy_from_food: 'base energy from a mature plant (32) — berry 48, mushroom 24, grass 32, poison 8',
  perceive_radius: 'base sight (20) — each caste scales it (Woman 0.8×, Priest 1.35×), night 0.6×, fog 0.6×, Eye totem 1.25×',
  food_giveup_ticks: 'a meal blocked by rock/wall is abandoned this many ticks — the hungry give up and seek food elsewhere (0 = never give up)',
  lifespan_mult: 'scales every caste’s natural lifespan',
  door_clearance: 'doorways scale with the largest creature × this (1.5)',
  house_min_size: 'applies to houses built after the next reset (6)',
  house_max_size: 'applies to houses built after the next reset (10)',
  adult_age: 'creatures must be this many ticks old to mate (200)',
  birth_rate: 'chance per eligible pair per tick, before fertility (0.35)',
  sex_ratio: 'probability a child is a son (polygons ascend; daughters are lines)',
  mutation_rate: 'chance a son’s side count deviates ±1 from inheritance (0.05)',
  euthanasia_threshold: 'irregular children at/above this are consumed at adulthood, below it demoted (0.7)',
  carrying_capacity: 'above this population, fertility fades gradually (-1 = scale with map area, 80 per 200×200)',
  max_population: 'hard cap — no births beyond (-1 = scale with map area, 140 per 200×200)',
  house_capacity: 'beds in an 8×8 hall (12) — scales with floor area, so a small hut cannot hold a whole clan; overflow spills to the nearest roof with space',
  exposure_drain: 'energy lost per tick outdoors in rain/storm/night (0.03)',
  rest_recovery_mult: 'health regen multiplier when sleeping indoors (2.0)',
  totems_enabled: 'each clan bears a Sacred Avatar of the Sphere with a subtle blessing — ⭕ Radiant Circle ⚡ Celestial Strike 👁️ All-Seeing Vertex 🛡️ Indomitable Monolith 🌿 Sacred Spiral ⚖️ Cosmic Scales 🌀 Dimensional Rift 🕯️ Eternal Hearth',
  succession_enabled: 'leader succession on death emits succession event',
  max_clans: 'society granularity: -1 = one clan per house; N ≥ 1 clusters founders into N spatial clans (applies at reset)',
  rain_growth_mult: 'rain/storm boost to plant growth (1.25) — soaked ground regrows faster',
  fog_mushroom_mult: 'fog boost to mushroom growth (1.35) — the decomposer tier loves mist',
  storm_plant_damage: 'chance a storm strips growth from exposed plants (0.02) — occasionally uproots',
  chill_rate: 'chill built per tick unsheltered in rain/storm/winter night (0.04)',
  chill_threshold: 'chill at which creature sickens (12) — shelter sheds 2.5× faster',
  chill_drain: 'health drain per tick when chilled (0.18) — death cause chill',
  wet_disease_mult: 'wet/cold catch disease faster and recover slower (1.5×)',
  age_length: 'ticks per age (12000 = 5 seasons) — Golden×1.25 food, Ice×0.55 food + chill, Chaos×1.8 mutation, Plague×1.8 disease',
  culture_spread_rate: 'allied clans within territory adopt same culture with this chance/tick (0.005)',
  trait_mutation_rate: 'chance mutation adds heritable trait greedy/peaceful/paranoid/bold (0.02) — bold war, paranoid flee, greedy food',
  fire_rate: 'chance a random mature plant ignites each tick (0.0005) — storm lightning raises to 0.002',
  river_count: 'channel bands across the map at world creation (2) — fords, floods, bridges & dams (§AQ PH-3)',
  signal_speed: 'news wavefront speed in units/tick (8) — distant ears hear the alarm later; wind carries sound faster downwind; 0 = instant',
  earthquake_rate: 'chance/tick an earthquake begins (0.00008)',
  lightning_strike_rate: 'chance/tick of a bolt during a storm (0.0015)',
  anomaly_count: 'hidden zones of altered physics at world creation (3)',
  fire_spread_rate: 'spread to neighboring plants within 6 (0.08) — kills creatures/plants, ash fertilizes',
  disaster_rate: 'meteor/flood stochastic gated by this per tick (0.0003) — crater/water reshapes terrain',
  signal_radius: 'heard within this range (12) — clan-mates respond strongly, strangers weakly',
  food_call_rate: 'well-fed finds food → calls with this chance/tick (0.08)',
  alarm_call_rate: 'sees predator → alarm call chance/tick (0.12)',
  knowledge_ttl: 'ticks a learned fact stays in memory before it fades (600)',
  knowledge_share_rate: 'chance/tick a creature broadcasts its freshest fact to clan-mates (0.05) — rumors arrive at half confidence',
  help_radius: 'clan-mates rally to a help call within this range (12); defenders near the fight soften its blows',
  defense_weight: 'damage reduction per defender mobbing the attacker (0.5 → 2 defenders = 50% softer)',
  winter_food_mult: 'winter bounty × winter_food_mult (0.7 gentle, 0.5 harsh, 0.3 extinction) — lean season target = food_count × winter_food_mult',
  schism_threshold: 'fraction unhappy (starving/homeless) to split (0.4)',
  schism_min_pop: 'minimum clan population to consider schism (4)',
  coalition_threshold: 'relation score at which a leader may fold another clan into a coalition (40)',
  coalition_min_size: 'smallest viable coalition; smaller blocs dissolve (2)',
  larder_capacity: 'energy a clan store at the settlement can hold (300) — surplus deposited, famine withdraws',
  aid_rate: 'chance/tick a full-bellied ally tops up a starving ally\'s larder (0.05)',
  food_lifespan_ticks: 'ticks a mature plant lives before it withers (9000) — mushroom 0.4×, grass ×1, berry 1.5×, poisonous 3×; withered plants fertilise the soil',
  theology_enabled: 'the Sacred Avatars of the Sphere: settled clans consecrate shrines, the devout tithe at dawn & dusk, faith works miracles, chimes ring when laws change, and high faith raises temples',
  tithe_rate: 'fraction of max energy offered at the shrine each dawn & dusk (0.04); priests tithe double — fills the clan faith pool',
  temple_faith_cost: 'clan faith spent to raise a shrine into a glowing Temple whose blessing aura covers all territory (400)',
  cannibalism_hunger_ratio: 'only creatures below this energy fraction may eat the living (0.15)',
  cannibalism_energy: 'energy gained per desperate kill (45) — the victim leaves a partial corpse',
  kin_stigma: 'relation hit between a kin-eater\'s outcast band and their former clan (40) — they become rivals',
  granary_capacity: 'units one clan granary holds (400) — sated harvesters lay grain & cured berries by; famine and feasts draw it down',
  agriculture_enabled: 'farmers glean seed from wild harvests, sow cultivated plots near the settlement (2× growth, 2.5× yield), weed toxic sprouts, tend beds against withering, and dig irrigation furrows near fertile groves',
  granaries_enabled: 'a dry roofed store at each settlement: sated grain/berry harvests are laid by (35%), starving members withdraw, raids & markets & caravans move it',
  soil_depletion_enabled: 'monocropping exhausts the living soil grid; corpses, ash and farmer compost restore it',
  banquets_enabled: 'a granary at ≥80% feeds a clan feast: morale, bonds and a fertility boost while the mead lasts',
  vocalizations_enabled: 'every caste has a voice: priests chant away panic, women hum peace corridors, soldiers chirp rally signals at enemies, artisans chime gifts from baskets, touching vertices in peace builds trust',
  scent_enabled: 'foragers drop scent trails home from rich finds; violent deaths and ruins leave danger scent the young learn to shun',
  envoys_enabled: 'peaceful leaders commission banner-carrying emissaries to rival houses (+15 relations on delivery); clans raise boundary stones that ring warning chimes at trespassers',
  markets_enabled: 'allied neighbours found neutral trading posts at shared borders and barter surplus every few minutes; peddler caravans carry goods and news between distant settlements',
  omens_enabled: 'at each season turn a shrine priest proclaims what comes; worshippers who hear it drift home prepared',
  dialect_drift_enabled: 'isolated clans drift apart in speech — strangers understand each other less the further their dialects split; allies converge on a shared tongue',
}

function Switch({
  checked,
  onChange,
  title,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  title?: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      title={title}
      onClick={() => onChange(!checked)}
      className="god-switch-btn"
      style={{
        width: 38,
        height: 22,
        minHeight: 22,
        maxHeight: 22,
        borderRadius: 11,
        background: checked ? '#238636' : '#21262d',
        border: `1px solid ${checked ? '#2ea043' : '#30363d'}`,
        position: 'relative',
        cursor: 'pointer',
        flex: 'none',
        padding: 0,
        margin: 0,
        transition: 'background .15s',
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 2,
          left: checked ? 18 : 2,
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: '#e6edf3',
          boxShadow: '0 1px 2px rgba(0,0,0,0.4)',
          transition: 'left .15s',
          display: 'block',
        }}
      />
    </button>
  )
}

interface Props {
  open: boolean
  onClose: () => void
}

interface PresetItem {
  key: string
  label: string
  subtitle: string
  badge?: string
  color: string
  border: string
  bg: string
  title: string
  description: string
  tags: string[]
}

const PRESET_LIST: PresetItem[] = [
  {
    key: 'balance',
    label: '⚖️ Balance',
    subtitle: 'Goldilocks World',
    badge: 'DEFAULT',
    color: '#e3b341',
    border: '#d29922',
    bg: 'rgba(227, 179, 65, 0.15)',
    title: 'Goldilocks balance: 220 food, carrying 600, max 800 — gentle harmony for 500-800 population',
    description: 'All 15+ simulation mechanics active in gentle harmony: 220 food, carrying capacity 600 (max 800), mild war, rare predation, mild plagues, gentle winters, and thriving multi-generational clans.',
    tags: ['500-800 Pop', 'Everything Active', 'Harmonious'],
  },
  {
    key: 'sustainable',
    label: '🌿 Sustainable',
    subtitle: '1000-Day Peace',
    color: '#3fb950',
    border: '#2ea043',
    bg: 'rgba(63, 185, 80, 0.15)',
    title: '1000-day gentle: 450 food, carrying 2200, rare war/predation, calm society',
    description: 'Plentiful food (450), calm diplomacy, rare conflict, and very gentle winter for flourishing multi-generational stability.',
    tags: ['Abundant Food', 'Peaceful', 'Low Conflict'],
  },
  {
    key: 'chaos',
    label: '🔥 Chaos',
    subtitle: 'Total Turmoil',
    color: '#f85149',
    border: '#da3633',
    bg: 'rgba(248, 81, 73, 0.15)',
    title: 'Chaos: famine, predators, wars, plagues, fires',
    description: 'Brutal stress test: high predator ratio, lethal wars, frequent plagues, wildfires, and rapid seasonal turnover.',
    tags: ['Deadly Wars', 'Wildfires', 'Frequent Plagues'],
  },
  {
    key: 'extinction',
    label: '💀 Extinction',
    subtitle: 'Cataclysmic Collapse',
    color: '#bc8cff',
    border: '#8957e5',
    bg: 'rgba(188, 140, 255, 0.15)',
    title: 'Extinction: 100 food, harsh winter 0.3, high decay',
    description: 'Extreme famine (100 food), harsh winter (0.3x), rampant disease, and rapid decay. Tests how fast societies collapse.',
    tags: ['Famine', 'Harsh Winter', 'Extinction Risk'],
  },
  {
    key: 'boom',
    label: '🚀 Boom',
    subtitle: 'High-Scale Growth',
    color: '#79c0ff',
    border: '#388bfd',
    bg: 'rgba(121, 192, 255, 0.15)',
    title: 'Boom: 650 food, carrying 3500, max 5000 — massive population scale test',
    description: 'Massive population scale test: rapid reproduction, food abundance (650), peace, and carrying capacity up to 5,000.',
    tags: ['5000+ Pop', 'Rapid Births', 'Zero War/Plague'],
  },
]

function detectPreset(laws: GodLaws): string | null {
  if (laws.food_count === 220 && laws.carrying_capacity === 600) return 'balance'
  if (laws.food_count === 420 && laws.carrying_capacity === 2000) return 'balance'
  if (laws.food_count === 450 && laws.carrying_capacity === 2200) return 'sustainable'
  if (laws.food_count === 320 && laws.carrying_capacity === 800) return 'chaos'
  if (laws.food_count === 100 && laws.carrying_capacity === 250) return 'extinction'
  if (laws.food_count === 650 && laws.carrying_capacity === 3500) return 'boom'
  return null
}

export default function GodPanel({ open, onClose }: Props) {
  const [laws, setLaws] = useState<GodLaws>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPreset, setCurrentPreset] = useState<string | null>('balance')
  const [expandedPreset, setExpandedPreset] = useState<string | null>('balance')
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768)

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    Promise.all([
      fetch('/api/laws').then((r) => r.json()),
      fetch('/api/presets').then((r) => r.json()).catch(() => null),
    ])
      .then(([lawsData, presetsData]) => {
        setLaws(lawsData)
        const detected = presetsData?.current || detectPreset(lawsData) || 'balance'
        setCurrentPreset(detected)
        setExpandedPreset(detected)
      })
      .catch(() => setError('failed to load laws'))
      .finally(() => setLoading(false))
  }, [open])

  const [openHint, setOpenHint] = useState<string | null>(null)

  if (!open) return null

  const set = (key: NumberLawKey, raw: string | number) => {
    const val = raw === '' ? undefined : Number(raw)
    setLaws((l) => {
      const updated = { ...l, [key]: val }
      setCurrentPreset(detectPreset(updated))
      return updated
    })
  }

  const stepVal = (key: NumberLawKey, min: number, max: number, step: number, dir: 1 | -1) => {
    const curr = (laws[key] as number | undefined) ?? min
    const next = Math.max(min, Math.min(max, Number((curr + dir * step).toFixed(4))))
    set(key, next)
  }

  const boolVal = (k: BoolLawKey) => laws[k] ?? BOOL_DEFAULTS[k] ?? false
  const setBool = (k: BoolLawKey, v: boolean) => {
    setLaws((l) => {
      const updated = { ...l, [k]: v }
      setCurrentPreset(detectPreset(updated))
      return updated
    })
  }
  const gateOpen = (gate?: BoolLawKey | BoolLawKey[]) =>
    !gate || (Array.isArray(gate) ? gate : [gate]).every((g) => boolVal(g))

  const ToggleRow = ({ k, label, title, hideIfOff }: { k: BoolLawKey; label: string; title?: string; hideIfOff?: BoolLawKey | BoolLawKey[] }) => {
    if (hideIfOff && !gateOpen(hideIfOff)) return null
    return (
      <div className="god-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, borderBottom: '1px solid #21262d', padding: '8px 10px' }}>
        <span title={title} style={{ color: '#e6edf3', fontSize: 13, fontWeight: 500 }}>{label}</span>
        <Switch checked={boolVal(k)} onChange={(v) => setBool(k, v)} title={title ?? label} />
      </div>
    )
  }

  const postLaws = async (persist: boolean) => {
    setError(null)
    setSaved(false)
    setSubmitting(true)
    try {
      const qs = persist ? '?persist=true' : '?persist=false'
      const res = await godFetch(`/api/laws${qs}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(laws),
      })
      if (!res.ok) {
        const body = await res.json()
        throw new Error(
          typeof body.detail === 'string'
            ? body.detail
            : (body.detail?.[0]?.msg ?? 'law rejected'),
        )
      }
      const data = await res.json()
      setLaws(data)
      setCurrentPreset(detectPreset(data))
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      if (e instanceof Error && e.message === 'cancelled') return
      setError(e instanceof Error ? e.message : 'failed to apply law')
    } finally {
      setSubmitting(false)
    }
  }
  const apply = () => postLaws(false)
  const save = () => postLaws(true)
  const applyPreset = async (name: string, reset: boolean) => {
    setError(null)
    setSaved(false)
    setSubmitting(true)
    try {
      const res = await godFetch(`/api/presets/${name}?persist=true${reset ? '&reset=true' : ''}`, { method: 'POST' })
      if (!res.ok) throw new Error((await res.json()).detail ?? 'preset failed')
      const data = await res.json()
      setLaws(data.laws)
      setCurrentPreset(name)
      setExpandedPreset(name)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      if (e instanceof Error && e.message === 'cancelled') return
      setError(e instanceof Error ? e.message : 'preset failed')
    } finally {
      setSubmitting(false)
    }
  }

  const foot = (
    <footer className="god-foot">
      {error && <span className="god-error">{error}</span>}
      {!error && saved && <span className="god-saved">✓ Laws active</span>}
      {!error && !saved && submitting && <span className="god-note" style={{ color: '#d29922' }}>Applying…</span>}
      <button onClick={apply} disabled={submitting} title="apply to current world only (Reset reverts)">Apply</button>
      <button onClick={save} disabled={submitting} title="The Sphere — save laws to current and future worlds (Reset keeps it)" className="god-save">
        Save
      </button>
    </footer>
  )

  const head = (
    <header className="god-head">
      <h2>⚖ The Sphere — Laws of Flatland</h2>
      <button className="god-close" onClick={onClose} aria-label="close">
        ×
      </button>
    </header>
  )

  const activePresetMeta = PRESET_LIST.find((p) => p.key === currentPreset)

  const body = (
    <>
      <p className="god-note">
        You are The Sphere (God): set the universal laws from Spaceland, never the fates.
        Creatures and the world obey the higher-dimensional law; no single life may be touched.
      </p>

      <div className="god-group" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: 2 }}>
          <span style={{ fontSize: 12, color: '#8b949e', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            World Presets
          </span>
          <span
            style={{
              fontSize: 11,
              padding: '2px 10px',
              borderRadius: 12,
              background: activePresetMeta ? activePresetMeta.bg : 'rgba(163, 113, 247, 0.15)',
              border: `1px solid ${activePresetMeta ? activePresetMeta.border : '#8b949e'}`,
              color: activePresetMeta ? activePresetMeta.color : '#d2a8ff',
              fontWeight: 700,
            }}
          >
            {activePresetMeta ? `Active: ${activePresetMeta.label}` : 'Active: ⚙ Custom'}
          </span>
        </div>

        {/* Preset Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(280px, 1fr))', gap: 8 }}>
          {PRESET_LIST.map(({ key, label, subtitle, badge, description, tags, color, border, bg }) => {
            const isActive = currentPreset === key
            const isExpanded = expandedPreset === key
            return (
              <div
                key={key}
                onClick={() => setExpandedPreset(key)}
                style={{
                  background: isActive ? bg : isExpanded ? '#1c2128' : '#161b22',
                  border: `1.5px solid ${isActive ? border : isExpanded ? '#444c56' : '#30363d'}`,
                  borderRadius: 8,
                  padding: '10px 12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                  cursor: 'pointer',
                  boxShadow: isActive ? `0 0 14px ${bg}` : 'none',
                  transition: 'all 0.15s ease-in-out',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: isActive ? color : '#e6edf3' }}>{label}</span>
                    <span style={{ fontSize: 11, color: '#8b949e', fontStyle: 'italic' }}>({subtitle})</span>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {badge && (
                      <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 4, background: '#d29922', color: '#0d1117', fontWeight: 800 }}>
                        {badge}
                      </span>
                    )}
                    {isActive && (
                      <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 4, background: color, color: '#0d1117', fontWeight: 800 }}>
                        ACTIVE
                      </span>
                    )}
                  </div>
                </div>

                <p style={{ fontSize: 12, color: '#c9d1d9', margin: 0, lineHeight: 1.4 }}>
                  {description}
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 2 }}>
                  {tags.map((t) => (
                    <span key={t} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 10, background: '#21262d', color: '#8b949e', border: '1px solid #30363d' }}>
                      {t}
                    </span>
                  ))}
                </div>

                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      applyPreset(key, false)
                    }}
                    title={`Apply ${label} laws to live world`}
                    style={{
                      flex: 1,
                      padding: '5px 8px',
                      fontSize: 11,
                      fontWeight: 600,
                      background: isActive ? '#21262d' : '#21262d',
                      borderColor: isActive ? border : '#30363d',
                      color: isActive ? color : '#c9d1d9',
                      borderRadius: 6,
                    }}
                  >
                    ⚡ Apply Laws
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      applyPreset(key, true)
                    }}
                    title={`Apply ${label} + start fresh world`}
                    style={{
                      flex: 1,
                      padding: '5px 8px',
                      fontSize: 11,
                      fontWeight: 700,
                      background: isActive ? '#238636' : '#238636',
                      borderColor: '#2ea043',
                      color: '#fff',
                      borderRadius: 6,
                    }}
                  >
                    🔄 Apply & Reset
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {loading ? (
        <p className="god-note">reading the tablets…</p>
      ) : (
        <>
          <label className="god-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', borderBottom: '1px solid #30363d' }}>
            <span title="what happens at the edge of the world" style={{ color: '#e6edf3', fontSize: 13, fontWeight: 500 }}>Edge of world</span>
            <select
              value={laws.boundary ?? 'wrap'}
              onChange={(e) =>
                setLaws((l) => ({ ...l, boundary: e.target.value as 'wrap' | 'clamp' }))
              }
              style={{ minHeight: 32, padding: '4px 8px' }}
            >
              <option value="wrap">wrap</option>
              <option value="clamp">walls</option>
            </select>
          </label>

          {GROUP_ORDER.map((group) => {
            const lawsInGroup = NUMBER_LAWS.filter((l) => l.group === group && gateOpen(l.gate))
            const special = (
              <>
                {group === 'Reproduction' && (
                  <ToggleRow k="birth_enabled" label="Births allowed" title="whether new life may begin at all — off hides the lineage dials" />
                )}
                {group === 'Disease' && (
                  <ToggleRow k="disease_enabled" label="Plagues allowed" title="plagues walk the world; disabling freezes all sickness" />
                )}
                {group === 'Sky & Seasons' && (
                  <>
                    <ToggleRow k="weather_enabled" label="Weather allowed" title="whether the weather ever turns — off hides rain/fog/storm dials everywhere" />
                    <ToggleRow k="sleep_enabled" label="Night rest" title="creatures shelter in houses after dark" />
                  </>
                )}
                {group === 'Shelter' && (
                  <>
                    <ToggleRow k="shelter_enabled" label="Shelter allowed" title="creatures may claim roofs; disabling leaves all exposed and hides the shelter dials" />
                    <ToggleRow k="house_claim_enabled" label="Clan house claims" title="clans claim houses as settlements" hideIfOff="shelter_enabled" />
                    <ToggleRow k="hearths_enabled" label="Hearths" title="kin buy hearth fuel from the larder — a lit hearth warms the roof through winter; unfed, it goes dark (§AQ PH-1)" hideIfOff="shelter_enabled" />
                  </>
                )}
                {group === 'Territory' && (
                  <ToggleRow k="territory_enabled" label="Territory claimed" title="clans claim a circle around their house; disabling removes borders" />
                )}
                {group === 'Weather Sickness' && (
                  <ToggleRow k="weather_sickness_enabled" label="Weather sickness" title="chill and wet contagion — rain/storm/winter nights build chill, past threshold drains health; wet catches disease faster" />
                )}
                {group === 'Communication' && (
                  <ToggleRow k="communication_enabled" label="Communication" title="food + alarm calls — clan-mates respond strongly, strangers weakly; rendered as ripples" />
                )}
                {group === 'Communication II' && (
                  <>
                    <ToggleRow k="knowledge_enabled" label="Knowledge" title="creatures learn facts from experience (food/danger/enemies/safe homes), share them as rumors at half confidence; the clan remembers" />
                    <ToggleRow k="help_call_enabled" label="Help calls" title="an attacked creature calls its clan; warriors rally first and mob the attacker, defenders soften its blows" hideIfOff="knowledge_enabled" />
                  </>
                )}
                {group === 'Wildfire & Disasters' && (
                  <>
                    <ToggleRow k="wildfire_enabled" label="Wildfire" title="fire ignites via storm lightning / fire_rate and spreads grass→plant→house; ash fertilizes" />
                    <ToggleRow k="disaster_enabled" label="Disasters" title="meteor/flood stochastic — god sets frequency, never a specific strike" />
                  </>
                )}
                {group === 'Rivers' && (
                  <ToggleRow k="rivers_enabled" label="Rivers" title="horizontal channels: fords cost energy, the current sweeps infants and the wounded, rain floods the banks and leaves silt; builders span planks and raise dams (§AQ PH-3)" />
                )}
                {group === 'Terrain' && (
                  <ToggleRow k="relief_enabled" label="Relief (height field)" title="the land has height: uphill burns energy, cliffs deal fall damage, rain slides steep slopes, feet pack fast roads that grow nothing (§AQ PH-4)" />
                )}
                {group === 'Seismic & Waves' && (
                  <ToggleRow k="earthquake_enabled" label="Earthquakes" title="rare quakes throw bodies, drop weakened roofs and crack stone; Pentagons+ feel the deep hum three ticks early (§AQ PH-8)" />
                )}
                {group === 'Electrostatics' && (
                  <ToggleRow k="lightning_enabled" label="Storm lightning" title="bolts kill under the arc, ignite the ground and fuse electrostatic rock (§AQ PH-9)" />
                )}
                {group === 'Cosmology' && (
                  <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>Hidden zones of altered physics — fertile ground, heavy gravity, calm air. Skilled foragers discover them; shrines beside one draw extra power. Law changes sweep a shimmer wave across the land (§AQ PH-10).</div>
                )}
                {group === 'Materials' && (
                  <>
                    <ToggleRow k="structural_enabled" label="Structural integrity" title="storms & floodwater wear buildings down; builders mend what still stands; a spent roof collapses to ruin (§AQ PH-6)" />
                    <ToggleRow k="rubble_blocking_enabled" label="Rubble blocks lots" title="collapsed ruins leave rubble that bars the ground until builders clear it" />
                  </>
                )}
                {group === 'Culture' && (
                  <ToggleRow k="culture_enabled" label="Culture" title="culture spreads to allied neighbours, can split into rival traditions; grants small collective bonus" />
                )}
                {group === 'Genetics' && (
                  <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>Heritable traits: greedy/peaceful/paranoid/bold — mutation {laws.trait_mutation_rate ?? 0.02}</div>
                )}
                {group === 'Ages' && (
                  <ToggleRow k="age_enabled" label="Ages" title="super-seasons: Golden/ Ice/ Chaos/ Plague — each bends food/mutation/disease/chill. God sets length, world cycles." />
                )}
                {group === 'Rebellion' && (
                  <ToggleRow k="schism_enabled" label="Schism allowed" title="unhappy members (starving/homeless) split off to found new clan then war parent — schism_threshold fraction to trigger" />
                )}
                {group === 'Clan' && (
                  <>
                    <ToggleRow k="totems_enabled" label="Sacred Avatars" title="each clan bears one of the 8 Sacred Avatars of the Sphere (⭕ ⚡ 👁️ 🛡️ 🌿 ⚖️ 🌀 🕯️) granting a distinct divine blessing; disabling makes all clans plain" />
                    <ToggleRow k="succession_enabled" label="Succession" title="leader succession on death emits succession event; disabling keeps founder as eternal leader" />
                  </>
                )}
                {group === 'Ecosystem' && (
                  <ToggleRow k="plant_variants_enabled" label="Plant variants" title="grass/berry/mushroom/poisonous diversity; disabling makes all plants grass" />
                )}
                {group === 'Predation' && (
                  <ToggleRow k="predation_enabled" label="Predation allowed" title="predators hunt prey; disabling makes them docile" />
                )}
                {group === 'Clan War' && (
                  <ToggleRow k="war_enabled" label="War allowed" title="rival clans fight on contact; disabling enforces peace" />
                )}
                {group === 'Politics' && (
                  <>
                    <ToggleRow k="coalitions_enabled" label="Coalitions" title="allied clans form defensive blocs — strike one member and every mate turns on you; soured relations dissolve the pact" />
                    <ToggleRow k="leader_decisions_enabled" label="Leader decisions" title="leaders declare war on remembered enemies, sue for peace when weakened, demand tribute, betray allies (bold→war, peaceful→peace, paranoid→betrayal)" />
                    <ToggleRow k="resource_sharing_enabled" label="Resource sharing" title="a food store at the settlement: well-fed members deposit surplus, starving members withdraw; allies aid each other in famine" />
                    <ToggleRow k="tribute_enabled" label="Tribute" title="weak clans pay periodic tribute from their larder to a stronger protector" hideIfOff={['leader_decisions_enabled']} />
                    <ToggleRow k="betrayal_enabled" label="Betrayal" title="a leader breaks an alliance and strikes — the betrayed clan's rivals are told the same tale (treason)" hideIfOff="leader_decisions_enabled" />
                    <ToggleRow k="defection_enabled" label="Defection" title="unhappy members (starving/homeless) walk to a healthier nearby banner, even a rival's" />
                  </>
                )}
                {group === 'Desperation' && (
                  <>
                    <ToggleRow k="cannibalism_enabled" label="Cannibalism" title="the starving may hunt and eat living creatures — sated/hungry never do; cooldown between kills" />
                    <ToggleRow k="eat_enemy_enabled" label="Eat enemies" title="enemy-clan members (negative relation) and the weak (starving/elder/wounded) of any clan are legitimate prey; never predators, infants or indoor refugees" hideIfOff="cannibalism_enabled" />
                    <ToggleRow k="eat_kin_enabled" label="Eat kin" title="weak kin may be eaten too — at a terrible price: exile, stigma, and a clan that now counts you an enemy" hideIfOff="cannibalism_enabled" />
                    <ToggleRow k="exile_on_kin_eat" label="Exile on kin-eat" title="the kin-eater is cast out and founds a one-being outcast band; disabling keeps them in the clan but shunned" hideIfOff={['cannibalism_enabled', 'eat_kin_enabled']} />
                  </>
                )}
                {group === 'Food Decay' && (
                  <ToggleRow k="food_decay_enabled" label="Food decay" title="mature plants wither after their lifespan (× variant pace), fertilise nearby soil, then vanish — nothing lasts forever" />
                )}
                {group === 'Agriculture' && (
                  <>
                    <ToggleRow k="agriculture_enabled" label="Agriculture" title="seed pouches from wild harvests, cultivated farm plots near the settlement (2× growth, 2.5× yield), weeding & tending, irrigation furrows by fertile groves" />
                    <ToggleRow k="granaries_enabled" label="Granaries" title="a dry roofed store: sated harvesters lay grain & cured berries by (35%), starving members withdraw, feasts burn it" hideIfOff="agriculture_enabled" />
                    <ToggleRow k="soil_depletion_enabled" label="Living soil" title="monocropping exhausts the soil grid and slows regrowth; corpses, withered plants and farmer compost restore it" hideIfOff="agriculture_enabled" />
                    <ToggleRow k="banquets_enabled" label="Banquets" title="granary ≥80% feeds a feast: energy, cheer, warmer relations and +30% fertility while it lasts" hideIfOff="granaries_enabled" />
                  </>
                )}
                {group === 'Language & Diplomacy' && (
                  <>
                    <ToggleRow k="vocalizations_enabled" label="Caste voices & rituals" title="priest liturgy calms panic, women's peace-hum parts crowds, soldiers' war-chirps rally allies, artisan chimes gift basket food, touching vertices builds trust" />
                    <ToggleRow k="scent_enabled" label="Scent trails & markers" title="foragers drop breadcrumb trails home from rich finds; violent deaths and ruins leave danger scent the young learn to avoid" />
                    <ToggleRow k="envoys_enabled" label="Envoys & boundary stones" title="peaceful leaders send banner-carrying emissaries to rival houses; clans raise boundary stones that ring warning chimes at trespassers" />
                    <ToggleRow k="markets_enabled" label="Markets & caravans" title="allied neighbours found neutral trading posts at shared borders and barter surplus; peddler caravans carry goods and news between distant settlements" />
                    <ToggleRow k="omens_enabled" label="Season omens" title="at each season turn a shrine priest proclaims what comes; worshippers who hear it head home prepared" hideIfOff="theology_enabled" />
                    <ToggleRow k="dialect_drift_enabled" label="Dialect drift" title="isolated clans drift apart in speech; strangers understand each other less the further dialects split, allies converge on a shared tongue" />
                  </>
                )}
                {group === 'Theology' && (
                  <>
                    <ToggleRow k="theology_enabled" label="Theology of the Sphere" title="shrines beside main houses, dawn & dusk tithes fill the clan faith pool, the aura mends the faithful, seasonal miracles, law-change chimes & sermons, holy synods in crisis ages, temples at high faith" />
                    <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>
                      8 Sacred Avatars: ⭕ Abundance · ⚡ Wrath · 👁️ Omniscience · 🛡️ Permanence · 🌿 Renewal · ⚖️ Equilibrium · 🌀 Ascent · 🕯️ Sanctuary
                    </div>
                  </>
                )}
              </>
            )
            const rows = lawsInGroup.map(({ key, label, min, max, step }) => {
              const hint = LAW_HINTS[key]
              const isOpen = openHint === key
              return (
                <div key={key} style={{ borderBottom: '1px solid #30363d', padding: isOpen ? '8px 10px' : '6px 10px' }}>
                  <label className="god-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', gap: 8 }}>
                    <span style={{ display: 'flex', gap: 6, alignItems: 'center', flex: 1, minWidth: 0 }}>
                      <span title={hint} style={{ color: '#e6edf3', fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {label}
                      </span>
                      {hint && (
                        <button
                          type="button"
                          onClick={() => setOpenHint(isOpen ? null : key)}
                          title={hint}
                          style={{ width: 22, height: 22, borderRadius: '50%', border: '1px solid #484f58', background: isOpen ? '#30363d' : '#21262d', color: isOpen ? '#f0f6fc' : '#8b949e', fontSize: 12, lineHeight: 1, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}
                          aria-label={`hint for ${label}`}
                        >
                          ?
                        </button>
                      )}
                    </span>
                    {isMobile ? (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center', flex: 'none' }}>
                        <button
                          type="button"
                          onClick={() => stepVal(key, min, max, step, -1)}
                          style={{ minHeight: 30, height: 30, width: 30, padding: 0, fontSize: 16, fontWeight: 700, borderRadius: 6, background: '#21262d', border: '1px solid #484f58', color: '#f0f6fc', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}
                        >
                          -
                        </button>
                        <input
                          type="range"
                          min={min}
                          max={max}
                          step={step}
                          value={(laws[key] as number | undefined) ?? min}
                          onChange={(e) => set(key, e.target.value)}
                          style={{ width: 88, height: 24, accentColor: '#e3b341', cursor: 'pointer' }}
                        />
                        <button
                          type="button"
                          onClick={() => stepVal(key, min, max, step, 1)}
                          style={{ minHeight: 30, height: 30, width: 30, padding: 0, fontSize: 16, fontWeight: 700, borderRadius: 6, background: '#21262d', border: '1px solid #484f58', color: '#f0f6fc', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}
                        >
                          +
                        </button>
                        <span style={{ minWidth: 42, textAlign: 'right', fontSize: 12, fontWeight: 700, color: '#f0f6fc', fontVariantNumeric: 'tabular-nums' }}>
                          {(laws[key] as number | undefined)?.toFixed?.(step < 1 ? 2 : 0) ?? ''}
                        </span>
                      </span>
                    ) : (
                      <input
                        type="number"
                        min={min}
                        max={max}
                        step={step}
                        value={(laws[key] as number | undefined) ?? ''}
                        onChange={(e) => set(key, e.target.value)}
                      />
                    )}
                  </label>
                  {isOpen && hint && (
                    <div style={{ fontSize: 12, color: '#c9d1d9', background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '8px 10px', margin: '6px 0 4px', lineHeight: 1.45 }}>
                      {hint}
                      <div style={{ marginTop: 6 }}>
                        <a href="/docs/god-laws.md" rel="noreferrer" style={{ fontSize: 11, color: '#58a6ff' }}>Open docs/god-laws.md ↗</a>
                        {' · '}
                        <a href="/wiki#god-laws" style={{ fontSize: 11, color: '#58a6ff' }}>Wiki → God laws</a>
                      </div>
                    </div>
                  )}
                </div>
              )
            })
            return (
              <section key={group} className="god-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, borderBottom: '1px solid #30363d', paddingBottom: 6 }}>
                  <h3 style={{ margin: 0, fontSize: 13, color: '#e3b341', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{group}</h3>
                  <span style={{ fontSize: 10, color: '#8b949e', fontWeight: 600, background: '#21262d', padding: '1px 6px', borderRadius: 10, border: '1px solid #30363d' }}>
                    {lawsInGroup.length} laws
                  </span>
                </div>
                {special}
                {rows}
              </section>
            )
          })}

        </>
      )}
    </>
  )

  if (isMobile) {
    // Phone: the laws are their own full-screen page — big text, scrollable
    // body, sticky Apply/Save. No cramped sidebar, no backdrop squeeze.
    return (
      <div className="god-screen" role="dialog" aria-label="Laws of Nature">
        {head}
        <div className="god-screen-body">{body}</div>
        {foot}
      </div>
    )
  }
  return (
    <aside className="god-panel" onClick={e => e.stopPropagation()}>
      {head}
      {body}
      {foot}
    </aside>
  )
}
