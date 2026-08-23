import type { ControlMessage, HelloMessage, StateMessage } from './types'

export type ConnStatus = 'connecting' | 'open' | 'closed'

interface Handlers {
  onHello?: (msg: HelloMessage) => void
  onState?: (msg: StateMessage) => void
  onStatus?: (status: ConnStatus) => void
  /** server rejected a control message for lack of a valid passkey */
  onAuthError?: () => void
}

/** WebSocket client with exponential-backoff auto-reconnect. */
export class WorldSocket {
  private ws: WebSocket | null = null
  private attempts = 0
  private disposed = false
  private timer: ReturnType<typeof setTimeout> | undefined

  constructor(
    private url: string,
    private handlers: Handlers,
  ) {}

  connect(): void {
    if (this.disposed) return
    this.handlers.onStatus?.('connecting')
    const ws = new WebSocket(this.url)
    this.ws = ws
    ws.onopen = () => {
      this.attempts = 0
      this.handlers.onStatus?.('open')
    }
    ws.onmessage = (ev) => this.handle(ev.data)
    ws.onerror = () => ws.close()
    ws.onclose = () => {
      this.handlers.onStatus?.('closed')
      this.ws = null
      if (!this.disposed) {
        const delay = Math.min(5000, 400 * 2 ** this.attempts++)
        this.timer = setTimeout(() => this.connect(), delay)
      }
    }
  }

  private handle(raw: string): void {
    try {
      const msg = JSON.parse(raw)
      if (msg.type === 'state') this.handlers.onState?.(msg as StateMessage)
      else if (msg.type === 'hello') this.handlers.onHello?.(msg as HelloMessage)
      else if (msg.type === 'auth_error') this.handlers.onAuthError?.()
    } catch {
      // ignore malformed frames
    }
  }

  send(msg: ControlMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  dispose(): void {
    this.disposed = true
    if (this.timer) clearTimeout(this.timer)
    this.ws?.close()
  }
}
