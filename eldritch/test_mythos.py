#!/usr/bin/env python3

import collections
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.characters as characters
from eldritch.events import *
import eldritch.gates as gates
import eldritch.monsters as monsters
from eldritch.mythos import *
import eldritch.places as places
from eldritch.test_events import EventTest


class OpenGateTest(EventTest):

  def setUp(self):
    super(OpenGateTest, self).setUp()
    self.state.gates.clear()
    self.info = places.OtherWorldInfo("Pluto", {"blue", "yellow"})
    self.gate = gates.Gate(self.info, -2)
    self.state.gates.append(self.gate)
    self.square = self.state.places["Square"]
    self.woods = self.state.places["Woods"]
    # Add two characters to the square.
    self.state.characters.append(characters.Character("A", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.characters[-1].place = self.state.places["Square"]
    self.state.characters.append(characters.Character("B", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.characters[-1].place = self.state.places["Square"]

  def monstersByPlace(self):
    counts = collections.defaultdict(int)
    for monster in self.state.monsters:
      counts[monster.place.name if monster.place is not None else "nowhere"] += 1
    return counts

  def testOpenGate(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertIsNone(self.woods.gate)
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Square")
    self.assertEqual(self.state.characters[2].place.name, "Square")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    cup_count = monster_counts["cup"]

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 0)
    self.assertEqual(self.square.gate, self.gate)
    self.assertIsNone(self.woods.gate)
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Pluto1")
    self.assertEqual(self.state.characters[2].place.name, "Pluto1")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 1)
    self.assertEqual(monster_counts["Woods"], 0)
    self.assertEqual(monster_counts["cup"], cup_count-1)

  def testOpenGateSealed(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    monster_counts = self.monstersByPlace()
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Square")
    self.assertEqual(self.state.characters[2].place.name, "Square")
    self.assertEqual(monster_counts["Square"], 0)
    cup_count = monster_counts["cup"]
    self.square.sealed = True

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertTrue(self.square.sealed)
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Square")
    self.assertEqual(self.state.characters[2].place.name, "Square")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["cup"], cup_count)


class CloseGateTest(EventTest):

  def setUp(self):
    super(CloseGateTest, self).setUp()
    self.square = self.state.places["Square"]
    self.square.gate = self.state.gates.popleft()
    self.char.place = self.square
    self.char.explored = True
    # Set fight and lore to 4, since max difficulty is -3.
    self.char.lore_luck_slider = 3
    self.char.fight_will_slider = 3

  def testDeclineToClose(self):
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)

    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices[2], "Don't close")
    choice.resolve(self.state, "Don't close")
    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertTrue(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 0)

  def testFailToClose(self):
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)

    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices[0], "Close with fight")
    choice.resolve(self.state, "Close with fight")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertTrue(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 0)

  def testCloseWithFight(self):
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)

    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices[0], "Close with fight")
    choice.resolve(self.state, "Close with fight")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertFalse(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 0)

  def testCloseWithLore(self):
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)

    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices[1], "Close with lore")
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertFalse(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 0)

  def testDeclineToSeal(self):
    self.char.clues = 5
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)

    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_usable(0, -1, SpendClue)
    self.state.done_using[0] = True
    seal_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(seal_choice.choices[1], "No")
    seal_choice.resolve(self.state, "No")
    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertFalse(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 5)

  def testSeal(self):
    self.char.clues = 6
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)

    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_usable(0, -1, SpendClue)
    self.state.done_using[0] = True
    seal_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(seal_choice.choices[0], "Yes")
    seal_choice.resolve(self.state, "Yes")
    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertFalse(self.square.gate)
    self.assertTrue(self.square.sealed)
    self.assertEqual(self.char.clues, 1)


class SpawnClueTest(EventTest):

  def setUp(self):
    super(SpawnClueTest, self).setUp()
    self.square = self.state.places["Square"]

  def testSpawnClue(self):
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.square.clues, 0)

    self.state.event_stack.append(SpawnClue("Square"))
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.square.clues, 1)

  def testSpawnClueOnCharacter(self):
    self.char.place = self.square
    self.assertEqual(self.char.clues, 0)

    self.state.event_stack.append(SpawnClue("Square"))
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.square.clues, 0)

  def testSpawnClueOnTwoCharacters(self):
    self.char.place = self.square
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.square
    buddy.clues = 2
    self.state.characters.append(buddy)

    self.state.event_stack.append(SpawnClue("Square"))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Buddy"])
    choice.resolve(self.state, "Buddy")
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 0)
    self.assertEqual(buddy.clues, 3)
    self.assertEqual(self.square.clues, 0)


