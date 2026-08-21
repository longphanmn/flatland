/** Mirrors backend/app/protocol.py. Keep in sync. */

export type EntityKind = 'creature' | 'food' | 'house'
export type EntityShape = 'polygon' | 'line'

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
