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
  { key: 'mutation_heritability', label: 'Mutation heritability', min: 0, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'sex_ratio', label: 'Son probability', min: 0, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'adult_age', label: 'Adult age', min: 0, max: 5000, step: 50, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'max_sides', label: 'Max caste sides', min: 3, max: 64, step: 1, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'euthanasia_threshold', label: 'Euthanasia ≥', min: 0.3, max: 1, step: 0.05, group: 'Reproduction', gate: 'birth_enabled' },
  { key: 'mutation_sigma', label: 'NN mutation σ', min: 0, max: 0.5, step: 0.01, group: 'Neuroevolution' },
  { key: 'crossover_rate', label: 'NN crossover rate', min: 0, max: 1, step: 0.05, group: 'Neuroevolution' },
  { key: 'annealing_start_generation', label: 'Morphology start gen', min: 0, max: 500, step: 5, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'annealing_decay_generations', label: 'Morphology decay gens', min: 10, max: 5000, step: 25, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'morph_lambda_override', label: 'Manual λ override (-1 = auto)', min: -1.0, max: 1.0, step: 0.05, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'vertex_mutation_std', label: 'Vertex jitter σr', min: 0.005, max: 0.20, step: 0.005, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'angle_mutation_std', label: 'Angle jitter σφ', min: 0.005, max: 0.10, step: 0.005, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'topological_mutation_rate', label: 'Topo mutation rate', min: 0.0, max: 0.10, step: 0.005, group: 'Morphology', gate: 'morphology_annealing_enabled' },
  { key: 'disease_outbreak_rate', label: 'Outbreak rate / tick', min: 0, max: 0.05, step: 0.0005, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_rate', label: 'Contagion chance', min: 0, max: 1, step: 0.01, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_energy_drain', label: 'Energy drain / tick', min: 0, max: 2, step: 0.05, group: 'Disease', gate: 'disease_enabled' },
  { key: 'disease_lethality', label: 'Lethality', min: 0, max: 1, step: 0.05, group: 'Disease', gate: 'disease_enabled' },

  // Extinction Safeguards (Phase 5)
  { key: 'safeguard_critical_pop', label: 'Emergency pop floor (Kcrit)', min: 2, max: 50, step: 1, group: 'Extinction Safeguards', gate: 'safeguard_enabled' },
  { key: 'safeguard_relief_ratio', label: 'Relief threshold ratio (Ksafe)', min: 0.05, max: 0.50, step: 0.01, group: 'Extinction Safeguards', gate: 'safeguard_enabled' },
  { key: 'safeguard_genesis_batch', label: 'Genesis miracle batch', min: 1, max: 20, step: 1, group: 'Extinction Safeguards', gate: 'safeguard_enabled' },

  // Density-Dependent Soft-Cap Damping (Phase 4)
  { key: 'damping_steepness', label: 'Damping steepness', min: 1.0, max: 20.0, step: 0.5, group: 'Density Soft-Cap Damping', gate: 'soft_cap_enabled' },
  { key: 'crowding_stress_mult', label: 'Crowding stress mult', min: 0.0, max: 1.0, step: 0.05, group: 'Density Soft-Cap Damping', gate: 'soft_cap_enabled' },
  { key: 'resource_strain_mult', label: 'Resource strain mult', min: 0.0, max: 2.0, step: 0.05, group: 'Density Soft-Cap Damping', gate: 'soft_cap_enabled' },

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
  { id: 'biology', icon: '🧬', label: 'Biology & Evolution', shortLabel: 'Biology', groups: ['Movement', 'Life & Death', 'Reproduction', 'Extinction Safeguards', 'Density Soft-Cap Damping', 'Disease', 'Neuroevolution', 'Morphology', 'Predation'] },
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
  'Extinction Safeguards': 'safeguards',
  'Density Soft-Cap Damping': 'softCap',
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
  morphology_annealing_enabled: true,
  safeguard_enabled: true,
  safeguard_morph_mercy: true,
  soft_cap_enabled: true,
}

