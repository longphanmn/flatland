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
