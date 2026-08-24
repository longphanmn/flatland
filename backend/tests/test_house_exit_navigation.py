import pytest
from app.config import Config
from app.entities import Creature, House, Food
from app.simulation import Simulation


def house_test_cfg(**kwargs) -> Config:
    base = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        day_length=500, season_length=1000,
    )
    base.update(kwargs)
    return Config(**base)


@pytest.mark.parametrize("door_side", ["north", "south", "east", "west"])
@pytest.mark.parametrize("door_offset", [-1.5, 0.0, 1.5])
def test_creatures_navigate_out_of_house_through_door(door_side, door_offset):
    """Creatures spawned or sleeping inside houses must reliably find and exit through doorways."""
    s = Simulation(house_test_cfg())
    h = s.world.add(House(x=50.0, y=50.0, size=8.0, door_width=3.0, door_side=door_side, door_offset=door_offset))
    
    # Food is placed on the opposite side of the house from the doorway
    food_x = 50.0 if door_side in ("north", "south") else (10.0 if door_side == "east" else 90.0)
    food_y = (10.0 if door_side == "south" else 90.0) if door_side in ("north", "south") else 50.0
    s.world.add(Food(x=food_x, y=food_y, variant="grass", growth=1.0))
    
    # Place creature inside house
    c = s.world.add(Creature(x=48.0, y=48.0, sides=4, energy=50.0, speed=0.6))
    s._init_creature_evolution(c)
    
    assert s._is_inside_house(c, h) is True
    
    exited = False
    for _ in range(30):
        s.step()
        if not s._is_inside_house(c, h):
            exited = True
            break
            
    assert exited is True, f"Creature failed to exit house with door_side={door_side}, offset={door_offset}"
    # Ensure creature didn't die or get blocked indefinitely
    assert c.id in s.world.entities
    assert c.blocked_ticks < 5


def test_sleeping_creature_exits_at_dawn_to_eat():
    """Creatures sheltering at night wake up at dawn and cleanly leave to forage."""
    cfg = house_test_cfg(day_length=40, sleep_enabled=True, shelter_enabled=True)
    s = Simulation(cfg)
    h = s.world.add(House(x=50.0, y=50.0, size=8.0, door_width=3.0, door_side="south", door_offset=0.0))
    s.world.add(Food(x=50.0, y=10.0, variant="grass", growth=1.0)) # Food north, door south
    
    c = s.world.add(Creature(x=50.0, y=50.0, sides=4, energy=60.0, speed=0.6))
    s._init_creature_evolution(c)
    
    # Start at night (tick 30 of day_length 40)
    s.tick = 30
    s.step()
    assert c.sleeping is True or c.indoors is True
    
    # Run through dawn (tick 40 wraps to tick 0 / daytime)
    for _ in range(30):
        s.step()
        
    # At daytime, creature must exit house and not be stuck inside
    assert not s._is_inside_house(c, h)
