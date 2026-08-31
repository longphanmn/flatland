import { useI18n } from '../i18n'
import MetricCard from './MetricCard'
import { CreatureAvatar, SIDES_COLORS } from '../components/CreatureAvatar'

interface Props {
  data: any
  onSelectCreature?: (id: number) => void
}

const CASTE_NAMES: Record<number, string> = {
  2: 'Woman (Line)',
  3: 'Soldier / Artisan',
  4: 'Gentleman',
  5: 'Professional',
  6: 'Hexagon',
  7: 'Heptagon (Mutant)',
  8: 'Noble',
  9: 'Nonagon (Mutant)',
  10: 'Decagon',
  24: 'Priest (Sphere)',
}


export default function MutationLab({ data, onSelectCreature }: Props) {
  const { t } = useI18n()
  const gen = data?.generational ?? {}
  const ring = data?.ring ?? {}

  const mutationFreq = gen.mutation_freq ?? 0
  const lambdaVal = gen.lambda_val ?? 1.0
  const maxGen = gen.max_generation ?? 0
  const abbottLadder: Record<string, number> = gen.abbott_ladder ?? {}
  const topMutants: any[] = gen.top_mutants ?? []
  const recentMutations: any[] = gen.recent_mutations ?? []

  // Total Abbott creatures
  const totalAbbott = Object.values(abbottLadder).reduce((a, b) => a + b, 0) || 1

  // Compute lambda progress percentage (0..100%)
  const lambdaPercent = Math.round(lambdaVal * 100)
  const speciationPercent = 100 - lambdaPercent

  // Status for mutation frequency
  const mutStatus = mutationFreq > 0.3 ? 'warning' : mutationFreq > 0.1 ? 'healthy' : 'neutral'
  const mutStatusLabel = mutationFreq > 0.3 ? 'High Variance' : mutationFreq > 0.1 ? 'Active Divergence' : 'Orthodox'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Annealing & Speciation Progress Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, #161b22 0%, #1b1a2e 100%)',
          border: '1px solid #388bfd44',
          borderRadius: 8,
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 14 }}>🌀</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#e6edf3' }}>
              {t('analytics.mutation_lab.annealing_stage')}
            </span>
            <span
              style={{
                fontSize: 10,
                color: '#bc8cff',
                fontWeight: 700,
                background: 'rgba(188, 140, 255, 0.15)',
                border: '1px solid #bc8cff44',
                padding: '1px 6px',
                borderRadius: 4,
              }}
            >
              λ = {lambdaVal.toFixed(2)} ({speciationPercent}% Diverged)
            </span>
          </div>
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            {t('analytics.mutation_lab.max_generation')}: <b style={{ color: '#58a6ff' }}>Gen {maxGen}</b>
          </span>
        </div>

        {/* Multi-segment Progress Bar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ height: 8, background: '#0d1117', borderRadius: 4, overflow: 'hidden', border: '1px solid #30363d', display: 'flex' }}>
            <div
              style={{
                width: `${lambdaPercent}%`,
                background: 'linear-gradient(90deg, #58a6ff, #79c0ff)',
                transition: 'width 0.3s ease',
              }}
            />
            <div
              style={{
                width: `${speciationPercent}%`,
                background: 'linear-gradient(90deg, #a371f7, #f778ba)',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#8b949e' }}>
            <span>🏛️ {t('analytics.mutation_lab.caste_orthodoxy')}</span>
            <span>🧬 {t('analytics.mutation_lab.hybrid')}</span>
            <span>🌀 {t('analytics.mutation_lab.freeform')}</span>
          </div>
        </div>

        <p style={{ margin: 0, fontSize: 10, color: '#8b949e', lineHeight: 1.3 }}>
          {t('analytics.mutation_lab.annealing_hint')}
        </p>
      </div>

      {/* Mutation Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
        <MetricCard
          title={t('analytics.mutation_lab.mutation_frequency')}
          value={`${(mutationFreq * 100).toFixed(1)}%`}
          subvalue="of total population"
          status={mutStatus}
          statusLabel={mutStatusLabel}
          icon="🧬"
          hint={t('analytics.mutation_lab.mutation_freq_hint')}
          sparklineData={ring.mutation_freq}
          sparklineColor="#bc8cff"
          sparklineHeight={34}
        />
        <MetricCard
          title={t('analytics.mutation_lab.mean_irregularity')}
          value={ring.avg_irregularity?.[ring.avg_irregularity.length - 1]?.toFixed(3) ?? '0.000'}
          subvalue="asymmetry index"
          status="neutral"
          icon="📐"
          hint={t('analytics.mutation_lab.irregularity_hint')}
          sparklineData={ring.avg_irregularity}
          sparklineColor="#f778ba"
          sparklineHeight={34}
        />
        <MetricCard
          title={t('analytics.mutation_lab.max_generation')}
          value={`Gen ${maxGen}`}
          subvalue={`${gen.mobility ? (gen.mobility * 100).toFixed(0) : 0}% at frontier`}
          status="neutral"
          icon="👑"
          hint={t('analytics.mutation_lab.max_gen_hint')}
          sparklineData={ring.max_generation}
          sparklineColor="#3fb950"
          sparklineHeight={34}
        />
      </div>

      {/* Abbott Caste Ladder Distribution */}
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
            <span style={{ fontSize: 13 }}>📊</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {t('analytics.mutation_lab.abbott_ladder')}
            </span>
          </div>
          <span style={{ fontSize: 10, color: '#8b949e' }}>
            {t('analytics.mutation_lab.abbott_hint')}
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
          {Object.entries(abbottLadder)
            .sort(([a], [b]) => Number(a) - Number(b))
            .map(([sidesStr, count]) => {
              const k = Number(sidesStr)
              const name = CASTE_NAMES[k] || `${k}-gon (Aberration)`
              const color = SIDES_COLORS[k] || '#bc8cff'
              const pct = ((count / totalAbbott) * 100).toFixed(1)
              const isMutantSide = ![2, 3, 4, 5, 8, 24].includes(k)

              return (
                <div key={k} style={{ display: 'grid', gridTemplateColumns: '130px 1fr 65px', alignItems: 'center', gap: 8, fontSize: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color, fontWeight: 600 }}>{name}</span>
                    {isMutantSide && (
                      <span style={{ fontSize: 8, background: '#a371f733', color: '#d2a8ff', padding: '1px 3px', borderRadius: 3, border: '1px solid #a371f766' }}>
                        MUTANT
                      </span>
                    )}
                  </div>
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

      {/* Living Mutant Spotlight Gallery */}
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
            <span style={{ fontSize: 13 }}>⭐</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {t('analytics.mutation_lab.top_mutants')}
            </span>
          </div>
          <span style={{ fontSize: 10, color: '#8b949e' }}>
            {t('analytics.mutation_lab.top_mutants_hint')}
          </span>
        </div>

        {topMutants.length === 0 ? (
          <div style={{ padding: '12px', textAlign: 'center', color: '#8b949e', fontSize: 11, background: '#0d1117', borderRadius: 6 }}>
            {t('analytics.mutation_lab.no_mutations_yet')}
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8 }}>
            {topMutants.map((mutant) => (
              <div
                key={mutant.id}
                style={{
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: 6,
                  padding: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                }}
              >
                <CreatureAvatar
                  e={mutant}
                  size={64}
                />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 700, fontSize: 11, color: '#f0f6fc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {mutant.name}
                    </span>
                    <span style={{ fontSize: 9, color: '#f778ba', fontWeight: 700 }}>
                      Irr: {mutant.irregularity}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#8b949e' }}>
                    Gen {mutant.generation} · {mutant.sides} {t('analytics.mutation_lab.sides')} ({mutant.caste})
                  </span>
                  {mutant.clan_name && (
                    <span style={{ fontSize: 9, color: mutant.clan_color }}>
                      Clan: {mutant.clan_name}
                    </span>
                  )}
                  {onSelectCreature && (
                    <button
                      type="button"
                      onClick={() => onSelectCreature(mutant.id)}
                      style={{
                        marginTop: 4,
                        background: '#21262d',
                        border: '1px solid #30363d',
                        borderRadius: 4,
                        color: '#58a6ff',
                        fontSize: 9,
                        fontWeight: 600,
                        padding: '2px 6px',
                        cursor: 'pointer',
                        alignSelf: 'flex-start',
                      }}
                    >
                      🔍 {t('analytics.mutation_lab.inspect')} #{mutant.id}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Live Mutation Chronicle Feed */}
      <div
        style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: '10px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13 }}>📜</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              {t('analytics.mutation_lab.recent_feed')}
            </span>
          </div>
          <span style={{ fontSize: 10, color: '#8b949e' }}>
            {t('analytics.mutation_lab.recent_feed_hint')}
          </span>
        </div>

        {recentMutations.length === 0 ? (
          <div style={{ padding: '8px', color: '#8b949e', fontSize: 10, textAlign: 'center' }}>
            {t('analytics.mutation_lab.no_mutations_yet')}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 150, overflowY: 'auto' }}>
            {recentMutations
              .slice()
              .reverse()
              .map((evt, idx) => (
                <div
                  key={`${evt.tick}-${evt.creature_id}-${idx}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 8,
                    background: '#0d1117',
                    border: '1px solid #21262d',
                    borderRadius: 4,
                    padding: '4px 8px',
                    fontSize: 10,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
                    <span style={{ color: '#8b949e', fontSize: 9 }}>[t={evt.tick}]</span>
                    <span style={{ fontWeight: 600, color: '#f0f6fc' }}>
                      #{evt.creature_id} (Gen {evt.generation})
                    </span>
                    <span style={{ color: evt.clan_color || '#8b949e' }}>
                      {evt.desc}
                    </span>
                  </div>
                  {onSelectCreature && (
                    <button
                      type="button"
                      onClick={() => onSelectCreature(evt.creature_id)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#58a6ff',
                        cursor: 'pointer',
                        fontSize: 10,
                        padding: 0,
                      }}
                    >
                      🔍
                    </button>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}
