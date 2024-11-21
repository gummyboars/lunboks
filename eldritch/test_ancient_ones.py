#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])
from eldritch.test_events import EventTest
from eldritch.ancient_ones import base as ancient_ones
from eldritch import events
from eldritch.characters import seaside as seaside_characters
from eldritch.eldritch import GameState
from eldritch.encounters.location import core as location_encounters
from eldritch.events import CityMovement
from eldritch.items.common import base as common
from eldritch.items import deputy
from eldritch.monsters import base as monsters
from eldritch.skills import base as skills
from eldritch import specials
from eldritch.mythos import base as mythos
from game import InvalidMove


def CreateDummyEncounterCard():
  return location_encounters.EncounterCard("Dummy", {"Woods": lambda char: events.Nothing()})


class TestSquidFace(EventTest):
  def testInitialMaxSanStam(self):
    self.state.all_characters.update({"Spy": seaside_characters.Spy()})
    self.state.characters.append(self.state.all_characters["Spy"])
    self.state.ancient_one = ancient_ones.SquidFace()
    self.state.ancient_one.setup(self.state)
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.state.characters[-1].stamina, 3)
    self.assertEqual(self.state.characters[-1].sanity, 5)

  def testMaxSanStamAfterDevoured(self):
    self.state.ancient_one = ancient_ones.SquidFace()
    self.state.turn_phase = "mythos"
    self.state.event_stack.append(events.Devoured(self.char))
    self.resolve_until_done()

    self.state.common.extend([common.Food(0), common.Food(1)])
    self.state.unique.append(common.Food(2))
    self.state.skills.append(skills.Marksman(0))
    self.state.handle_choose_char(0, "Researcher")

    self.state.next_turn()
    self.assertEqual(self.state.characters[0].name, "Researcher")
    self.assertEqual(self.state.characters[0].sanity, 4)
    self.assertEqual(self.state.characters[0].stamina, 4)

  def testMaxSanStamGain(self):
    self.char.stamina = 5
    self.char.sanity = 5
    self.state.event_stack.append(events.Gain(self.char, {"sanity": 5, "stamina": 5}))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.state.ancient_one = ancient_ones.SquidFace()
    self.char.stamina = 3
    self.char.sanity = 3
    self.state.event_stack.append(events.Gain(self.char, {"sanity": 5, "stamina": 5}))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)

  def testMaxSanStamOnlyDuringSlumber(self):
    self.state.ancient_one = ancient_ones.SquidFace()
    self.assertEqual(self.char.max_stamina(self.state), 4)
    self.assertEqual(self.char.max_sanity(self.state), 4)

    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.assertEqual(self.char.max_stamina(self.state), 5)
    self.assertEqual(self.char.max_sanity(self.state), 5)

  def testMonsters(self):
    cultist = monsters.Cultist()
    self.assertEqual(cultist.damage("horror", self.state, self.char), None)
    self.state.ancient_one = ancient_ones.SquidFace()
    self.assertEqual(cultist.damage("horror", self.state, self.char), 2)
    self.assertEqual(cultist.difficulty("horror", self.state, self.char), -2)

  def testAttack(self):
    self.state.ancient_one = ancient_ones.SquidFace()
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.RemoveDoom())
    self.resolve_until_done()

    self.assertEqual(self.state.ancient_one.doom, 12)
    self.assertEqual(self.state.ancient_one.health, 12)
    self.assertEqual(self.char.max_stamina(self.state), 5)

    self.state.event_stack.append(events.AncientAttack(self.char))
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.assertCountEqual(choice.choices, ["Sanity", "Stamina"])
    choice.resolve(self.state, "Stamina")
    self.resolve_until_done()

    self.assertEqual(self.state.ancient_one.doom, 13)
    self.assertEqual(self.state.ancient_one.health, 13)
    self.assertEqual(self.char.max_stamina(self.state), 4)

  def testAttackMaxDoom(self):
    self.state.ancient_one = ancient_ones.SquidFace()
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.assertEqual(self.state.ancient_one.doom, 13)
    self.assertEqual(self.state.ancient_one.health, 13)
    self.assertEqual(self.char.max_sanity(self.state), 5)

    self.state.event_stack.append(events.AncientAttack(self.char))
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.assertCountEqual(choice.choices, ["Sanity", "Stamina"])
    choice.resolve(self.state, "Sanity")
    self.resolve_until_done()

    self.assertEqual(self.state.ancient_one.doom, 13)
    self.assertEqual(self.state.ancient_one.health, 13)
    self.assertEqual(self.char.max_sanity(self.state), 4)


