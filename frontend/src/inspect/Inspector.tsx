import { useEffect, useRef, useState } from 'react'
import type { EntityState, HistoryEvent } from '../types'
import { totemEmoji } from '../totems'
import { useI18n } from '../i18n'
import { CreatureAvatar, CASTE_COLORS } from '../components/CreatureAvatar'


interface KinCard {
  id: number
  caste: string | null
  alive: boolean
  clan_color: string | null
  personal_name?: string | null
  glyph?: string | null
  hue_shift?: number | null
  scale_jitter?: number | null
}

interface Family {
  mother: KinCard | null
  father: KinCard | null
  children: KinCard[]
}

interface CreatureResponse {
  entity: EntityState | null
  events: HistoryEvent[]
  family?: Family
}

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="insp-bar">
      <span className="chip" style={{ minWidth: 60 }}>{label}</span>
      <div className="insp-track">
        <div className="insp-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="chip" style={{ minWidth: 32, textAlign: 'right' }}>
        <b>{Math.round(value)}</b>
      </span>
    </div>
  )
}

function eventLine(ev: HistoryEvent, t: (k: string, v?: any) => string): string {
  switch (ev.type) {
    case 'birth':
      return t('inspector.bornTo', { mother: (ev.payload as any)?.mother, father: (ev.payload as any)?.father })
    case 'promotion':
      return t('inspector.roseTo', { caste: ev.caste })
    case 'demotion':
      return t('inspector.demoted', { caste: ev.caste })
    case 'recovery':
      return t('inspector.recovered', { id: (ev.payload as any)?.disease_id ?? '' })
    case 'death':
      return t('inspector.diedOf', { cause: ev.cause, x: Math.round(ev.x), y: Math.round(ev.y) })
    default:
      return ev.type
  }
}
// keep for future i18n use
void eventLine

function KinCardView({
  kin,
  role,
  onNavigate,
}: {
  kin: KinCard | null
  role: string
  onNavigate: (id: number) => void
}) {
  const { t } = useI18n()
  if (!kin) return <div className="kin-node empty" style={{ background: '#161b22', border: '1px dashed #30363d', borderRadius: 6, padding: '8px 10px', color: '#8b949e', fontSize: 12 }}>{role}: —</div>
  return (
    <button
      className={`kin-node ${kin.alive ? '' : 'dead'}`}
      onClick={() => onNavigate(kin.id)}
      title={kin.alive ? t('inspector.openDossier') : t('inspector.deceased')}
      style={{ background: kin.alive ? '#161b22' : '#21262d', border: `1px solid ${kin.clan_color ?? '#30363d'}`, borderLeft: `3px solid ${kin.clan_color ?? '#8b949e'}`, borderRadius: 6, padding: '8px 10px', display: 'flex', flexDirection: 'column', gap: 2, cursor: 'pointer', textAlign: 'left', minWidth: 120 }}
    >
      <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>{role} {kin.alive ? '' : '†'}</span>
      <span style={{ fontWeight: 700, color: '#e6edf3', fontSize: 12 }}>{kin.personal_name ? `${kin.personal_name} ` : ''}#{kin.id} <span style={{ opacity: 0.7 }}>{kin.glyph ?? ''}</span></span>
      <span style={{ fontSize: 11, color: kin.alive ? '#3fb950' : '#8b949e' }}>{kin.caste ?? '?'} · {kin.alive ? t('inspector.alive') ?? 'alive' : t('inspector.deceased')}</span>
    </button>
  )
}

interface Props {
  id: number
  state?: any
  onClose: () => void
  onNavigate: (id: number) => void
  onSelectClan?: (clanId: number) => void
}

type TabKey = 'vitals' | 'skills' | 'lineage' | 'chronicle'

