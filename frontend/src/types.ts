/** Mirrors backend/app/protocol.py. Keep in sync. */

export type EntityKind = 'creature' | 'food' | 'house'
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
  door_width?: number
  door_offset?: number
}

export interface StateMessage {
  type: 'state'
  tick: number
  width: number
  height: number
  boundary: 'wrap' | 'clamp'
  population: Record<string, number>
  entities: EntityState[]
}

export interface HelloMessage {
  type: 'hello'
  seed: number
  tick_rate: number
  width: number
  height: number
  boundary: 'wrap' | 'clamp'
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
  door_clearance?: number
  house_min_size?: number
  house_max_size?: number
}
