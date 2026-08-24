"""Native C acceleration bridge (Phase 3 AJ) with pure Python fallback.

Provides compiled SIMD/C99 speedups for spatial queries and vector math.
"""

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

_C_LIB: ctypes.CDLL | None = None
_LIB_DIR = Path(__file__).resolve().parent
_SRC_PATH = _LIB_DIR / "flatland_core.c"
_LIB_PATH = _LIB_DIR / ("_flatland_core.dylib" if sys.platform == "darwin" else "_flatland_core.so")


def _compile_native_core() -> bool:
    """Attempt to compile flatland_core.c using clang or gcc if available."""
    if not _SRC_PATH.exists():
        return False
    # If binary exists and is newer than source, we're good
    if _LIB_PATH.exists() and _LIB_PATH.stat().st_mtime >= _SRC_PATH.stat().st_mtime:
        return True
    cc = os.environ.get("CC", "clang" if sys.platform == "darwin" else "gcc")
    cmd = [
        cc,
        "-O3",
        "-shared",
        "-fPIC",
        "-Wall",
        str(_SRC_PATH),
        "-o",
        str(_LIB_PATH),
        "-lm",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=10)
        return res.returncode == 0 and _LIB_PATH.exists()
    except Exception:
        return False


def _init_native_lib() -> ctypes.CDLL | None:
    global _C_LIB
    if _C_LIB is not None:
        return _C_LIB
    try:
        if _compile_native_core():
            lib = ctypes.CDLL(str(_LIB_PATH))
            # Set up function prototypes
            lib.c_query_radius.argtypes = [
                ctypes.c_float, ctypes.c_float, ctypes.c_float,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
            ]
            lib.c_query_radius.restype = ctypes.c_int

            lib.c_boids_separation.argtypes = [
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int,
                ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
            ]
            lib.c_boids_separation.restype = None

            _C_LIB = lib
            return _C_LIB
    except Exception:
        _C_LIB = None
    return None


_init_native_lib()


def is_native_available() -> bool:
    """Returns True if the compiled C acceleration library is loaded."""
    return _C_LIB is not None


def native_query_radius(
    qx: float, qy: float, radius: float,
    entity_x: Sequence[float], entity_y: Sequence[float], entity_ids: Sequence[int],
    width: float, height: float, is_wrap: bool,
    max_out: int = 1024,
) -> tuple[list[int], list[float]]:
    """C-accelerated spatial query radius."""
    lib = _C_LIB
    n = len(entity_ids)
    if lib is None or n == 0:
        # Pure Python fallback
        r2 = radius * radius
        half_w = width * 0.5
        half_h = height * 0.5
        out_ids = []
        out_d2 = []
        for i in range(n):
            dx = abs(qx - entity_x[i])
            dy = abs(qy - entity_y[i])
            if is_wrap:
                if dx > half_w:
                    dx -= width
                if dy > half_h:
                    dy -= height
            d2 = dx * dx + dy * dy
            if d2 <= r2:
                out_ids.append(entity_ids[i])
                out_d2.append(d2)
                if len(out_ids) >= max_out:
                    break
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
