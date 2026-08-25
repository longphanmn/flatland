/** §AP Sacred Avatars of the Sphere — mirrors backend TOTEM_BUFF/TOTEM_SPEC
 * (simulation.py). Each clan bears one avatar: a 2D projection of the One True
 * God with a distinct divine aspect. */
export interface TotemInfo {
  emoji: string
  color: string
  buff: string
}

export const TOTEMS: Record<string, TotemInfo> = {
  'Radiant Circle': { emoji: '⭕', color: '#f2cc60', buff: "God's Abundance — +30% harvest, +20% fertility" },
  'Celestial Strike': { emoji: '⚡', color: '#ffa657', buff: "God's Wrath & Justice — +25% warrior damage" },
  'All-Seeing Vertex': { emoji: '👁️', color: '#d2a8ff', buff: "God's Omniscience — +40% sight, sees clearly at night" },
  'Indomitable Monolith': { emoji: '🛡️', color: '#79c0ff', buff: "God's Permanence — -30% damage taken, resists the cold" },
  'Sacred Spiral': { emoji: '🌿', color: '#3fb950', buff: "God's Renewal — herbs heal twice, faster plague recovery, composts the dead" },
  'Cosmic Scales': { emoji: '⚖️', color: '#e6edf3', buff: "God's Equilibrium — reliable peace treaties; keeps the law even while starving" },
  'Dimensional Rift': { emoji: '🌀', color: '#58a6ff', buff: "God's Ascent — faster Isosceles promotion, adaptive mutations, elder lore" },
  'Eternal Hearth': { emoji: '🕯️', color: '#ff9bce', buff: "God's Sanctuary — warm hearths, calm through the night" },
}

/** Complementary aspects sympathise (§AP holy alliances) — mirrors AVATAR_ALLIES. */
export const AVATAR_ALLIES: Record<string, string> = {
  'Radiant Circle': 'Sacred Spiral',
  'Celestial Strike': 'All-Seeing Vertex',
  'Indomitable Monolith': 'Eternal Hearth',
  'Cosmic Scales': 'Dimensional Rift',
}

export function totemEmoji(name: string | null | undefined): string {
  return (name && TOTEMS[name]?.emoji) || ''
}
