import { useEffect, useRef } from 'react'
import type { EntityState, StateMessage } from '../types'
import { houseWallSegments } from '../types'

const TAU = Math.PI * 2

/** Polygons with >= this many sides render as circles (backend PRIEST_SIDES). */
const PRIEST_SIDES = 24

const MIN_SCALE_FACTOR = 0.4 // can zoom out to half fit-size
const MAX_SCALE = 80 // device px per world unit

const CASTE_COLORS: Record<string, string> = {
  Soldier: '#ff7b72',
  Gentleman: '#ffa657',
  Professional: '#d2a8ff',
  Noble: '#79c0ff',
  Priest: '#e6edf3',
  Woman: '#ff9bce',
}

function creatureColor(e: EntityState): string {
  return (e.caste && CASTE_COLORS[e.caste]) || '#8b949e'
}

function tracePolygon(ctx: CanvasRenderingContext2D, sides: number, radius: number): void {
  ctx.beginPath()
  for (let i = 0; i < sides; i++) {
    const a = (i / sides) * TAU - Math.PI / 2
    const px = Math.cos(a) * radius
    const py = Math.sin(a) * radius
    if (i === 0) ctx.moveTo(px, py)
    else ctx.lineTo(px, py)
  }
  ctx.closePath()
}

interface Camera {
  scale: number // device px per world unit
  ox: number
  oy: number
  initialized: boolean
}

interface Props {
  stateRef: React.RefObject<StateMessage | null>
}

