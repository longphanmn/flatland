import { useEffect, useMemo, useState } from 'react'
import type { StateMessage, WorldSummary } from '../types'
import { totemEmoji } from '../totems'
import { useI18n } from '../i18n'

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

const CATEGORY_TABS: Array<{ key: MajorCategory; icon: string }> = [
  { key: 'all', icon: '📅' },
  { key: 'war', icon: '⚔️' },
  { key: 'plague', icon: '☣️' },
  { key: 'politics', icon: '👑' },
  { key: 'faith', icon: '🏛️' },
  { key: 'disaster', icon: '🌋' },
]

interface WarDetail {
  aName: string
  bName: string
  battles: number
  casualties: number
}

interface ConquestDetail {
  invaderName: string
  victimName: string
  houseId: number
  plunderedFood?: number
}

interface OutbreakDetail {
  diseaseId: number
  caste?: string
}

interface DynastyDetail {
  kind: 'succession' | 'regicide' | 'schism' | 'treaty' | 'coalition' | 'betrayal' | 'extinction'
  title: string
  detail: string
}

interface FaithDetail {
  kind: 'temple' | 'miracle' | 'epiphany' | 'synod'
  clanName?: string
  detail: string
}

interface DisasterDetail {
  kind: string
  count: number
}

export interface DayRecord {
  day: number
  startTick: number
  endTick: number
  summaryLine: string
  primaryIcon: string
  badgeColor: string
  categories: Set<MajorCategory>
  wars: WarDetail[]
  conquests: ConquestDetail[]
  outbreaks: OutbreakDetail[]
  dynasties: DynastyDetail[]
  faiths: FaithDetail[]
  disasters: DisasterDetail[]
  totalCasualties: number
}

type StoryStyle = 'saga' | 'chronicle' | 'mythos' | 'tragedy'

const STYLE_LABELS: Record<StoryStyle, string> = {
  saga: '⚔️ Epic Novel Saga',
  chronicle: '📜 Ancient Historical Chronicle',
  mythos: '🔮 Spiritual & Mythological Lore',
  tragedy: '💀 Tragic Extinction & Decline',
}

const STYLE_PROMPTS: Record<StoryStyle, string> = {
  saga: 'Write a dramatic, multi-chapter historical epic saga following specific chieftains, named warriors, and priests across the daily chronicle. Emphasize character journeys, tactical battles between named clans, political betrayals, and survival during harsh winters.',
  chronicle: 'Write an ancient, scholarly historical chronicle recording the day-by-day rise and fall of named geometric clans, territorial conquests, legal philosophy, demographic curves, and military campaigns.',
  mythos: 'Write a spiritual and philosophical mythos focusing on the 2D inhabitants discovering the divine 3D Sphere, worshipping sacred avatars, raising glowing temples, and experiencing cosmic epiphanies.',
  tragedy: 'Write a poignant tragedy recording the golden heights of the geometric civilization, its slow descent into plague and ice, and the solemn extinction of the final living creature.',
}

const ADJECTIVES = ['Silent', 'Ancient', 'Crimson', 'Silver', 'Golden', 'Shadow', 'Azure', 'Iron', 'Emerald', 'Solar', 'Lunar', 'Obsidian', 'Dawn', 'Dusk', 'Misty', 'Starlight', 'Verdant', 'Echoing', 'Storm', 'Radiant']
const NOUNS = ['Spire', 'Shield', 'Circle', 'Blade', 'Monolith', 'Sanctum', 'Vertex', 'Lineage', 'Hearth', 'Haven', 'Vanguard', 'Beacon', 'Sovereigns', 'Keepers', 'Pillars', 'Wardens', 'Foundry', 'Sands', 'Bridges', 'Valley']

function generateClanName(id: number): string {
  const adj = ADJECTIVES[Math.abs(id * 7 + 13) % ADJECTIVES.length]
  const noun = NOUNS[Math.abs(id * 11 + 37) % NOUNS.length]
  return `Clan of the ${adj} ${noun}`
}

