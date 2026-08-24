import { useEffect, useState } from 'react'
import type { EntityState, HistoryEvent } from '../types'
import Collapsible from '../render/Collapsible'
import { totemEmoji } from '../totems'

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
  // hue shift for avatar border? keep simple use base color
  const points = isLine
    ? null
    : isPriest
      ? null
      : Array.from({ length: sides }, (_, i) => {
          const a = (i / sides) * Math.PI * 2 - Math.PI / 2 + ((e.angle_jitter ?? 0))
          return `${cx + Math.cos(a) * r},${cy + Math.sin(a) * r}`
        }).join(' ')
  return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 4px' }}>
      <svg width={80} height={80} viewBox="0 0 80 80" style={{ background: '#161b22', borderRadius: 10, border: `1px solid ${e.clan_color ?? '#30363d'}` }}>
        {/* clan ring */}
        {e.clan_color && <circle cx={cx} cy={cy} r={r + 6} fill="none" stroke={e.clan_color} strokeWidth={1.2} opacity={0.9} />}
        {/* body */}
        {isLine ? (
          <line x1={cx - r * 1.3} y1={cy} x2={cx + r * 1.3} y2={cy} stroke={color} strokeWidth={3} strokeLinecap="round" />
        ) : isPriest ? (
          <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} />
        ) : (
          <polygon points={points!} fill={color} fillOpacity={0.22} stroke={color} strokeWidth={1.2} strokeLinejoin="round" />
        )}
        {/* glyph in center */}
        {e.glyph && (
          <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle" fontSize={r * 0.85} fill="#e6edf3" style={{ fontFamily: 'ui-monospace, monospace' }}>
            {e.glyph}
          </text>
        )}
        {/* status dots */}
        {e.infected && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#3fb950" stroke="#0d1117" strokeWidth={1} />}
        {e.status === 'starving' && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#f85149" stroke="#0d1117" strokeWidth={1} />}
        {e.status === 'hungry' && <circle cx={cx + 22} cy={cy - 22} r={4} fill="#d29922" stroke="#0d1117" strokeWidth={1} />}
        {(e.chill ?? 0) >= 12 && <circle cx={cx - 22} cy={cy - 22} r={4} fill="#79c0ff" stroke="#0d1117" strokeWidth={1} />}
        {/* trait glyph corner */}
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
      <span className="chip">{label}</span>
      <div className="insp-track">
        <div className="insp-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="chip">
        <b>{Math.round(value)}</b>
      </span>
    </div>
  )
}

