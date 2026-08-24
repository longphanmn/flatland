import { useEffect, useRef } from 'react'
import type { EntityState, StateMessage } from '../types'
import { houseWallSegments } from '../types'
import { TOTEMS } from '../totems'

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

export const EMOTE_ICONS: Record<string, string> = {
  hungry: '🍖',
  love: '❤️',
  combat: '⚔️',
  panic: '😱',
  heal: '🌿',
  cheer: '🏆',
  sleep: '💤',
  craft: '🧺',
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
  const isMobile = cw <= 768 || ('ontouchstart' in window)
  const drops = isMobile ? (weather === 'storm' ? 50 : 25) : (weather === 'storm' ? 120 : 60)
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

interface Camera {
  scale: number // device px per world unit
  ox: number
  oy: number
  initialized: boolean
}

interface Props {
  stateRef: React.RefObject<StateMessage | null>
  selectedRef?: React.RefObject<number | null>
  selectedClanRef?: React.RefObject<number | null>
  onTapCreature?: (id: number | null) => void
  /** When set, the canvas renders this frozen snapshot instead of the live world. */
  overrideRef?: React.RefObject<StateMessage | null>
}

export default function CanvasRenderer({ stateRef, selectedRef, selectedClanRef, onTapCreature, overrideRef }: Props) {
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

    const isMobileClient = typeof window !== 'undefined' && (window.innerWidth <= 768 || 'ontouchstart' in window)
    // T: cap DPR to 1.25 on mobile, 1.5 on desktop to keep GPU raster fill fast
    const dpr = () => Math.min(isMobileClient ? 1.25 : 1.5, window.devicePixelRatio || 1)

    const resize = () => {
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * dpr()))
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * dpr()))
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    let lastTrackedId: number | null = null
    let targetZoomScale: number | null = null
    let lastTrackedClanId: number | null = null
    let targetClanScale: number | null = null

    const fitCamera = (state: StateMessage) => {
      baseFit = Math.min(canvas.width / state.width, canvas.height / state.height)
      cam.scale = baseFit
      cam.ox = (canvas.width - state.width * cam.scale) / 2
      cam.oy = (canvas.height - state.height * cam.scale) / 2
      cam.initialized = true
      targetZoomScale = null
      lastTrackedId = null
      lastTrackedClanId = null
      targetClanScale = null
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
      if (selectedRef?.current != null) {
        targetZoomScale = next
      }
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

    let lastTap: { x: number; y: number; t: number } | null = null
    let longPressTimer: number | null = null
    let longPressFired = false
    const showQuickInfo = (clientX: number, clientY: number) => {
      const id = pickCreature(clientX, clientY)
      if (id === null) return
      const state = stateRef.current
      const ent = state?.entities.find(e => e.id === id)
      if (!ent) return
      // small quick-info tooltip near the creature (no inspector)
      const tip = document.createElement('div')
      tip.className = 'custom-tooltip'
      tip.style.left = `${clientX}px`
      tip.style.top = `${clientY - 12}px`
      tip.style.transform = 'translate(-50%, -100%)'
      tip.textContent = `${(ent as any).personal_name ?? ent.caste ?? 'Creature'} #${id} ${ent.caste ?? ''} ${ent.stage ?? ''}`.trim()
      document.body.appendChild(tip)
      setTimeout(() => tip.remove(), 1800)
      // also briefly highlight
      if (onTapCreature) {
        const prev = (selectedRef as any)?.current
        if (selectedRef) (selectedRef as any).current = id
        setTimeout(() => { if ((selectedRef as any) && (selectedRef as any).current === id) (selectedRef as any).current = prev ?? null }, 1200)
      }
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
      longPressFired = false
      if (longPressTimer) window.clearTimeout(longPressTimer)
      // long-press 500ms → quick info (keep pan/pinch/tap)
      longPressTimer = window.setTimeout(() => {
        if (tapStart && Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * dpr() < 10 * dpr()) {
          longPressFired = true
          showQuickInfo(tapStart.x, tapStart.y)
          // haptic feedback if available
          try { (navigator as any).vibrate?.(30) } catch {}
        }
      }, 500) as unknown as number
      canvas.style.cursor = 'grab'
      if (ev.cancelable) ev.preventDefault()
    }

    /** Screen-tap → nearest creature within a forgiving pick radius. */
    const pickCreature = (clientX: number, clientY: number): number | null => {
      const state = stateRef.current
      if (!state) return null
      const ratio = dpr()
      const px = clientX * ratio
      const py = clientY * ratio
      const pickRadiusWorld = Math.max(6.0, 44 / cam.scale)
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
      if (bestId !== null && bestD <= Math.max(28, pickRadiusWorld * cam.scale)) return bestId
      return null
    }

    const onPointerMove = (ev: PointerEvent) => {
      const prev = pointers.get(ev.pointerId)
      if (!prev || !cam.initialized) return
      const state = stateRef.current
      if (!state) return
      pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY })
      const ratio = dpr()
      // cancel long-press on move
      if (tapStart && Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * ratio > 10 * ratio) {
        if (longPressTimer) { window.clearTimeout(longPressTimer); longPressTimer = null }
      }
      if (pointers.size === 1) {
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
        if (longPressTimer) { window.clearTimeout(longPressTimer); longPressTimer = null }
        const [a, b] = twoPointers()
        const m = mid(a, b)
        const d = dist(a, b)
        if (lastMid && lastPinchDist > 0 && d > 0) {
          cam.ox += (m.x - lastMid.x) * ratio
          cam.oy += (m.y - lastMid.y) * ratio
          zoomAt(state, d / lastPinchDist, m.x * ratio, m.y * ratio)
        }
        lastPinchDist = d
        lastMid = m
      }
    }

    const onPointerUp = (ev: PointerEvent) => {
      pointers.delete(ev.pointerId)
      if (longPressTimer) { window.clearTimeout(longPressTimer); longPressTimer = null }
      if (pointers.size < 2) {
        lastPinchDist = 0
        lastMid = null
      }
      if (pointers.size === 0) canvas.style.cursor = 'grab'
      if (!tapStart || !onTapCreature) { tapStart = null; return }
      const isTap = performance.now() - tapStart.t < 500 && Math.hypot(ev.clientX - tapStart.x, ev.clientY - tapStart.y) * dpr() < 10 * dpr()
      if (!isTap) { tapStart = null; return }
      if (longPressFired) { longPressFired = false; tapStart = null; return }
      const now = performance.now()
      const isDoubleTap = lastTap && now - lastTap.t < 300 && Math.hypot(tapStart.x - lastTap.x, tapStart.y - lastTap.y) < 24
      if (isDoubleTap) {
        // double-tap → inspect + zoom to creature
        const id = pickCreature(tapStart.x, tapStart.y)
        if (id !== null) {
          onTapCreature(id)
          const st = stateRef.current
          const ent = st?.entities.find(e => e.id === id)
          if (ent && st) {
            // center and zoom in a bit
            const targetScale = Math.min(MAX_SCALE, cam.scale * 1.6)
            cam.ox = canvas.width / 2 - ent.x * targetScale
            cam.oy = canvas.height / 2 - ent.y * targetScale
            cam.scale = targetScale
            clampCamera(st)
          }
        }
        lastTap = null
      } else {
        // single tap → inspect
        onTapCreature(pickCreature(tapStart.x, tapStart.y))
        lastTap = { x: tapStart.x, y: tapStart.y, t: now }
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

    // §Y double-click zoom: plain = in, Shift/Alt+double-click = out (at the cursor)
    const onDblClick = (ev: MouseEvent) => {
      ev.preventDefault()
      const state = stateRef.current
      if (!state || !cam.initialized) return
      const out = ev.shiftKey || ev.altKey
      zoomAt(state, out ? 1 / 1.8 : 1.8, ev.clientX * dpr(), ev.clientY * dpr())
    }

    canvas.style.cursor = 'grab'
    canvas.addEventListener('pointerdown', onPointerDown)
    canvas.addEventListener('pointermove', onPointerMove)
    canvas.addEventListener('pointerup', onPointerUp)
    canvas.addEventListener('pointercancel', onPointerUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    canvas.addEventListener('dblclick', onDblClick)

    // ---- AF: High-performance batched drawing & LOD rendering ----
    const drawBatchedEntities = (
      ctx: CanvasRenderingContext2D,
      entities: EntityState[],
      visible: (x: number, y: number, r?: number) => boolean,
      camScale: number,
      selectedId: number | null,
    ) => {
      const isZoomedOut = camScale < 4.0
      const isVeryZoomedOut = camScale < 2.2
      const isDense = entities.length > 300

      // 1. Group visible entities into batch categories in a single pass
      const grassPlants: EntityState[] = []
      const berryPlants: EntityState[] = []
      const mushroomPlants: EntityState[] = []
      const poisonPlants: EntityState[] = []
      const corpses: EntityState[] = []
      const houses: EntityState[] = []
      const women: EntityState[] = []
      const polygonsByCaste: Map<string, EntityState[]> = new Map()
      const crestsByColor: Map<string, EntityState[]> = new Map()
      const sleepingCreatures: EntityState[] = []
      const hungryCreatures: EntityState[] = []
      const starvingCreatures: EntityState[] = []
      const infectedCreatures: EntityState[] = []
      const chilledCreatures: EntityState[] = []
      const glyphCreatures: EntityState[] = []
      const visibleCreatures: EntityState[] = []

      for (const e of entities) {
        const rad = (e as any).radius ?? (e as any).size ?? 1.5
        if (!visible(e.x, e.y, rad)) continue

        if (e.kind === 'food') {
          const v = e.variant ?? 'grass'
          if (v === 'berry') berryPlants.push(e)
          else if (v === 'mushroom') mushroomPlants.push(e)
          else if (v === 'poisonous') poisonPlants.push(e)
          else grassPlants.push(e)
          continue
        }

        if (e.kind === 'corpse') {
          corpses.push(e)
          continue
        }

        if (e.kind === 'house') {
          houses.push(e)
          continue
        }

        // Creature
        visibleCreatures.push(e)
        if (e.shape === 'line') {
          women.push(e)
        } else {
          const caste = e.caste || 'Soldier'
          let list = polygonsByCaste.get(caste)
          if (!list) {
            list = []
            polygonsByCaste.set(caste, list)
          }
          list.push(e)
        }

        if (e.clan_color) {
          let list = crestsByColor.get(e.clan_color)
          if (!list) {
            list = []
            crestsByColor.set(e.clan_color, list)
          }
          list.push(e)
        }

        if (e.sleeping && camScale >= 4.5) sleepingCreatures.push(e)
        if (camScale >= 1.8) {
          if (e.infected) infectedCreatures.push(e)
          if (e.status === 'starving') starvingCreatures.push(e)
          else if (e.status === 'hungry') hungryCreatures.push(e)
          if ((e.chill ?? 0) >= 12) chilledCreatures.push(e)
        }
        if (e.glyph && ((camScale >= 6.0 && !isDense) || selectedId === e.id)) glyphCreatures.push(e)
      }

      // 2. Draw Batched Houses
      for (const h of houses) {
        if (h.is_ruin) {
          const size = (h.size ?? 8) * 0.7
          ctx.strokeStyle = 'rgba(110,118,129,0.25)'
          ctx.lineWidth = 0.2
          ctx.setLineDash([0.8, 0.6])
          ctx.strokeRect(h.x - size / 2, h.y - size / 2, size, size)
          ctx.setLineDash([])
          ctx.fillStyle = 'rgba(110,118,129,0.08)'
          ctx.fillRect(h.x - size / 2, h.y - size / 2, size, size)
        } else {
          const size = h.size ?? 8
          const segs = houseWallSegments(
            h.x,
            h.y,
            size,
            h.door_side ?? 'south',
            h.door_width ?? 3,
            h.door_offset ?? 0,
          )
          ctx.strokeStyle = h.clan_color ?? '#8b949e'
          ctx.lineWidth = 0.35
          ctx.beginPath()
          for (const [ax, ay, bx, by] of segs) {
            ctx.moveTo(ax, ay)
            ctx.lineTo(bx, by)
          }
          ctx.stroke()
          if (h.clan_color) {
            ctx.fillStyle = h.clan_color
            ctx.globalAlpha = 0.18
            ctx.fillRect(h.x - size / 2, h.y - size / 2, size, 1.2)
            ctx.globalAlpha = 1
          }
        }
      }

      // 3. Draw Batched Plants by Variant
      const drawPlantBatch = (plants: EntityState[], fillStyle: string) => {
        if (plants.length === 0) return
        ctx.fillStyle = fillStyle
        ctx.beginPath()
        for (const f of plants) {
          const r = f.withering
            ? (0.35 + 0.55 * (f.growth ?? 0.15)) * 0.8
            : 0.35 + 0.55 * (f.growth ?? 0.15)
          ctx.moveTo(f.x + r, f.y)
          ctx.arc(f.x, f.y, r, 0, TAU)
        }
        ctx.fill()
      }

      drawPlantBatch(grassPlants, '#3fb950')
      drawPlantBatch(berryPlants, '#f85149')
      drawPlantBatch(mushroomPlants, '#a67c52')
      drawPlantBatch(poisonPlants, '#8957e5')

      // Poison halo
      if (poisonPlants.length > 0) {
        ctx.globalAlpha = 0.25
        ctx.strokeStyle = '#8957e5'
        ctx.lineWidth = 0.3
        ctx.beginPath()
        for (const f of poisonPlants) {
          const r = (0.35 + 0.55 * (f.growth ?? 0.15)) * 1.4
          ctx.moveTo(f.x + r, f.y)
          ctx.arc(f.x, f.y, r, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      // 4. Draw Batched Corpses
      if (corpses.length > 0) {
        ctx.strokeStyle = '#6e7681'
        ctx.globalAlpha = 0.8
        ctx.lineWidth = 0.3
        ctx.beginPath()
        for (const c of corpses) {
          ctx.moveTo(c.x - 1.1, c.y - 1.1)
          ctx.lineTo(c.x + 1.1, c.y + 1.1)
          ctx.moveTo(c.x - 1.1, c.y + 1.1)
          ctx.lineTo(c.x + 1.1, c.y - 1.1)
          ctx.moveTo(c.x + 0.5, c.y)
          ctx.arc(c.x, c.y, 0.5, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      // 5. Draw Batched Lines (Women)
      if (women.length > 0) {
        const color = CASTE_COLORS.Woman || '#ff9bce'
        ctx.strokeStyle = color
        ctx.lineWidth = 0.7
        ctx.beginPath()
        for (const w of women) {
          const stage = w.stage ?? 'adult'
          const sizeF = stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1.0
          const r = (w.radius ?? 0.9) * sizeF * (w.scale_jitter ?? 1)
          const len = Math.max(1.8, r * 2.4)
          const ang = w.angle + (w.angle_jitter ?? 0)
          const cosA = Math.cos(ang)
          const sinA = Math.sin(ang)
          ctx.moveTo(w.x - len * cosA, w.y - len * sinA)
          ctx.lineTo(w.x + len * cosA, w.y + len * sinA)
        }
        ctx.stroke()

        // Peace-cry ripples for visible women when zoomed in
        if (!isVeryZoomedOut && women.length < 150) {
          const nowTime = performance.now() / 900
          for (let i = 0; i < Math.min(women.length, 30); i++) {
            const w = women[i]
            const stage = w.stage ?? 'adult'
            const sizeF = stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1.0
            const r = (w.radius ?? 0.9) * sizeF * (w.scale_jitter ?? 1)
            const alphaF = stage === 'elder' ? 0.6 : 1.0
            const phase = (nowTime + w.id * 0.37) % 1
            ctx.globalAlpha = alphaF * 0.35 * (1 - phase)
            ctx.lineWidth = 0.25
            ctx.beginPath()
            ctx.arc(w.x, w.y, r * 1.6 + phase * 3.5, 0, TAU)
            ctx.stroke()
          }
          ctx.globalAlpha = 1
        }
      }

      // 6. Draw Batched Polygons by Caste (with LOD circle fallback when dense/zoomed-out)
      const useCircleLOD = isVeryZoomedOut || (isZoomedOut && isDense)
      for (const [caste, list] of polygonsByCaste.entries()) {
        const color = CASTE_COLORS[caste] || '#8b949e'

        // Single path for all fills and strokes of this caste
        ctx.beginPath()
        for (const c of list) {
          const stage = c.stage ?? 'adult'
          const sizeF = stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1.0
          const r = (c.radius ?? 1.2) * sizeF * (c.scale_jitter ?? 1)
          const sides = c.sides ?? 4
          const ang = c.angle + (c.angle_jitter ?? 0)

          if (useCircleLOD || sides >= PRIEST_SIDES) {
            ctx.moveTo(c.x + r, c.y)
            ctx.arc(c.x, c.y, r, 0, TAU)
          } else {
            const startAng = ang - Math.PI / 2
            for (let i = 0; i < sides; i++) {
              const a = startAng + (i / sides) * TAU
              const px = c.x + Math.cos(a) * r
              const py = c.y + Math.sin(a) * r
              if (i === 0) ctx.moveTo(px, py)
              else ctx.lineTo(px, py)
            }
            ctx.closePath()
          }
        }
        ctx.globalAlpha = 0.22
        ctx.fillStyle = color
        ctx.fill()
        ctx.globalAlpha = 1.0
        ctx.strokeStyle = color
        ctx.lineWidth = 0.3
        ctx.stroke()
      }

      // 7. Draw Batched Clan Crests
      for (const [clanColor, list] of crestsByColor.entries()) {
        ctx.globalAlpha = 0.85
        ctx.strokeStyle = clanColor
        ctx.lineWidth = 0.18
        ctx.beginPath()
        for (const c of list) {
          const stage = c.stage ?? 'adult'
          const sizeF = stage === 'infant' ? 0.55 : stage === 'juvenile' ? 0.8 : 1.0
          const r = (c.radius ?? 1.2) * sizeF + 0.45
          ctx.moveTo(c.x + r, c.y)
          ctx.arc(c.x, c.y, r, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      // 8. Draw Status Rings (Starving, Hungry, Infected, Chill)
      if (starvingCreatures.length > 0) {
        const pulse = 0.35 + 0.45 * Math.sin(performance.now() / 120)
        ctx.globalAlpha = pulse
        ctx.strokeStyle = '#f85149'
        ctx.lineWidth = 0.4
        ctx.beginPath()
        for (const c of starvingCreatures) {
          const r = (c.radius ?? 1.2) + 0.9
          ctx.moveTo(c.x + r, c.y)
          ctx.arc(c.x, c.y, r, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      if (hungryCreatures.length > 0) {
        ctx.globalAlpha = 0.65
        ctx.strokeStyle = '#d29922'
        ctx.lineWidth = 0.22
        ctx.beginPath()
        for (const c of hungryCreatures) {
          const r = (c.radius ?? 1.2) + 0.7
          ctx.moveTo(c.x + r, c.y)
          ctx.arc(c.x, c.y, r, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      if (infectedCreatures.length > 0) {
        const pulse = 0.4 + 0.3 * Math.sin(performance.now() / 180)
        ctx.globalAlpha = pulse
        ctx.strokeStyle = '#3fb950'
        ctx.lineWidth = 0.45
        ctx.beginPath()
        for (const c of infectedCreatures) {
          const r = (c.radius ?? 1.2) + 1.2
          ctx.moveTo(c.x + r, c.y)
          ctx.arc(c.x, c.y, r, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      if (chilledCreatures.length > 0) {
        ctx.globalAlpha = 0.55
        ctx.strokeStyle = '#79c0ff'
        ctx.lineWidth = 0.35
        ctx.beginPath()
        for (const c of chilledCreatures) {
          const r = (c.radius ?? 1.2) + 0.5
          ctx.moveTo(c.x + r, c.y)
          ctx.arc(c.x, c.y, r, 0, TAU)
        }
        ctx.stroke()
        ctx.globalAlpha = 1
      }

      // 9. Sleeping Markers (when zoomed in)
      if (sleepingCreatures.length > 0) {
        ctx.globalAlpha = 0.8
        ctx.fillStyle = '#c9d1d9'
        ctx.font = '1.6px ui-monospace, monospace'
        for (const c of sleepingCreatures) {
          const r = c.radius ?? 1.2
          ctx.fillText('z', c.x + r + 0.4, c.y - r - 0.2)
        }
        ctx.globalAlpha = 1
      }

      // 10. Soul-Code Glyphs (LOD-managed)
      if (glyphCreatures.length > 0) {
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.font = '1.2px ui-monospace, monospace'
        for (const c of glyphCreatures) {
          const isSel = selectedId === c.id
          ctx.globalAlpha = isSel ? 1 : 0.75
          ctx.fillStyle = isSel ? '#e6edf3' : 'rgba(230,237,243,0.85)'
          if (isSel) {
            ctx.strokeStyle = 'rgba(11,15,20,0.9)'
            ctx.lineWidth = 0.25
            ctx.strokeText(c.glyph!, c.x, c.y + 0.15)
          }
          ctx.fillText(c.glyph!, c.x, c.y + 0.15)
        }
        ctx.globalAlpha = 1
      }

      // 11. Held Equipment & Tools (LOD-managed)
      if (!isVeryZoomedOut) {
        for (const c of visibleCreatures) {
          if (!c.equipped_item) continue
          const r = c.radius ?? 1.2
          const ang = c.angle + (c.angle_jitter ?? 0)

          if (c.equipped_item === 'spear') {
            const tipX = c.x + Math.cos(ang) * (r + 1.8)
            const tipY = c.y + Math.sin(ang) * (r + 1.8)
            const baseX = c.x + Math.cos(ang) * (r - 0.4)
            const baseY = c.y + Math.sin(ang) * (r - 0.4)
            ctx.strokeStyle = '#d29922'
            ctx.lineWidth = 0.35
            ctx.beginPath()
            ctx.moveTo(baseX, baseY)
            ctx.lineTo(tipX, tipY)
            ctx.stroke()
            // spearhead
            ctx.fillStyle = '#ff7b72'
            ctx.beginPath()
            ctx.arc(tipX, tipY, 0.4, 0, TAU)
            ctx.fill()
          } else if (c.equipped_item === 'crown') {
            ctx.font = '1.7px ui-monospace, monospace'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'bottom'
            ctx.fillText('👑', c.x, c.y - r - 0.3)
          } else if (c.equipped_item === 'basket') {
            const bx = c.x + Math.cos(ang + Math.PI / 2) * (r + 0.6)
            const by = c.y + Math.sin(ang + Math.PI / 2) * (r + 0.6)
            ctx.font = '1.3px ui-monospace, monospace'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText('🧺', bx, by)
            if ((c.food_basket ?? 0) > 0) {
              ctx.fillStyle = '#3fb950'
              ctx.beginPath()
              ctx.arc(bx + 0.5, by - 0.5, 0.3, 0, TAU)
              ctx.fill()
            }
          } else if (c.equipped_item === 'herb_poultice') {
            const hx = c.x + Math.cos(ang - Math.PI / 2) * (r + 0.6)
            const hy = c.y + Math.sin(ang - Math.PI / 2) * (r + 0.6)
            ctx.font = '1.3px ui-monospace, monospace'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'middle'
            ctx.fillText('🌿', hx, hy)
          }
        }
      }

      // 12. Floating Emote Bubbles
      const nowTime = performance.now() / 1000
      for (const c of visibleCreatures) {
        if (!c.emote && !c.sleeping) continue
        const emoteKey = c.emote ?? (c.sleeping ? 'sleep' : null)
        if (!emoteKey) continue
        const icon = EMOTE_ICONS[emoteKey]
        if (!icon) continue

        const r = c.radius ?? 1.2
        const bob = Math.sin(nowTime * 4.5 + c.id * 0.7) * 0.3
        const bx = c.x
        const by = c.y - r - 2.2 + bob

        // speech bubble background
        ctx.fillStyle = 'rgba(13, 17, 23, 0.88)'
        ctx.strokeStyle = '#58a6ff'
        ctx.lineWidth = 0.25
        const bw = 2.8
        const bh = 2.4
        ctx.beginPath()
        ctx.roundRect(bx - bw / 2, by - bh / 2, bw, bh, 0.8)
        ctx.fill()
        ctx.stroke()

        // emoji text
        ctx.font = '1.6px ui-monospace, monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(icon, bx, by + 0.1)
      }

      return houses
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

      // Auto-zoom and follow selected creature or zoom-out to selected clan area
      const sel = selectedRef?.current ?? null
      const selClanId = selectedClanRef?.current ?? null

      if (sel !== null) {
        lastTrackedClanId = null
        targetClanScale = null
        const selEnt = state.entities.find((e) => e.id === sel && e.kind === 'creature')
        if (selEnt) {
          if (sel !== lastTrackedId) {
            lastTrackedId = sel
            // Zoom in on selection: at least 3.5x base fit, min 8.0 device px per world unit
            const minFollowScale = Math.min(MAX_SCALE, Math.max(baseFit * 3.5, 8.0))
            targetZoomScale = Math.max(cam.scale, minFollowScale)
          }

          // Smoothly glide camera to track creature when user is not actively panning/pinching
          if (pointers.size === 0 && !tapStart) {
            const desiredScale = targetZoomScale ?? cam.scale
            cam.scale += (desiredScale - cam.scale) * 0.12
            const targetOx = cw / 2 - selEnt.x * cam.scale
            const targetOy = ch / 2 - selEnt.y * cam.scale

            // Handle wrap jump vs smooth tracking
            if (Math.abs(targetOx - cam.ox) > cw * 0.75 || Math.abs(targetOy - cam.oy) > ch * 0.75) {
              cam.ox = targetOx
              cam.oy = targetOy
            } else {
              cam.ox += (targetOx - cam.ox) * 0.15
              cam.oy += (targetOy - cam.oy) * 0.15
            }
            clampCamera(state)
          }
        }
      } else if (selClanId !== null) {
        lastTrackedId = null
        targetZoomScale = null
        const clanHouses = state.entities.filter((e) => e.kind === 'house' && e.clan_id === selClanId && !e.is_ruin)
        const clanMembers = state.entities.filter((e) => e.kind === 'creature' && e.clan_id === selClanId)
        const clanEntities = clanHouses.length > 0 ? clanHouses : clanMembers

        if (clanEntities.length > 0) {
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
          for (const e of clanEntities) {
            if (e.x < minX) minX = e.x
            if (e.x > maxX) maxX = e.x
            if (e.y < minY) minY = e.y
            if (e.y > maxY) maxY = e.y
          }
          const pad = 24
          minX -= pad; maxX += pad
          minY -= pad; maxY += pad
          const spanX = Math.max(50, maxX - minX)
          const spanY = Math.max(50, maxY - minY)
          const centerX = (minX + maxX) / 2
          const centerY = (minY + maxY) / 2

          if (selClanId !== lastTrackedClanId) {
            lastTrackedClanId = selClanId
            // Zoom out to show full clan territory and surrounding area
            const fitClanScale = Math.min((cw * 0.8) / spanX, (ch * 0.8) / spanY)
            targetClanScale = Math.max(baseFit * 0.9, Math.min(fitClanScale, 3.6))
          }

          if (pointers.size === 0 && !tapStart) {
            const desiredScale = targetClanScale ?? cam.scale
            cam.scale += (desiredScale - cam.scale) * 0.08
            const targetOx = cw / 2 - centerX * cam.scale
            const targetOy = ch / 2 - centerY * cam.scale
            cam.ox += (targetOx - cam.ox) * 0.1
            cam.oy += (targetOy - cam.oy) * 0.1
            clampCamera(state)
          }
        }
      } else {
        lastTrackedId = null
        targetZoomScale = null
        lastTrackedClanId = null
        targetClanScale = null
      }

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
      // T: view bounds for culling (world coords)
      const padVL = 2
      const vL0 = -cam.ox / cam.scale - padVL
      const vR0 = (cw - cam.ox) / cam.scale + padVL
      const vT0 = -cam.oy / cam.scale - padVL
      const vB0 = (ch - cam.oy) / cam.scale + padVL
      const visible0 = (x: number, y: number, r = padVL) => x + r >= vL0 && x - r <= vR0 && y + r >= vT0 && y - r <= vB0
      // age tint — super-season bend
      if ((state as any).age) {
        const ageTint: Record<string, string> = {
          Golden: 'rgba(255,215,80,0.07)',
          Ice: 'rgba(150,200,255,0.09)',
          Chaos: 'rgba(180,80,255,0.06)',
          Plague: 'rgba(80,200,80,0.06)',
        }
        const at = ageTint[(state as any).age]
        if (at) {
          ctx.fillStyle = at
          ctx.fillRect(0, 0, cw, ch)
        }
      }
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

      // ---- territory: clan zones as faint circles around claimed houses (§P) (culled)
      for (const e of state.entities) {
        if (e.kind === 'house' && e.clan_id && !e.is_ruin && e.clan_color) {
          if (!visible0(e.x, e.y, 14)) continue
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

      // §Q/§X signals — ripples at caller position (culled); food green, alarm/help red, knowledge blue
      if ((state as any).signals) {
        const SIGNAL_COLOR: Record<string, string> = {
          food: '#3fb950',
          alarm: '#f85149',
          help: '#ffd166',
          knowledge: '#79c0ff',
        }
        for (const sg of (state as any).signals) {
          if (!visible0(sg.x, sg.y, 5)) continue
          const sx = cam.ox + sg.x * cam.scale
          const sy = cam.oy + sg.y * cam.scale
          const age = 15 - (sg.ttl ?? 0)
          const radius = (4 + age * 2.2) * (cam.scale / 12)
          const alpha = Math.max(0, 0.45 - age * 0.03)
          if (alpha <= 0) continue
          ctx.globalAlpha = alpha
          const signalColor = SIGNAL_COLOR[sg.kind] ?? '#f85149'
          ctx.strokeStyle = signalColor
          ctx.lineWidth = 1.2
          ctx.beginPath()
          ctx.arc(sx, sy, radius, 0, TAU)
          ctx.stroke()
          // small dot at sender
          ctx.globalAlpha = 0.9
          ctx.fillStyle = signalColor
          ctx.beginPath()
          ctx.arc(sx, sy, 2, 0, TAU)
          ctx.fill()
          ctx.globalAlpha = 1
        }
      }

      ctx.setTransform(cam.scale, 0, 0, cam.scale, cam.ox, cam.oy)
      // T: culling bounds in world coords (with 2-unit padding for radius)
      const pad = 2
      const vL = -cam.ox / cam.scale - pad
      const vR = (cw - cam.ox) / cam.scale + pad
      const vT = -cam.oy / cam.scale - pad
      const vB = (ch - cam.oy) / cam.scale + pad
      const visible = (x: number, y: number, r = pad) => x + r >= vL && x - r <= vR && y + r >= vT && y - r <= vB
      // §S wildfire — flame overlay at burning plants (culled)
      if ((state as any).fires) {
        for (const f of (state as any).fires) {
          if (!visible(f.x, f.y, f.r)) continue
          const alpha = Math.max(0.35, Math.min(0.9, f.ttl / 28))
          ctx.globalAlpha = alpha
          ctx.fillStyle = '#ff6b35'
          ctx.beginPath()
          ctx.arc(f.x, f.y, f.r * 0.9, 0, TAU)
          ctx.fill()
          ctx.strokeStyle = '#ffd166'
          ctx.lineWidth = 0.25
          ctx.stroke()
          // inner flame
          ctx.fillStyle = '#ffd166'
          ctx.globalAlpha = alpha * 0.85
          ctx.beginPath()
          ctx.arc(f.x, f.y, f.r * 0.45, 0, TAU)
          ctx.fill()
          ctx.globalAlpha = 1
        }
      }

      // AF: execute high-performance batched draws for all visible entities
      const selId = selectedRef?.current ?? null
      const visibleHouses = drawBatchedEntities(ctx, state.entities, visible, cam.scale, selId)
      // totem poles — small marker beside each claimed house (§P) (culled)
      for (const e of visibleHouses) {
        if (!e.clan_id || e.is_ruin) continue
        const clan = (state as any).clans?.[String(e.clan_id)]
        const totem: string | undefined = clan?.totem
        const isMain = e.is_main
        const size = e.size ?? 8
        const poleX = e.x + size / 2 + 1.2
        const poleY = e.y - size / 2 + 1.0
        ctx.save()
        ctx.translate(poleX, poleY)
        // pole
        ctx.fillStyle = isMain ? '#e3b341' : '#8b949e'
        ctx.fillRect(-0.2, -1.3, 0.4, 2.6)
        // totem icon (emoji, from the shared registry)
        const info = totem ? TOTEMS[totem] : null
        ctx.fillStyle = info?.color ?? '#e6edf3'
        ctx.font = isMain ? '2.1px ui-monospace, monospace' : '1.7px ui-monospace, monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText(info?.emoji ?? (isMain ? '👑' : '•'), 0, -1.8)
        if (isMain) {
          ctx.fillStyle = '#e3b341'
          ctx.font = '1.3px ui-monospace, monospace'
          ctx.fillText('👑', 0, -3.4)
        }
        ctx.restore()
      }
      // selection halo
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
          // name label above selection
          if ((selEnt as any).personal_name) {
            ctx.fillStyle = '#e6edf3'
            ctx.font = '2px ui-monospace, monospace'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'bottom'
            const titleSuffix = (selEnt as any).title ? ` ${(selEnt as any).title}` : ''
            const label = `${(selEnt as any).personal_name}${titleSuffix} ${(selEnt as any).glyph ?? ''}`
            ctx.strokeStyle = 'rgba(11,15,20,0.85)'
            ctx.lineWidth = 0.4
            ctx.strokeText(label, selEnt.x, selEnt.y - (selEnt.radius ?? 1.2) - 2.5)
            ctx.fillText(label, selEnt.x, selEnt.y - (selEnt.radius ?? 1.2) - 2.5)
          }
        }
      }

      // Clan territory overlay (prominent dashed border, area coverage, member halos, and banner)
      if (selClanId !== null) {
        const clan = (state as any).clans?.[String(selClanId)]
        const clanColor = clan?.color ?? '#58a6ff'
        const clanName = clan?.name ?? `Clan ${selClanId}`
        const clanTotem = clan?.totem
        const totemChar = (clanTotem && TOTEMS[clanTotem]?.emoji) || '🚩'

        const clanHouses = state.entities.filter((e) => e.kind === 'house' && e.clan_id === selClanId && !e.is_ruin)
        const clanMembers = state.entities.filter((e) => e.kind === 'creature' && e.clan_id === selClanId)

        // Accent halo around all living clan members
        for (const m of clanMembers) {
          ctx.strokeStyle = clanColor
          ctx.lineWidth = 0.35
          ctx.setLineDash([1.0, 0.8])
          ctx.beginPath()
          ctx.arc(m.x, m.y, (m.radius ?? 1.2) + 1.6, 0, TAU)
          ctx.stroke()
          ctx.setLineDash([])
        }

        // Highlight houses: Main House (Leader's Residence) has a prominent gold accent ring
        for (const h of clanHouses) {
          if (h.is_main) {
            ctx.strokeStyle = '#e3b341'
            ctx.lineWidth = 0.5
            ctx.setLineDash([2, 1.5])
            ctx.beginPath()
            ctx.arc(h.x, h.y, (h.size ?? 6) * 0.75, 0, TAU)
            ctx.stroke()
            ctx.setLineDash([])

            ctx.fillStyle = '#e3b341'
            ctx.font = '1.7px ui-monospace, monospace'
            ctx.textAlign = 'center'
            ctx.textBaseline = 'bottom'
            ctx.fillText('👑 Leader Main House', h.x, h.y - (h.size ?? 6) / 2 - 1.2)
          }
        }

        // Territory bounding envelope with dashed border
        const clanEntities = clanHouses.length > 0 ? clanHouses : clanMembers
        if (clanEntities.length > 0) {
          let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
          for (const e of clanEntities) {
            minX = Math.min(minX, e.x)
            maxX = Math.max(maxX, e.x)
            minY = Math.min(minY, e.y)
            maxY = Math.max(maxY, e.y)
          }
          const pad = 16
          minX -= pad; maxX += pad
          minY -= pad; maxY += pad

          // Territory area dashed border + tint
          ctx.strokeStyle = clanColor
          ctx.lineWidth = 0.55
          ctx.setLineDash([3.0, 2.0])
          ctx.strokeRect(minX, minY, maxX - minX, maxY - minY)
          ctx.fillStyle = clanColor
          ctx.globalAlpha = 0.06
          ctx.fillRect(minX, minY, maxX - minX, maxY - minY)
          ctx.globalAlpha = 1
          ctx.setLineDash([])

          // Territory banner at the top edge of clan area
          const midX = (minX + maxX) / 2
          const bannerY = minY - 2.8
          const bannerText = `${totemChar} ${clanName} (${clanMembers.length} members · ${clanHouses.length} houses)`

          ctx.font = '2.2px ui-monospace, monospace'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          const bw = Math.max(30, (bannerText.length * 1.35) + 4)
          const bh = 3.8

          ctx.fillStyle = 'rgba(13,17,23,0.92)'
          ctx.strokeStyle = clanColor
          ctx.lineWidth = 0.35
          ctx.fillRect(midX - bw / 2, bannerY - bh / 2, bw, bh)
          ctx.strokeRect(midX - bw / 2, bannerY - bh / 2, bw, bh)

          ctx.fillStyle = '#e6edf3'
          ctx.fillText(bannerText, midX, bannerY + 0.1)
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
      canvas.removeEventListener('dblclick', onDblClick)
    }
  }, [stateRef])

  return <canvas ref={canvasRef} className="world-canvas" />
}
