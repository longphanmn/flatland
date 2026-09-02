import { useI18n } from '../i18n'
import MetricCard from './MetricCard'
import { CreatureAvatar, SIDES_COLORS } from '../components/CreatureAvatar'

interface Props {
  data: any
  onSelectCreature?: (id: number) => void
}

const getCasteName = (k: number, t: (key: string, vars?: any) => string): string => {
  const map: Record<number, string> = {
    2: 'analytics.mutation_lab.castes.line',
    3: 'analytics.mutation_lab.castes.triangle',
    4: 'analytics.mutation_lab.castes.square',
    5: 'analytics.mutation_lab.castes.pentagon',
    6: 'analytics.mutation_lab.castes.hexagon',
    7: 'analytics.mutation_lab.castes.heptagon',
    8: 'analytics.mutation_lab.castes.octagon',
    9: 'analytics.mutation_lab.castes.nonagon',
    10: 'analytics.mutation_lab.castes.decagon',
    24: 'analytics.mutation_lab.castes.sphere',
  }
  const key = map[k]
  if (key && t(key) !== key) return t(key)
  return t('analytics.mutation_lab.castes.aberration', { k }) !== 'analytics.mutation_lab.castes.aberration'
    ? t('analytics.mutation_lab.castes.aberration', { k })
    : `${k}-gon (Aberration)`
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
  const totalAbbott = Object.values(abbottLadder).reduce((a: number, b: any) => a + Number(b), 0) || 1

  // Compute lambda progress percentage (0..100%)
  const lambdaPercent = Math.round(lambdaVal * 100)
  const speciationPercent = 100 - lambdaPercent

  // Status for mutation frequency
  const mutStatus = mutationFreq > 0.3 ? 'warning' : mutationFreq > 0.1 ? 'healthy' : 'neutral'
  const mutStatusLabel = mutationFreq > 0.3
    ? t('analytics.mutation_lab.variance_high')
    : mutationFreq > 0.1
    ? t('analytics.mutation_lab.variance_active')
    : t('analytics.mutation_lab.variance_orthodox')

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
              λ = {lambdaVal.toFixed(2)} {t('analytics.mutation_lab.diverged', { pct: speciationPercent })}
            </span>
          </div>
          <span style={{ fontSize: 11, color: '#8b949e' }}>
            {t('analytics.mutation_lab.max_generation')}: <b style={{ color: '#58a6ff' }}>{t('analytics.mutation_lab.gen')} {maxGen}</b>
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
          subvalue={t('analytics.mutation_lab.pop_sub')}
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
          subvalue={t('analytics.mutation_lab.asym_sub')}
          status="neutral"
          icon="📐"
          hint={t('analytics.mutation_lab.irregularity_hint')}
          sparklineData={ring.avg_irregularity}
          sparklineColor="#f778ba"
          sparklineHeight={34}
        />
        <MetricCard
          title={t('analytics.mutation_lab.max_generation')}
          value={`${t('analytics.mutation_lab.gen')} ${maxGen}`}
          subvalue={t('analytics.mutation_lab.frontier_sub', { pct: gen.mobility ? (gen.mobility * 100).toFixed(0) : 0 })}
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
              const name = getCasteName(k, t)
              const color = SIDES_COLORS[k] || '#bc8cff'
              const pct = ((count / totalAbbott) * 100).toFixed(1)
              const isMutantSide = ![2, 3, 4, 5, 8, 24].includes(k)

              return (
                <div key={k} style={{ display: 'grid', gridTemplateColumns: '130px 1fr 65px', alignItems: 'center', gap: 8, fontSize: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color, fontWeight: 600 }}>{name}</span>
                    {isMutantSide && (
                      <span style={{ fontSize: 8, background: '#a371f733', color: '#d2a8ff', padding: '1px 3px', borderRadius: 3, border: '1px solid #a371f766' }}>
                        {t('analytics.mutation_lab.mutant_tag')}
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
                      {t('analytics.mutation_lab.irr_label', { val: mutant.irregularity })}
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: '#8b949e' }}>
                    {t('analytics.mutation_lab.gen')} {mutant.generation} · {mutant.sides} {t('analytics.mutation_lab.sides')} ({getCasteName(mutant.sides, t)})
                  </span>
                  {mutant.clan_name && (
                    <span style={{ fontSize: 9, color: mutant.clan_color }}>
                      {t('analytics.mutation_lab.clan_label', { name: mutant.clan_name })}
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

      {/* §BG-12 Morphospace 2D Scatterplot — Area vs Sharpness */}
      {(() => {
        const scatter: any[] = gen.morph_scatter ?? []
        if (scatter.length === 0) return null
        const W = 360, H = 200, pad = 28
        const areas = scatter.map((p:any)=>p.area)
        const thetas = scatter.map((p:any)=>p.theta_min*180/Math.PI)
        const minA = Math.min(...areas, 0.5), maxA = Math.max(...areas, 6)
        const minT = Math.min(...thetas, 5), maxT = Math.max(...thetas, 120)
        const sx = (a:number)=> pad + ((a-minA)/Math.max(0.01,maxA-minA))*(W-pad*2)
        const sy = (t:number)=> H-pad - ((t-minT)/Math.max(0.01,maxT-minT))*(H-pad*2-14)
        return (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13 }}>🗺️</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{t('mutationLab.morphospaceTitle')}</span>
            </div>
            <span style={{ fontSize: 10, color: '#8b949e' }}>{scatter.length} points · elders ★ highlight</span>
          </div>
          <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ background: '#0d1117', borderRadius: 6, border: '1px solid #21262d', maxWidth: '100%', height: 'auto' }}>
            {/* grid */}
            {[0,0.25,0.5,0.75,1].map(f=>(
              <g key={'g'+f}>
                <line x1={pad + f*(W-pad*2)} y1={14} x2={pad + f*(W-pad*2)} y2={H-pad} stroke="#21262d" strokeWidth={0.6} strokeDasharray="2 2" />
                <line x1={pad} y1={14+f*(H-pad*2-14)} x2={W-pad} y2={14+f*(H-pad*2-14)} stroke="#21262d" strokeWidth={0.6} strokeDasharray="2 2" />
              </g>
            ))}
            {/* axes */}
            <line x1={pad} y1={H-pad} x2={W-pad} y2={H-pad} stroke="#30363d" strokeWidth={0.8}/>
            <line x1={pad} y1={14} x2={pad} y2={H-pad} stroke="#30363d" strokeWidth={0.8}/>
            <text x={W/2} y={H-6} textAnchor="middle" fontSize={7} fill="#8b949e">{t('mutationLab.areaAxis')}</text>
            <text x={8} y={H/2} textAnchor="middle" fontSize={7} fill="#8b949e" transform={`rotate(-90 8 ${H/2})`}>{t('mutationLab.sharpnessAxis')}</text>
            {scatter.map((p:any)=>{
              const x=sx(p.area), y=sy(p.theta_min*180/Math.PI)
              const col = SIDES_COLORS[p.sides] || (p.irregularity>0.3?'#d2a8ff':'#79c0ff')
              const isElder = p.is_elder
              return (
                <g key={p.id} style={{ cursor: onSelectCreature? 'pointer':'default' }} onClick={()=>onSelectCreature?.(p.id)}>
                  <circle cx={x} cy={y} r={2.8 + p.irregularity*4} fill={col} fillOpacity={0.85} stroke={isElder?'#e3b341':'#0d1117'} strokeWidth={isElder?1.2:0.7} />
                  {isElder && <text x={x} y={y-6} textAnchor="middle" fontSize={5} fill="#e3b341">★</text>}
                </g>
              )
            })}
          </svg>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', fontSize: 9, color: '#8b949e' }}>
            <span>◉ area = Shoelace A, y = θₘᵢₙ (°) lower = sharper razor</span>
            <span style={{ marginLeft:'auto' }}>{t('mutationLab.clustersHint')}</span>
          </div>
        </div>
        )})()}

      {/* §BG-11 Morphological Phylogeny Tree */}
      {(() => {
        const nodes: any[] = gen.phylogeny_nodes ?? []
        if (nodes.length === 0) return null
        const sorted = [...nodes].sort((a,b)=>a.generation-b.generation)
        const maxG = Math.max(...sorted.map(n=>n.generation), 1)
        const Wp = 360, Hp = 160, padT = 12, padL = 24
        const xFor = (g:number)=> padL + (g/Math.max(1,maxG))*(Wp-padL-12)
        // group by generation buckets for y spreading
        const buckets: Record<number, any[]> = {}
        sorted.forEach(n=>{ const b=Math.floor(n.generation/ Math.max(1, Math.ceil(maxG/6))); (buckets[b]=buckets[b]||[]).push(n)})
        const yFor = (n:any)=>{
          const b=Math.floor(n.generation/ Math.max(1, Math.ceil(maxG/6)))
          const arr=buckets[b]||[]
          const idx=arr.indexOf(n)
          const h=(Hp-padT*2)/Math.max(1, arr.length)
          return padT+ idx*h + h/2
        }
        const idMap = new Map<number, any>(sorted.map(n=>[n.id,n]))
        return (
        <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13 }}>🌳</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#c9d1d9', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{t('mutationLab.phylogenyTitle')}</span>
            </div>
            <span style={{ fontSize: 10, color: '#8b949e' }}>gen 0→{maxG} · dashed = ancestral ghost</span>
          </div>
          <svg width="100%" viewBox={`0 0 ${Wp} ${Hp}`} style={{ background: '#0d1117', borderRadius: 6, border: '1px solid #21262d' }}>
            {/* generational axis */}
            {[0, maxG].map(g=>(
              <g key={g}>
                <line x1={xFor(g)} y1={padT} x2={xFor(g)} y2={Hp-padT} stroke="#21262d" strokeWidth={0.5} strokeDasharray="3 3"/>
                <text x={xFor(g)} y={Hp-2} textAnchor="middle" fontSize={6} fill="#6e7681">g{g}</text>
              </g>
            ))}
            {/* Abbott ghost templates as faint icons at g0 */}
            {[
              {s:3, y: Hp*0.18}, {s:4, y: Hp*0.38}, {s:5, y: Hp*0.58}, {s:8, y: Hp*0.78}, {s:24, y: Hp*0.92}
            ].map(t=>(
              <g key={'ab'+t.s} opacity={0.22}>
                <polygon
                  points={Array.from({length: Math.min(24,t.s)},(_,i)=>{ const a=(i/t.s)*Math.PI*2 -Math.PI/2; const cx=xFor(0)+7, cy=t.y; const rr=7; return `${cx+Math.cos(a)*rr},${cy+Math.sin(a)*rr}`}).join(' ')}
                  fill="none" stroke="#8b949e" strokeWidth={0.7} strokeDasharray="2 2"
                />
                <text x={xFor(0)-8} y={t.y+2} textAnchor="end" fontSize={5} fill="#6e7681">{t.s===24?'○ Priest':`${t.s}-gon`}</text>
              </g>
            ))}
            {/* parent edges */}
            {sorted.map(n=>{
              const parents=[n.mother_id, n.father_id].filter(id=>id && idMap.has(id))
              return parents.map((pid:any)=>{
                const p=idMap.get(pid)
                return <line key={`${n.id}-${pid}`} x1={xFor(p.generation)} y1={yFor(p)} x2={xFor(n.generation)} y2={yFor(n)} stroke="#388bfd" strokeWidth={0.7} opacity={0.35} />
              })
            })}
            {/* nodes */}
            {sorted.map(n=>{
              const col=SIDES_COLORS[n.sides]||'#d2a8ff'
              const isElder=n.stage==='elder'
              return (
                <g key={n.id} style={{ cursor: onSelectCreature? 'pointer':'default' }} onClick={()=>onSelectCreature?.(n.id)}>
                  <circle cx={xFor(n.generation)} cy={yFor(n)} r={4 + n.irregularity*5} fill={col} stroke={isElder?'#e3b341':'#0d1117'} strokeWidth={isElder?1.2:0.8} opacity={0.95} />
                  {isElder && <text x={xFor(n.generation)} y={yFor(n)-7} textAnchor="middle" fontSize={5} fill="#e3b341">👑</text>}
                  <text x={xFor(n.generation)+7} y={yFor(n)+2} fontSize={5} fill="#8b949e">#{n.id} {n.caste}·{n.sides}</text>
                </g>
              )
            })}
          </svg>
          <div style={{ fontSize: 9, color: '#8b949e' }}>{t('mutationLab.phylogenyHint')}</div>
        </div>
        )})()}

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
                      #{evt.creature_id} ({t('analytics.mutation_lab.gen')} {evt.generation})
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
