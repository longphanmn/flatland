"""Living guide — backend-rendered docs that always match the running code.

No Vite dependency. Renders markdown to HTML with a minimal template + nav.
Auto-generates GodLaws table and API reference from the live OpenAPI schema.
"""

import re
import html
from pathlib import Path
from typing import Any

from .config import Config
from .protocol import GodLaws


def _md_to_html(md: str) -> str:
    """Tiny markdown → HTML: headings, bold, italic, code, links, lists, paragraphs."""
    # Escape first, then selectively unescape markdown constructs
    lines = md.split("\n")
    out: list[str] = []
    in_code = False
    in_ul = False
    in_ol = False

    def inline(s: str) -> str:
        # escape html
        s = html.escape(s)
        # code `x`
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        # bold **x** or __x__
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", s)
        # italic *x* or _x_
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        # links [text](url)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(html.escape(line))
            continue
        if not line.strip():
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            continue
        # headings
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            lvl = len(m.group(1))
            text = inline(m.group(2).strip())
            slug = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
            out.append(f'<h{lvl} id="{slug}">{text}</h{lvl}>')
            continue
        # unordered list
        if re.match(r"^[-*]\s+", line):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            if in_ol:
                out.append("</ol>")
                in_ol = False
            txt = inline(re.sub(r"^[-*]\s+", "", line))
            out.append(f"<li>{txt}</li>")
            continue
        # ordered list
        if re.match(r"^\d+\.\s+", line):
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            if in_ul:
                out.append("</ul>")
                in_ul = False
            txt = inline(re.sub(r"^\d+\.\s+", "", line))
            out.append(f"<li>{txt}</li>")
            continue
        # paragraph
        if in_ul or in_ol:
            # close lists if next line is paragraph
            pass
        out.append(f"<p>{inline(line)}</p>")

    if in_ul:
        out.append("</ul>")
    if in_ol:
        out.append("</ol>")
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


def _god_laws_table() -> str:
    """Auto-generated table of every GodLaws field with type/range/default + hint."""
    cfg = Config()
    # keep hints in sync with frontend/src/god/GodPanel.tsx LAW_HINTS and docs/god-laws.md
    try:
        from .wiki import LAW_HINTS_MD
    except Exception:
        LAW_HINTS_MD = {}
    rows = []
    for name, field in GodLaws.model_fields.items():
        ann = str(field.annotation)
        constraints = []
        for m in getattr(field, "metadata", []):
            if hasattr(m, "ge") and m.ge is not None:
                constraints.append(f"≥{m.ge}")
            if hasattr(m, "le") and m.le is not None:
                constraints.append(f"≤{m.le}")
            if hasattr(m, "gt") and m.gt is not None:
                constraints.append(f">{m.gt}")
        default = getattr(cfg, name, None) if hasattr(cfg, name) else None
        typ = ann.replace("Optional", "").replace("[", "").replace("]", "").strip(" |None")
        hint = html.escape(LAW_HINTS_MD.get(name, "")) if 'LAW_HINTS_MD' in locals() else ""
        hint_cell = f'<small style="color:#8b949e">{hint}</small> <a href="/docs/god-laws.md#{html.escape(name)}" style="font-size:10px">md</a>' if hint else "—"
        rows.append(
            f"<tr><td><code>{html.escape(name)}</code></td>"
            f"<td>{html.escape(typ)}</td>"
            f"<td>{html.escape(', '.join(constraints) or '—')}</td>"
            f"<td>{html.escape(str(default))}</td>"
            f"<td>{hint_cell}</td></tr>"
        )
    header = "<tr><th>Law</th><th>Type</th><th>Range</th><th>Default</th><th>Hint + docs</th></tr>"
    return f'<div style="overflow-x:auto"><table><thead>{header}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def _api_table(app: Any) -> str:
    """Auto-generated API table from live routes + OpenAPI schema."""
    rows = []
    for route in app.routes:
        # FastAPI routes have path and methods
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if not path or path.startswith("/guide") or path.startswith("/openapi") or path.startswith("/docs") or path.startswith("/redoc"):
            # include /guide itself for completeness but skip swagger internal
            if path.startswith("/guide"):
                pass
            else:
                continue
        if methods:
            for m in sorted(methods):
                if m in ("HEAD", "OPTIONS"):
                    continue
                rows.append(f"<tr><td><code>{html.escape(m)} {html.escape(path)}</code></td>"
                            f"<td>{html.escape(getattr(route, 'name', ''))}</td></tr>")
        else:
            rows.append(f"<tr><td><code>{html.escape(path)}</code></td><td></td></tr>")
    # ensure every REST route is listed: deduplicate
    rows = sorted(set(rows))
    header = "<tr><th>Route</th><th>Name</th></tr>"
    return f"<table><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"


