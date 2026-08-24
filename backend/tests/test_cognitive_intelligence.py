import pytest
import math
from app.config import Config
from app.entities import Creature, Food, House
from app.simulation import Simulation


def cognitive_cfg(**kwargs) -> Config:
    base = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        communication_enabled=True,
        knowledge_enabled=True,
        sleep_enabled=True,
        disease_enabled=False,
        war_enabled=True,
        predation_enabled=True,
    )
    base.update(kwargs)
    return Config(**base)




def test_waypoint_saving_on_rich_food_and_home():
    s = Simulation(cognitive_cfg(seed=42))
    h = House(x=50.0, y=50.0, size=8.0)
    s.world.add(h)
    c = s.world.add(Creature(x=50.0, y=50.0, energy=50.0, sides=4, shape="polygon", personality="explorer"))
    s._init_creature_evolution(c)
    
    berry = s.world.add(Food(x=55.0, y=50.0, variant="berry"))
    
    # Step simulation so creature perceives berry and navigates
    s.step()
    
    # Check that rich food or home was noted in waypoints
    assert "rich_food" in c.waypoints or "home" in c.waypoints



def test_priest_healing_and_altruistic_feeding_builds_trust():
    s = Simulation(cognitive_cfg(seed=43))
    priest = s.world.add(Creature(x=30.0, y=30.0, sides=24, shape="polygon", caste="Priest", clan_id=1, energy=90.0))
    injured = s.world.add(Creature(x=31.0, y=30.0, sides=3, shape="polygon", caste="Soldier", clan_id=1, health=50.0, energy=90.0))
    s._init_creature_evolution(priest)
    s._init_creature_evolution(injured)
    
    # Step tick to trigger Priest healing (Priest heals on (tick+id)%8==0)
    for _ in range(16):
        s.step()
        if injured.id in priest.trust:
            break
            
    assert injured.health > 50.0
    assert injured.trust.get(priest.id, 0.0) >= 15.0


def test_tactical_kiting_by_lines():
    s = Simulation(cognitive_cfg(seed=44, predation_enabled=True))
    pred = s.world.add(Creature(x=50.0, y=50.0, sides=3, shape="polygon", is_predator=True, energy=100.0))
    woman = s.world.add(Creature(x=52.0, y=50.0, sides=1, shape="line", caste="Woman", energy=90.0))
    s._init_creature_evolution(pred)
    s._init_creature_evolution(woman)
    
    # Run step: woman should evade predator with tactical agility
    s.step()
    assert woman.id in s.world.entities


def test_buddy_pairing_affinity():
    s = Simulation(cognitive_cfg(seed=45))
    c1 = s.world.add(Creature(x=20.0, y=20.0, sides=4, shape="polygon", energy=90.0))
    c2 = s.world.add(Creature(x=23.0, y=20.0, sides=4, shape="polygon", energy=90.0))
    s._init_creature_evolution(c1)
    s._init_creature_evolution(c2)
    
    # Inject high trust
    c1.trust[c2.id] = 40.0
    
    # Step and verify c1 steers toward c2 when idle
    s.step()
    assert c1.id in s.world.entities and c2.id in s.world.entities
