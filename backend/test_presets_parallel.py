import concurrent.futures
import dataclasses
import time
from app.simulation import Simulation
from app.config import Config

PRESETS_TO_RUN = {
    'balance': {
        'adult_age': 240.0,
        'reproduction_cooldown': 260,
        'birth_rate': 0.075,
        'birth_energy_cost': 16.0,
        'mate_energy_min': 28.0,
        'boom_ramp_days': 1.2,
        'boom_birth_floor': 0.40,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'winter_food_mult': 0.65,
        'safeguard_max_miracles': 1,
    },
    'sustainable': {
        'adult_age': 220.0,
        'reproduction_cooldown': 240,
        'birth_rate': 0.080,
        'birth_energy_cost': 15.0,
        'mate_energy_min': 26.0,
        'boom_ramp_days': 1.0,
        'boom_birth_floor': 0.45,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'winter_food_mult': 0.70,
        'damping_steepness': 7.0,
        'crowding_stress_mult': 0.25,
        'safeguard_max_miracles': 1,
    },
    'theocracy': {
        'adult_age': 250.0,
        'reproduction_cooldown': 280,
        'birth_rate': 0.070,
        'boom_ramp_days': 1.5,
        'boom_birth_floor': 0.35,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'morph_lambda_override': 1.0,
        'damping_steepness': 4.0,
        'winter_food_mult': 0.65,
        'safeguard_max_miracles': 1,
    },
    'chaos': {
        'adult_age': 180.0,
        'reproduction_cooldown': 200,
        'birth_rate': 0.095,
        'boom_ramp_days': 0.8,
        'boom_birth_floor': 0.60,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'annealing_start_generation': 0,
        'annealing_decay_generations': 10,
        'topological_mutation_rate': 0.05,
        'damping_steepness': 10.0,
        'winter_food_mult': 0.60,
        'safeguard_max_miracles': 1,
    },
    'boom': {
        'adult_age': 150.0,
        'reproduction_cooldown': 180,
        'birth_rate': 0.120,
        'boom_ramp_days': 0.5,
        'boom_birth_floor': 0.70,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'carrying_capacity': 600,
        'max_population': 900,
        'damping_steepness': 3.0,
        'winter_food_mult': 0.75,
        'safeguard_max_miracles': 1,
    },
    'warlords': {
        'adult_age': 200.0,
        'reproduction_cooldown': 220,
        'birth_rate': 0.085,
        'boom_ramp_days': 1.0,
        'boom_birth_floor': 0.45,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'attack_damage': 35.0,
        'winter_food_mult': 0.60,
        'safeguard_max_miracles': 1,
    },
    'extinction': {
        'adult_age': 450.0,
        'reproduction_cooldown': 400,
        'birth_rate': 0.040,
        'boom_ramp_days': 2.0,
        'boom_birth_floor': 0.20,
        'boom_energy_mult': 1.0,
        'boom_cooldown_mult': 1.0,
        'initial_season_offset': 0,
        'winter_food_mult': 0.35,
        'disease_outbreak_rate': 0.003,
        'safeguard_max_miracles': 1,
    }
}

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
        results = list(executor.map(simulate_preset, PRESETS_TO_RUN.items()))

    dur = time.time() - t0
    print(f'\n=== ALL 7 PRESETS FINISHED IN {dur:.1f}s ===\n', flush=True)
    for name, extinct_day, pop, min_pop, max_pop, miracles, trace in results:
        status = f'EXTINCT at Day {extinct_day}' if extinct_day else f'SURVIVED 20 days (pop={pop:3d}, min={min_pop:3d}, max={max_pop:3d}, miracles={miracles})'
        print(f'Preset [{name:12s}]: {status}', flush=True)
        samples = [f'D{d}:{p}c({f}F)' for d, p, f in trace if d in (1, 3, 5, 8, 12, 16, 20)]
        print('   Trace -> ' + ' | '.join(samples) + '\n', flush=True)
