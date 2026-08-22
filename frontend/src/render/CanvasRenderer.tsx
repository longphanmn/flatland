import { useEffect, useRef } from 'react'
import type { EntityState, StateMessage } from '../types'
import { houseWallSegments } from '../types'

const TAU = Math.PI * 2

/** Polygons with >= this many sides render as circles (backend PRIEST_SIDES). */
const PRIEST_SIDES = 24

const MIN_SCALE_FACTOR = 0.4 // can zoom out to half fit-size
const MAX_SCALE = 80 // device px per world unit

export const CASTE_COLORS: Record<string, string> = {
  Soldier: '#ff7b72',
  Artisan: '#f2cc60',
  Gentleman: '#ffa657',
  Professional: '#d2a8ff',
  Noble: '#79c0ff',
  Priest: '#e6edf3',
  Woman: '#ff9bce',
  Predator: '#ff3838',
  Herbivore: '#90be6d',
}

function creatureColor(e: EntityState): string {
  return (e.caste && CASTE_COLORS[e.caste]) || '#8b949e'
}

/** Rain streaks and fog veil, drawn in screen space. */
function drawWeather(
  ctx: CanvasRenderingContext2D,
  weather: string,
  cw: number,
  ch: number,
): void {
  if (weather === 'fog') {
    ctx.fillStyle = 'rgba(190,205,225,0.13)'
    ctx.fillRect(0, 0, cw, ch)
    return
  }
  if (weather !== 'rain' && weather !== 'storm') return
  const drops = weather === 'storm' ? 150 : 80
  const t = performance.now() / 16
  ctx.strokeStyle = 'rgba(140,170,220,0.35)'
  ctx.lineWidth = Math.max(1, cw / 1200)
  ctx.beginPath()
  for (let i = 0; i < drops; i++) {
    const x = (i * 977 + t * (13 + (i % 5))) % cw
    const y = (i * 613 + t * (23 + (i % 7) * 3)) % ch
    ctx.moveTo(x, y)
    ctx.lineTo(x - cw * 0.004, y + ch * 0.02)
  }
  ctx.stroke()
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
  selectedRef?: React.RefObject<number | null>
  onTapCreature?: (id: number | null) => void
  /** When set, the canvas renders this frozen snapshot instead of the live world. */
  overrideRef?: React.RefObject<StateMessage | null>
}

