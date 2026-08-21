import { useCallback, useEffect, useRef, useState } from 'react'
import CanvasRenderer from './render/CanvasRenderer'
import GodPanel from './god/GodPanel'
import { WorldSocket, type ConnStatus } from './websocket'
import type { HelloMessage, StateMessage } from './types'

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

  const stateRef = useRef<StateMessage | null>(null)
  const sockRef = useRef<WorldSocket | null>(null)

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
        {hello && (
          <span className="chip">
            seed <b>{hello.seed}</b> · {hello.width}×{hello.height} · {hello.boundary}
          </span>
        )}
      </header>

      <main className="stage">
        <CanvasRenderer stateRef={stateRef} />
      </main>

      <footer className="controls">
        {paused ? (
          <button onClick={sendResume}>Resume</button>
        ) : (
          <button onClick={sendPause}>Pause</button>
        )}
        <button onClick={sendStep}>Step</button>
        <button onClick={sendReset}>Reset</button>
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
      </footer>

      <GodPanel open={godOpen} onClose={() => setGodOpen(false)} />
    </div>
  )
}
