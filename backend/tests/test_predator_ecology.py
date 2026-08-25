"""§X-fix production incident @ tick ~34k — the world died into a wolf monoculture.

Root cause: the Carnivore caste could graze living plants (`can_eat` bypass +
§O diet gate defaulting off), giving predators a double income — hunt AND
harvest. They out-competed every clan caste, drove them extinct, and settled
at the population cap as 800 fat, clanless predators: no clans had members,
every creature had no clan, nobody was ever hungry again.

The fix: predators hunt the living and scavenge the dead — never graze.
Their survival is coupled strictly to prey (real Lotka–Volterra).
"""

import pytest

from app.config import Config
from app.entities import Corpse, Creature, Food
from app.simulation import Simulation


def eco_cfg(**kw) -> Config:
    kw.setdefault("relief_enabled", False)
    zeros = dict(
        seed=17, width=80.0, height=80.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0,
        weather_enabled=False,
        age_enabled=False,
        birth_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        schism_enabled=False,
        culture_enabled=False,
        predation_enabled=True,
        predator_ratio=0.0,  # hand-spawned predators only
        shelter_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def place_predator(sim: Simulation, x: float, y: float, energy: float = 40.0) -> Creature:
    sim._spawn_predator()
    p = next(c for c in sim.world.creatures() if c.is_predator and c.x == c.x)
    p = [c for c in sim.world.creatures() if c.is_predator][-1]
    p.x, p.y, p.energy = x, y, energy
    return p


def test_predators_never_graze_plants():
    """A hungry predator beside a ripe field leaves it untouched and pays upkeep."""
    s = Simulation(eco_cfg(food_count=1))
    wolf = place_predator(s, 30.0, 30.0, energy=40.0)
    field = s.world.add(Food(x=31.0, y=30.0, growth=1.0, variant="grass"))

    for _ in range(80):
        s.step()

    assert field.id in s.world.entities, "the Carnivore does not graze the field"
    assert field.growth >= 1.0
    assert wolf.id in s.world.entities
    assert wolf.energy < 40.0, "no free lunch — upkeep bites"


def test_predators_scavenge_corpses():
    """The dead are fair game: scavenging keeps the carrion tier honest."""
    s = Simulation(eco_cfg(food_count=0))
    wolf = place_predator(s, 30.0, 30.0, energy=15.0)
    remains = s.world.add(Corpse(x=31.0, y=30.0, ttl=600, energy=25.0))

    fed = False
    for _ in range(40):
        s.step()
        if remains.id not in s.world.entities or wolf.energy > 25.0:
            fed = True
            break
    assert fed, "the wolf scavenges the fallen"


def test_predators_starve_out_without_prey_even_when_fields_are_full():
    """THE INCIDENT: prey gone, bounty at target — the old code let predators
    sit at the population cap forever, farming grass. Now they starve out."""
    s = Simulation(eco_cfg(seed=23, food_count=40))  # full seasonal bounty
    for _ in range(8):
        s._spawn_predator()
    for c in s.world.creatures():
        c.energy = 30.0  # mid-hunger: shortens the march to starvation
    assert len(s.world.creatures()) == 8

    for _ in range(2400):
        s.step()
        if len(s.world.creatures()) <= 1:
            break

    survivors = len(s.world.creatures())
    assert survivors <= 1, (
        "without prey the predator population must collapse — "
        f"{survivors} survived a full bounty"
    )


def test_prey_survives_predator_contact_longer_than_before():
    """With grazing closed off, hunting pressure alone cannot clear the map:
    a prey population next to a lone wolf persists well past the old horizon."""
    s = Simulation(
        eco_cfg(seed=31, food_count=30, birth_enabled=True,
                carrying_capacity=120, max_population=160)
    )
    s._spawn_predator()
    wolf = [c for c in s.world.creatures() if c.is_predator][0]
    wolf.x, wolf.y = 10.0, 10.0
    for i in range(14):
        prey = s.world.add(Creature(
            x=50.0 + (i % 5), y=50.0 + (i // 5), sides=3, shape="polygon",
            caste="Soldier", energy=90.0,
        ))
        s._init_creature_evolution(prey)

    for _ in range(900):
        s.step()

    civilians = [c for c in s.world.creatures() if not c.is_predator]
    assert len(civilians) > 0, "one wolf cannot eat a breeding village"
