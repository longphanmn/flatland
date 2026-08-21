"""World container: entity registry + uniform spatial hash with wrap-aware queries."""

import math
from typing import Iterator

from .config import Config
from .entities import Creature, Entity


class World:
    def __init__(self, config: Config):
        self.config = config
        self.entities: dict[int, Entity] = {}
        self._next_id = 1
        self.cell_size = max(4.0, config.perceive_radius)
        self.cols = max(1, math.ceil(config.width / self.cell_size))
        self.rows = max(1, math.ceil(config.height / self.cell_size))
        self._cells: dict[tuple[int, int], list[Entity]] = {}

    # ---------------------------------------------------------------- registry
    def add(self, entity: Entity) -> Entity:
        entity.id = self._next_id
        self._next_id += 1
        self.entities[entity.id] = entity
        return entity

    def remove(self, entity_id: int) -> None:
        self.entities.pop(entity_id, None)

    def creatures(self) -> list[Creature]:
        return [e for e in self.entities.values() if e.kind == "creature"]

    # ------------------------------------------------------------ spatial index
    def rebuild_index(self) -> None:
        """Re-bucket all entities; called once per tick."""
        self._cells.clear()
        cs = self.cell_size
        for e in self.entities.values():
            key = (int(e.x // cs) % self.cols, int(e.y // cs) % self.rows)
            self._cells.setdefault(key, []).append(e)

    def delta(self, ax: float, ay: float, bx: float, by: float) -> tuple[float, float]:
        """Shortest displacement from b to a, honouring wrap-around edges."""
        dx, dy = ax - bx, ay - by
        if self.config.boundary == "wrap":
            w, h = self.config.width, self.config.height
            if dx > w / 2:
                dx -= w
            elif dx < -w / 2:
                dx += w
            if dy > h / 2:
                dy -= h
            elif dy < -h / 2:
                dy += h
        return dx, dy

    def distance(self, ax: float, ay: float, bx: float, by: float) -> float:
        dx, dy = self.delta(ax, ay, bx, by)
        return math.hypot(dx, dy)

    def query_radius(self, x: float, y: float, radius: float) -> Iterator[Entity]:
        """Yield entities within `radius` of (x, y); requires a fresh index."""
        cs = self.cell_size
        seen: set[int] = set()
        x0, x1 = int(math.floor((x - radius) / cs)), int(math.floor((x + radius) / cs))
        y0, y1 = int(math.floor((y - radius) / cs)), int(math.floor((y + radius) / cs))
        for cx in range(x0, x1 + 1):
            for cy in range(y0, y1 + 1):
                bucket = self._cells.get((cx % self.cols, cy % self.rows))
                if not bucket:
                    continue
                for e in bucket:
                    if e.id in seen:
                        continue
                    seen.add(e.id)
                    if self.distance(x, y, e.x, e.y) <= radius:
                        yield e

    # -------------------------------------------------------------- boundaries
    def normalize(self, x: float, y: float) -> tuple[float, float]:
        """Clamp or wrap a position back inside the world bounds."""
        if self.config.boundary == "wrap":
            return x % self.config.width, y % self.config.height
        cx = min(max(x, 0.0), self.config.width)
        cy = min(max(y, 0.0), self.config.height)
        return cx, cy
