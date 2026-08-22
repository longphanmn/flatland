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
    variant: Optional[Literal["grass", "berry", "mushroom", "poisonous"]] = None
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
    is_predator: Optional[bool] = None
    is_herbivore: Optional[bool] = None
    sleeping: Optional[bool] = None
    indoors: Optional[bool] = None
    generation: Optional[int] = None
    born_tick: Optional[int] = None
    door_width: Optional[float] = None
    door_offset: Optional[float] = None
    door_side: Optional[Literal["north", "east", "south", "west"]] = None
    is_ruin: Optional[bool] = None
    abandoned_ticks: Optional[int] = None


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
    events: list["HistoryEvent"] = Field(default_factory=list)


class HistoryEvent(BaseModel):
    type: Literal[
        "death", "birth", "promotion", "demotion", "outbreak", "recovery",
        "bloom", "alliance", "rivalry", "predation", "war", "ruin", "settlement",
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
    food_count: Optional[int] = Field(None, ge=0, le=500)
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
    carrying_capacity: Optional[int] = Field(None, ge=2, le=2000)
    max_population: Optional[int] = Field(None, ge=2, le=5000)
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
    door_clearance: Optional[float] = Field(None, ge=1, le=5)
    house_min_size: Optional[float] = Field(None, ge=3, le=60)
    house_max_size: Optional[float] = Field(None, ge=3, le=80)

    # Shelter
    shelter_enabled: Optional[bool] = None
    exposure_drain: Optional[float] = Field(None, ge=0, le=10)
    house_capacity: Optional[int] = Field(None, ge=1, le=64)
    house_claim_enabled: Optional[bool] = None
    rest_recovery_mult: Optional[float] = Field(None, ge=0, le=10)
    house_decay_ticks: Optional[int] = Field(None, ge=100, le=100000)

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
