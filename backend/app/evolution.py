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


# BH-5 block-specific and BH-6 inversion
_SENSORY_IDX = set(range(0, 192))          # W1 16*12
_MOTOR_IDX = set(range(204, 288))          # W2 12*7
_REC_IDX = set(list(range(192, 204)) + list(range(288, 295)))  # b1+b2

def crossover_mutate_blockwise(parent_a, parent_b, rng=None, clip_min: float = -4.0, clip_max: float = 4.0):
    """BH-5 uniform crossover + block-specific Gaussian mutation + BH-6 0.5% sign-flip inversion."""
    # block rates
    block_p = {"sensory": 0.03, "motor": 0.05, "rec": 0.02}
    block_sigma = {"sensory": 0.06, "motor": 0.10, "rec": 0.04}
    if HAS_NUMPY and isinstance(parent_a, np.ndarray):
        N_genes = parent_a.shape[0]
        # crossover mask (numpy path)
        try:
            import numpy as _np  # type: ignore
            if rng is not None and hasattr(rng, "random") and hasattr(rng, "integers"):
                # numpy Generator
                mask = rng.random(N_genes) < 0.5
            elif rng is not None and hasattr(rng, "random"):
                # python Random — generate via list comp then array
                mask = _np.array([rng.random() < 0.5 for _ in range(N_genes)], dtype=bool)
            else:
                mask = _np.random.random(N_genes) < 0.5
        except Exception:
            import numpy as _np  # type: ignore
            mask = _np.random.random(N_genes) < 0.5
        child = np.where(mask, parent_a, parent_b).astype(np.float32)
        # blockwise mutation
        for idx_set, key in [(_SENSORY_IDX, "sensory"), (_MOTOR_IDX, "motor"), (_REC_IDX, "rec")]:
            p = block_p[key]; s = block_sigma[key]
            try:
                if rng is not None and hasattr(rng, "random") and hasattr(rng, "normal"):
                    # attempt numpy Generator path per block
                    mut_mask = rng.random(N_genes) < p
                    noise = rng.normal(0.0, s, size=N_genes).astype(np.float32)
                elif rng is not None and hasattr(rng, "random"):
                    mut_mask = np.array([rng.random() < p for _ in range(N_genes)], dtype=bool)
                    noise = np.array([rng.gauss(0, s) for _ in range(N_genes)], dtype=np.float32)
                else:
                    mut_mask = _np.random.random(N_genes) < p
                    noise = _np.random.normal(0.0, s, size=N_genes).astype(np.float32)
            except Exception:
                mut_mask = _np.random.random(N_genes) < p
                noise = _np.random.normal(0.0, s, size=N_genes).astype(np.float32)
            # only apply to indices in block
            idx_arr = np.array(list(idx_set), dtype=int)
            # filter idx within N_genes
            idx_arr = idx_arr[idx_arr < N_genes]
            child[idx_arr] = child[idx_arr] + mut_mask[idx_arr].astype(np.float32) * noise[idx_arr]
        child = np.clip(child, clip_min, clip_max)
        # BH-6 behavioral inversion 0.5% sign-flip
        try:
            do_inv = False
            if rng is not None and hasattr(rng, "random"):
                do_inv = rng.random() < 0.005
            else:
                import numpy as _np
                do_inv = _np.random.random() < 0.005
            if do_inv:
                import numpy as _np
                k = _np.random.randint(5, 11)  # 5-10 genes
                sensory_list = list(_SENSORY_IDX)
                chosen = _np.random.choice(sensory_list, size=min(k, len(sensory_list)), replace=False)
                child[chosen] = -child[chosen]
        except Exception:
            pass
        return child
    # pure python
    import random as _rnd
    r = rng if rng is not None else _rnd
    child = []
    for i, (a, b) in enumerate(zip(parent_a, parent_b)):
        v = a if (r.random() < 0.5 if hasattr(r, "random") else _rnd.random() < 0.5) else b
        # determine block
        if i in _SENSORY_IDX:
            p, s = 0.03, 0.06
        elif i in _MOTOR_IDX:
            p, s = 0.05, 0.10
        elif i in _REC_IDX:
            p, s = 0.02, 0.04
        else:
            p, s = 0.03, 0.06
        if (r.random() < p if hasattr(r, "random") else _rnd.random() < p):
            v += (r.gauss(0, s) if hasattr(r, "gauss") else _rnd.gauss(0, s))
            if v < clip_min:
                v = clip_min
            elif v > clip_max:
                v = clip_max
        child.append(float(v))
    # BH-6 inversion pure python
    try:
        if (r.random() < 0.005 if hasattr(r, "random") else _rnd.random() < 0.005):
            import random as __rnd
            k = __rnd.randint(5, 10)
            sensory_list = list(_SENSORY_IDX)
            for _ in range(k):
                idx = r.choice(sensory_list) if hasattr(r, "choice") else __rnd.choice(sensory_list)
                if 0 <= idx < len(child):
                    child[idx] = -child[idx]
    except Exception:
        pass
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
