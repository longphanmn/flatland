"""§V Clan founding redesign — mixed-caste settlements.

Every functional house anchors a clan; the founding generation joins the clan
of its nearest house, so castes mix inside settlements. `max_clans` pins how
many spatial clans arise. All founding is deterministic given the seed.
"""

from fastapi.testclient import TestClient

from app.config import Config
from app.entities import House
from app.main import app
from app.simulation import Simulation


def anchors_of(s: Simulation) -> dict[int, House]:
    """House claims by clan id (each clan at most one anchor)."""
    anchors: dict[int, House] = {}
    for e in s.world.entities.values():
        if isinstance(e, House) and not e.is_ruin and e.clan_id:
            assert e.clan_id not in anchors  # no double-claim
            anchors[e.clan_id] = e
    return anchors


def houses_of(s: Simulation) -> list[House]:
    return [e for e in s.world.entities.values() if isinstance(e, House) and not e.is_ruin]


def roster_by_house(s: Simulation) -> dict[int, set[int]]:
    """Reconstruct 'join your nearest house's clan' from scratch."""
    houses = houses_of(s)
    by_house: dict[int, set[int]] = {}
    for c in s.world.creatures():
        home = min(houses, key=lambda h: (s.distance(c.x, c.y, h.x, h.y), h.id))
        by_house.setdefault(home.id, set()).add(c.id)
    return by_house


def test_founding_clans_are_mixed_caste_settlements():
    s = Simulation(Config(seed=77))
    founders = s.world.creatures()
    houses = houses_of(s)
    assert houses

    # -1 default: every non-ruin house founded exactly one clan; all founders enrolled
    assert len(s.clans) == len(houses)
    assert set(anchors_of(s)) == set(s.clans)
    assert all(c.clan_id > 0 for c in founders)

    # membership is spatial: each founder's nearest anchor house is its own
    anchors = anchors_of(s)
    for c in founders:
        home = anchors[c.clan_id]
        nearest_cid = min(
            anchors,
            key=lambda cid: (s.distance(c.x, c.y, anchors[cid].x, anchors[cid].y), cid),
        )
        assert nearest_cid == c.clan_id

    # mixed castes share settlements — no caste-pure world
    castes_by_clan: dict[int, set[str]] = {}
    for c in founders:
        castes_by_clan.setdefault(c.clan_id, set()).add(c.caste)
    assert any(len(v) >= 2 for v in castes_by_clan.values())


def test_anchor_claims_match_nearest_house_not_round_robin():
    """Uncapped founding: clan rosters must exactly match an independent
    reconstruction of 'every founder joins its nearest house's clan', and each
    anchor wall carries its clan crest (territory/totem anchor on that house)."""
    s = Simulation(Config(seed=31))
    houses = houses_of(s)

    expected = roster_by_house(s)  # house id -> founder ids
    actual: dict[int, set[int]] = {}
    for h in houses:
        if h.clan_id:
            actual.setdefault(h.clan_id, set()).update(expected.get(h.id, set()))
    real_roster: dict[int, set[int]] = {}
    for c in s.world.creatures():
        real_roster.setdefault(c.clan_id, set()).add(c.id)
    assert actual == real_roster

    anchors = anchors_of(s)
    assert all(h.clan_color == s.clans[h.clan_id]["color"] for h in anchors.values())


def test_max_clans_pins_spatial_cluster_count():
    s = Simulation(Config(seed=9, max_clans=3))
    founders = s.world.creatures()
    founding_clans = {c.clan_id for c in founders}
    assert founding_clans == {1, 2, 3}  # exactly N clans, ids 1..N
    # every clan settled at a distinct anchor house
    anchors = anchors_of(s)
    assert set(founding_clans) <= set(anchors)


def test_max_clans_one_unites_founders_in_single_clan():
    s = Simulation(Config(seed=11, max_clans=1))
    founders = s.world.creatures()
    assert {c.clan_id for c in founders} == {1}
    leader_id = s.clans[1]["leader_id"]
    assert leader_id in {c.id for c in founders}


