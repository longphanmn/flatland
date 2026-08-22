import { useCallback, useEffect, useRef, useState } from 'react'
import CanvasRenderer, { CASTE_COLORS } from './render/CanvasRenderer'
import CasteChart from './render/CasteChart'
import GodPanel from './god/GodPanel'
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
  const [chronicleOpen, setChronicleOpen] = useState(true)
  const [log, setLog] = useState<HistoryEvent[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
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
  // Chronicle header shows only objects (Food/House/Corpse), creatures are in graph
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
      <header className="hud">
        <span className="title">Flatland</span>
        <button className="god-btn" onClick={() => setGodOpen(true)}>
          ⚖ God
        </button>
        <span className={`dot ${status}`} title={STATUS_LABEL[status]} />
        <span className="chip">{STATUS_LABEL[status]}</span>
        {paused && <span className="chip paused">PAUSED</span>}
        <span className="chip">
          tick <b>{state?.tick ?? 0}</b>
        </span>
        <span className="chip">
          entities <b>{state?.entities.length ?? 0}</b>
        </span>
        <span className="chip alive">
          alive <b>{state?.creatures_alive ?? 0}</b>
        </span>
        <span className="chip dead" title={deadBreakdown}>
          dead <b>{state?.creatures_dead ?? 0}</b>
        </span>
        {hungryCount > 0 && (
          <span className="chip hungry">
            hungry <b>{hungryCount}</b>
          </span>
        )}
        {starvingCount > 0 && (
          <span className="chip starving">
            starving <b>{starvingCount}</b>
          </span>
        )}
        {(state?.infected_count ?? 0) > 0 && (
          <span className="chip sick">
            infected <b>{state?.infected_count}</b>
          </span>
        )}
        {raining && exposedCount > 0 && (
          <span className="chip exposed" title="awake creatures outdoors in the rain">
            ⛈ exposed <b>{exposedCount}</b>
          </span>
        )}
        {hello && (
          <span className="chip">
            seed <b>{state?.seed ?? hello.seed}</b> · {state?.width ?? hello.width}×
            {state?.height ?? hello.height} · {state?.boundary ?? hello.boundary}
          </span>
        )}
        {state && (
          <span className="chip" title={`time of day ${state.time_of_day}`}>
            {isNight ? '🌙' : '☀'} day <b>{state.day}</b> · {state.season}
            {weatherIcon && ` · ${weatherIcon}`}
          </span>
        )}
      </header>

      <main className="stage">
        <CanvasRenderer
          stateRef={stateRef}
          selectedRef={selectedRef}
          onTapCreature={(id) => setSelectedId(id)}
        />
      </main>

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
        <span className="spark-wrap" title="alive creatures, recent ticks">
          <svg viewBox="0 0 100 22" className="spark">
            {aliveHist.length > 1 && (
              <polyline
                points={aliveHist
                  .map(
                    (v, i) =>
                      `${(i / (aliveHist.length - 1)) * 100},${
                        21 - ((v - Math.min(...aliveHist)) / (Math.max(...aliveHist, 1) - Math.min(...aliveHist) || 1)) * 20
                      }`,
                  )
                  .join(' ')}
              />
            )}
          </svg>
        </span>
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
        <aside className="chronicle">
          <h3 className="chronicle-title">
            Chronicle
            {objectEntries.length > 0 && (
              <span className="chronicle-pop" title="objects in world">
                {' '}
                —{' '}
                {objectEntries.map(([k, v], i) => {
                  const color = k === 'Food' ? '#d29922' : k === 'House' ? '#8b949e' : k === 'Corpse' ? '#6e7681' : '#8b949e'
                  return (
                    <span key={k} className="pop-chip">
                      <span className="dot-inline" style={{ background: color }} />
                      {k} <b>{v}</b>
                      {i < objectEntries.length - 1 && ' · '}
                    </span>
                  )
                })}
              </span>
            )}
          </h3>
          {archiveMode && selectedRunId !== null && (
            <p className="archive-banner">
              viewing archive of world #{selectedRunId} — live feed paused
            </p>
          )}
          <CasteChart history={popHist} />
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
          {log.length === 0 ? (
            <p className="chip">nothing recorded yet</p>
          ) : (
            <ul>
              {log.map((ev) => {
                const key = `${ev.tick}:${ev.entity_id}:${ev.type}`
                if (ev.type === 'birth') {
                  const p = (ev.payload ?? {}) as { mother?: number; father?: number; generation?: number }
                  return (
                    <li key={key} className="ev-birth">
                      <b>{ev.caste}</b> #{ev.entity_id} born to #{p.mother} × #
                      {p.father} (gen {p.generation}) at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'promotion') {
                  const p = (ev.payload ?? {}) as { from?: string; to?: string }
                  return (
                    <li key={key} className="ev-promo">
                      <b>#{ev.entity_id}</b> rose {String(p.from ?? 'Soldier')} →{' '}
                      {String(p.to ?? ev.caste)} at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'demotion') {
                  return (
                    <li key={key} className="ev-demote">
                      <b>{ev.caste}</b> #{ev.entity_id} judged irregular and demoted
                      at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'predation') {
                  const p = (ev.payload ?? {}) as { prey?: number; prey_caste?: string }
                  return (
                    <li key={key} className="ev-predation" style={{ color: '#ff3838' }}>
                      <b>{ev.caste}</b> #{ev.entity_id} predated <b>{p.prey_caste}</b> #{p.prey} at tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'war') {
                  const p = (ev.payload ?? {}) as { winner?: number; a?: number; b?: number }
                  return (
                    <li key={key} className="ev-war" style={{ color: '#f85149' }}>
                      <b>{ev.caste}</b> #{ev.entity_id} fell in clan war (winner #{p.winner}) at tick {ev.tick}
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
                if (ev.type === 'bloom') {
                  return (
                    <li key={key} className="ev-bloom" style={{ color: '#3fb950' }}>
                      bloom at ({Math.round(ev.x)}, {Math.round(ev.y)}) tick {ev.tick}
                    </li>
                  )
                }
                if (ev.type === 'outbreak' || ev.type === 'recovery') {
                  return (
                    <li key={key} className={ev.type === 'outbreak' ? 'ev-outbreak' : 'ev-recovery'} style={{ color: ev.type === 'outbreak' ? '#d29922' : '#3fb950' }}>
                      <b>{ev.caste}</b> #{ev.entity_id} {ev.type} at tick {ev.tick}
                    </li>
                  )
                }
                return (
                  <li key={key}>
                    <b>{ev.caste}</b> #{ev.entity_id} died of {ev.cause} at tick{' '}
                    {ev.tick} ({Math.round(ev.x)}, {Math.round(ev.y)})
                  </li>
                )
              })}
            </ul>
          )}
        </aside>
      )}

      {selectedId !== null && (
        <Inspector
          id={selectedId}
          onClose={() => setSelectedId(null)}
          onNavigate={(nid) => setSelectedId(nid)}
        />
      )}

      <GodPanel open={godOpen} onClose={() => setGodOpen(false)} />

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