# Static markdown sections (How the world works etc)
HOW_IT_WORKS_MD = """
# How the world works

**The Sphere (God model):** The Sphere (God) sets *laws* from Spaceland, never touches individual creatures. Everything else emerges.

## The deterministic tick
`s = Simulation(Config(seed))` → `s.step()` is fully deterministic (one `random.Random` per world). Same seed ⇒ same world. Tick loop (`simulation.py:539` `simulation.py:335`) order: weather → plants → rebuild index → creatures → disease → war → reproduce → relations → food law → corpses → settlements → tick+=1. Snapshots are pushed over WebSocket `state` every tick.

## Life cycle & stages (§A)
Creature.age ticks + caste-based lifespan (Woman 4800 → Priest 9000). Stage by `age/lifespan`: infant <15%, juvenile <30%, adult <75%, else elder. Stage scales speed & sight (infant 0.6×, elder 0.85×) and fertility (elder ×0.5). Death causes: `starvation`, `old_age`, `euthanasia`, `disease`.

## Health core (§AT-4 H-0)
Health is a resource, not a constant. Regeneration demands an energy surplus: below 40% of `energy_max` (`HEALTH_REGEN_MIN_ENERGY`) wounds stop closing — awake or asleep; sheltered rest heals at `0.15×rest_recovery_mult`, waking regen is `0.1/tick` (+Shield/Bear totems). Below 20% energy the body cannibalizes itself: `−0.05` health/tick (`HEALTH_SELF_DRAIN_*`) until death by `starvation` — famine now kills twice. Weakness slows every stride (`HEALTH_SPEED_TIERS`): health <80 ×0.95, <60 ×0.85, <40 ×0.70, <20 ×0.50. Sickly bodies cannot beget children: mating requires `health ≥ REPRO_MIN_HEALTH` (50), so a plague suppresses births without touching birth laws.

## Damage variety & healing economy (§AT-4 H-1)
Chronic hunger gnaws: below 20% energy for more than `EXHAUSTION_TICKS` 30 ticks drains `EXHAUSTION_DRAIN` 0.08 health/tick (death cause `exhaustion`). Age withers: elders lose `ELDER_DECAY_RATE` 0.02/tick passively. Sickness dims the eyes (`HEALTH_SIGHT_TIERS`: <60 ×0.90, <30 ×0.75) and blunts the harvest (`_forage_mult`: −20% under 60 HP, −50% under 30) so decline feeds on itself. The badly wounded (<30 HP) or grievously wounded never start a duel, though they can still be attacked; blows above `WOUND_MIN_DAMAGE` 15 leave a lingering wound (50–100 ticks, severity 1–2 by damage ≥40) that halves or quarters regen and hobbles speed (×0.85/×0.70). Where a body stands decides how fast it mends: waking regen runs at ×0.5 outdoors (`REGEN_OUTDOOR_MULT`) vs ×0.8 sheltered-awake vs full strength asleep indoors. And supper keeps working: berries set +0.3 health/tick for 20 ticks, grain +0.2×30, medicinal herbs +0.8×40 (`FOOD_HEAL_BONUS`) — a hurt creature even seeks herbs on a full stomach (herb targeting ignores the sated gate under 60 HP). Bodies differ in depth, too (`CASTE_MAX_HP`): Soldiers/Artisans pool 130 HP, Nobles/Predators 120, Women 110, Gentlemen/Herbivores 100, Professionals/Priests a delicate 90 — regeneration and healing cap at each body's own pool.

## Physics axioms (§AQ PH-0)
Energy is the universal currency. Sunlight is the world's only income: `_sun_factor()` follows the day cycle — zero through the night, full strength at noon — and gates both plant growth and seed spread, so nothing grows for free in the dark (winter's bite remains the season table). Every body pays upkeep by its geometric complexity (`METABOLIC_COST`): triangles 1.0×, squares 1.1×, pentagons 1.2×, hexagons/nobles 1.3×, women and priests 1.5× (a priest burns energy maintaining the aura) — applied to the per-tick decay on top of stage/lifestyle multipliers. And mending is a conversion, not a miracle: each point of regenerated health costs `HEALING_ENERGY_COST` 0.5 energy (charged only when healing actually happens).

## Thermodynamics & heat (§AQ PH-1)
A coarse ambient heat field (`TEMP_CELL` 25-unit cells, `_update_temperature`) relaxes toward a target each tick: the seasonal base (`SEASON_BASE_TEMP` spring 12° / summer 24° / autumn 8° / winter −4°) swept across the map from an edge — cold fronts enter from the west, warm fronts from the east — plus the day cycle (`DAY_HEAT_AMPLITUDE` ±5°), weather (rain −2°, storm −3°, fog −1°) and open flame (`FIRE_HEAT` 60° within 8 units). Every creature carries `body_temp` (on the wire) that drifts toward the local ambient at `BODY_TEMP_DRIFT`; standing indoors replaces ambient with `indoor_ambient()`, where the house material insulates (`INSULATION_BY_MATERIAL`: straw 0.15 < wood 0.35 < stone 0.55) toward `HOUSE_COMFORT_TEMP` 18°, and larger floors shed heat faster (`HOUSE_REF_SIDE/size`). Extreme heat is always physics: past `HYPERTHERMIA_TEMP` 36° health drains with the excess (`HYPERTHERMIA_DRAIN`) until death by `hyperthermia`. Extreme cold feeds §R chill below `HYPOTHERMIA_TEMP` 2° when the weather-sickness law is on.

## Wind (§AQ PH-2)
The sky has a breath: a wind vector (`wind_angle`/`wind_speed`, on every snapshot payload) whose strength follows the weather — calm 0.25, rain 0.55, storm howls at 1.0 (`WIND_*_SPEED`, relaxed each tick) — and whose direction re-rolls near the season's prevailing bearing whenever the weather turns (`WIND_SEASON_BIAS`). Fire obeys it: both random ignition and plant-to-plant spread multiply by a tailwind factor (`WIND_FIRE_MULT` × speed × alignment), so flame races downwind while upwind groves stand longer.

## Nature's Law inheritance (§B)
Sex: polygons male, lines female (`entities.py:137`). Sons `sides = father.sides+1` capped at `max_sides` (24→Priest); daughters lines. Mutation `mutation_rate` ±1 side → `irregularity` 0.3–1.0. Isosceles triangles: `iso_angle+0.5°` per generation, `≥60°` promotes Soldier→Artisan. Fertility: per-caste table × crowding `carrying_capacity`/`max_population`.

## Irregularity & caste (§C)
Mutated children's `irregularity` judged at `adult_age`: `≥euthanasia_threshold` → consumed (`euthanasia`), else demoted to Soldier. `CASTE_TRAITS` (`entities.py:39`) gives lifespan/speed/sight_mult/fertility.

## Disease (§D)
`disease_enabled`, `disease_outbreak_rate` starts new `disease_id`, spreads within `disease_radius` at `disease_rate` (winter ×1.5), drains `disease_energy_drain` + health `2×disease_lethality`, recovers `recovery_rate`. Disabling freezes instantly.

## Environment (§E)
Clock from tick: `time_of_day` (`day_length` cycle, starts sunrise), `day`, `season` (`season_length`). Night `night_sight_mult`, fog `fog_sight_mult` stack. `SEASON_FOOD_MULT` spring 1.0/summer 1.2/autumn 1.0/winter 0.5; spring ×1.25 birth, winter ×1.5 disease. Weather FSM clear/rain/fog/storm at `weather_change_rate`: rain/storm `rain_speed_mult`, storm `storm_wander_bonus`.

## Clans & social order (§C/I/P/V)
Settlements seed clans (§V): every non-ruin house founds a clan led by the founding creature nearest its centre, and every founding creature joins its nearest house's clan — soldiers, women, nobles and priests mix inside one settlement (`simulation.py` `_found_founding_clans`, deterministic given the seed). God law `max_clans` caps society granularity: `-1` = one clan per house; `N ≥ 1` clusters the founders into N spatial clans (greedy k-centre) instead — a pinned value applies at world creation. A clan's settlement IS its anchor house: claims match the clustering (`_assign_house_claims`/`_claim_house_for_clan` pick the free house nearest a clan's people, never round-robin), and territory/totem/crest anchor there. Children inherit mother's `clan_id`; orphans found new clans that settle at the nearest free house (or build one, §L). Procedural name (`CLAN_ADJECTIVES/NOUNS`) + Sacred Avatar of the Sphere (§AP: ⭕ Radiant Circle, ⚡ Celestial Strike, 👁️ All-Seeing Vertex, 🛡️ Indomitable Monolith, 🌿 Sacred Spiral, ⚖️ Cosmic Scales, 🌀 Dimensional Rift, 🕯️ Eternal Hearth — emoji on the map) if `totems_enabled` (`config.py:59`, `simulation.py` `AVATARS`/`TOTEM_BUFF`, `renderCore.tsx` pole + shrine). Clan crest color on snapshot, totem pole + glowing shrine beside the main house, `StateMessage.clans` carries `name`/`totem`/`faith`/`shrine_level`/`leader_id`/`color`. Clan stats & history (§P): `GET /api/clans` (`main.py:363`) roster with `leader_id`/`population`/`house`/`war_wins`/`losses`/`territory_radius`, polled by `ClanPanel.tsx` under trophic chart. Relations −100..+100 drift `relation_drift_rate` →0, threshold `alliance_threshold`/`rivalry_threshold` → `alliance`/`rivalry` events; shared feeding within `flock_radius` `+2`. Boids `cohesion_weight`/`alignment_weight`/`separation_weight` blended after food-seeking; social yielding `YIELD_RADIUS` 2.5. Territory (§P): each settlement anchors a `territory_radius` 14 circle (`config.py:49`, `simulation.py:793` `_update_territory`, `CanvasRenderer.tsx:514`) — members steer home when outside (`0.35×steer`), trespass inside a rival's circle sours relations `trespass_decay` (`protocol.py:127`) via `_bump_relation`. Totem buffs (§AP): eight Sacred Avatars with divine aspects — ⭕ `Radiant Circle` +30% harvest/+20% fertility, ⚡ `Celestial Strike` +25% warrior damage, 👁️ `All-Seeing Vertex` +40% sight + nocturnal clarity, 🛡️ `Indomitable Monolith` −30% damage/cold immunity, 🌿 `Sacred Spiral` herbs ×2/plague recovery/composting, ⚖️ `Cosmic Scales` reliable peace/refuses kin-eating, 🌀 `Dimensional Rift` faster promotion/adaptive mutation/elder lore, 🕯️ `Eternal Hearth` nocturnal calm. Theology (§AP): settled clans consecrate a shrine beside the main house (`_update_faith`); the devout tithe `tithe_rate` at dawn & dusk into the clan faith pool; the aura mends the faithful; faith overflowing at a season turn works a `miracle` (bloom + mending); `temple_faith_cost` raises a Temple whose aura covers all territory (`temple` event); when God sets laws every shrine chimes and priests preach doctrinal `sermons` (`on_law_change` from `POST /api/laws`); same/complementary-avatar clans sympathise (+1 relation, holy alliances); crisis ages convene the Great `synod` (+relations, sacred truce); and rarely an elder priest receives the 3D `epiphany` — all strife stills (`truce_ticks`). Leadership (§P): founder is `leader_id` (`simulation.py:323`), death triggers succession to oldest living member → `succession` event (`protocol.py:129`, `simulation.py:1225`) if `succession_enabled` (`config.py:54`).

## Food economy (§H/N/O)
`Food` is a living plant `growth` 0.15→1.0 (`plant_growth_rate`), spreads `plant_spread_rate` within `SPREAD_RADIUS` 6.0 if below seasonal bounty `food_count×SEASON_FOOD_MULT`. Winter die-back removes youngest first. A meal whose straight path is blocked by a rock circle or a house wall is abandoned for `food_giveup_ticks` — the hungry give up and seek food somewhere else instead of grinding against the obstacle until they starve; eating anything clears the grudge, 0 disables giving up (`_segment_hits_circle`, `_give_up_on`). Death leaves `Corpse` (`corpse_ttl`, `corpse_energy`) edible like food; decay boosts nearby plants `NUTRIENT_BOOST×nutrient_cycle_rate` within `NUTRIENT_RADIUS`. §O biodiversity: `Food.variant` grass/berry/mushroom/poisonous (`entities.py:169`) — `plant_variants_enabled`/`poison_rate` (`config.py:44`), `VARIANT_ENERGY` grass 32/berry 48/mushroom 24/poison 8 and `VARIANT_HEALTH` berry +1/poison -30 (`simulation.py:49`), growth `VARIANT_GROWTH_MULT`×`VARIANT_SEASON_MULT` (`simulation.py:754`), spawn picks berry burst in autumn / mushroom on corpses/rocks (`simulation.py:530`), `poisonous` mutates via `poison_rate`; `bloom` carries `variant` (`simulation.py:782`). Wild herbivores (§O): `Herbivore` clanless grazers (`entities.py:40`, `is_herbivore`) spawn `area×density×beast_ratio` (`config.py:46`, `simulation.py:289`), graze plants and are hunted by predators (plants → herbivores → predators); `beast_ratio`/`diet_strictness` GodLaws (`protocol.py:123`). Diet & preference (§O): `diet_strictness` (`config.py:46`) filters perceived meals (`simulation.py:1304`) — herbivore ignores `corpse` when strict, predator ignores `food`, higher castes skip low-energy `grass` when strict (`berry` preferred), herbivore avoids `poisonous`; `test_synergies.py:test_diet_preference_respects_strictness` verifies.

## Communication & knowledge (§Q/X)
Signals (§Q): food calls and alarm calls ripple within `signal_radius`; clan-mates respond strongly, strangers weakly. Knowledge (§X): creatures learn typed facts from experience — `food` spots seen/eaten, `danger` at predator sightings, `safe` roofs while sheltered, `enemy` clans that struck them (`Creature.facts`, decay after `knowledge_ttl`). Teaching: `knowledge_share_rate` chance/tick to broadcast the freshest fact to clan-mates; heard facts land at half confidence — retold knowledge is vaguer than firsthand sighting, only better news overwrites. Mobbing: an attacked creature emits a help call; clan-mates within `help_radius` converge on the attacker (warriors first via caste rank, the peaceful lag behind, high castes only when bold), and every defender inside earshot softens the attacker's blows by `defense_weight`. Clan memory: `/api/clans` surfaces each clan's remembered enemies/danger zones/food spots (`clan_knowledge()`), and clans that remember each other as enemies plot wars faster (§S foreshadowing). Full history (§AT-1): `GET /api/clans/{id}/history?page=&size=` paginates the clan's entire filtered event stream (newest first, `total`/`has_more`) alongside the internal milestone log; the durable chronicle filters by clan at the SQL level — `GET /api/history?clan_id=N` matches any clan-bearing payload key (`a`/`b`/`clan_id`/conquest/schism/takeover pairs) so events stay queryable after rolling off the in-memory deque; ClanDetails renders a lazy "Full History" panel with `load older`. Senses interact (§AR S-0): sleeping bodies are fully deaf — a sleeper never processes signals and never counts as a mob defender (`_mob_defenders` skips the asleep), so predators may stalk a silent village. Ripe plants smell through the dark: a hungry or starving creature with no visual target catches the scent of any mature plant (`growth 1.0`) within `FOOD_SCENT_RADIUS` 8.0 at night — blind starvation is cured by the nose. And starvation dulls fear: `_effective_fear_radius` halves `fear_radius` for the starving (traits paranoid +4 / bold −2.5 still apply first), so the desperate walk toward death chasing scented food.

## Politics (§AB)
Coalitions: a leader folds friendly unaligned clans (relation ≥ `coalition_threshold`) into a named bloc (`coalition_formed`/`coalition_joined`); soured or shrunken blocs dissolve (`coalition_dissolved`). Mutual defence — strike one member and every mate's relations with the attacker sour −12, dragging them into the war. Leader agency: leaders act on their heritable trait — bold declares war on a remembered enemy (§X), peaceful sues for peace when weakened (`peace` event), paranoid betrays an ally (`betrayal` event + treason: false enemy knowledge seeded into nearby third clans). Strong clans demand tribute: vassals pay from their larder every 240 ticks (`tribute` events). Resource sharing: each settlement keeps a larder capped by `larder_capacity` — well-fed members deposit surplus, starving members withdraw; full-bellied allies top up starving allies at `aid_rate`. Defection: unhappy members (starving or homeless) walk to the healthiest nearby banner, even a rival's (`defection` events). `/api/clans` exposes `coalition_id`, `larder`, `tribute_to`; ClanPanel shows 🤝 pact / 🛡️ vassal / 🏺 larder chips. The leader is leverage (§AS L-0): kin within `LEADER_AURA_RADIUS` 15 of the living leader gain +10% sight (`LEADER_SIGHT_BONUS`), −5% energy burn (`LEADER_DECAY_MULT`) and a calmer hand (fear radius −1); with no living leader the whole clan glooms — sight −10%, burn +5% (`LEADERLESS_DECAY_MULT`), food gain ×0.85 (`LEADERLESS_GAIN_MULT`), bylaws and task boards pause, war declarations stop, and members drift `cautious` at `LEADERLESS_CAUTIOUS_CHANCE`. The death itself shocks: every member instantly loses 10 energy (`LEADER_SHOCK_ENERGY`), panics for 20 ticks (+0.3 flee urge), the larder loses 20% to looting, and a grey grief ripple marks the spot.

## Desperation cannibalism (§AC)
Only the desperate eat the living: below `cannibalism_hunger_ratio` energy a creature perceives eligible prey — enemy-clan members (negative relation) and the weak (starving, elder, wounded) of any clan; never predators, wild beasts, infants or indoor refugees. On contact within `eat_radius` the prey dies (cause `cannibalism`), the eater gains `cannibalism_energy` and leaves a partial corpse, and a cooldown separates kills. Kin-eating carries a terrible price (`eat_kin_enabled`): the kin-slayer is exiled (`exile_on_kin_eat`) to found a one-being outcast band, witnesses remember the band as an enemy (§X), and relations between former clan and band sink by `kin_stigma` — rivalry, plots, war.

## Food decay (§AE)
Nothing lasts forever: a mature plant lives `food_lifespan_ticks` × its variant's pace (mushroom 0.4×, grass ×1, berry 1.5×, poisonous 3×) before it withers — sprouts and growing plants never rot. Withered plants fade brown in the renderer, release half a corpse's nutrient boost to nearby plants (§H death feeds life), then vanish (`wither` events stay in-memory like blooms, never the DB). The bounty law respawns replacement growth, so plant counts now churn instead of freezing.

## Shelter & Settlements (§L/N)
Houses (`entities.py:184`) squares with doorway; walls block except door — doorway too small for Carnivore predators (§L refuge) so houses are safe havens. Exposure `exposure_drain` outdoors in rain/storm or night unless `indoors`. Beds scale with floor area: `house_capacity` counts beds in an average 8×8 hall (`HOUSE_REF_AREA`), small huts have fewer beds, and large houses are strictly capped at 16 beds max (`HOUSE_MAX_BEDS`). Clans can settle across multiple houses, with the leader residing in the primary **Main House** marked with a golden crown. Abandoned houses decay to ruins (`is_ruin`). One house, one clan (§AT-2/AT-3): a creature sleeps only under its own clan's roof or an unclaimed one — `_house_for()` never returns a foreign house, so rival bodies cannot poison occupancy caps. A growing clan with no free roof may **take over** a weak rival's spare house (non-main, nobody sleeping there tonight, rival population under half its bed count — `_try_house_takeover`): the invader claims it outright, relations sour −25 and a `takeover` event hits the chronicle with an expanding crest-ring flash on the map; conquest-by-war transfers houses too (winner repoints the loser's seat). An audit pass each settlement tick (`_audit_house_claims`) clears claims whose clan died so no house ends a tick owned by a ghost.


## Autonomous Evolution & Tools (§AG)
Evolution emerges 100% autonomously without god interventions:
- **Personality Archetypes**: `brave`, `cautious`, `altruistic`, `greedy`, `explorer`, `builder` (65% heritability). Altruistic creatures feed starving kin with basket food.
- **Dynamic Equipment & Tools**: Soldiers/Predators wield Spears (+20% combat damage & reach); Farmers/Artisans/Herbivores carry Baskets (haul up to 3 food units for field snacks or clan larder deposits); Priests carry Herb Poultices (+25 HP healing & infection cure); Chieftains wear the golden Crown.
- **Skill Mastery & Dynamic Titles**: 4 skills (Farming 🌾, Combat ⚔️, Foraging 🦴, Healing 🌿) progress from Novice to Master, unlocking titles (*the Slayer*, *the Fearless Champion*, *the Grand Harvester*, *the Wise Shaman*, *the Pathfinder*).
- **Oral Lore**: Elders sleeping in houses transmit their highest skill mastery XP to resting youth.
- **Floating Emote Thoughts**: Real-time mood balloons (`🍖`, `❤️`, `⚔️`, `🌿`, `🏆`, `💤`, `🧺`, `😱`) above creature heads.

## Energy Dynamics & Stage Metabolism (§AH)
- **Stage-Aware Metabolism**: Born infants burn 55% less energy per tick (`0.45x`), juveniles burn 25% less (`0.75x`), adults standard (`1.0x`), elders `0.85x`.
- **Combat Stamina**: Duels and war clashes expend energy (winner -6, loser -10); low energy (<20%) causes an exhaustion penalty (30% less damage).
- **Food Reserves & Field Eating**: Roaming creatures with <45 energy autonomously eat carried food from their basket. Full creatures (>85% energy) never eat or destroy food plants.

## Cognitive Agency & Clan Social Intelligence (§AL)
- **Multi-Objective Utility AI Engine**: Dynamic utility scoring evaluating survival energy, caste duty, personality weights, and kin emergency signals.
- **Mental Map & Purposeful Waypoints**: Coordinates for `home`, `rich_food`, `danger`, and `patrol` enable purposeful foraging and perimeter circuits over random Brownian noise.
- **Tactical Combat Formations**: Allied Soldiers in combat align into disciplined phalanxes; 1D lines (women) execute evasive tangential kiting; outnumbered creatures execute organized retreats to shelter.
- **Interpersonal Trust Matrix**: Pairs develop affinity from healing (+15) and feeding (+20), forming loyal buddy pairs for shared foraging.
- **Clan Division of Labor & Task Board**: Dynamic macro priorities (`balanced`, `food_security`, `defense`, `quarantine_healing`) boost harvester (2.0×) and guard (2.5×) action weights.
- **Governance Archetypes**: Distinct institutional succession models (`Monarchy` royal dynasty, `Theocracy` priest succession, `Junta` combat mastery, `Republic` council of elders).
- **Dynamic Bylaws**: Automated policies including winter food rationing (<35 energy threshold) and wartime martial law curfews.
- **Macro Geopolitics & Casus Belli**: Intentional war declarations based on famine food raids, blood feuds, and territorial friction with documented Casus Belli.
- **Inter-Clan Trade Caravans**: Economic specialization barter transferring surplus grain from agrarian clans to martial clans in exchange for combat training and diplomatic goodwill (+12 relations).
- **Tribal Traditions & Harvest Festivals**: Annual autumn celebrations at clan Main Houses boosting energy (+25), mood emotes, leader trust (+10), and oral lore transmission (+2.0 skill XP).



## Food & Botanical Ecology (§AM)
- **Crop Diversity & Botanical Variants**: 6 distinct flora species (`grass`, `grain`, `berry`, `medicinal_herb`, `mushroom`, `poisonous`).
- **Functional Nutrition**:
  - *Golden Grain*: Dense calorie staple (+45 Energy), slow decay rate ($2.5\times$ lifespan), foundational for settlement security.
  - *Sun Berry*: Energy burst (+48 Energy) and +15% movement speed surge.
  - *Medicinal Herb*: Healing remedy (+18 Energy, $+30\text{ HP}$), cures infections, grants heal emotes.

  - *Fungi / Mushroom*: Decomposer thriving near corpses, rocks, and during winter (+24 Energy).
- **Targeted Dietary Selection**: Injured and infected creatures actively seek medicinal herbs (0.2× effective distance weighting); starving creatures seek golden grain (0.4× distance weighting).

## Terminal User Interface (§AI)

A complete Textual terminal interface (`backend/tui/`) attaches to running worlds with:
- Camera follow mode (`w`) tracking moving creatures.
- Category-filtered Chronicle (`t`) (All, Birth, Death, War, Politics, Settlement).
- Full creature dossier inspector (`enter` / `i`) and clan details modal (`c`).
- God laws manager (`g`) and ASCII/half-block renderer (`a` / `f`).
"""


