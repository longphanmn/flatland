"""Entity model: Flatland creatures (social castes) and static objects."""

from dataclasses import dataclass

# Polygons with at least this many sides are treated as Circles (priests).
PRIEST_SIDES = 24


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

    def __post_init__(self) -> None:
        if not self.caste:
            self.caste = caste_name(self.sides, self.shape)


@dataclass
class Food(Entity):
    kind: str = "food"


@dataclass
class House(Entity):
    kind: str = "house"
    size: float = 6.0  # square side length
