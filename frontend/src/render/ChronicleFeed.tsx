import { useMemo, useState } from 'react'
import type { HistoryEvent } from '../types'

export type EventCategory = 'all' | 'conflict' | 'clan' | 'deaths' | 'plague' | 'nature'

interface Props {
  events: HistoryEvent[]
  clanLabel: (id?: number | null) => string
  onSelectCreature: (id: number) => void
  onSelectClan: (id: number) => void
  onLoadOlder?: () => void
  loadingOlder?: boolean
  noMoreHistory?: boolean
  archiveMode?: boolean
  selectedRunId?: number | null
  maxDisplay?: number
  compact?: boolean
  onOpenWorldHistory?: () => void
}

const CATEGORIES: Array<{ key: EventCategory; label: string; icon: string }> = [
  { key: 'all', label: 'All', icon: '📜' },
  { key: 'conflict', label: 'Conflict', icon: '⚔️' },
  { key: 'clan', label: 'Clan & Life', icon: '🌱' },
  { key: 'deaths', label: 'Deaths', icon: '💀' },
  { key: 'plague', label: 'Plague', icon: '☣️' },
  { key: 'nature', label: 'Nature', icon: '🌸' },
]

function matchesCategory(ev: HistoryEvent, category: EventCategory): boolean {
  if (category === 'all') {
    return ev.type !== 'bloom' && ev.type !== 'wither' && ev.type !== 'ruin'
  }
  if (category === 'conflict') {
    return [
      'war',
      'betrayal',
      'schism',
      'conquest',
      'takeover',
      'raid',
      'coalition_formed',
      'coalition_joined',
      'coalition_dissolved',
      'peace',
      'peace_envoy',
      'defection',
      'cannibalism',
      'exile',
      'predation',
      'rivalry',
    ].includes(ev.type)
  }
  if (category === 'clan') {
    return [
      'birth',
      'settlement',
      'succession',
      'culture',
      'alliance',
      'tribute',
      'promotion',
      'demotion',
      'miracle',
      'sermon',
      'synod',
      'temple',
      'epiphany',
      'resonance',
      'hospitality',
      'banquet',
      'market',
      'caravan',
      'omen',
      'regicide',
      'herald',
    ].includes(ev.type)
  }
  if (category === 'deaths') {
    return ev.type === 'death' || ev.type === 'war' || ev.type === 'predation' || ev.type === 'cannibalism'
  }
  if (category === 'plague') {
    return ev.type === 'outbreak' || ev.type === 'recovery' || (ev.type === 'death' && ev.cause === 'disease')
  }
  if (category === 'nature') {
    return ['bloom', 'wither', 'ruin', 'fire', 'disaster', 'compost', 'anomaly'].includes(ev.type)
  }
  return true
}

function matchesSearch(ev: HistoryEvent, query: string, clanLabel: (id?: number | null) => string): boolean {
  if (!query) return true
  const q = query.toLowerCase().trim()
  const p = (ev.payload ?? {}) as Record<string, any>
  const idStr = String(ev.entity_id)
  if (idStr === q || `#${idStr}` === q || idStr.includes(q)) return true
  if (p.personal_name && String(p.personal_name).toLowerCase().includes(q)) return true
  if (ev.caste && ev.caste.toLowerCase().includes(q)) return true
  if (ev.cause && ev.cause.toLowerCase().includes(q)) return true
  if (ev.type && ev.type.toLowerCase().includes(q)) return true
  if (p.clan_name && String(p.clan_name).toLowerCase().includes(q)) return true
  if (p.culture && String(p.culture).toLowerCase().includes(q)) return true
  if (p.mother && (String(p.mother) === q || `#${p.mother}` === q)) return true
  if (p.father && (String(p.father) === q || `#${p.father}` === q)) return true
  if (p.winner && (String(p.winner) === q || `#${p.winner}` === q)) return true
  if (p.prey && (String(p.prey) === q || `#${p.prey}` === q)) return true
  if (p.clan_id && clanLabel(p.clan_id).toLowerCase().includes(q)) return true
  if (p.a != null && clanLabel(p.a).toLowerCase().includes(q)) return true
  if (p.b != null && clanLabel(p.b).toLowerCase().includes(q)) return true
  if (p.from != null && clanLabel(p.from).toLowerCase().includes(q)) return true
  if (p.to != null && clanLabel(p.to).toLowerCase().includes(q)) return true
  if (p.parent != null && clanLabel(p.parent).toLowerCase().includes(q)) return true
  if (p.new_clan != null && clanLabel(p.new_clan).toLowerCase().includes(q)) return true
  return false
}