CODEBASE_MAP_MD = """
# Codebase map

## Backend (`backend/app/`)
- `config.py:13` — `Config` dataclass: world geometry, densities, food, corpses, behaviour, life, reproduction, disease, environment, shelter, terrain, society, houses, chronicle. `from_env()` + `tick_interval`.
- `entities.py:1` — `CasteTraits`, `CASTE_TRAITS`, `YIELD_RANK`, `caste_name()`, `Creature` (shape/sides/caste/age/lifespan/health/infected/clan_id/sleeping...), `Food` (growth), `Corpse`, `House` (size/door/clan).
- `world.py:32` — `World` registry + uniform spatial hash (`cell_size`, `rebuild_index`), `delta`/`distance` wrap-aware, `query_radius`.
- `simulation.py:57` — `Simulation` deterministic tick: `CLAN_COLORS`, `STAGE_MULT`, `SEASONS`, `SEASON_FOOD_MULT`, `YIELD_RADIUS`, `SPREAD_RADIUS` etc.
- `auth.py:1` — `require_god` FastAPI dependency for God passkey cryptographic verification (`X-God-Key`).
- `protocol.py:7` — Pydantic wire schemas: `ControlAction`, `ControlMessage`, `EntityState`, `StateMessage`, `HistoryEvent`, `HelloMessage`, `GodLaws`.
- `db.py:1` — `Database` stdlib `sqlite3` thin wrapper: `worlds`, `events`, `law_changes`, `creatures`, `snapshots`; WAL, thread-safe reentrant lock; §AD OS-log — RAM buffer + writer daemon (`log_event`/`log_birth`/`log_death`, `flush()` every 5s or 5000 ops, forced on world end/snapshot/close), reads may lag ≤5s.
- `main.py:1` — FastAPI `app`, `Hub` broadcast, `RuntimeState`, `tick_loop`, `apply_control`, `hello_payload`, `LAW_FIELDS`, `get_laws`/`apply_laws`, WebSocket `/ws`, REST routes, `/guide`.

## Frontend (`frontend/src/`)
- `App.tsx` — Main application layout, HUD, WebSocket synchronization, mobile drawer tabs.
- `render/CanvasRenderer.tsx` — High-performance 60 FPS batched HTML5 Canvas renderer with trigonometric vertex geometry.
- `render/ClanPanel.tsx` — Live clan settlements, totems, and war records.
- `render/ChronicleFeed.tsx` — Filterable, scrollable real-time event log.
- `render/PlotsPanel.tsx` — Multi-metric population, caste, and trophic sparklines.
- `clan/ClanDetails.tsx` — Clan profile, leader residence, founded day & casualty tracking.
- `history/WorldHistoryModal.tsx` — Daily chronicle digest, major wars, and AI Story export.
- `god/GodPanel.tsx` — Interactive Laws of Nature drawer with 7 curated presets.
- `god/auth.tsx` — God passkey modal dialog and authenticated fetch wrapper (`godFetch`).
- `inspect/Inspector.tsx` — Creature dossier, vitals, inventory & family tree.
- `wiki/Wiki.tsx` — In-app interactive wiki & API playground.
- `types.ts` — TypeScript definitions mirroring backend protocol schemas.
- `websocket.ts` — Auto-reconnecting WebSocket client.

## Data flow
`tick_loop` → `sim.step()` → `sim.snapshot()` → `HUB.broadcast` → `ws` → `CanvasRenderer` + `App` state. Client → `ControlMessage` → `apply_control` → `RT.config`/`RT.sim` → DB law_changes. Events → `DB.add_events` + genealogy.
"""

