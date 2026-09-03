"""BJ-6 Production tick-budget regression: 3 -> 10+ TPS guardrail.

Runs 100 ticks under production-sized founding conditions (170 creatures,
380 food, 88 houses, sustainable-preset laws) and asserts mean tick duration
<= 45ms on dev hardware (equivalent to <= 85ms on low-power Intel N150 /
4-core servers), guaranteeing >= 11.5 TPS headroom for the 10.0 TPS target.
Also covers the per-subsystem timing telemetry in /healthz and
/api/perf/telemetry.
"""

import time

from fastapi.testclient import TestClient

from app.analytics import AnalyticsEngine
from app.config import Config
from app.main import RT, app, start_world
from app.simulation import Simulation


def sustainable_production_cfg(**kw) -> Config:
    try:
        from app.main import PRESETS  # type: ignore

        preset = dict(PRESETS["sustainable"])
    except Exception:
        preset = {}
    fields = Config.__dataclass_fields__
    base = {k: v for k, v in preset.items() if k in fields}
    base.update(
        dict(
            seed=42,
            tick_rate=10.0,
            # BJ-6 founding: 170 creatures / 380 food / 88 houses.
            num_triangles=60,
            num_squares=40,
            num_pentagons=20,
            num_hexagons=10,
            num_priests=10,
            num_women=30,
            num_houses=88,
            food_count=380,
        )
    )
    base.update(kw)
    return Config(**base)


def test_production_tick_budget():
    """Mean tick <= 45ms over 100 production-sized ticks (BJ-6)."""
    sim = Simulation(sustainable_production_cfg())
    pop0 = len(sim.world.creatures())
    assert pop0 == 170, f"expected 170 founders, got {pop0}"
    assert len(sim._cached_foods) == 380 or len([e for e in sim.world.entities.values() if e.kind == "food"]) == 380
    houses = [e for e in sim.world.entities.values() if e.kind == "house"]
    assert len(houses) == 88, f"expected 88 houses, got {len(houses)}"

    durs: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        sim.step()
        durs.append((time.perf_counter() - t0) * 1000.0)

    assert sim.tick == 100
    assert len(sim.world.creatures()) > 0
    mean_ms = sum(durs) / len(durs)
    print(
        f"\n[tick-budget] mean={mean_ms:.2f}ms max={max(durs):.2f}ms "
        f"pop={len(sim.world.creatures())} phases={sim._phase_ms}"
    )
    assert mean_ms <= 45.0, f"tick budget blown: mean {mean_ms:.2f}ms > 45ms (N150 equiv >85ms)"
    # Per-subsystem timing must be recorded for every phase.
    for phase in ("cache_full", "creatures", "post_disease_war", "society", "soa_nn"):
        assert phase in sim._phase_ms, f"missing phase timing: {phase}"
    avgs = sim.phase_averages()
    assert set(avgs) >= {"creatures", "society"}


def test_telemetry_throttle_2hz_production(monkeypatch):
    """BJ-3: production samples telemetry at 2 Hz (every 5th tick at 10 TPS)."""
    import app.simulation.core as core_mod

    sim = Simulation(Config(seed=7, num_triangles=4, num_squares=4, food_count=10))
    sim._analytics = AnalyticsEngine()
    monkeypatch.setattr(core_mod, "_IS_TEST", False)
    for _ in range(10):
        sim.step()
    # ticks 5 and 10 sampled at tick_rate=10 -> 2 Hz
    assert list(sim._analytics.ring.ticks) == [5, 10]

    sim2 = Simulation(Config(seed=7, num_triangles=4, num_squares=4, food_count=10))
    sim2._analytics = AnalyticsEngine()
    monkeypatch.setattr(core_mod, "_IS_TEST", True)
    for _ in range(10):
        sim2.step()
    assert len(sim2._analytics.ring.ticks) == 10


def test_healthz_reports_subsystem_timing():
    RT.config = Config.from_env()
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    RT.sim.step()
    start_world()
    c = TestClient(app)
    r = c.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert "subsystems_ms" in body
    assert "subsystems_avg_ms" in body
    assert "tick_budget" in body
    assert body["tick_budget"]["dev_ms"] == 45.0
    assert body["tick_budget"]["n150_ms"] == 85.0
    assert "creatures" in body["subsystems_ms"]


def test_perf_telemetry_reports_subsystems():
    RT.config = Config.from_env()
    RT.paused = False
    RT.speed = RT.config.tick_rate
    RT.sim = Simulation(RT.config)
    RT.sim.step()
    start_world()
    c = TestClient(app)
    c.headers["X-God-Key"] = "test-key"
    r = c.get("/api/perf/telemetry")
    assert r.status_code == 200
    body = r.json()
    assert "subsystems_ms" in body
    assert "subsystems_avg_ms" in body
    assert "tick_budget" in body
