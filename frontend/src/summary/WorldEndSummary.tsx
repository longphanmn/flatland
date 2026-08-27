import { useEffect, useState } from 'react'
import type { StateMessage } from '../types'
import { totemEmoji } from '../totems'

export default function WorldEndSummary({
  state,
  onReset,
  onClose,
  onOpenWorldHistory,
}: {
  state: StateMessage | null
  onReset: () => void
  onClose: () => void
  onOpenWorldHistory?: () => void
}) {
  const [clans, setClans] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])

  useEffect(() => {
    fetch('/api/clans').then(r => r.json()).then(d => setClans(d.clans ?? [])).catch(() => {})
    fetch('/api/history?limit=100').then(r => r.json()).then(d => setHistory(d.events ?? [])).catch(() => {})
  }, [])

  if (!state || state.creatures_alive !== 0) return null

  const totalDays = (state.tick / 1200).toFixed(1) // day_length 1200
  const deadByCause = state.dead_by_cause ?? {}

  return (
    <div className="world-end-backdrop" onClick={onClose}>
      <div className="world-end-panel" onClick={e => e.stopPropagation()}>
        <header className="god-head">
          <h2 style={{ color: '#f85149' }}>☠ World End — Extinction</h2>
          <button className="god-close" onClick={onClose}>×</button>
        </header>

        <div style={{ textAlign: 'center', padding: '12px 0', borderBottom: '1px solid #21262d', marginBottom: 12 }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>💀</div>
          <div style={{ fontSize: 18, color: '#e6edf3', fontWeight: 700 }}>All creatures have perished</div>
          <div className="chip" style={{ marginTop: 6 }}>Tick {state.tick} · {totalDays} days · Day {state.day} · {state.season} · Seed {state.seed}</div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div style={{ background: 'rgba(248,81,73,0.08)', border: '1px solid #30363d', borderRadius: 6, padding: 10 }}>
            <div style={{ fontSize: 12, color: '#8b949e' }}>Total Dead</div>
            <div style={{ fontSize: 28, color: '#f85149', fontWeight: 700 }}>{state.creatures_dead}</div>
            <div style={{ fontSize: 11, color: '#8b949e' }}>{Object.entries(deadByCause).map(([k,v]) => `${k} ${v}`).join(' · ') || 'no breakdown'}</div>
          </div>
          <div style={{ background: 'rgba(110,118,129,0.08)', border: '1px solid #30363d', borderRadius: 6, padding: 10 }}>
            <div style={{ fontSize: 12, color: '#8b949e' }}>Final Population</div>
            <div style={{ fontSize: 28, color: '#8b949e', fontWeight: 700 }}>{state.creatures_alive} alive</div>
            <div style={{ fontSize: 11, color: '#8b949e' }}>{Object.entries(state.population).map(([k,v]) => `${k} ${v}`).join(' · ')}</div>
          </div>
        </div>

        <h3 style={{ fontSize: 13, color: '#e6edf3', margin: '12px 0 6px' }}>Clans at the End — {clans.length} clans</h3>
        {clans.length === 0 ? <p className="chip">No clans recorded.</p> : (
          <div style={{ display: 'grid', gap: 6, maxHeight: 180, overflow: 'auto' }}>
            {clans.map((c: any) => (
              <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(110,118,129,0.08)', borderRadius: 4, borderLeft: `4px solid ${c.color}` }}>
                <span><b style={{ color: c.color }}>{c.name}</b> #{c.id} · pop {c.population} {c.totem ? `· ${totemEmoji(c.totem)} ${c.totem}` : ''}</span>
                <span className="chip">{c.war_wins}W/{c.war_losses}L</span>
              </div>
            ))}
          </div>
        )}

        <h3 style={{ fontSize: 13, color: '#e6edf3', margin: '12px 0 6px' }}>Last Events — {history.length} recent</h3>
        <div style={{ maxHeight: 160, overflow: 'auto', border: '1px solid #21262d', borderRadius: 6, padding: 8, background: '#161b22' }}>
          {history.slice(0, 20).map((ev: any, i: number) => (
            <div key={i} style={{ fontSize: 11, padding: '3px 0', borderBottom: '1px solid #21262d' }}>
              <b>{ev.type}</b> tick {ev.tick} · {ev.caste ?? ''} {ev.cause ? `· ${ev.cause}` : ''} · {ev.payload?.personal_name ?? ''} #{ev.entity_id}
            </div>
          ))}
          {history.length === 0 && <div className="chip">No history.</div>}
        </div>

        <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
          {onOpenWorldHistory && (
            <button
              onClick={onOpenWorldHistory}
              style={{
                background: '#1f6feb',
                borderColor: '#388bfd',
                color: '#fff',
                padding: '10px 18px',
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span>📜</span> World History & Story Export
            </button>
          )}
          <button onClick={onReset} style={{ background: '#238636', borderColor: '#2ea043', color: '#fff', padding: '10px 20px', fontSize: 14, cursor: 'pointer' }}>🔄 Reset World — New Seed</button>
          <button onClick={onClose} style={{ padding: '10px 16px', cursor: 'pointer' }}>Close</button>
        </div>

        <p className="god-note" style={{ textAlign: 'center', marginTop: 8 }}>The world has fallen silent. God may set new laws or reset for a fresh seed. History remains in <code>/api/history</code> and <code>/api/worlds</code>.</p>
      </div>
    </div>
  )
}
