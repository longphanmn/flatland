"""World and simulation configuration."""

import os
from dataclasses import dataclass


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    return cast(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Config:
    # World geometry (grid units) — 200x200 = 4x the original 100x100 area
    width: float = 200.0
    height: float = 200.0
    boundary: str = "wrap"  # "wrap" | "clamp"

    # Simulation
    seed: int = 42
    tick_rate: float = 10.0  # ticks per second

    # Initial population (Flatland castes).
    # -1 => auto-scale from map area × density with ±spawn_variance jitter;
    # any value >= 0 pins that group explicitly (used by tests/scenarios).
    num_triangles: int = -1  # soldiers/workmen (isosceles triangles)
    num_squares: int = -1  # gentlemen
    num_pentagons: int = -1  # professionals
    num_hexagons: int = -1  # nobility
    num_priests: int = -1  # near-circles (priesthood)
    num_women: int = -1  # line segments
    num_houses: int = -1

    # World generation densities (per grid unit²) and spawn jitter.
    creature_density: float = 0.0005  # ~20 creatures on a 200×200 map
    house_density: float = 0.00015  # ~6 houses
    spawn_variance: float = 0.25  # ±25% around the density target

    food_count: int = 24  # god's law: the world maintains this much food

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
    lifespan_mult: float = 1.0  # god's law: scale every caste's natural lifespan

    # Reproduction & inheritance (Nature's Law)
    birth_enabled: bool = True
    adult_age: float = 600.0  # ticks before a creature may mate
    mate_radius: float = 3.0  # max distance between parents
    mate_energy_min: float = 50.0  # both parents must hold this much energy
    birth_rate: float = 0.15  # chance per eligible pair per tick (× fertility)
    sex_ratio: float = 0.5  # probability a child is a son
    mutation_rate: float = 0.05  # chance a son's side count deviates ±1
    max_sides: int = 24  # sons stop gaining sides here (= Circle)
    birth_energy_cost: float = 25.0  # each parent pays
    reproduction_cooldown: int = 300  # ticks both parents wait after a birth
    carrying_capacity: int = 60  # soft cap: fertility fades above it
    max_population: int = 120  # hard cap: no births beyond it

    # Houses
    house_min_size: float = 6.0
    house_max_size: float = 10.0
    door_clearance: float = 1.5  # door width = clearance * largest creature diameter

    # Chronicle
    history_max: int = 200  # death events kept in the chronicle

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            width=_env("FLATWORLD_WIDTH", float, 200.0),
            height=_env("FLATWORLD_HEIGHT", float, 200.0),
            boundary=_env("FLATWORLD_BOUNDARY", str, "wrap"),
            seed=_env("FLATWORLD_SEED", int, 42),
            tick_rate=_env("FLATWORLD_TICK_RATE", float, 10.0),
        )

    @property
    def tick_interval(self) -> float:
        return 1.0 / self.tick_rate if self.tick_rate > 0 else 0.1
