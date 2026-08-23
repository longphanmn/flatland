/** Totem registry — mirrors backend TOTEM_BUFF/TOTEM_SPEC (simulation.py). */
export interface TotemInfo {
  emoji: string
  color: string
  buff: string
}

export const TOTEMS: Record<string, TotemInfo> = {
  Wolf: { emoji: '🐺', color: '#ff7b72', buff: 'hunts farther, faster in the chase' },
  Tree: { emoji: '🌳', color: '#3fb950', buff: '+25% harvest' },
  Shield: { emoji: '🛡️', color: '#79c0ff', buff: '-30% damage taken, heals faster' },
  Eye: { emoji: '👁️', color: '#d2a8ff', buff: '+25% sight' },
  Bear: { emoji: '🐻', color: '#a67c52', buff: '-20% damage, sturdy cubs' },
  Stag: { emoji: '🦌', color: '#f2cc60', buff: 'quicker, +15% fertility' },
  Owl: { emoji: '🦉', color: '#d29922', buff: '+35% sight' },
  Rabbit: { emoji: '🐇', color: '#ff9bce', buff: '+25% fertility' },
  Boar: { emoji: '🐗', color: '#f85149', buff: '+15% harvest, -10% damage' },
  Fox: { emoji: '🦊', color: '#ffa657', buff: 'hunts much farther, a little quicker' },
  Raven: { emoji: '🐦‍⬛', color: '#8b949e', buff: '+15% sight, +10% harvest' },
  Serpent: { emoji: '🐍', color: '#56d364', buff: '-15% damage, a little quicker' },
}

export function totemEmoji(name: string | null | undefined): string {
  return (name && TOTEMS[name]?.emoji) || ''
}
