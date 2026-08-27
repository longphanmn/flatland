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
  { key: 'all', label: 'All Days', icon: '📅' },
  { key: 'war', label: 'War Days', icon: '⚔️' },
  { key: 'plague', label: 'Plague Days', icon: '☣️' },
  { key: 'politics', label: 'Dynasty Days', icon: '👑' },
  { key: 'faith', label: 'Faith Days', icon: '🏛️' },
  { key: 'disaster', label: 'Cataclysm Days', icon: '🌋' },
]

export interface DayRecord {
  day: number
  startTick: number
  endTick: number
  summaryLine: string
  primaryIcon: string
  badgeColor: string
  categories: Set<MajorCategory>
  wars: number
  lethalCasualties: number
  outbreaks: number
  schisms: number
  successions: number
  temples: number
  miracles: number
  disasters: number
  conquests: number
  eventSnippets: string[]
}

export default function WorldHistoryModal({ open, onClose, state, selectedRunId }: Props) {
  const [rawEvents, setRawEvents] = useState<any[]>([])
  const [clans, setClans] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'timeline' | 'llm'>('timeline')
  const [category, setCategory] = useState<MajorCategory>('all')
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState(false)
  const [expandedDay, setExpandedDay] = useState<number | null>(null)
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

  // Aggregate raw events into DayRecords (1 Day = 1200 ticks)
  const dayRecords = useMemo<DayRecord[]>(() => {
    const currentTick = state?.tick ?? 0
    const maxDay = Math.max(0, Math.floor(currentTick / 1200))
    const daysMap: Map<number, DayRecord> = new Map()

    // Initialize all days up to current day
    for (let d = 0; d <= maxDay; d++) {
      daysMap.set(d, {
        day: d,
        startTick: d * 1200,
        endTick: (d + 1) * 1200 - 1,
        summaryLine: '',
        primaryIcon: '🌱',
        badgeColor: '#3fb950',
        categories: new Set<MajorCategory>(['all']),
        wars: 0,
        lethalCasualties: 0,
        outbreaks: 0,
        schisms: 0,
        successions: 0,
        temples: 0,
        miracles: 0,
        disasters: 0,
        conquests: 0,
        eventSnippets: [],
      })
    }

    // Group events by day
    for (const ev of rawEvents) {
      const dayNum = Math.floor(ev.tick / 1200)
      let dRec = daysMap.get(dayNum)
      if (!dRec) {
        dRec = {
          day: dayNum,
          startTick: dayNum * 1200,
          endTick: (dayNum + 1) * 1200 - 1,
          summaryLine: '',
          primaryIcon: '🌱',
          badgeColor: '#3fb950',
          categories: new Set<MajorCategory>(['all']),
          wars: 0,
          lethalCasualties: 0,
          outbreaks: 0,
          schisms: 0,
          successions: 0,
          temples: 0,
          miracles: 0,
          disasters: 0,
          conquests: 0,
          eventSnippets: [],
        }
        daysMap.set(dayNum, dRec)
      }

      const p = ev.payload ?? {}

      if (ev.type === 'war') {
        dRec.wars++
        if (p.lethal) dRec.lethalCasualties++
        dRec.categories.add('war')
      } else if (ev.type === 'takeover' || ev.type === 'conquest') {
        dRec.conquests++
        dRec.categories.add('war')
        const invader = clanName(p.invader_clan ?? p.clan_id)
        const victim = clanName(p.victim_clan ?? p.rival)
        dRec.eventSnippets.push(`🚩 ${invader} conquered shelter from ${victim}`)
      } else if (ev.type === 'regicide') {
        dRec.lethalCasualties++
        dRec.categories.add('war')
        const cName = clanName(p.victim_clan ?? p.clan_id)
        dRec.eventSnippets.push(`👑 Regicide: Ruler of ${cName} slain in battle`)
      } else if (ev.type === 'outbreak') {
        dRec.outbreaks++
        dRec.categories.add('plague')
        dRec.eventSnippets.push(`☣️ Plague outbreak #${p.disease_id ?? 1} erupted`)
      } else if (ev.type === 'schism') {
        dRec.schisms++
        dRec.categories.add('politics')
        const fromName = clanName(p.from_clan)
        dRec.eventSnippets.push(`⚡ Rebellion: Splinter faction fractured from ${fromName}`)
      } else if (ev.type === 'succession') {
        dRec.successions++
        dRec.categories.add('politics')
        const cName = clanName(p.clan_id)
        dRec.eventSnippets.push(`👑 New ruler ascended in ${cName}`)
      } else if (ev.type === 'alliance' || ev.type === 'coalition_formed') {
        dRec.categories.add('politics')
        const cAName = clanName(p.a ?? p.founder)
        const cBName = p.b ? clanName(p.b) : ''
        dRec.eventSnippets.push(ev.type === 'coalition_formed' ? `🛡️ Defensive coalition formed by ${cAName}` : `🕊️ Treaty signed between ${cAName} & ${cBName}`)
      } else if (ev.type === 'betrayal') {
        dRec.categories.add('politics')
        const cName = clanName(p.clan_id)
        const tName = clanName(p.target_clan)
        dRec.eventSnippets.push(`🗡️ ${cName} betrayed alliance with ${tName}`)
      } else if (ev.type === 'temple') {
        dRec.temples++
        dRec.categories.add('faith')
        const cName = clanName(p.clan_id)
        dRec.eventSnippets.push(`🏛️ ${cName} raised a Glowing Temple of the Sphere`)
      } else if (ev.type === 'miracle') {
        dRec.miracles++
        dRec.categories.add('faith')
        const cName = clanName(p.clan_id)
        dRec.eventSnippets.push(`🌸 Avatar miracle answered prayers of ${cName}`)
      } else if (ev.type === 'epiphany') {
        dRec.categories.add('faith')
        dRec.eventSnippets.push(`✨ 3D Epiphany revelation revealed higher dimension`)
      } else if (ev.type === 'synod') {
        dRec.categories.add('faith')
        dRec.eventSnippets.push(`🕊️ Great Synod proclaimed general peace truce`)
      } else if (ev.type === 'disaster') {
        dRec.disasters++
        dRec.categories.add('disaster')
        dRec.eventSnippets.push(`🌋 Cataclysm (${p.kind ?? 'Disaster'}) struck landscape`)
      } else if (ev.type === 'extinction') {
        dRec.categories.add('disaster')
        dRec.eventSnippets.push(`💀 World extinction: Civilization fell silent`)
      }
    }

    // Synthesize concise One-Line Daily Digest Sentence per Day
    const sortedDays = Array.from(daysMap.values()).sort((a, b) => a.day - b.day)

    for (const d of sortedDays) {
      const parts: string[] = []

      if (d.day === 0) {
        parts.push('🌱 Genesis: Initial civilization founded core settlements & river bridges')
        d.primaryIcon = '🌱'
        d.badgeColor = '#3fb950'
      }

      if (d.wars > 0 || d.conquests > 0) {
        d.primaryIcon = '⚔️'
        d.badgeColor = '#f85149'
        const warDesc = d.wars > 0
          ? `${d.wars} war battle${d.wars > 1 ? 's' : ''}${d.lethalCasualties > 0 ? ` (${d.lethalCasualties} fallen)` : ''}`
          : ''
        const conqDesc = d.conquests > 0 ? `${d.conquests} shelter${d.conquests > 1 ? 's' : ''} conquered` : ''
        parts.push(`⚔️ ${[warDesc, conqDesc].filter(Boolean).join(', ')}`)
      }

      if (d.outbreaks > 0) {
        d.primaryIcon = '☣️'
        d.badgeColor = '#3fb950'
        parts.push(`☣️ ${d.outbreaks} plague outbreak${d.outbreaks > 1 ? 's' : ''} erupted`)
      }

      if (d.temples > 0 || d.miracles > 0) {
        if (!d.wars) d.primaryIcon = '🏛️'
        if (!d.wars) d.badgeColor = '#bc8cff'
        const tDesc = d.temples > 0 ? `${d.temples} Temple raised` : ''
        const mDesc = d.miracles > 0 ? `${d.miracles} Avatar miracle` : ''
        parts.push(`🏛️ ${[tDesc, mDesc].filter(Boolean).join(', ')}`)
      }

      if (d.schisms > 0 || d.successions > 0) {
        if (!d.wars && !d.outbreaks) {
          d.primaryIcon = '👑'
          d.badgeColor = '#e3b341'
        }
        const sDesc = d.schisms > 0 ? `${d.schisms} rebellion/schism` : ''
        const sucDesc = d.successions > 0 ? `${d.successions} ruler succession` : ''
        parts.push(`👑 ${[sDesc, sucDesc].filter(Boolean).join(', ')}`)
      }

      if (d.disasters > 0) {
        d.primaryIcon = '🌋'
        d.badgeColor = '#f85149'
        parts.push(`🌋 ${d.disasters} natural cataclysm`)
      }

      if (parts.length === 0) {
        parts.push('🌾 Peaceful flourishing: Clans gathered food and expanded territory under calm skies')
        d.primaryIcon = '🌾'
        d.badgeColor = '#2ea043'
      }

      d.summaryLine = parts.join(' · ')
    }

    // Return newest day first for timeline UI
    return sortedDays.reverse()
  }, [rawEvents, clans, state?.tick])

  // Filter day records
  const filteredDays = useMemo(() => {
    return dayRecords.filter((d) => {
      if (category !== 'all' && !d.categories.has(category)) return false
      if (search.trim()) {
        const q = search.toLowerCase().trim()
        const text = `day ${d.day} ${d.summaryLine} ${d.eventSnippets.join(' ')}`.toLowerCase()
        if (!text.includes(q)) return false
      }
      return true
    })
  }, [dayRecords, category, search])

  // Total stats
  const totalStats = useMemo(() => {
    let wars = 0
    let lethalWars = 0
    let outbreaks = 0
    let schisms = 0
    let disasters = 0
    let temples = 0
    let miracles = 0
    let successions = 0

    for (const d of dayRecords) {
      wars += d.wars
      lethalWars += d.lethalCasualties
      outbreaks += d.outbreaks
      schisms += d.schisms
      disasters += d.disasters
      temples += d.temples
      miracles += d.miracles
      successions += d.successions
    }

    return { wars, lethalWars, outbreaks, schisms, disasters, temples, miracles, successions }
  }, [dayRecords])

  const totalDays = state ? (state.tick / 1200).toFixed(1) : '0'

  // Build the LLM Story Prompt (Chronological One-Line-Per-Day Digest)
  const llmPrompt = useMemo(() => {
    const seed = state?.seed ?? 42
    const aliveCount = state?.creatures_alive ?? 0
    const deadCount = state?.creatures_dead ?? 0
    const deadByCause = state?.dead_by_cause ?? {}

    const clanSummary = Object.values(clans).map((c) => {
      const avatar = c.totem ? `${totemEmoji(c.totem)} ${c.totem}` : 'Unknown'
      return `- **${c.name}** (#${c.id}): Avatar ${avatar} | Pop: ${c.population} | Record: ${c.war_wins}W - ${c.war_losses}L | Faith: ${c.faith ?? 0}`
    }).join('\n')

    // Chronological order (Day 0, Day 1, Day 2...)
    const chronologicalDays = [...dayRecords].reverse()

    const dayTimeline = chronologicalDays.map((d) => {
      return `- **Day ${d.day}**: ${d.summaryLine}`
    }).join('\n')

    let stylePrompt = ''
    if (storyStyle === 'saga') {
      stylePrompt = 'Write a dramatic, multi-chapter historical epic saga following chieftains, warriors, and priests across the daily chronicle. Emphasize character journeys, tactical battles, political betrayals, and survival during harsh winters.'
    } else if (storyStyle === 'chronicle') {
      stylePrompt = 'Write an ancient, scholarly historical chronicle recording the day-by-day rise and fall of geometric clans, legal philosophy, demographic curves, and military campaigns.'
    } else if (storyStyle === 'mythos') {
      stylePrompt = 'Write a spiritual and philosophical mythos focusing on the 2D inhabitants discovering the divine 3D Sphere, worshipping sacred avatars, raising temples, and experiencing epiphanies.'
    } else {
      stylePrompt = 'Write a poignant tragedy recording the golden heights of the geometric civilization, its slow descent into plague and ice, and the solemn extinction of the final living creature.'
    }

    return `# The Chronicles of Flatland: World Seed ${seed}

## Context & World Lore
You are an epic historian and bard recording the true history of a simulated 2D world inspired by Edwin A. Abbott's *Flatland*.
- **Society**: Women are razor-sharp line segments; Men are regular polygons whose status ascends by side count (Isosceles Triangles -> Soldiers -> Equilateral Artisans -> Squares -> Pentagons -> Hexagonal Nobles -> Multi-sided Priests/Circles).
- **Faith & Avatars**: Clans revere Sacred 2D Avatars of the 3D Sphere (Radiant Circle, Celestial Strike, All-Seeing Vertex, Indomitable Monolith, Sacred Spiral, Cosmic Scales, Dimensional Rift, Eternal Hearth).
- **Environment**: The world cycles through 4 Great Ages (Golden Era, Ice Age, Chaos Era, Plague Age) and dynamic seasons.

## World Statistics
- **Total Duration**: ${totalDays} Days (${state?.tick ?? 0} Ticks)
- **World Seed**: ${seed}
- **Current Population**: ${aliveCount} Alive | ${deadCount} Fallen
- **Mortality Breakdown**: ${Object.entries(deadByCause).map(([k, v]) => `${k}: ${v}`).join(', ') || 'None recorded'}
- **Major Milestone Tallies**: ${totalStats.wars} Battles (${totalStats.lethalWars} fallen), ${totalStats.outbreaks} Pandemics, ${totalStats.schisms} Rebellions, ${totalStats.temples} Temples Raised, ${totalStats.disasters} Cataclysms.

## Clan Roster & Avatars
${clanSummary || 'No formal clans recorded.'}

## Day-by-Day Historical Chronicle (${chronologicalDays.length} Days)
${dayTimeline || 'No daily records recorded yet.'}

---

## Story Writing Instructions for LLM:
${stylePrompt}

**Guidelines**:
1. Follow the chronological day-by-day turning points above.
2. Portray the unique geometric nature of Flatland characters (angles, vertex sharpness, fog perception, line speed).
3. Weave the historical milestones (wars, plagues, temples, schisms) into pivotal chapter turns.`
  }, [state, clans, dayRecords, totalStats, totalDays, storyStyle])

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
    a.download = `flatland_daily_history_seed_${state?.seed ?? 42}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({ state, totalStats, clans, dayRecords }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flatland_daily_history_seed_${state?.seed ?? 42}.json`
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
                World History & Daily Chronicle
              </h2>
              <div style={{ fontSize: 11, color: '#8b949e', marginTop: 2 }}>
                Seed {state?.seed ?? 42} · {dayRecords.length} Days recorded · {state?.creatures_alive ?? 0} alive
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
              📅 Daily Chronicle ({filteredDays.length} Days)
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
          <div className="chip" title="Major battles fought">
            ⚔️ <b>{totalStats.wars}</b> battles ({totalStats.lethalWars} fallen)
          </div>
          <div className="chip" title="Plague outbreaks">
            ☣️ <b>{totalStats.outbreaks}</b> plagues
          </div>
          <div className="chip" title="Internal rebellions">
            ⚡ <b>{totalStats.schisms}</b> schisms
          </div>
          <div className="chip" title="Ruler successions">
            👑 <b>{totalStats.successions}</b> successions
          </div>
          <div className="chip" title="Temples of the Sphere">
            🏛️ <b>{totalStats.temples}</b> temples
          </div>
          <div className="chip" title="Avatar seasonal miracles">
            🌸 <b>{totalStats.miracles}</b> miracles
          </div>
          <div className="chip" title="Natural cataclysms">
            🌋 <b>{totalStats.disasters}</b> cataclysms
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
                  placeholder="Filter days..."
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

              {/* Day Feed */}
              {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  Analyzing daily chronicle...
                </div>
              ) : filteredDays.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  No days found matching filter.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {filteredDays.map((d) => {
                    const isExpanded = expandedDay === d.day
                    return (
                      <div
                        key={d.day}
                        onClick={() => setExpandedDay(isExpanded ? null : d.day)}
                        style={{
                          background: isExpanded ? '#1c2128' : '#161b22',
                          border: '1px solid',
                          borderColor: isExpanded ? '#444c56' : '#21262d',
                          borderLeft: `4px solid ${d.badgeColor}`,
                          borderRadius: 8,
                          padding: '10px 14px',
                          fontSize: 12,
                          cursor: 'pointer',
                          transition: 'background 0.15s',
                        }}
                      >
                        {/* One-Line Day Row */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>
                            <span
                              className="chip"
                              style={{
                                background: '#21262d',
                                color: '#e3b341',
                                fontWeight: 700,
                                fontSize: 11,
                                padding: '2px 8px',
                                flexShrink: 0,
                              }}
                            >
                              Day {d.day}
                            </span>
                            <span style={{ fontSize: 16, flexShrink: 0 }}>{d.primaryIcon}</span>
                            <span
                              style={{
                                color: '#e6edf3',
                                fontSize: 12,
                                fontWeight: 500,
                                lineHeight: 1.4,
                              }}
                            >
                              {d.summaryLine}
                            </span>
                          </div>
                          <span style={{ fontSize: 11, color: '#8b949e', flexShrink: 0, marginLeft: 8 }}>
                            {isExpanded ? '▲' : '▼'}
                          </span>
                        </div>

                        {/* Expanded Day Details (if clicked) */}
                        {isExpanded && (
                          <div
                            style={{
                              marginTop: 10,
                              paddingTop: 8,
                              borderTop: '1px solid #30363d',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 4,
                              fontSize: 11,
                              color: '#8b949e',
                            }}
                          >
                            <div style={{ fontWeight: 600, color: '#c9d1d9' }}>
                              Ticks {d.startTick} – {d.endTick} Milestone Log:
                            </div>
                            {d.eventSnippets.length > 0 ? (
                              d.eventSnippets.map((snip, idx) => (
                                <div key={idx} style={{ paddingLeft: 8 }}>
                                  • {snip}
                                </div>
                              ))
                            ) : (
                              <div style={{ paddingLeft: 8, fontStyle: 'italic' }}>
                                Steady generational growth with no major disruptions.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
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
                      Clean, concise day-by-day chronicle formatted for ChatGPT, Claude, or Gemini to write an epic world story.
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
          <span>One-line-per-day historical chronicle synthesized from SQLite (<code>/api/history?major=true</code>)</span>
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
