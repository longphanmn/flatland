import type { EntityState, StateMessage } from '../types'
import { houseWallSegments } from '../types'
import { TOTEMS } from '../totems'

export const TAU = Math.PI * 2
export const PRIEST_SIDES = 24
export const MIN_SCALE_FACTOR = 0.4
export const MAX_SCALE = 80

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

export interface Camera {
  scale: number
  ox: number
  oy: number
  initialized: boolean
}

export function drawWeather(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
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
  const isMobile = cw <= 768
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

export function drawBatchedEntities(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
  entities: EntityState[],
  visible: (x: number, y: number, r?: number) => boolean,
  camScale: number,
  selectedId: number | null,
  tick = 0,
): EntityState[] {
  const isZoomedOut = camScale < 4.0
  const isVeryZoomedOut = camScale < 2.2
  const isDense = entities.length > 300

  const grassPlants: EntityState[] = []
  const grainPlants: EntityState[] = []
  const berryPlants: EntityState[] = []
  const herbPlants: EntityState[] = []
  const mushroomPlants: EntityState[] = []
  const poisonPlants: EntityState[] = []
  const cultivatedPlants: EntityState[] = []
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
      if ((e as any).cultivated) {
        cultivatedPlants.push(e) // §AM sown fields read as wheat-gold
        continue
      }
      const v = e.variant ?? 'grass'
      if (v === 'grain') grainPlants.push(e)
      else if (v === 'berry') berryPlants.push(e)
      else if (v === 'medicinal_herb') herbPlants.push(e)
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

  // Draw Houses
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
      // §AT-3: brief takeover flash — an expanding ring fades over ~90 ticks
      const tAge = h.takeover_age
      if (tAge !== null && tAge !== undefined && tAge >= 0 && tAge < 90) {
        const fade = 1 - tAge / 90
        ctx.strokeStyle = h.clan_color ?? '#f85149'
        ctx.globalAlpha = 0.7 * fade
        ctx.lineWidth = 0.25 + 0.5 * fade
        ctx.beginPath()
        ctx.arc(h.x, h.y, size / 2 + 1.5 + tAge * 0.06, 0, TAU)
        ctx.stroke()
        ctx.globalAlpha = 1
      }
      // §AQ PH-1: a lit hearth — warm glow and a flame dot on the floor
      if (h.hearth_lit) {
        const flick = 0.85 + 0.3 * Math.sin(tick * 0.7 + h.x)
        ctx.fillStyle = 'rgba(255,158,60,0.16)'
        ctx.beginPath()
        ctx.arc(h.x, h.y, size * 0.42 * flick, 0, TAU)
        ctx.fill()
        ctx.fillStyle = '#ffa657'
        ctx.beginPath()
        ctx.arc(h.x, h.y, 0.9 * flick, 0, TAU)
        ctx.fill()
        ctx.fillStyle = '#ffe08a'
        ctx.beginPath()
        ctx.arc(h.x, h.y - 0.2, 0.45, 0, TAU)
        ctx.fill()
      }
    }
  }

  // Draw Plants
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
  drawPlantBatch(grainPlants, '#e3b341')
  drawPlantBatch(berryPlants, '#f85149')
  drawPlantBatch(herbPlants, '#2ea043')
  drawPlantBatch(mushroomPlants, '#a67c52')
  drawPlantBatch(poisonPlants, '#8957e5')
  drawPlantBatch(cultivatedPlants, '#d8c341')


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

  // Draw Corpses
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

  // Draw Women (Lines)
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
  }

  // Draw Polygons
  const useCircleLOD = isVeryZoomedOut || (isZoomedOut && isDense)
  for (const [caste, list] of polygonsByCaste.entries()) {
    const color = CASTE_COLORS[caste] || '#8b949e'
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

  // Draw Crests
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

  // Draw Status Rings
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

  // Draw Sleeping Markers
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

  // Draw Glyphs
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

  // Draw Items
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

  // Draw Thought Emotes
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

    ctx.fillStyle = 'rgba(13, 17, 23, 0.88)'
    ctx.strokeStyle = '#58a6ff'
    ctx.lineWidth = 0.25
    const bw = 2.8
    const bh = 2.4
    ctx.beginPath()
    ctx.roundRect(bx - bw / 2, by - bh / 2, bw, bh, 0.8)
    ctx.fill()
    ctx.stroke()

    ctx.font = '1.6px ui-monospace, monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(icon, bx, by + 0.1)
  }

  return houses
}

