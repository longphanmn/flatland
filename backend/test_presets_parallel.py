import concurrent.futures
import dataclasses
import time
from app.simulation import Simulation
from app.config import Config
from app.main import PRESETS

def simulate_preset(item):
    name, overrides = item
    cfg = Config.from_env()
    valid_fields = {f.name for f in dataclasses.fields(Config)}
    valid_overrides = {k: v for k, v in overrides.items() if k in valid_fields}
    cfg = dataclasses.replace(cfg, **valid_overrides)
    sim = Simulation(cfg)
    
    extinct_day = None
    min_pop, max_pop = 999, 0
    pop_trace = []
    
    for day in range(1, 21):
        for tick in range(cfg.day_length):
            sim.step()
        pop = sum(1 for e in sim.world.entities.values() if getattr(e, 'kind', None) == 'creature')
        females = sum(1 for e in sim.world.entities.values() if getattr(e, 'kind', None) == 'creature' and getattr(e, 'shape', None) == 'line')
        pop_trace.append((day, pop, females))
        if pop < min_pop: min_pop = pop
        if pop > max_pop: max_pop = pop
        if pop == 0:
            extinct_day = day
            break
            
    miracles = sim._safeguard.miracles if sim._safeguard else 0
    return name, extinct_day, pop, min_pop, max_pop, miracles, pop_trace

if __name__ == '__main__':
    print('Starting parallel simulation of all 7 presets across 7 CPU cores...', flush=True)
    t0 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=7) as executor:
        results = list(executor.map(simulate_preset, PRESETS.items()))

    dur = time.time() - t0
    print(f'\n=== ALL 7 PRESETS FINISHED IN {dur:.1f}s ===\n', flush=True)
    for name, extinct_day, pop, min_pop, max_pop, miracles, trace in results:
        status = f'EXTINCT at Day {extinct_day}' if extinct_day else f'SURVIVED 20 days (pop={pop:3d}, min={min_pop:3d}, max={max_pop:3d}, miracles={miracles})'
        print(f'Preset [{name:12s}]: {status}', flush=True)
        samples = [f'D{d}:{p}c({f}F)' for d, p, f in trace if d in (1, 3, 5, 8, 12, 16, 20)]
        print('   Trace -> ' + ' | '.join(samples) + '\n', flush=True)