export default function ChronicleFeed({
  events,
  clanLabel,
  onSelectCreature,
  onSelectClan,
  onLoadOlder,
  loadingOlder = false,
  noMoreHistory = false,
  archiveMode = false,
  selectedRunId = null,
  maxDisplay = 200,
  compact = false,
  onOpenWorldHistory,
}: Props) {
  const [category, setCategory] = useState<EventCategory>('all')
  const [search, setSearch] = useState('')
  const [visibleLimit, setVisibleLimit] = useState(maxDisplay)

  const filtered = useMemo(() => {
    return events.filter(
      (ev) => matchesCategory(ev, category) && matchesSearch(ev, search, clanLabel),
    )
  }, [events, category, search, clanLabel])

  const displayed = useMemo(() => filtered.slice(0, visibleLimit), [filtered, visibleLimit])

  return (
    <div
      className={`chronicle-feed-container ${compact ? 'chronicle-compact' : ''}`}
      style={{ display: 'flex', flexDirection: 'column', gap: compact ? 6 : 8, height: '100%', minHeight: 0, flex: '1 1 0' }}
    >
      {archiveMode && selectedRunId !== null && (
        <p className="archive-banner" style={{ margin: 0 }}>
          viewing archive of world #{selectedRunId} — live feed paused
        </p>
      )}

      {/* Filter Controls Bar */}
      <div
        className="chronicle-controls"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          background: 'rgba(22, 27, 34, 0.75)',
          border: '1px solid #30363d',
          borderRadius: 8,
          padding: '6px 8px',
        }}
      >
        {/* Search input */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: '#8b949e' }}>🔍</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter logs (e.g. #42, Wolf, starvation, birth)..."
            style={{
              flex: 1,
              background: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: 6,
              padding: '4px 8px',
              fontSize: 12,
              color: '#e6edf3',
              minHeight: 28,
            }}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#8b949e',
                fontSize: 12,
                cursor: 'pointer',
                padding: '2px 6px',
                minHeight: 28,
              }}
              title="Clear search"
            >
              ✕
            </button>
          )}
          {onOpenWorldHistory && (
            <button
              type="button"
              onClick={onOpenWorldHistory}
              style={{
                background: '#1f6feb',
                border: '1px solid #388bfd',
                color: '#fff',
                borderRadius: 6,
                padding: '3px 8px',
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                flex: 'none',
                minHeight: 28,
              }}
              title="Open Major World History & Export AI Story Prompt"
            >
              <span>📜</span> History & Story
            </button>
          )}
        </div>

        {/* Category Pills */}
        <div
          className="chronicle-pills"
          style={{
            display: 'flex',
            gap: 4,
            overflowX: 'auto',
            scrollbarWidth: 'none',
            paddingBottom: 2,
          }}
        >
          {CATEGORIES.map((cat) => {
            const active = category === cat.key
            return (
              <button
                key={cat.key}
                type="button"
                onClick={() => setCategory(cat.key)}
                style={{
                  padding: '2px 8px',
                  fontSize: 11,
                  fontWeight: active ? 700 : 500,
                  borderRadius: 12,
                  background: active ? '#21262d' : '#161b22',
                  borderColor: active ? '#58a6ff' : '#30363d',
                  color: active ? '#58a6ff' : '#8b949e',
                  whiteSpace: 'nowrap',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  minHeight: 24,
                  flex: 'none',
                  cursor: 'pointer',
                }}
              >
                <span>{cat.icon}</span>
                <span>{cat.label}</span>
              </button>
            )
          })}
        </div>

        {/* Status Count & Clear */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: 11,
            color: '#8b949e',
            paddingTop: 2,
          }}
        >
          <span>
            Showing <b>{displayed.length}</b> of <b>{filtered.length}</b> {filtered.length === 1 ? 'event' : 'events'}
            {filtered.length !== events.length && ` (${events.length} total)`}
          </span>
          {(category !== 'all' || search) && (
            <button
              type="button"
              onClick={() => {
                setCategory('all')
                setSearch('')
              }}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#58a6ff',
                fontSize: 11,
                cursor: 'pointer',
                padding: 0,
                textDecoration: 'underline',
              }}
            >
              Reset filter
            </button>
          )}
        </div>
      </div>

      {!archiveMode && onLoadOlder && (
        <button
          type="button"
          className="chron-btn"
          onClick={onLoadOlder}
          disabled={loadingOlder || noMoreHistory}
          style={{ width: '100%', minHeight: 28, fontSize: 11 }}
        >
          {loadingOlder ? 'loading older…' : noMoreHistory ? 'no older events' : '↓ Load older events'}
        </button>
      )}

      {/* Event Items List */}
      {displayed.length === 0 ? (
        <p className="chip" style={{ margin: '8px 0', textAlign: 'center' }}>
          {search || category !== 'all' ? 'No events matching filter' : 'No major events recorded yet'}
        </p>
      ) : (
        <ul
          className="chronicle-feed-list"
          style={{ margin: 0, padding: 0, listStyle: 'none', flex: '1 1 0', overflowY: 'auto', minHeight: 0 }}
        >
          {displayed.map((ev) => {
            const key = `${ev.tick}:${ev.entity_id}:${ev.type}`
            const p = (ev.payload ?? {}) as Record<string, any>

            if (ev.type === 'birth') {
              const nm = p.personal_name ?? ev.caste
              const gl = p.glyph ? ` ${p.glyph}` : ''
              return (
                <li key={key} className="ev-birth">
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show profile">
                    <b>{nm}{gl}</b> #{ev.entity_id}
                  </button>{' '}
                  born to{' '}
                  <button className="chronicle-name" onClick={() => p.mother && onSelectCreature(p.mother)} title="show mother">
                    #{p.mother}
                  </button>{' '}
                  ×{' '}
                  <button className="chronicle-name" onClick={() => p.father && onSelectCreature(p.father)} title="show father">
                    #{p.father}
                  </button>{' '}
                  (gen {p.generation ?? 0}) at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'promotion') {
              const nm = p.personal_name ? `${p.personal_name} ` : ''
              return (
                <li key={key} className="ev-promo">
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show profile">
                    <b>{nm}#{ev.entity_id}</b>
                  </button>{' '}
                  rose {String(p.from ?? 'Soldier')} → {String(p.to ?? ev.caste)} at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'demotion') {
              const nm = p.personal_name ?? ev.caste
              const gl = p.glyph ? ` ${p.glyph}` : ''
              return (
                <li key={key} className="ev-demote">
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show profile">
                    <b>{nm}{gl}</b> #{ev.entity_id}
                  </button>{' '}
                  judged irregular and demoted to Woman at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'predation') {
              const nm = p.personal_name ?? ev.caste
              const gl = p.glyph ? ` ${p.glyph}` : ''
              return (
                <li key={key} className="ev-predation">
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show predator">
                    <b>{nm}{gl}</b> #{ev.entity_id}
                  </button>{' '}
                  predated <b>{p.prey_caste ?? 'Creature'}</b>{' '}
                  <button className="chronicle-name" onClick={() => p.prey && onSelectCreature(p.prey)} title="show prey">
                    #{p.prey}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'war') {
              const nm = p.personal_name ?? ev.caste
              const gl = p.glyph ? ` ${p.glyph}` : ''
              return (
                <li key={key} className="ev-war">
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show fallen">
                    <b>{nm}{gl}</b> #{ev.entity_id}
                  </button>{' '}
                  fell in clan war (winner{' '}
                  <button className="chronicle-name" onClick={() => p.winner && onSelectCreature(p.winner)} title="show winner">
                    #{p.winner}
                  </button>) at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'alliance' || ev.type === 'rivalry') {
              return (
                <li key={key} className={ev.type === 'alliance' ? 'ev-alliance' : 'ev-rivalry'}>
                  Clans{' '}
                  <button className="chronicle-name" onClick={() => p.a != null && onSelectClan(p.a)} title="show clan">
                    {clanLabel(p.a)}
                  </button>{' '}
                  &{' '}
                  <button className="chronicle-name" onClick={() => p.b != null && onSelectClan(p.b)} title="show clan">
                    {clanLabel(p.b)}
                  </button>{' '}
                  {ev.type} (score {p.score}) at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'schism') {
              return (
                <li key={key} className="ev-schism">
                  schism:{' '}
                  <button className="chronicle-name" onClick={() => p.parent != null && onSelectClan(p.parent)} title="show parent clan">
                    {p.parent_name ?? clanLabel(p.parent)}
                  </button>{' '}
                  →{' '}
                  <button className="chronicle-name" onClick={() => p.new_clan != null && onSelectClan(p.new_clan)} title="show new clan">
                    {p.new_name ?? clanLabel(p.new_clan)}
                  </button>{' '}
                  ({(p.members as number[])?.length ?? 0} broke away) at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'conquest') {
              return (
                <li key={key} className="ev-war">
                  conquest: clan{' '}
                  <button className="chronicle-name" onClick={() => p.winner_clan != null && onSelectClan(p.winner_clan)} title="show winner clan">
                    {clanLabel(p.winner_clan)}
                  </button>{' '}
                  seized house {p.house_id} from clan{' '}
                  <button className="chronicle-name" onClick={() => p.loser_clan != null && onSelectClan(p.loser_clan)} title="show loser clan">
                    {clanLabel(p.loser_clan)}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'takeover') {
              return (
                <li key={key} className="ev-war">
                  takeover: clan{' '}
                  <button className="chronicle-name" onClick={() => p.invader_clan != null && onSelectClan(p.invader_clan)} title="show invader clan">
                    {p.invader_name ?? clanLabel(p.invader_clan)}
                  </button>{' '}
                  moved into house {p.house_id} abandoned by clan{' '}
                  <button className="chronicle-name" onClick={() => p.victim_clan != null && onSelectClan(p.victim_clan)} title="show victim clan">
                    {p.victim_name ?? clanLabel(p.victim_clan)}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'coalition_formed' || ev.type === 'coalition_joined' || ev.type === 'coalition_dissolved') {
              const who = ev.type === 'coalition_joined'
                ? <>clan <button className="chronicle-name" onClick={() => p.clan != null && onSelectClan(p.clan)} title="show clan">{clanLabel(p.clan)}</button> joined</>
                : ev.type === 'coalition_dissolved'
                  ? <>{p.reason ?? 'dissolved'} —</>
                  : <>founded by clan <button className="chronicle-name" onClick={() => p.leader_clan != null && onSelectClan(p.leader_clan)} title="show founder clan">{clanLabel(p.leader_clan)}</button></>
              return (
                <li key={key} className="ev-alliance" style={{ color: '#7ee787' }}>
                  {ev.type === 'coalition_formed' ? 'coalition formed: ' : ''}{who} <b>{String(p.name ?? `coalition #${p.coalition}`)}</b> ({(p.members as number[] | undefined)?.length ?? 0} members) at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'peace') {
              return (
                <li key={key} className="ev-alliance">
                  peace: clans{' '}
                  <button className="chronicle-name" onClick={() => p.a != null && onSelectClan(p.a)} title="show clan">
                    {clanLabel(p.a)}
                  </button>{' '}
                  &{' '}
                  <button className="chronicle-name" onClick={() => p.b != null && onSelectClan(p.b)} title="show clan">
                    {clanLabel(p.b)}
                  </button>{' '}
                  lay down arms at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'tribute') {
              return (
                <li key={key} className="ev-alliance">
                  tribute: clan{' '}
                  <button className="chronicle-name" onClick={() => p.from != null && onSelectClan(p.from)} title="show vassal clan">
                    {clanLabel(p.from)}
                  </button>{' '}
                  pays {p.amount ?? '?'} to protector{' '}
                  <button className="chronicle-name" onClick={() => p.to != null && onSelectClan(p.to)} title="show protector clan">
                    {clanLabel(p.to)}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'betrayal') {
              return (
                <li key={key} className="ev-war">
                  betrayal: clan{' '}
                  <button className="chronicle-name" onClick={() => p.a != null && onSelectClan(p.a)} title="show betrayer">
                    {clanLabel(p.a)}
                  </button>{' '}
                  turns on ally{' '}
                  <button className="chronicle-name" onClick={() => p.b != null && onSelectClan(p.b)} title="show betrayed">
                    {clanLabel(p.b)}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'defection') {
              return (
                <li key={key} className="ev-schism">
                  defection:{' '}
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show creature">
                    #{ev.entity_id}
                  </button>{' '}
                  leaves clan{' '}
                  <button className="chronicle-name" onClick={() => p.from != null && onSelectClan(p.from)} title="show old clan">
                    {clanLabel(p.from)}
                  </button>{' '}
                  for{' '}
                  <button className="chronicle-name" onClick={() => p.to != null && onSelectClan(p.to)} title="show new clan">
                    {clanLabel(p.to)}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'cannibalism') {
              return (
                <li key={key} className="ev-predation">
                  cannibalism: starving{' '}
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show eater">
                    <b>{ev.caste}</b> #{ev.entity_id}
                  </button>{' '}
                  ate {p.kin ? <b>kin</b> : 'enemy'} {p.prey_caste}{' '}
                  <button className="chronicle-name" onClick={() => p.prey && onSelectCreature(p.prey)} title="show prey">
                    #{p.prey}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'exile') {
              return (
                <li key={key} className="ev-demote">
                  exile: kin-eater{' '}
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show outcast">
                    <b>{String(p.personal_name ?? '')}{String(p.glyph ?? '')}</b> #{ev.entity_id}
                  </button>{' '}
                  cast out of {p.former_name ?? clanLabel(p.former_clan)} at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'miracle') {
              return (
                <li key={key} className="ev-bloom" style={{ color: '#7ee787' }}>
                  miracle: the {String(p.avatar ?? 'avatar')} grants{' '}
                  <button className="chronicle-name" onClick={() => p.clan_id != null && onSelectClan(p.clan_id)} title="show clan">
                    {p.clan_name ?? clanLabel(p.clan_id)}
                  </button>{' '}
                  a bounty — food blooms around the shrine at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'sermon') {
              return (
                <li key={key} className="ev-alliance" style={{ color: '#d2a8ff' }}>
                  sermon:{' '}
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show priest">
                    <b>{ev.caste} #{ev.entity_id}</b>
                  </button>{' '}
                  of{' '}
                  <button className="chronicle-name" onClick={() => p.clan_id != null && onSelectClan(p.clan_id)} title="show clan">
                    {p.clan_name ?? clanLabel(p.clan_id)}
                  </button>{' '}
                  interprets the new law — {String(p.text ?? '')} at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'synod') {
              return (
                <li key={key} className="ev-alliance" style={{ color: '#e3b341' }}>
                  ⛪ synod of the Sphere: priests of {(p.clans as number[] | undefined)?.length ?? '?'} clans convene during the {String(p.age ?? 'crisis')} age —
                  a sacred truce stills all strife at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'temple') {
              return (
                <li key={key} className="ev-settlement" style={{ color: '#e3b341' }}>
                  temple:{' '}
                  <button className="chronicle-name" onClick={() => p.clan_id != null && onSelectClan(p.clan_id)} title="show clan">
                    {p.clan_name ?? clanLabel(p.clan_id)}
                  </button>{' '}
                  raises its {String(p.avatar ?? 'avatar')} shrine into a glowing Temple of the Sphere at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'epiphany') {
              return (
                <li key={key} className="ev-miracle" style={{ color: '#bc8cff' }}>
                  ✦ epiphany: elder priest{' '}
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show priest">
                    <b>{String(p.personal_name ?? '')}{String(p.glyph ?? '')}</b> #{ev.entity_id}
                  </button>{' '}
                  beholds the Sphere in three dimensions — sectarian strife stills at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'resonance') {
              return (
                <li key={key} className="ev-alliance" style={{ color: '#e3b341' }}>
                  🔔 resonance: god alters {String(((p.laws as string[]) ?? []).join(', ') || 'the laws')} — every shrine chimes ({String(p.chimes ?? 0)}), {String(p.sermons ?? 0)} sermons ring out at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'settlement') {
              return (
                <li key={key} className="ev-bloom">
                  settlement founded
                  {p.clan_id ? (
                    <>
                      {' '}by clan{' '}
                      <button className="chronicle-name" onClick={() => onSelectClan(p.clan_id)} title="show clan">
                        {clanLabel(p.clan_id)}
                      </button>
                    </>
                  ) : ''}{' '}
                  at ({Math.round(ev.x)}, {Math.round(ev.y)}) tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'succession') {
              return (
                <li key={key} className="ev-promo">
                  succession in{' '}
                  <button className="chronicle-name" onClick={() => p.clan_id != null && onSelectClan(p.clan_id)} title="show clan">
                    {p.clan_name ?? clanLabel(p.clan_id)}
                  </button>
                  :{' '}
                  <button className="chronicle-name" onClick={() => p.new_leader && onSelectCreature(p.new_leader)} title="show new leader">
                    #{p.new_leader}
                  </button>{' '}
                  succeeds{' '}
                  <button className="chronicle-name" onClick={() => p.prev_leader && onSelectCreature(p.prev_leader)} title="show previous leader">
                    #{p.prev_leader}
                  </button>{' '}
                  at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'culture') {
              return (
                <li key={key} className="ev-bloom">
                  clan{' '}
                  <button className="chronicle-name" onClick={() => p.clan_id != null && onSelectClan(p.clan_id)} title="show clan">
                    {clanLabel(p.clan_id)}
                  </button>{' '}
                  embraces a new tradition: <b>{p.culture}</b> at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'bloom' || ev.type === 'wither') {
              return (
                <li key={key} className={ev.type === 'bloom' ? 'ev-bloom' : 'ev-wither'} style={{ color: ev.type === 'bloom' ? '#3fb950' : '#8b949e' }}>
                  {ev.type} at ({Math.round(ev.x)}, {Math.round(ev.y)}) tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'outbreak' || ev.type === 'recovery') {
              const nm = p.personal_name ?? ev.caste
              const gl = p.glyph ? ` ${p.glyph}` : ''
              return (
                <li key={key} className={ev.type === 'outbreak' ? 'ev-outbreak' : 'ev-recovery'}>
                  <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show creature">
                    <b>{nm}{gl}</b> #{ev.entity_id}
                  </button>{' '}
                  {ev.type} at tick {ev.tick}
                </li>
              )
            }

            if (ev.type === 'raid') {
              return (
                <li key={key} style={{ color: '#f85149' }}>
                  <button className="chronicle-name" onClick={() => onSelectClan(p.a)} title="show clan"><b>{p.a_name ?? `Clan ${p.a}`}</b></button>
                  {' '}raided the granary of{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.b)} title="show clan"><b>{p.b_name ?? `Clan ${p.b}`}</b></button>
                  {' '}(−{p.loot} grain) at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'banquet') {
              return (
                <li key={key} style={{ color: '#e3b341' }}>
                  🍞 <button className="chronicle-name" onClick={() => onSelectClan(p.clan_id)} title="show clan"><b>{p.clan_name ?? `Clan ${p.clan_id}`}</b></button>
                  {' '}feasted on their overflowing granary at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'compost') {
              const nm = p.personal_name ?? ev.caste
              return (
                <li key={key} style={{ color: '#3fb950' }}>
                  ♻️ <b>{nm}</b> #{ev.entity_id} composted the fields of{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.clan_id)} title="show clan">{p.clan_name ?? `Clan ${p.clan_id}`}</button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'hospitality') {
              return (
                <li key={key} style={{ color: '#79c0ff' }}>
                  🍞 bread broken between{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.a)} title="show clan"><b>{p.a_name ?? `Clan ${p.a}`}</b></button>
                  {' '}and{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.b)} title="show clan"><b>{p.b_name ?? `Clan ${p.b}`}</b></button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'peace_envoy') {
              return (
                <li key={key} style={{ color: '#d2a8ff' }}>
                  📜 an emissary of{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.a)} title="show clan"><b>{p.a_name ?? `Clan ${p.a}`}</b></button>
                  {' '}delivered treaty terms to{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.b)} title="show clan"><b>{p.b_name ?? `Clan ${p.b}`}</b></button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'market') {
              return (
                <li key={key} style={{ color: '#e3b341' }}>
                  ⚖️ a neutral market opened between{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.a)} title="show clan"><b>{p.a_name ?? `Clan ${p.a}`}</b></button>
                  {' '}and{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.b)} title="show clan"><b>{p.b_name ?? `Clan ${p.b}`}</b></button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'caravan') {
              return (
                <li key={key} style={{ color: '#8b949e' }}>
                  🐫 a trade caravan travelled between{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.a)} title="show clan"><b>{p.a_name ?? `Clan ${p.a}`}</b></button>
                  {' '}and{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.b)} title="show clan"><b>{p.b_name ?? `Clan ${p.b}`}</b></button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'regicide') {
              return (
                <li key={key} style={{ color: '#f85149' }}>
                  🗡 regicide: <b>{p.assassin}</b> of{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.assassin_clan)} title="show clan"><b>{p.assassin_clan_name ?? `Clan ${p.assassin_clan}`}</b></button>
                  {' '}murdered Chief #{p.victim} of{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.victim_clan)} title="show clan"><b>{p.victim_clan_name ?? `Clan ${p.victim_clan}`}</b></button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'herald') {
              return (
                <li key={key} style={{ color: '#8b949e' }}>
                  📜 a herald carried terms from{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.a)} title="show clan"><b>{p.a_name ?? `Clan ${p.a}`}</b></button>
                  {' '}to{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.b)} title="show clan"><b>{p.b_name ?? `Clan ${p.b}`}</b></button>
                  {' '}at tick {ev.tick}
                </li>
              )
            }
            if (ev.type === 'omen') {
              const nm = p.personal_name ?? ev.caste
              return (
                <li key={key} style={{ color: '#e3b341' }}>
                  🔮 <b>{nm}</b> beheld an omen for{' '}
                  <button className="chronicle-name" onClick={() => onSelectClan(p.clan_id)} title="show clan">{p.clan_name ?? `Clan ${p.clan_id}`}</button>
                  {': the '}{String(p.season)}{' '}approaches (tick {ev.tick})
                </li>
              )
            }

            // Default: death
            const nm = p.personal_name ?? ev.caste
            const gl = p.glyph ? ` ${p.glyph}` : ''
            return (
              <li key={key}>
                <button className="chronicle-name" onClick={() => onSelectCreature(ev.entity_id)} title="show profile">
                  <b>{nm}{gl}</b> #{ev.entity_id}
                </button>{' '}
                died of {ev.cause} at tick {ev.tick} ({Math.round(ev.x)}, {Math.round(ev.y)})
              </li>
            )
          })}
        </ul>
      )}

      {filtered.length > visibleLimit && (
        <button
          type="button"
          className="chron-btn"
          onClick={() => setVisibleLimit((l) => l + 100)}
          style={{ width: '100%', minHeight: 28, fontSize: 11, marginTop: 4 }}
        >
          Show more ({filtered.length - visibleLimit} remaining)
        </button>
      )}
    </div>
  )
}
