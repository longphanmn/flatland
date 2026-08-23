"""Deterministic fixed-tick simulation of Flatland."""

import math
import random
from collections import deque
from functools import lru_cache
from typing import Any, Callable, cast

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

YIELD_RADIUS = 2.5  # lower castes step aside within this range

# §L shelter: reference floor area for the house_capacity law (8×8 hall)
HOUSE_REF_AREA = 64.0

# §AB politics pacing (per-tick chances; determinism via fixed iteration order)
COALITION_FORM_CHANCE = 0.003  # a leader founds a bloc this often
COALITION_JOIN_CHANCE = 0.01  # an unaligned clan petitions an existing bloc
LEADER_DECISION_CHANCE = 0.01  # a leader acts (war/peace/betrayal/tribute)
TRIBUTE_INTERVAL = 240  # ticks between vassal payments
DEFECT_CHANCE = 0.03  # unhappy member defects per tick
TREASON_RADIUS = 14.0  # false-knowledge seeding reach during betrayal

# §AC desperation cannibalism pacing
CANNIBAL_COOLDOWN = 120  # ticks between desperate kills
CANNIBAL_CORPSE_MULT = 0.5  # the body left after a cannibal feeds

# §AE food decay — nothing lasts forever: variant lifespan multipliers
FOOD_LIFESPAN_MULT = {"grass": 1.0, "berry": 1.5, "mushroom": 0.4, "poisonous": 3.0}
WILT_FRACTION = 0.8  # wilting (render fade) begins at this fraction of lifespan
WITHER_NUTRIENT_MULT = 0.5  # a withered plant fertilises at half a corpse's worth

# §H Plants & the nutrient cycle
SPREAD_RADIUS = 6.0  # mature plants seed new ground within this range
NUTRIENT_RADIUS = 10.0  # a fully decayed corpse fertilises plants within this range
NUTRIENT_BOOST = 0.5  # base growth granted by a decayed corpse (× nutrient_cycle_rate)
SPROUT_GROWTH = 0.15  # every newly spawned plant starts here

# §O Biodiversity — plant variants (§O)
VARIANT_ENERGY = {"grass": 32.0, "berry": 48.0, "mushroom": 24.0, "poisonous": 8.0}
VARIANT_HEALTH = {"grass": 0.0, "berry": 1.0, "mushroom": 0.0, "poisonous": -30.0}
VARIANT_GROWTH_MULT = {"grass": 1.0, "berry": 0.65, "mushroom": 0.85, "poisonous": 0.60}
# berry peaks in autumn, mushrooms tolerate winter, grass thrives summer
VARIANT_SEASON_MULT = {
    "grass": {"spring": 1.05, "summer": 1.15, "autumn": 1.0, "winter": 0.45},
    "berry": {"spring": 0.5, "summer": 0.8, "autumn": 1.9, "winter": 0.25},
    "mushroom": {"spring": 1.0, "summer": 0.6, "autumn": 1.35, "winter": 1.1},
    "poisonous": {"spring": 1.0, "summer": 1.0, "autumn": 1.0, "winter": 1.0},
}

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

