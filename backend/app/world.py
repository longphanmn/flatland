"""World container: entity registry + uniform spatial hash with wrap-aware queries."""

import math
from typing import Iterator

from .config import Config
from .entities import Creature, Entity


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def segments_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    """True if segment p1-p2 intersects segment q1-q2."""
    rx, ry = p2[0] - p1[0], p2[1] - p1[1]
    sx, sy = q2[0] - q1[0], q2[1] - q1[1]
    denom = _cross(rx, ry, sx, sy)
    if abs(denom) < 1e-12:
        return False  # parallel: treated as non-crossing
    qpx, qpy = q1[0] - p1[0], q1[1] - p1[1]
    t = _cross(qpx, qpy, sx, sy) / denom
    u = _cross(qpx, qpy, rx, ry) / denom
    return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0


class World:
    def __init__(self, config: Config):
        self.config = config
        self.entities: dict[int, Entity] = {}
        self._next_id = 1
        # T: fixed ~8 so fine queries don't scan 81 cells
        self.cell_size = 8.0
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

    def distance_sq(self, ax: float, ay: float, bx: float, by: float) -> float:
        """Wrap-aware squared distance — for threshold tests without sqrt."""
        dx, dy = self.delta(ax, ay, bx, by)
        return dx * dx + dy * dy

    def query_radius(self, x: float, y: float, radius: float) -> Iterator[Entity]:
        """Yield entities within `radius` of (x, y); requires a fresh index.

        T: toroidal dx iteration for fixed 8; correct wrap handling.
        """
        cs = self.cell_size
        if self.config.boundary == "wrap":
            cx_center = int(math.floor(x / cs)) % self.cols if self.cols else 0
            cy_center = int(math.floor(y / cs)) % self.rows if self.rows else 0
            rx = int(math.ceil(radius / cs)) + 1
            ry = int(math.ceil(radius / cs)) + 1
            need_seen = (rx * 2 + 1 >= self.cols) or (ry * 2 + 1 >= self.rows)
            if need_seen:
                seen: set[int] = set()
                for dx in range(-rx, rx + 1):
                    cx = (cx_center + dx) % self.cols
                    for dy in range(-ry, ry + 1):
                        cy = (cy_center + dy) % self.rows
                        bucket = self._cells.get((cx, cy))
                        if not bucket:
                            continue
                        for e in bucket:
                            if e.id in seen:
                                continue
                            seen.add(e.id)
                            if self.distance(x, y, e.x, e.y) <= radius:
                                yield e
                return
            for dx in range(-rx, rx + 1):
                cx = (cx_center + dx) % self.cols
                for dy in range(-ry, ry + 1):
                    cy = (cy_center + dy) % self.rows
                    bucket = self._cells.get((cx, cy))
                    if not bucket:
                        continue
                    for e in bucket:
                        if self.distance(x, y, e.x, e.y) <= radius:
                            yield e
            return
        # clamp: no wrap
        cs = self.cell_size
        x0, x1 = int(math.floor((x - radius) / cs)), int(math.floor((x + radius) / cs))
        y0, y1 = int(math.floor((y - radius) / cs)), int(math.floor((y + radius) / cs))
        for cx in range(x0, x1 + 1):
            if cx < 0 or cx >= self.cols:
                continue
            for cy in range(y0, y1 + 1):
                if cy < 0 or cy >= self.rows:
                    continue
                bucket = self._cells.get((cx, cy))
                if not bucket:
                    continue
                for e in bucket:
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
