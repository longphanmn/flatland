"""Density-Dependent Soft-Cap Damping Engine — Phase 4.

Implements non-linear homeostatic damping xi(N) for overpopulation.
Runs at 1 Hz, zero-alloc when disabled.
"""

from __future__ import annotations

import math
from typing import Dict


def compute_xi(N: int, Kcap: int, enabled: bool) -> float:
    """Overpopulation stress index xi(N).

    xi = (N - Kcap)/Kcap if N > Kcap and soft_cap_enabled else 0
    """
    if not enabled:
        return 0.0
    try:
        if N <= Kcap:
            return 0.0
        return (float(N) - float(Kcap)) / float(Kcap)
    except Exception:
        return 0.0


def scales_for_xi(xi: float, config) -> Dict[str, float]:
    """Compute 4-channel damping scales for xi."""
    try:
        damping = float(getattr(config, "damping_steepness", 6.0))
        crowding = float(getattr(config, "crowding_stress_mult", 0.35))
        resource = float(getattr(config, "resource_strain_mult", 1.2))
    except Exception:
        damping = 6.0
        crowding = 0.35
        resource = 1.2

    # Channel 1: reproductive suppression
    birth_rate_eff = 1.0 / (1.0 + damping * xi * xi) if xi else 1.0
    birth_cost_eff = 1.0 + 1.5 * xi
    cooldown_eff = 1.0 + 2.0 * xi

    # Channel 2: crowding stress
    decay_eff = 1.0 + crowding * xi

    # Channel 3: ecological strain
    growth_eff = 1.0 / (1.0 + resource * xi) if xi else 1.0
    spread_eff = 1.0 / (1.0 + 2.0 * xi) if xi else 1.0

    # Channel 4: social friction (pathogens)
    outbreak_eff = 1.0 + 3.0 * xi

    return {
        "birth_rate_eff": birth_rate_eff,
        "birth_cost_eff": birth_cost_eff,
        "cooldown_eff": cooldown_eff,
        "decay_eff": decay_eff,
        "growth_eff": growth_eff,
        "spread_eff": spread_eff,
        "outbreak_eff": outbreak_eff,
        "xi": xi,
    }


class DensityDampingEngine:
    """1 Hz engine for xi(N) and scales."""

    def __init__(self, config):
        self.config = config
        self.last_xi = 0.0
        self.last_scales: Dict[str, float] = {}
        self.last_N = 0

    def update(self, N: int, tick: int) -> tuple[float, Dict[str, float]]:
        Kcap = int(getattr(self.config, "carrying_capacity", 350))
        enabled = bool(getattr(self.config, "soft_cap_enabled", True))
        xi = compute_xi(N, Kcap, enabled)
        scales = scales_for_xi(xi, self.config)
        self.last_xi = xi
        self.last_scales = scales
        self.last_N = N
        return xi, scales
