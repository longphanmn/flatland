"""§AT-2 / §AT-3 — one house, one clan: strict sleeping exclusivity, hostile
takeover of weak rivals' spare roofs, and orphan-claim cleanup."""

import pytest

from app.config import Config
from app.entities import Creature, House
from app.protocol import HistoryEvent
from app.simulation import Simulation


def clan_cfg(**kw) -> Config:
    zeros = dict(
        num_triangles=0, num_squares=0, num_pentagons=0, num_hexagons=0,
        num_priests=0, num_women=0, food_count=0, num_houses=-1,
        house_density=0.0,  # no random houses: tests place their own roofs
        day_length=8,
        adult_age=0.0,
        weather_change_rate=0.0,
        shelter_enabled=True,
        house_claim_enabled=True,
        schism_enabled=False,
        war_enabled=False,
        predation_enabled=False,
        cannibalism_enabled=False,
        communication_enabled=False,
        knowledge_enabled=False,
        disease_enabled=False,
        birth_enabled=False,
    )
    zeros.update(kw)
    return Config(**zeros)


def make_clan(s: Simulation, members: list[Creature]) -> int:
    """Register a clan for the given creatures (bypasses founding seeding)."""
    cid = s._new_clan(members[0] if members else None)
    for m in members:
        m.clan_id = cid
    return cid


def test_house_for_never_returns_a_foreign_roof():
    """§AT-3 strict exclusivity: a creature whose own roof is full must not
    spill into another clan's house — only neutral roofs qualify."""
    s = Simulation(clan_cfg(seed=31))
    big = House(x=25.0, y=25.0, size=16.0)  # rival's hall
    neutral = House(x=90.0, y=25.0, size=10.0)
    s.world.add(big)
    s.world.add(neutral)
    rival = s.world.add(Creature(x=25.0, y=25.0, energy=100.0))
    home_body = s.world.add(Creature(x=80.0, y=25.0, energy=100.0))

    rcid = make_clan(s, [rival])
    hcid = make_clan(s, [home_body])
    big.clan_id = rcid
    big.clan_color = s.clans[rcid]["color"]
    neutral.clan_id = 0
    s._refresh_cache()

    # The rival house is nearer but foreign — the pick must be the neutral roof.
    got = s._house_for(home_body, [big, neutral])
    assert got is not None and got.id == neutral.id


def test_clanless_creature_sleeps_only_in_unowned_houses():
    s = Simulation(clan_cfg(seed=32, house_claim_enabled=True))
    claimed = House(x=25.0, y=25.0, size=10.0)
    free = House(x=60.0, y=25.0, size=10.0)
    s.world.add(claimed)
    s.world.add(free)
    owner = s.world.add(Creature(x=25.0, y=25.0, energy=100.0))
    drifter = s.world.add(Creature(x=55.0, y=25.0, energy=100.0))
    ocid = make_clan(s, [owner])
    claimed.clan_id = ocid
    claimed.clan_color = s.clans[ocid]["color"]
    drifter.clan_id = 0  # clanless
    s._refresh_cache()

    got = s._house_for(drifter, [claimed, free])
    assert got is not None and got.id == free.id


