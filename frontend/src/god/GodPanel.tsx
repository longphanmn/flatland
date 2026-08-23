import { useEffect, useState } from 'react'
import { godFetch } from './auth'
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
  // Ecosystem — biodiversity of the meadow
  { key: 'plant_growth_rate', label: 'Plant growth / tick', min: 0, max: 1, step: 0.01, group: 'Ecosystem' },
  { key: 'plant_spread_rate', label: 'Plant spread chance', min: 0, max: 1, step: 0.005, group: 'Ecosystem' },
  { key: 'nutrient_cycle_rate', label: 'Nutrient cycle ×', min: 0, max: 10, step: 0.1, group: 'Ecosystem' },
  { key: 'poison_rate', label: 'Poison sprout chance', min: 0, max: 1, step: 0.01, group: 'Ecosystem' },
  { key: 'beast_ratio', label: 'Herbivore ratio', min: 0, max: 1, step: 0.01, group: 'Ecosystem' },
  { key: 'diet_strictness', label: 'Diet strictness', min: 0, max: 1, step: 0.05, group: 'Ecosystem' },
  // Hunger & Sight — perception of the world
  { key: 'hungry_ratio', label: 'Hungry threshold', min: 0.05, max: 1, step: 0.05, group: 'Hunger & Sight' },
  { key: 'starving_ratio', label: 'Starving threshold', min: 0.01, max: 1, step: 0.01, group: 'Hunger & Sight' },
  { key: 'perceive_radius', label: 'Base sight radius', min: 1, max: 40, step: 0.5, group: 'Hunger & Sight' },
  { key: 'eat_radius', label: 'Eat radius', min: 0.2, max: 5, step: 0.1, group: 'Hunger & Sight' },
  { key: 'hungry_perceive_mult', label: 'Hungry sight ×', min: 1, max: 3, step: 0.1, group: 'Hunger & Sight' },
  { key: 'desperate_perceive_mult', label: 'Starving sight ×', min: 1, max: 3, step: 0.1, group: 'Hunger & Sight' },
  { key: 'desperate_speed_mult', label: 'Starving speed ×', min: 1, max: 3, step: 0.05, group: 'Hunger & Sight' },
  { key: 'food_giveup_ticks', label: 'Give-up ticks', min: 0, max: 2000, step: 10, group: 'Hunger & Sight' },
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
  { key: 'winter_food_mult', label: 'Winter food ×', min: 0.1, max: 1.5, step: 0.05, group: 'Sky & Seasons' },
  { key: 'night_sight_mult', label: 'Night sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'weather_change_rate', label: 'Weather turn chance', min: 0, max: 1, step: 0.001, group: 'Sky & Seasons' },
  { key: 'fog_sight_mult', label: 'Fog sight ×', min: 0.05, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'rain_speed_mult', label: 'Rain speed ×', min: 0.1, max: 2, step: 0.05, group: 'Sky & Seasons' },
  { key: 'storm_wander_bonus', label: 'Storm wander +', min: 0, max: 3.2, step: 0.05, group: 'Sky & Seasons' },
  // Weather & Crops — rain waters, fog favours mushrooms, storms damage (§R)
  { key: 'rain_growth_mult', label: 'Rain growth ×', min: 0.5, max: 3, step: 0.05, group: 'Weather & Crops' },
  { key: 'fog_mushroom_mult', label: 'Fog mushroom ×', min: 0.5, max: 3, step: 0.05, group: 'Weather & Crops' },
  { key: 'storm_plant_damage', label: 'Storm plant damage', min: 0, max: 1, step: 0.005, group: 'Weather & Crops' },
  // Weather Sickness — chill and wet contagion (§R)
  { key: 'chill_rate', label: 'Chill rate / tick', min: 0, max: 1, step: 0.005, group: 'Weather Sickness' },
  { key: 'chill_threshold', label: 'Chill threshold', min: 1, max: 100, step: 1, group: 'Weather Sickness' },
  { key: 'chill_drain', label: 'Chill drain / tick', min: 0, max: 5, step: 0.05, group: 'Weather Sickness' },
  { key: 'wet_disease_mult', label: 'Wet disease ×', min: 1, max: 5, step: 0.1, group: 'Weather Sickness' },
  // Shelter — roofs against the sky
  { key: 'exposure_drain', label: 'Exposure drain / tick', min: 0, max: 2, step: 0.05, group: 'Shelter' },
  { key: 'house_capacity', label: 'House capacity', min: 1, max: 20, step: 1, group: 'Shelter' },
  { key: 'rest_recovery_mult', label: 'Rest healing ×', min: 0.5, max: 5, step: 0.25, group: 'Shelter' },
  { key: 'house_decay_ticks', label: 'House decay ticks', min: 100, max: 100000, step: 100, group: 'Shelter' },
  // Territory — clan land and trespass
  { key: 'territory_radius', label: 'Territory radius', min: 1, max: 50, step: 1, group: 'Territory' },
  { key: 'trespass_decay', label: 'Trespass decay / tick', min: 0, max: 5, step: 0.05, group: 'Territory' },
  // Clan founding (§V) — settlements define clans
  { key: 'max_clans', label: 'Max clans', min: -1, max: 24, step: 1, group: 'Clan' },
  { key: 'max_sides', label: 'Max sides', min: 3, max: 64, step: 1, group: 'Reproduction' },
  { key: 'birth_energy_cost', label: 'Birth energy cost', min: 0, max: 100, step: 1, group: 'Reproduction' },
  { key: 'reproduction_cooldown', label: 'Cooldown ticks', min: 0, max: 3000, step: 10, group: 'Reproduction' },
  { key: 'carrying_capacity', label: 'Carrying capacity', min: -1, max: 2000, step: 10, group: 'Reproduction' },
  { key: 'max_population', label: 'Hard pop cap', min: -1, max: 5000, step: 10, group: 'Reproduction' },
  // Society — interaction & clan relations
  { key: 'cohesion_weight', label: 'Cohesion weight', min: 0, max: 3, step: 0.1, group: 'Interaction' },
  { key: 'alignment_weight', label: 'Alignment weight', min: 0, max: 3, step: 0.1, group: 'Interaction' },
  { key: 'separation_weight', label: 'Separation weight', min: 0, max: 3, step: 0.1, group: 'Interaction' },
  { key: 'flock_radius', label: 'Flock radius', min: 1, max: 40, step: 1, group: 'Interaction' },
  { key: 'relation_drift_rate', label: 'Relation drift / tick', min: 0, max: 10, step: 0.5, group: 'Interaction' },
  { key: 'alliance_threshold', label: 'Alliance threshold', min: -100, max: 100, step: 5, group: 'Interaction' },
  { key: 'rivalry_threshold', label: 'Rivalry threshold', min: -100, max: 100, step: 5, group: 'Interaction' },
  // Predation — hunters and prey
  { key: 'predator_ratio', label: 'Predator ratio', min: 0, max: 1, step: 0.01, group: 'Predation' },
  { key: 'hunt_radius', label: 'Hunt radius', min: 1, max: 40, step: 1, group: 'Predation' },
  { key: 'bite_damage', label: 'Bite damage', min: 0, max: 200, step: 10, group: 'Predation' },
  { key: 'bite_cooldown', label: 'Bite cooldown', min: 0, max: 100, step: 1, group: 'Predation' },
  { key: 'energy_from_prey', label: 'Energy from prey', min: 0, max: 200, step: 5, group: 'Predation' },
  { key: 'fear_radius', label: 'Fear radius', min: 1, max: 40, step: 1, group: 'Predation' },
  // Communication — clan calls (§Q)
  { key: 'signal_radius', label: 'Signal radius', min: 3, max: 40, step: 1, group: 'Communication' },
  { key: 'food_call_rate', label: 'Food call rate', min: 0, max: 1, step: 0.01, group: 'Communication' },
  { key: 'alarm_call_rate', label: 'Alarm call rate', min: 0, max: 1, step: 0.01, group: 'Communication' },
  // Communication II — knowledge, teaching & mobbing (§X)
  { key: 'knowledge_ttl', label: 'Knowledge TTL', min: 20, max: 100000, step: 10, group: 'Communication II' },
  { key: 'knowledge_share_rate', label: 'Share rate / tick', min: 0, max: 1, step: 0.01, group: 'Communication II' },
  { key: 'help_radius', label: 'Help radius', min: 2, max: 60, step: 1, group: 'Communication II' },
  { key: 'defense_weight', label: 'Defense weight', min: 0, max: 5, step: 0.05, group: 'Communication II' },
  // Rebellion — clan schism (§S)
  { key: 'schism_threshold', label: 'Schism threshold', min: 0, max: 1, step: 0.05, group: 'Rebellion' },
  { key: 'schism_min_pop', label: 'Schism min pop', min: 2, max: 100, step: 1, group: 'Rebellion' },
  // Ages — super-seasons (§S)
  { key: 'age_length', label: 'Age length (ticks)', min: 100, max: 1000000, step: 100, group: 'Ages' },
  // Culture (§S)
  { key: 'culture_spread_rate', label: 'Culture spread / tick', min: 0, max: 1, step: 0.0005, group: 'Culture' },
  // Genetics — heritable traits (§S)
  { key: 'trait_mutation_rate', label: 'Trait mutation rate', min: 0, max: 1, step: 0.005, group: 'Genetics' },
  // Wildfire & Disasters (§S)
  { key: 'fire_rate', label: 'Fire ignite / tick', min: 0, max: 0.05, step: 0.0001, group: 'Wildfire & Disasters' },
  { key: 'fire_spread_rate', label: 'Fire spread / tick', min: 0, max: 1, step: 0.01, group: 'Wildfire & Disasters' },
  { key: 'disaster_rate', label: 'Disaster / tick', min: 0, max: 0.05, step: 0.0001, group: 'Wildfire & Disasters' },
  // Clan war — rival blood
  { key: 'attack_radius', label: 'Attack radius', min: 0.5, max: 10, step: 0.1, group: 'Clan War' },
  { key: 'attack_damage', label: 'Attack damage', min: 0, max: 200, step: 10, group: 'Clan War' },
  // Bodies & Houses — geometry of the flat world
  { key: 'door_clearance', label: 'Door clearance ×', min: 1, max: 4, step: 0.1, group: 'Bodies & Houses' },
  { key: 'house_min_size', label: 'House min size', min: 4, max: 30, step: 1, group: 'Bodies & Houses' },
  { key: 'house_max_size', label: 'House max size', min: 6, max: 60, step: 1, group: 'Bodies & Houses' },
]

