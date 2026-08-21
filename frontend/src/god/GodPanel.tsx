import { useEffect, useState } from 'react'
import type { GodLaws } from '../types'

const NUMBER_LAWS: {
  key: NumberLawKey
  label: string
  min: number
  max: number
  step: number
}[] = [
  { key: 'food_count', label: 'Food abundance', min: 0, max: 300, step: 1 },
  { key: 'energy_max', label: 'Max energy', min: 10, max: 500, step: 5 },
  { key: 'energy_decay_per_tick', label: 'Energy decay / tick', min: 0, max: 2, step: 0.01 },
  { key: 'energy_from_food', label: 'Energy from food', min: 0, max: 100, step: 1 },
  { key: 'hungry_ratio', label: 'Hungry threshold', min: 0.05, max: 1, step: 0.05 },
  { key: 'starving_ratio', label: 'Starving threshold', min: 0.01, max: 1, step: 0.01 },
  { key: 'perceive_radius', label: 'Sight radius', min: 1, max: 40, step: 0.5 },
  { key: 'eat_radius', label: 'Eat radius', min: 0.2, max: 5, step: 0.1 },
  { key: 'wander_turn', label: 'Wander turn', min: 0, max: 2, step: 0.05 },
  { key: 'steer_turn', label: 'Steer turn', min: 0, max: 2, step: 0.05 },
  { key: 'hungry_perceive_mult', label: 'Hungry sight ×', min: 1, max: 3, step: 0.1 },
  { key: 'desperate_perceive_mult', label: 'Starving sight ×', min: 1, max: 3, step: 0.1 },
  { key: 'desperate_speed_mult', label: 'Starving speed ×', min: 1, max: 3, step: 0.05 },
]

type NumberLawKey = Exclude<keyof GodLaws, 'boundary'>

const LAW_HINTS: Partial<Record<NumberLawKey, string>> = {
  food_count: 'the world keeps this much food alive — bounty or famine',
  energy_decay_per_tick: 'how fast all life burns out without eating',
  door_clearance: 'doorways scale with the largest creature × this',
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function GodPanel({ open, onClose }: Props) {
  const [laws, setLaws] = useState<GodLaws>({})
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    fetch('/api/laws')
      .then((r) => r.json())
      .then(setLaws)
      .catch(() => setError('failed to load laws'))
      .finally(() => setLoading(false))
  }, [open])

  if (!open) return null

  const set = (key: NumberLawKey, raw: string) =>
    setLaws((l) => ({ ...l, [key]: raw === '' ? undefined : Number(raw) }))

  const apply = async () => {
    setError(null)
    setSaved(false)
    try {
      const res = await fetch('/api/laws', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(laws),
      })
      if (!res.ok) {
        const body = await res.json()
        throw new Error(
          typeof body.detail === 'string'
            ? body.detail
            : (body.detail?.[0]?.msg ?? 'law rejected'),
        )
      }
      setLaws(await res.json())
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to apply law')
    }
  }

  return (
    <aside className="god-panel">
      <header className="god-head">
        <h2>⚖ Laws of Nature</h2>
        <button className="god-close" onClick={onClose} aria-label="close">
          ×
        </button>
      </header>

      <p className="god-note">
        You are god: set the rules, never the fates. Creatures and the world obey
        the law; no single life may be touched.
      </p>

      {loading ? (
        <p className="god-note">reading the tablets…</p>
      ) : (
        <>
          <label className="god-row">
            <span title="what happens at the edge of the world">Edge of world</span>
            <select
              value={laws.boundary ?? 'wrap'}
              onChange={(e) =>
                setLaws((l) => ({ ...l, boundary: e.target.value as 'wrap' | 'clamp' }))
              }
            >
              <option value="wrap">wrap</option>
              <option value="clamp">walls</option>
            </select>
          </label>

          {NUMBER_LAWS.map(({ key, label, min, max, step }) => (
            <label className="god-row" key={key}>
              <span title={LAW_HINTS[key]}>{label}</span>
              <input
                type="number"
                min={min}
                max={max}
                step={step}
                value={(laws[key] as number | undefined) ?? ''}
                onChange={(e) => set(key, e.target.value)}
              />
            </label>
          ))}

          <footer className="god-foot">
            {error && <span className="god-error">{error}</span>}
            {!error && saved && <span className="god-saved">laws applied</span>}
            <button onClick={apply}>Apply Law</button>
          </footer>
        </>
      )}
    </aside>
  )
}
