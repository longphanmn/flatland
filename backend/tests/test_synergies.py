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
