/** Mirrors backend/app/protocol.py. Keep in sync. */

export type EntityKind = 'creature' | 'food' | 'house' | 'corpse'
export type EntityShape = 'polygon' | 'line'
export type HungerStatus = '' | 'hungry' | 'starving'

export interface EntityState {
  id: number
  kind: EntityKind
  x: number
  y: number
  angle: number
  shape?: EntityShape
  sides?: number
  caste?: string
  energy?: number
  size?: number
  status?: HungerStatus
  radius?: number
  age?: number
  lifespan?: number
  stage?: 'infant' | 'juvenile' | 'adult' | 'elder'
  irregularity?: number
  health?: number
  infected?: boolean
  meals?: number
  clan_id?: number
  clan_color?: string
  is_predator?: boolean
  sleeping?: boolean
  indoors?: boolean
  generation?: number
  born_tick?: number
  door_width?: number
  door_offset?: number
  door_side?: 'north' | 'east' | 'south' | 'west'
  is_ruin?: boolean
  abandoned_ticks?: number
  growth?: number
  variant?: 'grass' | 'berry' | 'mushroom' | 'poisonous'
  sex?: 'male' | 'female'
  mother_id?: number
  father_id?: number
}

export interface StateMessage {
  type: 'state'
  tick: number
  seed: number
  width: number
  height: number
  boundary: 'wrap' | 'clamp'
  population: Record<string, number>
  entities: EntityState[]
  creatures_alive: number
  creatures_dead: number
  dead_by_cause: Record<string, number>
  infected_count: number
  time_of_day: number
  day: number
  season: 'spring' | 'summer' | 'autumn' | 'winter'
  weather: 'clear' | 'rain' | 'fog' | 'storm'
  terrain_fertile: { x: number; y: number; r: number }[]
  terrain_rocks: { x: number; y: number; r: number }[]
  events: HistoryEvent[]
}

export interface HistoryEvent {
  /** Present only on events fetched from GET /api/history; absent on live-streamed ones. */
  id?: number
  type: 'death' | 'birth' | 'promotion' | 'demotion' | 'outbreak' | 'recovery' | 'bloom' | 'alliance' | 'rivalry' | 'predation' | 'war' | 'ruin' | 'settlement'
  tick: number
  entity_id: number
  caste?: string | null
  cause?: string
  x: number
  y: number
  payload?: Record<string, unknown>
}

export interface HelloMessage {
  type: 'hello'
  seed: number
  tick_rate: number
  width: number
  height: number
  boundary: 'wrap' | 'clamp'
}

/** One row of GET /api/worlds — a past or current world run. */
export interface WorldSummary {
  id: number
  seed: number
  width: number
  height: number
  boundary: 'wrap' | 'clamp'
  started_at: string
  ended_at: string | null
}

/** House wall segments for rendering; mirrors backend _house_wall_segments. */
export function houseWallSegments(
  x: number,
  y: number,
  size: number,
  side: string,
  doorWidth: number,
  doorOffset: number,
): [number, number, number, number][] {
  const h = size / 2
  const x0 = x - h
  const x1 = x + h
  const y0 = y - h
  const y1 = y + h
  const d = doorWidth / 2
  const cx = x + doorOffset
  const cy = y + doorOffset
  switch (side) {
    case 'north':
      return [
        [x0, y0, cx - d, y0],
        [cx + d, y0, x1, y0],
        [x0, y0, x0, y1],
        [x1, y0, x1, y1],
        [x0, y1, x1, y1],
      ]
    case 'west':
      return [
        [x0, y0, x1, y0],
        [x0, y1, x1, y1],
        [x1, y0, x1, y1],
        [x0, y0, x0, cy - d],
        [x0, cy + d, x0, y1],
      ]
    case 'east':
      return [
        [x0, y0, x1, y0],
        [x0, y0, x0, y1],
        [x0, y1, x1, y1],
        [x1, y0, x1, cy - d],
        [x1, cy + d, x1, y1],
      ]
    default: // south
      return [
        [x0, y0, x1, y0],
        [x0, y0, x0, y1],
        [x1, y0, x1, y1],
        [x0, y1, cx - d, y1],
        [cx + d, y1, x1, y1],
      ]
  }
}

export type ControlAction = 'pause' | 'resume' | 'step' | 'reset' | 'set_speed'

export interface ControlMessage {
  action: ControlAction
  value?: number
}

/** Laws of nature god may set — never per-creature interventions. */
export interface GodLaws {
  boundary?: 'wrap' | 'clamp'
  food_count?: number
  plant_growth_rate?: number
  plant_spread_rate?: number
  nutrient_cycle_rate?: number
  plant_variants_enabled?: boolean
  poison_rate?: number
  energy_max?: number
  energy_decay_per_tick?: number
  energy_from_food?: number
  hungry_ratio?: number
  starving_ratio?: number
  perceive_radius?: number
  eat_radius?: number
  wander_turn?: number
  steer_turn?: number
  hungry_perceive_mult?: number
  desperate_perceive_mult?: number
  desperate_speed_mult?: number
  lifespan_mult?: number

  // Reproduction & inheritance (Nature's Law)
  birth_enabled?: boolean
  adult_age?: number
  mate_radius?: number
  mate_energy_min?: number
  birth_rate?: number
  sex_ratio?: number
  mutation_rate?: number
  max_sides?: number
  birth_energy_cost?: number
  reproduction_cooldown?: number
  carrying_capacity?: number
  max_population?: number
  euthanasia_threshold?: number

  // Health & disease
  disease_enabled?: boolean
  disease_outbreak_rate?: number
  disease_rate?: number
  disease_radius?: number
  disease_energy_drain?: number
  recovery_rate?: number
  disease_lethality?: number

  // Environment: sky, seasons, weather
  day_length?: number
  season_length?: number
  night_sight_mult?: number
  weather_enabled?: boolean
  weather_change_rate?: number
  fog_sight_mult?: number
  rain_speed_mult?: number
  storm_wander_bonus?: number
  sleep_enabled?: boolean
  sleep_energy_mult?: number

  // Shelter — roofs against the sky
  shelter_enabled?: boolean
  exposure_drain?: number
  house_capacity?: number
  house_claim_enabled?: boolean
  rest_recovery_mult?: number
  house_decay_ticks?: number

  door_clearance?: number
  house_min_size?: number
  house_max_size?: number

  // Predation (§I)
  predation_enabled?: boolean
  predator_ratio?: number
  hunt_radius?: number
  bite_damage?: number
  bite_cooldown?: number
  energy_from_prey?: number
  fear_radius?: number

  // Clan war (§I)
  war_enabled?: boolean
  attack_radius?: number
  attack_damage?: number

  // Society — interaction
  cohesion_weight?: number
  alignment_weight?: number
  separation_weight?: number
  flock_radius?: number
  relation_drift_rate?: number
  alliance_threshold?: number
  rivalry_threshold?: number
}
