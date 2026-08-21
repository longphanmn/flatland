"""Deterministic fixed-tick simulation of Flatland."""

import math
import random

from .config import Config
from .entities import PRIEST_SIDES, Creature, Entity, Food, House, caste_name
from .protocol import EntityState, StateMessage
from .world import World

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
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.world = World(self.config)
        self.rng = random.Random(self.config.seed)
        self.tick = 0
        self._eaten: set[int] = set()
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
        for _ in range(cfg.num_food):
            x, y = self._rand_pos()
            self.world.add(Food(x=x, y=y))
        for _ in range(cfg.num_houses):
            x, y = self._rand_pos()
            self.world.add(House(x=x, y=y, size=self.rng.uniform(4.0, 8.0)))

    # ------------------------------------------------------------------ tick
    def step(self) -> None:
        """Advance the world by exactly one tick (deterministic)."""
        self._eaten.clear()
        self.world.rebuild_index()
        houses = [e for e in self.world.entities.values() if e.kind == "house"]
        for creature in self.world.creatures():  # snapshot list; removals are safe
            self._update_creature(creature, houses)
        self._replenish_food()
        self.tick += 1

    def _update_creature(self, c: Creature, houses: list[Entity]) -> None:
        cfg, w = self.config, self.world

        # 1. Perceive the nearest food.
        target: Food | None = None
        best = math.inf
        for e in w.query_radius(c.x, c.y, cfg.perceive_radius):
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

        # 3. Move (with boundary handling).
        nx = c.x + math.cos(c.angle) * c.speed
        ny = c.y + math.sin(c.angle) * c.speed
        if cfg.boundary == "clamp":
            hit_x = nx <= 0 or nx >= cfg.width
            hit_y = ny <= 0 or ny >= cfg.height
            if hit_x:
                c.angle = math.pi - c.angle
            if hit_y:
                c.angle = -c.angle
        c.x, c.y = w.normalize(nx, ny)

        # 4. Eat.
        if target is not None and best <= cfg.eat_radius:
            w.remove(target.id)
            self._eaten.add(target.id)
            c.energy = min(cfg.energy_max, c.energy + cfg.energy_from_food)

        # 5. Houses are solid: push out and face away.
        for h in houses:
            d = w.distance(c.x, c.y, h.x, h.y)
            min_d = h.size / 2 + 0.8
            if d < min_d:
                ux, uy = w.delta(c.x, c.y, h.x, h.y)
                if abs(ux) < 1e-6 and abs(uy) < 1e-6:
                    ang = self.rng.uniform(0, 2 * math.pi)
                    ux, uy = math.cos(ang), math.sin(ang)
                norm = math.hypot(ux, uy) or 1.0
                c.x, c.y = w.normalize(h.x + ux / norm * min_d, h.y + uy / norm * min_d)
                c.angle = math.atan2(uy, ux)

        # 6. Metabolism; starvation removes the creature.
        c.energy -= cfg.energy_decay_per_tick
        if c.energy <= 0:
            w.remove(c.id)

    def _replenish_food(self) -> None:
        for _ in self._eaten:
            x, y = self._rand_pos()
            self.world.add(Food(x=x, y=y))

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
        )

    @staticmethod
    def _entity_state(e: Entity) -> EntityState:
        base = dict(id=e.id, kind=e.kind, x=round(e.x, 3), y=round(e.y, 3), angle=round(e.angle, 4))
        if isinstance(e, Creature):
            return EntityState(**base, shape=e.shape, sides=e.sides, caste=e.caste, energy=round(e.energy, 2))  # type: ignore[arg-type]
        if isinstance(e, House):
            return EntityState(**base, size=round(e.size, 2))  # type: ignore[arg-type]
        return EntityState(**base)  # type: ignore[arg-type]
