import pytest
from app.config import Config
from app.entities import Creature, Food, House
from app.simulation import Simulation


def test_creature_evolution_initialization():
    cfg = Config(seed=42)
    sim = Simulation(cfg)

    # All creatures have personality, skills, tools initialized
    creatures = list(sim.world.creatures())
    assert len(creatures) > 0
    for c in creatures:
        assert c.personality in ("brave", "cautious", "altruistic", "greedy", "explorer", "builder")
        assert isinstance(c.skills, dict)
        assert "farming" in c.skills
        assert "combat" in c.skills
        assert "foraging" in c.skills
        assert "healing" in c.skills
        if c.caste == "Soldier":
            assert c.equipped_item == "spear"
        elif c.caste == "Priest":
            assert c.equipped_item == "herb_poultice"


def test_basket_harvest_and_larder_deposit():
    cfg = Config(seed=42, shelter_enabled=True, house_claim_enabled=True, diet_strictness=0.0)
    sim = Simulation(cfg)
    c = Creature(
        shape="polygon",
        sides=4,
        x=20.0,
        y=20.0,
        energy=80.0,
        equipped_item="basket",
        food_basket=0,
        clan_id=1,
        personality="greedy",
    )
    sim._init_creature_evolution(c)
    c.equipped_item = "basket"
    c.food_basket = 0
    sim.world.add(c)

    food = Food(x=20.0, y=20.0, growth=1.0, variant="berry")
    sim.world.add(food)
    sim.world.rebuild_index()

    # Step simulation to eat/harvest
    houses = [h for h in sim.world.entities.values() if isinstance(h, House)]
    sim._update_creature(c, houses)

    # High energy creature stores food in basket
    assert c.food_basket == 1
    assert c.skills["farming"] >= 0.8
    assert c.emote == "craft"


def test_priest_heals_clanmates():
    cfg = Config(seed=42)
    sim = Simulation(cfg)

    priest = Creature(
        shape="polygon",
        sides=24,
        caste="Priest",
        x=10.0,
        y=10.0,
        clan_id=1,
    )
    sim._init_creature_evolution(priest)
    priest.caste = "Priest"
    priest.equipped_item = "herb_poultice"
    sim.world.add(priest)

    patient = Creature(
        shape="polygon",
        sides=4,
        caste="Artisan",
        x=11.0,
        y=10.0,
        clan_id=1,
        health=40.0,
        infected=True,
    )
    sim._init_creature_evolution(patient)
    patient.health = 40.0
    patient.infected = True
    sim.world.add(patient)
    sim.world.rebuild_index()

    houses = []
    # Trigger tick where priest acts
    sim.tick = (8 - (priest.id % 8)) % 8
    sim._update_creature(priest, houses)

    # §AT-4 H-1: base round is 15 HP, scaling with the priest's healing skill
    assert patient.health >= 55.0
    assert not patient.infected
    assert priest.skills["healing"] >= 1.5
    assert priest.emote == "heal"
    assert patient.emote == "cheer"


def test_skill_milestone_and_title_unlock():
    cfg = Config(seed=42)
    sim = Simulation(cfg)

    c = Creature(shape="polygon", sides=3, caste="Soldier", x=5.0, y=5.0)
    sim._init_creature_evolution(c)
    assert c.title is None

    # Give combat XP
    c.skills["combat"] = 15.0
    sim._update_creature_skills_and_titles(c)
    assert c.title == "the Slayer"

    # Master level
    c.skills["combat"] = 35.0
    sim._update_creature_skills_and_titles(c)
    assert c.title == "the Fearless Champion"
    assert c.emote == "cheer"


def test_infant_metabolic_energy_decay():
    cfg = Config(seed=42, shelter_enabled=False)
    sim = Simulation(cfg)

    # Infant creature
    infant = Creature(shape="polygon", sides=4, x=10.0, y=10.0, energy=80.0, age=10, lifespan=1000, generation=1)
    assert infant.stage == "infant"

    # Adult creature
    adult = Creature(shape="polygon", sides=4, x=30.0, y=30.0, energy=80.0, age=500, lifespan=1000, generation=1)
    assert adult.stage == "adult"

    sim._update_creature(infant, [])
    sim._update_creature(adult, [])

    infant_loss = 80.0 - infant.energy
    adult_loss = 80.0 - adult.energy

    # Infant decay is ~45% of adult decay
    assert infant_loss < adult_loss
    assert pytest.approx(infant_loss / adult_loss, 0.05) == 0.45


def test_combat_energy_drain():
    cfg = Config(seed=42, attack_radius=5.0, attack_damage=10.0, war_enabled=True)
    sim = Simulation(cfg)

    # Create 2 creatures from enemy clans
    c1 = Creature(shape="polygon", sides=3, caste="Soldier", x=10.0, y=10.0, clan_id=1, energy=80.0, health=100.0)
    c2 = Creature(shape="polygon", sides=3, caste="Soldier", x=10.5, y=10.0, clan_id=2, energy=80.0, health=100.0)
    sim.world.add(c1)
    sim.world.add(c2)
    sim.world.rebuild_index()

    # Mark clans at war (rivalry threshold is -75)
    sim.relations[(1, 2)] = -80

    sim._update_war()

    # Combatants expend energy
    winner = c2 if c1.id < c2.id else c1
    loser = c1 if c1.id < c2.id else c2
    assert winner.energy < 80.0
    assert loser.energy < 80.0


def test_creature_carries_and_consumes_food_reserve():
    cfg = Config(seed=42, shelter_enabled=False)
    sim = Simulation(cfg)

    # Creature far from any food with low energy and 2 food in basket
    c = Creature(shape="polygon", sides=4, x=10.0, y=10.0, energy=30.0, equipped_item="basket", food_basket=2)
    sim.world.add(c)
    sim.world.rebuild_index()

    # Step creature update
    sim._update_creature(c, [])

    # Autonomously consumed 1 food from reserve, replenished energy
    assert c.food_basket == 1
    assert c.energy > 30.0
    assert c.emote == "craft"

