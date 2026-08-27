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

export type MajorCategory = 'all' | 'war' | 'plague' | 'politics' | 'faith' | 'disaster' | 'foundation'

const CATEGORY_TABS: Array<{ key: MajorCategory; label: string; icon: string }> = [
  { key: 'all', label: 'All Major', icon: '🌟' },
  { key: 'war', label: 'Wars & Conquest', icon: '⚔️' },
  { key: 'plague', label: 'Plagues & Disease', icon: '☣️' },
  { key: 'politics', label: 'Dynasties & Schisms', icon: '👑' },
  { key: 'faith', label: 'Faith & Miracles', icon: '🏛️' },
  { key: 'disaster', label: 'Cataclysms', icon: '🌋' },
  { key: 'foundation', label: 'Foundations & Bridges', icon: '🏗️' },
]

export default function WorldHistoryModal({ open, onClose, state, selectedRunId }: Props) {
  const [events, setEvents] = useState<any[]>([])
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
        setEvents(histData.events ?? [])
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

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter((ev) => {
      // Category filter
      if (category === 'war') {
        if (!['war', 'conquest', 'takeover', 'regicide', 'peace', 'peace_envoy', 'betrayal', 'rivalry'].includes(ev.type)) return false
      } else if (category === 'plague') {
        if (!['outbreak', 'recovery'].includes(ev.type) && !(ev.type === 'death' && ev.cause === 'disease')) return false
      } else if (category === 'politics') {
        if (!['succession', 'schism', 'alliance', 'coalition_formed', 'coalition_joined', 'coalition_dissolved', 'defection', 'tribute', 'banquet'].includes(ev.type)) return false
      } else if (category === 'faith') {
        if (!['temple', 'miracle', 'synod', 'epiphany', 'sermon', 'resonance'].includes(ev.type)) return false
      } else if (category === 'disaster') {
        if (!['disaster', 'fire', 'earthquake', 'extinction'].includes(ev.type)) return false
      } else if (category === 'foundation') {
        if (!['settlement'].includes(ev.type)) return false
      }

      // Search filter
      if (search.trim()) {
        const q = search.toLowerCase().trim()
        const p = ev.payload ?? {}
        const textToSearch = `${ev.type} ${ev.caste ?? ''} ${ev.cause ?? ''} ${p.personal_name ?? ''} ${p.kind ?? ''} ${clanName(p.clan_id)} ${clanName(p.a)} ${clanName(p.b)} ${p.winner_name ?? ''}`.toLowerCase()
        if (!textToSearch.includes(q)) return false
      }
      return true
    })
  }, [events, category, search, clans])

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
    let bridges = 0

    for (const ev of events) {
      if (ev.type === 'war') {
        wars++
        if (ev.payload?.lethal) lethalWars++
      } else if (ev.type === 'outbreak') outbreaks++
      else if (ev.type === 'schism') schisms++
      else if (ev.type === 'disaster') disasters++
      else if (ev.type === 'temple') temples++
      else if (ev.type === 'miracle') miracles++
      else if (ev.type === 'succession') successions++
      else if (ev.type === 'settlement' && ev.payload?.kind === 'bridge') bridges++
    }

    return { wars, lethalWars, outbreaks, schisms, disasters, temples, miracles, successions, bridges }
  }, [events])

  const totalDays = state ? (state.tick / 1200).toFixed(1) : '0'

  // Build the LLM Story Prompt
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
    const chronologicalEvents = [...events].sort((a, b) => a.tick - b.tick)

    const eventTimeline = chronologicalEvents.slice(0, 400).map((ev) => {
      const day = (ev.tick / 1200).toFixed(1)
      const p = ev.payload ?? {}
      let desc = ''

      if (ev.type === 'war') {
        const clanA = clanName(p.a)
        const clanB = clanName(p.b)
        desc = `[WAR CLASH] Conflict erupted between ${clanA} and ${clanB}. (Winner: ${p.winner ? '#' + p.winner : 'Inconclusive'}, Damage: ${p.damage?.toFixed(1) ?? 'N/A'}${p.lethal ? ', LETHAL' : ''})`
      } else if (ev.type === 'conquest' || ev.type === 'takeover') {
        desc = `[CONQUEST] ${clanName(p.invader ?? p.clan_id)} seized shelter territory from ${clanName(p.rival ?? p.victim_clan)}.`
      } else if (ev.type === 'schism') {
        desc = `[REBELLION & SCHISM] Internal strife splintered ${clanName(p.from_clan)}, birthing a rebel faction.`
      } else if (ev.type === 'betrayal') {
        desc = `[TREACHERY] ${clanName(p.clan_id)} betrayed former ally ${clanName(p.target_clan)}!`
      } else if (ev.type === 'outbreak') {
        desc = `[PLAGUE OUTBREAK #${p.disease_id ?? 1}] A virulent contagion infected patient #${ev.entity_id} (${ev.caste ?? 'citizen'}), sweeping through local settlements.`
      } else if (ev.type === 'recovery') {
        desc = `[PLAGUE RECOVERY] Patient #${ev.entity_id} successfully overcame disease #${p.disease_id ?? 1}.`
      } else if (ev.type === 'succession') {
        desc = `[DYNASTIC SUCCESSION] Following the death of Chieftain #${p.prev_leader}, Ruler #${p.new_leader} took the helm of ${clanName(p.clan_id)}.`
      } else if (ev.type === 'regicide') {
        desc = `[REGICIDE] Chieftain of ${clanName(p.clan_id)} was slain in battle!`
      } else if (ev.type === 'alliance') {
        desc = `[HOLY ALLIANCE] ${clanName(p.a)} and ${clanName(p.b)} forged a sacred peace pact.`
      } else if (ev.type === 'coalition_formed') {
        desc = `[COALITION FORMED] Defensive bloc "${p.name ?? 'Alliance'}" established under ${clanName(p.founder)}.`
      } else if (ev.type === 'temple') {
        desc = `[TEMPLE OF THE SPHERE] ${clanName(p.clan_id)} consecrated a grand Temple of the Sphere.`
      } else if (ev.type === 'miracle') {
        desc = `[DIVINE MIRACLE] The Sacred Avatar worked a seasonal miracle for ${clanName(p.clan_id)}, healing the faithful.`
      } else if (ev.type === 'synod') {
        desc = `[GREAT SYNOD] The Great Synod convened across all clans during the ${p.age ?? 'crisis'} era, declaring sacred truce.`
      } else if (ev.type === 'epiphany') {
        desc = `[3D EPIPHANY] An elder priest received the divine revelation of the 3D Sphere from Spaceland.`
      } else if (ev.type === 'disaster') {
        desc = `[NATURAL DISASTER] Cataclysm: ${p.kind ?? 'Catastrophe'} struck at (${ev.x}, ${ev.y}).`
      } else if (ev.type === 'settlement' && p.kind === 'bridge') {
        desc = `[CIVIL ENGINEERING] ${clanName(p.clan_id)} built a river plank bridge spanning channel cy=${p.river_cy}.`
      } else if (ev.type === 'defection') {
        desc = `[DEFECTION] Dissatisfied ${ev.caste ?? 'member'} defected from ${p.from_name ?? 'Clan'} to ${p.to_name ?? 'Clan'}.`
      } else if (ev.type === 'cannibalism') {
        desc = `[DESPERATION CANNIBALISM] Starving citizen consumed fallen kin; kin-eater exiled into wilderness.`
      } else if (ev.type === 'death') {
        desc = `[MORTALITY] ${ev.caste ?? 'Citizen'} #${ev.entity_id} (${p.personal_name ?? ''}) perished due to ${ev.cause ?? 'unknown'}.`
      } else {
        desc = `[${ev.type.toUpperCase()}] Event occurred involving #${ev.entity_id}.`
      }

      return `- **Day ${day} (Tick ${ev.tick})**: ${desc}`
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
- **Major Milestone Tallies**: ${stats.wars} Wars (${stats.lethalWars} lethal), ${stats.outbreaks} Pandemics, ${stats.schisms} Rebellions, ${stats.temples} Temples Raised, ${stats.disasters} Cataclysms, ${stats.bridges} Bridges Built.

## Clan Roster & Avatars
${clanSummary || 'No formal clans recorded.'}

## Chronological Major Milestones & Epochs
${eventTimeline || 'No major events recorded yet.'}

---

## Story Writing Instructions for LLM:
${stylePrompt}

**Guidelines**:
1. Ground the narrative strictly in the real recorded events and clan names above.
2. Portray the unique geometric nature of Flatland characters (angles, vertex sharpness, fog perception, line speed).
3. Weave the historical milestones (wars, plagues, bridges, temples, schisms) into pivotal plot turns.
4. Structure the response into structured chronological chapters or epochs.`
  }, [state, clans, events, stats, totalDays, storyStyle])

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
    const blob = new Blob([JSON.stringify({ state, stats, clans, events }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `flatland_history_events_seed_${state?.seed ?? 42}.json`
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
                Seed {state?.seed ?? 42} · Day {totalDays} ({state?.tick ?? 0} ticks) · {state?.creatures_alive ?? 0} alive · {state?.creatures_dead ?? 0} fallen
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
              📜 Timeline ({filteredEvents.length})
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
              🤖 LLM Story Exporter
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
            gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
            gap: 6,
            padding: '8px 16px',
            background: 'rgba(110,118,129,0.06)',
            borderBottom: '1px solid #21262d',
            fontSize: 11,
          }}
        >
          <div className="chip" title="Total war clashes & casualties">
            ⚔️ <b>{stats.wars}</b> wars ({stats.lethalWars} lethal)
          </div>
          <div className="chip" title="Plague outbreaks recorded">
            ☣️ <b>{stats.outbreaks}</b> plagues
          </div>
          <div className="chip" title="Internal rebellions & schisms">
            ⚡ <b>{stats.schisms}</b> schisms
          </div>
          <div className="chip" title="Dynastic ruler successions">
            👑 <b>{stats.successions}</b> successions
          </div>
          <div className="chip" title="Great Temples raised">
            🏛️ <b>{stats.temples}</b> temples
          </div>
          <div className="chip" title="Seasonal Avatar Miracles">
            🌸 <b>{stats.miracles}</b> miracles
          </div>
          <div className="chip" title="Natural cataclysms & floods">
            🌋 <b>{stats.disasters}</b> cataclysms
          </div>
          <div className="chip" title="River plank bridges constructed">
            🏗️ <b>{stats.bridges}</b> bridges
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
                  placeholder="Filter by clan, event, casualty..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{
                    background: '#161b22',
                    border: '1px solid #30363d',
                    color: '#c9d1d9',
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    width: 200,
                  }}
                />
              </div>

              {/* Event Feed */}
              {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  Loading world historical records...
                </div>
              ) : filteredEvents.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  No major historical events recorded for this category yet.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {filteredEvents.map((ev, i) => {
                    const day = (ev.tick / 1200).toFixed(1)
                    const p = ev.payload ?? {}

                    let badgeColor = '#58a6ff'
                    let icon = '📜'
                    let title = ev.type.toUpperCase()
                    let detail = ''

                    if (ev.type === 'war') {
                      badgeColor = '#f85149'
                      icon = '⚔️'
                      title = `War Clash · ${clanName(p.a)} vs ${clanName(p.b)}`
                      detail = `Damage: ${p.damage?.toFixed(1) ?? 'N/A'}${p.lethal ? ' (LETHAL)' : ''} · Winner: ${p.winner ? '#' + p.winner : 'Inconclusive'}`
                    } else if (ev.type === 'conquest' || ev.type === 'takeover') {
                      badgeColor = '#d29922'
                      icon = '🚩'
                      title = `Territorial Conquest · ${clanName(p.invader ?? p.clan_id)}`
                      detail = `Seized hall from ${clanName(p.rival ?? p.victim_clan)}`
                    } else if (ev.type === 'schism') {
                      badgeColor = '#ff7b72'
                      icon = '⚡'
                      title = `Rebellion & Schism · ${clanName(p.from_clan)}`
                      detail = 'Dissidents fractured away to establish a rival clan'
                    } else if (ev.type === 'betrayal') {
                      badgeColor = '#f85149'
                      icon = '🗡️'
                      title = `Treachery & Betrayal`
                      detail = `${clanName(p.clan_id)} struck former ally ${clanName(p.target_clan)}`
                    } else if (ev.type === 'outbreak') {
                      badgeColor = '#3fb950'
                      icon = '☣️'
                      title = `Plague Outbreak #${p.disease_id ?? 1}`
                      detail = `Contagion gripped Patient #${ev.entity_id} (${ev.caste ?? 'citizen'})`
                    } else if (ev.type === 'recovery') {
                      badgeColor = '#3fb950'
                      icon = '🌿'
                      title = `Plague Recovery`
                      detail = `Patient #${ev.entity_id} healed from infection`
                    } else if (ev.type === 'succession') {
                      badgeColor = '#d29922'
                      icon = '👑'
                      title = `Ruler Succession · ${clanName(p.clan_id)}`
                      detail = `Chieftain #${p.new_leader} ascended after #${p.prev_leader}`
                    } else if (ev.type === 'regicide') {
                      badgeColor = '#f85149'
                      icon = '👑'
                      title = `Regicide in Battle`
                      detail = `Chieftain of ${clanName(p.clan_id)} perished in war`
                    } else if (ev.type === 'temple') {
                      badgeColor = '#bc8cff'
                      icon = '🏛️'
                      title = `Temple Consecration · ${clanName(p.clan_id)}`
                      detail = 'Raised the sacred shrine into a glowing Temple of the Sphere'
                    } else if (ev.type === 'miracle') {
                      badgeColor = '#bc8cff'
                      icon = '🌸'
                      title = `Divine Miracle`
                      detail = `Avatar granted seasonal miracle to ${clanName(p.clan_id)}`
                    } else if (ev.type === 'synod') {
                      badgeColor = '#58a6ff'
                      icon = '🕊️'
                      title = `The Great Synod of the Sphere`
                      detail = `Crisis council convened sacred truce during ${p.age ?? 'crisis'} era`
                    } else if (ev.type === 'epiphany') {
                      badgeColor = '#f0883e'
                      icon = '✨'
                      title = `3D Epiphany Revelation`
                      detail = 'Elder priest beheld the sacred third dimension'
                    } else if (ev.type === 'disaster') {
                      badgeColor = '#f85149'
                      icon = '🌋'
                      title = `Cataclysm: ${p.kind ?? 'Disaster'}`
                      detail = `Severe event struck at coordinates (${ev.x}, ${ev.y})`
                    } else if (ev.type === 'settlement' && p.kind === 'bridge') {
                      badgeColor = '#8b949e'
                      icon = '🏗️'
                      title = `Plank Bridge Constructed`
                      detail = `${clanName(p.clan_id)} built bridge over river channel (cy=${p.river_cy})`
                    } else if (ev.type === 'extinction') {
                      badgeColor = '#f85149'
                      icon = '💀'
                      title = `World Extinction Event`
                      detail = 'All living citizens perished; world fell silent'
                    } else {
                      detail = JSON.stringify(p)
                    }

                    return (
                      <div
                        key={ev.id ?? i}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          background: '#161b22',
                          border: '1px solid #21262d',
                          borderLeft: `4px solid ${badgeColor}`,
                          borderRadius: 6,
                          padding: '8px 12px',
                          fontSize: 12,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontSize: 16 }}>{icon}</span>
                          <div>
                            <div style={{ color: '#e6edf3', fontWeight: 600 }}>{title}</div>
                            <div style={{ color: '#8b949e', fontSize: 11, marginTop: 1 }}>{detail}</div>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          <span
                            className="chip"
                            style={{
                              background: '#21262d',
                              padding: '2px 6px',
                              borderRadius: 4,
                              fontSize: 10,
                            }}
                          >
                            Day {day} · #{ev.tick}
                          </span>
                        </div>
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
                      Ready to paste into ChatGPT, Claude, or Gemini to generate a novel, chronicle, or saga of your world.
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
          <span>Chronicle records stored in SQLite and accessible via <code>/api/history?major=true</code></span>
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
