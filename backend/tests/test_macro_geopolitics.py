import pytest
from app.config import Config
from app.entities import Creature, House
from app.simulation import Simulation


def macro_cfg(**kwargs) -> Config:
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
        resource_sharing_enabled=True,
        leader_decisions_enabled=True,
        season_length=40,
    )
    base.update(kwargs)
    return Config(**base)


def test_inter_clan_trade_caravan():
    s = Simulation(macro_cfg(seed=200))
    
    # Clan 1: Farmer clan with surplus food
    c1_leader = s.world.add(Creature(x=10.0, y=10.0, sides=4, shape="polygon", caste="Gentleman"))
    cid1 = s._new_clan(c1_leader)
    c1_leader.clan_id = cid1
    s.clans[cid1]["specialization"] = {"farmer": 0.6, "warrior": 0.2, "scavenger": 0.2}
    s.clans[cid1]["larder"] = 80.0
    
    # Clan 2: Warrior clan with low larder
    c2_leader = s.world.add(Creature(x=30.0, y=30.0, sides=3, shape="polygon", caste="Soldier"))
    cid2 = s._new_clan(c2_leader)
    c2_leader.clan_id = cid2
    s.clans[cid2]["specialization"] = {"farmer": 0.1, "warrior": 0.7, "scavenger": 0.2}
    s.clans[cid2]["larder"] = 5.0
    
    # Mutual relations neutral/positive
    s.relations[s._relation_pair(cid1, cid2)] = 10
    
    # Trigger trade check on tick 80
    s.tick = 80
    s._update_trade_caravans()
    
    # Assert food transferred and relations boosted
    assert s.clans[cid1]["larder"] == 68.0
    assert s.clans[cid2]["larder"] == 17.0
    assert s.relations[s._relation_pair(cid1, cid2)] == 22
    assert c1_leader.skills.get("combat", 0.0) >= 1.0


def test_autumn_harvest_festival():
    s = Simulation(macro_cfg(seed=201, season_length=40))
    leader = s.world.add(Creature(x=20.0, y=20.0, sides=4, shape="polygon", caste="Gentleman"))
    cid = s._new_clan(leader)
    leader.clan_id = cid
    
    house = s.world.add(House(x=20.0, y=20.0, size=8.0, clan_id=cid, is_main=True))
    
    child = s.world.add(Creature(x=22.0, y=20.0, sides=4, shape="polygon", generation=1, age=250, clan_id=cid, energy=40.0))
    s._init_creature_evolution(child)
    
    # End of autumn is tick 119 (season index 2, ticks 80..119)
    s.tick = 119
    assert s._season() == "autumn"
    
    s._update_festivals_and_traditions()
    
    assert child.energy > 40.0
    assert child.emote == "cheer"
    assert child.trust.get(leader.id, 0.0) >= 10.0
    assert child.skills.get("farming", 0.0) >= 2.0