export default function CanvasRenderer({ stateRef, selectedRef, onTapCreature, overrideRef }: Props) {
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

    /** Keyboard zoom: window dispatches 'flatworld-zoom' with {factor}. */
    const onZoomEvent = (ev: Event) => {
      const state = stateRef.current
      if (!state || !cam.initialized) return
      const factor = (ev as CustomEvent<{ factor?: number }>).detail?.factor ?? 1.2
      zoomAt(state, factor, canvas.width / 2, canvas.height / 2)
    }
    window.addEventListener('flatworld-zoom', onZoomEvent)

    // ---- unified pointer interaction: drag pan, wheel zoom, pinch zoom ----
    interface P {
      x: number
      y: number
    }
    const pointers = new Map<number, P>()
    let lastPinchDist = 0
    let lastMid: P | null = null
    let tapStart: { x: number; y: number; t: number } | null = null

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
      tapStart = { x: ev.clientX, y: ev.clientY, t: performance.now() }
      canvas.style.cursor = 'grab'
      // prevent scroll/zoom at edge of screen from swallowing the tap
      if (ev.cancelable) ev.preventDefault()
    }

    /** Screen-tap → nearest creature within a forgiving pick radius. */
    const pickCreature = (clientX: number, clientY: number): number | null => {
      const state = stateRef.current
      if (!state) return null
      const ratio = dpr()
      const px = clientX * ratio
      const py = clientY * ratio
      const pickRadiusWorld = Math.max(4.0, 24 / cam.scale)
      let bestId: number | null = null
      let bestD = Infinity
      for (const e of state.entities) {
        if (e.kind !== 'creature') continue
        const sx = cam.ox + e.x * cam.scale
        const sy = cam.oy + e.y * cam.scale
        const d = Math.hypot(sx - px, sy - py)
        if (d < bestD) {
          bestD = d
          bestId = e.id
        }
      }
      if (bestId !== null && bestD <= pickRadiusWorld * cam.scale) return bestId
      return null
    }

    const onPointerMove = (ev: PointerEvent) => {
      const prev = pointers.get(ev.pointerId)
      if (!prev || !cam.initialized) return
      const state = stateRef.current
      if (!state) return
      pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })
      const ratio = dpr()

      if (pointers.size === 1) {
        // Dead zone: small moves are still taps, not drags (fixes edge-tap → hand/drag)
        if (tapStart) {
          const dragDist = Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * ratio
          if (dragDist < 6 * ratio) return
        }
        canvas.style.cursor = 'grabbing'
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
      // A short, still press is a tap → select the nearest creature.
      // Use the original tap position (not release) so a slight drag doesn't miss the creature.
      if (
        tapStart &&
        onTapCreature &&
        performance.now() - tapStart.t < 500 &&
        Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * dpr() <
          10 * dpr()
      ) {
        onTapCreature(pickCreature(tapStart.x, tapStart.y))
      }
      tapStart = null
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
        const variantColors: Record<string, string> = {
          grass: '#3fb950',
          berry: '#f85149',
          mushroom: '#a67c52',
          poisonous: '#8957e5',
        }
        ctx.fillStyle = variantColors[e.variant ?? 'grass'] ?? '#d29922'
        // size ∝ growth (sprout 0.15 small, mature 1.0 full)
        const r = 0.35 + 0.55 * (e.growth ?? 0.15)
        ctx.beginPath()
        ctx.arc(e.x, e.y, r, 0, TAU)
        ctx.fill()
        // poisonous: faint purple halo
        if (e.variant === 'poisonous') {
          ctx.globalAlpha = 0.25
          ctx.strokeStyle = '#8957e5'
          ctx.lineWidth = 0.3
          ctx.stroke()
          ctx.globalAlpha = 1
        }
        return
      }
      if (e.kind === 'corpse') {
        // small remains: a dim cross that fades with its remaining life
        ctx.strokeStyle = '#6e7681'
        ctx.globalAlpha = 0.8
        ctx.lineWidth = 0.3
        ctx.beginPath()
        ctx.moveTo(e.x - 1.1, e.y - 1.1)
        ctx.lineTo(e.x + 1.1, e.y + 1.1)
        ctx.moveTo(e.x - 1.1, e.y + 1.1)
        ctx.lineTo(e.x + 1.1, e.y - 1.1)
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(e.x, e.y, 0.5, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = 1
        return
      }
      if (e.kind === 'house') {
        if (e.is_ruin) {
          // ruins: faint collapsed square, no walls/door
          const size = (e.size ?? 8) * 0.7
          ctx.strokeStyle = 'rgba(110,118,129,0.25)'
          ctx.lineWidth = 0.2
          ctx.setLineDash([0.8, 0.6])
          ctx.strokeRect(e.x - size / 2, e.y - size / 2, size, size)
          ctx.setLineDash([])
          ctx.fillStyle = 'rgba(110,118,129,0.08)'
          ctx.fillRect(e.x - size / 2, e.y - size / 2, size, size)
          return
        }
        const size = e.size ?? 8
        const segs = houseWallSegments(
          e.x,
          e.y,
          size,
          e.door_side ?? 'south',
          e.door_width ?? 3,
          e.door_offset ?? 0,
        )
        ctx.strokeStyle = e.clan_color ?? '#8b949e'
        ctx.lineWidth = 0.35
        ctx.beginPath()
        for (const [ax, ay, bx, by] of segs) {
          ctx.moveTo(ax, ay)
          ctx.lineTo(bx, by)
        }
        ctx.stroke()
        // clan crest on wall (settlement)
        if (e.clan_color) {
          ctx.fillStyle = e.clan_color
          ctx.globalAlpha = 0.18
          ctx.fillRect(e.x - size / 2, e.y - size / 2, size, 1.2)
          ctx.globalAlpha = 1
        }
        return
      }
      const color = creatureColor(e)
      const stage = e.stage ?? 'adult'
      const sizeF = stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1.0
      const alphaF = stage === 'elder' ? 0.6 : 1.0
      const r = (e.radius ?? 1.2) * sizeF
      ctx.save()
      ctx.globalAlpha = alphaF
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
        // peace-cry: women announce themselves as they move (Flatland law)
        const phase = ((performance.now() / 900 + e.id * 0.37) % 1)
        ctx.globalAlpha = alphaF * 0.35 * (1 - phase)
        ctx.lineWidth = 0.25
        ctx.beginPath()
        ctx.arc(0, 0, r * 1.6 + phase * 3.5, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = alphaF
      } else {
        const sides = e.sides ?? 4
        ctx.beginPath()
        if (sides >= PRIEST_SIDES) ctx.arc(0, 0, r, 0, TAU)
        else tracePolygon(ctx, sides, r)
        ctx.globalAlpha = alphaF * 0.22
        ctx.fillStyle = color
        ctx.fill()
        ctx.globalAlpha = alphaF
        ctx.strokeStyle = color
        ctx.lineWidth = 0.3
        ctx.stroke()
      }
      ctx.restore()
      // sleeping: little z's drift above the sleeper
      if (e.sleeping) {
        ctx.globalAlpha = 0.8
        ctx.fillStyle = '#c9d1d9'
        ctx.font = `${1.6}px ui-monospace, monospace`
        ctx.fillText('z', r + 0.4, -r - 0.2)
        ctx.font = `${1.1}px ui-monospace, monospace`
        ctx.fillText('z', r + 1.5, -r - 1.3)
        ctx.globalAlpha = 1
      }
      // clan crest: a thin tinted ring for those who belong to a line
      if (e.clan_color) {
        ctx.globalAlpha = 0.85
        ctx.strokeStyle = e.clan_color
        ctx.lineWidth = 0.18
        ctx.beginPath()
        ctx.arc(e.x, e.y, (e.radius ?? 1.2) * sizeF + 0.45, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = 1
      }
      if (e.infected) {
        const pulse = 0.4 + 0.3 * Math.sin(performance.now() / 180)
        ctx.globalAlpha = pulse
        ctx.strokeStyle = '#3fb950'
        ctx.lineWidth = 0.45
        ctx.beginPath()
        ctx.arc(e.x, e.y, r + 1.2, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = 1
      }
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
      const state = overrideRef?.current ?? stateRef.current
      const cw = canvas.width
      const ch = canvas.height

      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.fillStyle = '#0b0f14'
      ctx.fillRect(0, 0, cw, ch)
      if (!state) return

      if (!cam.initialized || cam.scale <= 0) fitCamera(state)

      // ---- sky: night darkness + season tint + weather overlays ----
      const sun = Math.sin((state.time_of_day - 0.25) * TAU) // -1 midnight .. 1 noon
      const darkness = Math.max(0, Math.min(1, 0.55 - 0.55 * sun))
      if (darkness > 0.01) {
        ctx.fillStyle = `rgba(4,8,24,${(darkness * 0.45).toFixed(3)})`
        ctx.fillRect(0, 0, cw, ch)
      }
      const seasonTint: Record<string, string> = {
        spring: 'rgba(80,160,90,0.05)',
        summer: 'rgba(220,180,60,0.05)',
        autumn: 'rgba(200,120,50,0.06)',
        winter: 'rgba(150,190,255,0.08)',
      }
      ctx.fillStyle = seasonTint[state.season] ?? 'rgba(0,0,0,0)'
      ctx.fillRect(0, 0, cw, ch)
      drawWeather(ctx, state.weather, cw, ch)

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

      // ---- terrain: fertile grounds then rocks, under everything else ----
      for (const p of state.terrain_fertile ?? []) {
        ctx.fillStyle = 'rgba(80,160,90,0.10)'
        ctx.beginPath()
        ctx.arc(cam.ox + p.x * cam.scale, cam.oy + p.y * cam.scale, p.r * cam.scale, 0, TAU)
        ctx.fill()
      }
      for (const r of state.terrain_rocks ?? []) {
        ctx.fillStyle = '#30363d'
        ctx.strokeStyle = '#6e7681'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.arc(cam.ox + r.x * cam.scale, cam.oy + r.y * cam.scale, r.r * cam.scale, 0, TAU)
        ctx.fill()
        ctx.stroke()
      }

      // ---- territory: clan zones as faint circles around claimed houses (§P)
      for (const e of state.entities) {
        if (e.kind === 'house' && e.clan_id && !e.is_ruin && e.clan_color) {
          const tr = 14 // territory_radius default; matches config.py: territory_radius
          ctx.fillStyle = e.clan_color
          ctx.globalAlpha = 0.07
          ctx.beginPath()
          ctx.arc(cam.ox + e.x * cam.scale, cam.oy + e.y * cam.scale, tr * cam.scale, 0, TAU)
          ctx.fill()
          ctx.globalAlpha = 0.18
          ctx.strokeStyle = e.clan_color
          ctx.lineWidth = 1
          ctx.setLineDash([5, 4])
          ctx.beginPath()
          ctx.arc(cam.ox + e.x * cam.scale, cam.oy + e.y * cam.scale, tr * cam.scale, 0, TAU)
          ctx.stroke()
          ctx.setLineDash([])
          ctx.globalAlpha = 1
        }
      }

      ctx.setTransform(cam.scale, 0, 0, cam.scale, cam.ox, cam.oy)
      for (const e of state.entities) drawEntity(ctx, e)
      // totem poles — small marker beside each claimed house (§P)
      for (const e of state.entities) {
        if (e.kind !== 'house' || !e.clan_id || e.is_ruin) continue
        const clan = (state as any).clans?.[String(e.clan_id)]
        const totem: string | undefined = clan?.totem
        if (!totem) continue
        const size = e.size ?? 8
        const poleX = e.x + size / 2 + 1.2
        const poleY = e.y - size / 2 + 1.0
        ctx.save()
        ctx.translate(poleX, poleY)
        // pole
        ctx.fillStyle = '#8b949e'
        ctx.fillRect(-0.18, -1.2, 0.36, 2.4)
        // totem icon
        const iconMap: Record<string, string> = { Wolf: '▲', Tree: '♣', Shield: '⬢', Eye: '◉' }
        const colorMap: Record<string, string> = { Wolf: '#ff7b72', Tree: '#3fb950', Shield: '#79c0ff', Eye: '#d2a8ff' }
        ctx.fillStyle = colorMap[totem] ?? '#e6edf3'
        ctx.font = '1.6px ui-monospace, monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(iconMap[totem] ?? '•', 0, -1.6)
        ctx.restore()
      }
      // selection halo
      const sel = selectedRef?.current ?? null
      if (sel !== null) {
        const selEnt = state.entities.find((e) => e.id === sel)
        if (selEnt) {
          ctx.strokeStyle = '#e3b341'
          ctx.lineWidth = 0.4
          ctx.setLineDash([1.2, 0.8])
          ctx.beginPath()
          ctx.arc(selEnt.x, selEnt.y, (selEnt.radius ?? 1.2) + 2.0, 0, TAU)
          ctx.stroke()
          ctx.setLineDash([])
        }
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0)
    }
    raf = requestAnimationFrame(draw)

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
    }
  }, [stateRef])

  return <canvas ref={canvasRef} className="world-canvas" />
}
