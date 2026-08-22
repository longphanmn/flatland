import { useEffect, useState } from 'react'
import type { EntityState, HistoryEvent } from '../types'

interface CreatureResponse {
  entity: EntityState | null
  events: HistoryEvent[]
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

interface Props {
  id: number
  onClose: () => void
}

export default function Inspector({ id, onClose }: Props) {
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

      {!e && data && <p className="god-note">no longer among the living.</p>}
      {e && (
        <>
          <p className="god-note">
            generation {e.generation ?? 0} · born tick {e.born_tick ?? '?'} · stage{' '}
            {e.stage}
            {e.infected && ' · 🤒 infected'}
          </p>
          <Bar label="energy" value={e.energy ?? 0} max={100} color="#d29922" />
          <Bar label="health" value={e.health ?? 0} max={100} color="#3fb950" />
          <div className="insp-grid">
            <span className="chip">
              age <b>{e.age ?? 0}</b> / {Math.round(e.lifespan ?? 0)}
            </span>
            <span className="chip">
              sight ×<b>{'—'}</b>
            </span>
            {typeof e.irregularity === 'number' && e.irregularity > 0 && (
              <span className="chip" style={{ color: '#f85149' }}>
                irregularity <b>{e.irregularity}</b>
              </span>
            )}
            <span className="chip">
              meals <b>{e.meals ?? 0}</b> · sides <b>{e.sides}</b>
            </span>
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