class TestYellowKing(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.YellowKing()

  def testMonsters(self):
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertTrue(cultist.has_attribute("flying", self.state, self.char))
    self.assertEqual(cultist.movement(self.state), "flying")
    self.assertEqual(cultist.difficulty("combat", self.state, self.char), -2)

  def testSealClues(self):
    self.state.places["Isle"].gate = self.state.gates.pop()
    self.char.place = self.state.places["Isle"]
    self.char.clues = 10
    self.state.event_stack.append(events.GateCloseAttempt(self.char, "Isle"))
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(events.SpendChoice)
      choice.resolve(self.state, "Pass")
    choice = self.resolve_to_choice(events.SpendChoice)
    self.spend("clues", 5, choice)
    with self.assertRaisesRegex(InvalidMove, "additional 3 clues"):
      choice.resolve(self.state, "Yes")
    self.spend("clues", 3, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()

  def testCombatRating(self):
    self.state.terror = 5
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.assertEqual(self.state.ancient_one.combat_rating(self.state, self.char), -5)

  def testAttack(self):
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Luck of 1 + difficulty of +1 = 2
    self.assertEqual(self.char.sanity, 3)

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 1)  # Luck of 1 + difficulty of 0 = 1
    self.assertEqual(self.char.sanity, 3)


class TestChaosGod(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.ChaosGod()

  def testMonsters(self):
    maniac = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Maniac)
    )
    self.assertEqual(maniac.toughness(self.state, self.char), 2)

  def testDefeat(self):
    self.state.event_stack.append(events.Awaken())
    for _ in self.state.resolve_loop():
      pass

    self.assertEqual(self.state.game_stage, "defeat")


class TestWendigo(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.Wendigo()

  def testMonsters(self):
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertEqual(cultist.toughness(self.state, self.char), 3)

  def testStreet(self):
    stamina = self.char.stamina
    self.advance_turn(self.state.turn_number, "movement")
    self.char.place = self.state.places["Merchant"]
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, stamina)
    self.advance_turn(self.state.turn_number + 1, "upkeep")
    self.assertEqual(self.char.stamina, stamina - 1)

  def testLocation(self):
    self.advance_turn(self.state.turn_number, "movement")
    self.char.place = self.state.places["Woods"]
    self.state.places["Uptown"].encounters = [CreateDummyEncounterCard()]
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    stamina = self.char.stamina
    self.advance_turn(self.state.turn_number + 1, "upkeep")
    self.assertEqual(self.char.stamina, stamina)

  def testDiscardWeather(self):
    self.state.mythos.appendleft(mythos.Mythos6())
    self.state.event_stack.append(events.Mythos(self.char))
    self.resolve_until_done()

    self.assertIsNotNone(self.state.places["Graveyard"].gate)
    self.assertIsNone(self.state.environment)

  def testIgnoresOtherEnvironments(self):
    self.state.mythos.appendleft(mythos.Mythos2())
    self.state.event_stack.append(events.Mythos(self.char))
    self.resolve_until_done()

    self.assertIsNotNone(self.state.places["Isle"].gate)
    self.assertIsNotNone(self.state.environment)
    self.assertEqual(self.state.environment.name, "Mythos2")

  def testAwaken(self):
    self.state.all_characters.update({"Spy": seaside_characters.Spy()})
    self.state.characters.append(self.state.all_characters["Spy"])
    spy = self.state.characters[-1]
    self.char.possessions.extend([common.Food(0), common.Derringer18(0), skills.Marksman(0)])
    spy.possessions.extend([deputy.PatrolWagon(), specials.Deputy(), specials.Blessing(0)])

    self.state.event_stack.append(events.Awaken())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Rolled once for food, once for patrol wagon

    self.assertNotIn("Food", [pos.name for pos in self.char.possessions])
    self.assertEqual(len(self.char.possessions), 2)
    self.assertIn("Patrol Wagon", [pos.name for pos in spy.possessions])
    self.assertEqual(len(spy.possessions), 3)

  def testAttack(self):
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight of 4 + difficulty of +1 = 5
    self.assertEqual(self.char.stamina, 3)

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight of 4 + difficulty of 0 = 4
    self.assertEqual(self.char.stamina, 3)


