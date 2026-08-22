"""Reproduction & inheritance tests: Nature's Law, mating, lineage, caps."""

import math

import pytest

from app.config import Config
from app.entities import Creature
from app.simulation import Simulation


def repro_cfg(**kw) -> Config:
    """Deterministic breeding-world config: adults, adjacent pairs conceive."""
    base = dict(
        seed=99,
        width=50.0,
        height=50.0,
        birth_enabled=True,
        adult_age=0.0,
        mate_radius=5.0,
        mate_energy_min=10.0,
        birth_rate=1.0,
        mutation_rate=0.0,
        birth_energy_cost=5.0,
        reproduction_cooldown=10,
    )
    base.update(kw)
    return Config(**base)


def empty_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
    )
    zeros.update(kw)
    return repro_cfg(**zeros)


def pair(sim: Simulation, father_kwargs: dict, mother_kwargs: dict) -> tuple[Creature, Creature]:
    fk = dict(age=1000, lifespan=2000)  # adults by life stage
    fk.update(father_kwargs)
    mk = dict(age=1000, lifespan=2000)
    mk.update(mother_kwargs)
    father = sim.world.add(Creature(x=25.0, y=25.0, energy=100.0, **fk))
    mother = sim.world.add(Creature(x=26.0, y=25.0, shape="line", sides=2, angle=0.0, energy=100.0, **mk))
    return father, mother


def test_law_of_nature_son_gains_a_side():
    s = Simulation(empty_cfg(sex_ratio=1.0))
    father, _ = pair(s, dict(sides=4), {})  # Gentleman father
    s.step()
    children = [c for c in s.world.creatures() if c.generation == 1]
    assert len(children) == 1
    child = children[0]
    assert child.sex == "male"
    assert child.sides == 5  # son of a Square is a Pentagon
    assert child.caste == "Professional"
    assert child.mother_id == _.id and child.father_id == father.id


def test_daughter_is_a_line():
    s = Simulation(empty_cfg(sex_ratio=0.0))
    _, mother = pair(s, dict(sides=4), {})
    s.step()
    child = next(c for c in s.world.creatures() if c.generation == 1)
    assert child.sex == "female" and child.shape == "line"
    assert child.caste == "Woman"


def test_mutation_deviates_side_count():
    s = Simulation(empty_cfg(sex_ratio=1.0, mutation_rate=1.0))
    pair(s, dict(sides=4), {})
    s.step()
    child = next(c for c in s.world.creatures() if c.generation == 1)
    assert child.sides in (4, 6)  # inherited 5, mutated ±1


def test_birth_event_and_lineage_recorded():
    s = Simulation(empty_cfg(sex_ratio=1.0))
    father, mother = pair(s, dict(sides=4), {})
    s.step()
    ev = [e for e in s.history if e.type == "birth"]
    assert len(ev) == 1
    child_id = next(c for c in s.world.creatures() if c.generation == 1).id
    assert ev[0].entity_id == child_id
    assert ev[0].payload["mother"] == mother.id
    assert ev[0].payload["father"] == father.id
    assert ev[0].payload["generation"] == 1


def test_parents_pay_energy_and_cooldown():
    s = Simulation(empty_cfg(sex_ratio=1.0))
    father, mother = pair(s, dict(sides=4), {})
    before_f, before_m = father.energy, mother.energy
    s.step()
    assert father.energy <= before_f - 5.0 + 1.0  # cost paid (decay may also apply)
    assert mother.energy <= before_m - 5.0 + 1.0
    assert father.repro_cooldown > 0 and mother.repro_cooldown > 0
    # cooldown blocks an immediate second birth even at birth_rate 1.0
    n = len(s.world.creatures())
    s.step()
    assert len(s.world.creatures()) == n


def test_untouchable_pairs_do_not_breed():
    # too far apart
    s = Simulation(empty_cfg(mate_radius=2.0))
    s.world.add(Creature(x=10.0, y=10.0, sides=4, energy=100.0))
    s.world.add(Creature(x=20.0, y=10.0, shape="line", sides=2, energy=100.0))
    s.step()
    assert not [c for c in s.world.creatures() if c.generation == 1]
    # too hungry
    s2 = Simulation(empty_cfg(mate_energy_min=200.0))
    s2.world.add(Creature(x=10.0, y=10.0, sides=4, energy=100.0))
    s2.world.add(Creature(x=11.0, y=10.0, shape="line", sides=2, energy=100.0))
    s2.step()
    assert not [c for c in s2.world.creatures() if c.generation == 1]


