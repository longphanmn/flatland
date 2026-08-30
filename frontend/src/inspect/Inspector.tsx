import { useEffect, useState } from 'react'
import type { EntityState, HistoryEvent } from '../types'
import Collapsible from '../render/Collapsible'
import { totemEmoji } from '../totems'
import { useI18n } from '../i18n'

const CASTE_COLORS: Record<string, string> = {
  Soldier: '#ff7b72',
  Artisan: '#f2cc60',
  Gentleman: '#ffa657',
  Professional: '#d2a8ff',
  Noble: '#79c0ff',
  Priest: '#e6edf3',
  Woman: '#ff9bce',
  Predator: '#ff3838',
  Herbivore: '#90be6d',
}

function CreatureAvatar({ e }: { e: EntityState }) {
  const color = (e.caste && CASTE_COLORS[e.caste]) || '#8b949e'
  const sides = e.sides ?? 4
  const isLine = e.shape === 'line'
  const isPriest = sides >= 24
  const cx = 40
  const cy = 40
  const r = 18 * (e.scale_jitter ?? 1) * (e.stage === 'infant' ? 0.55 : e.stage === 'juvenile' ? 0.8 : 1)
  const points = isLine
    ? null
    : isPriest
      ? null
      : Array.from({ length: sides }, (_, i) => {
          const a = (i / sides) * Math.PI * 2 - Math.PI / 2 + ((e.angle_jitter ?? 0))
          return `${cx + Math.cos(a) * r},${cy + Math.sin(a) * r}`
        }).join(' ')
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '6px 0 2px' }}>
      <svg width={76} height={76} viewBox="0 0 80 80" style={{ background: '#161b22', borderRadius: 8, border: `1px solid ${e.clan_color ?? '#30363d'}` }}>
        {e.clan_color && <circle cx={cx} cy={cy} r={r + 6} fill="none" stroke={e.clan_color} strokeWidth={1.2} opacity={0.9} />}
        {isLine ? (
          <line x1={cx - r * 1.3} y1={cy} x2={cx + r * 1.3} y2={cy} stroke={color} strokeWidth={3} strokeLinecap="round" />
        ) : isPriest ? (
          <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} />
        ) : (
          <polygon points={points!} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} strokeLinejoin="round" />
        )}
        {e.glyph && (
          <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fontSize={r * 0.85} fill="#e6edf3" style={{ fontFamily: 'ui-monospace, monospace' }}>
            {e.glyph}
          </text>
        )}
        {e.infected && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#3fb950" stroke="#0d1117" strokeWidth={1} />}
        {e.status === 'starving' && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#f85149" stroke="#0d1117" strokeWidth={1} />}
        {e.status === 'hungry' && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#d29922" stroke="#0d1117" strokeWidth={1} />}
        {(e.chill ?? 0) >= 12 && <circle cx={cx - 22} cy={cy - 22} r={4} fill="#79c0ff" stroke="#0d1117" strokeWidth={1} />}
        {e.trait && (
          <text x={cx} y={72} textAnchor="middle" fontSize={7} fill="#8b949e">
            {e.trait === 'greedy' ? '⬔ greedy' : e.trait === 'peaceful' ? '◯ peaceful' : e.trait === 'paranoid' ? '⬥ paranoid' : e.trait === 'bold' ? '▲ bold' : e.trait}
          </text>
        )}
      </svg>
    </div>
  )
}

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

function KinNode({
  kin,
  label,
  onNavigate,
}: {
  kin: KinCard | null
  label: string
  onNavigate: (id: number) => void
}) {
  const { t } = useI18n()
  if (!kin) return <div className="kin-node empty">{label}: —</div>
  return (
    <button
      className={`kin-node ${kin.alive ? '' : 'dead'}`}
      onClick={() => onNavigate(kin.id)}
      title={kin.alive ? t('inspector.openDossier') : t('inspector.deceased')}
    >
      <span className="kin-role">{label}</span>{' '}
      {kin.personal_name ? `${kin.personal_name} ` : ''}#{kin.id} {kin.caste ?? '?'} {kin.glyph ? kin.glyph : ''} {kin.alive ? '' : '†'}
    </button>
  )
}

interface Props {
  id: number
  onClose: () => void
  onNavigate: (id: number) => void
  onSelectClan?: (clanId: number) => void
}

export default function Inspector({ id, onClose, onNavigate, onSelectClan }: Props) {
  const { t } = useI18n()
  const [data, setData] = useState<CreatureResponse | null>(null)

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
    <aside className="inspector">
      <header className="god-head">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span>{e?.personal_name ?? `${e?.caste ?? t('inspector.creature')}`} #{id}</span>
          {e?.title ? <span style={{ color: '#e3b341', fontSize: '0.85em', fontWeight: 600 }}>{e.title}</span> : null}
          {e?.glyph ? <span title="soul-code glyph" style={{ fontSize: '0.9em' }}>{e.glyph}</span> : null}
        </h2>
        <button className="god-close" onClick={onClose} aria-label="close">
          ×
        </button>
      </header>

      {e && (
        <div className="chip" style={{ fontSize: 11, opacity: 0.85, margin: '2px 0 4px' }}>
          {e.caste} · {e.shape === 'line' ? t('inspector.female') : t('inspector.male')} · {e.stage} · Gen {e.generation ?? 0}
        </div>
      )}

      {e && <CreatureAvatar e={e} />}

      {!e && data && <p className="god-note">{t('inspector.noLongerLiving')}</p>}

      {e && (
        <>
          {statusChips.length > 0 && (
            <div className="status-row" style={{ margin: '4px 0' }}>
              {statusChips.map((s) => (
                <span key={s.text} className={`status-chip ${s.cls}`}>
                  {s.text}
                </span>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, margin: '4px 0' }}>
            <Bar label={t('inspector.energy')} value={e.energy ?? 0} max={100} color="#d29922" />
            <Bar label={t('inspector.health')} value={e.health ?? 0} max={100} color="#3fb950" />
            {typeof e.chill === 'number' && e.chill > 0.5 && (
              <Bar label={t('inspector.chill')} value={e.chill} max={24} color="#79c0ff" />
            )}
          </div>

          {/* Personality & Equipped Tool */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, margin: '6px 0' }}>
            <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '6px 8px', borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>{t('inspector.personality')}</span>
              <span style={{ fontWeight: 600, color: '#58a6ff', textTransform: 'capitalize' }}>
                {e.personality === 'brave' ? t('inspector.brave') :
                 e.personality === 'cautious' ? t('inspector.cautious') :
                 e.personality === 'altruistic' ? t('inspector.altruistic') :
                 e.personality === 'greedy' ? t('inspector.greedy') :
                 e.personality === 'explorer' ? t('inspector.explorer') :
                 e.personality === 'builder' ? t('inspector.builder') : e.personality ?? t('inspector.brave')}
              </span>
            </div>
            <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '6px 8px', borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 }}>{t('inspector.toolBasket')}</span>
              <span style={{ fontWeight: 600, color: '#f2cc60' }}>
                {e.equipped_item === 'spear' ? t('inspector.spear') :
                 e.equipped_item === 'crown' ? t('inspector.crown') :
                 e.equipped_item === 'basket' ? t('inspector.basket', { n: e.food_basket ?? 0 }) :
                 e.equipped_item === 'herb_poultice' ? t('inspector.poultice') :
                 (e.food_basket ?? 0) > 0 ? t('inspector.food', { n: e.food_basket ?? 0 }) : t('inspector.none')}
              </span>
            </div>
          </div>

          {/* Skill Mastery Matrix */}
          <Collapsible id="inspector-skills" title={<h3 className="insp-h">{t('inspector.skillMastery')}</h3>} defaultOpen={true}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '4px 0' }}>
              {[
                { name: t('inspector.farming'), key: 'farming', icon: '🌾', max: 30, color: '#3fb950' },
                { name: t('inspector.combat'), key: 'combat', icon: '⚔️', max: 30, color: '#ff7b72' },
                { name: t('inspector.foraging'), key: 'foraging', icon: '🦴', max: 30, color: '#d2a8ff' },
                { name: t('inspector.healing'), key: 'healing', icon: '🌿', max: 30, color: '#79c0ff' },
              ].map((sk) => {
                const xp = (e.skills as any)?.[sk.key] ?? 0
                const level = xp >= 30 ? 3 : xp >= 12 ? 2 : xp >= 4 ? 1 : 0
                const lvlName = level === 3 ? t('inspector.master') : level === 2 ? t('inspector.adept') : level === 1 ? t('inspector.novice') : t('inspector.unranked')
                return (
                  <div key={sk.key} style={{ display: 'flex', flexDirection: 'column', gap: 2, background: 'rgba(22, 27, 34, 0.6)', padding: '4px 6px', borderRadius: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                      <span>{sk.icon} <b>{sk.name}</b> · {lvlName}</span>
                      <span style={{ color: '#8b949e' }}>{xp.toFixed(1)} / {sk.max} XP</span>
                    </div>
                    <div className="insp-track" style={{ height: 4 }}>
                      <div className="insp-fill" style={{ width: `${Math.min(100, (xp / sk.max) * 100)}%`, background: sk.color }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </Collapsible>

          {/* Neural Engine (BA) — always on */}
          <Collapsible id="inspector-nn" title={<h3 className="insp-h">🧠 Neural Engine (BA)</h3>} defaultOpen={true}>
            {e.nn_hidden == null && !e.nn_outputs ? (
              <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '8px', borderRadius: 6, fontSize: 12, color: '#8b949e' }}>
                Gathering live neural state — 16→12→7 (295) at 15 Hz (every 4th tick). Move or tap again in a moment.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '4px 0' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '6px 8px', borderRadius: 6 }}>
                    <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Hidden state</span>
                    <div style={{ fontWeight: 700, color: '#58a6ff', fontSize: 13 }}>{e.nn_hidden?.toFixed(3) ?? '—'} <span style={{ opacity: 0.6 }}>∈ [-1,1]</span></div>
                  </div>
                  <div className="chip" style={{ background: '#161b22', border: '1px solid #30363d', padding: '6px 8px', borderRadius: 6 }}>
                    <span style={{ fontSize: 10, color: '#8b949e', textTransform: 'uppercase' }}>Genome preview (8/295)</span>
                    <div style={{ fontFamily: 'ui-monospace, monospace', fontSize: 10, color: '#e6edf3', wordBreak: 'break-all' }}>
                      {e.nn_genome_preview ? e.nn_genome_preview.map((v) => v.toFixed(2)).join(', ') : '—'}
                    </div>
                  </div>
                </div>
                {e.nn_outputs && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {[
                      { label: 'Thrust', idx: 0, range: '[0,1]', color: '#f0883e', hint: 'sigmoid → velocity + energy drain' },
                      { label: 'Steer', idx: 1, range: '[-1,1]', color: '#79c0ff', hint: 'tanh → orientation' },
                      { label: 'Interact', idx: 2, range: '[-1,1]', color: '#ff7b72', hint: '>+0.3 consume, <-0.3 attack' },
                      { label: 'Social', idx: 3, range: '[-1,1]', color: '#a371f7', hint: '>+0.5 mating readiness' },
                      { label: 'Vocal amp', idx: 4, range: '[0,1]', color: '#e3b341', hint: 'sigmoid → audio amplitude' },
                      { label: 'Vocal freq', idx: 5, range: '[-1,1]', color: '#bc8cff', hint: 'tanh → audio freq' },
                      { label: 'Recurrent', idx: 6, range: '[-1,1]', color: '#58a6ff', hint: '→ next hidden' },
                    ].map((o) => {
                      const v = e.nn_outputs![o.idx] ?? 0
                      // map to 0-100% for bar
                      const isSigmoid = o.idx === 0 || o.idx === 4
                      const pct = isSigmoid ? Math.max(0, Math.min(100, v * 100)) : Math.max(0, Math.min(100, (v + 1) * 50))
                      return (
                        <div key={o.label} style={{ display: 'flex', flexDirection: 'column', gap: 2, background: 'rgba(22,27,34,0.6)', padding: '4px 6px', borderRadius: 4 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                            <span><b>{o.label}</b> <span style={{ color: '#8b949e' }}>{o.range}</span> <span style={{ opacity: 0.6, fontSize: 10 }}>{o.hint}</span></span>
                            <span style={{ color: o.color, fontWeight: 700, fontFamily: 'ui-monospace, monospace' }}>{v.toFixed(3)}</span>
                          </div>
                          <div className="insp-track" style={{ height: 4 }}>
                            <div className="insp-fill" style={{ width: `${pct}%`, background: o.color }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
                <div className="chip" style={{ fontSize: 10, color: '#8b949e', background: '#0d1117', border: '1px dashed #30363d', padding: '4px 6px', borderRadius: 4 }}>
                  Live from SoA: <code>nn_hidden</code> + <code>nn_outputs[7]</code> + <code>nn_genome_preview[8/295]</code> — 60 Hz physics, 15 Hz brain (latched). Always on — 295 fixed.
                </div>
              </div>
            )}
          </Collapsible>

          {/* Vitals & Affiliation Grid */}
          <div className="insp-grid">
            <span className="chip">
              {t('inspector.age')} <b>{e.age ?? 0}</b> / {Math.round(e.lifespan ?? 0)}
            </span>
            <span className="chip">
              {t('inspector.meals')} <b>{e.meals ?? 0}</b> · {t('inspector.sides')} <b>{e.sides}</b>
            </span>
            {typeof e.irregularity === 'number' && e.irregularity > 0 && (
              <span className="chip" style={{ color: '#f85149' }}>
                {t('inspector.irregularity')} <b>{e.irregularity}</b>
              </span>
            )}
            {e.clan_id != null && e.clan_id > 0 && (
              <button
                type="button"
                className="chip clan-link-chip"
                onClick={() => onSelectClan?.(e.clan_id!)}
                title={t('inspector.openClanDetails', { name: e.clan_name ?? `Clan ${e.clan_id}` })}
                style={{
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  border: `1px solid ${e.clan_color ?? '#58a6ff'}`,
                  background: 'rgba(33, 38, 45, 0.85)',
                  color: '#e6edf3',
                  borderRadius: 6,
                  padding: '4px 8px',
                  fontSize: 12,
                  fontWeight: 600,
                }}
              >
                {totemEmoji(e.clan_totem) && (
                  <span style={{ fontSize: 13, marginRight: 1 }}>{totemEmoji(e.clan_totem)}</span>
                )}
                <span
                  className="dot-inline"
                  style={{ background: e.clan_color ?? '#8b949e', width: 7, height: 7, borderRadius: '50%' }}
                />
                <span>{e.clan_name ?? `Clan ${e.clan_id}`}</span>
                <span style={{ fontSize: 10, color: '#58a6ff' }}>↗</span>
              </button>
            )}
            {e.trait && (
              <span className="chip" title={t('inspector.trait', { trait: e.trait })}>
                {e.trait === 'greedy' ? '⬔' : e.trait === 'peaceful' ? '◯' : e.trait === 'paranoid' ? '⬥' : e.trait === 'bold' ? '▲' : '•'} {e.trait}
              </span>
            )}
          </div>

          {/* Family Tree */}
          <Collapsible id="inspector-family" title={<h3 className="insp-h">{t('inspector.familyLineage')}</h3>}>
            <div className="family-tree">
              <div className="tree-row">
                <KinNode kin={fam?.mother ?? null} label={t('inspector.mother')} onNavigate={onNavigate} />
                <KinNode kin={fam?.father ?? null} label={t('inspector.father')} onNavigate={onNavigate} />
              </div>
              <div className="tree-self">#{id} · {t('inspector.currentSubject')}</div>
              <div className="tree-row wrap">
                {(fam?.children ?? []).length === 0 ? (
                  <span className="chip">{t('inspector.noOffspring')}</span>
                ) : (
                  fam!.children.map((k) => (
                    <KinNode key={k.id} kin={k} label={t('inspector.child')} onNavigate={onNavigate} />
                  ))
                )}
              </div>
            </div>
          </Collapsible>
        </>
      )}

      <Collapsible id="inspector-chronicle" title={<h3 className="insp-h">{t('inspector.personalChronicle')}</h3>}>
        <ul className="insp-events" style={{ maxHeight: 150, overflowY: 'auto' }}>
          {(data?.events ?? []).slice().reverse().map((ev) => (
            <li key={`${ev.tick}:${ev.type}`} className={`ev-${ev.type}`}>
              tick {ev.tick}: {eventLine(ev, t)}
            </li>
          ))}
          {(data?.events?.length ?? 0) === 0 && (
            <li className="chip">{t('inspector.nothingRecorded')}</li>
          )}
        </ul>
      </Collapsible>
    </aside>
  )
}