const LAW_HINTS: Partial<Record<NumberLawKey, string>> = {
  // 1. Food & Energy
  food_count: 'The world keeps this much food alive — bounty or famine (winter ×0.5, summer ×1.2).',
  energy_max: 'Maximum metabolic energy capacity an organism can store before full saturation (10–500).',
  energy_decay_per_tick: 'Baseline metabolic burn rate per tick without food intake; shelter and infancy reduce decay.',
  energy_from_food: 'Base energy yield from harvesting a mature plant (berry 48, grass 32, mushroom 24, poison 8).',

  // 2. Ecosystem & Biodiversity
  plant_growth_rate: 'How fast sprouted plants mature into harvestable food; seasons and rain accelerate growth.',
  plant_spread_rate: 'Probability per tick that a mature plant drops seeds into adjacent fertile ground.',
  nutrient_cycle_rate: 'Acceleration of plant growth near decomposing corpses (death nourishes new life).',
  poison_rate: 'Chance a new wild sprout is poisonous (-30 HP damage on ingestion).',
  food_lifespan_ticks: 'Ticks a mature plant lives before naturally withering into the living soil grid.',
  granary_capacity: 'Units of food a settlement granary can store; sated harvesters deposit grain and berries.',

  // 3. Organism Sensory & Physics
  perceive_radius: 'Base perception sight radius; scaled by caste (Woman 0.8×, Priest 1.35×), night (0.6×), and fog.',
  eat_radius: 'Physical contact distance required to consume a plant, corpse, or prey item.',
  hungry_ratio: 'Energy fraction threshold (≤ 35%) where normalized energy enters NN sensor slot 0 to trigger foraging.',
  starving_ratio: 'Severe energy threshold (≤ 15%) triggering desperation sprint and pulsing survival distress.',
  steer_turn: 'Maximum heading angular turn rate per tick, dynamically scaled by creature moment of inertia (Izz).',

  // 4. Life Cycle, Reproduction & Population
  lifespan_mult: 'Multiplier scaling all caste lifespans (Woman: 4,800 ticks → Priest: 9,000 ticks).',
  birth_rate: 'Base reproduction probability per eligible mating pair per tick when energy and adult age are met.',
  carrying_capacity: 'Population density threshold above which fertility begins to gradually diminish.',
  max_population: 'Hard global population cap preventing any new births until density declines.',
  mutation_rate: 'Probability a newborn son deviates ±1 side from classical caste inheritance.',
  mutation_heritability: 'Fraction of parental irregularity inherited by offspring; lower values prevent rapid mutation spread.',
  sex_ratio: 'Probability a child is a son (ascending regular polygon) vs daughter (agile line).',
  adult_age: 'Ticks required for an infant/juvenile to mature into a sexually fertile adult (220 ticks).',
  max_sides: 'Upper limit on regular polygon vertex ascendance (up to Priest / Circle status).',
  euthanasia_threshold: 'Irregularity threshold; deformed infants exceeding this are consumed at adulthood.',

  // Extinction Safeguards & Soft-Cap Damping
  safeguard_critical_pop: 'Population floor Kcrit (≤12) triggering emergency Tier 3 Genesis miracles from The Sphere.',
  safeguard_relief_ratio: 'Carrying capacity ratio Ksafe = carrying × ratio (0.30) below which Tier 1/2 relief scales activate.',
  safeguard_genesis_batch: 'Number of pristine regular polygon beings created per Tier 3 Genesis miracle.',
  damping_steepness: 'Divisor coefficient damping birth rate as population overshoots carrying capacity (1/(1+d*xi^2)).',
  crowding_stress_mult: 'Multiplier scaling metabolic energy drain under overpopulation density stress (1+c*xi).',
  resource_strain_mult: 'Multiplier scaling plant growth & spread slowdown under overpopulation strain (1/(1+r*xi)).',

  // 5. Neural Network & Morphology
  mutation_sigma: 'Gaussian mutation standard deviation (σ) applied to genome weights during crossover.',
  crossover_rate: 'Probability of uniform 50/50 parental genome blending during sexual reproduction.',
  annealing_start_generation: 'Generation where polar morphology begins decaying from Abbott templates (higher = delays speciation).',
  annealing_decay_generations: 'Generations over which polar morphology annealing decays from Abbott templates to free evolution (higher = slower speciation).',
  morph_lambda_override: 'Manually pin morphology λ weight (1.0 = strict classical, 0.0 = freeform divergence, -1 = auto annealing).',
  vertex_mutation_std: 'Radial jitter magnitude σr applied to polar genome radii when offspring are born (lower = subtle shapes).',
  angle_mutation_std: 'Angular jitter magnitude σφ applied to polar genome vertex angles (lower = subtle angles).',
  topological_mutation_rate: 'Probability of adding or removing vertices during reproduction (lower = slower topological speciation).',

  // 6. Pathology & Health
  disease_outbreak_rate: 'Spontaneous plague outbreak probability per tick during crowded or unsanitary conditions.',
  disease_rate: 'Transmission rate of contagion when in close contact with an infected organism.',
  disease_energy_drain: 'Metabolic energy drained per tick from infected creatures.',
  disease_lethality: 'Direct health (HP) damage dealt per tick to actively diseased creatures.',

  // 7. Meteorology, Sky & Housing
  day_length: 'Total duration in ticks of a single diurnal day/night cycle (2400 ticks).',
  season_length: 'Duration in ticks of each season (Spring, Summer, Autumn, Winter).',
  winter_food_mult: 'Winter food abundance multiplier (0.7 gentle, 0.5 harsh, 0.3 extinction collapse).',
  night_sight_mult: 'Perception radius multiplier during night ticks for non-nocturnal castes.',
  weather_change_rate: 'Frequency of meteorological transitions between clear, rain, fog, and storm.',
  exposure_drain: 'Health and energy drain per tick when outdoors during harsh storms, heavy rain, or freezing winter.',
  house_capacity: 'Bed capacity inside a settlement hall; excess members sleep outdoors or search for other roofs.',
  house_decay_ticks: 'Ticks before an abandoned, roofless house crumbles into ruins.',
  rest_recovery_mult: 'Health regeneration multiplier when sleeping indoors under a roof.',
  chill_drain: 'Direct health drain per tick when chilled outdoors without shelter.',

  // 8. Clan Territory & Settlements
  territory_radius: 'Radius of clan territorial influence around settlement houses; trespass sours diplomacy.',
  trespass_decay: 'Diplomatic relation points lost per tick when a rival clan enters marked territory.',
  max_clans: 'Maximum number of sovereign clans spawned during world initialization.',
  larder_capacity: 'Energy capacity of settlement communal food stores where surplus is shared.',
  coalition_threshold: 'Diplomatic trust score required for two friendly clans to form a defensive coalition.',
  schism_threshold: 'Dissatisfaction fraction (hunger, homelessness) triggering a factional clan schism.',

  // 9. Predation & Combat
  predator_ratio: 'Fraction of population spawned as predatory carnivores hunting prey.',
  hunt_radius: 'Aggro detection radius within which carnivores and war parties acquire targets.',
  bite_damage: 'Combat damage dealt per carnivore attack or predatory strike.',
  energy_from_prey: 'Caloric energy extracted from slaying and eating a prey creature.',
  fear_radius: 'Distance at which herbivores and vulnerable castes detect threats and execute evasion.',
  attack_damage: 'Base damage dealt by soldiers and warriors in inter-clan battles.',
  cannibalism_energy: 'Energy gained by starving creatures resorting to eating fallen kin or rivals.',

  // 10. Theology & Culture
  tithe_rate: 'Fraction of energy devout worshippers offer at shrines each dawn & dusk to build clan faith.',
  temple_faith_cost: 'Faith points required to consecrate a glowing Temple of the Sphere.',
  age_length: 'Ticks per historical age (Golden Age, Ice Age, Age of Chaos, Age of Plague).',
  culture_spread_rate: 'Rate at which allied clans sharing borders adopt common cultural traits and beliefs.',

  // 11. World Physics & Disasters
  fire_rate: 'Probability per tick that a mature plant ignites during dry spells or lightning strikes.',
  disaster_rate: 'Stochastic probability of catastrophic environmental disasters (meteors, deluges).',
  river_count: 'Number of procedural river channels carved across the terrain at world generation.',
  earthquake_rate: 'Frequency of seismic quakes that crack buildings and shake terrain.',
  lightning_strike_rate: 'Frequency of deadly electrical arc strikes during thunder storms.',
  anomaly_count: 'Number of mysterious spatial anomaly zones altering local physics.',
  door_clearance: 'Width multiplier for house doorways relative to the largest creature size.',
}

