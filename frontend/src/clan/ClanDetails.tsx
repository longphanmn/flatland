import { useEffect, useState } from 'react'
import { TOTEMS, totemEmoji } from '../totems'
import Collapsible from '../render/Collapsible'
import type { ClanHistoryEvent } from '../types'

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
  founded_day?: number
  dead_count?: number
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
  history?: ClanHistoryEvent[]
  faith?: number
  shrine_level?: number
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
    const t = setInterval(() => {
      if (document.hidden) return
      load()
    }, 2500)
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
          {data.totem ? `${totemEmoji(data.totem)} ${data.totem}` : 'No Avatar'} · Born tick {data.born_tick}
        </span>
        <span style={{ color: data.color, fontWeight: 700 }}>{data.population} alive</span>
      </div>

      {/* §AP Theology — avatar dogma + faith pool */}
      {(data.faith != null || (data.shrine_level ?? 0) >= 1) && (
        <div className="chip" title="§AP Theology — the Sacred Avatar watches this clan; dawn & dusk tithes fill its faith pool and the shrine aura mends the faithful">
          {(data.shrine_level ?? 0) >= 2 ? '⛪ Temple of the Sphere' : (data.shrine_level ?? 0) >= 1 ? '🕯️ Shrine consecrated' : 'No shrine'}
          {typeof data.faith === 'number' && data.faith > 0 ? ` · ⛲ ${Math.round(data.faith)} faith` : ''}
        </div>
      )}

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
        <span className="chip" title={`Founded at tick ${data.born_tick ?? 0}`}>
          🌱 Founded <b>Day {data.founded_day ?? Math.floor((data.born_tick ?? 0) / 1200)}</b>
        </span>
        <span className="chip dead" title="Total clan members who have died">
          💀 Dead <b>{data.dead_count ?? 0}</b>
        </span>
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
        <div style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px 8px', background: 'rgba(22, 27, 34, 0.6)', padding: '5px 8px', borderRadius: 4, border: '1px solid #30363d' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
            <span>👑</span>
            {data.house ? (
              <span><b style={{ color: '#e6edf3' }}>Main House #{data.house.id}</b> <span style={{ color: '#8b949e', fontSize: 11 }}>({Math.round(data.house.x)}, {Math.round(data.house.y)})</span></span>
            ) : (
              <span style={{ color: '#8b949e' }}>🏕 Homeless</span>
            )}
          </div>
          {data.house && data.leader_id ? (
            <span style={{ color: data.color, fontWeight: 600, fontSize: 11, background: `${data.color}22`, padding: '1px 6px', borderRadius: 3, border: `1px solid ${data.color}44`, whiteSpace: 'nowrap' }}>
              👑 Leader Residence
            </span>
          ) : null}
        </div>
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
          <div style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 5, color: '#e6edf3', fontSize: 12, background: 'rgba(22, 27, 34, 0.6)', padding: '4px 8px', borderRadius: 4, border: '1px solid #30363d', wordBreak: 'break-word' }}>
            <span>🎭</span> <span>{data.culture}</span>
          </div>
        )}
      </div>

      {/* Clan History & Major Milestones Section */}
      {data.history && data.history.length > 0 && (
        <Collapsible id={`clan-history-${data.id}`} title={<h3 className="insp-h">📜 Clan History & Milestones</h3>} defaultOpen={true}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 4, maxHeight: 180, overflowY: 'auto' }}>
            {data.history.slice().reverse().map((h, i) => (
              <div
                key={i}
                style={{
                  background: 'rgba(22, 27, 34, 0.7)',
                  borderLeft: `3px solid ${h.event === 'founded' ? '#3fb950' : h.event === 'leader_change' ? '#e3b341' : '#58a6ff'}`,
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 11,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e', fontSize: 10 }}>
                  <span style={{ textTransform: 'capitalize', fontWeight: 600, color: '#c9d1d9' }}>
                    {h.event === 'founded' ? '🌱 Foundation' :
                     h.event === 'leader_change' ? '👑 Succession' :
                     h.event === 'hq_relocated' ? '🏛️ Headquarters' :
                     h.event === 'war_declared' ? '⚔️ War' :
                     h.event === 'tribute_paid' ? '🤝 Treaty' : h.event}
                  </span>
                  <span>Day {h.day} · tick {h.tick}</span>
                </div>
                <div style={{ color: '#e6edf3', marginTop: 1 }}>{h.desc}</div>
              </div>
            ))}
          </div>
        </Collapsible>
      )}

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
                  {h.is_main ? '👑 Main House' : '🏠 Outpost'} #{h.id} ({Math.round(h.x)}, {Math.round(h.y)})
                </span>
                <span style={{ fontSize: 10.5, color: h.is_main ? '#e3b341' : '#8b949e', fontWeight: 600 }}>
                  {h.is_main ? `Leader HQ` : `size ${h.size.toFixed(1)}`}
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 180, overflowY: 'auto' }}>
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
      <Collapsible id={`clan-events-${data.id}`} title={<h3 className="insp-h">Recent Activity</h3>}>
        {data.events.length === 0 ? (
          <p className="chip" style={{ margin: '4px 0' }}>No recent clan events.</p>
        ) : (
          <ul className="insp-events" style={{ maxHeight: 150, overflowY: 'auto', margin: 0, padding: 0 }}>
            {data.events.slice().reverse().map((ev: any, i: number) => (
              <li key={i} className={`ev-${ev.type}`} style={{ fontSize: 11.5 }}>
                tick {ev.tick}: <b>{ev.type}</b> {ev.caste ? `· ${ev.caste}` : ''} {ev.cause ? `· ${ev.cause}` : ''}
              </li>
            ))}
          </ul>
        )}
      </Collapsible>

      {/* §AT-1 Full History — every clan event, paginated from the server */}
      <FullHistory clanId={data.id} color={data.color} />
    </aside>
  )
}

