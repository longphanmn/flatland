"""Typed mirror of the wire protocol (backend/app/protocol.py).

The TUI is a separate client and never imports backend code, so the
message schemas live here. Parsing is tolerant: unknown fields are
ignored, missing fields fall back to defaults — an older/newer server
must not crash the terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _f(d: dict, k: str, default: float = 0.0) -> float:
    v = d.get(k)
    return default if v is None else float(v)


def _i(d: dict, k: str, default: int = 0) -> int:
    v = d.get(k)
    return default if v is None else int(v)


def _s(d: dict, k: str, default: str = "") -> str:
    v = d.get(k)
    return default if v is None else str(v)


def _o(d: dict, k: str):
    return d.get(k)


@dataclass(slots=True)
class EntityState:
    id: int
    kind: str
    x: float = 0.0
    y: float = 0.0
    angle: float = 0.0
    shape: Optional[str] = None
    sides: Optional[int] = None
    caste: Optional[str] = None
    energy: Optional[float] = None
    growth: Optional[float] = None
    variant: Optional[str] = None
    size: Optional[float] = None
    status: Optional[str] = None
    radius: Optional[float] = None
    age: Optional[int] = None
    lifespan: Optional[float] = None
    stage: Optional[str] = None
    irregularity: Optional[float] = None
    health: Optional[float] = None
    infected: bool = False
    meals: Optional[int] = None
    sex: Optional[str] = None
    mother_id: Optional[int] = None
    father_id: Optional[int] = None
    clan_id: Optional[int] = None
    clan_color: Optional[str] = None
    clan_name: Optional[str] = None
    is_predator: bool = False
    is_herbivore: bool = False
    sleeping: bool = False
    indoors: bool = False
    generation: Optional[int] = None
    born_tick: Optional[int] = None
    personal_name: Optional[str] = None
    glyph: Optional[str] = None
    chill: Optional[float] = None
    trait: Optional[str] = None
    equipped_item: Optional[str] = None
    food_basket: int = 0
    personality: Optional[str] = None
    skills: dict[str, float] = field(default_factory=dict)
    title: Optional[str] = None
    emote: Optional[str] = None
    door_width: Optional[float] = None
    door_offset: Optional[float] = None
    door_side: Optional[str] = None
    is_ruin: bool = False
    is_main: bool = False
    abandoned_ticks: Optional[int] = None

    @classmethod
    def from_dict(cls, d: dict) -> "EntityState":
        return cls(
            id=_i(d, "id"),
            kind=_s(d, "kind"),
            x=_f(d, "x"),
            y=_f(d, "y"),
            angle=_f(d, "angle"),
            shape=_o(d, "shape"),
            sides=_o(d, "sides"),
            caste=_o(d, "caste"),
            energy=_o(d, "energy"),
            growth=_o(d, "growth"),
            variant=_o(d, "variant"),
            size=_o(d, "size"),
            status=_o(d, "status"),
            radius=_o(d, "radius"),
            age=_o(d, "age"),
            lifespan=_o(d, "lifespan"),
            stage=_o(d, "stage"),
            irregularity=_o(d, "irregularity"),
            health=_o(d, "health"),
            infected=bool(_o(d, "infected")),
            meals=_o(d, "meals"),
            sex=_o(d, "sex"),
            mother_id=_o(d, "mother_id"),
            father_id=_o(d, "father_id"),
            clan_id=_o(d, "clan_id"),
            clan_color=_o(d, "clan_color"),
            clan_name=_o(d, "clan_name"),
            is_predator=bool(_o(d, "is_predator")),
            is_herbivore=bool(_o(d, "is_herbivore")),
            sleeping=bool(_o(d, "sleeping")),
            indoors=bool(_o(d, "indoors")),
            generation=_o(d, "generation"),
            born_tick=_o(d, "born_tick"),
            personal_name=_o(d, "personal_name"),
            glyph=_o(d, "glyph"),
            chill=_o(d, "chill"),
            trait=_o(d, "trait"),
            equipped_item=_o(d, "equipped_item"),
            food_basket=_i(d, "food_basket", 0),
            personality=_o(d, "personality"),
            skills=dict(_o(d, "skills") or {}),
            title=_o(d, "title"),
            emote=_o(d, "emote"),
            door_width=_o(d, "door_width"),
            door_offset=_o(d, "door_offset"),
            door_side=_o(d, "door_side"),
            is_ruin=bool(_o(d, "is_ruin")),
            is_main=bool(_o(d, "is_main")),
            abandoned_ticks=_o(d, "abandoned_ticks"),
        )

    @property
    def display_name(self) -> str:
        name = self.personal_name or self.caste or self.kind
        if self.title:
            return f"{name} {self.title} #{self.id}"
        return f"{name} #{self.id}"


@dataclass(slots=True)
class HistoryEvent:
    type: str = "death"
    tick: int = 0
    entity_id: int = 0
    caste: Optional[str] = None
    cause: str = ""
    x: float = 0.0
    y: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEvent":
        return cls(
            type=_s(d, "type", "death"),
            tick=_i(d, "tick"),
            entity_id=_i(d, "entity_id"),
            caste=_o(d, "caste"),
            cause=_s(d, "cause"),
            x=_f(d, "x"),
            y=_f(d, "y"),
            payload=d.get("payload") or {},
        )

    @property
    def key(self) -> tuple:
        return (self.tick, self.type, self.entity_id)


@dataclass(slots=True)
class HelloMessage:
    seed: int = 0
    tick_rate: float = 10.0
    width: float = 400.0
    height: float = 300.0
    boundary: str = "wrap"

    @classmethod
    def from_dict(cls, d: dict) -> "HelloMessage":
        return cls(
            seed=_i(d, "seed"),
            tick_rate=_f(d, "tick_rate", 10.0),
            width=_f(d, "width", 400.0),
            height=_f(d, "height", 300.0),
            boundary=_s(d, "boundary", "wrap"),
        )


@dataclass(slots=True)
class StateMessage:
    tick: int = 0
    seed: int = 0
    width: float = 400.0
    height: float = 300.0
    boundary: str = "wrap"
    population: dict[str, int] = field(default_factory=dict)
    entities: list[EntityState] = field(default_factory=list)
    creatures_alive: int = 0
    creatures_dead: int = 0
    dead_by_cause: dict[str, int] = field(default_factory=dict)
    infected_count: int = 0
    time_of_day: float = 0.25
    day: int = 1
    season: str = "spring"
    weather: str = "clear"
    terrain_fertile: list[dict] = field(default_factory=list)
    terrain_rocks: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)
    clans: dict[str, dict] = field(default_factory=dict)
    events: list[HistoryEvent] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    fires: list[dict] = field(default_factory=list)
    age: Optional[str] = None
    age_tick: int = 0
    age_day: int = 1
    age_total_days: int = 10

    @classmethod
    def from_dict(cls, d: dict) -> "StateMessage":
        return cls(
            tick=_i(d, "tick"),
            seed=_i(d, "seed"),
            width=_f(d, "width", 400.0),
            height=_f(d, "height", 300.0),
            boundary=_s(d, "boundary", "wrap"),
            population=d.get("population") or {},
            entities=[EntityState.from_dict(e) for e in d.get("entities") or []],
            creatures_alive=_i(d, "creatures_alive"),
            creatures_dead=_i(d, "creatures_dead"),
            dead_by_cause=d.get("dead_by_cause") or {},
            infected_count=_i(d, "infected_count"),
            time_of_day=_f(d, "time_of_day", 0.25),
            day=_i(d, "day", 1),
            season=_s(d, "season", "spring"),
            weather=_s(d, "weather", "clear"),
            terrain_fertile=d.get("terrain_fertile") or [],
            terrain_rocks=d.get("terrain_rocks") or [],
            relations=d.get("relations") or [],
            clans=d.get("clans") or {},
            events=[HistoryEvent.from_dict(e) for e in d.get("events") or []],
            signals=d.get("signals") or [],
            fires=d.get("fires") or [],
            age=_o(d, "age"),
            age_tick=_i(d, "age_tick"),
            age_day=_i(d, "age_day", 1),
            age_total_days=_i(d, "age_total_days", 10),
        )
