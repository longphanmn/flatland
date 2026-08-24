import { useEffect, useState } from 'react'
import { totemEmoji } from '../totems'

interface ClanKnowledge {
  enemy_clans?: number[]
  danger_zones?: { x: number; y: number; conf: number }[]
  food_spots?: { x: number; y: number; conf: number }[]
  members_with_home_knowledge?: number
}

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
  culture?: string | null
  culture_id?: number | null
  knowledge?: ClanKnowledge | null
  coalition_id?: number | null
  larder?: number
  tribute_to?: number | null
}

export default function ClanPanel({ onSelectClan, onSelectCreature }: { onSelectClan?: (id: number) => void; onSelectCreature?: (id: number) => void }) {
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
    // 5s poll reduces proxy load; visibility check pauses when tab hidden
    const t = setInterval(() => {
      if (document.hidden) return
      load()
    }, 5000)
    const onVis = () => {
      if (!document.hidden) load()
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      alive = false
      clearInterval(t)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  if (clans.length === 0) return <p className="chip">no clans yet</p>
  const alive = clans.filter((c) => c.population > 0)

  return (
    <div className="clan-panel">
      <h4 style={{ margin: '8px 0 6px', fontSize: '0.9em' }}>Clans — {tick} ticks</h4>
      <div style={{ display: 'grid', gap: 6 }}>
        {alive.map((c) => (
          <div key={c.id} className="clan-card" onClick={() => onSelectClan?.(c.id)} style={{ borderLeft: `4px solid ${c.color}`, padding: '6px 8px', background: 'rgba(110,118,129,0.08)', borderRadius: 4, cursor: onSelectClan ? 'pointer' : 'default' }} title={onSelectClan ? 'Click for clan details' : undefined}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <b style={{ color: c.color }}>{c.name}</b>
              <span className="chip" style={{ background: c.color, color: '#0b0f14' }}>{totemEmoji(c.totem)} {c.totem ?? '—'}</span>
            </div>
            <div className="chip" style={{ marginTop: 4 }}>
              #{c.id} · pop <b>{c.population}</b> · {c.house ? (c.house.is_ruin ? 'ruins' : `house ${Math.round(c.house.x)},${Math.round(c.house.y)}`) : 'homeless'} · war {c.war_wins}W/{c.war_losses}L
            </div>
            <div className="chip">
              leader{' '}
              <button className="chronicle-name" onClick={(e) => { e.stopPropagation(); c.leader_id != null && onSelectCreature?.(c.leader_id) }} title="show leader profile">#{c.leader_id ?? '—'}</button>
              {' · '}founder{' '}
              <button className="chronicle-name" onClick={(e) => { e.stopPropagation(); onSelectCreature?.(c.founder_id) }} title="show founder profile">#{c.founder_id}</button>
              {' · '}born tick {c.born_tick}
            </div>
            {c.knowledge && (c.knowledge.enemy_clans?.length || c.knowledge.danger_zones?.length || c.knowledge.food_spots?.length) ? (
              <div className="chip" title="Clan memory — the union of what members remember: enemy clans that struck them, danger zones (predator sightings), known food spots">
                🧠 remembers:{' '}
                {c.knowledge.enemy_clans?.length ? `enemies ${c.knowledge.enemy_clans.map((id) => '#' + id).join(' ')} · ` : ''}
                {c.knowledge.danger_zones?.length ? `⚠ ${c.knowledge.danger_zones.length} · ` : ''}
                {c.knowledge.food_spots?.length ? `🍃 ${c.knowledge.food_spots.length}` : ''}
              </div>
            ) : null}
            {c.specialization && (
              <div className="chip" title="Clan specialization drifts over generations — warrior (war), farmer (harvest), scavenger (corpse) — totem biases start, environment + history drift it">
                <span style={{ color: '#f85149' }}>⚔ warrior {c.specialization.warrior.toFixed(2)}</span> · <span style={{ color: '#3fb950' }}>🌾 farmer {c.specialization.farmer.toFixed(2)}</span> · <span style={{ color: '#8b949e' }}>🦴 scavenger {c.specialization.scavenger.toFixed(2)}</span>
              </div>
            )}
            {c.culture && (
              <div className="chip" title="Culture — spreads to allies, can diverge into rival traditions; grants small collective bonus">
                🎭 {c.culture}
              </div>
            )}
            {(c.coalition_id != null || (c.tribute_to != null)) && (
              <div className="chip" title="§AB politics — coalition bloc membership; tribute_to marks a protector this clan pays">
                {c.coalition_id != null && <span title="member of a defensive coalition">🤝 pact #{c.coalition_id}{' · '}</span>}
                {c.tribute_to != null && <span title="pays tribute to a stronger protector">🛡️ vassal of #{c.tribute_to}{' · '}</span>}
              </div>
            )}
            {typeof c.larder === 'number' && c.larder > 0 && (
              <div className="chip" title="Clan larder — surplus stored at the settlement, famine draws it down; allies aid each other">
                🏺 larder {Math.round(c.larder)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
