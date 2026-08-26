#!/usr/bin/env python3
"""Tick stats and CPU cores usage monitor.

Polls simulation /healthz and /proc/stat every interval for the specified duration,
computes per-core utilization and tick latency distribution, and prints
a detailed performance telemetry report.
"""

import argparse
import json
import time
import urllib.request


def read_proc_stat() -> list[tuple[int, int]]:
    """Read per-core (idle, total) jiffies from /proc/stat."""
    cores = []
    try:
        with open("/proc/stat", "r") as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                name = parts[0]
                if name.startswith("cpu") and name != "cpu":
                    times = [int(x) for x in parts[1:]]
                    idle = times[3] + (times[4] if len(times) > 4 else 0)
                    total = sum(times)
                    cores.append((idle, total))
    except Exception:
        pass
    return cores


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Flatland simulation tick & CPU stats")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of Flatland backend")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default 60s)")
    parser.add_argument("--interval", type=float, default=2.0, help="Sampling interval in seconds (default 2s)")
    args = parser.parse_args()

    health_url = f"{args.url.rstrip('/')}/healthz"
    print(f"=== Flatland Performance Telemetry Monitor ===")
    print(f"Target: {health_url}")
    print(f"Duration: {args.duration}s (interval: {args.interval}s, total samples: {int(args.duration / args.interval)})")
    print("-" * 80)

    samples = []
    prev_stat = read_proc_stat()
    start_time = time.time()

    while time.time() - start_time < args.duration:
        t0 = time.time()
        health_data = {}
        try:
            req = urllib.request.urlopen(health_url, timeout=2.0)
            health_data = json.loads(req.read().decode("utf-8"))
        except Exception as exc:
            health_data = {"error": str(exc)}

        curr_stat = read_proc_stat()
        core_pcts = []
        if prev_stat and curr_stat and len(prev_stat) == len(curr_stat):
            for (p_idle, p_tot), (c_idle, c_tot) in zip(prev_stat, curr_stat):
                d_idle = c_idle - p_idle
                d_tot = c_tot - p_tot
                if d_tot > 0:
                    pct = 100.0 * (1.0 - (d_idle / d_tot))
                    core_pcts.append(pct)
                else:
                    core_pcts.append(0.0)
        prev_stat = curr_stat

        elapsed = time.time() - start_time
        tick = health_data.get("tick", 0)
        tps = health_data.get("actual_tps", 0.0)
        avg_ms = health_data.get("avg_tick_ms", 0.0)
        max_ms = health_data.get("max_tick_ms", 0.0)
        pop = health_data.get("creatures", 0)
        overrun = health_data.get("overrun", False)

        samples.append({
            "elapsed": elapsed,
            "tick": tick,
            "tps": tps,
            "avg_ms": avg_ms,
            "max_ms": max_ms,
            "pop": pop,
            "overrun": overrun,
            "core_pcts": core_pcts,
        })

        cores_str = " | ".join(f"C{i}:{p:3.0f}%" for i, p in enumerate(core_pcts)) if core_pcts else "N/A"
        overrun_str = " [OVERRUN]" if overrun or tps < 8.0 else ""
        print(f"[{elapsed:5.1f}s] tick={tick:<7} TPS={tps:5.2f} | avg={avg_ms:5.1f}ms max={max_ms:5.1f}ms | pop={pop:<4}{overrun_str} | {cores_str}")

        sleep_dur = max(0.1, args.interval - (time.time() - t0))
        time.sleep(sleep_dur)

    print("-" * 80)
    print("=== SUMMARY REPORT ===")
    valid_samples = [s for s in samples if s["tps"] > 0]
    if not valid_samples:
        print("No valid samples recorded.")
        return

    all_tps = [s["tps"] for s in valid_samples]
    all_avg_ms = [s["avg_ms"] for s in valid_samples]
    all_pop = [s["pop"] for s in valid_samples]
    overrun_count = sum(1 for s in valid_samples if s["overrun"] or s["tps"] < 8.0)

    print(f"Total Samples: {len(valid_samples)}")
    print(f"TPS: min={min(all_tps):.2f}, avg={sum(all_tps)/len(all_tps):.2f}, max={max(all_tps):.2f}")
    print(f"Tick Latency (ms): min={min(all_avg_ms):.1f}ms, avg={sum(all_avg_ms)/len(all_avg_ms):.1f}ms, max={max(all_avg_ms):.1f}ms")
    print(f"Creature Population: min={min(all_pop)}, avg={sum(all_pop)/len(all_pop):.0f}, max={max(all_pop)}")
    print(f"Overrun / Sub-8 TPS Samples: {overrun_count} / {len(valid_samples)} ({100.0*overrun_count/len(valid_samples):.1f}%)")

    # CPU core averages
    if any(s["core_pcts"] for s in valid_samples):
        num_cores = len(valid_samples[0]["core_pcts"])
        core_sums = [0.0] * num_cores
        for s in valid_samples:
            for i, p in enumerate(s["core_pcts"]):
                core_sums[i] += p
        core_avgs = [s / len(valid_samples) for s in core_sums]
        print("Average CPU Utilization by Core:")
        for i, avg_p in enumerate(core_avgs):
            bar = "#" * int(avg_p // 5) + "-" * (20 - int(avg_p // 5))
            print(f"  Core {i}: [{bar}] {avg_p:5.1f}%")


if __name__ == "__main__":
    main()
