"""2D Spatial Hash Grid — BA Step 1.1

Fixed cell size (32x32), flat 1D bucket array. Wraps if world boundary is "wrap".
Reuses world.py pre-allocated bucket idea but is a standalone, vector-friendly
structure for the BA SoA path. The legacy World hash stays untouched.
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple


class SpatialHashGrid:
    """Flat 1D spatial hash grid.

    Buckets are list[int] of entity_ids. Positions are stored separately
    so update_positions can be vectorized via numpy.
    """

    def __init__(self, width: float, height: float, cell_size: float = 32.0, boundary: str = "wrap"):
        self.width = float(width)
        self.height = float(height)
        self.cell_size = float(cell_size)
        self.boundary = boundary
        self.cols = max(1, math.ceil(self.width / self.cell_size))
        self.rows = max(1, math.ceil(self.height / self.cell_size))
        self._num_cells = self.cols * self.rows
        self._buckets: List[List[int]] = [[] for _ in range(self._num_cells)]
        # id -> (x, y, type_str)
        self._pos: Dict[int, Tuple[float, float, str | None]] = {}

    # ------------------------------------------------------------------
    def _cell(self, x: float, y: float) -> int:
        cx = int(x // self.cell_size) % self.cols if self.boundary == "wrap" else max(0, min(self.cols - 1, int(x // self.cell_size)))
        cy = int(y // self.cell_size) % self.rows if self.boundary == "wrap" else max(0, min(self.rows - 1, int(y // self.cell_size)))
        return cy * self.cols + cx

    def insert(self, entity_id: int, x: float, y: float, type_str: str | None = None) -> None:
        self._pos[entity_id] = (float(x), float(y), type_str)
        idx = self._cell(x, y)
        # avoid duplicate
        if entity_id not in self._buckets[idx]:
            self._buckets[idx].append(entity_id)

    def remove(self, entity_id: int) -> None:
        if entity_id not in self._pos:
            return
        x, y, _ = self._pos.pop(entity_id)
        idx = self._cell(x, y)
        try:
            self._buckets[idx].remove(entity_id)
        except ValueError:
            pass

    def move(self, entity_id: int, x: float, y: float, type_str: str | None = None) -> None:
        """BJ-1: incremental single-agent position update.

        Moves the id between buckets only when its cell changes; otherwise
        just refreshes the stored position. O(1) average, no full rebucket.
        """
        eid = int(entity_id)
        fx, fy = float(x), float(y)
        old = self._pos.get(eid)
        if old is None:
            self.insert(eid, fx, fy, type_str)
            return
        _, _, old_t = old
        t = type_str if type_str is not None else old_t
        old_cell = self._cell(old[0], old[1])
        new_cell = self._cell(fx, fy)
        self._pos[eid] = (fx, fy, t)
        if old_cell == new_cell:
            return
        try:
            self._buckets[old_cell].remove(eid)
        except ValueError:
            pass
        if eid not in self._buckets[new_cell]:
            self._buckets[new_cell].append(eid)

    def update_positions(self, ids, pos_array) -> None:
        """Batch update: ids iterable, pos_array shape (N,2)."""
        # clear and rebucket for simplicity (O(N))
        for b in self._buckets:
            b.clear()
        # pos_array may be numpy or list
        try:
            import numpy as np  # type: ignore

            if isinstance(pos_array, np.ndarray):
                for i, eid in enumerate(ids):
                    x = float(pos_array[i, 0])
                    y = float(pos_array[i, 1])
                    # keep type if known
                    t = self._pos.get(int(eid), (x, y, None))[2]
                    self._pos[int(eid)] = (x, y, t)
                    self._buckets[self._cell(x, y)].append(int(eid))
                return
        except Exception:
            pass
        for eid, (x, y) in zip(ids, pos_array):
            t = self._pos.get(int(eid), (float(x), float(y), None))[2]
            self._pos[int(eid)] = (float(x), float(y), t)
            self._buckets[self._cell(float(x), float(y))].append(int(eid))

    def _toroidal_delta(self, ax: float, bx: float, size: float) -> float:
        d = ax - bx
        if self.boundary == "wrap":
            half = size * 0.5
            if d > half:
                d -= size
            elif d < -half:
                d += size
        return d

    def query_radius(self, x: float, y: float, radius: float, filter_type: str | None = None) -> List[int]:
        """O(1) average: scan cells intersecting radius, filter by distance and type."""
        cs = self.cell_size
        r2 = radius * radius
        w, h = self.width, self.height
        half_w, half_h = w * 0.5, h * 0.5
        res: List[int] = []
        if self.boundary == "wrap":
            cx_center = int(x // cs) % self.cols
            cy_center = int(y // cs) % self.rows
            rx = int(radius / cs) + 1
            ry = rx
            seen = set()
            for dx in range(-rx, rx + 1):
                cx = (cx_center + dx) % self.cols
                for dy in range(-ry, ry + 1):
                    cy = (cy_center + dy) % self.rows
                    for eid in self._buckets[cy * self.cols + cx]:
                        if eid in seen:
                            continue
                        seen.add(eid)
                        ex, ey, et = self._pos[eid]
                        if filter_type is not None and et != filter_type:
                            continue
                        dx_ = x - ex
                        if dx_ < 0:
                            dx_ = -dx_
                        if self.boundary == "wrap" and dx_ > half_w:
                            dx_ -= w
                        dy_ = y - ey
                        if dy_ < 0:
                            dy_ = -dy_
                        if self.boundary == "wrap" and dy_ > half_h:
                            dy_ -= h
                        if dx_ * dx_ + dy_ * dy_ <= r2:
                            res.append(eid)
            return res
        # clamp
        x0 = max(0, int((x - radius) // cs))
        x1 = min(self.cols - 1, int((x + radius) // cs))
        y0 = max(0, int((y - radius) // cs))
        y1 = min(self.rows - 1, int((y + radius) // cs))
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                for eid in self._buckets[cy * self.cols + cx]:
                    ex, ey, et = self._pos[eid]
                    if filter_type is not None and et != filter_type:
                        continue
                    dx_ = x - ex
                    dy_ = y - ey
                    if dx_ * dx_ + dy_ * dy_ <= r2:
                        res.append(eid)
        return res

    def raycast(self, origin: Tuple[float, float], angle: float, max_dist: float, ignore_id: int | None = None) -> Tuple[float, str | None]:
        """Walk cells along ray, return (hit_dist, hit_type) or (max_dist, None)."""
        ox, oy = origin
        # step through cells along ray
        steps = int(max_dist / self.cell_size) + 2
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        best = max_dist
        best_type = None
        # naive: query radius expanding along ray via small steps
        for s in range(1, steps + 1):
            d = (s / steps) * max_dist
            x = ox + cos_a * d
            y = oy + sin_a * d
            if self.boundary == "wrap":
                x %= self.width
                y %= self.height
            else:
                if not (0 <= x <= self.width and 0 <= y <= self.height):
                    break
            # radius ~ cell/2 to catch nearby entities
            cand = self.query_radius(x, y, self.cell_size * 0.6)
            for eid in cand:
                if ignore_id is not None and eid == ignore_id:
                    continue
                ex, ey, et = self._pos[eid]
                # precise toroidal distance from origin to entity center
                dx = self._toroidal_delta(ex, ox, self.width)
                dy = self._toroidal_delta(ey, oy, self.height)
                # project onto ray
                proj = dx * cos_a + dy * sin_a
                if proj < 0 or proj > best:
                    continue
                # perpendicular distance
                perp = abs(dx * sin_a - dy * cos_a)
                if perp <= 1.5:  # hit radius ~ entity size
                    best = proj
                    best_type = et
        return best, best_type
