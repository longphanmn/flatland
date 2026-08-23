import { useEffect, useState } from 'react'
import { totemEmoji } from '../totems'

interface ClanMember {
  id: number
  caste: string
  sex: string
  age: number
  lifespan: number
  stage: string
  energy: number
  health: number
  status: string
  personal_name: string
  glyph: string
}

interface ClanDetailsData {
  id: number
  name: string
  color: string
  totem: string | null
  founder_id: number
  leader_id: number | null
  born_tick: number
  population: number
  house: { x: number; y: number; size: number } | null
  war_wins: number
  war_losses: number
  territory_radius: number | null
  specialization: { warrior: number; farmer: number; scavenger: number } | null
  culture: string | null
  members: ClanMember[]
  events: any[]
}

export default function ClanDetails({ clanId, onClose, onSelectCreature }: { clanId: number; onClose: () => void; onSelectCreature?: (id: number) => void }) {
  const [data, setData] = useState<ClanDetailsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/clans/${clanId}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [clanId])

  if (loading) {
    return (
      <div className="clan-details-backdrop" onClick={onClose}>
        <div className="clan-details-panel" onClick={e => e.stopPropagation()}>
          <p className="god-note">Loading clan {clanId}…</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="clan-details-backdrop" onClick={onClose}>
        <div className="clan-details-panel" onClick={e => e.stopPropagation()}>
          <p className="god-note">Clan not found.</p>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    )
  }

  return (
    <div className="clan-details-backdrop" onClick={onClose}>
      <div className="clan-details-panel" onClick={e => e.stopPropagation()}>
        <header className="god-head">
          <h2 style={{ color: data.color, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: data.color, display: 'inline-block' }} />
            {data.name} <span style={{ fontSize: 12, color: '#8b949e' }}>#{data.id}</span>
            {data.totem && <span style={{ background: data.color, color: '#0b0f14', padding: '2px 6px', borderRadius: 4, fontSize: 11 }}>{totemEmoji(data.totem)} {data.totem}</span>}
          </h2>
          <button className="god-close" onClick={onClose}>×</button>
        </header>

        <div className="chip" style={{ marginBottom: 8 }}>
          Founder{' '}
          <button className="chronicle-name" onClick={() => data.founder_id != null && onSelectCreature?.(data.founder_id)} title="show founder profile">#{data.founder_id ?? '—'}</button>
          {' · '}Leader{' '}
          <button className="chronicle-name" onClick={() => data.leader_id != null && onSelectCreature?.(data.leader_id)} title="show leader profile">#{data.leader_id ?? '—'}</button>
          {' · '}Born tick {data.born_tick} · Pop <b>{data.population}</b> · War {data.war_wins}W/{data.war_losses}L
          {data.house ? ` · House ${Math.round(data.house.x)},${Math.round(data.house.y)}` : ' · Homeless'}
          {data.territory_radius ? ` · Territory r${data.territory_radius}` : ''}
        </div>

        {data.specialization && (
          <div className="chip" style={{ marginBottom: 8 }}>
            <span style={{ color: '#f85149' }}>⚔ warrior {data.specialization.warrior.toFixed(2)}</span> · <span style={{ color: '#3fb950' }}>🌾 farmer {data.specialization.farmer.toFixed(2)}</span> · <span style={{ color: '#8b949e' }}>🦴 scavenger {data.specialization.scavenger.toFixed(2)}</span>
          </div>
        )}
        {data.culture && <div className="chip" style={{ marginBottom: 8 }}>🎭 {data.culture}</div>}

        <h3 style={{ fontSize: 13, color: '#e6edf3', margin: '12px 0 6px' }}>Members — {data.members.length} alive</h3>
        {data.members.length === 0 ? (
          <p className="chip">No living members — clan is extinct. History remains.</p>
        ) : (
          <div style={{ display: 'grid', gap: 6, maxHeight: 220, overflow: 'auto' }}>
            {data.members.map(m => (
              <div key={m.id} onClick={() => onSelectCreature?.(m.id)} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(110,118,129,0.08)', borderRadius: 4, cursor: onSelectCreature ? 'pointer' : 'default', borderLeft: `3px solid ${data.color}` }}>
                <span><b>{m.personal_name}</b> {m.glyph} #{m.id} · {m.caste} · {m.sex} · {m.stage}</span>
                <span className="chip" style={{ fontSize: 11 }}>{m.status || 'alive'} · {Math.round(m.energy)}⚡ {Math.round(m.health)}❤</span>
              </div>
            ))}
          </div>
        )}

        <h3 style={{ fontSize: 13, color: '#e6edf3', margin: '12px 0 6px' }}>Recent clan events</h3>
        {data.events.length === 0 ? <p className="chip">No recent events.</p> : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, maxHeight: 160, overflow: 'auto' }}>
            {data.events.map((ev: any, i: number) => (
              <li key={i} style={{ fontSize: 12, padding: '4px 0', borderBottom: '1px solid rgba(48,54,61,0.5)' }}>
                <b>{ev.type}</b> at tick {ev.tick} {ev.caste ? `· ${ev.caste}` : ''} {ev.cause ? `· ${ev.cause}` : ''}
              </li>
            ))}
          </ul>
        )}

        <div style={{ marginTop: 12, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
