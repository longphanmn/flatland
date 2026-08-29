#!/usr/bin/env python3
"""tracemalloc growth snapshot at ticks 500/1500/3000 (AZ Phase 0)."""
import tracemalloc
from app.config import Config
from app.simulation import Simulation

def snapshot_top(limit=20):
    snap = tracemalloc.take_snapshot()
    stats = snap.statistics("lineno")
    print(f"\n[tracemalloc] top {limit}:")
    for i, s in enumerate(stats[:limit], 1):
        print(f"{i:2d}. {s}")

def main():
    tracemalloc.start()
    cfg = Config(seed=42)
    sim = Simulation(cfg)
    checkpoints = {500, 1500, 3000}
    max_tick = 3000
    for t in range(1, max_tick + 1):
        sim.step()
        if t in checkpoints:
            import psutil, os
            try:
                rss = psutil.Process().memory_info().rss / 1024 / 1024
            except Exception:
                import resource
                rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            print(f"\n=== tick {t} === entities={len(sim.world.entities)} creatures={len(sim._cached_creatures)} RSS={rss:.1f} MB pending=?")
            snapshot_top(20)
    tracemalloc.stop()

if __name__ == "__main__":
    main()
