"""Deterministic fixed-tick simulation of Flatland."""

import math
import random
from collections import deque

from .config import Config
from .entities import (
    DEFAULT_RADIUS,
    PRIEST_SIDES,
    Creature,
    Entity,
    Food,
    House,
    caste_name,
)
from .protocol import EntityState, HistoryEvent, StateMessage
from .world import World, segments_intersect

# Caste -> movement speed (grid units per tick).
SPEEDS = {
    "Soldier": 0.85,
    "Gentleman": 0.55,
    "Professional": 0.5,
    "Noble": 0.45,
    "Priest": 0.35,
    "Woman": 0.75,
}


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
        self._eaten: set[int] = set()
        self._events_this_tick: list[HistoryEvent] = []
        self._spawn_initial()

    # ------------------------------------------------------------------ setup
    def _rand_pos(self) -> tuple[float, float]:
        cfg = self.config
        return self.rng.uniform(0, cfg.width), self.rng.uniform(0, cfg.height)

    def _spawn_creature(self, shape: str, sides: int) -> None:
        cfg = self.config
        x, y = self._rand_pos()
        caste = caste_name(sides, shape)
        self.world.add(
            Creature(
                shape=shape,
                sides=sides,
                x=x,
                y=y,
                angle=self.rng.uniform(0, 2 * math.pi),
                speed=SPEEDS.get(caste, 0.6),
                energy=cfg.energy_start,
            )
        )

    def _spawn_initial(self) -> None:
        cfg = self.config
        for _ in range(cfg.num_triangles):
            self._spawn_creature("polygon", 3)
        for _ in range(cfg.num_squares):
            self._spawn_creature("polygon", 4)
        for _ in range(cfg.num_pentagons):
            self._spawn_creature("polygon", 5)
        for _ in range(cfg.num_hexagons):
            self._spawn_creature("polygon", 6)
        for _ in range(cfg.num_priests):
            self._spawn_creature("polygon", PRIEST_SIDES)
        for _ in range(cfg.num_women):
            self._spawn_creature("line", 2)
        for _ in range(cfg.food_count):
            x, y = self._rand_pos()
            self.world.add(Food(x=x, y=y))
        max_radius = max(
            (c.radius for c in self.world.creatures()), default=DEFAULT_RADIUS
        )
        for _ in range(cfg.num_houses):
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
        self._events_this_tick = []
        self.world.rebuild_index()
        houses = [e for e in self.world.entities.values() if e.kind == "house"]
        for creature in self.world.creatures():  # snapshot list; removals are safe
            self._update_creature(creature, houses)
        self._enforce_food_law()
        self.tick += 1

    def _update_creature(self, c: Creature, houses: list[Entity]) -> None:
        cfg, w = self.config, self.world
        c.ticks_since_meal += 1

        # Hunger state drives perception range and urgency.
        ratio = c.energy / cfg.energy_max if cfg.energy_max > 0 else 0.0
        if ratio <= cfg.starving_ratio:
            c.status = "starving"
        elif ratio <= cfg.hungry_ratio:
            c.status = "hungry"
        else:
            c.status = ""

        perceive = cfg.perceive_radius
        speed_mult = 1.0
        if c.status == "hungry":
            perceive *= cfg.hungry_perceive_mult
        elif c.status == "starving":
            perceive *= cfg.desperate_perceive_mult
            speed_mult = cfg.desperate_speed_mult

        # 1. Perceive the nearest food.
        target: Food | None = None
        best = math.inf
        for e in w.query_radius(c.x, c.y, perceive):
            if e.kind != "food" or e.id in self._eaten:
                continue
            d = w.distance(c.x, c.y, e.x, e.y)
            if d < best:
                best, target = d, e  # type: ignore[assignment]

        # 2. Steer toward food or wander.
        if target is not None:
            dx, dy = w.delta(target.x, target.y, c.x, c.y)
            desired = math.atan2(dy, dx)
            diff = (desired - c.angle + math.pi) % (2 * math.pi) - math.pi
            step = max(-cfg.steer_turn, min(cfg.steer_turn, diff))
            c.angle += step
        else:
            c.angle += self.rng.uniform(-cfg.wander_turn, cfg.wander_turn)

        # 3. Move (hunger speeds up the desperate).
        step_len = c.speed * speed_mult
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
        mdx, mdy = w.delta(c.x, c.y, px, py)
        if math.hypot(mdx, mdy) <= step_len * 1.5:  # skip wrap teleports
            for h in houses:
                assert isinstance(h, House)
                if _path_crosses_wall(px, py, px + mdx, py + mdy, h):
                    c.x, c.y = w.normalize(px, py)
                    c.angle += math.pi + self.rng.uniform(-0.3, 0.3)
                    break

        # 5. Eat.
        if target is not None and best <= cfg.eat_radius:
            w.remove(target.id)
            self._eaten.add(target.id)
            c.ticks_since_meal = 0
            c.meals += 1
            c.energy = min(cfg.energy_max, c.energy + cfg.energy_from_food)

        # 6. Metabolism; starving to death removes the creature.
        c.energy -= cfg.energy_decay_per_tick
        if c.energy <= 0:
            w.remove(c.id)
            self.deaths += 1
            event = HistoryEvent(
                type="death",
                tick=self.tick + 1,  # the tick being completed
                entity_id=c.id,
                caste=c.caste,
                cause="starvation",
                x=round(c.x, 2),
                y=round(c.y, 2),
            )
            self.history.append(event)
            self._events_this_tick.append(event)

    def _enforce_food_law(self) -> None:
        """God's bounty or famine: keep food population at the law's target."""
        foods = [e for e in self.world.entities.values() if e.kind == "food"]
        deficit = self.config.food_count - len(foods)
        if deficit > 0:
            for _ in range(deficit):
                x, y = self._rand_pos()
                self.world.add(Food(x=x, y=y))
        elif deficit < 0:
            for victim in self.rng.sample(foods, -deficit):
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
            width=cfg.width,
            height=cfg.height,
            boundary=cfg.boundary,
            population=population,
            entities=entities,
            creatures_alive=len(self.world.creatures()),
            creatures_dead=self.deaths,
            events=list(self._events_this_tick),
        )

    @staticmethod
    def _entity_state(e: Entity) -> EntityState:
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
            )
        if isinstance(e, House):
            return EntityState(
                **base,
                size=round(e.size, 2),
                door_width=round(e.door_width, 2),
                door_offset=round(e.door_offset, 2),
                door_side=e.door_side,  # type: ignore[arg-type]
            )
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


def _path_crosses_wall(
    px: float, py: float, qx: float, qy: float, h: House
) -> bool:
    """True if the movement path p->q crosses a house wall (door is passable)."""
    path = ((px, py), (qx, qy))
    return any(
        segments_intersect(path[0], path[1], a, b)
        for a, b in _house_wall_segments(h)
    )
