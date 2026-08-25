"""Native C acceleration bridge (AJ Phase 3 + AY Phase M-2) with pure Python fallback.

Provides compiled C99 speedups for spatial queries, vector math,
toroidal distance, raycasting and collision sweeps.
"""

import ctypes
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_C_LIB = None  # type: ignore
_LIB_DIR = Path(__file__).resolve().parent
_SRC_PATH = _LIB_DIR / "flatland_core.c"
_LIB_PATH = _LIB_DIR / ("_flatland_core.dylib" if sys.platform == "darwin" else "_flatland_core.so")


def _compile_native_core() -> bool:
    """Attempt to compile flatland_core.c using clang or gcc if available."""
    if not _SRC_PATH.exists():
        return False
    if _LIB_PATH.exists() and _LIB_PATH.stat().st_mtime >= _SRC_PATH.stat().st_mtime:
        return True
    cc = os.environ.get("CC", "clang" if sys.platform == "darwin" else "gcc")
    cmd = [
        cc,
        "-O3",
        "-shared",
        "-fPIC",
        "-Wall",
        "-ffast-math",
        str(_SRC_PATH),
        "-o",
        str(_LIB_PATH),
        "-lm",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=15)
        return res.returncode == 0 and _LIB_PATH.exists()
    except Exception:
        return False


def _init_native_lib():
    global _C_LIB
    if _C_LIB is not None:
        return _C_LIB
    try:
        if _compile_native_core():
            lib = ctypes.CDLL(str(_LIB_PATH))
            lib.c_query_radius.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
            ]
            lib.c_query_radius.restype = ctypes.c_int

            lib.c_spatial_hash_query.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
                ctypes.c_int, ctypes.c_int, ctypes.c_float,
                ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
            ]
            lib.c_spatial_hash_query.restype = ctypes.c_int

            lib.c_toroidal_dist_sq.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.c_float, ctypes.c_float, ctypes.c_int,
            ]
            lib.c_toroidal_dist_sq.restype = ctypes.c_float

            lib.c_segments_intersect.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ]
            lib.c_segments_intersect.restype = ctypes.c_int

            lib.c_path_crosses_wall.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.POINTER(ctypes.c_float), ctypes.c_int,
            ]
            lib.c_path_crosses_wall.restype = ctypes.c_int

            lib.c_boids_separation.argtypes = [
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ]
            lib.c_boids_separation.restype = None

            lib.c_boids_alignment.argtypes = [
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ]
            lib.c_boids_alignment.restype = None

            lib.c_boids_cohesion.argtypes = [
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ]
            lib.c_boids_cohesion.restype = None

            lib.c_collision_sweep.argtypes = [
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
            ]
            lib.c_collision_sweep.restype = ctypes.c_int

            _C_LIB = lib
            return _C_LIB
    except Exception:
        _C_LIB = None
    return None


_init_native_lib()


def is_native_available() -> bool:
    return _C_LIB is not None


# ------------------------------------------------------------------ queries

def native_query_radius(
    qx: float, qy: float, radius: float,
    entity_x: Sequence[float], entity_y: Sequence[float], entity_ids: Sequence[int],
    width: float, height: float, is_wrap: bool,
    max_out: int = 1024,
) -> tuple[list[int], list[float]]:
    lib = _C_LIB
    n = len(entity_ids)
    if lib is None or n == 0:
        r2 = radius * radius
        half_w = width * 0.5
        half_h = height * 0.5
        out_ids: list[int] = []
        out_d2: list[float] = []
        for i in range(n):
            dx = abs(qx - entity_x[i])
            dy = abs(qy - entity_y[i])
            if is_wrap:
                if dx > half_w: dx -= width
                if dy > half_h: dy -= height
            d2 = dx * dx + dy * dy
            if d2 <= r2:
                out_ids.append(entity_ids[i])
                out_d2.append(d2)
                if len(out_ids) >= max_out: break
        return out_ids, out_d2
    c_x = (ctypes.c_float * n)(*entity_x)
    c_y = (ctypes.c_float * n)(*entity_y)
    c_ids = (ctypes.c_int * n)(*entity_ids)
    out_ids_buf = (ctypes.c_int * max_out)()
    out_d2_buf = (ctypes.c_float * max_out)()
    found = lib.c_query_radius(
        ctypes.c_float(qx), ctypes.c_float(qy), ctypes.c_float(radius),
        c_x, c_y, c_ids, ctypes.c_int(n),
        ctypes.c_float(width), ctypes.c_float(height), ctypes.c_int(1 if is_wrap else 0),
        out_ids_buf, out_d2_buf, ctypes.c_int(max_out),
    )
    return list(out_ids_buf[:found]), list(out_d2_buf[:found])


def native_toroidal_dist_sq(ax: float, ay: float, bx: float, by: float, width: float, height: float, is_wrap: bool) -> float:
    if _C_LIB is not None:
        return float(_C_LIB.c_toroidal_dist_sq(
            ctypes.c_float(ax), ctypes.c_float(ay), ctypes.c_float(bx), ctypes.c_float(by),
            ctypes.c_float(width), ctypes.c_float(height), ctypes.c_int(1 if is_wrap else 0)))
    # pure python
    dx = abs(ax - bx); dy = abs(ay - by)
    if is_wrap:
        hw = width * 0.5; hh = height * 0.5
        if dx > hw: dx -= width
        if dy > hh: dy -= height
    return dx * dx + dy * dy


