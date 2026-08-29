import { useEffect, useState } from 'react'
import { godFetch } from '../god/auth'
import { useI18n } from '../i18n'

type WikiData = {
  laws: string[]
  routes: string[]
  presets: Record<string, Record<string, any>>
  law_details: Record<string, { type: string; default: any; hint?: string }>
  overview: string
}

export default function Wiki({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n()
  const [data, setData] = useState<WikiData | null>(null)
  const [tab, setTab] = useState<'guide' | 'book' | 'api' | 'laws' | 'presets'>('guide')
  const [q, setQ] = useState('')
  const [laws, setLaws] = useState<Record<string, any> | null>(null)
  const [presetFeedback, setPresetFeedback] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    fetch('/api/wiki').then(r => r.json()).then(setData).catch(() => {})
    fetch('/api/laws').then(r => r.json()).then(setLaws).catch(() => {})
  }, [open])

  if (!open) return null

  const activePreset =
    (laws?.food_count === 240 && laws?.carrying_capacity === 350) || (laws?.food_count === 220 && laws?.carrying_capacity === 600)
      ? 'balance'
      : (laws?.food_count === 360 && laws?.carrying_capacity === 450) || (laws?.food_count === 450 && laws?.carrying_capacity === 2200)
      ? 'sustainable'
      : laws?.food_count === 320 && laws?.carrying_capacity === 400
      ? 'theocracy'
      : laws?.food_count === 290 && laws?.carrying_capacity === 380
      ? 'warlords'
      : (laws?.food_count === 280 && laws?.carrying_capacity === 350) || (laws?.food_count === 320 && laws?.carrying_capacity === 800)
      ? 'chaos'
      : (laws?.food_count === 120 && laws?.carrying_capacity === 180) || (laws?.food_count === 100 && laws?.carrying_capacity === 250)
      ? 'extinction'
      : (laws?.food_count === 500 && laws?.carrying_capacity === 800) || (laws?.food_count === 650 && laws?.carrying_capacity === 3500)
      ? 'boom'
      : null

  const applyPreset = async (name: string, reset: boolean = false) => {
    try {
      const r = await godFetch(`/api/presets/${name}?persist=true${reset ? '&reset=true' : ''}`, { method: 'POST' })
      if (r.ok) {
        setPresetFeedback(`✓ ${name} preset applied${reset ? ' (world reset)' : ''}`)
        fetch('/api/laws').then(res => res.json()).then(setLaws).catch(() => {})
      } else {
        setPresetFeedback(`✗ Failed to apply ${name}`)
      }
      setTimeout(() => setPresetFeedback(null), 3000)
    } catch {
      /* cancelled */
    }
  }

  // filter helpers
  const match = (s: string) => !q || s.toLowerCase().includes(q.toLowerCase())

  return (
    <div className="wiki-backdrop" onClick={onClose}>
      <div className="wiki-panel" onClick={e => e.stopPropagation()}>
        <header className="god-head" style={{ position: 'sticky', top: 0, background: '#0d1117', zIndex: 1, paddingBottom: 8 }}>
          <h2>{t('wiki.title')}</h2>
          <button className="god-close" onClick={onClose} aria-label="close">×</button>
        </header>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
          <input
            placeholder={t('wiki.searchPlaceholder')}
            value={q}
            onChange={e => setQ(e.target.value)}
            style={{ flex: 1, minWidth: 160, background: '#161b22', color: '#e6edf3', border: '1px solid #30363d', borderRadius: 6, padding: '6px 8px' }}
          />
          <span className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/wiki</span>
          <span className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/guide</span>
          <span className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/docs</span>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {(['guide', 'book', 'api', 'laws', 'presets'] as const).map(tt => (
            <button key={tt} onClick={() => setTab(tt)} style={{ background: tab === tt ? '#1f6feb' : '#21262d', color: tab === tt ? '#fff' : '#c9d1d9', borderColor: tab === tt ? '#1f6feb' : '#30363d' }}>
              {t(`wiki.tabs.${tt}`)}
            </button>
          ))}
        </div>

        {tab === 'guide' && (
          <div style={{ fontSize: 13, lineHeight: 1.6, color: '#c9d1d9' }}>
            <h3 style={{ color: '#e6edf3', marginTop: 0 }}>{t('wiki.aboutTitle')}</h3>
            <p>{t('wiki.aboutDesc')}</p>

            <h4 style={{ color: '#e6edf3' }}>{t('wiki.mechanicsTitle')}</h4>
            <ul>
              <li>{t('wiki.sphereDesc')}</li>
              <li>{t('wiki.evolutionDesc')}</li>
              <li>{t('wiki.lifeStagesDesc')}</li>
              <li>{t('wiki.settlementsDesc')}</li>
            </ul>

            <h4 style={{ color: '#e6edf3' }}>{t('wiki.featuresTitle')}</h4>
            <ul>
              <li>{t('wiki.spherePanelDesc')}</li>
              <li>{t('wiki.inspectorDesc')}</li>
              <li>{t('wiki.controlsDesc')}</li>
            </ul>

            <h4 style={{ color: '#e6edf3' }}>{t('wiki.quickstartTitle')}</h4>
            <pre style={{ background: '#161b22', padding: 12, borderRadius: 6, overflow: 'auto', border: '1px solid #30363d' }}><code>{`./run.sh
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
# Living Wiki: http://localhost:8000/wiki`}</code></pre>

            <h4 style={{ color: '#e6edf3' }}>{t('wiki.docsTitle')}</h4>
            <ul>
              <li><a href="/wiki">{t('wiki.docWiki')}</a></li>
              <li><a href="/guide">{t('wiki.docGuide')}</a></li>
              <li><a href="/docs">{t('wiki.docApi')}</a> + <a href="/openapi.json">/openapi.json</a></li>
              <li><a href="/docs/god-laws.md">{t('wiki.docLaws')}</a></li>
            </ul>
          </div>
        )}

        {tab === 'book' && (
          <div style={{ fontSize: 13, lineHeight: 1.6, color: '#c9d1d9' }}>
            <h3 style={{ color: '#e6edf3', marginTop: 0 }}>{t('wiki.bookTitle')}</h3>
            <p>{t('wiki.bookDesc')}</p>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4 }}>{t('wiki.bookSection1')}</h4>
            <div style={{ overflowX: 'auto', margin: '8px 0' }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '6px 8px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.dimCol')}</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.bookCol')}</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.simCol')}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#e6edf3' }}>{t('wiki.hierarchy')}</td>
                    <td style={{ padding: '6px 8px' }}><em>{t('wiki.hierarchyBook')}</em></td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.hierarchySim')}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#ff9bce' }}>{t('wiki.women')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.womenBook')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.womenSim')}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#ff7b72' }}>{t('wiki.soldiers')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.soldiersBook')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.soldiersSim')}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#f2cc60' }}>{t('wiki.artisans')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.artisansBook')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.artisansSim')}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#ffa657' }}>{t('wiki.gentlemen')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.gentlemenBook')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.gentlemenSim')}</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#e6edf3' }}>{t('wiki.priests')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.priestsBook')}</td>
                    <td style={{ padding: '6px 8px' }}>{t('wiki.priestsSim')}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4, marginTop: 16 }}>{t('wiki.bookSection2')}</h4>
            <p>{t('wiki.bookSection2Desc')}</p>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4, marginTop: 16 }}>{t('wiki.bookSection3')}</h4>
            <p>{t('wiki.bookSection3Desc')}</p>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4, marginTop: 16 }}>{t('wiki.bookSection4')}</h4>
            <p>{t('wiki.bookSection4Desc')}</p>
          </div>
        )}

        {tab === 'api' && (
          <div>
            <h3 style={{ marginTop: 0, color: '#e6edf3' }}>{t('wiki.apiTitle')}</h3>
            <p className="god-note" style={{ color: '#8b949e', fontSize: 12, margin: '4px 0 10px' }}>{t('wiki.apiDesc')}</p>
            <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid #30363d', borderRadius: 6 }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead><tr><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.routeCol')}</th><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.tryCol')}</th></tr></thead>
                <tbody>
                  {(data?.routes ?? []).filter(r => match(r) && r).sort().map(r => (
                    <tr key={r} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '6px 10px' }}><code>{r || '/'}</code></td>
                      <td style={{ padding: '6px 10px' }}><code style={{ fontSize: 11, wordBreak: 'break-all' }}>{`curl ${location.origin}${r}`}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h4 style={{ marginTop: 14, color: '#e6edf3' }}>{t('wiki.curlPlayground')}</h4>
            <pre style={{ background: '#161b22', padding: 12, borderRadius: 6, overflow: 'auto', fontSize: 12, border: '1px solid #30363d' }}><code>{`curl ${location.origin}/api/laws
curl -X POST ${location.origin}/api/laws -H 'content-type: application/json' -H 'X-God-Key: <passkey>' -d '{"food_count": 90}'
curl -X POST ${location.origin}/api/presets/sustainable?reset=true -H 'X-God-Key: <passkey>'
curl ${location.origin}/api/state | jq .tick
curl ${location.origin}/api/history?limit=5 | jq`}</code></pre>
          </div>
        )}

        {tab === 'laws' && (
          <div>
            <h3 style={{ marginTop: 0, color: '#e6edf3' }}>{t('wiki.lawsTitle', { count: data?.laws.length ?? 0 })}</h3>
            <p className="god-note" style={{ color: '#8b949e', fontSize: 12, margin: '4px 0 10px' }}>{t('wiki.lawsNote')}</p>

            <div style={{ maxHeight: 380, overflow: 'auto', border: '1px solid #30363d', borderRadius: 6 }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', minWidth: 480 }}>
                <thead><tr><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.lawCol')}</th><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.defaultCol')}</th><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>{t('wiki.hintCol')}</th></tr></thead>
                <tbody>
                  {(data?.laws ?? []).filter(n => match(n) || (t(`godHints.${n}`) || ((data?.law_details as any)?.[n]?.hint ?? '')).toLowerCase().includes(q.toLowerCase())).sort().map(name => {
                    const det = (data?.law_details as any)?.[name]
                    const cur = (laws as any)?.[name]
                    const hintText = t(`godHints.${name}`) !== `godHints.${name}` ? t(`godHints.${name}`) : det?.hint ?? ''
                    const lawLabel = t(`godLaws.${name}`) !== `godLaws.${name}` ? t(`godLaws.${name}`) : name
                    return (
                      <tr key={name} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '6px 10px' }}><code>{name}</code> <span style={{ color: '#8b949e', fontSize: 11 }}>({lawLabel})</span></td>
                        <td style={{ padding: '6px 10px', color: '#ffa657' }}>{String(cur ?? det?.default ?? '—')}</td>
                        <td style={{ padding: '6px 10px', fontSize: 11, color: '#c9d1d9', maxWidth: 300 }}>{hintText} <a href="/docs/god-laws.md" style={{ color: '#58a6ff', fontSize: 10 }}>md</a> · <a href="/wiki#god-laws" style={{ color: '#58a6ff', fontSize: 10 }}>wiki</a></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === 'presets' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>{t('wiki.presetsTitle')}</h3>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {presetFeedback && (
                  <span style={{ fontSize: 12, color: presetFeedback.startsWith('✓') ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                    {presetFeedback}
                  </span>
                )}
                {activePreset && (
                  <span className="chip" style={{ color: '#3fb950', borderColor: '#3fb950', background: 'rgba(63, 185, 80, 0.15)' }}>
                    {t('god.presets.active', { name: activePreset })}
                  </span>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              <button
                onClick={() => applyPreset('balance')}
                style={{
                  borderColor: '#e3b341',
                  color: '#e3b341',
                  background: activePreset === 'balance' ? 'rgba(227, 179, 65, 0.2)' : undefined,
                  fontWeight: activePreset === 'balance' ? 700 : undefined,
                }}
              >
                {t('god.presets.balance')} {activePreset === 'balance' ? '✓' : ''}
              </button>
              <button
                onClick={() => applyPreset('sustainable')}
                style={{
                  borderColor: '#3fb950',
                  color: '#3fb950',
                  background: activePreset === 'sustainable' ? 'rgba(63, 185, 80, 0.2)' : undefined,
                  fontWeight: activePreset === 'sustainable' ? 700 : undefined,
                }}
              >
                {t('god.presets.sustainable')} {activePreset === 'sustainable' ? '✓' : ''}
              </button>
              <button
                onClick={() => applyPreset('theocracy')}
                style={{
                  borderColor: '#bc8cff',
                  color: '#bc8cff',
                  background: activePreset === 'theocracy' ? 'rgba(188, 140, 255, 0.2)' : undefined,
                  fontWeight: activePreset === 'theocracy' ? 700 : undefined,
                }}
              >
                {t('god.presets.theocracy')} {activePreset === 'theocracy' ? '✓' : ''}
              </button>
              <button
                onClick={() => applyPreset('warlords')}
                style={{
                  borderColor: '#f0883e',
                  color: '#f0883e',
                  background: activePreset === 'warlords' ? 'rgba(240, 136, 62, 0.2)' : undefined,
                  fontWeight: activePreset === 'warlords' ? 700 : undefined,
                }}
              >
                {t('god.presets.warlords')} {activePreset === 'warlords' ? '✓' : ''}
              </button>
              <button
                onClick={() => applyPreset('chaos')}
                style={{
                  borderColor: '#f85149',
                  color: '#f85149',
                  background: activePreset === 'chaos' ? 'rgba(248, 81, 73, 0.2)' : undefined,
                  fontWeight: activePreset === 'chaos' ? 700 : undefined,
                }}
              >
                {t('god.presets.chaos')} {activePreset === 'chaos' ? '✓' : ''}
              </button>
              <button
                onClick={() => applyPreset('extinction')}
                style={{
                  borderColor: '#ff7b72',
                  color: '#ff7b72',
                  background: activePreset === 'extinction' ? 'rgba(255, 123, 114, 0.2)' : undefined,
                  fontWeight: activePreset === 'extinction' ? 700 : undefined,
                }}
              >
                {t('god.presets.extinction')} {activePreset === 'extinction' ? '✓' : ''}
              </button>
              <button
                onClick={() => applyPreset('boom')}
                style={{
                  borderColor: '#79c0ff',
                  color: '#79c0ff',
                  background: activePreset === 'boom' ? 'rgba(121, 192, 255, 0.2)' : undefined,
                  fontWeight: activePreset === 'boom' ? 700 : undefined,
                }}
              >
                {t('god.presets.boom')} {activePreset === 'boom' ? '✓' : ''}
              </button>
            </div>
            {data?.presets && Object.entries(data.presets).map(([name, pLaws]) => {
              const isCurrent = activePreset === name
              return (
                <div key={name} style={{ border: `1px solid ${isCurrent ? '#3fb950' : '#21262d'}`, borderRadius: 6, padding: 10, marginBottom: 8, background: isCurrent ? 'rgba(63, 185, 80, 0.06)' : '#161b22' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <b style={{ color: isCurrent ? '#3fb950' : '#e6edf3' }}>{name} {isCurrent && t('wiki.activeTag')}</b>
                    <button onClick={() => applyPreset(name, false)} style={{ marginLeft: 'auto', padding: '4px 8px', fontSize: 12, cursor: 'pointer' }}>{t('wiki.apply')}</button>
                    <button onClick={() => applyPreset(name, true)} style={{ padding: '4px 8px', fontSize: 12, background: '#238636', borderColor: '#2ea043', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>{t('wiki.applyReset')}</button>
                  </div>
                  <div style={{ fontSize: 11, color: '#8b949e', marginTop: 6, wordBreak: 'break-all' }}>
                    {Object.entries(pLaws).slice(0, 8).map(([k, v]) => <span key={k} style={{ marginRight: 8 }}><code>{k}={String(v)}</code></span>)}
                    {Object.keys(pLaws).length > 8 && <span>{t('wiki.moreLaws', { count: Object.keys(pLaws).length - 8 })}</span>}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #21262d', fontSize: 11, color: '#8b949e', lineHeight: 1.5 }}>
          {t('wiki.footerLive', { laws: data?.laws.length ?? 0, routes: data?.routes.length ?? 0, presets: Object.keys(data?.presets ?? {}).length })} · <a href="/wiki">/wiki HTML</a> · <a href="/api/wiki">/api/wiki JSON</a>
          <br />{t('wiki.developedBy')} <strong>Long Phan</strong> — <a href="mailto:long@minhnhan.in">long@minhnhan.in</a> · <a href="https://minhnhan.in">minhnhan.in</a> · <a href="https://world.minhnhan.in">world.minhnhan.in</a>
          <br /><span style={{ opacity: 0.85 }}>{t('wiki.inspiration')}</span>
        </div>
      </div>
    </div>
  )
}