TOTEMS = (
    "Wolf", "Tree", "Shield", "Eye",
    "Bear", "Stag", "Owl", "Rabbit", "Boar", "Fox", "Raven", "Serpent",
)
# Buff vocabulary (all optional keys, consumed generically via _totem_stat):
#   speed        additive speed multiplier when hunting/fleeing (Wolf-style)
#   hunt_radius  flat bonus to predator sight (Wolf-style)
#   harvest      fractional harvest bonus on plants (×1+h) and corpses (×1+0.4h)
#   sight        fractional perceive-radius bonus (×1+s)
#   defense      fractional damage reduction; sheltered healing scales ×(1+d)
#   health       flat health gift at birth
#   birth        fractional fertility bonus for the mother's clan
TOTEM_BUFF = {
    "Wolf": {"speed": 0.10, "hunt_radius": 2.0},
    "Tree": {"harvest": 0.25},
    "Shield": {"defense": 0.30, "health": 15.0},
    "Eye": {"sight": 0.25},
    "Bear": {"defense": 0.20, "health": 10.0},
    "Stag": {"speed": 0.08, "birth": 0.15},
    "Owl": {"sight": 0.35},
    "Rabbit": {"birth": 0.25},
    "Boar": {"harvest": 0.15, "defense": 0.10},
    "Fox": {"hunt_radius": 3.0, "speed": 0.06},
    "Raven": {"sight": 0.15, "harvest": 0.10},
    "Serpent": {"defense": 0.15, "speed": 0.05},
}
# Totem biases the clan's starting specialization drift (§P specialization)
TOTEM_SPEC = {
    "Wolf": {"warrior": 0.50, "farmer": 0.25, "scavenger": 0.25},
    "Tree": {"warrior": 0.20, "farmer": 0.60, "scavenger": 0.20},
    "Shield": {"warrior": 0.45, "farmer": 0.25, "scavenger": 0.30},
    "Eye": {"warrior": 0.25, "farmer": 0.25, "scavenger": 0.50},
    "Bear": {"warrior": 0.45, "farmer": 0.30, "scavenger": 0.25},
    "Stag": {"warrior": 0.25, "farmer": 0.45, "scavenger": 0.30},
    "Owl": {"warrior": 0.25, "farmer": 0.35, "scavenger": 0.40},
    "Rabbit": {"warrior": 0.20, "farmer": 0.50, "scavenger": 0.30},
    "Boar": {"warrior": 0.35, "farmer": 0.40, "scavenger": 0.25},
    "Fox": {"warrior": 0.30, "farmer": 0.25, "scavenger": 0.45},
    "Raven": {"warrior": 0.20, "farmer": 0.25, "scavenger": 0.55},
    "Serpent": {"warrior": 0.40, "farmer": 0.25, "scavenger": 0.35},
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
        self._events_this_tick: list[HistoryEvent] = []
        # T: per-tick caches
        self._cached_creatures: list[Creature] = []
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
        self._eaters_this_tick: list[int] = []
        self.fertile: list[dict] = []  # {x,y,r} — food prefers these grounds
        self.rocks: list[dict] = []  # {x,y,r} — solid circles that block movement
        self.signals: list[dict] = []  # §Q: {x,y,kind,sender,clan_id,ttl}
        self.fires: list[dict] = []  # §S wildfire: {x,y,r,ttl}
        self._spawn_initial()
        self._generate_terrain()

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

    @property
    def day(self) -> int:
        return self.tick // max(1, self.config.day_length) + 1

    def _update_weather(self) -> None:
        cfg = self.config
        if not cfg.weather_enabled or self.rng.random() >= cfg.weather_change_rate:
            return
        others = [w for w in WEATHER_STATES if w != self.weather]
        self.weather = self.rng.choice(others)

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

    def distance(self, ax: float, ay: float, bx: float, by: float) -> float:
        """Proxy to world distance (convenience for tests)."""
        return self.world.distance(ax, ay, bx, by)

    def _inside_house(self, c: Creature, h: House) -> bool:
        if h.is_ruin:
            return False
        return (
            abs(c.x - h.x) < h.size / 2 - 0.3 and abs(c.y - h.y) < h.size / 2 - 0.3
        )

    def _claim_bed(self, house: House) -> bool:
        """One bed per occupant until the house is full; creatures arrive in id order."""
        taken = self._beds.get(house.id, 0)
        if taken >= self._house_beds(house):
            return False
        self._beds[house.id] = taken + 1
        return True

    def _house_beds(self, house: House) -> int:
        """Beds scale with floor area: `house_capacity` is the law for an
        average 8×8 hall — a cramped 6×6 hut holds barely half that, a grand
        hall twice it. No village can cram a whole clan into one shelter."""
        return max(1, int(self.config.house_capacity * (house.size * house.size) / HOUSE_REF_AREA))

    # ------------------------------------------------------------------ setup
    def _rand_pos(self) -> tuple[float, float]:
        cfg = self.config
        return self.rng.uniform(0, cfg.width), self.rng.uniform(0, cfg.height)

    def _spawn_creature(self, shape: str, sides: int) -> None:
        cfg = self.config
        x, y = self._rand_pos()
        iso = 60.0
        if sides == 3:
            # Founding Isosceles: somewhere on the long road toward 60 degrees.
            iso = self.rng.uniform(0.5, 59.5)
        caste = caste_name(sides, shape, iso)
        traits = traits_for(caste)
        self.world.add(
            Creature(
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
        )

    def _spawn_predator(self) -> None:
        """Spawn a Carnivore predator (§I) — fast, no clan, hunts prey."""
        cfg = self.config
        x, y = self._rand_pos()
        traits = traits_for("Predator")
        self.world.add(
            Creature(
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
        )

    def _spawn_herbivore(self) -> None:
        """Spawn a wild herbivore grazer (§O) — clanless, eats plants, hunted by predators."""
        cfg = self.config
        x, y = self._rand_pos()
        traits = traits_for("Herbivore")
        self.world.add(
            Creature(
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
        )

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
        for _ in range(cfg.food_count):
            x, y = self._food_pos()
            # World-spawned plants arrive mature: the food law promises harvest.
            self.world.add(self._new_food(x, y, growth=1.0))
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
                )
            )
        self._found_founding_clans()
        # Predators (§I) — spawn after clans so they don't get a clan crest; only if enabled
        if cfg.predation_enabled and cfg.predator_ratio > 0:
            n_predators = self._jittered(area * cfg.creature_density * cfg.predator_ratio)
            for _ in range(n_predators):
                self._spawn_predator()
        # Herbivores (§O) — wild grazers, clanless, compete for plants and feed predators
        if cfg.beast_ratio > 0:
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
            totem = TOTEMS[(cid * 17 + self.config.seed) % len(TOTEMS)]
        # specialization drift start — totem biases initial role.
        # COPY: TOTEM_SPEC entries are mutated in place by drift; sharing them
        # across clans (or worlds!) would couple their specializations.
        spec = dict(TOTEM_SPEC.get(totem, {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34}))
        culture = f"{CULTURE_ADJECTIVES[(cid * 11 + self.config.seed) % len(CULTURE_ADJECTIVES)]} {CULTURE_NOUNS[(cid * 19 + self.config.seed) % len(CULTURE_NOUNS)]}"
        self.clans[cid] = {
            "name": name,
            "founder_id": founder.id if founder is not None else None,
            "born_tick": self.tick,
            "color": CLAN_COLORS[(cid - 1) % len(CLAN_COLORS)],
            "totem": totem,
            "leader_id": founder.id if founder is not None else None,
            "specialization": spec,
            "culture": culture,
            "culture_id": cid,
            "coalition_id": None,
            "larder": 0.0,
            "tribute_to": None,
        }
        return cid

    def _functional_houses(self) -> list[House]:
        """Non-ruin houses in id order — the possible settlement anchors (§V)."""
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
        """Generic totem-buff lookup (see TOTEM_BUFF vocabulary)."""
        return float(TOTEM_BUFF.get(self._totem_of(c), {}).get(key, 0.0))

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
        # clans without a free house: build a settlement when unpinned (§L)
        # (ghost clans with no living members never build)
        for cid in sorted(clan_ids):
            if not any(h.clan_id == cid for h in self._functional_houses()):
                if any(c.clan_id == cid for c in self.world.creatures()):
                    self._claim_house_for_clan(cid)

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
        homeless = [
            cid
            for cid in sorted(self.clans.keys())
            if not any(h.clan_id == cid for h in houses)
        ]
        if not homeless:
            return
        self._anchor_homeless_clans(homeless)

    def _claim_house_for_clan(self, clan_id: int) -> None:
        """Settle a clan at the free house nearest its members (§V anchor claim);
        with none free it founds a new settlement (§L settlement economy)."""
        if not self.config.house_claim_enabled:
            return
        houses = self._functional_houses()
        members = [c for c in self.world.creatures() if c.clan_id == clan_id]
        free = [h for h in houses if h.clan_id == 0]
        if free and members:
            ax, ay = self._clan_centroid(members)
            h = self._nearest_house_to(ax, ay, free)
            h.clan_id = clan_id
            h.clan_color = self.clans.get(clan_id, {}).get("color")
            return
        # No free house: a new clan founds a new settlement (§L settlement economy)
        # But respect explicit overrides: tests/scenarios that pin num_houses keep housing shortage
        if self.config.shelter_enabled and self.config.num_houses < 0:
            founder = min(members, key=lambda c: (-c.age, c.id)) if members else None
            self._spawn_settlement_house(clan_id, near=founder)

    def _refresh_house_claims(self) -> None:
        """Sync house crests with the current law (enable/disable)."""
        houses = [e for e in self.world.entities.values() if isinstance(e, House) and not e.is_ruin]
        if not self.config.house_claim_enabled:
            for h in houses:  # type: ignore[union-attr]
                h.clan_id = 0
                h.clan_color = None
        else:
            self._assign_house_claims()

    # ------------------------------------------------------- settlement economy
    def _target_house_count(self) -> int:
        """Houses scale with map area and with carrying capacity (§L settlement economy).

        Base is area × house_density (W worldgen); then scaled by carrying_capacity
        relative to the default 80 so that raising the soft cap raises the bed supply.
        Keeps the historic housing shortage (≈60% beds vs cap) while letting god tune it.
        """
        cfg = self.config
        area = cfg.width * cfg.height
        base = area * cfg.house_density
        carrying = cfg.effective_carrying_capacity
        # scale with carrying_capacity; default 80 → factor 1.0
        factor = carrying / 80.0 if 80 else 1.0
        target = round(base * factor)
        # also ensure at least enough beds for ~60% of the carrying capacity
        cap_based = round(carrying / max(1, cfg.house_capacity) * 0.6)
        target = max(target, cap_based)
        return max(1, target)

    def _spawn_settlement_house(self, clan_id: int | None = None, near: Creature | None = None) -> House:
        """Spawn a new house — near a clan founder if given, else random; claim it if clan_id."""
        cfg = self.config
        max_radius = max(
            (c.radius for c in self.world.creatures()), default=DEFAULT_RADIUS
        )
        size = self.rng.uniform(cfg.house_min_size, cfg.house_max_size)
        x, y = self._find_non_overlapping_house_pos(size, near=near)
        door_width = min(size * 0.8, 2.0 * max_radius * cfg.door_clearance)
        house = House(
            x=x, y=y, size=size, door_width=door_width,
            door_side=self.rng.choice(("north", "east", "south", "west")),
        )
        if clan_id is not None and self.config.house_claim_enabled:
            house.clan_id = clan_id
            house.clan_color = self.clans.get(clan_id, {}).get("color")
        self.world.add(house)
        self._emit(
            HistoryEvent(
                type="settlement", tick=self.tick + 1, entity_id=house.id,
                x=round(house.x, 2), y=round(house.y, 2),
                payload={"clan_id": clan_id, "size": round(size, 2)},
            )
        )
        return house

    def _update_settlements(self) -> None:
        """Settlement economy tick: grow to meet demand, crumble abandoned houses (§L)."""
        cfg = self.config
        if not cfg.shelter_enabled:
            return
        # Respect explicit overrides: pinned scenarios (tests) keep exact housing
        if cfg.num_houses >= 0:
            return
        # — growth: houses scale with carrying_capacity / density —
        functional = [h for h in self.world.entities.values() if isinstance(h, House) and not h.is_ruin]
        target = self._target_house_count()
        # Spawn at most one per tick to keep determinism smooth (jitter already in target)
        if len(functional) < target:
            # avoid spawning every tick when far below target — one per tick is enough
            self._spawn_settlement_house()

        # — decay: abandoned houses crumble to ruins —
        # Build living-clan set once
        living_clans = {c.clan_id for c in self.world.creatures() if c.clan_id}
        for h in list(functional):
            assert isinstance(h, House)
            # A house is abandoned if unclaimed, or its clan has no living members
            is_abandoned = (h.clan_id == 0) or (h.clan_id not in living_clans)
            if is_abandoned:
                h.abandoned_ticks += 1
            else:
                h.abandoned_ticks = 0
            if h.abandoned_ticks >= cfg.house_decay_ticks:
                h.is_ruin = True
                h.clan_id = 0
                h.clan_color = None
                self._emit(
                    HistoryEvent(
                        type="ruin", tick=self.tick + 1, entity_id=h.id,
                        x=round(h.x, 2), y=round(h.y, 2),
                        payload={"abandoned_ticks": h.abandoned_ticks},
                    )
                )

    def _house_for(self, c: Creature, houses: list[Entity]) -> House | None:
        """Preferred shelter: the clan's own roof while it has beds free; when
        it is full (or the creature is clanless) the nearest roof WITH space —
        a house's capacity depends on its size, so overflow spills across the
        village instead of queueing all night at one packed door. Only when
        every roof is full does the nearest door queue for tomorrow."""
        if not houses:
            return None

        def dist(h: House) -> float:
            return self.world.distance(c.x, c.y, h.x, h.y)

        def has_room(h: House) -> bool:
            return self._beds.get(h.id, 0) < self._house_beds(h)

        own: House | None = None
        if self.config.house_claim_enabled and c.clan_id:
            own = next(
                (
                    h  # type: ignore[union-attr]
                    for h in houses
                    if isinstance(h, House) and h.clan_id == c.clan_id
                ),
                None,
            )
        if own is not None and has_room(own):
            return own
        free = [h for h in houses if isinstance(h, House) and has_room(h)]
        if free:
            # kin keep to kin where several roofs of their clan have space
            # (conquest/settlements can leave a clan more than one house)
            own_free = [h for h in free if own is not None and h.clan_id == c.clan_id]
            return min(own_free or free, key=dist)
        # every roof is full: fall back to own (or nearest) and queue at the door
        return own or min(houses, key=dist)  # type: ignore[arg-type,return-value]

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

    def _food_pos(self) -> tuple[float, float]:
        """New food prefers fertile ground (god law sets the bias)."""
        cfg = self.config
        if self.fertile and self.rng.random() < cfg.fertile_food_bias:
            patch = self.rng.choice(self.fertile)
            ang = self.rng.uniform(0, 2 * math.pi)
            rad = math.sqrt(self.rng.random()) * patch["r"]
            return (
                (patch["x"] + math.cos(ang) * rad) % cfg.width,
                (patch["y"] + math.sin(ang) * rad) % cfg.height,
            )
        return self._rand_pos()

    def _pick_variant(self, x: float, y: float) -> str:
        """§O: choose grass/berry/mushroom/poisonous for a new sprout."""
        cfg = self.config
        if not cfg.plant_variants_enabled:
            return "grass"
        if cfg.poison_rate > 0 and self.rng.random() < cfg.poison_rate:
            return "poisonous"
        season = self._season()
        # base weights shift with season (autumn → berries, winter → mushrooms)
        if season == "autumn":
            weights = {"grass": 0.30, "berry": 0.48, "mushroom": 0.22}
        elif season == "winter":
            weights = {"grass": 0.35, "berry": 0.08, "mushroom": 0.57}
        elif season == "summer":
            weights = {"grass": 0.58, "berry": 0.22, "mushroom": 0.20}
        else:  # spring
            weights = {"grass": 0.50, "berry": 0.18, "mushroom": 0.32}
        # decomposer boost: near corpses or rocks → more mushrooms
        near_decomposer = False
        for e in self.world.entities.values():
            if e.kind == "corpse" and self.world.distance(x, y, e.x, e.y) < NUTRIENT_RADIUS:
                near_decomposer = True
                break
        if not near_decomposer:
            for rock in self.rocks:
                if self.world.distance(x, y, rock["x"], rock["y"]) < rock["r"] + 4.0:
                    near_decomposer = True
                    break
        if near_decomposer:
            # shift 0.25 from grass/berry to mushroom
            weights["mushroom"] = min(0.70, weights["mushroom"] + 0.25)
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
        """Push a creature out of any rock it has wandered into; return the rock."""
        hit = None
        for rock in self.rocks:
            d = self.world.distance(c.x, c.y, rock["x"], rock["y"])
            min_d = rock["r"] + c.radius
            if d < min_d:
                ux, uy = self.world.delta(c.x, c.y, rock["x"], rock["y"])
                if abs(ux) < 1e-6 and abs(uy) < 1e-6:
                    ang = self.rng.uniform(0, 2 * math.pi)
                    ux, uy = math.cos(ang), math.sin(ang)
                norm = math.hypot(ux, uy) or 1.0
                c.x, c.y = self.world.normalize(
                    rock["x"] + ux / norm * min_d,
                    rock["y"] + uy / norm * min_d,
                )
                c.angle = math.atan2(uy, ux)
                hit = rock
        return hit

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

    def _give_up_on(self, c: Creature, target: Entity) -> None:
        """A meal is unreachable (behind stone or wall): abandon it for a while
        and seek food somewhere else — no creature starves grinding at an obstacle.
        Grudges are per-meal and never refreshed while fresh, so each memory
        always fades and the creature keeps retrying other meals meanwhile."""
        ttl = self.config.food_giveup_ticks
        if ttl <= 0:
            return
        grudges = c.give_ups
        if len(grudges) > 8:  # keep the memory small
            expired = [k for k, t0 in grudges.items() if self.tick - t0 >= ttl]
            for k in expired:
                del grudges[k]
        if self.tick - grudges.get(target.id, -ttl) < ttl:
            return
        grudges[target.id] = self.tick

    # ------------------------------------------------------------- §X knowledge
    def _fact_fresh(self, c: Creature, key, ttl: int | None = None) -> dict | None:
        """Return a live fact or None (and prune it when stale)."""
        f = c.facts.get(key)
        if not isinstance(f, dict):
            return None
        limit = ttl if ttl is not None else max(1, self.config.knowledge_ttl)
        if self.tick - int(f.get("tick", -limit)) > limit:
            del c.facts[key]
            return None
        return f

    def _learn(self, c: Creature, key, x: float | None = None, y: float | None = None,
               conf: float = 1.0) -> None:
        """§X firsthand experience becomes knowledge (conf 1.0)."""
        if not self.config.knowledge_enabled or self.config.knowledge_ttl <= 0:
            return
        fact: dict = {"tick": self.tick, "conf": round(conf, 3)}
        if x is not None and y is not None:
            fact["x"], fact["y"] = round(x, 2), round(y, 2)
        c.facts[key] = fact

    def _hear_fact(self, c: Creature, msg_fact: dict | None) -> None:
        """§X rumor: a heard fact lands with halved confidence — retold knowledge
        is vaguer than firsthand sighting; only better news overwrites."""
        if not msg_fact or not self.config.knowledge_enabled:
            return
        kind = msg_fact.get("kind")
        conf = float(msg_fact.get("conf", 1.0)) * 0.5
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
        """T: cache creatures once per tick and clan→members map."""
        self._cached_creatures = self.world.creatures()
        m: dict[int, list[Creature]] = {}
        for c in self._cached_creatures:
            m.setdefault(c.clan_id, []).append(c)
        self._clan_members = m

    def _get_creatures(self) -> list[Creature]:
        if self._cached_creatures:
            return self._cached_creatures
        self._refresh_cache()
        return self._cached_creatures

    # ------------------------------------------------------------------ tick
    def step(self) -> None:
        """Advance the world by exactly one tick (deterministic)."""
        self._eaten.clear()
        self._beds.clear()  # beds are re-contested every tick, in id order
        self._events_this_tick = []
        self._eaters_this_tick = []
        self._update_weather()
        # §Q signals decay (ripples fade)
        self.signals = [sg for sg in self.signals if sg["ttl"] > 1]
        for sg in self.signals:
            sg["ttl"] -= 1
        self._update_fires()
        self._update_disasters()
        self._update_plants()
        self.world.rebuild_index()
        self._refresh_cache()
        houses = [e for e in self.world.entities.values() if e.kind == "house" and not e.is_ruin]  # type: ignore[union-attr]
        for creature in list(self._cached_creatures):
            if creature.id not in self.world.entities:
                continue
            self._update_creature(creature, houses)
        self._refresh_cache()
        self._update_disease()
        # AA: positions moved this tick; re-bucket so the spatial war/mob
        # queries below see where everyone actually stands now.
        self.world.rebuild_index()
        self._update_war()
        self._refresh_cache()
        self._reproduce()
        self._update_relations()
        self._update_territory()
        self._update_schism()
        self._update_politics()
        self._update_clan_specialization()
        self._update_culture()
        self._enforce_food_law()
        self._update_corpses()
        self._update_settlements()
        self.tick += 1
        self._cached_creatures = []
        self._clan_members = {}

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
            "clan_id": victim.clan_id or None, "ttl": 12,
            "threat_x": round(aggressor.x, 2), "threat_y": round(aggressor.y, 2),
            "threat_clan": aggressor.clan_id or None,
        })

    def _mob_defenders(self, loser: Creature, winner: Creature) -> int:
        """Clan-mates of the victim within earshot of the fight (§X mobbing).

        AA: spatial query around the winner instead of scanning the whole
        roster inside the war pair loop (was O(n) per pair → O(n³)/tick).
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
        creatures = sorted(self.world.creatures(), key=lambda c: c.id)
        to_kill: list[tuple[Creature, Creature]] = []
        to_wound: list[tuple[Creature, Creature]] = []
        fallen: set[int] = set()  # losers already scheduled this tick
        r2 = cfg.attack_radius * cfg.attack_radius
        dist_sq = self.world.distance_sq
        w = self.world
        for a in creatures:
            if a.id not in w.entities or a.id in fallen:
                continue
            if a.is_predator or a.is_herbivore:
                continue
            neighbours = [
                b
                for b in w.query_radius(a.x, a.y, cfg.attack_radius)
                if b.kind == "creature" and b.id > a.id and b.id not in fallen
            ]
            neighbours.sort(key=lambda c: c.id)
            for b in neighbours:  # type: ignore[union-attr]
                b = cast(Creature, b)
                if b.id not in w.entities or b.is_predator or b.is_herbivore:
                    continue
                if not a.clan_id or not b.clan_id or a.clan_id == b.clan_id:
                    continue
                pair = self._relation_pair(a.clan_id, b.clan_id)
                if self._zone_of(self.relations.get(pair, 0)) != -1:
                    continue
                if dist_sq(a.x, a.y, b.x, b.y) > r2:
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
                if loser.trait == "paranoid":
                    # paranoid dodges? slight reduction
                    dmg *= 0.9
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
                    payload={"winner": winner.id, "a": loser.clan_id, "b": winner.clan_id, "lethal": True},
                )
            )
            self._bump_relation(loser.clan_id, winner.clan_id, -5)
            # §AB mutual defence — the loser attacked a whole coalition
            self._mobilise_coalition(winner.clan_id, loser.clan_id)
            # Territory conquest — winner absorbs loser's territory and house (§S)
            loser_house = None
            for h in self.world.entities.values():
                if isinstance(h, House) and getattr(h, "clan_id", 0) == loser.clan_id and not getattr(h, "is_ruin", False):
                    loser_house = h
                    break
            if loser_house is not None:
                winner_color = self.clans.get(winner.clan_id, {}).get("color")
                loser_house.clan_id = winner.clan_id
                loser_house.clan_color = winner_color
                self._emit(
                    HistoryEvent(
                        type="conquest",
                        tick=self.tick + 1,
                        entity_id=loser_house.id,
                        x=round(loser_house.x, 2),
                        y=round(loser_house.y, 2),
                        payload={"winner_clan": winner.clan_id, "loser_clan": loser.clan_id, "house_id": loser_house.id, "winner": winner.id, "loser": loser.id},
                    )
                )
        for loser, winner in to_wound:
            if loser.id not in self.world.entities:
                continue
            self._emit_help(loser, winner)  # §X wounded cry — rally the clan
            self._learn_enemy(loser, winner.clan_id)
            self._learn_enemy(winner, loser.clan_id)
            w_spec2 = self.clans.get(winner.clan_id, {}).get("specialization", {}).get("warrior", 0.33) if winner.clan_id else 0.33
            trait_mult = 1.0
            if winner.trait == "bold":
                trait_mult *= 1.25
            elif winner.trait == "peaceful":
                trait_mult *= 0.65
            if loser.trait == "paranoid":
                trait_mult *= 0.9
            dmg = cfg.attack_damage * (0.85 + w_spec2 * 0.45) * trait_mult * (1.0 - self._totem_stat(loser, "defense"))
            # §X mobbing softens blows on the wound path too
            dmg /= 1.0 + cfg.defense_weight * min(self._mob_defenders(loser, winner), 4)
            loser.health = max(0, loser.health - dmg)
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
                    payload={"winner": winner.id, "a": loser.clan_id, "b": winner.clan_id, "lethal": False, "damage": round(dmg,1)},
                )
            )
            self._bump_relation(loser.clan_id, winner.clan_id, -3)
            # §AB mutual defence on the wound path too
            self._mobilise_coalition(winner.clan_id, loser.clan_id)

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

    def _update_territory(self) -> None:
        """§P: clan territory — members prefer own ground, trespass sours relations."""
        cfg = self.config
        if not cfg.territory_enabled:
            return
        # functional claimed houses are territory anchors
        houses = [h for h in self.world.entities.values() if isinstance(h, House) and not h.is_ruin and h.clan_id != 0]
        if not houses:
            return
        # Trespass: each creature inside a rival's radius slightly sours the two clans
        r2 = cfg.territory_radius * cfg.territory_radius
        dist_sq = self.world.distance_sq
        for c in self.world.creatures():
            if not c.clan_id or c.is_predator or c.is_herbivore:
                continue
            for h in houses:
                if h.clan_id == c.clan_id:
                    continue
                if dist_sq(c.x, c.y, h.x, h.y) <= r2:
                    # probabilistic decay if <1, deterministic if >=1
                    if cfg.trespass_decay >= 1:
                        delta = -int(round(cfg.trespass_decay))
                        self._bump_relation(c.clan_id, h.clan_id, delta)
                    else:
                        if self.rng.random() < cfg.trespass_decay:
                            self._bump_relation(c.clan_id, h.clan_id, -1)
                    break  # one rival territory per tick is enough

    def _update_schism(self) -> None:
        """§S Schism — unhappy members split off as new clan and war parent."""
        cfg = self.config
        if not cfg.schism_enabled:
            return
        # One schism per tick max to keep determinism smooth
        # AA: one membership pass per tick (was a full roster scan PER CLAN).
        members_by_clan: dict[int, list[Creature]] = {}
        for c in self._get_creatures():
            if c.clan_id:
                members_by_clan.setdefault(c.clan_id, []).append(c)
        for cid, info in list(self.clans.items()):
            members = members_by_clan.get(cid, [])
            pop = len(members)
            if pop < cfg.schism_min_pop:
                continue
            # Unhappy: starving or homeless (no house)
            has_house = any(h.clan_id == cid and not h.is_ruin for h in self.world.entities.values() if isinstance(h, House))
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
                totem = TOTEMS[(new_cid * 17 + self.config.seed) % len(TOTEMS)]
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
            unaligned = [
                cid for cid in sorted(self.clans.keys())
                if cid not in self._clan_coalition and any(
                    h.clan_id == cid and not h.is_ruin
                    for h in self.world.entities.values() if isinstance(h, House)
                )
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

    def _update_leader_decisions(self) -> None:
        """§AB Leader agency — war, peace, tribute demand and betrayal surface as plots.

        God watches but never vetoes. The leader's heritable trait biases the
        hand: bold → war, peaceful → peace, paranoid → betrayal (with treason).
        """
        cfg = self.config
        if not cfg.leader_decisions_enabled:
            return
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
                                "clan_id": other or None, "ttl": 12,
                                "fact": {"kind": "enemy", "clan_id": victim,
                                         "x": round(leader.x, 2), "y": round(leader.y, 2),
                                         "conf": 1.0},
                            })
                    acted = True
                    break
            if acted:
                continue
            # Peace: a weakened leader sues a rival for peace.
            if trait == "peaceful" or pops.get(cid, 0) < 3:
                for pair, score in sorted(self.relations.items()):
                    if self._zone_of(score) != -1 or cid not in pair:
                        continue
                    rival = pair[1] if pair[0] == cid else pair[0]
                    my_pop = pops.get(cid, 0)
                    if my_pop and my_pop <= pops.get(rival, 0):
                        self.relations[pair] = min(100, score + 60)
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
                        acted = True
                        break
            if acted:
                continue
            # War: declare on a remembered enemy (bold hands, then any).
            if trait == "bold" or trait is None:
                enemy = self._remembered_enemy(cid)
                if enemy is not None and self._zone_of(
                    self.relations.get(self._relation_pair(cid, enemy), 0)
                ) != -1:
                    self._bump_relation(cid, enemy, -50)
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
        for e in self.world.entities.values():
            if isinstance(e, House) and e.clan_id and not e.is_ruin and e.clan_id not in houses_by_clan:
                houses_by_clan[e.clan_id] = e
        starving_by_clan: dict[int, int] = {}
        for c in self._get_creatures():
            if not c.clan_id or c.is_predator or c.is_herbivore:
                continue
            house = houses_by_clan.get(c.clan_id)
            if house is None:
                continue
            clan = self.clans[c.clan_id]
            ratio = c.energy / cfg.energy_max if cfg.energy_max else 1.0
            if ratio > 0.75:
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
                    take = min(3.0, stored)
                    clan["larder"] = stored - take
                    c.energy += take
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
                room = max(0.0, cfg.larder_capacity - float(pinfo.get("larder", 0.0)))
                pinfo["larder"] = float(pinfo.get("larder", 0.0)) + min(amount, room)
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
            for e in self.world.entities.values()
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

    def _update_politics(self) -> None:
        """§AB orchestrator — fixed order keeps the rng stream deterministic."""
        self._update_coalitions()
        self._update_leader_decisions()
        self._update_larders()
        self._update_defection()

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
                for e in self.world.entities.values():
                    if isinstance(e, Food) and self.world.distance(e.x, e.y, f["x"], f["y"]) < 8:
                        e.growth = min(1.0, e.growth + 0.15)
        self.fires = new_fires
        # Ignition: storm lightning or random fire_rate
        ignite_chance = cfg.fire_rate
        if self.weather == "storm":
            ignite_chance = max(ignite_chance, 0.002)  # lightning
        if self.rng.random() < ignite_chance:
            foods = [e for e in self.world.entities.values() if isinstance(e, Food) and e.growth > 0.5]
            if foods:
                victim = self.rng.choice(foods)
                self.fires.append({"x": victim.x, "y": victim.y, "r": 3.0, "ttl": 28})
                self.world.remove(victim.id)
                self._emit(HistoryEvent(type="fire", tick=self.tick+1, entity_id=0, x=round(victim.x,2), y=round(victim.y,2), payload={"kind": "ignite", "r": 3.0}))
        # Spread to neighboring plants
        if self.fires and self.rng.random() < cfg.fire_spread_rate * len(self.fires):
            for f in list(self.fires):
                for e in list(self.world.entities.values()):
                    if not isinstance(e, Food):
                        continue
                    if self.world.distance(e.x, e.y, f["x"], f["y"]) < 6 and self.rng.random() < 0.35:
                        self.fires.append({"x": e.x, "y": e.y, "r": 2.5, "ttl": 22})
                        self.world.remove(e.id)
                        break
        # Burn creatures and plants within fire radius
        for f in list(self.fires):
            for e in list(self.world.entities.values()):
                if isinstance(e, Creature) and self.world.distance(e.x, e.y, f["x"], f["y"]) < f["r"] + 1.2:
                    # chance to burn
                    if self.rng.random() < 0.18:
                        self._kill(e, "fire")
                elif isinstance(e, Food) and self.world.distance(e.x, e.y, f["x"], f["y"]) < f["r"]:
                    if self.rng.random() < 0.25:
                        self.world.remove(e.id)
            # also burn houses? small chance to ignite house (is_ruin)
            for h in [h for h in self.world.entities.values() if isinstance(h, House) and not h.is_ruin]:
                if self.world.distance(h.x, h.y, f["x"], f["y"]) < f["r"] + h.size/2:
                    if self.rng.random() < 0.03:
                        h.is_ruin = True
                        h.clan_id = 0
                        h.clan_color = None
                        self._emit(HistoryEvent(type="fire", tick=self.tick+1, entity_id=h.id, x=round(h.x,2), y=round(h.y,2), payload={"kind": "house_burn"}))

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
        for cid, info in self.clans.items():
            spec = info.get("specialization")
            if spec is None:
                spec = {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34}
                info["specialization"] = spec
            # totem bias already in founding; now environment drift
            # find clan house
            house = None
            for e in self.world.entities.values():
                if isinstance(e, House) and getattr(e, "clan_id", 0) == cid and not getattr(e, "is_ruin", False):
                    house = e
                    break
            # count recent war involvement (last 80 history)
            recent = list(self.history)[-80:]
            war_cnt = sum(1 for ev in recent if ev.type == "war" and (ev.payload.get("a")==cid or ev.payload.get("b")==cid))
            # count food/corpse near house (if has house)
            food_near = 0
            corpse_near = 0
            if house is not None:
                for e in self.world.entities.values():
                    if e.kind == "food" and self.world.distance(e.x, e.y, house.x, house.y) < 18:
                        food_near += 1
                    elif e.kind == "corpse" and self.world.distance(e.x, e.y, house.x, house.y) < 18:
                        corpse_near += 1
                # fertile patches near house also farmer
                for fp in self.fertile:
                    if self.world.distance(fp["x"], fp["y"], house.x, house.y) < 20:
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
            for k in ("warrior","farmer","scavenger"):
                spec[k] += self.rng.uniform(-0.0005, 0.0005)
                spec[k] = max(0.05, min(0.85, spec[k]))
            # renormalize to 1
            tot = spec["warrior"] + spec["farmer"] + spec["scavenger"]
            for k in spec:
                spec[k] = round(spec[k]/tot, 3)

    def clan_knowledge(self) -> dict[int, dict]:
        """§X Clan memory — union of member knowledge: 'the clan remembers'."""
        ttl = max(1, self.config.knowledge_ttl)
        out: dict[int, dict] = {}
        for cid in self.clans:
            enemies: set[int] = set()
            danger: list[dict] = []
            food: list[dict] = []
            safe_spots = 0
            for m in self.world.creatures():
                if m.clan_id != cid:
                    continue
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
            for cid, info in self.clans.items():
                members = members_by_clan.get(cid, [])
                pop = len(members)
                if pop < self.config.schism_min_pop:
                    continue
                has_house = any(
                    isinstance(h, House) and h.clan_id == cid and not h.is_ruin
                    for h in self.world.entities.values()
                )
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
        """§H: every plant grows toward maturity; the mature ones spread. §O variant rhythms. §R weather waters/damages. §AE mature plants wither."""
        cfg = self.config
        if cfg.plant_growth_rate > 0:
            for e in self.world.entities.values():
                if isinstance(e, Food) and e.growth < 1.0:
                    if cfg.plant_variants_enabled:
                        vm = VARIANT_GROWTH_MULT.get(e.variant, 1.0)
                        sm = VARIANT_SEASON_MULT.get(e.variant, {}).get(self._season(), 1.0)
                    else:
                        vm, sm = 1.0, 1.0
                    wm = 1.0
                    if self.weather in ("rain", "storm"):
                        wm = cfg.rain_growth_mult
                    elif self.weather == "fog" and e.variant == "mushroom":
                        wm = cfg.fog_mushroom_mult
                    e.growth = min(1.0, e.growth + cfg.plant_growth_rate * vm * sm * wm)
                    if e.growth >= 1.0:
                        self._emit_bloom(e)
        # §AE Food decay — a mature plant lives food_lifespan_ticks × its
        # variant's pace, wilts near the end, fertilises, then vanishes.
        # Sprouts and growing plants don't rot; only the harvest does.
        if cfg.food_decay_enabled and cfg.food_lifespan_ticks > 0:
            for e in list(self.world.entities.values()):
                if not isinstance(e, Food) or e.growth < 1.0:
                    continue
                life = max(1, round(cfg.food_lifespan_ticks * FOOD_LIFESPAN_MULT.get(e.variant, 1.0)))
                e.mature_ticks += 1
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
        # Storm damage: exposed plants stripped, occasionally uprooted (§R)
        if self.weather == "storm" and cfg.storm_plant_damage > 0:
            for e in list(self.world.entities.values()):
                if not isinstance(e, Food):
                    continue
                if self.rng.random() < cfg.storm_plant_damage:
                    e.growth = max(0.0, e.growth - self.rng.uniform(0.2, 0.5))
                    if e.growth <= 0.05 and self.rng.random() < 0.5:
                        self.world.remove(e.id)
        if cfg.plant_spread_rate > 0:
            target = round(cfg.food_count * _season_food_mult(self._season(), cfg.winter_food_mult))
            total = sum(1 for e in self.world.entities.values() if e.kind == "food")
            for parent in list(self.world.entities.values()):
                if not isinstance(parent, Food) or parent.growth < 1.0:
                    continue  # only mature plants carry seeds
                if self.rng.random() >= cfg.plant_spread_rate:
                    continue
                if total >= target:
                    continue  # the land holds exactly god's seasonal bounty
                ang = self.rng.uniform(0, 2 * math.pi)
                rad = self.rng.uniform(0, SPREAD_RADIUS)
                x, y = self.world.normalize(
                    parent.x + math.cos(ang) * rad,
                    parent.y + math.sin(ang) * rad,
                )
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
        for e in list(self.world.entities.values()):
            if isinstance(e, Corpse):
                e.ttl -= 1
                if e.ttl <= 0:
                    self._release_nutrients(e)
                    self.world.remove(e.id)

    def _release_nutrients(self, corpse: Entity, mult: float = 1.0) -> None:
        """A fully decayed corpse (or withered plant, §AE) boosts nearby plant growth."""
        boost = NUTRIENT_BOOST * self.config.nutrient_cycle_rate * mult
        if boost <= 0:
            return
        for e in self.world.entities.values():
            if not isinstance(e, Food):
                continue
            if self.world.distance(e.x, e.y, corpse.x, corpse.y) > NUTRIENT_RADIUS:
                continue
            was = e.growth
            e.growth = min(1.0, e.growth + boost)
            if was < 1.0 <= e.growth:
                self._emit_bloom(e)

    # ---------------------------------------------------------------- disease
    def _emit(self, event: HistoryEvent) -> None:
        self.history.append(event)
        self._events_this_tick.append(event)
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
            )

        males = [c for c in creatures if c.sex == "male" and eligible(c)]
        females = [c for c in creatures if c.sex == "female" and eligible(c)]
        if not males or not females:
            return

        for mother in females:
            father = None
            best = math.inf
            for m in males:
                if m.repro_cooldown > 0 or m.energy < cfg.mate_energy_min:
                    continue
                d = self.world.distance(mother.x, mother.y, m.x, m.y)
                if d <= cfg.mate_radius and d < best:
                    father, best = m, d
            if father is None:
                continue
            fert = (
                traits_for(mother.caste).fertility
                * Creature.FERTILITY_MULT[mother.stage]
                * traits_for(father.caste).fertility
                * Creature.FERTILITY_MULT[father.stage]
                * room
            )
            rate = cfg.birth_rate
            age2 = self._age()
            if age2 is not None:
                rate = min(1.0, rate * AGE_BIRTH_MULT.get(age2, 1.0))
            if self._season() == "spring":
                rate = min(1.0, rate * SPRING_BIRTH_MULT)  # spring quickens the blood
            rate *= 1.0 + self._totem_stat(mother, "birth")  # Stag/Rabbit fecundity
            if self.rng.random() >= min(rate * fert, 1.0):
                continue
            self._birth(mother, father)
            if len(self.world.creatures()) >= max_pop:
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
            # Predators don't get clan or irregularity
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
            event = HistoryEvent(
                type="birth", tick=tick, entity_id=child.id, caste=child.caste,
                x=round(child.x, 2), y=round(child.y, 2),
                payload=event_payload,
            )
            self.history.append(event)
            self._events_this_tick.append(event)
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
            event = HistoryEvent(
                type="birth", tick=tick, entity_id=child.id, caste=child.caste,
                x=round(child.x, 2), y=round(child.y, 2),
                payload=event_payload,
            )
            self.history.append(event)
            self._events_this_tick.append(event)
            if self.on_event is not None:
                self.on_event(event)
            return

        promoted = False
        if self.rng.random() < cfg.sex_ratio:
            if father.sides == 3:
                # Isosceles line: sons stay triangles, creeping toward Regular.
                sides = 3
                iso = min(60.0, father.iso_angle + 0.5)
                promoted = iso >= 60.0 and father.iso_angle < 60.0
            else:
                # Law of Nature: a son has one more side than his father.
                sides = min(father.sides + 1, cfg.max_sides)
                iso = 60.0
            irregularity = 0.0
            mut_rate = cfg.mutation_rate
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

        self.world.add(child)
        gift = self._totem_stat(child, "health")  # totem vitality: Bear/Shield cubs
        if gift:
            child.health = min(100.0, child.health + gift)
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
        self._events_this_tick.append(event)
        if self.on_event is not None:
            self.on_event(event)

        if promoted:
            pevent = HistoryEvent(
                type="promotion", tick=tick, entity_id=child.id, caste=child.caste,
                x=round(child.x, 2), y=round(child.y, 2),
                payload={"from": "Soldier", "to": "Artisan"},
            )
            self.history.append(pevent)
            self._events_this_tick.append(pevent)
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
        self._events_this_tick.append(event)
        if self.on_event is not None:
            self.on_event(event)
        # Leadership succession (§P)
        if c.clan_id and self.config.succession_enabled:
            clan = self.clans.get(c.clan_id)
            if clan and clan.get("leader_id") == c.id:
                candidates = [cc for cc in self.world.creatures() if cc.clan_id == c.clan_id]
                if candidates:
                    successor = sorted(candidates, key=lambda cc: (-cc.age, cc.id))[0]
                    clan["leader_id"] = successor.id
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

    def _update_creature(self, c: Creature, houses: list[Entity]) -> None:
        cfg, w = self.config, self.world
        c.ticks_since_meal += 1
        c.age += 1
        if c.repro_cooldown > 0:
            c.repro_cooldown -= 1
        if c.bite_cooldown > 0:
            c.bite_cooldown -= 1
        if c.cannibal_cooldown > 0:
            c.cannibal_cooldown -= 1

        # 0. Night rest: after dark, creatures make for the nearest house and
        # those who win a bed sleep — half the hunger, multiplied healing.
        # Predators cannot fit through the doorway (§L refuge).
        # Starving creatures skip sleep to forage — survival over comfort.
        c.sleeping = False
        c.indoors = False
        tod = self._time_of_day()
        # hunger check for shelter: starving creatures ignore the call of home
        ratio = c.energy / cfg.energy_max if cfg.energy_max > 0 else 1.0
        is_starving = ratio <= cfg.starving_ratio
        if (
            cfg.sleep_enabled
            and cfg.shelter_enabled
            and not c.is_predator
            and not c.is_herbivore
            and not is_starving
            and self._is_night(tod)
            and houses
        ):
            # Assigned roof (room-aware, §L); if we're not under it but stand
            # inside ANOTHER roof with a free bed, rest here instead of
            # trekking across the village. No bed ⇒ no rest: capacity is law.
            assigned = self._house_for(c, houses)
            home: House | None = None
            if assigned is not None and self._inside_house(c, assigned):
                home = assigned
            else:
                for h in houses:
                    hh = cast(House, h)
                    if self._inside_house(c, hh) and self._beds.get(hh.id, 0) < self._house_beds(hh):
                        home = hh
                        break
            if home is not None and self._claim_bed(home):
                c.indoors = True
                c.sleeping = True
                if cfg.knowledge_enabled:
                    self._learn(c, "safe", home.x, home.y)  # §X: this roof is safe
                c.energy -= cfg.energy_decay_per_tick * cfg.sleep_energy_mult
                if c.infected and cfg.disease_enabled:
                    c.energy -= cfg.disease_energy_drain
                    c.health -= 2.0 * cfg.disease_lethality
                else:
                    regen = 0.15 * cfg.rest_recovery_mult
                    regen *= 1.0 + self._totem_stat(c, "defense")  # totem vitality heals faster
                    c.health = min(100.0, c.health + regen)
                if c.energy <= 0:
                    self._kill(c, "starvation")
                elif c.health <= 0:
                    self._kill(c, "disease")
                elif c.age >= c.lifespan:
                    self._kill(c, "old_age")
                # Asleep means STILL: no steering, no wandering, no fleeing —
                # the body does not move again until dawn (or death).
                return

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
            self._events_this_tick.append(event)
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
        perceive = cfg.perceive_radius * c.sight_mult * stage_sight * self.env_sight_mult()
        # Totem sight (§P): Eye +25%, Owl +35%, Raven +15% …
        perceive *= 1.0 + self._totem_stat(c, "sight")
        speed_mult = 1.0
        if c.status == "hungry":
            perceive *= cfg.hungry_perceive_mult
        elif c.status == "starving":
            perceive *= cfg.desperate_perceive_mult
            speed_mult = cfg.desperate_speed_mult
        # Totem speed: hunting/fleeing burst (Wolf, Stag, Fox, Serpent …)
        if self._totem_of(c) and (c.is_predator or perceive > cfg.perceive_radius):
            speed_mult *= 1.0 + self._totem_stat(c, "speed")

        # trait paranoid/bold nudges flee threshold (§S)
        # paranoid sees predator farther, bold tolerates closer
        fear_radius_eff = cfg.fear_radius
        if c.trait == "paranoid":
            fear_radius_eff += 4.0
        elif c.trait == "bold":
            fear_radius_eff = max(2.0, fear_radius_eff - 2.5)
        # 1. Predation: hunt (predator) / flee (prey) — highest priority after sleep
        hunt_target: Creature | None = None
        flee_target: Creature | None = None
        if cfg.predation_enabled:
            if c.is_predator and c.bite_cooldown <= 0:
                # Find nearest non-predator prey within hunt_radius (+2 Wolf totem)
                hunt_r = cfg.hunt_radius + self._totem_stat(c, "hunt_radius")
                best_prey: Creature | None = None
                best_prey_d = hunt_r + 1e-9
                for o in w.query_radius(c.x, c.y, hunt_r):
                    if not isinstance(o, Creature) or o.id == c.id or o.is_predator:
                        continue
                    if o.id not in w.entities or o.indoors:
                        continue  # indoors prey are safe (predator refuge)
                    d = w.distance(c.x, c.y, o.x, o.y)
                    if d < best_prey_d:
                        best_prey_d, best_prey = d, o
                if best_prey is not None:
                    if best_prey_d <= cfg.eat_radius:
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
            elif not c.is_predator:
                # Find nearest predator within fear_radius to flee from
                best_pred: Creature | None = None
                best_pred_d = fear_radius_eff + 1e-9
                for o in w.query_radius(c.x, c.y, fear_radius_eff):
                    if not isinstance(o, Creature) or not o.is_predator:
                        continue
                    if o.id not in w.entities:
                        continue
                    d = w.distance(c.x, c.y, o.x, o.y)
                    if d < best_pred_d:
                        best_pred_d, best_pred = d, o
                flee_target = best_pred

        # 2. Perceive the nearest meal — food or the fallen. Diet strictness (§O) filters.
        target: Entity | None = None
        best = math.inf
        for e in w.query_radius(c.x, c.y, perceive):
            if e.kind not in ("food", "corpse") or e.id in self._eaten:
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
                        # peek if a berry/mushroom is also within perceive — if so, ignore grass
                        # (cheaper than full scan: just skip grass with 70% chance when strict)
                        if self.rng.random() < 0.7:
                            continue
                # herbivores avoid poisonous when strict
                if c.is_herbivore and isinstance(e, Food) and e.variant == "poisonous" and cfg.diet_strictness > 0.3:
                    if self.rng.random() < cfg.diet_strictness:
                        continue
                # trait greedy: prefer richer food (berry/corpse) over grass
                if c.trait == "greedy" and isinstance(e, Food) and e.variant == "grass":
                    if self.rng.random() < 0.45:
                        continue
            d = w.distance(c.x, c.y, e.x, e.y)
            if d < best:
                best, target = d, e  # type: ignore[assignment]

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
                home_fact = self._house_for(c, houses) if houses else None
                if home_fact is not None:
                    self._learn(c, "safe", home_fact.x, home_fact.y)
        if c.signal_cooldown > 0:
            c.signal_cooldown -= 1
        # §Q Communication — food and alarm calls
        if cfg.communication_enabled:
            # Food call: well-fed finds food → calls clan-mates
            if target is not None and c.energy / cfg.energy_max > cfg.hungry_ratio and c.signal_cooldown == 0:
                if self.rng.random() < cfg.food_call_rate:
                    self.signals.append({"x": c.x, "y": c.y, "kind": "food", "sender": c.id, "clan_id": c.clan_id or None, "ttl": 15, "food_x": target.x, "food_y": target.y})
                    c.signal_cooldown = 8
            # Alarm call: sees predator → alarm; teeth-close → a cry for help (§X)
            if flee_target is not None and c.signal_cooldown == 0:
                close = (
                    cfg.help_call_enabled
                    and cfg.knowledge_enabled
                    and w.distance(c.x, c.y, flee_target.x, flee_target.y) < cfg.help_radius * 0.6
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
                    self.signals.append({"x": c.x, "y": c.y, "kind": "knowledge", "sender": c.id, "clan_id": c.clan_id or None, "ttl": 12, "fact": fact_msg})
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
                        self.signals.append({"x": c.x, "y": c.y, "kind": "food", "sender": c.id, "clan_id": c.clan_id or None, "ttl": 12, "food_x": remembered_food[0], "food_y": remembered_food[1]})
                        c.signal_cooldown = 12
                        break

        # 3. Steer — priority: flee > hunt > home for night > food > wander
        # §Q Hearing signals — clan-mates respond strongly; §X knowledge & help
        signal_food_target = None
        signal_alarm_target = None
        signal_help_target = None
        best_help_d = math.inf
        if cfg.communication_enabled and self.signals:
            best_food = math.inf
            best_alarm = math.inf
            for sg in self.signals:
                d = w.distance(c.x, c.y, sg["x"], sg["y"])
                if d > cfg.signal_radius:
                    continue
                # clan weighting: clan-mates 1.0, strangers 0.35
                is_kin = sg.get("clan_id") and sg.get("clan_id") == c.clan_id
                if not is_kin and self.rng.random() < 0.65:
                    continue
                if sg["kind"] == "food" and c.status in ("hungry", "starving"):
                    # food signal points to food_x/food_y if present, else sender pos
                    fx = sg.get("food_x", sg["x"])
                    fy = sg.get("food_y", sg["y"])
                    df = w.distance(c.x, c.y, fx, fy)
                    if df < best_food:
                        best_food = df
                        signal_food_target = (fx, fy)
                elif sg["kind"] == "knowledge" and cfg.knowledge_enabled:
                    self._hear_fact(c, sg.get("fact"))
                    fact_kind = (sg.get("fact") or {}).get("kind")
                    f = (sg.get("fact") or {})
                    if (
                        fact_kind == "food"
                        and c.status in ("hungry", "starving")
                        and signal_food_target is None
                    ):
                        df = w.distance(c.x, c.y, f.get("x", sg["x"]), f.get("y", sg["y"]))
                        if df < best_food:
                            best_food = df
                            signal_food_target = (f.get("x", sg["x"]), f.get("y", sg["y"]))
                elif sg["kind"] == "help" and cfg.help_call_enabled and is_kin:
                    # §X Mobbing: rally to the defender's aid — warriors first,
                    # the peaceful lag behind, high castes only when bold.
                    rank = YIELD_RANK.get(c.caste, 3)
                    if rank >= 5 and c.trait != "bold":
                        continue
                    if c.trait == "peaceful" and self.rng.random() < 0.7:
                        continue
                    if not c.is_predator and not c.is_herbivore and d < best_help_d:
                        best_help_d = d
                        signal_help_target = (sg.get("threat_x", sg["x"]), sg.get("threat_y", sg["y"]))
                elif sg["kind"] == "alarm" and flee_target is None:
                    if d < best_alarm:
                        best_alarm = d
                        signal_alarm_target = sg
        # §X Danger zones: remembered predator sightings are avoided on sight of memory
        danger_avoid_target = None
        if cfg.knowledge_enabled and flee_target is None and c.status != "":
            danger_fact = self._fact_fresh(c, "danger")
            if danger_fact is not None and "x" in danger_fact:
                dd = w.distance(c.x, c.y, danger_fact["x"], danger_fact["y"])
                if dd < cfg.fear_radius * 1.5:
                    danger_avoid_target = (danger_fact["x"], danger_fact["y"])
        if flee_target is not None:
            # Prey flees directly away from predator (with extra urgency when starving)
            dx, dy = w.delta(c.x, c.y, flee_target.x, flee_target.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            # Flee is more urgent than normal steering
            c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
        elif signal_alarm_target is not None:
            # Alarm call: flee even without seeing predator (clan awareness)
            dx, dy = w.delta(c.x, c.y, signal_alarm_target["x"], signal_alarm_target["y"])
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
        elif signal_help_target is not None:
            # §X Mobbing: converge on the attacker threatening a clan-mate
            hx, hy = signal_help_target
            dx, dy = w.delta(hx, hy, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
        elif danger_avoid_target is not None:
            # §X steer away from a remembered danger zone
            gx, gy = danger_avoid_target
            dx, dy = w.delta(c.x, c.y, gx, gy)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn * 0.6, min(cfg.steer_turn * 0.6, diff))
        elif hunt_target is not None:
            dx, dy = w.delta(hunt_target.x, hunt_target.y, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
        elif prey_target is not None:
            # §AC: desperation outranks plants and calls — close on living prey
            dx, dy = w.delta(prey_target.x, prey_target.y, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn * 1.1, min(cfg.steer_turn * 1.1, diff))
        elif signal_food_target is not None and target is None:
            # Hungry follows clan-mate food call toward remembered food
            fx, fy = signal_food_target
            dx, dy = w.delta(fx, fy, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
        elif cfg.sleep_enabled and not c.is_predator and not c.is_herbivore and self._is_night(self._time_of_day()) and houses:
            home = self._house_for(c, houses)
            if home is None:
                home = min(houses, key=lambda h: w.distance(c.x, c.y, h.x, h.y))
            # Edge-follow door seek: slide along the near wall to the gap
            # instead of bumping the centre and grinding at the wall face.
            if self._inside_house(c, home):
                tx, ty = home.x, home.y
            else:
                tx, ty = self._house_entry_target(c, home)
            dx, dy = w.delta(tx, ty, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
        elif target is not None:
            dx, dy = w.delta(target.x, target.y, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            step = max(-cfg.steer_turn, min(cfg.steer_turn, diff))
            c.angle += step
        else:
            wander = cfg.wander_turn
            if self.weather == "storm":
                wander += cfg.storm_wander_bonus  # storms fling the lost about
            c.angle += self.rng.uniform(-wander, wander)

        # 2b. Social yielding: the lowly give way to their betters.
        my_rank = YIELD_RANK.get(c.caste, 0)
        if my_rank < 6:
            for o in w.query_radius(c.x, c.y, YIELD_RADIUS):
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
            for o in w.query_radius(c.x, c.y, cfg.flock_radius):
                if not isinstance(o, Creature) or o.id == c.id:
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
            own_house = None
            for h in houses:
                if isinstance(h, House) and h.clan_id == c.clan_id and not h.is_ruin:
                    own_house = h
                    break
            if own_house is not None:
                dist_home = w.distance(c.x, c.y, own_house.x, own_house.y)
                if dist_home > cfg.territory_radius:
                    dx, dy = w.delta(own_house.x, own_house.y, c.x, c.y)
                    desired = math.atan2(dy, dx)
                    diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
                    cap = cfg.steer_turn * 0.35
                    c.angle += max(-cap, min(cap, diff))

        # 3. Move (hunger speeds up the desperate; rain slows every body).
        step_len = c.speed * speed_mult * stage_speed * self.env_speed_mult()
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

        # 4. House walls block movement except through the doorway.
        # The doorway is too small for the Carnivore caste (§L refuge) — predators see a closed wall.
        mdx, mdy = w.delta(c.x, c.y, px, py)
        was_blocked = False
        if math.hypot(mdx, mdy) <= step_len * 1.5:  # skip wrap teleports
            for h in houses:
                assert isinstance(h, House)
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
                        # wedged (narrow alley/door shadow): a plain about-face just
                        # bounces back — try a fresh random heading to break out
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
            for h in houses:
                assert isinstance(h, House)
                if self._inside_house(c, h):
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
        # crosses the stone is abandoned — give up and look somewhere else.
        if self.rocks:
            hit_rock = self._resolve_rock_collision(c)
            if hit_rock is not None and target is not None and cfg.food_giveup_ticks > 0:
                if self._segment_hits_circle(c.x, c.y, target.x, target.y, hit_rock, pad=c.radius):
                    self._give_up_on(c, target)

        # 4c. §AC Desperation fulfilled: prey within reach is killed and eaten.
        if (
            prey_target is not None
            and prey_target.id in w.entities
            and c.id in w.entities
            and w.distance(c.x, c.y, prey_target.x, prey_target.y) <= cfg.eat_radius
        ):
            self._do_cannibalism(c, prey_target)
            if c.id not in w.entities:  # a kin-eater may have been exiled (still alive)
                return

        # 5. Eat. §O variant yields: grass low, berry high (autumn), mushroom decomposer, poisonous sickens.
        if target is not None and best <= cfg.eat_radius:
            w.remove(target.id)
            self._eaten.add(target.id)
            c.ticks_since_meal = 0
            c.meals += 1
            c.give_ups.clear()  # fed: old grudges against unreachable food fade
            self._eaters_this_tick.append(c.id)
            gain = cfg.energy_from_food
            health_delta = 0.0
            if isinstance(target, Food):
                if cfg.plant_variants_enabled:
                    base = VARIANT_ENERGY.get(target.variant, cfg.energy_from_food)
                    gain = base * target.growth  # immature plants feed proportionally less
                    health_delta = VARIANT_HEALTH.get(target.variant, 0.0)
                else:
                    gain = cfg.energy_from_food * target.growth
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
            c.energy = min(cfg.energy_max, c.energy + gain)
            if health_delta != 0:
                c.health = max(0.0, min(100.0, c.health + health_delta))
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
            home = self._house_for(c, houses)
            if self._inside_house(c, home) and self._claim_bed(home):
                c.indoors = True
                if cfg.knowledge_enabled:
                    self._learn(c, "safe", home.x, home.y)  # §X: shelter from the rain

        # 6. Metabolism, sickness and mortality. §R chill builds when cold & wet
        c.energy -= cfg.energy_decay_per_tick
        if (
            cfg.shelter_enabled
            and not c.indoors
            and (self._is_night(tod) or self.weather in ("rain", "storm"))
        ):
            c.energy -= cfg.exposure_drain
        # §R Chill — Ice age chills deeper (§S)
        if cfg.weather_sickness_enabled:
            is_wet = self.weather in ("rain", "storm")
            is_winter_night = self._season() == "winter" and self._is_night(tod)
            age = self._age()
            chill_mult = 1.4 if age == "Ice" else 1.0
            if not c.indoors and (is_wet or is_winter_night):
                c.chill = min(cfg.chill_threshold * 2, c.chill + cfg.chill_rate * chill_mult)
            else:
                shed = cfg.chill_rate * (2.5 if c.indoors else 1.0) * (0.8 if age == "Ice" else 1.0)
                c.chill = max(0.0, c.chill - shed)
            if c.chill >= cfg.chill_threshold:
                c.health -= cfg.chill_drain * (1.2 if age == "Ice" else 1.0)
                if c.health <= 0:
                    self._kill(c, "chill")
                    return
        else:
            c.chill = max(0.0, c.chill - 0.05)
        if cfg.disease_enabled and c.infected:
            c.energy -= cfg.disease_energy_drain
            c.health -= 2.0 * cfg.disease_lethality
            if c.health <= 0:
                self._kill(c, "disease")
                return
        elif c.health < 100.0:
            regen = 0.1 * (1.0 + self._totem_stat(c, "defense"))
            c.health = min(100.0, c.health + regen)
        if c.energy <= 0:
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
        foods = [e for e in self.world.entities.values() if e.kind == "food"]
        deficit = target - len(foods)
        if deficit > 0:
            for _ in range(deficit):
                x, y = self._food_pos()
                # Law-respawned food also arrives mature; only SPREAD sprouts young.
                self.world.add(self._new_food(x, y, growth=1.0))
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

    def snapshot_payload(self) -> dict:
        """AA: the broadcast payload as plain dicts — no pydantic validation
        and no model_dump on the hot path. Shared nested structures are copied,
        so the payload stays valid while the world keeps ticking."""
        cfg = self.config
        entities: list[dict] = []
        population: dict[str, int] = {}
        alive = 0
        infected = 0
        for e in sorted(self.world.entities.values(), key=lambda e: e.id):
            entities.append(self._entity_payload(e))
            if isinstance(e, Creature):
                label = e.caste
                alive += 1
                if e.infected:
                    infected += 1
            else:
                label = e.kind.capitalize()
            population[label] = population.get(label, 0) + 1
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
            "terrain_fertile": [dict(p) for p in self.fertile],
            "terrain_rocks": [dict(r) for r in self.rocks],
            "relations": [
                {"a": a, "b": b, "score": s}
                for (a, b), s in sorted(self.relations.items())
            ],
            "clans": {
                str(k): {kk: (dict(vv) if isinstance(vv, dict) else vv) for kk, vv in v.items()}
                for k, v in self.clans.items()
            },
            "events": [ev.model_dump(mode="json") for ev in self._events_this_tick],
            "signals": [dict(sg) for sg in self.signals],
            "fires": [dict(f) for f in self.fires],
            "age": self._age(),
            "age_tick": self._age_tick(),
        }

    def snapshot(self) -> StateMessage:
        """Typed snapshot for cold paths (REST /api/state, tests)."""
        return StateMessage.model_validate(self.snapshot_payload())

    def _entity_payload(self, e: Entity) -> dict:
        base: dict = {
            "id": e.id,
            "kind": e.kind,
            "x": round(e.x, 3),
            "y": round(e.y, 3),
            "angle": round(e.angle, 4),
        }
        if isinstance(e, Creature):
            name, glyph, hue_shift, scale_jitter, angle_jitter = self._cached_identity(
                e.id, e.generation
            )
            base.update(
                shape=e.shape,
                sides=e.sides,
                caste=e.caste,
                energy=round(e.energy, 2),
                status=e.status,
                radius=round(e.radius, 3),
                age=e.age,
                lifespan=round(e.lifespan, 1),
                stage=e.stage,
                irregularity=e.irregularity,
                health=round(e.health, 1),
                infected=e.infected,
                sex=e.sex,
                mother_id=e.mother_id or None,
                father_id=e.father_id or None,
                clan_id=e.clan_id or None,
                clan_color=self.clans.get(e.clan_id, {}).get("color"),
                clan_name=self.clans.get(e.clan_id, {}).get("name"),
                is_predator=e.is_predator or None,
                is_herbivore=e.is_herbivore or None,
                sleeping=e.sleeping,
                indoors=e.indoors,
                generation=e.generation,
                born_tick=e.born_tick,
                personal_name=name,
                glyph=glyph,
                hue_shift=hue_shift,
                scale_jitter=scale_jitter,
                angle_jitter=angle_jitter,
                chill=round(e.chill, 2),
                trait=e.trait,
            )
            return base
        if isinstance(e, House):
            base.update(
                size=round(e.size, 2),
                door_width=round(e.door_width, 2),
                door_offset=round(e.door_offset, 2),
                door_side=e.door_side,
                clan_id=e.clan_id or None,
                clan_color=e.clan_color,
                is_ruin=e.is_ruin or None,
                abandoned_ticks=e.abandoned_ticks or None,
            )
            return base
        if isinstance(e, Food):
            base.update(growth=round(e.growth, 3), variant=e.variant)
            if (
                self.config.food_decay_enabled
                and e.growth >= 1.0
                and e.mature_ticks
                >= WILT_FRACTION
                * max(1, round(self.config.food_lifespan_ticks * FOOD_LIFESPAN_MULT.get(e.variant, 1.0)))
            ):
                base["withering"] = True
            return base
        return base

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
    half = h.size / 2
    if (
        max(px, qx) < h.x - half
        or min(px, qx) > h.x + half
        or max(py, qy) < h.y - half
        or min(py, qy) > h.y + half
    ):
        return False
    path = ((px, py), (qx, qy))
    segments = _house_wall_segments_closed(h) if predator_blocked else _house_wall_segments(h)
    return any(
        segments_intersect(path[0], path[1], a, b)
        for a, b in segments
    )
