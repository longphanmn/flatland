#!/usr/bin/env python3
"""cProfile bench: top-40 by tottime at N~=1000 (AZ Phase 0)."""
import cProfile
import pstats
import time
from app.config import Config
from app.simulation import Simulation

def main(n: int = 1000, ticks: int = 60):
    cfg = Config(seed=42, width=400, height=300, carrying_capacity=800, max_population=1200, food_count=300)
    sim = Simulation(cfg)
    # warm up 5 ticks to build houses/clans
    for _ in range(5):
        sim.step()
    # ensure ~1000 creatures: bump via config or seed loop
    print(f"starting entities={len(sim.world.entities)} creatures={len(sim._cached_creatures)}")
    pr = cProfile.Profile()
    pr.enable()
    t0 = time.monotonic()
    for _ in range(ticks):
        sim.step()
    dur = (time.monotonic() - t0) * 1000 / ticks
    pr.disable()
    print(f"\n[bench_tick] {ticks} ticks avg {dur:.2f} ms/tick ({1000/dur:.1f} FPS) entities={len(sim.world.entities)}")
    ps = pstats.Stats(pr).sort_stats("tottime")
    ps.print_stats(40)
    # also cumtime
    print("\n--- cumtime top 20 ---")
    pstats.Stats(pr).sort_stats("cumtime").print_stats(20)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    main(ticks=args.ticks)
