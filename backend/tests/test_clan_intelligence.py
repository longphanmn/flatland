import pytest
from app.config import Config
from app.entities import Creature, House
from app.simulation import Simulation


def clan_cfg(**kwargs) -> Config:
    base = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, num_houses=0, food_count=0,
        communication_enabled=True,
        knowledge_enabled=True,
        sleep_enabled=True,
        disease_enabled=False,
        war_enabled=True,
        succession_enabled=True,
        territory_enabled=True,
    )
    base.update(kwargs)
    return Config(**base)


def test_clan_governance_archetypes():
    s = Simulation(clan_cfg(seed=100))
    
    # Founder Gentleman -> Monarchy
    g = s.world.add(Creature(x=10.0, y=10.0, sides=4, shape="polygon", caste="Gentleman"))
    cid1 = s._new_clan(g)
    assert s.clans[cid1]["governance"] == "monarchy"
    
    # Founder Priest -> Theocracy
    p = s.world.add(Creature(x=30.0, y=30.0, sides=24, shape="polygon", caste="Priest"))
    cid2 = s._new_clan(p)
    assert s.clans[cid2]["governance"] == "theocracy"
    
    # Founder Soldier -> Junta
    sol = s.world.add(Creature(x=50.0, y=50.0, sides=3, shape="polygon", caste="Soldier"))
    cid3 = s._new_clan(sol)
    assert s.clans[cid3]["governance"] == "junta"


def test_monarchy_dynastic_succession():
    s = Simulation(clan_cfg(seed=101))
    king = s.world.add(Creature(x=20.0, y=20.0, sides=4, shape="polygon", caste="Gentleman", clan_id=1, age=5000))
    cid = s._new_clan(king)
    king.clan_id = cid
    
    # Member 1: Older stranger
    stranger = s.world.add(Creature(x=21.0, y=20.0, sides=4, shape="polygon", caste="Gentleman", clan_id=cid, age=4000))
    # Member 2: King's child (younger)
    prince = s.world.add(Creature(x=22.0, y=20.0, sides=4, shape="polygon", caste="Gentleman", clan_id=cid, age=1000, father_id=king.id))
    
    # King dies
    s._kill(king, "old_age")
    
    # Prince should succeed due to dynastic monarchy rule
    assert s.clans[cid]["leader_id"] == prince.id


def test_clan_task_board_and_rationing_bylaw():
    s = Simulation(clan_cfg(seed=102))
    founder = s.world.add(Creature(x=20.0, y=20.0, sides=4, shape="polygon", caste="Gentleman"))
    cid = s._new_clan(founder)
    founder.clan_id = cid
    
    # Check initial balanced state
    assert s.clans[cid]["task_board"]["priority"] == "balanced"
    
    # Force low larder & winter (winter is season index 3)
    s.clans[cid]["larder"] = 10.0
    s.tick = s.config.season_length * 3
    assert s._season() == "winter"
    
    s._update_clan_task_boards_and_bylaws()

    
    assert s.clans[cid]["bylaws"]["rationing"] is True
    assert s.clans[cid]["task_board"]["priority"] == "food_security"
    assert s.clans[cid]["task_board"]["harvester_weight"] == 2.0

