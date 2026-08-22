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
    kind: Literal["creature", "food", "house"]
    x: float
    y: float
    angle: float
    shape: Optional[Literal["polygon", "line"]] = None
    sides: Optional[int] = None
    caste: Optional[str] = None
    energy: Optional[float] = None
    size: Optional[float] = None
    status: Optional[Literal["", "hungry", "starving"]] = None
    radius: Optional[float] = None
    age: Optional[int] = None
    lifespan: Optional[float] = None
    stage: Optional[Literal["infant", "juvenile", "adult", "elder"]] = None
    irregularity: Optional[float] = None
    generation: Optional[int] = None
    born_tick: Optional[int] = None
    door_width: Optional[float] = None
    door_offset: Optional[float] = None
    door_side: Optional[Literal["north", "east", "south", "west"]] = None


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
    events: list["HistoryEvent"] = Field(default_factory=list)


class HistoryEvent(BaseModel):
    type: Literal["death", "birth", "promotion", "demotion"] = "death"
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
    door_clearance: Optional[float] = Field(None, ge=1, le=5)
    house_min_size: Optional[float] = Field(None, ge=3, le=60)
    house_max_size: Optional[float] = Field(None, ge=3, le=80)