export function renderWorldFrame(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
  state: StateMessage,
  cw: number,
  ch: number,
  cam: Camera,
  selectedId: number | null,
  selectedClanId: number | null,
): void {
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.fillStyle = '#0b0f14'
  ctx.fillRect(0, 0, cw, ch)

  // Sky tint
  const sun = Math.sin((state.time_of_day - 0.25) * TAU)
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

  const padVL = 2
  const vL0 = -cam.ox / cam.scale - padVL
  const vR0 = (cw - cam.ox) / cam.scale + padVL
  const vT0 = -cam.oy / cam.scale - padVL
  const vB0 = (ch - cam.oy) / cam.scale + padVL
  const visible0 = (x: number, y: number, r = padVL) =>
    x + r >= vL0 && x - r <= vR0 && y + r >= vT0 && y - r <= vB0

  if (state.age) {
    const ageTint: Record<string, string> = {
      Golden: 'rgba(255,215,80,0.07)',
      Ice: 'rgba(150,200,255,0.09)',
      Chaos: 'rgba(180,80,255,0.06)',
      Plague: 'rgba(80,200,80,0.06)',
    }
    const at = ageTint[state.age]
    if (at) {
      ctx.fillStyle = at
      ctx.fillRect(0, 0, cw, ch)
    }
  }

  drawWeather(ctx, state.weather, cw, ch)

  ctx.strokeStyle = 'rgba(110,118,129,0.45)'
  ctx.lineWidth = 1
  ctx.strokeRect(cam.ox, cam.oy, state.width * cam.scale, state.height * cam.scale)

  // Grid
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

  // Fertile grounds & Rocks
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

  // Territory circles
  for (const e of state.entities) {
    if (e.kind === 'house' && e.clan_id && !e.is_ruin && e.clan_color) {
      if (!visible0(e.x, e.y, 14)) continue
      const tr = 14
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

  // Signals
  if (state.signals) {
    const SIGNAL_COLOR: Record<string, string> = {
      food: '#3fb950',
      alarm: '#f85149',
      help: '#ffd166',
      knowledge: '#79c0ff',
      grief: '#8b949e',
      chime: '#e3b341', // §AP divine law resonance + §AN boundary stones
      chant: '#b392f0', // §AN priest liturgy
      hum: '#ff9ecd',   // §AN woman's peace-hum
      war: '#ff7b72',   // §AN soldier war-chirp
      trail: '#d2a8ff', // §AN forager scent trail
      danger_scent: '#6e7681', // §AN death-site marker
      courier: '#e3b341',      // §AN tribute courier
      omen: '#e3b341',         // §AN season omen
    }
    for (const sg of state.signals) {
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
      ctx.globalAlpha = 0.9
      ctx.fillStyle = signalColor
      ctx.beginPath()
      ctx.arc(sx, sy, 2, 0, TAU)
      ctx.fill()
      ctx.globalAlpha = 1
    }
  }

  // Entities & World Space
  ctx.setTransform(cam.scale, 0, 0, cam.scale, cam.ox, cam.oy)
  const pad = 2
  const vL = -cam.ox / cam.scale - pad
  const vR = (cw - cam.ox) / cam.scale + pad
  const vT = -cam.oy / cam.scale - pad
  const vB = (ch - cam.oy) / cam.scale + pad
  const visible = (x: number, y: number, r = pad) =>
    x + r >= vL && x - r <= vR && y + r >= vT && y - r <= vB

  // §AN boundary stones — clan-colored diamonds on the border
  if (state.boundary_stones) {
    for (const st of state.boundary_stones) {
      if (!visible(st.x, st.y, 2)) continue
      const color = state.clans?.[String(st.clan_id)]?.color ?? '#8b949e'
      ctx.globalAlpha = 0.9
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.moveTo(st.x, st.y - 1.2)
      ctx.lineTo(st.x + 1.2, st.y)
      ctx.lineTo(st.x, st.y + 1.2)
      ctx.lineTo(st.x - 1.2, st.y)
      ctx.closePath()
      ctx.fill()
      ctx.globalAlpha = 1
    }
  }

  // §AN neutral trading posts
  if (state.markets) {
    for (const m of state.markets) {
      if (!visible(m.x, m.y, 2)) continue
      ctx.globalAlpha = 0.85
      ctx.strokeStyle = '#e3b341'
      ctx.lineWidth = 0.4
      ctx.beginPath()
      ctx.arc(m.x, m.y, 1.6, 0, TAU)
      ctx.stroke()
      ctx.fillStyle = '#e3b341'
      ctx.beginPath()
      ctx.arc(m.x, m.y, 0.45, 0, TAU)
      ctx.fill()
      ctx.globalAlpha = 1
    }
  }

  // Fires
  if (state.fires) {
    for (const f of state.fires) {
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
      ctx.fillStyle = '#ffd166'
      ctx.globalAlpha = alpha * 0.85
      ctx.beginPath()
      ctx.arc(f.x, f.y, f.r * 0.45, 0, TAU)
      ctx.fill()
      ctx.globalAlpha = 1
    }
  }

  const visibleHouses = drawBatchedEntities(ctx, state.entities, visible, cam.scale, selectedId, state.tick)

  // Totem Poles + §AP Shrines & Temples of the Sphere
  const drawnShrines = new Set<string>()
  for (const e of visibleHouses) {
    if (!e.clan_id || e.is_ruin) continue
    const clan = state.clans?.[String(e.clan_id)]
    const totem: string | undefined = clan?.totem
    const isMain = e.is_main
    const size = e.size ?? 8
    const poleX = e.x + size / 2 + 1.2
    const poleY = e.y - size / 2 + 1.0
    ctx.save()
    ctx.translate(poleX, poleY)
    ctx.fillStyle = isMain ? '#e3b341' : '#8b949e'
    ctx.fillRect(-0.2, -1.3, 0.4, 2.6)
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

    // §AP shrine beside the main house: a glowing avatar stone whose aura
    // scales with faith; a temple (level 2) shines across the territory.
    const shrineLevel = clan?.shrine_level ?? 0
    if (isMain && shrineLevel >= 1 && !drawnShrines.has(String(e.clan_id))) {
      drawnShrines.add(String(e.clan_id))
      const faith = clan?.faith ?? 0
      const sx = e.x + size / 2 + 1.5
      const sy = e.y
      const glowA = Math.min(0.55, 0.18 + faith / 800)
      const auraR = shrineLevel >= 2 ? Math.max(10, 14) : 10
      // blessing aura
      ctx.globalAlpha = glowA * (shrineLevel >= 2 ? 0.5 : 0.35)
      ctx.fillStyle = info?.color ?? '#e3b341'
      ctx.beginPath()
      ctx.arc(sx, sy, auraR, 0, TAU)
      ctx.fill()
      ctx.globalAlpha = 1
      // the shrine stone itself
      ctx.save()
      ctx.translate(sx, sy)
      ctx.fillStyle = shrineLevel >= 2 ? '#e3b341' : '#6e7681'
      ctx.fillRect(-0.5, -1.4, 1.0, 2.8)
      ctx.font = '1.9px ui-monospace, monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(info?.emoji ?? '⭕', 0, -2.4)
      if (shrineLevel >= 2) {
        ctx.strokeStyle = '#e3b341'
        ctx.lineWidth = 0.35
        ctx.setLineDash([1.4, 1.0])
        ctx.beginPath()
        ctx.arc(0, 0, auraR, 0, TAU)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.font = '1.2px ui-monospace, monospace'
        ctx.fillStyle = '#e3b341'
        ctx.fillText('⛪', 0, -4.2)
      }
      ctx.restore()
    }
  }

  // Selection Halo
  if (selectedId !== null) {
    const selEnt = state.entities.find((e) => e.id === selectedId)
    if (selEnt) {
      ctx.strokeStyle = '#e3b341'
      ctx.lineWidth = 0.4
      ctx.setLineDash([1.2, 0.8])
      ctx.beginPath()
      ctx.arc(selEnt.x, selEnt.y, (selEnt.radius ?? 1.2) + 2.0, 0, TAU)
      ctx.stroke()
      ctx.setLineDash([])
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

  // Selected Clan Highlight
  if (selectedClanId !== null) {
    const clan = state.clans?.[String(selectedClanId)]
    const clanColor = clan?.color ?? '#58a6ff'
    const clanName = clan?.name ?? `Clan ${selectedClanId}`
    const clanTotem = clan?.totem
    const totemChar = (clanTotem && TOTEMS[clanTotem]?.emoji) || '🚩'

    const clanHouses = state.entities.filter((e) => e.kind === 'house' && e.clan_id === selectedClanId && !e.is_ruin)
    const clanMembers = state.entities.filter((e) => e.kind === 'creature' && e.clan_id === selectedClanId)

    for (const m of clanMembers) {
      ctx.strokeStyle = clanColor
      ctx.lineWidth = 0.35
      ctx.setLineDash([1.0, 0.8])
      ctx.beginPath()
      ctx.arc(m.x, m.y, (m.radius ?? 1.2) + 1.6, 0, TAU)
      ctx.stroke()
      ctx.setLineDash([])
    }

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

    const clanEntities = clanHouses.length > 0 ? clanHouses : clanMembers
    if (clanEntities.length > 0) {
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
      for (const e of clanEntities) {
        minX = Math.min(minX, e.x)
        maxX = Math.max(maxX, e.x)
        minY = Math.min(minY, e.y)
        maxY = Math.max(maxY, e.y)
      }
      const padC = 16
      minX -= padC; maxX += padC
      minY -= padC; maxY += padC

      ctx.strokeStyle = clanColor
      ctx.lineWidth = 0.55
      ctx.setLineDash([3.0, 2.0])
      ctx.strokeRect(minX, minY, maxX - minX, maxY - minY)
      ctx.fillStyle = clanColor
      ctx.globalAlpha = 0.06
      ctx.fillRect(minX, minY, maxX - minX, maxY - minY)
      ctx.globalAlpha = 1
      ctx.setLineDash([])

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

export function pickCreatureAt(
  state: StateMessage | null,
  clientX: number,
  clientY: number,
  cam: Camera,
  dpr: number,
): number | null {
  if (!state) return null
  const px = clientX * dpr
  const py = clientY * dpr
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
