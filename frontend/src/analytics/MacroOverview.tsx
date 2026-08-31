import { useI18n } from '../i18n'
import MetricCard from './MetricCard'
import Sparkline from './Sparkline'

interface Props {
  data: any
}

const CAUSE_COLORS: Record<string, string> = {
  starvation: '#f85149',
  combat: '#ff7b72',
  predation: '#d29922',
  disease: '#a371f7',
  old_age: '#79c0ff',
  chill: '#58a6ff',
  other: '#8b949e',
}

export default function MacroOverview({ data }: Props) {
  const { t } = useI18n()
  const ring = data?.ring ?? {}
  const mortality = data?.mortality ?? {}
  const dist: Record<string, number> = mortality.distribution ?? {}

  const lastPop = ring.population?.[ring.population.length - 1] ?? 0
  const lastBio = ring.biomass?.[ring.biomass.length - 1] ?? 0
  const lastSat = ring.energy_saturation?.[ring.energy_saturation.length - 1] ?? 0
  const lastBirth = ring.birth_velocity?.[ring.birth_velocity.length - 1] ?? 0
  const lastDeath = ring.death_velocity?.[ring.death_velocity.length - 1] ?? 0

  const satStatus = lastSat > 0.7 ? 'healthy' : lastSat > 0.4 ? 'warning' : 'critical'
  const satLabel = lastSat > 0.7 ? 'Satiated' : lastSat > 0.4 ? 'Hungry' : 'Starving'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Primary Population & Biomass History Card */}
      <div
        style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13 }}>📈</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Population Dynamics (6000 Ticks)
            </span>
          </div>
          <span style={{ fontSize: 11, color: '#3fb950', fontWeight: 700 }}>
            {lastPop} Living Creatures
          </span>
        </div>

        <Sparkline data={ring.population} color="#3fb950" height={60} />
      </div>

      {/* Macro Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
        <MetricCard
          title="Total Biomass"
          value={lastBio >= 1000 ? `${(lastBio / 1000).toFixed(1)}k` : lastBio}
          subvalue="health + energy sum"
          status="neutral"
          icon="⚡"
          hint={t('analytics.hints.biomass')}
          sparklineData={ring.biomass}
          sparklineColor="#e3b341"
          sparklineHeight={34}
        />
        <MetricCard
          title="Energy Saturation"
          value={`${(lastSat * 100).toFixed(0)}%`}
          subvalue="average reserve"
          status={satStatus}
          statusLabel={satLabel}
          icon="🍞"
          hint={t('analytics.hints.energy_sat')}
          sparklineData={ring.energy_saturation}
          sparklineColor="#79c0ff"
          sparklineHeight={34}
        />
        <MetricCard
          title="Birth Velocity"
          value={lastBirth.toFixed(1)}
          subvalue="births / min"
          status="neutral"
          icon="🌱"
          hint={t('analytics.hints.birth_vel')}
          sparklineData={ring.birth_velocity}
          sparklineColor="#a371f7"
          sparklineHeight={34}
        />
        <MetricCard
          title="Death Velocity"
          value={lastDeath.toFixed(1)}
          subvalue="deaths / min"
          status="neutral"
          icon="💀"
          hint={t('analytics.hints.death_vel')}
          sparklineData={ring.death_velocity}
          sparklineColor="#f85149"
          sparklineHeight={34}
        />
      </div>

      {/* Mortality Cause Decomposition */}
      <div
        style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13 }}>☠️</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Mortality Decomposition (Last 500 Deaths)
            </span>
          </div>
          <span style={{ fontSize: 10, color: '#8b949e' }}>
            {t('analytics.hints.mortality_dist')}
          </span>
        </div>

        {/* Stacked bar visualization */}
        <div style={{ height: 12, background: '#0d1117', borderRadius: 6, overflow: 'hidden', display: 'flex' }}>
          {Object.entries(dist).map(([cause, fraction]) => {
            if (fraction <= 0.001) return null
            const color = CAUSE_COLORS[cause] || '#8b949e'
            return (
              <div
                key={cause}
                style={{
                  width: `${fraction * 100}%`,
                  background: color,
                  height: '100%',
                }}
                title={`${cause}: ${(fraction * 100).toFixed(1)}%`}
              />
            )
          })}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
          {Object.entries(dist).map(([cause, fraction]) => {
            const color = CAUSE_COLORS[cause] || '#8b949e'
            const pct = (fraction * 100).toFixed(0)
            return (
              <div key={cause} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                <span style={{ color: '#c9d1d9', textTransform: 'capitalize' }}>{cause}</span>
                <span style={{ color: '#8b949e', fontWeight: 600 }}>{pct}%</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
