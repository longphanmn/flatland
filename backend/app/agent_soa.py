"""Structure of Arrays substrate — BA Step 1.2

Contiguous numpy arrays for vectorized batch execution. Falls back to
python lists when numpy is not installed.
"""

from __future__ import annotations

from typing import Optional

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    HAS_NUMPY = False


class AgentSoA:
    """SoA storage for BA neural agents.

    Attributes are numpy arrays when available, else python lists.
    """

    # BC Kmax — 64 allows circles beyond priest (K>=24 threshold)
    KMAX = 64

    def __init__(self, capacity: int, genome_size: int = 295):
        self.capacity = int(capacity)
        self.genome_size = int(genome_size)
        self.N = 0  # active count
        if HAS_NUMPY:
            self.pos = np.zeros((capacity, 2), dtype=np.float32)
            self.vel = np.zeros((capacity, 2), dtype=np.float32)
            self.angle = np.zeros((capacity,), dtype=np.float32)
            # stats: [energy, max_energy, health, chill]
            self.stats = np.zeros((capacity, 4), dtype=np.float32)
            self.hidden_state = np.zeros((capacity, 1), dtype=np.float32)
            self.genomes = np.zeros((capacity, genome_size), dtype=np.float32)
            self.active_mask = np.zeros((capacity,), dtype=np.bool_)
            self.ids = np.zeros((capacity,), dtype=np.int32) - 1
            # BC morphology buffers
            self.morph_radii = np.ones((capacity, self.KMAX), dtype=np.float32)
            self.morph_angles = np.zeros((capacity, self.KMAX), dtype=np.float32)
            # regular K=4 default for first 4 verts, rest uniform
            for k in range(self.KMAX):
                if k < 4:
                    self.morph_angles[:, k] = 2 * np.pi * k / 4
                else:
                    self.morph_angles[:, k] = 2 * np.pi * k / self.KMAX
            self.morph_k = np.full((capacity,), 4, dtype=np.int32)
            self.morph_traits = np.zeros((capacity, 6), dtype=np.float32)  # A,P,Izz,theta_min,asym,Dmult
            self.reproduction_role = np.zeros((capacity,), dtype=np.int8)
        else:
            self.pos = [[0.0, 0.0] for _ in range(capacity)]
            self.vel = [[0.0, 0.0] for _ in range(capacity)]
            self.angle = [0.0] * capacity
            self.stats = [[0.0, 0.0, 0.0, 0.0] for _ in range(capacity)]
            self.hidden_state = [[0.0] for _ in range(capacity)]
            self.genomes = [[0.0] * genome_size for _ in range(capacity)]
            self.active_mask = [False] * capacity
            self.ids = [-1] * capacity
            import math as _math
            self.morph_radii = [[1.0]*self.KMAX for _ in range(capacity)]
            # regular K=4 for first 4
            self.morph_angles = [[(2*_math.pi*k/4 if k<4 else 2*_math.pi*k/self.KMAX) for k in range(self.KMAX)] for _ in range(capacity)]
            self.morph_k = [4]*capacity
            self.morph_traits = [[0.0]*6 for _ in range(capacity)]
            self.reproduction_role = [0]*capacity

        # pre-allocated buffers for Step 5.2
        if HAS_NUMPY:
            self.inputs_buf = np.zeros((capacity, 16), dtype=np.float32)
            self.outputs_buf = np.zeros((capacity, 7), dtype=np.float32)
            self.hidden_buf = np.zeros((capacity, 1), dtype=np.float32)
        else:
            self.inputs_buf = [[0.0]*16 for _ in range(capacity)]
            self.outputs_buf = [[0.0]*7 for _ in range(capacity)]
            self.hidden_buf = [[0.0] for _ in range(capacity)]

    def add_agent(self, eid: int, x: float, y: float, angle: float = 0.0, energy: float = 80.0, max_energy: float = 100.0, health: float = 100.0, chill: float = 0.0, genome=None, morph_radii=None, morph_angles=None, morph_k: int | None = None) -> int:
        idx = self.N
        if idx >= self.capacity:
            raise RuntimeError("AgentSoA capacity exceeded")
        if HAS_NUMPY:
            self.pos[idx, 0] = x
            self.pos[idx, 1] = y
            self.angle[idx] = angle
            self.stats[idx, 0] = energy
            self.stats[idx, 1] = max_energy
            self.stats[idx, 2] = health
            self.stats[idx, 3] = chill
            self.hidden_state[idx, 0] = 0.0
            if genome is not None:
                self.genomes[idx] = genome
            self.active_mask[idx] = True
            self.ids[idx] = int(eid)
            # BC morph — init or copy
            if morph_radii is not None:
                self.morph_radii[idx, :len(morph_radii)] = morph_radii
            else:
                self.morph_radii[idx, :] = 1.0
            if morph_angles is not None:
                self.morph_angles[idx, :len(morph_angles)] = morph_angles
            else:
                # regular polygon angles for K
                _k = int(morph_k) if morph_k is not None else 4
                for ki in range(_k):
                    self.morph_angles[idx, ki] = 2 * 3.141592653589793 * ki / _k
                for ki in range(_k, self.KMAX):
                    self.morph_angles[idx, ki] = 2 * 3.141592653589793 * ki / self.KMAX
            if morph_k is not None:
                self.morph_k[idx] = int(morph_k)
            else:
                self.morph_k[idx] = 4
            self.morph_traits[idx, :] = 0.0
            self.reproduction_role[idx] = 0
        else:
            self.pos[idx] = [float(x), float(y)]
            self.vel[idx] = [0.0, 0.0]
            self.angle[idx] = float(angle)
            self.stats[idx] = [float(energy), float(max_energy), float(health), float(chill)]
            self.hidden_state[idx] = [0.0]
            if genome is not None:
                self.genomes[idx] = list(genome)
            self.active_mask[idx] = True
            self.ids[idx] = int(eid)
            if morph_radii is not None:
                for i, v in enumerate(morph_radii):
                    if i < self.KMAX:
                        self.morph_radii[idx][i] = float(v)
            else:
                for i in range(self.KMAX):
                    self.morph_radii[idx][i] = 1.0
            if morph_angles is not None:
                for i, v in enumerate(morph_angles):
                    if i < self.KMAX:
                        self.morph_angles[idx][i] = float(v)
            else:
                _k = int(morph_k) if morph_k is not None else 4
                import math as _mm
                for ki in range(self.KMAX):
                    if ki < _k:
                        self.morph_angles[idx][ki] = 2 * _mm.pi * ki / _k
                    else:
                        self.morph_angles[idx][ki] = 2 * _mm.pi * ki / self.KMAX
            if morph_k is not None:
                self.morph_k[idx] = int(morph_k)
            else:
                self.morph_k[idx] = 4
            self.morph_traits[idx] = [0.0]*6
            self.reproduction_role[idx] = 0
        self.N += 1
        return idx

    def remove_at(self, idx: int) -> None:
        last = self.N - 1
        if idx < 0 or idx >= self.N:
            return
        if HAS_NUMPY:
            if idx != last:
                self.pos[idx] = self.pos[last].copy()
                self.vel[idx] = self.vel[last].copy()
                self.angle[idx] = self.angle[last]
                self.stats[idx] = self.stats[last].copy()
                self.hidden_state[idx] = self.hidden_state[last].copy()
                self.genomes[idx] = self.genomes[last].copy()
                self.active_mask[idx] = self.active_mask[last]
                self.ids[idx] = self.ids[last]
                self.morph_radii[idx] = self.morph_radii[last].copy()
                self.morph_angles[idx] = self.morph_angles[last].copy()
                self.morph_k[idx] = self.morph_k[last]
                self.morph_traits[idx] = self.morph_traits[last].copy()
                self.reproduction_role[idx] = self.reproduction_role[last]
            self.active_mask[last] = False
            self.ids[last] = -1
        else:
            if idx != last:
                self.pos[idx] = self.pos[last][:]
                self.vel[idx] = self.vel[last][:]
                self.angle[idx] = self.angle[last]
                self.stats[idx] = self.stats[last][:]
                self.hidden_state[idx] = self.hidden_state[last][:]
                self.genomes[idx] = self.genomes[last][:]
                self.active_mask[idx] = self.active_mask[last]
                self.ids[idx] = self.ids[last]
                self.morph_radii[idx] = self.morph_radii[last][:]
                self.morph_angles[idx] = self.morph_angles[last][:]
                self.morph_k[idx] = self.morph_k[last]
                self.morph_traits[idx] = self.morph_traits[last][:]
                self.reproduction_role[idx] = self.reproduction_role[last]
            self.active_mask[last] = False
            self.ids[last] = -1
        self.N -= 1

    def active_indices(self):
        if HAS_NUMPY:
            return np.where(self.active_mask[: self.N])[0]
        return [i for i in range(self.N) if self.active_mask[i]]

    def to_dict(self, idx: int) -> dict:
        if HAS_NUMPY:
            return dict(
                id=int(self.ids[idx]),
                x=float(self.pos[idx, 0]),
                y=float(self.pos[idx, 1]),
                angle=float(self.angle[idx]),
                energy=float(self.stats[idx, 0]),
                max_energy=float(self.stats[idx, 1]),
                health=float(self.stats[idx, 2]),
                chill=float(self.stats[idx, 3]),
                hidden=float(self.hidden_state[idx, 0]),
                morph_k=int(self.morph_k[idx]),
                morph_traits=[float(v) for v in self.morph_traits[idx]],
                reproduction_role=int(self.reproduction_role[idx]),
            )
        return dict(
            id=int(self.ids[idx]),
            x=float(self.pos[idx][0]),
            y=float(self.pos[idx][1]),
            angle=float(self.angle[idx]),
            energy=float(self.stats[idx][0]),
            max_energy=float(self.stats[idx][1]),
            health=float(self.stats[idx][2]),
            chill=float(self.stats[idx][3]),
            hidden=float(self.hidden_state[idx][0]),
            morph_k=int(self.morph_k[idx]),
            morph_traits=[float(v) for v in self.morph_traits[idx]],
            reproduction_role=int(self.reproduction_role[idx]),
        )
