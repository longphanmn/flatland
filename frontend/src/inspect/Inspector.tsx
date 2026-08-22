import { useEffect, useState } from 'react'
import type { EntityState, HistoryEvent } from '../types'

interface KinCard {
  id: number
  caste: string | null
  alive: boolean
  clan_color: string | null
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
      #{kin.id} {kin.caste ?? '?'} {kin.alive ? '' : '†'}
    </button>
  )
}

interface Props {
  id: number
  onClose: () => void
  onNavigate: (id: number) => void
}

export default function Inspector({ id, onClose, onNavigate }: Props) {
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

  return (
    <aside className="inspector">
      <header className="god-head">
        <h2>
          {e?.caste ?? 'Creature'} #{id}
          {e && ` · ${e.shape === 'line' ? 'female' : 'male'}`}
        </h2>
        <button className="god-close" onClick={onClose} aria-label="close">
          ×
        </button>
      </header>

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
              <span className="chip" title={e.clan_name ?? undefined}>
                <span
                  className="dot-inline"
                  style={{ background: e.clan_color ?? '#8b949e', marginRight: 4 }}
                />
                {e.clan_name ?? `Clan ${e.clan_id}`}
              </span>
            )}
          </div>

          {/* ---- family tree ---- */}
          <h3 className="insp-h">Family</h3>
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
        </>
      )}

      <h3 className="insp-h">Chronicle</h3>
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
    </aside>
  )
}
