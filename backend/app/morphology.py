"""BC Geometric Physics — polar polygon traits & trait baking.

Vectorized batch with numpy fallback. Zero-alloc tick when disabled.
"""
from __future__ import annotations

import math
from typing import Optional

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    HAS_NUMPY = False

KMAX = 64
R_MIN, R_MAX = 0.2, 2.5

# Reference square Gentleman r=1.0 K=4 — Aref=2, Pref≈5.657, Iref≈0.333 for unit
# Compute via shoelace for regular 4-gon: vertices at 45° increments radius 1 -> area 2
A_REF = 2.0
P_REF = 4 * math.sqrt(2)  # ≈5.65685
I_REF = 2.0 / 3.0  # approx for square side sqrt2


def compute_polygon_vertices(r, phi, k: int):
    """Single polygon polar -> cart. r,phi arrays length KMAX, only k active."""
    import math as _m

    xs = []
    ys = []
    for i in range(k):
        ri = float(r[i]) if hasattr(r, "__getitem__") else float(r)
        ph = float(phi[i]) if hasattr(phi, "__getitem__") else float(phi)
        xs.append(ri * _m.cos(ph))
        ys.append(ri * _m.sin(ph))
    return xs, ys


def _shoelace_single(xs, ys, k: int) -> float:
    s = 0.0
    for i in range(k):
        j = (i + 1) % k
        s += xs[i] * ys[j] - xs[j] * ys[i]
    return abs(s) * 0.5


def _perimeter_single(xs, ys, k: int) -> float:
    p = 0.0
    for i in range(k):
        j = (i + 1) % k
        dx = xs[j] - xs[i]
        dy = ys[j] - ys[i]
        p += math.hypot(dx, dy)
    return p


def _inertia_single(xs, ys, k: int, area: float) -> float:
    # Polar moment about centroid: approximation via shoelace inertia formula
    # I = (1/(12*area)) * sum cross*(x_i^2 + x_i*x_j + x_j^2 + y_i^2 + y_i*y_j + y_j^2) * cross
    # Fallback to area-proportional if degenerate
    if area < 1e-6:
        return 0.0
    s = 0.0
    for i in range(k):
        j = (i + 1) % k
        cross = xs[i] * ys[j] - xs[j] * ys[i]
        s += cross * (xs[i] * xs[i] + xs[i] * xs[j] + xs[j] * xs[j] + ys[i] * ys[i] + ys[i] * ys[j] + ys[j] * ys[j])
    return abs(s) / (12 * area + 1e-9)


def _min_angle_single(xs, ys, k: int) -> float:
    # interior angle at each vertex via adjacent edge vectors
    best = math.pi
    for i in range(k):
        im1 = (i - 1) % k
        ip1 = (i + 1) % k
        ux = xs[im1] - xs[i]
        uy = ys[im1] - ys[i]
        vx = xs[ip1] - xs[i]
        vy = ys[ip1] - ys[i]
        nu = math.hypot(ux, uy)
        nv = math.hypot(vx, vy)
        if nu < 1e-9 or nv < 1e-9:
            continue
        cosv = (ux * vx + uy * vy) / (nu * nv)
        cosv = max(-1.0, min(1.0, cosv))
        ang = math.acos(cosv)
        if ang < best:
            best = ang
    return best if best != math.pi else math.pi * 0.5


def _asymmetry_single(r, k: int) -> float:
    if k <= 0:
        return 0.0
    vals = [float(r[i]) for i in range(k)]
    mean = sum(vals) / k
    if mean < 1e-9:
        return 0.0
    var = sum((v - mean) ** 2 for v in vals) / k
    return var / mean