DATA_MODEL_MD = """
# Data model & protocol

## Entities (in-memory)
- `Creature` (`entities.py:95`): `id`, `x`, `y`, `angle`, `shape` polygon|line, `sides`, `caste`, `radius`, `age`, `lifespan`, `stage` infant|juvenile|adult|elder, `irregularity`, `health` 0–100, `infected`, `sex` male|female, `mother_id`/`father_id`, `clan_id`/`clan_color`, `sleeping`/`indoors`, `generation`, `born_tick`, `energy`, `status` hungry/starving, `meals`.
- `Food` (`entities.py:158`): `x`, `y`, `growth` 0–1.
- `Corpse` (`entities.py:170`): `x`, `y`, `ttl`, `energy`.
- `House` (`entities.py:184`): `x`, `y`, `size`, `door_width`/`door_side`/`door_offset`, `clan_id`/`clan_color` (settlement), `is_ruin`/`abandoned_ticks`, `takeover_tick` (last hostile takeover, §AT-3 render flash); ruin after `house_decay_ticks` (`config.py:113`), `settlement`/`ruin`/`takeover` events.
- Terrain: `fertile: [{x,y,r}]`, `rocks: [{x,y,r}]` in snapshot.

## Wire schemas (`protocol.py`)
- `EntityState` (`protocol.py:27`): `id`, `kind` creature|food|house|corpse, `x`/`y`/`angle`, plus optional fields above.
- `StateMessage` (`protocol.py:62`): `tick`, `seed`, `width`/`height`/`boundary`, `population`, `entities`, `creatures_alive`/`creatures_dead`/`dead_by_cause`, `infected_count`, `time_of_day`/`day`/`season`/`weather`, `terrain_fertile`/`terrain_rocks`, `relations`, `events`.
- `HistoryEvent` (`protocol.py:86`): `type` death|birth|promotion|demotion|outbreak|recovery|bloom|alliance|rivalry|predation|war|ruin|settlement, `tick`, `entity_id`, `caste`, `cause`, `x`/`y`, `payload` (parents/sides/generation/clan_id etc).
- `HelloMessage` (`protocol.py:99`): `seed`, `tick_rate`, `width`/`height`/`boundary`.
- `ControlMessage` (`protocol.py:22`): `action` pause|resume|step|reset|set_speed + `value`.

## WebSocket flow
Server → client: `{"type":"hello", ...}` then `{"type":"state", ...}` each tick. Client → server: `{"action":"pause"|"resume"|"step"|"reset"|"set_speed", "value":...}` (`main.py:270`).
"""

