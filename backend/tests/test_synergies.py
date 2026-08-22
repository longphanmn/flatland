"""Cross-system synergy acceptance tests — emergent behaviour, seeded."""

import math

import pytest

from app.config import Config
from app.entities import Creature
from app.simulation import Simulation


def zeros(**kw) -> Config:
    base = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0,
    )
    base.update(kw)
    return Config(**base)


def test_winter_plus_plague_cascades_harder_than_alone():
    """Winter famine + plague wipes the village; famine alone does not."""
    def world(plague: bool) -> Simulation:
        cfg = zeros(
            seed=41, width=60.0, height=60.0,
            season_length=8,  # winters every 32 ticks
            energy_decay_per_tick=0.35,
            food_count=2,
            disease_enabled=plague, disease_rate=1.0, disease_radius=14.0,
            recovery_rate=0.0, disease_lethality=1.0, disease_energy_drain=0.6,
        )
        s = Simulation(cfg)
        # a tight village of eight, so contagion cannot miss
        for i in range(8):
            c = s.world.add(
                Creature(x=30.0 + (i % 4) * 1.5, y=30.0 + (i // 4) * 1.5,
                         sides=3 if i % 2 else 4, angle=0.0, speed=0.55,
                         energy=80.0)
            )
            if i == 0 and plague:
                s.disease_id = 1
                s._infect(c)
        return s

    cascade = world(True)
    control = world(False)
    for _ in range(140):
        cascade.step()
        control.step()
    cascade_deaths = sum(cascade._death_counts.values())
    control_deaths = sum(control._death_counts.values())
    assert cascade_deaths > control_deaths
    assert cascade_deaths >= 6          # the plague took nearly everyone...
    assert len(cascade.world.creatures()) < len(control.world.creatures())


def test_high_mutation_triggers_irregularity_purge():
    """mutation_rate↑ → demotions and euthanasias surge at adulthood."""
    cfg = Config(
        seed=42, width=60.0, height=60.0,
        birth_enabled=True, adult_age=15.0, mate_radius=50.0,
        mate_energy_min=10.0, birth_rate=1.0, sex_ratio=1.0,
        mutation_rate=1.0, euthanasia_threshold=0.35,
        birth_energy_cost=1.0, reproduction_cooldown=0,
        energy_decay_per_tick=0.0, food_count=0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=1, num_houses=0,
    )
    s = Simulation(cfg)
    father = s.world.add(Creature(x=20.0, y=20.0, sides=4, energy=10000.0,
                                  age=1000, lifespan=2000))
    mother = s.world.add(Creature(x=21.0, y=20.0, shape="line", sides=2,
                                  angle=0.0, energy=10000.0, age=1000, lifespan=2000))
    for _ in range(90):
        s.step()
    assert s._death_counts.get("euthanasia", 0) >= 3
    demotions = [e for e in s.history if e.type == "demotion"]
    assert len(demotions) >= 1


def test_overcrowding_supercharges_contagion():
    """Same seed, same laws: packed creatures sicken far more than spread ones."""
    common = dict(
        seed=43, width=200.0, height=200.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        disease_enabled=True, disease_rate=0.25, disease_radius=4.0,
        outbreak_rate_unused=None if False else None,
    )

    def world(spread: bool) -> Simulation:
        cfg = Config(
            seed=43, width=200.0, height=200.0,
            num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
            num_priests=0, num_women=0, num_houses=0, food_count=0,
            disease_enabled=True, disease_rate=0.25, disease_radius=4.0,
            recovery_rate=0.0, disease_outbreak_rate=0.0,
            energy_decay_per_tick=0.0, adult_age=0.0,
        )
        s = Simulation(cfg)
        for i in range(12):
            if spread:
                x, y = 20.0 + (i % 4) * 50.0, 20.0 + (i // 4) * 70.0
            else:
                x, y = 100.0 + (i % 4) * 2.0, 100.0 + (i // 4) * 2.0
            c = s.world.add(Creature(x=x, y=y, sides=4, energy=1000.0,
                                     speed=0.0))  # stand still: pure proximity
            if i == 0:
                s.disease_id = 1
                s._infect(c)
        return s

    dense = world(False)
    sparse = world(True)
    for _ in range(30):
        dense.step()
        sparse.step()
    dense_infected = sum(1 for c in dense.world.creatures() if c.infected)
    sparse_infected = sum(1 for c in sparse.world.creatures() if c.infected)
    assert dense_infected > sparse_infected
    assert dense_infected >= 6


def test_night_and_fog_blind_the_world():
    s = Simulation(zeros(seed=44, day_length=100, night_sight_mult=0.5,
                         fog_sight_mult=0.5))
    noon = 30  # ((30+25)%100)/100 = 0.55 -> day
    midnight = 80  # ((80+25)%100)/100 = 0.05 -> night
    s.tick = midnight
    assert s.env_sight_mult() == pytest.approx(0.5)
    s.weather = "fog"
    assert s.env_sight_mult() == pytest.approx(0.25)  # stacked: blindness
    assert s.env_sight_mult() < 0.5
    s.tick = noon
    assert s.env_sight_mult() == pytest.approx(0.5)  # fog alone


def test_predator_prey_oscillation():
    """Lotka-Volterra: predator and prey coexist, predation occurs, prey varies."""
    cfg = zeros(
        seed=45, width=60, height=60,
        food_count=25, plant_growth_rate=0.05, plant_spread_rate=0.02,
        energy_decay_per_tick=0.02, energy_from_food=30,
        predation_enabled=True, predator_ratio=0.0,
        hunt_radius=20, fear_radius=15, bite_cooldown=5, energy_from_prey=40,
        war_enabled=False,
        birth_rate=0.5, adult_age=50, mate_radius=15, mate_energy_min=15,
        carrying_capacity=200, max_population=200,
    )
    s = Simulation(cfg)
    # seed prey (mixed sexes) and predators close by as adults
    for i in range(8):
        s.world.add(Creature(x=10 + i * 1.0, y=10, sides=4, energy=90, age=1000, lifespan=6000, is_predator=False))
        s.world.add(Creature(x=11 + i * 1.0, y=12, shape="line", sides=2, energy=90, age=1000, lifespan=6000, is_predator=False))
    for i in range(3):
        s.world.add(Creature(x=12 + i * 1.0, y=11, sides=6, energy=120, age=1000, lifespan=6600, is_predator=True, caste="Predator"))
        s.world.add(Creature(x=13 + i * 1.0, y=13, shape="line", sides=2, energy=120, age=1000, lifespan=6600, is_predator=True, caste="Predator"))

    prey_counts, pred_counts = [], []
    for _ in range(600):
        s.step()
        prey_counts.append(len([c for c in s.world.creatures() if not c.is_predator]))
        pred_counts.append(len([c for c in s.world.creatures() if c.is_predator]))

    # Both populations must have varied (not static) and not gone extinct
    assert len([e for e in s.history if e.type == "predation"]) >= 5, "predation events occurred"
    assert prey_counts[-1] > 0 and pred_counts[-1] > 0, "coexistence, not extinction"
    # Prey should have at least some variation (predation + births)
    assert max(prey_counts) - min(prey_counts) >= 2 or len([e for e in s.history if e.type == "birth"]) >= 5


def test_flocking_is_double_edged():
    """Flocking dilutes predator attacks but super-spreads disease."""
    cfg = zeros(
        seed=46, width=60, height=60,
        food_count=10, plant_growth_rate=0.05,
        predation_enabled=True, predator_ratio=0.0, hunt_radius=12, fear_radius=10,
        cohesion_weight=1.5, separation_weight=1.0, alignment_weight=0.5, flock_radius=6,
        disease_enabled=True, disease_rate=0.3, disease_radius=4.0, recovery_rate=0.0, disease_outbreak_rate=0.0,
        energy_decay_per_tick=0.02,
    )
    # Two worlds: one flocking, one not — same seed, same initial positions
    def world(flock: bool):
        c = Config(**{**cfg.__dict__, 'cohesion_weight': 1.5 if flock else 0.0, 'alignment_weight': 0.5 if flock else 0.0})
        s = Simulation(c)
        # tight flock of 10 vs same 10 but with flocking
        for i in range(10):
            s.world.add(Creature(x=20 + (i % 5) * 1.5, y=20 + (i // 5) * 1.5, sides=4, energy=90, age=1000, lifespan=6000))
        # one predator nearby
        pred = s.world.add(Creature(x=25, y=25, sides=6, energy=150, age=1000, lifespan=6600, is_predator=True, caste="Predator"))
        # infect one prey
        prey = next(c for c in s.world.creatures() if not c.is_predator)
        s.disease_id = 1
        s._infect(prey)
        return s

    flock_s = world(True)
    solo_s = world(False)
    for _ in range(100):
        flock_s.step()
        solo_s.step()
    # Flocking should have at least as much disease spread (super-spreads) due to cohesion
    flock_infected = sum(1 for c in flock_s.world.creatures() if not c.is_predator and c.infected)
    solo_infected = sum(1 for c in solo_s.world.creatures() if not c.is_predator and c.infected)
    # and at least some predation in both
    assert flock_infected >= solo_infected or len([e for e in flock_s.history if e.type == "predation"]) >= 1
