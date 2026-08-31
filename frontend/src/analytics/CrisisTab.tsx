import { useI18n } from '../i18n'
import MetricCard from './MetricCard'

interface Props {
  data: any
}

export default function CrisisTab({ data }: Props) {
  const { t } = useI18n()
  const famine = data?.famine ?? {}
  const extinction = data?.extinction ?? {}
  const unrest = data?.unrest ?? {}

  const horizon = famine.horizon_ticks ?? 9999
  const totalLarder = famine.larder ?? 0
  const burnRate = famine.burn_rate ?? 0
  const regrowth = famine.regrowth ?? 0

  const ne = extinction.Ne ?? 0
  const fertileFemales = extinction.fertile_females ?? 0
  const males = extinction.males ?? 0
  const extAlarm = extinction.alarm ?? false

  const unrestScore = unrest.unrest_score ?? 0
  const schismRisk = unrest.schism_risk ?? false
  const crowding = unrest.crowding ?? 0
  const hungry = unrest.hungry ?? 0
  const tenseClans = unrest.tense_clans ?? 0

  const famineStatus = horizon < 300 ? 'critical' : horizon < 1000 ? 'warning' : 'healthy'
  const famineLabel = horizon < 300 ? 'Famine Imminent' : horizon < 1000 ? 'Lean Reserves' : 'Food Secure'

  const neStatus = extAlarm ? 'critical' : ne < 18 ? 'warning' : 'healthy'
  const neLabel = extAlarm ? 'Extinction Cliff' : ne < 18 ? 'Vulnerable' : 'Genetically Viable'

  const unrestStatus = schismRisk ? 'critical' : unrestScore > 5 ? 'warning' : 'healthy'
  const unrestLabel = schismRisk ? 'Schism Imminent' : unrestScore > 5 ? 'Tense' : 'Stable'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Crisis Critical Alerts Banner */}
      {(extAlarm || schismRisk || horizon < 300) && (
        <div
          style={{
            background: 'linear-gradient(135deg, #331919 0%, #201010 100%)',
            border: '1px solid #f85149',
            borderRadius: 8,
            padding: '10px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 16 }}>⚠️</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#f85149', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Ecological & Societal Threat Warning
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, fontSize: 11, color: '#e6edf3' }}>
            {extAlarm && <div>• <b>Extinction Danger</b>: Effective breeding population (Ne={ne}) is below safe viability threshold ({fertileFemales}♀ / {males}♂).</div>}
            {horizon < 300 && <div>• <b>Starvation Threat</b>: Famine horizon is {horizon} ticks — granaries are depleting faster than plant regrowth.</div>}
            {schismRisk && <div>• <b>Schism & Revolt</b>: Internal unrest score is {unrestScore} — clan splintering or desertion is imminent.</div>}
          </div>
        </div>
      )}

      {/* Early Warning Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
        <MetricCard
          title="Famine Horizon"
          value={horizon >= 9999 ? '∞' : `${horizon} t`}
          subvalue={`Larder: ${totalLarder.toFixed(0)} | Burn: -${burnRate.toFixed(1)}/t`}
          status={famineStatus}
          statusLabel={famineLabel}
          icon="⏳"
          hint={t('analytics.hints.famine_horizon')}
        />
        <MetricCard
          title="Effective Pop (Ne)"
          value={ne}
          subvalue={`Breeding: ${fertileFemales}♀ · ${males}♂`}
          status={neStatus}
          statusLabel={neLabel}
          icon="🧬"
          hint={t('analytics.hints.extinction_ne')}
        />
        <MetricCard
          title="Internal Clan Unrest"
          value={unrestScore.toFixed(1)}
          subvalue={`Crowding: ${crowding} | Hungry: ${hungry}`}
          status={unrestStatus}
          statusLabel={unrestLabel}
          icon="⚡"
          hint={t('analytics.hints.unrest')}
        />
      </div>

      {/* Deep Dive Threat Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        {/* Famine Dynamics */}
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
          <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase' }}>
            🌾 Food Metabolism & Granaries
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Total Clan Larder Reserves:</span>
              <b style={{ color: '#e6edf3' }}>{totalLarder.toFixed(1)} energy</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Population Metabolic Drain:</span>
              <b style={{ color: '#f85149' }}>-{burnRate.toFixed(2)} energy/t</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Wild & Cultivated Regrowth:</span>
              <b style={{ color: '#3fb950' }}>+{regrowth.toFixed(2)} energy/t</b>
            </div>
          </div>
        </div>

        {/* Unrest Drivers */}
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
          <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase' }}>
            🔥 Societal Unrest Factors
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Overcrowded House Beds:</span>
              <b style={{ color: crowding > 0 ? '#d29922' : '#8b949e' }}>+{crowding} occupants</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Starving Clan Members:</span>
              <b style={{ color: hungry > 0 ? '#f85149' : '#8b949e' }}>{hungry} creatures</b>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#8b949e' }}>Clans with Personality Clashes:</span>
              <b style={{ color: tenseClans > 0 ? '#f85149' : '#8b949e' }}>{tenseClans} clans</b>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
