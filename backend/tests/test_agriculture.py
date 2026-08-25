"""§AM Food & Agriculture — seeds & furrows, granaries, living soil, feasts.

Farmers glean seed from wild harvests and sow cultivated plots near the
settlement (2× growth, 2.5× yield); tending weeds poison and holds back
withering; sated harvesters fill a dry roofed granary that famine draws on;
overflowing granaries feed a feast; monocropping exhausts the soil grid while
compost and the dead refill it; starving war parties raid rival granaries;
bread broken with strangers buys non-aggression.
"""

import pytest
from dataclasses import replace

from fastapi.testclient import TestClient

from app.config import Config
from app.entities import Creature, Food, House
from app.main import app
from app.simulation import (
    BANQUET_FILL_FRACTION,
    CULTIVATED_GROWTH_MULT,
    CULTIVATED_YIELD_MULT,
    SOIL_DEPLETION_PER_GROWTH,
    VARIANT_ENERGY,
    Simulation,
)


def ag_cfg(**kw) -> Config:
    zeros = dict(
        seed=7, width=80.0, height=80.0,
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        weather_enabled=False,
        age_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        disease_enabled=False,
        schism_enabled=False,
        culture_enabled=False,
        plant_growth_rate=0.05,
        plant_spread_rate=0.0,
        perceive_radius=20.0,
    )
    zeros.update(kw)
    return Config(**zeros)


