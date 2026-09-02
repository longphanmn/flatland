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

function pseudoRand(seed: number, i: number): number {
  const x = Math.sin(seed * 127.1 + i * 311.7) * 43758.5453
  return x - Math.floor(x)
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
  const sidesRaw = (e as any)?.morph_k ?? e?.sides ?? propSides ?? 4
  const sidesClamped = Math.max(3, Math.min(24, sidesRaw))
  const sides = sidesClamped
  const shape = e?.shape ?? propShape ?? (sides === 2 ? 'line' : 'polygon')
  const isLine = shape === 'line' || sides === 2 || (e as any)?.shape === 'line'
  const isPriest = sides >= 24

  const color = propColor ?? (caste && CASTE_COLORS[caste]) ?? (isLine ? CASTE_COLORS.Woman : CASTE_COLORS[caste || ''] || '#8b949e')
  const clanColor = e?.clan_color ?? propClanColor ?? '#30363d'
  const glyph = e?.glyph ?? propGlyph
  const stage = e?.stage ?? propStage ?? 'adult'
  const scaleJitter = (e as any)?.scale_jitter ?? propScaleJitter ?? 1
  const angleJitter = (e as any)?.angle_jitter ?? propAngleJitter ?? 0
  const trait = (e as any)?.trait ?? propTrait
  const infected = e?.infected ?? propInfected
  const status = e?.status ?? propStatus
  const chill = (e as any)?.chill ?? propChill ?? 0

  const irregularity: number = (e as any)?.irregularity ?? 0
  const isoAngle: number | undefined = (e as any)?.iso_angle
  const morphTraits: number[] | undefined = (e as any)?.morph_traits
  const generation: number = (e as any)?.generation ?? 0
  const idSeed: number = (e as any)?.id ?? 1

  const cx = 40
  const cy = 40
  const r = 18 * scaleJitter * (stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1)

  // Derive morph metrics for phenotypes
  const area = morphTraits && morphTraits.length > 0 ? morphTraits[0] : 2.0
  const izz = morphTraits && morphTraits.length > 2 ? morphTraits[2] : 0.3
  const thetaMin = morphTraits && morphTraits.length > 3 ? morphTraits[3] : (sides >= 3 ? (sides - 2) * Math.PI / sides : Math.PI / 3)
  const dmult = morphTraits && morphTraits.length > 5 ? morphTraits[5] : Math.max(0, (Math.cos(thetaMin) - 0.5) / 0.5)
  const isSoldierRazor = caste === 'Soldier' && sides === 3 && typeof isoAngle === 'number' && isoAngle < 59.9
  const hasArmor = (izz > 0.65 || area > 3.0) && !isLine && !isPriest
  const specBase = Math.max(irregularity * 1.8, generation > 40 ? Math.max(0, 1 - (1 - (generation - 15) / 250)) : 0)
  const specIntensity = specBase * ((sides >= 7 || irregularity > 0.25) ? 1 : 0.5)
  const hasSpeciation = specIntensity > 0.42 && !isLine
  const hasGlint = dmult > 0.18 && !isLine
  const hasNucleus = stage === 'elder' && generation >= 10 && !isLine

  // Build main polygon points
  let pointsStr: string | null = null
  let womanPointsStr: string | null = null
  let glintPos: [number, number] | null = null
  let ptsArray: Array<[number, number]> = []

  if (isLine) {
    // BG-3 variable thickness needle diamond
    const len = r * 1.3
    const perimFactor = morphTraits && morphTraits[1] ? Math.max(0.7, Math.min(1.9, morphTraits[1] / 5.657)) : 1
    const wMid = Math.max(1.2, r * 0.30 * perimFactor * (0.85 + irregularity * 0.9))
    const ax = Math.cos(angleJitter), ay = Math.sin(angleJitter)
    const px = -ay, py = ax
    const fx = cx + ax * len, fy = cy + ay * len
    const bx = cx - ax * len * 0.92, by = cy - ay * len * 0.92
    const tx = cx + px * wMid, ty = cy + py * wMid
    const bx2 = cx - px * wMid, by2 = cy - py * wMid
    womanPointsStr = `${fx},${fy} ${tx},${ty} ${bx},${by} ${bx2},${by2}`
  } else if (isPriest) {
    // circle handled separately
    if (irregularity > 0.08) {
      const pts: Array<[number, number]> = []
      for (let i = 0; i < sides; i++) {
        const aJ = (pseudoRand(idSeed, i * 2) - 0.5) * Math.min(0.3, irregularity) * 0.65
        const rJ = 1 + (pseudoRand(idSeed, i * 2 + 1) - 0.5) * Math.min(0.3, irregularity) * 0.5
        const a = (i / sides) * Math.PI * 2 - Math.PI / 2 + angleJitter + aJ
        const rr = r * rJ
        pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr])
      }
      ptsArray = pts
      pointsStr = pts.map(([x, y]) => `${x},${y}`).join(' ')
      // glint from sharpest
      if (hasGlint) {
        let best = 999, bx = pts[0][0], by = pts[0][1]
        for (let i = 0; i < pts.length; i++) {
          const im1 = (i - 1 + pts.length) % pts.length, ip1 = (i + 1) % pts.length
          const ux = pts[im1][0] - pts[i][0], uy = pts[im1][1] - pts[i][1]
          const vx = pts[ip1][0] - pts[i][0], vy = pts[ip1][1] - pts[i][1]
          const nu = Math.hypot(ux, uy), nv = Math.hypot(vx, vy)
          if (nu < 1e-6 || nv < 1e-6) continue
          const av = Math.acos(Math.max(-1, Math.min(1, (ux * vx + uy * vy) / (nu * nv))))
          if (av < best) { best = av; bx = pts[i][0]; by = pts[i][1] }
        }
        glintPos = [bx, by]
      }
    }
  } else if (isSoldierRazor) {
    const theta = Math.max(8, Math.min(59.8, isoAngle!)) * Math.PI / 180
    const xr = r * 1.05, xb = r * 0.55
    const dx = xr + xb
    const yb = dx * Math.tan(theta / 2)
    const local: Array<[number, number]> = [
      [xr, 0],
      [-xb, yb],
      [-xb, -yb],
    ]
    const ca = Math.cos(angleJitter), sa = Math.sin(angleJitter)
    const pts = local.map(([lx, ly]) => [cx + lx * ca - ly * sa, cy + lx * sa + ly * ca] as [number, number])
    ptsArray = pts
    pointsStr = pts.map(([x, y]) => `${x},${y}`).join(' ')
    if (hasGlint) glintPos = pts[0]
  } else {
    // BG-2 mutated polygon & BG-4 topological aberration
    const useMutated = irregularity > 0.02
    const pts: Array<[number, number]> = []
    if (useMutated) {
      for (let i = 0; i < sides; i++) {
        const aJ = (pseudoRand(idSeed, i * 2) - 0.5) * irregularity * 0.65
        const rJ = 1 + (pseudoRand(idSeed, i * 2 + 1) - 0.5) * irregularity * 0.9
        const a = (i / sides) * Math.PI * 2 - Math.PI / 2 + angleJitter + aJ
        const rr = r * rJ
        pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr])
      }
    } else {
      for (let i = 0; i < sides; i++) {
        const a = (i / sides) * Math.PI * 2 - Math.PI / 2 + angleJitter
        pts.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r])
      }
    }
    ptsArray = pts
    pointsStr = pts.map(([x, y]) => `${x},${y}`).join(' ')
    if (hasGlint) {
      let best = 999, bx = pts[0][0], by = pts[0][1]
      for (let i = 0; i < pts.length; i++) {
        const im1 = (i - 1 + pts.length) % pts.length, ip1 = (i + 1) % pts.length
        const ux = pts[im1][0] - pts[i][0], uy = pts[im1][1] - pts[i][1]
        const vx = pts[ip1][0] - pts[i][0], vy = pts[ip1][1] - pts[i][1]
        const nu = Math.hypot(ux, uy), nv = Math.hypot(vx, vy)
        if (nu < 1e-6 || nv < 1e-6) continue
        const av = Math.acos(Math.max(-1, Math.min(1, (ux * vx + uy * vy) / (nu * nv))))
        if (av < best) { best = av; bx = pts[i][0]; by = pts[i][1] }
      }
      glintPos = [bx, by]
    }
  }

  // Speciation offset points (chromatic)
  let specPointsA: string | null = null
  let specPointsB: string | null = null
  if (hasSpeciation && ptsArray.length) {
    const offA: Array<[number, number]> = ptsArray.map(([x, y]) => [x + 0.9, y + 0.6] as [number, number])
    const offB: Array<[number, number]> = ptsArray.map(([x, y]) => [x - 0.8, y - 0.5] as [number, number])
    specPointsA = offA.map(([x, y]) => `${x},${y}`).join(' ')
    specPointsB = offB.map(([x, y]) => `${x},${y}`).join(' ')
  }

  // Armor inner polygon
  let armorPointsStr: string | null = null
  if (hasArmor && ptsArray.length) {
    const innerR = 0.78
    const cpts: Array<[number, number]> = ptsArray.map(([x, y]) => {
      const dx = x - cx, dy = y - cy
      return [cx + dx * innerR, cy + dy * innerR] as [number, number]
    })
    armorPointsStr = cpts.map(([x, y]) => `${x},${y}`).join(' ')
  }

  // Nucleus inner polygon
  let nucleusPointsStr: string | null = null
  if (hasNucleus && ptsArray.length) {
    const inner = 0.38
    const cpts: Array<[number, number]> = ptsArray.map(([x, y]) => {
      const dx = x - cx, dy = y - cy
      return [cx + dx * inner, cy + dy * inner] as [number, number]
    })
    nucleusPointsStr = cpts.map(([x, y]) => `${x},${y}`).join(' ')
  }

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
          <polygon points={womanPointsStr!} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.1} strokeLinejoin="round" />
        ) : isPriest ? (
          pointsStr ? (
            <>
              <polygon points={pointsStr} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} strokeLinejoin="round" />
              {hasArmor && <circle cx={cx} cy={cy} r={r * 0.78} fill={color} fillOpacity={0.10} stroke={color} strokeWidth={0.9} opacity={0.6} />}
            </>
          ) : (
            <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} />
          )
        ) : (
          <>
            {hasSpeciation && specPointsA && specPointsB && (
              <>
                <polygon points={specPointsA} fill="none" stroke="#d2a8ff" strokeWidth={0.7} opacity={0.45 * Math.min(1, specIntensity)} strokeLinejoin="round" />
                <polygon points={specPointsB} fill="none" stroke="#79c0ff" strokeWidth={0.7} opacity={0.38 * Math.min(1, specIntensity)} strokeLinejoin="round" />
              </>
            )}
            <polygon points={pointsStr!} fill={color} fillOpacity={hasArmor ? 0.30 : 0.22} stroke={color} strokeWidth={hasArmor ? 1.6 : 1.2} strokeLinejoin="round" />
            {armorPointsStr && (
              <polygon points={armorPointsStr} fill={color} fillOpacity={0.11} stroke={color} strokeWidth={0.9} opacity={0.55} strokeLinejoin="round" />
            )}
            {hasGlint && glintPos && (
              <g>
                <circle cx={glintPos[0]} cy={glintPos[1]} r={1.6 + dmult * 1.2} fill="#ffe08a" opacity={0.9} />
                <circle cx={glintPos[0]} cy={glintPos[1]} r={0.55} fill="#ffffff" opacity={0.95} />
              </g>
            )}
            {nucleusPointsStr && (
              <g>
                <polygon points={nucleusPointsStr} fill={color} fillOpacity={0.18} stroke="#e6edf3" strokeWidth={0.7} opacity={0.6} strokeLinejoin="round" />
                {glyph && (
                  <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fontSize={r * 0.42} fill="#e6edf3" style={{ fontFamily: 'ui-monospace, monospace' }}>
                    {glyph}
                  </text>
                )}
              </g>
            )}
          </>
        )}
        {/* always show glyph centered for line & priest too, but nucleus already handles */}
        {glyph && !hasNucleus && (
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
        {hasNucleus && isPriest && glyph && (
          <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fontSize={r * 0.42} fill="#e6edf3" style={{ fontFamily: 'ui-monospace, monospace' }}>
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
