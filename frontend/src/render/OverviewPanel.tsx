import { useMemo } from 'react'
import type { StateMessage } from '../types'
import { CASTE_COLORS } from './CanvasRenderer'
import { totemEmoji } from '../totems'
import { useI18n } from '../i18n'

interface Props {
  state: StateMessage | null
  aliveHist?: number[]
  onSelectCreature: (id: number) => void
  onSelectClan: (id: number) => void
}

const AGE_ICONS: Record<string, string> = {
  'Golden Era': '🌟',
  'Golden Age': '🌟',
  'Ice Age': '❄️',
  'Plague Age': '☣️',
  'Chaos Era': '⚡',
  'Chaos Age': '⚡',
  'Age of Harmony': '🕊️',
  'Era of Harmony': '🕊️',
  'Age of Strife': '⚔️',
}

const SEASON_ICONS: Record<string, string> = {
  spring: '🌱',
  summer: '☀️',
  autumn: '🍂',
  winter: '❄️',
}

const WEATHER_ICONS: Record<string, string> = {
  clear: '☀️',
  rain: '🌧️',
  fog: '🌫️',
  storm: '⛈️',
}

export default function OverviewPanel({
  state,
  aliveHist = [],
  onSelectCreature,
  onSelectClan,
}: Props) {
  const { t } = useI18n()

  // Trend calculation
  const trend = useMemo(() => {
    if (aliveHist.length < 5) return 'stable'
    const recent = aliveHist.slice(-5)
    const delta = recent[recent.length - 1] - recent[0]
    if (delta > 1) return 'growing'
    if (delta < -1) return 'declining'
    return 'stable'
  }, [aliveHist])

  // Caste Breakdown
  const { casteData, menCount, womenCount } = useMemo(() => {
    if (!state) return { casteData: [], totalCreatures: 0, menCount: 0, womenCount: 0 }
    const pop = state.population ?? {}
    const entries = Object.entries(pop).filter(([k]) => k in CASTE_COLORS && pop[k] > 0)
    const total = entries.reduce((acc, [, v]) => acc + v, 0) || 1

    let women = pop['Woman'] ?? 0
    let men = total - women

    const items = entries
      .sort(([, a], [, b]) => b - a)
      .map(([caste, count]) => ({
        caste,
        count,
        pct: ((count / total) * 100).toFixed(1),
        color: CASTE_COLORS[caste] ?? '#8b949e',
      }))

    return { casteData: items, totalCreatures: total, menCount: men, womenCount: women }
  }, [state])

  // Health Vitals
  const { healthyCount, sickCount, hungryCount, starvingCount, chilledCount } = useMemo(() => {
    if (!state) return { healthyCount: 0, sickCount: 0, hungryCount: 0, starvingCount: 0, chilledCount: 0 }
    const entities = state.entities ?? []
    const sick = state.infected_count ?? entities.filter((e) => e.infected).length
    const hungry = entities.filter((e) => e.status === 'hungry').length
    const starving = entities.filter((e) => e.status === 'starving').length
    const chilled = entities.filter((e) => (e.chill ?? 0) >= 12).length
    const healthy = Math.max(0, (state.creatures_alive ?? 0) - sick - starving)
    return {
      healthyCount: healthy,
      sickCount: sick,
      hungryCount: hungry,
      starvingCount: starving,
      chilledCount: chilled,
    }
  }, [state])

  // Mortality Ranked Breakdown
  const mortalityList = useMemo(() => {
    if (!state?.dead_by_cause) return []
    const totalDead = Object.values(state.dead_by_cause).reduce((a, b) => a + b, 0) || 1
    return Object.entries(state.dead_by_cause)
      .filter(([, count]) => count > 0)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([cause, count]) => {
        let icon = '💀'
        if (cause.includes('starv') || cause.includes('hunger')) icon = '🌾'
        else if (cause.includes('war') || cause.includes('combat')) icon = '⚔️'
        else if (cause.includes('disease') || cause.includes('plague') || cause.includes('infect')) icon = '☣️'
        else if (cause.includes('age')) icon = '⏳'
        else if (cause.includes('cold') || cause.includes('freeze')) icon = '❄️'
        else if (cause.includes('heat') || cause.includes('burn')) icon = '🔥'
        else if (cause.includes('predat')) icon = '🐺'
        else if (cause.includes('cannibal')) icon = '🍖'

        return {
          cause,
          count,
          icon,
          pct: ((count / totalDead) * 100).toFixed(0),
        }
      })
  }, [state?.dead_by_cause])

  // Food Security & Economy
  const { totalGrain, securityStatus } = useMemo(() => {
    if (!state) return { totalGrain: 0, securityStatus: 'famineRisk' }
    const clans = Object.values(state.clans ?? {})
    const grain = clans.reduce((acc, c) => acc + (c.granary ?? 0) + (c.larder ?? 0), 0)
    const alive = Math.max(1, state.creatures_alive ?? 1)
    const ratio = grain / alive

    let status = 'adequate'
    if (ratio >= 2.0) status = 'abundant'
    else if (ratio < 0.6) status = 'famineRisk'

    return { totalGrain: grain, securityStatus: status }
  }, [state])

  // Geopolitics & Hegemon
  const { activeClansCount, hegemonClan, warPairsCount, alliedPairsCount, totalTemples, totalShrines } = useMemo(() => {
    if (!state) return { activeClansCount: 0, hegemonClan: null, warPairsCount: 0, alliedPairsCount: 0, totalTemples: 0, totalShrines: 0 }
    const clanEntries = Object.entries(state.clans ?? {})
    const activeCount = clanEntries.length

    let maxPop = -1
    let hegemon: any = null
    let temples = 0
    let shrines = 0

    for (const [id, c] of clanEntries) {
      const pop = c.population ?? 0
      if (pop > maxPop) {
        maxPop = pop
        hegemon = { id: Number(id), ...c }
      }
      if ((c.shrine_level ?? 0) >= 2) temples++
      else if ((c.shrine_level ?? 0) >= 1) shrines++
    }

    const relations = state.relations ?? []
    let wars = 0
    let allies = 0
    for (const r of relations) {
      if (r.score < -20) wars++
      else if (r.score > 20) allies++
    }

    return {
      activeClansCount: activeCount,
      hegemonClan: hegemon && maxPop > 0 ? {
        ...hegemon,
        pct: (((hegemon.population ?? 0) / Math.max(1, state.creatures_alive ?? 1)) * 100).toFixed(0),
      } : null,
      warPairsCount: wars,
      alliedPairsCount: allies,
      totalTemples: temples,
      totalShrines: shrines,
    }
  }, [state])

  // Prominent Citizens (Eldest & Top Chieftain)
  const { eldestCreature, topChief } = useMemo(() => {
    if (!state?.entities) return { eldestCreature: null, topChief: null }
    let oldest: any = null
    let maxAge = -1

    for (const e of state.entities) {
      if (e.kind !== 'creature') continue
      const a = e.age ?? 0
      if (a > maxAge) {
        maxAge = a
        oldest = e
      }
    }

    // Top Chief by wins
    let bestLeader: any = null
    let maxWins = -1
    for (const [clanId, c] of Object.entries(state.clans ?? {})) {
      if (c.leader_id && (c.war_wins ?? 0) > maxWins) {
        maxWins = c.war_wins ?? 0
        bestLeader = {
          id: c.leader_id,
          clanName: c.name,
          clanId: Number(clanId),
          wins: c.war_wins ?? 0,
        }
      }
    }

    return { eldestCreature: oldest, topChief: bestLeader }
  }, [state])

  if (!state) {
    return (
      <div style={{ padding: '12px 8px', textAlign: 'center', color: '#8b949e', fontSize: 12 }}>
        {t('app.overview.hint')}
      </div>
    )
  }

  const ageName = state.age || 'Golden Era'
  const ageIcon = AGE_ICONS[ageName] ?? '🌟'
  const seasonIcon = SEASON_ICONS[state.season] ?? '🌱'
  const weatherIcon = WEATHER_ICONS[state.weather] ?? '☀️'
  const ageDay = state.age_day ?? ((state.day % 10) + 1)
  const ageTotalDays = state.age_total_days ?? 10
  const agePct = Math.min(100, Math.max(0, (ageDay / ageTotalDays) * 100))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12, color: '#c9d1d9' }}>
      {/* 1. Era & Climate Progression Banner */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontWeight: 700, color: '#e6edf3', display: 'flex', alignItems: 'center', gap: 4 }}>
            <span>{ageIcon}</span> {ageName}
          </span>
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            {t('app.overview.eraProgress', { day: ageDay, total: ageTotalDays })}
          </span>
        </div>
        {/* Era Progress Bar */}
        <div style={{ background: '#21262d', height: 4, borderRadius: 2, overflow: 'hidden', marginBottom: 6 }}>
          <div style={{ width: `${agePct}%`, height: '100%', background: '#58a6ff', transition: 'width 0.3s' }} />
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', fontSize: 11 }}>
          <span className="chip" style={{ background: '#21262d', padding: '2px 6px' }}>
            {seasonIcon} {state.season.toUpperCase()} · Day {state.day}
          </span>
          <span className="chip" style={{ background: '#21262d', padding: '2px 6px' }}>
            {weatherIcon} {state.weather}
          </span>
        </div>
      </div>

      {/* 2. Demographics & Segmented Caste Bar */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontWeight: 700, color: '#e6edf3' }}>
            {t('app.overview.demographicsTitle')}
          </span>
          <span
            className="chip"
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              color: trend === 'growing' ? '#3fb950' : trend === 'declining' ? '#f85149' : '#8b949e',
              background: '#21262d',
              padding: '1px 6px',
            }}
          >
            {trend === 'growing' ? `▲ ${t('app.overview.growing')}` : trend === 'declining' ? `▼ ${t('app.overview.declining')}` : `● ${t('app.overview.stable')}`}
          </span>
        </div>

        {/* Visual Segmented Caste Bar */}
        <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', background: '#21262d', marginBottom: 6 }}>
          {casteData.map((c) => (
            <div
              key={c.caste}
              style={{
                width: `${c.pct}%`,
                background: c.color,
                transition: 'width 0.2s',
              }}
              title={`${c.caste}: ${c.count} (${c.pct}%)`}
            />
          ))}
        </div>

        {/* Caste Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
          {casteData.map((c) => (
            <span
              key={c.caste}
              className="chip"
              style={{
                fontSize: 10.5,
                background: '#21262d',
                padding: '2px 6px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
              title={`${c.caste}: ${c.count} alive (${c.pct}%)`}
            >
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: c.color }} />
              <span>{c.caste}</span>
              <b>{c.count}</b>
            </span>
          ))}
        </div>

        {/* Vitals & Status */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, fontSize: 10.5, color: '#8b949e', borderTop: '1px solid #21262d', paddingTop: 6 }}>
          <span style={{ color: '#79c0ff' }}>♂ {t('app.overview.men')}: <b>{menCount}</b></span>
          <span>·</span>
          <span style={{ color: '#ff9bce' }}>♀ {t('app.overview.women')}: <b>{womenCount}</b></span>
          <span>·</span>
          <span style={{ color: '#3fb950' }}>{t('app.overview.healthy')}: <b>{healthyCount}</b></span>
          {sickCount > 0 && (
            <>
              <span>·</span>
              <span style={{ color: '#f85149' }}>{t('app.overview.sick')}: <b>{sickCount}</b></span>
            </>
          )}
          {(hungryCount > 0 || starvingCount > 0) && (
            <>
              <span>·</span>
              <span style={{ color: '#d29922' }}>{t('app.overview.hungry')}: <b>{hungryCount + starvingCount}</b></span>
            </>
          )}
          {chilledCount > 0 && (
            <>
              <span>·</span>
              <span style={{ color: '#79c0ff' }}>{t('app.overview.chilled')}: <b>{chilledCount}</b></span>
            </>
          )}
        </div>
      </div>

      {/* 3. Mortality & Crisis Causes */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontWeight: 700, color: '#e6edf3' }}>
            {t('app.overview.mortalityTitle')}
          </span>
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            {state.creatures_dead} {t('history.stats.fallen')}
          </span>
        </div>

        {mortalityList.length === 0 ? (
          <div style={{ fontSize: 11, color: '#8b949e', fontStyle: 'italic' }}>
            {t('app.overview.noDeaths')}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {mortalityList.map((m) => (
              <div key={m.cause} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                <span style={{ minWidth: 16 }}>{m.icon}</span>
                <span style={{ flex: 1, textTransform: 'capitalize', color: '#c9d1d9' }}>{m.cause}</span>
                <div style={{ width: 60, height: 4, background: '#21262d', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${m.pct}%`, height: '100%', background: '#f85149' }} />
                </div>
                <span style={{ minWidth: 44, textAlign: 'right', color: '#8b949e' }}>
                  <b>{m.count}</b> ({m.pct}%)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Granaries & Food Security */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontWeight: 700, color: '#e6edf3' }}>
            {t('app.overview.economyTitle')}
          </span>
          <span style={{ fontSize: 11, color: '#e3b341', fontWeight: 600 }}>
            🌾 {totalGrain}
          </span>
        </div>
        <div style={{ fontSize: 11, marginBottom: 6 }}>
          {securityStatus === 'abundant' && <span style={{ color: '#3fb950' }}>{t('app.overview.abundant')}</span>}
          {securityStatus === 'adequate' && <span style={{ color: '#d29922' }}>{t('app.overview.adequate')}</span>}
          {securityStatus === 'famineRisk' && <span style={{ color: '#f85149' }}>{t('app.overview.famineRisk')}</span>}
        </div>
        <div style={{ display: 'flex', gap: 6, fontSize: 11, color: '#8b949e' }}>
          <span className="chip" style={{ background: '#21262d', padding: '2px 6px' }}>
            🏠 {t('app.overview.housesCount', { count: state.population?.House ?? 0 })}
          </span>
          <span className="chip" style={{ background: '#21262d', padding: '2px 6px' }}>
            🌱 {t('app.overview.wildFood', { count: state.population?.Food ?? 0 })}
          </span>
        </div>
      </div>

      {/* 5. Geopolitics & Sphere Devotion */}
      <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontWeight: 700, color: '#e6edf3' }}>
            {t('app.overview.geoTitle')}
          </span>
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            {t('app.overview.activeClans', { count: activeClansCount })}
          </span>
        </div>

        {hegemonClan && (
          <div style={{ fontSize: 11, marginBottom: 4 }}>
            <span style={{ color: '#8b949e' }}>{t('app.overview.hegemon', { name: hegemonClan.name, pct: hegemonClan.pct })}</span>{' '}
            {hegemonClan.totem && <span>{totemEmoji(hegemonClan.totem)}</span>}
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, fontSize: 11, color: '#8b949e' }}>
          <span className="chip" style={{ background: '#21262d', padding: '2px 6px' }}>
            ⚔️ {warPairsCount} wars · 🕊️ {alliedPairsCount} allies
          </span>
          {(totalTemples > 0 || totalShrines > 0) && (
            <span className="chip" style={{ background: '#21262d', padding: '2px 6px', color: '#bc8cff' }}>
              🏛️ {t('app.overview.templesAndShrines', { temples: totalTemples, shrines: totalShrines })}
            </span>
          )}
        </div>
      </div>

      {/* 6. Prominent Living Figures */}
      {(eldestCreature || topChief) && (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '8px 10px' }}>
          <div style={{ fontWeight: 700, color: '#e6edf3', marginBottom: 4 }}>
            {t('app.overview.notableTitle')}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
            {eldestCreature && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#8b949e' }}>
                  ⏳ {t('app.overview.eldest', { name: eldestCreature.personal_name || eldestCreature.caste || 'Citizen', id: eldestCreature.id, age: eldestCreature.age ?? 0, gen: eldestCreature.generation ?? 0 })}
                </span>
                <button
                  onClick={() => onSelectCreature(eldestCreature.id)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#58a6ff',
                    cursor: 'pointer',
                    fontSize: 11,
                    padding: 0,
                    textDecoration: 'underline',
                  }}
                >
                  inspect
                </button>
              </div>
            )}
            {topChief && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: '#8b949e' }}>
                  👑 {t('app.overview.topChief', { id: topChief.id, clan: topChief.clanName, wins: topChief.wins })}
                </span>
                <button
                  onClick={() => onSelectClan(topChief.clanId)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#58a6ff',
                    cursor: 'pointer',
                    fontSize: 11,
                    padding: 0,
                    textDecoration: 'underline',
                  }}
                >
                  clan
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
