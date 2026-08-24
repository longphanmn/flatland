import { useEffect, useRef } from 'react'
import type { StateMessage } from '../types'
import {
  Camera,
  CASTE_COLORS,
  EMOTE_ICONS,
  MAX_SCALE,
  MIN_SCALE_FACTOR,
  pickCreatureAt,
  renderWorldFrame,
} from './renderCore'

export { CASTE_COLORS, EMOTE_ICONS }

interface Props {
  stateRef: React.RefObject<StateMessage | null>
  selectedRef?: React.RefObject<number | null>
  selectedClanRef?: React.RefObject<number | null>
  onTapCreature?: (id: number | null) => void
  /** When set, the canvas renders this frozen snapshot instead of the live world. */
  overrideRef?: React.RefObject<StateMessage | null>
}

export default function CanvasRenderer({
  stateRef,
  selectedRef,
  selectedClanRef,
  onTapCreature,
  overrideRef,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const workerRef = useRef<Worker | null>(null)
  const isWorkerModeRef = useRef(false)

  // Fallback Camera ref for non-worker mode
  const camRef = useRef<Camera>({ scale: 1, ox: 0, oy: 0, initialized: false })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const isMobileClient = typeof window !== 'undefined' && (window.innerWidth <= 768 || 'ontouchstart' in window)
    const dpr = () => Math.min(isMobileClient ? 1.25 : 1.5, window.devicePixelRatio || 1)

    let worker: Worker | null = null
    let reqCounter = 0
    let lastTap: { x: number; y: number; t: number } | null = null
    let tapStart: { x: number; y: number; t: number } | null = null
    let lastPinchDist = 0
    let lastMid: { x: number; y: number } | null = null


    interface P {
      x: number
      y: number
    }
    const pointers = new Map<number, P>()
    const dist = (a: P, b: P): number => Math.hypot(a.x - b.x, a.y - b.y)
    const mid = (a: P, b: P): P => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })
    const twoPointers = (): [P, P] => {
      const it = [...pointers.values()]
      return [it[0], it[1]]
    }

    // Try OffscreenCanvas in Web Worker (Phase 2 AJ)
    const supportsOffscreen =
      typeof Worker !== 'undefined' &&
      'transferControlToOffscreen' in HTMLCanvasElement.prototype

    if (supportsOffscreen) {
      try {
        const offscreen = canvas.transferControlToOffscreen()
        worker = new Worker(new URL('./render.worker.ts', import.meta.url), {
          type: 'module',
        })
        workerRef.current = worker
        isWorkerModeRef.current = true

        const cw = Math.max(1, Math.floor(canvas.clientWidth * dpr()))
        const ch = Math.max(1, Math.floor(canvas.clientHeight * dpr()))
        offscreen.width = cw
        offscreen.height = ch

        worker.postMessage(
          {
            type: 'init',
            canvas: offscreen,
            width: cw,
            height: ch,
            dpr: dpr(),
          },
          [offscreen],
        )

        worker.onmessage = (e) => {
          const msg = e.data
          if (msg?.type === 'hit_test_result') {
            if (onTapCreature) {
              onTapCreature(msg.id)
              if (msg.isDoubleTap && msg.id !== null) {
                worker?.postMessage({ type: 'center_on', id: msg.id })
              }
            }
          }
        }
      } catch (err) {
        console.warn('[CanvasRenderer] OffscreenCanvas worker init failed, using in-thread fallback:', err)
        worker = null
        workerRef.current = null
        isWorkerModeRef.current = false
      }
    }

    // Resize observer
    const onResize = () => {
      const cw = Math.max(1, Math.floor(canvas.clientWidth * dpr()))
      const ch = Math.max(1, Math.floor(canvas.clientHeight * dpr()))
      if (worker && isWorkerModeRef.current) {
        worker.postMessage({ type: 'resize', width: cw, height: ch, dpr: dpr() })
      } else {
        canvas.width = cw
        canvas.height = ch
      }
    }
    const ro = new ResizeObserver(onResize)
    ro.observe(canvas)

    // Fit & Zoom events
    const onFit = () => {
      if (worker && isWorkerModeRef.current) {
        worker.postMessage({ type: 'fit' })
      } else {
        const state = overrideRef?.current ?? stateRef.current
        if (state) {
          const cam = camRef.current
          const baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
          cam.scale = baseFit
          cam.ox = (canvas.width - state.width * cam.scale) / 2
          cam.oy = (canvas.height - state.height * cam.scale) / 2
          cam.initialized = true
        }
      }
    }
    window.addEventListener('flatworld-fit', onFit)

    const onZoomEvent = (ev: Event) => {
      const factor = (ev as CustomEvent<{ factor?: number }>).detail?.factor ?? 1.2
      const cx = (canvas.clientWidth * dpr()) / 2
      const cy = (canvas.clientHeight * dpr()) / 2
      if (worker && isWorkerModeRef.current) {
        worker.postMessage({ type: 'zoom', factor, cx, cy })
      } else {
        const state = overrideRef?.current ?? stateRef.current
        if (state) {
          const cam = camRef.current
          const baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
          const next = Math.min(Math.max(cam.scale * factor, baseFit * MIN_SCALE_FACTOR), MAX_SCALE)
          const wx = (cx - cam.ox) / cam.scale
          const wy = (cy - cam.oy) / cam.scale
          cam.ox = cx - wx * next
          cam.oy = cy - wy * next
          cam.scale = next
        }
      }
    }
    window.addEventListener('flatworld-zoom', onZoomEvent)

    // Pointer event listeners
    const onPointerDown = (ev: PointerEvent) => {
      if (ev.target !== canvas) return
      canvas.setPointerCapture(ev.pointerId)
      pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })
      if (pointers.size === 2) {
        const [a, b] = twoPointers()
        lastPinchDist = dist(a, b)
        lastMid = mid(a, b)
      }
      tapStart = { x: ev.clientX, y: ev.clientY, t: performance.now() }
      if (worker && isWorkerModeRef.current) {
        worker.postMessage({ type: 'pan_start' })
      }

      canvas.style.cursor = 'grab'
      if (ev.cancelable) ev.preventDefault()
    }

    const onPointerMove = (ev: PointerEvent) => {
      const prev = pointers.get(ev.pointerId)
      if (!prev) return
      pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })
      const ratio = dpr()

      if (pointers.size === 1) {
        if (tapStart) {
          const dragDist = Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * ratio
          if (dragDist < 6 * ratio) return
        }
        canvas.style.cursor = 'grabbing'
        const dx = (ev.clientX - prev.x) * ratio
        const dy = (ev.clientY - prev.y) * ratio
        if (worker && isWorkerModeRef.current) {
          worker.postMessage({ type: 'pan', dx, dy })
        } else {
          camRef.current.ox += dx
          camRef.current.oy += dy
        }
        return
      }

      if (pointers.size >= 2) {
        const [a, b] = twoPointers()
        const m = mid(a, b)
        const d = dist(a, b)
        if (lastMid && lastPinchDist > 0 && d > 0) {
          const dx = (m.x - lastMid.x) * ratio
          const dy = (m.y - lastMid.y) * ratio
          const factor = d / lastPinchDist
          if (worker && isWorkerModeRef.current) {
            worker.postMessage({ type: 'pan', dx, dy })
            worker.postMessage({ type: 'zoom', factor, cx: m.x * ratio, cy: m.y * ratio })
          } else {
            const cam = camRef.current
            cam.ox += dx
            cam.oy += dy
            const state = overrideRef?.current ?? stateRef.current
            if (state) {
              const baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
              const next = Math.min(Math.max(cam.scale * factor, baseFit * MIN_SCALE_FACTOR), MAX_SCALE)
              const wx = (m.x * ratio - cam.ox) / cam.scale
              const wy = (m.y * ratio - cam.oy) / cam.scale
              cam.ox = m.x * ratio - wx * next
              cam.oy = m.y * ratio - wy * next
              cam.scale = next
            }
          }
        }
        lastPinchDist = d
        lastMid = m
      }
    }

    const onPointerUp = (ev: PointerEvent) => {
      pointers.delete(ev.pointerId)
      if (pointers.size < 2) {
        lastPinchDist = 0
        lastMid = null
      }
      if (pointers.size === 0) {
        canvas.style.cursor = 'grab'
        if (worker && isWorkerModeRef.current) {
          worker.postMessage({ type: 'pan_end' })
        }
      }
      if (!tapStart || !onTapCreature) {
        tapStart = null
        return
      }
      const isTap =
        performance.now() - tapStart.t < 500 &&
        Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * dpr() < 10 * dpr()
      if (!isTap) {
        tapStart = null
        return
      }
      const now = performance.now()
      const isDoubleTap =
        lastTap &&
        now - lastTap.t < 300 &&
        Math.hypot(tapStart.x - lastTap.x, tapStart.y - lastTap.y) < 24

      if (worker && isWorkerModeRef.current) {
        reqCounter++
        worker.postMessage({
          type: 'hit_test',
          clientX: tapStart.x,
          clientY: tapStart.y,
          dpr: dpr(),
          reqId: reqCounter,
          isDoubleTap: !!isDoubleTap,
        })
      } else {
        const id = pickCreatureAt(
          overrideRef?.current ?? stateRef.current,
          tapStart.x,
          tapStart.y,
          camRef.current,
          dpr(),
        )
        onTapCreature(id)
      }

      lastTap = isDoubleTap ? null : { x: tapStart.x, y: tapStart.y, t: now }
      tapStart = null
    }

    const onWheel = (ev: WheelEvent) => {
      if (ev.target !== canvas) return
      ev.preventDefault()
      const factor = Math.exp(-ev.deltaY * 0.0015)
      const cx = ev.clientX * dpr()
      const cy = ev.clientY * dpr()
      if (worker && isWorkerModeRef.current) {
        worker.postMessage({ type: 'zoom', factor, cx, cy })
      } else {
        const state = overrideRef?.current ?? stateRef.current
        if (state) {
          const cam = camRef.current
          const baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
          const next = Math.min(Math.max(cam.scale * factor, baseFit * MIN_SCALE_FACTOR), MAX_SCALE)
          const wx = (cx - cam.ox) / cam.scale
          const wy = (cy - cam.oy) / cam.scale
          cam.ox = cx - wx * next
          cam.oy = cy - wy * next
          cam.scale = next
        }
      }
    }

    const onDblClick = (ev: MouseEvent) => {
      if (ev.target !== canvas) return
      ev.preventDefault()
      const out = ev.shiftKey || ev.altKey
      const factor = out ? 1 / 1.8 : 1.8
      const cx = ev.clientX * dpr()
      const cy = ev.clientY * dpr()
      if (worker && isWorkerModeRef.current) {
        worker.postMessage({ type: 'zoom', factor, cx, cy })
      }
    }

    canvas.style.cursor = 'grab'
    canvas.addEventListener('pointerdown', onPointerDown)
    canvas.addEventListener('pointermove', onPointerMove)
    canvas.addEventListener('pointerup', onPointerUp)
    canvas.addEventListener('pointercancel', onPointerUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    canvas.addEventListener('dblclick', onDblClick)

    // Sync state and selection into worker or fallback loop
    let raf = 0
    const syncLoop = () => {
      raf = requestAnimationFrame(syncLoop)
      const state = overrideRef?.current ?? stateRef.current
      const selId = selectedRef?.current ?? null
      const selClanId = selectedClanRef?.current ?? null

      if (worker && isWorkerModeRef.current) {

        if (state) {
          worker.postMessage({ type: 'state', state })
        }
        worker.postMessage({ type: 'select', id: selId, clanId: selClanId })
      } else {
        // Fallback in-thread render loop
        const ctx = canvas.getContext('2d')
        if (ctx && state) {
          if (!camRef.current.initialized) {
            const baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
            camRef.current.scale = baseFit
            camRef.current.ox = (canvas.width - state.width * baseFit) / 2
            camRef.current.oy = (canvas.height - state.height * baseFit) / 2
            camRef.current.initialized = true
          }
          renderWorldFrame(
            ctx,
            state,
            canvas.width,
            canvas.height,
            camRef.current,
            selId,
            selClanId,
          )
        }
      }
    }
    raf = requestAnimationFrame(syncLoop)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      window.removeEventListener('flatworld-fit', onFit)
      window.removeEventListener('flatworld-zoom', onZoomEvent)
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('pointerup', onPointerUp)
      canvas.removeEventListener('pointercancel', onPointerUp)
      canvas.removeEventListener('wheel', onWheel)
      canvas.removeEventListener('dblclick', onDblClick)
      if (worker) {
        worker.terminate()
        workerRef.current = null
      }
    }
  }, [stateRef])

  return <canvas ref={canvasRef} className="world-canvas" />
}