CONFIG_OPS_MD = """
# Configuration & ops

## Env vars (`FLATWORLD_*`)
| Variable | Default | Description |
|---|---|---|
| `FLATWORLD_WIDTH` | `400` | World width (grid units) |
| `FLATWORLD_HEIGHT` | `300` | World height |
| `FLATWORLD_BOUNDARY` | `wrap` | `wrap` or `clamp` |
| `FLATWORLD_SEED` | `42` | RNG seed |
| `FLATWORLD_TICK_RATE` | `10` | Ticks per second |
| `FLATWORLD_DB` | `backend/flatworld.db` | SQLite path |
| `FLATWORLD_GOD_KEY` | — | Seed/override the god passkey at boot |

## God passkey (auth)

`POST /api/laws`, `POST /api/presets/{{name}}`, `POST /api/control` and
WebSocket control messages need the god passkey (`X-God-Key` header, `key`
field on the socket). No credential yet → any god call answers `409` and the
web UI asks to create one (`POST /api/auth/setup`). Lost it? Recover on the
server only: `cd backend && uv run python -m app.godkey reset <new>` (or
`clear`). The TUI takes no prompt: `./run.sh tui ws://host/ws <passkey>` or
export `FLATWORLD_GOD_KEY`. Only a PBKDF2 hash is stored.

## Persistence (`db.py:20`)
SQLite `flatworld.db` (WAL, thread lock). Tables:
- `worlds(id, seed, width, height, boundary, started_at, ended_at)`
- `events(id, world_id, tick, type, entity_id, caste, cause, x, y, payload, created_at)`
- `law_changes(id, world_id, tick, name, value, created_at)`
- `creatures(id, world_id, entity_id, caste, clan_id, generation, mother_id, father_id, born_tick, died_tick)`
- `snapshots(id, world_id, tick, payload, created_at)`

History survives restarts; `reset` closes old world row and opens new.

## Concurrency stance

The simulation is **single-threaded by design** — determinism is the product:
one seeded RNG stream, one fixed tick order. Run uvicorn with **1 worker**
(more workers = several disconnected worlds, not a faster one). The engine
thread advances ticks while the asyncio loop serves HTTP/WS; shared state
crosses threads strictly under `RT.lock`. Multi-core simulation is a non-goal
(CPython's GIL makes thread parallelism a wash for pure-Python compute);
performance work is algorithmic instead: spatial-hash neighbour queries for
war/mobbing/relations, per-tick clan caches, plain-dict snapshots with cached
identity (no pydantic validation per frame), `orjson` broadcast encoding and
one SQLite commit per tick (`Database.batch()`).

## Run & deploy
```bash
./run.sh
# or
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

## Tests
```bash
cd backend && uv run pytest -q
cd backend && uv run pytest tests/test_synergies.py -q
```
"""