class MoveMonsterTest(EventTest):

  def setUp(self):
    super(MoveMonsterTest, self).setUp()

  def testMoveMonsterWhite(self):
    monster = self.state.monsters[0]
    monster.place = self.state.places["Rivertown"]

    self.state.event_stack.append(MoveMonster(monster, "white"))
    self.resolve_until_done()

    self.assertEqual(monster.place.name, "FrenchHill")

  def testMoveMonsterBlack(self):
    monster = self.state.monsters[0]
    monster.place = self.state.places["Rivertown"]

    self.state.event_stack.append(MoveMonster(monster, "black"))
    self.resolve_until_done()

    self.assertEqual(monster.place.name, "Easttown")

  def testMoveMonsterLocation(self):
    monster = self.state.monsters[0]
    monster.place = self.state.places["Cave"]

    self.state.event_stack.append(MoveMonster(monster, "white"))
    self.resolve_until_done()

    self.assertEqual(monster.place.name, "Rivertown")

  def testMovementTypes(self):
    self.state.monsters.clear()
    self.state.monsters.extend([
      monsters.Cultist(),  # moon, moves on black
      monsters.Ghost(),  # moon, stationary
      monsters.DimensionalShambler(),  # square, moves on white
      monsters.Ghoul(),  # hex, no movement
    ])

    for monster in self.state.monsters:
      monster.place = self.state.places["Rivertown"]

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle", "moon"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Easttown")
    self.assertEqual(self.state.monsters[1].place.name, "Rivertown")
    self.assertEqual(self.state.monsters[2].place.name, "Southside")
    self.assertEqual(self.state.monsters[3].place.name, "Rivertown")

  def testMovementAfterSpawn(self):
    self.state.monsters.clear()
    shambler = monsters.DimensionalShambler()
    shambler.place = self.state.monster_cup
    self.state.monsters.append(shambler)

    self.state.event_stack.append(Mythos3().create_event(self.state))
    self.resolve_until_done()

    # The monster will appear at the Square, but should immediately move after appearing.
    self.assertEqual(shambler.place.name, "Easttown")


class ReturnToCupTest(EventTest):

  def setUp(self):
    super(ReturnToCupTest, self).setUp()
    self.cultist = monsters.Cultist()
    self.maniac = monsters.Maniac()
    self.dream_flier = monsters.DreamFlier()
    self.zombie = monsters.Zombie()
    self.furry_beast = monsters.FurryBeast()
    self.cultist.place = self.state.places["Southside"]
    self.maniac.place = self.state.places["Outskirts"]
    self.dream_flier.place = self.state.places["Sky"]
    self.furry_beast.place = self.state.places["Woods"]
    self.zombie.place = None
    self.state.monsters.clear()
    self.state.monsters.extend([
      self.cultist, self.maniac, self.dream_flier, self.zombie, self.furry_beast])
    # TODO: also test for monster trophies

  def testReturnByName(self):
    r = ReturnToCup(names={"Dream Flier", "Maniac", "Zombie"})
    self.state.event_stack.append(r)
    self.resolve_until_done()

    self.assertEqual(r.returned, 2)

    self.assertEqual(self.dream_flier.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place, self.state.monster_cup)
    self.assertIsNone(self.zombie.place)
    self.assertEqual(self.cultist.place.name, "Southside")

  def testReturnByLocation(self):
    r = ReturnToCup(places={"Southside", "Woods"})
    self.state.event_stack.append(r)
    self.resolve_until_done()

    self.assertEqual(r.returned, 2)

    self.assertEqual(self.cultist.place, self.state.monster_cup)
    self.assertEqual(self.furry_beast.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")
    self.assertIsNone(self.zombie.place)

  def testReturnInStreets(self):
    r = ReturnToCup(places={"streets"})
    self.state.event_stack.append(r)
    self.resolve_until_done()

    self.assertEqual(r.returned, 1)

    self.assertEqual(self.cultist.place, self.state.monster_cup)
    self.assertEqual(self.furry_beast.place.name, "Woods")
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")

  def testReturnInLocations(self):
    r = ReturnToCup(places={"locations"})
    self.state.event_stack.append(r)
    self.resolve_until_done()

    self.assertEqual(r.returned, 1)

    self.assertEqual(self.cultist.place.name, "Southside")
    self.assertEqual(self.furry_beast.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")


class GlobalModifierTest(EventTest):

  def setUp(self):
    super(GlobalModifierTest, self).setUp()
    more_monsters = [monsters.Cultist(), monsters.Maniac()]
    for monster in more_monsters:
      monster.place = self.state.monster_cup
    self.state.monsters.extend(more_monsters)

  def testEnvironmentModifier(self):
    self.assertEqual(self.char.will(self.state), 1)
    self.state.event_stack.append(ActivateEnvironment(Mythos6()))
    self.resolve_until_done()
    self.assertEqual(self.char.will(self.state), 0)

  def testReplaceEnvironment(self):
    self.assertIsNone(self.state.environment)
    mythos = Mythos6()
    self.state.event_stack.append(mythos.create_event(self.state))
    self.resolve_until_done()
    self.assertEqual(self.state.environment, mythos)

    headline = Mythos11()
    self.state.event_stack.append(headline.create_event(self.state))
    self.resolve_until_done()
    self.assertEqual(self.state.environment, mythos)

    env = Mythos45()
    self.state.event_stack.append(env.create_event(self.state))
    self.resolve_until_done()
    self.assertEqual(self.state.environment, env)


if __name__ == '__main__':
  unittest.main()
