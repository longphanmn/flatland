"""World and simulation configuration."""

import os
from dataclasses import dataclass


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    return cast(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class Config:
    # World geometry (grid units) — 400x300 = 3x the original 200x200 area
    width: float = 400.0
    height: float = 300.0
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
    creature_density: float = 0.0013  # ~156 creatures on the 400×300 map — at least 50 as requested
    house_density: float = 0.0002  # ~24 houses for 150+ pop
    spawn_variance: float = 0.25  # ±25% around the density target

    food_count: int = 450  # generous food for a thriving multi-generational civilization (sustainable default)
    # Plants & nutrient cycle (§H) + biodiversity (§O)
    plant_growth_rate: float = 0.06
    plant_spread_rate: float = 0.008
    nutrient_cycle_rate: float = 0.65
    plant_variants_enabled: bool = True
    poison_rate: float = 0.0  # clean crops in sustainable baseline
    beast_ratio: float = 0.0
    diet_strictness: float = 0.0
    winter_food_mult: float = 0.75  # gentle winter bounty mult

    # Territory & clan depth (§P)
    territory_enabled: bool = True  # §P: clans claim zone around house, trespass sours relations
    territory_radius: float = 14.0  # radius of clan territory circle
    trespass_decay: float = 0.0  # calm relations by default

    # Clan founding (§V) — settlements define clans, castes mix inside them
    max_clans: int = -1  # -1 = one clan per house; N ≥ 1 clusters founders into N spatial clans

    # Totem & clan depth (§P)
    totems_enabled: bool = True  # §P: each clan bears a totem (Wolf/Tree/Shield/Eye) with subtle buff
    succession_enabled: bool = True  # §P: leader succession on death emits succession event

    # Schism — WorldBox rebellion (§S P1) — enabled but rare
    schism_enabled: bool = True  # rebellion enabled by default
    schism_threshold: float = 0.55  # fraction unhappy to trigger
    schism_min_pop: int = 7  # minimum clan pop

    # Ages — super-seasons (§S)
    age_enabled: bool = True  # long era bending world: Ice/Chaos/Plague/Golden
    age_length: int = 12000  # ticks per age (5 seasons)

    # Culture & Traits (§S)
    culture_enabled: bool = False  # clan culture spreads/splits, grants bonus
    trait_mutation_rate: float = 0.02  # chance mutation adds heritable behaviour trait
    culture_spread_rate: float = 0.005  # per tick ally culture spread

    # Wildfire & Disasters (§S)
    wildfire_enabled: bool = False  # fire ignites via storm lightning, spreads
    fire_rate: float = 0.0005  # chance/tick to ignite random plant
    fire_spread_rate: float = 0.08  # spread to neighboring plants
    disaster_enabled: bool = False  # meteor/flood stochastic
    disaster_rate: float = 0.0003  # chance/tick for disaster

    # Communication & Care (§Q) — enabled by default
    communication_enabled: bool = True  # food + alarm calls, clan recruitment — enabled
    signal_radius: float = 12.0  # heard within this range
    food_call_rate: float = 0.08  # well-fed finds food → calls with this chance/tick
    alarm_call_rate: float = 0.12  # sees predator → alarm call chance/tick

    # Communication II — knowledge, teaching & mobbing (§X)
    knowledge_enabled: bool = True  # creatures learn/remember/share facts
    knowledge_ttl: int = 600  # ticks a fact stays in memory before it fades
    knowledge_share_rate: float = 0.05  # chance/tick to broadcast freshest fact to clan
    help_call_enabled: bool = True  # attacked creatures call their clan to mob the attacker
    help_radius: float = 12.0  # clan-mates rally within this range; defenders soften blows
    defense_weight: float = 0.5  # damage reduction per defender mobbing the attacker

    # Corpses & scavenging
    corpses_enabled: bool = True
    corpse_ttl: int = 600  # ticks before a corpse decays away
    corpse_energy: float = 25.0  # energy a fresh corpse holds

    # Food decay (§AE) — nothing lasts forever
    food_decay_enabled: bool = True  # mature plants wither, fertilise, vanish
    food_lifespan_ticks: int = 9000  # ticks a mature plant lives (× variant mult)

    # Behaviour tuning
    perceive_radius: float = 18.0  # gentle 18.0 sustainable sight
    eat_radius: float = 1.4
    energy_max: float = 100.0
    energy_start: float = 85.0
    energy_decay_per_tick: float = 0.025  # sustainable baseline
    energy_from_food: float = 32.0
    wander_turn: float = 0.35  # max heading change (rad) when wandering
    steer_turn: float = 0.45  # max heading change when steering to food

    # Life / hunger
    hungry_ratio: float = 0.35  # energy/max at or below -> hungry
    starving_ratio: float = 0.15  # energy/max at or below -> starving
    hungry_perceive_mult: float = 1.3  # hungry creatures notice food farther away
    desperate_perceive_mult: float = 1.6  # starving: even farther
    desperate_speed_mult: float = 1.35  # starving: move faster
    food_giveup_ticks: int = 240  # ticks a meal is abandoned when blocked by rock/wall; seek elsewhere
    lifespan_mult: float = 1.0  # god's law: scale every caste's natural lifespan

    # Reproduction & inheritance (Nature's Law) — tuned for 1000-day survival & high scale
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
    carrying_capacity: int = 2200  # soft cap: fertility fades above it (sustainable default)
    max_population: int = 3000  # hard cap: no births beyond it (sustainable default)
    euthanasia_threshold: float = 0.7  # irregularity at/below -> demotion, above -> consumed

    # Health & disease — gentle background presence
    disease_enabled: bool = True
    disease_outbreak_rate: float = 0.0001  # very rare outbreak in sustainable baseline
    disease_rate: float = 0.05  # gentle spread
    disease_radius: float = 3.0  # contagion range
    disease_energy_drain: float = 0.08  # mild drain
    recovery_rate: float = 0.025  # steady recovery
    disease_lethality: float = 0.25  # non-fatal when fed

    # Environment: day/night, seasons, weather
    day_length: int = 1200  # ticks per day cycle
    season_length: int = 14400  # ticks per season; 12 days per season (48-day year)
    night_sight_mult: float = 0.6  # sight scale during the night
    weather_enabled: bool = True
    weather_change_rate: float = 0.002  # chance/tick the weather turns
    fog_sight_mult: float = 0.6  # sight scale in fog
    rain_speed_mult: float = 0.85  # movement scale in rain/storm
    storm_wander_bonus: float = 0.35  # extra heading chaos in storms

    # Weather → crops (§R)
    rain_growth_mult: float = 1.25  # rain/storm boost to plant growth
    fog_mushroom_mult: float = 1.35  # fog boost to mushroom growth
    storm_plant_damage: float = 0.02  # chance/tick storm strips growth from exposed plants

    # Weather → sickness (§R) chill / wet contagion
    weather_sickness_enabled: bool = False  # chill + wet contagion; disabled by default
    chill_rate: float = 0.04  # chill built per tick unsheltered in rain/storm/winter night
    chill_threshold: float = 12.0  # chill at which creature is sick
    chill_drain: float = 0.18  # health drain per tick when chilled
    wet_disease_mult: float = 1.5  # wet/cold catch disease faster, recover slower

    # Night rest
    sleep_enabled: bool = True  # creatures shelter in houses after dark
    sleep_energy_mult: float = 0.5  # energy decay while asleep

    # Shelter — tuned for sustainability
    shelter_enabled: bool = True  # houses are scarce, contested and life-saving
    exposure_drain: float = 0.03  # extra energy/tick outdoors in rain/storm or at night
    house_capacity: int = 16  # beds in an 8×8 hall; scales with floor area (sustainable default)
    house_claim_enabled: bool = True  # clans claim houses as settlements
    rest_recovery_mult: float = 2.0  # indoor sleeping health regen multiplier
    house_decay_ticks: int = 2400  # abandoned house stands this many ticks before crumbling to ruin

    # Terrain (-1 => auto-scale from area)
    fertile_patches: int = -1  # green grounds where food prefers to grow
    rock_count: int = -1  # solid stone circles that block movement
    fertile_food_bias: float = 0.7  # fraction of food spawned on fertile ground

    # Society — interaction & clan relations — calm society
    cohesion_weight: float = 0.0  # pull toward same-clan flock centre
    alignment_weight: float = 0.0  # match neighbours' heading
    separation_weight: float = 0.0  # personal-space push from any neighbour
    flock_radius: float = 6.0  # interaction perception range
    relation_drift_rate: float = 2.8  # fast relation relaxation
    alliance_threshold: int = 50  # score at/above which two clans are allies
    rivalry_threshold: int = -85  # rare feuds

    # Predation (§I) — Carnivore caste (gentle, sustainable)
    predation_enabled: bool = True
    predator_ratio: float = 0.03  # low predator ratio
    hunt_radius: float = 8.0  # predator sight for prey
    bite_damage: float = 40.0  # wound not instant kill
    bite_cooldown: int = 12  # ticks between bites
    energy_from_prey: float = 40.0  # energy predator gains per kill
    fear_radius: float = 10.0  # prey flee when predator within this range

    # Clan war (§I) — rival clans fight on contact — enabled but rare
    war_enabled: bool = True  # enabled by default, but rare
    attack_radius: float = 1.8  # distance for clan war engagement
    attack_damage: float = 40.0  # wound (40) not lethal, so war rarely fatal

    # Politics (§AB) — coalitions, leader agency, resources, betrayal
    coalitions_enabled: bool = True  # allied clans form defensive blocs
    coalition_threshold: int = 40  # relation score at which a clan may join
    coalition_min_size: int = 2  # smallest viable bloc (incl. founder)
    leader_decisions_enabled: bool = True  # leaders declare war/peace/tribute as plots
    resource_sharing_enabled: bool = True  # clan larder at the settlement
    larder_capacity: float = 300.0  # energy a clan store holds
    aid_rate: float = 0.05  # chance/tick a surplus ally feeds a starving ally
    tribute_enabled: bool = True  # weak clans pay a protector for peace
    betrayal_enabled: bool = True  # leaders may break alliances and strike
    defection_enabled: bool = True  # unhappy members defect to other clans

    # Desperation cannibalism (§AC) — eat the enemy & the weak
    cannibalism_enabled: bool = True  # the starving may hunt the living
    cannibalism_hunger_ratio: float = 0.15  # only below this energy fraction
    cannibalism_energy: float = 45.0  # gained per desperate kill
    eat_enemy_enabled: bool = True  # enemy-clan members are legitimate prey
    eat_kin_enabled: bool = True  # weak kin too — at a terrible price
    kin_stigma: int = 40  # relation hit between exiled band and former clan
    exile_on_kin_eat: bool = True  # kin-eater cast out, founding an outcast band

    # Houses
    house_min_size: float = 6.0
    house_max_size: float = 10.0
    door_clearance: float = 1.5  # door width = clearance * largest creature diameter
    house_gap: float = 6.0  # min clear gap between house walls — keeps alleys passable so creatures never wedge between shelters

    # Chronicle
    history_max: int = 200  # death events kept in the chronicle

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            width=_env("FLATWORLD_WIDTH", float, 400.0),
            height=_env("FLATWORLD_HEIGHT", float, 300.0),
            boundary=_env("FLATWORLD_BOUNDARY", str, "wrap"),
            seed=_env("FLATWORLD_SEED", int, 42),
            tick_rate=_env("FLATWORLD_TICK_RATE", float, 10.0),
        )

    @property
    def tick_interval(self) -> float:
        return 1.0 / self.tick_rate if self.tick_rate > 0 else 0.1

    # -1 sentinels resolve against map area so caps keep pace with density-scaled
    # population (80 carrying / 140 hard cap on the classic 200x200 baseline).
    @property
    def area_scale(self) -> float:
        return (self.width * self.height) / (200.0 * 200.0)

    @property
    def effective_carrying_capacity(self) -> int:
        if self.carrying_capacity >= 0:
            return self.carrying_capacity
        return max(2, round(80 * self.area_scale))

    @property
    def effective_max_population(self) -> int:
        if self.max_population >= 0:
            return self.max_population
        return max(2, round(140 * self.area_scale))
