"""Neuroevolution engine — BA Step 4

Population init + mating (uniform crossover, Gaussian mutation).
Keeps lineage fields for genealogy compatibility.
"""

from __future__ import annotations

import random

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    HAS_NUMPY = False


def init_genomes(soa, rng=None, loc: float = 0.0, scale: float = 0.5, clip_min: float = -4.0, clip_max: float = 4.0) -> None:
    """Initialize active genomes with N(0,0.5) clipped to [-4,4]."""
    N = soa.N
    if N == 0:
        return
    if HAS_NUMPY:
        if rng is None:
            rng = np.random.default_rng(42)
        # rng may be np Generator or python random
        if hasattr(rng, "normal"):
            arr = rng.normal(loc=loc, scale=scale, size=(N, soa.genome_size)).astype(np.float32)
        else:
            arr = np.random.normal(loc=loc, scale=scale, size=(N, soa.genome_size)).astype(np.float32)
        arr = np.clip(arr, clip_min, clip_max)
        soa.genomes[:N] = arr
    else:
        import random as _rnd

        r = rng if rng is not None else _rnd
        for n in range(N):
            for i in range(soa.genome_size):
                v = r.gauss(loc, scale) if hasattr(r, "gauss") else _rnd.gauss(loc, scale)
                if v < clip_min:
                    v = clip_min
                elif v > clip_max:
                    v = clip_max
                soa.genomes[n][i] = v


def crossover_mutate(parent_a, parent_b, rng=None, p_mut: float = 0.03, sigma: float = 0.08, clip_min: float = -4.0, clip_max: float = 4.0):
    """Uniform crossover + per-gene Gaussian mutation.

    Returns child genome (numpy array or list).
    """
    if HAS_NUMPY and isinstance(parent_a, np.ndarray):
        N_genes = parent_a.shape[0]
        if rng is not None and hasattr(rng, "random"):
            mask = rng.random(N_genes) < 0.5
        else:
            import numpy as _np

            mask = _np.random.random(N_genes) < 0.5
        child = np.where(mask, parent_a, parent_b).astype(np.float32) if HAS_NUMPY else None
        # mutation
        if rng is not None and hasattr(rng, "random"):
            mut_mask = rng.random(N_genes) < p_mut
            noise = rng.normal(0.0, sigma, size=N_genes).astype(np.float32)
        else:
            mut_mask = np.random.random(N_genes) < p_mut
            noise = np.random.normal(0.0, sigma, size=N_genes).astype(np.float32)
        child = child + mut_mask.astype(np.float32) * noise
        child = np.clip(child, clip_min, clip_max)
        return child
    # pure python lists
    child = []
    import random as _rnd

    r = rng if rng is not None else _rnd
    for a, b in zip(parent_a, parent_b):
        v = a if (r.random() < 0.5 if hasattr(r, "random") else _rnd.random() < 0.5) else b
        if (r.random() < p_mut if hasattr(r, "random") else _rnd.random() < p_mut):
            v += (r.gauss(0, sigma) if hasattr(r, "gauss") else _rnd.gauss(0, sigma))
            if v < clip_min:
                v = clip_min
            elif v > clip_max:
                v = clip_max
        child.append(float(v))
    return child


def find_mating_pairs(soa, spatial_grid, mate_energy_min: float = 30.0, social_thresh: float = 0.5, max_pairs: int = 32):
    """Eligible pairs: energy > min and social output > 0.5 and within radius."""
    pairs = []
    N = soa.N
    if N < 2:
        return pairs
    # need outputs_buf social channel = 3
    try:
        if HAS_NUMPY:
            social = soa.outputs_buf[:N, 3]
            energy = soa.stats[:N, 0]
            eligible = [i for i in range(N) if float(energy[i]) > mate_energy_min and float(social[i]) > social_thresh and bool(soa.active_mask[i])]
        else:
            eligible = [i for i in range(N) if soa.stats[i][0] > mate_energy_min and soa.outputs_buf[i][3] > social_thresh and soa.active_mask[i]]
    except Exception:
        return pairs
    if len(eligible) < 2:
        return pairs
    # spatial check: for each eligible, query neighbors within 10
    for idx in eligible:
        if len(pairs) >= max_pairs:
            break
        x = float(soa.pos[idx, 0]) if HAS_NUMPY else float(soa.pos[idx][0])
        y = float(soa.pos[idx, 1]) if HAS_NUMPY else float(soa.pos[idx][1])
        neigh = spatial_grid.query_radius(x, y, 10.0) if spatial_grid else []
        # map entity ids to soa indices via ids array
        for nid in neigh:
            # find index of nid
            try:
                if HAS_NUMPY:
                    # linear scan (N<=2000, ok)
                    j = int(np.where(soa.ids[:N] == nid)[0][0]) if N else -1
                else:
                    j = soa.ids.index(nid) if nid in soa.ids else -1
            except Exception:
                j = -1
            if j == -1 or j == idx or j not in eligible:
                continue
            # ensure pair not already added (unordered)
            if (j, idx) in pairs or (idx, j) in pairs:
                continue
            pairs.append((idx, j))
            break
    return pairs
