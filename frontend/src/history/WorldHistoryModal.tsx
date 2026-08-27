import { useEffect, useMemo, useState } from 'react'
import type { StateMessage, WorldSummary } from '../types'
import { totemEmoji } from '../totems'

interface Props {
  open: boolean
  onClose: () => void
  state: StateMessage | null
  worlds?: WorldSummary[]
  selectedRunId?: number | null
  onSelectCreature?: (id: number) => void
  onSelectClan?: (id: number) => void
}

export type MajorCategory = 'all' | 'war' | 'plague' | 'politics' | 'faith' | 'disaster'

const CATEGORY_TABS: Array<{ key: MajorCategory; label: string; icon: string }> = [
  { key: 'all', label: 'All Turning Points', icon: '🌟' },
  { key: 'war', label: 'Wars & Conquest', icon: '⚔️' },
  { key: 'plague', label: 'Plagues & Outbreaks', icon: '☣️' },
  { key: 'politics', label: 'Dynasties & Schisms', icon: '👑' },
  { key: 'faith', label: 'Wonders & Epiphanies', icon: '🏛️' },
  { key: 'disaster', label: 'Cataclysms', icon: '🌋' },
]

export interface AggregatedMilestone {
  id: string
  startTick: number
  endTick: number
  day: string
  type: string
  category: MajorCategory
  title: string
  detail: string
  icon: string
  badgeColor: string
  casualtyCount: number
  primaryClanId?: number
}

