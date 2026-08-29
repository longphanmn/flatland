import { useCallback, useEffect, useRef, useState } from 'react'
import CanvasRenderer, { CASTE_COLORS } from './render/CanvasRenderer'
import CasteChart from './render/CasteChart'
import TrophicChart from './render/TrophicChart'
import ClanPanel from './render/ClanPanel'
import PlotsPanel from './render/PlotsPanel'
import Collapsible from './render/Collapsible'
import ChronicleFeed from './render/ChronicleFeed'
import GodPanel from './god/GodPanel'
import { AuthModal, ensureGodKey, forgetKey, getCachedKey } from './god/auth'
import Wiki from './wiki/Wiki'
import ClanDetails from './clan/ClanDetails'
import WorldEndSummary from './summary/WorldEndSummary'
import WorldHistoryModal from './history/WorldHistoryModal'
import Inspector from './inspect/Inspector'
import { WorldSocket, type ConnStatus } from './websocket'
import type { HelloMessage, HistoryEvent, StateMessage, WorldSummary } from './types'
import { useI18n } from './i18n'
import ConfirmModal from './components/ConfirmModal'

const SPEEDS = [1, 5, 10, 20, 40]
const HISTORY_PAGE = 200
const MAX_LOG = 600

const STATUS_LABEL: Record<ConnStatus, string> = {
  connecting: 'connecting',
  open: 'live',
  closed: 'reconnecting…',
}

const eventKey = (ev: HistoryEvent) => `${ev.tick}:${ev.entity_id}:${ev.type}`

/** Newest-first: later ticks on top, insertion id as tiebreak (live rows have none). */
const newestFirst = (a: HistoryEvent, b: HistoryEvent) =>
  b.tick - a.tick || (b.id ?? 0) - (a.id ?? 0)

/** "2026-08-22T06:47:01+00:00" → "06:47" for compact run labels. */
const fmtStart = (iso: string) => iso.slice(11, 16) || iso