GUIDE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flatland — Living Guide — World Simulation by Long Phan (long@minhnhan.in)</title>
<meta name="description" content="Official living architecture guide and technical reference for Flatland: 2D autonomous World Simulation by Long Phan (long@minhnhan.in).">
<meta name="keywords" content="Flatland, World Simulation, Architecture, Guide, API, God Laws, Long Phan, long@minhnhan.in, Artificial Life">
<meta name="author" content="Long Phan <long@minhnhan.in>">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://world.minhnhan.in/guide">
<meta property="og:title" content="Flatland — Living Guide | World Simulation by Long Phan">
<meta property="og:description" content="Official living guide and architecture documentation for Flatland World Simulation by Long Phan (long@minhnhan.in).">
<meta property="og:url" content="https://world.minhnhan.in/guide">
<meta property="og:type" content="article">
<style>
:root{{color-scheme:dark;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
*{{box-sizing:border-box}}
body{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;margin:0;color:#c9d1d9;background:#0b0f14;line-height:1.6}}
nav{{position:fixed;top:0;left:0;width:260px;height:100vh;overflow-y:auto;background:#0d1117;border-right:1px solid #21262d;padding:16px;scrollbar-width:thin}}
main{{margin-left:260px;padding:24px;max-width:960px;background:#0b0f14}}
a{{color:#58a6ff;text-decoration:none}} a:hover{{text-decoration:underline}}
pre{{background:#161b22;padding:12px;overflow:auto;border-radius:6px;border:1px solid #30363d;font-size:13px;color:#e6edf3}}
code{{background:#161b22;padding:2px 5px;border-radius:4px;font-size:0.9em;border:1px solid #21262d;color:#ffa657}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:12px;display:block;overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid #30363d;border-radius:6px}}
th,td{{border:1px solid #21262d;padding:8px 10px;text-align:left;white-space:nowrap}}
th{{background:#161b22;color:#e6edf3;font-weight:600;border-bottom:1px solid #30363d}}
td{{background:#0d1117}}
tr:hover td{{background:#161b22}}
h1{{border-bottom:1px solid #21262d;padding-bottom:8px;color:#e6edf3;font-size:20px;letter-spacing:0.04em}}
h2{{margin-top:28px;color:#e6edf3;font-size:16px;border-left:3px solid #e3b341;padding-left:8px}}
h3{{color:#e6edf3;font-size:14px}}
ul{{padding-left:20px}}
li{{margin:4px 0}}
@media(max-width:768px){{
  nav{{position:relative;width:auto;height:auto;border-right:none;border-bottom:1px solid #21262d}}
  main{{margin-left:0;padding:16px}}
  footer{{margin-left:0 !important}}
  table{{font-size:11px}}
}}
</style></head><body>
<nav><h3 style="margin:0 0 12px;color:#e6edf3">📖 Flatland Guide</h3><ul style="list-style:none;padding:0;margin:8px 0">{nav}</ul><p style="font-size:13px"><a href="/docs">Swagger /docs</a> · <a href="/openapi.json">OpenAPI</a> · <a href="/wiki">Wiki</a></p><p style="font-size:13px"><a href="/guide?format=json">JSON</a> · <a href="/">← Live world</a></p><p style="font-size:12px;color:#8b949e;margin-top:16px;border-top:1px solid #21262d;padding-top:12px">Developed by<br/><strong style="color:#e6edf3">Long Phan</strong><br/><a href="mailto:long@minhnhan.in">long@minhnhan.in</a><br/><a href="https://minhnhan.in">minhnhan.in</a><br/><small style="color:#8b949e;display:block;margin-top:4px">Built with OpenCode & Antigravity<br/>Inspired by Edwin A. Abbott</small></p></nav>
<main>{content}</main><footer style="margin-left:260px;padding:16px 24px;font-size:12px;color:#8b949e;border-top:1px solid #21262d;background:#0d1117;text-align:center">© Flatland — Developed by <strong style="color:#e6edf3">Long Phan</strong> &lt;<a href="mailto:long@minhnhan.in">long@minhnhan.in</a>&gt; · <a href="https://minhnhan.in">minhnhan.in</a> · <a href="https://world.minhnhan.in">world.minhnhan.in</a> · Built with OpenCode & Antigravity · Inspired by Edwin A. Abbott</footer></body></html>
"""


def build_guide_html(app: Any) -> str:
    """Assemble full guide HTML with nav + all sections + auto tables."""
    api_html = _md_to_html("# API reference\n\nAuto-generated from live OpenAPI (`/openapi.json`).") + _api_table(app) + _md_to_html("\nInteractive docs at [/docs](/docs).\n")
    laws_html = _md_to_html("# Laws of the Sphere\n\nEvery law in `GodLaws` (`protocol.py:108`) with type/range/default. The Sphere sets via `POST /api/laws`.") + _god_laws_table()
    sections = [
        ("how-the-world-works", "How the world works", _md_to_html(HOW_IT_WORKS_MD)),
        ("codebase-map", "Codebase map", _md_to_html(CODEBASE_MAP_MD)),
        ("data-model-protocol", "Data model & protocol", _md_to_html(DATA_MODEL_MD)),
        ("laws-of-the-sphere", "Laws of the Sphere", laws_html),
        ("api-reference", "API reference", api_html),
        ("configuration-ops", "Configuration & ops", _md_to_html(CONFIG_OPS_MD)),
    ]

    nav_items = []
    content_parts = []
    for slug, title, html_body in sections:
        nav_items.append(f'<li><a href="#{slug}">{html.escape(title)}</a></li>')
        content_parts.append(f'<section id="{slug}">{html_body}</section>')

    # Add roadmap linking back to TODO.md
    roadmap_md = f"# Roadmap\n\nSee [TODO.md](../TODO.md) for full task list. This guide is auto-generated; `#{len(sections)}` sections + `{len(GodLaws.model_fields)}` laws + `{len(app.routes)}` routes."
    content_parts.append(f'<section id="roadmap">{_md_to_html(roadmap_md)}</section>')
    nav_items.append('<li><a href="#roadmap">Roadmap</a></li>')

    nav_html = "\n".join(nav_items)
    content_html = "\n<hr/>\n".join(content_parts)
    return GUIDE_TEMPLATE.format(nav=nav_html, content=content_html)

