import { useEffect, useState } from 'react'
import { TOTEMS, totemEmoji } from '../totems'
import Collapsible from '../render/Collapsible'

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

interface ClanHouse {
  id: number
  x: number
  y: number
  size: number
  is_main?: boolean
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
  house: ClanHouse | null
  houses?: ClanHouse[]
  main_house_id?: number | null
  war_wins: number
  war_losses: number
  territory_radius: number | null
  specialization: { warrior: number; farmer: number; scavenger: number } | null
  culture: string | null
  members: ClanMember[]
  events: any[]
}

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="insp-bar">
      <span className="chip" style={{ minWidth: 80 }}>{label}</span>
      <div className="insp-track">
        <div className="insp-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="chip">
        <b>{Math.round(value)}%</b>
      </span>
    </div>
  )
}

export default function ClanDetails({
  clanId,
  onClose,
  onSelectCreature,
}: {
  clanId: number
  onClose: () => void
  onSelectCreature?: (id: number) => void
}) {
  const [data, setData] = useState<ClanDetailsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    let alive = true
    const load = () => {
      fetch(`/api/clans/${clanId}`)
        .then((r) => r.json())
        .then((d) => {
          if (alive) {
            setData(d)
            setLoading(false)
          }
        })
        .catch(() => {
          if (alive) setLoading(false)
        })
    }
    load()
    const t = setInterval(load, 1500)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [clanId])

  if (loading && !data) {
    return (
      <aside className="inspector clan-inspector">
        <header className="god-head">
          <h2>Clan #{clanId}</h2>
          <button className="god-close" onClick={onClose} aria-label="close">×</button>
        </header>
        <p className="god-note">Loading clan dossier…</p>
      </aside>
    )
  }

  if (!data) {
    return (
      <aside className="inspector clan-inspector">
        <header className="god-head">
          <h2>Clan #{clanId}</h2>
          <button className="god-close" onClick={onClose} aria-label="close">×</button>
        </header>
        <p className="god-note">Clan not found or has perished from the world.</p>
      </aside>
    )
  }

  const totemInfo = data.totem ? TOTEMS[data.totem] : null

  return (
    <aside className="inspector clan-inspector">
      <header className="god-head">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8, color: data.color }}>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: data.color,
              display: 'inline-block',
              boxShadow: `0 0 6px ${data.color}`,
            }}
          />
          {data.name} <span style={{ fontSize: 11, color: '#8b949e' }}>#{data.id}</span>
        </h2>
        <button className="god-close" onClick={onClose} aria-label="close">
          ×
        </button>
      </header>

      <div
        className="chip"
        style={{
          fontSize: 11,
          opacity: 0.9,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>
          {data.totem ? `${totemEmoji(data.totem)} ${data.totem} Totem` : 'No Totem'} · Born tick {data.born_tick}
        </span>
        <span style={{ color: data.color, fontWeight: 700 }}>{data.population} alive</span>
      </div>

      {/* Totem & Clan Emblem Box */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0 2px' }}>
        <div
          style={{
            width: '100%',
            background: '#161b22',
            borderRadius: 8,
            border: `1px solid ${data.color}`,
            padding: '10px 12px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 3,
          }}
        >
          <span style={{ fontSize: 28, lineHeight: 1 }}>{data.totem ? totemEmoji(data.totem) : '🚩'}</span>
          <div style={{ fontSize: 13, fontWeight: 700, color: data.color }}>{data.name}</div>
          {totemInfo && (
            <div style={{ fontSize: 10.5, color: '#8b949e', marginTop: 1 }}>
              {totemInfo.buff}
            </div>
          )}
        </div>
      </div>

      {/* Clan Stats Grid */}
      <div className="insp-grid">
        <span className="chip">
          Founder{' '}
          {data.founder_id != null ? (
            <button
              type="button"
              className="chronicle-name"
              onClick={() => onSelectCreature?.(data.founder_id)}
              title="Inspect founder dossier"
              style={{ fontWeight: 600 }}
            >
              #{data.founder_id} ↗
            </button>
          ) : (
            '—'
          )}
        </span>
        <span className="chip">
          Leader{' '}
          {data.leader_id != null ? (
            <button
              type="button"
              className="chronicle-name"
              onClick={() => onSelectCreature?.(data.leader_id!)}
              title="Inspect leader dossier"
              style={{ fontWeight: 600, color: data.color }}
            >
              #{data.leader_id} ↗
            </button>
          ) : (
            'none'
          )}
        </span>
        <span className="chip">
          War <b>{data.war_wins}W</b> / <b>{data.war_losses}L</b>
        </span>
        <span className="chip" style={{ width: '100%' }}>
          {data.house ? (
            <>
              👑 <b>Main House</b> ({Math.round(data.house.x)}, {Math.round(data.house.y)}) ·{' '}
              <span style={{ color: data.color, fontWeight: 600 }}>Leader #{data.leader_id ?? '—'} lives here</span>
            </>
          ) : (
            <>🏕 Homeless</>
          )}
        </span>
        {((data.houses?.length ?? 0) > 1) && (
          <span className="chip">
            🏠 Houses <b>{data.houses!.length}</b> total
          </span>
        )}
        {data.territory_radius && (
          <span className="chip">
            📍 Radius <b>r{data.territory_radius}</b>
          </span>
        )}
        {data.culture && (
          <span className="chip" style={{ width: '100%' }}>
            🎭 {data.culture}
          </span>
        )}
      </div>

      {/* Houses Collapsible */}
      {(data.houses && data.houses.length > 0) && (
        <Collapsible id={`clan-houses-${data.id}`} title={<h3 className="insp-h">Houses ({data.houses.length})</h3>}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
            {data.houses.map((h) => (
              <div
                key={h.id}
                className="chip"
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '5px 8px',
                  background: h.is_main ? 'rgba(227, 179, 65, 0.12)' : 'rgba(22, 27, 34, 0.7)',
                  border: h.is_main ? '1px solid #e3b341' : `1px solid ${data.color}`,
                  borderRadius: 6,
                }}
              >
                <span>
                  {h.is_main ? '👑 Main House' : '🏠 House'} #{h.id} ({Math.round(h.x)}, {Math.round(h.y)})
                </span>
                <span style={{ fontSize: 10.5, color: h.is_main ? '#e3b341' : '#8b949e', fontWeight: 600 }}>
                  {h.is_main ? `Leader #${data.leader_id ?? '—'}` : `size ${h.size.toFixed(1)}`}
                </span>
              </div>
            ))}
          </div>
        </Collapsible>
      )}

      {/* Specialization Bars */}
      {data.specialization && (
        <Collapsible id={`clan-spec-${data.id}`} title={<h3 className="insp-h">Specialization</h3>}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
            <Bar label="⚔ warrior" value={data.specialization.warrior * 100} max={100} color="#ff7b72" />
            <Bar label="🌾 farmer" value={data.specialization.farmer * 100} max={100} color="#3fb950" />
            <Bar label="🦴 scavenger" value={data.specialization.scavenger * 100} max={100} color="#8b949e" />
          </div>
        </Collapsible>
      )}

      {/* Members Section */}
      <Collapsible id={`clan-members-${data.id}`} title={<h3 className="insp-h">Members ({data.members.length})</h3>}>
        {data.members.length === 0 ? (
          <p className="chip" style={{ margin: '4px 0' }}>No living members — clan is extinct.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 200, overflowY: 'auto' }}>
            {data.members.map((m) => (
              <button
                key={m.id}
                type="button"
                className="kin-node"
                onClick={() => onSelectCreature?.(m.id)}
                style={{
                  textAlign: 'left',
                  borderLeft: `3px solid ${data.color}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '5px 8px',
                  cursor: 'pointer',
                }}
                title={`Inspect creature #${m.id}`}
              >
                <span>
                  <b>{m.personal_name}</b> {m.glyph} #{m.id} · {m.caste}
                </span>
                <span style={{ fontSize: 10, opacity: 0.85 }}>
                  {Math.round(m.energy)}⚡ {Math.round(m.health)}❤
                </span>
              </button>
            ))}
          </div>
        )}
      </Collapsible>

      {/* Events / Chronicle Section */}
      <Collapsible id={`clan-events-${data.id}`} title={<h3 className="insp-h">Chronicle</h3>}>
        {data.events.length === 0 ? (
          <p className="chip" style={{ margin: '4px 0' }}>No recent clan events.</p>
        ) : (
          <ul className="insp-events" style={{ maxHeight: 160, overflowY: 'auto', margin: 0, padding: 0 }}>
            {data.events.slice().reverse().map((ev: any, i: number) => (
              <li key={i} className={`ev-${ev.type}`} style={{ fontSize: 11.5 }}>
                tick {ev.tick}: <b>{ev.type}</b> {ev.caste ? `· ${ev.caste}` : ''} {ev.cause ? `· ${ev.cause}` : ''}
              </li>
            ))}
          </ul>
        )}
      </Collapsible>
    </aside>
  )
}
