import pytest
from app.config import Config
from app.entities import Creature, House
from app.simulation import Simulation


def test_single_main_house_invariant():
    """Verify that every clan has strictly ONE main house."""
    cfg = Config(seed=42, width=200, height=200, num_houses=10, house_claim_enabled=True)
    sim = Simulation(cfg)

    # Check initial clans
    for cid, clan in sim.clans.items():
        main_hid = clan.get("main_house_id")
        clan_houses = [
            h for h in sim.world.entities.values()
            if isinstance(h, House) and h.clan_id == cid and not h.is_ruin
        ]
        if clan_houses:
            assert main_hid is not None
            main_count = sum(1 for h in clan_houses if h.is_main)
            assert main_count == 1, f"Clan {cid} has {main_count} main houses instead of 1"
            assert any(h.id == main_hid and h.is_main for h in clan_houses)

    # Step simulation and verify invariant holds after expansions / settlements
    for _ in range(50):
        sim.step()

    for cid, clan in sim.clans.items():
        main_hid = clan.get("main_house_id")
        clan_houses = [
            h for h in sim.world.entities.values()
            if isinstance(h, House) and h.clan_id == cid and not h.is_ruin
        ]
        if clan_houses:
            assert main_hid is not None
            main_count = sum(1 for h in clan_houses if h.is_main)
            assert main_count == 1, f"Clan {cid} has {main_count} main houses after ticking"


def test_emergency_carried_food_consumption():
    """Verify that hungry or starving creatures eat carried food from their basket to survive."""
    cfg = Config(seed=101, food_count=0)
    sim = Simulation(cfg)

    # Add a creature with food in basket and low energy
    c = Creature(x=50.0, y=50.0, energy=10.0, caste="Artisan", sides=4)
    c.food_basket = 2
    c.status = "starving"
    sim.world.add(c)

    # Step world: creature should consume 1 food from basket and restore energy
    sim._update_creature(c, houses=[])

    assert c.food_basket == 1
    assert c.energy > 10.0
    assert c.id in sim.world.entities  # Creature survived!



def test_clan_history_tracking():
    """Verify that major clan milestones are logged in clan['history']."""
    cfg = Config(seed=777, width=150, height=150, num_houses=4, house_claim_enabled=True)
    sim = Simulation(cfg)

    for cid, clan in sim.clans.items():
        assert "history" in clan
        assert len(clan["history"]) >= 1
        assert clan["history"][0]["event"] == "founded"

    # Trigger succession by killing leader
    for cid, clan in list(sim.clans.items()):
        lid = clan.get("leader_id")
        if lid and lid in sim.world.entities:
            leader = sim.world.entities[lid]
            if isinstance(leader, Creature):
                sim._kill(leader, "old_age")
                # Check if succession event logged
                hist_events = [h["event"] for h in clan.get("history", [])]
                assert "leader_change" in hist_events
                break
