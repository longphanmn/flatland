"""Tick decoupling — BA Step 5

Multi-rate loop: physics 60Hz, NN 15Hz, zero-alloc pre-allocated buffers.
This module is the integration point between AgentSoA / neural_engine /
agent_pipeline and the existing Simulation.step().
"""

from __future__ import annotations

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    HAS_NUMPY = False

from .agent_soa import AgentSoA
from .neural_engine import forward_batch
from .agent_pipeline import build_inputs_batch, apply_outputs_batch
from .spatial_grid import SpatialHashGrid


class NNUpdatableSimulationMixin:
    """Mixin to be applied to Simulation. Keeps nn_enabled flag and tick counter."""

    nn_enabled: bool = False
    nn_inference_hz: int = 15
    _nn_tick: int = 0
    _soa: AgentSoA | None = None
    _nn_grid: SpatialHashGrid | None = None

    def init_nn(self, capacity: int = 2000, world=None) -> None:
        if world is None:
            return
        if self._soa is None:
            self._soa = AgentSoA(capacity=capacity)
            self._nn_grid = SpatialHashGrid(width=world.config.width, height=world.config.height, cell_size=32.0, boundary=world.config.boundary)
            # sync existing creatures into SoA
            for e in world.entities.values():
                if getattr(e, "kind", None) == "creature":
                    self._soa.add_agent(int(e.id), float(e.x), float(e.y), angle=float(getattr(e, "angle", 0.0)), energy=float(getattr(e, "energy", 80.0)), health=float(getattr(e, "health", 100.0)))
            # init genomes
            from .evolution import init_genomes

            init_genomes(self._soa)

    def nn_step(self, world=None) -> None:
        """Called every tick; runs inference every 4th tick if nn_enabled."""
        if not getattr(self, "nn_enabled", False):
            return
        if self._soa is None or self._nn_grid is None:
            if world is not None:
                self.init_nn(world=world)
            return
        self._nn_tick += 1
        # 60Hz physics: always update positions from vel
        # For now, simple vel integration (pos += vel)
        if HAS_NUMPY and self._soa.N:
            self._soa.pos[: self._soa.N] += self._soa.vel[: self._soa.N]
            # sync grid
            self._nn_grid.update_positions(self._soa.ids[: self._soa.N].tolist(), self._soa.pos[: self._soa.N])
        else:
            for i in range(self._soa.N):
                self._soa.pos[i][0] += self._soa.vel[i][0]
                self._soa.pos[i][1] += self._soa.vel[i][1]
        # 15Hz inference: every 4th tick
        if self._nn_tick % 4 != 0:
            return
        # build inputs
        inputs = build_inputs_batch(self._soa, spatial_grid=self._nn_grid, world=world)
        hidden = self._soa.hidden_state[: self._soa.N] if HAS_NUMPY else [self._soa.hidden_state[i] for i in range(self._soa.N)]
        # forward
        outputs, _ = forward_batch(inputs, self._soa.genomes[: self._soa.N] if HAS_NUMPY else [self._soa.genomes[i] for i in range(self._soa.N)], hidden_state=self._soa.hidden_state[: self._soa.N] if HAS_NUMPY else None)
        apply_outputs_batch(self._soa, outputs)
        # handle mating via evolution (stub: pairs found but not yet spawned into world)
        # spawning is deferred to simulation._reproduce replacement when BA 4.2 is fully wired