const GROUP_ORDER = [
  'Food & Energy',
  'Ecosystem',
  'Hunger & Sight',
  'Movement',
  'Life & Death',
  'Reproduction',
  'Disease',
  'Sky & Seasons',
  'Ages',
  'Culture',
  'Genetics',
  'Wildfire & Disasters',
  'Weather & Crops',
  'Weather Sickness',
  'Shelter',
  'Territory',
  'Clan',
  'Communication',
  'Communication II',
  'Rebellion',
  'Interaction',
  'Predation',
  'Clan War',
  'Bodies & Houses',
]

const LAW_HINTS: Partial<Record<NumberLawKey, string>> = {
  food_count: 'the world keeps this much food alive — bounty or famine (winter ×0.5, summer ×1.2)',
  plant_growth_rate: 'how fast plants mature (0.05) — berry 0.65×, mushroom 0.85×, poison 0.6×, season multiplies',
  plant_spread_rate: 'chance a mature plant seeds a nearby sprout each tick',
  nutrient_cycle_rate: 'corpse decay boost to nearby plants (0.65) — death feeds life',
  poison_rate: 'chance a new sprout is poisonous (0.01) — 1% sicken, berry heals +1, poison -30 health',
  beast_ratio: 'wild herbivores as fraction of creature density — grazers that feed predators',
  diet_strictness: '0 omnivore, 1 strict — herbivore ignores meat, predator ignores plants',
  territory_radius: 'clan territory circle radius around house (14) — members steer home, trespass sours relations',
  trespass_decay: 'relation points lost per tick a rival trespasses inside territory',
  house_decay_ticks: 'abandoned house ticks before crumbling to ruin (2400 = 2 seasons)',
  energy_decay_per_tick: 'how fast all life burns without eating (0.025) — winter/rain adds 0.03 exposure if roofless',
  energy_from_food: 'base energy from a mature plant (32) — berry 48, mushroom 24, grass 32, poison 8',
  perceive_radius: 'base sight (20) — each caste scales it (Woman 0.8×, Priest 1.35×), night 0.6×, fog 0.6×, Eye totem 1.25×',
  food_giveup_ticks: 'a meal blocked by rock/wall is abandoned this many ticks — the hungry give up and seek food elsewhere (0 = never give up)',
  lifespan_mult: 'scales every caste’s natural lifespan',
  door_clearance: 'doorways scale with the largest creature × this (1.5)',
  house_min_size: 'applies to houses built after the next reset (6)',
  house_max_size: 'applies to houses built after the next reset (10)',
  adult_age: 'creatures must be this many ticks old to mate (200)',
  birth_rate: 'chance per eligible pair per tick, before fertility (0.35)',
  sex_ratio: 'probability a child is a son (polygons ascend; daughters are lines)',
  mutation_rate: 'chance a son’s side count deviates ±1 from inheritance (0.05)',
  euthanasia_threshold: 'irregular children at/above this are consumed at adulthood, below it demoted (0.7)',
  carrying_capacity: 'above this population, fertility fades gradually (-1 = scale with map area, 80 per 200×200)',
  max_population: 'hard cap — no births beyond (-1 = scale with map area, 140 per 200×200)',
  house_capacity: 'beds in an 8×8 hall (12) — scales with floor area, so a small hut cannot hold a whole clan; overflow spills to the nearest roof with space',
  exposure_drain: 'energy lost per tick outdoors in rain/storm/night (0.03)',
  rest_recovery_mult: 'health regen multiplier when sleeping indoors (2.0)',
  totems_enabled: 'each clan bears a totem with a subtle buff — Wolf 🐺 Tree 🌳 Shield 🛡️ Eye 👁️ Bear 🐻 Stag 🦌 Owl 🦉 Rabbit 🐇 Boar 🐗 Fox 🦊 Raven 🐦‍⬛ Serpent 🐍',
  succession_enabled: 'leader succession on death emits succession event',
  max_clans: 'society granularity: -1 = one clan per house; N ≥ 1 clusters founders into N spatial clans (applies at reset)',
  rain_growth_mult: 'rain/storm boost to plant growth (1.25) — soaked ground regrows faster',
  fog_mushroom_mult: 'fog boost to mushroom growth (1.35) — the decomposer tier loves mist',
  storm_plant_damage: 'chance a storm strips growth from exposed plants (0.02) — occasionally uproots',
  chill_rate: 'chill built per tick unsheltered in rain/storm/winter night (0.04)',
  chill_threshold: 'chill at which creature sickens (12) — shelter sheds 2.5× faster',
  chill_drain: 'health drain per tick when chilled (0.18) — death cause chill',
  wet_disease_mult: 'wet/cold catch disease faster and recover slower (1.5×)',
  age_length: 'ticks per age (12000 = 5 seasons) — Golden×1.25 food, Ice×0.55 food + chill, Chaos×1.8 mutation, Plague×1.8 disease',
  culture_spread_rate: 'allied clans within territory adopt same culture with this chance/tick (0.005)',
  trait_mutation_rate: 'chance mutation adds heritable trait greedy/peaceful/paranoid/bold (0.02) — bold war, paranoid flee, greedy food',
  fire_rate: 'chance a random mature plant ignites each tick (0.0005) — storm lightning raises to 0.002',
  fire_spread_rate: 'spread to neighboring plants within 6 (0.08) — kills creatures/plants, ash fertilizes',
  disaster_rate: 'meteor/flood stochastic gated by this per tick (0.0003) — crater/water reshapes terrain',
  signal_radius: 'heard within this range (12) — clan-mates respond strongly, strangers weakly',
  food_call_rate: 'well-fed finds food → calls with this chance/tick (0.08)',
  alarm_call_rate: 'sees predator → alarm call chance/tick (0.12)',
  knowledge_ttl: 'ticks a learned fact stays in memory before it fades (600)',
  knowledge_share_rate: 'chance/tick a creature broadcasts its freshest fact to clan-mates (0.05) — rumors arrive at half confidence',
  help_radius: 'clan-mates rally to a help call within this range (12); defenders near the fight soften its blows',
  defense_weight: 'damage reduction per defender mobbing the attacker (0.5 → 2 defenders = 50% softer)',
  winter_food_mult: 'winter bounty × winter_food_mult (0.7 gentle, 0.5 harsh, 0.3 extinction) — lean season target = food_count × winter_food_mult',
  schism_threshold: 'fraction unhappy (starving/homeless) to split (0.4)',
  schism_min_pop: 'minimum clan population to consider schism (4)',
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

  const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768
  const [openHint, setOpenHint] = useState<string | null>(null)

  if (!open) return null

  const set = (key: NumberLawKey, raw: string) =>
    setLaws((l) => ({ ...l, [key]: raw === '' ? undefined : Number(raw) }))

  const postLaws = async (persist: boolean) => {
    setError(null)
    setSaved(false)
    try {
      const qs = persist ? '?persist=true' : '?persist=false'
      const res = await godFetch(`/api/laws${qs}`, {
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
      if (e instanceof Error && e.message === 'cancelled') return
      setError(e instanceof Error ? e.message : 'failed to apply law')
    }
  }
  const apply = () => postLaws(false)
  const save = () => postLaws(true)
  const applyPreset = async (name: string, reset: boolean) => {
    setError(null)
    setSaved(false)
    try {
      const res = await godFetch(`/api/presets/${name}?persist=true${reset ? '&reset=true' : ''}`, { method: 'POST' })
      if (!res.ok) throw new Error((await res.json()).detail ?? 'preset failed')
      const data = await res.json()
      setLaws(data.laws)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      if (e instanceof Error && e.message === 'cancelled') return
      setError(e instanceof Error ? e.message : 'preset failed')
    }
  }

  const panel = (
    <aside className="god-panel" onClick={e => e.stopPropagation()}>
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
      <div className="god-group" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: '#8b949e', width: '100%' }}>Presets — one click 1000-day world</span>
        <button onClick={() => applyPreset('sustainable', false)} title="1000-day gentle: 180 food, winter 0.7, rare war/predation, fast drift" style={{ flex: 1, borderColor: '#3fb950', color: '#3fb950' }}>🌿 Sustainable</button>
        <button onClick={() => applyPreset('chaos', false)} title="Chaos: famine, predators, wars, plagues, fires" style={{ flex: 1, borderColor: '#f85149', color: '#f85149' }}>🔥 Chaos</button>
        <button onClick={() => applyPreset('extinction', false)} title="Extinction: 30 food, harsh winter 0.3, high decay" style={{ flex: 1 }}>💀 Extinction</button>
        <button onClick={() => applyPreset('sustainable', true)} title="Apply sustainable + reset world now" style={{ width: '100%', marginTop: 4 }}>🌿 Sustainable + Reset</button>
      </div>

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

          {GROUP_ORDER.map((group) => {
            const lawsInGroup = NUMBER_LAWS.filter((l) => l.group === group)
            const special = (
              <>
                {group === 'Reproduction' && (
                  <label className="god-row">
                    <span title="whether new life may begin at all">Births allowed</span>
                    <select value={String(laws.birth_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, birth_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Disease' && (
                  <label className="god-row">
                    <span title="plagues walk the world; disabling freezes all sickness">Plagues allowed</span>
                    <select value={String(laws.disease_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, disease_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Sky & Seasons' && (
                  <>
                    <label className="god-row">
                      <span title="whether the weather ever turns">Weather allowed</span>
                      <select value={String(laws.weather_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, weather_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                    <label className="god-row">
                      <span title="creatures shelter in houses after dark">Night rest</span>
                      <select value={String(laws.sleep_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, sleep_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                  </>
                )}
                {group === 'Shelter' && (
                  <label className="god-row">
                    <span title="creatures may claim roofs; disabling leaves all exposed">Shelter allowed</span>
                    <select value={String(laws.shelter_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, shelter_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Territory' && (
                  <label className="god-row">
                    <span title="clans claim a circle around their house; disabling removes borders">Territory claimed</span>
                    <select value={String(laws.territory_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, territory_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Weather Sickness' && (
                  <label className="god-row">
                    <span title="chill and wet contagion — rain/storm/winter nights build chill, past threshold drains health; wet catches disease faster">Weather sickness</span>
                    <select value={String(laws.weather_sickness_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, weather_sickness_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Communication' && (
                  <label className="god-row">
                    <span title="food + alarm calls — clan-mates respond strongly, strangers weakly; rendered as ripples">Communication</span>
                    <select value={String(laws.communication_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, communication_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Communication II' && (
                  <>
                    <label className="god-row">
                      <span title="creatures learn facts from experience (food/danger/enemies/safe homes), share them as rumors at half confidence; the clan remembers">Knowledge</span>
                      <select value={String(laws.knowledge_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, knowledge_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                    <label className="god-row">
                      <span title="an attacked creature calls its clan; warriors rally first and mob the attacker, defenders soften its blows">Help calls</span>
                      <select value={String(laws.help_call_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, help_call_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                  </>
                )}
                {group === 'Wildfire & Disasters' && (
                  <>
                    <label className="god-row">
                      <span title="fire ignites via storm lightning / fire_rate and spreads grass→plant→house; ash fertilizes">Wildfire</span>
                      <select value={String(laws.wildfire_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, wildfire_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                    <label className="god-row">
                      <span title="meteor/flood stochastic — god sets frequency, never a specific strike">Disasters</span>
                      <select value={String(laws.disaster_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, disaster_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                  </>
                )}
                {group === 'Culture' && (
                  <label className="god-row">
                    <span title="culture spreads to allied neighbours, can split into rival traditions; grants small collective bonus">Culture</span>
                    <select value={String(laws.culture_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, culture_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Genetics' && (
                  <div className="god-note" style={{ fontSize: 11, opacity: 0.7 }}>Heritable traits: greedy/peaceful/paranoid/bold — mutation {laws.trait_mutation_rate ?? 0.02}</div>
                )}
                {group === 'Ages' && (
                  <label className="god-row">
                    <span title="super-seasons: Golden/ Ice/ Chaos/ Plague — each bends food/mutation/disease/chill. God sets length, world cycles.">Ages</span>
                    <select value={String(laws.age_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, age_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Rebellion' && (
                  <label className="god-row">
                    <span title="unhappy members (starving/homeless) split off to found new clan then war parent — schism_threshold fraction to trigger">Schism allowed</span>
                    <select value={String(laws.schism_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, schism_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Clan' && (
                  <>
                    <label className="god-row">
                      <span title="each clan bears a totem (Wolf 🐺, Tree 🌳, Shield 🛡️, Eye 👁️, Bear 🐻, Stag 🦌, Owl 🦉, Rabbit 🐇, Boar 🐗, Fox 🦊, Raven 🐦‍⬛, Serpent 🐍) granting a subtle buff; disabling makes all clans plain">Totems</span>
                      <select value={String(laws.totems_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, totems_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                    <label className="god-row">
                      <span title="leader succession on death emits succession event; disabling keeps founder as eternal leader">Succession</span>
                      <select value={String(laws.succession_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, succession_enabled: e.target.value === 'true' }))}>
                        <option value="true">yes</option><option value="false">no</option>
                      </select>
                    </label>
                  </>
                )}
                {group === 'Ecosystem' && (
                  <label className="god-row">
                    <span title="grass/berry/mushroom/poisonous diversity; disabling makes all plants grass">Plant variants</span>
                    <select value={String(laws.plant_variants_enabled ?? true)} onChange={(e) => setLaws((l) => ({ ...l, plant_variants_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Predation' && (
                  <label className="god-row">
                    <span title="predators hunt prey; disabling makes them docile">Predation allowed</span>
                    <select value={String(laws.predation_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, predation_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
                {group === 'Clan War' && (
                  <label className="god-row">
                    <span title="rival clans fight on contact; disabling enforces peace">War allowed</span>
                    <select value={String(laws.war_enabled ?? false)} onChange={(e) => setLaws((l) => ({ ...l, war_enabled: e.target.value === 'true' }))}>
                      <option value="true">yes</option><option value="false">no</option>
                    </select>
                  </label>
                )}
              </>
            )
            const rows = lawsInGroup.map(({ key, label, min, max, step }) => {
              const hint = LAW_HINTS[key]
              const isOpen = openHint === key
              return (
                <div key={key} style={{ borderBottom: '1px solid rgba(48,54,61,0.3)', paddingBottom: isOpen ? 6 : 0 }}>
                  <label className="god-row">
                    <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span title={hint}>{label}</span>
                      {hint && (
                        <button
                          onClick={() => setOpenHint(isOpen ? null : key)}
                          title={hint}
                          style={{ width: 20, height: 20, borderRadius: '50%', border: '1px solid #30363d', background: isOpen ? '#21262d' : '#161b22', color: isOpen ? '#e6edf3' : '#8b949e', fontSize: 11, lineHeight: 1, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}
                          aria-label={`hint for ${label}`}
                        >
                          ?
                        </button>
                      )}
                    </span>
                    {isMobile ? (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <input type="range" min={min} max={max} step={step} value={(laws[key] as number | undefined) ?? min} onChange={(e) => set(key, e.target.value)} style={{ width: 96 }} />
                        <span style={{ minWidth: 36, textAlign: 'right', fontSize: 11, color: '#8b949e' }}>{(laws[key] as number | undefined)?.toFixed?.(step < 1 ? 2 : 0) ?? ''}</span>
                      </span>
                    ) : (
                      <input type="number" min={min} max={max} step={step} value={(laws[key] as number | undefined) ?? ''} onChange={(e) => set(key, e.target.value)} />
                    )}
                  </label>
                  {isOpen && hint && (
                    <div style={{ fontSize: 11, color: '#c9d1d9', background: '#161b22', border: '1px solid #21262d', borderRadius: 6, padding: '6px 8px', margin: '4px 10px 8px 10px', lineHeight: 1.4 }}>
                      {hint}
                      <div style={{ marginTop: 6 }}>
                        <a href="/docs/god-laws.md" rel="noreferrer" style={{ fontSize: 11, color: '#58a6ff' }}>Open docs/god-laws.md ↗</a>
                        {' · '}
                        <a href="/wiki#god-laws" style={{ fontSize: 11, color: '#58a6ff' }}>Wiki → God laws</a>
                      </div>
                    </div>
                  )}
                </div>
              )
            })
            if (isMobile) {
              return (
                <details key={group} className="god-accordion" open={group === 'Food & Energy'}>
                  <summary>{group} <span style={{ fontSize: 10, color: '#8b949e' }}>{lawsInGroup.length}</span></summary>
                  {special}
                  {rows}
                </details>
              )
            }
            return (
              <section key={group} className="god-group">
                <h3>{group}</h3>
                {special}
                {rows}
              </section>
            )
          })}

          <footer className="god-foot">
            {error && <span className="god-error">{error}</span>}
            {!error && saved && <span className="god-saved">laws applied</span>}
            <button onClick={apply} title="apply to current world only (Reset reverts)">Apply</button>
            <button onClick={save} title="save to current and future worlds (Reset keeps it)" className="god-save">
              Save
            </button>
          </footer>
        </>
      )}
    </aside>
  )
  if (isMobile) {
    return (
      <div className="god-backdrop" onClick={onClose}>
        {panel}
      </div>
    )
  }
  return panel
}
