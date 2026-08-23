import { useCallback, useEffect, useRef, useState } from 'react'
import CanvasRenderer, { CASTE_COLORS } from './render/CanvasRenderer'
import CasteChart from './render/CasteChart'
import TrophicChart from './render/TrophicChart'
import ClanPanel from './render/ClanPanel'
import PlotsPanel from './render/PlotsPanel'
import GodPanel from './god/GodPanel'
import Wiki from './wiki/Wiki'
import ClanDetails from './clan/ClanDetails'
import WorldEndSummary from './summary/WorldEndSummary'
import Inspector from './inspect/Inspector'
import { WorldSocket, type ConnStatus } from './websocket'
import type { HelloMessage, HistoryEvent, StateMessage, WorldSummary } from './types'

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
  const [status, setStatus] = useState<ConnStatus>('connecting')
  const [hello, setHello] = useState<HelloMessage | null>(null)
  const [state, setState] = useState<StateMessage | null>(null)
  const [paused, setPaused] = useState(false)
  const [speed, setSpeed] = useState(10)
  const [godOpen, setGodOpen] = useState(false)
  const [chronicleOpen, setChronicleOpen] = useState(() => {
    if (typeof window !== 'undefined' && window.innerWidth <= 768) return false
    return true
  })
  const [helpOpen, setHelpOpen] = useState(false)
  const [wikiOpen, setWikiOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [statusExpanded, setStatusExpanded] = useState(false)
  const [sheetState, setSheetState] = useState<'peek' | 'half' | 'full'>('peek')
  const [sheetTab, setSheetTab] = useState<'world' | 'clans' | 'chronicle' | 'plots'>('world')
  const [versionInfo, setVersionInfo] = useState<{ version: string; revision: string } | null>(null)
  const [log, setLog] = useState<HistoryEvent[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedClanId, setSelectedClanId] = useState<number | null>(null)
  const [showWorldEnd, setShowWorldEnd] = useState(false)
  const [aliveHist, setAliveHist] = useState<number[]>([])
  const [popHist, setPopHist] = useState<Array<Record<string, number>>>([])
  const [album, setAlbum] = useState<Array<{ id: number; tick: number }>>([])
  const [albumOpen, setAlbumOpen] = useState(false)
  const [viewSnapTick, setViewSnapTick] = useState<number | null>(null)
  const [worlds, setWorlds] = useState<WorldSummary[]>([])
  /** null = follow the live run; a number = pinned to that (past) run. */
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [noMoreHistory, setNoMoreHistory] = useState(false)

  const stateRef = useRef<StateMessage | null>(null)
  const sockRef = useRef<WorldSocket | null>(null)
  const seenEventsRef = useRef(new Set<string>())
  const selectedRef = useRef<number | null>(null)
  const overrideRef = useRef<StateMessage | null>(null)
  const archiveModeRef = useRef(false)
  const oldestLoadedRef = useRef<number | null>(null)
  const fetchedByIdRef = useRef(new Map<string, HistoryEvent>())
  const seededRef = useRef(false)
  const loadingOlderRef = useRef(false)
  const prevTickRef = useRef<number | null>(null)
  const prevSeedRef = useRef<number | null>(null)
  useEffect(() => {
    selectedRef.current = selectedId
  }, [selectedId])

  const liveWorld = worlds.find((w) => w.ended_at === null)
  const liveWorldId = liveWorld?.id ?? null
  const archiveMode = selectedRunId !== null && selectedRunId !== liveWorldId

  useEffect(() => {
    archiveModeRef.current = archiveMode
  }, [archiveMode])

  useEffect(() => {
    fetch('/api/version')
      .then((r) => r.json())
      .then((d) => setVersionInfo({ version: d.version ?? '0.1.0', revision: d.revision ?? '' }))
      .catch(() => setVersionInfo({ version: '0.1.0', revision: '' }))
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
      const chip = raw.closest('[title], [data-hint]') as HTMLElement | null
      if (chip) {
        const txt = chip.getAttribute('title') || chip.getAttribute('data-hint') || chip.getAttribute('data-title')
        if (txt) {
          const rect = chip.getBoundingClientRect()
          setTooltip({ text: txt, x: rect.left + rect.width / 2, y: rect.top })
          if (hideTimer) window.clearTimeout(hideTimer)
          hideTimer = window.setTimeout(() => setTooltip(null), 2800) as unknown as number
          e.preventDefault()
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
    document.addEventListener('click', onClick, true)
    return () => {
      document.removeEventListener('mouseenter', onEnter, true)
      document.removeEventListener('mouseleave', onLeave, true)
      document.removeEventListener('click', onClick, true)
      if (hideTimer) window.clearTimeout(hideTimer)
    }
  }, [tooltip])

  // Keyboard controls: space pause · S step · R reset · +/- zoom · F fit.
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      const t = ev.target as HTMLElement | null
      if (t && ['INPUT', 'SELECT', 'TEXTAREA'].includes(t.tagName)) return
      switch (ev.code) {
        case 'Space':
          ev.preventDefault()
          setPaused((p) => {
            sockRef.current?.send({ action: p ? 'resume' : 'pause' })
            return !p
          })
          break
        case 'KeyS':
          sockRef.current?.send({ action: 'step' })
          break
        case 'KeyR':
          sockRef.current?.send({ action: 'reset' })
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
  }, [])

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
      onHello: (msg) => {
        setHello(msg)
        setSpeed(msg.tick_rate)
        refreshWorlds()
      },
      onState: (msg) => {
        // New world detection: tick reset or seed change → clear chronicle
        const isNewWorld =
          (prevTickRef.current !== null && msg.tick < prevTickRef.current) ||
          (prevSeedRef.current !== null && msg.seed !== prevSeedRef.current && msg.tick === 0)
        if (isNewWorld && !archiveModeRef.current) {
          setLog([])
          setAliveHist([])
          setPopHist([])
          seenEventsRef.current.clear()
          fetchedByIdRef.current.clear()
          oldestLoadedRef.current = null
          seededRef.current = false
          setNoMoreHistory(false)
          setViewSnapTick(null)
          overrideRef.current = null
        }
        prevTickRef.current = msg.tick
        prevSeedRef.current = msg.seed
        stateRef.current = msg
        setState(msg)
        setAliveHist((prev) => (isNewWorld && !archiveModeRef.current ? [msg.creatures_alive] : [...prev.slice(-119), msg.creatures_alive]))
        setPopHist((prev) => (isNewWorld && !archiveModeRef.current ? [msg.population] : [...prev.slice(-239), msg.population]))
        if (!archiveModeRef.current) {
          const fresh = msg.events.filter((ev) => {
            const key = eventKey(ev)
            if (seenEventsRef.current.has(key)) return false
            seenEventsRef.current.add(key)
            return true
          })
          if (fresh.length > 0) {
            setLog((prev) =>
              [...fresh.reverse(), ...prev].slice(0, MAX_LOG),
            )
          }
        }
      },

    })
    sock.connect()
    sockRef.current = sock
    return () => sock.dispose()
  }, [])

  // World end detection — extinction summary
  useEffect(() => {
    if (state && state.creatures_alive === 0 && state.tick > 30 && !showWorldEnd && !archiveMode) {
      setShowWorldEnd(true)
    }
    if (state && state.creatures_alive > 0 && showWorldEnd) {
      setShowWorldEnd(false)
    }
  }, [state?.creatures_alive, state?.tick, showWorldEnd, archiveMode])

  const sendPause = useCallback(() => {
    sockRef.current?.send({ action: 'pause' })
    setPaused(true)
  }, [])
  const sendResume = useCallback(() => {
    sockRef.current?.send({ action: 'resume' })
    setPaused(false)
  }, [])
  const sendStep = useCallback(() => sockRef.current?.send({ action: 'step' }), [])
  const sendReset = useCallback(() => sockRef.current?.send({ action: 'reset' }), [])
  const changeSpeed = useCallback((v: number) => {
    setSpeed(v)
    sockRef.current?.send({ action: 'set_speed', value: v })
  }, [])

  const takeSnapshot = useCallback(async () => {
    await fetch('/api/snapshot', { method: 'POST' })
    const list = await fetch('/api/snapshots').then((r) => r.json())
    setAlbum(list.snapshots)
  }, [])

  const openAlbum = useCallback(async () => {
    const list = await fetch('/api/snapshots').then((r) => r.json())
    setAlbum(list.snapshots)
    setAlbumOpen((o) => !o)
  }, [])

  const viewSnapshot = useCallback(async (id: number) => {
    const data = await fetch(`/api/snapshot/${id}`).then((r) => r.json())
    overrideRef.current = data.state as StateMessage
    setViewSnapTick(data.tick)
    setAlbumOpen(false)
  }, [])

  const exitSnapshot = useCallback(() => {
    overrideRef.current = null
    setViewSnapTick(null)
  }, [])

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
    if (!chronicleOpen || archiveMode || seededRef.current) return
    seededRef.current = true
    fetch(`/api/history?limit=${HISTORY_PAGE}`)
      .then((r) => r.json())
      .then((d) => mergeFetched(Array.isArray(d.events) ? d.events : []))
      .catch(() => {})
  }, [chronicleOpen, archiveMode, mergeFetched])

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
    (raw: string) => {
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

  return (
    <div className="app">
      <header className={`hud ${isMobile ? 'hud-compact' : ''}`} onClick={isMobile ? () => setStatusExpanded(o => !o) : undefined} style={isMobile ? { cursor: 'pointer' } : undefined}>
        <span className="title">Flatland</span>
        <span className={`dot ${status}`} title={STATUS_LABEL[status]} />
        <span className="chip">{STATUS_LABEL[status]}</span>
        {paused && <span className="chip paused">PAUSED</span>}
        <span className="chip" title="Current tick — simulation step count (10 ticks/s by default). Same seed ⇒ same world.">
          tick <b>{state?.tick ?? 0}</b>
        </span>
        <span className="chip alive" title="Alive creatures — Flatland castes + Predators + Herbivores. Hover Caste chart for breakdown.">
          alive <b>{state?.creatures_alive ?? 0}</b>
        </span>
        <span className="chip dead desktop-only" title={`${deadBreakdown} — hover for per-cause breakdown (starvation/old_age/euthanasia/disease/predation/war/poison).`}>
          dead <b>{state?.creatures_dead ?? 0}</b>
        </span>
        {hungryCount > 0 && (
          <span className="chip hungry" title="Hungry: energy ≤ 35% of max — perceives food farther (1.3×), still fertile.">
            hungry <b>{hungryCount}</b>
          </span>
        )}
        {starvingCount > 0 && (
          <span className="chip starving" title="Starving: energy ≤ 15% — sees farthest (1.6×) and moves 1.35× faster, pulsing red, will die soon.">
            starving <b>{starvingCount}</b>
          </span>
        )}
        {(state?.infected_count ?? 0) > 0 && (
          <span className="chip sick desktop-only" title="Infected — loses 0.15 energy/tick + 1.0 health/tick (winter ×1.5 spread), green pulsing ring, may recover.">
            infected <b>{state?.infected_count}</b>
          </span>
        )}
        {(state?.entities.filter((e) => (e.chill ?? 0) >= 12).length ?? 0) > 0 && (
          <span className="chip desktop-only" style={{ color: '#79c0ff' }} title="Chilled: built rain/storm/winter-night outside, past 12 drains health 0.18/tick (death cause chill). Shelter sheds 2.5× faster.">
            🥶 chilled <b>{state?.entities.filter((e) => (e.chill ?? 0) >= 12).length}</b>
          </span>
        )}
        {raining && exposedCount > 0 && (
          <span className="chip exposed desktop-only" title="Exposed: awake, outdoors, not in a House during rain/storm or winter night — loses 0.03 energy/tick extra. Shelter is scarce.">
            ⛈ exposed <b>{exposedCount}</b>
          </span>
        )}
        {hello && (
          <span className="chip desktop-only" title="Seed determines entire world deterministically; width×height is world size; wrap vs clamp is edge behavior. Reset rolls a new seed.">
            seed <b>{state?.seed ?? hello.seed}</b> · {state?.width ?? hello.width}×
            {state?.height ?? hello.height} · {state?.boundary ?? hello.boundary}
          </span>
        )}
        {state && state.age && (
          <span className="chip desktop-only" title={`Age ${state.age} — super-season bending world: Ice (food×0.55 chill×1.4), Chaos (mutation×1.8), Plague (disease×1.8), Golden (food×1.25 birth×1.3). God sets age_length.`}>
            🗓 age <b>{state.age}</b> · tick {state.age_tick}
          </span>
        )}
        {state && (
          <span className="chip" title={`Time of day ${state.time_of_day} — night (0-0.22, 0.78-1) dims sight 0.6×, fog 0.6× stack; season ${state.season} changes Food target and disease. Weather ${state.weather}: rain slows 0.85×, storm adds wander.`}>
            {isNight ? '🌙' : '☀'} day <b>{state.day}</b> · {state.season}
            {weatherIcon && ` · ${weatherIcon}`}
          </span>
        )}
        {isMobile && <span className="chip" style={{ marginLeft: 'auto', fontSize: 10, color: '#8b949e' }}>{statusExpanded ? '▲' : '▼'}</span>}
      </header>
      {isMobile && statusExpanded && (
        <div className="hud-detail-sheet" onClick={() => setStatusExpanded(false)}>
          <span className="chip">entities <b>{state?.entities.length ?? 0}</b></span>
          <span className="chip dead">dead <b>{state?.creatures_dead ?? 0}</b></span>
          <span className="chip" style={{ fontSize: 10, color: '#8b949e' }}>{deadBreakdown}</span>
          {(state?.infected_count ?? 0) > 0 && <span className="chip sick">infected <b>{state?.infected_count}</b></span>}
          {(state?.entities.filter((e) => (e.chill ?? 0) >= 12).length ?? 0) > 0 && <span className="chip" style={{ color: '#79c0ff' }}>🥶 chilled <b>{state?.entities.filter((e) => (e.chill ?? 0) >= 12).length}</b></span>}
          {raining && exposedCount > 0 && <span className="chip exposed">⛈ exposed <b>{exposedCount}</b></span>}
          {hello && <span className="chip">seed <b>{state?.seed ?? hello.seed}</b> · {state?.width ?? hello.width}×{state?.height ?? hello.height} · {state?.boundary ?? hello.boundary}</span>}
          {state?.age && <span className="chip">🗓 age <b>{state.age}</b> · tick {state.age_tick}</span>}
          <span className="chip">hungry <b>{hungryCount}</b> · starving <b>{starvingCount}</b></span>
        </div>
      )}

      <main className="stage">
        <CanvasRenderer
          stateRef={stateRef}
          selectedRef={selectedRef}
          onTapCreature={(id) => setSelectedId(id)}
        />
      </main>

      {/* Mobile thumb bar — persistent 48px */}
      {isMobile && (
        <div className="mobile-thumb-bar">
          <button onClick={paused ? sendResume : sendPause} title={paused ? 'Resume (space)' : 'Pause (space)'}>{paused ? '▶' : '⏸'}</button>
          <button onClick={sendStep} title="Step (S)">⏭</button>
          <button onClick={() => setGodOpen(true)} title="God laws">⚖</button>
          <button onClick={() => { setSheetTab('chronicle'); setSheetState('half'); }} title="Chronicle">📜</button>
          <button onClick={() => window.dispatchEvent(new Event('flatworld-fit'))} title="Fit view (F)">⛶</button>
          <button onClick={takeSnapshot} title="Snapshot 📷">📷</button>
          <button onClick={openAlbum} title="Album">🖼</button>
          <select value={speed} onChange={e => changeSpeed(Number(e.target.value))} title="ticks/s">
            {SPEEDS.map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
      )}

      {/* Mobile tabbed sheet — World / Clans / Chronicle / Plots */}
      {isMobile && (
        <div className="mobile-sheet" data-state={sheetState}>
          <div
            className="mobile-sheet-handle"
            onClick={() => setSheetState(s => s === 'peek' ? 'half' : s === 'half' ? 'full' : 'peek')}
            onTouchStart={e => {
              const startY = e.touches[0].clientY
              const startState = sheetState
              const onMove = (ev: TouchEvent) => {
                const dy = ev.touches[0].clientY - startY
                if (dy < -40 && startState === 'peek') setSheetState('half')
                else if (dy < -40 && startState === 'half') setSheetState('full')
                else if (dy > 40 && startState === 'full') setSheetState('half')
                else if (dy > 40 && startState === 'half') setSheetState('peek')
              }
              const onEnd = () => {
                window.removeEventListener('touchmove', onMove as any)
                window.removeEventListener('touchend', onEnd as any)
              }
              window.addEventListener('touchmove', onMove as any, { passive: true })
              window.addEventListener('touchend', onEnd as any)
            }}
          />
          <div className="mobile-sheet-tabs">
            <button className={sheetTab === 'world' ? 'active' : ''} onClick={() => setSheetTab('world')}>World</button>
            <button className={sheetTab === 'clans' ? 'active' : ''} onClick={() => setSheetTab('clans')}>Clans</button>
            <button className={sheetTab === 'chronicle' ? 'active' : ''} onClick={() => setSheetTab('chronicle')}>Log</button>
            <button className={sheetTab === 'plots' ? 'active' : ''} onClick={() => setSheetTab('plots')}>Plots</button>
          </div>
          <div className="mobile-sheet-body">
            {sheetTab === 'world' && (
              <>
                <h3 className="chronicle-title">Overview — <span className="chronicle-pop">{creatureEntries.map(([k,v],i)=>(<span key={k} className="pop-chip"><span className="dot-inline" style={{background:CASTE_COLORS[k]??'#8b949e'}}/>{k} <b>{v}</b>{(i<creatureEntries.length-1||objectEntries.length>0)&&' · '}</span>))}{objectEntries.map(([k,v],i)=>(<span key={k} className="pop-chip">{k} <b>{v}</b>{i<objectEntries.length-1&&' · '}</span>))}</span></h3>
                <CasteChart history={popHist} showLegend={false} />
                <div style={{ fontSize: 11, color: '#8b949e', margin: '6px 0 2px' }}>Alive — recent ticks</div>
                <span className="spark-wrap" style={{ display:'block', width:'100%' }}><svg viewBox="0 0 100 22" className="spark" style={{ width:'100%', height:28 }}>{aliveHist.length>1 && <polyline points={aliveHist.map((v,i)=> `${(i/(aliveHist.length-1))*100},${21-((v-Math.min(...aliveHist))/(Math.max(...aliveHist,1)-Math.min(...aliveHist)||1))*20}`).join(' ')} />}</svg></span>
                <h4 style={{ margin:'10px 0 4px', fontSize:'0.85em', opacity:0.8 }}>Trophic — Food · Herbivore · Predator</h4>
                <TrophicChart history={popHist} showLegend={false} />
              </>
            )}
            {sheetTab === 'clans' && <ClanPanel onSelectClan={setSelectedClanId} />}
            {sheetTab === 'plots' && <PlotsPanel />}
            {sheetTab === 'chronicle' && (
              <div className="chronicle" style={{ background:'transparent', border:'none', padding:0, maxHeight:'none' }}>
                <h3 className="chronicle-title">Chronicle — History</h3>
                {archiveMode && selectedRunId!==null && <p className="archive-banner">viewing archive #{selectedRunId} — live paused</p>}
                {!archiveMode && oldestLoadedRef.current!==null && <button className="chron-btn" onClick={loadOlder} disabled={loadingOlder||noMoreHistory}>{loadingOlder?'loading…':noMoreHistory?'no older events':'load older'}</button>}
                {(() => { const filtered=log.filter(ev=>ev.type!=='bloom'); if(filtered.length===0) return <p className="chip">no major events yet</p>; return <ul>{filtered.slice(0,60).map(ev=>{ const key=`${ev.tick}:${ev.entity_id}:${ev.type}`; if(ev.type==='birth'){ const p=ev.payload as any; return <li key={key} className="ev-birth"><b>{p.personal_name??ev.caste} {p.glyph??''}</b> #{ev.entity_id} born at {ev.tick}</li>} return <li key={key}><b>{(ev.payload as any)?.personal_name??ev.caste}</b> #{ev.entity_id} {ev.type} at {ev.tick}</li>})}</ul> })()}
              </div>
            )}
          </div>
        </div>
      )}

      <footer className="controls">
        {paused ? (
          <button onClick={sendResume}>Resume</button>
        ) : (
          <button onClick={sendPause}>Pause</button>
        )}
        <button onClick={sendStep}>Step</button>
        <button onClick={sendReset}>Reset</button>
        <button onClick={() => window.dispatchEvent(new Event('flatworld-fit'))}>
          Fit view
        </button>
        <button onClick={() => setChronicleOpen((o) => !o)}>
          {chronicleOpen ? 'Hide' : 'Show'} chronicle
        </button>
        <button onClick={takeSnapshot} title="freeze the current moment into the album">
          📷
        </button>
        <button onClick={openAlbum}>Album</button>
        <label className="chip" htmlFor="speed">
          ticks/s
        </label>
        <select
          id="speed"
          value={speed}
          onChange={(e) => changeSpeed(Number(e.target.value))}
        >
          {SPEEDS.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </footer>

      <p className="key-hints">space pause · S step · R reset · F fit · +/− zoom</p>

      {viewSnapTick !== null && (
        <button className="snap-banner" onClick={exitSnapshot}>
          viewing snapshot from tick {viewSnapTick} — click to return to the living
        </button>
      )}

      {albumOpen && (
        <aside className="album">
          <h3>Snapshot album</h3>
          {album.length === 0 ? (
            <p className="chip">no photos yet — press 📷</p>
          ) : (
            <ul>
              {album.map((s) => (
                <li key={s.id}>
                  <button onClick={() => viewSnapshot(s.id)}>tick {s.tick}</button>
                </li>
              ))}
            </ul>
          )}
        </aside>
      )}

      {chronicleOpen && (
        <div className="right-stack">
          <aside className="info-panel">
            <h3 className="chronicle-title" title="Live population — creatures (colored) + objects (Food/House) · history below. Creatures also in Caste graph.">
              Overview
              {(creatureEntries.length > 0 || objectEntries.length > 0) && (
                <span className="chronicle-pop">
                  {' '}
                  —{' '}
                  {creatureEntries.map(([k, v], i) => (
                    <span key={k} className="pop-chip" title={`${k}: ${v} alive — see Caste graph for trend`}>
                      <span className="dot-inline" style={{ background: CASTE_COLORS[k] ?? '#8b949e' }} />
                      {k} <b>{v}</b>
                      {(i < creatureEntries.length - 1 || objectEntries.length > 0) && ' · '}
                    </span>
                  ))}
                  {objectEntries.map(([k, v], i) => {
                    const color = k === 'Food' ? '#3fb950' : k === 'House' ? '#8b949e' : k === 'Corpse' ? '#6e7681' : '#8b949e'
                    return (
                      <span key={k} className="pop-chip" title={`${k}: ${v} objects — Food are plants (growth variant), House are shelters, Corpse are remains`}>
                        <span className="dot-inline" style={{ background: color }} />
                        {k} <b>{v}</b>
                        {i < objectEntries.length - 1 && ' · '}
                      </span>
                    )
                  })}
                </span>
              )}
            </h3>
            <CasteChart history={popHist} showLegend={false} />
            <div className="info-spark" title="alive creatures, recent ticks (was at bottom left, now in info box)">
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
            <h4
              style={{ margin: '10px 0 4px', fontSize: '0.85em', opacity: 0.8 }}
              title="Trophic pyramid: stacked history of Food (plants, variant colors) → Herbivore (wild grazers, beast_ratio) → Predator (carnivores). Shows Lotka-Volterra oscillation: plants feed herbivores, herbivores feed predators. Spikes mean blooms or hunts."
            >
              Trophic pyramid — Food · Herbivore · Predator{' '}
              <span style={{ fontWeight: 400, opacity: 0.7 }}>(plants → grazers → hunters)</span>
            </h4>
            <TrophicChart history={popHist} showLegend={false} />
            <ClanPanel onSelectClan={setSelectedClanId} />
            <PlotsPanel />
          </aside>
          <aside className="chronicle">
            <h3 className="chronicle-title" title="Event history — births, deaths, wars, plagues. Newest first.">
              Chronicle — History
            </h3>
            {archiveMode && selectedRunId !== null && (
              <p className="archive-banner">
                viewing archive of world #{selectedRunId} — live feed paused
              </p>
            )}
          {!archiveMode && oldestLoadedRef.current !== null && (
            <button
              className="chron-btn"
              onClick={loadOlder}
              disabled={loadingOlder || noMoreHistory}
            >
              {loadingOlder
                ? 'loading…'
                : noMoreHistory
                  ? 'no older events'
                  : 'load older'}
            </button>
          )}
          {(() => { const filtered = log.filter((ev) => ev.type !== 'bloom'); if (filtered.length === 0) return <p className="chip">no major events yet — blooms hidden</p>; return (<ul>{filtered.map((ev) => {
                const key = `${ev.tick}:${ev.entity_id}:${ev.type}`
                if (ev.type === 'birth') {
                  const p = (ev.payload ?? {}) as { mother?: number; father?: number; generation?: number; personal_name?: string; glyph?: string }
                  const nm = (p.personal_name as string) ?? ev.caste
                  const gl = (p.glyph as string) ? ` ${p.glyph}` : ''
                  return (
                    <li key={key} className="ev-birth">
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show profile"><b>{nm}{gl}</b> #{ev.entity_id}</button> born to <button className="chronicle-name" onClick={() => p.mother && setSelectedId(p.mother!)} title="show mother">#{p.mother}</button> × <button className="chronicle-name" onClick={() => p.father && setSelectedId(p.father!)} title="show father">#{p.father}</button> (gen {p.generation}) at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'promotion') {
                  const p = (ev.payload ?? {}) as { from?: string; to?: string; personal_name?: string }
                  const nm = (p.personal_name as string) ? `${p.personal_name} ` : ''
                  return (
                    <li key={key} className="ev-promo">
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show profile"><b>{nm}#{ev.entity_id}</b></button> rose {String(p.from ?? 'Soldier')} →{' '}
                      {String(p.to ?? ev.caste)} at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'demotion') {
                  const p = (ev.payload ?? {}) as { personal_name?: string; glyph?: string }
                  const nm = (p.personal_name as string) ?? ev.caste
                  const gl = (p.glyph as string) ? ` ${p.glyph}` : ''
                  return (
                    <li key={key} className="ev-demote">
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show profile"><b>{nm}{gl}</b> #{ev.entity_id}</button> judged irregular and demoted
                      at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'predation') {
                  const p = (ev.payload ?? {}) as { prey?: number; prey_caste?: string; personal_name?: string; glyph?: string }
                  const nm = (p.personal_name as string) ?? ev.caste
                  const gl = (p.glyph as string) ? ` ${p.glyph}` : ''
                  return (
                    <li key={key} className="ev-predation" style={{ color: '#ff3838' }}>
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show predator"><b>{nm}{gl}</b> #{ev.entity_id}</button> predated <b>{p.prey_caste}</b> <button className="chronicle-name" onClick={() => p.prey && setSelectedId(p.prey!)} title="show prey">#{p.prey}</button> at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'war') {
                  const p = (ev.payload ?? {}) as { winner?: number; a?: number; b?: number; personal_name?: string; glyph?: string }
                  const nm = (p.personal_name as string) ?? ev.caste
                  const gl = (p.glyph as string) ? ` ${p.glyph}` : ''
                  return (
                    <li key={key} className="ev-war" style={{ color: '#f85149' }}>
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show fallen"><b>{nm}{gl}</b> #{ev.entity_id}</button> fell in clan war (winner <button className="chronicle-name" onClick={() => p.winner && setSelectedId(p.winner!)} title="show winner">#{p.winner}</button>) at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'alliance' || ev.type === 'rivalry') {
                  const p = (ev.payload ?? {}) as { a?: number; b?: number; score?: number }
                  return (
                    <li key={key} className={ev.type === 'alliance' ? 'ev-alliance' : 'ev-rivalry'} style={{ color: ev.type === 'alliance' ? '#3fb950' : '#d29922' }}>
                      Clans #{p.a} & #{p.b} {ev.type} (score {p.score}) at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'schism') {
                  const p = (ev.payload ?? {}) as { parent?: number; new_clan?: number; parent_name?: string; new_name?: string; members?: number[] }
                  return (
                    <li key={key} className="ev-schism" style={{ color: '#e3b341' }}>
                      schism: {p.parent_name ?? `#${p.parent}`} → {p.new_name ?? `#${p.new_clan}`} ({(p.members as number[])?.length ?? 0} broke away) at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'fire') {
                  const p = (ev.payload ?? {}) as { kind?: string; r?: number }
                  return (
                    <li key={key} className="ev-bloom" style={{ color: '#ff6b35' }}>
                      fire {p.kind ?? ''} at ({Math.round(ev.x)}, {Math.round(ev.y)}) tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'disaster') {
                  const p = (ev.payload ?? {}) as { kind?: string; r?: number }
                  return (
                    <li key={key} className="ev-bloom" style={{ color: '#e3b341' }}>
                      disaster {p.kind ?? ''} r{p.r ?? ''} at ({Math.round(ev.x)}, {Math.round(ev.y)}) tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'conquest') {
                  const p = (ev.payload ?? {}) as { winner_clan?: number; loser_clan?: number; house_id?: number }
                  return (
                    <li key={key} className="ev-bloom" style={{ color: '#ff7b72' }}>
                      conquest: clan {p.winner_clan} seized house {p.house_id} from clan {p.loser_clan} at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'bloom') {
                  return (
                    <li key={key} className="ev-bloom" style={{ color: '#3fb950' }}>
                      bloom at ({Math.round(ev.x)}, {Math.round(ev.y)}) tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'outbreak' || ev.type === 'recovery') {
                  const p = (ev.payload ?? {}) as { personal_name?: string; glyph?: string }
                  const nm = (p.personal_name as string) ?? ev.caste
                  const gl = (p.glyph as string) ? ` ${p.glyph}` : ''
                  return (
                    <li key={key} className={ev.type === 'outbreak' ? 'ev-outbreak' : 'ev-recovery'} style={{ color: ev.type === 'outbreak' ? '#d29922' : '#3fb950' }}>
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show creature"><b>{nm}{gl}</b> #{ev.entity_id}</button> {ev.type} at tick {ev.tick}
                    </li>
                  )
                }
                {
                  const p = (ev.payload ?? {}) as { personal_name?: string; glyph?: string }
                  const nm = (p.personal_name as string) ?? ev.caste
                  const gl = (p.glyph as string) ? ` ${p.glyph}` : ''
                  return (
                    <li key={key}>
                      <button className="chronicle-name" onClick={() => setSelectedId(ev.entity_id)} title="show profile"><b>{nm}{gl}</b> #{ev.entity_id}</button> died of {ev.cause} at tick{' '}
                      {ev.tick} ({Math.round(ev.x)}, {Math.round(ev.y)})
                    </li>
                  )
                }
              })}
            </ul>)
          })()}
        </aside>
        </div>
      )}

      {selectedId !== null && (
        <Inspector
          id={selectedId}
          onClose={() => setSelectedId(null)}
          onNavigate={(nid) => setSelectedId(nid)}
        />
      )}

      <GodPanel open={godOpen} onClose={() => setGodOpen(false)} />
      <Wiki open={wikiOpen} onClose={() => setWikiOpen(false)} />
      {selectedClanId !== null && (
        <ClanDetails clanId={selectedClanId} onClose={() => setSelectedClanId(null)} onSelectCreature={(id) => { setSelectedClanId(null); setSelectedId(id) }} />
      )}
      {showWorldEnd && state && (
        <WorldEndSummary state={state} onReset={() => { sendReset(); setShowWorldEnd(false) }} onClose={() => setShowWorldEnd(false)} />
      )}

      {helpOpen && (
        <div className="help-backdrop" onClick={() => setHelpOpen(false)}>
          <div className="help-panel" onClick={(e) => e.stopPropagation()}>
            <header className="god-head">
              <h3>Hints</h3>
              <button className="god-close" onClick={() => setHelpOpen(false)}>×</button>
            </header>
            <p className="god-note">Tap any chip to see its hint. God never touches a single life — only laws.</p>
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
      {/* God + Help + Wiki — top right panel */}
      <div className="top-right-panel">
        <button className="god-btn wiki-btn" onClick={() => setWikiOpen(true)} title="Wiki — documentation & API ( /wiki )">
          📖<span className="hide-mobile"> Wiki</span>
        </button>
        <button className="god-btn" onClick={() => setHelpOpen((o) => !o)} title="Show hints for all HUD chips and controls">
          ?
        </button>
        <button className="god-btn god-main-btn" onClick={() => setGodOpen(true)} title="Laws of Nature — god sets laws, never touches a life">
          ⚖<span className="hide-mobile"> God</span>
        </button>
      </div>
      {/* version + revision at bottom */}
      <div className="version-bar" title={versionInfo ? `v${versionInfo.version} · ${versionInfo.revision}` : 'Flatland'}>
        {versionInfo ? `v${versionInfo.version} · ${versionInfo.revision}` : 'v0.1.0'}
      </div>
      {tooltip && (
        <div
          className="custom-tooltip"
          style={{ left: tooltip.x, top: tooltip.y - 8, transform: 'translate(-50%, -100%)' }}
          onClick={() => setTooltip(null)}
        >
          {tooltip.text}
        </div>
      )}
      {worlds.length > 0 && (
        <div className="run-switcher">
          <label className="chip run-label" htmlFor="run-bottom">
            run
            <select
              id="run-bottom"
              className="run-select"
              value={String(selectedRunId ?? liveWorldId ?? '')}
              onChange={(e) => selectRun(e.target.value)}
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
    </div>
  )
}
