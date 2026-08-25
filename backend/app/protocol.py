"""Wire protocol schemas shared with the web frontend.

Message flow:
  server -> client: {"type": "hello", ...} then {"type": "state", ...} each tick
  client -> server: {"action": "pause"|"resume"|"step"|"reset"|"set_speed", "value": ...}
"""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ControlAction(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    STEP = "step"
    RESET = "reset"
    SET_SPEED = "set_speed"


class ControlMessage(BaseModel):
    action: ControlAction
    value: Optional[float] = None


class EntityState(BaseModel):
    id: int
    kind: Literal["creature", "food", "house", "corpse"]
    x: float
    y: float
    angle: float
    shape: Optional[Literal["polygon", "line"]] = None
    sides: Optional[int] = None
    caste: Optional[str] = None
    energy: Optional[float] = None
    growth: Optional[float] = None  # plants: 0..1 maturity (renderer scales size)
    variant: Optional[Literal["grass", "grain", "berry", "medicinal_herb", "mushroom", "poisonous"]] = None
    withering: Optional[bool] = None  # §AE: mature plant past its wilt threshold
    cultivated: Optional[bool] = None  # §AM: sown crop — grows faster, feeds better
    irrigated: Optional[bool] = None  # §AM: furrow-watered crop

    size: Optional[float] = None
    status: Optional[Literal["", "hungry", "starving"]] = None
    radius: Optional[float] = None
    age: Optional[int] = None
    lifespan: Optional[float] = None
    stage: Optional[Literal["infant", "juvenile", "adult", "elder"]] = None
    irregularity: Optional[float] = None
    health: Optional[float] = None
    infected: Optional[bool] = None
    meals: Optional[int] = None
    sex: Optional[Literal["male", "female"]] = None
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    clan_id: Optional[int] = None
    clan_color: Optional[str] = None
    clan_name: Optional[str] = None
    is_predator: Optional[bool] = None
    is_herbivore: Optional[bool] = None
    sleeping: Optional[bool] = None
    indoors: Optional[bool] = None
    generation: Optional[int] = None
    born_tick: Optional[int] = None
    personal_name: Optional[str] = None
    glyph: Optional[str] = None
    hue_shift: Optional[float] = None
    scale_jitter: Optional[float] = None
    angle_jitter: Optional[float] = None
    chill: Optional[float] = None
    body_temp: Optional[float] = None  # §AQ PH-1: body temperature (°C-ish)
    torpid: Optional[bool] = None  # §AQ PH-7: cold-torpor shutdown
    trait: Optional[str] = None
    door_width: Optional[float] = None
    door_offset: Optional[float] = None
    door_side: Optional[Literal["north", "east", "south", "west"]] = None
    is_ruin: Optional[bool] = None
    abandoned_ticks: Optional[int] = None
    takeover_age: Optional[int] = None  # §AT-3: ticks since last hostile takeover
    material: Optional[Literal["straw", "wood", "stone", "clay"]] = None  # §AQ PH-1/6
    murals: Optional[int] = None  # §AN: painted chronicle inscribed on the walls
    hearth_lit: Optional[bool] = None  # §AQ PH-1: fire burns on this hearth
    hp_frac: Optional[float] = None  # §AQ PH-6: structural integrity remaining
    rubble: Optional[bool] = None  # §AQ PH-6: collapsed lot, uncleared rubble


class StateMessage(BaseModel):
    type: Literal["state"] = "state"
    tick: int
    seed: int = 0
    width: float
    height: float
    boundary: str
    population: dict[str, int] = Field(default_factory=dict)
    entities: list[EntityState] = Field(default_factory=list)
    creatures_alive: int = 0
    creatures_dead: int = 0
    dead_by_cause: dict[str, int] = Field(default_factory=dict)
    infected_count: int = 0
    time_of_day: float = 0.25
    day: int = 1
    season: Literal["spring", "summer", "autumn", "winter"] = "spring"
    weather: Literal["clear", "rain", "fog", "storm"] = "clear"
    terrain_fertile: list[dict[str, float]] = Field(default_factory=list)
    terrain_rocks: list[dict[str, float]] = Field(default_factory=list)
    relations: list[dict[str, int]] = Field(default_factory=list)
    clans: dict[str, dict[str, Any]] = Field(default_factory=dict)
    events: list["HistoryEvent"] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)
    fires: list[dict[str, Any]] = Field(default_factory=list)
    campfires: list[dict[str, Any]] = Field(default_factory=list)  # §AO field campfires
    boundary_stones: list[dict[str, Any]] = Field(default_factory=list)  # §AN
    markets: list[dict[str, Any]] = Field(default_factory=list)  # §AN trading posts
    wind: dict[str, float] = Field(default_factory=dict)  # §AQ PH-2 {angle,speed}
    rivers: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-3 channels
    bridges: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-3 planks
    dams: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-3 masonry
    elevation: dict[str, Any] = Field(default_factory=dict)  # §AQ PH-4 static height field
    lightning: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-9 bolts
    anomalies: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-10 discovered zones
    law_wave: dict[str, Any] = Field(default_factory=dict)  # §AQ PH-10 shimmer front
    age: Optional[str] = None
    age_tick: int = 0
    age_day: int = 1
    age_total_days: int = 10