def test_children_are_not_born_adults():
    s = Simulation(empty_cfg(adult_age=500.0, sex_ratio=1.0, reproduction_cooldown=0))
    pair(s, dict(sides=4, age=600), dict(age=600))  # adult parents
    for _ in range(8):
        s.step()
    gen1 = [c for c in s.world.creatures() if c.generation == 1]
    assert len(gen1) >= 1  # children were born...
    assert not [c for c in s.world.creatures() if c.generation >= 2]  # ...but none bred yet


def test_max_population_hard_cap():
    s = Simulation(
        empty_cfg(sex_ratio=1.0, reproduction_cooldown=0, max_population=3,
                  carrying_capacity=100, mate_radius=50.0)
    )
    pair(s, dict(sides=4), {})
    for _ in range(6):
        s.step()
        assert len(s.world.creatures()) <= 3


def test_births_disabled_by_law():
    s = Simulation(empty_cfg(birth_enabled=False))
    pair(s, dict(sides=4), {})
    for _ in range(3):
        s.step()
    assert not [c for c in s.world.creatures() if c.generation == 1]


def test_mutation_scores_irregularity():
    s = Simulation(empty_cfg(sex_ratio=1.0, mutation_rate=1.0))
    pair(s, dict(sides=4), {})
    s.step()
    child = next(c for c in s.world.creatures() if c.generation == 1)
    assert 0.3 <= child.irregularity <= 1.0


def test_regular_children_are_never_judged():
    s = Simulation(empty_cfg(sex_ratio=1.0, adult_age=5.0))
    pair(s, dict(sides=4), {})
    for _ in range(8):
        s.step()
    for c in s.world.creatures():
        assert c.irregularity == 0.0
        assert c.caste != "Soldier" or c.generation == 0
    assert not [e for e in s.history if e.type in ("demotion", "death")]


def test_irregular_child_demoted_at_maturity():
    s = Simulation(empty_cfg(adult_age=10.0, euthanasia_threshold=0.7))
    child = s.world.add(
        Creature(x=25.0, y=25.0, sides=6, irregularity=0.4, energy=100.0)
    )
    for _ in range(12):
        s.step()
    assert child.id in s.world.entities  # spared
    assert child.sides == 3 and child.caste == "Soldier"  # lowest regular order
    demos = [e for e in s.history if e.type == "demotion"]
    assert len(demos) == 1 and demos[0].entity_id == child.id


def test_grossly_irregular_child_consumed_at_maturity():
    s = Simulation(empty_cfg(adult_age=10.0, euthanasia_threshold=0.7))
    child = s.world.add(
        Creature(x=25.0, y=25.0, sides=6, irregularity=0.9, energy=100.0)
    )
    for _ in range(12):
        s.step()
    assert child.id not in s.world.entities
    deaths = [e for e in s.history if e.type == "death"]
    assert len(deaths) == 1 and deaths[0].cause == "euthanasia"
    assert s._death_counts.get("euthanasia") == 1


def test_isosceles_promotion_to_artisan():
    s = Simulation(empty_cfg(sex_ratio=1.0, mutation_rate=0.0))
    father = s.world.add(
        Creature(x=25.0, y=25.0, sides=3, iso_angle=59.5, energy=100.0, age=1000, lifespan=2000)
    )
    s.world.add(
        Creature(x=26.0, y=25.0, shape="line", sides=2, angle=0.0, energy=100.0, age=1000, lifespan=2000)
    )
    s.step()
    child = next(c for c in s.world.creatures() if c.generation == 1)
    assert child.sides == 3 and child.iso_angle == pytest.approx(60.0)
    assert child.caste == "Artisan"
    promos = [e for e in s.history if e.type == "promotion"]
    assert len(promos) == 1 and promos[0].entity_id == child.id
    # and the founding father was still a mere Soldier
    assert father.caste == "Soldier"