function FullHistory({ clanId, color }: { clanId: number; color: string }) {
  const [open, setOpen] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  const loadPage = (p: number, replace: boolean) => {
    setLoading(true)
    fetch(`/api/clans/${clanId}/history?page=${p}&size=50`)
      .then((r) => r.json())
      .then((d) => {
        setEvents((prev) => (replace ? d.events : [...prev, ...d.events]))
        setHasMore(d.has_more)
        setTotal(d.total)
        setPage(p)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  if (!open) {
    return (
      <button
        type="button"
        className="chip"
        style={{ margin: '4px 0', cursor: 'pointer', textAlign: 'left', borderLeft: `3px solid ${color}` }}
        onClick={() => {
          setOpen(true)
          loadPage(0, true)
        }}
      >
        📚 Full History (all pages)
      </button>
    )
  }
  return (
    <div style={{ marginTop: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span className="chip">📚 Full History · {total} events</span>
        <button type="button" className="chip" style={{ cursor: 'pointer' }} onClick={() => setOpen(false)}>
          close
        </button>
      </div>
      <ul className="insp-events" style={{ maxHeight: 220, overflowY: 'auto', margin: 0, padding: 0 }}>
        {events.map((ev: any, i: number) => (
          <li key={`${ev.tick}-${ev.entity_id}-${i}`} className={`ev-${ev.type}`} style={{ fontSize: 11.5 }}>
            tick {ev.tick}: <b>{ev.type}</b> {ev.caste ? `· ${ev.caste}` : ''} {ev.cause ? `· ${ev.cause}` : ''}
          </li>
        ))}
        {events.length === 0 && !loading && (
          <li className="chip" style={{ fontSize: 11.5 }}>No recorded clan events.</li>
        )}
      </ul>
      {hasMore && (
        <button
          type="button"
          className="chip"
          style={{ margin: '4px auto 0', display: 'block', cursor: 'pointer' }}
          disabled={loading}
          onClick={() => loadPage(page + 1, false)}
        >
          {loading ? 'loading…' : 'load older'}
        </button>
      )}
    </div>
  )
}
