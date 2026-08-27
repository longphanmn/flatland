import { useEffect, useState } from 'react'
import { godFetch } from '../god/auth'

type WikiData = {
  laws: string[]
  routes: string[]
  presets: Record<string, Record<string, any>>
  law_details: Record<string, { type: string; default: any }>
  overview: string
}

export default function Wiki({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [data, setData] = useState<WikiData | null>(null)
  const [tab, setTab] = useState<'guide' | 'book' | 'api' | 'laws' | 'presets'>('guide')
  const [q, setQ] = useState('')
  const [laws, setLaws] = useState<Record<string, any> | null>(null)

  useEffect(() => {
    if (!open) return
    fetch('/api/wiki').then(r => r.json()).then(setData).catch(() => {})
    fetch('/api/laws').then(r => r.json()).then(setLaws).catch(() => {})
  }, [open])

  if (!open) return null

  const [presetFeedback, setPresetFeedback] = useState<string | null>(null)

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
          <span className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/wiki</span>
          <span className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/guide</span>
          <span className="chip" style={{ border: '1px solid #30363d', borderRadius: 6, padding: '4px 8px', background: '#161b22' }}>/docs</span>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {(['guide', 'book', 'api', 'laws', 'presets'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{ background: tab === t ? '#1f6feb' : '#21262d', color: tab === t ? '#fff' : '#c9d1d9', borderColor: tab === t ? '#1f6feb' : '#30363d' }}>
              {t === 'book' ? '📖 Book vs Sim' : t}
            </button>
          ))}
        </div>

        {tab === 'guide' && (
          <div style={{ fontSize: 13, lineHeight: 1.6, color: '#c9d1d9' }}>
            <h3 style={{ color: '#e6edf3', marginTop: 0 }}>📖 About Flatland</h3>
            <p>
              <strong>Flatland</strong> is an autonomous 2D artificial life and ecosystem simulation developed from the foundational ideas of <strong>Edwin A. Abbott's 1884 classic <em>Flatland: A Romance of Many Dimensions</em></strong>. Rather than mimicking the novella literally, it takes Flatland's core geometric premises to build a <strong>living, autonomous evolutionary ecosystem that organically evolves and changes over time</strong>.
            </p>
            <h4 style={{ color: '#e6edf3' }}>Key Simulation Mechanics</h4>
            <ul>
              <li><strong>The Sphere (God Model)</strong>: The Sphere (God) sets universal <em>laws of nature</em> from Spaceland, never intervening in individual lives. Everything is 100% emergent.</li>
              <li><strong>Autonomous Evolution</strong>: Heritable personality archetypes (brave, altruistic, builder, etc.), tools (spears, baskets, poultices, crowns), 4 mastery skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿), dynamic titles, and oral lore taught in houses.</li>
              <li><strong>Life Stages & Metabolism</strong>: Infant low burn (0.45×), combat stamina drain, field food reserves, and natural lifespans.</li>
              <li><strong>Settlements & Politics</strong>: Walled houses, multi-house clan territories, settlement food larders, mutual coalitions, and schisms.</li>
            </ul>

            <h4 style={{ color: '#e6edf3' }}>Interactive Features</h4>
            <ul>
              <li><strong>The Sphere Panel</strong> (⚖ The Sphere) — Adjust carrying capacity, food growth, metabolism, disease, and apply presets.</li>
              <li><strong>Creature Inspector</strong> — Tap any creature to view its live vitals, personality, tools, skill mastery, and family lineage.</li>
              <li><strong>Controls</strong>: Space pause, S step, R reset seed, F fit camera, +/- zoom, drag to pan.</li>
            </ul>
            <h4 style={{ color: '#e6edf3' }}>Quickstart</h4>
            <pre style={{ background: '#161b22', padding: 12, borderRadius: 6, overflow: 'auto', border: '1px solid #30363d' }}><code>{`./run.sh
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
# Living Wiki: http://localhost:8000/wiki`}</code></pre>
            <h4 style={{ color: '#e6edf3' }}>Documentation Links</h4>
            <ul>
              <li><a href="/wiki">Backend Living Wiki (/wiki)</a> — Full documentation with presets & curl playground</li>
              <li><a href="/guide">Living Guide (/guide)</a> — Codebase architecture and system maps</li>
              <li><a href="/docs">Swagger Interactive API (/docs)</a> + <a href="/openapi.json">/openapi.json</a></li>
              <li><a href="/docs/god-laws.md">Laws of the Sphere (/docs/god-laws.md)</a></li>
            </ul>

          </div>
        )}

        {tab === 'book' && (
          <div style={{ fontSize: 13, lineHeight: 1.6, color: '#c9d1d9' }}>
            <h3 style={{ color: '#e6edf3', marginTop: 0 }}>📚 Flatland: Abbott's Novella vs. The Simulation</h3>
            <p>
              A comparative study between <strong>Edwin A. Abbott’s 1884 satirical classic <em>Flatland: A Romance of Many Dimensions</em></strong> and our autonomous artificial life simulation.
            </p>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4 }}>1. Caste, Geometry & Social Hierarchy</h4>
            <div style={{ overflowX: 'auto', margin: '8px 0' }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '6px 8px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Dimension</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Abbott’s Book (1884)</th>
                    <th style={{ textAlign: 'left', padding: '6px 8px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Our Simulation App</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#e6edf3' }}>Hierarchy Principle</td>
                    <td style={{ padding: '6px 8px' }}><em>"Configuration makes the man."</em> Social rank is governed strictly by side count and angular regularity.</td>
                    <td style={{ padding: '6px 8px' }}>Entities inherit exact geometric castes based on vertex count ($N$-gons) and regularity.</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#ff9bce' }}>Women (Lines)</td>
                    <td style={{ padding: '6px 8px' }}>Straight lines (zero angular width). Required to maintain a continuous peace-cry to prevent accidental stabbing.</td>
                    <td style={{ padding: '6px 8px' }}>Rendered as 1D segments (<code>shape: 'line'</code>). Highly agile with distinct domestic shelter dynamics.</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#ff7b72' }}>Soldiers / Workers</td>
                    <td style={{ padding: '6px 8px' }}>Isosceles triangles with sharp vertex angles (volatile and militaristic).</td>
                    <td style={{ padding: '6px 8px' }}><strong>Soldiers</strong>: High combat damage, defensive patrolling, equipped with spears.</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#f2cc60' }}>Artisans (Middle Class)</td>
                    <td style={{ padding: '6px 8px' }}>Equilateral triangles (3 equal sides) — steady tradespeople.</td>
                    <td style={{ padding: '6px 8px' }}><strong>Artisans</strong> (3–4 sides): Farmers, foragers, and builders managing houses and larders.</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#ffa657' }}>Gentlemen & Nobles</td>
                    <td style={{ padding: '6px 8px' }}>Squares (4 sides), Pentagons (5 sides), Hexagons (6 sides), and high polygons.</td>
                    <td style={{ padding: '6px 8px' }}><strong>Gentlemen</strong> (4), <strong>Professionals</strong> (5), <strong>Nobles</strong> (6–8): Administrative prestige and leadership.</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #21262d' }}>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#e6edf3' }}>Priesthood (Circles)</td>
                    <td style={{ padding: '6px 8px' }}>Polygons with so many sides that vertices appear as smooth circles. Rule society and religion.</td>
                    <td style={{ padding: '6px 8px' }}><strong>Priests</strong> ($\ge 24$ sides): Soothing auras, healing injured/infected clanmates, disease immunity.</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4, marginTop: 16 }}>2. The "Law of Nature" & Generational Ascent</h4>
            <p>
              In Abbott's world, the <strong>Law of Upward Development</strong> guarantees that sons of regular polygons gain $+1$ side over their fathers (Square $\to$ Pentagon $\to$ Hexagon), ascending toward circular priesthood over generations. In our simulation, offspring inherit side counts with probabilistic side promotions (<code>sides += 1</code>) and lineage tracking via the Family Tree.
            </p>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4, marginTop: 16 }}>3. Sight Recognition & Fog Perception</h4>
            <p>
              In Flatland, 2D beings look like flat edges. In the foggy South, they rely on <strong>Sight Recognition</strong> (how quickly vertices fade into fog). In our simulation, the <strong>Dynamic Weather Engine</strong> simulates Clear, Fog, Rain, and Storms, modulating creature <code>sight_radius</code> and forcing reliance on auditory alarms (<code>signals</code>).
            </p>

            <h4 style={{ color: '#e3b341', borderBottom: '1px solid #30363d', paddingBottom: 4, marginTop: 16 }}>4. The Higher Dimension: The User as "The Sphere"</h4>
            <p>
              In the novel, <strong>A Square</strong> is visited by <strong>A Sphere</strong> from 3D <em>Spaceland</em>, who gazes down into closed rooms, inspects interiors, and manipulates 2D physics. In our app, <strong>you are the Sphere (God)</strong>: peering down from the Z-axis, inspecting creature minds and lineage, and tuning the fundamental Laws of Nature via <strong>The Sphere Panel</strong>.
            </p>
          </div>
        )}


        {tab === 'api' && (
          <div>
            <h3 style={{ marginTop: 0, color: '#e6edf3' }}>API Reference — live routes</h3>
            <p className="god-note" style={{ color: '#8b949e', fontSize: 12, margin: '4px 0 10px' }}>From <code>app.routes</code> + <code>/openapi.json</code>. Try with <code>curl</code>.</p>
            <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid #30363d', borderRadius: 6 }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead><tr><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Route</th><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Try</th></tr></thead>
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
            <h4 style={{ marginTop: 14, color: '#e6edf3' }}>Curl playground</h4>
            <pre style={{ background: '#161b22', padding: 12, borderRadius: 6, overflow: 'auto', fontSize: 12, border: '1px solid #30363d' }}><code>{`curl ${location.origin}/api/laws
curl -X POST ${location.origin}/api/laws -H 'content-type: application/json' -H 'X-God-Key: <passkey>' -d '{"food_count": 90}'
curl -X POST ${location.origin}/api/presets/sustainable?reset=true -H 'X-God-Key: <passkey>'
curl ${location.origin}/api/state | jq .tick
curl ${location.origin}/api/history?limit=5 | jq`}</code></pre>
          </div>
        )}

        {tab === 'laws' && (
          <div>
            <h3 style={{ marginTop: 0, color: '#e6edf3' }}>Laws of the Sphere — {data?.laws.length ?? 0} laws</h3>
            <p className="god-note" style={{ color: '#8b949e', fontSize: 12, margin: '4px 0 10px' }}>Type/range/default + hint from <code>docs/god-laws.md</code>. Edit in The Sphere panel or <code>POST /api/laws</code>.</p>

            <div style={{ maxHeight: 380, overflow: 'auto', border: '1px solid #30363d', borderRadius: 6 }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', minWidth: 480 }}>
                <thead><tr><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Law</th><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Default</th><th style={{ textAlign: 'left', padding: '8px 10px', background: '#161b22', color: '#e6edf3', borderBottom: '1px solid #30363d' }}>Hint</th></tr></thead>
                <tbody>
                  {(data?.laws ?? []).filter(n => match(n) || ((data?.law_details as any)?.[n]?.hint ?? '').toLowerCase().includes(q.toLowerCase())).sort().map(name => {
                    const det = (data?.law_details as any)?.[name]
                    const cur = (laws as any)?.[name]
                    return (
                      <tr key={name} style={{ borderBottom: '1px solid #21262d' }}>
                        <td style={{ padding: '6px 10px' }}><code>{name}</code></td>
                        <td style={{ padding: '6px 10px', color: '#ffa657' }}>{String(cur ?? det?.default ?? '—')}</td>
                        <td style={{ padding: '6px 10px', fontSize: 11, color: '#c9d1d9', maxWidth: 300 }}>{det?.hint ?? ''} <a href="/docs/god-laws.md" style={{ color: '#58a6ff', fontSize: 10 }}>md</a> · <a href="/wiki#god-laws" style={{ color: '#58a6ff', fontSize: 10 }}>wiki</a></td>
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
              <h3 style={{ margin: 0 }}>Presets — one-click worlds</h3>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {presetFeedback && (
                  <span style={{ fontSize: 12, color: presetFeedback.startsWith('✓') ? '#3fb950' : '#f85149', fontWeight: 600 }}>
                    {presetFeedback}
                  </span>
                )}
                {activePreset && (
                  <span className="chip" style={{ color: '#3fb950', borderColor: '#3fb950', background: 'rgba(63, 185, 80, 0.15)' }}>
                    Active: {activePreset}
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
                ⚖️ Balance {activePreset === 'balance' ? '✓' : ''}
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
                🌿 Sustainable {activePreset === 'sustainable' ? '✓' : ''}
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
                🔮 Theocracy {activePreset === 'theocracy' ? '✓' : ''}
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
                ⚔️ Warlords {activePreset === 'warlords' ? '✓' : ''}
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
                🔥 Chaos {activePreset === 'chaos' ? '✓' : ''}
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
                💀 Extinction {activePreset === 'extinction' ? '✓' : ''}
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
                🚀 Boom {activePreset === 'boom' ? '✓' : ''}
              </button>
            </div>
            {data?.presets && Object.entries(data.presets).map(([name, pLaws]) => {
              const isCurrent = activePreset === name
              return (
                <div key={name} style={{ border: `1px solid ${isCurrent ? '#3fb950' : '#21262d'}`, borderRadius: 6, padding: 10, marginBottom: 8, background: isCurrent ? 'rgba(63, 185, 80, 0.06)' : '#161b22' }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <b style={{ color: isCurrent ? '#3fb950' : '#e6edf3' }}>{name} {isCurrent && '(active)'}</b>
                    <button onClick={() => applyPreset(name, false)} style={{ marginLeft: 'auto', padding: '4px 8px', fontSize: 12, cursor: 'pointer' }}>⚡ Apply</button>
                    <button onClick={() => applyPreset(name, true)} style={{ padding: '4px 8px', fontSize: 12, background: '#238636', borderColor: '#2ea043', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>🔄 Apply + Reset</button>
                  </div>
                  <div style={{ fontSize: 11, color: '#8b949e', marginTop: 6, wordBreak: 'break-all' }}>
                    {Object.entries(pLaws).slice(0, 8).map(([k, v]) => <span key={k} style={{ marginRight: 8 }}><code>{k}={String(v)}</code></span>)}
                    {Object.keys(pLaws).length > 8 && <span>…+{Object.keys(pLaws).length - 8} more</span>}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #21262d', fontSize: 11, color: '#8b949e', lineHeight: 1.5 }}>
          Wiki is live — <code>{data?.laws.length ?? 0} laws</code> · <code>{data?.routes.length ?? 0} routes</code> · <code>{Object.keys(data?.presets ?? {}).length} presets</code> · <a href="/wiki">/wiki HTML</a> · <a href="/api/wiki">/api/wiki JSON</a>
          <br />Developed by <strong>Long Phan</strong> — <a href="mailto:long@minhnhan.in">long@minhnhan.in</a> · <a href="https://minhnhan.in">minhnhan.in</a> · <a href="https://world.minhnhan.in">world.minhnhan.in</a>
          <br /><span style={{ opacity: 0.85 }}>Built with OpenCode & Antigravity · Inspired by Edwin A. Abbott's <em>Flatland</em></span>
        </div>
      </div>
    </div>
  )
}
