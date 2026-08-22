"""Disease tests: outbreaks, contagion, recovery, lethality. Plus corpses."""

import pytest

from app.config import Config
from app.entities import Creature
from app.simulation import Simulation


def disease_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0,
        disease_enabled=True, adult_age=0.0,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_outbreak_starts_and_is_recorded():
    s = Simulation(disease_cfg(seed=1, disease_outbreak_rate=1.0))
    a = s.world.add(Creature(x=10.0, y=10.0, energy=100.0))
    s.step()
    assert s.disease_id == 1
    assert any(c.infected for c in s.world.creatures())
    ev = [e for e in s.history if e.type == "outbreak"]
    assert len(ev) == 1 and ev[0].payload["disease_id"] == 1
    assert a.infected or any(c.infected for c in s.world.creatures())


def test_contagion_spreads_to_neighbours():
    s = Simulation(disease_cfg(seed=2, disease_rate=1.0, disease_radius=5.0))
    sick = s.world.add(Creature(x=10.0, y=10.0, energy=100.0))
    healthy = s.world.add(Creature(x=12.0, y=10.0, energy=100.0))
    s.disease_id = 1
    s._infect(sick)
    # no spontaneous outbreak: rate 0; but contagion is certain this tick
    s.step()
    assert healthy.infected


def test_distance_stops_contagion():
    s = Simulation(disease_cfg(seed=3, disease_rate=1.0, disease_radius=2.0))
    sick = s.world.add(Creature(x=10.0, y=10.0, energy=100.0))
    far = s.world.add(Creature(x=30.0, y=30.0, energy=100.0))
    s.disease_id = 1
    s._infect(sick)
    for _ in range(3):
        s.step()
    assert not far.infected


def test_recovery_when_law_favours_it():
    s = Simulation(disease_cfg(seed=4, recovery_rate=1.0))
    c = s.world.add(Creature(x=10.0, y=10.0, energy=100.0))
    s.disease_id = 1
    s._infect(c)
    s.step()
    assert not c.infected
    assert [e for e in s.history if e.type == "recovery"]


def test_lethal_disease_kills():
    s = Simulation(
        disease_cfg(seed=5, recovery_rate=0.0, disease_lethality=1.0,
                    disease_energy_drain=0.0)
    )
    c = s.world.add(Creature(x=10.0, y=10.0, energy=10000.0))
    s.disease_id = 1
    s._infect(c)
    for _ in range(60):
        s.step()
        if c.id not in s.world.entities:
            break
    assert c.id not in s.world.entities  # health 100 / (2 per tick) = 50 ticks
    assert s.snapshot().dead_by_cause.get("disease") == 1


def test_disabled_disease_freezes_everything():
    s = Simulation(
        Config(
            seed=6, width=50.0, height=50.0,
            num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
            num_priests=0, num_women=0, food_count=0, num_houses=0,
            disease_enabled=False,
        )
    )
    sick = s.world.add(Creature(x=10.0, y=10.0, energy=100.0))
    near = s.world.add(Creature(x=11.0, y=10.0, energy=100.0))
    s.disease_id = 1
    s._infect(sick)
    health_before = sick.health
    for _ in range(5):
        s.step()
    assert not near.infected  # never spreads while the law is off
    assert sick.health == pytest.approx(health_before)  # no drain either


# ----------------------------------------------------------- corpses §N
def corpses_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=0, adult_age=0.0,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_death_leaves_a_corpse():
    s = Simulation(corpses_cfg(seed=10))
    c = s.world.add(Creature(x=15.0, y=15.0, energy=0.01))
    s.step()
    assert c.id not in s.world.entities
    corpses = [e for e in s.world.entities.values() if e.kind == "corpse"]
    assert len(corpses) == 1 and corpses[0].energy == pytest.approx(25.0)


def test_corpses_are_eaten():
    s = Simulation(corpses_cfg(seed=11))
    fallen = s.world.add(Creature(x=20.0, y=20.0, energy=0.01))
    s.step()
    corpse = next(e for e in s.world.entities.values() if e.kind == "corpse")
    eater = s.world.add(
        Creature(x=(corpse.x - 1.0) % 50.0, y=corpse.y, sides=4, angle=0.0,
                 speed=0.55, energy=40.0, lifespan=100.0, age=50)
    )
    s.step()
    assert eater.meals >= 1
    assert eater.energy > 55.0  # 40 - decay + corpse energy
    # the eaten corpse was replaced by nothing: exactly the one corpse remains? No—
    # scavenged corpse is gone; a NEW one appears only when something dies.
    remaining = [e for e in s.world.entities.values() if e.kind == "corpse"]
    assert all(e.id != corpse.id for e in remaining)
    _ = fallen


def test_corpses_decay_after_ttl():
    s = Simulation(corpses_cfg(seed=12, corpse_ttl=5))
    c = s.world.add(Creature(x=15.0, y=15.0, energy=0.01))
    s.step()
    assert any(e.kind == "corpse" for e in s.world.entities.values())
    for _ in range(6):
        s.step()
    assert not any(e.kind == "corpse" for e in s.world.entities.values())


def test_corpses_disabled():
    s = Simulation(corpses_cfg(seed=13, corpses_enabled=False))
    c = s.world.add(Creature(x=15.0, y=15.0, energy=0.01))
    s.step()
    assert not any(e.kind == "corpse" for e in s.world.entities.values())
