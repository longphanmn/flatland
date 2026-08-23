import { useEffect, useState } from 'react'

type WikiData = {
  laws: string[]
  routes: string[]
  presets: Record<string, Record<string, any>>
  law_details: Record<string, { type: string; default: any }>
  overview: string
}

export default function Wiki({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [data, setData] = useState<WikiData | null>(null)
  const [tab, setTab] = useState<'guide' | 'api' | 'laws' | 'presets'>('guide')
  const [q, setQ] = useState('')
  const [laws, setLaws] = useState<Record<string, any> | null>(null)

  useEffect(() => {
    if (!open) return
    fetch('/api/wiki').then(r => r.json()).then(setData).catch(() => {})
    fetch('/api/laws').then(r => r.json()).then(setLaws).catch(() => {})
  }, [open])

  if (!open) return null

  const applyPreset = async (name: string) => {
    const r = await fetch(`/api/presets/${name}?persist=true`, { method: 'POST' })
    if (r.ok) alert(`${name} preset applied`)
    else alert('preset failed')
  }

  // filter helpers
  const match = (s: string) => !q || s.toLowerCase().includes(q.toLowerCase())

  return (
    <div className="wiki-backdrop" onClick={onClose}>
      <div className="wiki-panel" onClick={e => e.stopPropagation()}>
        <header className="god-head" style={{ position: 'sticky', top: 0, background: '#0d1117', zIndex: 1, paddingBottom: 8 }}>
          <h2>📖 Flatland Wiki</h2>
          <button className="god-close" onClick={onClose} aria-label="close">×</button>
        </header>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
          <input
            placeholder="Search laws, routes, docs… ( / )"
            value={q}
            onChange={e => setQ(e.target.value)}
            style={{ flex: 1, minWidth: 160, background: '#161b22', color: '#e6edf3', border: '1px solid #30363d', borderRadius: 6, padding: '6px 8px' }}
          />
          <a href="/wiki" rel="noreferrer" className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>Open /wiki ↗</a>
          <a href="/guide" rel="noreferrer" className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/guide</a>
          <a href="/docs" rel="noreferrer" className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/docs</a>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {(['guide', 'api', 'laws', 'presets'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? '#1f6feb' : '#21262d', color: tab === t ? '#fff' : '#c9d1d9', borderColor: tab === t ? '#1f6feb' : '#30363d' }}>
              {t}
            </button>
          ))}
        </div>

        {tab === 'guide' && (
          <div style={{ fontSize: 13, lineHeight: 1.5, color: '#c9d1d9' }}>
            <h3>Overview</h3>
            <p>Flatland is a 2D emergent world: geometric castes wander, eat, shelter, age, mate. God sets <em>laws</em>, never a life. Live at <code>/</code>, backend at <code>:8000</code>.</p>
            <h4>How to use</h4>
            <ul>
              <li><b>God panel</b> (⚖ God) — edit laws, presets (sustainable/chaos/extinction), Apply vs Save.</li>
              <li><b>Wiki</b> (this page) — docs + API playground. Backend wiki at <a href="/wiki">/wiki</a>.</li>
              <li><b>Controls</b>: space pause, S step, R reset, F fit, +/- zoom, drag/pinch.</li>
            </ul>
            <h4>Quickstart</h4>
            <pre style={{ background: '#161b22', padding: 12, borderRadius: 6, overflow: 'auto' }}><code>{`./run.sh
# backend: http://localhost:8000/docs  wiki: http://localhost:8000/wiki
# frontend: http://localhost:5173`}</code></pre>
            <h4>Data flow</h4>
            <p><code>tick_loop → sim.step() → snapshot → WS /ws</code> throttled ~30 Hz. Client sends <code>{"{"}"action":"pause"{"}"}</code>.</p>
            <h4>Links</h4>
            <ul>
              <li><a href="/wiki">Backend Wiki (/wiki)</a> — full docs with presets & playground</li>
              <li><a href="/guide">Guide (/guide)</a> — minimal living docs</li>
              <li><a href="/docs">Swagger (/docs)</a> + <a href="/openapi.json">/openapi.json</a></li>
            </ul>
          </div>
        )}

        {tab === 'api' && (
          <div>
            <h3>API Reference — live routes</h3>
            <p className="god-note">From <code>app.routes</code> + <code>/openapi.json</code>. Try with <code>curl</code>.</p>
            <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid #21262d', borderRadius: 6 }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead><tr><th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid #21262d' }}>Route</th><th style={{ padding: '6px 8px', borderBottom: '1px solid #21262d' }}>Try</th></tr></thead>
                <tbody>
                  {(data?.routes ?? []).filter(r => match(r) && r).sort().map(r => (
                    <tr key={r} style={{ borderBottom: '1px solid #21262d' }}>
                      <td style={{ padding: '6px 8px' }}><code>{r || '/'}</code></td>
                      <td style={{ padding: '6px 8px' }}><code style={{ fontSize: 11, wordBreak: 'break-all' }}>{`curl ${location.origin}${r}`}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h4 style={{ marginTop: 12 }}>Curl playground</h4>
            <pre style={{ background: '#161b22', padding: 12, borderRadius: 6, overflow: 'auto', fontSize: 12 }}><code>{`curl ${location.origin}/api/laws
curl -X POST ${location.origin}/api/presets/sustainable?reset=true
curl ${location.origin}/api/state | jq .tick
curl ${location.origin}/api/history?limit=5 | jq`}</code></pre>
          </div>
        )}

        {tab === 'laws' && (
          <div>
            <h3>God Laws — {data?.laws.length ?? 0} laws</h3>
            <p className="god-note">Type/range/default from live <code>GodLaws</code>. Edit in God panel or <code>POST /api/laws</code>.</p>
            <div style={{ maxHeight: 380, overflowY: 'auto', border: '1px solid #21262d', borderRadius: 6 }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead><tr><th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid #21262d' }}>Law</th><th style={{ padding: '6px 8px', borderBottom: '1px solid #21262d' }}>Default</th><th style={{ padding: '6px 8px', borderBottom: '1px solid #21262d' }}>Type</th></tr></thead>
                <tbody>
                  {(data?.laws ?? []).filter(n => match(n)).sort().map(name => {
                    const det = (data?.law_details as any)?.[name]
                    const cur = (laws as any)?.[name]
                    return (
                      <tr key={name} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '6px 8px' }}><code>{name}</code></td>
                        <td style={{ padding: '6px 8px' }}>{String(cur ?? det?.default ?? '—')}</td>
                        <td style={{ padding: '6px 8px', fontSize: 11, color: '#8b949e' }}>{String(det?.type ?? '').slice(0, 40)}</td>
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
            <h3>Presets — one-click worlds</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              <button onClick={() => applyPreset('sustainable')} style={{ borderColor: '#3fb950', color: '#3fb950' }}>🌿 Sustainable</button>
              <button onClick={() => applyPreset('chaos')} style={{ borderColor: '#f85149', color: '#f85149' }}>🔥 Chaos</button>
              <button onClick={() => applyPreset('extinction')}>💀 Extinction</button>
            </div>
            {data?.presets && Object.entries(data.presets).map(([name, laws]) => (
              <div key={name} style={{ border: '1px solid #21262d', borderRadius: 6, padding: 10, marginBottom: 8, background: '#161b22' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <b style={{ color: '#e6edf3' }}>{name}</b>
                  <button onClick={() => applyPreset(name)} style={{ marginLeft: 'auto', padding: '4px 8px', fontSize: 12 }}>Apply</button>
                  <button onClick={async () => { await fetch(`/api/presets/${name}?persist=true&reset=true`, { method: 'POST' }); alert(name + ' + reset'); }} style={{ padding: '4px 8px', fontSize: 12 }}>Apply + Reset</button>
                </div>
                <div style={{ fontSize: 11, color: '#8b949e', marginTop: 6, wordBreak: 'break-all' }}>
                  {Object.entries(laws).slice(0, 8).map(([k, v]) => <span key={k} style={{ marginRight: 8 }}><code>{k}={String(v)}</code></span>)}
                  {Object.keys(laws).length > 8 && <span>…+{Object.keys(laws).length - 8} more</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #21262d', fontSize: 11, color: '#8b949e' }}>
          Wiki is live — <code>{data?.laws.length ?? 0} laws</code> · <code>{data?.routes.length ?? 0} routes</code> · <code>{Object.keys(data?.presets ?? {}).length} presets</code> · <a href="/wiki">/wiki HTML</a> · <a href="/api/wiki">/api/wiki JSON</a>
        </div>
      </div>
    </div>
  )
}