def noon_step(sim: Simulation) -> None:
    """Park the clock at high noon so growth gets full sun deterministically."""
    dl = max(1, sim.config.day_length)
    sim.tick = (sim.tick // dl) * dl + dl // 4
    sim.step()


def make_farmer(sim: Simulation, x: float, y: float, clan_id: int = 1, skill: float = 12.0) -> Creature:
    c = sim.world.add(Creature(
        x=x, y=y, sides=3, shape="polygon", caste="Soldier",
        clan_id=clan_id, energy=90.0,
    ))
    sim._init_creature_evolution(c)
    c.skills["farming"] = skill
    return c


def make_clan(sim: Simulation, cid: int, house: House) -> None:
    """Register a clan whose seat is `house` (bypasses worldgen for focus)."""
    sim.clans[cid] = {
        "name": f"Clan {cid}", "founder_id": None, "born_tick": 0,
        "color": "#fff", "totem": None, "leader_id": None,
        "governance": "republic",
        "bylaws": {"rationing": False, "martial_law": False, "sanctuary": "open"},
        "task_board": {"priority": "balanced", "harvester_weight": 1.0, "guard_weight": 1.0},
        "specialization": {"warrior": 0.33, "farmer": 0.33, "scavenger": 0.34},
        "culture": "Test Rite", "culture_id": cid, "coalition_id": None,
        "larder": 0.0, "granary": 0.0, "harvest_total": 0.0, "feast_until": 0,
        "dialect": 0.0, "tribute_to": None, "main_house_id": house.id,
        "faith": 0.0, "shrine_level": 0, "history": [],
    }
    house.clan_id = cid


# ----------------------------------------------------------------- Phase B

def test_seed_gleaned_from_wild_harvest_and_sown_in_plot():
    s = Simulation(ag_cfg(food_count=1))  # the hand-placed plant IS the bounty
    farmer = make_farmer(s, 40.0, 40.0)
    farmer.energy = 60.0  # hungry enough to eat
    wild = s.world.add(Food(x=41.0, y=40.0, growth=1.0, variant="grass"))
    assert farmer.seeds == 0

    for _ in range(4):
        s.step()
        if wild.id not in s.world.entities:
            break
    assert wild.id not in s.world.entities, "the ripe grass gets eaten"
    assert farmer.seeds == 1, "a skilled hand gleans seed from a wild harvest"

    # Sowing: a clan plot underfoot receives the seed as a cultivated crop.
    house = House(x=30.0, y=30.0, size=6.0)
    s.world.add(house)
    make_clan(s, 1, house)
    s.farm_plots[1] = [{"x": round(farmer.x, 2), "y": round(farmer.y, 2), "irrigated": False}]
    before = farmer.skills.get("farming", 0.0)
    for _ in range(8):
        s.step()
        crops = [f for f in s.world.entities.values()
                 if isinstance(f, Food) and f.cultivated]
        if crops:
            break
    crops = [f for f in s.world.entities.values() if isinstance(f, Food) and f.cultivated]
    assert crops, "seed is sown as a cultivated crop"
    assert crops[0].cultivated and not crops[0].irrigated
    assert farmer.seeds == 0
    assert farmer.skills.get("farming", 0.0) > before


def test_unskilled_hands_glean_no_seed():
    s = Simulation(ag_cfg(seed=8, food_count=1))
    novice = make_farmer(s, 40.0, 40.0, skill=1.0)
    novice.energy = 60.0
    wild = s.world.add(Food(x=41.0, y=40.0, growth=1.0))
    for _ in range(6):
        s.step()
        if wild.id not in s.world.entities:
            break
    assert wild.id not in s.world.entities
    assert novice.seeds == 0, "farming is a craft — novices spill the seed"


def test_cultivated_crops_grow_faster():
    s = Simulation(ag_cfg(food_count=2))
    wild = s.world.add(Food(x=10.0, y=10.0, growth=0.5, variant="grass"))
    sown = s.world.add(Food(x=50.0, y=50.0, growth=0.5, variant="grass", cultivated=True))
    for _ in range(20):
        noon_step(s)
    assert wild.growth < 1.0 and sown.growth < 1.0  # neither finished: pure rate read
    # exact ratio check across identical windows
    w_gain = wild.growth - 0.5
    c_gain = sown.growth - 0.5
    assert c_gain == pytest.approx(w_gain * CULTIVATED_GROWTH_MULT)


def test_cultivated_harvest_feeds_far_better():
    s = Simulation(ag_cfg(seed=11, energy_max=400.0, food_count=2))  # headroom: no cap clips the ratio
    eater_a = make_farmer(s, 10.0, 10.0, skill=0.0)
    eater_b = make_farmer(s, 60.0, 60.0, skill=0.0)
    eater_a.energy = 20.0
    eater_b.energy = 20.0
    wild = s.world.add(Food(x=11.0, y=10.0, growth=1.0, variant="grass"))
    sown = s.world.add(Food(x=61.0, y=60.0, growth=1.0, variant="grass", cultivated=True))

    def feed_once(sim, eater, plant):
        for _ in range(6):
            sim.step()
            if plant.id not in sim.world.entities:
                return True
        return False

    ok_a = feed_once(s, eater_a, wild)
    ok_b = feed_once(s, eater_b, sown)
    assert ok_a and ok_b, "both meals get eaten"
    gain_a = eater_a.energy - 20.0
    gain_b = eater_b.energy - 20.0
    assert gain_b == pytest.approx(gain_a * CULTIVATED_YIELD_MULT, rel=0.02), \
        "the sown harvest feeds 2.5×"


def test_tending_holds_back_wither_and_weeds_poison():
    from app.simulation import TEND_REGRESS_TICKS
    s = Simulation(ag_cfg(food_decay_enabled=True, food_lifespan_ticks=50, food_count=2))
    tender = make_farmer(s, 40.0, 40.0, skill=9.0)
    bed = s.world.add(Food(x=41.0, y=40.5, growth=1.0, variant="grass", cultivated=True))
    poison = s.world.add(Food(x=42.0, y=40.0, growth=0.2, variant="poisonous"))
    bed.mature_ticks = 49  # one tick from withering

    s.world.rebuild_index()
    s.tick += (-(s.tick + tender.id)) % 9  # land on the tending cadence
    assert (s.tick + tender.id) % 9 == 0
    s._sow_and_tend()

    assert poison.id not in s.world.entities, "toxic sprouts are weeded out"
    assert bed.mature_ticks == max(0, 49 - TEND_REGRESS_TICKS), "tending rolls back the clock"
    for _ in range(3):
        s.step()
    assert bed.id in s.world.entities, "the tended bed outlives its lifespan"


def test_irrigated_plots_ride_out_winter_frost(monkeypatch):
    import app.simulation as sim_mod
    monkeypatch.setattr(sim_mod, "WINTER_FROST_CHANCE", 0.5)
    s = Simulation(ag_cfg(season_length=40, plant_growth_rate=0.0, food_count=2))
    s.tick = 3 * 40 + 5  # season_length=40 → winter is the fourth season band
    assert s._season() == "winter"
    open_crop = s.world.add(Food(x=10.0, y=10.0, growth=1.0, variant="grass"))
    furrow_crop = s.world.add(Food(x=50.0, y=50.0, growth=1.0, variant="grass", irrigated=True))
    for _ in range(14):
        s.step()
    assert open_crop.id not in s.world.entities or open_crop.growth < 0.7, \
        "exposed crops are bitten by frost"
    assert furrow_crop.id in s.world.entities and furrow_crop.growth >= 0.99, \
        "furrows hold the moisture — the bed survives intact"


# ----------------------------------------------------------------- Phase C

def test_granary_deposit_on_sated_grain_harvest():
    s = Simulation(ag_cfg(granary_capacity=100.0))
    house = House(x=30.0, y=30.0, size=6.0)
    s.world.add(house)
    make_clan(s, 1, house)
    harvester = make_farmer(s, 40.0, 40.0, skill=0.0)
    harvester.energy = 75.0  # sated enough to store, hungry enough to harvest
    grain = s.world.add(Food(x=41.0, y=40.0, growth=1.0, variant="grain"))

    for _ in range(6):
        s.step()
        if grain.id not in s.world.entities:
            break
    store = s.clans[1]
    assert grain.id not in s.world.entities
    assert store["granary"] > 0.0, "sated harvesters lay grain by"
    assert store["harvest_total"] >= store["granary"]


def test_starving_member_draws_the_granary():
    s = Simulation(ag_cfg(granary_capacity=100.0))
    house = House(x=30.0, y=30.0, size=6.0)
    s.world.add(house)
    make_clan(s, 1, house)
    s.clans[1]["larder"] = 0.0
    s.clans[1]["granary"] = 50.0
    hungry = make_farmer(s, 31.0, 31.0, skill=0.0)
    hungry.energy = 10.0  # starving

    for _ in range(5):
        s.step()
    assert s.clans[1]["granary"] < 50.0, "famine opens the granary doors"
    assert hungry.energy > 8.0, "the store feeds its own"


def test_banquet_at_overflowing_granary():
    s = Simulation(ag_cfg(banquets_enabled=True, granary_capacity=100.0))
    house = House(x=30.0, y=30.0, size=6.0)
    s.world.add(house)
    make_clan(s, 1, house)
    guest = make_farmer(s, 31.0, 31.0, skill=0.0)
    start = 100.0 * BANQUET_FILL_FRACTION + 20.0
    s.clans[1]["granary"] = start

    for _ in range(70):  # cross a %60 gate
        s.step()
        if any(e.type == "banquet" for e in s.history):
            break
    banquets = [e for e in s.history if e.type == "banquet"]
    assert banquets, "an overflowing granary feeds a feast"
    assert s.clans[1]["feast_until"] > 0
    assert s.clans[1]["granary"] < start
    assert guest.emote == "cheer" or guest.energy > 88.0


def test_feast_boosts_fertility():
    s = Simulation(ag_cfg(birth_enabled=True))
    house = House(x=30.0, y=30.0, size=6.0)
    s.world.add(house)
    make_clan(s, 1, house)
    s.clans[1]["feast_until"] = 10 ** 9  # eternal feast
    # adults in the fertile stage of life (≥30% of lifespan)
    mother = s.world.add(Creature(x=31.0, y=31.0, sides=2, shape="line", caste="Woman", clan_id=1, energy=95.0, age=2200))
    father = s.world.add(Creature(x=32.0, y=31.0, sides=3, shape="polygon", caste="Soldier", clan_id=1, energy=95.0, age=2200))
    s._init_creature_evolution(mother)
    s._init_creature_evolution(father)

    births = 0
    for _ in range(600):
        s.step()
        births = sum(1 for e in s.history if e.type == "birth")
        if births:
            break
    assert births, "feasting clans are generous with more than bread"


# ----------------------------------------------------------------- Phase D

def test_soil_depletes_under_monocropping():
    s = Simulation(ag_cfg(soil_depletion_enabled=True))
    x0, y0 = 10.0, 10.0
    fresh = s._soil_at(x0, y0)
    assert fresh == pytest.approx(1.0)
    for _ in range(50):
        s._deplete_soil(x0, y0, 0.1)
    assert s._soil_at(x0, y0) < fresh
    # a plant grown in the exhausted cell grows slower than one in fresh soil
    tired = s.world.add(Food(x=x0 + 1.0, y=y0, growth=0.5))
    perky = s.world.add(Food(x=70.0, y=70.0, growth=0.5))
    for _ in range(6):
        noon_step(s)
    assert perky.growth - 0.5 > tired.growth - 0.5 > 0, "exhausted soil grows less"


def test_compost_restores_depleted_soil():
    s = Simulation(ag_cfg())
    for _ in range(50):
        s._deplete_soil(40.0, 40.0, 0.1)
    low = s._soil_at(40.0, 40.0)
    s._fertilize_soil(40.0, 40.0, 10.0, 0.4)
    assert s._soil_at(40.0, 40.0) > low
    assert s._soil_at(48.0, 46.0) > low, "compost spreads through the bed"


def test_corpse_nutrients_refill_the_soil_grid():
    s = Simulation(ag_cfg(nutrient_cycle_rate=1.0, corpse_ttl=2))
    before = s._soil_at(26.0, 20.0)
    s.world.add(Creature(x=20.0, y=20.0, energy=0.01))  # dies at once
    for _ in range(4):
        s.step()
    assert s._soil_at(26.0, 20.0) > before, "death enriches the field it falls on"


# ----------------------------------------------------------------- Phase E

def test_famine_raid_carries_off_the_granary():
    s = Simulation(ag_cfg(war_enabled=True, granaries_enabled=True))
    ha = House(x=40.0, y=40.0, size=6.0)
    hb = House(x=44.0, y=44.0, size=6.0)
    s.world.add(ha)
    s.world.add(hb)
    make_clan(s, 1, ha)   # breadbasket: full granary
    make_clan(s, 2, hb)   # starving martial clan
    victim = make_farmer(s, 43.5, 43.0, clan_id=1, skill=0.0)   # lower id loses the duel
    raider = make_farmer(s, 43.0, 43.0, clan_id=2, skill=0.0)
    s.clans[1]["granary"] = 100.0
    s.clans[2]["granary"] = 0.0
    s.clans[2]["larder"] = 0.0
    pair = s._relation_pair(1, 2)
    s.relations[pair] = -100  # open feud
    s.world.rebuild_index()
    s._refresh_cache()

    s._update_war()

    raids = [e for e in s.history if e.type == "raid"]
    assert raids, "the war party carries off what it can carry"
    assert s.clans[1]["granary"] < 100.0
    assert s.clans[2]["granary"] > 0.0


def test_no_raid_when_stores_are_full():
    s = Simulation(ag_cfg(war_enabled=True, granaries_enabled=True))
    ha = House(x=40.0, y=40.0, size=6.0)
    hb = House(x=44.0, y=44.0, size=6.0)
    s.world.add(ha)
    s.world.add(hb)
    make_clan(s, 1, ha)
    make_clan(s, 2, hb)
    raider = make_farmer(s, 43.0, 43.0, clan_id=2, skill=0.0)
    victim = make_farmer(s, 43.5, 43.0, clan_id=1, skill=0.0)
    s.clans[1]["granary"] = 100.0
    s.clans[2]["granary"] = 300.0  # no famine here
    pair = s._relation_pair(1, 2)
    s.relations[pair] = -100
    s.world.rebuild_index()
    s._refresh_cache()

    s._update_war()

    assert not [e for e in s.history if e.type == "raid"], \
        "raids are desperation, not policy"
    assert s.clans[1]["granary"] == 100.0


def test_sacred_hospitality_buys_non_aggression():
    s = Simulation(ag_cfg(seed=13))
    host_house = House(x=30.0, y=30.0, size=6.0)
    s.world.add(host_house)
    make_clan(s, 1, host_house)
    stranger_house = House(x=60.0, y=60.0, size=6.0)
    s.world.add(stranger_house)
    make_clan(s, 2, stranger_house)
    host = s.world.add(Creature(x=40.0, y=40.0, sides=4, shape="polygon", caste="Gentleman",
                                clan_id=1, energy=90.0, personality="altruistic"))
    # an infant stranger: too slow to wander out of reach before the gift lands
    guest = s.world.add(Creature(x=41.0, y=40.0, sides=3, shape="polygon", caste="Soldier",
                                 clan_id=2, energy=15.0, age=10))
    guest.speed = 0.1
    s._init_creature_evolution(host)
    host.personality = "altruistic"  # evolution rolls personalities randomly
    host.food_basket = 2
    pair = s._relation_pair(1, 2)
    s.relations[pair] = 0  # neutral strangers may share bread

    fed = False
    for _ in range(60):
        s.step()
        if guest.energy > 20.0:
            fed = True
            break
    assert fed, "bread is broken with the stranger"
    assert s.relations[pair] > 0, "hospitality warms relations"
    assert any(e.type == "hospitality" for e in s.history)


# ------------------------------------------------------------------ laws

@pytest.fixture()
def client():
    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"
    return c


def test_agriculture_laws_roundtrip(client):
    r = client.post(
        "/api/laws?persist=false",
        json={
            "agriculture_enabled": False,
            "granaries_enabled": False,
            "granary_capacity": 250.0,
            "soil_depletion_enabled": False,
            "banquets_enabled": False,
        },
    )
    assert r.status_code == 200
    laws = r.json()
    assert laws["agriculture_enabled"] is False
    assert laws["granaries_enabled"] is False
    assert laws["granary_capacity"] == 250.0
    assert laws["soil_depletion_enabled"] is False
    assert laws["banquets_enabled"] is False