export default function CanvasRenderer({ stateRef }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const camRef = useRef<Camera>({ scale: 1, ox: 0, oy: 0, initialized: false })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const cam = camRef.current
    let raf = 0
    let baseFit = 1

    const dpr = () => window.devicePixelRatio || 1

    const resize = () => {
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * dpr()))
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * dpr()))
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    const fitCamera = (state: StateMessage) => {
      baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
      cam.scale = baseFit
      cam.ox = (canvas.width - state.width * cam.scale) / 2
      cam.oy = (canvas.height - state.height * cam.scale) / 2
      cam.initialized = true
    }

    const clampCamera = (state: StateMessage) => {
      const cxw = (canvas.width / 2 - cam.ox) / cam.scale
      const cyw = (canvas.height / 2 - cam.oy) / cam.scale
      const tx = Math.min(Math.max(cxw, 0), state.width)
      const ty = Math.min(Math.max(cyw, 0), state.height)
      cam.ox += (tx - cxw) * cam.scale
      cam.oy += (ty - cyw) * cam.scale
    }

    const zoomAt = (state: StateMessage, factor: number, ax: number, ay: number) => {
      const next = Math.min(
        Math.max(cam.scale * factor, baseFit * MIN_SCALE_FACTOR),
        MAX_SCALE,
      )
      const wx = (ax - cam.ox) / cam.scale
      const wy = (ay - cam.oy) / cam.scale
      cam.ox = ax - wx * next
      cam.oy = ay - wy * next
      cam.scale = next
      clampCamera(state)
    }

    const onFit = () => {
      const st = stateRef.current
      if (st) fitCamera(st)
    }
    window.addEventListener('flatworld-fit', onFit)

    // ---- unified pointer interaction: drag pan, wheel zoom, pinch zoom ----
    interface P {
      x: number
      y: number
    }
    const pointers = new Map<number, P>()
    let lastPinchDist = 0
    let lastMid: P | null = null

    const dist = (a: P, b: P): number => Math.hypot(a.x - b.x, a.y - b.y)
    const mid = (a: P, b: P): P => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 })

    const twoPointers = (): [P, P] => {
      const it = [...pointers.values()]
      return [it[0], it[1]]
    }

    const onPointerDown = (ev: PointerEvent) => {
      canvas.setPointerCapture(ev.pointerId)
      pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })
      if (pointers.size === 2) {
        const [a, b] = twoPointers()
        lastPinchDist = dist(a, b)
        lastMid = mid(a, b)
      }
      canvas.style.cursor = 'grabbing'
    }

    const onPointerMove = (ev: PointerEvent) => {
      const prev = pointers.get(ev.pointerId)
      if (!prev || !cam.initialized) return
      const state = stateRef.current
      if (!state) return
      pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })
      const ratio = dpr()

      if (pointers.size === 1) {
        cam.ox += (ev.clientX - prev.x) * ratio
        cam.oy += (ev.clientY - prev.y) * ratio
        clampCamera(state)
        return
      }
      if (pointers.size >= 2) {
        const [a, b] = twoPointers()
        const m = mid(a, b)
        const d = dist(a, b)
        if (lastMid && lastPinchDist > 0 && d > 0) {
          // pan with midpoint motion...
          cam.ox += (m.x - lastMid.x) * ratio
          cam.oy += (m.y - lastMid.y) * ratio
          // ...then zoom anchored at the midpoint
          zoomAt(state, d / lastPinchDist, m.x * ratio, m.y * ratio)
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
      if (pointers.size === 0) canvas.style.cursor = 'grab'
    }

    const onWheel = (ev: WheelEvent) => {
      ev.preventDefault()
      const state = stateRef.current
      if (!state || !cam.initialized) return
      const factor = Math.exp(-ev.deltaY * 0.0015)
      zoomAt(state, factor, ev.clientX * dpr(), ev.clientY * dpr())
    }

    canvas.style.cursor = 'grab'
    canvas.addEventListener('pointerdown', onPointerDown)
    canvas.addEventListener('pointermove', onPointerMove)
    canvas.addEventListener('pointerup', onPointerUp)
    canvas.addEventListener('pointercancel', onPointerUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })

    // ---- drawing ----
    const drawEntity = (ctx: CanvasRenderingContext2D, e: EntityState) => {
      if (e.kind === 'food') {
        ctx.fillStyle = '#d29922'
        ctx.beginPath()
        ctx.arc(e.x, e.y, 0.7, 0, TAU)
        ctx.fill()
        return
      }
      if (e.kind === 'house') {
        const size = e.size ?? 8
        const segs = houseWallSegments(
          e.x,
          e.y,
          size,
          e.door_side ?? 'south',
          e.door_width ?? 3,
          e.door_offset ?? 0,
        )
        ctx.strokeStyle = '#8b949e'
        ctx.lineWidth = 0.35
        ctx.beginPath()
        for (const [ax, ay, bx, by] of segs) {
          ctx.moveTo(ax, ay)
          ctx.lineTo(bx, by)
        }
        ctx.stroke()
        return
      }
      const color = creatureColor(e)
      const r = e.radius ?? 1.2
      ctx.save()
      ctx.translate(e.x, e.y)
      ctx.rotate(e.angle)
      if (e.shape === 'line') {
        ctx.strokeStyle = color
        ctx.lineWidth = 0.7 * Math.max(0.75, r / 1.2)
        ctx.beginPath()
        const len = Math.max(1.8, r * 2.4)
        ctx.moveTo(-len, 0)
        ctx.lineTo(len, 0)
        ctx.stroke()
      } else {
        const sides = e.sides ?? 4
        ctx.beginPath()
        if (sides >= PRIEST_SIDES) ctx.arc(0, 0, r, 0, TAU)
        else tracePolygon(ctx, sides, r)
        ctx.globalAlpha = 0.22
        ctx.fillStyle = color
        ctx.fill()
        ctx.globalAlpha = 1
        ctx.strokeStyle = color
        ctx.lineWidth = 0.3
        ctx.stroke()
      }
      ctx.restore()
      if (e.status === 'hungry') {
        ctx.globalAlpha = 0.65
        ctx.strokeStyle = '#d29922'
        ctx.lineWidth = 0.22
        ctx.beginPath()
        ctx.arc(e.x, e.y, r + 0.7, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = 1
      } else if (e.status === 'starving') {
        const pulse = 0.35 + 0.45 * Math.sin(performance.now() / 120)
        ctx.globalAlpha = pulse
        ctx.strokeStyle = '#f85149'
        ctx.lineWidth = 0.4
        ctx.beginPath()
        ctx.arc(e.x, e.y, r + 0.9, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = 1
      }
    }

    const draw = () => {
      raf = requestAnimationFrame(draw)
      const state = stateRef.current
      const cw = canvas.width
      const ch = canvas.height

      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.fillStyle = '#0b0f14'
      ctx.fillRect(0, 0, cw, ch)
      if (!state) return

      if (!cam.initialized || cam.scale <= 0) fitCamera(state)

      ctx.strokeStyle = 'rgba(110,118,129,0.45)'
      ctx.lineWidth = 1
      ctx.strokeRect(cam.ox, cam.oy, state.width * cam.scale, state.height * cam.scale)

      // adaptive grid: pick step so lines stay >= ~28 device px apart
      let step = 5
      while (step * cam.scale < 28 && step < 100) step *= 2
      ctx.strokeStyle = 'rgba(110,118,129,0.12)'
      ctx.beginPath()
      for (let x = step; x < state.width; x += step) {
        ctx.moveTo(cam.ox + x * cam.scale, cam.oy)
        ctx.lineTo(cam.ox + x * cam.scale, cam.oy + state.height * cam.scale)
      }
      for (let y = step; y < state.height; y += step) {
        ctx.moveTo(cam.ox, cam.oy + y * cam.scale)
        ctx.lineTo(cam.ox + state.width * cam.scale, cam.oy + y * cam.scale)
      }
      ctx.stroke()

      ctx.setTransform(cam.scale, 0, 0, cam.scale, cam.ox, cam.oy)
      for (const e of state.entities) drawEntity(ctx, e)
      ctx.setTransform(1, 0, 0, 1, 0, 0)
    }
    raf = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      window.removeEventListener('flatworld-fit', onFit)
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('pointerup', onPointerUp)
      canvas.removeEventListener('pointercancel', onPointerUp)
      canvas.removeEventListener('wheel', onWheel)
    }
  }, [stateRef])

  return <canvas ref={canvasRef} className="world-canvas" />
}
