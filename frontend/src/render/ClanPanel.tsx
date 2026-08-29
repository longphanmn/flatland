import { useEffect, useState } from 'react'
import { totemEmoji } from '../totems'
import { useI18n } from '../i18n'

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
  founded_day?: number
  dead_count?: number
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
  granary?: number
  harvest_total?: number
  feast?: boolean
  dialect?: number
  tribute_to?: number | null
  faith?: number
  shrine_level?: number
}

export default function ClanPanel({ onSelectClan, onSelectCreature }: { onSelectClan?: (id: number) => void; onSelectCreature?: (id: number) => void }) {
  const { t } = useI18n()
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

  if (clans.length === 0) return <p className="chip">{t('clanPanel.noClans')}</p>
  const alive = clans.filter((c) => c.population > 0)

  return (
    <div className="clan-panel">
      <h4 style={{ margin: '8px 0 6px', fontSize: '0.9em' }}>{t('clanPanel.title', { tick })}</h4>
      <div style={{ display: 'grid', gap: 6 }}>
        {alive.map((c) => (
          <div key={c.id} className="clan-card" onClick={() => onSelectClan?.(c.id)} style={{ borderLeft: `4px solid ${c.color}`, padding: '6px 8px', background: '#161b22', border: '1px solid #30363d', borderLeftWidth: 4, borderRadius: 6, cursor: onSelectClan ? 'pointer' : 'default' }} title={onSelectClan ? t('clanPanel.clickForDetails') : undefined}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <b style={{ color: c.color }}>{c.name}</b>
              <span className="chip" style={{ background: c.color, color: '#0b0f14' }}>{totemEmoji(c.totem)} {c.totem ?? '—'}</span>
            </div>
            <div className="chip" style={{ marginTop: 4 }}>
              #{c.id} · {t('clanPanel.pop')} <b>{c.population}</b> · {t('clanPanel.dead')} <b style={{ color: '#f85149' }}>{c.dead_count ?? 0}</b> · {c.house ? (c.house.is_ruin ? t('clanPanel.ruins') : t('clanPanel.house', { x: Math.round(c.house.x), y: Math.round(c.house.y) })) : t('clanPanel.homeless')} · {t('clanPanel.war')} {c.war_wins}W/{c.war_losses}L
            </div>
            <div className="chip">
              {t('clanPanel.leader')}{' '}
              <button className="chronicle-name" onClick={(e) => { e.stopPropagation(); c.leader_id != null && onSelectCreature?.(c.leader_id) }} title={t('clanPanel.showLeader')}>#{c.leader_id ?? '—'}</button>
              {' · '}{t('clanPanel.founder')}{' '}
              <button className="chronicle-name" onClick={(e) => { e.stopPropagation(); onSelectCreature?.(c.founder_id) }} title={t('clanPanel.showFounder')}>#{c.founder_id}</button>
              {' · '}{t('clanPanel.day', { day: c.founded_day ?? Math.floor((c.born_tick ?? 0) / 1200) })}
            </div>
            {c.knowledge && (c.knowledge.enemy_clans?.length || c.knowledge.danger_zones?.length || c.knowledge.food_spots?.length) ? (
              <div className="chip" title={t('clanPanel.culture')}>
                🧠 {t('clanPanel.remembers')}:{' '}
                {c.knowledge.enemy_clans?.length ? `${t('clanPanel.enemies', { list: c.knowledge.enemy_clans.map((id) => '#' + id).join(' ') })} · ` : ''}
                {c.knowledge.danger_zones?.length ? `${t('clanPanel.danger', { count: c.knowledge.danger_zones.length })} · ` : ''}
                {c.knowledge.food_spots?.length ? `${t('clanPanel.food', { count: c.knowledge.food_spots.length })}` : ''}
              </div>
            ) : null}
            {c.specialization && (
              <div className="chip">
                <span style={{ color: '#f85149' }}>⚔ {t('inspector.combat')} {c.specialization.warrior.toFixed(2)}</span> · <span style={{ color: '#3fb950' }}>🌾 {t('inspector.farming')} {c.specialization.farmer.toFixed(2)}</span> · <span style={{ color: '#8b949e' }}>🦴 {t('inspector.foraging')} {c.specialization.scavenger.toFixed(2)}</span>
              </div>
            )}
            {c.culture && (
              <div className="chip" title={t('clanPanel.culture')}>
                🎭 {c.culture}
              </div>
            )}
            {(c.coalition_id != null || (c.tribute_to != null)) && (
              <div className="chip">
                {c.coalition_id != null && <span>🤝 #{c.coalition_id}{' · '}</span>}
                {c.tribute_to != null && <span>🛡️ #{c.tribute_to}{' · '}</span>}
              </div>
            )}
            {typeof c.larder === 'number' && c.larder > 0 && (
              <div className="chip">
                🏺 {t('clanPanel.larder', { count: Math.round(c.larder) })}
              </div>
            )}
            {typeof c.granary === 'number' && (c.granary > 0 || c.feast) ? (
              <div className="chip">
                🌾 {t('clanPanel.granary', { count: Math.round(c.granary) })}{c.feast ? ` · 🍞 ${t('clanPanel.feasting')}` : ''}
              </div>
            ) : null}
            {(typeof c.faith === 'number' && c.faith > 0) || (c.shrine_level ?? 0) >= 1 ? (
              <div className="chip">
                {(c.shrine_level ?? 0) >= 2 ? `⛪ ${t('clanPanel.temple')}` : `🕯️ ${t('clanPanel.shrine')}`}{typeof c.faith === 'number' ? ` · ⛲ ${t('clanPanel.faith', { count: Math.round(c.faith) })}` : ''}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  )
}
