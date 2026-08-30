import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'

interface Plot {
  type: 'war' | 'schism'
  a: number
  b?: number
  a_name?: string
  b_name?: string
  progress: number
  max: number
  distance?: number
  unhappy?: number
  pop?: number
}

export default function PlotsPanel({ onSelectClan, state: _state }: { onSelectClan?: (id: number) => void; state?: any }) {
  const { t } = useI18n()
  const [plots, setPlots] = useState<Plot[]>([])
  useEffect(() => {
    let alive = true
    const load = () =>
      fetch('/api/plots')
        .then((r) => r.json())
        .then((d) => alive && setPlots(d.plots ?? []))
        .catch(() => {})
    load()
    const t = setInterval(() => {
      if (document.hidden) return
      load()
    }, 5000)
    const onVis = () => {
      if (!document.hidden) load()
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      alive = false
      clearInterval(t)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])
  if (plots.length === 0) return <p className="chip">{t('plots.noPlots')}</p>
  return (
    <div className="plots-panel">
      <h4 style={{ margin: '8px 0 6px', fontSize: '0.9em' }}>{t('plots.title')}</h4>
      <div style={{ display: 'grid', gap: 4 }}>
        {plots.map((pl, i) => (
          <div key={i} style={{ background: '#161b22', border: '1px solid #7e6325', borderRadius: 6, padding: '6px 8px' }}>
            <div className="chip" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>
                {pl.type === 'war' ? '⚔ ' : '💔 '}
                <button
                  className="chronicle-name"
                  onClick={() => onSelectClan?.(pl.a)}
                  title={t('chronicleEvents.showClan')}
                >
                  {pl.a_name ?? `#${pl.a}`}
                </button>
                {pl.type === 'war' && (
                  <>
                    {' → '}
                    <button
                      className="chronicle-name"
                      onClick={() => pl.b != null && onSelectClan?.(pl.b)}
                      title={t('chronicleEvents.showClan')}
                    >
                      {pl.b_name ?? `#${pl.b}`}
                    </button>
                  </>
                )}
                {pl.type === 'schism' && ` ${t('plots.schism')}`}
              </span>
              <span>
                {pl.progress}/{pl.max}
              </span>
            </div>
            <div style={{ height: 4, background: '#21262d', borderRadius: 2, marginTop: 4 }}>
              <div style={{ width: `${(pl.progress / pl.max) * 100}%`, height: '100%', background: pl.type === 'war' ? '#f85149' : '#e3b341', borderRadius: 2 }} />
            </div>
            {pl.type === 'war' && pl.distance != null && <div className="chip" style={{ marginTop: 2 }}>{t('plots.closest', { distance: pl.distance })}</div>}
            {pl.type === 'schism' && <div className="chip" style={{ marginTop: 2 }}>{t('plots.unhappy', { unhappy: pl.unhappy, pop: pl.pop })}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
