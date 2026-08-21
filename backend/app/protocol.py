"""Wire protocol schemas shared with the web frontend.

Message flow:
  server -> client: {"type": "hello", ...} then {"type": "state", ...} each tick
  client -> server: {"action": "pause"|"resume"|"step"|"reset"|"set_speed", "value": ...}
"""

from enum import Enum
from typing import Literal, Optional

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
    door_width: Optional[float] = None
    door_offset: Optional[float] = None


class StateMessage(BaseModel):
    type: Literal["state"] = "state"
    tick: int
    width: float
    height: float
    boundary: str
    population: dict[str, int] = Field(default_factory=dict)
    entities: list[EntityState] = Field(default_factory=list)


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
    door_clearance: Optional[float] = Field(None, ge=1, le=5)
    house_min_size: Optional[float] = Field(None, ge=3, le=60)
    house_max_size: Optional[float] = Field(None, ge=3, le=80)
