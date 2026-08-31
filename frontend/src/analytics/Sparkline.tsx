import { useI18n } from '../i18n'

interface Props {
  data?: number[]
  color?: string
  height?: number
  width?: number | string
  unit?: string
  showLast?: boolean
}

export default function Sparkline({
  data = [],
  color = '#79c0ff',
  height = 40,
  width = '100%',
  unit = '',
  showLast = true,
}: Props) {
  const { t } = useI18n()
  if (!data || data.length < 2) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#8b949e',
          fontSize: 10,
          background: '#0d1117',
          borderRadius: 6,
          border: '1px solid #21262d',
        }}
      >
        {t('analytics.collecting')}
      </div>
    )
  }

  // Decimate points if holding large history (e.g. 6000 ticks)
  let displayData = data
  if (data.length > 500) {
    const step = Math.ceil(data.length / 500)
    displayData = data.filter((_, i) => i % step === 0)
    if (displayData[displayData.length - 1] !== data[data.length - 1]) {
      displayData.push(data[data.length - 1])
    }
  }

  const w = 280
  const h = height
  const pad = 6
  const min = Math.min(...displayData)
  const max = Math.max(...displayData)
  const range = max - min || 1
  const stepPx = (w - pad * 2) / (displayData.length - 1)
  const points = displayData
    .map(
      (v, i) =>
        `${pad + i * stepPx},${h - pad - ((v - min) / range) * (h - pad * 2)}`
    )
    .join(' ')

  const last = data[data.length - 1]
  const formattedLast =
    typeof last === 'number'
      ? last >= 1000
        ? `${(last / 1000).toFixed(1)}k`
        : Number.isInteger(last)
        ? last
        : last.toFixed(2)
      : last

  return (
    <div style={{ position: 'relative', width }}>
      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        preserveAspectRatio="none"
        style={{
          display: 'block',
          background: '#0d1117',
          borderRadius: 6,
          border: '1px solid #21262d',
        }}
      >
        <polyline fill="none" stroke={color} strokeWidth={1.6} points={points} />
      </svg>
      {showLast && (
        <span
          style={{
            position: 'absolute',
            right: 6,
            top: 4,
            fontSize: 10,
            color,
            fontWeight: 700,
            background: 'rgba(13, 17, 23, 0.8)',
            padding: '1px 4px',
            borderRadius: 4,
          }}
        >
          {formattedLast}
          {unit}
        </span>
      )}
    </div>
  )
}
