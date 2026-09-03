import { useEffect, useRef, useState } from 'react'
import { TOTEMS, totemEmoji } from '../totems'
import type { ClanHistoryEvent } from '../types'
import { useI18n } from '../i18n'

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

type TabKey = 'stronghold' | 'roster' | 'warfare' | 'annals'

export default function ClanDetails({
  clanId,
  state: _state,
  onClose,
  onSelectCreature,
}: {
  clanId: number
  state?: any
  onClose: () => void
  onSelectCreature?: (id: number) => void
}) {
  const { t } = useI18n()
  const [data, setData] = useState<ClanDetailsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [snap, setSnap] = useState<'peek' | 'half' | 'full'>('half')
  const startYRef = useRef<number | null>(null)
  const snapRef = useRef(snap)
  useEffect(() => { snapRef.current = snap }, [snap])
  const handleDragStart = (e: React.TouchEvent) => {
    startYRef.current = e.touches[0].clientY
  }
  const handleDragEnd = (e: React.TouchEvent) => {
    if (startYRef.current === null) return
    const dy = e.changedTouches[0].clientY - startYRef.current
    startYRef.current = null
    const cur = snapRef.current
    if (dy < -30) {
      if (cur === 'peek') setSnap('half')
      else if (cur === 'half') setSnap('full')
    } else if (dy > 30) {
      if (cur === 'full') setSnap('half')
      else if (cur === 'half') setSnap('peek')
      else if (cur === 'peek') onClose()
    }
  }
  const cycleSnap = () => setSnap((s) => (s === 'peek' ? 'half' : s === 'half' ? 'full' : 'peek'))
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    try {
      const s = sessionStorage.getItem('clan-tab') as TabKey | null
      if (s && ['stronghold','roster','warfare','annals'].includes(s)) return s
    } catch {}
    return 'stronghold'
  })
  const [rosterFilter, setRosterFilter] = useState<'all'|'warriors'|'harvesters'|'elders'|'sick'>('all')

  useEffect(() => {
    try { sessionStorage.setItem('clan-tab', activeTab) } catch {}
  }, [activeTab])

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
      <aside className="inspector clan-inspector" data-snap={snap}>
        <div className="inspector-handle" role="button" aria-label="drag handle" onClick={cycleSnap} onTouchStart={handleDragStart} onTouchEnd={handleDragEnd} />
        <header className="god-head" onTouchStart={handleDragStart} onTouchEnd={handleDragEnd}>
          <h2>Clan #{clanId}</h2>
          <button className="god-close" onClick={onClose} aria-label="close">×</button>
        </header>
        <p className="god-note">{t('clanDetails.loading')}</p>
      </aside>
    )
  }

  if (!data) {
    return (
      <aside className="inspector clan-inspector" data-snap={snap}>
        <div className="inspector-handle" role="button" aria-label="drag handle" onClick={cycleSnap} onTouchStart={handleDragStart} onTouchEnd={handleDragEnd} />
        <header className="god-head" onTouchStart={handleDragStart} onTouchEnd={handleDragEnd}>
          <h2>Clan #{clanId}</h2>
          <button className="god-close" onClick={onClose} aria-label="close">×</button>
        </header>
        <p className="god-note">{t('clanDetails.notFound')}</p>
      </aside>
    )
  }

  const totemInfo = data.totem ? TOTEMS[data.totem] : null

  const filteredMembers = data.members.filter(m => {
    if (rosterFilter === 'all') return true
    if (rosterFilter === 'warriors') return m.caste === 'Soldier' || m.caste === 'Predator'
    if (rosterFilter === 'harvesters') return m.caste === 'Artisan' || m.caste === 'Gentleman'
    if (rosterFilter === 'elders') return m.stage === 'elder'
    if (rosterFilter === 'sick') return m.status === 'hungry' || m.status === 'starving' || m.health < 60
    return true
  })

  return (
    <aside className="inspector clan-inspector" data-snap={snap}>
      <div className="inspector-handle" role="button" aria-label="drag handle" onClick={cycleSnap} onTouchStart={handleDragStart} onTouchEnd={handleDragEnd} />
      {/* Hero Header & Banner Crest */}
      <header className="god-head" style={{ borderBottom: `2px solid ${data.color}`, background: `${data.color}12`, margin: '-14px -16px 0 -16px', padding: '10px 12px', borderRadius: '12px 12px 0 0', gap: 8 }} onTouchStart={handleDragStart} onTouchEnd={handleDragEnd}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8, color: data.color, fontSize: 15, minWidth: 0, flex: 1, overflow: 'hidden' }}>
          <span style={{ width: 14, height: 14, borderRadius: '50%', background: data.color, display: 'inline-block', boxShadow: `0 0 8px ${data.color}`, flex: 'none' }} />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.name}</span> <span style={{ fontSize: 11, color: '#8b949e', flex: 'none' }}>#{data.id}</span>
          {data.totem && <span style={{ fontSize: 16, flex: 'none' }}>{totemEmoji(data.totem)}</span>}
        </h2>
        <button className="god-close" onClick={onClose} aria-label="close" style={{ flex: 'none' }}>×</button>
      </header>

      <div className="chip" style={{ fontSize: 11, opacity: 0.9, display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
        <span>{data.totem ? `${totemEmoji(data.totem)} ${data.totem}` : t('clanDetails.noAvatar')} · {t('clanDetails.bornTick', { tick: data.born_tick })}</span>
        <span style={{ color: data.color, fontWeight: 700 }}>{t('clanDetails.alive', { count: data.population })} · {t('clanDetails.dead', { count: data.dead_count ?? 0 })}</span>
      </div>

      {(data.faith != null || (data.shrine_level ?? 0) >= 1) && (
        <div className="chip" style={{ background: '#1c2128', border: '1px solid #30363d', padding: '4px 8px', fontSize: 11, display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
          <span>{(data.shrine_level ?? 0) >= 2 ? `🏛️ ${t('clanDetails.templeOfSphere')}` : (data.shrine_level ?? 0) >= 1 ? `⛩️ ${t('clanDetails.shrine')}` : t('clanDetails.noShrine')}</span>
          {typeof data.faith === 'number' && data.faith > 0 ? <span style={{ color: '#e3b341', fontWeight: 600 }}>✨ {Math.round(data.faith)}</span> : null}
          {data.leader_id && <button onClick={() => onSelectCreature?.(data.leader_id!)} style={{ marginLeft: 'auto', background: data.color, color: '#0d1117', border: 'none', borderRadius: 4, padding: '2px 6px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}>👑 #{data.leader_id}</button>}
        </div>
      )}

      {/* Banner Crest Hero */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '6px 0 2px' }}>
        <div style={{ width: '100%', background: '#161b22', borderRadius: 8, border: `1px solid ${data.color}`, padding: '10px 12px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
          <span style={{ fontSize: 28, lineHeight: 1 }}>{data.totem ? totemEmoji(data.totem) : '🚩'}</span>
          <div style={{ fontSize: 13, fontWeight: 700, color: data.color }}>{data.name}</div>
          <div style={{ fontSize: 11, color: '#8b949e' }}>{t('clanDetails.founded', { day: data.founded_day ?? Math.floor((data.born_tick ?? 0)/1200) })} · {t('clanDetails.war', { wins: data.war_wins, losses: data.war_losses })}</div>
          {totemInfo && <div style={{ fontSize: 10.5, color: '#8b949e', marginTop: 1 }}>{data.totem && t(`totems.${data.totem}`) !== `totems.${data.totem}` ? t(`totems.${data.totem}`) : totemInfo.buff}</div>}
        </div>
      </div>

      {/* 4-Tab Codex */}
      <div className="insp-tabs" style={{ display: 'flex', gap: 4, margin: '8px 0 8px', borderBottom: '1px solid #21262d', paddingBottom: 6 }}>
        {([
          ['stronghold', t('clanDetails.tabStronghold') !== 'clanDetails.tabStronghold' ? t('clanDetails.tabStronghold') : 'Stronghold'],
          ['roster', t('clanDetails.tabRoster') !== 'clanDetails.tabRoster' ? t('clanDetails.tabRoster') : 'Roster'],
          ['warfare', t('clanDetails.tabWarfare') !== 'clanDetails.tabWarfare' ? t('clanDetails.tabWarfare') : 'Warfare & Diplomacy'],
          ['annals', t('clanDetails.tabAnnals') !== 'clanDetails.tabAnnals' ? t('clanDetails.tabAnnals') : 'Annals'],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setActiveTab(k)}
            style={{ flex: 1, minWidth: 64, padding: '6px 8px', fontSize: 11, fontWeight: activeTab===k?700:500, background: activeTab===k ? '#1f6feb' : '#21262d', color: activeTab===k ? '#fff' : '#8b949e', border: `1px solid ${activeTab===k ? '#1f6feb' : '#30363d'}`, borderRadius: 6, cursor: 'pointer' }}
          >
            {label} {k==='roster' && `(${data.members.length})`}
          </button>
        ))}
      </div>

      {activeTab === 'stronghold' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
          <div className="insp-grid insp-2col">
            <span className="chip">{t('clanDetails.founded', { day: data.founded_day ?? Math.floor((data.born_tick ?? 0)/1200) })}</span>
            <span className="chip dead">{t('clanDetails.dead', { count: data.dead_count ?? 0 })}</span>
            <span className="chip">{t('clanDetails.founder')} {data.founder_id ? <button onClick={() => onSelectCreature?.(data.founder_id)} className="chronicle-name" style={{ fontWeight: 600 }}>#{data.founder_id} ↗</button> : '—'}</span>
            <span className="chip">{t('clanDetails.leader')} {data.leader_id ? <button onClick={() => onSelectCreature?.(data.leader_id!)} className="chronicle-name" style={{ fontWeight: 600, color: data.color }}>#{data.leader_id} ↗</button> : 'none'}</span>
          </div>
          <div style={{ background: 'rgba(22,27,34,0.6)', padding: '6px 8px', borderRadius: 6, border: '1px solid #30363d', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
            <span style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>👑 {data.house ? <b style={{ color: '#e6edf3' }}>{t('clanDetails.mainHouse', { id: data.house.id, x: Math.round(data.house.x), y: Math.round(data.house.y) })}</b> : <span style={{ color: '#8b949e' }}>{t('clanDetails.homeless')}</span>}</span>
            {data.territory_radius && <span className="chip" style={{ fontSize: 11 }}>{t('clanDetails.radius', { r: data.territory_radius })}</span>}
          </div>
          {(data.houses && data.houses.length > 0) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>{t('clanDetails.housesTitle', { count: data.houses.length })}</div>
              {data.houses.map((h) => (
                <div key={h.id} className="chip" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 8px', background: h.is_main ? 'rgba(227,179,65,0.12)' : 'rgba(22,27,34,0.7)', border: h.is_main ? '1px solid #e3b341' : `1px solid ${data.color}`, borderRadius: 6 }}>
                  <span>{h.is_main ? t('clanDetails.mainHouseLabel') : t('clanDetails.outpost')} #{h.id} ({Math.round(h.x)}, {Math.round(h.y)})</span>
                  <span style={{ fontSize: 10.5, color: h.is_main ? '#e3b341' : '#8b949e', fontWeight: 600 }}>{h.is_main ? t('clanDetails.leaderResidence') : t('clanDetails.size', { n: h.size.toFixed(1) })}</span>
                </div>
              ))}
            </div>
          )}
          {data.culture && <div style={{ background: 'rgba(22,27,34,0.6)', padding: '6px 8px', borderRadius: 6, border: '1px solid #30363d', fontSize: 12, color: '#e6edf3' }}>🎭 {data.culture}</div>}
        </div>
      )}

      {activeTab === 'roster' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {(['all','warriors','harvesters','elders','sick'] as const).map(k => (
              <button
                key={k}
                onClick={() => setRosterFilter(k)}
                style={{ padding: '4px 8px', fontSize: 11, borderRadius: 12, border: `1px solid ${rosterFilter===k ? '#1f6feb' : '#30363d'}`, background: rosterFilter===k ? '#1f6feb' : '#21262d', color: rosterFilter===k ? '#fff' : '#8b949e', cursor: 'pointer', fontWeight: rosterFilter===k?600:400 }}
              >
                {k === 'all' ? `All (${data.members.length})` : k === 'warriors' ? `⚔ Warriors` : k === 'harvesters' ? `🌾 Harvesters` : k === 'elders' ? `👴 Elders` : `🤒 Sick`}
              </button>
            ))}
          </div>
          {filteredMembers.length === 0 ? (
            <p className="chip" style={{ margin: '4px 0' }}>{t('clanDetails.noMembers')}</p>
          ) : (
            <div className="clan-roster-list" style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 320, overflowY: 'auto', minWidth: 0 }}>
              {filteredMembers.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className="kin-node"
                  onClick={() => onSelectCreature?.(m.id)}
                  style={{ textAlign: 'left', borderLeft: `3px solid ${data.color}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '6px 8px', cursor: 'pointer', background: '#161b22', borderRadius: 6, border: '1px solid #21262d', borderLeftColor: data.color, minWidth: 0, width: '100%' }}
                  title={t('clanDetails.inspectCreature', { id: m.id })}
                >
                  <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0, flex: 1 }}>
                    <span style={{ fontWeight: 700, color: '#e6edf3', fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}><b>{m.personal_name}</b> {m.glyph} #{m.id} · {m.caste} <span style={{ color: m.sex === 'female' ? '#ff9bce' : '#79c0ff', fontSize: 10 }}>{m.stage}</span></span>
                    <span style={{ fontSize: 10, color: '#8b949e', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.status ? `${m.status} · ` : ''}Age {m.age}/{Math.round(m.lifespan)} · {m.energy.toFixed(0)}⚡ {m.health.toFixed(0)}❤</span>
                  </span>
                  <span style={{ fontSize: 11, color: '#58a6ff', flex: 'none' }}>↗</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'warfare' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 700, color: '#e6edf3', fontSize: 12 }}>{t('clanDetails.war', { wins: data.war_wins, losses: data.war_losses })} </span>
            <span style={{ fontSize: 11, color: data.war_wins > data.war_losses ? '#3fb950' : data.war_losses > data.war_wins ? '#f85149' : '#8b949e', fontWeight: 700 }}>
              {data.war_wins > data.war_losses ? '▲ Dominant' : data.war_losses > data.war_wins ? '▼ Struggling' : '— Balanced'}
            </span>
          </div>
          {data.specialization && (
            <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
              <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 }}>{t('clanDetails.specialization')}</div>
              <Bar label="⚔ warrior" value={data.specialization.warrior * 100} max={100} color="#ff7b72" />
              <Bar label="🌾 farmer" value={data.specialization.farmer * 100} max={100} color="#3fb950" />
              <Bar label="🦴 scavenger" value={data.specialization.scavenger * 100} max={100} color="#8b949e" />
              {/* tri-wheel visual */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginTop: 8, textAlign: 'center', fontSize: 11 }}>
                {[
                  { k: 'warrior', v: data.specialization.warrior, icon: '⚔️', color: '#ff7b72' },
                  { k: 'farmer', v: data.specialization.farmer, icon: '🌾', color: '#3fb950' },
                  { k: 'scavenger', v: data.specialization.scavenger, icon: '🦴', color: '#8b949e' },
                ].map(o => (
                  <div key={o.k} style={{ background: `${o.color}12`, border: `1px solid ${o.color}44`, borderRadius: 8, padding: '6px 4px' }}>
                    <div style={{ fontSize: 16 }}>{o.icon}</div>
                    <div style={{ fontWeight: 700, color: o.color }}>{Math.round(o.v*100)}%</div>
                    <div style={{ color: '#8b949e', fontSize: 10, textTransform: 'uppercase' }}>{o.k}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px', fontSize: 12, color: '#8b949e' }}>
            <div style={{ fontWeight: 600, color: '#e6edf3', marginBottom: 4, fontSize: 11, textTransform: 'uppercase' }}>{t('clanDetails.diplomaticIntel')}</div>
            <p style={{ margin: 0 }}>Relations drift {data.territory_radius ? `@ ${data.territory_radius} radius` : ''} · War pairs and alliances tracked in Overview’s Geopolitics. Clan-specific Casus Belli (famine/territory/blood feud) surfaced via `war_declared` history.</p>
            {data.events.length > 0 && <div style={{ marginTop: 6, fontSize: 11 }}>{data.events.slice(0,3).map((ev: any,i:number)=>(<div key={i} style={{ padding: '2px 0', borderBottom: '1px solid #21262d' }}><b>{ev.type}</b> tick {ev.tick} {ev.cause?`· ${ev.cause}`:''}</div>))}</div>}
          </div>
        </div>
      )}

      {activeTab === 'annals' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data.history && data.history.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 180, overflowY: 'auto' }}>
              {data.history.slice().reverse().map((h, i) => (
                <div key={i} style={{ background: 'rgba(22,27,34,0.7)', borderLeft: `3px solid ${h.event === 'founded' ? '#3fb950' : h.event === 'leader_change' ? '#e3b341' : '#58a6ff'}`, borderRadius: 4, padding: '4px 8px', fontSize: 11 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#8b949e', fontSize: 10 }}>
                    <span style={{ textTransform: 'capitalize', fontWeight: 600, color: '#c9d1d9' }}>
                      {h.event === 'founded' ? t('clanDetails.foundation') : h.event === 'leader_change' ? t('clanDetails.succession') : h.event === 'hq_relocated' ? t('clanDetails.hq') : h.event === 'war_declared' ? t('clanDetails.warEvent') : h.event === 'tribute_paid' ? t('clanDetails.treaty') : h.event}
                    </span>
                    <span>Day {h.day} · tick {h.tick}</span>
                  </div>
                  <div style={{ color: '#e6edf3', marginTop: 1 }}>{h.desc}</div>
                </div>
              ))}
            </div>
          )}
          <div style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: 6, padding: '6px 8px' }}>
            <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', marginBottom: 4 }}>{t('clanDetails.recentActivity')}</div>
            {data.events.length === 0 ? (
              <p className="chip" style={{ margin: '4px 0' }}>{t('clanDetails.noEvents')}</p>
            ) : (
              <ul className="insp-events" style={{ maxHeight: 120, overflowY: 'auto', margin: 0, padding: 0 }}>
                {data.events.slice().reverse().slice(0,8).map((ev: any, i: number) => (
                  <li key={i} className={`ev-${ev.type}`} style={{ fontSize: 11.5 }}>tick {ev.tick}: <b>{ev.type}</b> {ev.caste ? `· ${ev.caste}` : ''} {ev.cause ? `· ${ev.cause}` : ''}</li>
                ))}
              </ul>
            )}
          </div>
          <FullHistory clanId={data.id} color={data.color} />
        </div>
      )}
    </aside>
  )
}

function FullHistory({ clanId, color }: { clanId: number; color: string }) {
  const { t } = useI18n()
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
      <button type="button" className="chip" style={{ margin: '4px 0', cursor: 'pointer', textAlign: 'left', borderLeft: `3px solid ${color}` }} onClick={() => { setOpen(true); loadPage(0, true) }}>
        {t('clanDetails.fullHistory')}
      </button>
    )
  }
  return (
    <div style={{ marginTop: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span className="chip">{t('clanDetails.fullHistoryTitle', { total })}</span>
        <button type="button" className="chip" style={{ cursor: 'pointer' }} onClick={() => setOpen(false)}>{t('clanDetails.close')}</button>
      </div>
      <ul className="insp-events" style={{ maxHeight: 220, overflowY: 'auto', margin: 0, padding: 0 }}>
        {events.map((ev: any, i: number) => (
          <li key={`${ev.tick}-${ev.entity_id}-${i}`} className={`ev-${ev.type}`} style={{ fontSize: 11.5 }}>tick {ev.tick}: <b>{ev.type}</b> {ev.caste ? `· ${ev.caste}` : ''} {ev.cause ? `· ${ev.cause}` : ''}</li>
        ))}
        {events.length === 0 && !loading && <li className="chip" style={{ fontSize: 11.5 }}>{t('clanDetails.noRecorded')}</li>}
      </ul>
      {hasMore && (
        <button type="button" className="chip" style={{ margin: '4px auto 0', display: 'block', cursor: 'pointer' }} disabled={loading} onClick={() => loadPage(page + 1, false)}>
          {loading ? t('clanDetails.loading') : t('clanDetails.loadOlder')}
        </button>
      )}
    </div>
  )
}
