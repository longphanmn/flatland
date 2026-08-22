"""World and simulation configuration."""

import os
from dataclasses import dataclass


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    return cast(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Config:
    # World geometry (grid units) — 200x200 = 4x the original 100x100 area
    width: float = 200.0
    height: float = 200.0
    boundary: str = "wrap"  # "wrap" | "clamp"

    # Simulation
    seed: int = 42
    tick_rate: float = 10.0  # ticks per second

    # Initial population (Flatland castes).
    # -1 => auto-scale from map area × density with ±spawn_variance jitter;
    # any value >= 0 pins that group explicitly (used by tests/scenarios).
    num_triangles: int = -1  # soldiers/workmen (isosceles triangles)
    num_squares: int = -1  # gentlemen
    num_pentagons: int = -1  # professionals
    num_hexagons: int = -1  # nobility
    num_priests: int = -1  # near-circles (priesthood)
    num_women: int = -1  # line segments
    num_houses: int = -1

    # World generation densities (per grid unit²) and spawn jitter.
    creature_density: float = 0.0005  # ~20 creatures on a 200×200 map
    house_density: float = 0.00015  # ~6 houses
    spawn_variance: float = 0.25  # ±25% around the density target

    food_count: int = 70  # was 48 — 70 sustains 30d with §O variants + territory/totems (tested 30d alive 20)
    # Plants & nutrient cycle (§H) + biodiversity (§O)
    plant_growth_rate: float = 0.05  # was 0.04 — a bit faster for winter
    plant_spread_rate: float = 0.006  # was 0.005
    nutrient_cycle_rate: float = 0.65  # was 0.6
    plant_variants_enabled: bool = True
    poison_rate: float = 0.01  # was 0.03 — 1% keeps 30d alive
    beast_ratio: float = 0.0
    diet_strictness: float = 0.0

    # Territory & clan depth (§P)
    territory_enabled: bool = True  # §P: clans claim zone around house, trespass sours relations
    territory_radius: float = 14.0  # radius of clan territory circle
    trespass_decay: float = 1.0  # relation points lost per tick per trespasser inside rival territory (probabilistic if <1)

    # Totem & clan depth (§P)
    totems_enabled: bool = True  # §P: each clan bears a totem (Wolf/Tree/Shield/Eye) with subtle buff
    succession_enabled: bool = True  # §P: leader succession on death emits succession event

    # Corpses & scavenging
    corpses_enabled: bool = True
    corpse_ttl: int = 600  # ticks before a corpse decays away
    corpse_energy: float = 25.0  # energy a fresh corpse holds

    # Behaviour tuning
    perceive_radius: float = 20.0  # was 18 — fog/night + variants (tested 20)
    eat_radius: float = 1.4
    energy_max: float = 100.0
    energy_start: float = 85.0
    energy_decay_per_tick: float = 0.025  # was 0.05 — 0.025 sustains 30d (tested)
    energy_from_food: float = 32.0
    wander_turn: float = 0.35  # max heading change (rad) when wandering
    steer_turn: float = 0.45  # max heading change when steering to food

    # Life / hunger
    hungry_ratio: float = 0.35  # energy/max at or below -> hungry
    starving_ratio: float = 0.15  # energy/max at or below -> starving
    hungry_perceive_mult: float = 1.3  # hungry creatures notice food farther away
    desperate_perceive_mult: float = 1.6  # starving: even farther
    desperate_speed_mult: float = 1.35  # starving: move faster
    lifespan_mult: float = 1.0  # god's law: scale every caste's natural lifespan

    # Reproduction & inheritance (Nature's Law) — tuned for 30-day survival
    birth_enabled: bool = True
    adult_age: float = 200.0  # ticks before a creature may mate (was 600)
    mate_radius: float = 10.0  # max distance between parents (was 3.0)
    mate_energy_min: float = 30.0  # both parents must hold this much energy (was 50)
    birth_rate: float = 0.35  # chance per eligible pair per tick (× fertility) (was 0.15)
    sex_ratio: float = 0.5  # probability a child is a son
    mutation_rate: float = 0.05  # chance a son's side count deviates ±1
    max_sides: int = 24  # sons stop gaining sides here (= Circle)
    birth_energy_cost: float = 20.0  # each parent pays (was 25)
    reproduction_cooldown: int = 200  # ticks both parents wait after a birth (was 300)
    carrying_capacity: int = 80  # soft cap: fertility fades above it (was 60)
    max_population: int = 140  # hard cap: no births beyond it (was 120)
    euthanasia_threshold: float = 0.7  # irregularity at/below -> demotion, above -> consumed

    # Health & disease
    disease_enabled: bool = False
    disease_outbreak_rate: float = 0.0005  # chance/tick a new outbreak begins
    disease_rate: float = 0.08  # spread chance per healthy neighbour per tick
    disease_radius: float = 3.0  # contagion range
    disease_energy_drain: float = 0.15  # extra energy loss while infected
    recovery_rate: float = 0.01  # chance/tick an infected creature recovers
    disease_lethality: float = 0.5  # scales how fast infection drains health

    # Environment: day/night, seasons, weather
    day_length: int = 1200  # ticks per day cycle
    season_length: int = 2400  # ticks per season; four seasons per year
    night_sight_mult: float = 0.6  # sight scale during the night
    weather_enabled: bool = True
    weather_change_rate: float = 0.002  # chance/tick the weather turns
    fog_sight_mult: float = 0.6  # sight scale in fog
    rain_speed_mult: float = 0.85  # movement scale in rain/storm
    storm_wander_bonus: float = 0.35  # extra heading chaos in storms

    # Night rest
    sleep_enabled: bool = True  # creatures shelter in houses after dark
    sleep_energy_mult: float = 0.5  # energy decay while asleep

    # Shelter — tuned for sustainability (exposure was 0.3, now 0.03)
    shelter_enabled: bool = True  # houses are scarce, contested and life-saving
    exposure_drain: float = 0.03  # extra energy/tick outdoors in rain/storm or at night (was 0.3)
    house_capacity: int = 8  # beds per house per tick; overflow sleeps outside (was 4)
    house_claim_enabled: bool = True  # clans claim houses as settlements
    rest_recovery_mult: float = 2.0  # indoor sleeping health regen multiplier
    house_decay_ticks: int = 2400  # abandoned house stands this many ticks before crumbling to ruin

    # Terrain (-1 => auto-scale from area)
    fertile_patches: int = -1  # green grounds where food prefers to grow
    rock_count: int = -1  # solid stone circles that block movement
    fertile_food_bias: float = 0.7  # fraction of food spawned on fertile ground

    # Society — interaction & clan relations
    cohesion_weight: float = 0.0  # pull toward same-clan flock centre
    alignment_weight: float = 0.0  # match neighbours' heading
    separation_weight: float = 0.0  # personal-space push from any neighbour
    flock_radius: float = 6.0  # interaction perception range
    relation_drift_rate: float = 1.0  # points/tick clan scores relax toward 0
    alliance_threshold: int = 50  # score at/above which two clans are allies
    rivalry_threshold: int = -50  # score at/below which two clans are rivals

    # Predation (§I) — Carnivore caste
    predation_enabled: bool = False  # predators hunt prey
    predator_ratio: float = 0.08  # fraction of spawn that are predators
    hunt_radius: float = 8.0  # predator sight for prey
    bite_damage: float = 100.0  # damage on bite (100 = instant kill)
    bite_cooldown: int = 10  # ticks between bites
    energy_from_prey: float = 40.0  # energy predator gains per kill
    fear_radius: float = 10.0  # prey flee when predator within this range

    # Clan war (§I) — rival clans fight on contact
    war_enabled: bool = False  # rival-clan combat enabled
    attack_radius: float = 1.8  # distance for clan war engagement
    attack_damage: float = 100.0  # damage per attack (100 = lethal)

    # Houses
    house_min_size: float = 6.0
    house_max_size: float = 10.0
    door_clearance: float = 1.5  # door width = clearance * largest creature diameter

    # Chronicle
    history_max: int = 200  # death events kept in the chronicle

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            width=_env("FLATWORLD_WIDTH", float, 200.0),
            height=_env("FLATWORLD_HEIGHT", float, 200.0),
            boundary=_env("FLATWORLD_BOUNDARY", str, "wrap"),
            seed=_env("FLATWORLD_SEED", int, 42),
            tick_rate=_env("FLATWORLD_TICK_RATE", float, 10.0),
        )

    @property
    def tick_interval(self) -> float:
        return 1.0 / self.tick_rate if self.tick_rate > 0 else 0.1
