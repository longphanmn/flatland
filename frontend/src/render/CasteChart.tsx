import { CASTE_COLORS } from '../render/CanvasRenderer'

interface Props {
  history: Array<Record<string, number>>
  showLegend?: boolean
}

/** Stacked-line population history per caste, client-side only. */
export default function CasteChart({ history, showLegend = true }: Props) {
  if (history.length < 2) {
    return <p className="chip">collecting history…</p>
  }
  const castes = Object.keys(CASTE_COLORS).filter((c) =>
    history.some((h) => (h[c] ?? 0) > 0),
  )
  const max = Math.max(
    1,
    ...history.map((h) => Object.values(h).reduce((a, b) => a + b, 0)),
  )
  const W = 100
  const H = 46
  return (
    <div className="caste-chart">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {castes.map((caste) => {
          const pts = history
            .map((h, i) => {
              const x = (i / (history.length - 1)) * W
              // stacked: sum of this caste and all below it
              const idx = castes.indexOf(caste)
              const yVal = castes
                .slice(0, idx + 1)
                .reduce((acc, cc) => acc + (h[cc] ?? 0), 0)
              const y = H - (yVal / max) * H
              return `${x.toFixed(2)},${y.toFixed(2)}`
            })
            .join(' ')
          return (
            <polyline
              key={caste}
              points={pts}
              fill="none"
              stroke={CASTE_COLORS[caste]}
              strokeWidth={0.9}
            />
          )
        })}
      </svg>
      {showLegend && (
        <div className="caste-legend">
          {castes.map((c) => (
            <span key={c} className="chip">
              <span className="dot-inline" style={{ background: CASTE_COLORS[c] }} />
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
