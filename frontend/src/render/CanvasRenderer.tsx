import { useEffect, useRef } from 'react'
import type { EntityState, StateMessage } from '../types'

const TAU = Math.PI * 2

/** Polygons with >= this many sides render as circles (backend PRIEST_SIDES). */
const PRIEST_SIDES = 24

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

interface Props {
  stateRef: React.RefObject<StateMessage | null>
}

export default function CanvasRenderer({ stateRef }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    let raf = 0

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * dpr))
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * dpr))
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)

    const drawEntity = (ctx: CanvasRenderingContext2D, e: EntityState) => {
      if (e.kind === 'food') {
        ctx.fillStyle = '#d29922'
        ctx.beginPath()
        ctx.arc(e.x, e.y, 0.7, 0, TAU)
        ctx.fill()
        return
      }
      if (e.kind === 'house') {
        const size = e.size ?? 6
        const half = size / 2
        ctx.strokeStyle = '#8b949e'
        ctx.lineWidth = 0.35
        ctx.strokeRect(e.x - half, e.y - half, size, size)
        // door notch on the south wall
        ctx.fillStyle = '#0b0f14'
        ctx.fillRect(e.x - 0.8, e.y + half - 0.35, 1.6, 0.7)
        return
      }
      const color = creatureColor(e)
      ctx.save()
      ctx.translate(e.x, e.y)
      ctx.rotate(e.angle)
      if (e.shape === 'line') {
        ctx.strokeStyle = color
        ctx.lineWidth = 0.8
        ctx.beginPath()
        ctx.moveTo(-2.4, 0)
        ctx.lineTo(2.4, 0)
        ctx.stroke()
      } else {
        const sides = e.sides ?? 4
        const r = 1.9
        ctx.beginPath()
        if (sides >= PRIEST_SIDES) ctx.arc(0, 0, r, 0, TAU)
        else tracePolygon(ctx, sides, r)
        ctx.globalAlpha = 0.22
        ctx.fillStyle = color
        ctx.fill()
        ctx.globalAlpha = 1
        ctx.strokeStyle = color
        ctx.lineWidth = 0.35
        ctx.stroke()
      }
      ctx.restore()
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

      const s = Math.min(cw / state.width, ch / state.height)
      const ox = (cw - state.width * s) / 2
      const oy = (ch - state.height * s) / 2

      // border
      ctx.strokeStyle = 'rgba(110,118,129,0.45)'
      ctx.lineWidth = 1
      ctx.strokeRect(ox, oy, state.width * s, state.height * s)

      // grid every 10 world units
      ctx.strokeStyle = 'rgba(110,118,129,0.12)'
      ctx.beginPath()
      for (let x = 10; x < state.width; x += 10) {
        ctx.moveTo(ox + x * s, oy)
        ctx.lineTo(ox + x * s, oy + state.height * s)
      }
      for (let y = 10; y < state.height; y += 10) {
        ctx.moveTo(ox, oy + y * s)
        ctx.lineTo(ox + state.width * s, oy + y * s)
      }
      ctx.stroke()

      ctx.setTransform(s, 0, 0, s, ox, oy)
      for (const e of state.entities) drawEntity(ctx, e)
      ctx.setTransform(1, 0, 0, 1, 0, 0)
    }

    raf = requestAnimationFrame(draw)
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [stateRef])

  return <canvas ref={canvasRef} className="world-canvas" />
}
