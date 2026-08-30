"""Deterministic fixed-tick simulation of Flatland."""

import gc
import math
import operator
import random
import time
from collections import deque
from functools import lru_cache
from typing import Any, Callable, cast

# N150: disable automatic GC during tick — manual collect every 200 ticks
# to avoid 1s stop-the-world pauses at 1300c
gc.disable()

from .config import Config
from .entities import (
    DEFAULT_RADIUS,
    PRIEST_SIDES,
    YIELD_RANK,
    Corpse,
    Creature,
    Entity,
    Food,
    House,
    RADIUS_BY_CASTE,
    caste_name,
    traits_for,
)
from .protocol import EntityState, HistoryEvent, StateMessage
from .world import World, segments_intersect

# AY: native hot-path & parallel domain decomposition (optional, deterministic fallback)
try:
    from . import native_core as _native_core  # type: ignore
except Exception:
    _native_core = None  # type: ignore
try:
    from . import parallel as _parallel  # type: ignore
except Exception:
    _parallel = None  # type: ignore

# BA: micro-neural engine (optional, gated by nn_enabled)
try:
    from . import agent_soa as _agent_soa  # type: ignore
    from . import neural_engine as _neural_engine  # type: ignore
    from . import agent_pipeline as _agent_pipeline  # type: ignore
    from . import spatial_grid as _spatial_grid  # type: ignore
    from . import evolution as _evolution  # type: ignore
except Exception:  # pragma: no cover
    _agent_soa = None  # type: ignore
    _neural_engine = None  # type: ignore
    _agent_pipeline = None  # type: ignore
    _spatial_grid = None  # type: ignore
    _evolution = None  # type: ignore


# Life-stage multipliers (speed, sight) — the young are small and dim-sighted,
# the elders slow. Fertility multiplier lives on Creature.FERTILITY_MULT.
STAGE_MULT = {
    "infant": (0.60, 0.60),
    "juvenile": (0.85, 0.85),
    "adult": (1.00, 1.00),
    "elder": (0.85, 0.90),
}

SEASONS = ("spring", "summer", "autumn", "winter")
# Winter starves the land; summer is plenty. Winter mult is now a god law (winter_food_mult).
SEASON_FOOD_MULT = {"spring": 1.0, "summer": 1.2, "autumn": 1.0, "winter": 0.5}
SPRING_BIRTH_MULT = 1.25
WINTER_DISEASE_MULT = 1.5

def _season_food_mult(season: str, winter_mult: float) -> float:
    if season == "winter":
        return winter_mult
    return SEASON_FOOD_MULT.get(season, 1.0)
WEATHER_STATES = ("clear", "rain", "fog", "storm")
AGES = ("Golden", "Ice", "Chaos", "Plague")
AGE_FOOD_MULT = {"Golden": 1.25, "Ice": 0.55, "Chaos": 0.95, "Plague": 0.9}
AGE_MUTATION_MULT = {"Golden": 0.9, "Ice": 1.1, "Chaos": 1.8, "Plague": 1.0}
AGE_DISEASE_MULT = {"Golden": 0.8, "Ice": 1.1, "Chaos": 1.0, "Plague": 1.8}
AGE_BIRTH_MULT = {"Golden": 1.3, "Ice": 0.85, "Chaos": 1.0, "Plague": 0.9}
AGE_CAP_MULT = {"Golden": 1.25, "Chaos": 0.95, "Plague": 0.75, "Ice": 0.55}

YIELD_RADIUS = 2.5  # lower castes step aside within this range

# §L shelter: reference floor area for the house_capacity law (8×8 hall) and maximum bed limit
HOUSE_REF_AREA = 64.0
HOUSE_MAX_BEDS = 16


# §AB politics pacing (per-tick chances; determinism via fixed iteration order)
COALITION_FORM_CHANCE = 0.003  # a leader founds a bloc this often
COALITION_JOIN_CHANCE = 0.01  # an unaligned clan petitions an existing bloc
LEADER_DECISION_CHANCE = 0.01  # a leader acts (war/peace/betrayal/tribute)
TRIBUTE_INTERVAL = 240  # ticks between vassal payments
DEFECT_CHANCE = 0.03  # unhappy member defects per tick
TREASON_RADIUS = 14.0  # false-knowledge seeding reach during betrayal
WAR_DECLARE_COOLDOWN = 1200  # one active feud per pair; no re-declaring inside this window

# §AC desperation cannibalism pacing
CANNIBAL_COOLDOWN = 120  # ticks between desperate kills
CANNIBAL_CORPSE_MULT = 0.5  # the body left after a cannibal feeds

# §AP Unified Theology — shrines beside the main house, dawn & dusk tithes,
# seasonal miracles, law resonance, holy synods and the rare 3D epiphany.
SHRINE_AURA_RADIUS = 10.0   # blessing aura around a level-1 shrine
TEMPLE_AURA_MULT = 3.0      # a temple extends the blessing across territory
TITHE_WINDOW = 0.02         # fraction of a day on either side of sunrise/sunset
BLESS_HEAL_RATE = 0.15      # health/tick the shrine's aura mends (costs faith)
BLESS_FAITH_COST = 0.02     # faith spent per mended member per tick
MIRACLE_FAITH_COST = 150.0  # faith burned per seasonal miracle
MIRACLE_FOOD = 6            # plants gifted by one miracle
SYNOD_INTERVAL = 3600       # crisis-age cadence for the Great Synod
SYNOD_RELATION_BOOST = 4    # every pair warms this much at a synod
EPIPHANY_PERIODS_GAP = 997  # hash modulus: an epiphany is a once-in-ages event
TRUCE_TICKS = 600           # synods and epiphanies still all strife this long

# §AT-4 H-0 — health is a real resource: regeneration demands a fed body,
# weakness slows every stride, and sickly creatures cannot beget children.
HEALTH_REGEN_MIN_ENERGY = 0.4  # fraction of energy_max: regen stalls below this
HEALTH_SELF_DRAIN_ENERGY = 0.2  # below this fraction the body cannibalizes itself
HEALTH_SELF_DRAIN_RATE = 0.05  # health lost per tick while self-cannibalizing
HEALTH_SPEED_TIERS = ((80.0, 0.95), (60.0, 0.85), (40.0, 0.70), (20.0, 0.50))
REPRO_MIN_HEALTH = 50.0  # sickly creatures cannot mate

# §AT-4 H-1 — damage variety: hunger gnaws, age withers, wounds linger, and
# what a body eats decides how well it mends.
EXHAUSTION_ENERGY_FRACTION = 0.20  # chronic-hunger floor
EXHAUSTION_TICKS = 30              # below the floor this long → health drain
EXHAUSTION_DRAIN = 0.08
ELDER_DECAY_RATE = 0.02            # passive health decay in old age
HEALTH_SIGHT_TIERS = ((30.0, 0.75), (60.0, 0.90))  # ascending threshold check
COMBAT_MIN_HEALTH = 30.0           # cannot initiate combat below this
FORAGE_MULT_HURT = 0.80            # harvest mult at health <60
FORAGE_MULT_WEAK = 0.50            # harvest mult at health <30
FOOD_HEAL_BONUS = {                # variant -> (+health/tick, for N ticks)
    "berry": (0.3, 20),
    "grain": (0.2, 30),
    "medicinal_herb": (0.8, 40),
}
REGEN_OUTDOOR_MULT = 0.5   # waking regen in the open
REGEN_INDOOR_MULT = 0.8    # sheltered but awake
WOUND_MIN_DAMAGE = 15.0    # hits above this leave a lingering wound
WOUND_TICKS_BASE = 50      # wounds linger 50–100 ticks
WOUND_SPEED_MULT = {1: 0.85, 2: 0.70}
WOUND_REGEN_DIV = {1: 2.0, 2: 4.0}

# §AT-4 H-2 — systems depth: untreated wounds fester, healthy kin dress them,
# morale bends behaviour long before the body fails, and scars outlive wounds.
WOUND_INFECTION_CHANCE = 0.02  # per-tick risk an untreated wound turns septic
WOUND_INFECTION_AFTER = 30     # ticks before an open wound can fester
DRESS_MIN_HEALTH = 70.0        # a helper must be healthy to dress wounds
DRESS_RADIUS = 3.0             # bandages are applied at arm's reach
MORALE_DEATH_WITNESS = 6.0     # morale lost watching a clan-mate die
MORALE_LEADER_DEATH = 15.0     # extra grief when the fallen one is the chief
MORALE_STARVE_DRAIN = 0.08     # prolonged starvation erodes the will
MORALE_BASE_RECOVER = 0.02     # hearts mend slowly on their own
MORALE_EAT_RESTORE = 12.0      # a meal lifts the spirit
MORALE_AURA_RECOVER = 0.05     # the leader's aura mends hearts slowly
MORALE_FEAST_RECOVER = 0.10    # festivals lift every heart in the clan
MORALE_RALLY_MIN = 60.0        # below this rally calls fall on deaf ears
MORALE_FORAGE_MIN = 40.0       # below this the body stops providing
MORALE_ABANDON = 20.0          # below this a body abandons its clan
MORALE_ABANDON_CHANCE = 0.02   # per-tick chance the broken walk away
OVERCROWD_DRAIN = 0.03         # health/tick per body beyond a house's beds
INFIRMARY_REGEN_MULT = 2.0     # plague-response bylaw doubles rest healing
SCAR_CHANCE = 0.5              # surviving a grievous wound may leave a mark
SCAR_SIGHT_MULT = 0.97         # permanent sight loss per scar
SCAR_SPEED_MULT = 0.98         # permanent stride loss per scar

# §AO — nocturnal perils: the Flatland night is an existential hazard, and
# shelter is the only sanctuary. Night is when the cold kills, the wolves
# prowl in packs, and the blind stumble onto a woman's sharp line.
NIGHT_CHILL_MULT = 3.0         # unsheltered night chill builds this much faster
EXTREME_NIGHT_EXPOSURE = 0.06  # extra energy/tick: winter nights & night storms
FROSTBITE_SPEED_MULT = 0.4     # numb limbs crawl (chill past the threshold)
FROSTBITE_DRAIN = 0.5          # HP/tick of deep frostbite; cause `exposure`
PREDATOR_NIGHT_SIGHT = 1.4     # +40% hunt radius in the dark
PREDATOR_NIGHT_SPEED = 1.2     # +20% stealth chase vs unsheltered prey
PACK_HOUR = 0.85               # past midnight beasts converge in packs
PACK_RADIUS = 18.0             # pack-mates share a kill within this range
DUSK_TOD = 0.70                # dusk rush: instinct screams "home" from here
DUSK_SHELTER_URGE = 1.6        # overrides exploration before nightfall
HEARTH_SANCTUARY_HEAL = 1.5    # HP/tick beside a lit hearth
SPEAR_POKE_RADIUS = 3.0        # sentries poke outward from the doorway
SPEAR_POKE_DAMAGE = 22.0       # damage per poke at circling night beasts
PITCH_BLACK_SIGHT = 2.5        # outdoor night sight for non-predators
IMPALE_CHANCE = 0.08           # per-tick blind-collision risk in pitch dark
IMPALE_DAMAGE = 25.0           # a woman's line cuts deep (death: impalement)
MARAUDER_CHANCE = 0.03         # per-tick ambush roll for a dark isosceles
MARAUDER_AMBUSH_RADIUS = 6.0   # strike range against lone foragers
CAMPFIRE_LIGHT_RADIUS = 3.5    # a field campfire's circle of safety
CAMPFIRE_TTL_TO_DAWN = True    # campfires burn until dawn, no refuelling
CAMPFIRE_HEAT = 14.0           # warmth target near the flames
CAMPFIRE_KINDLE_CHANCE = 0.10  # per-tick kindling chance for stranded explorers
BED_OVERFLOW_BUILD_THRESHOLD = 3  # denied beds last night → build pressure

# §AR S-0 — senses interact: ripe plants smell through the dark, and
# desperation dulls fear.
FOOD_SCENT_RADIUS = 8.0  # mature plants are detectable by smell within this range

# §AR S-1..S-7 — senses that interact and suppress each other.
ALARM_HABITUATION_TICKS = 10   # same source this long → u_alarm drops to 0.3
ALARM_HABITUATED_U = 0.3
WARCRY_RADIUS_MULT = 2.0       # a predator pack's cry carries twice as far
ELDER_SIGHT_PENALTY = 0.9      # §AR S-2: old eyes dim a little further
VISION_CONE_COS = 0.0          # ±90° forward cone (cos 90°)
REAR_SIGHT_MULT = 0.5          # the rear 180° sees half as far
TRIANGLE_FALSE_ALARM = 0.30    # §AR S-2 Flatland canon: isosceles misread
TORCH_LIGHT_RADIUS = 6.0       # a torch restores night sight around its bearer
CAMOUFLAGE_RANGE = 2.5         # mature cover hides prey this close to plants
CAMOUFLAGE_HUNT_MULT = 0.8     # ...cutting predator range by a fifth
ORAL_LORE_CONF = 0.3           # §AR S-3: inherited memory arrives vague
WORKING_MEMORY_CAP = 6         # simultaneous facts a mind holds
MEMORY_CAP_STRESSED = 4        # hunger and wounds shrink the world
MEMORY_CAP_ELDER = 8           # a life of experience widens it
PRIEST_ORACLE_INTERVAL = 120   # cadence of the priest's clan briefing
PANIC_CONTAGION = 0.2          # §AR S-5: one runner spooks the flock
PRIEST_CALM_BONUS = 0.2        # ...a priest steadies them
PRIEST_CALM_RADIUS = 4.0       # the priest's calming presence range
RALLY_SIGNAL_TTL = 20
THERMAL_SEEK_UTILITY = 0.35    # §AR S-6: drift toward warmth when freezing
WEATHER_ANTICIPATION_TICKS = 3 # pentagon+ read the sky this fast
DISEASE_SCENT_RADIUS = 4.0     # the sick smell of sickness

# §AM Food & Agriculture — seed & furrow, granary & soil, feast & famine raid.
SEED_SKILL_MIN = 6.0        # farming XP before hands gather/sow seed
TEND_SKILL_MIN = 6.0        # farming XP before a creature tends crops
FARM_PLOTS_PER_CLAN = 3     # tilled plots ring each settlement
CULTIVATED_GROWTH_MULT = 2.0   # sown crops grow this much faster than weeds
CULTIVATED_YIELD_MULT = 2.5    # ...and feed this much better
IRRIGATED_GROWTH_MULT = 1.15   # furrows keep the soil moist through drought
TEND_REGRESS_TICKS = 60     # weeding rolls back the wither clock this far
WINTER_FROST_CHANCE = 0.004 # frost bites exposed (un-cultivated) winter crops
GRANARY_DEPOSIT_SHARE = 0.35   # fraction of a sated grain/berry harvest stored
GRANARY_WITHDRAW_RATE = 3.0    # energy/tick a starving member draws from store
BANQUET_FILL_FRACTION = 0.8   # feast fires when the granary is this full
BANQUET_COST_FRACTION = 0.25  # of the granary consumed by one feast
BANQUET_MIN_GAP = 1200        # ticks between banquets
BANQUET_FEAST_TICKS = 600     # morale window after a feast
BANQUET_FERTILITY_MULT = 1.3  # birth-rate boost while the feast lasts
SOIL_CELL = 25.0              # grid units per soil-fertility cell
SOIL_MIN, SOIL_MAX = 0.3, 1.6
SOIL_DEPLETION_PER_GROWTH = 0.01  # fertility burned per point of growth grown
COMPOST_INTERVAL = 900        # ticks between a farmer's compost rounds
COMPOST_NUTRIENT = 0.4        # soil fertility granted per compost heap
RAID_GRANARY_MAX = 40.0       # most a war party can haul from a rival granary
HOSPITALITY_GAP = 180         # min ticks between sacred-hospitality chronicles

# §AN Communication, language & diplomacy — every caste has a voice.
CHANT_CHANCE = 0.02           # priest liturgy per tick when idle-voiced
HUM_CHANCE = 0.05             # woman's peace-hum while moving
WARCHIRP_CHANCE = 0.15        # soldier's rallying signal on contact
GREET_CHANCE = 0.35           # tactile greeting on close vertex contact
GREET_TRUST = 2.0             # trust gained by touching vertices in peace
ELDER_TOUCH_XP = 0.1          # skill XP passed by an elder's blessing touch
ARTISAN_GIFT_ENERGY = 25.0    # a barter chime's gift from the basket
SCENT_TTL = 220               # forager trail markers fade after this long
DANGER_SCENT_TTL = 300        # death/ruin scent lingers longer
TRAIL_DROP_CHANCE = 0.06      # well-fed finder of rich food leaves a marker
SIGNALS_MAX = 400             # hard cap on live ripples (bounds memory)
ENVOY_MISSION_TICKS = 1200    # an emissary abandons a failed mission after this
ENVOY_RELATION_BOOST = 15     # a delivered peace treaty warms relations this much
MARKET_CHECK_INTERVAL = 480   # allied neighbours found trading posts this often
MARKET_BARTER_INTERVAL = 240  # barter cadence at a standing market
CARAVAN_INTERVAL = 2400       # wandering peddlers set out this often
OMEN_SIGNAL_TTL = 90          # prophetic ripples linger over the shrine
PREPARED_TICKS = 400          # worshippers heed the omen this long
STONE_CHIME_GAP = 90          # min ticks between warning chimes per clan
DIALECT_STEP = 0.02           # per-season drift quantum for isolated clans

# §AS L-0 — the leader is a single point of leverage: an aura when present,
# a crisis when dead.
LEADER_AURA_RADIUS = 15.0
LEADER_SIGHT_BONUS = 0.10     # +10% perceive inside the aura
LEADER_DECAY_MULT = 0.95      # −5% energy burn inside the aura
LEADERLESS_DECAY_MULT = 1.05  # +5% energy burn with no living leader
LEADER_CALM = 1.0             # fear radius shaved inside the aura (braver kin)
LEADERLESS_FEAR = 1.0         # fear radius added when leaderless
LEADERLESS_GAIN_MULT = 0.85   # −15% food energy gain while leaderless
LEADER_SHOCK_ENERGY = 10.0    # instant loss at the leader's death
LEADER_SHOCK_LARDER_MULT = 0.8  # looting: larder loses 20%
LEADER_SHOCK_PANIC_TICKS = 20
LEADER_SHOCK_U_FLEE = 0.3    # flee-urge spike while the panic window lasts
LEADERLESS_CAUTIOUS_CHANCE = 0.01  # per-tick personality drift toward cautious

# §AS L-1..L-6 — the leader as commander, provider, diplomat and symbol.
LEADERLESS_WAR_MULT = 0.5     # an army without a general fights at half strength
BODYGUARD_U_HELP = 1.5        # soldiers hold their chief above all else
COMBAT_BOOST_TICKS = 30       # a rally sharpens blades this long
COMBAT_RALLY_BONUS = 0.3      # effective combat skill while rallied
ASSASSIN_ATTACK_BONUS = 0.2   # bold/junta blades aim for the throat
REGICIDE_RELATION_HIT = -60   # killing chiefs unprovoked: "they murder chiefs"
REGICIDE_SYMPATHY = 40        # ...and mourners rally to the victim's banner
TALK_RADIUS = 6.0             # peace needs two chiefs face to face
RETREAT_HEALTH_FRAC = 0.30    # a bleeding general sounds the retreat
RETREAT_SHELTER_URGE = 2.0    # kin drop everything and run home
RITUAL_INTERVAL = 120         # the chief's rite at the great hall
RITUAL_TOTEM_MULT = 2.0       # the totem answers with doubled power
RITUAL_TICKS = 30             # ...for this long after each rite
HARVEST_ORDER_SEASON = "autumn"  # the chief calls the stores in before winter
ABSENT_TOTEM_MULT = 0.5       # no chief at the hall: half-strength totem
REPUBLIC_PEACE_MULT = 1.2     # councils negotiate hardest
REPUBLIC_LARDER_EFF = 1.25    # ...and portion out stores fairest
MONARCHY_TRIBUTE_MULT = 2.0   # kingdoms extract double protection money
MONARCHY_AURA_MULT = 1.5      # the crown's aura reaches farther
MONARCHY_INBREEDING = 1.25    # thin royal blood mutates more easily
THEOCRACY_RITUAL_POWER = 2.0  # faith doubles every rite
JUNTA_COMBAT_SKILL = 1.5      # soldiers of the junta live for war
JUNTA_LARDER_EFF = 0.75       # ...but stores are portioned wastefully
JUNTA_ASSASSINATION_MULT = 2.0
CONTESTED_SUCCESSION_CHANCE = 0.15  # two equal heirs may split the clan
TOTEM_CHANGE_CHANCE = 0.10    # a new chief may call a new avatar
LAW_INTERPRET_TICKS = 20      # the chief explains God's law for this long

# §AQ PH-0 — foundational axioms: energy is the universal currency.
# Sunlight is the world's only income; every body pays upkeep in proportion
# to its geometric complexity (Flatland: more sides, more ceremony).
METABOLIC_COST = {
    "Woman": 1.5,
    "Soldier": 1.0,   # triangles
    "Artisan": 1.0,   # equilateral triangles
    "Gentleman": 1.1,  # squares
    "Professional": 1.2,  # pentagons
    "Noble": 1.3,     # hexagons and beyond
    "Priest": 1.5,    # near-circles burn energy maintaining the aura
    "Predator": 1.0,
    "Herbivore": 0.9,
}
DEFAULT_METABOLIC_COST = 1.0
HEALING_ENERGY_COST = 0.5  # energy burned per point of health regenerated

# §AQ PH-1 — thermodynamics: a coarse heat field over the land, bodies that
# drift toward it, and houses that keep the world outside at arm's length.
TEMP_CELL = 25.0          # grid units per temperature cell
TEMP_RATE = 0.08          # per-tick relaxation of a cell toward its target
SEASON_BASE_TEMP = {"spring": 12.0, "summer": 24.0, "autumn": 8.0, "winter": -4.0}
DAY_HEAT_AMPLITUDE = 5.0  # extra degrees at noon (negative in the deep night)
FIRE_HEAT = 60.0          # target temp near open flame
FIRE_HEAT_RADIUS = 8.0
BODY_TEMP_DRIFT = 0.06    # fraction of the gap closed per tick
HYPOTHERMIA_TEMP = 2.0    # below this the body builds chill (§R)
CHILL_FROM_COLD_RATE = 0.06
HYPERTHERMIA_TEMP = 36.0  # above this the body cooks
HYPERTHERMIA_DRAIN = 0.15  # health per degree of excess per tick

# §AQ PH-7 — metabolic extremes: a frozen, starving body shuts down to
# near-nothing; sustained cooking drops the body where it stands.
TORPOR_ENERGY_RATIO = 0.10  # energy fraction below which the cold can claim a body
TORPOR_BURN_MULT = 0.05     # torpid metabolism: 5% of the awake burn
HEAT_STROKE_TICKS = 60      # ticks of cooking before the body gives out
HEAT_STROKE_HYST = 4.0      # degrees of cooling before the body rises again

# §AQ PH-8 — seismic & wave physics: the ground sometimes moves, the tall
# castes feel it coming, and no news travels faster than the air carries it.
QUAKE_WARN_TICKS = 3        # high castes feel the deep hum this long ahead
QUAKE_WARN_RADIUS = 30.0    # ...within this range of the coming epicentre
QUAKE_DISPLACEMENT = 3.5    # max shove per body at the epicentre (mag 8)
QUAKE_DAMAGE = 16.0         # health lost at the epicentre, fading outward
QUAKE_ROCK_CRACK_CHANCE = 0.35  # a rock inside the blast may split open
QUAKE_ROCK_SPAWN_CHANCE = 0.15  # ...or the ground may thrust new stone up
# §AQ PH-9 — electrostatics & bio-electric fields
LIGHTNING_KILL_RADIUS = 1.6  # instant death under the strike
LIGHTNING_ROCK_TTL = 240     # a fused, electrostatic rock lingers briefly
LIGHTNING_BOLT_TTL = 6       # the visible bolt fades fast
PRIEST_CALM = 1.5            # fear-radius soothed near a living priest
PRIEST_AURA_RADIUS = 6.0
TOTEM_RESONANCE_BONUS = 0.25  # aura power per same-totem allied shrine nearby
TOTEM_RESONANCE_CAP = 2.0
TOTEM_RIVAL_DIM = 0.75       # rival shrines too close weaken both auras
TOTEM_RIVAL_RADIUS = 22.0
ANOMALY_TOTEM_BONUS = 1.25   # shrines beside an anomaly draw extra power
# §AQ PH-10 — cosmological & metaphysical
LAW_WAVE_TICKS = 30          # the law-change shimmer sweeps the map this long
LAW_WAVE_BAND = 4.0          # half-width of the felt wavefront
ANOMALY_RADIUS = 9.0         # a zone of altered physics
ANOMALY_DISCOVER_SKILL = 3.0  # foraging skill needed to notice one
ANOMALY_GROWTH_MULT = 1.6    # fertile anomaly
ANOMALY_HEAVY_SPEED = 0.7    # heavy anomaly drags the stride
ANOMALY_CALM_DECAY = 0.8     # calm anomaly eases the burn
SHADOW_LENGTH = 1.4          # a roof shadows the ground this far × size
SHADOW_GROWTH_MULT = 0.7     # shade-starved plants grow slower
SUN_EDGE_BAND = 18.0         # dawn/dusk illumination sweeps in from the edges
SUN_EDGE_GROWTH_MULT = 1.15
HOUSE_COMFORT_TEMP = 18.0  # what insulation pulls the indoors toward
# §AQ PH-6 — material physics: four build materials with distinct stats.
MATERIAL_STATS = {
    #            durability (structural HP)   insulation
    "straw": {"durability": 120.0, "insulation": 0.15},
    "wood":  {"durability": 260.0, "insulation": 0.35},
    "stone": {"durability": 480.0, "insulation": 0.55},
    "clay":  {"durability": 320.0, "insulation": 0.70},  # riverbank brick
}
INSULATION_BY_MATERIAL = {m: s["insulation"] for m, s in MATERIAL_STATS.items()}
HOUSE_REF_SIDE = 8.0      # a reference hall; bigger houses shed heat faster
STORM_WEAR = 0.15         # structural HP lost per storm tick
FLOOD_WEAR = 0.60         # structural HP lost per flood tick in the water
REPAIR_RATE = 1.5         # HP a builder restores per tick of masonry work
RUBBLE_RADIUS_FRAC = 0.35  # a collapsed ruin blocks this fraction of its floor

# §AQ PH-2 — the wind: a vector over the land that bends flame and seed.
WIND_CALM_SPEED = 0.25
WIND_RAIN_SPEED = 0.55
WIND_STORM_SPEED = 1.0    # magnitude scales with storm severity
WIND_RATE = 0.05          # relaxation toward the weather's target speed
# prevailing direction by season (radians); re-rolls land near these
WIND_SEASON_BIAS = {"spring": 0.0, "summer": 1.3, "autumn": 2.5, "winter": 4.0}
WIND_FIRE_MULT = 0.8      # extra spread chance per unit of tailwind speed
# §AQ PH-2: the wind carries more than flame — seeds and scent ride it too.
WIND_SEED_BIAS = 0.65     # how strongly seed drift bends downwind (× speed)
SOUND_WIND_MULT = 0.4     # calls carry this much farther to DOWNWIND listeners
# (scent kept gentle — a strong upwind nose destabilises predator/prey cycles)
WIND_SCENT_MULT = 0.35    # upwind reach bonus (prey full, predators half)

# §AQ PH-1 — hearths & radiant fire: warmth is infrastructure, and open
# flame is a double-edged tool (it warms the winter roof AND cooks the unwary).
HEARTH_COMFORT_TEMP = 26.0  # a lit hearth pulls the indoors toward this
HEARTH_PULL = 0.6           # strength of that pull (× size_factor)
HEARTH_FUEL_PER_ENERGY = 60.0  # ticks of burn bought per larder unit
HEARTH_FUEL_MAX = 1200.0    # the woodpile caps out here
HEARTH_BURN_RATE = 1.0      # fuel ticks consumed per tick while lit
HEARTH_REFUEL_INTERVAL = 10  # pacing: kin top up the hearth every N ticks
HEARTH_REFUEL_CHUNK = 0.25  # larder units per top-up
FIRE_SCALD_RADIUS = 4.0     # radiant scalding beyond the flame core
FIRE_SCALD_DAMAGE = 2.2     # health/tick at the flame's edge, fading to zero

# §AQ PH-5 — ecological physics: roots contest the soil, and plants help
# and hinder their neighbours (mushrooms fruit on decay, herbs shelter in
# berry thickets, toxins stunt everything near).
ROOT_COMPETITION = 0.45     # growth divisor per mature neighbour
SYMBIOSIS_RADIUS = 3.5      # root/reach range for neighbour effects
MUSHROOM_CORPSE_MULT = 1.6  # mushrooms fruit where things die
HERB_BERRY_MULT = 1.35      # medicinal herbs thrive beside berries
POISON_SUPPRESS = 0.55      # poisonous plants stunt their neighbours

# §AQ PH-3 — fluid dynamics: rivers are horizontal 1D channels across the map
# (the Planiverse constraint — water can only flow east or west). They cost
# energy to ford, sweep the weak downstream, flood in the rain and leave silt.
RIVER_BASE_HW = 4.0         # calm half-width of a channel band
RIVER_FORD_COST = 0.06      # extra energy/tick while wading
RIVER_SPEED_MULT = 0.6      # wading slows the body
RIVER_SWEEP_SPEED = 0.4     # displacement downstream/tick for the weak
RIVER_SWEEP_HEALTH = 30.0   # below this HP (or any infant) the current wins
RIVER_RAIN_RATE = 0.0035    # water level gained per tick of rain (storm ×1.5)
RIVER_DRY_RATE = 0.0012     # evaporation per tick
RIVER_FLOOD_TICKS = 300     # a flood lasts this long once triggered
RIVER_FLOOD_GROW = 0.05     # per-tick approach to the flooded half-width
RIVER_FLOOD_EBB = 0.02      # per-tick return to the calm channel
RIVER_FLOOD_HW_MULT = 2.2   # flooded half-width multiplier
RIVER_SILT_TICKS = 600      # post-flood enrichment window on the banks
RIVER_SILT_RADIUS = 6.0     # banks beyond the band that catch the silt
RIVER_SILT_MULT = 1.5       # plant growth bonus on fresh silt
RIVER_DROWN_DAMAGE = 1.5    # health/tick in floodwater; foraging skill softens
BRIDGE_HALF_WIDTH = 1.5     # a plank crosses dry within this x-range of its post
BRIDGE_HP = 2400            # ticks a plank bridge lasts without repair
DAM_HP = 3600               # ticks a dam holds before rotting
DAM_STRESS_DAMAGE = 30      # masonry lost per flood tick under pressure
DAM_FLASH_SPIKE = 1.8       # flash-flood half-width spike on dam failure

# §AQ PH-4 — gravity & terrain topology: a smooth height field bends every
# journey (uphill bleeds energy, downhill runs free), sharp drops are cliffs
# you can fall off, and feet pack the earth into roads that choke plant life.
ELEV_CELL = 25.0            # grid units per elevation sample
ELEV_MAX_HEIGHT = 60.0      # world-units between the lowest and highest ground
SLOPE_ENERGY_COST = 0.05    # extra energy/tick per unit of uphill grade
SLOPE_SPEED_MULT = 0.35     # speed lost at the steepest climb
CLIFF_DROP_UNITS = 18.0     # a terraced cell-boundary drop this steep is a cliff (raised from 14 to cut 22%->~8% edges)
FALL_DAMAGE_PER_UNIT = 0.85  # health lost per unit fallen past the threshold (tuned to keep 60-unit plateau lethal)
FALL_COOLDOWN_TICKS = 40     # grace after a fall — no further cliff damage while stunned
TRAFFIC_DECAY = 0.995       # per-tick fade of packed earth
TRAFFIC_DECAY_STAGGERED = TRAFFIC_DECAY ** 10  # §AU O-2: applied every 10th tick
TRAFFIC_PER_PASS = 1.0      # traffic earned per body-tick on a cell
ROAD_SPEED_PER_TRAFFIC = 0.03  # speed bonus per traffic level (packed earth)
ROAD_SPEED_CAP = 0.30       # ...capped here
TRAFFIC_PLANT_BLOCK = 6.0   # traffic above this halts plant growth entirely
AVALANCHE_SLOPE = 0.5       # grade that can slide in the rain
AVALANCHE_CHANCE = 0.002    # per creature per rainy tick on such a slope

# §AE food decay — nothing lasts forever: variant lifespan multipliers (§AM)
FOOD_LIFESPAN_MULT = {
    "grass": 1.0,
    "grain": 2.5,
    "berry": 1.5,
    "medicinal_herb": 1.2,
    "mushroom": 0.4,
    "poisonous": 3.0,
}
WILT_FRACTION = 0.8  # wilting (render fade) begins at this fraction of lifespan
WITHER_NUTRIENT_MULT = 0.5  # a withered plant fertilises at half a corpse's worth

# §H Plants & the nutrient cycle
SPREAD_RADIUS = 6.0  # mature plants seed new ground within this range
NUTRIENT_RADIUS = 10.0  # a fully decayed corpse fertilises plants within this range
NUTRIENT_BOOST = 0.5  # base growth granted by a decayed corpse (× nutrient_cycle_rate)
SPROUT_GROWTH = 0.15  # every newly spawned plant starts here

# §O Biodiversity — plant variants (§O, §AM)
VARIANT_ENERGY = {
    "grass": 32.0,
    "grain": 45.0,
    "berry": 48.0,
    "medicinal_herb": 18.0,
    "mushroom": 24.0,
    "poisonous": 8.0,
}
VARIANT_HEALTH = {
    "grass": 0.0,
    "grain": 2.0,
    "berry": 1.0,
    "medicinal_herb": 30.0,
    "mushroom": 0.0,
    "poisonous": -30.0,
}
VARIANT_GROWTH_MULT = {
    "grass": 1.0,
    "grain": 0.85,
    "berry": 0.65,
    "medicinal_herb": 0.70,
    "mushroom": 0.85,
    "poisonous": 0.60,
}
# seasonal rhythms: grain thrives summer/autumn, berry peaks autumn, herb thrives spring, mushrooms tolerate winter
VARIANT_SEASON_MULT = {
    "grass": {"spring": 1.05, "summer": 1.15, "autumn": 1.00, "winter": 0.45},
    "grain": {"spring": 0.90, "summer": 1.40, "autumn": 1.25, "winter": 0.15},
    "berry": {"spring": 0.50, "summer": 0.80, "autumn": 1.90, "winter": 0.25},
    "medicinal_herb": {"spring": 1.35, "summer": 1.10, "autumn": 0.65, "winter": 0.00},
    "mushroom": {"spring": 1.00, "summer": 0.60, "autumn": 1.35, "winter": 1.10},
    "poisonous": {"spring": 1.00, "summer": 1.00, "autumn": 1.00, "winter": 1.00},
}



# Creature Evolution: Personality Archetypes & Metabolism
PERSONALITIES = ("brave", "cautious", "altruistic", "greedy", "explorer", "builder")
STAGE_ENERGY_MULT = {"infant": 0.45, "juvenile": 0.75, "adult": 1.0, "elder": 0.85}

# Clan crest colors, assigned round-robin as clans are founded.
CLAN_COLORS = (
    "#ffd166", "#06d6a0", "#118ab2", "#ef476f",
    "#c77dff", "#f4a261", "#90be6d", "#e0aaff",
)

# Procedural clan names — seeded adjective + noun table (§P)
CLAN_ADJECTIVES = (
    "Ash", "Stone", "Long", "Silent", "Red", "Grey", "White", "Black", "Bright", "Cold",
    "Wild", "High", "Low", "Dawn", "Dusk", "River", "Mountain", "Forest", "Sun", "Moon",
    "Star", "Wind", "Iron", "Bronze", "Golden", "Silver", "Shadow", "Storm", "Fire", "Ice",
    "Ember", "Frost", "Thorn", "Hollow", "Grim", "Bold", "Swift", "Keen",
)
CLAN_NOUNS = (
    "Wolves", "Hawks", "Shadows", "Blades", "Stewards", "Wardens", "Keepers", "Hunters",
    "Striders", "Sentinels", "Weavers", "Masons", "Reavers", "Echoes", "Thorns", "Flames",
    "Stones", "Winds", "Tides", "Crowns", "Spears", "Shields", "Eyes", "Hands", "Voices",
    "Wings", "Fangs", "Roots", "Branches", "Stars", "Sands", "Waters", "Fires",
)

# §AP Phase A — totems are no longer animals: each clan bears one of the
# eight Sacred Avatars of the Sphere, a 2D projection of the One True God,
# and with it a distinct divine aspect (buff).
AVATARS = (
    "Radiant Circle",       # ⭕ God's Abundance
    "Celestial Strike",     # ⚡ God's Wrath & Justice
    "All-Seeing Vertex",    # 👁️ God's Omniscience
    "Indomitable Monolith", # 🛡️ God's Permanence
    "Sacred Spiral",        # 🌿 God's Renewal
    "Cosmic Scales",        # ⚖️ God's Equilibrium
    "Dimensional Rift",     # 🌀 God's Ascent
    "Eternal Hearth",       # 🕯️ God's Sanctuary
)
# Buff vocabulary (all optional keys, consumed generically via _totem_stat):
#   speed        additive speed multiplier when hunting/fleeing
#   hunt_radius  flat bonus to predator sight
#   harvest      fractional harvest bonus on plants (×1+h) and corpses (×1+0.4h)
#   sight        fractional perceive-radius bonus (×1+s)
#   defense      fractional damage reduction; sheltered healing scales ×(1+d)
#   health       flat health gift at birth
#   birth        fractional fertility bonus for the mother's clan
#   damage       fractional combat-damage bonus for the attacker (Strike)
#   clarity      fraction of the night-sight penalty recovered (Vertex)
#   cold         fraction of chill build resisted (Monolith cold immunity)
#   medicine     herb potency ×(1+m) (Spiral)
#   recovery     disease recovery chance ×(1+r) (Spiral)
#   compost      corpse nutrients near the shrine ×(1+c) (Spiral composting)
#   peace        leader sues for peace harder; war hand stays sheathed (Scales)
#   lawful       kin-eating is refused even while starving (Scales low crime)
#   promote      Isosceles angle rises faster per generation (Rift ascent)
#   mutate       child mutation chance ×(1+m) — adaptability (Rift)
#   lore         elder oral-lore XP transfer ×(1+l) (Rift elder lore)
#   calm         fear radius shaved at night (Hearth nocturnal calmness)
TOTEM_BUFF = {
    "Radiant Circle": {"harvest": 0.30, "birth": 0.20},
    "Celestial Strike": {"damage": 0.25, "speed": 0.06, "hunt_radius": 2.0},
    "All-Seeing Vertex": {"sight": 0.40, "clarity": 1.0},
    "Indomitable Monolith": {"defense": 0.30, "cold": 0.40, "health": 15.0},
    "Sacred Spiral": {"medicine": 1.0, "recovery": 1.0, "compost": 0.5},
    "Cosmic Scales": {"peace": 1.0, "lawful": 1.0},
    "Dimensional Rift": {"promote": 1.0, "mutate": 1.0, "lore": 1.0},
    "Eternal Hearth": {"calm": 1.5, "hearth": 1.0},
}
# Doctrinal kinship: complementary aspects sympathise (§AP holy alliances)
AVATAR_ALLIES = {
    "Radiant Circle": "Sacred Spiral",        # abundance ↔ renewal
    "Celestial Strike": "All-Seeing Vertex",  # wrath ↔ omniscience
    "Indomitable Monolith": "Eternal Hearth", # permanence ↔ sanctuary
    "Cosmic Scales": "Dimensional Rift",      # equilibrium ↔ ascent
}
# Sermon dogma — how each avatar interprets God's law changes (§AP Phase C)
AVATAR_DOGMA = {
    "Radiant Circle": "God's Abundance flows through the law you have set",
    "Celestial Strike": "God's Wrath strikes where the law now points",
    "All-Seeing Vertex": "the All-Seeing Vertex has watched this law take shape",
    "Indomitable Monolith": "God's Permanence sets this law in stone",
    "Sacred Spiral": "God's Renewal turns all things toward this law",
    "Cosmic Scales": "the Cosmic Scales weigh the world and find this law just",
    "Dimensional Rift": "through the Rift, God's Ascent carries us along this law",
    "Eternal Hearth": "the Eternal Hearth warms all who keep this law",
}
# Avatar biases the clan's starting specialization drift (§P specialization)
TOTEM_SPEC = {
    "Radiant Circle": {"warrior": 0.20, "farmer": 0.60, "scavenger": 0.20},
    "Celestial Strike": {"warrior": 0.55, "farmer": 0.20, "scavenger": 0.25},
    "All-Seeing Vertex": {"warrior": 0.25, "farmer": 0.25, "scavenger": 0.50},
    "Indomitable Monolith": {"warrior": 0.45, "farmer": 0.25, "scavenger": 0.30},
    "Sacred Spiral": {"warrior": 0.15, "farmer": 0.45, "scavenger": 0.40},
    "Cosmic Scales": {"warrior": 0.30, "farmer": 0.35, "scavenger": 0.35},
    "Dimensional Rift": {"warrior": 0.25, "farmer": 0.30, "scavenger": 0.45},
    "Eternal Hearth": {"warrior": 0.35, "farmer": 0.40, "scavenger": 0.25},
}

# §AM E.1 — geometric gastronomy: each caste keeps a table of its own.
# Priests and nobles demand refined grain and fruit; soldiers crave meat.
CASTE_DIET_WEIGHTS: dict[str, dict[str, float]] = {
    # variant -> effective-distance multiplier (lower = more desirable)
    "Priest": {"grain": 0.5, "berry": 0.5, "medicinal_herb": 0.5},
    "Noble": {"grain": 0.5, "berry": 0.6},
    "Soldier": {},       # soldiers favour meat — handled via corpse weighting
    "Artisan": {"grain": 0.8},
}

# Personal identity — seeded adjective+noun table (§Q), deterministic id+seed
PERSONAL_FIRSTS = (
    "Alen", "Bran", "Cora", "Dell", "Ember", "Finn", "Galen", "Hala", "Iris", "Joren",
    "Kira", "Lyss", "Maren", "Nora", "Orin", "Pella", "Quill", "Rhea", "Sable", "Taryn",
    "Uri", "Vessa", "Wren", "Xara", "Yara", "Zane", "Aric", "Brielle", "Cade", "Dara",
    "Eldric", "Fiora", "Gideon", "Hessa", "Ivor", "Jessa", "Kell", "Lina", "Mira", "Nessa",
)
PERSONAL_LASTS = (
    "Ash", "Stone", "Hollow", "Quill", "Grey", "Lark", "Vale", "Thorn", "Ember", "Wren",
    "Frost", "Dusk", "Star", "River", "Shadow", "Flame", "Wind", "Haven", "Moor", "Glen",
    "Ridge", "Brook", "Hearth", "Sable", "Wisp", "Bramble", "Harrow", "Tide", "Dell", "Echo",
)
GLYPH_TABLE = ("◈", "⬡", "⬢", "◉", "⬣", "⟡", "✦", "◆", "▲", "●", "✕", "∆", "◐", "◑", "⬔", "⬕", "⟐", "⧫")


def _clan_sig(info: dict) -> tuple:
    """Broadcast signature of a clan's wire-relevant state (AA delta tracking).

    Faith is bucketed: it drifts by fractions every tick (blessings, tithes),
    and an exact comparison would re-send the full clan dict each frame —
    a 25-point step is plenty for the shrine glow and clan panel.
    """
    return (
        info.get("name"), info.get("color"), info.get("totem"),
        info.get("culture"), info.get("leader_id"), info.get("main_house_id"),
        info.get("tribute_to"),
        round(float(info.get("faith", 0.0)) / 25.0), int(info.get("shrine_level", 0)),
        round(float(info.get("granary", 0.0)) / 25.0),  # §AM granary fill (bucketed)
        round(float(info.get("dialect", 0.0)) * 20.0) / 20.0,  # §AN dialect drift
    )


def personal_name_for(entity_id: int, seed: int, generation: int = 0) -> str:
    """Seeded deterministic personal name — god's ledger, never RNG."""
    a = PERSONAL_FIRSTS[(entity_id * 37 + seed) % len(PERSONAL_FIRSTS)]
    b = PERSONAL_LASTS[(entity_id * 73 + seed + generation * 101) % len(PERSONAL_LASTS)]
    return f"{a} {b}"


def glyph_for(entity_id: int, seed: int, generation: int = 0) -> str:
    return GLYPH_TABLE[(entity_id * 101 + seed + generation * 17) % len(GLYPH_TABLE)]


def variation_for(entity_id: int, seed: int) -> dict:
    """Subtle per-creature jitter — cosmetic only, never touches RNG."""
    hue = ((entity_id * 9973 + seed) % 241) / 241 * 24 - 12  # -12..+12 deg
    scale = 0.96 + ((entity_id * 7919 + seed) % 109) / 109 * 0.08  # 0.96..1.04
    angle = ((entity_id * 1307 + seed) % 31) / 31 * 0.12 - 0.06  # -0.06..+0.06 rad
    return {"hue_shift": round(hue, 2), "scale_jitter": round(scale, 3), "angle_jitter": round(angle, 3)}

TRAITS = ("greedy", "peaceful", "paranoid", "bold")
TRAIT_GLYPH = {"greedy": "⬔", "peaceful": "◯", "paranoid": "⬥", "bold": "▲"}
CULTURE_ADJECTIVES = ("Ashen", "Ember", "Hollow", "Stone", "River", "Sky", "Thorn", "Iron")
CULTURE_NOUNS = ("Rite", "Way", "Path", "Creed", "Tradition", "Lore", "Custody", "Bond")


class Simulation:
    def __init__(
        self,
        config: Config | None = None,
        history: deque[HistoryEvent] | None = None,
    ):
        self.config = config or Config()
        self.world = World(self.config)
        self.rng = random.Random(self.config.seed)
        self.tick = 0
        self.deaths = 0
        # Chronicle of the world; survives resets when handed back in.
        self.history: deque[HistoryEvent] = history or deque(maxlen=self.config.history_max)
        # Optional sink for durable storage (set by the app layer); must never
        # touch the rng — determinism is unaffected by observers.
        self.on_event: Callable[[HistoryEvent], None] | None = None
        self._eaten: set[int] = set()
        self._beds: dict[int, int] = {}  # house id -> occupants granted this tick
        self._events_this_tick: list[dict] = []  # pre-dumped dicts (populated by _emit)
        # T: per-tick caches
        self._cached_creatures: list[Creature] = []
        self._cached_creatures_sorted: list[Creature] = []  # sorted by id, built in _refresh_cache
        self._cached_foods: list = []    # Food entities this tick
        self._cached_houses: list = []   # non-ruin House entities this tick (sorted by id)
        self._cached_corpses: list = []  # Corpse entities this tick
        self._clan_members: dict[int, list[Creature]] = {}
        self._death_counts: dict[str, int] = {}
        # AA: deterministic cosmetic identity (name/glyph/jitter) per creature,
        # computed once — pure function of (id, seed, generation).
        self._identity_cache: dict[tuple[int, int], tuple[str, str, float, float, float]] = {}
        self.disease_id = 0
        self.weather = "clear"
        self.clans: dict[int, dict] = {}  # id -> {name, founder_id, born_tick, color}
        self._next_clan_id = 1
        self.relations: dict[tuple[int, int], int] = {}  # clan pair -> -100..100
        self._relation_zones: dict[tuple[int, int], int] = {}  # last seen zone
        self.coalitions: dict[int, dict] = {}  # §AB: id -> {name, leader_clan, members}
        self._next_coalition_id = 1
        self._clan_coalition: dict[int, int] = {}  # clan id -> coalition id
        # §AB: declared wars — pair -> tick of the last declaration. One active
        # feud per pair; prevents leaders re-declaring war on the same clan
        # while the feud is already open (or freshly concluded).
        self._declared_wars: dict[tuple[int, int], int] = {}
        self._eaters_this_tick: list[int] = []
        # §AP theology: sacred truces (synod/epiphany) still all strife while > 0
        self.truce_ticks = 0
        self._last_season: str | None = None  # season-change detector for miracles
        self.fertile: list[dict] = []  # {x,y,r} — food prefers these grounds
        self.rocks: list[dict] = []  # {x,y,r} — solid circles that block movement
        self.rivers: list[dict] = []  # §AQ PH-3: horizontal channels {cy,hw,base_hw,dir,water,flood_ticks,silt_ticks}
        self.bridges: list[dict] = []  # §AQ PH-3: planks {x,cy,hw,hp}
        self.dams: list[dict] = []  # §AQ PH-3: stone dams {x,cy,hp}
        # §AQ PH-4: the height of the land + the paths feet pack into roads
        self._elev_cols = max(1, math.ceil(self.config.width / ELEV_CELL))
        self._elev_rows = max(1, math.ceil(self.config.height / ELEV_CELL))
        self.elev_grid: list[float] = [0.5] * (self._elev_cols * self._elev_rows)  # 0..1
        # §AQ PH-8/9/10: quakes, bolts, shimmer fronts & hidden zones
        self.pending_quake: dict | None = None  # {x,y,mag,hit_tick,warned}
        self.lightning: list[dict] = []  # {x,y,ttl} visible bolts
        self.law_wave: dict | None = None  # {born_tick}
        self.anomalies: list[dict] = []  # {x,y,kind,discovered}
        self._totem_mult_cache: dict[int, float] = {}
        self._clan_deaths: dict[int, int] = {}
        self.signals: list[dict] = []  # §Q: {x,y,kind,sender,clan_id,ttl}
        self.fires: list[dict] = []  # §S wildfire: {x,y,r,ttl}
        self.campfires: list[dict] = []  # §AO E: field campfires {x,y,day}
        # §AQ PH-1: coarse ambient heat field (row-major, top-left origin)
        self._temp_cols = max(1, math.ceil(self.config.width / TEMP_CELL))
        self._temp_rows = max(1, math.ceil(self.config.height / TEMP_CELL))
        base0 = SEASON_BASE_TEMP[SEASONS[0]]
        self.temperature_grid = [base0] * (self._temp_cols * self._temp_rows)
        # §AM: living soil — a fertility grid the harvests draw upon
        self._soil_cols = self._temp_cols
        self._soil_rows = self._temp_rows
        self.soil_grid = [1.0] * (self._soil_cols * self._soil_rows)
        # §AQ PH-4: traffic over the same coarse cells — feet pack the earth
        self.traffic_grid: list[float] = [0.0] * (self._temp_cols * self._temp_rows)
        self.wind_angle = (self.config.seed % 6283) / 1000.0  # §AQ PH-2, rng-free init
        self.wind_speed = WIND_CALM_SPEED
        # §AU O-1: wind direction trig computed once per tick, not per query
        self._wind_cached_for = None
        self._cos_wind = 1.0
        self._sin_wind = 0.0
        self._sync_wind_cache()
        # §AM agriculture: tilled plots per clan + feast pacing
        self.farm_plots: dict[int, list[dict]] = {}  # clan id -> [{x,y,irrigated}]
        self._banquet_last: dict[int, int] = {}  # clan id -> tick of last feast
        self._last_hospitality_tick = -10 * HOSPITALITY_GAP
        # §AN diplomacy: boundary stones, markets & omen bookkeeping
        self.boundary_stones: list[dict] = []  # {x,y,clan_id}
        self.markets: dict[tuple[int, int], dict] = {}  # pair -> {x,y,born_tick}
        self._stone_chime_last: dict[int, int] = {}  # clan id -> last chime tick
        self._omen_season: str | None = None
        self._caravan_last: dict[tuple[int, int], int] = {}  # pair -> last caravan
        # AJ: Delta compression tracking (Phase 1)
        self._last_broadcast_state: dict[int, tuple] = {}
        self._last_broadcast_entities: set[int] = set()
        # M-4: contiguous native buffers for OpenMP batch (zero-copy, pre-allocated)
        self._c_creatures_buf = None  # type: ignore
        self._c_entities_buf = None  # type: ignore
        self._c_out_buf = None  # type: ignore
        # BA: micro-neural SoA substrate (opt-in, gated by nn_enabled)
        self._soa: object | None = None  # AgentSoA when enabled
        self._nn_grid: object | None = None  # SpatialHashGrid when enabled
        self._nn_tick: int = 0
        self._generate_elevation()  # §AQ PH-4: the shape of the land comes first
        self._generate_rivers()  # §AQ PH-3: channels follow the slope
        self._generate_anomalies()  # §AQ PH-10: hidden zones of strange physics
        self._spawn_initial()
        self._generate_terrain()
        self._consecrate_initial_shrines()

    def _consecrate_initial_shrines(self) -> None:
        """§AP: settled clans consecrate their shrine at founding, not on the
        first tick afterwards — keeps the first delta frame free of an
        all-clans burst (the keyframe already carries shrine_level)."""
        if not self.config.theology_enabled:
            return
        living: set[int] = set()
        for c in self.world.creatures():
            if c.clan_id:
                living.add(c.clan_id)
        for cid, info in self.clans.items():
            if cid in living and int(info.get("shrine_level", 0)) == 0:
                info["shrine_level"] = 1


    # ------------------------------------------------------------- the sky
    def _time_of_day(self) -> float:
        """0=midnight, 0.25=sunrise, 0.5=noon, 0.75=sunset; world starts at sunrise."""
        dl = max(1, self.config.day_length)
        return ((self.tick + 0.25 * dl) % dl) / dl

    def _is_night(self, tod: float) -> bool:
        return tod < 0.22 or tod > 0.78

    def _season(self) -> str:
        return SEASONS[(self.tick // max(1, self.config.season_length)) % 4]

    def _age(self) -> str | None:
        if not self.config.age_enabled:
            return None
        idx = (self.tick // max(1, self.config.age_length)) % len(AGES)
        return AGES[idx]

    def _age_tick(self) -> int:
        if not self.config.age_enabled:
            return 0
        return self.tick % max(1, self.config.age_length)

    def _age_day(self) -> int:
        if not self.config.age_enabled:
            return 1
        dl = max(1, self.config.day_length)
        return (self._age_tick() // dl) + 1

    def _age_total_days(self) -> int:
        if not self.config.age_enabled:
            return 1
        dl = max(1, self.config.day_length)
        return max(1, self.config.age_length // dl)

    @property
    def day(self) -> int:
        return self.tick // max(1, self.config.day_length) + 1

    def _update_weather(self) -> None:
        cfg = self.config
        if not cfg.weather_enabled or self.rng.random() >= cfg.weather_change_rate:
            return
        others = [w for w in WEATHER_STATES if w != self.weather]
        self.weather = self.rng.choice(others)
        # §AR S-6: high castes read the sky the moment it turns
        self._weather_since_tick = self.tick
        # §AQ PH-2: a new sky brings a new wind — direction re-rolls near the
        # season's prevailing bearing.
        self.wind_angle = (
            WIND_SEASON_BIAS[self._season()] + self.rng.uniform(-1.0, 1.0)
        ) % (2 * math.pi)

    def _update_wind(self) -> None:
        """§AQ PH-2: the wind's strength follows the sky — storms howl, calm
        days barely stir the grass."""
        target = {
            "storm": WIND_STORM_SPEED,
            "rain": WIND_RAIN_SPEED,
        }.get(self.weather, WIND_CALM_SPEED)
        self.wind_speed += (target - self.wind_speed) * WIND_RATE
        self._sync_wind_cache()

    def _sync_wind_cache(self) -> None:
        """§AU O-1: keep the precomputed wind trig honest even when a test (or
        a future system) mutates wind_angle between ticks."""
        if getattr(self, "_wind_cached_for", None) != self.wind_angle:
            self._cos_wind = math.cos(self.wind_angle)
            self._sin_wind = math.sin(self.wind_angle)
            self._wind_cached_for = self.wind_angle

    def env_sight_mult(self) -> float:
        """Night and fog dim every eye (Sight Recognition suffers)."""
        cfg = self.config
        m = 1.0
        if self._is_night(self._time_of_day()):
            m *= cfg.night_sight_mult
        if self.weather == "fog":
            m *= cfg.fog_sight_mult
        return m

    def env_speed_mult(self) -> float:
        return self.config.rain_speed_mult if self.weather in ("rain", "storm") else 1.0

    @staticmethod
    def _health_speed_mult(health: float) -> float:
        """§AT-4 H-0: wounds slow the body — a creature at 5 HP is no sprinter."""
        for threshold, mult in sorted(HEALTH_SPEED_TIERS, key=lambda t: t[0]):
            if health < threshold:
                return mult
        return 1.0

    @staticmethod
    def _health_sight_mult(health: float) -> float:
        """§AT-4 H-1: a sick body cannot see as far."""
        for threshold, mult in HEALTH_SIGHT_TIERS:
            if health < threshold:
                return mult
        return 1.0

    @staticmethod
    def _forage_mult(health: float) -> float:
        """§AT-4 H-1: weakness blunts the harvest — decline feeds on itself."""
        if health < 30.0:
            return FORAGE_MULT_WEAK
        if health < 60.0:
            return FORAGE_MULT_HURT
        return 1.0

    def _effective_fear_radius(self, c: Creature, is_night: bool = False) -> float:
        """§AR S-0: the fear threshold is a sense like any other — traits bend
        it (paranoid +4, bold −2.5) and starvation halves it: the desperate
        walk toward death chasing scented food. §AP: the Eternal Hearth keeps
        its people calm through the night."""
        r = self.config.fear_radius
        if c.trait == "paranoid":
            r += 4.0
        elif c.trait == "bold":
            r = max(2.0, r - 2.5)
        ratio = c.energy / self.config.energy_max if self.config.energy_max > 0 else 1.0
        if ratio <= self.config.starving_ratio:
            r *= 0.5
        if is_night:
            r = max(2.0, r - self._totem_stat(c, "calm"))
        # §AN: the priest's liturgy calms the panicked heart for a while
        if c.calm_ticks > 0:
            r = max(1.0, r - 2.0)
        # §AQ PH-9: a living priest's bio-electric field quiets the nerves —
        # stronger the richer the clan's faith pool runs.
        ppos = self._priest_pos_for(c.clan_id)
        if ppos is not None:
            d2p = self.world.distance_sq(c.x, c.y, ppos[0], ppos[1])
            if d2p <= PRIEST_AURA_RADIUS * PRIEST_AURA_RADIUS:
                faith = float(self.clans.get(c.clan_id, {}).get("faith", 0.0))
                calm = PRIEST_CALM * max(0.6, min(1.6, 0.7 + faith / 200.0))
                r = max(1.0, r - calm)
        return r
    def _sun_factor(self) -> float:
        """§AQ PH-0: sunlight is the world's only income — no free growth at
        night. Zero through the dark, a low arc at the edges of day, full
        strength at noon. (Winter's bite stays the season table.)"""
        tod = self._time_of_day()
        if tod <= 0.22 or tod >= 0.78:
            return 0.0
        x = (tod - 0.5) / 0.28  # −1..1 across the daylight window
        return max(0.15, 1.0 - x * x)

    def _is_torpid(self, c: Creature) -> bool:
        """§AQ PH-7: a starving body in killing cold has shut down."""
        em = self.config.energy_max
        ratio = c.energy / em if em > 0 else 1.0
        return (
            not c.is_predator
            and ratio <= TORPOR_ENERGY_RATIO
            and self.ambient_at(c.x, c.y) < HYPOTHERMIA_TEMP
        )

    @staticmethod
    def _metabolic_cost(c: Creature) -> float:
        """§AQ PH-0: upkeep scales with body complexity — a priest's aura is
        expensive, a woman's line burns hot, triangles run lean."""
        return METABOLIC_COST.get(c.caste, DEFAULT_METABOLIC_COST)

    # -------------------------------------------------- §AQ PH-1 thermodynamics
    def _pick_house_material(self, x: float | None = None, y: float | None = None) -> str:
        """Seeded material mix: straw common, stone rare (insulation: straw <
        wood < stone). §AQ PH-6: settlements beside a river dig clay — riverbank
        brick insulates better than anything but stays middling in durability.
        Consumes the rng only at house creation."""
        r = self.rng.random()
        if (
            x is not None and y is not None and self.rivers
            and self._in_river_band(x, y, pad=RIVER_SILT_RADIUS + 4.0)
            and r < 0.55
        ):
            return "clay"
        if r < 0.20:
            return "stone"
        if r < 0.55:
            return "wood"
        return "straw"

    def _update_temperature(self) -> None:
        """§AQ PH-1 heat field: each cell relaxes toward its target — the
        seasonal base swept across the map from an edge, bent by the day
        cycle, weather, and any open flame."""
        cfg = self.config
        sl = max(1, cfg.season_length)
        p = (self.tick % sl) / sl  # progress through the current season
        s_idx = SEASONS.index(self._season())
        cur = SEASON_BASE_TEMP[SEASONS[s_idx]]
        nxt = SEASON_BASE_TEMP[SEASONS[(s_idx + 1) % 4]]
        cold_front = nxt < cur  # cold enters from the west, warmth from the east
        diurnal = DAY_HEAT_AMPLITUDE * (self._sun_factor() * 2.0 - 1.0)
        weather_bump = {"rain": -2.0, "storm": -3.0, "fog": -1.0}.get(self.weather, 0.0)
        w_cols = self._temp_cols
        for row in range(self._temp_rows):
            for col in range(w_cols):
                xn = (col + 0.5) / w_cols
                if cold_front:
                    sweep = min(1.0, max(0.0, p * 1.6 - xn * 0.6))
                else:
                    sweep = min(1.0, max(0.0, p * 1.6 - (1.0 - xn) * 0.6))
                target = cur + (nxt - cur) * sweep + diurnal + weather_bump
                i = row * w_cols + col
                self.temperature_grid[i] += (target - self.temperature_grid[i]) * TEMP_RATE
        # Open flame dominates its neighbourhood (circle-vs-cell overlap).
        if self.fires:
            cell_w = cfg.width / w_cols
            cell_h = cfg.height / self._temp_rows
            for f in self.fires:
                c0 = max(0, int((f["x"] - FIRE_HEAT_RADIUS) / cell_w))
                c1 = min(w_cols - 1, int((f["x"] + FIRE_HEAT_RADIUS) / cell_w))
                r0 = max(0, int((f["y"] - FIRE_HEAT_RADIUS) / cell_h))
                r1 = min(self._temp_rows - 1, int((f["y"] + FIRE_HEAT_RADIUS) / cell_h))
                for row in range(r0, r1 + 1):
                    for col in range(c0, c1 + 1):
                        qx = min(max(f["x"], col * cell_w), (col + 1) * cell_w)
                        qy = min(max(f["y"], row * cell_h), (row + 1) * cell_h)
                        dx = qx - f["x"]
                        dy = qy - f["y"]
                        if dx * dx + dy * dy <= FIRE_HEAT_RADIUS * FIRE_HEAT_RADIUS:
                            i = row * w_cols + col
                            self.temperature_grid[i] += (FIRE_HEAT - self.temperature_grid[i]) * TEMP_RATE

    def ambient_at(self, x: float, y: float) -> float:
        """Ambient temperature at a point on the heat field (§AQ PH-1)."""
        col = min(self._temp_cols - 1, max(0, int(x / self.config.width * self._temp_cols)))
        row = min(self._temp_rows - 1, max(0, int(y / self.config.height * self._temp_rows)))
        t = self.temperature_grid[row * self._temp_cols + col]
        # §AO E: a field campfire warms its circle of light.
        for cf in self.campfires:
            if (x - cf["x"]) ** 2 + (y - cf["y"]) ** 2 <= CAMPFIRE_LIGHT_RADIUS * CAMPFIRE_LIGHT_RADIUS:
                t = max(t, CAMPFIRE_HEAT)
        return t

    def indoor_ambient(self, house: House) -> float:
        """Inside air: insulation pulls the room toward comfort; bigger floors
        shed heat faster (perimeter/area bites in 2D). A lit hearth (§AQ PH-1)
        pulls the room past comfort toward hearth-warm."""
        ins = INSULATION_BY_MATERIAL.get(house.material, INSULATION_BY_MATERIAL["wood"])
        size_factor = max(0.4, min(1.0, HOUSE_REF_SIDE / max(1.0, house.size)))
        amb = self.ambient_at(house.x, house.y)
        indoor = amb + (HOUSE_COMFORT_TEMP - amb) * ins * size_factor
        if getattr(house, "hearth_lit", False):
            indoor += (HEARTH_COMFORT_TEMP - indoor) * HEARTH_PULL * size_factor
        return indoor

    def _update_hearths(self) -> None:
        """§AQ PH-1: hearths — permanent fire installations inside claimed
        houses. Kin buy fuel from the clan larder when the roof (or the cold)
        calls for it; the pile burns down every tick and an unfed hearth goes
        dark. Winter survival infrastructure."""
        if not self.config.hearths_enabled:
            for h in self._cached_houses:
                if h.hearth_lit:  # withdraw the law — every flame gutters out
                    h.hearth_lit = False
                    h.hearth_fuel = 0.0
            return
        tod = self._time_of_day()
        want_warmth = (
            self._season() in ("autumn", "winter")
            or self._is_night(tod)
            or self.weather in ("rain", "storm")
        )
        # Burn first — every lit hearth eats its woodpile this tick.
        for h in self._cached_houses:
            if not h.hearth_lit:
                continue
            h.hearth_fuel -= HEARTH_BURN_RATE
            if h.hearth_fuel <= 0.0:
                h.hearth_fuel = 0.0
                h.hearth_lit = False
        if not want_warmth or self.tick % HEARTH_REFUEL_INTERVAL != 0:
            return
        # Kin at home top up the hearth from the clan larder.
        members_by_clan: dict[int, list[Creature]] = {}
        for c in self._cached_creatures:
            if c.clan_id:
                members_by_clan.setdefault(c.clan_id, []).append(c)
        reach_sq: dict[float, float] = {}
        for h in self._cached_houses:
            if h.is_ruin or not h.clan_id:
                continue
            kin = members_by_clan.get(h.clan_id)
            if not kin:
                continue
            r2 = (h.size * 0.5 + 3.0) ** 2
            near = False
            for c in kin:
                dx, dy = self.world.delta(c.x, c.y, h.x, h.y)
                if dx * dx + dy * dy <= r2:
                    near = True
                    break
            if not near:
                continue
            clan = self.clans.get(h.clan_id)
            if clan is None:
                continue
            # people eat before fire burns: a clan with starving members
            # never feeds the hearth (the Ice age taught this the hard way)
            emax = self.config.energy_max or 1.0
            if any(k.energy / emax <= self.config.starving_ratio for k in kin):
                continue
            stored = float(clan.get("larder", 0.0))
            if stored < HEARTH_REFUEL_CHUNK:
                continue  # the larder is bare — the hearth dies tonight
            take = min(HEARTH_REFUEL_CHUNK, stored,
                       max(0.0, (HEARTH_FUEL_MAX - h.hearth_fuel)) / HEARTH_FUEL_PER_ENERGY)
            if take <= 0:
                continue
            clan["larder"] = stored - take
            h.hearth_fuel = min(HEARTH_FUEL_MAX, h.hearth_fuel + take * HEARTH_FUEL_PER_ENERGY)
            h.hearth_lit = True

    # -------------------------------------------------- §AQ PH-3 rivers
    def _generate_elevation(self) -> None:
        """§AQ PH-4: a smooth height field from seeded sinusoids (a dedicated
        geography rng — the shape of the land never perturbs the life stream),
        normalized to 0..1 across ELEV_MAX_HEIGHT world-units of relief."""
        if not self.config.relief_enabled:
            return
        geo_rng = random.Random((self.config.seed * 77017) ^ 0x5EED1A)
        w, h = self.config.width, self.config.height
        waves = []
        for _ in range(4):
            fx = geo_rng.uniform(1.0, 4.0) * math.tau / max(w, 1.0)
            fy = geo_rng.uniform(1.0, 4.0) * math.tau / max(h, 1.0)
            px = geo_rng.uniform(0, math.tau)
            py = geo_rng.uniform(0, math.tau)
            amp = geo_rng.uniform(0.6, 1.4)
            waves.append((amp, fx, fy, px, py))
        vals = []
        for row in range(self._elev_rows):
            for col in range(self._elev_cols):
                x = (col + 0.5) * w / self._elev_cols
                y = (row + 0.5) * h / self._elev_rows
                v = 0.0
                for amp, fx, fy, px, py in waves:
                    v += amp * math.sin(fx * x + px) * math.sin(fy * y + py)
                vals.append(v)
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1.0
        self.elev_grid = [round((v - lo) / span, 4) for v in vals]
        # §AQ PH-4 smooth: 2-pass 3x3 blur cuts cliff edges from ~22% to <5% while
        # preserving overall relief shape; plateau test (1.0 vs 0.0) stays a cliff.
        for _ in range(2):
            blurred: list[float] = []
            for r in range(self._elev_rows):
                for c in range(self._elev_cols):
                    s = 0.0
                    n = 0
                    for dr in (-1, 0, 1):
                        nr = r + dr
                        if nr < 0 or nr >= self._elev_rows:
                            continue
                        base = nr * self._elev_cols
                        for dc in (-1, 0, 1):
                            nc = c + dc
                            if 0 <= nc < self._elev_cols:
                                s += self.elev_grid[base + nc]
                                n += 1
                    blurred.append(s / n if n else self.elev_grid[r * self._elev_cols + c])
            self.elev_grid = blurred
        # re-normalize after blur to restore 0..1 extremes for the bounded test
        lo2, hi2 = min(self.elev_grid), max(self.elev_grid)
        span2 = (hi2 - lo2) or 1.0
        self.elev_grid = [round((v - lo2) / span2, 4) for v in self.elev_grid]
        try:
            import ctypes
            self._elev_c_buf = (ctypes.c_float * len(self.elev_grid))(*self.elev_grid)
        except Exception:
            self._elev_c_buf = None

    def _elev_at(self, x: float, y: float) -> float:
        """Normalised ground height (0..1) under a point; 0.5 flat worlds.
        Bilinear between cell centres — the land is smooth, so ordinary travel
        never trips the cliff threshold (only true escarpments do).
        §AU O-1: closure inlined — clamped grid reads straight off the buffer."""
        if not self.config.relief_enabled:
            return 0.5
        if getattr(self, "_elev_c_buf", None) is not None and _native_core and hasattr(_native_core, "native_elev_at"):
            return _native_core.native_elev_at(
                x, y, self._elev_c_buf, self._elev_cols, self._elev_rows, self.config.width, self.config.height
            )
        cols = self._elev_cols
        rows = self._elev_rows
        grid = self.elev_grid
        gx = x / self.config.width * cols - 0.5
        gy = y / self.config.height * rows - 0.5
        c0 = math.floor(gx)
        r0 = math.floor(gy)
        fx = gx - c0
        fy = gy - r0
        cc0 = 0 if c0 < 0 else (cols - 1 if c0 > cols - 1 else c0)
        cc1 = 0 if c0 + 1 < 0 else (cols - 1 if c0 + 1 > cols - 1 else c0 + 1)
        rr0 = 0 if r0 < 0 else (rows - 1 if r0 > rows - 1 else r0)
        rr1 = 0 if r0 + 1 < 0 else (rows - 1 if r0 + 1 > rows - 1 else r0 + 1)
        h00 = grid[rr0 * cols + cc0]
        h10 = grid[rr0 * cols + cc1]
        h01 = grid[rr1 * cols + cc0]
        h11 = grid[rr1 * cols + cc1]
        top = h00 * (1.0 - fx) + h10 * fx
        bot = h01 * (1.0 - fx) + h11 * fx
        return top * (1.0 - fy) + bot * fy

    def _elev_cell_units(self, x: float, y: float) -> float:
        """Nearest-cell height in world-units — the RAW terraced field, used
        only for cliff detection: a cell-boundary drop this steep is a cliff."""
        col = min(self._elev_cols - 1, max(0, int(x / self.config.width * self._elev_cols)))
        row = min(self._elev_rows - 1, max(0, int(y / self.config.height * self._elev_rows)))
        return self.elev_grid[row * self._elev_cols + col] * ELEV_MAX_HEIGHT

    def _elev_units(self, x: float, y: float) -> float:
        """Ground height in world-units (bodies and water care about these)."""
        return self._elev_at(x, y) * ELEV_MAX_HEIGHT

    def _terrain_effects(self, c: Creature, px: float, py: float) -> None:
        """§AQ PH-4 applied to one body after it moves: uphill grade bleeds
        energy and slows the stride, cliffs hurt, feet pack roads, and rain
        loosens steep slopes into landslides."""
        cfg = self.config
        if not cfg.relief_enabled:
            return
        # traffic: this body just packed the earth it stands on
        tcol = min(self._temp_cols - 1, max(0, int(c.x / cfg.width * self._temp_cols)))
        trow = min(self._temp_rows - 1, max(0, int(c.y / cfg.height * self._temp_rows)))
        ti = trow * self._temp_cols + tcol
        self.traffic_grid[ti] += TRAFFIC_PER_PASS
        # grade along the step just taken — smooth bilinear field: ordinary
        # ground never trips the cliff; only terraced cell drops do
        dxg, dyg = self.world.delta(px, py, c.x, c.y)
        dist = math.hypot(dxg, dyg)
        if dist < 1e-6:
            return
        # §AQ PH-4 cliff check first — terraced drop is law, not smooth grade.
        # Cooldown prevents a tumbling chain from shredding the same body.
        if getattr(c, "fall_cooldown", 0) <= 0:
            cell_drop = (
                self._elev_cell_units(px, py) - self._elev_cell_units(c.x, c.y)
            )
            if cell_drop >= CLIFF_DROP_UNITS:
                excess = cell_drop - CLIFF_DROP_UNITS
                dmg = FALL_DAMAGE_PER_UNIT * (excess + CLIFF_DROP_UNITS * 0.5)
                # Barrier: the edge stops the body — revert, turn, stumble.
                # Keeps the lethal-plateau test (60-unit drop) lethal, but
                # ordinary 15-20-unit steps become a bruise, not a grave.
                c.x, c.y = px, py
                c.angle += math.pi + self.rng.uniform(-0.6, 0.6)
                c.fall_cooldown = FALL_COOLDOWN_TICKS
                c.pause_ticks = max(getattr(c, "pause_ticks", 0), 6)
                c.wound_ticks = max(getattr(c, "wound_ticks", 0), 30)
                c.wound_severity = max(getattr(c, "wound_severity", 0), 1)
                if not c.emote:
                    c.emote = "panic"
                    c.emote_ticks = 12
                if c.health - dmg <= 0:
                    self._kill(c, "fall")
                else:
                    c.health -= dmg
                    # stumble drains a little energy too
                    c.energy = max(0.0, c.energy - 4.0)
                # cliff handled — don't also charge uphill energy on same step
                return
        rise = self._elev_units(c.x, c.y) - self._elev_units(px, py)  # >0 climbed
        grade = rise / dist  # >0 climbing
        if grade > 0:
            c.energy = max(0.0, c.energy - SLOPE_ENERGY_COST * grade)
        # avalanche: rain loosens genuinely steep ground underfoot — measured
        # from the terraced field's local cell grade, not the step just taken
        if self.weather in ("rain", "storm") and self.rng.random() < AVALANCHE_CHANCE:
            ecol = min(self._elev_cols - 1, max(0, int(c.x / cfg.width * self._elev_cols)))
            erow = min(self._elev_rows - 1, max(0, int(c.y / cfg.height * self._elev_rows)))
            here = self.elev_grid[erow * self._elev_cols + ecol]
            best_drop = 0.0
            slide_dx = slide_dy = 0.0
            for ddc, ddr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc = min(self._elev_cols - 1, max(0, ecol + ddc))
                nr = min(self._elev_rows - 1, max(0, erow + ddr))
                drop = here - self.elev_grid[nr * self._elev_cols + nc]  # >0 downhill
                if drop > best_drop:
                    best_drop = drop
                    slide_dx, slide_dy = float(ddc), float(ddr)
            if best_drop * ELEV_MAX_HEIGHT / ELEV_CELL >= AVALANCHE_SLOPE:
                push = 8.0
                c.x, c.y = self.world.normalize(
                    c.x + slide_dx * push, c.y + slide_dy * push
                )
                dmg = self.rng.uniform(8.0, 20.0)
                if c.health - dmg <= 0:
                    self._kill(c, "landslide")
                else:
                    c.health -= dmg

    def _road_speed_mult(self, x: float, y: float) -> float:
        """Packed earth is fast going (§AQ PH-4 emergent roads)."""
        col = min(self._temp_cols - 1, max(0, int(x / self.config.width * self._temp_cols)))
        row = min(self._temp_rows - 1, max(0, int(y / self.config.height * self._temp_rows)))
        traffic = self.traffic_grid[row * self._temp_cols + col]
        if traffic <= 0:
            return 1.0
        return 1.0 + min(ROAD_SPEED_CAP, traffic * ROAD_SPEED_PER_TRAFFIC)

    def _update_traffic(self) -> None:
        """Rain and grass slowly heal packed earth; roads need constant use.
        §AU O-2: the decay sweep runs every 10th tick with the compounded
        factor (`0.995**10`) — identical mathematics, a tenth of the work."""
        if not self.config.relief_enabled:
            return
        if self.tick % 10 != 0:
            return
        g = self.traffic_grid
        f = TRAFFIC_DECAY_STAGGERED
        for i in range(len(g)):
            if g[i] > 0:
                g[i] *= f
                if g[i] < 0.05:
                    g[i] = 0.0
    def _generate_rivers(self) -> None:
        """§AQ PH-3: seed the world's river channels — horizontal bands with a
        flow direction each, spaced down the map so every bank stays reachable.
        Runs before life spawns so houses and fields never root in the water.
        Draws from a dedicated rng so geography never perturbs the life stream."""
        if not self.config.rivers_enabled:
            return
        count = max(0, int(self.config.river_count))
        if count == 0:
            return
        geo_rng = random.Random((self.config.seed * 100003) ^ 0x9E3779B9)
        margin = 30.0
        usable = max(10.0, self.config.height - 2 * margin)
        for i in range(count):
            cy = (margin + usable * (i + 1 + geo_rng.uniform(-0.2, 0.2)) / (count + 1)) % self.config.height
            # water runs downhill: flow follows the east-west height gradient
            mid_x = self.config.width / 2
            probe = self.config.width / 8
            h_west = self._elev_units(mid_x - probe, cy)
            h_east = self._elev_units(mid_x + probe, cy)
            if h_west != h_east:
                direction = 1.0 if h_west > h_east else -1.0
            else:
                direction = 1.0 if geo_rng.random() < 0.5 else -1.0
            self.rivers.append({
                "cy": round(cy, 2),
                "hw": RIVER_BASE_HW,
                "base_hw": RIVER_BASE_HW,
                "dir": direction,
                "water": 0.0,
                "flood_ticks": 0,
                "silt_ticks": 0,
            })

    def _river_dy(self, y: float, cy: float) -> float:
        """Wrap-aware vertical distance to a channel centre line."""
        dy = abs(y - cy)
        return min(dy, self.config.height - dy)

    def _river_at(self, x: float, y: float) -> dict | None:
        """The channel band containing this point, if any."""
        for r in self.rivers:
            if self._river_dy(y, r["cy"]) <= r["hw"]:
                return r
        return None

    def _in_river_band(self, x: float, y: float, pad: float = 0.0) -> bool:
        """True when the point sits inside a channel plus margin — used by
        worldgen so houses never straddle the water."""
        for r in self.rivers:
            if self._river_dy(y, r["cy"]) <= r["hw"] + pad:
                return True
        return False

    def _on_bridge_or_dam(self, x: float, y: float) -> bool:
        """Crossings are dry: planks span the band at their post's x."""
        for b in self.bridges:
            dx = abs(x - b["x"])
            if dx > self.config.width / 2:
                dx = self.config.width - dx
            if dx <= BRIDGE_HALF_WIDTH and self._river_dy(y, b["cy"]) <= b["hw"] + 2.0:
                return True
        for d in self.dams:
            dx = abs(x - d["x"])
            if dx > self.config.width / 2:
                dx = self.config.width - dx
            r = next((r for r in self.rivers if r["cy"] == d["cy"]), None)
            if r is not None and dx <= BRIDGE_HALF_WIDTH and self._river_dy(y, r["cy"]) <= r["hw"] + 3.0:
                return True
        return False

    def _update_rivers(self) -> None:
        """§AQ PH-3: rain swells the channels; a full channel bursts its banks;
        floodwater widens the band, tears out plants and drowns the stubborn;
        receded water leaves fertile silt on the banks. Dams hold back floods
        until they fail. Planks rot; builders rebuild (see _update_builders)."""
        raining = self.weather in ("rain", "storm")
        for r in self.rivers:
            dam = next((d for d in self.dams if d["cy"] == r["cy"] and d["hp"] > 0), None)
            if raining:
                gain = RIVER_RAIN_RATE * (1.5 if self.weather == "storm" else 1.0)
                if dam is not None:
                    gain *= 0.5  # the dam drinks the crest
                r["water"] = min(1.5, r["water"] + gain)
            else:
                r["water"] = max(0.0, r["water"] - RIVER_DRY_RATE)
            # flood pressure grinds the masonry down — dams hold, then burst
            if dam is not None:
                if r["flood_ticks"] > 0 or (raining and r["water"] >= 1.0):
                    dam["hp"] -= DAM_STRESS_DAMAGE
            if r["flood_ticks"] <= 0 and r["water"] >= 1.0:
                r["flood_ticks"] = RIVER_FLOOD_TICKS
                r["water"] = 0.0
                self._emit(HistoryEvent(
                    type="disaster", tick=self.tick + 1, entity_id=0,
                    x=round(self.config.width / 2, 2), y=round(r["cy"], 2),
                    payload={"kind": "river_flood", "river_cy": r["cy"]},
                ))
            if r["flood_ticks"] > 0:
                r["flood_ticks"] -= 1
                target_hw = RIVER_BASE_HW * RIVER_FLOOD_HW_MULT
                r["hw"] += (target_hw - r["hw"]) * RIVER_FLOOD_GROW
                # floodwater tears out rooted plants in the swollen band
                if self._cached_foods and self.tick % 5 == 0:
                    for f in list(self._cached_foods):
                        if self._river_dy(f.y, r["cy"]) <= r["hw"] and self.rng.random() < 0.25:
                            self.world.remove(f.id)
                if r["flood_ticks"] == 0:
                    r["silt_ticks"] = RIVER_SILT_TICKS  # the gift the water leaves
            else:
                r["hw"] += (r["base_hw"] - r["hw"]) * RIVER_FLOOD_EBB
            if r["silt_ticks"] > 0:
                r["silt_ticks"] -= 1
        # dams fail catastrophically when ground away under pressure
        for d in [d for d in self.dams if d["hp"] <= 0]:
            self.dams.remove(d)
            r = next((r for r in self.rivers if r["cy"] == d["cy"]), None)
            if r is not None:
                r["flood_ticks"] = max(r["flood_ticks"], RIVER_FLOOD_TICKS // 2)
                r["hw"] = min(RIVER_BASE_HW * RIVER_FLOOD_HW_MULT * DAM_FLASH_SPIKE, r["hw"] * DAM_FLASH_SPIKE)
                self._emit_boom(d["x"], d["cy"])
                self._emit(HistoryEvent(
                    type="disaster", tick=self.tick + 1, entity_id=0,
                    x=round(d["x"], 2), y=round(d["cy"], 2),
                    payload={"kind": "flash_flood", "river_cy": d["cy"]},
                ))
        # planks rot
        # planks rot gracefully (decay every 20 ticks for realistic longevity)
        for b in [b for b in self.bridges if b["hp"] <= 0]:
            self.bridges.remove(b)
        if self.tick % 20 == 0:
            for b in self.bridges:
                b["hp"] -= 1

    def _river_effects(self, c: Creature) -> None:
        """§AQ PH-3 applied to one body after it moves: wading costs gentle energy,
        bridges cross dry, current carries gentle downstream drift,
        cools overheating creatures, washes disease, and rewards river foraging."""
        r = self._river_at(c.x, c.y)
        if r is None or self._on_bridge_or_dam(c.x, c.y):
            return
        flooded = r["flood_ticks"] > 0
        c.energy = max(0.0, c.energy - (RIVER_FORD_COST * 1.5 if flooded else RIVER_FORD_COST))

        # 1. Hydration & Thermal Cooling: cool hyperthermia towards comfort 20°C
        if getattr(c, "body_temp", 20.0) > 20.5:
            c.body_temp = max(20.0, getattr(c, "body_temp", 20.0) - 0.4)
        # 2. Hygiene & Cleanliness: freshwater washes contagion risk
        if getattr(c, "infected", False) and self.rng.random() < 0.02:
            c.infected = False  # river bath washes sickness
            c.emote = "cheer"
            c.emote_ticks = 15
        if getattr(c, "chill", 0.0) > 0 and self.weather not in ("rain", "storm", "snow"):
            c.chill = max(0.0, c.chill - 0.1)

        # 3. Downstream current drift without locking creature's steering angle
        weak = c.stage == "infant" or c.health < RIVER_SWEEP_HEALTH
        if weak or flooded:
            push = RIVER_SWEEP_SPEED * (1.5 if flooded else 0.8) * (0.5 if not weak else 1.0)
            nx = c.x + r["dir"] * push
            ny = c.y + (self.rng.uniform(-0.05, 0.05) if not weak else 0.0)
            c.x, c.y = self.world.normalize(nx, ny)
            # Gentle drift nudge rather than 100% hard override:
            if weak and self.rng.random() < 0.2:
                current_ang = 0.0 if r["dir"] > 0 else math.pi
                diff = (current_ang - c.angle + math.pi) % (2 * math.pi) - math.pi
                c.angle += max(-0.2, min(0.2, diff))

        # 4. Flood water damage: survival skill softens damage
        if flooded:
            soften = 1.0 / (1.0 + c.skills.get("foraging", 0.0) / 20.0)
            dmg = RIVER_DROWN_DAMAGE * soften * 0.2
            if c.health - dmg <= 0:
                self._kill(c, "drowning")
            else:
                c.health -= dmg

    def _point_in_any_house(self, x: float, y: float) -> bool:
        """True when the point stands under some roof (§AQ PH-2 sound block)."""
        for h in self._cached_houses:
            if abs(x - h.x) <= h.size / 2 and abs(y - h.y) <= h.size / 2:
                return True
        return False

    def _emit_boom(self, x: float, y: float) -> None:
        """§AQ PH-2: a loud event — collapse, dam burst — rolls out as a
        pressure wave every creature hears (roofs muffle, wind carries)."""
        if len(self.signals) < SIGNALS_MAX:
            self.signals.append({
                "x": round(x, 2), "y": round(y, 2),
                "kind": "boom", "sender": 0, "clan_id": None, "born_tick": self.tick, "ttl": 10,
            })

    def _update_leader_orders(self) -> None:
        """§AS L-2 — the chief's voice at need: the retreat when bleeding,
        the rite at the great hall, the autumn harvest call, and the
        evacuation when fire or flood comes for the village."""
        cfg = self.config
        if not self.clans or len(self.signals) >= SIGNALS_MAX:
            return
        w = self.world

        def emit(cid: int, leader: Creature, kind: str, ttl: int, **extra) -> None:
            if len(self.signals) < SIGNALS_MAX:
                sg = {
                    "x": round(leader.x, 2), "y": round(leader.y, 2),
                    "kind": kind, "sender": leader.id,
                    "clan_id": cid or None, "born_tick": self.tick, "ttl": ttl,
                }
                sg.update(extra)
                self.signals.append(sg)

        season = self._season()
        for cid in sorted(self.clans.keys()):
            info = self.clans[cid]
            lid = info.get("leader_id")
            leader = self.world.entities.get(lid) if lid is not None else None
            if not isinstance(leader, Creature):
                continue
            mh_id = info.get("main_house_id")
            mh = self.world.entities.get(mh_id) if mh_id is not None else None
            at_home = isinstance(mh, House) and not mh.is_ruin and (
                w.distance(leader.x, leader.y, mh.x, mh.y) <= cfg.territory_radius
            )
            gov = info.get("governance", "republic")
            # 1. retreat — a bleeding general pulls the war party home
            if (
                leader.health <= RETREAT_HEALTH_FRAC * leader.max_health
                and (self.tick + cid) % 20 == 0
            ):
                emit(cid, leader, "retreat", 30)
            # 2. ritual — the rite that powers the totem (§AS L-2/L-5)
            if at_home and self.config.totems_enabled and (self.tick + cid) % RITUAL_INTERVAL == 0:
                power_ticks = RITUAL_TICKS
                if gov == "theocracy":
                    power_ticks *= THEOCRACY_RITUAL_POWER
                info["ritual_until"] = self.tick + power_ticks
                leader.emote = "cheer"
                leader.emote_ticks = 20
            # 3. harvest order — autumn stores decide winter
            if (
                season == HARVEST_ORDER_SEASON
                and at_home
                and cfg.granaries_enabled
                and (self.tick + cid) % 240 == 0
            ):
                emit(cid, leader, "harvest", 60, house_x=round(mh.x, 2), house_y=round(mh.y, 2))
            # 4. evacuation — fire or flood closing on the settlement
            if (self.tick + cid) % 15 == 0:
                hazard = None
                for ffire in self.fires:
                    if w.distance(ffire["x"], ffire["y"], mh.x if mh else leader.x, mh.y if mh else leader.y) < 25.0:
                        hazard = (ffire["x"], ffire["y"])
                        break
                if hazard is None:
                    for rv in self.rivers:
                        if rv.get("flood_ticks", 0) > 0 and mh is not None:
                            dy_ = self._river_dy(mh.y, rv["cy"])
                            if abs(dy_) <= rv["hw"] + 6.0:
                                hazard = (mh.x, rv["cy"])
                                break
                if hazard is not None:
                    hx_, hy_ = hazard
                    dxl, dyl = w.delta(hx_, hy_, leader.x, leader.y)
                    dl = math.hypot(dxl, dyl) or 1e-6
                    ex = leader.x + dxl / dl * 18.0
                    ey = leader.y + dyl / dl * 18.0
                    emit(cid, leader, "evacuate", 40, evac_x=round(ex % cfg.width, 2),
                         evac_y=round(ey % cfg.height, 2))

    def _update_night_watch(self) -> None:
        """§AO Phase C: sentry spearmen hold the doorway — soldiers resting
        near their own threshold poke outward at any beast circling the
        settlement after dark."""
        tod = self._time_of_day()
        if not self._is_night(tod):
            return
        w = self.world
        for c in self._get_creatures():
            if (
                c.caste != "Soldier"
                or c.equipped_item != "spear"
                or c.sleeping
                or not c.clan_id
                or (self.tick + c.id) % 3 != 0
            ):
                continue
            info = self.clans.get(c.clan_id)
            if not info:
                continue
            hid = info.get("main_house_id")
            h = w.entities.get(hid) if hid is not None else None
            if not isinstance(h, House) or h.is_ruin:
                continue
            dx, dy = self._door_pos(h)
            if w.distance_sq(c.x, c.y, dx, dy) > (SPEAR_POKE_RADIUS * 2.0) ** 2:
                continue
            # poke anything hostile circling the threshold
            for o, d2 in w.query_radius_with_dist_sq(dx, dy, SPEAR_POKE_RADIUS):
                if not isinstance(o, Creature) or o.id == c.id or o.indoors:
                    continue
                if o.id not in w.entities:
                    continue
                hostile = (
                    o.is_predator
                    or (o.clan_id == 0 and o.sides == 3)
                    or (o.clan_id and self._zone_of(
                        self.relations.get(self._relation_pair(c.clan_id, o.clan_id), 0)) == -1)
                )
                if not hostile or d2 > SPEAR_POKE_RADIUS * SPEAR_POKE_RADIUS:
                    continue
                dmg = SPEAR_POKE_DAMAGE * (1.0 + c.skills.get("combat", 0.0) / 25.0)
                o.health -= dmg
                c.emote = "combat"
                c.emote_ticks = 12
                c.skills["combat"] = c.skills.get("combat", 0.0) + 0.5
                if o.health <= 0:
                    self._kill(o, "war")
                break

    def _update_structures(self) -> None:
        """§AQ PH-6: material physics — storms and floodwater wear buildings
        down, builders mend what still stands, collapsed roofs leave rubble
        that blocks the lot until it is cleared."""
        cfg = self.config
        houses = self._cached_houses or self._functional_houses()
        # wear
        for h in houses:
            if h.is_ruin:
                continue
            if h.hp < 0:
                h.hp = MATERIAL_STATS.get(h.material, MATERIAL_STATS["wood"])["durability"]
            if not cfg.structural_enabled:
                continue
            wear = 0.0
            if self.weather == "storm":
                wear += STORM_WEAR
            for r in self.rivers:
                if (
                    r["flood_ticks"] > 0
                    and self._river_dy(h.y, r["cy"]) <= r["hw"] + h.size * 0.5 + 2.0
                ):
                    wear += FLOOD_WEAR
            if wear > 0:
                h.hp -= wear
                if h.hp <= 0:
                    self._collapse_house(h)
        # repair & rubble clearing — builders within reach of a roof work it
        if cfg.structural_enabled or cfg.rubble_blocking_enabled:
            builders = [c for c in self._cached_creatures
                        if getattr(c, "personality", "") == "builder"]
            for c in builders:
                for h in houses:
                    dx, dy = self.world.delta(c.x, c.y, h.x, h.y)
                    reach = h.size * 0.5 + 3.0
                    if dx * dx + dy * dy > reach * reach:
                        continue
                    if h.is_ruin:
                        if cfg.rubble_blocking_enabled and h.rubble > 0:
                            h.rubble = max(0.0, h.rubble - 0.10)
                            c.energy = max(0.0, c.energy - 0.05)
                            if h.rubble == 0.0:
                                self.world.remove(h.id)  # lot cleared
                        break
                    if cfg.structural_enabled:
                        max_hp = MATERIAL_STATS.get(h.material, MATERIAL_STATS["wood"])["durability"]
                        if h.hp < max_hp:
                            h.hp = min(max_hp, h.hp + REPAIR_RATE)
                            c.energy = max(0.0, c.energy - 0.05)
                            break
            # §AQ PH-6 rubble auto-decay — ruins fade even without builders (1.5 seasons)
            # Prevents unbounded 7k-house blowup at 600k ticks (production 7782 houses).
            if cfg.rubble_blocking_enabled and self.tick % 10 == 0:
                for h in list(self.world.entities.values()):
                    if isinstance(h, House) and h.is_ruin and h.rubble > 0:
                        h.rubble = max(0.0, h.rubble - 0.08)
                        if h.rubble == 0.0:
                            self.world.remove(h.id)
            # hard cap: keep total houses (incl. ruins) < 400 to stay 60 Hz
            total_houses = sum(1 for e in self.world.entities.values() if isinstance(e, House))
            if total_houses > 400:
                # remove oldest ruins first (lowest id), batch 100/tick to avoid one slow tick
                ruins = sorted([e for e in self.world.entities.values() if isinstance(e, House) and e.is_ruin], key=lambda x: x.id)
                for r in ruins[: min(200, total_houses - 400)]:
                    self.world.remove(r.id)

    def _collapse_house(self, h: House) -> None:
        """A building whose structural HP is gone falls in (§AQ PH-6)."""
        h.is_ruin = True
        h.clan_id = 0
        h.clan_color = None
        h.hearth_lit = False
        h.hearth_fuel = 0.0
        if self.config.rubble_blocking_enabled:
            h.rubble = round(h.size, 2)  # blocks the lot until builders clear it
        self._emit_boom(h.x, h.y)
        self._emit(HistoryEvent(
            type="ruin", tick=self.tick + 1, entity_id=h.id,
            x=round(h.x, 2), y=round(h.y, 2),
            payload={"kind": "collapse", "material": h.material},
        ))

    # ------------------------------------------------- §AQ PH-8/9/10
    def _generate_anomalies(self) -> None:
        """§AQ PH-10: seed hidden zones where physics runs differently —
        fertile ground, heavy gravity, or calm air. Drawn from the dedicated
        geography rng; undiscovered until a skilled forager stumbles in."""
        count = max(0, int(self.config.anomaly_count))
        if count == 0:
            return
        geo_rng = random.Random((self.config.seed * 8191) ^ 0xA11A)
        kinds = ("fertile", "heavy", "calm")
        margin = 25.0
        for i in range(count):
            self.anomalies.append({
                "x": round(geo_rng.uniform(margin, self.config.width - margin), 2),
                "y": round(geo_rng.uniform(margin, self.config.height - margin), 2),
                "kind": kinds[i % len(kinds)],
                "discovered": False,
            })

    def _anomaly_at(self, x: float, y: float, kind: str | None = None) -> dict | None:
        for a in self.anomalies:
            if kind is not None and a["kind"] != kind:
                continue
            if self.world.distance_sq(x, y, a["x"], a["y"]) <= ANOMALY_RADIUS * ANOMALY_RADIUS:
                return a
        return None

    def _update_seismic(self) -> None:
        """§AQ PH-8: rare earthquakes — the tall castes feel the deep hum a
        few ticks early, then the ground moves: bodies are thrown, weakened
        roofs fall, and stone cracks open or thrusts up from below."""
        cfg = self.config
        if cfg.earthquake_enabled and self.pending_quake is None:
            if self.rng.random() < cfg.earthquake_rate:
                self.pending_quake = {
                    "x": self._rand_pos()[0],
                    "y": self._rand_pos()[1],
                    "mag": self.rng.uniform(4.0, 8.0),
                    "hit_tick": self.tick + QUAKE_WARN_TICKS + 1,
                    "warned": False,
                }
        q = self.pending_quake
        if q is None:
            return
        if not q["warned"] and self.tick >= q["hit_tick"] - QUAKE_WARN_TICKS:
            # Seismic early warning: Pentagons+ feel the vibration first and
            # raise the alarm — the clan heads for shelter before the shock.
            q["warned"] = True
            high_caste = ("Professional", "Noble", "Priest")
            for c in self._cached_creatures:
                if c.caste in high_caste and self.world.distance(
                    c.x, c.y, q["x"], q["y"]
                ) <= QUAKE_WARN_RADIUS:
                    c.panic_ticks = max(c.panic_ticks, 15)
                    if not c.emote:
                        c.emote = "panic"
                        c.emote_ticks = 12
            if len(self.signals) < SIGNALS_MAX:
                self.signals.append({
                    "x": round(q["x"], 2), "y": round(q["y"], 2),
                    "kind": "alarm", "sender": 0, "clan_id": None,
                    "ttl": 12, "born_tick": self.tick,
                })
            return
        if self.tick < q["hit_tick"]:
            return
        # The quake hits.
        self.pending_quake = None
        self._do_earthquake(q["x"], q["y"], q["mag"])

    def _do_earthquake(self, x: float, y: float, mag: float) -> None:
        radius = 12.0 + mag * 2.5
        for e in list(self.world.entities.values()):
            d = self.world.distance(e.x, e.y, x, y)
            if d > radius:
                continue
            falloff = 1.0 - d / radius
            if isinstance(e, Creature):
                ang = self.rng.uniform(0, 2 * math.pi)
                shove = QUAKE_DISPLACEMENT * (mag / 8.0) * falloff
                e.x, e.y = self.world.normalize(
                    e.x + math.cos(ang) * shove, e.y + math.sin(ang) * shove
                )
                dmg = QUAKE_DAMAGE * (mag / 8.0) * falloff
                if e.health - dmg <= 0:
                    self._kill(e, "earthquake")
                else:
                    e.health -= dmg
                    if not e.emote:
                        e.emote = "panic"
                        e.emote_ticks = 12
            elif isinstance(e, House) and not e.is_ruin:
                if self.config.structural_enabled:
                    if e.hp < 0:
                        e.hp = MATERIAL_STATS.get(e.material, MATERIAL_STATS["wood"])["durability"]
                    e.hp -= mag * 12.0 * falloff
                    if e.hp <= 0:
                        self._collapse_house(e)
                elif self.rng.random() < 0.25 * falloff:
                    self._collapse_house(e)
        # stone cracks open — or the ground thrusts new rock up
        for rock in list(self.rocks):
            if self.world.distance(rock["x"], rock["y"], x, y) > radius:
                continue
            roll = self.rng.random()
            if roll < QUAKE_ROCK_CRACK_CHANCE:
                self.rocks.remove(rock)  # a path opens
            elif roll < QUAKE_ROCK_CRACK_CHANCE + QUAKE_ROCK_SPAWN_CHANCE:
                if len(self.rocks) < 400:
                    ang = self.rng.uniform(0, 2 * math.pi)
                    self.rocks.append({
                        "x": self.world.normalize(
                            rock["x"] + math.cos(ang) * rock["r"] * 2.0, rock["y"]
                        )[0],
                        "y": rock["y"],
                        "r": max(1.5, rock["r"] * 0.7),
                    })
        self._cached_terrain_rocks = [dict(r) for r in self.rocks]
        self._emit_boom(x, y)
        self._emit(HistoryEvent(
            type="disaster", tick=self.tick + 1, entity_id=0,
            x=round(x, 2), y=round(y, 2),
            payload={"kind": "earthquake", "mag": round(mag, 1)},
        ))

    def _update_lightning(self) -> None:
        """§AQ PH-9: storms strike real bolts — instant death under the arc,
        fire where the ground burns, a briefly electrostatic fused rock."""
        cfg = self.config
        self.lightning = [b for b in self.lightning if b["ttl"] > 1]
        for b in self.lightning:
            b["ttl"] -= 1
        # electrostatic rocks decay back to plain stone
        for rock in [r for r in self.rocks if r.get("ttl") is not None]:
            rock["ttl"] -= 1
            if rock["ttl"] <= 0:
                self.rocks.remove(rock)
                self._cached_terrain_rocks = [dict(r) for r in self.rocks]
        if not (cfg.lightning_enabled and self.weather == "storm"):
            return
        if self.rng.random() >= cfg.lightning_strike_rate:
            return
        x, y = self._rand_pos()
        self.lightning.append({"x": round(x, 2), "y": round(y, 2), "ttl": LIGHTNING_BOLT_TTL})
        for e in self.world.query_radius(x, y, LIGHTNING_KILL_RADIUS):
            if isinstance(e, Creature) and e.id in self.world.entities:
                self._kill(e, "lightning")
            elif isinstance(e, Food) and e.id in self.world.entities:
                self.world.remove(e.id)
        if cfg.wildfire_enabled and self.rng.random() < 0.6:
            self.fires.append({"x": x, "y": y, "r": 2.5, "ttl": 24})
        elif not self._is_in_rock(x, y):
            self.rocks.append({"x": round(x, 2), "y": round(y, 2),
                               "r": 1.1, "ttl": LIGHTNING_ROCK_TTL})
            self._cached_terrain_rocks = [dict(r) for r in self.rocks]
        self._emit_boom(x, y)
        self._emit(HistoryEvent(
            type="disaster", tick=self.tick + 1, entity_id=0,
            x=round(x, 2), y=round(y, 2), payload={"kind": "lightning"},
        ))

    def _priest_pos_for(self, cid: int | None) -> tuple[float, float] | None:
        """The clan's living priest, for the bio-electric calm aura (§AQ PH-9)."""
        if not cid:
            return None
        cached = getattr(self, "_priest_pos", None)
        if cached is None:
            return None
        return cached.get(cid)

    def _totem_mult(self, cid: int | None) -> float:
        """§AQ PH-9: totem resonance — same-god allied shrines nearby amplify
        the aura, rival shrines too close interfere, anomalies empower."""
        if not cid:
            return 1.0
        cached = self._totem_mult_cache.get(cid)
        if cached is not None:
            return cached
        mult = 1.0
        shrine = self._shrine_pos(cid)
        my_totem = self.clans.get(cid, {}).get("totem")
        if shrine is not None:
            for other_id, info in self.clans.items():
                if other_id == cid:
                    continue
                other_shrine = self._shrine_pos(other_id)
                if other_shrine is None:
                    continue
                d = self.world.distance(shrine[0], shrine[1], other_shrine[0], other_shrine[1])
                if d > TOTEM_RIVAL_RADIUS:
                    continue
                score = self.relations.get(self._relation_pair(cid, other_id), 0)
                if info.get("totem") == my_totem and score >= self.config.alliance_threshold:
                    mult += TOTEM_RESONANCE_BONUS
                elif score <= self.config.rivalry_threshold:
                    mult *= TOTEM_RIVAL_DIM  # contested ground dims both
            # anomalies empower nearby shrines (known or not)
            for a in self.anomalies:
                if self.world.distance(shrine[0], shrine[1], a["x"], a["y"]) <= ANOMALY_RADIUS + 6.0:
                    mult *= ANOMALY_TOTEM_BONUS
                    break
        mult = min(TOTEM_RESONANCE_CAP, mult)
        self._totem_mult_cache[cid] = mult
        return mult

    def _update_anomaly_discovery(self) -> None:
        """§AQ PH-10: only exploration reveals an anomaly — a creature with
        sharp foraging senses (or an explorer's nose) who walks into one."""
        if not self.anomalies:
            return
        for c in self._cached_creatures:
            skill = c.skills.get("foraging", 0.0)
            if skill < ANOMALY_DISCOVER_SKILL and c.personality != "explorer":
                continue
            for a in self.anomalies:
                if a["discovered"]:
                    continue
                if self.world.distance_sq(c.x, c.y, a["x"], a["y"]) <= ANOMALY_RADIUS ** 2:
                    a["discovered"] = True
                    self._learn(c, "safe", a["x"], a["y"], conf=0.9)
                    self._emit(HistoryEvent(
                        type="anomaly", tick=self.tick + 1, entity_id=c.id,
                        caste=c.caste, x=round(a["x"], 2), y=round(a["y"], 2),
                        payload={"kind": a["kind"], "clan_id": c.clan_id},
                    ))

    def _update_law_wave(self) -> None:
        """§AQ PH-10: a law change sends a shimmer wave across the land; the
        old and the new law hang in the air for a transition window while the
        front sweeps west→east, and bodies inside the band feel the boundary
        pass through them (disorientation)."""
        if self.law_wave is None:
            return
        if self.tick - self.law_wave["born_tick"] > LAW_WAVE_TICKS:
            self.law_wave = None

    def _law_wave_front(self) -> float | None:
        if self.law_wave is None:
            return None
        p = (self.tick - self.law_wave["born_tick"]) / LAW_WAVE_TICKS
        return p * self.config.width

    def _update_builders(self) -> None:
        """§AQ PH-3: builder-personality creatures span the channels they live
        beside — planks first, dams when the water starts to rise."""
        if not self.rivers or not self._cached_creatures or self.tick % 15 != 0:
            return
        builders = [
            c for c in self._cached_creatures
            if (
                getattr(c, "personality", "") == "builder"
                or c.caste == "Artisan"
                or (isinstance(getattr(c, "skills", None), dict) and c.skills.get("foraging", 0.0) >= 10.0)
            )
            and c.energy > 35.0
        ]
        for b in builders:
            r = min(
                (rv for rv in self.rivers if self._river_dy(b.y, rv["cy"]) <= 24.0),
                key=lambda rv: self._river_dy(b.y, rv["cy"]),
                default=None,
            )
            if r is None:
                continue
            def _dx(ax: float, bx2: float) -> float:
                d = abs(ax - bx2)
                return min(d, self.config.width - d)
            near_crossing = any(
                _dx(b.x, br["x"]) <= 14.0 and br["cy"] == r["cy"]
                for br in self.bridges
            )
            rising = r["water"] > 0.5 or r["flood_ticks"] > 0
            has_dam = any(d["cy"] == r["cy"] for d in self.dams)
            if rising and not has_dam and len(self.dams) < 4:
                b.energy -= 15.0
                self.dams.append({"x": round(b.x, 2), "cy": r["cy"], "hp": DAM_HP})
                self._emit(HistoryEvent(
                    type="settlement", tick=self.tick + 1, entity_id=b.id, caste=b.caste,
                    x=round(b.x, 2), y=round(b.y, 2),
                    payload={"kind": "dam", "river_cy": r["cy"], "clan_id": b.clan_id},
                ))
                continue
            # Mend existing damaged bridge nearby
            repaired = False
            for br in self.bridges:
                if br["cy"] == r["cy"] and _dx(b.x, br["x"]) <= 18.0 and br["hp"] < BRIDGE_HP - 20:
                    br["hp"] = min(BRIDGE_HP, br["hp"] + 120)
                    b.energy -= 4.0
                    b.emote = "craft"
                    b.emote_ticks = 15
                    repaired = True
                    break
            if repaired:
                continue

            if not near_crossing and len(self.bridges) < 16:
                b.energy -= 10.0
                self.bridges.append({"x": round(b.x, 2), "cy": r["cy"], "hw": r["hw"], "hp": BRIDGE_HP})
                self._emit(HistoryEvent(
                    type="settlement", tick=self.tick + 1, entity_id=b.id, caste=b.caste,
                    x=round(b.x, 2), y=round(r["cy"], 2),
                    payload={"kind": "bridge", "river_cy": r["cy"], "clan_id": b.clan_id},
                ))

    # ------------------------------------------------ §AM living soil grid
    def _soil_index(self, x: float, y: float) -> int:
        col = min(self._soil_cols - 1, max(0, int(x / self.config.width * self._soil_cols)))
        row = min(self._soil_rows - 1, max(0, int(y / self.config.height * self._soil_rows)))
        return row * self._soil_cols + col

    def _soil_at(self, x: float, y: float) -> float:
        return self.soil_grid[self._soil_index(x, y)]

    def _deplete_soil(self, x: float, y: float, growth_gained: float) -> None:
        """Monocropping draws down the local fertility cell (§AM D.1)."""
        if not self.config.soil_depletion_enabled or growth_gained <= 0:
            return
        i = self._soil_index(x, y)
        self.soil_grid[i] = max(SOIL_MIN, self.soil_grid[i] - SOIL_DEPLETION_PER_GROWTH * growth_gained)

    def _fertilize_soil(self, x: float, y: float, radius: float, amount: float) -> None:
        """Compost, ash and the dead enrich every cell within radius (§AM D.2)."""
        cw = self.config.width / self._soil_cols
        ch = self.config.height / self._soil_rows
        c0 = max(0, int((x - radius) / cw)); c1 = min(self._soil_cols - 1, int((x + radius) / cw))
        r0 = max(0, int((y - radius) / ch)); r1 = min(self._soil_rows - 1, int((y + radius) / ch))
        for row in range(r0, r1 + 1):
            for col in range(c0, c1 + 1):
                qx = min(max(x, col * cw), (col + 1) * cw)
                qy = min(max(y, row * ch), (row + 1) * ch)
                if math.hypot(qx - x, qy - y) <= radius:
                    i = row * self._soil_cols + col
                    self.soil_grid[i] = min(SOIL_MAX, self.soil_grid[i] + amount)


    def distance(self, ax: float, ay: float, bx: float, by: float) -> float:
        """Proxy to world distance (convenience for tests)."""
        return self.world.distance(ax, ay, bx, by)

    def _inside_house(self, c: Creature, h: House | None) -> bool:
        if h is None or h.is_ruin:
            return False
        return (
            abs(c.x - h.x) < h.size / 2 - 0.3 and abs(c.y - h.y) < h.size / 2 - 0.3
        )

    def _is_inside_house(self, c: Creature, h: House | None) -> bool:
        """Geometric containment inside the four walls of house h."""
        if h is None or h.is_ruin:
            return False
        half = h.size * 0.5
        return abs(c.x - h.x) < half and abs(c.y - h.y) < half

    def _is_point_inside_any_house(self, x: float, y: float, pad: float = 0.5) -> bool:
        """Check if (x, y) falls inside any non-ruin house structure."""
        for e in self.world.entities.values():
            if isinstance(e, House) and not e.is_ruin:
                half = e.size * 0.5 + pad
                if abs(x - e.x) < half and abs(y - e.y) < half:
                    return True
        return False


    def _claim_bed(self, house: House) -> bool:
        """One bed per occupant until the house is full; creatures arrive in id order."""
        taken = self._beds.get(house.id, 0)
        if taken >= self._house_beds(house):
            return False
        self._beds[house.id] = taken + 1
        if hasattr(self, "_house_occupants"):
            self._house_occupants[house.id] = max(self._house_occupants.get(house.id, 0), self._beds[house.id])
        return True


    def _house_beds(self, house: House) -> int:
        """Beds scale with floor area: `house_capacity` is the law for an
        average 8×8 hall — smaller huts have fewer beds, and large houses
        are strictly capped at a maximum of 16 beds (HOUSE_MAX_BEDS)."""
        raw = int(self.config.house_capacity * (house.size * house.size) / HOUSE_REF_AREA)
        return max(1, min(HOUSE_MAX_BEDS, raw))


    # ------------------------------------------------------------------ setup
    def _rand_pos(self) -> tuple[float, float]:
        cfg = self.config
        return self.rng.uniform(0, cfg.width), self.rng.uniform(0, cfg.height)

    def _init_creature_evolution(
        self,
        c: Creature,
        parent_a: Creature | None = None,
        parent_b: Creature | None = None,
    ) -> None:
        """Initialize autonomous personality, skills, tools, and emote states."""
        # 1. Personality
        if parent_a and parent_b and self.rng.random() < 0.65:
            c.personality = self.rng.choice([parent_a.personality, parent_b.personality])
        else:
            c.personality = self.rng.choice(PERSONALITIES)

        # 2. Skills
        c.skills = {"farming": 0.0, "combat": 0.0, "foraging": 0.0, "healing": 0.0}
        if parent_a and parent_b:
            for k in c.skills:
                pa_xp = parent_a.skills.get(k, 0.0) if hasattr(parent_a, "skills") and isinstance(parent_a.skills, dict) else 0.0
                pb_xp = parent_b.skills.get(k, 0.0) if hasattr(parent_b, "skills") and isinstance(parent_b.skills, dict) else 0.0
                c.skills[k] = round(max(pa_xp, pb_xp) * 0.15, 1)

        # 3. Equipped item by caste/role
        if c.caste == "Soldier" or c.is_predator:
            c.equipped_item = "spear"
        elif c.caste == "Priest":
            c.equipped_item = "herb_poultice"
        elif c.caste in ("Woman", "Artisan", "Gentleman", "Herbivore"):
            c.equipped_item = "basket"
        else:
            c.equipped_item = None

        c.food_basket = 0
        c.title = None
        c.emote = None
        c.emote_ticks = 0
        c.waypoints = {}
        c.trust = {}
        if parent_a and hasattr(parent_a, "id"):
            c.trust[parent_a.id] = 30.0
        if parent_b and hasattr(parent_b, "id"):
            c.trust[parent_b.id] = 30.0


    def _spawn_creature(self, shape: str, sides: int) -> None:
        cfg = self.config
        x, y = self._rand_pos()
        iso = 60.0
        if sides == 3:
            # Founding Isosceles: somewhere on the long road toward 60 degrees.
            iso = self.rng.uniform(0.5, 59.5)
        caste = caste_name(sides, shape, iso)
        traits = traits_for(caste)
        c = Creature(
            shape=shape,
            sides=sides,
            iso_angle=iso,
            x=x,
            y=y,
            angle=self.rng.uniform(0, 2 * math.pi),
            speed=traits.speed,
            energy=cfg.energy_start,
            lifespan=traits.lifespan * cfg.lifespan_mult,
        )
        self._init_creature_evolution(c)
        self.world.add(c)

    def _spawn_predator(self) -> None:
        """Spawn a Carnivore predator (§I) — fast, no clan, hunts prey."""
        cfg = self.config
        x, y = self._rand_pos()
        traits = traits_for("Predator")
        c = Creature(
            shape="polygon",
            sides=6,
            iso_angle=60.0,
            caste="Predator",
            x=x,
            y=y,
            angle=self.rng.uniform(0, 2 * math.pi),
            speed=traits.speed,
            energy=cfg.energy_start,
            lifespan=traits.lifespan * cfg.lifespan_mult,
            is_predator=True,
            clan_id=0,
        )
        self._init_creature_evolution(c)
        self.world.add(c)

    def _spawn_herbivore(self) -> None:
        """Spawn a wild herbivore grazer (§O) — clanless, eats plants, hunted by predators."""
        cfg = self.config
        x, y = self._rand_pos()
        traits = traits_for("Herbivore")
        c = Creature(
            shape="polygon",
            sides=4,
            iso_angle=60.0,
            caste="Herbivore",
            x=x,
            y=y,
            angle=self.rng.uniform(0, 2 * math.pi),
            speed=traits.speed,
            energy=cfg.energy_start,
            lifespan=traits.lifespan * cfg.lifespan_mult,
            is_herbivore=True,
            clan_id=0,
        )
        self._init_creature_evolution(c)
        self.world.add(c)

    def _spawn_initial(self) -> None:
        cfg = self.config
        area = cfg.width * cfg.height

        # Founding generation scale with the map unless explicitly pinned.
        total = (
            self._jittered(area * cfg.creature_density) if cfg.num_triangles < 0 else 0
        )
        # Flatland's social pyramid: many soldiers and women, few nobles.
        shares = {
            "triangles": 0.30,
            "women": 0.25,
            "squares": 0.18,
            "pentagons": 0.12,
            "hexagons": 0.09,
            "priests": 0.06,
        }
        n_triangles = self._count(cfg.num_triangles, shares["triangles"], total)
        n_squares = self._count(cfg.num_squares, shares["squares"], total)
        n_pentagons = self._count(cfg.num_pentagons, shares["pentagons"], total)
        n_hexagons = self._count(cfg.num_hexagons, shares["hexagons"], total)
        n_priests = self._count(cfg.num_priests, shares["priests"], total)
        n_women = self._count(cfg.num_women, shares["women"], total)

        for _ in range(n_triangles):
            self._spawn_creature("polygon", 3)
        for _ in range(n_squares):
            self._spawn_creature("polygon", 4)
        for _ in range(n_pentagons):
            self._spawn_creature("polygon", 5)
        for _ in range(n_hexagons):
            self._spawn_creature("polygon", 6)
        for _ in range(n_priests):
            self._spawn_creature("polygon", PRIEST_SIDES)
        for _ in range(n_women):
            self._spawn_creature("line", 2)
        max_radius = max(
            (c.radius for c in self.world.creatures()), default=DEFAULT_RADIUS
        )
        n_houses = (
            self._jittered(area * cfg.house_density)
            if cfg.num_houses < 0
            else cfg.num_houses
        )
        for _ in range(n_houses):
            size = self.rng.uniform(cfg.house_min_size, cfg.house_max_size)
            x, y = self._rand_house_pos(size)
            door_width = min(size * 0.8, 2.0 * max_radius * cfg.door_clearance)
            self.world.add(
                House(
                    x=x,
                    y=y,
                    size=size,
                    door_width=door_width,
                    door_side=self.rng.choice(("north", "east", "south", "west")),
                    material=self._pick_house_material(x, y),
                )
            )
        for _ in range(cfg.food_count):
            x, y = self._food_pos()
            # World-spawned plants arrive mature: the food law promises harvest.
            self.world.add(self._new_food(x, y, growth=1.0))
        self._found_founding_clans()
        # Predators (§I) — spawn after clans so they don't get a clan crest; only if auto-scaling
        if cfg.predation_enabled and cfg.predator_ratio > 0 and cfg.num_triangles < 0:
            n_predators = self._jittered(area * cfg.creature_density * cfg.predator_ratio)
            for _ in range(n_predators):
                self._spawn_predator()
        # Herbivores (§O) — wild grazers, clanless, compete for plants and feed predators
        if cfg.beast_ratio > 0 and cfg.num_triangles < 0:
            n_herbivores = self._jittered(area * cfg.creature_density * cfg.beast_ratio)
            for _ in range(n_herbivores):
                self._spawn_herbivore()

    def _new_clan(self, founder: Creature | None) -> int:
        """Register a clan: seeded name/totem/culture/specialization (no house yet)."""
        cid = self._next_clan_id
        self._next_clan_id += 1
        # Procedural name: deterministic adj+noun from seed+cid (no rng consumption to keep determinism)
        adj = CLAN_ADJECTIVES[(cid * 13 + self.config.seed) % len(CLAN_ADJECTIVES)]
        noun = CLAN_NOUNS[(cid * 29 + self.config.seed) % len(CLAN_NOUNS)]
        if (cid * 7 + self.config.seed) % 10 < 3:
            name = f"Clan of the {adj} {noun}"
        else:
            name = f"{adj} {noun}"
        totem = None
        if self.config.totems_enabled:
            # §AP: the clan's avatar — a sacred 2D projection of the Sphere,
            # assigned procedurally at founding (deterministic, no rng).
            totem = AVATARS[(cid * 17 + self.config.seed) % len(AVATARS)]
        # specialization drift start — totem biases initial role.
        # COPY: TOTEM_SPEC entries are mutated in place by drift; sharing them
        # across clans (or worlds!) would couple their specializations.
        spec = dict(TOTEM_SPEC.get(totem, {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34}))
        culture = f"{CULTURE_ADJECTIVES[(cid * 11 + self.config.seed) % len(CULTURE_ADJECTIVES)]} {CULTURE_NOUNS[(cid * 19 + self.config.seed) % len(CULTURE_NOUNS)]}"
        # Governance archetype (§AL)
        if founder and founder.caste in ("Gentleman", "Noble"):
            governance = "monarchy"
        elif founder and founder.caste == "Priest":
            governance = "theocracy"
        elif founder and founder.caste == "Soldier":
            governance = "junta"
        else:
            governance = "republic"

        founder_name = personal_name_for(founder.id, self.config.seed, founder.generation) if founder is not None else None


        self.clans[cid] = {
            "name": name,
            "founder_id": founder.id if founder is not None else None,
            "born_tick": self.tick,
            "color": CLAN_COLORS[(cid - 1) % len(CLAN_COLORS)],
            "totem": totem,
            "leader_id": founder.id if founder is not None else None,
            "governance": governance,
            "bylaws": {
                "rationing": False,
                "martial_law": False,
                "sanctuary": "open",
            },
            "task_board": {
                "priority": "balanced",
                "harvester_weight": 1.0,
                "guard_weight": 1.0,
            },
            "specialization": spec,
            "culture": culture,
            "culture_id": cid,
            "coalition_id": None,
            "larder": 0.0,
            # §AM: the clan granary — grain & cured rations kept against winter
            "granary": 0.0,
            "harvest_total": 0.0,
            "feast_until": 0,
            # §AN: acoustic dialect — drifts apart for isolated clans
            "dialect": 0.0,
            "tribute_to": None,
            "main_house_id": None,
            # §AP theology: clan faith pool + shrine level (0 none, 1 shrine, 2 temple)
            "faith": 0.0,
            "shrine_level": 0,
            "history": [
                {
                    "tick": self.tick,
                    "day": self.day,
                    "event": "founded",
                    "desc": f"Founded as {governance.capitalize()} by {founder_name or f'Leader #{founder.id}' if founder else 'Settlers'} (Day {self.day})",
                }
            ],
        }
        return cid


    def _log_clan_history(self, cid: int, event_type: str, desc: str) -> None:
        """AK: Record major historical milestones for a clan.

        §AN: the great days are also painted on the main house walls by
        the clan's artisans — a mural per milestone, visible to god.
        """
        clan = self.clans.get(cid)
        if not clan:
            return
        if "history" not in clan or not isinstance(clan["history"], list):
            clan["history"] = []
        clan["history"].append({
            "tick": self.tick,
            "day": self.day,
            "event": event_type,
            "desc": desc,
        })
        if len(clan["history"]) > 30:
            clan["history"].pop(0)
        # §AN murals — succession, conquest, feasts & temples earn a painting
        if event_type in ("leader_change", "hq_relocated", "takeover",
                          "war_declared", "festival", "banquet", "temple"):
            hid = clan.get("main_house_id")
            house = self.world.entities.get(hid) if hid is not None else None
            if isinstance(house, House):
                house.murals += 1

    def _set_main_house_for_clan(self, cid: int, house: House) -> None:
        """AK: Ensure strictly ONE main house per clan across entities and metadata."""
        if not cid or cid not in self.clans:
            return
        prev_hid = self.clans[cid].get("main_house_id")
        self.clans[cid]["main_house_id"] = house.id
        for e in self.world.entities.values():
            if isinstance(e, House) and e.clan_id == cid and not e.is_ruin:
                e.is_main = (e.id == house.id)
        # §AN: the clan raises a boundary stone on its border — trespassers ring it.
        if self.config.envoys_enabled and not any(s["clan_id"] == cid for s in self.boundary_stones):
            r = self.config.territory_radius
            for k in range(3):  # deterministic angles; first clear spot wins
                ang = (cid * 2.399 + k * 2.094) % (2 * math.pi)
                sx, sy = self.world.normalize(house.x + math.cos(ang) * r,
                                              house.y + math.sin(ang) * r)
                if not self._is_in_rock(sx, sy):
                    self.boundary_stones.append({"x": round(sx, 2), "y": round(sy, 2), "clan_id": cid})
                    break
        if prev_hid != house.id:
            self._log_clan_history(
                cid,
                "hq_relocated",
                f"Headquarters established at House #{house.id} ({house.x:.0f}, {house.y:.0f})",
            )


    def _functional_houses(self) -> list[House]:
        """Non-ruin houses in id order — the possible settlement anchors (§V).

        AF: fast-path returns the per-tick cache (sorted by id) when available.
        Falls back to full entity scan during initialization (pre-first-refresh).
        """
        if self._cached_houses:
            return self._cached_houses
        # Fallback: initialization or outside-tick context (e.g. _spawn_initial)
        return sorted(
            [e for e in self.world.entities.values() if isinstance(e, House) and not e.is_ruin],
            key=lambda h: h.id,
        )

    def _nearest_house_to(self, x: float, y: float, houses: list[House]) -> House | None:
        """Wrap-aware nearest house; ties broken by lower house id (deterministic)."""
        if not houses:
            return None
        return min(houses, key=lambda h: (self.world.distance(x, y, h.x, h.y), h.id))

    def _clan_centroid(self, members: list[Creature]) -> tuple[float, float]:
        n = max(1, len(members))
        return sum(m.x for m in members) / n, sum(m.y for m in members) / n

    def _totem_of(self, c: Creature) -> str | None:
        if not self.config.totems_enabled or not c.clan_id:
            return None
        return self.clans.get(c.clan_id, {}).get("totem")

    def _totem_stat(self, c: Creature, key: str) -> float:
        """Fast pre-cached totem-buff lookup (§AY M-2)."""
        if not c.clan_id or not self.config.totems_enabled:
            return 0.0
        stats = getattr(self, "_clan_totem_stats", None)
        if stats is not None and c.clan_id in stats:
            return stats[c.clan_id].get(key, 0.0)
        base = float(TOTEM_BUFF.get(self._totem_of(c), {}).get(key, 0.0))
        power = float(getattr(self, "_totem_power", {}).get(c.clan_id, 1.0))
        return base * self._totem_mult(c.clan_id) * power

    def _found_founding_clans(self) -> None:
        """§V Settlement seeding — every functional house anchors one clan and each
        founding creature joins its nearest house's clan, so soldiers, women,
        nobles and priests mix inside a settlement. `max_clans` caps society
        granularity: -1 = one clan per house; N ≥ 1 clusters the founders into
        exactly N spatial clans instead (greedy k-centre). Deterministic given
        the seed — never touches the rng."""
        cfg = self.config
        founders = sorted(self.world.creatures(), key=lambda c: c.id)
        if not founders:
            return
        houses = self._functional_houses()
        taken_leaders: set[int] = set()

        def found(members: list[Creature], anchor: House | None) -> int:
            leader: Creature | None = None
            pool = [m for m in members if m.id not in taken_leaders]
            if members and not pool:
                pool = list(members)  # more settlements than founders: share leaders
            if pool:
                if anchor is not None:
                    leader = min(
                        pool,
                        key=lambda c: (self.world.distance(c.x, c.y, anchor.x, anchor.y), c.id),
                    )
                else:
                    ax, ay = self._clan_centroid(members)
                    leader = min(pool, key=lambda c: (self.world.distance(c.x, c.y, ax, ay), c.id))
            if leader is not None:
                taken_leaders.add(leader.id)
            cid = self._new_clan(leader)
            for m in members:
                m.clan_id = cid
            return cid

        if cfg.max_clans >= 0:
            k = min(cfg.max_clans, len(founders))
            for members in self._cluster_founders_kcenter(founders, k) if k > 0 else []:
                found(members, None)
            # Anchor claims: each clan settles at the free house nearest its people.
            self._anchor_homeless_clans(sorted(self.clans.keys()))
        elif houses:
            buckets: dict[int, list[Creature]] = {h.id: [] for h in houses}
            for c in founders:
                home = self._nearest_house_to(c.x, c.y, houses)
                buckets[home.id].append(c)
            for h in houses:
                cid = found(buckets[h.id], h)
                if cfg.house_claim_enabled:
                    h.clan_id = cid
                    h.clan_color = self.clans[cid]["color"]
                    self._set_main_house_for_clan(cid, h)
        # No houses and no cap: roofless founders stay clanless — a settlement
        # defines a clan (§V); clans rise later from the generations.

    def _cluster_founders_kcenter(self, founders: list[Creature], k: int) -> list[list[Creature]]:
        """Greedy k-centre over the founding generation (deterministic, rng-free).

        First centre is the founder nearest the world's heart; each next centre
        is the founder farthest from every chosen centre (ties → lowest id).
        Membership goes to the nearest centre (ties → earliest centre)."""
        w = self.world
        cx, cy = self.config.width / 2, self.config.height / 2
        centres = [min(founders, key=lambda c: (w.distance(c.x, c.y, cx, cy), c.id))]
        while len(centres) < k:
            rest = [c for c in founders if all(c.id != ct.id for ct in centres)]
            if not rest:
                break
            nxt = max(
                rest,
                key=lambda c: (min(w.distance(c.x, c.y, ct.x, ct.y) for ct in centres), -c.id),
            )
            centres.append(nxt)
        groups: list[list[Creature]] = [[] for _ in centres]
        for c in founders:
            best_i, best_d = 0, math.inf
            for i, ct in enumerate(centres):
                d = w.distance(c.x, c.y, ct.x, ct.y)
                if d < best_d:
                    best_i, best_d = i, d
            groups[best_i].append(c)
        return [g for g in groups if g]

    def _anchor_homeless_clans(self, clan_ids: list[int]) -> None:
        """§V anchor claims — greedy matching over (clan, house) pairs by distance:
        every homeless clan settles at its nearest free house, each house hosts at
        most one clan. Clans left over (housing shortage) found a new settlement
        via `_claim_house_for_clan` (which respects pinned `num_houses`)."""
        if not self.config.house_claim_enabled:
            return
        houses = [h for h in self._functional_houses() if h.clan_id == 0]
        if not houses:
            for cid in clan_ids:
                self._claim_house_for_clan(cid)
            return
        pairs: list[tuple[float, int, int]] = []
        for cid in sorted(clan_ids):
            members = [c for c in self.world.creatures() if c.clan_id == cid]
            if not members:
                continue
            ax, ay = self._clan_centroid(members)
            for h in houses:
                pairs.append((self.world.distance(ax, ay, h.x, h.y), cid, h.id))
        claimed: set[int] = set()
        houses_by_id = {h.id: h for h in houses}
        for _, cid, hid in sorted(pairs):
            if cid in claimed or hid in claimed:
                continue
            claimed.add(cid)
            claimed.add(hid)
            h = houses_by_id[hid]
            h.clan_id = cid
            h.clan_color = self.clans[cid]["color"]
            if not self.clans[cid].get("main_house_id"):
                self._set_main_house_for_clan(cid, h)
            else:
                h.is_main = False
        # clans without a free house: build a settlement when unpinned (§L)
        # (ghost clans with no living members never build)
        for cid in sorted(clan_ids):
            if not any(h.clan_id == cid for h in self._functional_houses()):
                if any(c.clan_id == cid for c in self.world.creatures()):
                    self._claim_house_for_clan(cid)

    def _prune_extinct_clans(self) -> None:
        """§P0: archive clans with 0 living members and 0 owned functional houses.
        Runs every 100 ticks; keeps relations/_clan_members/farm_plots/banquet_last bounded."""
        if self.tick % 100 != 0 or not self.clans:
            return
        # §AX: use fresh world scan — cached _clan_members is stale for clans
        # minted during the current tick's creature loop (e.g. exile bands).
        alive_cids = {c.clan_id for c in self.world.creatures() if c.clan_id}
        owned = {h.clan_id for h in self._functional_houses() if h.clan_id}
        extinct = [cid for cid in list(self.clans.keys()) if cid not in alive_cids and cid not in owned]
        if not extinct:
            return
        extinct_set = set(extinct)
        for cid in extinct:
            del self.clans[cid]
            self._clan_members.pop(cid, None)
            self.farm_plots.pop(cid, None) if hasattr(self, 'farm_plots') else None
            self._banquet_last.pop(cid, None) if hasattr(self, '_banquet_last') else None
            self.clans.pop(cid, None)  # idempotent
        # clean relations involving extinct clans
        for pair in list(self.relations.keys()):
            if pair[0] in extinct_set or pair[1] in extinct_set:
                del self.relations[pair]
        for pair in list(getattr(self, '_declared_wars', {}).keys()):
            if pair[0] in extinct_set or pair[1] in extinct_set:
                del self._declared_wars[pair]

    def _assign_house_claims(self) -> None:
        """§V Anchor claims — each homeless clan settles at the free house nearest
        its people (never round-robin): a clan's settlement IS its nearest house."""
        if not self.config.house_claim_enabled:
            return
        houses = self._functional_houses()
        # Clear stale claims from previous world generation / disabled period
        for h in houses:
            if h.clan_id and h.clan_id not in self.clans:
                h.clan_id = 0
                h.clan_color = None
                h.is_main = False
        # Clans that already own at least one house keep their claimed settlement
        claimed_clans = {h.clan_id for h in houses if h.clan_id}
        # §P0: only living clans can be homeless — dead entries bloat settlement ticks
        living = set(self._clan_members.keys()) if self._clan_members else {c.clan_id for c in self._get_creatures() if c.clan_id}
        homeless = [cid for cid in living if cid not in claimed_clans]
        if not homeless:
            return
        self._anchor_homeless_clans(homeless)

    def _claim_house_for_clan(self, clan_id: int) -> None:
        """Claim nearest free house for homeless clan or found a new settlement (§V)."""
        houses = self._functional_houses()
        members = [c for c in self.world.creatures() if c.clan_id == clan_id]
        free = [h for h in houses if h.clan_id == 0]
        if free and members:
            ax, ay = self._clan_centroid(members)
            h = self._nearest_house_to(ax, ay, free)
            h.clan_id = clan_id
            h.clan_color = self.clans.get(clan_id, {}).get("color")
            if not self.clans.get(clan_id, {}).get("main_house_id"):
                self._set_main_house_for_clan(clan_id, h)
            else:
                h.is_main = False
            return
        # No free house: a new clan founds a new settlement (§L settlement economy)
        # But respect explicit overrides: tests/scenarios that pin num_houses keep housing shortage
        if self.config.shelter_enabled and self.config.num_houses < 0:
            founder = min(members, key=lambda c: (-c.age, c.id)) if members else None
            self._spawn_settlement_house(clan_id, near=founder)

    def _refresh_house_claims(self) -> None:
        """Sync house crests with the current law (enable/disable)."""
        houses = self._functional_houses()
        if not self.config.house_claim_enabled:
            for h in houses:  # type: ignore[union-attr]
                h.clan_id = 0
                h.clan_color = None
                h.is_main = False
        else:
            self._assign_house_claims()

    # ------------------------------------------------------- settlement economy
    def _target_house_count(self) -> int:
        """Houses scale with map area and population to guarantee >=85% shelter coverage."""
        cfg = self.config
        if cfg.num_houses >= 0:
            return cfg.num_houses
        area = cfg.width * cfg.height
        density_base = round(area * max(cfg.house_density, 0.00055))
        # Ensure enough beds for >= 85% of carrying capacity or active population
        creatures = getattr(self, "_cached_creatures", None)
        pop = len(creatures) if creatures is not None else 100
        target_pop = max(pop, cfg.carrying_capacity if cfg.carrying_capacity > 0 else 100)
        beds_needed = int(target_pop * 0.85)
        # Average beds per house based on mean house size 6.8
        avg_beds = max(1.0, cfg.house_capacity * (6.8 * 6.8) / HOUSE_REF_AREA)
        houses_for_85pct = max(1, math.ceil(beds_needed / avg_beds))
        return max(density_base, houses_for_85pct)

    def _spawn_settlement_house(self, clan_id: int | None = None, near: Creature | None = None) -> House:
        """Spawn a new house — near a clan founder if given, else random; claim it if clan_id."""
        cfg = self.config
        max_radius = max(
            (c.radius for c in self._get_creatures()), default=DEFAULT_RADIUS
        )
        size = self.rng.uniform(cfg.house_min_size, cfg.house_max_size)
        x, y = self._find_non_overlapping_house_pos(size, near=near)
        door_width = min(size * 0.8, 2.0 * max_radius * cfg.door_clearance)
        house = House(
            x=x, y=y, size=size, door_width=door_width,
            door_side=self.rng.choice(("north", "east", "south", "west")),
            material=self._pick_house_material(x, y),
        )
        if clan_id is not None and self.config.house_claim_enabled:
            house.clan_id = clan_id
            house.clan_color = self.clans.get(clan_id, {}).get("color")
            if not self.clans.get(clan_id, {}).get("main_house_id"):
                self._set_main_house_for_clan(clan_id, house)
            else:
                house.is_main = False
        self.world.add(house)
        # Clear any wild plants on the new house foundation
        for fid in [
            e.id for e in self.world.entities.values()
            if e.kind == "food" and abs(e.x - x) < size * 0.5 + 0.5 and abs(e.y - y) < size * 0.5 + 0.5
        ]:
            self.world.remove(fid)
        self._emit(
            HistoryEvent(
                type="settlement", tick=self.tick + 1, entity_id=house.id,
                x=round(house.x, 2), y=round(house.y, 2),
                payload={"clan_id": clan_id, "size": round(size, 2)},
            )
        )
        return house

    def _try_house_takeover(self, cid: int, members: list[Creature], houses: list[House]) -> House | None:
        """§AT-2 Clan Invasion & Resource War — a desperate or growing clan lacking
        shelter or food invades a rival's settlement to secure shelter and plunder supplies.
        Conditions:
          - The invading clan has insufficient beds (len(members) > total_beds) or food shortages.
          - Targets the closest rival house; if undefended or if invader has military superiority,
            seizes the roof and plunders the rival's granary/larder for the starving population.
        Deterministic: nearest to clan centroid, ties by id."""
        if not self.config.house_claim_enabled or not members:
            return None
        ax, ay = self._clan_centroid(members)
        candidates: list[House] = []
        occupants = getattr(self, "_house_occupants", {})
        for h in houses:
            if h.is_ruin or h.clan_id == 0 or h.clan_id == cid:
                continue
            _tt = getattr(h, "takeover_tick", -9999)
            if _tt >= 0 and self.tick - _tt < 600:
                # 600 tick garrison immunity prevents immediate ping-pong takeovers
                continue
            if self.clans.get(h.clan_id, {}).get("main_house_id") == h.id:
                # Main seat protected — the clan seat is never taken (law preserved)
                continue
            rival_members = self._clan_members.get(h.clan_id, [])
            rival_beds = sum(self._house_beds(rh) for rh in houses if rh.clan_id == h.clan_id and not rh.is_ruin)
            # Invade if house is empty tonight and (rival has spare beds or invader has superiority)
            # Law: spare = rival population < half its beds (otherwise they need it)
            is_spare = len(rival_members) * 2 < rival_beds
            has_superiority = len(members) >= len(rival_members)
            is_empty_tonight = occupants.get(h.id, 0) == 0
            if is_empty_tonight and (is_spare or has_superiority):
                candidates.append(h)
        if not candidates:
            return None
        target = min(candidates, key=lambda h: (self.world.distance(ax, ay, h.x, h.y), h.id))
        old_cid = target.clan_id
        target.clan_id = cid
        target.clan_color = self.clans.get(cid, {}).get("color")
        target.is_main = False
        target.takeover_tick = self.tick

        # Plunder food resources from the victim clan to feed the invaders
        victim_info = self.clans.get(old_cid, {})
        invader_info = self.clans.get(cid, {})
        plundered = 0.0
        if victim_info:
            v_granary = float(victim_info.get("granary", 0.0))
            if v_granary > 5.0:
                plundered = min(50.0, v_granary * 0.6)
                victim_info["granary"] = max(0.0, v_granary - plundered)
                if invader_info:
                    invader_info["granary"] = float(invader_info.get("granary", 0.0)) + plundered
                    # Distribute food to feed hungry clan invaders immediately
                    for m in members:
                        if m.energy < 75.0:
                            m.energy = min(100.0, m.energy + 25.0)

        # The rival loses a roof and remembers the theft.
        self._bump_relation(cid, old_cid, -40)
        old_name = self.clans.get(old_cid, {}).get("name", f"Clan #{old_cid}")
        new_name = self.clans.get(cid, {}).get("name", f"Clan #{cid}")
        raid_desc = f" (plundered {plundered:.1f} food)" if plundered > 0 else ""
        self._log_clan_history(
            cid, "takeover",
            f"Invaded & seized House #{target.id} from {old_name}{raid_desc} (Day {self.day})",
        )
        self._log_clan_history(
            old_cid, "takeover_loss",
            f"Lost House #{target.id} to {new_name}{raid_desc} (Day {self.day})",
        )
        self._emit(
            HistoryEvent(
                type="takeover", tick=self.tick + 1, entity_id=target.id,
                x=round(target.x, 2), y=round(target.y, 2),
                payload={
                    "invader_clan": cid, "victim_clan": old_cid,
                    "invader_name": new_name, "victim_name": old_name,
                    "house_id": target.id, "plundered_food": round(plundered, 1),
                },
            )
        )
        return target

    def _update_settlements(self) -> None:
        """Settlement economy tick: grow to meet demand, crumble abandoned houses (§L)."""
        cfg = self.config
        if not cfg.shelter_enabled:
            return
        functional = self._functional_houses()
        # §AT-3 orphan audit runs every settlement tick — claims hygiene first.
        self._audit_house_claims(functional)
        # Respect explicit overrides: pinned scenarios (tests) keep exact housing
        if cfg.num_houses >= 0:
            return
        # — growth: replenish houses when ruined/shortage, paced every 100 ticks —
        target = self._target_house_count()
        if len(functional) < target and (self.tick % 100 == 0):
            self._spawn_settlement_house()
        # §AO Phase E: bed overflow last night is urgent social demand —
        # builders raise an emergency roof even at the density target.
        if (
            getattr(self, "_last_night_overflow", 0) >= BED_OVERFLOW_BUILD_THRESHOLD
            and self.tick % 50 == 0
        ):
            self._last_night_overflow = 0
            if len(functional) < int(target * 1.5):
                self._spawn_settlement_house()

        # — clan expansion: growing clans claim free houses, seize weak rivals'
        #    spares (§AT-2) or build new ones —
        if self.config.house_claim_enabled and (self.tick % 50 == 0):
            living_members_by_clan: dict[int, list[Creature]] = {}
            for c in self._get_creatures():
                if c.clan_id:
                    living_members_by_clan.setdefault(c.clan_id, []).append(c)

            for cid, members in living_members_by_clan.items():
                clan_houses = [h for h in functional if isinstance(h, House) and h.clan_id == cid]
                total_beds = sum(self._house_beds(h) for h in clan_houses)

                # Ensure the clan has strictly ONE designated main house
                if clan_houses:
                    main_hid = self.clans.get(cid, {}).get("main_house_id")
                    if not any(h.id == main_hid for h in clan_houses):
                        main_h = max(clan_houses, key=lambda h: h.size)
                        self._set_main_house_for_clan(cid, main_h)
                    else:
                        for h in clan_houses:
                            h.is_main = (h.id == main_hid)

                # If clan population outgrows beds: claim nearby free house,
                # then invade a weak rival's empty spare (§AT-2), then build.
                if len(members) > total_beds:
                    ax, ay = self._clan_centroid(members)
                    unclaimed = [h for h in functional if isinstance(h, House) and h.clan_id == 0]
                    claimed_free = False
                    if unclaimed:
                        nearest_free = self._nearest_house_to(ax, ay, unclaimed)
                        max_d = cfg.territory_radius * 2.0 if cfg.territory_enabled else 60.0
                        if self.world.distance(ax, ay, nearest_free.x, nearest_free.y) <= max_d:
                            nearest_free.clan_id = cid
                            nearest_free.clan_color = self.clans[cid]["color"]
                            nearest_free.is_main = False
                            claimed_free = True
                    if not claimed_free:
                        invaded = self._try_house_takeover(cid, members, [h for h in functional if isinstance(h, House)])
                        if invaded is None and cfg.num_houses < 0 and len(functional) < target * 1.5:
                            rand_m = self.rng.choice(members)
                            exp_house = self._spawn_settlement_house(cid, near=rand_m)
                            exp_house.is_main = False

        # — decay: abandoned houses crumble to ruins —
        # Build living-clan set once
        living_clans = {c.clan_id for c in self._get_creatures() if c.clan_id}
        for h in list(functional):
            assert isinstance(h, House)
            # A house is abandoned if unclaimed, or its clan has no living members
            is_abandoned = (h.clan_id == 0) or (h.clan_id not in living_clans)
            if is_abandoned:
                h.abandoned_ticks = (getattr(h, "abandoned_ticks", 0) or 0) + 1
            else:
                h.abandoned_ticks = 0
            if h.abandoned_ticks >= cfg.house_decay_ticks:
                h.is_ruin = True
                h.clan_id = 0
                h.clan_color = None
                h.is_main = False
                # §AN B.3: ruins exhale an old danger — keep the young away,
                # and let explorers dig lost knowledge from the stones.
                if cfg.scent_enabled and len(self.signals) < SIGNALS_MAX:
                    self.signals.append({
                        "x": round(h.x, 2), "y": round(h.y, 2), "kind": "danger_scent",
                        "sender": h.id, "clan_id": None, "born_tick": self.tick, "ttl": DANGER_SCENT_TTL * 3,
                    })
                self._emit(
                    HistoryEvent(
                        type="ruin", tick=self.tick + 1, entity_id=h.id,
                        x=round(h.x, 2), y=round(h.y, 2),
                        payload={"abandoned_ticks": h.abandoned_ticks},
                    )
                )

    def _audit_house_claims(self, houses: list[House] | None = None) -> None:
        """§AT-3 orphan-house cleanup — a claim whose clan is missing or has no
        living member is cleared immediately so no house ends a tick owned by
        a ghost; the roof then decays as abandoned through the usual §L path."""
        if houses is None:
            houses = self._functional_houses()
        living: set[int] | None = None
        for h in houses:
            if not h.clan_id:
                continue
            if h.clan_id not in self.clans:
                stale = True
            else:
                if living is None:
                    living = {c.clan_id for c in self._get_creatures() if c.clan_id}
                stale = h.clan_id not in living
            if stale:
                # Re-point the clan's seat before wiping, so main_house_id
                # never dangles on a house the clan no longer owns.
                info = self.clans.get(h.clan_id)
                if info is not None and info.get("main_house_id") == h.id:
                    others = [
                        o for o in houses
                        if o.clan_id == h.clan_id and o.id != h.id and not o.is_ruin
                    ]
                    info["main_house_id"] = max(others, key=lambda o: o.size).id if others else None
                h.clan_id = 0
                h.clan_color = None
                h.is_main = False

    def _house_for(self, c: Creature, houses: list[Entity]) -> House | None:
        """Preferred shelter: the clan's own roofs while they have beds free;
        the clan leader resides and prioritizes the MAIN house; other kin
        spread across all clan houses.

        §AT-2/AT-3 hard exclusivity: a creature sleeps only under its own
        clan's roof (or an unclaimed roof). Foreign houses are never entered —
        one house, one clan — so rival bodies can't poison occupancy caps.
        When every eligible roof is full the creature queues at home instead."""
        if not houses:
            return None

        def dist_sq(h: House) -> float:
            return self.world.distance_sq(c.x, c.y, h.x, h.y)

        def has_room(h: House) -> bool:
            occ = max(getattr(self, "_house_occupants", {}).get(h.id, 0), self._beds.get(h.id, 0))
            if self._inside_house(c, h):
                occ = max(0, occ - 1)
            return occ < self._house_beds(h)

        def allowed(h: House) -> bool:
            return not self.config.house_claim_enabled or h.clan_id == 0 or h.clan_id == c.clan_id

        if getattr(c, "waypoints", None) and "home" in c.waypoints:
            hx, hy = c.waypoints["home"]
            h_pos_map = getattr(self, "_house_by_pos", None)
            h = h_pos_map.get((hx, hy)) if h_pos_map else None
            if h is not None and not h.is_ruin and allowed(h) and has_room(h):
                return h

        if self.config.house_claim_enabled and c.clan_id:
            clan_info = self.clans.get(c.clan_id, {})
            leader_id = clan_info.get("leader_id")
            main_hid = clan_info.get("main_house_id")

            own_houses = getattr(self, "_houses_by_clan", {}).get(c.clan_id, [])
            if own_houses:
                # Leader prioritizes living in the main house
                if c.id == leader_id:
                    main_house = next((h for h in own_houses if h.id == main_hid or getattr(h, "is_main", False)), own_houses[0])
                    if has_room(main_house):
                        return main_house

                # Members (or leader if main house full) choose nearest own house with room
                own_free = [h for h in own_houses if has_room(h)]
                if own_free:
                    return min(own_free, key=dist_sq)

            # All own roofs full (or none): spill to the nearest UNCLAIMED roof
            # with space — never into another clan's house (§AT-2/AT-3).
            unclaimed = getattr(self, "_unclaimed_houses", None)
            if unclaimed is None:
                unclaimed = [h for h in houses if isinstance(h, House) and not h.is_ruin and h.clan_id == 0]
            free = [h for h in unclaimed if has_room(h)]
            if free:
                return min(free, key=dist_sq)

            # Every eligible roof is full: queue at main house (if leader) or nearest own house
            if own_houses:
                if c.id == leader_id:
                    return next((h for h in own_houses if h.id == main_hid or getattr(h, "is_main", False)), own_houses[0])
                return min(own_houses, key=dist_sq)
            return None

        # Clanless creature (or claims disabled): all non-ruined roofs count when claims disabled.
        unclaimed = [
            h for h in houses
            if isinstance(h, House) and not h.is_ruin and (h.clan_id == 0 or not self.config.house_claim_enabled)
        ]
        free = [h for h in unclaimed if has_room(h)]
        return min(free, key=dist_sq) if free else None



    def _door_pos(self, h: House) -> tuple[float, float]:
        """Center of the doorway gap (where creatures can pass)."""
        half = h.size / 2
        if h.door_side == "north":
            return h.x + h.door_offset, h.y - half
        if h.door_side == "south":
            return h.x + h.door_offset, h.y + half
        if h.door_side == "west":
            return h.x - half, h.y + h.door_offset
        # east
        return h.x + half, h.y + h.door_offset

    def _house_entry_target(self, c: Creature, h: House) -> tuple[float, float]:
        """§L Door-seek waypoints — no more grinding at a blank wall.

        Outside a house, the creature aims at a stand-off lane `margin` off
        its NEAREST face: level with the doorway when the door is on this
        face, the door-side corner when the door is around the corner, and
        the short-way corner when the door sits on the far face. Rounding a
        corner hands over to the next face, so the body follows the edges
        until it sees the gap — then walks straight through it. Deterministic,
        rng-free geometry."""
        w = self.world
        half = h.size / 2
        dx, dy = w.delta(c.x, c.y, h.x, h.y)  # house centre -> creature
        ax, ay = abs(dx), abs(dy)
        if ax < half - 0.3 and ay < half - 0.3:
            return h.x, h.y  # already under the roof: settle toward its heart
        m = 0.9  # stand-off lane off the wall
        lim = max(0.5, half - 0.8)  # slide clamp inside the face ends
        dw = max(h.door_width * 0.45, 1.3)  # "I can see the door" alignment
        sx = 1.0 if dx >= 0 else -1.0
        sy = 1.0 if dy >= 0 else -1.0
        if ax >= ay:  # nearest face: east / west
            face = "east" if sx > 0 else "west"
            out_x = h.x + sx * (half + m)
            if h.door_side == face:
                if abs(dy - h.door_offset) <= dw:
                    # aligned with the gap: walk straight in
                    return h.x + sx * max(1.0, half - 1.6), h.y + h.door_offset
                return out_x, h.y + max(-lim, min(lim, h.door_offset))
            if h.door_side in ("north", "south"):
                # door around the corner: head for the door-side corner
                return out_x, h.y + (half + m) * (1.0 if h.door_side == "south" else -1.0)
            # door on the far face: take the short way round this one
            return out_x, h.y + sy * (half + m)
        # nearest face: north / south
        face = "south" if sy > 0 else "north"
        out_y = h.y + sy * (half + m)
        if h.door_side == face:
            if abs(dx - h.door_offset) <= dw:
                return h.x + h.door_offset, h.y + sy * max(1.0, half - 1.6)
            return h.x + max(-lim, min(lim, h.door_offset)), out_y
        if h.door_side in ("east", "west"):
            return h.x + (half + m) * (1.0 if h.door_side == "east" else -1.0), out_y
        return h.x + sx * (half + m), out_y

    def _house_exit_target(self, c: Creature, h: House) -> tuple[float, float]:
        """§L Door-exit waypoint: direct path through the doorway to the outside stand-off lane."""
        half = h.size / 2
        m = 0.6
        dx, dy = self._door_pos(h)

        if h.door_side == "north":
            return dx, h.y - half - m
        if h.door_side == "south":
            return dx, h.y + half + m
        if h.door_side == "west":
            return h.x - half - m, dy
        # east
        return h.x + half + m, dy


    # --------------------------------------------------------------- terrain
    def _generate_terrain(self) -> None:
        cfg = self.config
        area = cfg.width * cfg.height
        n_fertile = (
            cfg.fertile_patches
            if cfg.fertile_patches >= 0
            else self._jittered(area * 0.00008)
        )
        n_rocks = (
            cfg.rock_count if cfg.rock_count >= 0 else self._jittered(area * 0.00006)
        )
        for _ in range(n_fertile):
            r = self.rng.uniform(8.0, 20.0)
            self.fertile.append(
                {
                    "x": self.rng.uniform(r, cfg.width - r),
                    "y": self.rng.uniform(r, cfg.height - r),
                    "r": r,
                }
            )
        for _ in range(n_rocks):
            r = self.rng.uniform(2.0, 5.0)
            self.rocks.append(
                {
                    "x": self.rng.uniform(r + 1, cfg.width - r - 1),
                    "y": self.rng.uniform(r + 1, cfg.height - r - 1),
                    "r": r,
                }
            )
        # AF: pre-cache static terrain payloads to avoid rebuilding dict lists on every snapshot frame
        self._cached_terrain_fertile = [dict(p) for p in self.fertile]
        self._cached_terrain_rocks = [dict(r) for r in self.rocks]

    def _is_in_rock(self, x: float, y: float, pad: float = 0.5) -> bool:
        """Check if (x, y) is inside or too close to any solid rock obstacle."""
        for rock in self.rocks:
            min_d = rock["r"] + pad
            if self.world.distance_sq(x, y, rock["x"], rock["y"]) < min_d * min_d:
                return True
        return False

    def _food_pos(self) -> tuple[float, float]:
        """New food prefers fertile ground (god law sets the bias), strictly avoiding rocks and shelters."""
        cfg = self.config
        for _ in range(32):
            if self.fertile and self.rng.random() < cfg.fertile_food_bias:
                patch = self.rng.choice(self.fertile)
                ang = self.rng.uniform(0, 2 * math.pi)
                rad = math.sqrt(self.rng.random()) * patch["r"]
                pos = (
                    (patch["x"] + math.cos(ang) * rad) % cfg.width,
                    (patch["y"] + math.sin(ang) * rad) % cfg.height,
                )
            else:
                pos = self._rand_pos()
            if (
                not self._is_in_rock(pos[0], pos[1])
                and not (self.rivers and self._in_river_band(pos[0], pos[1], pad=1.0))
                and not self._is_point_inside_any_house(pos[0], pos[1], pad=0.8)
            ):
                return pos
        for _ in range(30):
            pos = self._rand_pos()
            if not self._is_in_rock(pos[0], pos[1]) and not self._is_point_inside_any_house(pos[0], pos[1], pad=0.8):
                return pos
        return self._rand_pos()

    def _pick_variant(self, x: float, y: float) -> str:
        """§O, §AM: choose grass/grain/berry/medicinal_herb/mushroom/poisonous for a new sprout."""
        cfg = self.config
        if not cfg.plant_variants_enabled:
            return "grass"
        if cfg.poison_rate > 0 and self.rng.random() < cfg.poison_rate:
            return "poisonous"
        season = self._season()
        # base weights shift with season (§AM)
        if season == "autumn":
            weights = {"grass": 0.25, "grain": 0.25, "berry": 0.35, "medicinal_herb": 0.05, "mushroom": 0.10}
        elif season == "winter":
            weights = {"grass": 0.35, "grain": 0.05, "berry": 0.05, "medicinal_herb": 0.00, "mushroom": 0.55}
        elif season == "summer":
            weights = {"grass": 0.30, "grain": 0.40, "berry": 0.15, "medicinal_herb": 0.10, "mushroom": 0.05}
        else:  # spring
            weights = {"grass": 0.35, "grain": 0.15, "berry": 0.15, "medicinal_herb": 0.20, "mushroom": 0.15}

        # decomposer boost: near corpses or rocks → more mushrooms
        near_decomposer = False
        for e in self.world.query_radius(x, y, NUTRIENT_RADIUS):
            if e.kind == "corpse":
                near_decomposer = True
                break
        if not near_decomposer:
            for rock in self.rocks:
                if self.world.distance(x, y, rock["x"], rock["y"]) < rock["r"] + 4.0:
                    near_decomposer = True
                    break
        if near_decomposer:
            # shift weight from grass/grain to mushroom
            weights["mushroom"] = min(0.70, weights["mushroom"] + 0.30)
            # renormalize proportionally
            total = sum(weights.values())
            for k in weights:
                weights[k] /= total
        r = self.rng.random()
        cum = 0.0
        for v, w in weights.items():
            cum += w
            if r < cum:
                return v
        return "grass"


    def _new_food(self, x: float, y: float, growth: float) -> Food:
        """Create a Food with §O variant (deterministic via rng)."""
        variant = self._pick_variant(x, y)
        return Food(x=x, y=y, growth=growth, variant=variant)

    def _resolve_rock_collision(self, c: Creature) -> dict | None:
        """Push a creature out of any rock it has wandered into; return the rock.
        §AQ PH-6: collapsed ruins with uncleared rubble block the same way."""
        w, h = self.config.width, self.config.height
        is_wrap = self.config.boundary == "wrap"
        half_w = w * 0.5
        half_h = h * 0.5
        solids = list(self.rocks)
        if self.config.rubble_blocking_enabled:
            for rh in self._cached_houses:
                if rh.is_ruin and rh.rubble > 0:
                    solids.append({
                        "x": rh.x, "y": rh.y,
                        "r": rh.size * RUBBLE_RADIUS_FRAC, "_house_id": rh.id,
                    })
        for rock in solids:
            min_d = rock["r"] + c.radius
            rx, ry = rock["x"], rock["y"]
            dx = abs(c.x - rx)
            if is_wrap and dx > half_w:
                dx -= w
            if abs(dx) > min_d:
                continue
            dy = abs(c.y - ry)
            if is_wrap and dy > half_h:
                dy -= h
            if abs(dy) > min_d:
                continue
            d2 = dx * dx + dy * dy
            if d2 < min_d * min_d:
                ux, uy = self.world.delta(c.x, c.y, rx, ry)
                if abs(ux) < 1e-6 and abs(uy) < 1e-6:
                    ang = self.rng.uniform(0, 2 * math.pi)
                    ux, uy = math.cos(ang), math.sin(ang)
                norm = math.hypot(ux, uy) or 1.0
                c.x, c.y = self.world.normalize(
                    rx + ux / norm * min_d,
                    ry + uy / norm * min_d,
                )
                c.angle = math.atan2(uy, ux)
                return rock
        return None

    def _segment_hits_circle(
        self, ax: float, ay: float, bx: float, by: float, rock: dict, pad: float = 0.0
    ) -> bool:
        """Wrap-aware test: does the straight path a→b cross a rock circle?"""
        dx, dy = self.world.delta(ax, ay, bx, by)
        b2x, b2y = ax + dx, ay + dy
        dxc, dyc = self.world.delta(ax, ay, rock["x"], rock["y"])
        cx, cy = ax + dxc, ay + dyc
        vx, vy = b2x - ax, b2y - ay
        seg2 = vx * vx + vy * vy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((cx - ax) * vx + (cy - ay) * vy) / seg2))
        px_, py_ = ax + t * vx, ay + t * vy
        rr = rock["r"] + pad
        return (px_ - cx) ** 2 + (py_ - cy) ** 2 <= rr * rr

    def _warn_unreachable_food(self, c: Creature, target: Entity) -> None:
        """Warn nearby creatures about unreachable food so they also seek food elsewhere."""
        r = max(14.0, self.config.signal_radius)
        r2 = r * r
        creatures = self._cached_creatures if self._cached_creatures else self.world.entities.values()
        for other in creatures:
            if isinstance(other, Creature) and other.id != c.id:
                if self.world.distance_sq(c.x, c.y, other.x, other.y) <= r2:
                    if other.clan_id == c.clan_id or not self.config.territory_enabled:
                        other.give_ups[target.id] = self.tick

    def _give_up_on(self, c: Creature, target: Entity) -> None:
        """A meal is unreachable (behind stone or wall): abandon it for a while
        and seek food somewhere else — no creature starves grinding at an obstacle.
        Grudges are per-meal and shared with nearby clan members."""
        ttl = self.config.food_giveup_ticks
        if ttl <= 0:
            return
        grudges = c.give_ups
        if len(grudges) > 16:  # keep the memory bounded
            expired = [k for k, t0 in grudges.items() if self.tick - t0 >= ttl]
            for k in expired:
                del grudges[k]
        grudges[target.id] = self.tick
        self._warn_unreachable_food(c, target)

    # ------------------------------------------------------------- §X knowledge
    def _fact_fresh(self, c: Creature, key, ttl: int | None = None) -> dict | None:
        """Return a live fact or None (and prune it when stale).
        §AR S-3: confidence also decays linearly each tick in
        _maintain_facts, so facts fade gracefully before this hard limit."""
        f = c.facts.get(key)
        if not isinstance(f, dict):
            return None
        limit = ttl if ttl is not None else max(1, self.config.knowledge_ttl)
        if self.tick - int(f.get("tick", -limit)) > limit:
            del c.facts[key]
            return None
        return f

    def _maintain_facts(self, c: Creature) -> None:
        """§AR S-3 memory housekeeping, staggered across creatures:
        continuous confidence decay, spatial drift of stale rumours, and a
        working-memory capacity with lowest-confidence eviction."""
        if not self.config.knowledge_enabled or not c.facts:
            return
        if (self.tick + c.id) % 5 != 0:
            return
        ttl = max(1, self.config.knowledge_ttl)
        decay = 5.0 / ttl
        # capacity: hunger, wounds and age reshape the mind's workspace
        cap = WORKING_MEMORY_CAP
        if c.stage == "elder" and max(c.skills.values(), default=0.0) >= 6.0:
            cap = MEMORY_CAP_ELDER
        elif c.status == "starving" or (c.wound_severity >= 1 and c.wound_ticks > 10):
            cap = MEMORY_CAP_STRESSED
        # linear decay + drift
        for key in list(c.facts.keys()):
            f = c.facts.get(key)
            if not isinstance(f, dict):
                continue
            if key == "enemies":
                for cid in list(f.keys()):
                    meta = f.get(cid)
                    if not isinstance(meta, dict):
                        continue
                    meta["conf"] = round(float(meta.get("conf", 1.0)) - decay, 4)
                    if self.tick - int(meta.get("tick", 0)) > ttl or meta["conf"] <= 0.05:
                        del f[cid]
                if not f:
                    del c.facts[key]
                continue
            f["conf"] = round(float(f.get("conf", 1.0)) - decay, 4)
            # faded memories wander: low-conf coordinates blur
            if (
                "x" in f
                and (self.tick + c.id) % 5 == 0
                and f["conf"] < 0.9
            ):
                noise = (1.0 - f["conf"]) * 0.8
                f["x"] = round(f["x"] + self.rng.uniform(-noise, noise), 2)
                f["y"] = round(f["y"] + self.rng.uniform(-noise, noise), 2)
            if self.tick - int(f.get("tick", 0)) > ttl or f["conf"] <= 0.05:
                del c.facts[key]
        # eviction: too many facts → drop the least credible
        entries: list[tuple[float, str | int]] = []
        for key, f in c.facts.items():
            if isinstance(f, dict):
                entries.append((float(f.get("conf", 0.0)), key))
        while len(entries) > cap:
            entries.sort()
            worst_conf, worst_key = entries.pop(0)
            del c.facts[worst_key]

    def _learn(self, c: Creature, key, x: float | None = None, y: float | None = None,
               conf: float = 1.0) -> None:
        """§X firsthand experience becomes knowledge (conf 1.0)."""
        if not self.config.knowledge_enabled or self.config.knowledge_ttl <= 0:
            return
        fact: dict = {"tick": self.tick, "conf": round(conf, 3)}
        if x is not None and y is not None:
            fact["x"], fact["y"] = round(x, 2), round(y, 2)
        c.facts[key] = fact

    def _hear_fact(self, c: Creature, msg_fact: dict | None, sender_id: int | None = None) -> None:
        """§X rumor: a heard fact lands with halved confidence — retold knowledge
        is vaguer than firsthand sighting; only better news overwrites.
        §AR S-3: rumours are trust-weighted — a trusted clan-mate's word is
        believed at full strength, a stranger's or traitor's barely at all."""
        if not msg_fact or not self.config.knowledge_enabled:
            return
        kind = msg_fact.get("kind")
        conf = float(msg_fact.get("conf", 1.0)) * 0.5
        if sender_id is not None:
            trust = float(c.trust.get(sender_id, 50.0)) / 100.0
            conf *= max(0.05, min(1.0, trust))
        if conf < 0.05:
            return
        if kind == "enemy":
            clan_id = int(msg_fact.get("clan_id") or 0)
            if not clan_id or clan_id == c.clan_id:
                return
            enemies = c.facts.setdefault("enemies", {})
            old = enemies.get(clan_id)
            if old is None or conf >= float(old.get("conf", 0.0)) * 0.9:
                enemies[clan_id] = {"tick": self.tick, "conf": round(conf, 3)}
            return
        key = {"food": "food", "danger": "danger"}.get(kind)
        if key is None:
            return
        old = self._fact_fresh(c, key)
        if old is not None and float(old.get("conf", 0.0)) >= conf:
            return  # firsthand beats rumor
        c.facts[key] = {
            "x": float(msg_fact.get("x", 0.0)),
            "y": float(msg_fact.get("y", 0.0)),
            "tick": self.tick,
            "conf": round(conf, 3),
        }

    def _fact_to_share(self, c: Creature) -> dict | None:
        """The freshest known fact worth telling (rumors included while they last)."""
        ttl = max(1, self.config.knowledge_ttl)

        def score(f: dict) -> float:
            return float(f.get("conf", 1.0)) * 1000 - (self.tick - int(f.get("tick", 0)))

        best_kind = None
        best_score = -math.inf
        payload: dict = {}
        for kind in ("food", "danger"):
            f = self._fact_fresh(c, kind)
            if f is not None and score(f) > best_score:
                best_kind, best_score = kind, score(f)
                payload = {"kind": kind, "x": f["x"], "y": f["y"], "conf": f["conf"]}
        enemies = c.facts.get("enemies")
        if isinstance(enemies, dict):
            for clan_id, meta in enemies.items():
                if self.tick - int(meta.get("tick", 0)) > ttl:
                    continue
                if score(meta) > best_score:
                    best_kind, best_score = "enemy", score(meta)
                    payload = {
                        "kind": "enemy",
                        "clan_id": clan_id,
                        "x": round(c.x, 2),
                        "y": round(c.y, 2),
                        "conf": meta.get("conf", 1.0),
                    }
        return payload if best_kind is not None else None

    def _jittered(self, target: float) -> int:
        v = self.config.spawn_variance
        return max(0, round(self.rng.uniform(target * (1 - v), target * (1 + v))))

    def _count(self, override: int, share: float, total: int) -> int:
        """Explicit override wins; otherwise take this caste's slice of the pyramid."""
        if override >= 0:
            return override
        return max(0, round(total * share))

    def _house_overlaps(self, x: float, y: float, size: float) -> bool:
        """Check if a house at x,y,size would overlap any existing house or rock.

        Houses keep at least `house_gap` clear space between walls so the alley
        between two shelters stays passable — creatures wedged in a tighter gap
        block on a wall whichever way they turn.
        """
        cfg = self.config
        # check houses
        for e in self.world.entities.values():
            if isinstance(e, House) and not e.is_ruin:
                # use world distance for wrap
                dist = self.world.distance(x, y, e.x, e.y)
                min_dist = size / 2 + e.size / 2 + max(cfg.house_gap, 1.5)
                if dist < min_dist:
                    return True
        # check rocks
        for r in self.rocks:
            dist = self.world.distance(x, y, r["x"], r["y"])
            if dist < size / 2 + r["r"] + 1.0:
                return True
        # §AQ PH-3: no roof straddles the water — keep houses off the channels
        if self._in_river_band(x, y, pad=size / 2 + 2.0):
            return True
        return False

    def _find_non_overlapping_house_pos(self, size: float, near: Creature | None = None) -> tuple[float, float]:
        """Find a non-overlapping house position, trying near founder if given."""
        cfg = self.config
        margin = size / 2
        # try near founder first
        if near is not None:
            for _ in range(30):
                x = (near.x + self.rng.uniform(-12, 12)) % cfg.width
                y = (near.y + self.rng.uniform(-12, 12)) % cfg.height
                x = max(margin, min(cfg.width - margin, x))
                y = max(margin, min(cfg.height - margin, y))
                if not self._house_overlaps(x, y, size):
                    return x, y
        # fallback to random with retries
        for _ in range(50):
            x = self.rng.uniform(margin, max(margin, cfg.width - margin))
            y = self.rng.uniform(margin, max(margin, cfg.height - margin))
            if not self._house_overlaps(x, y, size):
                return x, y
        # last resort: return random even if overlaps (avoid infinite loop on crowded map)
        return self.rng.uniform(margin, max(margin, cfg.width - margin)), self.rng.uniform(margin, max(margin, cfg.height - margin))

    def _rand_house_pos(self, size: float) -> tuple[float, float]:
        """Position keeping the whole house inside the world edge (with overlap avoidance)."""
        return self._find_non_overlapping_house_pos(size)

    def _refresh_cache(self) -> None:
        """T: single-pass over entities — build creature/food/house/corpse caches + sorted creature list.

        AF: one O(N) scan replaces the old world.creatures() call (O(N)) plus
        independent per-subsystem entity scans in plants/fires/enforce_food_law/corpses.
        """
        creatures: list[Creature] = []
        foods: list = []
        houses: list = []
        corpses: list = []
        m: dict[int, list[Creature]] = {}
        for e in self.world.entities.values():
            t = type(e)
            if t is Creature:
                creatures.append(e)
                m.setdefault(e.clan_id, []).append(e)  # type: ignore[union-attr]
            elif t is Food:
                foods.append(e)
            elif t is House:
                if not e.is_ruin:  # type: ignore[union-attr]
                    houses.append(e)
            elif t is Corpse:
                corpses.append(e)
        self._cached_creatures = creatures
        self._clan_members = m
        # §AU CPU: entities insertion order == id-ascending (monotonic _next_id);
        # creatures list is already sorted — avoid O(N log N) sort without changing law.
        self._cached_creatures_sorted = creatures
        self._cached_foods = foods
        self._cached_houses = sorted(houses, key=lambda h: h.id)
        self._cached_corpses = corpses

        houses_by_clan: dict[int, list[House]] = {}
        unclaimed_houses: list[House] = []
        for h in houses:
            if h.clan_id:
                houses_by_clan.setdefault(h.clan_id, []).append(h)
            else:
                unclaimed_houses.append(h)
        self._houses_by_clan = houses_by_clan
        self._unclaimed_houses = unclaimed_houses
        self._house_by_pos = {(round(h.x, 2), round(h.y, 2)): h for h in houses}
        # Spatial house grid (50x50 cells) for O(1) near-house lookups without touching world entities
        house_grid: dict[tuple[int, int], list[House]] = {}
        for h in houses:
            gx, gy = int(h.x // 50), int(h.y // 50)
            for dgx in (-1, 0, 1):
                for dgy in (-1, 0, 1):
                    house_grid.setdefault((gx + dgx, gy + dgy), []).append(h)
        self._house_grid = house_grid

        # §AU CPU: merged single pass for sleeping occupancy + bodies under roof.
        house_occ: dict[int, int] = {}
        bodies: dict[int, int] = {}
        for c in creatures:
            # bodies physically under each roof (overcrowd drain)
            for h in house_grid.get((int(c.x // 50), int(c.y // 50)), []):
                half = h.size / 2
                if abs(c.x - h.x) < half and abs(c.y - h.y) < half:
                    bodies[h.id] = bodies.get(h.id, 0) + 1
                    break
            if getattr(c, "sleeping", False):
                hid = getattr(c, "house_id", None)
                if hid is not None:
                    house_occ[hid] = house_occ.get(hid, 0) + 1
                else:
                    for h in house_grid.get((int(c.x // 50), int(c.y // 50)), []):
                        if self._inside_house(c, h):
                            house_occ[h.id] = house_occ.get(h.id, 0) + 1
                            break
        self._house_occupants = house_occ
        self._house_bodies = bodies
        if getattr(self, "_elev_c_buf", None) is None and getattr(self, "elev_grid", None):
            try:
                import ctypes
                self._elev_c_buf = (ctypes.c_float * len(self.elev_grid))(*self.elev_grid)
            except Exception:
                self._elev_c_buf = None

        # Precompute shrine positions for instant O(1) lookups (§AP)
        shrine_pos: dict[int, tuple[float, float]] = {}
        for cid, info in self.clans.items():
            mhid = info.get("main_house_id")
            house = self.world.entities.get(mhid) if mhid else None
            if not isinstance(house, House) or house.is_ruin or house.clan_id != cid:
                c_houses = houses_by_clan.get(cid, [])
                house = c_houses[0] if c_houses else None
            if isinstance(house, House):
                shrine_pos[cid] = (house.x + house.size / 2.0 + 1.5, house.y)
        self._shrine_pos_by_clan = shrine_pos

        # AZ Phase 4a P0: _leader_pos O(N) inner scan → O(1) via world.entities.get
        leader_pos: dict[int, tuple[float, float]] = {}
        for cid, info in self.clans.items():
            lid = info.get("leader_id")
            if not lid:
                continue
            ent = self.world.entities.get(lid)
            if isinstance(ent, Creature) and ent.clan_id == cid:
                leader_pos[cid] = (ent.x, ent.y)
        self._leader_pos = leader_pos

        # §AS L-2/L-5: totem power rides on the chief's presence at the hall
        # and on his rites; theocracy never lets faith fall below full.
        totem_power: dict[int, float] = {}
        totem_stats: dict[int, dict[str, float]] = {}
        if self.config.totems_enabled:
            for cid, clan in self.clans.items():
                totem_name = clan.get("totem")
                tp = 1.0
                if clan.get("governance") == "theocracy":
                    tp = 1.0
                else:
                    lpos = leader_pos.get(cid)
                    mhid = clan.get("main_house_id")
                    if lpos and mhid:
                        for h in houses_by_clan.get(cid, ()):
                            if h.id == mhid and self.world.distance_sq(lpos[0], lpos[1], h.x, h.y) <= (h.size * 0.5) ** 2:
                                tp = 2.0
                                break
                        else:
                            tp = 0.5
                    elif not lpos:
                        tp = 0.5
                totem_power[cid] = tp
                if totem_name and totem_name in TOTEM_BUFF:
                    mult = self._totem_mult(cid) * tp
                    totem_stats[cid] = {k: v * mult for k, v in TOTEM_BUFF[totem_name].items()}
        self._totem_power = totem_power
        self._clan_totem_stats = totem_stats

        # §AQ PH-9: living priest per clan (bio-electric calm aura)
        priest_pos: dict[int, tuple[float, float]] = {}
        for cid, members in m.items():
            for c in members:
                if c.caste == "Priest" and c.energy > 20.0:
                    priest_pos[cid] = (c.x, c.y)
                    break
        self._priest_pos = priest_pos
        self._totem_mult_cache = {}  # resonance is recomputed per tick

    def _get_creatures(self) -> list[Creature]:
        if self._cached_creatures:
            return self._cached_creatures
        self._refresh_cache()
        return self._cached_creatures

    # ------------------------------------------------------------------ tick
    def step(self) -> None:
        """Advance the world by exactly one tick (deterministic)."""
        t_step0 = time.perf_counter()
        self._eaten.clear()
        self._fleeing_ids = set()  # §AR S-5: who ran scared this tick
        self._beds.clear()  # beds are re-contested every tick, in id order
        self._events_this_tick = []
        self._eaters_this_tick = []
        # §AP: a sacred truce (synod/epiphany) stills all strife while it lasts
        if self.truce_ticks > 0:
            self.truce_ticks -= 1
        self._update_weather()
        self._update_wind()  # §AQ PH-2: the sky's breath follows the weather
        self._update_rivers()  # §AQ PH-3: rain swells the channels
        self._update_traffic()  # §AQ PH-4: grass reclaims quiet paths
        self._update_seismic()  # §AQ PH-8: the ground sometimes moves
        self._update_lightning()  # §AQ PH-9: storms strike real bolts
        self._update_law_wave()  # §AQ PH-10: the shimmer front sweeps on
        # §Q signals decay (ripples fade)
        self.signals = [sg for sg in self.signals if sg["ttl"] > 1]
        for sg in self.signals:
            sg["ttl"] -= 1
        # §AU CPU: build spatial index for signals — per-creature hearing drops
        # from O(N*S) to O(N * avg_nearby) (~400 -> ~5-10). Law-preserving:
        # grid is superset for max_hear_d; iteration order = insertion order.
        self._signal_grid: dict[tuple[int, int], list[tuple[int, dict]]] = {}
        self._signal_grid_cs = self.world.cell_size
        if self.signals and self.config.communication_enabled:
            cols = self.world.cols
            rows = self.world.rows
            cs = self._signal_grid_cs
            sg_grid = self._signal_grid
            for idx, sg in enumerate(self.signals):
                gx = int(sg["x"] // cs) % cols if cols else 0
                gy = int(sg["y"] // cs) % rows if rows else 0
                sg_grid.setdefault((gx, gy), []).append((idx, sg))
        # §AR S-1: a war cry must wake sleepers BEFORE they settle — the full
        # hearing pass never reaches a sleeping body.
        if self.signals and self.config.communication_enabled:
            for sg in self.signals:
                if sg.get("kind") != "warcry":
                    continue
                wr = self.config.signal_radius * WARCRY_RADIUS_MULT
                for o in self.world.query_radius(sg["x"], sg["y"], wr):
                    if isinstance(o, Creature) and not o.is_predator:
                        o.alarm_wake_ticks = max(o.alarm_wake_ticks, 20)
        self._update_fires()
        self._update_campfires()  # §AO E: explorers kindle the night's fire
        self._update_disasters()
        self._update_temperature()  # §AQ PH-1: the heat field breathes
        self._update_plants()
        self.world.rebuild_index()
        self._refresh_cache()
        self._update_anomaly_discovery()  # §AQ PH-10: explorers map the strange

        # AZ Phase 2 P1: evict _identity_cache for dead entities (never queried again)
        if self.tick % 30 == 0 and self._identity_cache:
            try:
                live_entity_ids = set(self.world.entities.keys())
                dead_keys = [k for k in self._identity_cache if k[0] not in live_entity_ids]
                for k in dead_keys:
                    self._identity_cache.pop(k, None)
            except Exception:
                pass
        # Leaderless-clan repair: catch clans whose leader_id points to a dead or
        # missing creature (e.g. loaded from old state, or succession_enabled=False).
        # Runs every 30 ticks so the cost is negligible.
        if self.tick % 30 == 0 and self.clans:
            live_ids: set[int] = {c.id for c in self._cached_creatures}
            for cid, clan in self.clans.items():
                lid = clan.get("leader_id")
                if lid is not None and lid not in live_ids:
                    # Leader is dead or missing — elect a replacement immediately.
                    members = [c for c in self._cached_creatures if c.clan_id == cid]
                    if members:
                        gov = clan.get("governance", "republic")
                        if gov == "monarchy":
                            successor = sorted(members, key=lambda cc: (-cc.age, cc.id))[0]
                        elif gov == "theocracy":
                            priests = [cc for cc in members if cc.caste == "Priest"]
                            successor = sorted(priests or members, key=lambda cc: (-cc.age, cc.id))[0]
                        elif gov == "junta":
                            soldiers = [cc for cc in members if cc.caste == "Soldier"]
                            successor = sorted(soldiers or members, key=lambda cc: (-getattr(cc, "skills", {}).get("combat", 0.0), -cc.age, cc.id))[0]
                        else:
                            successor = sorted(members, key=lambda cc: (-cc.sides, -cc.age, cc.id))[0]
                        clan["leader_id"] = successor.id
                        if self.config.succession_enabled:
                            succ_name = personal_name_for(successor.id, self.config.seed, successor.generation)
                            self._log_clan_history(
                                cid,
                                "leader_change",
                                f"{succ_name} (#{successor.id}) elected after leaderless interregnum (Day {self.day})",
                            )
                            self._emit(
                                HistoryEvent(
                                    type="succession",
                                    tick=self.tick + 1,
                                    entity_id=successor.id,
                                    caste=successor.caste,
                                    x=round(successor.x, 2),
                                    y=round(successor.y, 2),
                                    payload={"clan_id": cid, "prev_leader": lid, "new_leader": successor.id, "clan_name": clan.get("name")},
                                )
                            )
                    else:
                        clan["leader_id"] = None

        houses = self._cached_houses
        tod = self._time_of_day()
        is_night = self._is_night(tod)
        # §AO Phase E: close the nightly bed-overflow census at dawn.
        if not is_night and getattr(self, "_overflow_was_night", False):
            self._last_night_overflow = max(
                getattr(self, "_last_night_overflow", 0),
                getattr(self, "_bed_overflow_night", 0),
            )
            self._bed_overflow_night = 0
        self._overflow_was_night = is_night
        env_sight = self.env_sight_mult()
        env_speed = self.env_speed_mult()
        clan_house_map: dict[int, House] = {
            h.clan_id: h for h in houses if isinstance(h, House) and h.clan_id and not h.is_ruin
        }
        self._sync_wind_cache()
        for creature in list(self._cached_creatures):
            if creature.id in self.world.entities:
                self._update_creature(creature, houses, tod, is_night, env_sight, env_speed, clan_house_map)
        # §AX P0: single consolidated cache — positions moved but clan membership
        # unchanged; defer full rebuild until after war/prune to avoid triplicate.
        # _update_disease and _update_war handle stale cache via w.entities checks
        # and rebuilt spatial index; next tick's _refresh_cache will be fresh.
        # M-4: stagger heavy post-creature work at >700c (saves ~30ms at 800c, keeps 300c single-core)
        _do_heavy_post = not (len(self._cached_creatures) > 700 and self.tick % 2 == 1)
        if _do_heavy_post:
            self._update_disease()
        # AA: positions moved this tick; re-bucket so the spatial war/mob
        # queries below see where everyone actually stands now.
        self.world.rebuild_index()
        if _do_heavy_post:
            self._update_war()
        self._update_night_watch()  # §AO C: spearmen guard the thresholds
        self._update_leader_orders()  # §AS L-2: retreat, ritual, harvest, evacuate
        self._prune_extinct_clans()  # §P0: keep clan bookkeeping bounded
        self._refresh_cache()
        self._reproduce()
        # N150 hotfix: throttle heavy clan/politics work when pop >800 — staggered offsets to avoid 15-tick pileup
        c_n = len(self._cached_creatures)
        if c_n > 400:
            if self.tick % 3 == 1:
                self._update_relations()
                self._update_territory()
            if self.tick % 5 == 2:
                self._update_politics()
            if self.tick % 10 == 3:
                self._update_clan_specialization()
            # schism/culture already gated by config, but also throttle
            if self.config.schism_enabled and self.tick % 3 == 1:
                self._update_schism()
            if self.config.culture_enabled and self.tick % 10 == 3:
                self._update_culture()
            if self.tick % 5 == 1:
                self._update_builders()
                self._update_structures()
            if self.tick % 5 == 3:
                self._update_hearths()
                self._update_agriculture()
            if self.tick % 5 == 4:
                self._update_faith()
        else:
            self._update_relations()
            self._update_territory()
            self._update_schism()
            self._update_politics()
            self._update_clan_specialization()
            self._update_culture()
            self._update_builders()
            self._update_structures()
            self._update_hearths()
            self._update_agriculture()
            self._update_faith()
        self._enforce_food_law()
        self._update_corpses()
        self._update_settlements()
        # BA: micro-neural multi-rate update (60Hz physics done, 15Hz inference every 4th tick)
        if getattr(self.config, "nn_enabled", False) and _agent_soa is not None and _neural_engine is not None:
            try:
                if self._soa is None:
                    # lazy init SoA with current creatures
                    self._soa = _agent_soa.AgentSoA(capacity=max(2000, len(self._cached_creatures) * 2 + 10))
                    self._nn_grid = _spatial_grid.SpatialHashGrid(width=self.config.width, height=self.config.height, cell_size=32.0, boundary=self.config.boundary)
                    for c in self._cached_creatures:
                        self._soa.add_agent(int(c.id), float(c.x), float(c.y), angle=float(c.angle), energy=float(c.energy), health=float(c.health))
                    # init genomes
                    if _evolution is not None:
                        _evolution.init_genomes(self._soa)
                # 60Hz: sync positions from world to SoA and vice versa (pos += vel)
                # For now keep SoA as shadow; update grid
                if getattr(self, "_soa", None) is not None and self._soa is not None:
                    # sync world pos -> SoA pos (one-way, keep SoA coherent)
                    # simple linear scan to update SoA pos from creatures
                    try:
                        # rebuild SoA pos from current creatures (keep ids aligned)
                        # If SoA size mismatches, rebuild
                        if self._soa.N != len(self._cached_creatures):
                            # rebuild SoA to match world (handles births/deaths)
                            from .agent_soa import AgentSoA as _AS

                            new_soa = _AS(capacity=max(2000, len(self._cached_creatures) * 2 + 10))
                            for c in self._cached_creatures:
                                new_soa.add_agent(int(c.id), float(c.x), float(c.y), angle=float(c.angle), energy=float(c.energy), health=float(c.health))
                            if _evolution is not None:
                                _evolution.init_genomes(new_soa)
                            self._soa = new_soa
                            self._nn_grid = _spatial_grid.SpatialHashGrid(width=self.config.width, height=self.config.height, cell_size=32.0, boundary=self.config.boundary)
                        else:
                            for idx, c in enumerate(self._cached_creatures):
                                if _agent_soa.HAS_NUMPY:
                                    self._soa.pos[idx, 0] = float(c.x)
                                    self._soa.pos[idx, 1] = float(c.y)
                                    self._soa.angle[idx] = float(c.angle)
                                    self._soa.stats[idx, 0] = float(c.energy)
                                    self._soa.stats[idx, 2] = float(c.health)
                                else:
                                    self._soa.pos[idx][0] = float(c.x)
                                    self._soa.pos[idx][1] = float(c.y)
                                    self._soa.angle[idx] = float(c.angle)
                                    self._soa.stats[idx][0] = float(c.energy)
                                    self._soa.stats[idx][2] = float(c.health)
                    except Exception:
                        pass
                    # 15Hz inference every 4th tick
                    self._nn_tick = getattr(self, "_nn_tick", 0) + 1
                    if self._nn_tick % 4 == 0:
                        try:
                            from .agent_pipeline import build_inputs_batch, apply_outputs_batch
                            from .neural_engine import forward_batch

                            inputs = build_inputs_batch(self._soa, spatial_grid=self._nn_grid, world=self.world)
                            hidden = self._soa.hidden_state[: self._soa.N] if _agent_soa.HAS_NUMPY else None
                            outputs, _ = forward_batch(inputs, self._soa.genomes[: self._soa.N] if _agent_soa.HAS_NUMPY else [self._soa.genomes[i] for i in range(self._soa.N)], hidden_state=self._soa.hidden_state[: self._soa.N] if _agent_soa.HAS_NUMPY else None)
                            apply_outputs_batch(self._soa, outputs)
                            # optional: write back thrust/steer to creatures as velocity hints (additive, not replacing)
                            for idx, c in enumerate(self._cached_creatures):
                                if idx < self._soa.N:
                                    if _agent_soa.HAS_NUMPY:
                                        c.angle = float(self._soa.angle[idx])
                                        # energy already drained in apply_outputs
                                        c.energy = float(self._soa.stats[idx, 0])
                                    else:
                                        c.angle = float(self._soa.angle[idx])
                                        c.energy = float(self._soa.stats[idx][0])
                        except Exception as _e:
                            # BA must never break the tick
                            pass
            except Exception:
                pass
        # Manual GC every 200 ticks to avoid stop-the-world at 1300c
        if self.tick % 200 == 0:
            gc.collect(1)
        # Log slow ticks for N150 profiling (over 150ms)
        dur = time.perf_counter() - t_step0
        if dur > 0.15:
            print(f"[sim] slow tick={self.tick} {dur*1000:.1f}ms c={len(self._cached_creatures)} food={len(self._cached_foods)} houses={len(self._cached_houses)}", flush=True)
        self.tick += 1

    # ---------------------------------------------------------------- society
    @staticmethod
    def _relation_pair(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    def _bump_relation(self, clan_a: int, clan_b: int, delta: int) -> None:
        if not clan_a or not clan_b or clan_a == clan_b:
            return
        pair = self._relation_pair(clan_a, clan_b)
        score = max(-100, min(100, self.relations.get(pair, 0) + delta))
        self.relations[pair] = score

    def _zone_of(self, score: int) -> int:
        if score >= self.config.alliance_threshold:
            return 1  # allies
        if score <= self.config.rivalry_threshold:
            return -1  # rivals
        return 0  # neutral

    def _learn_enemy(self, c: Creature, clan_id: int | None) -> None:
        """§X firsthand: this clan attacked me — remembered fresh at full confidence."""
        if not self.config.knowledge_enabled or not clan_id or clan_id == c.clan_id:
            return
        enemies = c.facts.setdefault("enemies", {})
        old = enemies.get(clan_id)
        enemies[clan_id] = {
            "tick": self.tick,
            "conf": 1.0,
            **({"prev_conf": old["conf"]} if old else {}),
        }

    def _emit_help(self, victim: Creature, aggressor: Creature) -> None:
        """§X Help call — an attacked creature rallies its clan to mob the attacker."""
        if not (self.config.communication_enabled and self.config.help_call_enabled):
            return
        self.signals.append({
            "x": round(victim.x, 2), "y": round(victim.y, 2),
            "kind": "help", "sender": victim.id,
            "clan_id": victim.clan_id or None, "born_tick": self.tick, "ttl": 12,
            "threat_x": round(aggressor.x, 2), "threat_y": round(aggressor.y, 2),
            "threat_clan": aggressor.clan_id or None,
        })

    def _mob_defenders(self, loser: Creature, winner: Creature) -> int:
        """Clan-mates of the victim within earshot of the fight (§X mobbing).

        AA: spatial query around the winner instead of scanning the whole
        roster inside the war pair loop (was O(n) per pair → O(n³)/tick).
        §AR S-0: the sleeping are fully deaf — a body in bed cannot mob.
        """
        if not (self.config.help_call_enabled and self.config.knowledge_enabled):
            return 0
        return sum(
            1
            for o in self.world.query_radius(winner.x, winner.y, self.config.help_radius)
            if o.kind == "creature"
            and o.clan_id == loser.clan_id  # type: ignore[union-attr]
            and o.id != loser.id
            and not o.is_predator  # type: ignore[union-attr]
            and not o.is_herbivore  # type: ignore[union-attr]
            and not o.sleeping  # type: ignore[union-attr]
        )

    def _update_war(self) -> None:
        """Rival-clan creatures fight on contact (§I). Shield totem reduces damage (§P).

        AA: pair discovery via the spatial hash — id-ascending outer loop, each
        rival neighbour within attack_radius considered once, so the schedule
        is identical to the old O(n²) all-pairs scan at a fraction of the cost.
        """
        cfg = self.config
        if not cfg.war_enabled:
            return
        # §AP: synods and epiphanies impose a sacred truce — strife is stilled.
        if self.truce_ticks > 0:
            return
        # AF: pre-sorted in _refresh_cache; fallback if called outside step()
        creatures = self._cached_creatures_sorted if self._cached_creatures_sorted else sorted(self.world.creatures(), key=operator.attrgetter("id"))
        to_kill: list[tuple[Creature, Creature]] = []
        to_wound: list[tuple[Creature, Creature]] = []
        fallen: set[int] = set()  # losers already scheduled this tick
        r2 = cfg.attack_radius * cfg.attack_radius
        dist_sq = self.world.distance_sq
        w = self.world
        for a in creatures:
            if a.id not in w.entities or a.id in fallen or a.is_predator or a.is_herbivore or not a.clan_id:
                continue
            # §AT-4 H-1: the badly wounded cannot start a fight — they can
            # still be attacked, and grievously wounded bodies never initiate.
            if a.health < COMBAT_MIN_HEALTH or (a.wound_ticks > 0 and a.wound_severity >= 2):
                continue
            neighbours = [
                b
                for b, _ in w.query_radius_with_dist_sq(a.x, a.y, cfg.attack_radius)
                if b.kind == "creature" and b.id > a.id and b.id not in fallen
            ]
            # §AX P0: early rival rejection — filter kin/non-rivals before assassin
            # checks and sorting (800 creatures → war step 15.6ms → <2ms).
            # Keep only: different clan, both have clan_id, and relation zone == -1 (rival).
            filtered: list[Creature] = []
            for nb in neighbours:  # type: ignore[union-attr]
                nb_c = cast(Creature, nb)
                if nb_c.is_predator or nb_c.is_herbivore or not nb_c.clan_id:
                    continue
                if a.clan_id == nb_c.clan_id:
                    continue
                pair_r = self._relation_pair(a.clan_id, nb_c.clan_id)
                if self._zone_of(self.relations.get(pair_r, 0)) != -1:
                    continue
                if nb_c.id not in w.entities:
                    continue
                filtered.append(nb_c)
            neighbours = filtered  # type: ignore[assignment]
            # §AS L-1 / §P0: bold/junta assassins prioritize enemy chiefs —
            # split without allocating a closure per attacker.
            is_assassin = (
                getattr(a, "trait", None) == "bold"
                or self.clans.get(a.clan_id, {}).get("governance") == "junta"
            )
            if is_assassin:
                chiefs = [cc for cc in neighbours if self.clans.get(cc.clan_id, {}).get("leader_id") == cc.id]  # type: ignore[union-attr]
                if chiefs:
                    chiefs.sort(key=lambda cc: cc.id)  # type: ignore[union-attr]
                    rest = [cc for cc in neighbours if cc not in chiefs]  # type: ignore[union-attr]
                    rest.sort(key=lambda cc: cc.id)  # type: ignore[union-attr]
                    neighbours = chiefs + rest
                else:
                    neighbours.sort(key=lambda cc: cc.id)  # type: ignore[union-attr]
            else:
                neighbours.sort(key=lambda cc: cc.id)  # type: ignore[union-attr]
            for b in neighbours:  # type: ignore[union-attr]
                b = cast(Creature, b)
                if b.id not in w.entities or b.is_predator or b.is_herbivore or not b.clan_id or a.clan_id == b.clan_id:
                    continue
                pair = self._relation_pair(a.clan_id, b.clan_id)
                if self._zone_of(self.relations.get(pair, 0)) != -1:
                    continue
                loser, winner = (a, b) if a.id < b.id else (b, a)
                # AA: original semantics — only previously-recorded LOSERS are
                # blocked; a fight's winner may still lose a later duel.
                if loser.id in fallen or winner.id in fallen:
                    continue
                # Shield totem: 30% damage reduction; warrior specialization adds bite (§P); traits bold/peaceful (§S)
                dmg = cfg.attack_damage
                # warrior clan hits harder
                w_spec = self.clans.get(winner.clan_id, {}).get("specialization", {}).get("warrior", 0.33) if winner.clan_id else 0.33
                dmg *= (0.85 + w_spec * 0.45)
                if winner.trait == "bold":
                    dmg *= 1.25
                elif winner.trait == "peaceful":
                    dmg *= 0.65
                # §AS L-5: the junta's soldiers live for war — their combat
                # mastery grows faster (skill gains scaled in the resolve pass)
                if self.clans.get(winner.clan_id, {}).get("governance") == "junta":
                    pass
                # §AS L-1: an army without its general fights at half strength;
                # a rally before battle sharpens every blade in earshot.
                if winner.clan_id and winner.clan_id not in getattr(self, "_leader_pos", {}):
                    dmg *= LEADERLESS_WAR_MULT
                if getattr(winner, "combat_boost_ticks", 0) > 0:
                    dmg *= 1.0 + COMBAT_RALLY_BONUS
                # §AS L-1: targeted assassination — striking at the enemy chief
                loser_is_enemy_chief = (
                    self.clans.get(loser.clan_id, {}).get("leader_id") == loser.id
                )
                if (
                    loser_is_enemy_chief
                    and (
                        winner.trait == "bold"
                        or self.clans.get(winner.clan_id, {}).get("governance") == "junta"
                    )
                ):
                    dmg *= 1.0 + ASSASSIN_ATTACK_BONUS
                # §AP: the Celestial Strike lends God's Wrath to its warriors
                dmg *= 1.0 + self._totem_stat(winner, "damage")
                if loser.trait == "paranoid":
                    # paranoid dodges? slight reduction
                    dmg *= 0.9
                if winner.energy < 0.20 * cfg.energy_max:
                    dmg *= 0.7  # exhaustion penalty
                if self._totem_stat(loser, "defense"):
                    dmg *= 1.0 - self._totem_stat(loser, "defense")
                # §X mobbing: a surrounded attacker hits softer
                dmg /= 1.0 + cfg.defense_weight * min(self._mob_defenders(loser, winner), 4)
                if dmg >= loser.health:
                    to_kill.append((loser, winner))
                else:
                    to_wound.append((loser, winner))
                fallen.add(loser.id)
        for loser, winner in to_kill:
            if loser.id not in self.world.entities:
                continue
            if hasattr(winner, "skills") and isinstance(winner.skills, dict):
                skill_gain = 3.0
                if self.clans.get(winner.clan_id, {}).get("governance") == "junta":
                    skill_gain *= JUNTA_COMBAT_SKILL  # §AS L-5
                winner.skills["combat"] = winner.skills.get("combat", 0.0) + skill_gain
            winner.energy = max(1.0, winner.energy - 6.0)
            winner.emote = "combat"
            winner.emote_ticks = 25
            loser.emote = "panic"
            loser.emote_ticks = 25
            self._emit_help(loser, winner)  # §X dying cry — the clan remembers
            self._learn_enemy(loser, winner.clan_id)
            self._learn_enemy(winner, loser.clan_id)
            self._kill(loser, "war")
            self._emit(
                HistoryEvent(
                    type="war",
                    tick=self.tick + 1,
                    entity_id=loser.id,
                    caste=loser.caste,
                    x=round(loser.x, 2),
                    y=round(loser.y, 2),
                    payload={
                        "winner": winner.id,
                        "a": loser.clan_id,
                        "b": winner.clan_id,
                        "a_name": self.clans.get(loser.clan_id, {}).get("name"),
                        "b_name": self.clans.get(winner.clan_id, {}).get("name"),
                        "lethal": True,
                    },
                )
            )
            # §AS L-1: killing the enemy chief breaks the army's will —
            # the war ends on the spot (forced peace).
            if loser_is_enemy_chief:
                pair2 = self._relation_pair(loser.clan_id, winner.clan_id)
                self.relations[pair2] = min(100, max(self.relations.get(pair2, 0), 10))
                self._declared_wars.pop(pair2, None)
                self._emit(
                    HistoryEvent(
                        type="peace",
                        tick=self.tick + 1,
                        entity_id=0,
                        payload={
                            "a": loser.clan_id, "b": winner.clan_id,
                            "a_name": self.clans.get(loser.clan_id, {}).get("name"),
                            "b_name": self.clans.get(winner.clan_id, {}).get("name"),
                            "reason": "leader_slain",
                        },
                    )
                )
                # §AS L-4: was this murder DECLARED? An undeclared regicide
                # turns every neutral stomach against the assassin's clan.
                formal = self._declared_wars.pop(
                    self._relation_pair(winner.clan_id, loser.clan_id), None
                )
                if formal is None:
                    self._emit(
                        HistoryEvent(
                            type="regicide",
                            tick=self.tick + 1,
                            entity_id=winner.id,
                            caste=winner.caste,
                            x=round(loser.x, 2),
                            y=round(loser.y, 2),
                            payload={
                                "victim": loser.id, "victim_clan": loser.clan_id,
                                "assassin_clan": winner.clan_id,
                                "assassin": winner.id,
                            },
                        )
                    )
                    for other in sorted(self.clans.keys()):
                        if other in (winner.clan_id, loser.clan_id):
                            continue
                        opair = self._relation_pair(other, winner.clan_id)
                        self.relations[opair] = max(-100, self.relations.get(opair, 0) + REGICIDE_RELATION_HIT)
                        vpair = self._relation_pair(other, loser.clan_id)
                        self.relations[vpair] = min(100, self.relations.get(vpair, 0) + REGICIDE_SYMPATHY)
            self._bump_relation(loser.clan_id, winner.clan_id, -5)
            # §AB mutual defence — the loser attacked a whole coalition
            self._mobilise_coalition(winner.clan_id, loser.clan_id)
            # Territory conquest — winner absorbs loser's territory and house (§S)
            loser_house = None
            for h in (self._cached_houses if self._cached_houses else self._functional_houses()):
                if isinstance(h, House) and h.clan_id == loser.clan_id and not h.is_ruin:
                    loser_house = h
                    break
            if loser_house is not None:
                winner_color = self.clans.get(winner.clan_id, {}).get("color")
                loser_cid = loser.clan_id
                loser_house.clan_id = winner.clan_id
                loser_house.clan_color = winner_color
                loser_house.is_main = False
                loser_house.takeover_tick = self.tick  # §AT-3 render flash
                # §AT-3 orphan cleanup: if this was the loser's seat, re-point
                # or clear it so no clan claims a house it no longer owns.
                if self.clans.get(loser_cid, {}).get("main_house_id") == loser_house.id:
                    remaining = [
                        h for h in (self._cached_houses or self._functional_houses())
                        if isinstance(h, House) and h.clan_id == loser_cid and not h.is_ruin
                    ]
                    if remaining:
                        self._set_main_house_for_clan(loser_cid, max(remaining, key=lambda h: h.size))
                    else:
                        self.clans[loser_cid]["main_house_id"] = None
                self._log_clan_history(
                    winner.clan_id, "conquest",
                    f"Conquered House #{loser_house.id} from {self.clans.get(loser_cid, {}).get('name')} (Day {self.day})",
                )
                self._emit(
                    HistoryEvent(
                        type="conquest",
                        tick=self.tick + 1,
                        entity_id=loser_house.id,
                        x=round(loser_house.x, 2),
                        y=round(loser_house.y, 2),
                        payload={"winner_clan": winner.clan_id, "loser_clan": loser_cid, "house_id": loser_house.id, "winner": winner.id, "loser": loser.id},
                    )
                )
            # §AM E.2 famine raid — a starving war party carries off the granary
            self._try_granary_raid(winner, loser)
        for loser, winner in to_wound:
            if loser.id not in self.world.entities:
                continue
            if hasattr(winner, "skills") and isinstance(winner.skills, dict):
                winner.skills["combat"] = winner.skills.get("combat", 0.0) + 1.2
            winner.energy = max(1.0, winner.energy - 6.0)
            loser.energy = max(1.0, loser.energy - 10.0)
            winner.emote = "combat"
            winner.emote_ticks = 20
            loser.emote = "panic"
            loser.emote_ticks = 20
            self._emit_help(loser, winner)  # §X wounded cry — rally the clan
            self._learn_enemy(loser, winner.clan_id)
            self._learn_enemy(winner, loser.clan_id)
            w_spec2 = self.clans.get(winner.clan_id, {}).get("specialization", {}).get("warrior", 0.33) if winner.clan_id else 0.33
            trait_mult = 1.0
            if winner.trait == "bold":
                trait_mult *= 1.25
            elif winner.trait == "peaceful":
                trait_mult *= 0.65
            if winner.equipped_item == "spear":
                trait_mult *= 1.2
            if winner.energy < 0.20 * cfg.energy_max:
                trait_mult *= 0.7  # exhaustion penalty
            if loser.trait == "paranoid":
                trait_mult *= 0.9
            dmg = cfg.attack_damage * (0.85 + w_spec2 * 0.45) * trait_mult * (1.0 - self._totem_stat(loser, "defense"))
            # §X mobbing softens blows on the wound path too
            dmg /= 1.0 + cfg.defense_weight * min(self._mob_defenders(loser, winner), 4)
            loser.health = max(0, loser.health - dmg)
            # §AT-4 H-1: a heavy blow leaves a lingering wound — regen halves
            # (or quarters, if grievous), the body hobbles, war is over for it.
            if dmg > WOUND_MIN_DAMAGE and loser.id in w.entities:
                loser.wound_ticks = self.rng.randint(WOUND_TICKS_BASE, WOUND_TICKS_BASE + 50)
                loser.wound_severity = 2 if dmg >= 40.0 else 1
            # wounded flees
            dx, dy = self.world.delta(loser.x, loser.y, winner.x, winner.y)
            loser.angle = math.atan2(dy, dx)
            self._emit(
                HistoryEvent(
                    type="war",
                    tick=self.tick + 1,
                    entity_id=loser.id,
                    caste=loser.caste,
                    x=round(loser.x, 2),
                    y=round(loser.y, 2),
                    payload={
                        "winner": winner.id,
                        "a": loser.clan_id,
                        "b": winner.clan_id,
                        "a_name": self.clans.get(loser.clan_id, {}).get("name"),
                        "b_name": self.clans.get(winner.clan_id, {}).get("name"),
                        "lethal": False,
                        "damage": round(dmg, 1),
                    },
                )
            )
            self._bump_relation(loser.clan_id, winner.clan_id, -3)
            # §AB mutual defence on the wound path too
            self._mobilise_coalition(winner.clan_id, loser.clan_id)
            # §AM E.2 famine raid — hunger follows the war band home
            self._try_granary_raid(winner, loser)

    def _try_granary_raid(self, winner: Creature, loser: Creature) -> None:
        """§AM E.2: a martial clan fighting beside a rival's granary hauls away
        what it can when its own stores run empty. Breadbasket clans learn why
        the neighbours build walls."""
        cfg = self.config
        if not (cfg.granaries_enabled and cfg.war_enabled):
            return
        raider_info = self.clans.get(winner.clan_id)
        victim_info = self.clans.get(loser.clan_id)
        if not raider_info or not victim_info or not loser.clan_id:
            return
        # famine condition: the raider's own stores are empty
        if float(raider_info.get("granary", 0.0)) + float(raider_info.get("larder", 0.0)) > 40.0:
            return
        hid = victim_info.get("main_house_id")
        granary_house = self.world.entities.get(hid) if hid is not None else None
        if not isinstance(granary_house, House) or granary_house.is_ruin:
            return
        if self.world.distance(winner.x, winner.y, granary_house.x, granary_house.y) > cfg.territory_radius:
            return  # too far from the store to carry anything off
        loot = min(RAID_GRANARY_MAX, float(victim_info.get("granary", 0.0)))
        if loot < 1.0:
            return
        victim_info["granary"] = float(victim_info.get("granary", 0.0)) - loot
        room = max(0.0, cfg.granary_capacity - float(raider_info.get("granary", 0.0)))
        raider_info["granary"] = float(raider_info.get("granary", 0.0)) + min(loot, room)
        self._bump_relation(loser.clan_id, winner.clan_id, -8)
        self._emit(
            HistoryEvent(
                type="raid",
                tick=self.tick + 1,
                entity_id=winner.id,
                caste=winner.caste,
                x=round(granary_house.x, 2), y=round(granary_house.y, 2),
                payload={
                    "a": winner.clan_id, "b": loser.clan_id,
                    "a_name": raider_info.get("name"), "b_name": victim_info.get("name"),
                    "loot": round(loot, 1),
                },
            )
        )

    def _update_relations(self) -> None:
        """Clan scores rise when strangers feast together and drift toward peace.

        AA: incremental — eater pairs come from the spatial hash instead of an
        O(eaters²) scan; dominant castes and border adjacency are computed once
        per tick (the dominant-caste pass was O(clans×creatures)); pairs that
        relax back to 0 are forgotten so the relation table stays bounded.
        """
        cfg = self.config
        w = self.world

        # Old zones are what the chronicle last saw (neutral for unseen pairs).
        old_zones: dict[tuple[int, int], int] = dict(self._relation_zones)

        # Shared feeding (+2): only actual eater pairs, found via the hash.
        # (Duplicates in _eaters_this_tick collapse — a creature eats once.)
        eaters = sorted(set(self._eaters_this_tick))
        if eaters:
            eater_ids = set(eaters)
            for aid in eaters:
                ea = w.entities.get(aid)
                if not isinstance(ea, Creature):
                    continue
                for n in sorted(
                    (x for x in w.query_radius(ea.x, ea.y, cfg.flock_radius)
                     if x.kind == "creature" and x.id in eater_ids and x.id > ea.id),
                    key=lambda x: x.id,
                ):
                    eb = cast(Creature, n)
                    if not ea.clan_id or not eb.clan_id or ea.clan_id == eb.clan_id:
                        continue
                    self._bump_relation(ea.clan_id, eb.clan_id, +2)

        # Emit events for bumps that crossed a threshold (including bumps done
        # outside this tick via _bump_relation).
        for pair in sorted(list(self.relations.keys())):
            old = old_zones.get(pair, 0)
            new = self._zone_of(self.relations[pair])
            if new != old and new != 0:
                a, b = pair
                self._emit(
                    HistoryEvent(
                        type="alliance" if new == 1 else "rivalry",
                        tick=self.tick + 1,
                        entity_id=0,
                        caste=None,
                        x=0.0,
                        y=0.0,
                        payload={"a": a, "b": b, "score": self.relations[pair]},
                    )
                )
            old_zones[pair] = new

        # Scores relax toward neutrality; crossing a threshold is news.
        rate = int(round(cfg.relation_drift_rate))
        for pair in sorted(list(self.relations.keys())):
            score = self.relations[pair]
            prev_zone = old_zones.get(pair, self._zone_of(score))
            if score > 0:
                score = max(0, score - rate)
            elif score < 0:
                score = min(0, score + rate)
            self.relations[pair] = score
            new_zone = self._zone_of(score)
            if new_zone != prev_zone and new_zone != 0:
                a, b = pair
                self._emit(
                    HistoryEvent(
                        type="alliance" if new_zone == 1 else "rivalry",
                        tick=self.tick + 1,
                        entity_id=0,
                        caste=None,
                        x=0.0,
                        y=0.0,
                        payload={"a": a, "b": b, "score": score},
                    )
                )
            if score == 0:
                # AA: neutral pairs are forgotten — bump re-creates on demand.
                del self.relations[pair]
                self._relation_zones.pop(pair, None)
            else:
                self._relation_zones[pair] = new_zone

        # Diplomacy depth — richer relation factors (§S)
        # Common enemy +, border-adjacency −, same-caste +
        # Applied as small per-tick bumps, still within -100..100
        # Common enemy: a and b share a rival c
        rival_sets: dict[int, set[int]] = {}
        for (a, b), score in self.relations.items():
            if self._zone_of(score) == -1:
                rival_sets.setdefault(a, set()).add(b)
                rival_sets.setdefault(b, set()).add(a)
        for (a, b) in list(self.relations.keys()):
            ra = rival_sets.get(a, set())
            rb = rival_sets.get(b, set())
            if ra & rb:
                self._bump_relation(a, b, +1)

        # Border adjacency: claimed houses within 2*territory_radius — via the
        # spatial hash instead of an O(houses²) scan.
        if cfg.territory_enabled:
            houses_by_clan: dict[int, House] = {}
            for e in w.entities.values():
                if isinstance(e, House) and e.clan_id and not e.is_ruin:
                    houses_by_clan[e.clan_id] = e  # type: ignore[assignment]
            done: set[tuple[int, int]] = set()
            reach = 2 * cfg.territory_radius
            for ca, ha in houses_by_clan.items():
                for n in w.query_radius(ha.x, ha.y, reach):
                    if not isinstance(n, House) or not n.clan_id or n.is_ruin or n.clan_id == ca:
                        continue
                    if w.distance(ha.x, ha.y, n.x, n.y) >= reach:
                        continue
                    pk = self._relation_pair(ca, n.clan_id)
                    if pk in done:
                        continue
                    done.add(pk)
                    self._bump_relation(pk[0], pk[1], -1)

        # Same-caste bonus: clans sharing the most common caste among members —
        # one pass over the cached roster (was one full roster scan PER CLAN).
        caste_counts: dict[int, dict[str, int]] = {}
        for c in self._get_creatures():
            if not c.clan_id:
                continue
            counts = caste_counts.setdefault(c.clan_id, {})
            counts[c.caste] = counts.get(c.caste, 0) + 1
        dominant = {
            cid: max(cnt.items(), key=lambda kv: kv[1])[0]
            for cid, cnt in caste_counts.items()
        }
        for (a, b) in list(self.relations.keys()):
            da = dominant.get(a)
            db = dominant.get(b)
            if da and da == db:
                self._bump_relation(a, b, +1)

        # §AP holy alliances: clans worshipping the same or a complementary
        # avatar sympathise — doctrine draws the faithful together.
        if self.config.totems_enabled and self.clans:
            avatars = {cid: info.get("totem") for cid, info in self.clans.items()}
            for (a, b) in list(self.relations.keys()):
                ta, tb = avatars.get(a), avatars.get(b)
                if not ta or not tb:
                    continue
                if ta == tb or AVATAR_ALLIES.get(ta) == tb or AVATAR_ALLIES.get(tb) == ta:
                    self._bump_relation(a, b, +1)

    def _update_territory(self) -> None:
        """§P: clan territory — members prefer own ground, trespass sours relations."""
        cfg = self.config
        if not cfg.territory_enabled:
            return
        # functional claimed houses are territory anchors
        houses = [h for h in (self._cached_houses if self._cached_houses else self._functional_houses()) if h.clan_id != 0]
        if not houses:
            return
        # Trespass: each creature inside a rival's radius slightly sours the two clans
        # Query spatial hash around each claimed house instead of scanning all creatures
        r = cfg.territory_radius
        r2 = r * r
        dist_sq = self.world.distance_sq
        decay_int = int(round(cfg.trespass_decay))
        for h in houses:
            for c in self.world.query_radius(h.x, h.y, r):
                if not isinstance(c, Creature) or not c.clan_id or c.is_predator or c.is_herbivore:
                    continue
                if h.clan_id == c.clan_id:
                    continue
                if dist_sq(c.x, c.y, h.x, h.y) <= r2:
                    if cfg.trespass_decay >= 1:
                        self._bump_relation(c.clan_id, h.clan_id, -decay_int)
                    else:
                        if self.rng.random() < cfg.trespass_decay:
                            self._bump_relation(c.clan_id, h.clan_id, -1)
                    # §AN C.3: the boundary stone rings — sentries walk the line
                    if (
                        cfg.envoys_enabled
                        and self.tick - self._stone_chime_last.get(h.clan_id, -STONE_CHIME_GAP) >= STONE_CHIME_GAP
                        and len(self.signals) < SIGNALS_MAX
                    ):
                        stone = next(
                            (s for s in self.boundary_stones if s["clan_id"] == h.clan_id
                             and dist_sq(s["x"], s["y"], c.x, c.y) <= 36.0),
                            None,
                        )
                        if stone is not None:
                            self._stone_chime_last[h.clan_id] = self.tick
                            self.signals.append({
                                "x": round(stone["x"], 2), "y": round(stone["y"], 2),
                                "kind": "chime", "sender": 0,
                                "clan_id": h.clan_id or None, "born_tick": self.tick, "ttl": 12,
                                "stone_x": stone["x"], "stone_y": stone["y"],
                                "trespasser_x": round(c.x, 2), "trespasser_y": round(c.y, 2),
                            })

    def _update_schism(self) -> None:
        """§S Schism — unhappy members split off as new clan and war parent."""
        cfg = self.config
        if not cfg.schism_enabled:
            return
        # One schism per tick max to keep determinism smooth
        # AA: one membership pass per tick (was a full roster scan PER CLAN).
        members_by_clan: dict[int, list[Creature]] = self._clan_members if self._clan_members else {}
        if not members_by_clan:
            for c in self._get_creatures():
                if c.clan_id:
                    members_by_clan.setdefault(c.clan_id, []).append(c)
        claimed_houses = {h.clan_id for h in (self._cached_houses if self._cached_houses else self._functional_houses()) if h.clan_id}
        for cid, info in list(self.clans.items()):
            members = members_by_clan.get(cid, [])
            pop = len(members)
            if pop < cfg.schism_min_pop:
                continue
            # Unhappy: starving or homeless (no house)
            has_house = cid in claimed_houses
            unhappy = 0
            for c in members:
                ratio = c.energy / cfg.energy_max if cfg.energy_max else 1
                if ratio <= cfg.starving_ratio:
                    unhappy += 1
                elif not has_house:
                    unhappy += 1
            if pop == 0 or unhappy / pop < cfg.schism_threshold:
                continue
            # Trigger schism: split unhappy half
            # Pick members to split: prioritize unhappy, then oldest
            def is_unhappy(c):
                ratio = c.energy / cfg.energy_max if cfg.energy_max else 1
                return ratio <= cfg.starving_ratio or not has_house
            unhappy_members = [c for c in members if is_unhappy(c)]
            other_members = [c for c in members if not is_unhappy(c)]
            # sort unhappy by age desc, others also
            unhappy_members.sort(key=lambda c: (-c.age, c.id))
            other_members.sort(key=lambda c: (-c.age, c.id))
            # take at least 1, at most pop//2
            take = max(1, min(pop // 2, len(unhappy_members) if unhappy_members else pop // 2))
            movers = unhappy_members[:take]
            if len(movers) < take:
                need = take - len(movers)
                movers += other_members[:need]
            if not movers:
                continue
            # Create new clan
            founder = sorted(movers, key=lambda c: (c.id))[0]
            new_cid = self._next_clan_id
            self._next_clan_id += 1
            adj = CLAN_ADJECTIVES[(new_cid * 13 + self.config.seed) % len(CLAN_ADJECTIVES)]
            noun = CLAN_NOUNS[(new_cid * 29 + self.config.seed) % len(CLAN_NOUNS)]
            if (new_cid * 7 + self.config.seed) % 10 < 3:
                name = f"Clan of the {adj} {noun}"
            else:
                name = f"{adj} {noun}"
            totem = None
            if self.config.totems_enabled:
                totem = AVATARS[(new_cid * 17 + self.config.seed) % len(AVATARS)]
            # inherit parent specialization with slight drift
            parent_spec = self.clans.get(cid, {}).get("specialization", {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34})
            # small random drift
            spec = dict(parent_spec)
            # culture inherits parent but may diverge
            parent_culture = self.clans.get(cid, {}).get("culture", "Unknown Rite")
            parent_cid = self.clans.get(cid, {}).get("culture_id", cid)
            # 15% chance to diverge into new culture on schism
            if self.rng.random() < 0.15:
                culture = f"{CULTURE_ADJECTIVES[(new_cid * 13 + self.config.seed) % len(CULTURE_ADJECTIVES)]} {CULTURE_NOUNS[(new_cid * 23 + self.config.seed) % len(CULTURE_NOUNS)]}"
                culture_id = new_cid
            else:
                culture = parent_culture
                culture_id = parent_cid
            self.clans[new_cid] = {
                "name": name,
                "founder_id": founder.id,
                "born_tick": self.tick + 1,
                "color": CLAN_COLORS[(new_cid - 1) % len(CLAN_COLORS)],
                "totem": totem,
                "leader_id": founder.id,
                "specialization": spec,
                "culture": culture,
                "culture_id": culture_id,
                "coalition_id": None,
                "larder": 0.0,
                "tribute_to": None,
            }
            for c in movers:
                c.clan_id = new_cid
            # House for new clan — claim free or spawn settlement
            if self.config.house_claim_enabled:
                self._claim_house_for_clan(new_cid)
                # if still homeless (no free house and num_houses pinned), new clan stays homeless (still schismed)
            # Rivalry with parent
            self.relations[self._relation_pair(cid, new_cid)] = -60
            self._relation_zones[self._relation_pair(cid, new_cid)] = -1
            self._emit(
                HistoryEvent(
                    type="schism",
                    tick=self.tick + 1,
                    entity_id=founder.id,
                    caste=founder.caste,
                    x=round(founder.x, 2),
                    y=round(founder.y, 2),
                    payload={"parent": cid, "new_clan": new_cid, "parent_name": info.get("name"), "new_name": name, "members": [c.id for c in movers]},
                )
            )
            self._emit(
                HistoryEvent(
                    type="rivalry",
                    tick=self.tick + 1,
                    entity_id=0,
                    caste=None,
                    x=0.0,
                    y=0.0,
                    payload={"a": cid, "b": new_cid, "score": -60},
                )
            )
            break  # only one schism per tick

    # -------------------------------------------------------------- §AB politics
    def _coalition_of(self, clan_id: int) -> int | None:
        return self._clan_coalition.get(clan_id)

    def _coalition_soured(self, members: list[int]) -> bool:
        """True once any member pair falls out of friendship — the bloc dissolves."""
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if self.relations.get(self._relation_pair(a, b), 0) < 10:
                    return True
        return False

    def _dissolve_coalition(self, coal_id: int, reason: str) -> None:
        info = self.coalitions.pop(coal_id, None)
        if info is None:
            return
        for cid in list(info["members"]):
            if self._clan_coalition.get(cid) == coal_id:
                self._clan_coalition.pop(cid, None)
            clan = self.clans.get(cid)
            if clan is not None and clan.get("coalition_id") == coal_id:
                clan["coalition_id"] = None
        self._emit(
            HistoryEvent(
                type="coalition_dissolved",
                tick=self.tick + 1,
                entity_id=0,
                payload={"coalition": coal_id, "name": info.get("name"), "reason": reason,
                         "members": list(info["members"])},
            )
        )

    def _update_coalitions(self) -> None:
        """§AB Explicit coalitions — leaders propose blocs; allies join; soured ones dissolve."""
        cfg = self.config
        if not cfg.coalitions_enabled:
            return
        # Prune dead clans; a bloc below size or with sour relations dissolves.
        for coal_id in sorted(list(self.coalitions.keys())):
            info = self.coalitions[coal_id]
            info["members"] = [m for m in info["members"] if m in self.clans]
            if len(info["members"]) < max(1, cfg.coalition_min_size - 1) or not info["members"]:
                self._dissolve_coalition(coal_id, reason="faded")
            elif self._coalition_soured(info["members"]):
                self._dissolve_coalition(coal_id, reason="soured")
        # A clan petitions to join an existing bloc.
        if self.rng.random() < COALITION_JOIN_CHANCE:
            claimed_clans = {h.clan_id for h in (self._cached_houses if self._cached_houses else self._functional_houses()) if h.clan_id}
            unaligned = [
                cid for cid in sorted(self.clans.keys())
                if cid not in self._clan_coalition and cid in claimed_clans
            ]
            for cid in unaligned:
                joined = False
                for coal_id in sorted(self.coalitions.keys()):
                    members = self.coalitions[coal_id]["members"]
                    if len(members) >= 8:
                        continue
                    if all(
                        self.relations.get(self._relation_pair(cid, m), 0)
                        >= cfg.coalition_threshold
                        for m in members
                    ):
                        self.coalitions[coal_id]["members"].append(cid)
                        self._clan_coalition[cid] = coal_id
                        self.clans[cid]["coalition_id"] = coal_id
                        self._emit(
                            HistoryEvent(
                                type="coalition_joined",
                                tick=self.tick + 1,
                                entity_id=0,
                                payload={"coalition": coal_id,
                                         "name": self.coalitions[coal_id].get("name"),
                                         "clan": cid},
                            )
                        )
                        joined = True
                        break
                if joined:
                    break
        # A leader founds a new bloc among friendly unaligned clans.
        if self.rng.random() < COALITION_FORM_CHANCE:
            for cid in sorted(self.clans.keys()):
                if cid in self._clan_coalition:
                    continue
                friends = [
                    other
                    for other in sorted(self.clans.keys())
                    if other != cid
                    and other not in self._clan_coalition
                    and self.relations.get(self._relation_pair(cid, other), 0)
                    >= cfg.coalition_threshold
                ]
                if len(friends) + 1 < cfg.coalition_min_size:
                    continue
                members = [cid] + friends[:4]
                coal_id = self._next_coalition_id
                self._next_coalition_id += 1
                name_a = self.clans[cid].get("name", f"Clan {cid}")
                name_b = self.clans[members[1]].get("name", "") if len(members) > 1 else ""
                name = f"Pact of {name_a}" if not name_b else f"{name_a} – {name_b} Pact"
                self.coalitions[coal_id] = {
                    "name": name,
                    "leader_clan": cid,
                    "members": members,
                    "born_tick": self.tick,
                }
                for m in members:
                    self._clan_coalition[m] = coal_id
                    self.clans[m]["coalition_id"] = coal_id
                self._emit(
                    HistoryEvent(
                        type="coalition_formed",
                        tick=self.tick + 1,
                        entity_id=0,
                        payload={"coalition": coal_id, "name": name,
                                 "leader_clan": cid, "members": members},
                    )
                )
                break

    def _mobilise_coalition(self, attacker_clan: int | None, victim_clan: int | None) -> None:
        """§AB Mutual defence — strike one member and every bloc-mate turns on you."""
        if not attacker_clan or not victim_clan or not self.config.coalitions_enabled:
            return
        coal_id = self._clan_coalition.get(victim_clan)
        if not coal_id:
            return
        for m in self.coalitions.get(coal_id, {}).get("members", []):
            if m == victim_clan or m == attacker_clan:
                continue
            self._bump_relation(attacker_clan, m, -12)

    def _remembered_enemy(self, clan_id: int) -> int | None:
        """The freshest enemy the clan collectively remembers (§X union)."""
        ttl = max(1, self.config.knowledge_ttl)
        best: tuple[int, int] | None = None  # (tick, enemy)
        for c in self._clan_members.get(clan_id, ()):
            for enemy, meta in (c.facts.get("enemies") or {}).items():
                t = int(meta.get("tick", 0))
                if int(enemy) != clan_id and self.tick - t <= ttl and (best is None or t > best[0]):
                    best = (t, int(enemy))
        return best[1] if best is not None else None

    def _dispatch_herald(self, cid: int, leader: Creature, rival: int) -> None:
        """§AS L-4: the two chiefs stand too far apart to talk — dispatch the
        highest-caste healthy subject as a herald. The herald must survive
        the journey for diplomacy to succeed (envoy machinery resolves it)."""
        candidates = [
            m for m in self._clan_members.get(cid, ())
            if m.stage in ("adult", "elder")
            and not m.is_predator and not m.is_herbivore
            and m.health > 50.0 and getattr(m, "mission", None) is None
            and m.id != leader.id
        ]
        if not candidates:
            return
        herald = max(candidates, key=lambda m: (m.sides, -m.id))
        rleader_id = self.clans.get(rival, {}).get("leader_id")
        rleader = self.world.entities.get(rleader_id) if rleader_id is not None else None
        tx, ty = (
            (rleader.x, rleader.y) if isinstance(rleader, Creature)
            else (herald.x, herald.y)
        )
        herald.mission = {
            "type": "peace", "target_clan": rival,
            "x": round(tx, 2), "y": round(ty, 2),
            "deadline": self.tick + ENVOY_MISSION_TICKS,
        }
        self._log_clan_history(
            cid, "herald",
            f"Dispatched a herald to {self.clans.get(rival, {}).get('name')} (Day {self.day})",
        )

    def _update_leader_decisions(self) -> None:
        """§AB Leader agency — war, peace, tribute demand and betrayal surface as plots.

        God watches but never vetoes. The leader's heritable trait biases the
        hand: bold → war, peaceful → peace, paranoid → betrayal (with treason).
        """
        cfg = self.config
        if not cfg.leader_decisions_enabled:
            return
        # Prune war markers for dead clans and cooled-down feuds so the map
        # stays bounded and concluded wars can eventually be re-opened.
        if self._declared_wars and self.tick % 500 == 0:
            live = set(self.clans.keys())
            self._declared_wars = {
                p: t for p, t in self._declared_wars.items()
                if p[0] in live and p[1] in live
                and self.tick - t < WAR_DECLARE_COOLDOWN * 4
            }
        pops = {cid: len(m) for cid, m in self._clan_members.items()}
        for cid in sorted(self.clans.keys()):
            info = self.clans[cid]
            lid = info.get("leader_id")
            leader = self.world.entities.get(lid) if lid is not None else None
            if not isinstance(leader, Creature):
                continue
            if self.rng.random() >= LEADER_DECISION_CHANCE:
                continue
            trait = leader.trait
            acted = False
            # Betrayal: break an alliance and strike (paranoid hands first).
            if cfg.betrayal_enabled and trait in ("paranoid", "bold"):
                for pair, score in sorted(self.relations.items()):
                    if self._zone_of(score) != 1 or cid not in pair:
                        continue
                    victim = pair[1] if pair[0] == cid else pair[0]
                    self.relations[pair] = max(-100, score - 95)
                    self.relations[pair] = min(100, self.relations[pair])
                    self._emit(
                        HistoryEvent(
                            type="betrayal",
                            tick=self.tick + 1,
                            entity_id=lid,
                            caste=leader.caste,
                            x=round(leader.x, 2),
                            y=round(leader.y, 2),
                            payload={"a": cid, "b": victim,
                                     "a_name": info.get("name"),
                                     "b_name": self.clans.get(victim, {}).get("name")},
                        )
                    )
                    # Treason: sow false knowledge so third clans distrust the victim too.
                    for other in sorted(self.clans.keys()):
                        if other in (cid, victim):
                            continue
                        mates = self._clan_members.get(other, ())
                        if not mates:
                            continue
                        herald = mates[int(self.rng.random() * len(mates))]
                        if self.world.distance(herald.x, herald.y, leader.x, leader.y) <= TREASON_RADIUS:
                            self.signals.append({
                                "x": round(herald.x, 2), "y": round(herald.y, 2),
                                "kind": "knowledge", "sender": leader.id,
                                "clan_id": other or None, "born_tick": self.tick, "ttl": 12,
                                "fact": {"kind": "enemy", "clan_id": victim,
                                         "x": round(leader.x, 2), "y": round(leader.y, 2),
                                         "conf": 1.0},
                            })
                    acted = True
                    break
            if acted:
                continue
            # Peace: a weakened leader sues a rival for peace.
            # §AP: the Cosmic Scales keep reliable peace — any Scales leader,
            # whatever their trait, may sue, and offers land harder.
            scales_peace = self._totem_stat(leader, "peace") > 0
            if trait == "peaceful" or scales_peace or pops.get(cid, 0) < 3:
                for pair, score in sorted(self.relations.items()):
                    if self._zone_of(score) != -1 or cid not in pair:
                        continue
                    rival = pair[1] if pair[0] == cid else pair[0]
                    my_pop = pops.get(cid, 0)
                    if my_pop and my_pop <= pops.get(rival, 0):
                        # §AS L-4: peace needs a face-to-face meeting — if the
                        # two chiefs stand far apart the offer rides with a
                        # herald instead (envoy mission below).
                        rleader_id = self.clans.get(rival, {}).get("leader_id")
                        rleader = self.world.entities.get(rleader_id) if rleader_id is not None else None
                        leaders_close = isinstance(rleader, Creature) and (
                            self.world.distance(leader.x, leader.y, rleader.x, rleader.y) <= TALK_RADIUS
                        )
                        boost = 90 if scales_peace else 60
                        gov = info.get("governance", "republic")
                        if gov == "republic":
                            boost = int(boost * REPUBLIC_PEACE_MULT)  # §AS L-5
                        elif gov == "junta":
                            boost //= 2  # militarists are half believed
                        if leaders_close:
                            self.relations[pair] = min(100, score + boost)
                            # §AP/§AB fix: peace closes the feud — the pair may only
                            # be re-declared on after the full cooldown.
                            self._declared_wars.pop(pair, None)
                            self._emit(
                                HistoryEvent(
                                    type="peace",
                                    tick=self.tick + 1,
                                    entity_id=0,
                                    payload={"a": cid, "b": rival,
                                             "a_name": info.get("name"),
                                             "b_name": self.clans.get(rival, {}).get("name")},
                                )
                            )
                        elif cfg.envoys_enabled:
                            self._dispatch_herald(cid, leader, rival)
                        acted = True
                        break
            if acted:
                continue
            # §AN C.1 — a peaceful (or deliberative) leader commissions an
            # emissary: a healthy adult carries treaty terms to a rival's
            # main house. God sees the banner; no veto exists.
            if cfg.envoys_enabled and (trait == "peaceful" or info.get("governance") == "republic"):
                for pair, score in sorted(self.relations.items()):
                    if cid not in pair or self._zone_of(score) == 1:
                        continue
                    rival = pair[1] if pair[0] == cid else pair[0]
                    if rival not in self.clans:
                        continue
                    rinfo = self.clans[rival]
                    rhid = rinfo.get("main_house_id")
                    rhouse = self.world.entities.get(rhid) if rhid is not None else None
                    if not isinstance(rhouse, House):
                        continue
                    # pick the healthiest adult non-soldier as herald
                    candidates_m = [
                        m for m in self._clan_members.get(cid, ())
                        if m.stage == "adult" and not m.is_predator and not m.is_herbivore and m.health > 60.0 and getattr(m, "mission", None) is None
                    ]
                    if not candidates_m:
                        break
                    herald = max(candidates_m, key=lambda m: (m.health, -m.id))
                    herald.mission = {
                        "type": "peace", "target_clan": rival,
                        "x": round(rhouse.x, 2), "y": round(rhouse.y, 2),
                        "deadline": self.tick + ENVOY_MISSION_TICKS,
                    }
                    acted = True
                    break
            if acted:
                continue
            # War: declare on an enemy with specific calculated Casus Belli (§AL)
            if trait == "bold" or trait is None or info.get("governance") == "junta":
                # §AS L-5: a theocracy cannot declare war unilaterally — it
                # needs a priest elder at the chief's side to co-sign.
                if info.get("governance") == "theocracy":
                    priest_elder = next(
                        (
                            m for m in self._clan_members.get(cid, ())
                            if m.caste == "Priest" and m.stage in ("adult", "elder")
                            and self.world.distance(m.x, m.y, leader.x, leader.y) <= 15.0
                        ),
                        None,
                    )
                    if priest_elder is None:
                        continue
                enemy = self._remembered_enemy(cid)
                casus_belli = "blood_feud"
                if enemy is None:
                    # Check for famine raid or territory dispute
                    own_larder = float(info.get("larder", 0.0))
                    for pair, score in sorted(self.relations.items()):
                        if cid not in pair:
                            continue
                        rival = pair[1] if pair[0] == cid else pair[0]
                        rival_info = self.clans.get(rival, {})
                        if own_larder < 20.0 and float(rival_info.get("larder", 0.0)) > 60.0:
                            enemy = rival
                            casus_belli = "famine_raid"
                            break
                if enemy is not None and enemy in self.clans and enemy != cid:
                    pair = self._relation_pair(cid, enemy)
                    score = self.relations.get(pair, 0)
                    last_declared = self._declared_wars.get(pair)
                    # One war per pair: skip clans we are already fighting
                    # (zone -1) or that this clan declared on within the
                    # cooldown — a declaration must not repeat itself.
                    if (
                        self._zone_of(score) != -1
                        and (last_declared is None or self.tick - last_declared >= WAR_DECLARE_COOLDOWN)
                    ):
                        # §AS L-5: a republic deliberates two ticks before war.
                        if info.get("governance") == "republic":
                            pending = info.get("war_pending")
                            if pending is None or pending[0] != enemy:
                                info["war_pending"] = (enemy, self.tick)
                                continue
                            if self.tick - pending[1] < 2:
                                continue
                            info.pop("war_pending", None)
                        # §AS L-1: the chief raises the rally BEFORE the blade —
                        # long-distance declarations without it are weaker.
                        if len(self.signals) < SIGNALS_MAX:
                            self.signals.append({
                                "x": round(leader.x, 2), "y": round(leader.y, 2),
                                "kind": "rally", "sender": lid,
                                "clan_id": cid or None, "born_tick": self.tick,
                                "ttl": RALLY_SIGNAL_TTL,
                            })
                        self._bump_relation(cid, enemy, -50)
                        self._declared_wars[pair] = self.tick
                        enemy_name = self.clans.get(enemy, {}).get("name", f"Clan {enemy}")
                        self._log_clan_history(
                            cid,
                            "war_declared",
                            f"Declared war on {enemy_name} (Casus Belli: {casus_belli.replace('_', ' ').capitalize()}, Day {self.day})",
                        )
                        acted = True

            if acted:
                continue
            # Tribute: a strong clan demands protection money from a weak neighbour.
            if cfg.tribute_enabled:
                my_pop = pops.get(cid, 0)
                if my_pop < 2:
                    continue
                for other in sorted(self.clans.keys()):
                    if other == cid or self._clan_coalition.get(other) == self._clan_coalition.get(cid):
                        continue
                    oinfo = self.clans[other]
                    if oinfo.get("tribute_to") is not None:
                        continue
                    if my_pop < pops.get(other, 0) * 1.6:
                        continue
                    pair = self._relation_pair(cid, other)
                    if self._zone_of(self.relations.get(pair, 0)) == -1:
                        continue  # protectors don't extort active enemies
                    oinfo["tribute_to"] = cid
                    break

    def _update_larders(self) -> None:
        """§AB Clan larder — surplus is stored at the settlement, famine draws it down."""
        cfg = self.config
        if not cfg.resource_sharing_enabled:
            return
        houses_by_clan: dict[int, House] = {}
        for e in (self._cached_houses if self._cached_houses else self._functional_houses()):
            if isinstance(e, House) and e.clan_id and not e.is_ruin and e.clan_id not in houses_by_clan:
                houses_by_clan[e.clan_id] = e
        # §AS L-3: the larder answers to its chief. Deposits are accepted only
        # when a living leader stands at the settlement; withdrawals run at a
        # rate set by governance and by the leader's farming wisdom.
        leader_at_settlement: dict[int, bool] = {}
        larder_eff: dict[int, float] = {}
        for cid, info in self.clans.items():
            seat = houses_by_clan.get(cid)
            if seat is None:
                mh_id = info.get("main_house_id")
                if mh_id is not None:
                    mh_e = self.world.entities.get(mh_id)
                    if isinstance(mh_e, House) and not mh_e.is_ruin:
                        seat = mh_e
            lpos3 = getattr(self, "_leader_pos", {}).get(cid)
            present = (
                isinstance(seat, House) and lpos3 is not None
                and self.world.distance(lpos3[0], lpos3[1], seat.x, seat.y) <= self.config.territory_radius
            )
            leader_at_settlement[cid] = present
            gov = info.get("governance", "republic")
            eff = 1.0
            if gov == "republic":
                eff = REPUBLIC_LARDER_EFF
            elif gov == "junta":
                eff = JUNTA_LARDER_EFF
            elif gov == "monarchy":
                eff = 1.0
            if not present:
                eff *= 0.5  # no chief: only a trickle leaves the store
            else:
                leader_c = self.world.entities.get(info.get("leader_id"))
                if isinstance(leader_c, Creature):
                    eff *= 1.0 + leader_c.skills.get("farming", 0.0) / 50.0
            larder_eff[cid] = eff
        starving_by_clan: dict[int, int] = {}
        for c in self._get_creatures():
            if not c.clan_id or c.is_predator or c.is_herbivore:
                continue
            house = houses_by_clan.get(c.clan_id)
            if house is None:
                continue
            clan = self.clans.get(c.clan_id)
            if clan is None:
                continue

            ratio = c.energy / cfg.energy_max if cfg.energy_max else 1.0
            if ratio > 0.75:
                # §AS L-3: deposits need the chief's presence at the settlement
                if not leader_at_settlement.get(c.clan_id, False):
                    continue
                deposit = min(0.5, (ratio - 0.75) * 8.0)
                stored = float(clan.get("larder", 0.0))
                room = max(0.0, cfg.larder_capacity - stored)
                put = min(deposit, room)
                if put > 0:
                    c.energy -= put
                    clan["larder"] = stored + put
            elif ratio <= cfg.starving_ratio:
                stored = float(clan.get("larder", 0.0))
                if stored > 0:
                    take = min(GRANARY_WITHDRAW_RATE * larder_eff.get(c.clan_id, 1.0), stored)
                    clan["larder"] = stored - take
                    c.energy += take
                # §AM C: the dry, roofed granary feeds its own through famine
                if cfg.granaries_enabled:
                    gstored = float(clan.get("granary", 0.0))
                    if gstored > 0:
                        gtake = min(GRANARY_WITHDRAW_RATE, gstored)
                        clan["granary"] = gstored - gtake
                        c.energy = min(cfg.energy_max, c.energy + gtake)
                starving_by_clan[c.clan_id] = starving_by_clan.get(c.clan_id, 0) + 1
        # Tribute: vassals pay their protector on the interval.
        if cfg.tribute_enabled and self.tick % TRIBUTE_INTERVAL == 0:
            for cid in sorted(self.clans.keys()):
                info = self.clans[cid]
                protector = info.get("tribute_to")
                if protector is None or protector not in self.clans:
                    info["tribute_to"] = None
                    continue
                amount = min(float(info.get("larder", 0.0)), 30.0)
                if amount <= 0:
                    continue
                info["larder"] = float(info.get("larder", 0.0)) - amount
                pinfo = self.clans[protector]
                # §AS L-5: a kingdom extracts double protection money
                if pinfo.get("governance") == "monarchy":
                    amount *= MONARCHY_TRIBUTE_MULT
                room = max(0.0, cfg.larder_capacity - float(pinfo.get("larder", 0.0)))
                pinfo["larder"] = float(pinfo.get("larder", 0.0)) + min(amount, room)
                # §AN C.2: the tribute rides in a courier's panniers — grain and
                # herbs carried to the suzerain granary to keep the peace.
                if cfg.granaries_enabled:
                    gpay = min(15.0, float(info.get("granary", 0.0)))
                    if gpay > 0:
                        info["granary"] = float(info.get("granary", 0.0)) - gpay
                        proom = max(0.0, cfg.granary_capacity - float(pinfo.get("granary", 0.0)))
                        pinfo["granary"] = float(pinfo.get("granary", 0.0)) + min(gpay, proom)
                        payer_house = self.world.entities.get(info.get("main_house_id")) if info.get("main_house_id") is not None else None
                        if isinstance(payer_house, House) and len(self.signals) < SIGNALS_MAX:
                            self.signals.append({
                                "x": round(payer_house.x, 2), "y": round(payer_house.y, 2),
                                "kind": "courier", "sender": 0,
                                "clan_id": cid or None, "born_tick": self.tick, "ttl": 20,
                            })
                self._emit(
                    HistoryEvent(
                        type="tribute",
                        tick=self.tick + 1,
                        entity_id=0,
                        payload={"from": cid, "to": protector,
                                 "amount": round(amount, 1),
                                 "from_name": info.get("name"),
                                 "to_name": pinfo.get("name")},
                    )
                )
        # Allied aid: a full-bellied ally feeds a starving one during famine.
        if cfg.aid_rate > 0 and self.rng.random() < cfg.aid_rate:
            for (a, b), score in sorted(self.relations.items()):
                if self._zone_of(score) != 1:
                    continue
                la, lb = (
                    float(self.clans[x].get("larder", 0.0)) for x in (a, b)
                )
                donor, recv = (a, b) if la > lb else (b, a)
                ld, lr = max(la, lb), min(la, lb)
                if ld < cfg.larder_capacity * 0.5 or lr > cfg.larder_capacity * 0.25:
                    continue
                if starving_by_clan.get(recv, 0) <= 0:
                    continue
                aid = min(ld * 0.4, cfg.larder_capacity - lr)
                if aid <= 1:
                    continue
                self.clans[donor]["larder"] = ld - aid
                self.clans[recv]["larder"] = lr + aid

    def _update_defection(self) -> None:
        """§AB Defection — the unhappy walk to a healthier banner, even a rival's."""
        cfg = self.config
        if not cfg.defection_enabled:
            return
        houses_by_clan: set[int] = {
            e.clan_id
            for e in (self._cached_houses if self._cached_houses else self._functional_houses())
            if isinstance(e, House) and e.clan_id and not e.is_ruin
        }
        for c in self._get_creatures():
            if not c.clan_id or c.is_predator or c.is_herbivore:
                continue
            ratio = c.energy / cfg.energy_max if cfg.energy_max else 1.0
            unhappy = ratio <= cfg.starving_ratio or c.clan_id not in houses_by_clan
            if not unhappy or self.rng.random() >= DEFECT_CHANCE:
                continue
            reach = cfg.flock_radius * 3.0
            candidates: dict[int, float] = {}
            for o in self.world.query_radius(c.x, c.y, reach):
                if not isinstance(o, Creature) or o.id == c.id:
                    continue
                if not o.clan_id or o.clan_id == c.clan_id or o.is_predator or o.is_herbivore:
                    continue
                d = self.world.distance(c.x, c.y, o.x, o.y)
                if o.clan_id not in candidates or d < candidates[o.clan_id]:
                    candidates[o.clan_id] = d
            if not candidates:
                continue
            # The healthiest nearby clan wins the defector.
            def vitality(cid: int) -> tuple[float, float]:
                mates = self._clan_members.get(cid, [])
                if not mates:
                    return (0.0, -float(cid))
                avg = sum(m.energy for m in mates) / len(mates)
                roofed = 1.0 if cid in houses_by_clan else 0.0
                return (roofed, avg)
            target = max(candidates, key=vitality)
            old = c.clan_id
            c.clan_id = target
            self._emit(
                HistoryEvent(
                    type="defection",
                    tick=self.tick + 1,
                    entity_id=c.id,
                    caste=c.caste,
                    x=round(c.x, 2),
                    y=round(c.y, 2),
                    payload={"from": old, "to": target,
                             "from_name": self.clans.get(old, {}).get("name"),
                             "to_name": self.clans.get(target, {}).get("name")},
                )
            )
            break  # one defection per tick keeps the world calm

    def _update_diplomacy(self) -> None:
        """§AN orchestrator — envoys, boundary chimes, markets, caravans,
        dialect drift and omens. Fixed order keeps the rng stream stable."""
        cfg = self.config
        # — envoy arrival & mission hygiene (every tick, cheap scan) —
        if cfg.envoys_enabled:
            for c in self._get_creatures():
                mission = getattr(c, "mission", None)
                if not isinstance(mission, dict) or mission.get("type") != "peace":
                    continue
                expired = self.tick >= int(mission.get("deadline", 0))
                target_clan = int(mission.get("target_clan", 0))
                arrived = (
                    not expired
                    and self.world.distance_sq(c.x, c.y, float(mission.get("x", 0.0)), float(mission.get("y", 0.0)))
                    <= max(4.0, cfg.territory_radius * 0.5) ** 2
                )
                if not (arrived or expired or target_clan not in self.clans or c.id not in self.world.entities):
                    continue
                c.mission = None
                if arrived and c.id in self.world.entities and target_clan in self.clans:
                    self._bump_relation(c.clan_id, target_clan, ENVOY_RELATION_BOOST)
                    self._emit(
                        HistoryEvent(
                            type="peace_envoy",
                            tick=self.tick + 1,
                            entity_id=c.id,
                            caste=c.caste,
                            x=round(c.x, 2), y=round(c.y, 2),
                            payload={"a": c.clan_id, "b": target_clan,
                                     "a_name": self.clans.get(c.clan_id, {}).get("name"),
                                     "b_name": self.clans.get(target_clan, {}).get("name"),
                                     "banner": "📜"},
                        )
                    )
        # — prune stones & markets of dead clans —
        live = set(self.clans.keys())
        self.boundary_stones = [s for s in self.boundary_stones if s["clan_id"] in live]
        for pair in list(self.markets.keys()):
            a, b = pair
            zone = self._zone_of(self.relations.get(pair, 0))
            if a not in live or b not in live or zone != 1:
                del self.markets[pair]
        # — markets: allied neighbours found neutral trading posts & barter —
        if cfg.markets_enabled and self.tick % MARKET_CHECK_INTERVAL == 0:
            houses_by_clan: dict[int, House] = {}
            for h in (self._cached_houses if self._cached_houses else self._functional_houses()):
                if isinstance(h, House) and h.clan_id and not h.is_ruin:
                    houses_by_clan.setdefault(h.clan_id, h)
            reach = cfg.territory_radius * 3.0
            for pair, score in sorted(self.relations.items()):
                if self._zone_of(score) != 1 or pair in self.markets:
                    continue
                ha, hb = houses_by_clan.get(pair[0]), houses_by_clan.get(pair[1])
                if ha is None or hb is None or self.world.distance(ha.x, ha.y, hb.x, hb.y) > reach:
                    continue
                mx = round((ha.x + hb.x) / 2.0, 2)
                my = round((ha.y + hb.y) / 2.0, 2)
                if self._is_in_rock(mx, my):
                    continue
                self.markets[pair] = {"x": mx, "y": my, "born_tick": self.tick}
                self._emit(
                    HistoryEvent(
                        type="market",
                        tick=self.tick + 1,
                        entity_id=0,
                        x=mx, y=my,
                        payload={"a": pair[0], "b": pair[1],
                                 "a_name": self.clans.get(pair[0], {}).get("name"),
                                 "b_name": self.clans.get(pair[1], {}).get("name")},
                    )
                )
        if cfg.markets_enabled and self.markets and self.tick % MARKET_BARTER_INTERVAL == 0:
            for pair in sorted(self.markets.keys()):
                ia, ib = self.clans.get(pair[0]), self.clans.get(pair[1])
                if not ia or not ib:
                    continue
                ga, gb = float(ia.get("granary", 0.0)), float(ib.get("granary", 0.0))
                donor, recv = (ia, ib) if ga > gb else (ib, ia)
                surplus = max(ga, gb) - min(ga, gb)
                swap = min(20.0, surplus / 2.0)
                if swap < 2.0:
                    continue
                donor["granary"] = max(0.0, float(donor.get("granary", 0.0)) - swap)
                cap_room = max(0.0, cfg.granary_capacity - float(recv.get("granary", 0.0)))
                recv["granary"] = float(recv.get("granary", 0.0)) + min(swap, cap_room)
                self._bump_relation(pair[0], pair[1], 1)
        # — travelling peddler caravans: news and rare goods between distant clans —
        if cfg.markets_enabled and self.tick % CARAVAN_INTERVAL == 0 and len(self.clans) >= 2:
            ids = sorted(cid for cid in self.clans if any(m.stage == "adult" for m in self._clan_members.get(cid, ())))
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    pair = self._relation_pair(a, b)
                    if self._zone_of(self.relations.get(pair, 0)) == -1:
                        continue
                    last = self._caravan_last.get(pair, -CARAVAN_INTERVAL)
                    if self.tick - last < CARAVAN_INTERVAL:
                        continue
                    ia, ib = self.clans[a], self.clans[b]
                    # goods flow to the leaner store; the chronicle carries the news
                    donor, recv = (ia, ib) if float(ia.get("granary", 0.0)) >= float(ib.get("granary", 0.0)) else (ib, ia)
                    gift = min(10.0, float(donor.get("granary", 0.0)))
                    if gift > 0:
                        donor["granary"] = float(donor.get("granary", 0.0)) - gift
                        room_c = max(0.0, cfg.granary_capacity - float(recv.get("granary", 0.0)))
                        recv["granary"] = float(recv.get("granary", 0.0)) + min(gift, room_c)
                    self._bump_relation(a, b, 2)
                    self._caravan_last[pair] = self.tick
                    self._emit(
                        HistoryEvent(
                            type="caravan",
                            tick=self.tick + 1,
                            entity_id=0,
                            payload={"a": a, "b": b,
                                     "a_name": ia.get("name"), "b_name": ib.get("name"),
                                     "news": True},
                        )
                    )
                    break
                else:
                    continue
                break
        # — season turn: omens from the shrine & dialect drift —
        season = self._season()
        if self._omen_season != season:
            first_turn = self._omen_season is None
            self._omen_season = season
            next_season = SEASONS[(SEASONS.index(season) + 1) % 4]
            if cfg.omens_enabled and not first_turn:
                for cid in sorted(self.clans.keys()):
                    info = self.clans[cid]
                    if int(info.get("shrine_level", 0)) < 1:
                        continue
                    priest = next(
                        (m for m in self._clan_members.get(cid, ()) if m.caste == "Priest" and m.id in self.world.entities),
                        None,
                    )
                    if priest is None:
                        continue
                    shrine = self._shrine_pos(cid)
                    sx, sy = shrine if shrine else (priest.x, priest.y)
                    if len(self.signals) < SIGNALS_MAX:
                        self.signals.append({
                            "x": round(sx, 2), "y": round(sy, 2), "kind": "omen",
                            "sender": priest.id, "clan_id": cid or None,
                            "born_tick": self.tick, "ttl": OMEN_SIGNAL_TTL, "season": next_season,
                        })
                    self._log_clan_history(
                        cid, "omen",
                        f"A priest beheld an omen: the {next_season} approaches (Day {self.day})",
                    )
                    self._emit(
                        HistoryEvent(
                            type="omen",
                            tick=self.tick + 1,
                            entity_id=priest.id,
                            caste=priest.caste,
                            x=round(sx, 2), y=round(sy, 2),
                            payload={"clan_id": cid, "season": next_season,
                                     "clan_name": info.get("name")},
                        )
                    )
            # §AN E.2 linguistic drift — isolated clans grow apart in speech;
            # allies converge toward a shared tongue.
            if cfg.dialect_drift_enabled and not first_turn:
                s_idx = SEASONS.index(season)
                ally_map: dict[int, list[int]] = {}
                for (a, b), score in self.relations.items():
                    if self._zone_of(score) == 1:
                        ally_map.setdefault(a, []).append(b)
                        ally_map.setdefault(b, []).append(a)
                for cid in sorted(self.clans.keys()):
                    info = self.clans[cid]
                    d = float(info.get("dialect", 0.0))
                    mates = ally_map.get(cid)
                    if mates:
                        mean_ally = sum(float(self.clans[m].get("dialect", 0.0)) for m in mates) / len(mates)
                        d += (mean_ally - d) * 0.25
                    else:
                        wobble = ((cid * 31 + s_idx * 7 + cfg.seed) % 9 - 4) * DIALECT_STEP
                        d += wobble
                    info["dialect"] = round(max(-1.0, min(1.0, d)), 4)

    def _update_clan_task_boards_and_bylaws(self) -> None:
        """§AL Clan Division of Labor & Dynamic Bylaws."""
        if not self.clans:
            return
        is_winter = self._season() == "winter"

        for cid, clan in self.clans.items():
            if not isinstance(clan, dict):
                continue
            bylaws = clan.setdefault("bylaws", {"rationing": False, "martial_law": False, "sanctuary": "open"})
            task_board = clan.setdefault("task_board", {"priority": "balanced", "harvester_weight": 1.0, "guard_weight": 1.0})

            # 1. Food security & winter rationing
            larder = float(clan.get("larder", 0.0))
            if is_winter or larder < 30.0:
                bylaws["rationing"] = True
                task_board["priority"] = "food_security"
                task_board["harvester_weight"] = 2.0
            else:
                bylaws["rationing"] = False
                task_board["harvester_weight"] = 1.0

            # 2. Wartime martial law
            is_at_war = False
            for pair, score in self.relations.items():
                if cid in pair and score <= self.config.rivalry_threshold:
                    is_at_war = True
                    break

            if is_at_war:
                bylaws["martial_law"] = True
                task_board["priority"] = "defense"
                task_board["guard_weight"] = 2.5
            else:
                bylaws["martial_law"] = False
                task_board["guard_weight"] = 1.0

            # 3. §AT-4 H-2 plague response: the main house becomes an infirmary —
            # its beds heal twice as well while sickness walks the clan.
            members = self._clan_members.get(cid, ())
            bylaws["plague_response"] = sum(1 for cc in members if cc.infected) >= 2

    def _update_trade_caravans(self) -> None:
        """§AL Inter-Clan Trade Caravans & Economic Specialization Barter."""
        if not self.config.resource_sharing_enabled or self.tick % 80 != 0:
            return
        # Find agricultural clans with surplus and warrior clans
        for cid, info in self.clans.items():
            if not isinstance(info, dict):
                continue
            spec = info.get("specialization", {})
            farmer_ratio = spec.get("farmer", 0.33)
            larder = float(info.get("larder", 0.0))
            if farmer_ratio > 0.35 and larder >= 40.0:
                # Seek a trading partner with neutral or positive relations
                for other_cid, other_info in self.clans.items():
                    if other_cid == cid or not isinstance(other_info, dict):
                        continue
                    pair = self._relation_pair(cid, other_cid)
                    if self._zone_of(self.relations.get(pair, 0)) >= 0:
                        other_spec = other_info.get("specialization", {})
                        if other_spec.get("warrior", 0.33) > 0.35:
                            # Trade: 12 food for combat martial lore
                            trade_amount = 12.0
                            info["larder"] = max(0.0, larder - trade_amount)
                            other_info["larder"] = min(self.config.larder_capacity, float(other_info.get("larder", 0.0)) + trade_amount)
                            self._bump_relation(cid, other_cid, 12)
                            # Boost farmer clan combat training
                            clan_members = self._clan_members.get(cid) or [cc for cc in self._get_creatures() if cc.clan_id == cid]
                            for c in clan_members:
                                if hasattr(c, "skills") and isinstance(c.skills, dict):
                                    c.skills["combat"] = c.skills.get("combat", 0.0) + 1.0
                            break

    def _update_festivals_and_traditions(self) -> None:
        """§AL Tribal Traditions & Autumn Harvest Festival."""
        season_len = max(1, self.config.season_length)
        if self._season() == "autumn" and (self.tick % season_len == season_len - 1):
            houses_by_clan = {}
            for h in (self._cached_houses if self._cached_houses else self._functional_houses()):
                if isinstance(h, House) and h.clan_id and getattr(h, "is_main", False) and not getattr(h, "is_ruin", False):
                    houses_by_clan[h.clan_id] = h

            for cid, clan in self.clans.items():
                if not isinstance(clan, dict):
                    continue
                main_h = houses_by_clan.get(cid)
                if not main_h:
                    continue
                # All clan members near Main House celebrate
                members = self._clan_members.get(cid) or [cc for cc in self._get_creatures() if cc.clan_id == cid]
                for c in members:
                    if self.world.distance(c.x, c.y, main_h.x, main_h.y) <= 18.0:
                        c.energy = min(self.config.energy_max, c.energy + 25.0)
                        c.emote = "cheer"
                        c.emote_ticks = 30
                        lid = clan.get("leader_id")
                        if lid and lid != c.id:
                            if not hasattr(c, "trust") or c.trust is None:
                                c.trust = {}
                            c.trust[lid] = min(100.0, c.trust.get(lid, 0.0) + 10.0)
                        if c.stage in ("infant", "juvenile"):
                            if hasattr(c, "skills") and isinstance(c.skills, dict):
                                c.skills["farming"] = c.skills.get("farming", 0.0) + 2.0


                self._log_clan_history(
                    cid,
                    "festival",
                    f"Celebrated the Annual Autumn Harvest Festival (Day {self.day})",
                )

    # ------------------------------------------------- §AP unified theology
    def _shrine_pos(self, cid: int) -> tuple[float, float] | None:
        """The shrine stands beside the clan's main house (east wall); faith
        follows the people, so a clanless-of-roof clan falls back to any
        claimed roof. None when the clan is homeless."""
        cached = getattr(self, "_shrine_pos_by_clan", None)
        if cached is not None:
            return cached.get(cid)
        info = self.clans.get(cid)
        if not info:
            return None
        house = self.world.entities.get(info.get("main_house_id"))
        if not isinstance(house, House) or house.is_ruin or house.clan_id != cid:
            house = None
            for h in self._functional_houses():
                if isinstance(h, House) and h.clan_id == cid and not h.is_ruin:
                    house = h
                    break
        if not isinstance(house, House):
            return None
        return (house.x + house.size / 2.0 + 1.5, house.y)

    def _shrine_aura_radius(self, cid: int) -> float:
        """A level-1 shrine blesses its immediate surroundings; a temple's
        aura extends across the whole territory."""
        if int(self.clans.get(cid, {}).get("shrine_level", 0)) >= 2:
            return max(SHRINE_AURA_RADIUS, self.config.territory_radius)
        return SHRINE_AURA_RADIUS

    def _clan_priest(self, cid: int) -> Creature | None:
        """First living priest of a clan — the voice of the avatar."""
        for m in self._clan_members.get(cid, ()):
            if m.caste == "Priest" and m.id in self.world.entities:
                return m
        for c in self.world.creatures():
            if c.clan_id == cid and c.caste == "Priest":
                return c
        return None

    def _update_faith(self) -> None:
        """§AP Theology tick — tithes at dawn & dusk fill the clan faith pool,
        the shrine aura mends the faithful, overflowing faith works seasonal
        miracles and raises temples, crisis ages convene synods, and once in
        an age an elder priest beholds the Sphere. Deterministic: hash-gates
        instead of rng draws so the world's rng stream never moves."""
        cfg = self.config
        if not cfg.theology_enabled or not self.clans:
            return
        dl = max(1, cfg.day_length)
        tod = self._time_of_day()
        at_dawn = abs(tod - 0.25) < TITHE_WINDOW
        at_dusk = abs(tod - 0.75) < TITHE_WINDOW
        season_now = self._season()

        for cid in sorted(self.clans.keys()):
            clan = self.clans[cid]
            members = [
                m for m in self._clan_members.get(cid, ())
                if m.id in self.world.entities and not m.is_predator and not m.is_herbivore
            ]
            if not members:
                continue
            shrine = self._shrine_pos(cid)
            level = int(clan.get("shrine_level", 0))
            faith = float(clan.get("faith", 0.0))
            avatar = clan.get("totem")

            # A settled clan consecrates its shrine beside the main house.
            if shrine is not None and level == 0:
                clan["shrine_level"] = 1
                level = 1
                self._log_clan_history(
                    cid, "shrine",
                    f"Consecrated a shrine to the {avatar} beside the main house (Day {self.day})",
                )

            if shrine is not None and level >= 1:
                aura2 = self._shrine_aura_radius(cid) ** 2

                # Morning & evening tithes: the devout offer energy at the totem base.
                if (at_dawn or at_dusk) and cfg.tithe_rate > 0:
                    gained = 0.0
                    for m in members:
                        if m.energy < cfg.energy_max * 0.6:
                            continue
                        if self.world.distance_sq(m.x, m.y, *shrine) > aura2:
                            continue
                        tithe = cfg.energy_max * cfg.tithe_rate * (2.0 if m.caste == "Priest" else 1.0)
                        m.energy -= tithe
                        gained += tithe
                    faith += gained

                # The blessing aura mends the faithful while the pool holds out.
                for m in members:
                    if faith <= BLESS_FAITH_COST:
                        break
                    if m.health >= m.max_health:
                        continue
                    if self.world.distance_sq(m.x, m.y, *shrine) > aura2:
                        continue
                    healed = min(m.max_health, m.health + BLESS_HEAL_RATE) - m.health
                    if healed > 0:
                        m.health += healed
                        faith -= BLESS_FAITH_COST

                # Seasonal miracle: faith overflowing at the turn of a season.
                if (
                    self._last_season is not None
                    and season_now != self._last_season
                    and faith >= MIRACLE_FAITH_COST
                ):
                    faith -= MIRACLE_FAITH_COST
                    clan["faith"] = round(faith, 2)
                    self._work_miracle(cid, clan, shrine)

                # Temple upgrade: high faith raises stone to the Sphere.
                if level == 1 and faith >= cfg.temple_faith_cost:
                    faith -= cfg.temple_faith_cost
                    clan["shrine_level"] = 2
                    self._emit(HistoryEvent(
                        type="temple", tick=self.tick + 1, entity_id=0,
                        x=round(shrine[0], 2), y=round(shrine[1], 2),
                        payload={"clan_id": cid, "clan_name": clan.get("name"), "avatar": avatar},
                    ))
                    self._log_clan_history(
                        cid, "temple",
                        f"Raised the {avatar} shrine into a glowing Temple of the Sphere (Day {self.day})",
                    )

            clan["faith"] = round(faith, 2)

        self._last_season = season_now

        # The Great Synod of the Sphere — crisis ages unify the clans (§AP Phase D).
        age = self._age()
        if age in ("Ice", "Plague") and self.tick % SYNOD_INTERVAL == (self.config.seed % SYNOD_INTERVAL):
            self._hold_synod(age)

        # The 3D Epiphany — rare enlightenment at a temple (§AP Phase E).
        self._maybe_epiphany()

    def _work_miracle(self, cid: int, clan: dict, shrine: tuple[float, float]) -> None:
        """A seasonal miracle — the avatar gifts a mature bounty around the
        shrine and mends its whole flock."""
        cfg = self.config
        for i in range(MIRACLE_FOOD):
            ang = ((self.tick * 31 + i * 97 + self.config.seed + cid * 7) % 6283) / 1000.0
            rad = 1.5 + (i % 3) * 1.3
            x, y = self.world.normalize(
                shrine[0] + math.cos(ang) * rad,
                shrine[1] + math.sin(ang) * rad,
            )
            self.world.add(self._new_food(x, y, growth=1.0))
        for m in self._clan_members.get(cid, ()):
            if m.id not in self.world.entities or m.is_predator or m.is_herbivore:
                continue
            m.health = min(m.max_health, m.health + 20.0)
            m.energy = min(cfg.energy_max, m.energy + 10.0)
            m.emote = "cheer"
            m.emote_ticks = 30
        self._emit(HistoryEvent(
            type="miracle", tick=self.tick + 1, entity_id=0,
            x=round(shrine[0], 2), y=round(shrine[1], 2),
            payload={"clan_id": cid, "clan_name": clan.get("name"), "avatar": clan.get("totem")},
        ))
        self._log_clan_history(
            cid, "miracle",
            f"The {clan.get('totem')} granted a miracle: food bloomed around the shrine (Day {self.day})",
        )

    def _hold_synod(self, age: str) -> None:
        """§AP Phase D: during global crises the priests convene at a neutral
        centre; every clan warms toward every other and strife is stilled."""
        priest_clans = {
            c.clan_id for c in self._get_creatures()
            if c.caste == "Priest" and c.clan_id and c.id in self.world.entities
        }
        if len(priest_clans) < 2:
            return
        shrines = [p for p in (self._shrine_pos(c) for c in sorted(priest_clans)) if p]
        cx = sum(p[0] for p in shrines) / len(shrines)
        cy = sum(p[1] for p in shrines) / len(shrines)
        for pair in list(self.relations.keys()):
            self.relations[pair] = min(100, self.relations[pair] + SYNOD_RELATION_BOOST)
        self.truce_ticks = TRUCE_TICKS
        self._emit(HistoryEvent(
            type="synod", tick=self.tick + 1, entity_id=0,
            x=round(cx, 2), y=round(cy, 2),
            payload={"age": age, "clans": sorted(priest_clans),
                     "clan_names": [self.clans[c].get("name") for c in sorted(priest_clans)]},
        ))

    def _maybe_epiphany(self) -> None:
        """§AP Phase E: once in a great age, an elder priest of a temple clan
        perceives the true 3D nature of the Sphere — sectarian strife stills."""
        day_index = self.tick // max(1, self.config.day_length)
        key = (day_index, self.config.seed % EPIPHANY_PERIODS_GAP)
        if getattr(self, "_epiphany_day_seen", None) == key:
            return
        for cid in sorted(self.clans.keys()):
            clan = self.clans[cid]
            if int(clan.get("shrine_level", 0)) < 2:
                continue
            if (self.config.seed * 31 + cid * 17 + day_index) % EPIPHANY_PERIODS_GAP != 0:
                continue
            priest = self._clan_priest(cid)
            if priest is None or priest.stage != "elder":
                continue
            self._epiphany_day_seen = key
            for pair in list(self.relations.keys()):
                self.relations[pair] = min(100, self.relations[pair] + 10)
            self.truce_ticks = TRUCE_TICKS * 2
            priest.emote = "heal"
            priest.emote_ticks = 60
            priest.skills["healing"] = priest.skills.get("healing", 0.0) + 5.0
            self._emit(HistoryEvent(
                type="epiphany", tick=self.tick + 1, entity_id=priest.id,
                caste=priest.caste, x=round(priest.x, 2), y=round(priest.y, 2),
                payload={
                    "clan_id": cid, "clan_name": clan.get("name"),
                    "avatar": clan.get("totem"),
                    "personal_name": personal_name_for(priest.id, self.config.seed, priest.generation),
                    "glyph": glyph_for(priest.id, self.config.seed, priest.generation),
                },
            ))
            self._log_clan_history(
                cid, "epiphany",
                f"An elder priest beheld the Sphere in three dimensions — strife stilled (Day {self.day})",
            )
            return

    def on_law_change(self, names: list[str]) -> None:
        """§AP Phase C: Divine Law Resonance — when God adjusts any law, every
        Totem Shrine emits harmonic chimes and radiant pulses, and priests
        deliver doctrinal sermons interpreting the change per their avatar's
        dogma (morale rally within the aura). Called from the god-law endpoint;
        never touches the rng."""
        # §AQ PH-10: the law-change physical wave — a shimmer front sweeps
        # the map while the new law settles (cosmology precedes doctrine).
        self.law_wave = {"born_tick": self.tick}
        if not names or not self.config.theology_enabled:
            return
        chimes = 0
        sermons = 0
        for cid in sorted(self.clans.keys()):
            clan = self.clans[cid]
            if int(clan.get("shrine_level", 0)) < 1:
                continue
            shrine = self._shrine_pos(cid)
            if shrine is None:
                continue
            self.signals.append({
                "x": round(shrine[0], 2), "y": round(shrine[1], 2),
                "kind": "chime", "sender": 0,
                "clan_id": cid, "born_tick": self.tick, "ttl": 15,
            })
            chimes += 1
            priest = self._clan_priest(cid)
            if priest is None:
                continue
            dogma = AVATAR_DOGMA.get(clan.get("totem"), "the Sphere reshapes the world")
            law_txt = ", ".join(n.replace("_", " ") for n in names[:4])
            self._emit(HistoryEvent(
                type="sermon", tick=self.tick + 1, entity_id=priest.id,
                caste=priest.caste, x=round(priest.x, 2), y=round(priest.y, 2),
                payload={
                    "clan_id": cid, "clan_name": clan.get("name"),
                    "avatar": clan.get("totem"), "laws": names[:4],
                    "text": f"{priest.caste} proclaims: '{dogma}' — the law of {law_txt} fulfils it",
                },
            ))
            sermons += 1
            # Rallying morale: the flock within the aura draws strength.
            aura2 = self._shrine_aura_radius(cid) ** 2
            for m in self._clan_members.get(cid, ()):
                if m.id not in self.world.entities or m.is_predator or m.is_herbivore:
                    continue
                if self.world.distance_sq(m.x, m.y, *shrine) <= aura2:
                    m.energy = min(self.config.energy_max, m.energy + 2.0)
        if chimes or sermons:
            self._emit(HistoryEvent(
                type="resonance", tick=self.tick + 1, entity_id=0, x=0.0, y=0.0,
                payload={"laws": names, "chimes": chimes, "sermons": sermons},
            ))
        # §AS L-6: the chiefs interpret God's will — bold frames it as a call
        # to arms, the peaceful as a farming blessing. Never touches the rng.
        for cid in sorted(self.clans.keys()):
            info = self.clans[cid]
            lid = info.get("leader_id")
            leader = self.world.entities.get(lid) if lid is not None else None
            if not isinstance(leader, Creature):
                continue
            tone = "war" if leader.trait == "bold" else "blessing"
            if len(self.signals) < SIGNALS_MAX:
                self.signals.append({
                    "x": round(leader.x, 2), "y": round(leader.y, 2),
                    "kind": "interpret", "tone": tone, "sender": leader.id,
                    "clan_id": cid or None, "born_tick": self.tick, "ttl": 15,
                })

    def _update_politics(self) -> None:
        """§AB orchestrator — fixed order keeps the rng stream deterministic."""
        self._update_coalitions()
        self._update_leader_decisions()
        self._update_larders()
        self._update_trade_caravans()
        self._update_festivals_and_traditions()
        self._update_defection()
        self._update_clan_task_boards_and_bylaws()
        self._update_diplomacy()  # §AN envoys, markets, dialects & omens



    # ------------------------------------------------- §AC desperation cannibalism
    @staticmethod
    def _is_weak_prey(o: Creature) -> bool:
        """Starving, elder or wounded — the weak are legitimate prey (§AC)."""
        return o.status == "starving" or o.stage == "elder" or o.health < 50.0

    def _cannibal_prey(self, c: Creature, radius: float) -> Creature | None:
        """Nearest eligible living prey for a starving creature (§AC).

        Eligible: enemy-clan members (negative relation) and the weak of any
        clan. Never predators, wild beasts, healthy same-clan adults, infants
        or anyone safe indoors — roofs are sanctuary.
        """
        cfg = self.config
        best: Creature | None = None
        best_d = radius + 1e-9
        for o in self.world.query_radius(c.x, c.y, radius):
            if not isinstance(o, Creature) or o.id == c.id:
                continue
            if o.id not in self.world.entities:
                continue
            if o.is_predator or o.is_herbivore or o.indoors:
                continue  # the Carnivore is never prey; roofs are sanctuary
            if o.stage == "infant":
                continue
            kin = bool(c.clan_id) and o.clan_id == c.clan_id
            weak = self._is_weak_prey(o)
            if kin:
                # only desperate need applies, and only when god allows it
                if not cfg.eat_kin_enabled or not weak:
                    continue
                # §AP: the Cosmic Scales keep the law even while starving —
                # eating kin is a crime their dogma refuses.
                if self._totem_stat(c, "lawful"):
                    continue
            else:
                if not cfg.eat_enemy_enabled:
                    continue
                if not weak:
                    pair = self._relation_pair(c.clan_id, o.clan_id) if c.clan_id and o.clan_id else None
                    rel = self.relations.get(pair, 0) if pair else 0
                    if rel >= 0 or not c.clan_id or not o.clan_id:
                        continue  # strangers must be rivals to be on the menu
            d = self.world.distance(c.x, c.y, o.x, o.y)
            if d < best_d:
                best, best_d = o, d
        return best

    def _exile_kin_eater(self, eater: Creature) -> None:
        """§AC The price of kin-eating — cast out, remembered, warred upon."""
        cfg = self.config
        former = eater.clan_id
        if not former:
            return
        if cfg.exile_on_kin_eat:
            band = self._new_clan(eater)  # a one-being outcast band
            eater.clan_id = band
            stigma = max(1, int(cfg.kin_stigma))
            pair = self._relation_pair(former, band)
            score = -stigma
            self.relations[pair] = max(-100, min(100, score))
            zone = self._zone_of(score)
            if zone != 0:
                self._relation_zones[pair] = zone
            # witnesses remember the outcast band as an enemy (§X knowledge)
            for m in self.world.query_radius(eater.x, eater.y, TREASON_RADIUS):
                if isinstance(m, Creature) and m.clan_id == former:
                    self._learn_enemy(m, band)
            self._emit(
                HistoryEvent(
                    type="exile",
                    tick=self.tick + 1,
                    entity_id=eater.id,
                    caste=eater.caste,
                    x=round(eater.x, 2),
                    y=round(eater.y, 2),
                    payload={
                        "former_clan": former,
                        "band": band,
                        "former_name": self.clans.get(former, {}).get("name"),
                        "personal_name": personal_name_for(eater.id, self.config.seed, eater.generation),
                        "glyph": glyph_for(eater.id, self.config.seed, eater.generation),
                    },
                )
            )

    def _do_cannibalism(self, eater: Creature, prey: Creature) -> None:
        """§AC Kill & feed — contact kill, partial corpse, exile for kin-eaters."""
        cfg = self.config
        kin = bool(eater.clan_id) and prey.clan_id == eater.clan_id
        eater.cannibal_cooldown = CANNIBAL_COOLDOWN
        eater.energy = min(cfg.energy_max, eater.energy + cfg.cannibalism_energy)
        eater.meals += 1
        self._kill(prey, "cannibalism", corpse_energy_mult=CANNIBAL_CORPSE_MULT)
        self._emit(
            HistoryEvent(
                type="cannibalism",
                tick=self.tick + 1,
                entity_id=eater.id,
                caste=eater.caste,
                x=round(prey.x, 2),
                y=round(prey.y, 2),
                payload={"prey": prey.id, "prey_caste": prey.caste, "kin": kin},
            )
        )
        # §AR S-5: reputation is observable — witnesses shun the man-eater.
        pr_sq = cfg.perceive_radius * cfg.perceive_radius
        for o in self._get_creatures():
            if o.id == eater.id:
                continue
            if o.clan_id and o.clan_id == eater.clan_id:
                continue
            if self.world.distance_sq(o.x, o.y, eater.x, eater.y) <= pr_sq:
                if not hasattr(o, "trust") or o.trust is None:
                    o.trust = {}
                o.trust[eater.id] = max(-100.0, o.trust.get(eater.id, 0.0) - 20.0)
        if kin:
            self._exile_kin_eater(eater)

    def _update_fires(self) -> None:
        """§S Wildfire — ignites via storm lightning / fire_rate, spreads, kills."""
        cfg = self.config
        if not cfg.wildfire_enabled:
            # decay existing fires even when disabled? keep them fading
            self.fires = [f for f in self.fires if f["ttl"] > 1]
            for f in self.fires:
                f["ttl"] -= 1
            return
        # Decay
        new_fires = []
        for f in self.fires:
            f["ttl"] -= 1
            if f["ttl"] > 0:
                new_fires.append(f)
            else:
                # ash fertilizes nearby plants (nutrient boost)
                for e in self.world.query_radius(f["x"], f["y"], 8.0):
                    if isinstance(e, Food):
                        e.growth = min(1.0, e.growth + 0.15)
        self.fires = new_fires
        # Ignition: storm lightning or random fire_rate — §AQ PH-2: buildings
        # and groves DOWNWIND of the flames catch first.
        ignite_chance = cfg.fire_rate
        if self.weather == "storm":
            ignite_chance = max(ignite_chance, 0.002)  # lightning
        if self.rng.random() < ignite_chance:
            foods = [e for e in (self._cached_foods or self.world.entities.values()) if isinstance(e, Food) and e.growth > 0.5]
            if foods:
                wx, wy = self._cos_wind, self._sin_wind
                f0 = max(self.fires, key=lambda f: f["r"]) if self.fires else None

                def tailwind(e: Entity) -> float:
                    if f0 is None:
                        return 1.0
                    d = self.world.distance(f0["x"], f0["y"], e.x, e.y) or 1.0
                    return 1.0 + WIND_FIRE_MULT * self.wind_speed * max(
                        0.0, ((e.x - f0["x"]) / d) * wx + ((e.y - f0["y"]) / d) * wy
                    )

                victim = max(foods, key=lambda e: (self.rng.random() ** (1.0 / tailwind(e)), -e.id))
                self.fires.append({"x": victim.x, "y": victim.y, "r": 3.0, "ttl": 28})
                self.world.remove(victim.id)
                self._emit(HistoryEvent(type="fire", tick=self.tick+1, entity_id=0, x=round(victim.x,2), y=round(victim.y,2), payload={"kind": "ignite", "r": 3.0}))
        # Spread to neighboring plants — faster downwind (§AQ PH-2)
        if self.fires and self.rng.random() < cfg.fire_spread_rate * len(self.fires):
            wx, wy = self._cos_wind, self._sin_wind
            for f in list(self.fires):
                for e in self.world.query_radius(f["x"], f["y"], 6.0):
                    if not isinstance(e, Food):
                        continue
                    d = self.world.distance(f["x"], f["y"], e.x, e.y) or 1.0
                    tailwind = max(0.0, ((e.x - f["x"]) / d) * wx + ((e.y - f["y"]) / d) * wy)
                    chance = 0.35 * (1.0 + WIND_FIRE_MULT * self.wind_speed * tailwind)
                    if self.rng.random() < min(0.9, chance):
                        self.fires.append({"x": e.x, "y": e.y, "r": 2.5, "ttl": 22})
                        self.world.remove(e.id)
                        break
        # Burn creatures and plants within fire radius
        for f in list(self.fires):
            for e in self.world.query_radius(f["x"], f["y"], f["r"] + 1.2):
                if isinstance(e, Creature) and e.id in self.world.entities:
                    if self.rng.random() < 0.18:
                        self._kill(e, "fire")
                elif isinstance(e, Food) and e.id in self.world.entities:
                    if self.world.distance(e.x, e.y, f["x"], f["y"]) < f["r"] and self.rng.random() < 0.25:
                        self.world.remove(e.id)
            # §AQ PH-1: radiant heat beyond the flame core — the fire warms the
            # winter grove AND cooks whoever lingers too close (double-edged).
            scald_r = f["r"] + FIRE_SCALD_RADIUS
            for e in self.world.query_radius(f["x"], f["y"], scald_r):
                if not isinstance(e, Creature) or e.id not in self.world.entities:
                    continue
                d = self.world.distance(e.x, e.y, f["x"], f["y"])
                if d <= f["r"] + 1.2:
                    continue  # core burn handled above
                frac = 1.0 - (d - f["r"]) / FIRE_SCALD_RADIUS
                dmg = FIRE_SCALD_DAMAGE * max(0.0, frac)
                if dmg <= 0 or self.rng.random() >= 0.5:
                    continue
                if e.health - dmg <= 0:
                    self._kill(e, "hyperthermia")
                else:
                    e.health -= dmg
            # also burn houses? small chance to ignite house (is_ruin)
            for h in (self._cached_houses if self._cached_houses else self._functional_houses()):
                if not h.is_ruin and self.world.distance(h.x, h.y, f["x"], f["y"]) < f["r"] + h.size/2:
                    if self.rng.random() < 0.03:
                        h.is_ruin = True
                        h.clan_id = 0
                        h.clan_color = None
                        self._emit(HistoryEvent(type="fire", tick=self.tick+1, entity_id=h.id, x=round(h.x,2), y=round(h.y,2), payload={"kind": "house_burn"}))

    def _update_campfires(self) -> None:
        """§AO Phase E: stranded explorers caught far from home at nightfall
        gather dry brush and light a field campfire — a small circle of light
        and warmth that repels predators and burns until dawn."""
        tod = self._time_of_day()
        if not self._is_night(tod):
            if self.campfires:
                self.campfires = []  # dawn: the fires go cold
            return
        if len(self.campfires) >= 12:
            return
        for c in self._get_creatures():
            if c.personality != "explorer" or c.is_predator or c.is_herbivore:
                continue
            if c.indoors or c.sleeping:
                continue
            if self.rng.random() >= CAMPFIRE_KINDLE_CHANCE:
                continue
            # stranded means far from any roof (own clan's or neutral)
            stranded = True
            for h in self._cached_houses:
                hh = cast(House, h)
                if not hh.is_ruin and self.world.distance(c.x, c.y, hh.x, hh.y) < 24.0:
                    stranded = False
                    break
            if not stranded:
                continue
            # no fire already burning nearby
            too_close = False
            for cf in self.campfires:
                if (cf["x"] - c.x) ** 2 + (cf["y"] - c.y) ** 2 < 64.0:
                    too_close = True
                    break
            if too_close:
                continue
            self.campfires.append({"x": round(c.x, 2), "y": round(c.y, 2), "day": self.day})
            c.emote = "craft"
            c.emote_ticks = 15

    def _update_disasters(self) -> None:
        """§S Disaster laws — meteor/flood stochastic, gated by disaster_rate."""
        cfg = self.config
        if not cfg.disaster_enabled or cfg.disaster_rate <= 0:
            return
        if self.rng.random() >= cfg.disaster_rate:
            return
        kind = self.rng.choice(["meteor", "flood"])
        cx, cy = self._rand_pos()
        r = self.rng.uniform(6, 12) if kind == "meteor" else self.rng.uniform(10, 18)
        if kind == "meteor":
            # crater kills, removes plants, adds rock
            self.rocks.append({"x": cx, "y": cy, "r": r*0.6})
            for e in list(self.world.entities.values()):
                if self.world.distance(e.x, e.y, cx, cy) < r:
                    if isinstance(e, Creature) and self.rng.random() < 0.85:
                        self._kill(e, "disaster")
                    elif isinstance(e, Food) and self.rng.random() < 0.9:
                        self.world.remove(e.id)
            self._emit(HistoryEvent(type="disaster", tick=self.tick+1, entity_id=0, x=round(cx,2), y=round(cy,2), payload={"kind": "meteor", "r": round(r,2)}))
        else:
            # flood: pushes creatures, drowns some, washes plants?
            for e in list(self.world.entities.values()):
                if self.world.distance(e.x, e.y, cx, cy) < r:
                    if isinstance(e, Creature):
                        # push out
                        ang = self.rng.uniform(0, 2*3.14159)
                        e.x, e.y = self.world.normalize(cx + math.cos(ang)*(r+2), cy + math.sin(ang)*(r+2))
                        if self.rng.random() < 0.15:
                            self._kill(e, "disaster")
                    elif isinstance(e, Food) and self.rng.random() < 0.4:
                        self.world.remove(e.id)
            self._emit(HistoryEvent(type="disaster", tick=self.tick+1, entity_id=0, x=round(cx,2), y=round(cy,2), payload={"kind": "flood", "r": round(r,2)}))

    def _update_clan_specialization(self) -> None:
        """§P Clan specialization — drift toward warrior/farmer/scavenger."""
        # AF: slice the history deque once before the clan loop; was O(history_len × num_clans)
        import itertools
        recent = list(itertools.islice(reversed(self.history), 80))
        # AF: build clan→house map from the house cache (avoids entity scan per clan)
        house_by_clan: dict[int, House] = {}
        for h in self._cached_houses:
            if isinstance(h, House) and h.clan_id and h.clan_id not in house_by_clan:
                house_by_clan[h.clan_id] = h
        for cid, info in self.clans.items():
            spec = info.get("specialization")
            if spec is None:
                spec = {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34}
                info["specialization"] = spec
            # totem bias already in founding; now environment drift
            house = house_by_clan.get(cid)
            # count recent war involvement (last 80 history)
            war_cnt = sum(1 for ev in recent if ev.type == "war" and (ev.payload.get("a") == cid or ev.payload.get("b") == cid))
            # count food/corpse near house (if has house)
            food_near = 0
            corpse_near = 0
            if house is not None:
                for e in self.world.query_radius(house.x, house.y, 18.0):
                    if e.kind == "food":
                        food_near += 1
                    elif e.kind == "corpse":
                        corpse_near += 1
                for fp in self.fertile:
                    if self.world.distance_sq(fp["x"], fp["y"], house.x, house.y) < 400.0:
                        food_near += 1
            # small drift per tick
            # warrior up if wars, farmer up if food_near, scavenger up if corpse_near
            # normalize drift to keep sum 1
            drift = 0.002
            if war_cnt > 0:
                spec["warrior"] = min(0.8, spec["warrior"] + drift * war_cnt)
            if food_near > 3:
                spec["farmer"] = min(0.8, spec["farmer"] + drift * 0.5)
            if corpse_near > 2:
                spec["scavenger"] = min(0.8, spec["scavenger"] + drift * 0.7)
            # slight decay toward 0.33 to avoid lock-in, plus random jitter
            for k in ("warrior", "farmer", "scavenger"):
                spec[k] += self.rng.uniform(-0.0005, 0.0005)
                spec[k] = max(0.05, min(0.85, spec[k]))
            # renormalize to 1
            tot = spec["warrior"] + spec["farmer"] + spec["scavenger"]
            for k in spec:
                spec[k] = round(spec[k] / tot, 3)

    def clan_knowledge(self) -> dict[int, dict]:
        """§X Clan memory — union of member knowledge: 'the clan remembers'."""
        ttl = max(1, self.config.knowledge_ttl)
        out: dict[int, dict] = {}
        clan_creatures = self._clan_members if self._clan_members else {}
        if not clan_creatures:
            for m in self._get_creatures():
                if m.clan_id:
                    clan_creatures.setdefault(m.clan_id, []).append(m)
        # §P0: only alive clans carry memory — dead clans bloat payloads
        alive_for_know = set(self._clan_members.keys()) if self._clan_members else {c.clan_id for c in self._get_creatures() if c.clan_id}
        for cid in alive_for_know:
            enemies: set[int] = set()
            danger: list[dict] = []
            food: list[dict] = []
            safe_spots = 0
            for m in clan_creatures.get(cid, ()):
                for clan_id, meta in (m.facts.get("enemies") or {}).items():
                    if isinstance(meta, dict) and self.tick - int(meta.get("tick", 0)) <= ttl:
                        enemies.add(int(clan_id))
                for kind, sink in (("danger", danger), ("food", food)):
                    f = self._fact_fresh(m, kind)
                    if f is None or "x" not in f or len(sink) >= 6:
                        continue
                    if any(
                        math.hypot(f["x"] - e["x"], f["y"] - e["y"]) < 2.0
                        for e in sink
                    ):
                        continue  # same spot another member already reported
                    sink.append({"x": f["x"], "y": f["y"], "conf": f["conf"]})
                if self._fact_fresh(m, "safe") is not None:
                    safe_spots += 1
            enemies.discard(cid)
            out[cid] = {
                "enemy_clans": sorted(enemies),
                "danger_zones": danger,
                "food_spots": food,
                "members_with_home_knowledge": safe_spots,
            }
        return out

    def get_plots(self) -> list[dict]:
        """§S Plots — upcoming war/schism as progress 0..10 for god observability."""
        plots = []
        # AA: shared lookups computed once per call (clan_knowledge was
        # re-computed PER RIVAL PAIR; membership scanned per clan).
        knowledge = self.clan_knowledge() if self.config.knowledge_enabled else {}
        members_by_clan: dict[int, list[Creature]] = {}
        for c in self._get_creatures():
            if c.clan_id:
                members_by_clan.setdefault(c.clan_id, []).append(c)
        # war plots: rival pairs with members near each other
        for (a,b), score in self.relations.items():
            if self._zone_of(score) != -1:
                continue
            # need members of both clans
            a_members = members_by_clan.get(a, [])
            b_members = members_by_clan.get(b, [])
            if not a_members or not b_members:
                continue
            # closest pair distance
            min_d = min(self.world.distance(ac.x, ac.y, bc.x, bc.y) for ac in a_members for bc in b_members)
            # progress: base from how rival they are + proximity; clans that
            # remember each other as enemies plot faster (§X clan memory)
            memory_bonus = 0
            if self.config.knowledge_enabled:
                ka = knowledge.get(a, {}).get("enemy_clans", [])
                kb = knowledge.get(b, {}).get("enemy_clans", [])
                if b in ka or a in kb:
                    memory_bonus = 2
            base = max(0, (-score - self.config.rivalry_threshold) // 8) + memory_bonus  # 0..8
            prox = 0
            if min_d < self.config.attack_radius * 3:
                prox = 4
            elif min_d < self.config.flock_radius * 2:
                prox = 2
            prog = min(10, int(base + prox + (self.tick % 10)/10))
            if prog > 0:
                plots.append({"type": "war", "a": a, "b": b, "a_name": self.clans.get(a, {}).get("name"), "b_name": self.clans.get(b, {}).get("name"), "progress": prog, "max": 10, "distance": round(min_d,1)})
        # schism plots: clans approaching schism threshold
        if self.config.schism_enabled:
            claimed_houses = {h.clan_id for h in (self._cached_houses if self._cached_houses else self._functional_houses()) if h.clan_id}
            for cid, info in self.clans.items():
                members = members_by_clan.get(cid, [])
                pop = len(members)
                if pop < self.config.schism_min_pop:
                    continue
                has_house = cid in claimed_houses
                unhappy = sum(1 for c in members if c.energy / self.config.energy_max <= self.config.starving_ratio or not has_house)
                frac = unhappy / pop if pop else 0
                if frac >= self.config.schism_threshold * 0.5:  # show even half-way
                    prog = min(10, int(frac / self.config.schism_threshold * 6 + 2))
                    plots.append({"type": "schism", "a": cid, "a_name": info.get("name"), "progress": prog, "max": 10, "unhappy": unhappy, "pop": pop})
        return plots

    def _update_culture(self) -> None:
        """§S Culture drift — spreads to neighbours, can split into rival traditions."""
        cfg = self.config
        if not cfg.culture_enabled:
            return
        # spread: allies within territory may adopt same culture
        if self.rng.random() < cfg.culture_spread_rate:
            # pick random allied pair
            allies = [pair for pair, score in self.relations.items() if self._zone_of(score)==1]
            if allies:
                a,b = self.rng.choice(allies)
                # decide direction: a adopts b's culture or vice versa
                ca = self.clans.get(a, {}).get("culture_id")
                cb = self.clans.get(b, {}).get("culture_id")
                if ca is not None and cb is not None and ca != cb:
                    # 50% chance a adopts b
                    if self.rng.random() < 0.5:
                        # a adopts b's culture
                        self.clans[a]["culture"] = self.clans[b].get("culture", "")
                        self.clans[a]["culture_id"] = cb
                    else:
                        self.clans[b]["culture"] = self.clans[a].get("culture", "")
                        self.clans[b]["culture_id"] = ca
        # split: small chance a clan's culture diverges (like schism but culture only)
        for cid, info in list(self.clans.items()):
            if self.rng.random() < 0.0004:  # rare
                new_culture = f"{self.rng.choice(CULTURE_ADJECTIVES)} {self.rng.choice(CULTURE_NOUNS)}"
                info["culture"] = new_culture
                info["culture_id"] = self._next_clan_id + 1000 + cid  # new id distinct
                self._emit(HistoryEvent(type="culture", tick=self.tick+1, entity_id=0, x=0, y=0, payload={"clan_id": cid, "culture": new_culture}))

    # ------------------------------------------------------------------ flora
    def _update_plants(self) -> None:
        """§H: every plant grows toward maturity; the mature ones spread. §O variant rhythms. §R weather waters/damages. §AE mature plants wither.
        §AQ PH-0: growth rides sunlight — the day cycle is the world's income."""
        cfg = self.config
        sun = self._sun_factor()
        tod = self._time_of_day()
        # §AQ PH-10: precompute roof shadows (cast west, the sun stands east)
        shadow_rects: list[tuple[float, float, float, float]] = []
        for h in (self._cached_houses or self._functional_houses()):
                ext = h.size * SHADOW_LENGTH
                shadow_rects.append((
                    h.x - h.size / 2 - ext, h.x - h.size / 2,
                    h.y - h.size / 2, h.y + h.size / 2,
                ))
        if cfg.plant_growth_rate > 0 and sun > 0.0:
            season = self._season()
            summer_drought = season == "summer"
            winter = season == "winter"
            for e in self.world.entities.values():
                if isinstance(e, Food) and e.growth < 1.0:
                    if cfg.plant_variants_enabled:
                        vm = VARIANT_GROWTH_MULT.get(e.variant, 1.0)
                        sm = VARIANT_SEASON_MULT.get(e.variant, {}).get(season, 1.0)
                    else:
                        vm, sm = 1.0, 1.0
                    wm = 1.0
                    if self.weather in ("rain", "storm"):
                        wm = cfg.rain_growth_mult
                    elif self.weather == "fog" and e.variant == "mushroom":
                        wm = cfg.fog_mushroom_mult
                    # §AM B: sown crops outrun the wild weeds; furrows hold moisture
                    if e.cultivated:
                        vm *= CULTIVATED_GROWTH_MULT
                        if e.irrigated:
                            vm *= IRRIGATED_GROWTH_MULT
                            wm = max(wm, 1.0)  # drought-proof through the dry heat
                    # §AQ PH-5: roots contest the soil; symbiosis tips the balance.
                    # Mature neighbours crowd the sprout, corpses feed mushrooms,
                    # berries shelter herbs, toxins stunt everything near.
                    near_mature = 0
                    corpse_near = False
                    berry_near = False
                    poison_near = False
                    for o in self.world.query_radius(e.x, e.y, SYMBIOSIS_RADIUS):
                        if o.id == e.id or o.id not in self.world.entities:
                            continue
                        if isinstance(o, Food):
                            if o.growth >= 1.0:
                                if o.variant == "poisonous":
                                    poison_near = True
                                elif (
                                    cfg.plant_variants_enabled
                                    and e.variant == "medicinal_herb"
                                    and o.variant == "berry"
                                ):
                                    berry_near = True  # thicket shelter, not rivalry
                                else:
                                    near_mature += 1
                        elif isinstance(o, Corpse):
                            corpse_near = True
                    eco_mult = 1.0 / (1.0 + ROOT_COMPETITION * near_mature)
                    if cfg.plant_variants_enabled:
                        if e.variant == "mushroom" and corpse_near:
                            eco_mult *= MUSHROOM_CORPSE_MULT
                        elif e.variant == "medicinal_herb" and berry_near:
                            eco_mult *= HERB_BERRY_MULT
                        if poison_near and e.variant != "poisonous":
                            eco_mult *= POISON_SUPPRESS
                    # §AQ PH-10: fertile anomalies grow strange and lush
                    if self.anomalies and self._anomaly_at(e.x, e.y, "fertile"):
                        eco_mult *= ANOMALY_GROWTH_MULT
                    # §AQ PH-10: roofs shade the ground west of them —
                    # shade-starved sprouts grow slower
                    for sh in shadow_rects:
                        if sh[0] <= e.x <= sh[1] and sh[2] <= e.y <= sh[3]:
                            eco_mult *= SHADOW_GROWTH_MULT
                            break
                    # §AQ PH-10: dawn light sweeps in from the east edge,
                    # dusk from the west — the rim gets a brief bonus
                    if (
                        (0.22 < tod < 0.30 and e.x > cfg.width - SUN_EDGE_BAND)
                        or (0.70 < tod < 0.78 and e.x < SUN_EDGE_BAND)
                    ):
                        eco_mult *= SUN_EDGE_GROWTH_MULT
                    # §AQ PH-3: fresh silt on the banks feeds the next harvest
                    for rv in self.rivers:
                        if (
                            rv["silt_ticks"] > 0
                            and self._river_dy(e.y, rv["cy"]) <= rv["hw"] + RIVER_SILT_RADIUS
                        ):
                            eco_mult *= RIVER_SILT_MULT
                            break
                    # §AQ PH-4: packed earth grows nothing — roads starve the field
                    if cfg.relief_enabled:
                        tcol = min(self._temp_cols - 1, max(0, int(e.x / cfg.width * self._temp_cols)))
                        trow = min(self._temp_rows - 1, max(0, int(e.y / cfg.height * self._temp_rows)))
                        traffic = self.traffic_grid[trow * self._temp_cols + tcol]
                        if traffic >= TRAFFIC_PLANT_BLOCK:
                            eco_mult = 0.0
                        elif traffic > 0:
                            eco_mult *= max(0.25, 1.0 - traffic / TRAFFIC_PLANT_BLOCK)
                    # §AM D: the soil gives what the soil has
                    soil = self._soil_at(e.x, e.y)
                    soil_f = max(0.5, min(1.4, 0.55 + 0.45 * soil))
                    age_now = self._age()
                    am = 0.75 if age_now == "Ice" else (1.25 if age_now == "Golden" else 1.0)
                    gained = min(
                        1.0 - e.growth,
                        cfg.plant_growth_rate * vm * sm * wm * am * sun * soil_f * eco_mult,
                    )
                    e.growth += gained
                    self._deplete_soil(e.x, e.y, gained)  # the harvest draws on the land
                    if e.growth >= 1.0:
                        self._emit_bloom(e)
        # §AM C.2: winter frost bites exposed crops — cultivated beds & irrigated
        # furrows shrug it off; everything else in the open fields suffers.
        if (
            cfg.agriculture_enabled
            and self._season() == "winter"
            and WINTER_FROST_CHANCE > 0
        ):
            for e in list(self.world.entities.values()):
                if not isinstance(e, Food) or e.cultivated or e.irrigated:
                    continue
                if e.growth < 0.3:
                    continue  # sprouts sleep under the snow
                if self.rng.random() < WINTER_FROST_CHANCE:
                    e.growth = max(0.0, e.growth - self.rng.uniform(0.15, 0.4))
                    if e.growth <= 0.05:
                        self.world.remove(e.id)
        # §AE Food decay — a mature plant lives food_lifespan_ticks × its
        # variant's pace, wilts near the end, fertilises, then vanishes.
        # Sprouts and growing plants don't rot; only the harvest does.
        if cfg.food_decay_enabled and cfg.food_lifespan_ticks > 0:
            for e in list(self.world.entities.values()):
                if not isinstance(e, Food) or e.growth < 1.0:
                    continue
                life = max(1, round(cfg.food_lifespan_ticks * FOOD_LIFESPAN_MULT.get(e.variant, 1.0)))
                e.mature_ticks = (getattr(e, "mature_ticks", 0) or 0) + 1
                if e.mature_ticks >= life:
                    self._release_nutrients(e, mult=WITHER_NUTRIENT_MULT)  # death feeds life
                    self.world.remove(e.id)
                    self._emit(
                        HistoryEvent(
                            type="wither",
                            tick=self.tick + 1,
                            entity_id=e.id,
                            x=round(e.x, 2),
                            y=round(e.y, 2),
                            payload={"variant": e.variant, "age": e.mature_ticks},
                        )
                    )
        # Storm damage: exposed plants stripped, occasionally uprooted (§R);
        # §AM: furrowed beds hold their soil — irrigation shelters them.
        if self.weather == "storm" and cfg.storm_plant_damage > 0:
            for e in list(self.world.entities.values()):
                if not isinstance(e, Food) or e.irrigated:
                    continue
                if self.rng.random() < cfg.storm_plant_damage:
                    e.growth = max(0.0, e.growth - self.rng.uniform(0.2, 0.5))
                    if e.growth <= 0.05 and self.rng.random() < 0.5:
                        self.world.remove(e.id)
        if cfg.plant_spread_rate > 0 and sun > 0.0:
            target = round(cfg.food_count * _season_food_mult(self._season(), cfg.winter_food_mult))
            total = sum(1 for e in self.world.entities.values() if e.kind == "food")
            wx, wy = self._cos_wind, self._sin_wind
            seed_blend = min(0.7, WIND_SEED_BIAS * self.wind_speed)
            for parent in list(self.world.entities.values()):
                if not isinstance(parent, Food) or parent.growth < 1.0:
                    continue  # only mature plants carry seeds
                if self.rng.random() >= cfg.plant_spread_rate * sun:
                    continue
                if total >= target:
                    continue  # the land holds exactly god's seasonal bounty
                ang = self.rng.uniform(0, 2 * math.pi)
                rad = self.rng.uniform(0, SPREAD_RADIUS)
                # §AQ PH-2: seeds ride the wind — the drift bends downwind, so
                # groves creep with the prevailing breeze and upwind ground
                # stays clear.
                vx = math.cos(ang) * (1.0 - seed_blend) + wx * seed_blend
                vy = math.sin(ang) * (1.0 - seed_blend) + wy * seed_blend
                norm = math.hypot(vx, vy) or 1.0
                x, y = self.world.normalize(
                    parent.x + vx / norm * rad,
                    parent.y + vy / norm * rad,
                )
                if (
                    not self._is_in_rock(x, y)
                    and not (self.rivers and self._in_river_band(x, y, pad=1.0))
                    and not self._is_point_inside_any_house(x, y, pad=0.8)
                ):
                    self.world.add(self._new_food(x, y, growth=SPROUT_GROWTH))
                    total += 1

    def _emit_bloom(self, plant: Food) -> None:
        """A plant has reached maturity: recorded in the chronicle."""
        self._emit(
            HistoryEvent(
                type="bloom",
                tick=self.tick + 1,
                entity_id=plant.id,
                x=round(plant.x, 2),
                y=round(plant.y, 2),
                payload={"x": round(plant.x, 2), "y": round(plant.y, 2), "variant": plant.variant},
            )
        )

    def _update_corpses(self) -> None:
        """Corpses rot away once their ttl runs out — and death feeds life."""
        if not self.config.corpses_enabled:
            return
        # AF: iterate pre-built corpse cache — no full entity scan needed
        for e in list(self._cached_corpses):
            e.ttl -= 1
            if e.ttl <= 0:
                self._release_nutrients(e)
                self.world.remove(e.id)

    # ------------------------------------------------------------ §AM agriculture
    def _ensure_farm_plots(self) -> None:
        """§AM B.1: settled clans till FARM_PLOTS_PER_CLAN plots around their
        main house. Plots near a fertile grove are furrow-irrigated (drought-
        and frost-proof). Deterministic ring angles; never touches the rng."""
        if not self.config.agriculture_enabled or self.tick % 120 != 0:
            return
        living = {c.clan_id for c in self._get_creatures() if c.clan_id}
        # prune plots of dead clans
        self.farm_plots = {cid: p for cid, p in self.farm_plots.items() if cid in living}
        r = max(6.0, self.config.territory_radius * 0.55)
        for cid in sorted(self.clans.keys()):
            hid = self.clans[cid].get("main_house_id")
            house = self.world.entities.get(hid) if hid is not None else None
            if not isinstance(house, House):
                continue
            plots = self.farm_plots.setdefault(cid, [])
            k = len(plots)
            while k < FARM_PLOTS_PER_CLAN:
                ang = (cid * 2.399 + k * 2.094) % (2 * math.pi)
                px, py = self.world.normalize(
                    house.x + math.cos(ang) * r, house.y + math.sin(ang) * r
                )
                if not self._is_in_rock(px, py):
                    irrigated = any(
                        self.world.distance(px, py, f["x"], f["y"]) <= f["r"] + 3.0
                        for f in self.fertile
                    )
                    plots.append({"x": round(px, 2), "y": round(py, 2), "irrigated": irrigated})
                k += 1

    def _sow_and_tend(self) -> None:
        """§AM B: farmers sow seed pouches into empty clan plots; skilled hands
        weed toxic sprouts, tend the beds against premature withering, and
        compost near the settlement to revive exhausted soil."""
        if not self.config.agriculture_enabled:
            return
        main_houses: dict[int, House] = {}
        for h in self._cached_houses:
            if isinstance(h, House) and h.clan_id and not h.is_ruin:
                main_houses.setdefault(h.clan_id, h)
        for c in self._get_creatures():
            if c.is_predator or c.is_herbivore or c.sleeping:
                continue
            farm_xp = float(getattr(c, "skills", {}).get("farming", 0.0))
            # — sowing —
            if (
                c.seeds > 0
                and c.clan_id
                and farm_xp >= SEED_SKILL_MIN
                and self.rng.random() < 0.5
            ):
                plot = next(
                    (
                        p for p in self.farm_plots.get(c.clan_id, ())
                        if self.world.distance_sq(c.x, c.y, p["x"], p["y"]) <= 9.0
                        and not any(
                            isinstance(f, Food)
                            and f.id in self.world.entities
                            and self.world.distance_sq(f.x, f.y, p["x"], p["y"]) <= 1.0
                            for f in (self._cached_foods if self._cached_foods is not None else [e for e in self.world.entities.values() if isinstance(e, Food)])
                        )
                    ),
                    None,
                )
                if plot is not None:
                    c.seeds -= 1
                    variant = "grain" if self.rng.random() < 0.7 else "grass"
                    crop = Food(x=plot["x"], y=plot["y"], growth=SPROUT_GROWTH,
                                variant=variant, cultivated=True,
                                irrigated=bool(plot.get("irrigated")))
                    self.world.add(crop)
                    c.skills["farming"] = farm_xp + 1.0
            # — tending & weeding & compost (staggered per creature) —
            if farm_xp < TEND_SKILL_MIN or (self.tick + c.id) % 9 != 0:
                continue
            for e, _ in self.world.query_radius_with_dist_sq(c.x, c.y, 4.0):
                if isinstance(e, Food):
                    if e.variant == "poisonous" and e.growth < 0.5:
                        self.world.remove(e.id)  # weeded out before it can harm
                    elif e.cultivated:
                        e.mature_ticks = max(0, e.mature_ticks - TEND_REGRESS_TICKS)
            # composting: master farmers refresh the home soil on a long cadence
            if (
                farm_xp >= 12.0
                and c.clan_id in main_houses
                and COMPOST_INTERVAL > 0
                and (self.tick + c.id * 7) % COMPOST_INTERVAL == 0
            ):
                mh = main_houses[c.clan_id]
                if self.world.distance(c.x, c.y, mh.x, mh.y) <= self.config.territory_radius:
                    self._fertilize_soil(mh.x, mh.y, 10.0, COMPOST_NUTRIENT)
                    self._emit(
                        HistoryEvent(
                            type="compost",
                            tick=self.tick + 1,
                            entity_id=c.id,
                            caste=c.caste,
                            x=round(mh.x, 2), y=round(mh.y, 2),
                            payload={"clan_id": c.clan_id,
                                     "clan_name": self.clans.get(c.clan_id, {}).get("name")},
                        )
                    )

    def _update_agriculture(self) -> None:
        """§AM orchestrator — fixed order keeps the rng stream deterministic."""
        self._ensure_farm_plots()
        self._sow_and_tend()
        self._update_banquets()

    def _update_banquets(self) -> None:
        """§AM E.2: an overflowing granary feeds a clan feast — morale, bonds
        and a baby boom while the mead lasts."""
        if not (self.config.banquets_enabled and self.config.granaries_enabled):
            return
        if self.tick % 60 != 0:
            return
        houses_by_clan: dict[int, House] = {}
        for h in self._cached_houses:
            if isinstance(h, House) and h.clan_id and not h.is_ruin:
                houses_by_clan.setdefault(h.clan_id, h)
        for cid in sorted(self.clans.keys()):
            info = self.clans[cid]
            granary = float(info.get("granary", 0.0))
            cap = max(1.0, self.config.granary_capacity)
            if granary < cap * BANQUET_FILL_FRACTION:
                continue
            if self.tick - int(self._banquet_last.get(cid, -BANQUET_MIN_GAP)) < BANQUET_MIN_GAP:
                continue
            house = houses_by_clan.get(cid)
            if house is None:
                continue
            cost = granary * BANQUET_COST_FRACTION
            info["granary"] = granary - cost
            info["feast_until"] = self.tick + BANQUET_FEAST_TICKS
            self._banquet_last[cid] = self.tick
            guests: set[int] = set()  # clans present at the table (incl. cid)
            for m in self._clan_members.get(cid, ()):
                if self.world.distance(m.x, m.y, house.x, house.y) <= self.config.territory_radius:
                    guests.add(m.clan_id)
                    m.energy = min(self.config.energy_max, m.energy + 12.0)
                    m.emote = "cheer"
                    m.emote_ticks = 40
            for other_cid in sorted(guests):
                if other_cid != cid:
                    self._bump_relation(other_cid, cid, 4)
            self._emit(
                HistoryEvent(
                    type="banquet",
                    tick=self.tick + 1,
                    entity_id=house.id,
                    x=round(house.x, 2), y=round(house.y, 2),
                    payload={"clan_id": cid, "clan_name": info.get("name"),
                             "spent": round(cost, 1)},
                )
            )


    def _release_nutrients(self, corpse: Entity, mult: float = 1.0) -> None:
        """A fully decayed corpse (or withered plant, §AE) boosts nearby plant growth."""
        boost = NUTRIENT_BOOST * self.config.nutrient_cycle_rate * mult
        if boost <= 0:
            return
        # §AM D.2: death also refills the living soil grid — the field remembers.
        if self.config.soil_depletion_enabled:
            self._fertilize_soil(corpse.x, corpse.y, NUTRIENT_RADIUS, boost * 0.1)
        # §AP: a Sacred Spiral shrine composts what dies beside it — death is
        # folded back into life faster within the aura.
        for cid, info in self.clans.items():
            if info.get("totem") != "Sacred Spiral" or int(info.get("shrine_level", 0)) < 1:
                continue
            shrine = self._shrine_pos(cid)
            if shrine and self.world.distance_sq(corpse.x, corpse.y, shrine[0], shrine[1]) <= NUTRIENT_RADIUS ** 2:
                boost *= 1.0 + self._totem_stat_compost(info)
                break
        # AF: spatial query around decaying entity instead of scanning all world entities
        for e in self.world.query_radius(corpse.x, corpse.y, NUTRIENT_RADIUS):
            if not isinstance(e, Food):
                continue
            was = e.growth
            e.growth = min(1.0, e.growth + boost)
            if was < 1.0 <= e.growth:
                self._emit_bloom(e)

    def _totem_stat_compost(self, clan_info: dict) -> float:
        return float(TOTEM_BUFF.get(clan_info.get("totem"), {}).get("compost", 0.0))

    # ---------------------------------------------------------------- disease
    def _emit(self, event: HistoryEvent) -> None:
        self.history.append(event)
        # AA: pre-dump once at source — snapshot_payload reads plain dicts directly,
        # eliminating per-frame Pydantic model_dump() on the broadcast hot path.
        self._events_this_tick.append(event.model_dump(mode="json"))
        if self.on_event is not None:
            self.on_event(event)

    def _infect(self, c: Creature) -> None:
        c.infected = True
        c.disease_id = self.disease_id

    def _update_disease(self) -> None:
        """Outbreaks, contagion and recovery. Disabling the law freezes it."""
        cfg = self.config
        if not cfg.disease_enabled:
            return
        creatures = self._get_creatures()
        active = [c for c in creatures if c.infected]

        age = self._age()
        age_disease = AGE_DISEASE_MULT.get(age, 1.0) if age is not None else 1.0
        if (
            not any(c.infected for c in creatures)
            and creatures
            and self.rng.random()
            < cfg.disease_outbreak_rate
            * (WINTER_DISEASE_MULT if self._season() == "winter" else 1.0)
            * age_disease
        ):
            patient = self.rng.choice(creatures)
            self.disease_id += 1
            self._infect(patient)
            self._emit(
                HistoryEvent(
                    type="outbreak",
                    tick=self.tick + 1,
                    entity_id=patient.id,
                    caste=patient.caste,
                    x=round(patient.x, 2),
                    y=round(patient.y, 2),
                    payload={"disease_id": self.disease_id},
                )
            )

        for c in active:
            if not c.infected or c.id not in self.world.entities:
                continue  # died or recovered earlier this tick
            # Recovery — wet/cold slows recovery (§R)
            eff_recovery = cfg.recovery_rate
            # §AP: the Sacred Spiral hastens recovery from plagues
            eff_recovery *= 1.0 + self._totem_stat(c, "recovery")
            if cfg.weather_sickness_enabled:
                wet_c = (self.weather in ("rain", "storm") and not c.indoors) or c.chill >= cfg.chill_threshold * 0.5
                if wet_c:
                    eff_recovery = cfg.recovery_rate / max(1.0, cfg.wet_disease_mult)
            if eff_recovery > 0 and self.rng.random() < eff_recovery:
                c.infected = False
                self._emit(
                    HistoryEvent(
                        type="recovery",
                        tick=self.tick + 1,
                        entity_id=c.id,
                        caste=c.caste,
                        x=round(c.x, 2),
                        y=round(c.y, 2),
                        payload={"disease_id": c.disease_id},
                    )
                )
                continue
            # Contagion to healthy neighbours (winter air carries further) — wet catches faster (§R) — age plague (§S)
            base_spread = cfg.disease_rate * (
                WINTER_DISEASE_MULT if self._season() == "winter" else 1.0
            ) * (AGE_DISEASE_MULT.get(age, 1.0) if age is not None else 1.0)
            for n in self.world.query_radius(c.x, c.y, cfg.disease_radius):
                if n.kind == "creature" and not n.infected and n.id != c.id:
                    rate = base_spread
                    if cfg.weather_sickness_enabled:
                        wet_n = (self.weather in ("rain", "storm") and not getattr(n, "indoors", False)) or getattr(n, "chill", 0) >= cfg.chill_threshold * 0.5
                        if wet_n:
                            rate *= cfg.wet_disease_mult
                    if self.rng.random() < min(rate, 1.0):
                        self._infect(n)  # type: ignore[arg-type]

    # ----------------------------------------------------------- reproduction
    def _reproduce(self) -> None:
        """Nature's Law: eligible pairs may beget children; god only sets rates."""
        cfg = self.config
        if not cfg.birth_enabled:
            return
        creatures = self._get_creatures()
        # live count
        live = [c for c in creatures if c.id in self.world.entities]
        pop = len(live)
        max_pop = cfg.effective_max_population
        carrying = cfg.effective_carrying_capacity
        age = self._age()
        if age is not None:
            cap_mult = AGE_CAP_MULT.get(age, 1.0)
            max_pop = max(2, round(max_pop * cap_mult))
            carrying = max(2, round(carrying * cap_mult))
        if pop >= max_pop:
            return
        room = 1.0  # fertility fades as the world crowds past carrying capacity
        if pop > carrying:
            gap = max(1.0, max_pop - carrying)
            room = max(0.0, 1.0 - (pop - carrying) / gap)

        def eligible(c: Creature) -> bool:
            return (
                c.age >= cfg.adult_age
                and c.repro_cooldown <= 0
                and c.energy >= cfg.mate_energy_min
                and c.health >= REPRO_MIN_HEALTH  # §AT-4 H-0: no heirs in sickness
            )

        females = [c for c in creatures if c.shape == "line" and eligible(c)]
        if not females:
            return

        if room <= 0.0:
            return

        mate_r2 = cfg.mate_radius * cfg.mate_radius
        for mother in females:
            father = None
            best_d2 = mate_r2 + 1e-9
            # AF: query candidate males via spatial index with precomputed distance
            for m, d2 in self.world.query_radius_with_dist_sq(mother.x, mother.y, cfg.mate_radius):
                if not isinstance(m, Creature) or m.shape == "line":
                    continue
                if m.repro_cooldown > 0 or m.energy < cfg.mate_energy_min or not eligible(m):
                    continue
                if d2 < best_d2:
                    father, best_d2 = m, d2
            if father is None:
                continue
            m_fert = 0.5 if mother.stage == "elder" else 1.0
            f_fert = 0.5 if father.stage == "elder" else 1.0
            fert = (
                traits_for(mother.caste).fertility
                * m_fert
                * traits_for(father.caste).fertility
                * f_fert
                * room
            )
            rate = cfg.birth_rate
            age2 = self._age()
            if age2 is not None:
                rate = min(1.0, rate * AGE_BIRTH_MULT.get(age2, 1.0))
            if self._season() == "spring":
                rate = min(1.0, rate * SPRING_BIRTH_MULT)  # spring quickens the blood
            # §AM E.2: a clan at its feast is generous with more than bread
            mother_clan = self.clans.get(mother.clan_id) if mother.clan_id else None
            if mother_clan and self.tick < int(mother_clan.get("feast_until", 0)):
                rate = min(1.0, rate * BANQUET_FERTILITY_MULT)
            rate *= 1.0 + self._totem_stat(mother, "birth")  # Stag/Rabbit fecundity
            if self.rng.random() >= min(rate * fert, 1.0):
                continue
            self._birth(mother, father)
            pop += 1
            if pop >= max_pop:
                break

    def _birth(self, mother: Creature, father: Creature) -> None:
        cfg = self.config
        gen = max(mother.generation, father.generation) + 1
        tick = self.tick + 1  # the tick being completed
        x = (mother.x + self.rng.uniform(-1.5, 1.5)) % cfg.width
        y = (mother.y + self.rng.uniform(-1.5, 1.5)) % cfg.height

        # Predator lineage: if either parent is a predator, child may be predator
        is_predator_child = False
        if mother.is_predator and father.is_predator:
            is_predator_child = True
        elif mother.is_predator or father.is_predator:
            is_predator_child = self.rng.random() < 0.5

        if is_predator_child:
            # Predator children are always Predator caste, no clan, no irregularity
            # trait inheritance (§S)
            ptrait = None
            if self.rng.random() < cfg.trait_mutation_rate:
                ptrait = self.rng.choice(TRAITS)
            elif mother.trait or father.trait:
                opts = [t for t in (mother.trait, father.trait) if t]
                ptrait = self.rng.choice(opts) if opts else None
            child = Creature(
                shape="polygon" if self.rng.random() < 0.5 else "line",
                sides=6 if self.rng.random() < 0.5 else 2,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for("Predator").lifespan * cfg.lifespan_mult,
                is_predator=True,
                caste="Predator",
                clan_id=0,
                trait=ptrait,
            )
            self._init_creature_evolution(child, mother, father)
            self.world.add(child)
            event_payload = {
                "mother": mother.id, "father": father.id,
                "sides": child.sides, "generation": gen, "sex": child.sex,
                "clan_id": 0, "is_predator": True,
                "personal_name": personal_name_for(child.id, self.config.seed, gen),
                "glyph": glyph_for(child.id, self.config.seed, gen),
            }
            for p in (mother, father):
                p.energy = max(1.0, p.energy - cfg.birth_energy_cost)
                p.repro_cooldown = cfg.reproduction_cooldown
                p.emote = "love"
                p.emote_ticks = 25
            event = HistoryEvent(
                type="birth", tick=tick, entity_id=child.id, caste=child.caste,
                x=round(child.x, 2), y=round(child.y, 2),
                payload=event_payload,
            )
            self.history.append(event)
            self._events_this_tick.append(event.model_dump(mode="json"))
            if self.on_event is not None:
                self.on_event(event)
            return

        # Herbivore lineage: wild grazers breed true outside the caste system
        is_herbivore_child = False
        if mother.is_herbivore and father.is_herbivore:
            is_herbivore_child = True
        elif mother.is_herbivore or father.is_herbivore:
            is_herbivore_child = self.rng.random() < 0.5
        if is_herbivore_child:
            htrait = None
            if self.rng.random() < cfg.trait_mutation_rate:
                htrait = self.rng.choice(TRAITS)
            elif mother.trait or father.trait:
                opts = [t for t in (mother.trait, father.trait) if t]
                htrait = self.rng.choice(opts) if opts else None
            child = Creature(
                shape="polygon", sides=4, iso_angle=60.0,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for("Herbivore").lifespan * cfg.lifespan_mult,
                is_herbivore=True,
                caste="Herbivore",
                clan_id=0,
                trait=htrait,
            )
            self._init_creature_evolution(child, mother, father)
            self.world.add(child)
            event_payload = {
                "mother": mother.id, "father": father.id,
                "sides": child.sides, "generation": gen, "sex": child.sex,
                "clan_id": 0, "is_herbivore": True,
                "personal_name": personal_name_for(child.id, self.config.seed, gen),
                "glyph": glyph_for(child.id, self.config.seed, gen),
            }
            for p in (mother, father):
                p.energy = max(1.0, p.energy - cfg.birth_energy_cost)
                p.repro_cooldown = cfg.reproduction_cooldown
                p.emote = "love"
                p.emote_ticks = 25
            event = HistoryEvent(
                type="birth", tick=tick, entity_id=child.id, caste=child.caste,
                x=round(child.x, 2), y=round(child.y, 2),
                payload=event_payload,
            )
            self.history.append(event)
            self._events_this_tick.append(event.model_dump(mode="json"))
            if self.on_event is not None:
                self.on_event(event)
            return

        promoted = False
        if self.rng.random() < cfg.sex_ratio:
            if father.sides == 3:
                # Isosceles line: sons stay triangles, creeping toward Regular.
                # §AP: the Dimensional Rift hastens God's Ascent through the castes.
                sides = 3
                iso = min(60.0, father.iso_angle + 0.5 + 0.25 * self._totem_stat(father, "promote"))
                promoted = iso >= 60.0 and father.iso_angle < 60.0
            else:
                # Law of Nature: a son has one more side than his father.
                sides = min(father.sides + 1, cfg.max_sides)
                iso = 60.0
            irregularity = 0.0
            mut_rate = cfg.mutation_rate
            # §AP: Rift clans breed adaptable children — mutation odds multiply.
            mut_rate = min(1.0, mut_rate * (1.0 + self._totem_stat(mother, "mutate")))
            # §AS L-5: thin royal blood — small monarchies mutate more easily
            mother_clan_gov = self.clans.get(mother.clan_id, {}).get("governance")
            if (
                mother_clan_gov == "monarchy"
                and len(self._clan_members.get(mother.clan_id, ())) < 8
            ):
                mut_rate = min(1.0, mut_rate * MONARCHY_INBREEDING)
            age = self._age()
            if age is not None:
                mut_rate = min(1.0, mut_rate * AGE_MUTATION_MULT.get(age, 1.0))
            if self.rng.random() < mut_rate:
                # A deformed child: sides deviate AND the irregularity is scored.
                sides = min(cfg.max_sides, max(3, sides + self.rng.choice((-1, 1))))
                if sides != 3:
                    promoted = False
                irregularity = round(self.rng.uniform(0.3, 1.0), 3)
            caste = caste_name(sides, "polygon", iso)
            # trait inheritance (§S)
            ntrait = None
            if self.rng.random() < cfg.trait_mutation_rate:
                ntrait = self.rng.choice(TRAITS)
            elif mother.trait or father.trait:
                opts = [t for t in (mother.trait, father.trait) if t]
                ntrait = self.rng.choice(opts) if opts else None
            child = Creature(
                shape="polygon", sides=sides, iso_angle=iso,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for(caste).lifespan * cfg.lifespan_mult,
                irregularity=irregularity,
                trait=ntrait,
            )
        else:
            dtrait = None
            if self.rng.random() < cfg.trait_mutation_rate:
                dtrait = self.rng.choice(TRAITS)
            elif mother.trait or father.trait:
                opts = [t for t in (mother.trait, father.trait) if t]
                dtrait = self.rng.choice(opts) if opts else None
            child = Creature(
                shape="line", sides=2,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for("Woman").lifespan * cfg.lifespan_mult,
                trait=dtrait,
            )

        self._init_creature_evolution(child, mother, father)
        self.world.add(child)
        gift = self._totem_stat(child, "health")  # totem vitality: Bear/Shield cubs
        if gift:
            child.health = min(child.max_health, child.health + gift)
        if child.clan_id == 0:
            # Children belong to their mother's clan; orphans found new ones
            # (clan set before the claim so the founder counts as a member, §V).
            parent_clan = mother.clan_id or father.clan_id
            if parent_clan:
                child.clan_id = parent_clan
            else:
                cid_new = self._new_clan(child)
                child.clan_id = cid_new
                if self.config.house_claim_enabled:
                    self._claim_house_for_clan(cid_new)
        event_payload = {
            "mother": mother.id, "father": father.id,
            "sides": child.sides, "generation": gen, "sex": child.sex,
            "clan_id": child.clan_id,
            "personal_name": personal_name_for(child.id, self.config.seed, gen),
            "glyph": glyph_for(child.id, self.config.seed, gen),
        }

        # The parents pay for it dearly.
        for p in (mother, father):
            p.energy = max(1.0, p.energy - cfg.birth_energy_cost)
            p.repro_cooldown = cfg.reproduction_cooldown

        event = HistoryEvent(
            type="birth", tick=tick, entity_id=child.id, caste=child.caste,
            x=round(child.x, 2), y=round(child.y, 2),
            payload=event_payload,
        )
        self.history.append(event)
        self._events_this_tick.append(event.model_dump(mode="json"))
        if self.on_event is not None:
            self.on_event(event)
        # §AR S-7: birth is literally good news — kin nearby share a joy
        # ripple and a small morale/health gift.
        if child.clan_id and len(self.signals) < SIGNALS_MAX:
            self.signals.append({
                "x": round(child.x, 2), "y": round(child.y, 2),
                "kind": "joy", "sender": mother.id,
                "clan_id": child.clan_id or None, "born_tick": self.tick, "ttl": 15,
                "joy_energy": 2.0, "joy_health": 1.0,
            })

        if promoted:
            pevent = HistoryEvent(
                type="promotion", tick=tick, entity_id=child.id, caste=child.caste,
                x=round(child.x, 2), y=round(child.y, 2),
                payload={"from": "Soldier", "to": "Artisan"},
            )
            self.history.append(pevent)
            self._events_this_tick.append(pevent.model_dump(mode="json"))
            if self.on_event is not None:
                self.on_event(pevent)

    def _kill(self, c: Creature, cause: str, corpse_energy_mult: float = 1.0) -> None:
        """Remove a creature from the world and record it in the chronicle."""
        self.world.remove(c.id)
        if self.config.corpses_enabled:
            self.world.add(
                Corpse(x=c.x, y=c.y, ttl=self.config.corpse_ttl,
                       energy=self.config.corpse_energy * corpse_energy_mult)
            )
        self.deaths += 1
        self._death_counts[cause] = self._death_counts.get(cause, 0) + 1
        if c.clan_id:
            self._clan_deaths[c.clan_id] = self._clan_deaths.get(c.clan_id, 0) + 1
        event = HistoryEvent(
            type="death",
            tick=self.tick + 1,  # the tick being completed
            entity_id=c.id,
            caste=c.caste,
            cause=cause,
            x=round(c.x, 2),
            y=round(c.y, 2),
            payload={"personal_name": personal_name_for(c.id, self.config.seed, c.generation), "glyph": glyph_for(c.id, self.config.seed, c.generation)},
        )
        self.history.append(event)
        self._events_this_tick.append(event.model_dump(mode="json"))
        if self.on_event is not None:
            self.on_event(event)
        # §AN B.3: a violent end leaves a danger scent that steers the
        # young and the vulnerable away from ambush grounds.
        if (
            self.config.scent_enabled
            and cause in ("predation", "war")
            and len(self.signals) < SIGNALS_MAX
        ):
            self.signals.append({
                "x": round(c.x, 2), "y": round(c.y, 2), "kind": "danger_scent",
                "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": DANGER_SCENT_TTL,
            })
        # Leadership succession (§P) — always runs; succession_enabled only gates the chronicle event.
        if c.clan_id:
            # §AT-4 H-2: kin who watch a clan-mate die carry the grief —
            # morale breaks a little in every witness (§AR S-7 grief ripple).
            witnesses = 0
            pr_sq = self.config.perceive_radius * self.config.perceive_radius
            # §P0: clan-scoped witness scan instead of full-world scan
            for other in self._clan_members.get(c.clan_id, ()) or self._get_creatures():
                if other.id == c.id or other.clan_id != c.clan_id:
                    continue
                if self.world.distance_sq(other.x, other.y, c.x, c.y) <= pr_sq:
                    other.morale = max(0.0, other.morale - MORALE_DEATH_WITNESS)
                    witnesses += 1
            if witnesses and len(self.signals) < SIGNALS_MAX:
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2),
                    "kind": "grief", "sender": c.id,
                    "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 15,
                    "witnesses": [
                        o.id for o in self._clan_members.get(c.clan_id, ()) or self._get_creatures()
                        if o.id != c.id and o.clan_id == c.clan_id
                        and self.world.distance_sq(o.x, o.y, c.x, c.y) <= pr_sq
                    ],
                })
            clan = self.clans.get(c.clan_id)
            if clan and clan.get("leader_id") == c.id:
                # Exclude the dying creature from candidates: world.remove() ran above but
                # _cached_creatures is only rebuilt at _refresh_cache(), so filter explicitly.
                candidates = [cc for cc in self._get_creatures() if cc.clan_id == c.clan_id and cc.id != c.id]
                if candidates:
                    gov = clan.get("governance", "republic")
                    if gov == "monarchy":
                        dynasty = [cc for cc in candidates if cc.mother_id == c.id or cc.father_id == c.id]
                        successor = sorted(dynasty or candidates, key=lambda cc: (-cc.age, cc.id))[0]
                    elif gov == "theocracy":
                        priests = [cc for cc in candidates if cc.caste == "Priest"]
                        successor = sorted(priests or candidates, key=lambda cc: (-cc.age, cc.id))[0]
                    elif gov == "junta":
                        soldiers = [cc for cc in candidates if cc.caste == "Soldier"]
                        successor = sorted(soldiers or candidates, key=lambda cc: (-getattr(cc, "skills", {}).get("combat", 0.0), -cc.age, cc.id))[0]
                    else:
                        # republic (Council of Elders)
                        successor = sorted(candidates, key=lambda cc: (-cc.sides, -cc.age, cc.id))[0]

                    clan["leader_id"] = successor.id
                    succ_name = personal_name_for(successor.id, self.config.seed, successor.generation)
                    # §AS L-6: succession flavor — a new chief may call a new
                    # avatar; two equal heirs may tear the clan in two.
                    if self.rng.random() < TOTEM_CHANGE_CHANCE:
                        bias = {
                            "bold": "Celestial Strike",
                            "peaceful": "Sacred Spiral",
                            "paranoid": "All-Seeing Vertex",
                            None: "Radiant Circle",
                        }.get(successor.trait, "Radiant Circle")
                        if successor.caste == "Soldier":
                            bias = "Celestial Strike"
                        old_totem = clan.get("totem")
                        clan["totem"] = bias
                        self._log_clan_history(
                            c.clan_id, "totem_change",
                            f"{bias} succeeds {old_totem} under Chief {succ_name} (Day {self.day})",
                        )
                    else:
                        equals = [
                            cc for cc in candidates
                            if (cc.sides, cc.age) == (successor.sides, successor.age)
                            and cc.id != successor.id
                        ]
                        if equals and self.rng.random() < CONTESTED_SUCCESSION_CHANCE:
                            faction = [
                                cc for cc in candidates if cc.id % 2 == 0
                            ][: max(1, len(candidates) // 2)]
                            if faction and len(faction) < len(candidates):
                                new_cid = self._new_clan(faction[0])
                                for cc in faction:
                                    cc.clan_id = new_cid
                                self._bump_relation(c.clan_id, new_cid, -40)
                                self._emit(
                                    HistoryEvent(
                                        type="schism",
                                        tick=self.tick + 1,
                                        entity_id=faction[0].id,
                                        caste=faction[0].caste,
                                        payload={"parent": c.clan_id, "new_clan": new_cid,
                                                 "reason": "contested_succession"},
                                    )
                                )
                    if self.config.succession_enabled:
                        self._log_clan_history(
                            c.clan_id,
                            "leader_change",
                            f"{succ_name} (#{successor.id}) ascended as Leader ({gov.capitalize()}, Day {self.day})",
                        )
                        self._emit(
                            HistoryEvent(
                                type="succession",
                                tick=self.tick + 1,
                                entity_id=successor.id,
                                caste=successor.caste,
                                x=round(successor.x, 2),
                                y=round(successor.y, 2),
                                payload={"clan_id": c.clan_id, "prev_leader": c.id, "new_leader": successor.id, "clan_name": clan.get("name")},
                            )
                        )
                else:
                    clan["leader_id"] = None
                    if self.config.succession_enabled:
                        self._log_clan_history(
                            c.clan_id,
                            "leader_change",
                            f"Leader #{c.id} perished without living successor (Day {self.day})",
                        )
                # §AS L-0 Leader shock: the chief's death rocks the whole clan —
                # energy drains in an instant, panic takes hold for 20 ticks,
                # the larder is looted, and a grief cry rings out.
                for member in self._get_creatures():
                    if member.clan_id == c.clan_id and member.id != c.id:
                        member.energy = max(0.5, member.energy - LEADER_SHOCK_ENERGY)
                        member.panic_ticks = LEADER_SHOCK_PANIC_TICKS
                        # §AT-4 H-2: the chief's death breaks more hearts than a common loss.
                        member.morale = max(0.0, member.morale - MORALE_LEADER_DEATH)
                        member.emote = "panic"
                        member.emote_ticks = 15
                if clan:
                    clan["larder"] = float(clan.get("larder", 0.0)) * LEADER_SHOCK_LARDER_MULT
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2),
                    "kind": "grief", "sender": c.id,
                    "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 15,
                })
                # §AS L-4: a chief cut down outside a declared feud is
                # regicide when any rival lives at war with the victim's clan.
                if cause == "war" and not any(
                    e.get("type") == "regicide"
                    and e.get("payload", {}).get("victim") == c.id
                    for e in getattr(self, "_events_this_tick", [])
                ):
                    for other in sorted(self.clans.keys()):
                        if other == c.clan_id:
                            continue
                        pair = self._relation_pair(c.clan_id, other)
                        if self._zone_of(self.relations.get(pair, 0)) != -1:
                            continue
                        if self._declared_wars.get(pair) is not None:
                            continue
                        self._emit(
                            HistoryEvent(
                                type="regicide",
                                tick=self.tick + 1,
                                entity_id=c.id,
                                payload={
                                    "victim": c.id, "victim_clan": c.clan_id,
                                    "assassin_clan": other,
                                },
                            )
                        )
                        for third in sorted(self.clans.keys()):
                            if third in (c.clan_id, other):
                                continue
                            opair = self._relation_pair(third, other)
                            self.relations[opair] = max(-100, self.relations.get(opair, 0) + REGICIDE_RELATION_HIT)
                            vpair = self._relation_pair(third, c.clan_id)
                            self.relations[vpair] = min(100, self.relations.get(vpair, 0) + REGICIDE_SYMPATHY)
                        break


    def _update_creature_skills_and_titles(self, c: Creature) -> None:
        """Evaluate dynamic titles and milestone level-ups."""
        skills = getattr(c, "skills", None)
        if not skills or not isinstance(skills, dict):
            c.skills = {"farming": 0.0, "combat": 0.0, "foraging": 0.0, "healing": 0.0}
            skills = c.skills

        farm = skills.get("farming", 0.0)
        combat = skills.get("combat", 0.0)
        forage = skills.get("foraging", 0.0)
        heal = skills.get("healing", 0.0)

        new_title = None
        if combat >= 30.0:
            new_title = "the Fearless Champion"
        elif combat >= 12.0:
            new_title = "the Slayer"
        elif farm >= 30.0:
            new_title = "the Grand Harvester"
        elif farm >= 12.0:
            new_title = "the Harvester"
        elif heal >= 30.0:
            new_title = "the Wise Shaman"
        elif heal >= 12.0:
            new_title = "the Herbalist"
        elif forage >= 30.0:
            new_title = "the Pathfinder"
        elif forage >= 12.0:
            new_title = "the Gatherer"

        if new_title and new_title != c.title:
            c.title = new_title
            c.emote = "cheer"
            c.emote_ticks = 30

    def _update_creature(
        self,
        c: Creature,
        houses: list[Entity],
        tod: float | None = None,
        is_night: bool | None = None,
        env_sight: float | None = None,
        env_speed: float | None = None,
        clan_house_map: dict[int, House] | None = None,
    ) -> None:
        cfg, w = self.config, self.world
        if tod is None:
            tod = self._time_of_day()
        if is_night is None:
            is_night = self._is_night(tod)
        if env_sight is None:
            env_sight = self.env_sight_mult()
        if env_speed is None:
            env_speed = self.env_speed_mult()
        if clan_house_map is None:
            clan_house_map = {
                h.clan_id: h for h in houses if isinstance(h, House) and h.clan_id and not h.is_ruin
            }

        c.ticks_since_meal += 1
        c.age += 1
        # §AU O-1: the assigned roof resolves lazily ONCE per creature tick;
        # every later consumer reuses it instead of re-scanning all houses.
        roof_resolved = False
        assigned_roof: House | None = None
        if c.repro_cooldown > 0:
            c.repro_cooldown -= 1
        if c.bite_cooldown > 0:
            c.bite_cooldown -= 1
        if c.cannibal_cooldown > 0:
            c.cannibal_cooldown -= 1
        if c.panic_ticks > 0:
            c.panic_ticks -= 1
        if c.alarm_wake_ticks > 0:
            c.alarm_wake_ticks -= 1
        if getattr(c, "combat_boost_ticks", 0) > 0:
            c.combat_boost_ticks -= 1
        if getattr(c, "fall_cooldown", 0) > 0:
            c.fall_cooldown -= 1
        # §AR S-3: decay, drift and eviction keep memory honest
        self._maintain_facts(c)
        if c.calm_ticks > 0:
            c.calm_ticks -= 1
        if c.prepared_ticks > 0:
            c.prepared_ticks -= 1
        if c.greet_cooldown > 0:
            c.greet_cooldown -= 1

        # Emote timer countdown
        if c.emote_ticks > 0:
            c.emote_ticks -= 1
            if c.emote_ticks <= 0:
                c.emote = None

        # Hunger emote trigger
        if c.energy < 25.0 and not c.sleeping and not c.emote:
            c.emote = "hungry"
            c.emote_ticks = 10

        # Leader crown
        if c.clan_id and self.clans.get(c.clan_id, {}).get("leader_id") == c.id:
            c.equipped_item = "crown"
        elif is_night and c.personality == "explorer" and not c.is_predator and not c.is_herbivore:
            # §AR S-2: the torch tradeoff — an explorer's flame restores night
            # sight around it, but the glow draws every wolf's eye.
            if c.equipped_item is None or c.equipped_item == "torch":
                c.equipped_item = "torch"
        elif c.equipped_item == "torch" and not is_night:
            c.equipped_item = None  # daybreak: douse the torch

        # §AR S-5 / §AS L-1: a leader whose clan is at war raises the rally —
        # kin set it as their waypoint and come running.
        if (
            c.clan_id
            and self.clans.get(c.clan_id, {}).get("leader_id") == c.id
            and not c.sleeping
            and not c.is_predator
            and (self.tick + c.id) % 30 == 0
            and len(self.signals) < SIGNALS_MAX
        ):
            at_war_now = False
            for pair, score in self.relations.items():
                if c.clan_id in pair and score <= cfg.rivalry_threshold:
                    at_war_now = True
                    break
            if at_war_now:
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2), "kind": "rally",
                    "sender": c.id, "clan_id": c.clan_id or None,
                    "born_tick": self.tick, "ttl": RALLY_SIGNAL_TTL,
                })
        # §AS L-2: retreat when bleeding + evacuation when threatened — independent cadence
        if (
            c.clan_id
            and self.clans.get(c.clan_id, {}).get("leader_id") == c.id
            and not c.sleeping
            and not c.is_predator
            and c.health <= RETREAT_HEALTH_FRAC * c.max_health
            and (self.tick + c.id) % 20 == 0
            and len(self.signals) < SIGNALS_MAX
        ):
            self.signals.append({
                "x": round(c.x, 2), "y": round(c.y, 2), "kind": "retreat",
                "sender": c.id, "clan_id": c.clan_id or None,
                "born_tick": self.tick, "ttl": 30,
            })
        if (
            c.clan_id
            and self.clans.get(c.clan_id, {}).get("leader_id") == c.id
            and not c.sleeping
            and not c.is_predator
            and (self.tick + c.id) % 15 == 0
            and len(self.signals) < SIGNALS_MAX
        ):
            fire_near2 = any(self.world.distance(c.x, c.y, f["x"], f["y"]) < 25.0 for f in self.fires)
            flood_near2 = any(rv.get("flood_ticks", 0) > 0 for rv in self.rivers)
            if fire_near2 or flood_near2:
                import math as _m3b
                hx_, hy_ = (self.fires[0]["x"], self.fires[0]["y"]) if self.fires else (c.x, c.y)
                dxl, dyl = self.world.delta(hx_, hy_, c.x, c.y)
                dl = _m3b.hypot(dxl, dyl) or 1e-6
                ex = c.x + dxl/dl*18.0; ey = c.y + dyl/dl*18.0
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2), "kind": "evacuate",
                    "sender": c.id, "clan_id": c.clan_id or None,
                    "born_tick": self.tick, "ttl": 40,
                    "evac_x": round(ex % self.config.width, 2),
                    "evac_y": round(ey % self.config.height, 2),
                })

        # Evaluate skills and dynamic epithets
        if self.tick % 10 == 0:
            self._update_creature_skills_and_titles(c)

        # 0. Night rest: after dark, creatures make for the nearest house and
        # those who win a bed sleep — half the hunger, multiplied healing.
        # Predators cannot fit through the doorway (§L refuge).
        # Starving creatures skip sleep to forage — survival over comfort.
        c.sleeping = False
        c.indoors = False
        ratio = c.energy / cfg.energy_max if cfg.energy_max > 0 else 1.0
        is_starving = ratio <= cfg.starving_ratio
        if (
            cfg.sleep_enabled
            and cfg.shelter_enabled
            and not c.is_predator
            and not c.is_herbivore
            and not is_starving
            and is_night
            and c.alarm_wake_ticks <= 0  # §AR S-1: a war cry wakes sleepers
            and houses
        ):
            # Assigned roof (room-aware, §L); if we're not under it but stand
            # inside ANOTHER roof with a free bed, rest here instead of
            # trekking across the village. No bed ⇒ no rest: capacity is law.
            # §AT-3: only own-clan or unclaimed roofs may be entered.
            if not roof_resolved:
                assigned_roof = self._house_for(c, houses)
                roof_resolved = True
            assigned = assigned_roof
            home: House | None = None
            if (
                assigned is not None
                and self._inside_house(c, assigned)
                and (not self.config.house_claim_enabled or assigned.clan_id == 0 or assigned.clan_id == c.clan_id)
            ):
                home = assigned
            else:
                for h in self._house_grid.get((int(c.x // 50), int(c.y // 50)), []):
                    if (
                        not h.is_ruin
                        and (not self.config.house_claim_enabled or h.clan_id == 0 or h.clan_id == c.clan_id)
                        and self._inside_house(c, h)
                        and self._beds.get(h.id, 0) < self._house_beds(h)
                    ):
                        home = h
                        break
            if home is not None and self._claim_bed(home):
                c.indoors = True
                c.sleeping = True
                if not c.emote:
                    c.emote = "sleep"
                    c.emote_ticks = 15
                # Oral Lore transmission in houses: elders pass XP to sleeping youth
                if c.stage == "elder" and c.clan_id and (self.tick + c.id) % 15 == 0:
                    skills_dict = getattr(c, "skills", {})
                    if skills_dict:
                        best_skill = max(skills_dict, key=lambda k: skills_dict.get(k, 0.0))
                        # §AP: the Dimensional Rift carries elder lore across generations
                        _totem_lore = getattr(self, "_clan_totem_stats", {}).get(c.clan_id, {}).get("lore", 0.0) if self.config.totems_enabled else 0.0
                        lore_xp = 0.15 * (1.0 + _totem_lore)
                        for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, 6.0):
                            if isinstance(o, Creature) and o.clan_id == c.clan_id and o.stage in ("infant", "juvenile"):
                                if hasattr(o, "skills") and isinstance(o.skills, dict):
                                    o.skills[best_skill] = o.skills.get(best_skill, 0.0) + lore_xp
                if cfg.knowledge_enabled:
                    self._learn(c, "safe", home.x, home.y)  # §X: this roof is safe
                    # §AR S-3: inherited memory — an elder at rest passes its
                    # sense of home and food grounds to the young asleep near.
                    if c.stage == "elder" and (self.tick + c.id) % 20 == 0:
                        for o in w.query_radius(c.x, c.y, 5.0):
                            if (
                                isinstance(o, Creature)
                                and o.clan_id == c.clan_id
                                and o.stage in ("infant", "juvenile")
                            ):
                                safe = self._fact_fresh(c, "safe")
                                food = self._fact_fresh(c, "food")
                                if safe is not None:
                                    o.facts["safe"] = dict(safe, conf=ORAL_LORE_CONF, tick=self.tick)
                                if food is not None:
                                    o.facts["food"] = dict(food, conf=ORAL_LORE_CONF, tick=self.tick)
                stage_mult = STAGE_ENERGY_MULT.get(c.stage, 1.0) if c.generation > 0 else 1.0
                # §AO Phase C: a lit hearth is total sanctuary — the fire
                # purges every trace of chill and halts the night's burn.
                hearth_sanctuary = bool(getattr(home, "hearth_lit", False))
                if hearth_sanctuary:
                    c.chill = 0.0
                else:
                    c.energy -= cfg.energy_decay_per_tick * cfg.sleep_energy_mult * stage_mult * self._metabolic_cost(c)
                if c.infected and cfg.disease_enabled:
                    c.energy -= cfg.disease_energy_drain
                    c.health -= 2.0 * cfg.disease_lethality
                else:
                    # §AT-4 H-0: healing is not free — a body running on fumes
                    # cannot mend itself, even asleep. §AQ PH-0: mending costs.
                    if (c.energy / cfg.energy_max) > HEALTH_REGEN_MIN_ENERGY:
                        regen = 0.15 * cfg.rest_recovery_mult
                        # §AO Phase C: the hearth's warmth knits wounds fast.
                        if hearth_sanctuary:
                            regen += HEARTH_SANCTUARY_HEAL
                        # §AT-4 H-2: plague-response bylaw — the main house is an
                        # infirmary and its beds heal twice as well.
                        ci_sl = self.clans.get(c.clan_id) if c.clan_id else None
                        if (
                            isinstance(ci_sl, dict)
                            and (ci_sl.get("bylaws") or {}).get("plague_response")
                            and ci_sl.get("main_house_id") == home.id
                        ):
                            regen *= INFIRMARY_REGEN_MULT
                        regen *= 1.0 + (getattr(self, "_clan_totem_stats", {}).get(c.clan_id, {}).get("defense", 0.0) if self.config.totems_enabled and c.clan_id else 0.0)  # totem vitality heals faster
                        if c.heal_bonus_ticks > 0:
                            regen += c.heal_bonus_amount  # §AT-4 H-1: supper keeps working
                        healed = min(c.max_health, c.health + regen) - c.health
                        if healed > 0:
                            c.health += healed
                            c.energy = max(0.0, c.energy - healed * HEALING_ENERGY_COST)
                if c.energy <= 0:
                    if getattr(c, "food_basket", 0) > 0:
                        c.food_basket -= 1
                        c.energy = min(cfg.energy_max, c.energy + cfg.energy_from_food * 0.9)
                        c.ticks_since_meal = 0
                        c.meals += 1
                        c.give_ups.clear()
                    else:
                        self._kill(c, "starvation")
                elif c.health <= 0:
                    self._kill(c, "disease")
                elif c.age >= c.lifespan:
                    self._kill(c, "old_age")
                # Asleep means STILL: no steering, no wandering, no fleeing —
                # the body does not move again until dawn (or death).
                return
            else:
                # §AO Phase E: wanted a roof, found no bed — tonight's housing
                # shortage census (drives emergency construction).
                self._bed_overflow_night = getattr(self, "_bed_overflow_night", 0) + 1

        # §AQ PH-7: torpor — a starving body in killing cold shuts down:
        # 5% burn, unconscious and defenceless until the air warms or it dies.
        if (
            not c.is_predator
            and ratio <= TORPOR_ENERGY_RATIO
            and self.ambient_at(c.x, c.y) < HYPOTHERMIA_TEMP
        ):
            stage_mult_t = STAGE_ENERGY_MULT.get(c.stage, 1.0)
            c.energy -= cfg.energy_decay_per_tick * TORPOR_BURN_MULT * stage_mult_t * self._metabolic_cost(c)
            if not c.emote or c.emote == "hungry":
                c.emote = "sleep"
                c.emote_ticks = 15
            if c.energy <= 0:
                self._kill(c, "starvation")
            elif c.age >= c.lifespan:
                self._kill(c, "old_age")
            return

        # Clan bylaws and task board modifiers (§AL). §AS L-0: with no living
        # leader the institutions pause — no rationing, no duty weights.
        clan_info = self.clans.get(c.clan_id) if c.clan_id else None
        leaderless = bool(c.clan_id) and not getattr(self, "_leader_pos", {}).get(c.clan_id)
        if leaderless:
            bylaws: dict = {}
            task_board: dict = {}
            harvester_weight = 1.0
            guard_weight = 1.0
            # The interregnum slowly makes everyone timid.
            if self.rng.random() < LEADERLESS_CAUTIOUS_CHANCE:
                c.personality = "cautious"
        else:
            bylaws = clan_info.get("bylaws", {}) if isinstance(clan_info, dict) else {}
            task_board = clan_info.get("task_board", {}) if isinstance(clan_info, dict) else {}
            harvester_weight = task_board.get("harvester_weight", 1.0)
            guard_weight = task_board.get("guard_weight", 1.0)
        is_rationing = bylaws.get("rationing", False)

        # Field consumption: eat from personal reserve when hungry or starving
        # Under rationing bylaw, preserve emergency reserve until energy < 35.0
        eat_thresh = 35.0 if is_rationing else 55.0
        if getattr(c, "food_basket", 0) > 0 and not c.sleeping and c.energy < eat_thresh:
            c.food_basket -= 1
            c.energy = min(cfg.energy_max, c.energy + cfg.energy_from_food * 0.9)
            c.ticks_since_meal = 0
            c.meals += 1
            c.give_ups.clear()
            c.emote = "craft"
            c.emote_ticks = 15



        # §AR S-3: the priest as living oracle — periodically broadcasts the
        # clan's best knowledge to every ear within signal range.
        if (
            c.caste == "Priest"
            and cfg.knowledge_enabled
            and not c.sleeping
            and (self.tick + c.id) % PRIEST_ORACLE_INTERVAL == 0
        ):
            oracle_fact = self._fact_to_share(c)
            if oracle_fact is not None and len(self.signals) < SIGNALS_MAX:
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2),
                    "kind": "knowledge", "sender": c.id,
                    "clan_id": c.clan_id or None,
                    "born_tick": self.tick, "ttl": 15,
                    "fact": dict(oracle_fact),
                })

        # Priests heal injured / infected clanmates — full healing rounds near
        # the settlement seat (§AT-4 H-1), a lighter touch on the road.
        if c.caste == "Priest" and not c.sleeping and (self.tick + c.id) % 8 == 0:
            main_house = None
            if c.clan_id:
                main_hid = self.clans.get(c.clan_id, {}).get("main_house_id")
                if main_hid:
                    mh = self.world.entities.get(main_hid)
                    if isinstance(mh, House) and not mh.is_ruin and w.distance_sq(c.x, c.y, mh.x, mh.y) <= cfg.territory_radius * cfg.territory_radius:
                        main_house = mh
            heal_radius = LEADER_AURA_RADIUS if main_house is not None else 4.0
            heal_amount = 15.0 * (1.0 + c.skills.get("healing", 0.0) / 20.0)
            for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, heal_radius):
                if isinstance(o, Creature) and o.clan_id == c.clan_id and o.id != c.id:
                    if (o.health < min(100.0, o.max_health) or o.infected) and o.id in w.entities:
                        o.health = min(o.max_health, o.health + heal_amount)
                        o.infected = False
                        c.skills["healing"] = c.skills.get("healing", 0.0) + 1.5
                        c.emote = "heal"
                        c.emote_ticks = 20
                        o.emote = "cheer"
                        o.emote_ticks = 20
                        if not hasattr(o, "trust") or o.trust is None:
                            o.trust = {}
                        o.trust[c.id] = min(100.0, o.trust.get(c.id, 0.0) + 15.0)
                        if not hasattr(c, "trust") or c.trust is None:
                            c.trust = {}
                        c.trust[o.id] = min(100.0, c.trust.get(o.id, 0.0) + 5.0)
                        break

        # §AT-4 H-2: wound dressing — healthy kin bandage the hurt, halving
        # how long a wound lingers (and with it the infection window).
        if (
            c.health >= DRESS_MIN_HEALTH
            and not c.sleeping
            and not c.is_predator
            and not c.is_herbivore
            and (self.tick + c.id) % 4 == 0
        ):
            for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, DRESS_RADIUS):
                if (
                    isinstance(o, Creature)
                    and o.id != c.id
                    and o.clan_id == c.clan_id
                    and o.wound_severity >= 1
                    and o.wound_ticks > 10
                    and not o.wound_dressed
                    and o.id in w.entities
                ):
                    o.wound_ticks = max(10, o.wound_ticks // 2)
                    o.wound_dressed = True
                    c.emote = "heal"
                    c.emote_ticks = 12
                    o.morale = min(100.0, o.morale + MORALE_EAT_RESTORE * 0.5)  # care lifts the spirit
                    if not hasattr(o, "trust") or o.trust is None:
                        o.trust = {}
                    o.trust[c.id] = min(100.0, o.trust.get(c.id, 0.0) + 8.0)
                    break

        # Altruistic feeding & basket hauling
        if getattr(c, "food_basket", 0) > 0 and not c.sleeping:
            if c.personality == "altruistic" and (self.tick + c.id) % 6 == 0:
                for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, 5.0):
                    if not isinstance(o, Creature) or o.id == c.id:
                        continue
                    kin = o.clan_id == c.clan_id
                    if not (o.energy < 40.0 or o.stage in ("infant", "juvenile")) or o.id not in w.entities:
                        continue
                    # §AM E.1 sacred hospitality — bread broken with a stranger
                    # buys mutual non-aggression; rivals at open feud refuse it.
                    if o.clan_id and c.clan_id and o.clan_id != c.clan_id:
                        pair = self._relation_pair(c.clan_id, o.clan_id)
                        if self.relations.get(pair, 0) <= cfg.rivalry_threshold // 2:
                            continue
                        c.food_basket -= 1
                        o.energy = min(cfg.energy_max, o.energy + 30.0)
                        c.emote = "love"
                        c.emote_ticks = 15
                        o.emote = "cheer"
                        o.emote_ticks = 15
                        self._bump_relation(c.clan_id, o.clan_id, 3)
                        o.trust[c.id] = min(100.0, o.trust.get(c.id, 0.0) + 20.0) if isinstance(o.trust, dict) else o.trust
                        c.trust[o.id] = min(100.0, c.trust.get(o.id, 0.0) + 10.0) if isinstance(c.trust, dict) else c.trust
                        if self.tick - self._last_hospitality_tick >= HOSPITALITY_GAP:
                            self._last_hospitality_tick = self.tick
                            self._emit(
                                HistoryEvent(
                                    type="hospitality",
                                    tick=self.tick + 1,
                                    entity_id=c.id,
                                    caste=c.caste,
                                    x=round(c.x, 2), y=round(c.y, 2),
                                    payload={"a": c.clan_id, "b": o.clan_id,
                                             "a_name": self.clans.get(c.clan_id, {}).get("name"),
                                             "b_name": self.clans.get(o.clan_id, {}).get("name")},
                                )
                            )
                        break
                    if kin and o.clan_id == c.clan_id:
                        o.energy = min(cfg.energy_max, o.energy + 30.0)
                        c.food_basket -= 1
                        c.emote = "love"
                        c.emote_ticks = 15
                        o.emote = "cheer"
                        o.emote_ticks = 15
                        if not hasattr(o, "trust") or o.trust is None:
                            o.trust = {}
                        o.trust[c.id] = min(100.0, o.trust.get(c.id, 0.0) + 20.0)
                        if not hasattr(c, "trust") or c.trust is None:
                            c.trust = {}
                        c.trust[o.id] = min(100.0, c.trust.get(o.id, 0.0) + 10.0)
                        break

            elif c.indoors or (c.clan_id and c.clan_id in clan_house_map and self.world.distance(c.x, c.y, clan_house_map[c.clan_id].x, clan_house_map[c.clan_id].y) <= 8.0):
                if c.clan_id and c.clan_id in self.clans:
                    clan_obj = self.clans[c.clan_id]
                    curr = float(clan_obj.get("larder", 0.0))
                    clan_obj["larder"] = min(cfg.larder_capacity, curr + c.food_basket * 18.0)
                c.food_basket = 0

        # At adulthood the world judges the irregular: consumed if far from
        # regular, otherwise demoted to the lowest of the regular orders.
        if not c.matured and c.irregularity > 0 and c.age >= cfg.adult_age:
            c.matured = True
            if c.irregularity >= cfg.euthanasia_threshold:
                self._kill(c, "euthanasia")
                return
            c.sides = 3
            c.iso_angle = min(c.iso_angle, 59.5)
            c.caste = caste_name(c.sides, "polygon", c.iso_angle)
            traits = traits_for(c.caste)
            c.speed = traits.speed
            c.radius = RADIUS_BY_CASTE.get(c.caste, DEFAULT_RADIUS)
            event = HistoryEvent(
                type="demotion",
                tick=self.tick + 1,
                entity_id=c.id,
                caste=c.caste,
                x=round(c.x, 2),
                y=round(c.y, 2),
                payload={"irregularity": c.irregularity},
            )
            self.history.append(event)
            self._events_this_tick.append(event.model_dump(mode="json"))
            if self.on_event is not None:
                self.on_event(event)

        # Hunger and life stage drive perception range and urgency; the
        # caste's Sight Recognition (aided by Fog) sets the base reach.
        ratio = c.energy / cfg.energy_max if cfg.energy_max > 0 else 0.0
        if ratio <= cfg.starving_ratio:
            c.status = "starving"
        elif ratio <= cfg.hungry_ratio:
            c.status = "hungry"
        else:
            c.status = ""

        stage_speed, stage_sight = STAGE_MULT[c.stage]
        perceive = cfg.perceive_radius * c.sight_mult * stage_sight * env_sight
        # §AR S-2: age dims the eyes further — elders see ×0.9 again.
        if c.stage == "elder":
            perceive *= ELDER_SIGHT_PENALTY
        # §AT-4 H-2: scars dim the eyes forever.
        if c.scars:
            perceive *= SCAR_SIGHT_MULT ** c.scars
        # §AU CPU: hoist clan totem stats once (law-preserving, _clan_totem_stats is final mult).
        _totem = getattr(self, "_clan_totem_stats", {}).get(c.clan_id, {}) if c.clan_id and self.config.totems_enabled else {}
        # Totem sight (§P): Eye +25%, Owl +35%, Raven +15% …
        perceive *= 1.0 + _totem.get("sight", 0.0)
        # §AP: the All-Seeing Vertex sees clearly even in the dark of the world —
        # its clarity recovers the night/fog dimming.
        clarity = _totem.get("clarity", 0.0)
        if clarity and env_sight < 1.0:
            perceive /= max(0.05, 1.0 - clarity * (1.0 - env_sight))
        speed_mult = 1.0
        if c.status == "hungry":
            perceive *= cfg.hungry_perceive_mult
        elif c.status == "starving":
            perceive *= cfg.desperate_perceive_mult
            speed_mult = cfg.desperate_speed_mult
        # Totem speed: hunting/fleeing burst (Wolf, Stag, Fox, Serpent …)
        if _totem and (c.is_predator or perceive > cfg.perceive_radius):
            speed_mult *= 1.0 + _totem.get("speed", 0.0)

        # §AO Phase D: pitch black — outdoors at night non-predator sight
        # contracts to a hand's width ahead. Predators hunt by nose; the
        # All-Seeing Vertex pierces the dark; a torch pushes it back (§AR S-2).
        if (
            is_night
            and not c.indoors
            and not c.is_predator
            and not c.sleeping
        ):
            dark_cap = PITCH_BLACK_SIGHT * (1.0 + _totem.get("clarity", 0.0))
            if c.equipped_item == "torch":
                dark_cap = max(dark_cap, cfg.perceive_radius * env_sight)
            else:
                # a torch within TORCH_LIGHT_RADIUS lights the ground here too
                for o in w.query_radius(c.x, c.y, TORCH_LIGHT_RADIUS):
                    if isinstance(o, Creature) and o.equipped_item == "torch" and not o.indoors:
                        dark_cap = max(dark_cap, cfg.perceive_radius * env_sight * 0.9)
                        break
            perceive = min(perceive, dark_cap)

        # trait paranoid/bold nudges flee threshold (§S); §AR S-0 starvation
        # dulls fear (all in _effective_fear_radius); §AP the Eternal Hearth
        # calms its people through the night.
        fear_radius_eff = self._effective_fear_radius(c, is_night=is_night)

        # §AS L-0 Morale aura — the leader's presence is a stat: kin within
        # LEADER_AURA_RADIUS see farther and burn less; a dead leader casts
        # gloom over the whole clan (weaker eyes, faster burn, deeper fear).
        clan_info_aura = self.clans.get(c.clan_id) if c.clan_id else None
        leader_alive = bool(clan_info_aura and clan_info_aura.get("leader_id"))
        # §AS L-5: a crown's aura reaches half again as far
        aura_radius = LEADER_AURA_RADIUS * (
            MONARCHY_AURA_MULT if (clan_info_aura or {}).get("governance") == "monarchy" else 1.0
        )
        lpos = getattr(self, "_leader_pos", {}).get(c.clan_id) if c.clan_id else None
        in_aura = False
        if leader_alive and lpos is not None:
            in_aura = w.distance_sq(c.x, c.y, lpos[0], lpos[1]) <= aura_radius * aura_radius
            if in_aura:
                perceive *= 1.0 + LEADER_SIGHT_BONUS
                fear_radius_eff = max(1.0, fear_radius_eff - LEADER_CALM)

        elif c.clan_id:
            perceive *= 1.0 - LEADER_SIGHT_BONUS
            fear_radius_eff += LEADERLESS_FEAR
        # §AT-4 H-1: sickness dims the eyes.
        perceive *= self._health_sight_mult(c.health)
        # 1. Predation: hunt (predator) / flee (prey) — highest priority after sleep
        # §AQ PH-2: scent rides the wind — a nose reaches farther toward UPWIND
        # targets (the smell travels downwind to the sniffer), so approaching
        # from downwind is the stealth play for hunter and hunted alike.
        hunt_target: Creature | None = None
        flee_target: Creature | None = None
        # §AX P1: batch spatial queries — single radius sweep for predation
        # + food perception + scent, instead of 6 separate generator calls.
        _batch_r = perceive
        _hunt_r_tmp = 0.0
        _batch_list: list[tuple[Entity, float]] = []  # will be filled below
        scent_boost = 0.0
        wx_s, wy_s = self._cos_wind, self._sin_wind
        if cfg.predation_enabled:
                # §AQ PH-2: asymmetric noses — smelling a wolf beats hunting by
                # scent, so prey read the wind twice as well as predators do.
                scent_boost = (
                    (WIND_SCENT_MULT * self.wind_speed * 0.5 if c.is_predator
                     else WIND_SCENT_MULT * self.wind_speed)
                    if cfg.scent_enabled else 0.0
                )
                if c.is_predator and c.bite_cooldown <= 0:
                    _hunt_r_tmp = cfg.hunt_radius + _totem.get("hunt_radius", 0.0)
                    if is_night:
                        _hunt_r_tmp *= PREDATOR_NIGHT_SIGHT
                    if self.campfires:
                        for cf in self.campfires:
                            if w.distance_sq(c.x, c.y, cf["x"], cf["y"]) <= CAMPFIRE_LIGHT_RADIUS * CAMPFIRE_LIGHT_RADIUS:
                                _hunt_r_tmp = 0.0
                                break
                    _batch_r = max(_batch_r, _hunt_r_tmp * 2.0, _hunt_r_tmp * (1.0 + scent_boost))
                elif not c.is_predator:
                    _batch_r = max(_batch_r, fear_radius_eff * (1.0 + scent_boost), cfg.fear_radius)
        if is_night and c.status in ("hungry", "starving") and not c.is_predator:
            _batch_r = max(_batch_r, FOOD_SCENT_RADIUS)
        # §AU CPU: extend batch to cover social micro-queries so every later
        # scan reuses the same hash lookup (law-preserving superset).
        _batch_r = max(_batch_r, YIELD_RADIUS, cfg.flock_radius, PRIEST_CALM_RADIUS, TORCH_LIGHT_RADIUS, DRESS_RADIUS, CAMPFIRE_LIGHT_RADIUS, max(8.0, cfg.fear_radius))
        # Use fast list variant to avoid generator overhead (1627) — always populated for food perception
        _batch_list: list[tuple[Entity, float]] = w.query_radius_with_dist_sq_list(c.x, c.y, _batch_r) if _batch_r > 0 else []  # type: ignore[assignment]
        if cfg.predation_enabled and c.is_predator and c.bite_cooldown <= 0:
                # Find nearest non-predator prey within hunt_radius (+2 Wolf totem)
                # §AO Phase B: night vision +40% in the dark; a lit campfire
                # is a wall of light no beast will cross.
                hunt_r = _hunt_r_tmp
                best_prey: Creature | None = None
                best_prey_d_sq = math.inf
                # §AR S-2: a torch bearer glows in the dark — visible twice
                # as far as any honest shadow.
                torch_glow_r2 = (hunt_r * 2.0) ** 2 if hunt_r > 0 else 0.0
                sight_r2 = hunt_r * hunt_r if hunt_r > 0 else math.inf
                # AY fix: reuse batched query (_batch_list already contains all prey within max search radius)
                for o, d2 in _batch_list:
                    if not isinstance(o, Creature) or o.id == c.id or o.is_predator:
                        continue
                    if o.id not in w.entities or o.indoors:
                        continue  # indoors prey are safe (predator refuge)
                    # §AR S-2: a torch bearer glows twice as far as any shadow
                    if getattr(o, "equipped_item", None) == "torch":
                        if d2 < torch_glow_r2 and d2 < best_prey_d_sq:
                            best_prey_d_sq, best_prey = d2, o
                        continue
                    # §AQ PH-2: beyond base sight only UPWIND prey is smelled
                    if d2 >= sight_r2:
                        if scent_boost <= 0.0:
                            continue
                        d = math.sqrt(d2) or 1e-6
                        dx, dy = w.delta(o.x, o.y, c.x, c.y)  # prey relative to predator
                        upwind = max(0.0, -(dx * wx_s + dy * wy_s) / d)
                        eff = hunt_r * (1.0 + scent_boost * upwind)
                        if d > eff:
                            continue
                    # §AU-fix: NEAREST always wins — a passing far candidate
                    # must never replace a closer one.
                    if d2 < best_prey_d_sq:
                        best_prey_d_sq, best_prey = d2, o
                # §AR S-2: terrain camouflage — prey standing in mature cover
                # are only visible at 80% of the hunter's reach.
                if (
                    best_prey is not None
                    and best_prey_d_sq > (hunt_r * CAMOUFLAGE_HUNT_MULT) ** 2
                ):
                    for veg, vd2 in w.query_radius_with_dist_sq(
                        best_prey.x, best_prey.y, CAMOUFLAGE_RANGE,
                    ):
                        if (
                            isinstance(veg, Food)
                            and veg.growth >= 1.0
                            and veg.variant in ("berry", "grass", "grain")
                        ):
                            best_prey, best_prey_d_sq = None, math.inf
                            break
                if best_prey is not None:
                    if best_prey_d_sq <= cfg.eat_radius * cfg.eat_radius:
                        # Bite — instant kill, predator feeds
                        self._kill(best_prey, "predation")
                        c.energy = min(cfg.energy_max, c.energy + cfg.energy_from_prey)
                        c.bite_cooldown = cfg.bite_cooldown
                        c.meals += 1
                        self._emit(
                            HistoryEvent(
                                type="predation",
                                tick=self.tick + 1,
                                entity_id=c.id,
                                caste=c.caste,
                                x=round(c.x, 2),
                                y=round(c.y, 2),
                                payload={"prey": best_prey.id, "prey_caste": best_prey.caste},
                            )
                        )
                        # Skip further steering this tick — predator just fed
                        hunt_target = None
                    else:
                        hunt_target = best_prey
                        # §AO Phase B: past midnight beasts converge in packs —
                        # the finder shares the kill with any wolf in earshot.
                        if tod > PACK_HOUR and len(self.signals) < SIGNALS_MAX:
                            self.signals.append({
                                "x": round(c.x, 2), "y": round(c.y, 2),
                                "kind": "pack", "sender": c.id,
                                "clan_id": None, "born_tick": self.tick, "ttl": 12,
                                "threat_x": round(hunt_target.x, 2),
                                "threat_y": round(hunt_target.y, 2),
                            })
                        # §AR S-1: three or more beasts together raise a war
                        # cry that carries twice as far and wakes sleepers.
                        if len(self.signals) < SIGNALS_MAX and (
                            self.rng.random() < 0.15
                        ):
                            pack_n = 0
                            for o2, d22 in w.query_radius_with_dist_sq(c.x, c.y, PACK_RADIUS):
                                if isinstance(o2, Creature) and o2.is_predator and o2.id != c.id:
                                    pack_n += 1
                            if pack_n >= 2:
                                self.signals.append({
                                    "x": round(c.x, 2), "y": round(c.y, 2),
                                    "kind": "warcry", "sender": hunt_target.id,
                                    "clan_id": None, "born_tick": self.tick,
                                    "ttl": max(6, int(cfg.signal_radius * WARCRY_RADIUS_MULT / cfg.signal_speed)) if cfg.signal_speed > 0 else 24,
                                    "threat_x": round(c.x, 2), "threat_y": round(c.y, 2),
                                })
        elif cfg.predation_enabled and not c.is_predator:
            # Normal creature / prey: flee the nearest predator
            # §AR S-2: forward cone = 120° full vision; rear hemisphere
            # detects at half range (smell ignores facing).
            # §AR S-2 canon: beyond half range an Isosceles triangle is
            # misread as a predator 30% of the time.
            # §AR S-4: kin are recognized by scent up close — no panic.
            ca, sa = math.cos(c.angle), math.sin(c.angle)
            best_pred: Creature | None = None
            best_pred_d_sq = math.inf
            fear_r_sq = cfg.fear_radius * cfg.fear_radius
            # §AX P1: reuse batched list instead of separate query
            for o, d2 in _batch_list:
                if d2 > fear_r_sq or not isinstance(o, Creature) or not o.is_predator or o.id not in w.entities:
                    continue
                dxo, dyo = w.delta(c.x, c.y, o.x, o.y)
                fwd = dxo * ca + dyo * sa  # >0: in the forward half
                visual_limit = (
                    fear_radius_eff if fwd >= VISION_CONE_COS
                    else fear_radius_eff * REAR_SIGHT_MULT
                )
                if d2 <= visual_limit * visual_limit:
                    if d2 < best_pred_d_sq:
                        best_pred_d_sq, best_pred = d2, o
                    continue
                # §AQ PH-2: beyond sight only an UPWIND predator reeks
                if scent_boost > 0.0:
                    d = math.sqrt(d2)
                    upwind = max(0.0, -(dxo * wx_s + dyo * wy_s) / (d or 1e-6))
                    eff = fear_radius_eff * (1.0 + scent_boost * upwind)
                    if d <= eff and d2 < best_pred_d_sq:
                        best_pred_d_sq, best_pred = d2, o
            if best_pred is None:
                # phantom wolves: far isosceles silhouettes misread 30%/tick
                # reuse batch (already contains fear_radius candidates)
                for o, d2 in _batch_list:
                    if d2 > fear_r_sq or not isinstance(o, Creature) or o.is_predator or o.id == c.id:
                        continue
                    if o.sides != 3 or (o.clan_id and o.clan_id == c.clan_id):
                        continue  # §AR S-4: kin smell like kin
                    if d2 > (cfg.fear_radius * 0.5) ** 2:
                        continue  # misreading only happens far out
                    if self.rng.random() >= TRIANGLE_FALSE_ALARM:
                        continue
                    best_pred_d_sq, best_pred = d2, o
                    break
            flee_target = best_pred

        # 2. Perceive the nearest meal — food or the fallen. Diet strictness (§O) filters.
        # §X-fix: the Carnivore caste hunts the living and scavenges the dead —
        # it never grazes fields. A predator that could eat plants out-competes
        # every caste for the bounty and the world dies into a wolf monoculture
        # (production incident @ tick 34k: 800 predators, zero clan members).
        target: Entity | None = None
        best_sq = perceive * perceive
        # §AU CPU: batch is superset for all micro-radii — no second hash lookup.
        _food_iter = _batch_list
        for e, d2 in _food_iter:
            if d2 > perceive * perceive:
                continue
            if e.kind not in ("food", "corpse") or e.id in self._eaten:
                continue
            if c.is_predator and e.kind == "food":
                continue
            # A meal given up on (unreachable behind stone or wall) is ignored
            # until its memory fades — the hungry look elsewhere instead of
            # grinding against the obstacle until they starve.
            if cfg.food_giveup_ticks > 0 and (
                self.tick - c.give_ups.get(e.id, -cfg.food_giveup_ticks)
                < cfg.food_giveup_ticks
            ):
                continue
            # Diet & preference (§O): herbivore↔plants, carnivore↔meat, omnivore both; strictness gates.
            if cfg.diet_strictness > 0:
                if c.is_herbivore and e.kind == "corpse":
                    if self.rng.random() < cfg.diet_strictness:
                        continue
                if c.is_predator and e.kind == "food":
                    if self.rng.random() < cfg.diet_strictness:
                        continue
                # higher castes prefer richer food when strict: skip grass if berry nearby (approx)
                if not c.is_herbivore and not c.is_predator and e.kind == "food" and cfg.diet_strictness > 0.5:
                    if isinstance(e, Food) and e.variant == "grass":
                        if self.rng.random() < 0.7:
                            continue
                # herbivores avoid poisonous when strict
                if c.is_herbivore and isinstance(e, Food) and e.variant == "poisonous" and cfg.diet_strictness > 0.3:
                    if self.rng.random() < cfg.diet_strictness:
                        continue
                # trait greedy: prefer richer food (grain/berry/corpse) over grass
                if c.trait == "greedy" and isinstance(e, Food) and e.variant == "grass":
                    if self.rng.random() < 0.45:
                        continue

            effective_d2 = d2
            # Health & status based dietary preferences (§AM)
            if isinstance(e, Food):
                if (c.health < 70.0 or c.infected) and e.variant == "medicinal_herb":
                    effective_d2 *= 0.2  # high attraction to healing herbs
                elif c.status == "starving" and e.variant == "grain":
                    effective_d2 *= 0.4  # high attraction to calorie-dense grain
                else:
                    # §AM E.1 geometric gastronomy — castes keep their own table
                    weight = CASTE_DIET_WEIGHTS.get(c.caste, {}).get(e.variant)
                    if weight is not None:
                        effective_d2 *= weight
            elif e.kind == "corpse" and c.caste == "Soldier":
                effective_d2 *= 0.6  # soldiers crave high-protein rations

            if effective_d2 < best_sq:
                best_sq, target = effective_d2, e

        # §AR S-0 Food scent: ripe plants smell through the dark. A hungry or
        # starving creature whose eyes fail at night still catches the scent
        # of mature food within FOOD_SCENT_RADIUS — no more blind starvation.
        if (
            target is None
            and is_night
            and c.status in ("hungry", "starving")
            and not c.is_predator
        ):
            scent_sq = FOOD_SCENT_RADIUS * FOOD_SCENT_RADIUS
            _scent_iter = _batch_list
            for e, d2 in _scent_iter:
                if d2 > FOOD_SCENT_RADIUS * FOOD_SCENT_RADIUS:
                    continue
                if e.kind != "food" or e.id in self._eaten:
                    continue
                f = cast(Food, e)
                if f.growth < 1.0:
                    continue  # only ripe plants carry a scent worth following
                # a scented meal behind stone/wall stays grudged (§X fixes)
                if cfg.food_giveup_ticks > 0 and (
                    self.tick - c.give_ups.get(e.id, -cfg.food_giveup_ticks)
                    < cfg.food_giveup_ticks
                ):
                    continue
                if d2 < scent_sq:
                    scent_sq = d2
                    target = e
                    best_sq = d2
        # §AN A.3 war-chirp targeting — a soldier facing a rival marks the
        # nearest open-feud enemy as the rally target (one gated query).
        enemy_target: Creature | None = None
        if (
            cfg.vocalizations_enabled
            and c.caste == "Soldier"
            and c.clan_id
            and hunt_target is None
            and flee_target is None
        ):
            er2 = max(8.0, cfg.fear_radius)
            best_enemy_d = er2 * er2 + 1e-9
            _war_chirp_iter = ((o, d2) for o, d2 in _batch_list if d2 <= er2 * er2)
            for o, d2 in _war_chirp_iter:
                if not isinstance(o, Creature) or o.clan_id == c.clan_id or not o.clan_id:
                    continue
                pair_z = self.relations.get(self._relation_pair(c.clan_id, o.clan_id), 0)
                if self._zone_of(pair_z) != -1 or d2 >= best_enemy_d:
                    continue
                best_enemy_d, enemy_target = d2, o

        # §AC Desperation: the starving may hunt the living. Sated/hungry
        # creatures never do; a cooldown separates desperate kills.
        prey_target: Creature | None = None
        if (
            cfg.cannibalism_enabled
            and c.status == "starving"
            and c.cannibal_cooldown <= 0
            and not c.is_predator
            and not c.is_herbivore
        ):
            prey_target = self._cannibal_prey(c, perceive)

        # §X Knowledge — firsthand experience: seen meal, seen predator.
        if cfg.knowledge_enabled:
            if target is not None and isinstance(target, Food):
                self._learn(c, "food", target.x, target.y)
            if flee_target is not None:
                self._learn(c, "danger", flee_target.x, flee_target.y)
            if c.indoors:
                home_fact = inside_house_obj or assigned_roof or (self._house_for(c, houses) if not roof_resolved else None)
                if home_fact is not None:
                    self._learn(c, "safe", home_fact.x, home_fact.y)
        if c.signal_cooldown > 0:
            c.signal_cooldown -= 1
        # §Q Communication — food and alarm calls
        if cfg.communication_enabled:
            # Food call: well-fed finds food → calls clan-mates
            if target is not None and c.energy / cfg.energy_max > cfg.hungry_ratio and c.signal_cooldown == 0:
                if self.rng.random() < cfg.food_call_rate:
                    self.signals.append({"x": c.x, "y": c.y, "kind": "food", "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 15, "food_x": target.x, "food_y": target.y})
                    c.signal_cooldown = 8
                # §AN B.2 forager scent trails — rich finds leave a breadcrumb
                # line home for hungry kin to follow (rain washes scent faster)
                elif (
                    isinstance(target, Food)
                    and target.variant in ("grain", "berry", "medicinal_herb")
                    and len(self.signals) < SIGNALS_MAX
                    and self.rng.random() < TRAIL_DROP_CHANCE * (2.0 if self.weather == "clear" else 1.0)
                ):
                    self.signals.append({
                        "x": round(c.x, 2), "y": round(c.y, 2), "kind": "trail",
                        "sender": c.id, "clan_id": c.clan_id or None,
                        "born_tick": self.tick, "ttl": SCENT_TTL, "food_x": round(target.x, 2), "food_y": round(target.y, 2),
                    })
            # Alarm call: sees predator → alarm; teeth-close → a cry for help (§X)
            if flee_target is not None and c.signal_cooldown == 0:
                close = (
                    cfg.help_call_enabled
                    and cfg.knowledge_enabled
                    and w.distance_sq(c.x, c.y, flee_target.x, flee_target.y) < (cfg.help_radius * 0.6) ** 2
                )
                if self.rng.random() < cfg.alarm_call_rate or close:
                    kind = "help" if close else "alarm"
                    sg: dict[str, Any] = {"x": c.x, "y": c.y, "kind": kind, "sender": c.id, "clan_id": c.clan_id or None, "ttl": 12}
                    if kind == "help":
                        sg.update({"threat_x": round(flee_target.x, 2), "threat_y": round(flee_target.y, 2), "threat_clan": flee_target.clan_id or None})
                    self.signals.append(sg)
                    c.signal_cooldown = 10
            # §X Teaching: broadcast the freshest fact to clan-mates
            if cfg.knowledge_enabled and c.signal_cooldown == 0 and self.rng.random() < cfg.knowledge_share_rate:
                fact_msg = self._fact_to_share(c)
                if fact_msg is not None:
                    self.signals.append({"x": c.x, "y": c.y, "kind": "knowledge", "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 12, "fact": fact_msg})
                    c.signal_cooldown = 14
            # Recruitment: sated clan-mate near starving one calls toward remembered food (§Q Care)
            food_fact = self._fact_fresh(c, "food") if cfg.knowledge_enabled else None
            remembered_food = (food_fact["x"], food_fact["y"]) if food_fact is not None else None
            if remembered_food is not None and c.energy / cfg.energy_max > 0.6:
                for other in w.query_radius(c.x, c.y, cfg.flock_radius):
                    if not isinstance(other, Creature) or other.id == c.id:
                        continue
                    if other.clan_id != c.clan_id:
                        continue
                    if other.energy / cfg.energy_max > cfg.starving_ratio:
                        continue  # only starving
                    if c.signal_cooldown == 0 and self.rng.random() < 0.08:
                        self.signals.append({"x": c.x, "y": c.y, "kind": "food", "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 12, "food_x": remembered_food[0], "food_y": remembered_food[1]})
                        c.signal_cooldown = 12
                        break

        # §AR S-4: smell made physical — scent marks and trails ride the air.
        if cfg.scent_enabled and not c.sleeping and len(self.signals) < SIGNALS_MAX:
            # territorial marking: sentries and chiefs scent the border
            if (
                c.clan_id
                and (c.caste == "Soldier" or self.clans.get(c.clan_id, {}).get("leader_id") == c.id)
                and (self.tick + c.id) % 45 == 0
            ):
                mh = self.world.entities.get(self.clans[c.clan_id].get("main_house_id")) if self.clans[c.clan_id].get("main_house_id") is not None else None
                if isinstance(mh, House):
                    d_home = w.distance(c.x, c.y, mh.x, mh.y)
                    if abs(d_home - cfg.territory_radius) <= cfg.territory_radius * 0.35:
                        ttl = max(10, int(SCENT_TTL / 2)) if self.weather in ("rain", "storm") else SCENT_TTL
                        self.signals.append({
                            "x": round(c.x, 2), "y": round(c.y, 2), "kind": "territory",
                            "sender": c.id, "clan_id": c.clan_id or None,
                            "born_tick": self.tick, "ttl": min(ttl, 90),
                        })
            # forager/prey scent: every moving body leaves a fading trail;
            # rain washes it thin. Predators leave their own — prey learn fear.
            if (self.tick + c.id) % 40 == 0 and (c.status or c.is_predator):
                ttl = max(8, SCENT_TTL // 2) if self.weather in ("rain", "storm") else SCENT_TTL
                kind = "pred_scent" if c.is_predator else "prey_scent"
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2), "kind": kind,
                    "sender": c.id, "clan_id": c.clan_id or None,
                    "born_tick": self.tick, "ttl": ttl,
                })
            # §AR S-6/S-7: the sick reek of sickness; the healthy take note.
            if (
                cfg.disease_enabled
                and c.infected
                and (self.tick + c.id) % 20 == 0
            ):
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2), "kind": "disease",
                    "sender": c.id, "clan_id": c.clan_id or None,
                    "born_tick": self.tick, "ttl": 30,
                })

        # §AN Phase A — every caste has a voice: the priest's liturgy, the
        # woman's peace-hum, the soldier's war-chirp.
        if cfg.vocalizations_enabled and c.signal_cooldown == 0 and not c.is_predator and not c.is_herbivore:
            if c.caste == "Priest" and self.rng.random() < CHANT_CHANCE:
                # Sonorous liturgy — calm flows outward through the clan
                self.signals.append({"x": round(c.x, 2), "y": round(c.y, 2), "kind": "chant", "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 10})
                c.signal_cooldown = 16
            elif c.shape == "line" and self.rng.random() < HUM_CHANCE:
                # Peace-hum — polygons step aside; corridors stay walkable (§C law)
                self.signals.append({"x": round(c.x, 2), "y": round(c.y, 2), "kind": "hum", "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 8})
                c.signal_cooldown = 14
            elif (
                c.caste == "Soldier"
                and (hunt_target is not None or flee_target is not None
                     or prey_target is not None or enemy_target is not None)
                and self.rng.random() < WARCHIRP_CHANCE
            ):
                # War-chirp — allied soldiers rally onto the flagged target
                threat = hunt_target or flee_target or prey_target or enemy_target
                self.signals.append({
                    "x": round(c.x, 2), "y": round(c.y, 2), "kind": "war",
                    "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 10,
                    "threat_x": round(threat.x, 2), "threat_y": round(threat.y, 2),
                })
                c.signal_cooldown = 12

        # §AN B — tactile recognition: touching vertices in peace builds trust;
        # an elder's blessing touch passes a sliver of skill to the young; a
        # friendly artisan's chime opens the basket for a gift.
        if (
            cfg.vocalizations_enabled
            and c.greet_cooldown <= 0
            and not c.sleeping
            and not c.is_predator
            and not c.is_herbivore
            and (self.tick + c.id) % 29 == 0
        ):
            for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, 1.2):
                if not isinstance(o, Creature) or o.id == c.id or o.sleeping:
                    continue
                if o.is_predator or o.is_herbivore:
                    continue
                kin = o.clan_id and o.clan_id == c.clan_id
                if not kin:
                    pair = self._relation_pair(c.clan_id, o.clan_id) if c.clan_id and o.clan_id else None
                    if pair is None or self.relations.get(pair, 0) <= cfg.rivalry_threshold // 2:
                        continue  # no greetings across open feuds
                c.greet_cooldown = 60
                o.trust[c.id] = min(100.0, o.trust.get(c.id, 0.0) + GREET_TRUST) if isinstance(o.trust, dict) else o.trust
                c.trust[o.id] = min(100.0, c.trust.get(o.id, 0.0) + GREET_TRUST) if isinstance(c.trust, dict) else c.trust
                # Elder blessing touch — skill flows to the next generation
                if c.stage == "elder" and o.stage in ("infant", "juvenile"):
                    skills_d = getattr(c, "skills", {})
                    if skills_d:
                        best_skill = max(skills_d, key=lambda k: skills_d.get(k, 0.0))
                        o.skills[best_skill] = o.skills.get(best_skill, 0.0) + ELDER_TOUCH_XP
                        o.emote = "cheer"
                        o.emote_ticks = 10
                # Artisan trade chime — greeting gifts from the basket
                if c.caste == "Artisan" and c.food_basket > 0 and o.energy < 65.0:
                    c.food_basket -= 1
                    o.energy = min(cfg.energy_max, o.energy + ARTISAN_GIFT_ENERGY)
                    o.emote = "cheer"
                    o.emote_ticks = 12
                    self.signals.append({"x": round(c.x, 2), "y": round(c.y, 2), "kind": "chime", "sender": c.id, "clan_id": c.clan_id or None, "born_tick": self.tick, "ttl": 8})
                    if not kin and c.clan_id and o.clan_id:
                        self._bump_relation(c.clan_id, o.clan_id, 1)
                break

        # §AN E.1 ruin archaeology — explorers reading old walls recover lost
        # technique: farming & foraging insight, vague lore of the old farms.
        if cfg.knowledge_enabled and (self.tick + c.id) % 23 == 7 and c.personality == "explorer":
            for e in w.query_radius(c.x, c.y, 4.0):
                if e.kind == "house" and getattr(e, "is_ruin", False):
                    c.skills["farming"] = c.skills.get("farming", 0.0) + 0.06
                    c.skills["foraging"] = c.skills.get("foraging", 0.0) + 0.04
                    self._learn(c, "food", e.x + 2.0, e.y - 2.0, conf=0.4)  # old farms fed these walls
                    break

        # 3. Steer — priority: flee > hunt > home for night > food > wander
        # §Q Hearing signals — clan-mates respond strongly; §X knowledge & help
        signal_food_target = None
        signal_alarm_target = None
        signal_help_target = None
        signal_hum_source = None  # §AN woman's peace-hum — corridor clearing
        best_help_d_sq = math.inf
        alarm_heard_conf = 1.0  # §AR S-1: distance attenuation of the cry
        disease_scent_near = False  # §AR S-6: sickness in the air
        retreat_heard = False  # §AS L-2: the general sounded retreat
        harvest_order = False  # §AS L-2: autumn stores call
        harvest_house: tuple[float, float] | None = None
        if cfg.communication_enabled and self.signals:
            sig_r = cfg.signal_radius
            # §AQ PH-2: sound rides the wind - listeners DOWNWIND of a source
            # hear it farther (the pressure wave drifts with the air).
            snd_boost = SOUND_WIND_MULT * self.wind_speed if cfg.scent_enabled else 0.0
            wx_s, wy_s = self._cos_wind, self._sin_wind
            # §AU O-2: hoisted per-tick constants and a cheap squared
            # far-reject before any wavefront trig runs.
            sig_r2 = sig_r * sig_r
            half_w = cfg.width * 0.5
            half_h = cfg.height * 0.5
            max_hear_d = sig_r * 2.5 * (1.0 + snd_boost)
            max_hear_d2 = max_hear_d * max_hear_d
            best_food_sq = math.inf
            best_alarm_sq = math.inf
            my_dialect = float(self.clans.get(c.clan_id, {}).get("dialect", 0.0)) if c.clan_id else 0.0
            # §AU CPU: grid-gather signals within max_hear_d (law-preserving superset,
            # insertion-order sorted, wrap-aware). O(S) -> O(~5-10) per creature.
            _sg_grid = getattr(self, "_signal_grid", {})
            _sg_cs = getattr(self, "_signal_grid_cs", self.world.cell_size)
            _sg_cols = self.world.cols
            _sg_rows = self.world.rows
            if _sg_grid:
                _rx = int(max_hear_d // _sg_cs) + 1
                _cx0 = int(c.x // _sg_cs) % _sg_cols if _sg_cols else 0
                _cy0 = int(c.y // _sg_cs) % _sg_rows if _sg_rows else 0
                if self.world.config.boundary == "wrap":
                    _cand: list[tuple[int, dict]] = []
                    _seen_cells: set[tuple[int,int]] = set()
                    for _dx in range(-_rx, _rx + 1):
                        for _dy in range(-_rx, _rx + 1):
                            _cx = (_cx0 + _dx) % _sg_cols if _sg_cols else 0
                            _cy = (_cy0 + _dy) % _sg_rows if _sg_rows else 0
                            if (_cx, _cy) in _seen_cells:
                                continue
                            _seen_cells.add((_cx, _cy))
                            bucket = _sg_grid.get((_cx, _cy))
                            if bucket:
                                _cand.extend(bucket)
                    _cand.sort(key=lambda t: t[0])
                    _iter_signals = (sg for _, sg in _cand)
                else:
                    # clamp: collect cells overlapping max_hear_d square
                    _cand = []
                    if _sg_grid:
                        # fallback to direct collection via bounding box
                        for (gx, gy), bucket in _sg_grid.items():
                            # quick cell-center far reject
                            cx_cell = (gx + 0.5) * _sg_cs
                            cy_cell = (gy + 0.5) * _sg_cs
                            if abs(cx_cell - c.x) > max_hear_d + _sg_cs and abs(cy_cell - c.y) > max_hear_d + _sg_cs:
                                continue
                            _cand.extend(bucket)
                        _cand.sort(key=lambda t: t[0])
                    _iter_signals = (sg for _, sg in _cand) if _cand else iter(self.signals)
                    # For clamp small maps, if grid sparse, fallback to filtered linear scan is still cheaper
                    if not _cand:
                        _iter_signals = (sg for sg in self.signals)
                        # apply same far-reject quickly inside loop anyway
            else:
                _iter_signals = iter(self.signals)
            for sg in _iter_signals:
                dxw = sg["x"] - c.x
                if dxw > half_w:
                    dxw -= cfg.width
                elif dxw < -half_w:
                    dxw += cfg.width
                adx = dxw if dxw >= 0 else -dxw
                if adx > max_hear_d:
                    continue
                dyw = sg["y"] - c.y
                if dyw > half_h:
                    dyw -= cfg.height
                elif dyw < -half_h:
                    dyw += cfg.height
                ady = dyw if dyw >= 0 else -dyw
                if ady > max_hear_d:
                    continue
                d2 = dxw * dxw + dyw * dyw
                if d2 > max_hear_d2:
                    continue  # beyond every reach: no wavefront math needed
                # §AQ PH-8: news travels at finite speed — the wavefront
                # expands from the source (faster downwind) and a listener
                # too far away simply hasn't heard it yet.
                born = sg.get("born_tick")
                if born is not None and cfg.signal_speed > 0.0:
                    age_t = self.tick - born
                    dl = math.sqrt(d2) or 1e-6
                    tail = (dxw * self._cos_wind + dyw * self._sin_wind) / dl
                    if tail <= 0.0:
                        # no tailwind: plain radius check, squared
                        speed0 = cfg.signal_speed
                        if d2 > age_t * age_t * speed0 * speed0:
                            continue
                    else:
                        speed = cfg.signal_speed * (1.0 + 0.4 * self.wind_speed * tail)
                        if dl > age_t * speed:
                            continue
                if d2 > sig_r2:
                    # §AQ PH-2: beyond base range only the downwind ear catches
                    # the call - and never through a roof. Downwind means the
                    # WIND carries the call TOWARD the listener: align
                    # (listener - source) with the wind vector.
                    if snd_boost <= 0.0 or c.indoors or d2 >= (sig_r * 2.5) ** 2:
                        continue
                    d_snd = math.sqrt(d2)
                    dxs, dys = w.delta(sg["x"], sg["y"], c.x, c.y)  # source rel. listener
                    downwind = max(0.0, -(dxs * wx_s + dys * wy_s) / d_snd)
                    if d_snd > sig_r * (1.0 + snd_boost * downwind):
                        continue
                kind = sg["kind"]
                # §AQ PH-2: roofs muffle the world - indoors creatures cannot
                # hear alarms or cries for help raised out in the open.
                if (
                    c.indoors
                    and kind in ("alarm", "help", "boom")
                    and not self._point_in_any_house(sg["x"], sg["y"])
                ):
                    continue
                # clan weighting: clan-mates always hear; strangers hear less,
                # the less our dialects agree (§AN E.2 linguistic drift)
                is_kin = sg.get("clan_id") and sg.get("clan_id") == c.clan_id
                if not is_kin:
                    if cfg.dialect_drift_enabled:
                        sender_dialect = float(self.clans.get(sg.get("clan_id") or -1, {}).get("dialect", 0.0))
                        ignore_p = max(0.45, min(0.95, 0.45 + abs(my_dialect - sender_dialect) * 0.5))
                    else:
                        ignore_p = 0.65
                    if self.rng.random() < ignore_p:
                        continue
                if (kind == "food" or kind == "trail") and c.status in ("hungry", "starving"):
                    # §AN B.2: scent trails point at the patch like a food call;
                    # food signals point to food_x/food_y if present, else sender pos
                    fx = sg.get("food_x", sg["x"])
                    fy = sg.get("food_y", sg["y"])
                    df2 = w.distance_sq(c.x, c.y, fx, fy)
                    if df2 < best_food_sq:
                        best_food_sq = df2
                        signal_food_target = (fx, fy)
                elif kind == "prey_scent" and c.is_predator:
                    # §AR S-4: a nose to the ground — wolves track fresh trails
                    # even before hunger bites.
                    if hunt_target is None and flee_target is None and d2 < best_food_sq:
                        best_food_sq = d2
                        signal_food_target = (sg["x"], sg["y"])
                elif kind == "pred_scent" and not c.is_predator:
                    # §AR S-4: prey smell wolf-passages and learn the danger
                    self._learn(c, "danger", sg["x"], sg["y"], conf=0.5)
                elif kind == "territory" and cfg.knowledge_enabled:
                    # §AR S-4: a rival's border-stench names its clan as enemy
                    marker_clan = sg.get("clan_id")
                    if marker_clan and marker_clan != c.clan_id:
                        self._learn_enemy(c, marker_clan)
                elif kind == "disease":
                    # §AR S-6/S-7: sickness has a smell — the healthy mark the
                    # spot dangerous (high castes notice first) and drift home.
                    if not c.infected and c.sides >= 4 and cfg.knowledge_enabled:
                        old_danger = self._fact_fresh(c, "danger")
                        if old_danger is None or float(old_danger.get("conf", 0.0)) < 0.4:
                            self._learn(c, "danger", sg["x"], sg["y"], conf=0.4)
                    u_shelter_bonus = 0.2  # applied below via flag
                    disease_scent_near = True
                elif kind == "chant" and cfg.vocalizations_enabled and is_kin:
                    # §AN A.1 liturgy: panic drains away; the starving find heart
                    c.panic_ticks = 0
                    c.calm_ticks = max(c.calm_ticks, 20)
                elif kind == "hum" and cfg.vocalizations_enabled and c.shape != "line":
                    # §AN A.2 peace-hum: polygons yield the corridor
                    if signal_hum_source is None or d2 < w.distance_sq(c.x, c.y, *signal_hum_source):
                        signal_hum_source = (sg["x"], sg["y"])
                elif kind == "war" and cfg.vocalizations_enabled and c.caste == "Soldier" and is_kin:
                    # §AN A.3 war-chirp: allied soldiers converge on the flagged target
                    tx, ty = sg.get("threat_x", sg["x"]), sg.get("threat_y", sg["y"])
                    td2 = w.distance_sq(c.x, c.y, tx, ty)
                    if td2 < best_help_d_sq:
                        best_help_d_sq = td2
                        signal_help_target = (tx, ty)
                elif kind == "chime" and cfg.envoys_enabled and c.caste == "Soldier" and is_kin:
                    # §AN C.3 boundary stone rings — sentries walk the border
                    tx, ty = sg.get("stone_x", sg["x"]), sg.get("stone_y", sg["y"])
                    td2 = w.distance_sq(c.x, c.y, tx, ty)
                    if td2 < best_help_d_sq:
                        best_help_d_sq = td2
                        signal_help_target = (tx, ty)
                elif kind == "pack" and cfg.predation_enabled and c.is_predator:
                    # §AO Phase B: pack convergence — beasts rally to the
                    # flagged prey past midnight.
                    tx, ty = sg.get("threat_x", sg["x"]), sg.get("threat_y", sg["y"])
                    td2 = w.distance_sq(c.x, c.y, tx, ty)
                    if hunt_target is None and flee_target is None and td2 < best_help_d_sq:
                        best_help_d_sq = td2
                        signal_help_target = (tx, ty)
                elif kind == "rally" and is_kin:
                    # §AR S-5: the banner is raised — kin mark the spot;
                    # only hearts above despair answer the call.
                    if (
                        c.morale >= MORALE_RALLY_MIN
                        and getattr(c, "waypoints", None) is not None
                    ):
                        c.waypoints["rally"] = (sg["x"], sg["y"])
                    # §AS L-1: a rally before battle sharpens every blade.
                    if c.caste == "Soldier" and c.morale >= MORALE_RALLY_MIN:
                        c.combat_boost_ticks = COMBAT_BOOST_TICKS
                elif kind == "retreat" and is_kin:
                    # §AS L-2: the general is bleeding — everyone home, now.
                    retreat_heard = True
                elif kind == "harvest" and is_kin:
                    # §AS L-2: the granary calls — farmers work the fields hard.
                    harvest_order = True
                    harvest_house = (sg.get("house_x", sg["x"]), sg.get("house_y", sg["y"]))
                elif kind == "evacuate" and is_kin:
                    # §AS L-2: fire and flood — run THIS way.
                    ex2, ey2 = sg.get("evac_x", sg["x"]), sg.get("evac_y", sg["y"])
                    if getattr(c, "waypoints", None) is not None:
                        c.waypoints["evacuate"] = (ex2, ey2)
                elif kind == "interpret" and is_kin:
                    # §AS L-6: the chief's reading of God's law bends the
                    # clan's mood for a while — war-hunger or blessing-calm.
                    if sg.get("tone") == "war" and c.caste == "Soldier":
                        c.combat_boost_ticks = max(c.combat_boost_ticks, LAW_INTERPRET_TICKS)
                        c.morale = min(100.0, c.morale + 2.0)
                    else:
                        c.calm_ticks = max(c.calm_ticks, LAW_INTERPRET_TICKS)
                        c.morale = min(100.0, c.morale + 3.0)
                elif kind == "omen" and cfg.omens_enabled and is_kin:
                    # §AN E.3 the priest has seen the turning of the season
                    c.prepared_ticks = PREPARED_TICKS
                elif kind == "joy" and is_kin:
                    # §AR S-7: birth is literally good news — a small gift of
                    # energy and health rides the cheer.
                    c.energy = min(cfg.energy_max, c.energy + float(sg.get("joy_energy", 2.0)))
                    c.health = min(c.max_health, c.health + float(sg.get("joy_health", 1.0)))
                    c.morale = min(100.0, c.morale + MORALE_EAT_RESTORE * 0.25)
                    if not c.emote:
                        c.emote = "cheer"
                        c.emote_ticks = 12
                elif kind == "danger_scent" and cfg.scent_enabled:
                    # §AN B.3: the young and vulnerable learn to shun death sites
                    if c.stage in ("infant", "juvenile") or c.health < 50.0:
                        self._learn(c, "danger", sg["x"], sg["y"], conf=0.6)
                elif kind == "grief" and is_kin:
                    # §AR S-7: shared loss bonds survivors — kin pause a few
                    # ticks to mourn, and those present draw closer together.
                    # Nobody mourns mid-flight or mid-ford: an active threat
                    # or moving water overrides grief.
                    if flee_target is None and (
                        not self.rivers or not self._in_river_band(c.x, c.y)
                    ):
                        c.pause_ticks = 1 + (c.id % 3)
                        if not c.emote:
                            c.emote = "grief"
                            c.emote_ticks = 12
                    for oid in sg.get("witnesses", ()):
                        if oid != c.id:
                            cur = c.trust.get(oid, 0.0)
                            c.trust[oid] = min(100.0, cur + 5.0)
                elif kind == "knowledge" and cfg.knowledge_enabled:
                    self._hear_fact(c, sg.get("fact"), sg.get("sender"))
                    f = (sg.get("fact") or {})
                    if (
                        f.get("kind") == "food"
                        and c.status in ("hungry", "starving")
                        and signal_food_target is None
                    ):
                        df2 = w.distance_sq(c.x, c.y, f.get("x", sg["x"]), f.get("y", sg["y"]))
                        if df2 < best_food_sq:
                            best_food_sq = df2
                            signal_food_target = (f.get("x", sg["x"]), f.get("y", sg["y"]))
                elif sg["kind"] == "help" and cfg.help_call_enabled and is_kin:
                    # §X Mobbing: rally to the defender's aid — warriors first,
                    # the peaceful lag behind, high castes only when bold.
                    rank = YIELD_RANK.get(c.caste, 3)
                    if rank >= 5 and c.trait != "bold":
                        continue
                    if c.trait == "peaceful" and self.rng.random() < 0.7:
                        continue
                    if not c.is_predator and not c.is_herbivore and d2 < best_help_d_sq:
                        best_help_d_sq = d2
                        signal_help_target = (sg.get("threat_x", sg["x"]), sg.get("threat_y", sg["y"]))
                elif sg["kind"] == "alarm" and flee_target is None:
                    if d2 < best_alarm_sq:
                        best_alarm_sq = d2
                        # §AR S-1: confidence fades with distance — far alarms
                        # move us less than close ones.
                        signal_alarm_target = sg
                        alarm_heard_conf = max(0.0, 1.0 - math.sqrt(d2) / (sig_r * (1.0 + snd_boost)))
                elif sg["kind"] == "warcry":
                    # §AR S-1: a predator pack's war cry carries twice as far
                    # and tears sleeping prey from their beds.
                    if c.alarm_wake_ticks < 20:
                        c.alarm_wake_ticks = 20
                    if flee_target is None and d2 < best_alarm_sq:
                        best_alarm_sq = d2
                        signal_alarm_target = sg
                        alarm_heard_conf = max(0.0, 1.0 - math.sqrt(d2) / (sig_r * WARCRY_RADIUS_MULT))
        # §X Danger zones: remembered predator sightings are avoided on sight of memory
        danger_avoid_target = None
        if cfg.knowledge_enabled and flee_target is None and c.status != "":
            danger_fact = self._fact_fresh(c, "danger")
            if danger_fact is not None and "x" in danger_fact:
                dd2 = w.distance_sq(c.x, c.y, danger_fact["x"], danger_fact["y"])
                if dd2 < (cfg.fear_radius * 1.5) ** 2:
                    danger_avoid_target = (danger_fact["x"], danger_fact["y"])
        # §AL Multi-Objective Utility Engine & Purposeful Tactical Steering
        if flee_target is not None:
            self._fleeing_ids.add(c.id)
        u_flee = 0.0
        if flee_target is not None:
            u_flee = 1.2
            if c.personality == "cautious":
                u_flee += 0.3
            elif c.personality == "brave" and c.caste == "Soldier":
                u_flee -= 0.3
            if c.health < 40.0:
                u_flee += 0.4
        # §AS L-0: the clan shock — for LEADER_SHOCK_PANIC_TICKS after the
        # leader's death every member startles at shadows.
        if c.panic_ticks > 0:
            u_flee += LEADER_SHOCK_U_FLEE
        # §AR S-5: panic is contagious — a running kinspanics the flock;
        # a priest's presence steadies it.
        if not c.is_predator and not c.is_herbivore:
            panicked_mate = False
            priest_near = False
            for o, d2o in w.query_radius_with_dist_sq(c.x, c.y, max(cfg.flock_radius, PRIEST_CALM_RADIUS)):
                if not isinstance(o, Creature) or o.id == c.id or o.clan_id != c.clan_id:
                    continue
                if o.id in getattr(self, "_fleeing_ids", ()) or o.panic_ticks > 0:
                    panicked_mate = True
                if o.caste == "Priest" and d2o <= PRIEST_CALM_RADIUS * PRIEST_CALM_RADIUS:
                    priest_near = True
            if panicked_mate and (
                flee_target is not None or self._fact_fresh(c, "danger") is not None
            ):
                # §AR S-5: contagion amplifies awareness — kin who smell the
                # threat secondhand join the flight; the truly oblivious stay.
                u_flee += PANIC_CONTAGION
            if priest_near and u_flee > 0.2:
                u_flee -= PRIEST_CALM_BONUS

        # §AR S-1: habituation — the same alarm ringing for many ticks stops
        # moving anyone; a fresh source startles anew.
        if signal_alarm_target is not None:
            sender_id = signal_alarm_target.get("sender", -1)
            if sender_id == c.last_alarm_sender:
                c.alarm_streak += 1
            else:
                c.last_alarm_sender = sender_id
                c.alarm_streak = 0
        else:
            c.alarm_streak = 0
            c.last_alarm_sender = -1
        u_alarm = 0.0
        if signal_alarm_target is not None and flee_target is None:
            u_alarm = max(0.25, alarm_heard_conf)
            if c.alarm_streak >= ALARM_HABITUATION_TICKS:
                u_alarm *= ALARM_HABITUATED_U

        u_help = 0.0
        if signal_help_target is not None and flee_target is None:
            u_help = 0.8
            if c.personality == "brave" or c.equipped_item == "spear":
                u_help += 0.35
            if c.personality == "cautious" or c.health < 35.0:
                u_help -= 0.45
        # §AS L-1: bodyguard clustering — soldiers hold their chief's side
        # above any other call; the cluster emerges from the utility system.
        if (
            c.caste == "Soldier"
            and c.clan_id
            and not c.is_predator
            and flee_target is None
        ):
            lpos_bg = getattr(self, "_leader_pos", {}).get(c.clan_id)
            aura_r = LEADER_AURA_RADIUS * (
                MONARCHY_AURA_MULT if self.clans.get(c.clan_id, {}).get("governance") == "monarchy" else 1.0
            )
            if lpos_bg is not None and w.distance_sq(c.x, c.y, *lpos_bg) <= aura_r * aura_r:
                # override any far help cry — the chief is the priority
                signal_help_target = lpos_bg
                u_help = max(u_help, BODYGUARD_U_HELP)

        u_hunt = 1.15 if hunt_target is not None else 0.0
        u_cannibal = 1.25 if prey_target is not None else 0.0

        u_shelter = 0.0
        if cfg.sleep_enabled and not c.is_predator and not c.is_herbivore and houses:
            if is_night:
                u_shelter = 1.5
            elif self.weather in ("storm", "rain") or c.chill > 5.0:
                u_shelter = 0.85
            elif c.personality == "cautious" and (c.energy < 40.0 or c.health < 50.0):
                u_shelter = 0.7
            # §AN E.3: the omen was heeded — worshippers drift home early
            if u_shelter < 1.5 and c.prepared_ticks > 0:
                u_shelter += 0.4
            # §AO Phase B: the dusk rush — at first dusk instinct drops every
            # non-essential plan and sprints for home before nightfall.
            if DUSK_TOD <= tod < 0.78 and u_shelter < DUSK_SHELTER_URGE:
                u_shelter = DUSK_SHELTER_URGE
            # §AR S-6: sickness smells like danger — heads for the roof.
            if disease_scent_near:
                u_shelter += 0.2
            # §AR S-6: pentagon+ castes read the sky the instant it turns —
            # they seek cover before the first drop lands.
            if (
                c.sides >= 5
                and self.weather in ("rain", "storm")
                and self.tick - getattr(self, "_weather_since_tick", self.tick) <= WEATHER_ANTICIPATION_TICKS
                and u_shelter < 1.0
            ):
                u_shelter += 0.5
            # §AS L-2: a retreat command overrides every other drive.
            if retreat_heard:
                u_shelter = max(u_shelter, RETREAT_SHELTER_URGE)

        # §AT-4 H-1: a wounded creature seeks herbs even on a full stomach.
        herb_need = (
            isinstance(target, Food)
            and target.variant == "medicinal_herb"
            and c.health < 60.0
        )
        u_eat = 0.0
        if target is not None and (c.is_predator or c.energy <= 0.85 * cfg.energy_max or herb_need):
            energy_deficit = 1.0 - (c.energy / cfg.energy_max) if cfg.energy_max > 0 else 0.5
            u_eat = 0.6 + energy_deficit * 0.8
            if herb_need:
                u_eat += 0.55
            if c.personality == "greedy":
                u_eat += 0.25
            if c.status == "starving":
                u_eat += 0.5
            # §AS L-2: the harvest order — autumn hands work faster.
            if harvest_order:
                farmer_spec = self.clans.get(c.clan_id, {}).get("specialization", {}).get("farmer", 0.33) if c.clan_id else 0.33
                if farmer_spec >= 0.4 or c.skills.get("farming", 0.0) >= 6.0:
                    u_eat += 0.25
            # §AT-4 H-2: despair blunts provision — but raw hunger overrides
            # despair, and the body always mends its spirit a little each tick.
            if c.morale < MORALE_FORAGE_MIN and c.status == "" and not herb_need:
                u_eat = 0.0

        u_signal_food = 0.0
        if signal_food_target is not None and target is None and c.status in ("hungry", "starving"):
            u_signal_food = 0.75

        u_danger_avoid = 0.6 if (danger_avoid_target is not None and flee_target is None) else 0.0

        # §AR S-6: the thermal gradient is a sense — freezing bodies drift
        # toward known heat, cooking bodies toward water; the very young and
        # the very old feel it most.
        u_thermal = 0.0
        thermal_target: tuple[float, float] | None = None
        if not c.indoors and not c.sleeping:
            amb_here = self.ambient_at(c.x, c.y)
            sens = 2.0 if c.stage in ("infant", "elder") else 0.0
            if amb_here < HYPOTHERMIA_TEMP + sens:
                near_heat: tuple[float, float] | None = None
                best_hd2 = 625.0  # 25 units
                for cf in self.campfires:
                    hd2 = w.distance_sq(c.x, c.y, cf["x"], cf["y"])
                    if hd2 < best_hd2:
                        best_hd2, near_heat = hd2, (cf["x"], cf["y"])
                for ffire in self.fires:
                    hd2 = w.distance_sq(c.x, c.y, ffire["x"], ffire["y"])
                    if hd2 < best_hd2:
                        best_hd2, near_heat = hd2, (ffire["x"], ffire["y"])
                for hhh in houses:
                    hh2 = cast(House, hhh)
                    if hh2.hearth_lit:
                        hd2 = w.distance_sq(c.x, c.y, hh2.x, hh2.y)
                        if hd2 < best_hd2:
                            best_hd2, near_heat = hd2, (hh2.x, hh2.y)
                if near_heat is not None and not c.is_predator:
                    thermal_target = near_heat
                    u_thermal = THERMAL_SEEK_UTILITY * (1.0 + sens * 0.25)
            elif c.body_temp > HYPERTHERMIA_TEMP - 2.0 and self.rivers:
                # overheated: make for the nearest riverbank (safe cooling)
                best_rv = min(self.rivers, key=lambda rv: self._river_dy(c.y, rv["cy"]))
                bank_y = best_rv["cy"] - best_rv["hw"] - 1.0 if c.y < best_rv["cy"] else best_rv["cy"] + best_rv["hw"] + 1.0
                if abs(bank_y - c.y) > 1.0:
                    thermal_target = (c.x, bank_y)
                    u_thermal = THERMAL_SEEK_UTILITY

        # Purposeful Waypoint Navigation (§AL)
        waypoint_target = None
        u_waypoint = 0.0
        if not c.is_predator and not c.is_herbivore:
            # §AN C.1: an emissary walks a diplomatic mission above all else
            mission = getattr(c, "mission", None)
            if isinstance(mission, dict) and mission.get("type") == "peace":
                ex_, ey_ = mission.get("x", 0.0), mission.get("y", 0.0)
                if w.distance_sq(c.x, c.y, ex_, ey_) > 4.0:
                    waypoint_target = (ex_, ey_)
                    u_waypoint = 1.1
                elif getattr(c, "waypoints", None) is not None:
                    c.waypoints["rich_food"] = (round(ex_, 2), round(ey_, 2))
            elif getattr(c, "waypoints", None) and isinstance(c.waypoints, dict):
                # §AS L-2: fire and flood — the evacuation overrides all errands.
                if "evacuate" in c.waypoints:
                    ex3, ey3 = c.waypoints["evacuate"]
                    if w.distance_sq(c.x, c.y, ex3, ey3) <= 4.0:
                        del c.waypoints["evacuate"]
                    else:
                        waypoint_target = (ex3, ey3)
                        u_waypoint = 2.0
                # §AR S-5: the rally overrides every errand — first time
                # leaders actually coordinate movement.
                elif "rally" in c.waypoints and c.morale >= MORALE_RALLY_MIN:
                    rx2, ry2 = c.waypoints["rally"]
                    if w.distance_sq(c.x, c.y, rx2, ry2) <= 4.0:
                        del c.waypoints["rally"]  # arrived; banner lowered
                    else:
                        waypoint_target = (rx2, ry2)
                        u_waypoint = 1.0
                elif c.status in ("hungry", "starving") and target is None and "rich_food" in c.waypoints:
                    rx, ry = c.waypoints["rich_food"]
                    if w.distance_sq(c.x, c.y, rx, ry) > 4.0:
                        waypoint_target = (rx, ry)
                        u_waypoint = 0.55
                elif c.personality == "explorer" and target is None and "patrol" in c.waypoints:
                    px, py = c.waypoints["patrol"]
                    if w.distance_sq(c.x, c.y, px, py) > 4.0:
                        waypoint_target = (px, py)
                        u_waypoint = 0.45

        # Task Board scaling (§AL)
        u_eat *= harvester_weight
        u_waypoint *= harvester_weight
        if c.caste == "Soldier":
            u_help *= guard_weight

        # Tactical Formations & Actions

        # §AU O-1: allocation-free argmax — direct scalar comparisons instead
        # of building a list of tuples every creature tick.
        top_util = u_flee
        top_action = "flee"
        if u_alarm > top_util:
            top_util, top_action = u_alarm, "alarm"
        if u_help > top_util:
            top_util, top_action = u_help, "help"
        if u_cannibal > top_util:
            top_util, top_action = u_cannibal, "cannibal"
        if u_hunt > top_util:
            top_util, top_action = u_hunt, "hunt"
        if u_shelter > top_util:
            top_util, top_action = u_shelter, "shelter"
        if u_eat > top_util:
            top_util, top_action = u_eat, "eat"
        if u_signal_food > top_util:
            top_util, top_action = u_signal_food, "signal_food"
        if u_danger_avoid > top_util:
            top_util, top_action = u_danger_avoid, "danger_avoid"
        if u_waypoint > top_util:
            top_util, top_action = u_waypoint, "waypoint"
        if u_thermal > top_util:
            top_util, top_action = u_thermal, "thermal"

        # Waypoints recording for rich food
        if target is not None and isinstance(target, Food) and target.variant in ("berry", "mushroom") and getattr(c, "waypoints", None) is not None:
            c.waypoints["rich_food"] = (round(target.x, 2), round(target.y, 2))

        # Check if creature is inside a house (§L indoor/outdoor navigation)
        inside_house_obj: House | None = None
        if houses and not c.is_predator:
            h_candidates = getattr(self, "_house_grid", {}).get((int(c.x // 50), int(c.y // 50)), houses)
            for h in h_candidates:
                if not h.is_ruin and abs(c.x - h.x) <= 14.0 and abs(c.y - h.y) <= 14.0 and self._is_inside_house(c, h):
                    inside_house_obj = h
                    break

        if inside_house_obj is not None:
            if not roof_resolved:
                assigned_roof = self._house_for(c, houses)
                roof_resolved = True
            home = assigned_roof
            if home is not None and getattr(c, "waypoints", None) is not None:
                c.waypoints["home"] = (round(home.x, 2), round(home.y, 2))

            if home is not None and top_action == "shelter" and inside_house_obj.id == home.id and not is_starving:
                # Intended shelter: stay inside and sleep/rest
                tx, ty = inside_house_obj.x, inside_house_obj.y
                dx, dy = w.delta(tx, ty, c.x, c.y)
                desired = math.atan2(dy, dx)
                diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
            else:
                # All other conditions (foraging, daytime, active tasks, or overflow seeking another house):
                # navigate cleanly through the doorway to avoid getting stuck in walls!
                ex_x, ex_y = self._house_exit_target(c, inside_house_obj)
                dx, dy = w.delta(ex_x, ex_y, c.x, c.y)
                desired = math.atan2(dy, dx)
                diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                c.angle += max(-cfg.steer_turn * 1.5, min(cfg.steer_turn * 1.5, diff))





        else:
            if top_util > 0.3:
                if top_action == "flee" and flee_target is not None:
                    # Kiting & Flanking Maneuver (§AL): Women / lines kite at 90 deg tangent
                    if c.shape == "line" or c.caste == "Woman":
                        dx, dy = w.delta(c.x, c.y, flee_target.x, flee_target.y)
                        base_angle = math.atan2(dy, dx)
                        desired = base_angle + (math.pi / 2 if (c.id % 2 == 0) else -math.pi / 2)
                        diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                        c.angle += max(-cfg.steer_turn * 1.3, min(cfg.steer_turn * 1.3, diff))
                    else:
                        dx, dy = w.delta(c.x, c.y, flee_target.x, flee_target.y)
                        desired = math.atan2(dy, dx)
                        diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                        c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
                elif top_action == "alarm" and signal_alarm_target is not None:
                    # §AR S-1: the alarm encodes the danger's bearing.
                    # world.delta(a, b) = a − b, so delta(c, sg) is the vector
                    # FROM the source TO us — turning along it flees outward.
                    dx, dy = w.delta(c.x, c.y, signal_alarm_target["x"], signal_alarm_target["y"])
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
                elif top_action == "help" and signal_help_target is not None:
                    hx, hy = signal_help_target
                    dx, dy = w.delta(hx, hy, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    # Phalanx Alignment (§AL): Soldiers within 4.0 align angle with allied soldiers
                    if c.caste == "Soldier":
                        for o in w.query_radius(c.x, c.y, 4.0):
                            if isinstance(o, Creature) and o.clan_id == c.clan_id and o.caste == "Soldier" and o.id != c.id:
                                desired = (desired + o.angle) / 2.0
                                break
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
                elif top_action == "cannibal" and prey_target is not None:
                    dx, dy = w.delta(prey_target.x, prey_target.y, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn * 1.1, min(cfg.steer_turn * 1.1, diff))
                elif top_action == "hunt" and hunt_target is not None:
                    dx, dy = w.delta(hunt_target.x, hunt_target.y, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
                elif top_action == "shelter" and houses:
                    if not roof_resolved:
                        assigned_roof = self._house_for(c, houses)
                        roof_resolved = True
                    home = assigned_roof or (houses[0] if houses else None)
                    if home is not None and getattr(c, "waypoints", None) is not None:
                        c.waypoints["home"] = (round(home.x, 2), round(home.y, 2))
                    if home is not None:
                        if self._inside_house(c, home):
                            tx, ty = home.x, home.y
                        else:
                            tx, ty = self._house_entry_target(c, home)
                        dx, dy = w.delta(tx, ty, c.x, c.y)
                        desired = math.atan2(dy, dx)
                        diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                        c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
                elif top_action == "eat" and target is not None:
                    if isinstance(target, Food) and target.variant in ("berry", "mushroom") and getattr(c, "waypoints", None) is not None:
                        c.waypoints["rich_food"] = (round(target.x, 2), round(target.y, 2))
                    dx, dy = w.delta(target.x, target.y, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
                elif top_action == "signal_food" and signal_food_target is not None:
                    fx, fy = signal_food_target
                    dx, dy = w.delta(fx, fy, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
                elif top_action == "danger_avoid" and danger_avoid_target is not None:
                    gx, gy = danger_avoid_target
                    dx, dy = w.delta(c.x, c.y, gx, gy)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn * 0.6, min(cfg.steer_turn * 0.6, diff))
                elif top_action == "waypoint" and waypoint_target is not None:
                    wx, wy = waypoint_target
                    dx, dy = w.delta(wx, wy, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn * 0.8, min(cfg.steer_turn * 0.8, diff))
                elif top_action == "thermal" and thermal_target is not None:
                    tx2, ty2 = thermal_target
                    dx, dy = w.delta(tx2, ty2, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    c.angle += max(-cfg.steer_turn * 0.7, min(cfg.steer_turn * 0.7, diff))
            else:
                # §AN A.2: a woman's peace-hum parts the crowd — polygons
                # drift aside so her corridor stays walkable.
                if signal_hum_source is not None:
                    hx_, hy_ = signal_hum_source
                    dx, dy = w.delta(c.x, c.y, hx_, hy_)  # away from the hum
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    cap = cfg.steer_turn * 0.4
                    c.angle += max(-cap, min(cap, diff))
                # High-trust buddy attraction (§AL): steer towards trusted kin when idle
                buddy_found = False
                if getattr(c, "trust", None) and isinstance(c.trust, dict) and not c.is_predator and not c.is_herbivore:
                    _buddy_iter = [o for o, _ in _batch_list if isinstance(o, Creature)]
                    for o in _buddy_iter:
                        if o.id in c.trust and c.trust[o.id] >= 15.0 and o.id != c.id:
                            dx, dy = w.delta(o.x, o.y, c.x, c.y)
                            desired = math.atan2(dy, dx)
                            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                            c.angle += max(-cfg.steer_turn * 0.4, min(cfg.steer_turn * 0.4, diff))
                            buddy_found = True
                            break
                if not buddy_found:
                    in_rv = self._river_at(c.x, c.y) if self.rivers else None
                    if in_rv is not None and not self._on_bridge_or_dam(c.x, c.y):
                        # steer out of the water to the nearest dry bank
                        bank_y = in_rv["cy"] - in_rv["hw"] - 1.5 if c.y < in_rv["cy"] else in_rv["cy"] + in_rv["hw"] + 1.5
                        dx, dy = w.delta(c.x, bank_y, c.x, c.y)
                        escape_ang = math.atan2(dy, dx)
                        diff = (escape_ang - c.angle + math.pi) % (2 * math.pi) - math.pi
                        c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
                    else:
                        wander = cfg.wander_turn
                        if self.weather == "storm":
                            wander += cfg.storm_wander_bonus
                        c.angle += self.rng.uniform(-wander, wander)

            # 2b. Social yielding: the lowly give way to their betters.
            my_rank = YIELD_RANK.get(c.caste, 0)
            if my_rank < 6:
                _yield_iter = ((o, d2) for o, d2 in _batch_list if d2 <= YIELD_RADIUS * YIELD_RADIUS)
                for o, _ in _yield_iter:
                    if o is c or o.kind != "creature":
                        continue
                    if YIELD_RANK.get(o.caste, 0) > my_rank:  # type: ignore[union-attr]
                        dx, dy = w.delta(c.x, c.y, o.x, o.y)
                        away = math.atan2(dy, dx)
                        diff = (away - c.angle + math.pi) % (2 * math.pi) - math.pi
                        cap = cfg.steer_turn * 0.6
                        c.angle += max(-cap, min(cap, diff))
                        break

            # 2c. Flock instincts: keep your distance, and hold formation with kin.
            if cfg.cohesion_weight or cfg.alignment_weight or cfg.separation_weight:
                fx = fy = 0.0
                _flock_iter = [o for o, _ in _batch_list if isinstance(o, Creature)]
                for o in _flock_iter:
                    if o.id == c.id:
                        continue
                    dxo, dyo = w.delta(o.x, o.y, c.x, c.y)
                    d = math.hypot(dxo, dyo) or 1e-6
                    if d < 1.5:
                        fx -= (dxo / d) * cfg.separation_weight
                        fy -= (dyo / d) * cfg.separation_weight
                    else:
                        # cohesion only with kin; alignment with any nearby flock-mate
                        if o.clan_id and o.clan_id == c.clan_id:
                            fx += (dxo / d) * cfg.cohesion_weight
                            fy += (dyo / d) * cfg.cohesion_weight
                        fx += math.cos(o.angle) * cfg.alignment_weight
                        fy += math.sin(o.angle) * cfg.alignment_weight
                if fx or fy:
                    desired = math.atan2(fy, fx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    cap = cfg.steer_turn * 0.5
                    c.angle += max(-cap, min(cap, diff))

            # 2d. Territory preference — members drift toward own settlement when outside radius (§P)
            if cfg.territory_enabled and c.clan_id and not c.is_predator and not c.is_herbivore:
                own_house = clan_house_map.get(c.clan_id)
                if own_house is not None:
                    d2 = w.distance_sq(c.x, c.y, own_house.x, own_house.y)
                    if d2 > cfg.territory_radius * cfg.territory_radius:
                        dx, dy = w.delta(own_house.x, own_house.y, c.x, c.y)
                        desired = math.atan2(dy, dx)
                        diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                        cap = cfg.steer_turn * 0.35
                        c.angle += max(-cap, min(cap, diff))


        # 3. Move (hunger speeds up the desperate; rain slows every body;
        # §AT-4 H-0: wounds and sickness slow it further; §AT-4 H-1: fresh
        # wounds hobble worse the graver they are).
        speed_mult *= self._health_speed_mult(c.health)
        if c.wound_ticks > 0 and c.wound_severity:
            speed_mult *= WOUND_SPEED_MULT.get(c.wound_severity, 1.0)
        # §AT-4 H-2: old scars shorten the stride forever.
        if c.scars:
            speed_mult *= SCAR_SPEED_MULT ** c.scars
        # §AO Phase A: frostbite numbness — deep-chilled limbs crawl.
        if cfg.weather_sickness_enabled and c.chill >= cfg.chill_threshold:
            speed_mult *= FROSTBITE_SPEED_MULT
        # §AR S-7: grieving kin stand still for a few ticks.
        if c.pause_ticks > 0:
            c.pause_ticks -= 1
            speed_mult = 0.0
        # §AQ PH-4: roads carry the stride; the grade ahead slows the climb
        stride_mult = 1.0
        # §AQ PH-10: hidden zones bend the body — heavy ground drags, and a
        # law-change shimmer front passing through turns the head
        front_x = self._law_wave_front()
        if front_x is not None:
            dxw = abs(c.x - front_x)
            dxw = min(dxw, self.config.width - dxw)
            if dxw <= LAW_WAVE_BAND:
                c.angle += self.rng.uniform(-0.35, 0.35)
        if self.anomalies and self._anomaly_at(c.x, c.y, "heavy"):
            stride_mult *= ANOMALY_HEAVY_SPEED
        if c.heat_stroke_ticks >= HEAT_STROKE_TICKS:
            # §AQ PH-7: heat prostration — the body refuses to move; it cools
            # where it fell, and dies there if shade never comes.
            stride_mult = 0.0
            if not c.emote or c.emote == "hungry":
                c.emote = "sleep"
                c.emote_ticks = 10
        elif cfg.relief_enabled:
            stride_mult *= self._road_speed_mult(c.x, c.y)
            here_h = self._elev_units(c.x, c.y)
            ahead_x = c.x + math.cos(c.angle) * 2.0
            ahead_y = c.y + math.sin(c.angle) * 2.0
            rise = self._elev_units(ahead_x, ahead_y) - here_h
            stride_mult *= max(0.55, 1.0 - SLOPE_SPEED_MULT * max(0.0, rise) / (2.0 * ELEV_MAX_HEIGHT))
        # §AO Phase B: night chase — a predator runs its unsheltered prey down
        # 20% faster in the dark (stealth of the hunter, blindness of the hunted).
        if c.is_predator and is_night and hunt_target is not None and not hunt_target.indoors:
            speed_mult *= PREDATOR_NIGHT_SPEED
        step_len = c.speed * speed_mult * stage_speed * env_speed * stride_mult
        px, py = c.x, c.y
        nx = c.x + math.cos(c.angle) * step_len
        ny = c.y + math.sin(c.angle) * step_len
        if cfg.boundary == "clamp":
            hit_x = nx <= 0 or nx >= cfg.width
            hit_y = ny <= 0 or ny >= cfg.height
            if hit_x:
                c.angle = math.pi - c.angle
            if hit_y:
                c.angle = -c.angle
        c.x, c.y = w.normalize(nx, ny)

        # §AQ PH-4: grades tax the climb, cliffs hurt, feet pack roads.
        if cfg.relief_enabled:
            self._terrain_effects(c, px, py)
        # §AQ PH-3: rivers — fording costs energy and speed, bridges cross dry,
        # the current sweeps the weak downstream, floods drown the stubborn.
        if self.rivers:
            self._river_effects(c)

        # 4. House walls block movement except through the doorway.
        # The doorway is too small for the Carnivore caste (§L refuge) — predators see a closed wall.
        mdx, mdy = w.delta(c.x, c.y, px, py)
        was_blocked = False
        if houses and mdx * mdx + mdy * mdy <= step_len * step_len * 2.25:  # skip wrap teleports
            near_houses = [h for h in getattr(self, "_house_grid", {}).get((int(px // 50), int(py // 50)), houses) if abs(px - h.x) <= 14.0 and abs(py - h.y) <= 14.0]
            for h in near_houses:
                crosses = (
                    _path_crosses_wall(px, py, px + mdx, py + mdy, h, predator_blocked=c.is_predator)
                    if c.is_predator
                    else _path_crosses_wall(px, py, px + mdx, py + mdy, h)
                )
                if crosses:
                    was_blocked = True
                    c.x, c.y = w.normalize(px, py)
                    c.blocked_ticks += 1
                    if c.blocked_ticks >= 3:
                        in_h = next((h for h in near_houses if self._is_inside_house(c, cast(House, h))), None)
                        if in_h is not None and not c.is_predator:
                            ex_x, ex_y = self._house_exit_target(c, in_h)
                            dx, dy = w.delta(ex_x, ex_y, c.x, c.y)
                            c.angle = math.atan2(dy, dx)
                        else:
                            c.angle = self.rng.uniform(0, 2 * math.pi)
                    else:
                        c.angle += math.pi + self.rng.uniform(-0.4, 0.4)
                    if target is not None and cfg.food_giveup_ticks > 0:
                        self._give_up_on(c, target)  # meal sits behind a wall
                    break
        if not was_blocked:
            c.blocked_ticks = 0
        # Predator refuge safety net: even if a predator spawns inside a house, push it out
        if c.is_predator and houses:
            for h in self._house_grid.get((int(c.x // 50), int(c.y // 50)), []):
                if not h.is_ruin and self._inside_house(c, h):
                    # push to doorway, then one step outside
                    dx, dy = self._door_pos(h)
                    # move predator just outside the door
                    if h.door_side == "north":
                        c.x, c.y = w.normalize(dx, h.y - h.size / 2 - c.radius - 0.2)
                    elif h.door_side == "south":
                        c.x, c.y = w.normalize(dx, h.y + h.size / 2 + c.radius + 0.2)
                    elif h.door_side == "west":
                        c.x, c.y = w.normalize(h.x - h.size / 2 - c.radius - 0.2, dy)
                    else:
                        c.x, c.y = w.normalize(h.x + h.size / 2 + c.radius + 0.2, dy)
                    c.angle += math.pi
                    break

        # 4b. Rocks are solid: push out and face away. A meal whose straight path
        # crosses the stone or sits inside is abandoned — give up, warn others, and steer away.
        if self.rocks:
            hit_rock = self._resolve_rock_collision(c)
            if hit_rock is not None and target is not None and cfg.food_giveup_ticks > 0:
                if self._segment_hits_circle(c.x, c.y, target.x, target.y, hit_rock, pad=c.radius):
                    self._give_up_on(c, target)

        # §AO Phase D: blind collisions in pitch darkness — a stumbling
        # polygon meets an unsheltered moving line and the line cuts deep.
        if (
            is_night
            and not c.indoors
            and c.shape != "line"
            and not c.is_predator
            and not c.is_herbivore
            and not c.sleeping
            and self.rng.random() < IMPALE_CHANCE
        ):
            for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, c.radius + 1.0):
                if (
                    isinstance(o, Creature)
                    and o.shape == "line"
                    and o.id != c.id
                    and o.id in w.entities
                    and not o.indoors
                    and not o.sleeping
                    and d2 <= (c.radius + o.radius) ** 2
                ):
                    c.health -= IMPALE_DAMAGE
                    c.emote = "panic"
                    c.emote_ticks = 12
                    if c.health <= 0:
                        self._kill(c, "impalement")
                        return
                    break

        # 4c. §AC Desperation fulfilled: prey within reach is killed and eaten.
        if (
            prey_target is not None
            and prey_target.id in w.entities
            and c.id in w.entities
            and w.distance_sq(c.x, c.y, prey_target.x, prey_target.y) <= cfg.eat_radius * cfg.eat_radius
        ):
            self._do_cannibalism(c, prey_target)
            if c.id not in w.entities:  # a kin-eater may have been exiled (still alive)
                return

        # 4c-bis. §AO Phase D: rogue isosceles marauders — a clanless or
        # starving triangle stalks the dark to ambush a lone forager and
        # loot its carried rations.
        if (
            is_night
            and not c.indoors
            and not c.sleeping
            and c.sides == 3
            and (c.clan_id == 0 or is_starving)
            and self.rng.random() < MARAUDER_CHANCE
        ):
            for o, d2 in w.query_radius_with_dist_sq(c.x, c.y, MARAUDER_AMBUSH_RADIUS):
                if (
                    not isinstance(o, Creature)
                    or o.id == c.id
                    or o.id not in w.entities
                    or o.is_predator
                    or o.is_herbivore
                    or o.indoors
                    or (o.clan_id and o.clan_id == c.clan_id)
                ):
                    continue
                # lone means alone: no kin of the victim within earshot
                lone = True
                for p, pd2 in w.query_radius_with_dist_sq(o.x, o.y, MARAUDER_AMBUSH_RADIUS):
                    if (
                        isinstance(p, Creature)
                        and p.id != o.id
                        and p.id != c.id
                        and p.clan_id == o.clan_id
                        and pd2 <= MARAUDER_AMBUSH_RADIUS * MARAUDER_AMBUSH_RADIUS
                    ):
                        lone = False
                        break
                if not lone:
                    continue
                loot = getattr(o, "food_basket", 0)
                if loot > 0:
                    o.food_basket = 0
                    room = max(0, 3 - c.food_basket)
                    kept = min(loot, room)
                    c.food_basket += kept
                    c.energy = min(cfg.energy_max, c.energy + (loot - kept) * cfg.energy_from_food * 0.5)
                c.emote = "combat"
                c.emote_ticks = 15
                o.emote = "panic"
                o.emote_ticks = 15
                break

        # 5. Eat or Harvest into basket / reserve. Full creatures (>85% energy) do not consume food.
        can_eat = target is not None and best_sq <= cfg.eat_radius * cfg.eat_radius and (
            c.is_predator or c.energy <= 0.85 * cfg.energy_max
            or (isinstance(target, Food) and target.variant == "medicinal_herb" and c.health < 60.0)
        )
        if can_eat and target is not None:
            w.remove(target.id)
            self._eaten.add(target.id)
            c.ticks_since_meal = 0
            c.meals += 1
            c.give_ups.clear()  # fed: old grudges against unreachable food fade
            self._eaters_this_tick.append(c.id)
            # §AT-4 H-2: a meal lifts the spirit.
            c.morale = min(100.0, c.morale + MORALE_EAT_RESTORE)
            gain = cfg.energy_from_food
            health_delta = 0.0
            if isinstance(target, Food):
                if cfg.plant_variants_enabled:
                    base = VARIANT_ENERGY.get(target.variant, cfg.energy_from_food)
                    gain = base * target.growth  # immature plants feed proportionally less
                    health_delta = VARIANT_HEALTH.get(target.variant, 0.0)
                else:
                    gain = cfg.energy_from_food * target.growth
                # §AM B: the sown harvest feeds far better than wild weeds
                if target.cultivated:
                    gain *= CULTIVATED_YIELD_MULT
                # Totem harvest (§P); farmer specialization adds harvest (§P specialization)
                farmer = self.clans.get(c.clan_id, {}).get("specialization", {}).get("farmer", 0.33) if c.clan_id else 0.0
                h = self._totem_stat(c, "harvest")
                if h:
                    gain *= 1.0 + h
                    health_delta += 2.0 * h  # Tree 0.25 → +0.5, as ever
                if farmer:
                    gain *= (1.0 + farmer * 0.25)
            elif isinstance(target, Corpse):
                gain = cfg.corpse_energy  # scavenged remains
                scav = self.clans.get(c.clan_id, {}).get("specialization", {}).get("scavenger", 0.33) if c.clan_id else 0.0
                h = self._totem_stat(c, "harvest")
                if h:
                    gain *= 1.0 + 0.4 * h
                if scav:
                    gain *= (1.0 + scav * 0.35)
            # §AS L-0: a leaderless clan gathers less — no one organises the hunt.
            if leaderless:
                gain *= LEADERLESS_GAIN_MULT
            # §AT-4 H-1: weak hands harvest less — decline feeds on itself.
            gain *= self._forage_mult(c.health)

            # Store in food basket / reserve when well-fed, else eat
            if isinstance(target, Food) and c.energy > 0.60 * cfg.energy_max and c.food_basket < 3:
                c.food_basket += 1
                c.skills["farming"] = c.skills.get("farming", 0.0) + 0.8
                c.emote = "craft"
                c.emote_ticks = 15
            else:
                c.energy = min(cfg.energy_max, c.energy + gain)
                if isinstance(target, Food):
                    c.skills["farming"] = c.skills.get("farming", 0.0) + 0.4
                    # §AT-4 H-1: rich food keeps mending the body for a while.
                    bonus = FOOD_HEAL_BONUS.get(target.variant)
                    if bonus:
                        c.heal_bonus_amount, c.heal_bonus_ticks = bonus
                    # Functional Dietary Effects (§AM)
                    if target.variant == "medicinal_herb":
                        c.infected = False
                        c.disease_id = 0
                        # §AP: the Sacred Spiral doubles herbal potency
                        c.health = min(c.max_health, c.health + 20.0 * (1.0 + self._totem_stat(c, "medicine")))
                        c.emote = "heal"
                        c.emote_ticks = 20
                    elif target.variant in ("sun_berry", "berry"):
                        c.speed = min(1.2, c.speed * 1.15)
                        c.emote = "cheer"
                        c.emote_ticks = 15
                    elif target.variant == "grain":
                        c.emote = "craft"
                        c.emote_ticks = 15
                    elif target.variant == "poisonous":
                        c.emote = "fear"
                        c.emote_ticks = 20
                elif isinstance(target, Corpse):
                    c.skills["foraging"] = c.skills.get("foraging", 0.0) + 0.6

            # §AM B: skilled hands glean seed from a wild mature harvest
            if (
                cfg.agriculture_enabled
                and isinstance(target, Food)
                and not target.cultivated
                and target.growth >= 1.0
                and c.seeds < 3
                and c.skills.get("farming", 0.0) >= SEED_SKILL_MIN
            ):
                c.seeds += 1

            # §AM C: the granary — sated harvesters lay grain & cured berries by
            # against winter; the store is dry, roofed and safe from beasts.
            if (
                cfg.granaries_enabled
                and c.clan_id
                and c.clan_id in self.clans
                and isinstance(target, Food)
                and target.variant in ("grain", "berry")
                and c.energy > 0.6 * cfg.energy_max
            ):
                clan_store = self.clans[c.clan_id]
                room = max(0.0, cfg.granary_capacity - float(clan_store.get("granary", 0.0)))
                put = min(gain * GRANARY_DEPOSIT_SHARE, room)
                if put > 0:
                    clan_store["granary"] = float(clan_store.get("granary", 0.0)) + put
                    clan_store["harvest_total"] = float(clan_store.get("harvest_total", 0.0)) + put

            if health_delta != 0:
                c.health = max(0.0, min(c.max_health, c.health + health_delta))
                if c.health <= 0:
                    self._kill(c, "poison")
                    return


        # 5b. Rain and storms send the roofless under cover — beds permitting.
        # Predators cannot shelter: the doorway is too small (§L refuge). Wild grazers don't seek roofs.
        if (
            cfg.shelter_enabled
            and not c.is_predator
            and not c.is_herbivore
            and not c.indoors
            and houses
            and not self._is_night(tod)
            and self.weather in ("rain", "storm")
        ):
            if not roof_resolved:
                assigned_roof = self._house_for(c, houses)
                roof_resolved = True
            home = assigned_roof or inside_house_obj or (houses[0] if houses else None)
            if (
                home is not None
                and self._inside_house(c, home)
                and self._claim_bed(home)
            ):
                c.indoors = True
                if cfg.knowledge_enabled:
                    self._learn(c, "safe", home.x, home.y)  # §X: shelter from the rain

        # 6. Metabolism, sickness and mortality. §R chill builds when cold & wet
        stage_mult = STAGE_ENERGY_MULT.get(c.stage, 1.0) if c.generation > 0 else 1.0
        decay_mult = stage_mult * self._metabolic_cost(c)  # §AQ PH-0 upkeep
        # §AQ PH-10: the air itself differs inside anomaly zones
        if self.anomalies:
            if self._anomaly_at(c.x, c.y, "calm"):
                decay_mult *= ANOMALY_CALM_DECAY
            elif self._anomaly_at(c.x, c.y, "heavy"):
                decay_mult *= 1.1
        # §AS L-0: the leader's aura eases every stride; an interregnum wearies.
        if c.clan_id:
            if in_aura:
                decay_mult *= LEADER_DECAY_MULT
            elif leaderless:
                decay_mult *= LEADERLESS_DECAY_MULT
        c.energy -= cfg.energy_decay_per_tick * decay_mult
        # §AT-4 H-2: morale — the second health axis. Starvation erodes the
        # will; the leader's aura, festivals and simple resilience mend it.
        if is_starving:
            c.morale = max(0.0, c.morale - MORALE_STARVE_DRAIN)
        else:
            c.morale = min(100.0, c.morale + MORALE_BASE_RECOVER)
        if c.clan_id:
            if in_aura:
                c.morale = min(100.0, c.morale + MORALE_AURA_RECOVER)
            ci_m = self.clans.get(c.clan_id)
            if ci_m and self.tick < int(ci_m.get("feast_until", 0)):
                c.morale = min(100.0, c.morale + MORALE_FEAST_RECOVER)
        # §AT-4 H-1 damage variety: chronic hunger, old age, lingering wounds.
        metabolism_ratio = c.energy / cfg.energy_max if cfg.energy_max > 0 else 1.0
        if metabolism_ratio < EXHAUSTION_ENERGY_FRACTION:
            c.low_energy_ticks += 1
        else:
            c.low_energy_ticks = 0
        if c.low_energy_ticks > EXHAUSTION_TICKS:
            c.health -= EXHAUSTION_DRAIN
            if c.health <= 0:
                self._kill(c, "exhaustion")
                return
        if c.stage == "elder":
            c.health -= ELDER_DECAY_RATE
            if c.health <= 0:
                self._kill(c, "old_age")
                return
        if c.heal_bonus_ticks > 0:
            c.heal_bonus_ticks -= 1
        if c.wound_ticks > 0:
            # §AT-4 H-2: an untreated wound left open long enough festers —
            # "a wounded soldier alone is a dead soldier".
            if (
                cfg.disease_enabled
                and not c.infected
                and c.wound_severity >= 1
                and c.wound_ticks > WOUND_INFECTION_AFTER
                and self.rng.random() < WOUND_INFECTION_CHANCE
            ):
                self._infect(c)
            c.wound_ticks -= 1
            if c.wound_ticks <= 0:
                # §AT-4 H-2: surviving a grievous wound may leave a permanent scar.
                if c.wound_severity >= 2 and self.rng.random() < SCAR_CHANCE:
                    c.scars += 1
                c.wound_severity = 0
                c.wound_dressed = False
        # §AQ PH-1: the body drifts toward the world's heat; houses insulate
        # against both extremes. Extreme cold feeds §R chill, extreme heat cooks.
        amb = self.ambient_at(c.x, c.y)
        if inside_house_obj is not None:
            amb = self.indoor_ambient(inside_house_obj)
        c.body_temp += (amb - c.body_temp) * BODY_TEMP_DRIFT
        if c.body_temp > HYPERTHERMIA_TEMP:
            # §AQ PH-1: too hot is always lethal physics — no law gates it.
            excess = c.body_temp - HYPERTHERMIA_TEMP
            c.health -= HYPERTHERMIA_DRAIN * excess
            # §AQ PH-7: sustained cooking collapses the body — heat stroke
            c.heat_stroke_ticks += 1
            if c.health <= 0:
                self._kill(c, "hyperthermia")
                return
        elif c.body_temp < HYPERTHERMIA_TEMP - HEAT_STROKE_HYST:
            c.heat_stroke_ticks = 0
        if cfg.weather_sickness_enabled and c.body_temp < HYPOTHERMIA_TEMP:
            cold_resist = 1.0 - self._totem_stat(c, "cold")  # §AP Monolith cold immunity
            c.chill = min(cfg.chill_threshold * 2, c.chill + CHILL_FROM_COLD_RATE * cold_resist)
        if (
            cfg.shelter_enabled
            and not c.indoors
            and (self._is_night(tod) or self.weather in ("rain", "storm"))
        ):
            c.energy -= cfg.exposure_drain
        # §AT-4 H-2: overcrowded houses breed misery — every body beyond the
        # bed count grinds health down a little more.
        if (
            inside_house_obj is not None
            and not c.sleeping
            and getattr(self, "_house_bodies", None)
        ):
            over = self._house_bodies.get(inside_house_obj.id, 0) - self._house_beds(inside_house_obj)
            if over > 0:
                c.health -= OVERCROWD_DRAIN * over
                if c.health <= 0:
                    self._kill(c, "overcrowding")
                    return
        # §R Chill — Ice age chills deeper (§S); §AO the night chills three
        # times faster than daytime rain, and frostbite numbs the body past
        # the sickness threshold.
        if cfg.weather_sickness_enabled:
            is_wet = self.weather in ("rain", "storm")
            is_winter_night = self._season() == "winter" and self._is_night(tod)
            age = self._age()
            chill_mult = 1.4 if age == "Ice" else 1.0
            # §AO Phase A: night chill bites 3× deeper than daytime rain.
            if not c.indoors and is_night:
                chill_mult *= NIGHT_CHILL_MULT
            if not c.indoors and (is_wet or is_winter_night):
                # §AP: the Indomitable Monolith resists the cold's bite
                chill_mult *= 1.0 - self._totem_stat(c, "cold")
                c.chill = min(cfg.chill_threshold * 2, c.chill + cfg.chill_rate * chill_mult)
            else:
                shed = cfg.chill_rate * (2.5 if c.indoors else 1.0) * (0.8 if age == "Ice" else 1.0)
                c.chill = max(0.0, c.chill - shed)
            if c.chill >= cfg.chill_threshold:
                c.health -= cfg.chill_drain * (1.2 if age == "Ice" else 1.0)
                if c.health <= 0:
                    self._kill(c, "chill")
                    return
                # §AO Phase A: frostbite numbness — carried food/seed pouches
                # are dropped by numb hands, and the body keeps dying.
                if getattr(c, "food_basket", 0) > 0:
                    c.food_basket = 0
                    c.emote = "panic"
                    c.emote_ticks = 12
                c.health -= FROSTBITE_DRAIN
                if c.health <= 0:
                    self._kill(c, "exposure")
                    return
            # §AO: winter nights and night storms drain the exposed body fast.
            if (
                not c.indoors
                and is_night
                and (is_winter_night or self.weather == "storm")
            ):
                c.energy -= EXTREME_NIGHT_EXPOSURE
        else:
            c.chill = max(0.0, c.chill - 0.05)
        if cfg.disease_enabled and c.infected:
            c.energy -= cfg.disease_energy_drain
            c.health -= 2.0 * cfg.disease_lethality
            if c.health <= 0:
                self._kill(c, "disease")
                return
        else:
            # §AT-4 H-0: regen requires an energy surplus; below the self-drain
            # floor a starving body consumes itself — starvation now threatens
            # health as well as energy.
            ratio_now = c.energy / cfg.energy_max if cfg.energy_max > 0 else 1.0
            if ratio_now <= HEALTH_SELF_DRAIN_ENERGY:
                c.health -= HEALTH_SELF_DRAIN_RATE
                if c.health <= 0:
                    self._kill(c, "starvation")
                    return
            elif ratio_now > HEALTH_REGEN_MIN_ENERGY and c.health < c.max_health:
                regen = 0.1 * (1.0 + self._totem_stat(c, "defense"))
                # §AT-4 H-1: shelter heals faster than the open plain; wounds
                # slow mending; rich food keeps working after the meal.
                regen *= REGEN_INDOOR_MULT if c.indoors else REGEN_OUTDOOR_MULT
                if c.wound_ticks > 0 and c.wound_severity:
                    regen /= WOUND_REGEN_DIV.get(c.wound_severity, 2.0)
                if c.heal_bonus_ticks > 0:
                    regen += c.heal_bonus_amount
                healed = min(c.max_health, c.health + regen) - c.health
                if healed > 0:
                    c.health += healed
                    c.energy = max(0.0, c.energy - healed * HEALING_ENERGY_COST)  # §AQ PH-0: mending costs
        # §AT-4 H-2: total despair — a broken creature abandons its clan and
        # walks to the nearest other banner, or wanders off clanless.
        if (
            c.morale < MORALE_ABANDON
            and c.clan_id
            and not c.is_predator
            and not c.is_herbivore
            and self.rng.random() < MORALE_ABANDON_CHANCE
        ):
            best_cid, best_d2 = None, math.inf
            for other_cid, members in self._clan_members.items():
                if other_cid == c.clan_id or not other_cid or not members:
                    continue
                info = self.clans.get(other_cid)
                if not info:
                    continue
                mh = self.world.entities.get(info.get("main_house_id")) if info.get("main_house_id") is not None else None
                tx, ty = (mh.x, mh.y) if isinstance(mh, House) else (members[0].x, members[0].y)
                d2c = w.distance_sq(c.x, c.y, tx, ty)
                if d2c < best_d2:
                    best_cid, best_d2 = other_cid, d2c
            old_cid = c.clan_id
            c.clan_id = best_cid or 0
            c.morale = 35.0  # a fresh start lifts the heart a little
            self._emit(
                HistoryEvent(
                    type="defection",
                    tick=self.tick + 1,
                    entity_id=c.id,
                    caste=c.caste,
                    x=round(c.x, 2),
                    y=round(c.y, 2),
                    payload={"from": old_cid, "to": c.clan_id,
                             "reason": "despair",
                             "personal_name": personal_name_for(c.id, self.config.seed, c.generation)},
                )
            )
        if c.energy <= 0:
            if getattr(c, "food_basket", 0) > 0:
                c.food_basket -= 1
                c.energy = min(cfg.energy_max, c.energy + cfg.energy_from_food * 0.9)
                c.ticks_since_meal = 0
                c.meals += 1
                c.give_ups.clear()
                c.emote = "craft"
                c.emote_ticks = 15
            else:
                self._kill(c, "starvation")
                return
        if c.age >= c.lifespan:
            self._kill(c, "old_age")


    def _enforce_food_law(self) -> None:
        """God's bounty or famine, bent by the season and age: winter starves the land."""
        season = self._season()
        target = round(self.config.food_count * _season_food_mult(season, self.config.winter_food_mult))
        age = self._age()
        if age is not None:
            target = round(target * AGE_FOOD_MULT.get(age, 1.0))
        foods = [e for e in self.world.entities.values() if e.kind == "food" and not getattr(e, "cultivated", False)]
        # Ensure no wild plants exist inside any shelter structure
        inside_shelter_ids = [
            f.id for f in foods if self._is_point_inside_any_house(f.x, f.y, pad=0.2)
        ]
        for f_id in inside_shelter_ids:
            self.world.remove(f_id)
        if inside_shelter_ids:
            foods = [f for f in foods if f.id not in inside_shelter_ids]
        deficit = target - len(foods)
        if deficit > 0:
            growth_init = 1.0
            if age == "Ice":
                growth_init = 0.25
            elif age == "Plague":
                growth_init = 0.45
            elif season == "winter":
                growth_init = 0.4
            for _ in range(deficit):
                x, y = self._food_pos()
                self.world.add(self._new_food(x, y, growth=growth_init))
        elif deficit < 0:
            # Winter die-back takes the youngest shoots first.
            ordered = sorted(foods, key=lambda f: f.growth)
            for victim in ordered[:-deficit]:
                self.world.remove(victim.id)

    # ------------------------------------------------------------------ output
    def _cached_identity(self, entity_id: int, generation: int) -> tuple[str, str, float, float, float]:
        """AA: name/glyph/jitter computed once per creature — never per frame."""
        key = (entity_id, generation)
        hit = self._identity_cache.get(key)
        if hit is None:
            seed = self.config.seed
            v = variation_for(entity_id, seed)
            hit = (
                personal_name_for(entity_id, seed, generation),
                glyph_for(entity_id, seed, generation),
                v["hue_shift"],
                v["scale_jitter"],
                v["angle_jitter"],
            )
            self._identity_cache[key] = hit
        return hit

    def _entity_sig(self, e: Entity) -> tuple:
        """Compact signature for delta change detection."""
        if isinstance(e, Creature):
            return (
                0,
                round(e.x, 1),
                round(e.y, 1),
                round(e.angle, 1),
                round(e.energy),
                e.status,
                round(e.health),
                e.stage,
                e.sleeping,
                e.infected,
                e.indoors,
                getattr(e, "emote", None),
                getattr(e, "equipped_item", None),
                getattr(e, "food_basket", 0),
                getattr(e, "title", None),
                self._is_torpid(e),
            )
        if isinstance(e, Food):
            is_withering = False
            if (
                self.config.food_decay_enabled
                and e.growth >= 1.0
                and e.mature_ticks
                >= WILT_FRACTION
                * max(1, round(self.config.food_lifespan_ticks * FOOD_LIFESPAN_MULT.get(e.variant, 1.0)))
            ):
                is_withering = True
            return (1, round(e.x, 1), round(e.y, 1), round(e.growth, 1), is_withering)
        if isinstance(e, House):
            return (2, round(e.x, 1), round(e.y, 1), e.clan_id, bool(getattr(e, "is_ruin", False)),
                    e.hearth_lit, int(max(0.0, min(1.0, e.hp / 480.0)) * 20) if e.hp >= 0 else -1, e.rubble > 0)
        if isinstance(e, Corpse):
            return (3, round(e.x, 1), round(e.y, 1), e.ttl // 30)
        return (4, round(e.x, 1), round(e.y, 1))

    def _entity_delta_payload(self, e: Entity) -> dict:
        """Compact payload containing only dynamic attributes for existing entities."""
        if isinstance(e, Creature):
            d: dict[str, Any] = {
                "id": e.id,
                "kind": e.kind,
                "torpid": self._is_torpid(e) or None,
                "x": round(e.x, 2),
                "y": round(e.y, 2),
                "angle": round(e.angle, 3),
                "energy": round(e.energy, 1),
                "status": e.status,
                "health": round(e.health, 1),
                "age": e.age,
                "stage": e.stage,
                "sleeping": e.sleeping,
                "indoors": e.indoors,
                "chill": round(e.chill, 2),
            }
            if e.infected:
                d["infected"] = True
            emote = getattr(e, "emote", None)
            if emote is not None:
                d["emote"] = emote
            item = getattr(e, "equipped_item", None)
            if item is not None:
                d["equipped_item"] = item
            basket = getattr(e, "food_basket", 0)
            if basket:
                d["food_basket"] = basket
            title = getattr(e, "title", None)
            if title is not None:
                d["title"] = title
            return d
        if isinstance(e, Food):
            is_withering = False
            if (
                self.config.food_decay_enabled
                and e.growth >= 1.0
                and e.mature_ticks
                >= WILT_FRACTION
                * max(1, round(self.config.food_lifespan_ticks * FOOD_LIFESPAN_MULT.get(e.variant, 1.0)))
            ):
                is_withering = True
            d = {
                "id": e.id,
                "kind": e.kind,
                "x": round(e.x, 2),
                "y": round(e.y, 2),
                "growth": round(e.growth, 2),
            }
            if is_withering:
                d["withering"] = True
            return d
        if isinstance(e, House):
            return {
                "id": e.id,
                "kind": e.kind,
                "clan_id": e.clan_id or None,
                "clan_color": e.clan_color,
                "is_main": bool(e.clan_id and self.clans.get(e.clan_id, {}).get("main_house_id") == e.id),
                "takeover_age": (self.tick - e.takeover_tick) if getattr(e, "takeover_tick", -1) >= 0 else None,
                "is_ruin": e.is_ruin or None,
                # §AQ PH-1: the hearth's state rides the delta so the flame
                # lights and gutters without a keyframe
                "hearth_lit": e.hearth_lit or None,
                # §AQ PH-6: integrity & rubble ride when they matter
                "hp_frac": (
                    round(max(0.0, e.hp) / MATERIAL_STATS.get(e.material, MATERIAL_STATS["wood"])["durability"], 2)
                    if e.hp >= 0 and e.hp < MATERIAL_STATS.get(e.material, MATERIAL_STATS["wood"])["durability"] * 0.98
                    else (None if not e.is_ruin else 0.0)
                ),
                "rubble": bool(e.rubble > 0) or None,
            }
        return {
            "id": e.id,
            "kind": e.kind,
            "x": round(e.x, 2),
            "y": round(e.y, 2),
            "angle": round(e.angle, 3),
        }

    def snapshot_payload(self) -> dict:
        """AA: the broadcast payload as plain dicts — no pydantic validation
        and no model_dump on the hot path. Shared nested structures are copied,
        so the payload stays valid while the world keeps ticking."""
        cfg = self.config
        entities: list[dict] = []
        population: dict[str, int] = {}
        alive = 0
        infected = 0
        clans = self.clans
        new_state: dict[int, tuple] = {}
        for e in self.world.entities.values():
            entities.append(self._entity_payload(e, clans))
            new_state[e.id] = self._entity_sig(e)
            if isinstance(e, Creature):
                label = e.caste
                alive += 1
                if e.infected:
                    infected += 1
            else:
                label = e.kind.capitalize()
            population[label] = population.get(label, 0) + 1

        self._last_broadcast_state = new_state
        self._last_broadcast_entities = set(new_state.keys())
        self._last_broadcast_clans = {
            str(cid): _clan_sig(info)
            for cid, info in self.clans.items()
        }


        return {
            "type": "state",
            "tick": self.tick,
            "seed": cfg.seed,
            "width": cfg.width,
            "height": cfg.height,
            "boundary": cfg.boundary,
            "population": population,
            "entities": entities,
            "creatures_alive": alive,
            "creatures_dead": self.deaths,
            "dead_by_cause": dict(self._death_counts),
            "infected_count": infected,
            "time_of_day": round(self._time_of_day(), 3),
            "day": self.day,
            "season": self._season(),
            "weather": self.weather,
            "terrain_fertile": getattr(self, "_cached_terrain_fertile", self.fertile),
            "terrain_rocks": getattr(self, "_cached_terrain_rocks", self.rocks),
            "relations": [
                {"a": a, "b": b, "score": s}
                for (a, b), s in sorted(self.relations.items())
            ],
            "clans": {
                str(k): {kk: (dict(vv) if isinstance(vv, dict) else vv) for kk, vv in v.items()}
                for k, v in self.clans.items()
            },
            "events": self._events_this_tick,  # AA: pre-dumped in _emit() — zero work here
            "signals": [dict(sg) for sg in self.signals],
            "fires": [dict(f) for f in self.fires],
            # §AO E: field campfires (tiny list, rides every frame)
            "campfires": [dict(cf) for cf in self.campfires],
            "boundary_stones": [dict(s) for s in self.boundary_stones],
            "markets": [dict(m, a=pair[0], b=pair[1]) for pair, m in self.markets.items()],
            "wind": {"angle": round(self.wind_angle, 3), "speed": round(self.wind_speed, 3)},
            # §AQ PH-3: channels, planks & masonry ride every frame (tiny lists)
            "rivers": [
                {"cy": r["cy"], "hw": round(r["hw"], 2),
                 "dir": r["dir"], "flood": r["flood_ticks"] > 0}
                for r in self.rivers
            ],
            "bridges": [{"x": b["x"], "cy": b["cy"]} for b in self.bridges],
            "dams": [
                {"x": d["x"], "cy": d["cy"], "hp_frac": round(max(0.0, d["hp"]) / DAM_HP, 2)}
                for d in self.dams
            ],
            # §AQ PH-4: the static height field rides only the keyframe
            "elevation": (
                {"cell": ELEV_CELL, "cols": self._elev_cols, "rows": self._elev_rows,
                 "h": self.elev_grid}
                if self.config.relief_enabled else {}
            ),
            # §AQ PH-9: visible bolts ride every frame (short-lived, few)
            "lightning": [dict(b) for b in self.lightning],
            # §AQ PH-10: only DISCOVERED anomalies appear on the wire
            "anomalies": [
                {"x": a["x"], "y": a["y"], "kind": a["kind"]}
                for a in self.anomalies if a["discovered"]
            ],
            # §AQ PH-10: the law-change shimmer front
            "law_wave": (
                {"born_tick": self.law_wave["born_tick"],
                 "ticks": LAW_WAVE_TICKS}
                if self.law_wave is not None else {}
            ),
            "wind": {"angle": round(self.wind_angle, 3), "speed": round(self.wind_speed, 3)},
            "age": self._age(),
            "age_tick": self._age_tick(),
            "age_day": self._age_day(),
            "age_total_days": self._age_total_days(),
        }

    def snapshot_delta_payload(self) -> dict:

        """Phase 1 AJ: Lightweight delta snapshot payload.

        Broadcasts only newly spawned, removed, or modified entities since last frame.
        Reduces payload size by 85–95%.
        """
        cfg = self.config
        upsert_entities: list[dict] = []
        population: dict[str, int] = {}
        alive = 0
        infected = 0
        clans = self.clans

        curr_entities = self.world.entities
        curr_ids = set(curr_entities.keys())
        prev_ids = self._last_broadcast_entities
        remove_ids = list(prev_ids - curr_ids)

        new_state: dict[int, tuple] = {}
        last_state = self._last_broadcast_state

        for eid, e in curr_entities.items():
            sig = self._entity_sig(e)
            new_state[eid] = sig
            if eid not in last_state:
                # Newly spawned entity: send full payload
                upsert_entities.append(self._entity_payload(e, clans))
            elif last_state[eid] != sig:
                # Existing entity modified: send compact delta payload
                upsert_entities.append(self._entity_delta_payload(e))

            if isinstance(e, Creature):
                label = e.caste
                alive += 1
                if e.infected:
                    infected += 1
            else:
                label = e.kind.capitalize()
            population[label] = population.get(label, 0) + 1

        self._last_broadcast_state = new_state
        self._last_broadcast_entities = curr_ids

        # Delta clans tracking: send only new or modified clans
        curr_clans = self.clans
        delta_clans: dict[str, dict] = {}
        last_clans = getattr(self, "_last_broadcast_clans", {})
        for cid, info in curr_clans.items():
            s_cid = str(cid)
            # Compare representation against last broadcast
            sig = _clan_sig(info)
            if s_cid not in last_clans or last_clans[s_cid] != sig:
                delta_clans[s_cid] = {kk: (dict(vv) if isinstance(vv, dict) else vv) for kk, vv in info.items()}
                last_clans[s_cid] = sig
        self._last_broadcast_clans = last_clans

        # §AQ PH-3: channels/planks/masonry ride deltas only when they change —
        # the client keeps the last known layout otherwise (websocket.ts ??).
        rivers_sig = (
            tuple((r["cy"], round(r["hw"], 1), r["dir"], r["flood_ticks"] > 0) for r in self.rivers),
            tuple((b["x"], b["cy"]) for b in self.bridges),
            tuple((d["x"], d["cy"], d["hp"] // 60) for d in self.dams),
        )
        geo: dict = {}
        if rivers_sig != getattr(self, "_last_rivers_sig", None):
            self._last_rivers_sig = rivers_sig
            geo = {
                "rivers": [
                    {"cy": r["cy"], "hw": round(r["hw"], 2),
                     "dir": r["dir"], "flood": r["flood_ticks"] > 0}
                    for r in self.rivers
                ],
                "bridges": [{"x": b["x"], "cy": b["cy"]} for b in self.bridges],
                "dams": [
                    {"x": d["x"], "cy": d["cy"], "hp_frac": round(max(0.0, d["hp"]) / DAM_HP, 2)}
                    for d in self.dams
                ],
            }
        # §AQ PH-9/10: bolts ride when present; anomalies/wave only on change
        if self.lightning:
            geo["lightning"] = [dict(b) for b in self.lightning]
        anomalies = [
            {"x": a["x"], "y": a["y"], "kind": a["kind"]}
            for a in self.anomalies if a["discovered"]
        ]
        a_sig = tuple((a["x"], a["y"]) for a in anomalies)
        if a_sig != getattr(self, "_last_anomalies_sig", None):
            self._last_anomalies_sig = a_sig
            geo["anomalies"] = anomalies
        if self.law_wave is not None:
            geo["law_wave"] = {"born_tick": self.law_wave["born_tick"], "ticks": LAW_WAVE_TICKS}

        return {
            "type": "delta_state",
            "tick": self.tick,
            "seed": cfg.seed,
            "upsert_entities": upsert_entities,
            "remove_ids": remove_ids,
            "population": population,
            "creatures_alive": alive,
            "creatures_dead": self.deaths,
            "dead_by_cause": dict(self._death_counts),
            "infected_count": infected,
            "time_of_day": round(self._time_of_day(), 3),
            "day": self.day,
            "season": self._season(),
            "weather": self.weather,
            "relations": [
                {"a": a, "b": b, "score": s}
                for (a, b), s in sorted(self.relations.items())
            ],
            "clans": delta_clans,
            "events": self._events_this_tick,
            "signals": [dict(sg) for sg in self.signals],
            "fires": [dict(f) for f in self.fires],
            # §AO E: field campfires (tiny list, rides every frame)
            "campfires": [dict(cf) for cf in self.campfires],
            "boundary_stones": [dict(s) for s in self.boundary_stones],
            "markets": [dict(m, a=pair[0], b=pair[1]) for pair, m in self.markets.items()],
            "wind": {"angle": round(self.wind_angle, 3), "speed": round(self.wind_speed, 3)},
            **geo,
            "age": self._age(),
            "age_tick": self._age_tick(),
            "age_day": self._age_day(),
            "age_total_days": self._age_total_days(),
        }

    def snapshot(self) -> StateMessage:
        """Typed snapshot for cold paths (REST /api/state, tests)."""
        return StateMessage.model_validate(self.snapshot_payload())

    def _entity_payload(self, e: Entity, clans: dict | None = None) -> dict:
        if clans is None:
            clans = self.clans
        if isinstance(e, Creature):
            name, glyph, hue_shift, scale_jitter, angle_jitter = self._cached_identity(
                e.id, e.generation
            )
            c_meta = clans.get(e.clan_id) if e.clan_id else None
            base: dict = {
                "id": e.id,
                "kind": e.kind,
                "x": round(e.x, 3),
                "y": round(e.y, 3),
                "angle": round(e.angle, 4),
                "shape": e.shape,
                "sides": e.sides,
                "caste": e.caste,
                "energy": round(e.energy, 2),
                "status": e.status,
                "radius": round(e.radius, 3),
                "age": e.age,
                "lifespan": round(e.lifespan, 1),
                "stage": e.stage,
                "irregularity": e.irregularity,
                "health": round(e.health, 1),
                "infected": e.infected,
                "sex": e.sex,
                "mother_id": e.mother_id or None,
                "father_id": e.father_id or None,
                "clan_id": e.clan_id or None,
                "clan_color": c_meta.get("color") if c_meta else None,
                "clan_name": c_meta.get("name") if c_meta else None,
                "clan_totem": c_meta.get("totem") if c_meta else None,
                "is_predator": e.is_predator or None,
                "is_herbivore": e.is_herbivore or None,
                "sleeping": e.sleeping,
                "indoors": e.indoors,
                "generation": e.generation,
                "born_tick": e.born_tick,
                "personal_name": name,
                "glyph": glyph,
                "hue_shift": hue_shift,
                "scale_jitter": scale_jitter,
                "angle_jitter": angle_jitter,
                "chill": round(e.chill, 2),
                "body_temp": round(getattr(e, "body_temp", 20.0), 1),
                # §AQ PH-7: cold-torpor collapses the body in place
                "torpid": self._is_torpid(e) or None,
                "trait": e.trait,
                "equipped_item": getattr(e, "equipped_item", None),
                "food_basket": getattr(e, "food_basket", 0) or None,
                "personality": getattr(e, "personality", "brave"),
                "skills": getattr(e, "skills", None),
                "title": getattr(e, "title", None),
                "emote": getattr(e, "emote", None),
            }
            # BA: NN state if enabled and SoA has this creature
            if getattr(self.config, "nn_enabled", False) and getattr(self, "_soa", None) is not None:
                try:
                    soa = self._soa  # type: ignore
                    idx = -1
                    if hasattr(soa, "ids"):
                        try:
                            import numpy as _np  # type: ignore

                            if hasattr(soa.ids, "shape"):
                                arr = soa.ids[: soa.N]  # type: ignore
                                w = _np.where(arr == e.id)[0]
                                if len(w):
                                    idx = int(w[0])
                            else:
                                for i in range(soa.N):
                                    if int(soa.ids[i]) == e.id:  # type: ignore
                                        idx = i
                                        break
                        except Exception:
                            for i in range(getattr(soa, "N", 0)):
                                try:
                                    if int(soa.ids[i]) == e.id:  # type: ignore
                                        idx = i
                                        break
                                except Exception:
                                    continue
                    if idx >= 0:
                        try:
                            if hasattr(soa.hidden_state, "shape"):
                                base["nn_hidden"] = round(float(soa.hidden_state[idx, 0]), 3)  # type: ignore
                                base["nn_outputs"] = [round(float(v), 3) for v in soa.outputs_buf[idx].tolist()]  # type: ignore
                                base["nn_genome_preview"] = [round(float(v), 3) for v in soa.genomes[idx, :8].tolist()]  # type: ignore
                            else:
                                base["nn_hidden"] = round(float(soa.hidden_state[idx][0]), 3)  # type: ignore
                                base["nn_outputs"] = [round(float(v), 3) for v in soa.outputs_buf[idx]]  # type: ignore
                                base["nn_genome_preview"] = [round(float(v), 3) for v in soa.genomes[idx][:8]]  # type: ignore
                        except Exception:
                            pass
                except Exception:
                    pass
            return base
        if isinstance(e, House):
            return {
                "id": e.id,
                "kind": e.kind,
                "x": round(e.x, 3),
                "y": round(e.y, 3),
                "angle": round(e.angle, 4),
                "size": round(e.size, 2),
                "door_width": round(e.door_width, 2),
                "door_offset": round(e.door_offset, 2),
                "door_side": e.door_side,
                "clan_id": e.clan_id or None,
                "clan_color": e.clan_color,
                "is_main": bool(e.clan_id and self.clans.get(e.clan_id, {}).get("main_house_id") == e.id),
                "is_ruin": e.is_ruin or None,

                "abandoned_ticks": e.abandoned_ticks or None,
                "material": e.material,  # §AQ PH-1 insulation tier
                # §AT-3: recent hostile takeover — renderer flashes the crest
                "takeover_age": (self.tick - e.takeover_tick) if getattr(e, "takeover_tick", -1) >= 0 else None,
                # §AN: painted chronicle of great days on the walls
                "murals": e.murals or None,
                # §AQ PH-1: fire burns on this hearth
                "hearth_lit": e.hearth_lit or None,
                # §AQ PH-6: structural integrity & rubble state
                "hp_frac": (
                    round(max(0.0, e.hp) / MATERIAL_STATS.get(e.material, MATERIAL_STATS["wood"])["durability"], 2)
                    if e.hp >= 0 else None
                ),
                "rubble": bool(e.rubble > 0) or None,
            }
        if isinstance(e, Food):
            is_withering = False
            if (
                self.config.food_decay_enabled
                and e.growth >= 1.0
                and e.mature_ticks
                >= WILT_FRACTION
                * max(1, round(self.config.food_lifespan_ticks * FOOD_LIFESPAN_MULT.get(e.variant, 1.0)))
            ):
                is_withering = True
            d = {
                "id": e.id,
                "kind": e.kind,
                "x": round(e.x, 3),
                "y": round(e.y, 3),
                "angle": round(e.angle, 4),
                "growth": round(e.growth, 3),
                "variant": e.variant,
            }
            if is_withering:
                d["withering"] = True
            # §AM: sown & furrowed crops read differently on the field
            if e.cultivated:
                d["cultivated"] = True
            if e.irrigated:
                d["irrigated"] = True
            return d
        return {
            "id": e.id,
            "kind": e.kind,
            "x": round(e.x, 3),
            "y": round(e.y, 3),
            "angle": round(e.angle, 4),
        }

    def _entity_state(self, e: Entity) -> EntityState:
        return EntityState.model_validate(self._entity_payload(e))


def _house_wall_segments(h: House) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The house's wall segments; the door side is split around the doorway."""
    return list(
        _wall_segments_cached(
            (h.id, h.x, h.y, h.size, h.door_width, h.door_side or "south", h.door_offset or 0.0)
        )
    )


@lru_cache(maxsize=1024)
def _wall_segments_cached(
    key: tuple,
) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    """Wall segments are pure geometry — cache them per house.

    Called ~10k times per tick across all creatures; rebuilding the segment
    list each call used to be a top-3 hotspot in the tick profile.
    """
    hid, x, y, size, door_w, side, offset = key
    half = size / 2
    x0, y0 = x - half, y - half
    x1, y1 = x + half, y + half
    d = door_w / 2
    c = offset
    if side == "north":
        return (
            ((x0, y0), (x + c - d, y0)),
            ((x + c + d, y0), (x1, y0)),
            ((x0, y0), (x0, y1)),
            ((x1, y0), (x1, y1)),
            ((x0, y1), (x1, y1)),
        )
    if side == "west":
        return (
            ((x0, y0), (x1, y0)),
            ((x0, y1), (x1, y1)),
            ((x1, y0), (x1, y1)),
            ((x0, y0), (x0, y + c - d)),
            ((x0, y + c + d), (x0, y1)),
        )
    if side == "east":
        return (
            ((x0, y0), (x1, y0)),
            ((x0, y0), (x0, y1)),
            ((x0, y1), (x1, y1)),
            ((x1, y0), (x1, y + c - d)),
            ((x1, y + c + d), (x1, y1)),
        )
    # south (default)
    return (
        ((x0, y0), (x1, y0)),
        ((x0, y0), (x0, y1)),
        ((x1, y0), (x1, y1)),
        ((x0, y1), (x + c - d, y1)),
        ((x + c + d, y1), (x1, y1)),
    )


def _house_wall_segments_closed(h: House) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Four fully closed walls — the doorway sealed (predator refuge, §L)."""
    half = h.size / 2
    x0, y0 = h.x - half, h.y - half
    x1, y1 = h.x + half, h.y + half
    return [
        ((x0, y0), (x1, y0)),
        ((x0, y0), (x0, y1)),
        ((x1, y0), (x1, y1)),
        ((x0, y1), (x1, y1)),
    ]


def _path_crosses_wall(
    px: float, py: float, qx: float, qy: float, h: House, predator_blocked: bool = False
) -> bool:
    """True if the movement path p->q crosses a house wall (door is passable unless predator_blocked)."""
    if h.is_ruin:
        return False  # crumbled ruins don't block
    # Broad phase — bounding-box reject. Most creature-house pairs are far
    # apart; this cheap test skips the expensive per-segment math below.
    half = h.size * 0.5
    hx, hy = h.x, h.y
    min_x = px if px < qx else qx
    max_x = qx if px < qx else px
    min_y = py if py < qy else qy
    max_y = qy if py < qy else py
    if max_x < hx - half or min_x > hx + half or max_y < hy - half or min_y > hy + half:
        return False
    path = ((px, py), (qx, qy))
    segments = _house_wall_segments_closed(h) if predator_blocked else _house_wall_segments(h)
    return any(
        segments_intersect(path[0], path[1], a, b)
        for a, b in segments
    )