class DeltaStateMessage(BaseModel):
    """Phase 1 AJ: Lightweight delta snapshot broadcasting only changed/moving entities."""
    type: Literal["delta_state"] = "delta_state"
    tick: int
    seed: int = 0
    upsert_entities: list[EntityState | dict[str, Any]] = Field(default_factory=list)
    remove_ids: list[int] = Field(default_factory=list)
    population: dict[str, int] = Field(default_factory=dict)
    creatures_alive: int = 0
    creatures_dead: int = 0
    dead_by_cause: dict[str, int] = Field(default_factory=dict)
    infected_count: int = 0
    time_of_day: float = 0.25
    day: int = 1
    season: Literal["spring", "summer", "autumn", "winter"] = "spring"
    weather: Literal["clear", "rain", "fog", "storm"] = "clear"
    relations: list[dict[str, int]] = Field(default_factory=list)
    clans: dict[str, dict[str, Any]] = Field(default_factory=dict)
    events: list["HistoryEvent"] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)
    fires: list[dict[str, Any]] = Field(default_factory=list)
    campfires: list[dict[str, Any]] = Field(default_factory=list)  # §AO field campfires
    boundary_stones: list[dict[str, Any]] = Field(default_factory=list)  # §AN
    markets: list[dict[str, Any]] = Field(default_factory=list)  # §AN trading posts
    wind: dict[str, float] = Field(default_factory=dict)  # §AQ PH-2 {angle,speed}
    rivers: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-3 channels
    bridges: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-3 planks
    dams: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-3 masonry
    elevation: dict[str, Any] = Field(default_factory=dict)  # §AQ PH-4 static height field
    lightning: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-9 bolts
    anomalies: list[dict[str, Any]] = Field(default_factory=list)  # §AQ PH-10 discovered zones
    law_wave: dict[str, Any] = Field(default_factory=dict)  # §AQ PH-10 shimmer front
    age: Optional[str] = None
    age_tick: int = 0
    age_day: int = 1
    age_total_days: int = 10



class HistoryEvent(BaseModel):
    type: Literal[
        "death", "birth", "promotion", "demotion", "outbreak", "recovery",
        "bloom", "alliance", "rivalry", "predation", "war", "ruin", "settlement", "succession", "schism",
        "fire", "disaster", "conquest", "culture",
        "coalition_formed", "coalition_joined", "coalition_dissolved",
        "peace", "tribute", "betrayal", "defection", "cannibalism", "exile",
        "wither", "takeover",
        "miracle", "sermon", "synod", "temple", "epiphany", "resonance",
        "compost", "banquet", "raid", "hospitality",
        "peace_envoy", "market", "caravan", "omen", "regicide", "herald",
        "anomaly",
    ] = ("death")
    tick: int
    entity_id: int
    caste: Optional[str] = None
    cause: str = ""  # death cause when type == "death"
    x: float = 0.0
    y: float = 0.0
    payload: dict[str, Any] = Field(default_factory=dict)


class HelloMessage(BaseModel):
    type: Literal["hello"] = "hello"
    seed: int
    tick_rate: float
    width: float
    height: float
    boundary: str


