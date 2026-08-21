"""World and simulation configuration."""

import os
from dataclasses import dataclass


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    return cast(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Config:
    # World geometry (grid units)
    width: float = 100.0
    height: float = 100.0
    boundary: str = "wrap"  # "wrap" | "clamp"

    # Simulation
    seed: int = 42
    tick_rate: float = 10.0  # ticks per second

    # Initial population (Flatland castes)
    num_triangles: int = 6  # soldiers / workmen (isosceles triangles)
    num_squares: int = 4  # gentlemen
    num_pentagons: int = 2  # professionals
    num_hexagons: int = 2  # nobility
    num_priests: int = 1  # near-circles (priesthood)
    num_women: int = 5  # line segments
    num_food: int = 24
    num_houses: int = 6

    # Behaviour tuning
    perceive_radius: float = 12.0
    eat_radius: float = 1.4
    energy_max: float = 100.0
    energy_start: float = 80.0
    energy_decay_per_tick: float = 0.08
    energy_from_food: float = 30.0
    wander_turn: float = 0.35  # max heading change (rad) when wandering
    steer_turn: float = 0.45  # max heading change when steering to food

    # Life / hunger
    hungry_ratio: float = 0.35  # energy/max at or below -> hungry
    starving_ratio: float = 0.15  # energy/max at or below -> starving
    hungry_perceive_mult: float = 1.3  # hungry creatures notice food farther away
    desperate_perceive_mult: float = 1.6  # starving: even farther
    desperate_speed_mult: float = 1.35  # starving: move faster

    # Houses
    house_min_size: float = 6.0
    house_max_size: float = 10.0
    door_clearance: float = 1.5  # door width = clearance * largest creature diameter

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            width=_env("FLATWORLD_WIDTH", float, 100.0),
            height=_env("FLATWORLD_HEIGHT", float, 100.0),
            boundary=_env("FLATWORLD_BOUNDARY", str, "wrap"),
            seed=_env("FLATWORLD_SEED", int, 42),
            tick_rate=_env("FLATWORLD_TICK_RATE", float, 10.0),
        )

    @property
    def tick_interval(self) -> float:
        return 1.0 / self.tick_rate if self.tick_rate > 0 else 0.1
