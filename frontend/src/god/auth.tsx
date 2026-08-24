/** God passkey client-side flow.

First visit (no credential on the server): a dialog asks to CREATE a passkey.
Afterwards: the key lives in localStorage and is attached automatically;
a 401 clears it and asks to enter it again. REST uses the X-God-Key header,
WebSocket control messages carry it in the `key` field.
*/
import { useEffect, useState } from 'react'

const STORAGE_KEY = 'flatworld-god-key'

type Mode = 'create' | 'enter'

interface PromptState {
  mode: Mode
  error?: string
}

let current: PromptState | null = null
let pendingResolve: ((key: string | null) => void) | null = null
let statusKnown: boolean | null = null // null = not checked this session

const listeners = new Set<() => void>()

function emit() {
  listeners.forEach((l) => l())
}

export function getCachedKey(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function rememberKey(key: string) {
  try {
    localStorage.setItem(STORAGE_KEY, key)
  } catch {
    /* private mode etc. — session-only use */
  }
}

export function forgetKey() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

async function serverConfigured(): Promise<boolean> {
  if (statusKnown !== null) return statusKnown
  try {
    const d = await fetch('/api/auth/status').then((r) => r.json())
    statusKnown = !!d.configured
  } catch {
    statusKnown = true // assume protected when the backend is unreachable
  }
  return statusKnown
}

function requestPasskey(mode: Mode, error?: string): Promise<string | null> {
  // A fresh ask replaces whatever was on screen before.
  pendingResolve?.(null)
  return new Promise<string | null>((resolve) => {
    pendingResolve = resolve
    current = { mode, error }
    emit()
  })
}

/** Ask for a passkey only when needed; resolves null if the user cancels. */
export async function ensureGodKey(
  hint: { mode?: Mode; error?: string } = {},
): Promise<string | null> {
  const cached = getCachedKey()
  if (!hint.mode && !hint.error) {
    if (cached) return cached
    const configured = await serverConfigured()
    return requestPasskey(configured ? 'enter' : 'create')
  }
  if (hint.mode) return requestPasskey(hint.mode, hint.error)
  const configured = await serverConfigured()
  return requestPasskey(configured ? 'enter' : 'create', hint.error)
}

/** fetch wrapper for god-touching calls: attaches the key, re-asks on failure. */
export async function godFetch(url: string, init?: RequestInit): Promise<Response> {
  let key = await ensureGodKey()
  for (let attempt = 0; attempt < 3 && key; attempt++) {
    const headers = new Headers(init?.headers)
    headers.set('X-God-Key', key)
    const res = await fetch(url, { ...init, headers })
    if (res.status !== 401 && res.status !== 409) return res
    const body = await res.clone().json().catch(() => null)
    const code: string = body?.detail?.error ?? body?.error ?? ''
    forgetKey()
    if (code === 'god_key_not_configured') {
      statusKnown = false
      key = await requestPasskey('create')
    } else {
      key = await requestPasskey('enter', 'Wrong passkey — reset must be done in backend terminal (python -m app.godkey reset <key>)')
    }
  }
  throw new Error('cancelled')
}

/** The dialog itself — mount once, near the app root. */
export function AuthModal() {
  const [tick, setTick] = useState(0)
  const [value, setValue] = useState('')
  useEffect(() => {
    const l = () => setTick((t) => t + 1)
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])
  useEffect(() => {
    setValue('')
  }, [current?.mode, tick])
  if (!current) return null
  const submitting = false

  const close = (key: string | null) => {
    const resolve = pendingResolve
    pendingResolve = null
    current = null
    emit()
    resolve?.(key)
  }

  const currentMode = current.mode

  const submit = async () => {
    const passkey = value.trim()
    if (!passkey) return
    if (currentMode === 'create') {
      try {
        const r = await fetch('/api/auth/setup', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ passkey }),
        })
        if (r.ok) {
          statusKnown = true
          rememberKey(passkey)
          close(passkey)
          return
        }
        if (r.status === 409) {
          statusKnown = true
          current = { mode: 'enter', error: 'A passkey already exists — enter it to unlock.' }
          emit()
          return
        }
        const body = await r.json().catch(() => null)
        const detail = typeof body?.detail === 'string' ? body.detail : 'could not save passkey'
        current = { mode: currentMode, error: detail }
        emit()
        return
      } catch {
        current = { mode: currentMode, error: 'backend unreachable — try again' }
        emit()
        return
      }
    }
    rememberKey(passkey)
    close(passkey)
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(1,4,9,0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: 16,
      }}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <div
        className="modal-card"
        style={{
          background: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: 12,
          padding: 20,
          width: 'min(380px, 92vw)',
          display: 'flex',
          gap: 12,
          flexDirection: 'column',
          boxShadow: '0 16px 36px rgba(0,0,0,0.6)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>
            {currentMode === 'create' ? 'Create a god passkey' : 'God passkey'}
          </h3>
          <button
            onClick={() => close(null)}
            style={{ background: 'transparent', border: 'none', color: '#8b949e', fontSize: 18, cursor: 'pointer', padding: 0, minHeight: 28 }}
          >
            ✕
          </button>
        </div>
        <p style={{ margin: 0, fontSize: 12, color: '#8b949e', lineHeight: 1.4 }}>
          {currentMode === 'create'
            ? 'No passkey exists yet. Pick one (min 4 chars) to control the world.'
            : 'Setting laws and controlling the world requires your passkey. (Reset is only available via server terminal: python -m app.godkey reset <key>)'}
        </p>
        {current.error && <p style={{ margin: 0, fontSize: 12, color: '#f85149', lineHeight: 1.4 }}>{current.error}</p>}
        <input
          autoFocus
          type="password"
          value={value}
          placeholder={currentMode === 'create' ? 'new passkey' : 'passkey'}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void submit()
            if (e.key === 'Escape') close(null)
          }}
          style={{
            background: '#010409',
            border: '1px solid #30363d',
            borderRadius: 6,
            padding: '10px 12px',
            color: '#c9d1d9',
            fontSize: 16,
          }}
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center' }}>
          <button onClick={() => close(null)} style={{ padding: '6px 12px', minHeight: 36 }}>
            Cancel
          </button>
          <button
            onClick={() => void submit()}
            disabled={submitting}
            style={{ padding: '6px 14px', borderColor: '#d29922', color: '#d29922', minHeight: 36, fontWeight: 600 }}
          >
            {currentMode === 'create' ? 'Create' : 'Unlock'}
          </button>
        </div>
      </div>
    </div>
  )
}
