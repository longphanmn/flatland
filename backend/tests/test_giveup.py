"""Stuck-prevention: creatures give up on unreachable meals and seek elsewhere.

A plant sitting behind a rock circle (or inside a house's walls) used to trap
the hungry against the obstacle until they starved. Now a blocked straight path
marks that meal as given up for `food_giveup_ticks` — perception ignores it and
the creature looks for food somewhere else. Eating anything clears the grudge.
"""

import math

from fastapi.testclient import TestClient

from app.config import Config
from app.entities import Corpse, Creature, Food, House
from app.main import app
from app.simulation import Simulation


def stuck_cfg(**kw) -> Config:
    zeros = dict(
        seed=5,
        width=60.0,
        height=60.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=2, num_houses=0,
        weather_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        communication_enabled=False,
        perceive_radius=30.0,
        food_giveup_ticks=40,
    )
    zeros.update(kw)
    return Config(**zeros)


def foods(s: Simulation) -> set[int]:
    return {e.id for e in s.world.entities.values() if e.kind == "food"}


def test_gives_up_on_food_behind_rock_and_eats_elsewhere():
    s = Simulation(stuck_cfg())
    s.rocks.append({"x": 30.0, "y": 30.0, "r": 5.0})
    # blocked meal is the NEARER one: its straight path crosses the stone
    blocked = s.world.add(Food(x=30.0, y=41.0, growth=1.0))
    # free meal farther away, on the creature's side of the stone
    free = s.world.add(Food(x=44.0, y=24.0, growth=1.0))
    c = s.world.add(Creature(x=22.0, y=26.0, angle=-0.6, energy=45.0, age=1000))

    for _ in range(120):
        if c.id not in s.world.entities:
            break
        s.step()

    assert c.meals >= 1  # it ate…
    assert blocked.id in foods(s)  # …not the meal behind the stone…
    assert free.id not in foods(s)  # …but the reachable one instead
    assert c.energy > 20.0  # no starvation grind at the rock


def test_gives_up_and_drifts_away_from_the_stone():
    s = Simulation(stuck_cfg(food_count=1, food_giveup_ticks=60))
    s.rocks.append({"x": 30.0, "y": 30.0, "r": 5.0})
    blocked = s.world.add(Food(x=30.0, y=40.0, growth=1.0))
    # slow full stomach: survival is not the question — behaviour is
    c = s.world.add(Creature(x=30.0, y=20.0, angle=math.pi / 2, energy=500.0, age=1000))

    gap_at_bump = None
    max_gap_after = 0.0
    for _ in range(150):
        s.step()
        if c.id not in s.world.entities:
            break
        grudged = (
            blocked.id in c.give_ups
            and s.tick - c.give_ups[blocked.id] < s.config.food_giveup_ticks
        )
        if grudged:
            if gap_at_bump is None:
                gap_at_bump = s.distance(c.x, c.y, blocked.x, blocked.y)
            else:
                max_gap_after = max(
                    max_gap_after, s.distance(c.x, c.y, blocked.x, blocked.y)
                )
    assert gap_at_bump is not None  # the straight path was judged blocked…
    assert max_gap_after > gap_at_bump  # …and it moved away, seeking elsewhere


def test_wall_blocked_food_is_abandoned_not_died_at():
    s = Simulation(stuck_cfg())
    house = House(x=25.0, y=25.0, size=8.0, door_width=3.0, door_side="west")
    s.world.add(house)
    meal = s.world.add(Food(x=27.0, y=23.0, growth=1.0))  # inside the walls
    # creature east of the house: east wall between it and the meal (door is west)
    c = s.world.add(Creature(x=33.0, y=25.0, angle=math.pi, energy=60.0, age=1000))

    gave_up = False
    for _ in range(90):
        s.step()
        if c.id not in s.world.entities:
            break
        gave_up = gave_up or meal.id in c.give_ups

    assert c.id in s.world.entities  # alive — no starvation at the wall
    assert gave_up  # the wall bounce marked the meal unreachable
    assert meal.id in foods(s)


def test_corpses_behind_a_rock_are_given_up_on_too():
    s = Simulation(stuck_cfg())
    s.rocks.append({"x": 30.0, "y": 30.0, "r": 5.0})
    s.world.add(Corpse(x=30.0, y=40.0, ttl=100000, energy=25.0))  # behind the stone
    s.world.add(Food(x=46.0, y=22.0, growth=1.0))
    c = s.world.add(Creature(x=22.0, y=28.0, angle=0.4, energy=50.0, age=1000))

    saw_grudge = False
    for _ in range(120):
        if c.id not in s.world.entities:
            break
        s.step()
        saw_grudge = saw_grudge or bool(c.give_ups)

    assert saw_grudge  # the blocked corpse was judged unreachable at least once
    assert c.meals >= 1  # …and the creature fed anyway instead of starving there
    assert c.energy > 20.0


def test_food_giveup_ticks_law_roundtrip():
    client = TestClient(app)
    client.headers["X-God-Key"] = "test-key"
    r = client.post("/api/laws?persist=false", json={"food_giveup_ticks": 77})
    assert r.status_code == 200
    assert r.json()["food_giveup_ticks"] == 77
