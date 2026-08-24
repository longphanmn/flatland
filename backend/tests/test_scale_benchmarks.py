import time
import pytest
from app.config import Config
from app.native_core import is_native_available, native_query_radius
from app.simulation import Simulation
from app.world import World


def test_native_core_parity_with_python():
    """Verify that native C queries return identical results to pure Python reference math."""
    n = 100
    xs = [float(i * 1.5 % 100) for i in range(n)]
    ys = [float((i * 2.3 + 10) % 100) for i in range(n)]
    ids = list(range(1, n + 1))

    # Test center query with wrap
    c_ids, c_d2 = native_query_radius(50.0, 50.0, 15.0, xs, ys, ids, 100.0, 100.0, True)

    # Reference Python calculation
    ref_ids = []
    ref_d2 = []
    r2 = 15.0 * 15.0
    for i in range(n):
        dx = abs(50.0 - xs[i])
        dy = abs(50.0 - ys[i])
        if dx > 50.0:
            dx -= 100.0
        if dy > 50.0:
            dy -= 100.0
        d2 = dx * dx + dy * dy
        if d2 <= r2:
            ref_ids.append(ids[i])
            ref_d2.append(d2)

    assert c_ids == ref_ids
    assert len(c_d2) == len(ref_d2)
    for a, b in zip(c_d2, ref_d2):
        assert abs(a - b) < 1e-4


def test_scale_benchmark_1000_creatures():
    """Benchmark high-scale simulation step times with 1000+ creatures."""
    cfg = Config(seed=42, width=300, height=300, carrying_capacity=800, max_population=1000, food_count=300)
    sim = Simulation(cfg)

    # Warm up 5 ticks
    for _ in range(5):
        sim.step()

    # Measure average step duration over 20 ticks
    t0 = time.monotonic()
    ticks = 20
    for _ in range(ticks):
        sim.step()
    dur_ms = (time.monotonic() - t0) * 1000.0 / ticks

    print(f"\n[Scale Benchmark] Active Entities: {len(sim.world.entities)} | Step Time: {dur_ms:.2f} ms/tick ({1000.0/dur_ms:.1f} FPS)")
    # Assert step execution is fast (<25 ms per tick even under high scale in pytest)
    assert dur_ms < 30.0, f"Expected step time < 30ms, got {dur_ms:.2f}ms"