def test_growing_clan_takes_over_weak_rivals_empty_spare():
    """§AT-2: crowded clan + no free houses + a weak rival's empty non-main
    house ⇒ the invader claims it, an event lands, relations sour."""
    s = Simulation(clan_cfg(seed=33, house_capacity=4))
    # Invader clan: 6 bodies, one small hut (capacity int(36/64*4)=2 beds).
    invaders = [
        s.world.add(Creature(x=20.0 + i * 0.5, y=20.0, energy=100.0)) for i in range(6)
    ]
    # Victim clan: 1 member, main hall (8 beds) + a distant spare hut.
    victim = s.world.add(Creature(x=200.0, y=200.0, energy=100.0))
    icid = make_clan(s, invaders)
    vid = make_clan(s, [victim])

    main_hall = House(x=21.0, y=21.0, size=12.0)
    spare = House(x=205.0, y=205.0, size=8.0)
    s.world.add(main_hall)
    s.world.add(spare)
    main_hall.clan_id = icid
    main_hall.clan_color = s.clans[icid]["color"]
    spare.clan_id = vid
    spare.clan_color = s.clans[vid]["color"]
    s._set_main_house_for_clan(icid, main_hall)
    s._set_main_house_for_clan(vid, main_hall if False else spare)
    # ^ victim's MAIN is the spare? No — fix: main should be distinct. Reassign:
    # give the victim its seat at the spare and add nothing else; instead mark
    # the takeover target as NOT main by pointing main elsewhere.

    # Simpler setup: victim keeps `spare` as non-main by making a tiny main hut.
    victims_seat = House(x=210.0, y=210.0, size=6.0)
    s.world.add(victims_seat)
    victims_seat.clan_id = vid
    victims_seat.clan_color = s.clans[vid]["color"]
    s._set_main_house_for_clan(vid, victims_seat)
    spare.is_main = False

    s._refresh_cache()
    before = spare.clan_id
    taken = s._try_house_takeover(icid, invaders, s._functional_houses())
    assert taken is not None and taken.id == spare.id
    assert spare.clan_id == icid and before == vid
    types = [e.type for e in s.history]
    assert "takeover" in types
    ev = next(e for e in s.history if e.type == "takeover")
    assert ev.payload["invader_clan"] == icid
    assert ev.payload["victim_clan"] == vid
    pair = tuple(sorted((icid, vid)))
    assert s.relations.get(pair, 0) <= -25


def test_takeover_spares_occupied_or_main_or_needed_houses():
    """Main seats, slept-in houses and houses a rival still needs (pop ≥ beds/2)
    are never stolen."""
    # 1. main seat is protected
    s = Simulation(clan_cfg(seed=34, house_capacity=4))
    invaders = [s.world.add(Creature(x=20.0, y=20.0, energy=100.0))]
    icid = make_clan(s, invaders)
    victim = s.world.add(Creature(x=200.0, y=200.0, energy=100.0))
    vid = make_clan(s, [victim])
    seat = House(x=201.0, y=201.0, size=10.0)
    s.world.add(seat)
    seat.clan_id = vid
    seat.clan_color = s.clans[vid]["color"]
    s._set_main_house_for_clan(vid, seat)
    s._refresh_cache()
    assert s._try_house_takeover(icid, invaders, s._functional_houses()) is None

    # 2. a house with a sleeper under its roof tonight is protected
    s2 = Simulation(clan_cfg(seed=35, house_capacity=4))
    inv2 = [s2.world.add(Creature(x=20.0, y=20.0, energy=100.0))]
    icid2 = make_clan(s2, inv2)
    vic2 = s2.world.add(Creature(x=200.0, y=200.0, energy=100.0))
    vid2 = make_clan(s2, [vic2])
    seat2 = House(x=201.0, y=201.0, size=6.0)
    slept = House(x=220.0, y=220.0, size=10.0)
    for h in (seat2, slept):
        s2.world.add(h)
        h.clan_id = vid2
        h.clan_color = s2.clans[vid2]["color"]
    s2._set_main_house_for_clan(vid2, seat2)
    sleeper = s2.world.add(Creature(x=220.5, y=220.5, energy=100.0))
    sleeper.clan_id = vid2
    sleeper.sleeping = True
    s2._refresh_cache()
    assert s2._try_house_takeover(icid2, inv2, s2._functional_houses()) is None

    # 3. a rival whose population fills half its beds still needs its roofs
    s3 = Simulation(clan_cfg(seed=36, house_capacity=4))
    inv3 = [s3.world.add(Creature(x=20.0, y=20.0, energy=100.0))]
    icid3 = make_clan(s3, inv3)
    fam = [
        s3.world.add(Creature(x=200.0 + i * 0.4, y=200.0, energy=100.0))
        for i in range(8)
    ]
    vid3 = make_clan(s3, fam)
    hut3 = House(x=201.0, y=201.0, size=10.0)
    spare3 = House(x=220.0, y=220.0, size=8.0)
    for h in (hut3, spare3):
        s3.world.add(h)
        h.clan_id = vid3
        h.clan_color = s3.clans[vid3]["color"]
        h.is_main = False
    s3._set_main_house_for_clan(vid3, hut3)
    s3._refresh_cache()
    assert s3._try_house_takeover(icid3, inv3, s3._functional_houses()) is None


