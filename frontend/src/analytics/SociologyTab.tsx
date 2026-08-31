import { useI18n } from '../i18n'
import MetricCard from './MetricCard'

interface Props {
  data: any
}

export default function SociologyTab({ data }: Props) {
  const { t } = useI18n()
  const hegemony = data?.hegemony ?? {}
  const gini = data?.gini ?? {}
  const trade = data?.trade ?? {}
  const casus = data?.casus ?? {}

  const hhi = hegemony.hhi ?? 0.0
  const clanCount = hegemony.clan_count ?? 0
  const territories: Record<string, any> = hegemony.territories ?? {}

  const larderGini = gini.larder_gini ?? 0.0
  const basketGini = gini.basket_gini ?? 0.0

  const marketCount = trade.market_count ?? 0
  const caravanRoutes = trade.caravan_routes ?? 0

  const warRisk = casus.war_risk ?? 0.0
  const tensions: any[] = casus.tensions ?? []

  const hhiStatus = hhi > 0.4 ? 'critical' : hhi > 0.25 ? 'warning' : 'healthy'
  const hhiLabel = hhi > 0.4 ? 'Monopolized' : hhi > 0.25 ? 'Oligopoly' : 'Pluralistic'

  const giniStatus = larderGini > 0.5 ? 'critical' : larderGini > 0.35 ? 'warning' : 'healthy'
  const giniLabel = larderGini > 0.5 ? 'Extreme Hoarding' : larderGini > 0.35 ? 'Unequal' : 'Egalitarian'

  const warStatus = warRisk > 0.7 ? 'critical' : warRisk > 0.3 ? 'warning' : 'healthy'
  const warLabel = warRisk > 0.7 ? 'Imminent Conflict' : warRisk > 0.3 ? 'Tense Feuds' : 'Peaceful'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Power Concentration & Wealth Inequality Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
        <MetricCard
          title="Hegemony Index (HHI)"
          value={hhi.toFixed(3)}
          subvalue={`${clanCount} active clans`}
          status={hhiStatus}
          statusLabel={hhiLabel}
          icon="👑"
          hint={t('analytics.hints.hhi')}
        />
        <MetricCard
          title="Larder Inequality (Gini)"
          value={larderGini.toFixed(3)}
          subvalue="clan granary disparity"
          status={giniStatus}
          statusLabel={giniLabel}
          icon="⚖️"
          hint={t('analytics.hints.larder_gini')}
        />
        <MetricCard
          title="Personal Basket Gini"
          value={basketGini.toFixed(3)}
          subvalue="foraging disparity"
          status="neutral"
          icon="🧺"
          hint={t('analytics.hints.basket_gini')}
        />
        <MetricCard
          title="Geopolitical War Risk"
          value={`${(warRisk * 100).toFixed(0)}%`}
          subvalue="feud escalation"
          status={warStatus}
          statusLabel={warLabel}
          icon="⚔️"
          hint="Aggregate likelihood of border raids or inter-clan war breaking out."
        />
      </div>

      {/* Trade & Commerce */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <MetricCard
          title="Border Trade Markets"
          value={marketCount}
          subvalue="neutral commerce posts"
          status="neutral"
          icon="🎪"
          hint="Neutral trading hubs established at mutual borders between allied or trade-partner clans."
        />
        <MetricCard
          title="Active Caravan Routes"
          value={caravanRoutes}
          subvalue="cross-map grain routes"
          status="neutral"
          icon="🐪"
          hint="Active merchant supply lines transporting grain, goods, and cultural news between settlements."
        />
      </div>

      {/* Clan Hegemony & Territory Breakdown */}
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
            <span style={{ fontSize: 13 }}>🏰</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Clan Demographics & Territorial Holdings
            </span>
          </div>
        </div>

        {Object.keys(territories).length === 0 ? (
          <div style={{ padding: '8px', color: '#8b949e', fontSize: 10, textAlign: 'center' }}>
            No structured clan settlements established.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(territories).map(([cid, tInfo]) => {
              const domPct = ((tInfo.dominance ?? 0) * 100).toFixed(1)
              return (
                <div key={cid} style={{ display: 'grid', gridTemplateColumns: '80px 1fr 120px', alignItems: 'center', gap: 8, fontSize: 10 }}>
                  <span style={{ fontWeight: 600, color: '#f0f6fc' }}>
                    Clan #{cid}
                  </span>
                  <div style={{ height: 6, background: '#0d1117', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${domPct}%`, background: '#58a6ff', borderRadius: 3 }} />
                  </div>
                  <span style={{ textAlign: 'right', color: '#8b949e', fontSize: 10 }}>
                    <b style={{ color: '#e6edf3' }}>{tInfo.population}</b> pop ({domPct}%) · 🏠 {tInfo.houses}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Diplomatic Tensions Radar */}
      {tensions.length > 0 && (
        <div
          style={{
            background: '#161b22',
            border: '1px solid #da363344',
            borderRadius: 8,
            padding: '10px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 13 }}>🔥</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#f85149', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              High-Tension Rivalries & Casus Belli
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {tensions.map((tItem, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: '#0d1117',
                  border: '1px solid #21262d',
                  borderRadius: 4,
                  padding: '4px 8px',
                  fontSize: 10,
                }}
              >
                <span style={{ color: '#e6edf3', fontWeight: 600 }}>
                  Clan #{tItem.a} ⚔️ Clan #{tItem.b}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: '#8b949e' }}>Score: {tItem.score}</span>
                  <span style={{ color: '#f85149', fontWeight: 700 }}>
                    Tension: {(tItem.tension * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