export default function Inspector({ id, onClose, onNavigate, onSelectClan }: Props) {
  const { t } = useI18n()
  const [data, setData] = useState<CreatureResponse | null>(null)
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
  const cycleSnap = () => {
    setSnap((s) => (s === 'peek' ? 'half' : s === 'half' ? 'full' : 'peek'))
  }
  const [activeTab, setActiveTab] = useState<TabKey>(() => {
    try {
      const s = sessionStorage.getItem('insp-tab') as TabKey | null
      if (s && ['vitals','skills','lineage','chronicle'].includes(s)) return s
    } catch {}
    return 'vitals'
  })

  useEffect(() => {
    try { sessionStorage.setItem('insp-tab', activeTab) } catch {}
  }, [activeTab])

  useEffect(() => {
    let alive = true
    const load = () =>
      fetch(`/api/creature/${id}`)
        .then((r) => r.json())
        .then((d) => alive && setData(d))
        .catch(() => {})
    load()
    const t = setInterval(() => {
      if (document.hidden) return
      load()
    }, 2000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [id])

  const e = data?.entity
  const fam = data?.family

  const statusChips: Array<{ text: string; cls: string }> = []
  if (e?.status === 'hungry') statusChips.push({ text: t('inspector.hungry'), cls: 'st-hungry' })
  if (e?.status === 'starving') statusChips.push({ text: t('inspector.starving'), cls: 'st-starving' })
  if (e?.infected) statusChips.push({ text: t('inspector.sick'), cls: 'st-sick' })
  if (e?.sleeping) statusChips.push({ text: t('inspector.asleep'), cls: 'st-asleep' })
  if ((e?.chill ?? 0) >= 12) statusChips.push({ text: t('inspector.chilled', { v: (e?.chill ?? 0).toFixed(1) }), cls: 'st-asleep' })

  return (
    <aside className="inspector" data-snap={snap}>
      <div
        className="inspector-handle"
        role="button"
        aria-label="drag handle"
        onClick={cycleSnap}
        onTouchStart={handleDragStart}
        onTouchEnd={handleDragEnd}
      />
      {/* Hero Header — compact geometric avatar */}
      <header className="god-head" style={{ borderBottom: '1px solid #21262d', paddingBottom: 8 }} onTouchStart={handleDragStart} onTouchEnd={handleDragEnd}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', fontSize: 14 }}>
          <span style={{ color: (e?.caste && CASTE_COLORS[e.caste]) || '#e6edf3' }}>{e?.personal_name ?? `${e?.caste ?? t('inspector.creature')}`} #{id}</span>
          {e?.title ? <span style={{ color: '#e3b341', fontSize: '0.85em', fontWeight: 600, background: 'rgba(227,179,65,0.12)', border: '1px solid #e3b341', borderRadius: 4, padding: '1px 5px' }}>{e.title}</span> : null}
          {e?.glyph ? <span title="soul-code glyph" style={{ fontSize: '0.9em' }}>{e.glyph}</span> : null}
        </h2>
        <button className="god-close" onClick={onClose} aria-label="close">×</button>
      </header>

      {e && (
        <div className="chip" style={{ fontSize: 11, opacity: 0.9, margin: '4px 0 6px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ background: CASTE_COLORS[e.caste ?? ''] ?? '#21262d', color: '#0d1117', padding: '1px 6px', borderRadius: 4, fontWeight: 700 }}>{e.caste}</span>
          <span>{e.shape === 'line' ? t('inspector.female') : t('inspector.male')} · {e.stage} · Gen {e.generation ?? 0}</span>
          {e.clan_id ? <span style={{ color: e.clan_color ?? '#58a6ff', fontWeight: 600 }}>{e.clan_name ?? `Clan ${e.clan_id}`} {totemEmoji(e.clan_totem)}</span> : null}
        </div>
      )}

      {e && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <CreatureAvatar e={e} />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {statusChips.length > 0 && (
              <div className="status-row" style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {statusChips.map((s) => (
                  <span key={s.text} className={`status-chip ${s.cls}`} style={{ fontSize: 11, padding: '2px 6px', borderRadius: 4, background: '#161b22', border: '1px solid #30363d' }}>{s.text}</span>
                ))}
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '6px 8px', borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 1 }}>
                <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>{t('inspector.energy')}</span>
                <span style={{ fontWeight: 700, color: '#d29922' }}>{Math.round(e.energy ?? 0)} / 100</span>
                <div className="insp-track" style={{ height: 3 }}><div className="insp-fill" style={{ width: `${Math.min(100, e.energy ?? 0)}%`, background: '#d29922' }} /></div>
              </div>
              <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '6px 8px', borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 1 }}>
                <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>{t('inspector.health')}</span>
                <span style={{ fontWeight: 700, color: '#3fb950' }}>{Math.round(e.health ?? 0)} / 100</span>
                <div className="insp-track" style={{ height: 3 }}><div className="insp-fill" style={{ width: `${Math.min(100, e.health ?? 0)}%`, background: '#3fb950' }} /></div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {e.personality && <span className="chip" style={{ fontSize: 11, background: '#21262d', border: '1px solid #30363d', padding: '2px 6px' }}>🎭 {e.personality}</span>}
              {e.equipped_item && <span className="chip" style={{ fontSize: 11, background: '#21262d', border: '1px solid #30363d', padding: '2px 6px' }}>{e.equipped_item === 'spear' ? '⚔ spear' : e.equipped_item === 'crown' ? '👑 crown' : e.equipped_item === 'basket' ? `🧺 ${e.food_basket ?? 0}` : e.equipped_item === 'herb_poultice' ? '🌿 poultice' : e.equipped_item}</span>}
              {typeof e.chill === 'number' && e.chill > 0.5 && <span className="chip" style={{ color: '#79c0ff', fontSize: 11 }}>❄ {e.chill.toFixed(1)}</span>}
            </div>
          </div>
        </div>
      )}

      {!e && data && <p className="god-note">{t('inspector.noLongerLiving')}</p>}

      {/* 4-Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, margin: '10px 0 8px', borderBottom: '1px solid #21262d', paddingBottom: 6, flexWrap: 'wrap' }}>
        {([
          ['vitals', t('inspector.tabVitals') !== 'inspector.tabVitals' ? t('inspector.tabVitals') : 'Vitals & Morph'],
          ['skills', t('inspector.tabSkills') !== 'inspector.tabSkills' ? t('inspector.tabSkills') : 'Skills & Neural'],
          ['lineage', t('inspector.tabLineage') !== 'inspector.tabLineage' ? t('inspector.tabLineage') : 'Lineage & Kin'],
          ['chronicle', t('inspector.tabChronicle') !== 'inspector.tabChronicle' ? t('inspector.tabChronicle') : 'Life Chronicle'],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => setActiveTab(k)}
            style={{
              flex: 1,
              minWidth: 64,
              padding: '6px 8px',
              fontSize: 11,
              fontWeight: activeTab === k ? 700 : 500,
              background: activeTab === k ? '#1f6feb' : '#21262d',
              color: activeTab === k ? '#fff' : '#8b949e',
              border: `1px solid ${activeTab === k ? '#1f6feb' : '#30363d'}`,
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {e && activeTab === 'vitals' && (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <Bar label={t('inspector.energy')} value={e.energy ?? 0} max={100} color="#d29922" />
            <Bar label={t('inspector.health')} value={e.health ?? 0} max={100} color="#3fb950" />
            {typeof e.chill === 'number' && e.chill > 0.5 && <Bar label={t('inspector.chill')} value={e.chill} max={24} color="#79c0ff" />}
          </div>
          <div className="insp-grid" style={{ marginTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            <span className="chip">{t('inspector.age')} <b>{e.age ?? 0}</b> / {Math.round(e.lifespan ?? 0)}</span>
            <span className="chip">{t('inspector.meals')} <b>{e.meals ?? 0}</b> · {t('inspector.sides')} <b>{e.sides}</b></span>
            {typeof e.irregularity === 'number' && e.irregularity > 0 && <span className="chip" style={{ color: '#f85149' }}>{t('inspector.irregularity')} <b>{e.irregularity}</b></span>}
            {e.clan_id != null && e.clan_id > 0 && (
              <button type="button" className="chip clan-link-chip" onClick={() => onSelectClan?.(e.clan_id!)} style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 5, border: `1px solid ${e.clan_color ?? '#58a6ff'}`, background: 'rgba(33,38,45,0.85)', color: '#e6edf3', borderRadius: 6, padding: '4px 8px', fontSize: 12, fontWeight: 600 }}>
                <span className="dot-inline" style={{ background: e.clan_color ?? '#8b949e', width: 7, height: 7, borderRadius: '50%' }} />
                <span>{e.clan_name ?? `Clan ${e.clan_id}`}</span><span style={{ fontSize: 10, color: '#58a6ff' }}>↗</span>
              </button>
            )}
            {e.trait && <span className="chip"> {e.trait === 'greedy' ? '⬔' : e.trait === 'peaceful' ? '◯' : e.trait === 'paranoid' ? '⬥' : e.trait === 'bold' ? '▲' : '•'} {e.trait}</span>}
          </div>
          {/* Morphology (BC) placeholder — shows when annealing enabled */}
          <div style={{ marginTop: 8, background: '#161b22', border: '1px solid #30363d', borderRadius: 6, padding: '8px 10px' }}>
            <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 }}>🧬 Morphology (BC)</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11 }}>
              <span className="chip" style={{ justifyContent: 'space-between' }}>Sides <b>{e.sides}</b></span>
              <span className="chip" style={{ justifyContent: 'space-between' }}>Shape <b>{e.shape}</b></span>
              <span className="chip" style={{ justifyContent: 'space-between' }}>Stage <b>{e.stage}</b></span>
              <span className="chip" style={{ justifyContent: 'space-between' }}>Gen <b>{e.generation ?? 0}</b></span>
            </div>
            <div style={{ fontSize: 10, color: '#8b949e', marginTop: 4 }}>Polar (r, φ) K 3-64 · trait baking A,P,Izz → Emax/steer when Morphology on.</div>
          </div>
        </>
      )}

      {e && activeTab === 'skills' && (
        <>
          {/* 2x2 circular mastery badge grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
            {[
              { name: t('inspector.farming'), key: 'farming', icon: '🌾', color: '#3fb950', max: 30 },
              { name: t('inspector.combat'), key: 'combat', icon: '⚔️', max: 30, color: '#ff7b72' },
              { name: t('inspector.foraging'), key: 'foraging', icon: '🦴', max: 30, color: '#d2a8ff' },
              { name: t('inspector.healing'), key: 'healing', icon: '🌿', max: 30, color: '#79c0ff' },
            ].map((sk) => {
              const xp = (e.skills as any)?.[sk.key] ?? 0
              const level = xp >= 30 ? 3 : xp >= 12 ? 2 : xp >= 4 ? 1 : 0
              const lvlName = level === 3 ? t('inspector.master') : level === 2 ? t('inspector.adept') : level === 1 ? t('inspector.novice') : t('inspector.unranked')
              const pct = Math.min(100, (xp / sk.max) * 100)
              return (
                <div key={sk.key} style={{ background: '#161b22', border: `1px solid ${sk.color}44`, borderRadius: 10, padding: '10px 8px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 52, height: 52, borderRadius: '50%', border: `3px solid ${sk.color}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, position: 'relative', background: `${sk.color}14` }}>
                    <span>{sk.icon}</span>
                    <div style={{ position: 'absolute', inset: -3, borderRadius: '50%', border: `3px solid transparent`, borderTopColor: sk.color, transform: `rotate(${pct * 3.6}deg)`, opacity: 0.9 }} />
                  </div>
                  <span style={{ fontWeight: 700, color: '#e6edf3', fontSize: 12 }}>{sk.name}</span>
                  <span style={{ fontSize: 11, color: sk.color, fontWeight: 600 }}>{lvlName} · {xp.toFixed(1)}/{sk.max}</span>
                </div>
              )
            })}
          </div>
          {/* Neural radar compact gauges */}
          <div style={{ background: '#0d1117', border: '1px solid #21262d', borderRadius: 8, padding: '8px 10px' }}>
            <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6, display: 'flex', justifyContent: 'space-between' }}>
              <span>🧠 Neural Engine (BA)</span>
              <span style={{ color: '#58a6ff', textTransform: 'none' }}>hidden {e.nn_hidden?.toFixed(3) ?? '—'}</span>
            </div>
            {e.nn_hidden == null && !e.nn_outputs ? (
              <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '8px', borderRadius: 6, fontSize: 12, color: '#8b949e' }}>Gathering live neural state — 16→12→7 (295) at 15 Hz.</div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {[
                  { label: 'Thrust', idx: 0, color: '#f0883e' },
                  { label: 'Steer', idx: 1, color: '#79c0ff' },
                  { label: 'Interact', idx: 2, color: '#ff7b72' },
                  { label: 'Social', idx: 3, color: '#a371f7' },
                  { label: 'Vocal amp', idx: 4, color: '#e3b341' },
                  { label: 'Vocal freq', idx: 5, color: '#bc8cff' },
                  { label: 'Recurrent', idx: 6, color: '#58a6ff' },
                ].map((o) => {
                  const v = e.nn_outputs?.[o.idx] ?? 0
                  const isSig = o.idx === 0 || o.idx === 4
                  const pct = isSig ? Math.max(0, Math.min(100, v * 100)) : Math.max(0, Math.min(100, (v + 1) * 50))
                  return (
                    <div key={o.label} style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 6, padding: '4px 6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#8b949e' }}><span>{o.label}</span><span style={{ color: o.color, fontFamily: 'ui-monospace' }}>{v.toFixed(2)}</span></div>
                      <div className="insp-track" style={{ height: 3, marginTop: 2 }}><div className="insp-fill" style={{ width: `${pct}%`, background: o.color }} /></div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}

      {e && activeTab === 'lineage' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <KinCardView kin={fam?.mother ?? null} role={t('inspector.mother')} onNavigate={onNavigate} />
            <KinCardView kin={fam?.father ?? null} role={t('inspector.father')} onNavigate={onNavigate} />
          </div>
          <div style={{ textAlign: 'center', background: '#1f6feb', color: '#fff', borderRadius: 6, padding: '6px 8px', fontWeight: 700, fontSize: 12, border: `1px solid ${e.clan_color ?? '#30363d'}` }}>
            #{id} · {t('inspector.currentSubject')} · {e.caste} {e.glyph ?? ''} Gen {e.generation ?? 0}
          </div>
          <div style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 8, padding: '8px 10px' }}>
            <div style={{ fontSize: 11, color: '#8b949e', textTransform: 'uppercase', marginBottom: 6 }}>{t('inspector.children') ?? 'Offspring'} ({fam?.children.length ?? 0})</div>
            {(fam?.children ?? []).length === 0 ? (
              <span className="chip" style={{ fontSize: 12 }}>{t('inspector.noOffspring')}</span>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, maxHeight: 220, overflowY: 'auto' }}>
                {fam!.children.map((k) => (
                  <KinCardView key={k.id} kin={k} role={t('inspector.child')} onNavigate={onNavigate} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'chronicle' && (
        <ul className="insp-events" style={{ maxHeight: 280, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {(data?.events ?? []).slice().reverse().map((ev) => (
            <li key={`${ev.tick}:${ev.type}`} className={`ev-${ev.type}`} style={{ background: '#161b22', border: '1px solid #21262d', borderRadius: 6, padding: '6px 8px', fontSize: 11, display: 'flex', justifyContent: 'space-between', gap: 6 }}>
              <span><b>{ev.type}</b> {ev.cause ? `· ${ev.cause}` : ''} {ev.caste ? `· ${ev.caste}` : ''}</span>
              <span style={{ color: '#8b949e', whiteSpace: 'nowrap' }}>tick {ev.tick}</span>
            </li>
          ))}
          {(data?.events?.length ?? 0) === 0 && <li className="chip">{t('inspector.nothingRecorded')}</li>}
        </ul>
      )}
    </aside>
  )
}
