import { useCallback, useEffect, useRef, useState } from 'react'
import CanvasRenderer from './render/CanvasRenderer'
import GodPanel from './god/GodPanel'
import Inspector from './inspect/Inspector'
import { WorldSocket, type ConnStatus } from './websocket'
import type { HelloMessage, HistoryEvent, StateMessage } from './types'

const SPEEDS = [1, 5, 10, 20, 40]

const STATUS_LABEL: Record<ConnStatus, string> = {
  connecting: 'connecting',
  open: 'live',
  closed: 'reconnecting…',
}

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

  const stateRef = useRef<StateMessage | null>(null)
  const sockRef = useRef<WorldSocket | null>(null)
  const seenEventsRef = useRef(new Set<string>())
  const selectedRef = useRef<number | null>(null)
  useEffect(() => {
    selectedRef.current = selectedId
  }, [selectedId])

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

  useEffect(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const sock = new WorldSocket(`${proto}://${location.host}/ws`, {
      onStatus: setStatus,
      onHello: (msg) => {
        setHello(msg)
        setSpeed(msg.tick_rate)
      },
      onState: (msg) => {
        stateRef.current = msg
        setState(msg)
        setAliveHist((prev) => [...prev.slice(-119), msg.creatures_alive])
        const fresh = msg.events.filter((ev) => {
          const key = `${ev.tick}:${ev.entity_id}:${ev.type}`
          if (seenEventsRef.current.has(key)) return false
          seenEventsRef.current.add(key)
          return true
        })
        if (fresh.length > 0) {
          setLog((prev) => [...fresh.reverse(), ...prev].slice(0, 200))
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

  const populationSummary = state
    ? Object.entries(state.population)
        .map(([k, v]) => `${k} ${v}`)
        .join(' · ')
    : '—'

  const hungryCount = state?.entities.filter((e) => e.status === 'hungry').length ?? 0
  const starvingCount = state?.entities.filter((e) => e.status === 'starving').length ?? 0
  const deadBreakdown = state
    ? Object.entries(state.dead_by_cause)
        .sort((a, b) => b[1] - a[1])
        .map(([cause, n]) => `${cause}: ${n}`)
        .join(' · ') || 'no deaths yet'
    : ''

  const isNight = state ? state.time_of_day < 0.22 || state.time_of_day > 0.78 : false
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
        <span className="chip legend">{populationSummary}</span>
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

      {chronicleOpen && (
        <aside className="chronicle">
          <h3>Chronicle</h3>
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
        <Inspector id={selectedId} onClose={() => setSelectedId(null)} />
      )}

      <GodPanel open={godOpen} onClose={() => setGodOpen(false)} />
    </div>
  )
}
