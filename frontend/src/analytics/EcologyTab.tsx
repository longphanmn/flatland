import { useI18n } from '../i18n'
import MetricCard from './MetricCard'

interface Props {
  data: any
}

const PLANT_COLORS: Record<string, string> = {
  grass: '#90be6d',
  grain: '#f9c74f',
  berry: '#f94144',
  medicinal_herb: '#43aa8b',
  mushroom: '#9d4edd',
  poisonous: '#f72585',
}

export default function EcologyTab({ data }: Props) {
  const { t } = useI18n()
  const trophic = data?.trophic ?? {}
  const biodiv = data?.biodiversity ?? {}

  const plantBiomass = trophic.plant_biomass ?? 0
  const herbivores = trophic.herbivores ?? 0
  const predators = trophic.predators ?? 0

  const shannon = biodiv.shannon ?? 0.0
  const evenness = biodiv.evenness ?? 0.0
  const richness = biodiv.richness ?? 0
  const recycle = biodiv.corpse_recycle ?? 0.0
  const bySpecies: Record<string, number> = biodiv.by_species ?? {}

  const bioStatus = shannon > 1.2 ? 'healthy' : shannon > 0.8 ? 'warning' : 'critical'
  const bioLabel = shannon > 1.2 ? 'Rich & Diverse' : shannon > 0.8 ? 'Moderate' : 'Monoculture'

  const totalPlants = Object.values(bySpecies).reduce((a, b) => a + b, 0) || 1

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Trophic Pyramid & Lotka-Volterra Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
        <MetricCard
          title="Flora Biomass"
          value={plantBiomass}
          subvalue="active plants on map"
          status="healthy"
          icon="🌿"
          hint={t('analytics.hints.plant_biomass')}
        />
        <MetricCard
          title="Herbivores"
          value={herbivores}
          subvalue="peaceful foragers"
          status="neutral"
          icon="🦌"
          hint={t('analytics.hints.herbivore')}
        />
        <MetricCard
          title="Carnivores"
          value={predators}
          subvalue="predatory hunters"
          status={predators > herbivores * 0.4 ? 'warning' : 'neutral'}
          statusLabel={predators > herbivores * 0.4 ? 'High Pressure' : 'Balanced'}
          icon="🐺"
          hint={t('analytics.hints.predator')}
        />
      </div>

      {/* Biodiversity Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
        <MetricCard
          title="Shannon Entropy"
          value={shannon.toFixed(2)}
          subvalue="diversity index"
          status={bioStatus}
          statusLabel={bioLabel}
          icon="🌈"
          hint={t('analytics.hints.shannon')}
        />
        <MetricCard
          title="Evenness Score"
          value={`${(evenness * 100).toFixed(0)}%`}
          subvalue="species balance"
          status="neutral"
          icon="⚖️"
          hint={t('analytics.hints.evenness')}
        />
        <MetricCard
          title="Species Richness"
          value={`${richness} / 6`}
          subvalue="distinct varieties"
          status={richness >= 5 ? 'healthy' : 'warning'}
          icon="🌱"
          hint={t('analytics.hints.richness')}
        />
        <MetricCard
          title="Corpse Recycling"
          value={`${(recycle * 100).toFixed(1)}%`}
          subvalue="nutrient return"
          status="neutral"
          icon="🔄"
          hint={t('analytics.hints.corpse_recycle')}
        />
      </div>

      {/* Plant Species Breakdown */}
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
            <span style={{ fontSize: 13 }}>🌾</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Plant Species Distribution
            </span>
          </div>
          <span style={{ fontSize: 10, color: '#8b949e' }}>
            Total: {totalPlants} Flora Entities
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          {Object.entries(bySpecies).map(([species, count]) => {
            const color = PLANT_COLORS[species] || '#90be6d'
            const pct = ((count / totalPlants) * 100).toFixed(1)

            return (
              <div key={species} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 60px', alignItems: 'center', gap: 8, fontSize: 10 }}>
                <span style={{ color, fontWeight: 600, textTransform: 'capitalize' }}>
                  {species.replace('_', ' ')}
                </span>
                <div style={{ height: 6, background: '#0d1117', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3 }} />
                </div>
                <span style={{ textAlign: 'right', color: '#8b949e', fontSize: 10 }}>
                  <b style={{ color: '#e6edf3' }}>{count}</b> ({pct}%)
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
