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


def _build_base_genome(genome_size: int = 295):
    """Construct inductive foraging template with active forward search and food-steering."""
    if HAS_NUMPY:
        base = np.zeros(genome_size, dtype=np.float32)
    else:
        base = [0.0] * genome_size

    # W1 indices: i * 12 + j
    # Unit 0 (Forward hunger drive): W1[0, 0] = -1.2, W1[5, 0] = +1.2, W1[6, 0] = +0.8
    base[0] = -1.2
    base[60] = 1.2
    base[72] = 0.8
    # Unit 1 (Left ray attraction): W1[3, 1] = +1.2, W1[4, 1] = +1.0
    base[37] = 1.2
    base[49] = 1.0
    # Unit 2 (Right ray attraction): W1[7, 2] = +1.2, W1[8, 2] = +1.0
    base[86] = 1.2
    base[98] = 1.0
    # Unit 3 (Obstacle avoidance): W1[5, 3] = +1.5, W1[6, 3] = -1.2
    base[63] = 1.5
    base[75] = -1.2

    # b1 indices: 192 + j
    base[192] = 0.8  # b1[0] forward drive bias

    # W2 indices: 204 + i * 7 + j
    base[204] = 1.5   # W2[0, 0] thrust
    base[212] = -1.8  # W2[1, 1] left steer
    base[219] = 1.8   # W2[2, 1] right steer
    base[226] = 1.2   # W2[3, 1] dodge obstacle

    # b2 indices: 288 + j
    base[288] = 0.5   # b2[0] baseline thrust
    return base


def init_genomes(soa, rng=None, loc: float = 0.0, scale: float = 0.35, clip_min: float = -4.0, clip_max: float = 4.0) -> None:
    """Initialize active genomes with foraging template + Gaussian noise N(0, scale)."""
    N = soa.N
    if N == 0:
        return
    base = _build_base_genome(soa.genome_size)
    if HAS_NUMPY:
        if isinstance(rng, int):
            gen = np.random.default_rng(rng)
        elif hasattr(rng, "normal"):
            gen = rng
        else:
            gen = np.random.default_rng(42)
        noise = gen.normal(loc=loc, scale=scale, size=(N, soa.genome_size)).astype(np.float32)
        arr = np.clip(base + noise, clip_min, clip_max)
        soa.genomes[:N] = arr
    else:
        import random as _rnd

        seed_val = rng if isinstance(rng, int) else 42
        r = _rnd.Random(seed_val)
        for n in range(N):
            for i in range(soa.genome_size):
                v = base[i] + r.gauss(loc, scale)
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
