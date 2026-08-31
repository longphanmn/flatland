import type { EntityState } from '../types'
import { CASTE_COLORS } from '../render/renderCore'

export { CASTE_COLORS }

export const SIDES_COLORS: Record<number, string> = {
  2: CASTE_COLORS.Woman || '#ff9bce',
  3: CASTE_COLORS.Soldier || '#ff7b72',
  4: CASTE_COLORS.Gentleman || '#ffa657',
  5: CASTE_COLORS.Professional || '#d2a8ff',
  6: '#79c0ff',
  7: '#bc8cff',
  8: CASTE_COLORS.Noble || '#79c0ff',
  9: '#bc8cff',
  10: '#7ee787',
  24: CASTE_COLORS.Priest || '#e6edf3',
}

export interface CreatureAvatarProps {
  e?: Partial<EntityState> | null
  sides?: number
  shape?: string
  caste?: string
  color?: string
  clanColor?: string
  glyph?: string
  stage?: string
  scaleJitter?: number
  angleJitter?: number
  trait?: string
  infected?: boolean
  status?: string
  chill?: number
  size?: number
}

export function CreatureAvatar({
  e,
  sides: propSides,
  shape: propShape,
  caste: propCaste,
  color: propColor,
  clanColor: propClanColor,
  glyph: propGlyph,
  stage: propStage,
  scaleJitter: propScaleJitter,
  angleJitter: propAngleJitter,
  trait: propTrait,
  infected: propInfected,
  status: propStatus,
  chill: propChill,
  size = 76,
}: CreatureAvatarProps) {
  const caste = e?.caste ?? propCaste
  const sides = e?.sides ?? propSides ?? 4
  const shape = e?.shape ?? propShape ?? (sides === 2 ? 'line' : 'polygon')
  const isLine = shape === 'line' || sides === 2
  const isPriest = sides >= 24

  const color = propColor ?? (caste && CASTE_COLORS[caste]) ?? (isLine ? CASTE_COLORS.Woman : CASTE_COLORS[caste || ''] || '#8b949e')
  const clanColor = e?.clan_color ?? propClanColor ?? '#30363d'
  const glyph = e?.glyph ?? propGlyph
  const stage = e?.stage ?? propStage ?? 'adult'
  const scaleJitter = e?.scale_jitter ?? propScaleJitter ?? 1
  const angleJitter = e?.angle_jitter ?? propAngleJitter ?? 0
  const trait = e?.trait ?? propTrait
  const infected = e?.infected ?? propInfected
  const status = e?.status ?? propStatus
  const chill = e?.chill ?? propChill ?? 0

  const cx = 40
  const cy = 40
  const r = 18 * scaleJitter * (stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1)

  const points = isLine
    ? null
    : isPriest
      ? null
      : Array.from({ length: sides }, (_, i) => {
          const a = (i / sides) * Math.PI * 2 - Math.PI / 2 + angleJitter
          return `${cx + Math.cos(a) * r},${cy + Math.sin(a) * r}`
        }).join(' ')

  return (
    <div style={{ display: 'inline-flex', justifyContent: 'center', alignItems: 'center' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 80 80"
        style={{
          background: '#161b22',
          borderRadius: 8,
          border: `1px solid ${clanColor}`,
        }}
      >
        {clanColor && <circle cx={cx} cy={cy} r={r + 6} fill="none" stroke={clanColor} strokeWidth={1.2} opacity={0.9} />}
        {isLine ? (
          <line x1={cx - r * 1.3} y1={cy} x2={cx + r * 1.3} y2={cy} stroke={color} strokeWidth={3} strokeLinecap="round" />
        ) : isPriest ? (
          <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} />
        ) : (
          <polygon points={points!} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} strokeLinejoin="round" />
        )}
        {glyph && (
          <text
            x={cx}
            y={cy + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={r * 0.85}
            fill="#e6edf3"
            style={{ fontFamily: 'ui-monospace, monospace' }}
          >
            {glyph}
          </text>
        )}
        {infected && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#3fb950" stroke="#0d1117" strokeWidth={1} />}
        {status === 'starving' && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#f85149" stroke="#0d1117" strokeWidth={1} />}
        {status === 'hungry' && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#d29922" stroke="#0d1117" strokeWidth={1} />}
        {chill >= 12 && <circle cx={cx - 22} cy={cy - 22} r={4} fill="#79c0ff" stroke="#0d1117" strokeWidth={1} />}
        {trait && size >= 60 && (
          <text x={cx} y={72} textAnchor="middle" fontSize={7} fill="#8b949e">
            {trait === 'greedy' ? '⬔ greedy' : trait === 'peaceful' ? '◯ peaceful' : trait === 'paranoid' ? '⬥ paranoid' : trait === 'bold' ? '▲ bold' : trait}
          </text>
        )}
      </svg>
    </div>
  )
}

export default CreatureAvatar
