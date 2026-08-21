"""Entity model: Flatland creatures (social castes) and static objects."""

from dataclasses import dataclass

# Polygons with at least this many sides are treated as Circles (priests).
PRIEST_SIDES = 24

# Body radius (grid units) per caste. Houses size their doorway from these.
RADIUS_BY_CASTE = {
    "Woman": 0.9,
    "Soldier": 1.05,
    "Gentleman": 1.15,
    "Professional": 1.25,
    "Noble": 1.35,
    "Priest": 1.45,
}
DEFAULT_RADIUS = 1.2


def caste_name(sides: int, shape: str) -> str:
    """Map a creature's geometry to its Flatland social caste."""
    if shape == "line":
        return "Woman"
    if sides < 3:
        return "Irregular"
    if sides == 3:
        return "Soldier"
    if sides == 4:
        return "Gentleman"
    if sides == 5:
        return "Professional"
    if sides < PRIEST_SIDES:
        return "Noble"
    return "Priest"


@dataclass
class Entity:
    id: int = 0  # assigned by World.add
    kind: str = ""  # "creature" | "food" | "house"
    x: float = 0.0
    y: float = 0.0
    angle: float = 0.0


@dataclass
class Creature(Entity):
    kind: str = "creature"
    shape: str = "polygon"  # "polygon" | "line"
    sides: int = 4
    speed: float = 0.6  # grid units per tick
    energy: float = 80.0
    caste: str = ""
    radius: float = 0.0  # body radius; derived from caste when unset
    ticks_since_meal: int = 0
    meals: int = 0
    status: str = ""  # "" | "hungry" | "starving"

    def __post_init__(self) -> None:
        if not self.caste:
            self.caste = caste_name(self.sides, self.shape)
        if not self.radius:
            self.radius = RADIUS_BY_CASTE.get(self.caste, DEFAULT_RADIUS)


@dataclass
class Food(Entity):
    kind: str = "food"


@dataclass
class House(Entity):
    kind: str = "house"
    size: float = 6.0  # square side length
    door_width: float = 4.0  # gap in the south wall
    door_offset: float = 0.0  # door centre offset along the south wall
