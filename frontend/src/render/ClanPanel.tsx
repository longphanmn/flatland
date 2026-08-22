import { useEffect, useState } from 'react'

interface ClanInfo {
  id: number
  name: string
  color: string
  totem: string | null
  founder_id: number
  leader_id: number | null
  born_tick: number
  population: number
  house: { x: number; y: number; size: number; is_ruin: boolean } | null
  war_wins: number
  war_losses: number
  territory_radius: number | null
  specialization?: { warrior: number; farmer: number; scavenger: number } | null
}

export default function ClanPanel() {
  const [clans, setClans] = useState<ClanInfo[]>([])
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let alive = true
    const load = () =>
      fetch('/api/clans')
        .then((r) => r.json())
        .then((d) => {
          if (!alive) return
          setClans(d.clans ?? [])
          setTick(d.tick ?? 0)
        })
        .catch(() => {})
    load()
    const t = setInterval(load, 2000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  if (clans.length === 0) return <p className="chip">no clans yet</p>

  return (
    <div className="clan-panel">
      <h4 style={{ margin: '8px 0 6px', fontSize: '0.9em' }}>Clans — {tick} ticks</h4>
      <div style={{ display: 'grid', gap: 6 }}>
        {clans.map((c) => (
          <div key={c.id} className="clan-card" style={{ borderLeft: `4px solid ${c.color}`, padding: '6px 8px', background: 'rgba(110,118,129,0.08)', borderRadius: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <b style={{ color: c.color }}>{c.name}</b>
              <span className="chip" style={{ background: c.color, color: '#0b0f14' }}>{c.totem ?? '—'}</span>
            </div>
            <div className="chip" style={{ marginTop: 4 }}>
              #{c.id} · pop <b>{c.population}</b> · {c.house ? (c.house.is_ruin ? 'ruins' : `house ${Math.round(c.house.x)},${Math.round(c.house.y)}`) : 'homeless'} · war {c.war_wins}W/{c.war_losses}L
            </div>
            <div className="chip">
              leader #{c.leader_id ?? '—'} · founder #{c.founder_id} · born tick {c.born_tick}
            </div>
            {c.specialization && (
              <div className="chip" title="Clan specialization drifts over generations — warrior (war), farmer (harvest), scavenger (corpse) — totem biases start, environment + history drift it">
                <span style={{ color: '#f85149' }}>⚔ warrior {c.specialization.warrior.toFixed(2)}</span> · <span style={{ color: '#3fb950' }}>🌾 farmer {c.specialization.farmer.toFixed(2)}</span> · <span style={{ color: '#8b949e' }}>🦴 scavenger {c.specialization.scavenger.toFixed(2)}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
