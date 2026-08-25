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
        # T: 16 trades a few extra checks for 3× fewer cells at 1000+ creatures
        # 18u perceive 8→25 cells → 12/16→9 cells → ~60% less scan
        self.cell_size = 16.0
        self.cols = max(1, math.ceil(config.width / self.cell_size))
        self.rows = max(1, math.ceil(config.height / self.cell_size))
        self._num_cells = self.cols * self.rows
        # AF: pre-allocated cell buckets avoid creating/clearing dict keys and lists per tick
        self._buckets: list[list[Entity]] = [[] for _ in range(self._num_cells)]

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
        cols = self.cols
        rows = self.rows
        cs = self.cell_size
        buckets = self._buckets
        for b in buckets:
            b.clear()
        for e in self.entities.values():
            cx = int(e.x // cs) % cols
            cy = int(e.y // cs) % rows
            buckets[cy * cols + cx].append(e)

    def delta(self, ax: float, ay: float, bx: float, by: float) -> tuple[float, float]:
        """Shortest displacement from b to a, honouring wrap-around edges."""
        dx = ax - bx
        dy = ay - by
        if self.config.boundary == "wrap":
            w = self.config.width
            h = self.config.height
            half_w = w * 0.5
            half_h = h * 0.5
            if dx > half_w:
                dx -= w
            elif dx < -half_w:
                dx += w
            if dy > half_h:
                dy -= h
            elif dy < -half_h:
                dy += h
        return dx, dy

    def distance(self, ax: float, ay: float, bx: float, by: float) -> float:
        dx = ax - bx
        dy = ay - by
        if self.config.boundary == "wrap":
            w = self.config.width
            h = self.config.height
            half_w = w * 0.5
            half_h = h * 0.5
            if dx > half_w:
                dx -= w
            elif dx < -half_w:
                dx += w
            if dy > half_h:
                dy -= h
            elif dy < -half_h:
                dy += h
        return math.hypot(dx, dy)

    def distance_sq(self, ax: float, ay: float, bx: float, by: float) -> float:
        """Wrap-aware squared distance — for threshold tests without sqrt or tuple allocation."""
        dx = ax - bx
        if dx < 0:
            dx = -dx
        dy = ay - by
        if dy < 0:
            dy = -dy
        if self.config.boundary == "wrap":
            w = self.config.width
            h = self.config.height
            if dx > w * 0.5:
                dx -= w
            if dy > h * 0.5:
                dy -= h
        return dx * dx + dy * dy

    def query_radius(self, x: float, y: float, radius: float) -> list[Entity]:
        """Return list of entities within `radius` of (x, y); requires a fresh index.

        T: toroidal dx iteration for fixed 8; correct wrap handling.
        AF: inlined squared distance check eliminates math.hypot / math.sqrt and tuple allocation overhead.
        """
        cs = self.cell_size
        r2 = radius * radius
        cols = self.cols
        rows = self.rows
        buckets = self._buckets
        w = self.config.width
        h = self.config.height
        half_w = w * 0.5
        half_h = h * 0.5
        is_wrap = self.config.boundary == "wrap"
        res: list[Entity] = []

        if is_wrap:
            cx_center = int(x // cs) % cols if cols else 0
            cy_center = int(y // cs) % rows if rows else 0
            rx = int(math.ceil(radius / cs)) + 1
            ry = int(math.ceil(radius / cs)) + 1
            need_seen = (rx * 2 + 1 >= cols) or (ry * 2 + 1 >= rows)
            if need_seen:
                seen: set[int] = set()
                for dx_grid in range(-rx, rx + 1):
                    cx = (cx_center + dx_grid) % cols
                    for dy_grid in range(-ry, ry + 1):
                        cy = (cy_center + dy_grid) % rows
                        for e in buckets[cy * cols + cx]:
                            if e.id in seen:
                                continue
                            seen.add(e.id)
                            edx = x - e.x
                            if edx < 0: edx = -edx
                            if edx > half_w: edx -= w
                            edy = y - e.y
                            if edy < 0: edy = -edy
                            if edy > half_h: edy -= h
                            if edx * edx + edy * edy <= r2:
                                res.append(e)
                return res
            for dx_grid in range(-rx, rx + 1):
                cx = (cx_center + dx_grid) % cols
                for dy_grid in range(-ry, ry + 1):
                    cy = (cy_center + dy_grid) % rows
                    for e in buckets[cy * cols + cx]:
                        edx = x - e.x
                        if edx < 0: edx = -edx
                        if edx > half_w: edx -= w
                        edy = y - e.y
                        if edy < 0: edy = -edy
                        if edy > half_h: edy -= h
                        if edx * edx + edy * edy <= r2:
                            res.append(e)
            return res
        # clamp: no wrap
        x0 = max(0, int((x - radius) // cs))
        x1 = min(cols - 1, int((x + radius) // cs))
        y0 = max(0, int((y - radius) // cs))
        y1 = min(rows - 1, int((y + radius) // cs))
        for cy in range(y0, y1 + 1):
            row_off = cy * cols
            for cx in range(x0, x1 + 1):
                for e in buckets[row_off + cx]:
                    edx = x - e.x
                    edy = y - e.y
                    if edx * edx + edy * edy <= r2:
                        res.append(e)
        return res

    def query_radius_with_dist_sq(self, x: float, y: float, radius: float) -> list[tuple[Entity, float]]:
        """Return list of (entity, dist_sq) within `radius` of (x, y) without recomputing distances."""
        cs = self.cell_size
        r2 = radius * radius
        cols = self.cols
        rows = self.rows
        buckets = self._buckets
        w = self.config.width
        h = self.config.height
        half_w = w * 0.5
        half_h = h * 0.5
        is_wrap = self.config.boundary == "wrap"
        res: list[tuple[Entity, float]] = []

        if is_wrap:
            cx_center = int(x // cs) % cols if cols else 0
            cy_center = int(y // cs) % rows if rows else 0
            rx = int(math.ceil(radius / cs)) + 1
            ry = int(math.ceil(radius / cs)) + 1
            need_seen = (rx * 2 + 1 >= cols) or (ry * 2 + 1 >= rows)

            if need_seen:
                seen: set[int] = set()
                for dx_grid in range(-rx, rx + 1):
                    cx = (cx_center + dx_grid) % cols
                    for dy_grid in range(-ry, ry + 1):
                        cy = (cy_center + dy_grid) % rows
                        for e in buckets[cy * cols + cx]:
                            if e.id in seen:
                                continue
                            seen.add(e.id)
                            edx = x - e.x
                            if edx < 0: edx = -edx
                            if edx > half_w: edx -= w
                            edy = y - e.y
                            if edy < 0: edy = -edy
                            if edy > half_h: edy -= h
                            d2 = edx * edx + edy * edy
                            if d2 <= r2:
                                res.append((e, d2))
                return res
            for dx_grid in range(-rx, rx + 1):
                cx = (cx_center + dx_grid) % cols
                for dy_grid in range(-ry, ry + 1):
                    cy = (cy_center + dy_grid) % rows
                    for e in buckets[cy * cols + cx]:
                        edx = x - e.x
                        if edx < 0: edx = -edx
                        if edx > half_w: edx -= w
                        edy = y - e.y
                        if edy < 0: edy = -edy
                        if edy > half_h: edy -= h
                        d2 = edx * edx + edy * edy
                        if d2 <= r2:
                            res.append((e, d2))
            return res
        # clamp: no wrap
        x0 = max(0, int((x - radius) // cs))
        x1 = min(cols - 1, int((x + radius) // cs))
        y0 = max(0, int((y - radius) // cs))
        y1 = min(rows - 1, int((y + radius) // cs))
        for cy in range(y0, y1 + 1):
            row_off = cy * cols
            for cx in range(x0, x1 + 1):
                for e in buckets[row_off + cx]:
                    edx = x - e.x
                    edy = y - e.y
                    d2 = edx * edx + edy * edy
                    if d2 <= r2:
                        res.append((e, d2))
        return res

    def query_radius_list(self, x: float, y: float, radius: float) -> list[Entity]:
        """Direct list-returning alias of query_radius."""
        return self.query_radius(x, y, radius)

    def query_radius_with_dist_sq_list(self, x: float, y: float, radius: float) -> list[tuple[Entity, float]]:
        """Direct list-returning alias of query_radius_with_dist_sq."""
        return self.query_radius_with_dist_sq(x, y, radius)

    # -------------------------------------------------------------- boundaries
    def normalize(self, x: float, y: float) -> tuple[float, float]:
        """Clamp or wrap a position back inside the world bounds."""
        if self.config.boundary == "wrap":
            return x % self.config.width, y % self.config.height
        cx = min(max(x, 0.0), self.config.width)
        cy = min(max(y, 0.0), self.config.height)
        return cx, cy
