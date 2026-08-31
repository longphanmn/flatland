import React, { useEffect, useMemo, useState } from 'react'
import { godFetch } from './auth'
import { useI18n } from '../i18n'
import type { GodLaws } from '../types'

class GodPanelErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  state = { hasError: false, error: null as any }
  static getDerivedStateFromError(error: any) { return { hasError: true, error } }
  componentDidCatch(error: any, info: any) { console.error('[GodPanel] crash', error, info) }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 16, color: '#f85149' }}>
          <h3 style={{ margin: '0 0 8px' }}>God Panel crashed</h3>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 11, background: '#161b22', padding: 8, borderRadius: 6, border: '1px solid #30363d' }}>{String(this.state.error?.message ?? this.state.error)}</pre>
          <button onClick={() => this.setState({ hasError: false, error: null })} style={{ marginTop: 8, padding: '6px 10px', background: '#21262d', border: '1px solid #30363d', borderRadius: 6, color: '#e6edf3', cursor: 'pointer' }}>Retry</button>
        </div>
      )
    }
    return this.props.children
  }
}

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
  gate?: BoolLawKey | BoolLawKey[]
}

const NUMBER_LAWS: LawSpec[] = [
  // Ecology & Survival
  { key: 'food_count', label: 'Food abundance', min: 0, max: 1000, step: 5, group: 'Food & Energy' },
  { key: 'energy_max', label: 'Max energy', min: 10, max: 500, step: 5, group: 'Food & Energy' },
  { key: 'energy_decay_per_tick', label: 'Energy decay / tick', min: 0, max: 2, step: 0.01, group: 'Food & Energy' },
  { key: 'energy_from_food', label: 'Energy from food', min: 0, max: 100, step: 1, group: 'Food & Energy' },
  { key: 'plant_growth_rate', label: 'Plant growth / tick', min: 0, max: 1, step: 0.01, group: 'Ecosystem' },
  { key: 'plant_spread_rate', label: 'Plant spread chance', min: 0, max: 1, step: 0.005, group: 'Ecosystem' },
  { key: 'nutrient_cycle_rate', label: 'Nutrient cycle ×', min: 0, max: 10, step: 0.1, group: 'Ecosystem' },
  { key: 'poison_rate', label: 'Poison sprout chance', min: 0, max: 1, step: 0.01, group: 'Ecosystem', gate: 'plant_variants_enabled' },
  { key: 'food_lifespan_ticks', label: 'Food lifespan (ticks)', min: 100, max: 100000, step: 100, group: 'Food Decay', gate: 'food_decay_enabled' },
  { key: 'granary_capacity', label: 'Granary capacity', min: 0, max: 2000, step: 25, group: 'Agriculture', gate: 'granaries_enabled' },
  { key: 'perceive_radius', label: 'Base sight radius', min: 1, max: 40, step: 0.5, group: 'Hunger & Sight' },
  { key: 'eat_radius', label: 'Eat radius', min: 0.2, max: 5, step: 0.1, group: 'Hunger & Sight' },
  { key: 'hungry_ratio', label: 'Hungry threshold (NN slot 0)', min: 0.05, max: 1, step: 0.05, group: 'Hunger & Sight' },
  { key: 'starving_ratio', label: 'Starving threshold', min: 0.01, max: 1, step: 0.01, group: 'Hunger & Sight' },

  // Biology & Evolution
  { key: 'steer_turn', label: 'Turning agility', min: 0.05, max: 2, step: 0.05, group: 'Movement' },
  { key: 'lifespan_mult', label: 'Lifespan ×', min: 0.05, max: 5, step: 0.05, group: 'Life & Death' },
  { key: 'birth_rate', label: 'Birth rate', min: 0, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'carrying_capacity', label: 'Carrying capacity', min: -1, max: 5000, step: 25, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'max_population', label: 'Hard pop cap', min: -1, max: 8000, step: 25, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'mutation_rate', label: 'Caste mutation rate', min: 0, max: 1, step: 0.01, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'sex_ratio', label: 'Son probability', min: 0, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'adult_age', label: 'Adult age', min: 0, max: 5000, step: 50, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'max_sides', label: 'Max caste sides', min: 3, max: 64, step: 1, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'euthanasia_threshold', label: 'Euthanasia ≥', min: 0.3, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'mutation_sigma', label: 'NN mutation σ', min: 0, max: 0.5, step: 0.01, group: 'Neuroevolution' },
  { key: 'crossover_rate', label: 'NN crossover rate', min: 0, max: 1, step: 0.05, group: 'Neuroevolution' },
  { key: 'annealing_decay_generations', label: 'Morphology decay gens', min: 1, max: 5000, step: 10, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'disease_outbreak_rate', label: 'Outbreak rate / tick', min: 0, max: 0.05, step: 0.0005, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_rate', label: 'Contagion chance', min: 0, max: 1, step: 0.01, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_energy_drain', label: 'Energy drain / tick', min: 0, max: 2, step: 0.05, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_lethality', label: 'Lethality', min: 0, max: 1, step: 0.05, group: 'Disease', gate: 'disease_enabled' },

  // Climate & Sky
  { key: 'day_length', label: 'Day length (ticks)', min: 4, max: 20000, step: 4, group: 'Sky & Seasons' },
  { key: 'season_length', label: 'Season length (ticks)', min: 4, max: 100000, step: 10, group: 'Sky & Seasons' },
  { key: 'winter_food_mult', label: 'Winter food ×', min: 0.1, max: 1.5, step: 0.05, group: 'Sky & Seasons' },
  { key: 'night_sight_mult', label: 'Night sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'weather_change_rate', label: 'Weather turn chance', min: 0, max: 1, step: 0.001, group: 'Sky & Seasons', gate: 'weather_enabled' },
  { key: 'exposure_drain', label: 'Exposure drain / tick', min: 0, max: 2, step: 0.05, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'house_capacity', label: 'House capacity', min: 1, max: 20, step: 1, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'house_decay_ticks', label: 'House decay ticks', min: 100, max: 100000, step: 100, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'rest_recovery_mult', label: 'Rest healing ×', min: 0.5, max: 5, step: 0.25, group: 'Shelter', gate: 'shelter_enabled' },
  { key: 'chill_drain', label: 'Chill drain / tick', min: 0, max: 5, step: 0.05, group: 'Weather Sickness', gate: 'weather_sickness_enabled' },

  // Society, Warfare & Trade
  { key: 'territory_radius', label: 'Territory radius', min: 1, max: 50, step: 1, group: 'Territory', gate: 'territory_enabled' },
  { key: 'trespass_decay', label: 'Trespass decay / tick', min: 0, max: 5, step: 0.05, group: 'Territory', gate: 'territory_enabled' },
  { key: 'max_clans', label: 'Max clans', min: -1, max: 24, step: 1, group: 'Clan' },
  { key: 'larder_capacity', label: 'Larder capacity', min: 0, max: 2000, step: 25, group: 'Politics', gate: 'resource_sharing_enabled' },
  { key: 'coalition_threshold', label: 'Coalition threshold', min: -100, max: 100, step: 5, group: 'Politics', gate: 'coalitions_enabled' },
  { key: 'schism_threshold', label: 'Schism threshold', min: 0, max: 1, step: 0.05, group: 'Rebellion', gate: 'schism_enabled' },
  { key: 'predator_ratio', label: 'Predator ratio', min: 0, max: 1, step: 0.01, group: 'Predation', gate: 'predation_enabled' },
  { key: 'hunt_radius', label: 'Hunt radius', min: 1, max: 40, step: 1, group: 'Predation', gate: 'predation_enabled' },
  { key: 'bite_damage', label: 'Bite damage', min: 0, max: 200, step: 10, group: 'Predation', gate: 'predation_enabled' },
  { key: 'energy_from_prey', label: 'Energy from prey', min: 0, max: 200, step: 5, group: 'Predation', gate: 'predation_enabled' },
  { key: 'fear_radius', label: 'Fear radius', min: 1, max: 40, step: 1, group: 'Predation', gate: 'predation_enabled' },
  { key: 'attack_damage', label: 'Attack damage', min: 0, max: 200, step: 10, group: 'Clan War', gate: 'war_enabled' },
  { key: 'cannibalism_energy', label: 'Energy per kill', min: 0, max: 200, step: 5, group: 'Desperation', gate: 'cannibalism_enabled' },

  // Theology & Sacred Avatars
  { key: 'tithe_rate', label: 'Tithe rate', min: 0, max: 0.5, step: 0.01, group: 'Theology', gate: 'theology_enabled' },
  { key: 'temple_faith_cost', label: 'Temple faith cost', min: 50, max: 5000, step: 50, group: 'Theology', gate: 'theology_enabled' },
  { key: 'age_length', label: 'Age length (ticks)', min: 100, max: 1000000, step: 100, group: 'Ages', gate: 'age_enabled' },
  { key: 'culture_spread_rate', label: 'Culture spread / tick', min: 0, max: 1, step: 0.0005, group: 'Culture', gate: 'culture_enabled' },

  // World Physics & Disasters
  { key: 'fire_rate', label: 'Fire ignite / tick', min: 0, max: 0.05, step: 0.0001, group: 'Wildfire & Disasters', gate: 'wildfire_enabled' },
  { key: 'disaster_rate', label: 'Disaster / tick', min: 0, max: 0.05, step: 0.0001, group: 'Wildfire & Disasters', gate: 'disaster_enabled' },
  { key: 'river_count', label: 'River count', min: 0, max: 8, step: 1, group: 'Rivers', gate: 'rivers_enabled' },
  { key: 'earthquake_rate', label: 'Quake rate / tick', min: 0, max: 0.001, step: 0.00001, group: 'Seismic & Waves', gate: 'earthquake_enabled' },
  { key: 'lightning_strike_rate', label: 'Bolt rate / storm tick', min: 0, max: 0.02, step: 0.0005, group: 'Electrostatics', gate: 'lightning_enabled' },
  { key: 'anomaly_count', label: 'Anomaly zones', min: 0, max: 8, step: 1, group: 'Cosmology' },
  { key: 'door_clearance', label: 'Door clearance ×', min: 1, max: 4, step: 0.1, group: 'Bodies & Houses' },
]

/* 6 Macro Domains — BD.8.1 */
interface DomainSpec { id: string; icon: string; label: string; shortLabel: string; groups: string[] }
const DOMAINS: DomainSpec[] = [
  { id: 'ecology', icon: '🌿', label: 'Ecology & Survival', shortLabel: 'Ecology', groups: ['Food & Energy', 'Ecosystem', 'Hunger & Sight', 'Food Decay', 'Agriculture'] },
  { id: 'biology', icon: '🧬', label: 'Biology & Evolution', shortLabel: 'Biology', groups: ['Movement', 'Life & Death', 'Reproduction', 'Disease', 'Neuroevolution', 'Morphology', 'Predation'] },
  { id: 'climate', icon: '☀️', label: 'Climate & Sky', shortLabel: 'Climate', groups: ['Sky & Seasons', 'Weather Sickness', 'Shelter'] },
  { id: 'society', icon: '🏰', label: 'Society, Warfare & Trade', shortLabel: 'Society', groups: ['Territory', 'Clan', 'Communication', 'Rebellion', 'Clan War', 'Politics', 'Desperation'] },
  { id: 'theology', icon: '🔮', label: 'Theology & Sacred Avatars', shortLabel: 'Theology', groups: ['Theology', 'Culture', 'Ages'] },
  { id: 'physics', icon: '⚙️', label: 'World Physics & Disasters', shortLabel: 'Physics', groups: ['Bodies & Houses', 'Rivers', 'Terrain', 'Materials', 'Seismic & Waves', 'Electrostatics', 'Cosmology', 'Wildfire & Disasters'] },
]

const GROUP_KEY: Record<string, string> = {
  'Food & Energy': 'foodEnergy',
  'Ecosystem': 'ecosystem',
  'Hunger & Sight': 'hungerSight',
  'Movement': 'movement',
  'Life & Death': 'lifeDeath',
  'Reproduction': 'reproduction',
  'Disease': 'disease',
  'Sky & Seasons': 'skySeasons',
  'Ages': 'ages',
  'Culture': 'culture',
  'Wildfire & Disasters': 'wildfire',
  'Weather Sickness': 'weatherSickness',
  'Shelter': 'shelter',
  'Territory': 'territory',
  'Clan': 'clan',
  'Communication': 'communication',
  'Rebellion': 'rebellion',
  'Predation': 'predation',
  'Clan War': 'clanWar',
  'Politics': 'politics',
  'Desperation': 'desperation',
  'Food Decay': 'foodDecay',
  'Agriculture': 'agriculture',
  'Theology': 'theology',
  'Bodies & Houses': 'bodiesHouses',
  'Rivers': 'rivers',
  'Terrain': 'terrain',
  'Materials': 'materials',
  'Seismic & Waves': 'seismic',
  'Electrostatics': 'electrostatics',
  'Cosmology': 'cosmology',
  'Neuroevolution': 'neuroevolution',
  'Morphology': 'morphology',
}

const BOOL_DEFAULTS: Partial<Record<BoolLawKey, boolean>> = {
  birth_enabled: true,
  disease_enabled: false,
  weather_enabled: true,
  sleep_enabled: true,
  shelter_enabled: true,
  weather_sickness_enabled: false,
  territory_enabled: true,
  totems_enabled: true,
  succession_enabled: true,
  communication_enabled: true,
  knowledge_enabled: true,
  wildfire_enabled: false,
  disaster_enabled: false,
  culture_enabled: false,
  age_enabled: true,
  schism_enabled: true,
  plant_variants_enabled: true,
  predation_enabled: false,
  war_enabled: true,
  coalitions_enabled: true,
  leader_decisions_enabled: true,
  resource_sharing_enabled: true,
  cannibalism_enabled: true,
  eat_kin_enabled: true,
  food_decay_enabled: true,
  theology_enabled: true,
  agriculture_enabled: true,
  granaries_enabled: true,
  rivers_enabled: true,
  relief_enabled: true,
  structural_enabled: true,
  earthquake_enabled: false,
  lightning_enabled: true,
  morphology_annealing_enabled: false,
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
  nn_inference_hz: 'NN inference frequency per second (15) — 60Hz physics, 15Hz brain, rest latched',
  mutation_sigma: 'Gaussian mutation σ for genome (0.08) — per-gene noise on crossover',
  crossover_rate: 'crossover rate (0.5) — uniform 50/50 parent blend; higher = more mixing',
  morphology_annealing_enabled: 'master switch for geometric physics — off keeps classic sides, on enables polar (r,φ) annealing BC',
  annealing_start_generation: 'generation where λ starts decaying 1→0 (50) — before, children snap to Abbott templates',
  annealing_decay_generations: 'generations to decay λ 1→0 (150) — short = instant morph freedom',
  morph_lambda_override: 'force λ 0..1 (empty=auto); 1 freezes Abbott, 0 pure parental (BC)',
  vertex_mutation_std: 'radial mutation σ for r_i (0.05) — per-vertex Gaussian [0.2,2.5]',
  angle_mutation_std: 'angular mutation σ for φ (0.02) — sorted circularly to avoid bow-tie',
  topological_mutation_rate: 'topological p·(1-λ) (0.01) — add longest edge / remove closest neighbor, K 3..64',
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

function Switch({ checked, onChange, title }: { checked: boolean; onChange: (v: boolean) => void; title?: string }) {
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

interface Props { open: boolean; onClose: () => void }

const PRESET_META: Record<string, { color: string; border: string; bg: string; badge?: string }> = {
  balance: { color: '#e3b341', border: '#d29922', bg: 'rgba(227, 179, 65, 0.15)', badge: 'DEFAULT' },
  sustainable: { color: '#3fb950', border: '#2ea043', bg: 'rgba(63, 185, 80, 0.15)' },
  theocracy: { color: '#bc8cff', border: '#a371f7', bg: 'rgba(188, 140, 255, 0.15)' },
  warlords: { color: '#f0883e', border: '#d26a1b', bg: 'rgba(240, 136, 62, 0.15)' },
  chaos: { color: '#f85149', border: '#da3633', bg: 'rgba(248, 81, 73, 0.15)' },
  extinction: { color: '#ff7b72', border: '#f85149', bg: 'rgba(255, 123, 114, 0.15)' },
  boom: { color: '#79c0ff', border: '#388bfd', bg: 'rgba(121, 192, 255, 0.15)' },
}

const PRESET_BADGES: Record<string, string[]> = {
  balance: ['Food: 240', 'Winter: 0.72×', 'Cap: 350'],
  sustainable: ['Food: 360 (Abundant)', 'Winter: 0.78×', 'Cap: 450'],
  theocracy: ['Food: 320 (Faith)', 'Winter: 0.75×', 'Temple: 180'],
  warlords: ['Food: 290 (War)', 'Winter: 0.65×', 'Damage: 50'],
  chaos: ['Food: 280 (Scarce)', 'Winter: 0.50× (Harsh)', 'Disease: 1.8×'],
  extinction: ['Food: 120 (Harsh)', 'Winter: 0.30× (Cold)', 'Pop: 180'],
  boom: ['Food: 500 (Boom)', 'Winter: 0.85×', 'Cap: 800'],
}

const PRESET_IMPACT: Record<string, string> = {
  balance: '⚖ Stable equilibrium — all 15+ mechanics harmonized',
  sustainable: '🌿 Flourishing growth — rich fields, full granaries, calm winters',
  theocracy: '🔮 Divine devotion — miracles, temples & sacred resonance',
  warlords: '⚔️ Martial age — conquests, alliances & plundered larders',
  chaos: '🔥 Turmoil — predators, plague, fire & quakes test survival',
  extinction: '💀 Collapse — famine, chill & cannibalism cull the weak',
  boom: '🚀 Metropolis — rapid births, bumper harvests & grand settlements',
}

function detectPreset(laws: GodLaws): string | null {
  if (laws.food_count === 240 && laws.carrying_capacity === 350) return 'balance'
  if (laws.food_count === 360 && laws.carrying_capacity === 450) return 'sustainable'
  if (laws.food_count === 320 && laws.carrying_capacity === 400) return 'theocracy'
  if (laws.food_count === 290 && laws.carrying_capacity === 380) return 'warlords'
  if (laws.food_count === 280 && laws.carrying_capacity === 350) return 'chaos'
  if (laws.food_count === 320 && laws.carrying_capacity === 800) return 'chaos'
  if (laws.food_count === 120 && laws.carrying_capacity === 180) return 'extinction'
  if (laws.food_count === 100 && laws.carrying_capacity === 250) return 'extinction'
  if (laws.food_count === 500 && laws.carrying_capacity === 800) return 'boom'
  if (laws.food_count === 650 && laws.carrying_capacity === 3500) return 'boom'
  return null
}

function getZone(value: number, baseline: number | undefined, min: number, max: number): 'safe' | 'strained' | 'extreme' {
  if (baseline === undefined || baseline === null) return 'safe'
  const range = max - min
  if (range === 0) return 'safe'
  const dist = Math.abs(value - baseline) / range
  if (dist < 0.15) return 'safe'
  if (dist < 0.32) return 'strained'
  return 'extreme'
}

function GodPanelInner({ open, onClose }: Props) {
  const { t } = useI18n()
  const [laws, setLaws] = useState<GodLaws>({})
  const [baselineLaws, setBaselineLaws] = useState<GodLaws>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPreset, setCurrentPreset] = useState<string | null>('balance')
  const [expandedPreset, setExpandedPreset] = useState<string | null>('balance')
  const [activeSection, setActiveSection] = useState<'presets' | 'laws'>(() => {
    try { return (sessionStorage.getItem('god-section') as 'presets' | 'laws') || 'presets' } catch { return 'presets' }
  })
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768)
  const [searchQuery, setSearchQuery] = useState('')
  const [showModifiedOnly, setShowModifiedOnly] = useState(false)
  const [openHint, setOpenHint] = useState<string | null>(null)
  const [activeDomain, setActiveDomain] = useState<string>(() => {
    try { return sessionStorage.getItem('god-domain') || 'ecology' } catch { return 'ecology' }
  })

  useEffect(() => {
    try { sessionStorage.setItem('god-section', activeSection) } catch { /* ignore */ }
  }, [activeSection])

  useEffect(() => {
    try { sessionStorage.setItem('god-domain', activeDomain) } catch { /* ignore */ }
  }, [activeDomain])

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
        setBaselineLaws(lawsData)
        const detected = presetsData?.current || detectPreset(lawsData) || 'balance'
        setCurrentPreset(detected)
        setExpandedPreset(detected)
      })
      .catch(() => setError('failed to load laws'))
      .finally(() => setLoading(false))
  }, [open])

  if (!open) return null

  const set = (key: NumberLawKey, raw: string | number) => {
    const val = raw === '' ? undefined : Number(raw)
    setLaws((l) => {
      const updated = { ...l, [key]: val }
      setCurrentPreset(detectPreset(updated))
      return updated
    })
  }

  const revertOne = (key: NumberLawKey) => {
    const base = (baselineLaws as any)[key]
    if (base === undefined) return
    setLaws((l) => ({ ...l, [key]: base }))
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

  const modifiedKeys = useMemo(() => {
    const set = new Set<string>()
    for (const spec of NUMBER_LAWS) {
      const cur = (laws as any)[spec.key]
      const base = (baselineLaws as any)[spec.key]
      if (cur !== undefined && base !== undefined && cur !== base) set.add(spec.key)
      else if ((cur === undefined) !== (base === undefined) && cur !== base) set.add(spec.key)
    }
    // also boolean toggles count as modified for N badge
    for (const k of Object.keys(BOOL_DEFAULTS) as BoolLawKey[]) {
      if ((laws as any)[k] !== undefined && (laws as any)[k] !== (baselineLaws as any)[k]) set.add(k)
    }
    return set
  }, [laws, baselineLaws])

  const q = searchQuery.trim().toLowerCase()
  const matchesSearch = (spec: LawSpec): boolean => {
    if (!q) return true
    const hint = (LAW_HINTS[spec.key] || '').toLowerCase()
    const label = spec.label.toLowerCase()
    const group = spec.group.toLowerCase()
    const key = spec.key.toLowerCase()
    return label.includes(q) || hint.includes(q) || group.includes(q) || key.includes(q)
  }

  const filteredSpecs = (specs: LawSpec[]) => {
    let out = specs.filter((s) => gateOpen(s.gate))
    out = out.filter(matchesSearch)
    if (showModifiedOnly) out = out.filter((s) => modifiedKeys.has(s.key))
    return out
  }

  const ToggleRow = ({ k, label, title, hideIfOff }: { k: BoolLawKey; label: string; title?: string; hideIfOff?: BoolLawKey | BoolLawKey[] }) => {
    if (hideIfOff && !gateOpen(hideIfOff)) return null
    // Apply modified filter: hide if modifiedOnly and not modified
    if (showModifiedOnly && !modifiedKeys.has(k)) {
      // also check search query for toggles
      if (q) {
        const trLabel2 = (t(`godToggles.${k}`) !== `godToggles.${k}` ? t(`godToggles.${k}`) : label).toLowerCase()
        const trTitle2 = (t(`godToggles.${k}Hint`) !== `godToggles.${k}Hint` ? t(`godToggles.${k}Hint`) : (title || '')).toLowerCase()
        if (!trLabel2.includes(q) && !trTitle2.includes(q) && !k.includes(q)) return null
      } else return null
    }
    if (q) {
      const trLabel2 = (t(`godToggles.${k}`) !== `godToggles.${k}` ? t(`godToggles.${k}`) : label).toLowerCase()
      const trTitle2 = (t(`godToggles.${k}Hint`) !== `godToggles.${k}Hint` ? t(`godToggles.${k}Hint`) : (title || '')).toLowerCase()
      if (!trLabel2.includes(q) && !trTitle2.includes(q) && !k.includes(q)) return null
    }
    const trLabel = t(`godToggles.${k}`) !== `godToggles.${k}` ? t(`godToggles.${k}`) : label
    const trTitle = t(`godToggles.${k}Hint`) !== `godToggles.${k}Hint` ? t(`godToggles.${k}Hint`) : title
    const isMod = modifiedKeys.has(k)
    return (
      <div className="god-row god-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, borderBottom: '1px solid #21262d', padding: '8px 10px', background: isMod ? 'rgba(227,179,65,0.06)' : undefined, borderLeft: isMod ? '2px solid #d29922' : '2px solid transparent' }}>
        <span title={trTitle} style={{ color: isMod ? '#e3b341' : '#e6edf3', fontSize: 13, fontWeight: isMod ? 600 : 500, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          {trLabel}
          {isMod && <span style={{ fontSize: 9, padding: '1px 4px', borderRadius: 4, background: '#d29922', color: '#0d1117', fontWeight: 800 }}>MOD</span>}
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          {isMod && <button onClick={() => setBool(k, (baselineLaws as any)[k] ?? BOOL_DEFAULTS[k] ?? false)} title="Revert to preset" style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: '#21262d', border: '1px solid #484f58', color: '#c9d1d9', cursor: 'pointer' }}>↺ Revert</button>}
          <Switch checked={boolVal(k)} onChange={(v) => setBool(k, v)} title={trTitle ?? trLabel} />
        </span>
      </div>
    )
  }

  const postLaws = async (persist: boolean, reset: boolean = false) => {
    setError(null)
    setSaved(false)
    setSubmitting(true)
    try {
      const qs = `?persist=${persist ? 'true' : 'false'}${reset ? '&reset=true' : ''}`
      const res = await godFetch(`/api/laws${qs}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(laws),
      })
      const body = await res.json().catch(() => null)
      if (!res.ok) {
        throw new Error(
          typeof body?.detail === 'string'
            ? body.detail
            : (body?.detail?.[0]?.msg ?? 'law rejected'),
        )
      }
      const lawsData = body?.laws ?? body
      setLaws(lawsData)
      setBaselineLaws(lawsData)
      setCurrentPreset(detectPreset(lawsData))
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
  const applyAndReset = () => postLaws(true, true)
  const selectPreset = (name: string) => {
    setExpandedPreset(name)
    setCurrentPreset(name)
    fetch('/api/presets')
      .then((r) => r.json())
      .then((data) => {
        if (data.details?.[name]) {
          setLaws((prev) => ({ ...prev, ...data.details[name] }))
        }
      })
      .catch(() => {})
  }
  const applyPreset = async (name: string, reset: boolean) => {
    setError(null)
    setSaved(false)
    setSubmitting(true)
    try {
      const res = await godFetch(`/api/presets/${name}?persist=true${reset ? '&reset=true' : ''}`, { method: 'POST' })
      const body = await res.json().catch(() => null)
      if (!res.ok) {
        throw new Error(
          typeof body?.detail === 'string'
            ? body.detail
            : (body?.detail?.[0]?.msg ?? 'preset failed'),
        )
      }
      setLaws(body.laws ?? body)
      setBaselineLaws(body.laws ?? body)
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
    <footer
      className="god-foot"
      style={{
        display: 'flex',
        gap: 6,
        flexWrap: 'wrap',
        alignItems: 'center',
        position: 'sticky',
        bottom: 0,
        background: '#0d1117',
        padding: '10px 0 max(10px, env(safe-area-inset-bottom))',
        borderTop: '1px solid #21262d',
        zIndex: 1,
      }}
    >
      {error && <span className="god-error">{error}</span>}
      {!error && saved && <span className="god-saved">{t('god.presets.saved')}</span>}
      {!error && !saved && submitting && <span className="god-note" style={{ color: '#d29922' }}>{t('god.presets.applying')}</span>}
      <button
        onClick={apply}
        disabled={submitting}
        title={t('god.footer.applyDesc')}
        style={{ minHeight: isMobile ? 44 : undefined, touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent' as any }}
      >
        Apply
      </button>
      <button
        onClick={save}
        disabled={submitting}
        title={t('god.footer.saveDesc')}
        className="god-save"
        style={{ minHeight: isMobile ? 44 : undefined, touchAction: 'manipulation', WebkitTapHighlightColor: 'transparent' as any }}
      >{t('god.footer.save')}
      </button>
      <button
        onClick={applyAndReset}
        disabled={submitting}
        title={t('god.footer.applyResetDesc')}
        style={{
          background: '#238636',
          borderColor: '#2ea043',
          color: '#fff',
          fontWeight: 600,
          padding: isMobile ? '10px 12px' : '4px 10px',
          borderRadius: 6,
          cursor: 'pointer',
          minHeight: isMobile ? 44 : undefined,
          touchAction: 'manipulation',
          WebkitTapHighlightColor: 'transparent' as any,
        }}
      >{t('god.footer.applyReset')}
      </button>
    </footer>
  )

  const head = (
    <header className="god-head">
      <h2>{t('god.title')}</h2>
      <button className="god-close" onClick={onClose} aria-label="close">
        ×
      </button>
    </header>
  )

  const activePresetMeta = currentPreset ? (PRESET_META as any)[currentPreset] : null
  const presetKeys = ['balance','sustainable','theocracy','warlords','chaos','extinction','boom'] as const

  // law count helpers
  const domainLawCounts = useMemo(() => {
    const m: Record<string, number> = {}
    for (const d of DOMAINS) {
      let c = 0
      for (const g of d.groups) c += NUMBER_LAWS.filter(s => s.group === g && gateOpen(s.gate)).length
      m[d.id] = c
    }
    return m
  }, [laws, gateOpen])

  const body = (
    <>
      <p className="god-note">{t('god.subtitle')}</p>

      {/* Top Section Navigator: Presets vs Laws of Nature */}
      <div className="god-section-nav" role="tablist" aria-label="God panel sections">
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'presets'}
          className={`god-section-btn ${activeSection === 'presets' ? 'active' : ''}`}
          onClick={() => setActiveSection('presets')}
        >
          <span className="god-section-icon">🎯</span>
          <span>{t('god.presets.title')}</span>
          <span className="god-section-badge">{presetKeys.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'laws'}
          className={`god-section-btn ${activeSection === 'laws' ? 'active' : ''}`}
          onClick={() => setActiveSection('laws')}
        >
          <span className="god-section-icon">⚖️</span>
          <span>{t('god.title')}</span>
          <span className="god-section-badge">{NUMBER_LAWS.length}</span>
        </button>
      </div>

      {activeSection === 'presets' && (
        <div className="god-group" style={{ display: 'flex', flexDirection: 'column', gap: 10, border: 'none', padding: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: 2 }}>
            <span style={{ fontSize: 12, color: '#8b949e', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Curated World Presets
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
              {activePresetMeta && currentPreset ? `${t('god.presets.active', { name: t(`god.presets.${currentPreset}`) })}` : t('god.presets.custom')}
            </span>
          </div>

          <div className="god-preset-grid">
            {presetKeys.map((key) => {
              const meta = PRESET_META[key as keyof typeof PRESET_META]
              const label = t(`god.presets.${key}`)
              const subtitle = t(`god.presets.${key}Subtitle`)
              const description = t(`god.presets.${key}Desc`)
              const badges = PRESET_BADGES[key] || []
              const impact = PRESET_IMPACT[key] || ''
              const { color, border, bg, badge } = meta as any
              const isActive = currentPreset === key
              const isExpanded = expandedPreset === key
              return (
                <div
                  key={key}
                  onClick={() => selectPreset(key)}
                  className="god-preset-card"
                  data-active={isActive ? 'true' : 'false'}
                  data-expanded={isExpanded ? 'true' : 'false'}
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
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: isActive ? color : '#e6edf3' }}>{label}</span>
                      <span style={{ fontSize: 11, color: '#8b949e', fontStyle: 'italic' }}>({subtitle})</span>
                    </div>
                    <div style={{ display: 'flex', gap: 4, flex: 'none' }}>
                      {badge && (
                        <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 4, background: '#d29922', color: '#0d1117', fontWeight: 800 }}>
                          {badge}
                        </span>
                      )}
                      {isActive && (
                        <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: color, color: '#0d1117', fontWeight: 800 }}>
                          ● ACTIVE
                        </span>
                      )}
                    </div>
                  </div>

                  <p style={{ fontSize: 12, color: '#c9d1d9', margin: 0, lineHeight: 1.4 }}>
                    {description}
                  </p>
                  <p style={{ fontSize: 11, color: '#8b949e', margin: 0, lineHeight: 1.3, fontStyle: 'italic' }}>{impact}</p>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 2 }}>
                    {badges.map((b) => (
                      <span key={b} className="god-preset-badge" style={{ fontSize: 10, padding: '2px 7px', borderRadius: 10, background: isActive ? 'rgba(0,0,0,0.25)' : '#21262d', color: isActive ? color : '#8b949e', border: `1px solid ${isActive ? border : '#30363d'}`, fontWeight: 600 }}>
                        {b}
                      </span>
                    ))}
                  </div>

                  <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        applyPreset(key, false)
                      }}
                      title={`Apply ${label} laws live`}
                      className="god-preset-apply"
                      style={{
                        flex: 1,
                        padding: isMobile ? '10px 8px' : '6px 8px',
                        fontSize: 11,
                        fontWeight: 600,
                        background: '#21262d',
                        borderColor: isActive ? border : '#30363d',
                        color: isActive ? color : '#c9d1d9',
                        borderRadius: 6,
                        cursor: 'pointer',
                        minHeight: isMobile ? 44 : undefined,
                        touchAction: 'manipulation',
                        WebkitTapHighlightColor: 'transparent',
                      }}
                    >
                      ⚡ Apply Live
                    </button>
                    <button
                      type="button"
                      disabled={submitting}
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        applyPreset(key, true)
                      }}
                      title={`Apply ${label} + reset world`}
                      className="god-preset-reset"
                      style={{
                        flex: 1,
                        padding: isMobile ? '10px 8px' : '6px 8px',
                        fontSize: 11,
                        fontWeight: 700,
                        background: '#238636',
                        borderColor: '#2ea043',
                        color: '#fff',
                        borderRadius: 6,
                        cursor: 'pointer',
                        minHeight: isMobile ? 44 : undefined,
                        touchAction: 'manipulation',
                        WebkitTapHighlightColor: 'transparent',
                      }}
                    >
                      🔄 Apply & Reset
                    </button>
                  </div>
                  {isActive && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        setActiveSection('laws')
                      }}
                      style={{
                        marginTop: 2,
                        padding: '5px 8px',
                        fontSize: 11,
                        fontWeight: 600,
                        background: 'transparent',
                        border: '1px dashed #484f58',
                        color: '#58a6ff',
                        borderRadius: 6,
                        cursor: 'pointer',
                        textAlign: 'center',
                      }}
                    >
                      🛠️ Customise laws for {label} ➔
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {activeSection === 'laws' && (
        <>
          {loading ? (
            <p className="god-note">{t('god.presets.loading' as any) || 'reading the tablets…'}</p>
          ) : (
            <>
              {/* Active Preset Status Ribbon */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 10px', background: '#161b22', border: '1px solid #30363d', borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, color: '#8b949e' }}>Baseline:</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: activePresetMeta ? activePresetMeta.color : '#e6edf3' }}>
                    {activePresetMeta && currentPreset ? t(`god.presets.${currentPreset}`) : 'Custom'}
                  </span>
                  {modifiedKeys.size > 0 && (
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 6, background: 'rgba(227,179,65,0.18)', color: '#e3b341', fontWeight: 700 }}>
                      {modifiedKeys.size} modified
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveSection('presets')}
                  style={{ fontSize: 11, color: '#58a6ff', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, fontWeight: 600 }}
                >
                  🎯 Switch Preset ➔
                </button>
              </div>

              {/* Law Search & Modified Filter — BD.8.2 */}
              <div className="god-search-bar">
                <div className="god-search-input-wrap">
                  <span className="god-search-icon">🔍</span>
                  <input
                    className="god-search-input"
                    type="text"
                    placeholder="Search laws… (e.g. food, winter, disease, food_count)"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button className="god-search-clear" onClick={() => setSearchQuery('')} title="Clear search">×</button>
                  )}
                </div>
                <button
                  className={`god-filter-btn ${showModifiedOnly ? 'active' : ''}`}
                  onClick={() => setShowModifiedOnly(!showModifiedOnly)}
                  title="Show only laws that differ from preset baseline"
                >
                  {showModifiedOnly ? '✓ ' : ''}Show Modified Only ({modifiedKeys.size})
                </button>
                {showModifiedOnly && modifiedKeys.size > 0 && (
                  <button
                    className="god-revert-all"
                    onClick={() => setLaws({ ...baselineLaws })}
                    title="Revert all modified laws to baseline"
                  >
                    ↺ Revert All
                  </button>
                )}
              </div>

              <label className="god-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', borderBottom: '1px solid #30363d', background: modifiedKeys.has('boundary' as any) ? 'rgba(227,179,65,0.06)' : undefined, borderLeft: (modifiedKeys.has('boundary' as any) ? '2px solid #d29922' : '2px solid transparent') }}>
                <span title={t('godToggles.edgeHint' as any) || 'what happens at the edge of the world'} style={{ color: '#e6edf3', fontSize: 13, fontWeight: 500 }}>{t('godToggles.edgeOfWorld' as any) || 'Edge of world'}</span>
                <select
                  value={laws.boundary ?? 'wrap'}
                  onChange={(e) =>
                    setLaws((l) => ({ ...l, boundary: e.target.value as 'wrap' | 'clamp' }))
                  }
                  style={{ minHeight: 32, padding: '4px 8px' }}
                >
                  <option value="wrap">{t('god.edge.wrap')}</option>
                  <option value="clamp">{t('god.edge.walls')}</option>
                </select>
              </label>

              {/* Domain tabs — BD.8.1 */}
              {!q && !showModifiedOnly && (
                <nav className="god-domain-tabs" role="tablist" aria-label="Law domains">
                  {DOMAINS.map((d) => (
                    <button
                      key={d.id}
                      role="tab"
                      aria-selected={activeDomain === d.id}
                      className={`god-domain-tab ${activeDomain === d.id ? 'active' : ''}`}
                      onClick={() => setActiveDomain(d.id)}
                      title={`${d.label} — ${d.groups.join(', ')}`}
                    >
                      <span className="god-domain-icon">{d.icon}</span>
                      <span className="god-domain-label">{d.shortLabel}</span>
                      <span className="god-domain-count">{domainLawCounts[d.id] ?? 0}</span>
                    </button>
                  ))}
                </nav>
              )}
              {(q || showModifiedOnly) && (
                <div className="god-search-meta">
                  {q ? `🔍 ${filteredSpecs(NUMBER_LAWS).length} laws match "${q}"` : ''}
                  {q && showModifiedOnly ? ' · ' : ''}
                  {showModifiedOnly ? `✏️ ${modifiedKeys.size} modified` : ''}
                  {(q || showModifiedOnly) && (
                    <button className="god-search-clear-link" onClick={() => { setSearchQuery(''); setShowModifiedOnly(false) }}>Clear filters</button>
                  )}
                </div>
              )}

          {/* Render domains */}
          {(q || showModifiedOnly ? DOMAINS : DOMAINS.filter(d => d.id === activeDomain)).map((domain) => {
            const domainGroups = q || showModifiedOnly ? domain.groups : domain.groups
            // Build rows per group
            const groupSections = domainGroups.map((group) => {
              const allInGroup = NUMBER_LAWS.filter((l) => l.group === group)
              const visibleSpecs = filteredSpecs(allInGroup)
              // decide visibility: if search/modified filtering and group has zero visible specs, skip entirely
              const hasVisibleToggle = (() => {
                // check if any toggle belonging to this group would be visible under current filters
                // We enumerate toggles per group below via special handling; for simplicity, if no numeric specs and not matching, we still may show toggle row
                // So we compute toggle visibility lazily inside section rendering — here we just keep group if visibleSpecs>0 OR toggle would be visible
                // For now, skip only if both specs and potential toggles are hidden
                return false
              })()
              void hasVisibleToggle
              // If filtering and no specs, we still need to check if group has a toggle that passes filter — handle via ToggleRow visibility later
              // But to avoid empty groups, we will keep group hidden only if visibleSpecs.length===0 and we are filtering and toggles would also be hidden
              // Simplify: hide group when filtering and visibleSpecs empty — ToggleRow will self-hide but we may show empty group header unnecessarily
              // We instead render group only if visibleSpecs.length>0 or not filtering
              const isFiltering = !!q || showModifiedOnly
              if (isFiltering && visibleSpecs.length === 0) {
                const toggleGroups = new Set(['Reproduction','Disease','Neuroevolution','Morphology','Sky & Seasons','Shelter','Territory','Weather Sickness','Communication','Wildfire & Disasters','Rivers','Terrain','Materials','Seismic & Waves','Electrostatics','Cosmology','Culture','Ages','Rebellion','Clan','Ecosystem','Predation','Clan War','Politics','Desperation','Food Decay','Agriculture','Theology'])
                if (!toggleGroups.has(group)) return null
                // for toggle groups, we will check after rendering toggles — if none visible, skip
              }

              const special = (
                <>
                  {group === 'Reproduction' && (
                    <ToggleRow k="birth_enabled" label="Births allowed" title="whether new life may begin at all — off hides the lineage dials" />
                  )}
                  {group === 'Disease' && (
                    <ToggleRow k="disease_enabled" label="Plagues allowed" title="plagues walk the world; disabling freezes all sickness" />
                  )}
                  {group === 'Neuroevolution' && (
                    <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>
                      ⚡ Micro-RNN Neural Engine: 16 sensory inputs (vitals, raycasts, sound, scent, slope) continuously drive 7 actuators (thrust, steer, vocal, interact).
                    </div>
                  )}
                  {group === 'Morphology' && (
                    <ToggleRow k="morphology_annealing_enabled" label="Morphology annealing" title="master switch for geometric physics — off keeps classic sides, on enables polar (r,φ) annealing" />
                  )}
                  {group === 'Sky & Seasons' && (
                    <>
                      <ToggleRow k="weather_enabled" label="Weather allowed" title="whether the weather ever turns — off hides weather dials" />
                      <ToggleRow k="sleep_enabled" label="Night rest" title="creatures shelter in houses after dark" />
                    </>
                  )}
                  {group === 'Shelter' && (
                    <ToggleRow k="shelter_enabled" label="Shelter allowed" title="creatures may claim roofs; disabling leaves all exposed and hides the shelter dials" />
                  )}
                  {group === 'Territory' && (
                    <ToggleRow k="territory_enabled" label="Territory claimed" title="clans claim a circle around their house; disabling removes borders" />
                  )}
                  {group === 'Weather Sickness' && (
                    <ToggleRow k="weather_sickness_enabled" label="Weather sickness" title="chill and wet contagion — rain/storm/winter nights build chill, past threshold drains health" />
                  )}
                  {group === 'Communication' && (
                    <>
                      <ToggleRow k="communication_enabled" label="Communication & Signals" title="food + alarm calls, caste vocalizations and scent trails rendered as live ripples" />
                      <ToggleRow k="knowledge_enabled" label="Knowledge & Memory" title="creatures remember food and hazard coordinates, teaching clan-mates" />
                    </>
                  )}
                  {group === 'Wildfire & Disasters' && (
                    <>
                      <ToggleRow k="wildfire_enabled" label="Wildfire" title="fire ignites via storm lightning / fire_rate and spreads grass→plant→house; ash fertilizes" />
                      <ToggleRow k="disaster_enabled" label="Disasters" title="meteor/flood stochastic — god sets frequency, never a specific strike" />
                    </>
                  )}
                  {group === 'Rivers' && (
                    <ToggleRow k="rivers_enabled" label="Rivers" title="horizontal channels: fords cost energy, current sweeps the weak, floods enrich banks" />
                  )}
                  {group === 'Terrain' && (
                    <ToggleRow k="relief_enabled" label="Relief (height field)" title="the land has height: uphill burns energy, cliffs deal fall damage, traffic packs roads" />
                  )}
                  {group === 'Seismic & Waves' && (
                    <ToggleRow k="earthquake_enabled" label="Earthquakes" title="rare quakes throw bodies, drop weakened roofs and crack stone" />
                  )}
                  {group === 'Electrostatics' && (
                    <ToggleRow k="lightning_enabled" label="Storm lightning" title="bolts kill under the arc, ignite the ground and fuse electrostatic rock" />
                  )}
                  {group === 'Cosmology' && (
                    <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>Hidden zones of altered physics — fertile ground, heavy gravity, calm air. Skilled foragers discover them.</div>
                  )}
                  {group === 'Materials' && (
                    <ToggleRow k="structural_enabled" label="Structural integrity" title="storms & floodwater wear buildings down; builders mend what stands" />
                  )}
                  {group === 'Culture' && (
                    <ToggleRow k="culture_enabled" label="Culture" title="culture spreads to allied neighbours, granting collective bonuses" />
                  )}
                  {group === 'Ages' && (
                    <ToggleRow k="age_enabled" label="Ages" title="super-seasons: Golden / Ice / Chaos / Plague — each bends food, mutation, disease, chill" />
                  )}
                  {group === 'Rebellion' && (
                    <ToggleRow k="schism_enabled" label="Schism allowed" title="unhappy members (starving/homeless) split off to found new clan then war parent" />
                  )}
                  {group === 'Clan' && (
                    <>
                      <ToggleRow k="totems_enabled" label="Sacred Avatars" title="each clan bears one of the 8 Sacred Avatars of the Sphere granting distinct divine blessings" />
                      <ToggleRow k="succession_enabled" label="Succession" title="leader succession on death emits succession event" />
                    </>
                  )}
                  {group === 'Ecosystem' && (
                    <ToggleRow k="plant_variants_enabled" label="Plant variants" title="grass/berry/mushroom/poisonous diversity" />
                  )}
                  {group === 'Predation' && (
                    <ToggleRow k="predation_enabled" label="Predation allowed" title="predators hunt prey; disabling makes them docile" />
                  )}
                  {group === 'Clan War' && (
                    <ToggleRow k="war_enabled" label="War allowed" title="rival clans fight on contact; disabling enforces peace" />
                  )}
                  {group === 'Politics' && (
                    <>
                      <ToggleRow k="coalitions_enabled" label="Coalitions" title="allied clans form defensive blocs — strike one member and every ally responds" />
                      <ToggleRow k="leader_decisions_enabled" label="Leader decisions" title="leaders declare war on enemies, sue for peace, demand tribute, and defect" />
                      <ToggleRow k="resource_sharing_enabled" label="Resource sharing" title="clan larder at settlement: well-fed deposit surplus, starving withdraw" />
                    </>
                  )}
                  {group === 'Desperation' && (
                    <>
                      <ToggleRow k="cannibalism_enabled" label="Cannibalism" title="the starving may hunt and eat living enemies" />
                      <ToggleRow k="eat_kin_enabled" label="Eat kin" title="weak kin may be eaten too — at the price of exile and feud" hideIfOff="cannibalism_enabled" />
                    </>
                  )}
                  {group === 'Food Decay' && (
                    <ToggleRow k="food_decay_enabled" label="Food decay" title="mature plants wither after their lifespan, fertilise nearby soil, then vanish" />
                  )}
                  {group === 'Agriculture' && (
                    <>
                      <ToggleRow k="agriculture_enabled" label="Agriculture" title="seed pouches from wild harvests, cultivated farm plots, weeding & tending" />
                      <ToggleRow k="granaries_enabled" label="Granaries" title="a dry roofed store at each settlement storing harvested rations" hideIfOff="agriculture_enabled" />
                    </>
                  )}
                  {group === 'Theology' && (
                    <>
                      <ToggleRow k="theology_enabled" label="Theology of the Sphere" title="shrines beside main houses, dawn & dusk tithes, healing aura, miracles, temples" />
                      <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>
                        8 Sacred Avatars: ⭕ Abundance · ⚡ Wrath · 👁️ Omniscience · 🛡️ Permanence · 🌿 Renewal · ⚖️ Equilibrium · 🌀 Ascent · 🕯️ Sanctuary
                      </div>
                    </>
                  )}
                </>
              )

              const rows = visibleSpecs.map(({ key, label, min, max, step }) => {
                const translatedLabel = t(`godLaws.${key}`) !== `godLaws.${key}` ? t(`godLaws.${key}`) : label
                const hint = (t(`godHints.${key}`) !== `godHints.${key}` ? t(`godHints.${key}`) : LAW_HINTS[key])
                const isOpen = openHint === key
                const curVal = (laws[key] as number | undefined) ?? min
                const baseVal = (baselineLaws[key] as number | undefined)
                const isModified = modifiedKeys.has(key)
                const zone = getZone(curVal, baseVal, min, max)
                const pct = max === min ? 0 : ((curVal - min) / (max - min)) * 100
                const basePct = baseVal !== undefined && max !== min ? ((baseVal - min) / (max - min)) * 100 : null
                const fmt = (v: number) => step < 1 ? v.toFixed(step < 0.01 ? 3 : 2) : String(Math.round(v))
                // highlight match
                const qLower = q
                const labelMatch = qLower && translatedLabel.toLowerCase().includes(qLower)
                return (
                  <div key={key} className={`god-law-row zone-${zone} ${isModified ? 'modified' : ''}`} style={{ borderBottom: '1px solid #21262d', padding: isOpen ? '10px 10px 8px' : '8px 10px', background: isModified ? 'rgba(227,179,65,0.05)' : undefined }}>
                    <div className="god-law-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center', flex: 1, minWidth: 0 }}>
                        <span title={hint} style={{ color: isModified ? '#e3b341' : '#e6edf3', fontSize: 13, fontWeight: isModified ? 600 : 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', background: labelMatch ? 'rgba(227,179,65,0.2)' : undefined, padding: labelMatch ? '0 3px' : 0, borderRadius: 3 }}>
                          {translatedLabel}
                        </span>
                        {isModified && <span className="god-mod-dot" title="Modified from preset">●</span>}
                        {hint && (
                          <button
                            type="button"
                            onClick={() => setOpenHint(isOpen ? null : key)}
                            title={hint}
                            style={{ width: 20, height: 20, borderRadius: '50%', border: '1px solid #484f58', background: isOpen ? '#30363d' : '#21262d', color: isOpen ? '#f0f6fc' : '#8b949e', fontSize: 11, lineHeight: 1, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}
                            aria-label={`hint for ${translatedLabel}`}
                          >
                            ?
                          </button>
                        )}
                      </span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flex: 'none' }}>
                        {isModified && (
                          <button onClick={() => revertOne(key)} title="Revert to preset" className="god-revert-btn">↺ Revert</button>
                        )}
                        <span className={`god-zone-pill zone-${zone}`} title={`${zone} zone — distance from default`}>{zone}</span>
                      </span>
                    </div>
                    {/* Dual slider + number pill — BD.8.3 */}
                    <div className="god-dual-control">
                      <div className="god-slider-wrap">
                        <div className="god-slider-track">
                          <div className="god-slider-zones">
                            <span className="z-extreme-left" />
                            <span className="z-strained-left" />
                            <span className="z-safe" />
                            <span className="z-strained-right" />
                            <span className="z-extreme-right" />
                          </div>
                          <div className="god-slider-fill" style={{ width: `${pct}%` }} />
                          {basePct !== null && <span className="god-baseline-marker" style={{ left: `${basePct}%` }} title={`Default: ${fmt(baseVal as number)}`} />}
                        </div>
                        <input
                          type="range"
                          className="god-range"
                          min={min}
                          max={max}
                          step={step}
                          value={curVal}
                          onChange={(e) => set(key, e.target.value)}
                          style={{ ['--pct' as any]: `${pct}%` }}
                        />
                      </div>
                      <span className={`god-number-pill zone-${zone}`}>
                        <button type="button" className="god-pill-step" onClick={() => stepVal(key, min, max, step, -1)} aria-label="decrease">−</button>
                        <input
                          type="number"
                          className="god-pill-input"
                          min={min}
                          max={max}
                          step={step}
                          value={curVal}
                          onChange={(e) => set(key, e.target.value)}
                        />
                        <button type="button" className="god-pill-step" onClick={() => stepVal(key, min, max, step, 1)} aria-label="increase">+</button>
                      </span>
                    </div>
                    {baseVal !== undefined && (
                      <div className="god-baseline-row">
                        <span className="god-baseline-text">Default {fmt(baseVal)} · {curVal > baseVal ? `+${fmt(curVal - baseVal)}` : curVal < baseVal ? fmt(curVal - baseVal) : 'baseline'}</span>
                        <span className="god-range-labels"><span>{fmt(min)}</span><span>{fmt(max)}</span></span>
                      </div>
                    )}
                    {isOpen && hint && (
                      <div style={{ fontSize: 12, color: '#c9d1d9', background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '8px 10px', margin: '6px 0 2px', lineHeight: 1.45 }}>
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

              const hideGroup = visibleSpecs.length === 0 && (isFiltering ? true : false)
              if (hideGroup) {
                if (showModifiedOnly && !q) {
                  const groupBoolKeys: Record<string, BoolLawKey[]> = {
                    'Reproduction': ['birth_enabled'],
                    'Disease': ['disease_enabled'],
                    'Morphology': ['morphology_annealing_enabled'],
                    'Sky & Seasons': ['weather_enabled', 'sleep_enabled'],
                    'Shelter': ['shelter_enabled'],
                    'Territory': ['territory_enabled'],
                    'Weather Sickness': ['weather_sickness_enabled'],
                    'Communication': ['communication_enabled', 'knowledge_enabled'],
                    'Wildfire & Disasters': ['wildfire_enabled', 'disaster_enabled'],
                    'Rivers': ['rivers_enabled'],
                    'Terrain': ['relief_enabled'],
                    'Materials': ['structural_enabled'],
                    'Seismic & Waves': ['earthquake_enabled'],
                    'Electrostatics': ['lightning_enabled'],
                    'Culture': ['culture_enabled'],
                    'Ages': ['age_enabled'],
                    'Rebellion': ['schism_enabled'],
                    'Clan': ['totems_enabled', 'succession_enabled'],
                    'Ecosystem': ['plant_variants_enabled'],
                    'Predation': ['predation_enabled'],
                    'Clan War': ['war_enabled'],
                    'Politics': ['coalitions_enabled', 'leader_decisions_enabled', 'resource_sharing_enabled'],
                    'Desperation': ['cannibalism_enabled', 'eat_kin_enabled'],
                    'Food Decay': ['food_decay_enabled'],
                    'Agriculture': ['agriculture_enabled', 'granaries_enabled'],
                    'Theology': ['theology_enabled'],
                  }
                  const bks = groupBoolKeys[group] || []
                  if (bks.some(k => modifiedKeys.has(k))) { /* keep */ } else return null
                } else if (q) {
                  // keep if any bool label matches q
                  // approximate: don't hide — let header show but rows empty and ToggleRow may show/hide internally
                  // For search, we should hide groups where no bool matches; to avoid noise we hide if no spec rows
                  // We'll attempt to keep only if group name matches q itself
                  if (group.toLowerCase().includes(q)) { /* keep to show toggles */ } else return null
                } else {
                  return null
                }
              }

              return (
                <section key={group} className="god-group">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, borderBottom: '1px solid #30363d', paddingBottom: 6 }}>
                    <h3 style={{ margin: 0, fontSize: 13, color: '#e3b341', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{(t(`god.groups.${GROUP_KEY[group] ?? group}`) !== `god.groups.${GROUP_KEY[group] ?? group}` ? t(`god.groups.${GROUP_KEY[group] ?? group}`) : group)}</h3>
                    <span style={{ fontSize: 10, color: '#8b949e', fontWeight: 600, background: '#21262d', padding: '1px 6px', borderRadius: 10, border: '1px solid #30363d' }}>
                      {visibleSpecs.length} laws
                    </span>
                  </div>
                  {special}
                  {rows}
                </section>
              )
            }).filter(Boolean)

            if (groupSections.length === 0) return null
            return (
              <div key={domain.id} className="god-domain-section">
                <div className="god-domain-header">
                  <span className="god-domain-title">{domain.icon} {domain.label}</span>
                  <span className="god-domain-meta">{groupSections.length} groups · {groupSections.length} sections</span>
                </div>
                {groupSections}
              </div>
            )
          })}
        </>
      )}
    </>
  )}
</>
)

  if (isMobile) {
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

export default function GodPanel(props: Props) {
  if (!props.open) return null
  return (
    <GodPanelErrorBoundary>
      <GodPanelInner {...props} />
    </GodPanelErrorBoundary>
  )
}
