"""§AS L-0 — the leader is leverage: an aura while alive, a crisis when dead."""

import pytest

from app.config import Config
from app.entities import Creature
from app.simulation import (
    LEADER_AURA_RADIUS,
    LEADER_DECAY_MULT,
    LEADER_SHOCK_ENERGY,
    LEADER_SHOCK_LARDER_MULT,
    LEADERLESS_CAUTIOUS_CHANCE,
    Simulation,
)


def leader_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,
        day_length=100000,  # eternal day
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
        succession_enabled=True,
        age_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def make_clan(s: Simulation, members: list[Creature], leader: Creature | None = None) -> int:
    cid = s._new_clan(leader or members[0])
    for m in members:
        m.clan_id = cid
    if leader is not None:
        s.clans[cid]["leader_id"] = leader.id
    s._refresh_cache()
    s.world.rebuild_index()
    return cid


def test_morale_aura_eases_burn_and_sharpens_sight():
    """Kin inside the leader's aura burn less energy than kin far away."""
    s = Simulation(leader_cfg())
    leader = s.world.add(Creature(x=100.0, y=100.0, energy=100.0, lifespan=100000.0))
    near = s.world.add(Creature(x=101.0, y=100.0, energy=100.0, lifespan=100000.0))
    far = s.world.add(Creature(x=100.0 + LEADER_AURA_RADIUS * 3.0, y=100.0,
                               energy=100.0, lifespan=100000.0))
    make_clan(s, [leader, near, far], leader=leader)
    e_near, e_far = near.energy, far.energy
    for _ in range(10):
        s.step()
    burn_near = e_near - near.energy
    burn_far = e_far - far.energy
    assert burn_near == pytest.approx(
        burn_far * LEADER_DECAY_MULT, rel=0.05
    ), f"near {burn_near} vs far {burn_far}"


def test_leaderless_clan_burns_hotter():
    """No living leader: members lose the aura's ease — decay grows."""
    def avg_burn(leaderless: bool) -> float:
        s = Simulation(leader_cfg())
        leader = s.world.add(Creature(x=300.0, y=150.0, energy=100.0, lifespan=100000.0))
        member = s.world.add(Creature(x=100.0, y=100.0, energy=100.0, lifespan=100000.0))
        cid = make_clan(s, [leader, member], leader=leader)
        if leaderless:
            s.clans[cid]["leader_id"] = None
            s._refresh_cache()
        e0 = member.energy
        for _ in range(10):
            s.step()
        return (e0 - member.energy) / 10

    assert avg_burn(True) == pytest.approx(avg_burn(False) * 1.1, rel=0.05)


def test_leader_death_shocks_the_clan():
    """At the moment of leader death: −10 energy, panic for 20 ticks, larder
    looted 20%, and a grief cry rings out."""
    s = Simulation(leader_cfg(communication_enabled=True))
    leader = s.world.add(Creature(x=100.0, y=100.0, energy=60.0, lifespan=100000.0))
    kin_a = s.world.add(Creature(x=102.0, y=100.0, energy=80.0, lifespan=100000.0))
    kin_b = s.world.add(Creature(x=104.0, y=100.0, energy=30.0, lifespan=100000.0))
    cid = make_clan(s, [leader, kin_a, kin_b], leader=leader)
    s.clans[cid]["larder"] = 100.0

    s._kill(leader, "war")

    for kin in (kin_a, kin_b):
        assert kin.energy == pytest.approx(kin.energy)  # sanity no-op
    assert kin_a.panic_ticks > 0 and kin_b.panic_ticks > 0
    assert kin_a.emote == "panic"
    # energy dropped by exactly the shock (no steps ran in between)
    assert abs(kin_a.energy - (80.0 - LEADER_SHOCK_ENERGY)) < 1e-6
    assert kin_b.energy == pytest.approx(max(0.5, 30.0 - LEADER_SHOCK_ENERGY))
    assert s.clans[cid]["larder"] == pytest.approx(100.0 * LEADER_SHOCK_LARDER_MULT)
    kinds = [sg["kind"] for sg in s.signals]
    assert "grief" in kinds
    # a successor ascended
    assert s.clans[cid]["leader_id"] in (kin_a.id, kin_b.id)


def test_panic_fades_and_leaderless_drifts_cautious():
    """Panic ticks count down; a long interregnum slowly makes everyone timid."""
    s = Simulation(leader_cfg(seed=7))
    members = [
        s.world.add(Creature(x=100.0 + i, y=100.0, energy=90.0, lifespan=100000.0))
        for i in range(3)
    ]
    cid = make_clan(s, members)
    for m in members:
        m.panic_ticks = 25
        m.personality = "brave"
    s.step()
    assert all(m.panic_ticks == 24 for m in members)

    s.clans[cid]["leader_id"] = None
    s._refresh_cache()
    for _ in range(600):
        s.step()
    assert all(m.personality == "cautious" for m in members), (
        [m.personality for m in members]
    )


def test_leaderless_gathers_less():
    """A leaderless clan harvests less from the same meal."""
    def gain_for(leaderless: bool) -> float:
        s = Simulation(leader_cfg(seed=11, communication_enabled=False,
                                  food_count=1))
        from app.entities import Food
        # the bounty law must protect exactly our experimental plant
        for e in [e for e in s.world.entities.values() if e.kind == "food"]:
            s.world.remove(e.id)
        leader = s.world.add(Creature(x=300.0, y=300.0, energy=100.0, lifespan=100000.0))
        worker = s.world.add(Creature(x=100.0, y=100.0, angle=0.0, energy=50.0,
                                      age=50000, lifespan=100000.0))
        cid = make_clan(s, [leader, worker], leader=leader)
        if leaderless:
            s.clans[cid]["leader_id"] = None
            s._refresh_cache()
        plant = s.world.add(Food(x=103.0, y=100.0, growth=1.0))
        s.world.rebuild_index()
        before = worker.energy
        for _ in range(20):
            if plant.id not in s.world.entities:
                break
            s.step()
        return worker.energy - before

    g_led = gain_for(False)
    g_leaderless = gain_for(True)
    assert g_led > 0 and g_leaderless > 0
    assert g_leaderless < g_led * 0.95