def test_kcenter_clusters_are_spatially_contiguous():
    """max_clans=N: clusters must equal the greedy k-centre over the founders
    (first centre nearest the world's heart, then farthest-from-chosen), and
    greedy anchor matching must never take a house from a strictly nearer
    claimant — contiguity without round-robin."""
    seed, n = 5, 3

    def reconstruct(s: Simulation) -> list[set[int]]:
        w = s.world
        founders = sorted(s.world.creatures(), key=lambda c: c.id)
        cx, cy = s.config.width / 2, s.config.height / 2
        centres = [min(founders, key=lambda c: (w.distance(c.x, c.y, cx, cy), c.id))]
        while len(centres) < n:
            rest = [c for c in founders if all(c.id != ct.id for ct in centres)]
            nxt = max(
                rest,
                key=lambda c: (min(w.distance(c.x, c.y, ct.x, ct.y) for ct in centres), -c.id),
            )
            centres.append(nxt)
        groups: list[set[int]] = [set() for _ in centres]
        for c in founders:
            best_i, best_d = 0, float("inf")
            for i, ct in enumerate(centres):
                d = w.distance(c.x, c.y, ct.x, ct.y)
                if d < best_d:
                    best_i, best_d = i, d
            groups[best_i].add(c.id)
        return [g for g in groups if g]

    s = Simulation(Config(seed=seed, max_clans=n))
    actual: list[set[int]] = []
    for cid in sorted({c.clan_id for c in s.world.creatures()}):
        actual.append({c.id for c in s.world.creatures() if c.clan_id == cid})
    assert sorted(actual) == sorted(reconstruct(s))

    # fairness of greedy matching: if a rival's anchor is nearer this clan's
    # centroid than its own, that rival must be at least as close to it
    anchors = anchors_of(s)
    centroids = {
        cid: (
            sum(m.x for m in members) / len(members),
            sum(m.y for m in members) / len(members),
        )
        for cid in anchors
        for members in [[c for c in s.world.creatures() if c.clan_id == cid]]
        if members
    }
    for cid, (ax, ay) in centroids.items():
        d_own = s.distance(ax, ay, anchors[cid].x, anchors[cid].y)
        for other_cid, other in anchors.items():
            if other_cid == cid:
                continue
            d_alt = s.distance(ax, ay, other.x, other.y)
            if d_alt < d_own:
                ox, oy = centroids[other_cid]
                assert s.distance(ox, oy, other.x, other.y) <= d_alt + 1e-6


def test_founding_is_deterministic_given_seed():
    def build(seed: int) -> dict:
        s = Simulation(Config(seed=seed))
        return {
            "members": sorted((c.id, c.clan_id) for c in s.world.creatures()),
            "clans": {
                cid: (info["name"], info["totem"], info["leader_id"])
                for cid, info in s.clans.items()
            },
            "claims": sorted(
                (e.id, e.clan_id)
                for e in s.world.entities.values()
                if isinstance(e, House)
            ),
        }

    assert build(4242) == build(4242)
    assert build(7) != build(8)  # different seeds, different societies


def test_leader_is_founder_nearest_the_settlement_centre():
    """Founder/leader = the founding creature nearest the house centre; a
    founder leads at most one clan (settlements beyond the founder count get
    leader None). Mirrors the id-order walk used at world creation."""
    s = Simulation(Config(seed=21))  # uncapped: one clan per house
    pos = {c.id: (c.x, c.y) for c in s.world.creatures()}
    by_house = roster_by_house(s)
    taken: set[int] = set()
    for h in sorted(houses_of(s), key=lambda hh: hh.id):
        members = by_house.get(h.id, set())
        pool = [mid for mid in members if mid not in taken] or list(members)
        expected = (
            min(pool, key=lambda mid: (s.distance(*pos[mid], h.x, h.y), mid))
            if pool
            else None
        )
        assert s.clans[h.clan_id]["leader_id"] == expected
        if expected is not None:
            taken.add(expected)


def test_get_plots_handles_mixed_settlement_clans():
    """Regression: /api/plots crashed with AttributeError ('Creature' object has
    no attribute 'is_ruin') because the schism-plot house check matched every
    creature's clan_id via hasattr instead of filtering to House."""
    from dataclasses import replace

    s = Simulation(Config(seed=3))
    big = max(s.clans, key=lambda cid: sum(1 for c in s.world.creatures() if c.clan_id == cid))
    for c in s.world.creatures():  # pack everyone into one settlement clan
        c.clan_id = big
    s.config = replace(s.config, schism_enabled=True, schism_min_pop=2)

    plots = s.get_plots()
    assert isinstance(plots, list)  # did not raise

    client = TestClient(app)
    r = client.get("/api/plots")
    assert r.status_code == 200
