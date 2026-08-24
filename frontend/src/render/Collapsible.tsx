import { ReactNode, useEffect, useState } from 'react'

interface Props {
  /** Stable key for localStorage persistence (e.g. 'overview-caste'). */
  id: string
  title: ReactNode
  children: ReactNode
  defaultOpen?: boolean
  hint?: string
  className?: string
}

/** §Y Reusable collapsible block — header + chevron, persisted in localStorage. */
export default function Collapsible({ id, title, children, defaultOpen = true, hint, className = '' }: Props) {
  const storageKey = `fl-collapsed-${id}`
  const [open, setOpen] = useState<boolean>(() => {
    if (typeof window === 'undefined') return defaultOpen
    const saved = window.localStorage.getItem(storageKey)
    if (saved === null) return defaultOpen
    return saved !== '1'
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, open ? '0' : '1')
    } catch {
      // ignore localStorage disabled/quota errors
    }
  }, [open, storageKey])

  return (
    <section className={`collapsible ${className}`.trim()} data-open={open}>
      <button
        type="button"
        className="collapsible-head"
        onClick={(e) => {
          e.stopPropagation()
          setOpen((o) => !o)
        }}
        aria-expanded={open}
        title={hint}
      >
        <span
          className="collapsible-chevron"
          style={{
            display: 'inline-block',
            transition: 'transform 0.15s ease',
            transform: open ? 'rotate(90deg)' : 'rotate(0deg)',
            pointerEvents: 'none',
          }}
        >
          ▸
        </span>
        {title}
      </button>
      {open && <div className="collapsible-body">{children}</div>}
    </section>
  )
}

