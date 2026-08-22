"""Deterministic fixed-tick simulation of Flatland."""

import math
import random
from collections import deque
from typing import Callable

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
# Winter starves the land; summer is plenty.
SEASON_FOOD_MULT = {"spring": 1.0, "summer": 1.2, "autumn": 1.0, "winter": 0.5}
SPRING_BIRTH_MULT = 1.25
WINTER_DISEASE_MULT = 1.5
WEATHER_STATES = ("clear", "rain", "fog", "storm")

YIELD_RADIUS = 2.5  # lower castes step aside within this range

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
        self._death_counts: dict[str, int] = {}
        self.disease_id = 0
        self.weather = "clear"
        self.clans: dict[int, dict] = {}  # id -> {name, founder_id, born_tick, color}
        self._next_clan_id = 1
        self.relations: dict[tuple[int, int], int] = {}  # clan pair -> -100..100
        self._relation_zones: dict[tuple[int, int], int] = {}  # last seen zone
        self._eaters_this_tick: list[int] = []
        self.fertile: list[dict] = []  # {x,y,r} — food prefers these grounds
        self.rocks: list[dict] = []  # {x,y,r} — solid circles that block movement
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
        if taken >= max(0, self.config.house_capacity):
            return False
        self._beds[house.id] = taken + 1
        return True

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

    def _found_clan(self, founder: Creature) -> int:
        cid = self._next_clan_id
        self._next_clan_id += 1
        # Procedural name: deterministic adj+noun from seed+cid (no rng consumption to keep determinism)
        adj = CLAN_ADJECTIVES[(cid * 13 + self.config.seed) % len(CLAN_ADJECTIVES)]
        noun = CLAN_NOUNS[(cid * 29 + self.config.seed) % len(CLAN_NOUNS)]
        if (cid * 7 + self.config.seed) % 10 < 3:
            name = f"Clan of the {adj} {noun}"
        else:
            name = f"{adj} {noun}"
        self.clans[cid] = {
            "name": name,
            "founder_id": founder.id,
            "born_tick": self.tick,
            "color": CLAN_COLORS[(cid - 1) % len(CLAN_COLORS)],
        }
        if self.config.house_claim_enabled:
            self._claim_house_for_clan(cid)
        return cid

    def _found_founding_clans(self) -> None:
        """The founding generation seeds one clan per caste."""
        by_caste: dict[str, Creature] = {}
        for c in self.world.creatures():
            by_caste.setdefault(c.caste, c)
        for caste, first in sorted(by_caste.items()):
            cid = self._found_clan(first)
            for c in self.world.creatures():
                if c.caste == caste:
                    c.clan_id = cid
        self._assign_house_claims()

    def _assign_house_claims(self) -> None:
        """Each clan claims a distinct house as its settlement (distinct if enough houses)."""
        if not self.config.house_claim_enabled:
            return
        houses = sorted(
            [e for e in self.world.entities.values() if isinstance(e, House) and not e.is_ruin],
            key=lambda h: h.id,
        )
        if not houses:
            return
        # Clear stale claims from previous world generation / disabled period
        for h in houses:
            if h.clan_id and h.clan_id not in self.clans:
                h.clan_id = 0
                h.clan_color = None
        # Assign each unclaimed clan a free house round-robin
        free = [h for h in houses if h.clan_id == 0]
        for cid in sorted(self.clans.keys()):
            if any(h.clan_id == cid for h in houses):
                continue  # already has a settlement
            if not free:
                break  # housing shortage: some clans remain homeless
            h = free.pop(0)
            h.clan_id = cid
            h.clan_color = self.clans[cid]["color"]

    def _claim_house_for_clan(self, clan_id: int) -> None:
        """Give a newly founded clan the first free house, if any — or found a new one."""
        if not self.config.house_claim_enabled:
            return
        houses = sorted(
            [e for e in self.world.entities.values() if isinstance(e, House) and not e.is_ruin],
            key=lambda h: h.id,
        )
        for h in houses:
            if h.clan_id == 0:
                h.clan_id = clan_id
                h.clan_color = self.clans[clan_id]["color"]
                return
        # No free house: a new clan founds a new settlement (§L settlement economy)
        # But respect explicit overrides: tests/scenarios that pin num_houses keep housing shortage
        if self.config.shelter_enabled and self.config.num_houses < 0:
            founder = None
            for c in self.world.creatures():
                if c.clan_id == clan_id:
                    founder = c
                    break
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
        # scale with carrying_capacity; default 80 → factor 1.0
        factor = cfg.carrying_capacity / 80.0 if 80 else 1.0
        target = round(base * factor)
        # also ensure at least enough beds for ~60% of the carrying capacity
        cap_based = round(cfg.carrying_capacity / max(1, cfg.house_capacity) * 0.6)
        target = max(target, cap_based)
        return max(1, target)

    def _spawn_settlement_house(self, clan_id: int | None = None, near: Creature | None = None) -> House:
        """Spawn a new house — near a clan founder if given, else random; claim it if clan_id."""
        cfg = self.config
        max_radius = max(
            (c.radius for c in self.world.creatures()), default=DEFAULT_RADIUS
        )
        size = self.rng.uniform(cfg.house_min_size, cfg.house_max_size)
        if near is not None:
            # scatter near founder but keep inside world
            x = (near.x + self.rng.uniform(-12, 12)) % cfg.width
            y = (near.y + self.rng.uniform(-12, 12)) % cfg.height
            # keep whole house inside clamp? we use normalize wrap path, so just clamp margin
            x = max(size / 2, min(cfg.width - size / 2, x))
            y = max(size / 2, min(cfg.height - size / 2, y))
        else:
            x, y = self._rand_house_pos(size)
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
        """Preferred shelter: clan's claimed house if enabled, else nearest."""
        if not houses:
            return None
        if self.config.house_claim_enabled and c.clan_id:
            for h in houses:
                if isinstance(h, House) and h.clan_id == c.clan_id:
                    return h  # type: ignore[return-value]
        # Fall back to nearest house by wrap-aware distance
        return min(houses, key=lambda h: self.world.distance(c.x, c.y, h.x, h.y))  # type: ignore[arg-type]

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

    def _resolve_rock_collision(self, c: Creature) -> None:
        """Push a creature out of any rock it has wandered into."""
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

    def _jittered(self, target: float) -> int:
        v = self.config.spawn_variance
        return max(0, round(self.rng.uniform(target * (1 - v), target * (1 + v))))

    def _count(self, override: int, share: float, total: int) -> int:
        """Explicit override wins; otherwise take this caste's slice of the pyramid."""
        if override >= 0:
            return override
        return max(0, round(total * share))

    def _rand_house_pos(self, size: float) -> tuple[float, float]:
        """Position keeping the whole house inside the world edge."""
        cfg = self.config
        margin = size / 2
        return (
            self.rng.uniform(margin, max(margin, cfg.width - margin)),
            self.rng.uniform(margin, max(margin, cfg.height - margin)),
        )

    # ------------------------------------------------------------------ tick
    def step(self) -> None:
        """Advance the world by exactly one tick (deterministic)."""
        self._eaten.clear()
        self._beds.clear()  # beds are re-contested every tick, in id order
        self._events_this_tick = []
        self._eaters_this_tick = []
        self._update_weather()
        self._update_plants()
        self.world.rebuild_index()
        houses = [e for e in self.world.entities.values() if e.kind == "house" and not e.is_ruin]  # type: ignore[union-attr]
        for creature in self.world.creatures():  # snapshot list; removals are safe
            self._update_creature(creature, houses)
        self._update_disease()
        self._update_war()
        self._reproduce()
        self._update_relations()
        self._update_territory()
        self._enforce_food_law()
        self._update_corpses()
        self._update_settlements()
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

    def _update_war(self) -> None:
        """Rival-clan creatures fight on contact (§I)."""
        cfg = self.config
        if not cfg.war_enabled:
            return
        # Collect rival pairs first (deterministic order by id)
        creatures = sorted(self.world.creatures(), key=lambda c: c.id)
        to_kill: list[tuple[Creature, Creature]] = []
        for i, a in enumerate(creatures):
            if a.id not in self.world.entities:
                continue
            if a.is_predator or a.is_herbivore:
                continue
            for b in creatures[i + 1 :]:
                if b.id not in self.world.entities or b.is_predator or b.is_herbivore:
                    continue
                if not a.clan_id or not b.clan_id or a.clan_id == b.clan_id:
                    continue
                pair = self._relation_pair(a.clan_id, b.clan_id)
                if self._zone_of(self.relations.get(pair, 0)) != -1:
                    continue  # not rivals
                if self.world.distance(a.x, a.y, b.x, b.y) > cfg.attack_radius:
                    continue
                # Deterministic loser: lower id dies (no extra RNG)
                loser, winner = (a, b) if a.id < b.id else (b, a)
                # avoid double-kill in same tick
                if any(loser.id == x[0].id for x in to_kill) or any(winner.id == x[0].id for x in to_kill):
                    continue
                to_kill.append((loser, winner))
        for loser, winner in to_kill:
            if loser.id not in self.world.entities:
                continue
            self._kill(loser, "war")
            self._emit(
                HistoryEvent(
                    type="war",
                    tick=self.tick + 1,
                    entity_id=loser.id,
                    caste=loser.caste,
                    x=round(loser.x, 2),
                    y=round(loser.y, 2),
                    payload={"winner": winner.id, "a": loser.clan_id, "b": winner.clan_id},
                )
            )
            self._bump_relation(loser.clan_id, winner.clan_id, -5)

    def _update_relations(self) -> None:
        """Clan scores rise when strangers feast together and drift toward peace."""
        cfg = self.config

        # Old zones are what the chronicle last saw (neutral for unseen pairs).
        old_zones: dict[tuple[int, int], int] = dict(self._relation_zones)

        eaters = sorted(self._eaters_this_tick)
        for i, aid in enumerate(eaters):
            ea = self.world.entities.get(aid)
            for bid in eaters[i + 1:]:
                eb = self.world.entities.get(bid)
                if ea is None or eb is None or not isinstance(ea, Creature) or not isinstance(eb, Creature):
                    continue
                if not ea.clan_id or not eb.clan_id or ea.clan_id == eb.clan_id:
                    continue
                if self.world.distance(ea.x, ea.y, eb.x, eb.y) <= cfg.flock_radius:
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
            self._relation_zones[pair] = new_zone

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
        for c in self.world.creatures():
            if not c.clan_id or c.is_predator or c.is_herbivore:
                continue
            for h in houses:
                if h.clan_id == c.clan_id:
                    continue
                if self.world.distance(c.x, c.y, h.x, h.y) <= cfg.territory_radius:
                    # probabilistic decay if <1, deterministic if >=1
                    if cfg.trespass_decay >= 1:
                        delta = -int(round(cfg.trespass_decay))
                        self._bump_relation(c.clan_id, h.clan_id, delta)
                    else:
                        if self.rng.random() < cfg.trespass_decay:
                            self._bump_relation(c.clan_id, h.clan_id, -1)
                    break  # one rival territory per tick is enough

    # ------------------------------------------------------------------ flora
    def _update_plants(self) -> None:
        """§H: every plant grows toward maturity; the mature ones spread. §O variant rhythms."""
        cfg = self.config
        if cfg.plant_growth_rate > 0:
            for e in self.world.entities.values():
                if isinstance(e, Food) and e.growth < 1.0:
                    if cfg.plant_variants_enabled:
                        vm = VARIANT_GROWTH_MULT.get(e.variant, 1.0)
                        sm = VARIANT_SEASON_MULT.get(e.variant, {}).get(self._season(), 1.0)
                    else:
                        vm, sm = 1.0, 1.0
                    e.growth = min(1.0, e.growth + cfg.plant_growth_rate * vm * sm)
                    if e.growth >= 1.0:
                        self._emit_bloom(e)
        if cfg.plant_spread_rate > 0:
            target = round(cfg.food_count * SEASON_FOOD_MULT[self._season()])
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

    def _release_nutrients(self, corpse: Corpse) -> None:
        """A fully decayed corpse boosts nearby plant growth instantly."""
        boost = NUTRIENT_BOOST * self.config.nutrient_cycle_rate
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
        creatures = self.world.creatures()
        active = [c for c in creatures if c.infected]

        if (
            not any(c.infected for c in creatures)
            and creatures
            and self.rng.random()
            < cfg.disease_outbreak_rate
            * (WINTER_DISEASE_MULT if self._season() == "winter" else 1.0)
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
            # Recovery
            if cfg.recovery_rate > 0 and self.rng.random() < cfg.recovery_rate:
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
            # Contagion to healthy neighbours (winter air carries further)
            spread_rate = cfg.disease_rate * (
                WINTER_DISEASE_MULT if self._season() == "winter" else 1.0
            )
            for n in self.world.query_radius(c.x, c.y, cfg.disease_radius):
                if n.kind == "creature" and not n.infected and n.id != c.id:
                    if self.rng.random() < min(spread_rate, 1.0):
                        self._infect(n)  # type: ignore[arg-type]

    # ----------------------------------------------------------- reproduction
    def _reproduce(self) -> None:
        """Nature's Law: eligible pairs may beget children; god only sets rates."""
        cfg = self.config
        if not cfg.birth_enabled:
            return
        creatures = self.world.creatures()
        pop = len(creatures)
        if pop >= cfg.max_population:
            return
        room = 1.0  # fertility fades as the world crowds past carrying capacity
        if pop > cfg.carrying_capacity:
            gap = max(1.0, cfg.max_population - cfg.carrying_capacity)
            room = max(0.0, 1.0 - (pop - cfg.carrying_capacity) / gap)

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
            if self._season() == "spring":
                rate = min(1.0, rate * SPRING_BIRTH_MULT)  # spring quickens the blood
            if self.rng.random() >= min(rate * fert, 1.0):
                continue
            self._birth(mother, father)
            if len(self.world.creatures()) >= cfg.max_population:
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
            )
            # Predators don't get clan or irregularity
            self.world.add(child)
            event_payload = {
                "mother": mother.id, "father": father.id,
                "sides": child.sides, "generation": gen, "sex": child.sex,
                "clan_id": 0, "is_predator": True,
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
            child = Creature(
                shape="polygon", sides=4, iso_angle=60.0,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for("Herbivore").lifespan * cfg.lifespan_mult,
                is_herbivore=True,
                caste="Herbivore",
                clan_id=0,
            )
            self.world.add(child)
            event_payload = {
                "mother": mother.id, "father": father.id,
                "sides": child.sides, "generation": gen, "sex": child.sex,
                "clan_id": 0, "is_herbivore": True,
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
            if self.rng.random() < cfg.mutation_rate:
                # A deformed child: sides deviate AND the irregularity is scored.
                sides = min(cfg.max_sides, max(3, sides + self.rng.choice((-1, 1))))
                if sides != 3:
                    promoted = False
                irregularity = round(self.rng.uniform(0.3, 1.0), 3)
            caste = caste_name(sides, "polygon", iso)
            child = Creature(
                shape="polygon", sides=sides, iso_angle=iso,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for(caste).lifespan * cfg.lifespan_mult,
                irregularity=irregularity,
            )
        else:
            child = Creature(
                shape="line", sides=2,
                x=x, y=y, angle=self.rng.uniform(0, 2 * math.pi),
                energy=cfg.energy_start, generation=gen, born_tick=tick,
                mother_id=mother.id, father_id=father.id,
                lifespan=traits_for("Woman").lifespan * cfg.lifespan_mult,
            )

        self.world.add(child)
        if child.clan_id == 0:
            # Children belong to their mother's clan; orphans found new ones.
            child.clan_id = mother.clan_id or father.clan_id or self._found_clan(child)
        event_payload = {
            "mother": mother.id, "father": father.id,
            "sides": child.sides, "generation": gen, "sex": child.sex,
            "clan_id": child.clan_id,
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

    def _kill(self, c: Creature, cause: str) -> None:
        """Remove a creature from the world and record it in the chronicle."""
        self.world.remove(c.id)
        if self.config.corpses_enabled:
            self.world.add(
                Corpse(x=c.x, y=c.y, ttl=self.config.corpse_ttl,
                       energy=self.config.corpse_energy)
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
        )
        self.history.append(event)
        self._events_this_tick.append(event)
        if self.on_event is not None:
            self.on_event(event)

    def _update_creature(self, c: Creature, houses: list[Entity]) -> None:
        cfg, w = self.config, self.world
        c.ticks_since_meal += 1
        c.age += 1
        if c.repro_cooldown > 0:
            c.repro_cooldown -= 1
        if c.bite_cooldown > 0:
            c.bite_cooldown -= 1

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
            home = self._house_for(c, houses)
            inside = (
                abs(c.x - home.x) < home.size / 2 - 0.3
                and abs(c.y - home.y) < home.size / 2 - 0.3
            )
            if inside and self._claim_bed(home):
                c.indoors = True
                c.sleeping = True
                c.energy -= cfg.energy_decay_per_tick * cfg.sleep_energy_mult
                if c.infected and cfg.disease_enabled:
                    c.energy -= cfg.disease_energy_drain
                    c.health -= 2.0 * cfg.disease_lethality
                else:
                    c.health = min(100.0, c.health + 0.15 * cfg.rest_recovery_mult)
                if c.energy <= 0:
                    self._kill(c, "starvation")
                elif c.health <= 0:
                    self._kill(c, "disease")
                elif c.age >= c.lifespan:
                    self._kill(c, "old_age")
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
        speed_mult = 1.0
        if c.status == "hungry":
            perceive *= cfg.hungry_perceive_mult
        elif c.status == "starving":
            perceive *= cfg.desperate_perceive_mult
            speed_mult = cfg.desperate_speed_mult

        # 1. Predation: hunt (predator) / flee (prey) — highest priority after sleep
        hunt_target: Creature | None = None
        flee_target: Creature | None = None
        if cfg.predation_enabled:
            if c.is_predator and c.bite_cooldown <= 0:
                # Find nearest non-predator prey within hunt_radius
                best_prey: Creature | None = None
                best_prey_d = cfg.hunt_radius + 1e-9
                for o in w.query_radius(c.x, c.y, cfg.hunt_radius):
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
                best_pred_d = cfg.fear_radius + 1e-9
                for o in w.query_radius(c.x, c.y, cfg.fear_radius):
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
            d = w.distance(c.x, c.y, e.x, e.y)
            if d < best:
                best, target = d, e  # type: ignore[assignment]

        # 3. Steer — priority: flee > hunt > home for night > food > wander
        if flee_target is not None:
            # Prey flees directly away from predator (with extra urgency when starving)
            dx, dy = w.delta(c.x, c.y, flee_target.x, flee_target.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            # Flee is more urgent than normal steering
            c.angle += max(-cfg.steer_turn * 1.2, min(cfg.steer_turn * 1.2, diff))
        elif hunt_target is not None:
            dx, dy = w.delta(hunt_target.x, hunt_target.y, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            c.angle += max(-cfg.steer_turn, min(cfg.steer_turn, diff))
        elif cfg.sleep_enabled and not c.is_predator and not c.is_herbivore and self._is_night(self._time_of_day()) and houses:
            home = self._house_for(c, houses)
            if home is None:
                home = min(houses, key=lambda h: w.distance(c.x, c.y, h.x, h.y))
            # Target door only when near the house (within 12 units), otherwise center
            if not self._inside_house(c, home) and w.distance(c.x, c.y, home.x, home.y) < 12:
                dx, dy = w.delta(*self._door_pos(home), c.x, c.y)
            else:
                dx, dy = w.delta(home.x, home.y, c.x, c.y)
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
        if math.hypot(mdx, mdy) <= step_len * 1.5:  # skip wrap teleports
            for h in houses:
                assert isinstance(h, House)
                crosses = (
                    _path_crosses_wall(px, py, px + mdx, py + mdy, h, predator_blocked=c.is_predator)
                    if c.is_predator
                    else _path_crosses_wall(px, py, px + mdx, py + mdy, h)
                )
                if crosses:
                    c.x, c.y = w.normalize(px, py)
                    c.angle += math.pi + self.rng.uniform(-0.4, 0.4)
                    break
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

        # 4b. Rocks are solid: push out and face away.
        if self.rocks:
            self._resolve_rock_collision(c)

        # 5. Eat. §O variant yields: grass low, berry high (autumn), mushroom decomposer, poisonous sickens.
        if target is not None and best <= cfg.eat_radius:
            w.remove(target.id)
            self._eaten.add(target.id)
            c.ticks_since_meal = 0
            c.meals += 1
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
            elif isinstance(target, Corpse):
                gain = cfg.corpse_energy  # scavenged remains
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

        # 6. Metabolism, sickness and mortality.
        c.energy -= cfg.energy_decay_per_tick
        if (
            cfg.shelter_enabled
            and not c.indoors
            and (self._is_night(tod) or self.weather in ("rain", "storm"))
        ):
            c.energy -= cfg.exposure_drain
        if cfg.disease_enabled and c.infected:
            c.energy -= cfg.disease_energy_drain
            c.health -= 2.0 * cfg.disease_lethality
            if c.health <= 0:
                self._kill(c, "disease")
                return
        elif c.health < 100.0:
            c.health = min(100.0, c.health + 0.1)
        if c.energy <= 0:
            self._kill(c, "starvation")
            return
        if c.age >= c.lifespan:
            self._kill(c, "old_age")

    def _enforce_food_law(self) -> None:
        """God's bounty or famine, bent by the season: winter starves the land."""
        season = self._season()
        target = round(self.config.food_count * SEASON_FOOD_MULT[season])
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
    def snapshot(self) -> StateMessage:
        cfg = self.config
        entities: list[EntityState] = []
        population: dict[str, int] = {}
        for e in sorted(self.world.entities.values(), key=lambda e: e.id):
            entities.append(self._entity_state(e))
            label = e.caste if isinstance(e, Creature) else e.kind.capitalize()
            population[label] = population.get(label, 0) + 1
        return StateMessage(
            type="state",
            tick=self.tick,
            seed=cfg.seed,
            width=cfg.width,
            height=cfg.height,
            boundary=cfg.boundary,
            population=population,
            entities=entities,
            creatures_alive=len(self.world.creatures()),
            creatures_dead=self.deaths,
            dead_by_cause=dict(self._death_counts),
            infected_count=sum(1 for c in self.world.creatures() if c.infected),
            time_of_day=round(self._time_of_day(), 3),
            day=self.day,
            season=self._season(),
            weather=self.weather,
            terrain_fertile=self.fertile,
            terrain_rocks=self.rocks,
            relations=[
                {"a": a, "b": b, "score": s}
                for (a, b), s in sorted(self.relations.items())
            ],
            clans={str(k): v for k, v in self.clans.items()},
            events=list(self._events_this_tick),
        )

    def _entity_state(self, e: Entity) -> EntityState:
        base = dict(id=e.id, kind=e.kind, x=round(e.x, 3), y=round(e.y, 3), angle=round(e.angle, 4))
        if isinstance(e, Creature):
            return EntityState(
                **base,
                shape=e.shape,
                sides=e.sides,
                caste=e.caste,
                energy=round(e.energy, 2),
                status=e.status,  # type: ignore[arg-type]
                radius=round(e.radius, 3),
                age=e.age,
                lifespan=round(e.lifespan, 1),
                stage=e.stage,  # type: ignore[arg-type]
                irregularity=e.irregularity,
                health=round(e.health, 1),
                infected=e.infected,
                sex=e.sex,  # type: ignore[arg-type]
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
            )
        if isinstance(e, House):
            return EntityState(
                **base,
                size=round(e.size, 2),
                door_width=round(e.door_width, 2),
                door_offset=round(e.door_offset, 2),
                door_side=e.door_side,  # type: ignore[arg-type]
                clan_id=e.clan_id or None,
                clan_color=e.clan_color,
                is_ruin=e.is_ruin or None,
                abandoned_ticks=e.abandoned_ticks or None,
            )
        if isinstance(e, Food):
            return EntityState(**base, growth=round(e.growth, 3), variant=e.variant)  # type: ignore[arg-type]
        return EntityState(**base)  # type: ignore[arg-type]


def _house_wall_segments(h: House) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The house's wall segments; the door side is split around the doorway."""
    half = h.size / 2
    x0, y0 = h.x - half, h.y - half
    x1, y1 = h.x + half, h.y + half
    d = h.door_width / 2
    c = h.door_offset
    if h.door_side == "north":
        return [
            ((x0, y0), (h.x + c - d, y0)),
            ((h.x + c + d, y0), (x1, y0)),
            ((x0, y0), (x0, y1)),
            ((x1, y0), (x1, y1)),
            ((x0, y1), (x1, y1)),
        ]
    if h.door_side == "south":
        return [
            ((x0, y0), (x1, y0)),
            ((x0, y0), (x0, y1)),
            ((x1, y0), (x1, y1)),
            ((x0, y1), (h.x + c - d, y1)),
            ((h.x + c + d, y1), (x1, y1)),
        ]
    if h.door_side == "west":
        return [
            ((x0, y0), (x1, y0)),
            ((x0, y1), (x1, y1)),
            ((x1, y0), (x1, y1)),
            ((x0, y0), (x0, h.y + c - d)),
            ((x0, h.y + c + d), (x0, y1)),
        ]
    # east
    return [
        ((x0, y0), (x1, y0)),
        ((x0, y0), (x0, y1)),
        ((x0, y1), (x1, y1)),
        ((x1, y0), (x1, h.y + c - d)),
        ((x1, h.y + c + d), (x1, y1)),
    ]


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
    path = ((px, py), (qx, qy))
    segments = _house_wall_segments_closed(h) if predator_blocked else _house_wall_segments(h)
    return any(
        segments_intersect(path[0], path[1], a, b)
        for a, b in segments
    )