def test_takeover_disabled_with_house_claim_law_off():
    s = Simulation(clan_cfg(seed=35, house_claim_enabled=False))
    invaders = [s.world.add(Creature(x=20.0, y=20.0, energy=100.0))]
    icid = make_clan(s, invaders)
    victim = s.world.add(Creature(x=200.0, y=200.0, energy=100.0))
    vid = make_clan(s, [victim])
    spare = House(x=205.0, y=205.0, size=8.0)
    s.world.add(spare)
    spare.clan_id = vid
    s._set_main_house_for_clan(vid, spare)
    s._refresh_cache()
    assert s._try_house_takeover(icid, invaders, s._functional_houses()) is None
    assert spare.clan_id == vid


def test_orphan_house_claim_cleared_when_clan_dies():
    """§AT-3 audit: a claim whose clan no longer exists is reset immediately."""
    s = Simulation(clan_cfg(seed=36))
    ghost_owner = s.world.add(Creature(x=50.0, y=50.0, energy=100.0))
    cid = make_clan(s, [ghost_owner])
    h = House(x=52.0, y=52.0, size=8.0)
    s.world.add(h)
    h.clan_id = cid
    h.clan_color = s.clans[cid]["color"]
    s._set_main_house_for_clan(cid, h)
    # The clan dies out entirely
    s.world.remove(ghost_owner.id)
    s._audit_house_claims()
    assert h.clan_id == 0
    assert h.clan_color is None
    assert not h.is_main


def test_settlement_tick_runs_takeover_end_to_end():
    """Integration through step(): expansion block every 50 ticks picks up the
    invasion when the growing clan has nowhere else to sleep."""
    cfg = clan_cfg(seed=37, house_capacity=4)  # density 0: no auto houses
    s = Simulation(cfg)
    invaders = [
        s.world.add(Creature(x=30.0 + i * 0.4, y=30.0, energy=500.0, lifespan=100000.0))
        for i in range(7)
    ]
    icid = make_clan(s, invaders)
    victim = s.world.add(Creature(x=120.0, y=120.0, energy=500.0, lifespan=100000.0))
    vid = make_clan(s, [victim])

    hut = House(x=30.0, y=30.0, size=8.0)       # invader home: 4 beds for 7 bodies
    spare = House(x=118.0, y=118.0, size=8.0)   # victim spare, nobody sleeps there
    seat = House(x=126.0, y=126.0, size=6.0)    # victim main
    for hh in (hut, spare, seat):
        s.world.add(hh)
    hut.clan_id = icid
    hut.clan_color = s.clans[icid]["color"]
    spare.clan_id = vid
    spare.clan_color = s.clans[vid]["color"]
    seat.clan_id = vid
    seat.clan_color = s.clans[vid]["color"]
    s._set_main_house_for_clan(icid, hut)
    s._set_main_house_for_clan(vid, seat)
    spare.takeover_tick = -1

    # Drive into an expansion tick (tick % 50 == 0 inside step)
    while s.tick % 50 != 49:
        s.step()
    s.step()  # now the expansion block runs during this tick
    assert spare.clan_id == icid, "crowded clan should have seized the spare"
    types = [e.type for e in s.history]
    assert "takeover" in types