def batch_compute_traits(morph_radii, morph_angles, morph_k, out_traits=None):
    """Compute (N,6) traits for all active. Numpy vectorized when possible, else python fallback.

    Returns out_traits or new array (numpy) / list (python).
    """
    if HAS_NUMPY and isinstance(morph_radii, np.ndarray):
        N = morph_radii.shape[0]
        if out_traits is None:
            out_traits = np.zeros((N, 6), dtype=np.float32)
        for idx in range(N):
            k = int(morph_k[idx]) if hasattr(morph_k, "__getitem__") else int(morph_k)
            if k < 3:
                out_traits[idx, :] = 0
                continue
            r = morph_radii[idx]
            phi = morph_angles[idx]
            xs = r[:k] * np.cos(phi[:k])  # type: ignore
            ys = r[:k] * np.sin(phi[:k])  # type: ignore
            # shoelace
            # rolled
            x_next = np.roll(xs, -1)
            y_next = np.roll(ys, -1)
            area = float(np.abs(np.sum(xs * y_next - x_next * ys)) * 0.5)
            # perimeter
            dx = x_next - xs
            dy = y_next - ys
            perim = float(np.sum(np.sqrt(dx * dx + dy * dy)))
            # inertia
            cross = xs * y_next - x_next * ys
            # avoid div by zero
            if area > 1e-6:
                inertia = float(np.abs(np.sum(cross * (xs * xs + xs * x_next + x_next * x_next + ys * ys + ys * y_next + y_next * y_next))) / (12 * area))
            else:
                inertia = 0.0
            # min angle
            # compute per vertex via vectorized loop (k<=64, python loop cheap)
            best = math.pi
            for i in range(k):
                im1 = (i - 1) % k
                ip1 = (i + 1) % k
                ux = float(xs[im1] - xs[i])
                uy = float(ys[im1] - ys[i])
                vx = float(xs[ip1] - xs[i])
                vy = float(ys[ip1] - ys[i])
                nu = math.hypot(ux, uy)
                nv = math.hypot(vx, vy)
                if nu < 1e-9 or nv < 1e-9:
                    continue
                cosv = (ux * vx + uy * vy) / (nu * nv)
                cosv = max(-1.0, min(1.0, cosv))
                ang = math.acos(cosv)
                if ang < best:
                    best = ang
            theta = best if best != math.pi else math.pi * 0.5
            # asymmetry
            rk = r[:k]
            mean_r = float(np.mean(rk))
            var_r = float(np.var(rk))
            asym = (var_r / mean_r) if mean_r > 1e-9 else 0.0
            # Dmult
            # D = max(0,(cos theta - cos60)/(1 - cos60)), cos60=0.5
            cos_theta = math.cos(theta)
            dmult = max(0.0, (cos_theta - 0.5) / 0.5)
            out_traits[idx, 0] = area
            out_traits[idx, 1] = perim
            out_traits[idx, 2] = inertia
            out_traits[idx, 3] = theta
            out_traits[idx, 4] = asym
            out_traits[idx, 5] = dmult
        return out_traits
    else:
        # python fallback
        N = len(morph_radii)
        if out_traits is None:
            out_traits = [[0.0] * 6 for _ in range(N)]
        for idx in range(N):
            k = int(morph_k[idx])
            if k < 3:
                out_traits[idx] = [0.0] * 6
                continue
            r = morph_radii[idx]
            phi = morph_angles[idx]
            xs, ys = compute_polygon_vertices(r, phi, k)
            area = _shoelace_single(xs, ys, k)
            perim = _perimeter_single(xs, ys, k)
            inertia = _inertia_single(xs, ys, k, area)
            theta = _min_angle_single(xs, ys, k)
            asym = _asymmetry_single(r, k)
            cos_theta = math.cos(theta)
            dmult = max(0.0, (cos_theta - 0.5) / 0.5)
            out_traits[idx][0] = area
            out_traits[idx][1] = perim
            out_traits[idx][2] = inertia
            out_traits[idx][3] = theta
            out_traits[idx][4] = asym
            out_traits[idx][5] = dmult
        return out_traits


def bake_traits_for_index(idx: int, soa, config=None) -> dict:
    """Bake single index morph_traits and return baked physics dict.

    Applies caps 0.5-2.0 area, 0.7-1.8 perimeter per BC.2 spec.
    """
    if HAS_NUMPY and hasattr(soa.morph_radii, "shape"):
        k = int(soa.morph_k[idx])
        r = soa.morph_radii[idx]
        phi = soa.morph_angles[idx]
        # compute via batch helper for one
        traits = batch_compute_traits(soa.morph_radii[idx : idx + 1], soa.morph_angles[idx : idx + 1], soa.morph_k[idx : idx + 1])
        area, perim, izz, theta, asym, dmult = [float(v) for v in traits[0]]
        soa.morph_traits[idx, :] = traits[0]
    else:
        k = int(soa.morph_k[idx])
        r = soa.morph_radii[idx]
        phi = soa.morph_angles[idx]
        xs, ys = compute_polygon_vertices(r, phi, k)
        area = _shoelace_single(xs, ys, k)
        perim = _perimeter_single(xs, ys, k)
        izz = _inertia_single(xs, ys, k, area)
        theta = _min_angle_single(xs, ys, k)
        asym = _asymmetry_single(r, k)
        dmult = max(0.0, (math.cos(theta) - 0.5) / 0.5)
        soa.morph_traits[idx] = [area, perim, izz, theta, asym, dmult]
        area, perim, izz, theta, asym, dmult = area, perim, izz, theta, asym, dmult

    # trait baking caps
    emax_scale = max(0.5, min(2.0, (area / A_REF) if A_REF else 1.0))
    decay_scale = max(0.7, min(1.8, (perim / P_REF) if P_REF else 1.0))
    # steering resistance handled elsewhere: Δθ = steer * (steer_turn/(1+I/Iref))
    # asymmetry -> irregularity mapping
    irregularity = max(0.0, min(1.0, asym * 1.5))  # scale so asym 0.46 -> 0.7 threshold
    baked = {
        "area": area,
        "perimeter": perim,
        "izz": izz,
        "theta_min": theta,
        "asymmetry": asym,
        "dmult": dmult,
        "emax_scale": emax_scale,
        "decay_scale": decay_scale,
        "irregularity": irregularity,
    }
    return baked


def sat_overlap(ax, ay, bx, by) -> bool:
    """SAT for convex polygons (ax,ay) and (bx,by) lists."""
    import math as _m

    ka = len(ax)
    kb = len(bx)
    if ka < 3 or kb < 3:
        return False

    def poly_axes(xs, ys):
        k = len(xs)
        a = []
        for i in range(k):
            j = (i + 1) % k
            ex = xs[j] - xs[i]
            ey = ys[j] - ys[i]
            nx, ny = -ey, ex
            l = _m.hypot(nx, ny)
            if l > 1e-9:
                a.append((nx / l, ny / l))
        return a

    axes_a = poly_axes(ax, ay)
    axes_b = poly_axes(bx, by)
    for nx, ny in axes_a + axes_b:
        min_a = max_a = ax[0] * nx + ay[0] * ny
        for i in range(1, ka):
            p = ax[i] * nx + ay[i] * ny
            if p < min_a:
                min_a = p
            if p > max_a:
                max_a = p
        min_b = max_b = bx[0] * nx + by[0] * ny
        for i in range(1, kb):
            p = bx[i] * nx + by[i] * ny
            if p < min_b:
                min_b = p
            if p > max_b:
                max_b = p
        if max_a < min_b - 1e-9 or max_b < min_a - 1e-9:
            return False
    return True