class TestBlackPharaohMasks(unittest.TestCase):
  def testMasksIncluded(self):
    state = GameState()
    state.ancient_one = ancient_ones.BlackPharaoh()
    state.initialize()
    self.assertIn("Haunter", [mon.name for mon in state.monsters])
    self.assertIn("Dark Pharaoh", [mon.name for mon in state.monsters])

  def testMasksNotIncluded(self):
    state = GameState()
    state.ancient_one = ancient_ones.BlackGoat()
    state.initialize()
    self.assertNotIn("Haunter", [mon.name for mon in state.monsters])


class TestBlackPharaoh(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.BlackPharaoh()

  def testMonsters(self):
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertTrue(cultist.has_attribute("endless", self.state, self.char))

  def testAwaken(self):
    self.state.all_characters.update({"Spy": seaside_characters.Spy()})
    self.state.characters.append(self.state.all_characters["Spy"])
    spy = self.state.characters[-1]
    spy.clues = 3

    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.assertTrue(self.char.gone)
    self.assertFalse(spy.gone)

  def testAttack(self):
    self.char.clues = 1
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      spend_choice = self.resolve_to_choice(events.SpendChoice)
      spend_choice.resolve(self.state, "Pass")
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Lore of 4 + difficulty of +1 = 5
    self.assertEqual(self.char.clues, 1)
    self.assertFalse(self.char.gone)

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      spend_choice = self.resolve_to_choice(events.SpendChoice)
      spend_choice.resolve(self.state, "Fail")
      for _ in self.state.resolve_loop():
        pass
      self.assertEqual(rand.call_count, 4)  # Lore of 4 + difficulty of 0 = 4
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(self.char.gone)


class TestBlackGoat(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.BlackGoat()

  def testMonsters(self):
    tree = monsters.TentacleTree()
    self.assertTrue(tree.has_attribute("endless", self.state, self.char))

  def testSlumberToughness(self):
    tree = monsters.TentacleTree()
    self.assertTrue(tree.toughness(self.state, self.char), 4)
    cultist = monsters.Cultist()
    self.assertTrue(cultist.toughness(self.state, self.char), 2)

  def testAwaken(self):
    self.state.all_characters.update({"Spy": seaside_characters.Spy()})
    self.state.characters.append(self.state.all_characters["Spy"])
    spy = self.state.characters[-1]
    spy.trophies.append(monsters.Cultist())
    self.char.trophies.append(self.state.gates.pop())

    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.assertTrue(self.char.gone)
    self.assertFalse(spy.gone)

  def testAttack(self):
    self.char.trophies.append(monsters.Cultist())
    self.char.trophies[0].idx = 0
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Sneak of 1 + difficulty of +1 = 2
    self.assertFalse(self.char.gone)

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      choice = self.resolve_to_choice(events.SpendChoice)
      self.toggle_spend(0, "Cultist0", choice)
      choice.resolve(self.state, "Spend")
      for _ in self.state.resolve_loop():
        pass
      self.assertEqual(rand.call_count, 1)  # Sneak of 1 + difficulty of 0 = 1
    self.assertTrue(self.char.gone)


class TestSerpentGod(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.SerpentGod()

  def testMonsters(self):
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertEqual(cultist.damage("combat", self.state, self.char), 4)
    self.assertEqual(cultist.difficulty("combat", self.state, self.char), 0)

  def testDefeatCultist(self):
    self.assertEqual(self.state.ancient_one.doom, 0)
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    cultist.place = self.state.places["Downtown"]
    self.char.place = self.state.places["Downtown"]
    self.state.event_stack.append(events.Combat(self.char, cultist))

    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(events.CombatChoice)
    self.choose_items(choose_weapons, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.state.ancient_one.doom, 1)

  def testEvadeCultist(self):
    self.char.speed_sneak_slider = 0
    self.assertEqual(self.state.ancient_one.doom, 0)
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    cultist.place = self.state.places["Downtown"]
    self.char.place = self.state.places["Downtown"]
    self.state.event_stack.append(events.Combat(self.char, cultist))

    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testLost(self):
    self.assertEqual(self.state.ancient_one.doom, 0)
    self.state.event_stack.append(events.LostInTimeAndSpace(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.ancient_one.doom, 1)

  def testAwaken(self):
    self.state.all_characters.update({"Spy": seaside_characters.Spy()})
    self.state.characters.append(self.state.all_characters["Spy"])
    spy = self.state.characters[-1]
    self.state.event_stack.append(events.Curse(self.char))
    self.resolve_until_done()

    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.assertTrue(self.char.gone)
    self.assertFalse(spy.gone)
    self.assertEqual(spy.bless_curse, -1)

  def testAttack(self):
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=6)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Speed of 4 + difficulty of +1 = 5
    self.assertFalse(self.char.gone)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Speed of 4 + difficulty of 0 = 4
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)


class TestSpaceBubbles(EventTest):
  def setUp(self):
    super().setUp()
    self.state.ancient_one = ancient_ones.SpaceBubbles()

  def testMonsters(self):
    cultist = next(
      monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertEqual(cultist.damage("combat", self.state, self.char), 1)
    self.assertEqual(cultist.difficulty("combat", self.state, self.char), -1)
    self.assertTrue(cultist.has_attribute("magical immunity", self.state, self.char))

  def testCloseGateDifficulty(self):
    self.state.places["Isle"].gate = self.state.gates.pop()
    self.char.place = self.state.places["Isle"]
    self.char.clues = 1
    self.state.event_stack.append(events.GateCloseAttempt(self.char, "Isle"))
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1, 1, 1])):
      choice = self.resolve_to_choice(events.SpendChoice)
      self.assertIn("Fail", choice.choices)
      choice.resolve(self.state, "Fail")
    self.resolve_until_done()

    self.state.event_stack.append(events.GateCloseAttempt(self.char, "Isle"))
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(events.SpendChoice)
      self.assertIn("Pass", choice.choices)
      choice.resolve(self.state, "Pass")
    seal_choice = self.resolve_to_choice(events.SpendChoice)
    seal_choice.resolve(self.state, "No")
    self.resolve_until_done()

  def testLost(self):
    self.state.event_stack.append(events.LostInTimeAndSpace(self.char))
    self.resolve_until_done()
    self.assertTrue(self.char.gone)

  def testAwaken(self):
    self.state.all_characters.update({"Spy": seaside_characters.Spy()})
    self.state.characters.append(self.state.all_characters["Spy"])
    spy = self.state.characters[-1]
    spy.trophies.append(monsters.Cultist())
    self.char.trophies.append(self.state.gates.pop())

    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.assertTrue(spy.gone)
    self.assertFalse(self.char.gone)

  def testAttack(self):
    self.char.trophies.append(self.state.gates.pop())
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Will of 1 + difficulty of +1 = 2
    self.assertFalse(self.char.gone)

    self.state.event_stack.append(events.AncientAttack(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      choice = self.resolve_to_choice(events.SpendChoice)
      self.toggle_spend(0, self.char.trophies[0].handle, choice)
      choice.resolve(self.state, "Lose")
      for _ in self.state.resolve_loop():
        pass
      self.assertEqual(rand.call_count, 1)  # Will of 1 + difficulty of 0 = 1
    self.assertTrue(self.char.gone)


if __name__ == "__main__":
  unittest.main()
