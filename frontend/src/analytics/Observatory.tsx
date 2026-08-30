import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'

interface Props {
  state?: any
}

export default function Observatory({ state }: Props) {
  const {} = useI18n()
  const [data, setData] = useState<any>(null)

  // Prefer WS analytics if present, else fetch
  useEffect(() => {
    if (state?.analytics) {
      setData(state.analytics)
      return
    }
    let alive = true
    const load = () =>
      fetch('/api/analytics/summary')
        .then((r) => r.json())
        .then((d) => alive && setData(d))
        .catch(() => {})
    load()
    // 30s fallback poll when no WS analytics (low frequency)
    const iv = setInterval(() => { if (!document.hidden) load() }, 30000)
    return () => { alive = false; clearInterval(iv) }
  }, [state])

  if (!data || data.error) {
    return <p className="chip">Analytics — gathering…</p>
  }

  const ring = data.ring ?? {}
  const trophic = data.trophic ?? {}
  const biodiv = data.biodiversity ?? {}
  const famine = data.famine ?? {}
  const extinction = data.extinction ?? {}
  const unrest = data.unrest ?? {}
  const hegemony = data.hegemony ?? {}
  const gini = data.gini ?? {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11 }}>
      <h4 style={{ margin: '4px 0', fontSize: 12 }}>🔭 Observatory — tick {data.tick}</h4>

      {/* Macro sparklines */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '6px 8px' }}>
        <div style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Population · Biomass · Saturation</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 4 }}>
          <span className="chip" style={{ justifyContent: 'space-between' }}>Pop <b>{ring.population?.[ring.population.length-1] ?? '—'}</b></span>
          <span className="chip" style={{ justifyContent: 'space-between' }}>Bio <b>{ring.biomass?.[ring.biomass.length-1] ?? '—'}</b></span>
          <span className="chip" style={{ justifyContent: 'space-between' }}>E sat <b>{ring.energy_saturation?.[ring.energy_saturation.length-1] ?? '—'}</b></span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 6 }}>
          <span className="chip" style={{ justifyContent: 'space-between' }}>Birth/min <b>{ring.birth_velocity?.[ring.birth_velocity.length-1] ?? '—'}</b></span>
          <span className="chip" style={{ justifyContent: 'space-between' }}>Death/min <b>{ring.death_velocity?.[ring.death_velocity.length-1] ?? '—'}</b></span>
        </div>
      </div>

      {/* Mortality */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '6px 8px' }}>
        <div style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Mortality · 500-tick dist</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
          {Object.entries(data.mortality?.distribution ?? {}).map(([k, v]: any) => (
            <span key={k} className="chip" style={{ fontSize: 10 }}>{k} {(v*100).toFixed(0)}%</span>
          ))}
        </div>
      </div>

      {/* Trophic */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '6px 8px' }}>
        <div style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Lotka-Volterra · Biodiversity</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 4 }}>
          <span className="chip">🌿 {trophic.plant_biomass ?? '—'}</span>
          <span className="chip">🦌 {trophic.herbivores ?? '—'}</span>
          <span className="chip">🐺 {trophic.predators ?? '—'}</span>
        </div>
        <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>
          <span className="chip">Shannon {biodiv.shannon ?? '—'}</span>
          <span className="chip">Even {biodiv.evenness ?? '—'}</span>
          <span className="chip">Rich {biodiv.richness ?? '—'}</span>
        </div>
      </div>

      {/* Hegemony + Gini */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '6px 8px' }}>
        <div style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Hegemony · Gini</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 4 }}>
          <span className="chip">HHI {hegemony.hhi ?? '—'}</span>
          <span className="chip">Lar Gini {gini.larder_gini ?? '—'}</span>
        </div>
      </div>

      {/* Warnings */}
      <div style={{ background: unrest.schism_risk ? '#2a1a1a' : '#161b22', border: `1px solid ${unrest.schism_risk ? '#f85149' : '#30363d'}`, borderRadius: 6, padding: '6px 8px' }}>
        <div style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Famine · Extinction · Unrest</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 4 }}>
          <span className="chip" style={{ color: famine.horizon_ticks < 200 ? '#f85149' : '#8b949e' }}>Famine {famine.horizon_ticks ?? '∞'}t</span>
          <span className="chip" style={{ color: extinction.alarm ? '#f85149' : '#3fb950' }}>Ne {extinction.Ne ?? '—'}</span>
          <span className="chip" style={{ color: unrest.schism_risk ? '#f85149' : '#8b949e' }}>Unrest {unrest.unrest_score ?? 0}</span>
          <span className="chip">Fertile {extinction.fertile_females ?? '—'}♀</span>
        </div>
        {(extinction.alarm || unrest.schism_risk) && (
          <div style={{ marginTop: 4, color: '#f85149', fontWeight: 600 }}>⚠ {extinction.alarm ? 'Extinction cliff! ' : ''}{unrest.schism_risk ? 'Schism risk!' : ''}</div>
        )}
      </div>
    </div>
  )
}