export default function App() {
  const { t, lang, setLang } = useI18n()
  const [status, setStatus] = useState<ConnStatus>('connecting')
  const [hello, setHello] = useState<HelloMessage | null>(null)
  const [state, setState] = useState<StateMessage | null>(null)
  const [paused, setPaused] = useState(false)
  const [speed, setSpeed] = useState(10)
  const [godOpen, setGodOpen] = useState(false)
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false)
  const [chronicleOpen, setChronicleOpen] = useState(() => {
    if (typeof window !== 'undefined' && window.innerWidth <= 768) return false
    return true
  })
  const [helpOpen, setHelpOpen] = useState(false)
  const [wikiOpen, setWikiOpen] = useState(false)
  const [worldHistoryOpen, setWorldHistoryOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.innerWidth <= 768)
  const [statusExpanded, setStatusExpanded] = useState(false)
  const [sheetState, setSheetState] = useState<'hidden' | 'peek' | 'half' | 'full'>('hidden')
  const [sheetTab, setSheetTab] = useState<'world' | 'clans' | 'chronicle' | 'plots'>('world')
  const [versionInfo, setVersionInfo] = useState<{ version: string; revision: string } | null>(null)
  const [log, setLog] = useState<HistoryEvent[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedClanId, setSelectedClanId] = useState<number | null>(null)
  const [showWorldEnd, setShowWorldEnd] = useState(false)
  const [aliveHist, setAliveHist] = useState<number[]>([])
  const [popHist, setPopHist] = useState<Array<Record<string, number>>>([])
  const [worlds, setWorlds] = useState<WorldSummary[]>([])
  /** null = follow the live run; a number = pinned to that (past) run. */
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [noMoreHistory, setNoMoreHistory] = useState(false)

  /** §Y clan display name from live state, falling back to bare #id. */
  const clanLabel = (id?: number | null): string => {
    if (id == null) return '#?'
    return state?.clans?.[String(id)]?.name ?? `#${id}`
  }

  const stateRef = useRef<StateMessage | null>(null)
  const sockRef = useRef<WorldSocket | null>(null)
  const seenEventsRef = useRef(new Set<string>())
  const selectedRef = useRef<number | null>(null)
  const selectedClanRef = useRef<number | null>(null)
  const archiveModeRef = useRef(false)

  const oldestLoadedRef = useRef<number | null>(null)
  const fetchedByIdRef = useRef(new Map<string, HistoryEvent>())
  const seededRef = useRef(false)
  const loadingOlderRef = useRef(false)
  const prevTickRef = useRef<number | null>(null)
  const prevSeedRef = useRef<number | null>(null)
  const lastUiUpdateRef = useRef<number>(0)
  const queuedEventsRef = useRef<HistoryEvent[]>([])
  const [estTps, setEstTps] = useState<number | null>(null)
  const lastTpsTimeRef = useRef<number>(0)
  const lastTpsTickRef = useRef<number | null>(null)
  useEffect(() => {
    selectedRef.current = selectedId
  }, [selectedId])
  useEffect(() => {
    selectedClanRef.current = selectedClanId
  }, [selectedClanId])

  const liveWorld = worlds.find((w) => w.ended_at === null)
  const liveWorldId = liveWorld?.id ?? null
  const archiveMode = selectedRunId !== null && selectedRunId !== liveWorldId

  useEffect(() => {
    archiveModeRef.current = archiveMode
  }, [archiveMode])

  useEffect(() => {
    fetch('/api/version')
      .then((r) => r.json())
      .then((d) => setVersionInfo({ version: d.version ?? '0.1.2', revision: d.revision ?? '' }))
      .catch(() => setVersionInfo({ version: '0.1.2', revision: '' }))
  }, [])

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth <= 768)
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)
  // Custom tooltip for HUD chips and law hints — works on hover (desktop) and tap (mobile)
  useEffect(() => {
    let hideTimer: number | null = null
    const show = (el: HTMLElement, x: number, y: number) => {
      const txt = el.getAttribute('title') || el.getAttribute('data-hint')
      if (!txt) return
      // suppress native title
      el.setAttribute('data-title', txt)
      el.removeAttribute('title')
      setTooltip({ text: txt, x, y })
      if (hideTimer) window.clearTimeout(hideTimer)
    }
    const hide = (el: HTMLElement) => {
      const orig = el.getAttribute('data-title')
      if (orig) {
        el.setAttribute('title', orig)
        el.removeAttribute('data-title')
      }
      if (hideTimer) window.clearTimeout(hideTimer)
      hideTimer = window.setTimeout(() => setTooltip(null), 120) as unknown as number
    }
    const onEnter = (e: Event) => {
      const raw = e.target as HTMLElement | null
      if (!raw || !(raw instanceof Element)) return
      const chip = raw.closest('[title], [data-hint]') as HTMLElement | null
      if (!chip) return
      const rect = chip.getBoundingClientRect()
      show(chip, rect.left + rect.width / 2, rect.top)
    }
    const onLeave = (e: Event) => {
      const raw = e.target as HTMLElement | null
      if (!raw || !(raw instanceof Element)) return
      const chip = raw.closest('[title], [data-hint]') as HTMLElement | null
      if (chip) hide(chip)
      else setTooltip(null)
    }
    const onClick = (e: Event) => {
      const raw = e.target as HTMLElement | null
      if (!raw || !(raw instanceof Element)) return
      const chip = raw.closest('.hud [title], .hud [data-hint], .chip[data-hint]') as HTMLElement | null
      if (chip && !chip.closest('button, select, input, a, .collapsible-head, .right-stack')) {
        const txt = chip.getAttribute('title') || chip.getAttribute('data-hint') || chip.getAttribute('data-title')
        if (txt) {
          const rect = chip.getBoundingClientRect()
          setTooltip({ text: txt, x: rect.left + rect.width / 2, y: rect.top })
          if (hideTimer) window.clearTimeout(hideTimer)
          hideTimer = window.setTimeout(() => setTooltip(null), 2800) as unknown as number
        }
      }
    }
    document.addEventListener('mouseenter', onEnter, true)
    document.addEventListener('mouseleave', onLeave, true)
    document.addEventListener('mousemove', (e: MouseEvent) => {
      if (tooltip) {
        const raw = e.target as HTMLElement | null
        if (!raw || !(raw instanceof Element)) return
        const t = raw.closest('[title], [data-hint]') as HTMLElement | null
        if (t) {
          const rect = t.getBoundingClientRect()
          setTooltip((prev) => prev ? { ...prev, x: rect.left + rect.width / 2, y: rect.top } : prev)
        }
      }
    })
    document.addEventListener('click', onClick, false)
    return () => {
      document.removeEventListener('mouseenter', onEnter, true)
      document.removeEventListener('mouseleave', onLeave, true)
      document.removeEventListener('click', onClick, false)
      if (hideTimer) window.clearTimeout(hideTimer)
    }
  }, [tooltip])

  const refreshWorlds = useCallback(async () => {
    try {
      const d = await fetch('/api/worlds').then((r) => r.json())
      setWorlds(Array.isArray(d.worlds) ? d.worlds : [])
    } catch {
      // backend briefly unreachable — keep previous list
    }
  }, [])

  useEffect(() => {
    refreshWorlds()
  }, [refreshWorlds])

  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const sock = new WorldSocket(`${proto}://${location.host}/ws`, {
      onStatus: setStatus,
      onAuthError: () => {
        // the stored passkey stopped working (db reset, wrong world) — re-ask next time
        forgetKey()
      },
      onHello: (msg) => {
        setHello(msg)
        setSpeed(msg.tick_rate)
        refreshWorlds()
      },
      onState: (msg) => {
        // New world detection: tick reset or seed change → clear chronicle
        const isNewWorld =
          (prevTickRef.current !== null && msg.tick < prevTickRef.current) ||
          (prevSeedRef.current !== null && msg.seed !== prevSeedRef.current)
        if (isNewWorld && !archiveModeRef.current) {
          setLog([])
          setAliveHist([])
          setPopHist([])
          seenEventsRef.current.clear()
          fetchedByIdRef.current.clear()
          oldestLoadedRef.current = null
          seededRef.current = false
          setNoMoreHistory(false)
          refreshWorlds()
        }
        prevTickRef.current = msg.tick
        prevSeedRef.current = msg.seed
        stateRef.current = msg

        // Estimate true ticks/s from WS stream (wall-clock), independent of UI throttle
        {
          const nowMs = performance.now()
          if (lastTpsTickRef.current !== null && lastTpsTimeRef.current) {
            const dt = (nowMs - lastTpsTimeRef.current) / 1000
            const dTick = msg.tick - (lastTpsTickRef.current ?? msg.tick)
            if (dt >= 0.5 && dTick > 0) {
              const tps = dTick / dt
              setEstTps(Math.round(tps * 10) / 10)
              lastTpsTimeRef.current = nowMs
              lastTpsTickRef.current = msg.tick
            }
          } else {
            lastTpsTimeRef.current = nowMs
            lastTpsTickRef.current = msg.tick
          }
          // Reset on new world
          if (isNewWorld) {
            lastTpsTimeRef.current = nowMs
            lastTpsTickRef.current = msg.tick
            setEstTps(null)
          }
        }

        // AF: Throttle React virtual DOM re-renders to ~10 Hz (every 100ms) so HUD tick
        // appears at true rate (was 200ms → 5Hz, looked like 2 ticks/s when counting updates).
        // CanvasRenderer continues to read stateRef.current at full 60 FPS.
        const now = performance.now()
        const isExtinct = msg.creatures_alive === 0
        const shouldUpdateReactState =
          isNewWorld ||
          isExtinct ||
          now - (lastUiUpdateRef.current || 0) >= 100

        if (!archiveModeRef.current && msg.events && msg.events.length > 0) {
          for (const ev of msg.events) {
            const key = eventKey(ev)
            if (!seenEventsRef.current.has(key)) {
              seenEventsRef.current.add(key)
              queuedEventsRef.current.push(ev)
            }
          }
        }

        if (shouldUpdateReactState) {
          lastUiUpdateRef.current = now
          setState(msg)
          setAliveHist((prev) =>
            isNewWorld && !archiveModeRef.current
              ? [msg.creatures_alive]
              : [...prev.slice(-119), msg.creatures_alive],
          )
          setPopHist((prev) =>
            isNewWorld && !archiveModeRef.current
              ? [msg.population]
              : [...prev.slice(-239), msg.population],
          )
          if (!archiveModeRef.current && queuedEventsRef.current.length > 0) {
            const batch = queuedEventsRef.current.splice(0)
            setLog((prev) => [...batch.reverse(), ...prev].slice(0, MAX_LOG))
          }
        }
      },

    })
    sock.connect()
    sockRef.current = sock
    return () => sock.dispose()
  }, [])

  // World end detection — extinction summary & pause
  useEffect(() => {
    if (state && state.creatures_alive === 0 && state.tick > 30 && !showWorldEnd && !archiveMode) {
      setShowWorldEnd(true)
      setPaused(true)
    }
    if (state && state.creatures_alive > 0 && showWorldEnd) {
      setShowWorldEnd(false)
    }
  }, [state?.creatures_alive, state?.tick, showWorldEnd, archiveMode])

  const sendControl = useCallback(async (action: 'pause' | 'resume' | 'step' | 'reset', after?: () => void) => {
    const key = await ensureGodKey()
    if (!key) return // cancelled dialog — world untouched
    sockRef.current?.send({ action, key })
    after?.()
  }, [])
  const sendPause = useCallback(() => {
    void sendControl('pause', () => setPaused(true))
  }, [sendControl])
  const sendResume = useCallback(() => {
    void sendControl('resume', () => setPaused(false))
  }, [sendControl])
  const sendStep = useCallback(() => void sendControl('step'), [sendControl])
  const sendReset = useCallback(() => void sendControl('reset'), [sendControl])
  const confirmReset = useCallback(() => setResetConfirmOpen(true), [])
  const doReset = useCallback(() => void sendControl('reset'), [sendControl])
  const changeSpeed = useCallback(
    (v: number) => {
      setSpeed(v)
      void ensureGodKey().then((key) => {
        if (!key) return
        sockRef.current?.send({ action: 'set_speed', value: v, key })
      })
    },
    [],
  )

  // Keyboard controls: space pause · S step · R reset · +/- zoom · F fit.
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement | null
      if (t && ['INPUT', 'SELECT', 'TEXTAREA'].includes(t.tagName)) return
      switch (ev.code) {
        case 'Space':
          ev.preventDefault()
          setPaused((p) => {
            void sendControl(p ? 'resume' : 'pause', () => setPaused(!p))
            return !p
          })
          break
        case 'KeyS':
          sendStep()
          break
        case 'KeyR':
          confirmReset()
          break
        case 'KeyH':
          setWorldHistoryOpen((o) => !o)
          break
        case 'KeyF':
          window.dispatchEvent(new Event('flatworld-fit'))
          break
        case 'Equal':
        case 'NumpadAdd':
          window.dispatchEvent(new CustomEvent('flatworld-zoom', { detail: { factor: 1.25 } }))
          break
        case 'Minus':
        case 'NumpadSubtract':
          window.dispatchEvent(new CustomEvent('flatworld-zoom', { detail: { factor: 0.8 } }))
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [sendControl, sendStep, sendReset, confirmReset])


  /** Merge fetched (id-bearing) events into the log newest-first, deduped by tick+entity_id+type. */
  const mergeFetched = useCallback((fetched: HistoryEvent[]) => {
    if (fetched.length === 0) return
    let minId: number | null = null
    for (const ev of fetched) {
      if (typeof ev.id === 'number') {
        fetchedByIdRef.current.set(String(ev.id), ev)
        if (minId === null || ev.id < minId) minId = ev.id
      }
      // Register keys so a later live rebroadcast of the same window is dropped.
      seenEventsRef.current.add(eventKey(ev))
    }
    if (minId !== null && (oldestLoadedRef.current === null || minId < oldestLoadedRef.current)) {
      oldestLoadedRef.current = minId
    }
    setLog((prev) => {
      const byKey = new Map<string, HistoryEvent>()
      for (const ev of fetched) byKey.set(eventKey(ev), ev)
      for (const ev of prev) {
        const k = eventKey(ev)
        if (!byKey.has(k)) byKey.set(k, ev)
      }
      return [...byKey.values()].sort(newestFirst).slice(0, MAX_LOG)
    })
  }, [])

  useEffect(() => {
    const shouldFetchChronicle = chronicleOpen || (isMobile && sheetTab === 'chronicle' && sheetState !== 'hidden')
    if (!shouldFetchChronicle || archiveMode || seededRef.current) return
    seededRef.current = true
    fetch(`/api/history?limit=${HISTORY_PAGE}`)
      .then((r) => r.json())
      .then((d) => mergeFetched(Array.isArray(d.events) ? d.events : []))
      .catch(() => {})
  }, [chronicleOpen, isMobile, sheetTab, sheetState, archiveMode, mergeFetched])

  const loadOlder = useCallback(async () => {
    const since = oldestLoadedRef.current
    if (since === null || loadingOlderRef.current) return
    loadingOlderRef.current = true
    setLoadingOlder(true)
    try {
      const d = await fetch(`/api/history?since=${since}&limit=${HISTORY_PAGE}`).then((r) =>
        r.json(),
      )
      const events: HistoryEvent[] = Array.isArray(d.events) ? d.events : []
      if (events.length === 0) setNoMoreHistory(true)
      else mergeFetched(events)
    } catch {
      // transient failure — button stays usable for a retry
    } finally {
      loadingOlderRef.current = false
      setLoadingOlder(false)
    }
  }, [mergeFetched])

  const selectRun = useCallback(
    async (raw: string) => {
      const key = await ensureGodKey()
      if (!key) return
      const id = Number(raw)
      // Picking the live run canonicalizes back to follow-live mode.
      setSelectedRunId(id === liveWorldId ? null : id)
    },
    [liveWorldId],
  )


  const populationEntries = state
    ? Object.entries(state.population).sort(([a], [b]) => a.localeCompare(b))
    : []
  const creatureEntries = populationEntries.filter(([k]) => k in CASTE_COLORS)
  const objectEntries = populationEntries.filter(([k]) => !(k in CASTE_COLORS))

  const hungryCount = state?.entities.filter((e) => e.status === 'hungry').length ?? 0
  const starvingCount = state?.entities.filter((e) => e.status === 'starving').length ?? 0
  const chilledCount = state?.entities.filter((e) => (e.chill ?? 0) >= 12).length ?? 0
  const deadBreakdown = state
    ? Object.entries(state.dead_by_cause)
        .sort((a, b) => b[1] - a[1])
        .map(([cause, n]) => `${cause}: ${n}`)
        .join(' · ') || 'no deaths yet'
    : ''

  const isNight = state ? state.time_of_day < 0.22 || state.time_of_day > 0.78 : false
  const raining = state?.weather === 'rain' || state?.weather === 'storm'
  const exposedCount = raining
    ? (state?.entities.filter(
        (e) => e.kind === 'creature' && e.sleeping === false && e.indoors === false && e.infected === false,
      ).length ?? 0)
    : 0
  const weatherIcon =
    state?.weather === 'rain' ? '🌧' : state?.weather === 'fog' ? '🌫' : state?.weather === 'storm' ? '⛈' : ''
  const ageDay = state?.age_day ?? (state?.age_tick !== undefined ? Math.floor(state.age_tick / 1200) + 1 : 1)
  const ageTotalDays = state?.age_total_days ?? 10

  return (
    <div className="app">
      <header className={`hud ${isMobile ? 'hud-compact' : ''}`} onClick={isMobile ? () => setStatusExpanded(o => !o) : undefined} style={isMobile ? { cursor: 'pointer' } : undefined}>
        <span className="title">{t('app.title')}</span>
        <select value={lang} onChange={e => setLang(e.target.value as any)} onClick={e => e.stopPropagation()} style={{ background: '#161b22', color: '#c9d1d9', border: '1px solid #30363d', borderRadius: 6, padding: '2px 6px', fontSize: 11, cursor: 'pointer' }} title={t('common.language')}>
          <option value="en">EN</option>
          <option value="fr">FR</option>
          <option value="vi">VI</option>
        </select>
        <span className={`dot ${status}`} title={`Connection: ${STATUS_LABEL[status]}`} data-hint={`Connection: ${STATUS_LABEL[status]}`} />
        {status !== 'open' && <span className="chip" style={{ color: status === 'connecting' ? '#d29922' : '#f85149' }}>{STATUS_LABEL[status]}</span>}
        {paused && <span className="chip paused">PAUSED</span>}
        {state && (
          <span className="chip" title={`Time of day ${state.time_of_day} — night (0-0.22, 0.78-1) dims sight 0.6×, fog 0.6× stack; season ${state.season} changes Food target and disease. Weather ${state.weather}: rain slows 0.85×, storm adds wander.`}>
            {isNight ? '🌙' : '☀'} day <b>{state.day}</b> · {state.season}
            {weatherIcon && ` · ${weatherIcon}`}
          </span>
        )}
        <span className="chip" title="Current tick — simulation step count (10 ticks/s by default). Est TPS is wall-clock measured from WS stream; if it drops below target, healthz avg_tick_ms shows overrun.">
          tick <b>{state?.tick ?? 0}</b>{estTps !== null && ` · ${estTps} t/s`}
        </span>
        <span
          className="chip alive"
          title={`Alive: ${state?.creatures_alive ?? 0} creatures — Flatland castes + Predators + Herbivores. Hover Caste chart for breakdown.`}
          data-hint={`Alive: ${state?.creatures_alive ?? 0} creatures`}
        >
          💚 <b>{state?.creatures_alive ?? 0}</b>
        </span>
        <span
          className="chip dead desktop-only"
          title={`Dead: ${state?.creatures_dead ?? 0} — ${deadBreakdown} (hover for per-cause breakdown: starvation/old_age/euthanasia/disease/predation/war/poison).`}
          data-hint={`Dead: ${state?.creatures_dead ?? 0} creatures (${deadBreakdown})`}
        >
          💀 <b>{state?.creatures_dead ?? 0}</b>
        </span>
        {hungryCount > 0 && (
          <span
            className="chip hungry desktop-only"
            title={`Hungry: ${hungryCount} creatures (energy ≤ 35% of max) — perceives food farther (1.3×), still fertile.`}
            data-hint={`Hungry: ${hungryCount} creatures`}
          >
            🍖 <b>{hungryCount}</b>
          </span>
        )}
        {starvingCount > 0 && (
          <span
            className="chip starving desktop-only"
            title={`Starving: ${starvingCount} creatures (energy ≤ 15%) — sees farthest (1.6×) and moves 1.35× faster, pulsing red, will die soon.`}
            data-hint={`Starving: ${starvingCount} creatures`}
          >
            ⚠️ <b>{starvingCount}</b>
          </span>
        )}
        {(state?.infected_count ?? 0) > 0 && (
          <span
            className="chip sick desktop-only"
            title={`Infected: ${state?.infected_count} creatures — loses 0.15 energy/tick + 1.0 health/tick (winter ×1.5 spread), green pulsing ring, may recover.`}
            data-hint={`Infected: ${state?.infected_count} creatures`}
          >
            ☣️ <b>{state?.infected_count}</b>
          </span>
        )}
        {chilledCount > 0 && (
          <span
            className="chip desktop-only"
            style={{ color: '#79c0ff' }}
            title={`Chilled: ${chilledCount} creatures — built rain/storm/winter-night outside, past 12 drains health 0.18/tick. Shelter sheds 2.5× faster.`}
            data-hint={`Chilled: ${chilledCount} creatures`}
          >
            🥶 <b>{chilledCount}</b>
          </span>
        )}
        {raining && exposedCount > 0 && (
          <span
            className="chip exposed desktop-only"
            title={`Exposed: ${exposedCount} creatures — awake, outdoors, not in a House during rain/storm or winter night (loses 0.03 energy/tick extra).`}
            data-hint={`Exposed: ${exposedCount} creatures`}
          >
            ⛈ <b>{exposedCount}</b>
          </span>
        )}
        {state && state.age && (
          <span
            className="chip desktop-only"
            title={`Age ${state.age} — super-season bending world: Ice (food×0.55 chill×1.4), Chaos (mutation×1.8), Plague (disease×1.8), Golden (food×1.25 birth×1.3). Day ${ageDay} of ${ageTotalDays} in this age.`}
            data-hint={`Age ${state.age} · Day ${ageDay}/${ageTotalDays}`}
          >
            🗓 age <b>{state.age}</b> · day {ageDay}/{ageTotalDays}
          </span>
        )}

        {isMobile && <span className="chip" style={{ marginLeft: 'auto', fontSize: 10, color: '#58a6ff' }}>{statusExpanded ? '▲ Close' : '▼ More'}</span>}

        <div className="top-right-panel">
          <button className="god-btn" onClick={() => setWorldHistoryOpen(true)} title="World History & AI Story Export (H)" data-hint="World History & AI Story Export (H)">
            📜
          </button>
          <button className="god-btn wiki-btn" onClick={() => setWikiOpen(true)} title="Wiki — documentation & API ( /wiki )" data-hint="Wiki — documentation & API ( /wiki )">
            📖
          </button>
          <button className="god-btn god-main-btn" onClick={() => setGodOpen(true)} title="The Sphere (God) — sets laws from Spaceland, never touches a life" data-hint="The Sphere (God) — sets laws from Spaceland, never touches a life">
            ⚖
          </button>
        </div>
      </header>
      {isMobile && statusExpanded && (
        <div className="hud-detail-sheet" onClick={(e) => { if ((e.target as HTMLElement).tagName !== 'SELECT' && (e.target as HTMLElement).tagName !== 'BUTTON') setStatusExpanded(false); }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#e6edf3' }}>World Details & Navigation</span>
            <button onClick={() => setStatusExpanded(false)} style={{ background: 'transparent', border: 'none', color: '#8b949e', fontSize: 16, cursor: 'pointer', padding: 0, minHeight: 24 }}>✕</button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            <span className="chip">entities <b>{state?.entities.length ?? 0}</b></span>
            <span className="chip dead">dead <b>{state?.creatures_dead ?? 0}</b></span>
            <span className="chip" style={{ fontSize: 10, color: '#8b949e' }}>{deadBreakdown}</span>
            {(state?.infected_count ?? 0) > 0 && <span className="chip sick">infected <b>{state?.infected_count}</b></span>}
            {(state?.entities.filter((e) => (e.chill ?? 0) >= 12).length ?? 0) > 0 && <span className="chip" style={{ color: '#79c0ff' }}>🥶 chilled <b>{state?.entities.filter((e) => (e.chill ?? 0) >= 12).length}</b></span>}
            {raining && exposedCount > 0 && <span className="chip exposed">⛈ exposed <b>{exposedCount}</b></span>}
            {hello && <span className="chip">seed <b>{state?.seed ?? hello.seed}</b> · {state?.width ?? hello.width}×{state?.height ?? hello.height} · {state?.boundary ?? hello.boundary}</span>}
            {state?.age && <span className="chip">🗓 age <b>{state.age}</b> · day {ageDay}/{ageTotalDays}</span>}
            <span className="chip">hungry <b>{hungryCount}</b> · starving <b>{starvingCount}</b></span>
          </div>
          {worlds.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6, paddingTop: 6, borderTop: '1px solid #21262d' }}>
              <span style={{ fontSize: 12, color: '#8b949e', flex: 'none' }}>⚖ History Run (The Sphere):</span>
              <select
                className="run-select"
                value={String(selectedRunId ?? liveWorldId ?? '')}
                onPointerDown={async (e) => {
                  if (!getCachedKey()) {
                    e.preventDefault()
                    await ensureGodKey()
                  }
                }}
                onChange={(e) => void selectRun(e.target.value)}
                style={{ flex: 1, minHeight: 32, fontSize: 12 }}
              >
                {worlds.map((w) => (
                  <option key={w.id} value={String(w.id)}>
                    #{w.id} · seed {w.seed} · {fmtStart(w.started_at)}
                    {w.ended_at === null ? ' · (live)' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button className="god-btn" onClick={() => { setStatusExpanded(false); setWorldHistoryOpen(true); }} style={{ flex: 1, minHeight: 34, fontSize: 12 }}>
              📜 History
            </button>
            <button className="god-btn" onClick={() => { setStatusExpanded(false); setWikiOpen(true); }} style={{ flex: 1, minHeight: 34, fontSize: 12 }}>
              📖 Wiki
            </button>
            <button className="god-btn god-main-btn" onClick={() => { setStatusExpanded(false); setGodOpen(true); }} style={{ flex: 1, minHeight: 34, fontSize: 12 }}>
              ⚖ The Sphere
            </button>

            <button className="god-btn" onClick={() => { setStatusExpanded(false); confirmReset(); }} style={{ flex: 1, minHeight: 34, fontSize: 12, borderColor: '#f85149', color: '#ff7b72' }} title="Reset world with new seed (R)">
              🔄 Reset
            </button>
          </div>
        </div>
      )}

      <main className="stage">
        <CanvasRenderer
          stateRef={stateRef}
          selectedRef={selectedRef}
          selectedClanRef={selectedClanRef}
          onTapCreature={(id) => {
            setSelectedId(id)
            if (id === null) {
              setSelectedClanId(null)
            }
          }}
        />
      </main>

      {/* Mobile thumb bar — persistent 48px */}
      {isMobile && (
        <div className="mobile-thumb-bar">
          <button onClick={paused ? sendResume : sendPause} title={paused ? 'Resume (space)' : 'Pause (space)'}>{paused ? '▶' : '⏸'}</button>
          <button onClick={sendStep} title="Step (S)">⏭</button>
          <button onClick={confirmReset} title="Reset world with new seed (R)" style={{ color: '#ff7b72' }}>🔄</button>
          <button onClick={() => setGodOpen(true)} title="Laws of the Sphere (God)">⚖</button>
          <button

            className={sheetState !== 'hidden' ? 'active-sheet-btn' : ''}
            onClick={() => {
              if (sheetState === 'hidden') {
                setSheetTab('chronicle')
                setSheetState('half')
              } else {
                setSheetState('hidden')
              }
            }}
            title="Toggle stats & log sheet"
          >
            📊
          </button>
          <button onClick={() => window.dispatchEvent(new Event('flatworld-fit'))} title="Fit view (F)">⛶</button>
          <select value={speed} onChange={e => changeSpeed(Number(e.target.value))} title="ticks/s">
            {SPEEDS.map(v => <option key={v} value={v}>{v}t/s</option>)}
          </select>
        </div>
      )}

      {/* Mobile tabbed sheet — World / Clans / Chronicle / Plots */}
      {isMobile && sheetState !== 'hidden' && (
        <div className="mobile-sheet" data-state={sheetState}>
          <div
            className="mobile-sheet-handle"
            onClick={() => setSheetState(s => s === 'peek' ? 'half' : s === 'half' ? 'full' : 'peek')}
            onTouchStart={e => {
              const startY = e.touches[0].clientY
              const startState = sheetState
              const onMove = (ev: TouchEvent) => {
                const dy = ev.touches[0].clientY - startY
                if (dy < -30 && startState === 'peek') setSheetState('half')
                else if (dy < -30 && startState === 'half') setSheetState('full')
                else if (dy > 30 && startState === 'full') setSheetState('half')
                else if (dy > 30 && startState === 'half') setSheetState('peek')
                else if (dy > 30 && startState === 'peek') setSheetState('hidden')
              }
              const onEnd = () => {
                window.removeEventListener('touchmove', onMove as any)
                window.removeEventListener('touchend', onEnd as any)
              }
              window.addEventListener('touchmove', onMove as any, { passive: true })
              window.addEventListener('touchend', onEnd as any)
            }}
          />
          <div className="mobile-sheet-header">
            <div className="mobile-sheet-tabs">
              <button className={sheetTab === 'world' ? 'active' : ''} onClick={() => setSheetTab('world')}>World</button>
              <button className={sheetTab === 'clans' ? 'active' : ''} onClick={() => setSheetTab('clans')}>Clans</button>
              <button className={sheetTab === 'chronicle' ? 'active' : ''} onClick={() => setSheetTab('chronicle')}>Log</button>
              <button className={sheetTab === 'plots' ? 'active' : ''} onClick={() => setSheetTab('plots')}>Plots</button>
            </div>
            <button
              className="mobile-sheet-close"
              onClick={(e) => {
                e.stopPropagation()
                e.preventDefault()
                setSheetState('hidden')
              }}
              title="Hide sheet"
              aria-label="Close bottom sheet"
            >
              ✕
            </button>
          </div>
          <div className="mobile-sheet-body">
            {sheetTab === 'world' && (
              <>
                <h3 className="chronicle-title">Overview<span className="chronicle-pop">{creatureEntries.map(([k,v],i)=>(<span key={k} className="pop-chip"><span className="dot-inline" style={{background:CASTE_COLORS[k]??'#8b949e'}}/>{k} <b>{v}</b>{(i<creatureEntries.length-1||objectEntries.length>0)&&' · '}</span>))}{objectEntries.map(([k,v],i)=>(<span key={k} className="pop-chip">{k} <b>{v}</b>{i<objectEntries.length-1&&' · '}</span>))}</span></h3>
                <CasteChart history={popHist} showLegend={false} />
                <div style={{ fontSize: 11, color: '#8b949e', margin: '6px 0 2px' }}>Alive — recent ticks</div>
                <span className="spark-wrap" style={{ display:'block', width:'100%' }}><svg viewBox="0 0 100 22" className="spark" style={{ width:'100%', height:28 }}>{aliveHist.length>1 && <polyline points={aliveHist.map((v,i)=> `${(i/(aliveHist.length-1))*100},${21-((v-Math.min(...aliveHist))/(Math.max(...aliveHist,1)-Math.min(...aliveHist)||1))*20}`).join(' ')} />}</svg></span>
                <h4 style={{ margin:'10px 0 4px', fontSize:'0.85em', opacity:0.8 }}>Trophic — Food · Herbivore · Predator</h4>
                <TrophicChart history={popHist} showLegend={false} />
              </>
            )}
            {sheetTab === 'clans' && <ClanPanel onSelectClan={setSelectedClanId} onSelectCreature={setSelectedId} />}
            {sheetTab === 'plots' && <PlotsPanel onSelectClan={setSelectedClanId} />}
            {sheetTab === 'chronicle' && (
              <div className="chronicle" style={{ background: 'transparent', border: 'none', padding: 0, maxHeight: 'none' }}>
                <ChronicleFeed
                  events={log}
                  clanLabel={clanLabel}
                  onSelectCreature={(id) => setSelectedId(id)}
                  onSelectClan={(id) => setSelectedClanId(id)}
                  onLoadOlder={loadOlder}
                  loadingOlder={loadingOlder}
                  noMoreHistory={noMoreHistory}
                  archiveMode={archiveMode}
                  selectedRunId={selectedRunId}
                  compact
                />
              </div>
            )}
          </div>
        </div>
      )}

      {!isMobile && (
        <>
          <footer className="controls">
            {paused ? (
              <button onClick={sendResume} title="Resume (Space)" data-hint="Resume (Space)">▶</button>
            ) : (
              <button onClick={sendPause} title="Pause (Space)" data-hint="Pause (Space)">⏸</button>
            )}
            <button onClick={sendStep} title="Step (S)" data-hint="Step (S)">⏭</button>
            <button onClick={confirmReset} title="Reset (R)" data-hint="Reset (R)">🔄</button>
            <button onClick={() => window.dispatchEvent(new Event('flatworld-fit'))} title="Fit view (F)" data-hint="Fit view (F)">
              ⛶
            </button>
            <button onClick={() => setChronicleOpen((o) => !o)} title={chronicleOpen ? 'Hide chronicle' : 'Show chronicle'} data-hint={chronicleOpen ? 'Hide chronicle' : 'Show chronicle'}>
              {chronicleOpen ? '▤' : '📜'}
            </button>
            <label className="chip" htmlFor="speed" title="ticks per second" data-hint="ticks per second">
              ⚡
            </label>
            <select
              id="speed"
              value={speed}
              onChange={(e) => changeSpeed(Number(e.target.value))}
              title="ticks/s"
              data-hint="ticks/s"
            >
              {SPEEDS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
            {worlds.length > 0 && (
              <div className="run-switcher">
                <label className="chip run-label" htmlFor="run-bottom" title="Select world run (The Sphere)" data-hint="Select world run (The Sphere)">
                  ⚖ run
                  <select
                    id="run-bottom"
                    className="run-select"
                    value={String(selectedRunId ?? liveWorldId ?? '')}
                    onPointerDown={async (e) => {
                      if (!getCachedKey()) {
                        e.preventDefault()
                        await ensureGodKey()
                      }
                    }}
                    onChange={(e) => void selectRun(e.target.value)}
                  >
                    {worlds.map((w) => (
                      <option key={w.id} value={String(w.id)}>
                        #{w.id} · seed {w.seed} · {fmtStart(w.started_at)}
                        {w.ended_at === null ? ' · (live)' : ''}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )}

          </footer>

          <p className="key-hints">space pause · S step · R reset · F fit · +/− zoom</p>
        </>
      )}


      {!isMobile && (
        <div
          className="right-stack"
          onPointerDown={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
          onWheel={(e) => e.stopPropagation()}
        >
          <Collapsible id="box-overview" title="Overview" hint="Live population — Caste, Alive spark, Trophic, Plots" defaultOpen={true}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 0', fontSize: 11, color: '#8b949e', marginBottom: 6 }}>
              {creatureEntries.map(([k, v], i) => (
                <span key={k} className="pop-chip" title={`${k}: ${v} alive`}>
                  <span className="dot-inline" style={{ background: CASTE_COLORS[k] ?? '#8b949e' }} />
                  {k} <b>{v}</b>
                  {(i < creatureEntries.length - 1 || objectEntries.length > 0) && ' · '}
                </span>
              ))}
              {objectEntries.map(([k, v], i) => {
                const color = k === 'Food' ? '#3fb950' : k === 'House' ? '#8b949e' : k === 'Corpse' ? '#6e7681' : '#8b949e'
                return (
                  <span key={k} className="pop-chip" title={`${k}: ${v} objects`}>
                    <span className="dot-inline" style={{ background: color }} />
                    {k} <b>{v}</b>
                    {i < objectEntries.length - 1 && ' · '}
                  </span>
                )
              })}
            </div>
            <Collapsible id="overview-caste-v2" title="Caste population" hint="Stacked per-caste population over recent ticks" defaultOpen={true}>
              <CasteChart history={popHist} showLegend={false} />
            </Collapsible>
            <div className="info-spark" title="alive creatures, recent ticks">
              <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: 2 }}>Alive — recent ticks</div>
              <span className="spark-wrap" title="alive creatures, recent ticks">
                <svg viewBox="0 0 100 22" className="spark">
                  {aliveHist.length > 1 && (
                    <polyline
                      points={aliveHist
                        .map(
                          (v, i) =>
                            `${(i / (aliveHist.length - 1)) * 100},${21 - ((v - Math.min(...aliveHist)) / (Math.max(...aliveHist, 1) - Math.min(...aliveHist) || 1)) * 20}`,
                        )
                        .join(' ')}
                    />
                  )}
                </svg>
              </span>
            </div>
            <Collapsible
              id="overview-trophic-v2"
              title={<>Trophic pyramid — Food · Herbivore · Predator <span style={{ fontWeight: 400, opacity: 0.7 }}>(plants → grazers → hunters)</span></>}
              hint="Trophic pyramid: stacked history"
              defaultOpen={true}
            >
              <TrophicChart history={popHist} showLegend={false} />
            </Collapsible>
            <Collapsible id="overview-plots" title="Plots" defaultOpen={true}>
              <PlotsPanel onSelectClan={setSelectedClanId} />
            </Collapsible>
          </Collapsible>
          <Collapsible id="box-clans" title="Clans" hint="Clans — settlements with population, totem and war record" defaultOpen={true}>
            <ClanPanel onSelectClan={setSelectedClanId} onSelectCreature={setSelectedId} />
          </Collapsible>
          <Collapsible id="box-chronicle" title="Chronicle" hint="Event history — births, deaths, wars" defaultOpen={true}>
            <ChronicleFeed
              events={log}
              clanLabel={clanLabel}
              onSelectCreature={(id) => setSelectedId(id)}
              onSelectClan={(id) => setSelectedClanId(id)}
              onLoadOlder={loadOlder}
              loadingOlder={loadingOlder}
              noMoreHistory={noMoreHistory}
              archiveMode={archiveMode}
              selectedRunId={selectedRunId}
            />
          </Collapsible>
        </div>
      )}

      {selectedId !== null && (
        <Inspector
          id={selectedId}
          onClose={() => setSelectedId(null)}
          onNavigate={(nid) => setSelectedId(nid)}
          onSelectClan={(cid) => setSelectedClanId(cid)}
        />
      )}

      <GodPanel open={godOpen} onClose={() => setGodOpen(false)} />
      <Wiki open={wikiOpen} onClose={() => setWikiOpen(false)} />
      {selectedClanId !== null && (
        <ClanDetails clanId={selectedClanId} onClose={() => setSelectedClanId(null)} onSelectCreature={(id) => { setSelectedClanId(null); setSelectedId(id) }} />
      )}
      {showWorldEnd && state && (
        <WorldEndSummary
          state={state}
          onReset={() => { sendReset(); setShowWorldEnd(false) }}
          onClose={() => setShowWorldEnd(false)}
          onOpenWorldHistory={() => setWorldHistoryOpen(true)}
        />
      )}
      <WorldHistoryModal
        open={worldHistoryOpen}
        onClose={() => setWorldHistoryOpen(false)}
        state={state}
        worlds={worlds}
        selectedRunId={selectedRunId}
        onSelectClan={setSelectedClanId}
        onSelectCreature={setSelectedId}
      />
      <ConfirmModal open={resetConfirmOpen} onClose={() => setResetConfirmOpen(false)} onConfirm={doReset} />

      {helpOpen && (
        <div className="help-backdrop" onClick={() => setHelpOpen(false)}>
          <div className="help-panel" onClick={(e) => e.stopPropagation()}>
            <header className="god-head">
              <h3>Hints</h3>
              <button className="god-close" onClick={() => setHelpOpen(false)}>×</button>
            </header>
            <p className="god-note">Tap any chip to see its hint. The Sphere (God) sets universal laws from Spaceland, never touching a single life.</p>
            <ul>
              <li><b>tick</b>: step count, 10/s by default, same seed ⇒ same world</li>
              <li><b>entities</b>: creatures + Food plants + Houses + Corpses</li>
              <li><b>alive/dead</b>: alive castes + predators/herbivores; dead per-cause breakdown on hover/tap</li>
              <li><b>hungry/starving</b>: ≤35%/15% energy, see farther, starving 1.35× speed pulsing red</li>
              <li><b>infected</b>: 0.15 energy +1 health/tick drain, winter 1.5× spread, green ring</li>
              <li><b>exposed</b>: awake outdoors rain/storm/winter night −0.03 energy, shelter scarce</li>
              <li><b>chilled</b>: rain/storm/winter-night builds chill ≥12 → −0.18 health/tick, shelter sheds 2.5×</li>
              <li><b>seed·WxH·boundary</b>: seed determines world, Reset rolls new seed</li>
              <li><b>day/season/weather</b>: night 0.6× sight, fog 0.6×, rain 0.85× speed, storm +wander; seasons change Food target</li>
              <li><b>age</b>: super-season Golden/Ice/Chaos/Plague bends food/mut/disease</li>
              <li><b>Overview</b>: alive spark + caste/trophic graphs + ClanPanel + Plots; Chronicle below is history only (blooms hidden)</li>
              <li><b>Tap creature</b>: works at any zoom (44px hit radius), shows dossier left, gold halo + name glyph</li>
              <li><b>Controls</b>: space pause, S step, R reset, F fit, +/- zoom, drag pan, pinch zoom</li>
            </ul>
          </div>
        </div>
      )}
      {!isMobile && (
        <div className="version-bar" title={versionInfo ? `v${versionInfo.version} · ${versionInfo.revision} · Developed by Long Phan <long@minhnhan.in> · Built with OpenCode & Antigravity` : 'Flatland · Developed by Long Phan <long@minhnhan.in>'}>
          {versionInfo ? `v${versionInfo.version} · ${versionInfo.revision}` : 'v0.1.2'} · <span style={{ opacity: 0.85 }}>Developed by Long Phan · <a href="mailto:long@minhnhan.in" style={{ color: 'inherit', textDecoration: 'underline' }}>long@minhnhan.in</a></span>
        </div>
      )}
      <AuthModal />
    </div>
  )
}
