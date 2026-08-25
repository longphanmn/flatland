"""§AQ PH-6 — material physics: four build materials, structural wear and
repair, collapses that leave rubble blocking the lot until builders clear it."""
import math

from app.config import Config
from app.entities import Creature, House
from app.simulation import (
    INSULATION_BY_MATERIAL,
    MATERIAL_STATS,
    RIVER_BASE_HW,
    RIVER_SILT_RADIUS,
    Simulation,
)


def mat_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=100000,
        season_length=100000,
        weather_change_rate=0.0,
        weather_enabled=False,
        shelter_enabled=False,
        disease_enabled=False,
        birth_enabled=False,
        predation_enabled=False,
        war_enabled=False,
        cannibalism_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
        schism_enabled=False,
        age_enabled=False,
        rivers_enabled=False,
        relief_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def test_material_table_covers_four_builds_with_clay_best_insulator():
    assert set(MATERIAL_STATS) == {"straw", "wood", "stone", "clay"}
    assert INSULATION_BY_MATERIAL["clay"] > INSULATION_BY_MATERIAL["stone"]
    assert MATERIAL_STATS["stone"]["durability"] > MATERIAL_STATS["clay"]["durability"]
    assert MATERIAL_STATS["clay"]["durability"] > MATERIAL_STATS["straw"]["durability"]


def test_riverbank_settlements_dig_clay():
    s = Simulation(mat_cfg())
    s.rivers = [{
        "cy": 150.0, "hw": RIVER_BASE_HW, "base_hw": RIVER_BASE_HW,
        "dir": 1.0, "water": 0.0, "flood_ticks": 0, "silt_ticks": 0,
    }]
    picks = set()
    for _ in range(60):
        picks.add(s._pick_house_material(200.0, 155.0))  # beside the channel
    assert "clay" in picks
    dry = {s._pick_house_material(200.0, 280.0) for _ in range(40)}
    assert "clay" not in dry  # the high ground never digs brick


def test_storms_wear_and_spent_roofs_collapse():
    s = Simulation(mat_cfg(weather_enabled=True))
    h = s.world.add(House(x=100.0, y=100.0, size=8.0, material="straw"))
    s._refresh_cache()
    s.world.rebuild_index()
    max_hp = MATERIAL_STATS["straw"]["durability"]
    h.hp = 0.5  # a roof already at the end of its life
    for _ in range(6):
        s.weather = "storm"
        s.step()
        if h.is_ruin:
            break
        s.weather = "clear"
        s.step()
    assert h.is_ruin
    kinds = [e.payload.get("kind") for e in s.history if e.type == "ruin"]
    assert "collapse" in kinds


def test_builders_mend_the_roof():
    s = Simulation(mat_cfg())
    h = s.world.add(House(x=100.0, y=100.0, size=8.0, material="wood"))
    mason = s.world.add(Creature(x=103.0, y=103.0, energy=90.0, lifespan=100000.0))
    mason.personality = "builder"
    max_hp = MATERIAL_STATS["wood"]["durability"]
    h.hp = max_hp * 0.5
    houses = [h]
    tod = 0.5
    for _ in range(30):
        mason.x, mason.y = 103.0, 103.0
        s._refresh_cache()
        s.world.rebuild_index()
        s._update_structures()
    assert h.hp > max_hp * 0.5


def test_rubble_blocks_until_cleared():
    s = Simulation(mat_cfg())
    h = s.world.add(House(x=200.0, y=150.0, size=10.0, material="stone"))
    h.is_ruin = True
    h.rubble = 5.0
    s._cached_houses = [h]
    loiterer = s.world.add(Creature(x=200.0, y=150.0, energy=90.0,
                                    lifespan=100000.0, speed=0.2))
    s.world.rebuild_index()
    s._resolve_rock_collision(loiterer)  # inside the rubble: pushed out
    dx, dy = s.world.delta(h.x, h.y, loiterer.x, loiterer.y)
    assert math.hypot(dx, dy) >= h.size * 0.35 - 0.01
    # a builder clears the lot over time
    mason = s.world.add(Creature(x=202.0, y=152.0, energy=90.0, lifespan=100000.0))
    mason.personality = "builder"
    for _ in range(120):
        if h.id not in s.world.entities or h.rubble == 0.0:
            break
        mason.x, mason.y = 202.0, 152.0
        s._cached_houses = [h]
        s._cached_creatures = [mason]
        s._update_structures()
    assert h.rubble == 0.0