export default function WorldHistoryModal({ open, onClose, state, selectedRunId }: Props) {
  const [rawEvents, setRawEvents] = useState<any[]>([])
  const [clans, setClans] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'timeline' | 'llm'>('timeline')
  const [category, setCategory] = useState<MajorCategory>('all')
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState(false)
  const [storyStyle, setStoryStyle] = useState<'saga' | 'chronicle' | 'mythos' | 'tragedy'>('saga')

  // Close on Escape key
  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  // Fetch major events and clans
  useEffect(() => {
    if (!open) return
    setLoading(true)
    Promise.all([
      fetch('/api/history?major=true&limit=1500').then((r) => r.json()),
      fetch('/api/clans').then((r) => r.json()),
    ])
      .then(([histData, clanData]) => {
        setRawEvents(histData.events ?? [])
        const clanMap: Record<string, any> = {}
        for (const c of clanData.clans ?? []) {
          clanMap[String(c.id)] = c
        }
        setClans(clanMap)
      })
      .catch((err) => console.error('Failed to load world history:', err))
      .finally(() => setLoading(false))
  }, [open, selectedRunId])

  const clanName = (id?: number | null) => {
    if (id == null) return '#?'
    return clans[String(id)]?.name ?? state?.clans?.[String(id)]?.name ?? `Clan #${id}`
  }

  // Deduplicate and aggregate raw events into high-value milestones
  const milestones = useMemo<AggregatedMilestone[]>(() => {
    if (!rawEvents.length) return []

    // Sort chronologically (oldest first for grouping)
    const sorted = [...rawEvents].sort((a, b) => a.tick - b.tick)
    const result: AggregatedMilestone[] = []

    let i = 0
    while (i < sorted.length) {
      const ev = sorted[i]
      const p = ev.payload ?? {}
      const tick = ev.tick
      const day = (tick / 1200).toFixed(1)

      // 1. Group consecutive war skirmishes between the same clan pair
      if (ev.type === 'war') {
        const a = p.a
        const b = p.b
        const pairKey = [Math.min(a, b), Math.max(a, b)].join(':')
        let totalDamage = p.damage ?? 0
        let lethalCount = p.lethal ? 1 : 0
        let count = 1
        let lastTick = tick
        let j = i + 1

        while (j < sorted.length) {
          const nextEv = sorted[j]
          const np = nextEv.payload ?? {}
          if (nextEv.type === 'war' && nextEv.tick - lastTick <= 240) {
            const nextPairKey = [Math.min(np.a, np.b), Math.max(np.a, np.b)].join(':')
            if (nextPairKey === pairKey) {
              totalDamage += np.damage ?? 0
              if (np.lethal) lethalCount++
              count++
              lastTick = nextEv.tick
              j++
              continue
            }
          }
          break
        }

        const clanAName = clanName(a)
        const clanBName = clanName(b)
        result.push({
          id: `war:${tick}:${pairKey}`,
          startTick: tick,
          endTick: lastTick,
          day,
          type: 'war',
          category: 'war',
          title: `War Campaign · ${clanAName} vs ${clanBName}`,
          detail: count > 1
            ? `${count} engagements fought (${lethalCount} fallen, ${totalDamage.toFixed(1)} total damage dealt)`
            : `Border clash (${p.lethal ? '1 casualty' : 'non-lethal'}, ${p.damage?.toFixed(1) ?? 'N/A'} damage)`,
          icon: '⚔️',
          badgeColor: '#f85149',
          casualtyCount: lethalCount,
          primaryClanId: a,
        })

        i = j
        continue
      }

      // 2. House Takeovers & Territory Conquests
      if (ev.type === 'takeover' || ev.type === 'conquest') {
        const invader = p.invader_clan ?? p.clan_id
        const victim = p.victim_clan ?? p.rival
        const houseId = p.house_id ?? ev.entity_id
        const invaderName = clanName(invader)
        const victimName = clanName(victim)

        result.push({
          id: `takeover:${ev.id ?? tick}:${houseId}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'conquest',
          category: 'war',
          title: `Territory Conquered · ${invaderName}`,
          detail: `Seized settlement Hall #${houseId} from ${victimName}${p.plundered_food ? ` (plundered ${p.plundered_food} food)` : ''}`,
          icon: '🚩',
          badgeColor: '#d29922',
          casualtyCount: 0,
          primaryClanId: invader,
        })
        i++
        continue
      }

      // 3. Regicide
      if (ev.type === 'regicide') {
        const victimClan = clanName(p.victim_clan ?? p.clan_id)
        result.push({
          id: `regicide:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'regicide',
          category: 'war',
          title: `Chieftain Slain (Regicide)`,
          detail: `The ruler of ${victimClan} was struck down in battle`,
          icon: '👑',
          badgeColor: '#f85149',
          casualtyCount: 1,
          primaryClanId: p.victim_clan ?? p.clan_id,
        })
        i++
        continue
      }

      // 4. Outbreak (Pestilence)
      if (ev.type === 'outbreak') {
        const diseaseId = p.disease_id ?? 1
        result.push({
          id: `outbreak:${ev.id ?? tick}:${diseaseId}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'outbreak',
          category: 'plague',
          title: `Plague Outbreak #${diseaseId}`,
          detail: `A virulent contagion erupted in the settlement (Patient Zero: #${ev.entity_id}, ${ev.caste ?? 'citizen'})`,
          icon: '☣️',
          badgeColor: '#3fb950',
          casualtyCount: 0,
        })
        i++
        continue
      }

      // 5. Dynastic Succession
      if (ev.type === 'succession') {
        const cName = clanName(p.clan_id)
        result.push({
          id: `succession:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'succession',
          category: 'politics',
          title: `Ruler Succession · ${cName}`,
          detail: `New chieftain #${p.new_leader} ascended following the death of #${p.prev_leader}`,
          icon: '👑',
          badgeColor: '#e3b341',
          casualtyCount: 0,
          primaryClanId: p.clan_id,
        })
        i++
        continue
      }

      // 6. Schism & Rebellion
      if (ev.type === 'schism') {
        const fromName = clanName(p.from_clan)
        result.push({
          id: `schism:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'schism',
          category: 'politics',
          title: `Civil Rebellion & Schism`,
          detail: `Dissidents fractured away from ${fromName} to found an independent rebel clan`,
          icon: '⚡',
          badgeColor: '#ff7b72',
          casualtyCount: 0,
          primaryClanId: p.from_clan,
        })
        i++
        continue
      }

      // 7. Betrayal & Broken Alliances
      if (ev.type === 'betrayal') {
        const cName = clanName(p.clan_id)
        const targetName = clanName(p.target_clan)
        result.push({
          id: `betrayal:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'betrayal',
          category: 'politics',
          title: `Treachery & Broken Treaty`,
          detail: `${cName} betrayed their sacred alliance with ${targetName}`,
          icon: '🗡️',
          badgeColor: '#f85149',
          casualtyCount: 0,
          primaryClanId: p.clan_id,
        })
        i++
        continue
      }

      // 8. Holy Alliance & Coalition
      if (ev.type === 'alliance' || ev.type === 'coalition_formed') {
        const cAName = clanName(p.a ?? p.founder)
        const cBName = p.b ? clanName(p.b) : ''
        result.push({
          id: `alliance:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'alliance',
          category: 'politics',
          title: ev.type === 'coalition_formed' ? `Defensive Coalition Formed` : `Sacred Peace Treaty`,
          detail: ev.type === 'coalition_formed'
            ? `${cAName} established the defensive league "${p.name ?? 'Grand Alliance'}"`
            : `${cAName} and ${cBName} signed a binding non-aggression pact`,
          icon: '🕊️',
          badgeColor: '#58a6ff',
          casualtyCount: 0,
        })
        i++
        continue
      }

      // 9. Temples & Spiritual Wonders
      if (ev.type === 'temple') {
        const cName = clanName(p.clan_id)
        result.push({
          id: `temple:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'temple',
          category: 'faith',
          title: `Temple of the Sphere Consecrated`,
          detail: `${cName} consecrated a great glowing Temple of the Sphere with community faith`,
          icon: '🏛️',
          badgeColor: '#bc8cff',
          casualtyCount: 0,
          primaryClanId: p.clan_id,
        })
        i++
        continue
      }

      // 10. Avatar Miracle
      if (ev.type === 'miracle') {
        const cName = clanName(p.clan_id)
        result.push({
          id: `miracle:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'miracle',
          category: 'faith',
          title: `Seasonal Avatar Miracle`,
          detail: `The Sacred Avatar answered prayers of ${cName}, bestowing divine harvest and vitality`,
          icon: '🌸',
          badgeColor: '#bc8cff',
          casualtyCount: 0,
          primaryClanId: p.clan_id,
        })
        i++
        continue
      }

      // 11. 3D Epiphany Revelation
      if (ev.type === 'epiphany') {
        result.push({
          id: `epiphany:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'epiphany',
          category: 'faith',
          title: `Divine 3D Epiphany`,
          detail: `An elder priest was touched by the 3D Sphere, beholding the sacred third dimension beyond Flatland`,
          icon: '✨',
          badgeColor: '#f0883e',
          casualtyCount: 0,
        })
        i++
        continue
      }

      // 12. Great Synod
      if (ev.type === 'synod') {
        result.push({
          id: `synod:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'synod',
          category: 'faith',
          title: `The Great Synod of the Sphere`,
          detail: `Chieftains and priests of all clans gathered in council, proclaiming a general truce`,
          icon: '🕊️',
          badgeColor: '#58a6ff',
          casualtyCount: 0,
        })
        i++
        continue
      }

      // 13. Cataclysms & Natural Disasters
      if (ev.type === 'disaster') {
        result.push({
          id: `disaster:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'disaster',
          category: 'disaster',
          title: `Natural Cataclysm (${p.kind ?? 'Disaster'})`,
          detail: `Catastrophe swept across coordinates (${ev.x}, ${ev.y}), reshaping the landscape`,
          icon: '🌋',
          badgeColor: '#f85149',
          casualtyCount: 0,
        })
        i++
        continue
      }

      // 14. Extinction
      if (ev.type === 'extinction') {
        result.push({
          id: `extinction:${ev.id ?? tick}`,
          startTick: tick,
          endTick: tick,
          day,
          type: 'extinction',
          category: 'disaster',
          title: `World Extinction Epoch`,
          detail: `The final geometric citizen perished; civilization fell silent`,
          icon: '💀',
          badgeColor: '#f85149',
          casualtyCount: 0,
        })
        i++
        continue
      }

      i++
    }

    // Return newest first for timeline viewing
    return result.reverse()
  }, [rawEvents, clans])

  // Filter milestones by category and search
  const filteredMilestones = useMemo(() => {
    return milestones.filter((m) => {
      if (category !== 'all' && m.category !== category) return false
      if (search.trim()) {
        const q = search.toLowerCase().trim()
        const text = `${m.title} ${m.detail} ${m.type}`.toLowerCase()
        if (!text.includes(q)) return false
      }
      return true
    })
  }, [milestones, category, search])

  // Aggregate stats
  const stats = useMemo(() => {
    let wars = 0
    let lethalWars = 0
    let outbreaks = 0
    let schisms = 0
    let disasters = 0
    let temples = 0
    let miracles = 0
    let successions = 0

    for (const m of milestones) {
      if (m.type === 'war') {
        wars++
        if (m.casualtyCount > 0) lethalWars++
      } else if (m.type === 'outbreak') outbreaks++
      else if (m.type === 'schism') schisms++
      else if (m.type === 'disaster') disasters++
      else if (m.type === 'temple') temples++
      else if (m.type === 'miracle') miracles++
      else if (m.type === 'succession') successions++
    }

    return { wars, lethalWars, outbreaks, schisms, disasters, temples, miracles, successions }
  }, [milestones])

  const totalDays = state ? (state.tick / 1200).toFixed(1) : '0'

  // Build the LLM Story Prompt (Chronological digest of turning points)
  const llmPrompt = useMemo(() => {
    const seed = state?.seed ?? 42
    const aliveCount = state?.creatures_alive ?? 0
    const deadCount = state?.creatures_dead ?? 0
    const deadByCause = state?.dead_by_cause ?? {}

    const clanSummary = Object.values(clans).map((c) => {
      const avatar = c.totem ? `${totemEmoji(c.totem)} ${c.totem}` : 'Unknown'
      return `- **${c.name}** (#${c.id}): Avatar ${avatar} | Pop: ${c.population} | Record: ${c.war_wins}W - ${c.war_losses}L | Faith: ${c.faith ?? 0}`
    }).join('\n')

    // Chronological ordering (oldest first for storytelling)
    const chronological = [...milestones].reverse()

    const turningPoints = chronological.map((m) => {
      return `- **Day ${m.day} (Tick ${m.startTick})**: ${m.title} — ${m.detail}`
    }).join('\n')

    let stylePrompt = ''
    if (storyStyle === 'saga') {
      stylePrompt = 'Write a dramatic, multi-chapter historical epic saga exploring the lives of chieftains, warriors, priests, and civilians. Emphasize character journeys, tactical battles, political betrayals, and survival during harsh winter/ice ages.'
    } else if (storyStyle === 'chronicle') {
      stylePrompt = 'Write an ancient, scholarly chronicle in the style of Edward Gibbon or Thucydides, methodically recording the rise of clans, societal institutions, legal philosophies, demographic curves, and military campaigns.'
    } else if (storyStyle === 'mythos') {
      stylePrompt = 'Write a spiritual and philosophical mythos focusing on the 2D inhabitants discovering the divine 3D Sphere, worshipping sacred avatars, consecrating temples, and deciphering cosmic epiphanies.'
    } else {
      stylePrompt = 'Write a poignant, haunting tragedy recording the golden heights of the geometric civilization, its slow descent into plague, ice, and famine, and the solemn extinction of the final living creature.'
    }

    return `# The Chronicles of Flatland: World Seed ${seed}

## Context & World Lore
You are an epic historian and bard recording the true history of a simulated 2D world inspired by Edwin A. Abbott's *Flatland*.
- **Society**: Women are razor-sharp line segments; Men are regular polygons whose status ascends by side count (Isosceles Triangles -> Soldiers -> Equilateral Artisans -> Squares -> Pentagons -> Hexagonal Nobles -> Multi-sided Priests/Circles).
- **Faith & Avatars**: Clans revere Sacred 2D Avatars of the 3D Sphere (Radiant Circle, Celestial Strike, All-Seeing Vertex, Indomitable Monolith, Sacred Spiral, Cosmic Scales, Dimensional Rift, Eternal Hearth).
- **Environment**: The world cycles through 4 Great Ages (Golden Era of bounty, Ice Age of deep freeze, Chaos Era of mutation and war, Plague Age of disease) and dynamic seasons.

## World Statistics
- **Total Duration**: ${totalDays} Days (${state?.tick ?? 0} Ticks)
- **World Seed**: ${seed}
- **Current Population**: ${aliveCount} Alive | ${deadCount} Fallen
- **Mortality Breakdown**: ${Object.entries(deadByCause).map(([k, v]) => `${k}: ${v}`).join(', ') || 'None recorded'}
- **Major Milestone Tallies**: ${stats.wars} War Campaigns (${stats.lethalWars} lethal), ${stats.outbreaks} Pandemics, ${stats.schisms} Rebellions, ${stats.temples} Temples Raised, ${stats.disasters} Cataclysms.

## Clan Roster & Avatars
${clanSummary || 'No formal clans recorded.'}

## Chronological Major Historical Turning Points (${chronological.length} Curated Milestones)
${turningPoints || 'No major historical turning points recorded yet.'}

---

## Story Writing Instructions for LLM:
${stylePrompt}

**Guidelines**:
1. Ground the narrative strictly in the real recorded events and clan names above.
2. Portray the unique geometric nature of Flatland characters (angles, vertex sharpness, fog perception, line speed).
3. Weave the historical milestones (wars, plagues, temples, schisms) into pivotal plot turns.
4. Structure the response into structured chronological chapters or epochs.`
  }, [state, clans, milestones, stats, totalDays, storyStyle])

  const copyToClipboard = () => {
    navigator.clipboard.writeText(llmPrompt)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const downloadMarkdown = () => {
    const blob = new Blob([llmPrompt], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flatland_epic_history_seed_${state?.seed ?? 42}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({ state, stats, clans, milestones }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flatland_history_milestones_seed_${state?.seed ?? 42}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!open) return null

  return (
    <div className="clan-details-backdrop" onClick={onClose} style={{ zIndex: 100 }}>
      <div
        className="clan-details-panel"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(860px, 96vw)',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          background: '#0d1117',
          border: '1px solid #30363d',
          boxShadow: '0 20px 48px rgba(0,0,0,0.8)',
          borderRadius: 12,
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <header
          style={{
            padding: '14px 18px',
            borderBottom: '1px solid #21262d',
            background: '#161b22',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 24 }}>📜</span>
            <div>
              <h2 style={{ fontSize: 16, margin: 0, color: '#e6edf3', fontWeight: 700 }}>
                World History & Epic Chronicle
              </h2>
              <div style={{ fontSize: 11, color: '#8b949e', marginTop: 2 }}>
                Seed {state?.seed ?? 42} · Day {totalDays} ({state?.tick ?? 0} ticks) · {milestones.length} major turning points · {state?.creatures_alive ?? 0} alive
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={() => setActiveTab('timeline')}
              className="chip"
              style={{
                background: activeTab === 'timeline' ? '#238636' : '#21262d',
                color: activeTab === 'timeline' ? '#fff' : '#c9d1d9',
                borderColor: activeTab === 'timeline' ? '#2ea043' : '#30363d',
                padding: '6px 12px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              📜 Milestones ({filteredMilestones.length})
            </button>
            <button
              onClick={() => setActiveTab('llm')}
              className="chip"
              style={{
                background: activeTab === 'llm' ? '#1f6feb' : '#21262d',
                color: activeTab === 'llm' ? '#fff' : '#c9d1d9',
                borderColor: activeTab === 'llm' ? '#388bfd' : '#30363d',
                padding: '6px 12px',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              🤖 AI Story Exporter
            </button>
            <button
              className="god-close"
              onClick={onClose}
              style={{ fontSize: 20, cursor: 'pointer', color: '#8b949e', marginLeft: 8 }}
            >
              ×
            </button>
          </div>
        </header>

        {/* Major Stats Ticker */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
            gap: 6,
            padding: '8px 16px',
            background: 'rgba(110,118,129,0.06)',
            borderBottom: '1px solid #21262d',
            fontSize: 11,
          }}
        >
          <div className="chip" title="Major war campaigns fought">
            ⚔️ <b>{stats.wars}</b> wars ({stats.lethalWars} lethal)
          </div>
          <div className="chip" title="Plague epidemic outbreaks">
            ☣️ <b>{stats.outbreaks}</b> plagues
          </div>
          <div className="chip" title="Internal rebellions & schisms">
            ⚡ <b>{stats.schisms}</b> schisms
          </div>
          <div className="chip" title="Ruler successions">
            👑 <b>{stats.successions}</b> successions
          </div>
          <div className="chip" title="Temples of the Sphere raised">
            🏛️ <b>{stats.temples}</b> temples
          </div>
          <div className="chip" title="Avatar seasonal miracles">
            🌸 <b>{stats.miracles}</b> miracles
          </div>
          <div className="chip" title="Natural cataclysms">
            🌋 <b>{stats.disasters}</b> cataclysms
          </div>
        </div>

        {/* Main Body */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
          {activeTab === 'timeline' ? (
            <div>
              {/* Category Pills & Search */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 8,
                  marginBottom: 14,
                }}
              >
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {CATEGORY_TABS.map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setCategory(tab.key)}
                      style={{
                        padding: '4px 10px',
                        fontSize: 11,
                        borderRadius: 20,
                        border: '1px solid',
                        background: category === tab.key ? '#388bfd' : '#21262d',
                        borderColor: category === tab.key ? '#58a6ff' : '#30363d',
                        color: category === tab.key ? '#fff' : '#8b949e',
                        cursor: 'pointer',
                        fontWeight: category === tab.key ? 700 : 500,
                      }}
                    >
                      {tab.icon} {tab.label}
                    </button>
                  ))}
                </div>

                <input
                  type="text"
                  placeholder="Filter milestones..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{
                    background: '#161b22',
                    border: '1px solid #30363d',
                    color: '#c9d1d9',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    width: 180,
                  }}
                />
              </div>

              {/* Event Feed */}
              {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  Analyzing historical milestones...
                </div>
              ) : filteredMilestones.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  No major turning points recorded for this category yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {filteredMilestones.map((m) => (
                    <div
                      key={m.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: '#161b22',
                        border: '1px solid #21262d',
                        borderLeft: `4px solid ${m.badgeColor}`,
                        borderRadius: 8,
                        padding: '10px 14px',
                        fontSize: 12,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontSize: 20 }}>{m.icon}</span>
                        <div>
                          <div style={{ color: '#e6edf3', fontWeight: 600, fontSize: 13 }}>{m.title}</div>
                          <div style={{ color: '#8b949e', fontSize: 12, marginTop: 2 }}>{m.detail}</div>
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 12 }}>
                        <span
                          className="chip"
                          style={{
                            background: '#21262d',
                            padding: '3px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            fontWeight: 600,
                          }}
                        >
                          Day {m.day} · #{m.startTick}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* LLM Exporter Tab */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div
                style={{
                  background: '#161b22',
                  border: '1px solid #30363d',
                  borderRadius: 8,
                  padding: 14,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                  <div>
                    <h3 style={{ fontSize: 14, margin: 0, color: '#e6edf3', fontWeight: 700 }}>
                      🤖 AI Story Generation Prompt
                    </h3>
                    <p style={{ fontSize: 11, color: '#8b949e', margin: '4px 0 0' }}>
                      Clean, curated turning points ready to paste into ChatGPT, Claude, or Gemini to write an epic story.
                    </p>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <select
                      value={storyStyle}
                      onChange={(e) => setStoryStyle(e.target.value as any)}
                      style={{
                        background: '#21262d',
                        border: '1px solid #30363d',
                        color: '#c9d1d9',
                        padding: '6px 10px',
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                    >
                      <option value="saga">⚔️ Epic Novel Saga</option>
                      <option value="chronicle">📜 Ancient Historical Chronicle</option>
                      <option value="mythos">🔮 Spiritual & Mythological Lore</option>
                      <option value="tragedy">💀 Tragic Extinction & Decline</option>
                    </select>

                    <button
                      onClick={copyToClipboard}
                      style={{
                        background: copied ? '#238636' : '#1f6feb',
                        border: '1px solid',
                        borderColor: copied ? '#2ea043' : '#388bfd',
                        color: '#fff',
                        padding: '6px 14px',
                        borderRadius: 6,
                        fontSize: 12,
                        cursor: 'pointer',
                        fontWeight: 600,
                      }}
                    >
                      {copied ? '✓ Copied Prompt!' : '📋 Copy Prompt'}
                    </button>
                    <button
                      onClick={downloadMarkdown}
                      style={{
                        background: '#21262d',
                        border: '1px solid #30363d',
                        color: '#c9d1d9',
                        padding: '6px 12px',
                        borderRadius: 6,
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      ⬇️ .md
                    </button>
                    <button
                      onClick={downloadJSON}
                      style={{
                        background: '#21262d',
                        border: '1px solid #30363d',
                        color: '#c9d1d9',
                        padding: '6px 12px',
                        borderRadius: 6,
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      ⬇️ JSON
                    </button>
                  </div>
                </div>
              </div>

              {/* Prompt Preview Box */}
              <div
                style={{
                  background: '#090d13',
                  border: '1px solid #21262d',
                  borderRadius: 6,
                  padding: 14,
                  maxHeight: 440,
                  overflow: 'auto',
                  fontFamily: 'ui-monospace, monospace',
                  fontSize: 11,
                  lineHeight: 1.5,
                  color: '#c9d1d9',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {llmPrompt}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer
          style={{
            padding: '10px 18px',
            borderTop: '1px solid #21262d',
            background: '#161b22',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: 11,
            color: '#8b949e',
          }}
        >
          <span>Curated milestone history synthesized from SQLite (<code>/api/history?major=true</code>)</span>
          <button
            onClick={onClose}
            style={{
              padding: '6px 16px',
              background: '#21262d',
              border: '1px solid #30363d',
              borderRadius: 6,
              color: '#c9d1d9',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </footer>
      </div>
    </div>
  )
}