class GodLaws(BaseModel):
    """Laws of nature god may set. God cannot touch individual creatures."""

    boundary: Optional[Literal["wrap", "clamp"]] = None
    food_count: Optional[int] = Field(None, ge=0, le=2000)
    energy_max: Optional[float] = Field(None, gt=1, le=10000)

    # Plants & nutrient cycle (§H) + biodiversity (§O)
    plant_growth_rate: Optional[float] = Field(None, ge=0, le=1)
    plant_spread_rate: Optional[float] = Field(None, ge=0, le=1)
    nutrient_cycle_rate: Optional[float] = Field(None, ge=0, le=10)
    plant_variants_enabled: Optional[bool] = None
    poison_rate: Optional[float] = Field(None, ge=0, le=1)
    beast_ratio: Optional[float] = Field(None, ge=0, le=1)
    diet_strictness: Optional[float] = Field(None, ge=0, le=1)

    # Territory & clan depth (§P)
    territory_enabled: Optional[bool] = None
    territory_radius: Optional[float] = Field(None, ge=1, le=50)
    trespass_decay: Optional[float] = Field(None, ge=0, le=5)
    totems_enabled: Optional[bool] = None
    succession_enabled: Optional[bool] = None

    # Clan founding (§V) — settlement granularity
    max_clans: Optional[int] = Field(None, ge=-1, le=64)

    energy_decay_per_tick: Optional[float] = Field(None, ge=0, le=2)
    energy_from_food: Optional[float] = Field(None, ge=0, le=1000)
    hungry_ratio: Optional[float] = Field(None, gt=0, le=1)
    starving_ratio: Optional[float] = Field(None, gt=0, le=1)
    perceive_radius: Optional[float] = Field(None, gt=0.5, le=60)
    eat_radius: Optional[float] = Field(None, gt=0.1, le=10)
    wander_turn: Optional[float] = Field(None, ge=0, le=3.2)
    steer_turn: Optional[float] = Field(None, ge=0, le=3.2)
    desperate_perceive_mult: Optional[float] = Field(None, ge=1, le=4)
    hungry_perceive_mult: Optional[float] = Field(None, ge=1, le=4)
    desperate_speed_mult: Optional[float] = Field(None, ge=1, le=4)
    food_giveup_ticks: Optional[int] = Field(None, ge=0, le=100000)
    lifespan_mult: Optional[float] = Field(None, ge=0.01, le=100)

    # Reproduction & inheritance (Nature's Law)
    birth_enabled: Optional[bool] = None
    adult_age: Optional[float] = Field(None, ge=0, le=100000)
    mate_radius: Optional[float] = Field(None, ge=0.5, le=50)
    mate_energy_min: Optional[float] = Field(None, ge=0, le=10000)
    birth_rate: Optional[float] = Field(None, ge=0, le=1)
    sex_ratio: Optional[float] = Field(None, ge=0, le=1)
    mutation_rate: Optional[float] = Field(None, ge=0, le=1)
    max_sides: Optional[int] = Field(None, ge=3, le=64)
    birth_energy_cost: Optional[float] = Field(None, ge=0, le=1000)
    reproduction_cooldown: Optional[int] = Field(None, ge=0, le=100000)
    carrying_capacity: Optional[int] = Field(None, ge=-1, le=10000)
    max_population: Optional[int] = Field(None, ge=-1, le=15000)
    euthanasia_threshold: Optional[float] = Field(None, ge=0, le=1)

    # Health & disease
    disease_enabled: Optional[bool] = None
    disease_outbreak_rate: Optional[float] = Field(None, ge=0, le=1)
    disease_rate: Optional[float] = Field(None, ge=0, le=1)
    disease_radius: Optional[float] = Field(None, ge=0.5, le=50)
    disease_energy_drain: Optional[float] = Field(None, ge=0, le=10)
    recovery_rate: Optional[float] = Field(None, ge=0, le=1)
    disease_lethality: Optional[float] = Field(None, ge=0, le=1)

    # Environment: sky, seasons, weather
    day_length: Optional[int] = Field(None, ge=2, le=200000)
    season_length: Optional[int] = Field(None, ge=2, le=1000000)
    night_sight_mult: Optional[float] = Field(None, ge=0.05, le=2)
    weather_enabled: Optional[bool] = None
    weather_change_rate: Optional[float] = Field(None, ge=0, le=1)
    fog_sight_mult: Optional[float] = Field(None, ge=0.05, le=2)
    rain_speed_mult: Optional[float] = Field(None, ge=0.1, le=2)
    storm_wander_bonus: Optional[float] = Field(None, ge=0, le=3.2)

    # Society — interaction & clan relations
    cohesion_weight: Optional[float] = Field(None, ge=0, le=3)
    alignment_weight: Optional[float] = Field(None, ge=0, le=3)
    separation_weight: Optional[float] = Field(None, ge=0, le=3)
    flock_radius: Optional[float] = Field(None, ge=1, le=40)
    relation_drift_rate: Optional[float] = Field(None, ge=0, le=10)
    alliance_threshold: Optional[int] = Field(None, ge=-100, le=100)
    rivalry_threshold: Optional[int] = Field(None, ge=-100, le=100)
    communication_enabled: Optional[bool] = None
    signal_radius: Optional[float] = Field(None, ge=3, le=40)
    food_call_rate: Optional[float] = Field(None, ge=0, le=1)
    alarm_call_rate: Optional[float] = Field(None, ge=0, le=1)

    # Communication II — knowledge, teaching & mobbing (§X)
    knowledge_enabled: Optional[bool] = None
    knowledge_ttl: Optional[int] = Field(None, ge=20, le=100000)
    knowledge_share_rate: Optional[float] = Field(None, ge=0, le=1)
    help_call_enabled: Optional[bool] = None
    help_radius: Optional[float] = Field(None, ge=2, le=60)
    defense_weight: Optional[float] = Field(None, ge=0, le=5)
    age_enabled: Optional[bool] = None
    age_length: Optional[int] = Field(None, ge=100, le=1000000)
    culture_enabled: Optional[bool] = None
    culture_spread_rate: Optional[float] = Field(None, ge=0, le=1)
    trait_mutation_rate: Optional[float] = Field(None, ge=0, le=1)
    wildfire_enabled: Optional[bool] = None
    fire_rate: Optional[float] = Field(None, ge=0, le=0.05)
    fire_spread_rate: Optional[float] = Field(None, ge=0, le=1)
    disaster_enabled: Optional[bool] = None
    disaster_rate: Optional[float] = Field(None, ge=0, le=0.05)

    door_clearance: Optional[float] = Field(None, ge=1, le=5)
    schism_enabled: Optional[bool] = None
    schism_threshold: Optional[float] = Field(None, ge=0, le=1)
    schism_min_pop: Optional[int] = Field(None, ge=2, le=100)

    house_min_size: Optional[float] = Field(None, ge=3, le=60)
    house_max_size: Optional[float] = Field(None, ge=3, le=80)

    # Weather → crops (§R)
    rain_growth_mult: Optional[float] = Field(None, ge=0.5, le=3)
    fog_mushroom_mult: Optional[float] = Field(None, ge=0.5, le=3)
    storm_plant_damage: Optional[float] = Field(None, ge=0, le=1)

    # Weather → sickness (§R)
    weather_sickness_enabled: Optional[bool] = None
    chill_rate: Optional[float] = Field(None, ge=0, le=1)
    chill_threshold: Optional[float] = Field(None, ge=1, le=100)
    chill_drain: Optional[float] = Field(None, ge=0, le=5)
    wet_disease_mult: Optional[float] = Field(None, ge=1, le=5)

    # Shelter
    shelter_enabled: Optional[bool] = None
    exposure_drain: Optional[float] = Field(None, ge=0, le=10)
    house_capacity: Optional[int] = Field(None, ge=1, le=64)
    house_claim_enabled: Optional[bool] = None
    rest_recovery_mult: Optional[float] = Field(None, ge=0, le=10)
    house_decay_ticks: Optional[int] = Field(None, ge=100, le=100000)

    # Hearths (§AQ PH-1)
    hearths_enabled: Optional[bool] = None

    # Predation (§I)
    predation_enabled: Optional[bool] = None
    predator_ratio: Optional[float] = Field(None, ge=0, le=1)
    hunt_radius: Optional[float] = Field(None, ge=1, le=40)
    bite_damage: Optional[float] = Field(None, ge=0, le=1000)
    bite_cooldown: Optional[int] = Field(None, ge=0, le=100000)
    energy_from_prey: Optional[float] = Field(None, ge=0, le=1000)
    fear_radius: Optional[float] = Field(None, ge=1, le=40)

    # Clan war (§I)
    war_enabled: Optional[bool] = None
    attack_radius: Optional[float] = Field(None, ge=0.5, le=10)
    attack_damage: Optional[float] = Field(None, ge=0, le=1000)

    # Politics (§AB) — coalitions, leaders, resources, betrayal
    coalitions_enabled: Optional[bool] = None
    coalition_threshold: Optional[int] = Field(None, ge=-100, le=100)
    coalition_min_size: Optional[int] = Field(None, ge=2, le=16)
    leader_decisions_enabled: Optional[bool] = None
    resource_sharing_enabled: Optional[bool] = None
    larder_capacity: Optional[float] = Field(None, ge=0, le=5000)
    aid_rate: Optional[float] = Field(None, ge=0, le=1)
    tribute_enabled: Optional[bool] = None
    betrayal_enabled: Optional[bool] = None
    defection_enabled: Optional[bool] = None

    # Desperation cannibalism (§AC)
    cannibalism_enabled: Optional[bool] = None
    cannibalism_hunger_ratio: Optional[float] = Field(None, ge=0, le=1)
    cannibalism_energy: Optional[float] = Field(None, ge=0, le=1000)
    eat_enemy_enabled: Optional[bool] = None
    eat_kin_enabled: Optional[bool] = None
    kin_stigma: Optional[int] = Field(None, ge=0, le=100)
    exile_on_kin_eat: Optional[bool] = None

    # Food decay (§AE)
    food_decay_enabled: Optional[bool] = None
    food_lifespan_ticks: Optional[int] = Field(None, ge=100, le=1000000)

    # Unified Theology (§AP) — shrines, tithes & the clan faith pool
    theology_enabled: Optional[bool] = None
    tithe_rate: Optional[float] = Field(None, ge=0, le=1)
    temple_faith_cost: Optional[float] = Field(None, ge=0, le=100000)

    # Agriculture (§AM) — sowing, farm plots, granaries, soil & feasts
    agriculture_enabled: Optional[bool] = None
    granaries_enabled: Optional[bool] = None
    granary_capacity: Optional[float] = Field(None, ge=0, le=100000)
    soil_depletion_enabled: Optional[bool] = None
    banquets_enabled: Optional[bool] = None

    # Communication, language & diplomacy (§AN)
    vocalizations_enabled: Optional[bool] = None
    scent_enabled: Optional[bool] = None
    envoys_enabled: Optional[bool] = None
    markets_enabled: Optional[bool] = None
    omens_enabled: Optional[bool] = None
    dialect_drift_enabled: Optional[bool] = None

    # Rivers (§AQ PH-3)
    rivers_enabled: Optional[bool] = None
    river_count: Optional[int] = Field(None, ge=0, le=8)

    # Relief (§AQ PH-4) — elevation, cliffs & roads
    relief_enabled: Optional[bool] = None

    # Materials (§AQ PH-6)
    structural_enabled: Optional[bool] = None
    rubble_blocking_enabled: Optional[bool] = None

    # Seismic & wave physics (§AQ PH-8)
    earthquake_enabled: Optional[bool] = None
    earthquake_rate: Optional[float] = Field(None, ge=0, le=0.01)
    signal_speed: Optional[float] = Field(None, ge=0, le=40)

    # Electrostatics (§AQ PH-9)
    lightning_enabled: Optional[bool] = None
    lightning_strike_rate: Optional[float] = Field(None, ge=0, le=0.05)

    # Cosmological (§AQ PH-10)
    anomaly_count: Optional[int] = Field(None, ge=0, le=8)

    # T: soften winter
    winter_food_mult: Optional[float] = Field(None, ge=0.1, le=2)