def native_segments_intersect(p1, p2, q1, q2) -> bool:
    if _C_LIB is not None:
        return bool(_C_LIB.c_segments_intersect(
            ctypes.c_float(p1[0]), ctypes.c_float(p1[1]), ctypes.c_float(p2[0]), ctypes.c_float(p2[1]),
            ctypes.c_float(q1[0]), ctypes.c_float(q1[1]), ctypes.c_float(q2[0]), ctypes.c_float(q2[1])))
    # python fallback
    def _cross(ax, ay, bx, by): return ax * by - ay * bx
    rx, ry = p2[0] - p1[0], p2[1] - p1[1]
    sx, sy = q2[0] - q1[0], q2[1] - q1[1]
    denom = _cross(rx, ry, sx, sy)
    if abs(denom) < 1e-12: return False
    qpx, qpy = q1[0] - p1[0], q1[1] - p1[1]
    t = _cross(qpx, qpy, sx, sy) / denom
    u = _cross(qpx, qpy, rx, ry) / denom
    return 0 <= t <= 1 and 0 <= u <= 1


def native_path_crosses_wall(x0: float, y0: float, x1: float, y1: float, wall_segs: list[tuple[float,float,float,float]]) -> bool:
    if not wall_segs:
        return False
    if _C_LIB is not None:
        n = len(wall_segs)
        flat = (ctypes.c_float * (n * 4))(*[c for seg in wall_segs for c in seg])
        return bool(_C_LIB.c_path_crosses_wall(
            ctypes.c_float(x0), ctypes.c_float(y0), ctypes.c_float(x1), ctypes.c_float(y1),
            flat, ctypes.c_int(n)))
    # fallback
    for seg in wall_segs:
        if native_segments_intersect((x0,y0),(x1,y1),(seg[0],seg[1]),(seg[2],seg[3])):
            return True
    return False


def native_boids_forces(x: Sequence[float], y: Sequence[float], angles: Sequence[float], clan_ids: Sequence[int], radius: float, width: float, height: float, is_wrap: bool):
    """Return separation, alignment, cohesion vectors from native core (or python fallback)."""
    n = len(x)
    if n == 0:
        return [], [], [], [], [], []
    if _C_LIB is None:
        # pure python separation fallback (slow)
        sep_x = [0.0]*n; sep_y = [0.0]*n
        half_w = width*0.5; half_h = height*0.5
        r2 = radius*radius
        for i in range(n):
            fx = fy = 0.0
            for j in range(n):
                if i==j or clan_ids[j]!=clan_ids[i]: continue
                dx = x[i]-x[j]; dy = y[i]-y[j]
                if is_wrap:
                    if dx > half_w: dx -= width
                    elif dx < -half_w: dx += width
                    if dy > half_h: dy -= height
                    elif dy < -half_h: dy += height
                d2 = dx*dx+dy*dy
                if 0.0001 < d2 < r2:
                    inv = 1.0/d2
                    fx += dx*inv; fy += dy*inv
            sep_x[i]=fx; sep_y[i]=fy
        return sep_x, sep_y, [0.0]*n, [0.0]*n, [0.0]*n, [0.0]*n
    cx = (ctypes.c_float * n)(*x); cy = (ctypes.c_float * n)(*y)
    cang = (ctypes.c_float * n)(*angles); cclan = (ctypes.c_int * n)(*clan_ids)
    sep_x = (ctypes.c_float * n)(); sep_y = (ctypes.c_float * n)()
    ali_x = (ctypes.c_float * n)(); ali_y = (ctypes.c_float * n)()
    coh_x = (ctypes.c_float * n)(); coh_y = (ctypes.c_float * n)()
    _C_LIB.c_boids_separation(cx, cy, cclan, n, ctypes.c_float(radius*radius),
                              ctypes.c_float(width), ctypes.c_float(height), ctypes.c_int(1 if is_wrap else 0),
                              sep_x, sep_y)
    _C_LIB.c_boids_alignment(cx, cy, cang, cclan, n, ctypes.c_float(radius),
                             ctypes.c_float(width), ctypes.c_float(height), ctypes.c_int(1 if is_wrap else 0),
                             ali_x, ali_y)
    _C_LIB.c_boids_cohesion(cx, cy, cclan, n, ctypes.c_float(radius),
                            ctypes.c_float(width), ctypes.c_float(height), ctypes.c_int(1 if is_wrap else 0),
                            coh_x, coh_y)
    return list(sep_x), list(sep_y), list(ali_x), list(ali_y), list(coh_x), list(coh_y)


def native_collision_sweep(x: Sequence[float], y: Sequence[float], radius: Sequence[float], ids: Sequence[int], width: float, height: float, is_wrap: bool) -> list[tuple[int,int]]:
    n = len(ids)
    if n == 0 or _C_LIB is None:
        # python fallback
        out=[]
        hw=width*0.5; hh=height*0.5
        for i in range(n):
            for j in range(i+1,n):
                dx=abs(x[i]-x[j]); dy=abs(y[i]-y[j])
                if is_wrap:
                    if dx>hw: dx=width-dx
                    if dy>hh: dy=height-dy
                rr=radius[i]+radius[j]
                if dx*dx+dy*dy < rr*rr:
                    out.append((ids[i],ids[j]))
        return out
    cx=(ctypes.c_float*n)(*x); cy=(ctypes.c_float*n)(*y); cr=(ctypes.c_float*n)(*radius); cids=(ctypes.c_int*n)(*ids)
    max_pairs=n*2
    out_buf=(ctypes.c_int*(max_pairs*2))()
    cnt=_C_LIB.c_collision_sweep(cx,cy,cr,cids,n, ctypes.c_float(width), ctypes.c_float(height), ctypes.c_int(1 if is_wrap else 0), out_buf, ctypes.c_int(max_pairs*2))
    return [(int(out_buf[i*2]), int(out_buf[i*2+1])) for i in range(min(cnt, max_pairs))]
