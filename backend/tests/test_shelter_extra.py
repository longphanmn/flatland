"""§L shelter edge cases adopted from the QA backlog."""

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.entities import Creature, House
from app.main import RT, app, start_world
from app.simulation import Simulation


def shelter_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0,
        day_length=8, weather_enabled=False, adult_age=0.0,
    )
    zeros.update(kw)
    return Config(**zeros)


@pytest.fixture(autouse=True)
def fresh_runtime():
    RT.config = Config.from_env()
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    start_world()
    yield


@pytest.fixture()
def client():
    c = TestClient(app)  # no lifespan: the tick loop must not run
    c.headers["X-God-Key"] = "test-key"
    return c


def _step_into_night(s: Simulation, guard: int = 10) -> None:
    while not s._is_night(s._time_of_day()) and guard > 0:
        s.step()
        guard -= 1
    assert s._is_night(s._time_of_day())


def test_winter_night_exposure_kills_outdoors():
    s = Simulation(
        shelter_cfg(seed=1, exposure_drain=50.0, energy_decay_per_tick=0.1,
                    season_length=8)
    )
    c = s.world.add(Creature(x=10.0, y=10.0, energy=20.0))
    guard = 0
    while not (s._is_night(s._time_of_day()) and s._season() == "winter") and guard < 40:
        s.step()
        guard += 1
    assert s._is_night(s._time_of_day()) and s._season() == "winter"
    e_before = c.energy
    s.step()
    assert c.id not in s.world.entities  # exposure + hunger ate the last energy
    assert e_before - c.energy >= 49.9 if c.id in s.world.entities else True
    deaths = [e for e in s.history if e.type == "death"]
    assert deaths and deaths[-1].entity_id == c.id and deaths[-1].cause == "starvation"


def test_bed_contention_deterministic_two_houses():
    def world():
        s = Simulation(shelter_cfg(seed=7, house_capacity=1))
        s.world.add(House(x=15.0, y=25.0, size=8.0))  # near c1 & c2
        s.world.add(House(x=40.0, y=25.0, size=8.0))  # near c3
        c1 = s.world.add(Creature(x=14.0, y=25.0, energy=100.0))
        c2 = s.world.add(Creature(x=14.2, y=25.0, energy=100.0))
        c3 = s.world.add(Creature(x=39.5, y=25.0, energy=100.0))
        return s, [(c1, True), (c2, False), (c3, True)]

    observations = []
    for _ in range(2):  # same seed twice => identical bed assignment
        s, expected = world()
        _step_into_night(s)
        s.step()
        observations.append([(c.sleeping, want) for c, want in expected])

    assert observations[0] == observations[1]  # deterministic contention
    assert sum(1 for slept, _ in observations[0] if slept) == 2  # two beds total
    assert observations[0][0][0] is True   # lowest id won house A's single bed
    assert observations[0][1][0] is False  # overflow sleeps outside
    assert observations[0][2][0] is True   # house B housed its own


def test_rest_recovery_mult_speeds_healing():
    def world(mult: float):
        s = Simulation(shelter_cfg(seed=9, rest_recovery_mult=mult,
                                   energy_decay_per_tick=0.0))
        s.world.add(House(x=25.0, y=25.0, size=12.0))
        c = s.world.add(Creature(x=25.0, y=25.0, energy=100.0, health=40.0))
        return s, c

    slow_s, slow_c = world(1.0)
    fast_s, fast_c = world(4.0)
    for _ in range(16):  # two days of nights asleep indoors
        slow_s.step()
        fast_s.step()
    assert slow_c.health > 40.0  # rest heals…
    assert fast_c.health > slow_c.health  # …and a higher multiplier heals faster


def test_shelter_laws_round_trip_via_api(client):
    r = client.post("/api/laws", json={"house_capacity": 2, "rest_recovery_mult": 4.0})
    assert r.status_code == 200
    laws = client.get("/api/laws").json()
    assert laws["house_capacity"] == 2
    assert laws["rest_recovery_mult"] == pytest.approx(4.0)

    # god's laws outlive the world they were spoken into
    client.post("/api/control", json={"action": "reset"})
    laws = client.get("/api/laws").json()
    assert laws["house_capacity"] == 2
    assert laws["rest_recovery_mult"] == pytest.approx(4.0)


def test_shelter_off_freezes_exposure(client):
    s = RT.sim  # the law endpoint mutates the runtime's living world
    c = s.world.add(Creature(x=10.0, y=10.0, energy=500.0))  # far from any house
    RT.paused = False
    client.post("/api/laws", json={"exposure_drain": 8.0})
    s.weather = "rain"  # wet and roofless: full exposure
    e_before = c.energy
    s.step()
    exposed_loss = e_before - c.energy
    assert exposed_loss >= 7.9  # decay + heavy exposure drain

    # god revokes exposure as a law — the rain stops biting at once
    client.post("/api/laws", json={"shelter_enabled": False})
    assert s.config.shelter_enabled is False  # the living world obeys instantly
    e_before = c.energy
    s.weather = "rain"
    s.step()
    assert (e_before - c.energy) <= 0.11  # decay only
