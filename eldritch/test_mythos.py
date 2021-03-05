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

  def monstersByPlace(self):
    counts = collections.defaultdict(int)
    for monster in self.state.monsters:
      counts[monster.place.name if monster.place is not None else "nowhere"] += 1
    return counts

  def testOpenGate(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertIsNone(self.woods.gate)
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    cup_count = monster_counts["cup"]

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 0)
    self.assertEqual(self.square.gate, self.gate)
    self.assertIsNone(self.woods.gate)
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 1)
    self.assertEqual(monster_counts["Woods"], 0)
    self.assertEqual(monster_counts["cup"], cup_count-1)

  def testOpenGateSealed(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    cup_count = monster_counts["cup"]
    self.square.sealed = True

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertTrue(self.square.sealed)
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["cup"], cup_count)


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
    self.cultist = [mon for mon in self.state.monsters if mon.name == "Cultist"][0]
    self.maniac = [mon for mon in self.state.monsters if mon.name == "Maniac"][0]
    self.dream_flier = [mon for mon in self.state.monsters if mon.name == "Dream Flier"][0]
    self.zombie = [mon for mon in self.state.monsters if mon.name == "Zombie"][0]
    self.furry_beast = [mon for mon in self.state.monsters if mon.name == "Furry Beast"][0]
    self.cultist.place = self.state.places["Southside"]
    self.maniac.place = self.state.places["Outskirts"]
    self.dream_flier.place = self.state.places["Sky"]
    self.furry_beast.place = self.state.places["Woods"]
    self.zombie.place = None
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