function eventLine(ev: HistoryEvent): string {
  switch (ev.type) {
    case 'birth':
      return `born to #${(ev.payload as any)?.mother} × #${(ev.payload as any)?.father}`
    case 'promotion':
      return `rose to ${ev.caste}`
    case 'demotion':
      return `judged irregular → ${ev.caste}`
    case 'recovery':
      return `recovered from disease ${(ev.payload as any)?.disease_id ?? ''}`
    case 'death':
      return `died of ${ev.cause} (${Math.round(ev.x)}, ${Math.round(ev.y)})`
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
  if (!kin) return <div className="kin-node empty">{label}: —</div>
  return (
    <button
      className={`kin-node ${kin.alive ? '' : 'dead'}`}
      onClick={() => onNavigate(kin.id)}
      title={kin.alive ? 'open dossier' : 'deceased — view record'}
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
  const [data, setData] = useState<CreatureResponse | null>(null)

  useEffect(() => {
    let alive = true
    const load = () =>
      fetch(`/api/creature/${id}`)
        .then((r) => r.json())
        .then((d) => alive && setData(d))
        .catch(() => {})
    load()
    const t = setInterval(load, 1000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [id])

  const e = data?.entity
  const fam = data?.family

  const statusChips: Array<{ text: string; cls: string }> = []
  if (e?.status === 'hungry') statusChips.push({ text: 'hungry', cls: 'st-hungry' })
  if (e?.status === 'starving') statusChips.push({ text: 'starving', cls: 'st-starving' })
  if (e?.infected) statusChips.push({ text: 'sick', cls: 'st-sick' })
  if (e?.sleeping) statusChips.push({ text: 'asleep', cls: 'st-asleep' })
  if ((e?.chill ?? 0) >= 12) statusChips.push({ text: `chilled ${(e?.chill ?? 0).toFixed(1)}`, cls: 'st-asleep' })

  return (
    <aside className="inspector">
      <header className="god-head">
        <h2>
          {e?.personal_name ?? `${e?.caste ?? 'Creature'} #${id}`} {e?.glyph ? <span title="soul-code glyph">{e.glyph}</span> : ''}
          {e && ` · ${e.shape === 'line' ? 'female' : 'male'}`}
        </h2>
        <button className="god-close" onClick={onClose} aria-label="close">
          ×
        </button>
      </header>
      {e && (
        <div className="chip" style={{ fontSize: 11, opacity: 0.8 }}>
          {e.personal_name} · {e.caste} #{id} {e.glyph} · scale {(e.scale_jitter ?? 1).toFixed(2)} · hue {(e.hue_shift ?? 0) > 0 ? '+' : ''}{e.hue_shift ?? 0}°
        </div>
      )}
      {e && <CreatureAvatar e={e} />}

      {!e && data && <p className="god-note">no longer among the living — their chronicle remains.</p>}
      {e && (
        <>
          {statusChips.length > 0 && (
            <div className="status-row">
              {statusChips.map((s) => (
                <span key={s.text} className={`status-chip ${s.cls}`}>
                  {s.text}
                </span>
              ))}
            </div>
          )}
          <Bar label="energy" value={e.energy ?? 0} max={100} color="#d29922" />
          <Bar label="health" value={e.health ?? 0} max={100} color="#3fb950" />
          {typeof e.chill === 'number' && e.chill > 0.5 && (
            <Bar label="chill" value={e.chill} max={24} color="#79c0ff" />
          )}
          <div className="insp-grid">
            <span className="chip">
              age <b>{e.age ?? 0}</b> / {Math.round(e.lifespan ?? 0)} · {e.stage}
            </span>
            <span className="chip">
              meals <b>{e.meals ?? 0}</b> · sides <b>{e.sides}</b> · gen{' '}
              <b>{e.generation ?? 0}</b>
            </span>
            {typeof e.irregularity === 'number' && e.irregularity > 0 && (
              <span className="chip" style={{ color: '#f85149' }}>
                irregularity <b>{e.irregularity}</b>
              </span>
            )}
            {e.clan_id != null && e.clan_id > 0 && (
              <button
                type="button"
                className="chip clan-link-chip"
                onClick={() => onSelectClan?.(e.clan_id!)}
                title={`Open clan details for ${e.clan_name ?? `Clan ${e.clan_id}`}`}
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
              <span className="chip" title={`Heritable trait: ${e.trait} — greedy/peaceful/paranoid/bold nudges food/war/flee`}>
                {e.trait === 'greedy' ? '⬔' : e.trait === 'peaceful' ? '◯' : e.trait === 'paranoid' ? '⬥' : e.trait === 'bold' ? '▲' : '•'} {e.trait}
              </span>
            )}
          </div>

          {/* ---- family tree ---- */}
          <Collapsible id="inspector-family" title={<h3 className="insp-h">Family</h3>}>
            <div className="family-tree">
              <div className="tree-row">
                <KinNode kin={fam?.mother ?? null} label="♀ mother" onNavigate={onNavigate} />
                <KinNode kin={fam?.father ?? null} label="♂ father" onNavigate={onNavigate} />
              </div>
              <div className="tree-self">#{id} ← you are here</div>
              <div className="tree-row wrap">
                {(fam?.children ?? []).length === 0 ? (
                  <span className="chip">no children yet</span>
                ) : (
                  fam!.children.map((k) => (
                    <KinNode key={k.id} kin={k} label="child" onNavigate={onNavigate} />
                  ))
                )}
              </div>
            </div>
          </Collapsible>
        </>
      )}

      <Collapsible id="inspector-chronicle" title={<h3 className="insp-h">Chronicle</h3>}>
        <ul className="insp-events">
          {(data?.events ?? []).slice().reverse().map((ev) => (
            <li key={`${ev.tick}:${ev.type}`} className={`ev-${ev.type}`}>
              tick {ev.tick}: {eventLine(ev)}
            </li>
          ))}
          {(data?.events?.length ?? 0) === 0 && (
            <li className="chip">nothing recorded yet</li>
          )}
        </ul>
      </Collapsible>
    </aside>
  )
}
