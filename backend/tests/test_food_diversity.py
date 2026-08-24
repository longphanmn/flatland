import pytest
from app.config import Config
from app.entities import Creature, Food
from app.simulation import Simulation


def food_cfg(**kwargs) -> Config:
    base = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        plant_variants_enabled=True,
        disease_enabled=True,
        food_decay_enabled=True,
        food_lifespan_ticks=100,
    )
    base.update(kwargs)
    return Config(**base)


def test_grain_calorie_density_and_longevity():
    s = Simulation(food_cfg(seed=300))
    c = s.world.add(Creature(x=10.0, y=10.0, energy=40.0, sides=4, shape="polygon"))
    s._init_creature_evolution(c)
    
    grain = s.world.add(Food(x=10.5, y=10.0, variant="grain", growth=1.0))
    
    # Step simulation to eat grain
    s.step()
    
    # Check energy boost is high (grain gives 45.0 base)
    assert c.energy > 40.0 + 40.0 * 0.9
    assert c.emote == "craft"


def test_medicinal_herb_cures_infection_and_heals():
    s = Simulation(food_cfg(seed=301))
    c = s.world.add(Creature(x=10.0, y=10.0, energy=60.0, health=40.0, infected=True, disease_id=1, sides=4, shape="polygon"))
    s._init_creature_evolution(c)
    
    herb = s.world.add(Food(x=10.5, y=10.0, variant="medicinal_herb", growth=1.0))
    
    # Step simulation to eat herb
    s.step()
    
    # Check infection cured and health healed
    assert c.infected is False
    assert c.disease_id == 0
    assert c.health >= 60.0
    assert c.emote == "heal"


def test_berry_speed_boost():
    s = Simulation(food_cfg(seed=302))
    initial_speed = 0.6
    c = s.world.add(Creature(x=10.0, y=10.0, energy=50.0, speed=initial_speed, sides=4, shape="polygon"))
    s._init_creature_evolution(c)
    
    berry = s.world.add(Food(x=10.5, y=10.0, variant="berry", growth=1.0))
    
    # Step simulation to eat berry
    s.step()
    
    assert c.speed > initial_speed
    assert c.emote == "cheer"


def test_foraging_preference_for_medicinal_herb_when_injured():
    s = Simulation(food_cfg(seed=303))
    # Sick creature placed between grass (closer: 2.0 to the right) and medicinal herb (further: 3.5 to the left)
    c = s.world.add(Creature(x=10.0, y=10.0, energy=70.0, health=30.0, infected=True, angle=3.1415, sides=4, shape="polygon"))
    s._init_creature_evolution(c)
    
    grass = s.world.add(Food(x=12.0, y=10.0, variant="grass", growth=1.0))
    herb = s.world.add(Food(x=6.5, y=10.0, variant="medicinal_herb", growth=1.0))
    
    for _ in range(3):
        s.step()
    
    # Because effective_d2 for herb is scaled by 0.2 (3.5^2 * 0.2 = 2.45 vs 2.0^2 = 4.0),
    # creature targets and moves left towards herb at x=6.5
    assert c.x < 10.0

