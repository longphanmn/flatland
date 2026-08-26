import type { StateMessage } from '../types'
import {
  Camera,
  clusterEntities,
  MAX_SCALE,
  MIN_SCALE_FACTOR,
  pickCreatureAt,
  renderWorldFrame,
} from './renderCore'

let canvas: OffscreenCanvas | null = null
let ctx: OffscreenCanvasRenderingContext2D | null = null
let currentState: StateMessage | null = null
let selectedId: number | null = null
let selectedClanId: number | null = null
let baseFit = 1
let targetZoomScale: number | null = null
let lastTrackedId: number | null = null
let targetClanScale: number | null = null
let lastTrackedClanId: number | null = null
let isPanningOrPinching = false

const cam: Camera = {
  scale: 1,
  ox: 0,
  oy: 0,
  initialized: false,
}

function fitCamera(state: StateMessage) {
  if (!canvas) return
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

function clampCamera(state: StateMessage) {
  if (!canvas) return
  const cxw = (canvas.width / 2 - cam.ox) / cam.scale
  const cyw = (canvas.height / 2 - cam.oy) / cam.scale
  const tx = Math.min(Math.max(cxw, 0), state.width)
  const ty = Math.min(Math.max(cyw, 0), state.height)
  cam.ox += (tx - cxw) * cam.scale
  cam.oy += (ty - cyw) * cam.scale
}

function zoomAt(state: StateMessage, factor: number, ax: number, ay: number) {
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
  if (selectedId !== null) {
    targetZoomScale = next
  }
}

function renderLoop() {
  if (ctx && canvas && currentState) {
    const cw = canvas.width
    const ch = canvas.height

    if (!cam.initialized || cam.scale <= 0) {
      fitCamera(currentState)
    }

    // Auto-follow logic in worker
    if (selectedId !== null) {
      lastTrackedClanId = null
      targetClanScale = null
      const selEnt = currentState.entities.find((e) => e.id === selectedId && e.kind === 'creature')
      if (selEnt) {
        if (selectedId !== lastTrackedId) {
          lastTrackedId = selectedId
          const minFollowScale = Math.min(MAX_SCALE, Math.max(baseFit * 3.5, 8.0))
          targetZoomScale = Math.max(cam.scale, minFollowScale)
        }
        if (!isPanningOrPinching) {
          const desiredScale = targetZoomScale ?? cam.scale
          cam.scale += (desiredScale - cam.scale) * 0.12
          const targetOx = cw / 2 - selEnt.x * cam.scale
          const targetOy = ch / 2 - selEnt.y * cam.scale
          if (Math.abs(targetOx - cam.ox) > cw * 0.75 || Math.abs(targetOy - cam.oy) > ch * 0.75) {
            cam.ox = targetOx
            cam.oy = targetOy
          } else {
            cam.ox += (targetOx - cam.ox) * 0.15
            cam.oy += (targetOy - cam.oy) * 0.15
          }
          clampCamera(currentState)
        }
      }
    } else if (selectedClanId !== null) {
      lastTrackedId = null
      targetZoomScale = null
      const clanHouses = currentState.entities.filter((e) => e.kind === 'house' && e.clan_id === selectedClanId && !e.is_ruin)
      const clanMembers = currentState.entities.filter((e) => e.kind === 'creature' && e.clan_id === selectedClanId)
      const clanEntities = clanHouses.length > 0 ? clanHouses : clanMembers

      const clusters = clusterEntities(clanEntities, 40.0)
      let primaryCluster = clusters[0]
      for (const cl of clusters) {
        if (cl.some((e: any) => e.is_main)) {
          primaryCluster = cl
          break
        }
        if (cl.length > primaryCluster.length) {
          primaryCluster = cl
        }
      }

      if (primaryCluster && primaryCluster.length > 0) {
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
        for (const e of primaryCluster) {
          if (e.x < minX) minX = e.x
          if (e.x > maxX) maxX = e.x
          if (e.y < minY) minY = e.y
          if (e.y > maxY) maxY = e.y
        }
        const pad = 20
        minX -= pad; maxX += pad
        minY -= pad; maxY += pad
        const spanX = Math.max(45, maxX - minX)
        const spanY = Math.max(45, maxY - minY)
        const centerX = (minX + maxX) / 2
        const centerY = (minY + maxY) / 2

        if (selectedClanId !== lastTrackedClanId) {
          lastTrackedClanId = selectedClanId
          const fitClanScale = Math.min((cw * 0.8) / spanX, (ch * 0.8) / spanY)
          targetClanScale = Math.max(baseFit * 0.9, Math.min(fitClanScale, 3.6))
        }

        if (!isPanningOrPinching) {
          const desiredScale = targetClanScale ?? cam.scale
          cam.scale += (desiredScale - cam.scale) * 0.08
          const targetOx = cw / 2 - centerX * cam.scale
          const targetOy = ch / 2 - centerY * cam.scale
          cam.ox += (targetOx - cam.ox) * 0.1
          cam.oy += (targetOy - cam.oy) * 0.1
          clampCamera(currentState)
        }
      }
    } else {
      lastTrackedId = null
      targetZoomScale = null
      lastTrackedClanId = null
      targetClanScale = null
    }

    renderWorldFrame(ctx, currentState, cw, ch, cam, selectedId, selectedClanId)
  }

  requestAnimationFrame(renderLoop)
}

self.onmessage = (e: MessageEvent) => {
  const msg = e.data
  if (!msg) return

  switch (msg.type) {
    case 'init': {
      canvas = msg.canvas as OffscreenCanvas
      ctx = canvas.getContext('2d') as OffscreenCanvasRenderingContext2D
      canvas.width = msg.width
      canvas.height = msg.height
      requestAnimationFrame(renderLoop)
      break
    }
    case 'resize': {
      if (canvas) {
        canvas.width = msg.width
        canvas.height = msg.height
        if (currentState) clampCamera(currentState)
      }
      break
    }
    case 'state': {
      currentState = msg.state as StateMessage
      break
    }
    case 'select': {
      selectedId = msg.id ?? null
      selectedClanId = msg.clanId ?? null
      break
    }
    case 'pan_start': {
      isPanningOrPinching = true
      break
    }
    case 'pan_end': {
      isPanningOrPinching = false
      break
    }
    case 'pan': {
      cam.ox += msg.dx
      cam.oy += msg.dy
      if (currentState) clampCamera(currentState)
      break
    }
    case 'zoom': {
      if (currentState) {
        zoomAt(currentState, msg.factor, msg.cx, msg.cy)
      }
      break
    }
    case 'fit': {
      if (currentState) fitCamera(currentState)
      break
    }
    case 'center_on': {
      if (currentState && canvas) {
        const ent = currentState.entities.find((e) => e.id === msg.id)
        if (ent) {
          const targetScale = Math.min(MAX_SCALE, cam.scale * 1.6)
          cam.ox = canvas.width / 2 - ent.x * targetScale
          cam.oy = canvas.height / 2 - ent.y * targetScale
          cam.scale = targetScale
          clampCamera(currentState)
        }
      }
      break
    }
    case 'hit_test': {
      const id = pickCreatureAt(currentState, msg.clientX, msg.clientY, cam, msg.dpr)
      self.postMessage({ type: 'hit_test_result', id, reqId: msg.reqId, isDoubleTap: msg.isDoubleTap })
      break
    }
  }
}
