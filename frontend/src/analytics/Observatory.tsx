import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'
import MutationLab from './MutationLab'
import MacroOverview from './MacroOverview'
import EcologyTab from './EcologyTab'
import SociologyTab from './SociologyTab'
import CrisisTab from './CrisisTab'

interface Props {
  state?: any
  onSelectCreature?: (id: number) => void
}

type TabType = 'mutation' | 'overview' | 'ecology' | 'society' | 'crisis'

export default function Observatory({ state, onSelectCreature }: Props) {
  const { t } = useI18n()
  const [data, setData] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<TabType>('mutation')

  // Prefer WS analytics if present, else fallback poll
  useEffect(() => {
    if (state?.analytics) {
      setData(state.analytics)
      return
    }
    let alive = true
    const load = () =>
      fetch('/api/analytics/summary')
        .then((r) => r.json())
        .then((d) => alive && setData(d))
        .catch(() => {})
    load()
    const iv = setInterval(() => {
      if (!document.hidden) load()
    }, 5000)
    return () => {
      alive = false
      clearInterval(iv)
    }
  }, [state])

  if (!data || data.error) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: '#8b949e', fontSize: 12 }}>
        <span style={{ fontSize: 24, display: 'block', marginBottom: 8 }}>🔭</span>
        {t('analytics.gathering')}
      </div>
    )
  }

  const extinction = data.extinction ?? {}
  const famine = data.famine ?? {}
  const unrest = data.unrest ?? {}
  const gen = data.generational ?? {}
  const mutationFreq = gen.mutation_freq ?? 0
  const hasCriticalCrisis = extinction.alarm || (famine.horizon_ticks ?? 9999) < 300 || unrest.schism_risk
  const hasWarningCrisis = (extinction.Ne ?? 20) < 18 || (famine.horizon_ticks ?? 9999) < 1000 || (unrest.unrest_score ?? 0) > 5

  const worldStatusLabel = hasCriticalCrisis ? '⚠️ CRISIS ALERT' : hasWarningCrisis ? '🟡 ELEVATED STRAIN' : '🟢 STABLE HOMEOSTASIS'
  const worldStatusColor = hasCriticalCrisis ? '#f85149' : hasWarningCrisis ? '#d29922' : '#3fb950'

  const tabs: { id: TabType; label: string; badge?: string; badgeColor?: string }[] = [
    {
      id: 'mutation',
      label: t('analytics.tabs.mutation'),
      badge: `${(mutationFreq * 100).toFixed(0)}%`,
      badgeColor: '#bc8cff',
    },
    {
      id: 'overview',
      label: t('analytics.tabs.overview'),
    },
    {
      id: 'ecology',
      label: t('analytics.tabs.ecology'),
    },
    {
      id: 'society',
      label: t('analytics.tabs.society'),
    },
    {
      id: 'crisis',
      label: t('analytics.tabs.crisis'),
      badge: hasCriticalCrisis ? '!' : undefined,
      badgeColor: '#f85149',
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 11 }}>
      {/* Top World Status Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 6,
          background: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: '6px 10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 700, color: '#f0f6fc', fontSize: 12 }}>
            🔭 World Tick: <b style={{ color: '#58a6ff' }}>{data.tick}</b>
          </span>
          <span
            style={{
              fontSize: 9,
              fontWeight: 700,
              color: worldStatusColor,
              background: 'rgba(0,0,0,0.4)',
              border: `1px solid ${worldStatusColor}44`,
              padding: '2px 6px',
              borderRadius: 4,
            }}
          >
            {worldStatusLabel}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#8b949e' }}>
          <span>Max Gen: <b style={{ color: '#bc8cff' }}>{gen.max_generation ?? 0}</b></span>
          <span>·</span>
          <span>Speciation: <b style={{ color: '#79c0ff' }}>λ={(gen.lambda_val ?? 1.0).toFixed(2)}</b></span>
        </div>
      </div>

      {/* Navigation Tab Bar */}
      <div
        style={{
          display: 'flex',
          gap: 4,
          background: '#0d1117',
          padding: '4px',
          borderRadius: 8,
          border: '1px solid #21262d',
          overflowX: 'auto',
        }}
      >
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: isActive ? '#21262d' : 'transparent',
                border: isActive ? '1px solid #388bfd' : '1px solid transparent',
                borderRadius: 6,
                color: isActive ? '#f0f6fc' : '#8b949e',
                fontWeight: isActive ? 700 : 500,
                fontSize: 11,
                padding: '5px 10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {tab.label}
              {tab.badge && (
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: '#0d1117',
                    background: tab.badgeColor || '#58a6ff',
                    padding: '1px 5px',
                    borderRadius: 8,
                  }}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Active Tab View */}
      <div style={{ minHeight: 320 }}>
        {activeTab === 'mutation' && (
          <MutationLab data={data} onSelectCreature={onSelectCreature} />
        )}
        {activeTab === 'overview' && <MacroOverview data={data} />}
        {activeTab === 'ecology' && <EcologyTab data={data} />}
        {activeTab === 'society' && <SociologyTab data={data} />}
        {activeTab === 'crisis' && <CrisisTab data={data} />}
      </div>
    </div>
  )
}