export default function WorldHistoryModal({ open, onClose, state, selectedRunId }: Props) {
  const { t } = useI18n()
  const [rawEvents, setRawEvents] = useState<any[]>([])
  const [clans, setClans] = useState<Record<string, any>>({})
  const [clanNames, setClanNames] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'timeline' | 'llm'>('timeline')
  const [category, setCategory] = useState<MajorCategory>('all')
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState(false)
  const [expandedDay, setExpandedDay] = useState<number | null>(null)
  const [storyStyle, setStoryStyle] = useState<StoryStyle>(() => {
    try {
      const s = sessionStorage.getItem('history-story-style') as StoryStyle | null
      if (s && s in STYLE_LABELS) return s
    } catch { /* ignore */ }
    return 'saga'
  })
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768)

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  // Persist the chosen writing style across modal reopens
  useEffect(() => {
    try { sessionStorage.setItem('history-story-style', storyStyle) } catch { /* ignore */ }
  }, [storyStyle])

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
      fetch('/api/history?major=true&limit=2000').then((r) => r.json()),
      fetch('/api/clans').then((r) => r.json()),
    ])
      .then(([histData, clanData]) => {
        setRawEvents(histData.events ?? [])
        const clanMap: Record<string, any> = {}
        const nameMap: Record<string, string> = {
          ...(histData.clan_names ?? {}),
          ...(clanData.names ?? {}),
        }
        for (const c of clanData.clans ?? []) {
          clanMap[String(c.id)] = c
          if (c.name) nameMap[String(c.id)] = c.name
        }
        setClans(clanMap)
        setClanNames(nameMap)
      })
      .catch((err) => console.error('Failed to load world history:', err))
      .finally(() => setLoading(false))
  }, [open, selectedRunId])

  const clanName = (id?: number | null, fallbackName?: string | null) => {
    if (fallbackName && !fallbackName.startsWith('Clan #') && !fallbackName.startsWith('#')) {
      return fallbackName
    }
    if (id == null) return 'Independent Realm'
    const fromMap = clanNames[String(id)] ?? clans[String(id)]?.name ?? state?.clans?.[String(id)]?.name
    if (fromMap && !fromMap.startsWith('Clan #') && !fromMap.startsWith('#')) {
      return fromMap
    }
    return generateClanName(id)
  }

  // Aggregate raw events into DayRecords (1 Day = 1200 ticks)
  const dayRecords = useMemo<DayRecord[]>(() => {
    const currentTick = state?.tick ?? 0
    const maxDay = Math.max(0, Math.floor(currentTick / 1200))
    const daysMap: Map<number, DayRecord> = new Map()

    // Initialize days
    for (let d = 0; d <= maxDay; d++) {
      daysMap.set(d, {
        day: d,
        startTick: d * 1200,
        endTick: (d + 1) * 1200 - 1,
        summaryLine: '',
        primaryIcon: '🌱',
        badgeColor: '#3fb950',
        categories: new Set<MajorCategory>(['all']),
        wars: [],
        conquests: [],
        outbreaks: [],
        dynasties: [],
        faiths: [],
        disasters: [],
        totalCasualties: 0,
      })
    }

    // Temporary war tracker per day: Map<dayNumber, Map<pairKey, WarDetail>>
    const dayWarMap: Map<number, Map<string, WarDetail>> = new Map()

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
          wars: [],
          conquests: [],
          outbreaks: [],
          dynasties: [],
          faiths: [],
          disasters: [],
          totalCasualties: 0,
        }
        daysMap.set(dayNum, dRec)
      }

      const p = ev.payload ?? {}

      if (ev.type === 'war') {
        dRec.categories.add('war')
        const a = p.a ?? 0
        const b = p.b ?? 0
        const pairKey = [Math.min(a, b), Math.max(a, b)].join(':')
        let warMap = dayWarMap.get(dayNum)
        if (!warMap) {
          warMap = new Map()
          dayWarMap.set(dayNum, warMap)
        }
        let w = warMap.get(pairKey)
        if (!w) {
          w = {
            aName: clanName(a, p.a_name),
            bName: clanName(b, p.b_name),
            battles: 0,
            casualties: 0,
          }
          warMap.set(pairKey, w)
        }
        w.battles++
        if (p.lethal) {
          w.casualties++
          dRec.totalCasualties++
        }
      } else if (ev.type === 'takeover' || ev.type === 'conquest') {
        dRec.categories.add('war')
        const invaderName = clanName(p.invader_clan ?? p.clan_id, p.invader_name)
        const victimName = clanName(p.victim_clan ?? p.rival, p.victim_name)
        dRec.conquests.push({
          invaderName,
          victimName,
          houseId: p.house_id ?? ev.entity_id,
          plunderedFood: p.plundered_food,
        })
      } else if (ev.type === 'regicide') {
        dRec.categories.add('war')
        dRec.categories.add('politics')
        dRec.totalCasualties++
        const victimClan = clanName(p.victim_clan ?? p.clan_id, p.clan_name)
        dRec.dynasties.push({
          kind: 'regicide',
          title: t('history.details.regicideTitle', { clan: victimClan }),
          detail: t('history.details.regicideDetail', { clan: victimClan }),
        })
      } else if (ev.type === 'outbreak') {
        dRec.categories.add('plague')
        dRec.outbreaks.push({
          diseaseId: p.disease_id ?? 1,
          caste: ev.caste ?? 'citizen',
        })
      } else if (ev.type === 'schism') {
        dRec.categories.add('politics')
        const parentClan = clanName(p.parent ?? p.from_clan ?? p.clan_id, p.parent_name ?? p.from_name)
        const newClan = clanName(p.new_clan ?? p.to_clan, p.new_name ?? p.to_name)
        const count = (p.members?.length ?? p.member_count) || 1
        dRec.dynasties.push({
          kind: 'schism',
          title: t('history.details.schismTitle', { clan: parentClan }),
          detail: t('history.details.schismBreakdown', { parent: parentClan, child: newClan, count }),
        })
      } else if (ev.type === 'clan_extinction') {
        dRec.categories.add('politics')
        const cName = clanName(p.clan_id, p.clan_name)
        const days = p.lifespan_days ?? (p.lifespan_ticks ? Math.round(p.lifespan_ticks / 1200) : 0)
        dRec.dynasties.push({
          kind: 'extinction',
          title: t('history.details.clanExtinctionTitle', { clan: cName }),
          detail: t('history.details.clanExtinctionDetail', { clan: cName, days }),
        })
      } else if (ev.type === 'succession') {
        dRec.categories.add('politics')
        const cName = clanName(p.clan_id, p.clan_name)
        dRec.dynasties.push({
          kind: 'succession',
          title: t('history.details.successionTitle', { clan: cName }),
          detail: t('history.details.successionDetail', { leader: p.new_leader, clan: cName }),
        })
      } else if (ev.type === 'alliance' || ev.type === 'coalition_formed') {
        dRec.categories.add('politics')
        const cAName = clanName(p.a ?? p.founder, p.a_name)
        const cBName = p.b ? clanName(p.b, p.b_name) : ''
        dRec.dynasties.push({
          kind: ev.type === 'coalition_formed' ? 'coalition' : 'treaty',
          title: ev.type === 'coalition_formed' ? t('history.details.coalitionTitle', { name: p.name ?? 'Grand Coalition' }) : t('history.details.treatyTitle', { a: cAName, b: cBName }),
          detail: ev.type === 'coalition_formed' ? t('history.details.coalitionDetail', { clan: cAName }) : t('history.details.treatyDetail'),
        })
      } else if (ev.type === 'betrayal') {
        dRec.categories.add('politics')
        const cName = clanName(p.clan_id, p.clan_name)
        const tName = clanName(p.target_clan, p.target_name)
        dRec.dynasties.push({
          kind: 'betrayal',
          title: t('history.details.betrayalTitle', { clan: cName }),
          detail: t('history.details.betrayalDetail', { target: tName }),
        })
      } else if (ev.type === 'temple') {
        dRec.categories.add('faith')
        const cName = clanName(p.clan_id, p.clan_name)
        dRec.faiths.push({
          kind: 'temple',
          clanName: cName,
          detail: t('history.details.templeDetail', { clan: cName }),
        })
      } else if (ev.type === 'miracle') {
        dRec.categories.add('faith')
        const cName = clanName(p.clan_id)
        dRec.faiths.push({
          kind: 'miracle',
          clanName: cName,
          detail: t('history.details.miracleDetail', { clan: cName }),
        })
      } else if (ev.type === 'epiphany') {
        dRec.categories.add('faith')
        dRec.faiths.push({
          kind: 'epiphany',
          detail: t('history.details.epiphanyDetail'),
        })
      } else if (ev.type === 'synod') {
        dRec.categories.add('faith')
        dRec.faiths.push({
          kind: 'synod',
          detail: t('history.details.synodDetail'),
        })
      } else if (ev.type === 'disaster') {
        dRec.categories.add('disaster')
        const rawKind = String(p.kind ?? 'Cataclysm')
        const kindLabel = rawKind === 'river_flood' ? t('history.details.riverFlood')
          : rawKind === 'flash_flood' ? t('history.details.flashFlood')
          : rawKind === 'meteor' ? t('history.details.meteor')
          : rawKind === 'earthquake' ? t('history.details.earthquake')
          : rawKind
        const existing = dRec.disasters.find((dis) => dis.kind === kindLabel)
        if (existing) {
          existing.count++
        } else {
          dRec.disasters.push({
            kind: kindLabel,
            count: 1,
          })
        }
      } else if (ev.type === 'extinction') {
        dRec.categories.add('disaster')
        dRec.disasters.push({
          kind: 'World Extinction',
          count: 1,
        })
      }
    }

    // Attach consolidated wars to DayRecords
    for (const [dayNum, warMap] of dayWarMap.entries()) {
      const dRec = daysMap.get(dayNum)
      if (dRec) {
        dRec.wars = Array.from(warMap.values())
      }
    }

    // Build rich, specific One-Line Daily Digest Sentence
    const sortedDays = Array.from(daysMap.values()).sort((a, b) => a.day - b.day)

    for (const d of sortedDays) {
      const highlights: string[] = []

      // 1. Genesis
      if (d.day === 0) {
        const clanNames = Object.values(clans).slice(0, 3).map((c) => c.name).filter(Boolean).join(', ')
        highlights.push(t('history.details.genesis', { clans: clanNames || 'founding clans' }))
        d.primaryIcon = '🌱'
        d.badgeColor = '#3fb950'
      }

      // 2. High-Impact Dynasties (Clan Schisms / Fracturing / Regicides / Clan Extinctions)
      const schisms = d.dynasties.filter((dyn) => dyn.kind === 'schism')
      const clanExtinctions = d.dynasties.filter((dyn) => dyn.kind === 'extinction')
      const regicides = d.dynasties.filter((dyn) => dyn.kind === 'regicide')

      if (schisms.length > 0 || clanExtinctions.length > 0 || regicides.length > 0) {
        d.primaryIcon = schisms.length > 0 ? '👑' : regicides.length > 0 ? '🗡️' : '💀'
        d.badgeColor = schisms.length > 0 ? '#e3b341' : '#f85149'

        if (schisms.length >= 2) {
          highlights.push(t('history.details.greatFracturingMultiple', { count: schisms.length }))
        } else if (schisms.length === 1) {
          highlights.push(schisms[0].detail)
        }

        if (clanExtinctions.length > 0) {
          const extSnippets = clanExtinctions.map((e) => e.title).join(', ')
          highlights.push(extSnippets)
        }

        if (regicides.length > 0) {
          const regSnippets = regicides.map((r) => r.title).join(', ')
          highlights.push(regSnippets)
        }
      }

      // 3. Detailed Major Wars (lethal casualties) & Territorial Conquests
      const lethalWars = d.wars.filter((w) => w.casualties > 0)
      if (lethalWars.length > 0 || d.conquests.length > 0) {
        if (!d.dynasties.some(dyn => dyn.kind === 'schism')) {
          d.primaryIcon = '⚔️'
          d.badgeColor = '#f85149'
        }
        if (lethalWars.length > 0) {
          const warSnippets = lethalWars.map((w) => {
            const casText = t('history.details.fallenDigest', { count: w.casualties })
            return `${w.aName} vs ${w.bName}${casText}`
          })
          highlights.push(t('history.details.warDigest', { wars: warSnippets.join(', ') }))
        }
        if (d.conquests.length > 0) {
          const conqSnippets = d.conquests.slice(0, 2).map((c) => {
            return t('history.details.conquestDigestItem', { invader: c.invaderName, house: c.houseId, victim: c.victimName })
          })
          highlights.push(t('history.details.conquestDigest', { conquests: conqSnippets.join(', ') }))
        }
      }

      // 4. Detailed Plagues
      if (d.outbreaks.length > 0) {
        if (highlights.length === 0) {
          d.primaryIcon = '☣️'
          d.badgeColor = '#3fb950'
        }
        highlights.push(t('history.details.plagueDigest', { id: d.outbreaks[0].diseaseId }))
      }

      // 5. Detailed Faith
      if (d.faiths.length > 0) {
        if (highlights.length === 0) {
          d.primaryIcon = '🏛️'
          d.badgeColor = '#bc8cff'
        }
        const fSnippets = d.faiths.slice(0, 2).map((f) => f.detail)
        highlights.push(t('history.details.faithDigest', { faiths: fSnippets.join(' & ') }))
      }

      // 6. Detailed Disasters (Deduplicated with count)
      if (d.disasters.length > 0) {
        if (highlights.length === 0) {
          d.primaryIcon = '🌋'
          d.badgeColor = '#f85149'
        }
        const disSnippets = d.disasters.map((dis) => dis.count > 1 ? `${dis.kind} (×${dis.count})` : dis.kind)
        highlights.push(t('history.details.cataclysmDigest', { kinds: disSnippets.join(', ') }))
      }

      // 7. Other Political Treaties & Successions
      const otherDynasties = d.dynasties.filter((dyn) => dyn.kind !== 'schism' && dyn.kind !== 'extinction' && dyn.kind !== 'regicide')
      if (otherDynasties.length > 0 && highlights.length < 2) {
        if (highlights.length === 0) {
          d.primaryIcon = '👑'
          d.badgeColor = '#e3b341'
        }
        const dSnippets = otherDynasties.slice(0, 2).map((dyn) => dyn.title)
        highlights.push(t('history.details.politicsDigest', { politics: dSnippets.join(' · ') }))
      }

      // 8. Peaceful / Flourishing Day variety based on seasonal cycles, clan leaders, and active demographics
      if (highlights.length === 0) {
        const seasonIndex = Math.floor((d.day % 12) / 3)
        const seasonDesc = [
          t('history.details.springThaw'),
          t('history.details.highSummer'),
          t('history.details.autumnBounty'),
          t('history.details.deepWinter'),
        ][seasonIndex]

        const clanList = Object.values(clans).filter((c: any) => c.name)
        const leadClan = clanList.length > 0 ? clanList[(d.day * 3 + 7) % clanList.length]?.name : null

        const flavorIndex = d.day % 4
        let flavorDesc = [
          t('history.details.flavor0'),
          t('history.details.flavor1'),
          t('history.details.flavor2'),
          t('history.details.flavor3'),
        ][flavorIndex]

        if (leadClan) {
          flavorDesc = `${leadClan} ${flavorDesc}`
        }

        highlights.push(`${seasonDesc} · ${flavorDesc}`)
        d.primaryIcon = ['🌱', '☀️', '🍂', '❄️'][seasonIndex]
        d.badgeColor = ['#3fb950', '#e3b341', '#f0883e', '#79c0ff'][seasonIndex]
      }

      d.summaryLine = highlights.join(' · ')
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
        const text = `day ${d.day} ${d.summaryLine}`.toLowerCase()
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
    let clanExtinctions = 0
    let disasters = 0
    let temples = 0
    let miracles = 0
    let successions = 0

    for (const d of dayRecords) {
      wars += d.wars.reduce((acc, w) => acc + w.battles, 0)
      lethalWars += d.totalCasualties
      outbreaks += d.outbreaks.length
      schisms += d.dynasties.filter((dyn) => dyn.kind === 'schism').length
      clanExtinctions += d.dynasties.filter((dyn) => dyn.kind === 'extinction').length
      successions += d.dynasties.filter((dyn) => dyn.kind === 'succession').length
      temples += d.faiths.filter((f) => f.kind === 'temple').length
      miracles += d.faiths.filter((f) => f.kind === 'miracle').length
      disasters += d.disasters.reduce((acc, dis) => acc + dis.count, 0)
    }

    return { wars, lethalWars, outbreaks, schisms, clanExtinctions, disasters, temples, miracles, successions }
  }, [dayRecords])

  const totalDays = state ? (state.tick / 1200).toFixed(1) : '0'

  // Build the LLM Story Prompt (Chronological Rich Day-by-Day Historical Chronicle)
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

    const styleLabel = STYLE_LABELS[storyStyle]
    const stylePrompt = STYLE_PROMPTS[storyStyle]

    return `# The Chronicles of Flatland: World Seed ${seed}

## Writing Style — ${styleLabel}
${stylePrompt}


## Context & World Lore
You are an epic historian and bard recording the true history of a simulated 2D world inspired by Edwin A. Abbott's *Flatland*.
- **Society**: Women are razor-sharp line segments; Men are regular polygons whose status ascends by side count (Isosceles Triangles -> Soldiers -> Equilateral Artisans -> Squares -> Pentagons -> Hexagonal Nobles -> Multi-sided Priests/Circles).
- **Faith & Avatars**: Clans revere Sacred 2D Avatars of the 3D Sphere (Radiant Circle, Celestial Strike, All-Seeing Vertex, Indomitable Monolith, Sacred Spiral, Cosmic Scales, Tactical Rift, Eternal Hearth).
- **Environment**: The world cycles through 4 Great Ages (Golden Era, Ice Age, Chaos Era, Plague Age) and dynamic seasons.

## World Statistics
- **Total Duration**: ${totalDays} Days (${state?.tick ?? 0} Ticks)
- **World Seed**: ${seed}
- **Current Population**: ${aliveCount} Alive | ${deadCount} Fallen
- **Mortality Breakdown**: ${Object.entries(deadByCause).map(([k, v]) => `${k}: ${v}`).join(', ') || 'None recorded'}
- **Major Milestone Tallies**: ${totalStats.wars} Battles (${totalStats.lethalWars} fallen), ${totalStats.outbreaks} Pandemics, ${totalStats.schisms} Rebellions, ${totalStats.temples} Temples Raised, ${totalStats.disasters} Cataclysms.

## Clan Roster & Avatars
${clanSummary || 'No formal clans recorded.'}

## Detailed Day-by-Day Historical Chronicle (${chronologicalDays.length} Days)
${dayTimeline || 'No daily records recorded yet.'}

---

## Story Writing Instructions for LLM:
${stylePrompt}

**Guidelines**:
1. Follow the chronological day-by-day turning points above with the exact clan names, casualties, and milestones.
2. Portray the unique geometric nature of Flatland characters (angles, vertex sharpness, fog perception, line speed).
3. Weave the historical milestones (named wars, house conquests, outbreaks, temples, schisms) into pivotal chapter turns.`
  }, [state, clans, dayRecords, totalStats, totalDays, storyStyle])

  const copyToClipboard = async () => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(llmPrompt)
      } else {
        throw new Error('no clipboard')
      }
    } catch {
      // fallback for iOS / insecure context: textarea + execCommand + prompt
      try {
        const ta = document.createElement('textarea')
        ta.value = llmPrompt
        ta.style.position = 'fixed'
        ta.style.opacity = '0'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      } catch {
        window.prompt('Copy the chronicle (⌘C / Ctrl+C):', llmPrompt)
        return
      }
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    setTimeout(() => {
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }, 1000)
    // iOS fallback: if download didn't trigger, open in new tab
    if (navigator.userAgent.match(/iPhone|iPad|iPod/i)) {
      setTimeout(() => window.open(url, '_blank') ?? undefined, 100)
    }
  }

  const downloadMarkdown = () => {
    const blob = new Blob([llmPrompt], { type: 'text/markdown;charset=utf-8' })
    triggerDownload(blob, `flatland_detailed_daily_history_seed_${state?.seed ?? 42}.md`)
  }

  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({ state, totalStats, clans, dayRecords }, null, 2)], { type: 'application/json' })
    triggerDownload(blob, `flatland_detailed_daily_history_seed_${state?.seed ?? 42}.json`)
  }

  if (!open) return null

  return (
    <div
      className="clan-details-backdrop"
      onClick={onClose}
      style={{
        zIndex: 100,
        padding: isMobile ? 0 : undefined,
        paddingTop: isMobile ? 'env(safe-area-inset-top)' : undefined,
        paddingBottom: isMobile ? 'env(safe-area-inset-bottom)' : undefined,
        overflow: 'auto',
        WebkitOverflowScrolling: 'touch' as any,
      }}
    >
      <div
        className="clan-details-panel"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: isMobile ? '100vw' : 'min(900px, 96vw)',
          height: isMobile ? '100dvh' : 'auto',
          maxHeight: isMobile ? '100dvh' : '92vh',
          minHeight: isMobile ? '100dvh' : undefined,
          display: 'flex',
          flexDirection: 'column',
          padding: 0,
          background: '#0d1117',
          border: isMobile ? 'none' : '1px solid #30363d',
          boxShadow: '0 20px 48px rgba(0,0,0,0.8)',
          borderRadius: isMobile ? 0 : 12,
          overflow: 'hidden',
        }}
      >
        {/* Header — sticky on phone so topbar never scrolls under notch */}
        <header
          style={{
            padding: isMobile ? 'max(10px, env(safe-area-inset-top)) 12px 8px' : '14px 18px',
            borderBottom: '1px solid #21262d',
            background: '#161b22',
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'stretch' : 'center',
            gap: isMobile ? 8 : 12,
            position: isMobile ? ('sticky' as const) : undefined,
            top: isMobile ? 0 : undefined,
            zIndex: isMobile ? 5 : undefined,
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: isMobile ? '100%' : 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 8 : 10 }}>
              <span style={{ fontSize: isMobile ? 20 : 24 }}>📜</span>
              <div>
                <h2 style={{ fontSize: isMobile ? 14 : 16, margin: 0, color: '#e6edf3', fontWeight: 700 }}>
                  {t('history.title')}
                </h2>
                <div style={{ fontSize: 10.5, color: '#8b949e', marginTop: 1, wordBreak: 'break-word', overflowWrap: 'anywhere' as any }}>
                  {t('history.subtitle', { seed: state?.seed ?? 42, days: dayRecords.length, alive: state?.creatures_alive ?? 0 })}
                </div>
              </div>
            </div>
            {isMobile && (
              <button
                className="god-close"
                onClick={onClose}
                style={{ fontSize: 22, cursor: 'pointer', color: '#8b949e', background: 'transparent', border: 'none', padding: '0 6px', minHeight: 28 }}
              >
                ×
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: isMobile ? '100%' : 'auto' }}>
            <button
              onClick={() => setActiveTab('timeline')}
              className="chip"
              style={{
                flex: isMobile ? 1 : 'none',
                justifyContent: 'center',
                background: activeTab === 'timeline' ? '#238636' : '#21262d',
                color: activeTab === 'timeline' ? '#fff' : '#c9d1d9',
                borderColor: activeTab === 'timeline' ? '#2ea043' : '#30363d',
                padding: isMobile ? '6px 8px' : '6px 12px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: isMobile ? 11 : 12,
              }}
            >
              {t('history.tabs.timeline', { count: filteredDays.length })}
            </button>
            <button
              onClick={() => setActiveTab('llm')}
              className="chip"
              style={{
                flex: isMobile ? 1 : 'none',
                justifyContent: 'center',
                background: activeTab === 'llm' ? '#1f6feb' : '#21262d',
                color: activeTab === 'llm' ? '#fff' : '#c9d1d9',
                borderColor: activeTab === 'llm' ? '#388bfd' : '#30363d',
                padding: isMobile ? '6px 8px' : '6px 12px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: isMobile ? 11 : 12,
              }}
            >
              {t('history.tabs.ai')}
            </button>
            {!isMobile && (
              <button
                className="god-close"
                onClick={onClose}
                style={{ fontSize: 20, cursor: 'pointer', color: '#8b949e', marginLeft: 8 }}
              >
                ×
              </button>
            )}
          </div>
        </header>

        {/* Major Stats Ticker */}
        <div
          style={{
            display: 'flex',
            overflowX: 'auto',
            gap: 6,
            padding: isMobile ? '6px 10px' : '8px 16px',
            background: 'rgba(110,118,129,0.06)',
            borderBottom: '1px solid #21262d',
            fontSize: isMobile ? 10.5 : 11,
            scrollbarWidth: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          <div className="chip" style={{ flexShrink: 0 }} title="Major battles fought">
            ⚔️ <b>{totalStats.wars}</b> {t('history.stats.battles')} ({totalStats.lethalWars} {t('history.stats.fallen')})
          </div>
          <div className="chip" style={{ flexShrink: 0 }} title="Plague outbreaks">
            ☣️ <b>{totalStats.outbreaks}</b> {t('history.stats.plagues')}
          </div>
          <div className="chip" style={{ flexShrink: 0 }} title="Internal rebellions">
            ⚡ <b>{totalStats.schisms}</b> {t('history.stats.schisms')}
          </div>
          <div className="chip" style={{ flexShrink: 0 }} title="Ruler successions">
            👑 <b>{totalStats.successions}</b> {t('history.stats.successions')}
          </div>
          <div className="chip" style={{ flexShrink: 0 }} title="Temples of the Sphere">
            🏛️ <b>{totalStats.temples}</b> {t('history.stats.temples')}
          </div>
          <div className="chip" style={{ flexShrink: 0 }} title="Avatar seasonal miracles">
            🌸 <b>{totalStats.miracles}</b> {t('history.stats.miracles')}
          </div>
          <div className="chip" style={{ flexShrink: 0 }} title="Natural cataclysms">
            🌋 <b>{totalStats.disasters}</b> {t('history.stats.cataclysms')}
          </div>
        </div>

        {/* Main Body */}
        <div style={{ flex: 1, overflow: 'auto', padding: isMobile ? '10px 12px' : '16px 20px' }}>
          {activeTab === 'timeline' ? (
            <div>
              {/* Category Pills & Search */}
              <div
                style={{
                  display: 'flex',
                  flexDirection: isMobile ? 'column' : 'row',
                  justifyContent: 'space-between',
                  alignItems: isMobile ? 'stretch' : 'center',
                  gap: 8,
                  marginBottom: 12,
                }}
              >
                <div style={{ display: 'flex', overflowX: 'auto', gap: 4, paddingBottom: isMobile ? 4 : 0, scrollbarWidth: 'none' }}>
                  {CATEGORY_TABS.map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setCategory(tab.key)}
                      style={{
                        padding: isMobile ? '3px 8px' : '4px 10px',
                        fontSize: isMobile ? 10.5 : 11,
                        borderRadius: 20,
                        border: '1px solid',
                        background: category === tab.key ? '#388bfd' : '#21262d',
                        borderColor: category === tab.key ? '#58a6ff' : '#30363d',
                        color: category === tab.key ? '#fff' : '#8b949e',
                        cursor: 'pointer',
                        fontWeight: category === tab.key ? 700 : 500,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                      }}
                    >
                      {tab.icon} {t(`history.tabs.${tab.key}`)}
                    </button>
                  ))}
                </div>

                <input
                  type="text"
                  placeholder={t('history.searchPlaceholder')}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{
                    background: '#161b22',
                    border: '1px solid #30363d',
                    color: '#c9d1d9',
                    padding: '6px 10px',
                    borderRadius: 6,
                    fontSize: 12,
                    width: isMobile ? '100%' : 220,
                  }}
                />
              </div>

              {/* Day Feed */}
              {loading ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  {t('history.analyzing')}
                </div>
              ) : filteredDays.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#8b949e' }}>
                  {t('history.empty')}
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
                              {t('history.dayNumber', { day: d.day })}
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
                              paddingTop: 10,
                              borderTop: '1px solid #30363d',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 8,
                              fontSize: 12,
                              color: '#c9d1d9',
                            }}
                          >
                            <div style={{ fontWeight: 600, color: '#8b949e', fontSize: 11 }}>
                              {t('history.dossier', { start: d.startTick, end: d.endTick })}
                            </div>

                            {/* Wars */}
                            {d.wars.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ color: '#f85149', fontWeight: 600 }}>{t('history.sections.military')}</span>
                                {d.wars.map((w, idx) => (
                                  <div key={idx} style={{ paddingLeft: 12, color: '#c9d1d9' }}>
                                    {t('history.details.warEntry', { a: w.aName, b: w.bName, battles: w.battles, casualties: w.casualties })}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Conquests */}
                            {d.conquests.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ color: '#d29922', fontWeight: 600 }}>{t('history.sections.conquests')}</span>
                                {d.conquests.map((c, idx) => (
                                  <div key={idx} style={{ paddingLeft: 12, color: '#c9d1d9' }}>
                                    {t('history.details.conquestEntry', { invader: c.invaderName, house: c.houseId, victim: c.victimName, food: c.plunderedFood ? t('history.details.conquestFood', { food: c.plunderedFood }) : '' })}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Plagues */}
                            {d.outbreaks.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ color: '#3fb950', fontWeight: 600 }}>{t('history.sections.plagues')}</span>
                                {d.outbreaks.map((o, idx) => (
                                  <div key={idx} style={{ paddingLeft: 12, color: '#c9d1d9' }}>
                                    {t('history.details.plagueEntry', { id: o.diseaseId, caste: o.caste })}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Dynasties */}
                            {d.dynasties.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ color: '#e3b341', fontWeight: 600 }}>{t('history.sections.dynasties')}</span>
                                {d.dynasties.map((dyn, idx) => (
                                  <div key={idx} style={{ paddingLeft: 12, color: '#c9d1d9' }}>
                                    • <b>{dyn.title}</b>: {dyn.detail}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Faith */}
                            {d.faiths.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ color: '#bc8cff', fontWeight: 600 }}>{t('history.sections.faith')}</span>
                                {d.faiths.map((f, idx) => (
                                  <div key={idx} style={{ paddingLeft: 12, color: '#c9d1d9' }}>
                                    • {f.detail}
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Disasters */}
                            {d.disasters.length > 0 && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ color: '#f85149', fontWeight: 600 }}>{t('history.sections.cataclysms')}</span>
                                {d.disasters.map((dis, idx) => (
                                  <div key={idx} style={{ paddingLeft: 12, color: '#c9d1d9' }}>
                                    {t('history.details.disasterEntry', { kind: dis.count > 1 ? `${dis.kind} (×${dis.count})` : dis.kind })}
                                  </div>
                                ))}
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
                      {t('history.tabs.ai')} Generation Prompt
                    </h3>
                    <p style={{ fontSize: 11, color: '#8b949e', margin: '4px 0 0' }}>
                      Rich, day-by-day historical chronicle with specific clan wars, conquests, successions, and miracles ready for ChatGPT, Claude, or Gemini.
                    </p>
                    {/* Live style badge — proves the dropdown took effect */}
                    <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <span
                        style={{
                          fontSize: 10.5,
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: 10,
                          background: 'rgba(56,139,253,0.18)',
                          border: '1px solid #388bfd',
                          color: '#79c0ff',
                        }}
                      >
                        {STYLE_LABELS[storyStyle]}
                      </span>
                      <span style={{ fontSize: 10, color: '#8b949e' }}>instructions applied at the top of the prompt ↓</span>
                    </div>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      flexDirection: isMobile ? 'column' : 'row',
                      alignItems: isMobile ? 'stretch' : 'center',
                      gap: 8,
                      width: isMobile ? '100%' : 'auto',
                      marginTop: isMobile ? 8 : 0,
                    }}
                  >
                    <select
                      value={storyStyle}
                      onChange={(e) => setStoryStyle(e.target.value as any)}
                      style={{
                        background: '#21262d',
                        border: '1px solid #30363d',
                        color: '#c9d1d9',
                        padding: isMobile ? '10px 10px' : '6px 10px',
                        borderRadius: 6,
                        fontSize: 12,
                        width: isMobile ? '100%' : 'auto',
                        minHeight: isMobile ? 44 : undefined,
                      }}
                    >
                      {(Object.keys(STYLE_LABELS) as StoryStyle[]).map((k) => (
                        <option key={k} value={k}>{STYLE_LABELS[k]}</option>
                      ))}
                    </select>

                    <div style={{ display: 'flex', gap: 6, width: isMobile ? '100%' : 'auto' }}>
                      <button
                        onClick={copyToClipboard}
                        style={{
                          flex: isMobile ? 1 : 'none',
                          background: copied ? '#238636' : '#1f6feb',
                          border: '1px solid',
                          borderColor: copied ? '#2ea043' : '#388bfd',
                          color: '#fff',
                          padding: isMobile ? '10px 14px' : '6px 14px',
                          borderRadius: 6,
                          fontSize: 12,
                          cursor: 'pointer',
                          fontWeight: 600,
                          minHeight: isMobile ? 44 : undefined,
                          touchAction: 'manipulation',
                          WebkitTapHighlightColor: 'transparent' as any,
                          textAlign: 'center',
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
                          padding: isMobile ? '10px 10px' : '6px 10px',
                          borderRadius: 6,
                          fontSize: 12,
                          cursor: 'pointer',
                          minHeight: isMobile ? 44 : undefined,
                          touchAction: 'manipulation',
                          WebkitTapHighlightColor: 'transparent' as any,
                        }}
                        title="Download Markdown"
                      >
                        ⬇️ .md
                      </button>
                      <button
                        onClick={downloadJSON}
                        style={{
                          background: '#21262d',
                          border: '1px solid #30363d',
                          color: '#c9d1d9',
                          padding: isMobile ? '10px 10px' : '6px 10px',
                          borderRadius: 6,
                          fontSize: 12,
                          cursor: 'pointer',
                          minHeight: isMobile ? 44 : undefined,
                          touchAction: 'manipulation',
                          WebkitTapHighlightColor: 'transparent' as any,
                        }}
                        title="Download JSON"
                      >
                        ⬇️ JSON
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Prompt Preview Box */}
              <div
                style={{
                  background: '#090d13',
                  border: '1px solid #21262d',
                  borderRadius: 6,
                  padding: isMobile ? 10 : 14,
                  maxHeight: isMobile ? 300 : 440,
                  overflow: 'auto',
                  fontFamily: 'ui-monospace, monospace',
                  fontSize: isMobile ? 10 : 11,
                  lineHeight: 1.5,
                  color: '#c9d1d9',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {llmPrompt}
              </div>
            </div>
          )}
        </div>

        {/* Footer — sticky so Close always reachable on phone */}
        <footer
          style={{
            padding: isMobile ? '8px 12px max(12px, env(safe-area-inset-bottom))' : '10px 18px',
            borderTop: '1px solid #21262d',
            background: '#161b22',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: isMobile ? 10.5 : 11,
            color: '#8b949e',
            position: isMobile ? ('sticky' as const) : undefined,
            bottom: isMobile ? 0 : undefined,
            flexShrink: 0,
          }}
        >
          <span>{isMobile ? t('history.synthesizedMobile') : t('history.synthesized')}</span>
          <button
            onClick={onClose}
            style={{
              padding: isMobile ? '10px 16px' : '6px 16px',
              background: '#21262d',
              border: '1px solid #30363d',
              borderRadius: 6,
              color: '#c9d1d9',
              cursor: 'pointer',
              fontSize: isMobile ? 11 : 12,
              minHeight: isMobile ? 44 : undefined,
              touchAction: 'manipulation',
              WebkitTapHighlightColor: 'transparent' as any,
            }}
          >
            {t('history.close')}
          </button>
        </footer>
      </div>
    </div>
  )
}
