import { useI18n } from '../i18n'

interface Props {
  history: Array<Record<string, number>>
  showLegend?: boolean
}

const TROPHIC_COLORS: Record<string, string> = {
  Food: '#3fb950',
  Herbivore: '#90be6d',
  Predator: '#ff3838',
  Corpse: '#6e7681',
}

/** Trophic pyramid history: plants → herbivores → predators, client-side only. */
export default function TrophicChart({ history, showLegend = true }: Props) {
  const { t } = useI18n()
  if (history.length < 2) return <p className="chip">{t('charts.collectingTrophic')}</p>
  const trophics = ['Food', 'Herbivore', 'Predator'] as const
  // only show those that ever appeared
  const shown = trophics.filter((k) => history.some((h) => (h[k] ?? 0) > 0))
  if (shown.length === 0) return <p className="chip">{t('charts.noTrophic')}</p>
  const max = Math.max(1, ...history.map((h) => shown.reduce((a, k) => a + (h[k] ?? 0), 0)))
  const W = 100
  const H = 46
  return (
    <div className="caste-chart">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {shown.map((k) => {
          const pts = history
            .map((h, i) => {
              const x = (i / (history.length - 1)) * W
              const idx = shown.indexOf(k)
              const yVal = shown.slice(0, idx + 1).reduce((acc, cc) => acc + (h[cc] ?? 0), 0)
              const y = H - (yVal / max) * H
              return `${x.toFixed(2)},${y.toFixed(2)}`
            })
            .join(' ')
          return <polyline key={k} points={pts} fill="none" stroke={TROPHIC_COLORS[k]} strokeWidth={0.9} />
        })}
      </svg>
      {showLegend !== false && (
        <div className="caste-legend">
          {shown.map((k) => (
            <span key={k} className="chip">
              <span className="dot-inline" style={{ background: TROPHIC_COLORS[k] }} />
              {k}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
