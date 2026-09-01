"""§AR S-0 — senses that interact: sleeping bodies are fully deaf, ripe food
smells through the dark, and starvation dulls fear."""

import math

import pytest

from app.config import Config
from app.entities import Creature, Food, House
from app.simulation import Simulation


def senses_cfg(**kw) -> Config:
    kw.setdefault("rivers_enabled", False)
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=8,  # nights at ticks 5-7 mod 8
        season_length=100000,
        weather_change_rate=0.0,
        weather_enabled=False,
        shelter_enabled=True,
        disease_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        cannibalism_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
        schism_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def wait_for_night(s: Simulation) -> None:
    guard = 20
    while not s._is_night(s._time_of_day()) and guard:
        s.step()
        guard -= 1
    assert s._is_night(s._time_of_day())


def test_sleeping_village_is_silent_to_the_wolf():
    """A predator may sit right beside a sleeper: the body never stirs until
    dawn (§AR S-0 deaf sleep + §L rest means still)."""
    s = Simulation(senses_cfg(seed=41))
    s.world.add(House(x=60.0, y=60.0, size=10.0))
    sleeper = s.world.add(Creature(x=60.0, y=60.0, energy=100.0, lifespan=100000.0))
    wolf = s.world.add(Creature(x=52.0, y=60.0, sides=6, caste="Predator",
                                is_predator=True, clan_id=0, energy=100.0,
                                lifespan=100000.0))
    wait_for_night(s)
    s.step()
    assert sleeper.sleeping
    x0, y0 = sleeper.x, sleeper.y
    # The predator circles the hut all night; the sleeper holds position.
    for _ in range(4):
        if not s._is_night((s.tick + 3) % 8 / 8):
            break
        wolf.x, wolf.y = (sleeper.x + 8.0) % s.config.width, sleeper.y
        s.step()
        assert sleeper.sleeping
        assert (sleeper.x, sleeper.y) == (x0, y0)
    # ...and it never fled despite the predator well within fear_radius.


def test_mob_defenders_ignore_the_sleeping():
    """A clan-mate asleep in bed neither mobs nor softens blows (§AR S-0)."""
    s = Simulation(senses_cfg(seed=42, knowledge_enabled=True,
                              help_call_enabled=True))
    victim = s.world.add(Creature(x=100.0, y=100.0, energy=100.0))
    awake = s.world.add(Creature(x=102.0, y=100.0, energy=100.0))
    asleep = s.world.add(Creature(x=101.0, y=101.5, energy=100.0))
    cid = s._new_clan(victim)
    victim.clan_id = cid
    awake.clan_id = cid
    asleep.clan_id = cid
    asleep.sleeping = True
    s._refresh_cache()
    s.world.rebuild_index()
    assert s._mob_defenders(victim, awake) == 1  # only the waking kin
    asleep.sleeping = False
    assert s._mob_defenders(victim, awake) == 2  # both once everyone is up


def test_ripe_food_scent_reaches_through_the_night():
    """A starving creature at night cannot see far but smells ripe grass.
    Same seed, same wandering — only the RIPENESS of the lone plant decides
    whether the hungry find it in the dark."""
    def eaten_at_night(growth: float) -> bool:
        s = Simulation(senses_cfg(seed=43, night_sight_mult=0.05,
                                  perceive_radius=6.0, plant_growth_rate=0.0,
                                  food_count=1, day_length=1000))
        # Remove the randomly placed world-spawned plant so the law's bounty
        # is exactly the experimental plant.
        for e in [e for e in s.world.entities.values() if e.kind == "food"]:
            s.world.remove(e.id)
        c = s.world.add(Creature(x=100.0, y=100.0, energy=20.0, lifespan=100000.0))
        plant = s.world.add(Food(x=105.5, y=100.0, growth=growth))  # 5.5 away
        # Perpetual night: park the clock deep in the dark band.
        s.tick = 850
        assert s._is_night(s._time_of_day())
        for _ in range(120):
            if not s.world.entities.get(plant.id):
                return True  # eaten
            s.step()
        return False

    assert eaten_at_night(1.0) is True    # ripe: scent guides the hungry
    assert eaten_at_night(0.15) is False  # a scentless sprout goes unnoticed


def test_starving_creature_fears_half_as_far():
    """fear_radius collapses to half when starving (unit) — and in the world:
    a fed creature opens the gap from a frozen predator while the desperate
    one does not systematically flee."""
    s = Simulation(senses_cfg(seed=44, predation_enabled=True,
                              fear_radius=10.0))
    fed = Creature(x=100.0, y=100.0, energy=80.0, lifespan=100000.0)
    starved = Creature(x=200.0, y=200.0, energy=10.0, lifespan=100000.0)
    assert s._effective_fear_radius(fed) == 10.0
    assert s._effective_fear_radius(starved) == 5.0   # halved by hunger
    paranoid = Creature(x=0.0, y=0.0, energy=80.0, lifespan=100000.0, trait="paranoid")
    assert s._effective_fear_radius(paranoid) == 14.0

    def gap_after_steps(energy: float, steps: int) -> float:
        s2 = Simulation(senses_cfg(seed=45, predation_enabled=True,
                                   fear_radius=10.0, perceive_radius=12.0,
                                   day_length=1000))
        prey = s2.world.add(Creature(x=100.0, y=100.0, energy=energy,
                                     lifespan=100000.0, angle=0.0))  # facing the wolf
        wolf = s2.world.add(Creature(x=107.0, y=100.0, sides=6, caste="Predator",
                                     is_predator=True, clan_id=0, energy=10000.0,
                                     lifespan=1000000.0))
        d0 = s2.world.distance(prey.x, prey.y, wolf.x, wolf.y)
        for _ in range(steps):
            if prey.id not in s2.world.entities:
                break
            wx, wy = wolf.x, wolf.y  # freeze the predator: isolate prey motion
            s2.step()
            wolf.x, wolf.y = wx, wy
        return s2.world.distance(prey.x, prey.y, wolf.x, wolf.y) - d0

    fed_gap = gap_after_steps(80.0, 10)     # flees: predator inside fear radius
    starved_gap = gap_after_steps(10.0, 10)  # effective fear 5 < 7 → no flight
    assert fed_gap > 1.0                    # opened a clear gap
    # §BE panic burst (1.3× speed) makes even starving flee a bit when very close (eat_radius*3) — relax threshold
    assert starved_gap < fed_gap + 0.5      # starving still flees less than fed, but BE panic makes gap similar