const BOOL_HINTS: Partial<Record<BoolLawKey, string>> = {
  birth_enabled: 'Master switch enabling reproduction, mating, and generational ascendance.',
  disease_enabled: 'Enables contagious pathogen transmission, quarantine behavior, and priestly healing.',
  weather_enabled: 'Enables dynamic meteorological cycles (sun, rain, fog, storms).',
  sleep_enabled: 'Enables diurnal sleep cycles, house resting, and oral lore transfer.',
  shelter_enabled: 'Enables walled house mechanics, door navigation, and roof protection.',
  weather_sickness_enabled: 'Enables exposure chill and hypothermia when caught unsheltered in rain or winter.',
  territory_enabled: 'Enables clan boundary markings, territory defence, and trespass penalties.',
  totems_enabled: 'Enables Sacred Avatar totem blessings for each clan settlement.',
  succession_enabled: 'Enables dynamic governance leadership transfers on chieftain death.',
  communication_enabled: 'Enables vocalizations, alarm chirps, peace hums, and emotional thought bubbles.',
  knowledge_enabled: 'Enables spatial memory, waypoint mapping, and rumor broadcasting among kin.',
  wildfire_enabled: 'Enables combustive flame propagation across dense vegetation and forests.',
  disaster_enabled: 'Enables cataclysmic meteors, floods, and natural world disturbances.',
  culture_enabled: 'Enables traditions, governance archetypes, and cultural diffusion.',
  age_enabled: 'Enables historical epoch progression (Golden Age, Ice Age, Age of Chaos, Age of Plague).',
  schism_enabled: 'Enables internal clan fractures when members starve or lack shelter.',
  plant_variants_enabled: 'Enables botanical diversity across 6 distinct functional plant species.',
  predation_enabled: 'Enables carnivorous predator-prey ecology and hunting dynamics.',
  war_enabled: 'Enables inter-clan warfare, tactical raids, and territorial conquest.',
  coalitions_enabled: 'Enables mutual defensive alliances and diplomatic treaties.',
  leader_decisions_enabled: 'Enables chieftain governance bylaws (rationing, martial law, war declarations).',
  resource_sharing_enabled: 'Enables communal larders and altruistic basket food sharing.',
  cannibalism_enabled: 'Enables desperate consumption of the living during extreme starvation.',
  eat_kin_enabled: 'Allows consumption of deceased or weak clanmates at the cost of tribal exile and feuds.',
  food_decay_enabled: 'Enables mature plants to wither over time and fertilize the living soil.',
  theology_enabled: 'Enables the 8 Sacred Avatars, shrines, temples, miracles, and divine tithes.',
  agriculture_enabled: 'Enables seed gathering, farm plots, irrigation furrows, and agricultural tending.',
  granaries_enabled: 'Enables communal settlement granaries to stockpile grains and berries against winter.',
  rivers_enabled: 'Enables water channels, fords, water currents, bridges, and dams.',
  relief_enabled: 'Enables topographical elevation, slope inertia, cliffs, and road packing.',
  structural_enabled: 'Enables weather wear on buildings, builder repairs, and roof collapse into rubble.',
  earthquake_enabled: 'Enables seismic tremors that shake terrain and damage weakened structures.',
  lightning_enabled: 'Enables real lightning strikes during storms that ignite fires and damage creatures.',
  morphology_annealing_enabled: 'Enables polar genome evolution transitioning from Abbott templates to free morphology.',
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
  balance: ['Food: 300', 'Winter: 0.80×', 'Cap: 400'],
  sustainable: ['Food: 550 (Abundant)', 'Winter: 0.85×', 'Cap: 550'],
  theocracy: ['Food: 400 (Faith)', 'Winter: 0.80×', 'Cap: 500'],
  warlords: ['Food: 340 (War)', 'Winter: 0.70×', 'Cap: 450'],
  chaos: ['Food: 320 (Scarce)', 'Winter: 0.55× (Harsh)', 'Cap: 350'],
  extinction: ['Food: 120 (Harsh)', 'Winter: 0.30× (Cold)', 'Cap: 180'],
  boom: ['Food: 440 (Boom)', 'Winter: 0.85×', 'Cap: 800'],
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

function detectPreset(laws: GodLaws, presetsDetails?: Record<string, Record<string, any>>): string | null {
  if (presetsDetails) {
    for (const [name, p] of Object.entries(presetsDetails)) {
      if (Object.entries(p).every(([k, v]) => (laws as any)[k] === v)) return name
    }
    for (const [name, p] of Object.entries(presetsDetails)) {
      if (
        laws.food_count === p.food_count &&
        laws.carrying_capacity === p.carrying_capacity &&
        laws.max_population === p.max_population
      ) return name
    }
  }
  if (laws.food_count === 300 && laws.carrying_capacity === 400) return 'balance'
  if (laws.food_count === 550 && laws.carrying_capacity === 550) return 'sustainable'
  if (laws.food_count === 400 && laws.carrying_capacity === 500) return 'theocracy'
  if (laws.food_count === 340 && laws.carrying_capacity === 450) return 'warlords'
  if (laws.food_count === 320 && laws.carrying_capacity === 350) return 'chaos'
  if (laws.food_count === 120 && laws.carrying_capacity === 180) return 'extinction'
  if (laws.food_count === 440 && laws.carrying_capacity === 800) return 'boom'
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
  const [presetsDetails, setPresetsDetails] = useState<Record<string, Record<string, any>> | null>(null)
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
        if (presetsData?.details) setPresetsDetails(presetsData.details)
        const detected = presetsData?.current || detectPreset(lawsData, presetsData?.details) || 'balance'
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
      setCurrentPreset(detectPreset(updated, presetsDetails ?? undefined))
      return updated
    })
  }

  const revertOne = (key: NumberLawKey) => {
    const base = (baselineLaws as any)[key]
    if (base === undefined) return
    setLaws((l) => {
      const updated = { ...l, [key]: base }
      setCurrentPreset(detectPreset(updated, presetsDetails ?? undefined))
      return updated
    })
  }

  const stepVal = (key: NumberLawKey, min: number, max: number, step: number, dir: 1 | -1) => {
    const raw = laws[key]
    const curr = (typeof raw === 'number' && !isNaN(raw)) ? raw : min
    const next = Math.max(min, Math.min(max, Number((curr + dir * step).toFixed(4))))
    set(key, next)
  }

  const boolVal = (k: BoolLawKey) => laws[k] ?? BOOL_DEFAULTS[k] ?? false
  const setBool = (k: BoolLawKey, v: boolean) => {
    setLaws((l) => {
      const updated = { ...l, [k]: v }
      setCurrentPreset(detectPreset(updated, presetsDetails ?? undefined))
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
    const getTrLabel = () => {
      if (t(`godToggles.${k}`) !== `godToggles.${k}`) return t(`godToggles.${k}`)
      if (t(`godLaws.${k}`) !== `godLaws.${k}`) return t(`godLaws.${k}`)
      return label
    }
    const getTrTitle = () => {
      if (t(`godToggles.${k}Hint`) !== `godToggles.${k}Hint`) return t(`godToggles.${k}Hint`)
      if (t(`godHints.${k}`) !== `godHints.${k}`) return t(`godHints.${k}`)
      return title || BOOL_HINTS[k] || ''
    }
    const trLabel = getTrLabel()
    const trTitle = getTrTitle()
    if (showModifiedOnly && !modifiedKeys.has(k)) {
      if (q) {
        const trLabel2 = trLabel.toLowerCase()
        const trTitle2 = trTitle.toLowerCase()
        if (!trLabel2.includes(q) && !trTitle2.includes(q) && !k.includes(q)) return null
      } else return null
    }
    if (q) {
      const trLabel2 = trLabel.toLowerCase()
      const trTitle2 = trTitle.toLowerCase()
      if (!trLabel2.includes(q) && !trTitle2.includes(q) && !k.includes(q)) return null
    }
    const isMod = modifiedKeys.has(k)
    const isOpen = openHint === k
    return (
      <div style={{ borderBottom: '1px solid #21262d', background: isMod ? 'rgba(227,179,65,0.06)' : undefined, borderLeft: isMod ? '2px solid #d29922' : '2px solid transparent' }}>
        <div className="god-row god-toggle-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '9px 12px' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span title={trTitle} style={{ color: isMod ? '#e3b341' : '#e6edf3', fontSize: 13, fontWeight: isMod ? 600 : 500, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              {trLabel}
            </span>
            {isMod && <span style={{ fontSize: 9, padding: '1px 5px', borderRadius: 4, background: '#d29922', color: '#0d1117', fontWeight: 800 }}>MOD</span>}
            {trTitle && (
              <button
                type="button"
                className={`god-hint-btn ${isOpen ? 'active' : ''}`}
                onClick={() => setOpenHint(isOpen ? null : k)}
                title={trTitle}
                aria-label={`hint for ${trLabel}`}
              >
                ?
              </button>
            )}
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            {isMod && <button onClick={() => setBool(k, (baselineLaws as any)[k] ?? BOOL_DEFAULTS[k] ?? false)} title={t('god.ui.revert_title')} className="god-revert-btn">{t('god.ui.revert')}</button>}
            <Switch checked={boolVal(k)} onChange={(v) => setBool(k, v)} title={trTitle ?? trLabel} />
          </span>
        </div>
        {isOpen && trTitle && (
          <div className="god-hint-box" style={{ margin: '0 12px 8px' }}>
            {trTitle}
            <div style={{ marginTop: 6 }}>
              <a href="/docs/god-laws.md" rel="noreferrer" style={{ fontSize: 11, color: '#58a6ff' }}>{t('god.ui.open_docs')}</a>
              {' · '}
              <a href="/wiki#god-laws" style={{ fontSize: 11, color: '#58a6ff' }}>{t('god.ui.wiki_link')}</a>
            </div>
          </div>
        )}
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
      setCurrentPreset(detectPreset(lawsData, presetsDetails ?? undefined))
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>⚖️</span>
          <h2 style={{ margin: 0, fontSize: 15, fontWeight: 700, letterSpacing: '0.02em', color: '#f0f6fc' }}>
            {t('god.title')}
          </h2>
        </div>
        <span style={{ fontSize: 11, color: '#8b949e' }}>
          {t('god.subtitle')}
        </span>
      </div>
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
      {/* Top Segmented Mode Switcher: Presets vs Laws of Nature */}
      <div className="god-segmented-control" role="tablist" aria-label="God panel sections">
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'presets'}
          className={`god-segment-btn ${activeSection === 'presets' ? 'active' : ''}`}
          onClick={() => setActiveSection('presets')}
        >
          <span style={{ fontSize: 14 }}>🎯</span>
          <span>Curated Presets</span>
          <span className="god-segment-pill">{presetKeys.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeSection === 'laws'}
          className={`god-segment-btn ${activeSection === 'laws' ? 'active' : ''}`}
          onClick={() => setActiveSection('laws')}
        >
          <span style={{ fontSize: 14 }}>⚖️</span>
          <span>Laws of Nature</span>
          <span className="god-segment-pill">{NUMBER_LAWS.length}</span>
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
                    {activePresetMeta && currentPreset ? t(`god.presets.${currentPreset}`) : (t('god.presets.custom') || 'Custom')}
                  </span>
                  {modifiedKeys.size > 0 && (
                    <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 6, background: 'rgba(227,179,65,0.18)', color: '#e3b341', fontWeight: 700 }}>
                      {t('god.ui.modified_count', { count: modifiedKeys.size })}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveSection('presets')}
                  style={{ fontSize: 11, color: '#58a6ff', background: 'transparent', border: 'none', cursor: 'pointer', padding: 0, fontWeight: 600 }}
                >
                  {t('god.ui.switch_preset')}
                </button>
              </div>

              {/* Law Search & Modified Filter — BD.8.2 */}
              <div className="god-search-bar">
                <div className="god-search-input-wrap">
                  <span className="god-search-icon">🔍</span>
                  <input
                    className="god-search-input"
                    type="text"
                    placeholder={t('god.ui.search_placeholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button className="god-search-clear" onClick={() => setSearchQuery('')} title={t('god.ui.clear_search')}>×</button>
                  )}
                </div>
                <button
                  className={`god-filter-btn ${showModifiedOnly ? 'active' : ''}`}
                  onClick={() => setShowModifiedOnly(!showModifiedOnly)}
                  title={t('god.ui.show_modified_title')}
                >
                  {showModifiedOnly ? '✓ ' : ''}{t('god.ui.show_modified', { count: modifiedKeys.size })}
                </button>
                {showModifiedOnly && modifiedKeys.size > 0 && (
                  <button
                    className="god-revert-all"
                    onClick={() => setLaws({ ...baselineLaws })}
                    title={t('god.ui.revert_all_title')}
                  >
                    {t('god.ui.revert_all')}
                  </button>
                )}
              </div>

              <div style={{ borderBottom: '1px solid #30363d', background: modifiedKeys.has('boundary' as any) ? 'rgba(227,179,65,0.06)' : undefined, borderLeft: (modifiedKeys.has('boundary' as any) ? '2px solid #d29922' : '2px solid transparent') }}>
                <label className="god-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 12px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: '#e6edf3', fontSize: 13, fontWeight: 500 }}>{t('godToggles.edgeOfWorld' as any) || 'Edge of world'}</span>
                    <button
                      type="button"
                      className={`god-hint-btn ${openHint === 'boundary' ? 'active' : ''}`}
                      onClick={() => setOpenHint(openHint === 'boundary' ? null : 'boundary')}
                      title={t('god.ui.edge_hint_title')}
                      aria-label="hint for edge of world"
                    >
                      ?
                    </button>
                  </span>
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
                {openHint === 'boundary' && (
                  <div className="god-hint-box" style={{ margin: '0 12px 8px' }} dangerouslySetInnerHTML={{ __html: t('god.ui.edge_hint_body') }} />
                )}
              </div>

              {/* Domain selector grid */}
              {!q && !showModifiedOnly && (
                <div className="god-domain-grid" role="tablist" aria-label="Law domains">
                  {DOMAINS.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      role="tab"
                      aria-selected={activeDomain === d.id}
                      className={`god-domain-card-btn ${activeDomain === d.id ? 'active' : ''}`}
                      onClick={() => setActiveDomain(d.id)}
                      title={`${t(`god.domains.${d.id}`) !== `god.domains.${d.id}` ? t(`god.domains.${d.id}`) : d.label}`}
                    >
                      <span className="god-domain-btn-label">
                        <span className="god-domain-icon">{d.icon}</span>
                        <span>{t(`god.domainShort.${d.id}`) !== `god.domainShort.${d.id}` ? t(`god.domainShort.${d.id}`) : d.shortLabel}</span>
                      </span>
                      <span className="god-domain-count">{domainLawCounts[d.id] ?? 0}</span>
                    </button>
                  ))}
                </div>
              )}
              {(q || showModifiedOnly) && (
                <div className="god-search-meta">
                  {q ? t('god.ui.match_count', { count: filteredSpecs(NUMBER_LAWS).length, q }) : ''}
                  {q && showModifiedOnly ? ' · ' : ''}
                  {showModifiedOnly ? t('god.ui.modified_indicator', { count: modifiedKeys.size }) : ''}
                  {(q || showModifiedOnly) && (
                    <button className="god-search-clear-link" onClick={() => { setSearchQuery(''); setShowModifiedOnly(false) }}>{t('god.ui.clear_filters')}</button>
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
              const isFiltering = !!q || showModifiedOnly
              if (isFiltering && visibleSpecs.length === 0) {
                const toggleGroups = new Set(['Reproduction','Disease','Neuroevolution','Morphology','Sky & Seasons','Shelter','Territory','Weather Sickness','Communication','Wildfire & Disasters','Rivers','Terrain','Materials','Seismic & Waves','Electrostatics','Cosmology','Culture','Ages','Rebellion','Clan','Ecosystem','Predation','Clan War','Politics','Desperation','Food Decay','Agriculture','Theology'])
                if (!toggleGroups.has(group)) return null
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
                      {t('god.ui.notes.neuroevolution')}
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
                    <div className="god-note" style={{ fontSize: 11, opacity: 0.7, padding: '4px 10px' }}>
                      {t('god.ui.notes.cosmology')}
                    </div>
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
                        {t('god.ui.notes.theology_avatars')}
                      </div>
                    </>
                  )}
                </>
              )

              const rows = visibleSpecs.map(({ key, label, min, max, step }) => {
                const translatedLabel = t(`godLaws.${key}`) !== `godLaws.${key}` ? t(`godLaws.${key}`) : label
                const hint = (t(`godHints.${key}`) !== `godHints.${key}` ? t(`godHints.${key}`) : LAW_HINTS[key])
                const isOpen = openHint === key
                const rawCur = laws[key]
                const curVal = (typeof rawCur === 'number' && !isNaN(rawCur)) ? rawCur : min
                const rawBase = baselineLaws[key]
                const baseVal = (typeof rawBase === 'number' && !isNaN(rawBase)) ? rawBase : undefined
                const isModified = modifiedKeys.has(key)
                const zone = getZone(curVal, baseVal, min, max)
                const pct = max === min ? 0 : ((curVal - min) / (max - min)) * 100
                const basePct = baseVal !== undefined && max !== min ? ((baseVal - min) / (max - min)) * 100 : null
                const fmt = (v: number | null | undefined) => {
                  if (v === null || v === undefined || isNaN(v)) return '—'
                  return step < 1 ? v.toFixed(step < 0.01 ? 3 : 2) : String(Math.round(v))
                }
                // highlight match
                const qLower = q
                const labelMatch = qLower && translatedLabel.toLowerCase().includes(qLower)
                return (
                  <div key={key} className={`god-law-row zone-${zone} ${isModified ? 'modified' : ''}`} style={{ borderBottom: '1px solid #21262d', padding: '10px 12px', background: isModified ? 'rgba(227,179,65,0.05)' : undefined }}>
                    <div className="god-law-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                      <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center', flex: 1, minWidth: 0 }}>
                        <span title={hint} style={{ color: isModified ? '#e3b341' : '#e6edf3', fontSize: 13, fontWeight: isModified ? 600 : 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', background: labelMatch ? 'rgba(227,179,65,0.2)' : undefined, padding: labelMatch ? '0 3px' : 0, borderRadius: 3 }}>
                          {translatedLabel}
                        </span>
                        {isModified && <span className="god-mod-dot" title={t('god.ui.modified_from_preset')}>●</span>}
                        {hint && (
                          <button
                            type="button"
                            className={`god-hint-btn ${isOpen ? 'active' : ''}`}
                            onClick={() => setOpenHint(isOpen ? null : key)}
                            title={hint}
                            aria-label={`hint for ${translatedLabel}`}
                          >
                            ?
                          </button>
                        )}
                      </span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flex: 'none' }}>
                        {isModified && (
                          <button onClick={() => revertOne(key)} title={t('god.ui.revert_title')} className="god-revert-btn">{t('god.ui.revert')}</button>
                        )}
                        <span className={`god-zone-pill zone-${zone}`} title={t('god.ui.zone_distance', { zone: t(`god.ui.zones.${zone}`) || zone })}>{t(`god.ui.zones.${zone}`) || zone}</span>
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
                          {basePct !== null && baseVal !== undefined && <span className="god-baseline-marker" style={{ left: `${basePct}%` }} title={`${t('god.ui.default_label', { val: fmt(baseVal) })}`} />}
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
                        <span className="god-baseline-text">{t('god.ui.default_label', { val: fmt(baseVal) })} · {curVal > baseVal ? `+${fmt(curVal - baseVal)}` : curVal < baseVal ? fmt(curVal - baseVal) : (t('god.ui.baseline') || 'baseline')}</span>
                        <span className="god-range-labels"><span>{fmt(min)}</span><span>{fmt(max)}</span></span>
                      </div>
                    )}
                    {isOpen && hint && (
                      <div className="god-hint-box">
                        {hint}
                        <div style={{ marginTop: 6 }}>
                          <a href="/docs/god-laws.md" rel="noreferrer" style={{ fontSize: 11, color: '#58a6ff' }}>{t('god.ui.open_docs')}</a>
                          {' · '}
                          <a href="/wiki#god-laws" style={{ fontSize: 11, color: '#58a6ff' }}>{t('god.ui.wiki_link')}</a>
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
                      {t('god.ui.laws_count', { count: visibleSpecs.length })}
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
                  <span className="god-domain-title">{domain.icon} {t(`god.domains.${domain.id}`) !== `god.domains.${domain.id}` ? t(`god.domains.${domain.id}`) : domain.label}</span>
                  <span className="god-domain-meta">{t('god.ui.groups_sections', { groups: groupSections.length, sections: groupSections.length })}</span>
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
