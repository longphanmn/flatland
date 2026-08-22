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


@dataclass(frozen=True)
class CasteTraits:
    """The social order of Flatland, expressed as natural law.

    - lifespan: ticks of natural life (at 10 ticks/s: 4800 = 8 minutes)
    - speed: grid units per tick
    - sight_mult: "Sight Recognition" — higher castes perceive farther,
      aided by Fog; women see least
    - fertility: relative reproductive rate (used by §B reproduction;
      Nature's Law: development accelerates while fertility declines)
    """

    lifespan: float
    speed: float
    sight_mult: float = 1.0
    fertility: float = 1.0


CASTE_TRAITS = {
    "Woman": CasteTraits(lifespan=4800, speed=0.75, sight_mult=0.80, fertility=1.20),
    "Soldier": CasteTraits(lifespan=5400, speed=0.85, sight_mult=0.90, fertility=1.10),
    "Gentleman": CasteTraits(lifespan=6000, speed=0.55, sight_mult=1.00, fertility=1.00),
    "Professional": CasteTraits(lifespan=6600, speed=0.50, sight_mult=1.10, fertility=0.90),
    "Noble": CasteTraits(lifespan=7200, speed=0.45, sight_mult=1.20, fertility=0.80),
    # Priests: longest-lived, sharpest-sighted, nearly sterile (Nature's Law).
    "Priest": CasteTraits(lifespan=9000, speed=0.35, sight_mult=1.35, fertility=0.50),
}
DEFAULT_TRAITS = CasteTraits(lifespan=6000, speed=0.60)


def traits_for(caste: str) -> CasteTraits:
    return CASTE_TRAITS.get(caste, DEFAULT_TRAITS)


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
    age: int = 0  # ticks lived
    lifespan: float = 0.0  # 0 => derived from caste table
    sight_mult: float = 0.0  # 0 => derived from caste table
    ticks_since_meal: int = 0
    meals: int = 0
    status: str = ""  # "" | "hungry" | "starving"

    def __post_init__(self) -> None:
        if not self.caste:
            self.caste = caste_name(self.sides, self.shape)
        traits = traits_for(self.caste)
        if not self.radius:
            self.radius = RADIUS_BY_CASTE.get(self.caste, DEFAULT_RADIUS)
        if not self.lifespan:
            self.lifespan = traits.lifespan
        if not self.sight_mult:
            self.sight_mult = traits.sight_mult


@dataclass
class Food(Entity):
    kind: str = "food"


@dataclass
class House(Entity):
    kind: str = "house"
    size: float = 6.0  # square side length
    door_width: float = 4.0  # gap in the wall
    door_side: str = "south"  # "north" | "east" | "south" | "west"
    door_offset: float = 0.0  # door centre offset along that wall
