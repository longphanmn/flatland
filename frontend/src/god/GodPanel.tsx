import { useEffect, useState } from 'react'
import type { GodLaws } from '../types'

type NumberLawKey = Exclude<keyof GodLaws, 'boundary'>

interface LawSpec {
  key: NumberLawKey
  label: string
  min: number
  max: number
  step: number
  group: string
}

const NUMBER_LAWS: LawSpec[] = [
  // Food & Energy — the economy of survival
  { key: 'food_count', label: 'Food abundance', min: 0, max: 300, step: 1, group: 'Food & Energy' },
  { key: 'energy_max', label: 'Max energy', min: 10, max: 500, step: 5, group: 'Food & Energy' },
  { key: 'energy_decay_per_tick', label: 'Energy decay / tick', min: 0, max: 2, step: 0.01, group: 'Food & Energy' },
  { key: 'energy_from_food', label: 'Energy from food', min: 0, max: 100, step: 1, group: 'Food & Energy' },
  // Hunger & Sight — perception of the world
  { key: 'hungry_ratio', label: 'Hungry threshold', min: 0.05, max: 1, step: 0.05, group: 'Hunger & Sight' },
  { key: 'starving_ratio', label: 'Starving threshold', min: 0.01, max: 1, step: 0.01, group: 'Hunger & Sight' },
  { key: 'perceive_radius', label: 'Base sight radius', min: 1, max: 40, step: 0.5, group: 'Hunger & Sight' },
  { key: 'eat_radius', label: 'Eat radius', min: 0.2, max: 5, step: 0.1, group: 'Hunger & Sight' },
  { key: 'hungry_perceive_mult', label: 'Hungry sight ×', min: 1, max: 3, step: 0.1, group: 'Hunger & Sight' },
  { key: 'desperate_perceive_mult', label: 'Starving sight ×', min: 1, max: 3, step: 0.1, group: 'Hunger & Sight' },
  { key: 'desperate_speed_mult', label: 'Starving speed ×', min: 1, max: 3, step: 0.05, group: 'Hunger & Sight' },
  // Movement — how bodies turn through the plane
  { key: 'wander_turn', label: 'Wander turn', min: 0, max: 2, step: 0.05, group: 'Movement' },
  { key: 'steer_turn', label: 'Steer turn', min: 0, max: 2, step: 0.05, group: 'Movement' },
  // Life & Death — the span of beings
  { key: 'lifespan_mult', label: 'Lifespan ×', min: 0.05, max: 5, step: 0.05, group: 'Life & Death' },
  // Reproduction — Nature's Law of lineage
  { key: 'adult_age', label: 'Adult age', min: 0, max: 5000, step: 50, group: 'Reproduction' },
  { key: 'mate_radius', label: 'Mate radius', min: 0.5, max: 30, step: 0.5, group: 'Reproduction' },
  { key: 'mate_energy_min', label: 'Mate energy ≥', min: 0, max: 200, step: 5, group: 'Reproduction' },
  { key: 'birth_rate', label: 'Birth rate', min: 0, max: 1, step: 0.05, group: 'Reproduction' },
  { key: 'sex_ratio', label: 'Son probability', min: 0, max: 1, step: 0.05, group: 'Reproduction' },
  { key: 'mutation_rate', label: 'Mutation rate', min: 0, max: 1, step: 0.01, group: 'Reproduction' },
  { key: 'euthanasia_threshold', label: 'Euthanasia ≥', min: 0.3, max: 1, step: 0.05, group: 'Reproduction' },
  // Disease — plague and mercy
  { key: 'disease_outbreak_rate', label: 'Outbreak rate / tick', min: 0, max: 0.05, step: 0.0005, group: 'Disease' },
  { key: 'disease_rate', label: 'Contagion chance', min: 0, max: 1, step: 0.01, group: 'Disease' },
  { key: 'disease_radius', label: 'Contagion radius', min: 0.5, max: 20, step: 0.5, group: 'Disease' },
  { key: 'disease_energy_drain', label: 'Energy drain / tick', min: 0, max: 2, step: 0.05, group: 'Disease' },
  { key: 'recovery_rate', label: 'Recovery chance / tick', min: 0, max: 1, step: 0.005, group: 'Disease' },
  { key: 'disease_lethality', label: 'Lethality', min: 0, max: 1, step: 0.05, group: 'Disease' },
  // Sky & Seasons — the turning of the world
  { key: 'day_length', label: 'Day length (ticks)', min: 4, max: 20000, step: 4, group: 'Sky & Seasons' },
  { key: 'season_length', label: 'Season length (ticks)', min: 4, max: 100000, step: 10, group: 'Sky & Seasons' },
  { key: 'night_sight_mult', label: 'Night sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'weather_change_rate', label: 'Weather turn chance', min: 0, max: 1, step: 0.001, group: 'Sky & Seasons' },
  { key: 'fog_sight_mult', label: 'Fog sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'rain_speed_mult', label: 'Rain speed ×', min: 0.1, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'storm_wander_bonus', label: 'Storm wander +', min: 0, max: 3.2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'max_sides', label: 'Max sides', min: 3, max: 64, step: 1, group: 'Reproduction' },
  { key: 'birth_energy_cost', label: 'Birth energy cost', min: 0, max: 100, step: 1, group: 'Reproduction' },
  { key: 'reproduction_cooldown', label: 'Cooldown ticks', min: 0, max: 3000, step: 10, group: 'Reproduction' },
  { key: 'carrying_capacity', label: 'Carrying capacity', min: 2, max: 400, step: 2, group: 'Reproduction' },
  { key: 'max_population', label: 'Hard pop cap', min: 2, max: 1000, step: 2, group: 'Reproduction' },
  // Bodies & Houses — geometry of the flat world
  { key: 'door_clearance', label: 'Door clearance ×', min: 1, max: 4, step: 0.1, group: 'Bodies & Houses' },
  { key: 'house_min_size', label: 'House min size', min: 4, max: 30, step: 1, group: 'Bodies & Houses' },
  { key: 'house_max_size', label: 'House max size', min: 6, max: 60, step: 1, group: 'Bodies & Houses' },
]

const GROUP_ORDER = [
  'Food & Energy',
  'Hunger & Sight',
  'Movement',
  'Life & Death',
  'Reproduction',
  'Disease',
  'Sky & Seasons',
  'Bodies & Houses',
]

const LAW_HINTS: Partial<Record<NumberLawKey, string>> = {
  food_count: 'the world keeps this much food alive — bounty or famine',
  energy_decay_per_tick: 'how fast all life burns out without eating',
  perceive_radius: 'base sight; each caste scales it by its Sight Recognition',
  lifespan_mult: 'scales every caste’s natural lifespan',
  door_clearance: 'doorways scale with the largest creature × this',
  house_min_size: 'applies to houses built after the next reset',
  house_max_size: 'applies to houses built after the next reset',
  adult_age: 'creatures must be this many ticks old to mate',
  birth_rate: 'chance per eligible pair per tick, before fertility',
  sex_ratio: 'probability a child is a son (polygons ascend; daughters are lines)',
  mutation_rate: 'chance a son’s side count deviates ±1 from inheritance',
  euthanasia_threshold: 'irregular children at/above this are consumed at adulthood, below it demoted',
  carrying_capacity: 'above this population, fertility fades gradually',
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

          {GROUP_ORDER.map((group) => (
            <section key={group} className="god-group">
              <h3>{group}</h3>
              {group === 'Reproduction' && (
                <label className="god-row">
                  <span title="whether new life may begin at all">Births allowed</span>
                  <select
                    value={String(laws.birth_enabled ?? true)}
                    onChange={(e) =>
                      setLaws((l) => ({ ...l, birth_enabled: e.target.value === 'true' }))
                    }
                  >
                    <option value="true">yes</option>
                    <option value="false">no</option>
                  </select>
                </label>
              )}
              {group === 'Disease' && (
                <label className="god-row">
                  <span title="plagues walk the world; disabling freezes all sickness">
                    Plagues allowed
                  </span>
                  <select
                    value={String(laws.disease_enabled ?? false)}
                    onChange={(e) =>
                      setLaws((l) => ({ ...l, disease_enabled: e.target.value === 'true' }))
                    }
                  >
                    <option value="true">yes</option>
                    <option value="false">no</option>
                  </select>
                </label>
              )}
              {group === 'Sky & Seasons' && (
                <label className="god-row">
                  <span title="whether the weather ever turns">Weather allowed</span>
                  <select
                    value={String(laws.weather_enabled ?? true)}
                    onChange={(e) =>
                      setLaws((l) => ({ ...l, weather_enabled: e.target.value === 'true' }))
                    }
                  >
                    <option value="true">yes</option>
                    <option value="false">no</option>
                  </select>
                </label>
              )}
              {NUMBER_LAWS.filter((l) => l.group === group).map(({ key, label, min, max, step }) => (
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
            </section>
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
