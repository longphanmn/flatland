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
        else:
            self.pos = [[0.0, 0.0] for _ in range(capacity)]
            self.vel = [[0.0, 0.0] for _ in range(capacity)]
            self.angle = [0.0] * capacity
            self.stats = [[0.0, 0.0, 0.0, 0.0] for _ in range(capacity)]
            self.hidden_state = [[0.0] for _ in range(capacity)]
            self.genomes = [[0.0] * genome_size for _ in range(capacity)]
            self.active_mask = [False] * capacity
            self.ids = [-1] * capacity

        # pre-allocated buffers for Step 5.2
        if HAS_NUMPY:
            self.inputs_buf = np.zeros((capacity, 16), dtype=np.float32)
            self.outputs_buf = np.zeros((capacity, 7), dtype=np.float32)
            self.hidden_buf = np.zeros((capacity, 1), dtype=np.float32)
        else:
            self.inputs_buf = [[0.0]*16 for _ in range(capacity)]
            self.outputs_buf = [[0.0]*7 for _ in range(capacity)]
            self.hidden_buf = [[0.0] for _ in range(capacity)]

    def add_agent(self, eid: int, x: float, y: float, angle: float = 0.0, energy: float = 80.0, max_energy: float = 100.0, health: float = 100.0, chill: float = 0.0, genome=None) -> int:
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
        )
