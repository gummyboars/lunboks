#!/usr/bin/env python3

import collections
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import characters
from eldritch.events import *
from eldritch import gates
from eldritch import items
from eldritch import monsters
from eldritch.mythos import *
from eldritch import places
from eldritch import assets
from eldritch import abilities
from eldritch import encounters
from eldritch import location_specials
from eldritch.test_events import EventTest, Canceller

from game import InvalidMove, InvalidInput


class OpenGateTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.gates.clear()
    self.info = places.OtherWorldInfo("Pluto", {"blue", "yellow"})
    self.gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.gates.append(self.gate)
    self.square = self.state.places["Square"]
    self.woods = self.state.places["Woods"]
    # Add two characters to the square.
    self.state.characters.append(characters.Character("A", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["A"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]
    self.state.characters.append(characters.Character("B", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["B"] = self.state.characters[-1]
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
    self.assertEqual(self.state.ancient_one.doom, 0)
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
    self.assertEqual(self.state.ancient_one.doom, 1)
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
    self.assertEqual(self.state.ancient_one.doom, 0)
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

  def testOpenGateOnScientist(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    scientist = characters.Scientist()
    self.state.characters.append(scientist)
    self.state.all_characters["Scientist"] = scientist
    scientist.place = self.square

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.state.ancient_one.doom, 0)

  def testOpenGateAwayFromScientist(self):
    self.assertEqual(len(self.state.gates), 1)
    self.assertIsNone(self.square.gate)
    scientist = characters.Scientist()
    self.state.characters.append(scientist)
    self.state.all_characters["Scientist"] = scientist
    scientist.place = self.woods

    self.state.event_stack.append(OpenGate("Square"))
    self.resolve_until_done()

    self.assertEqual(len(self.state.gates), 0)
    self.assertIsNotNone(self.square.gate)
    self.assertEqual(self.state.ancient_one.doom, 1)
    self.assertFalse(self.square.sealed)

  def testOpenGateDrawMonstersCancelled(self):
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Square")
    self.assertEqual(self.state.characters[2].place.name, "Square")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    cup_count = monster_counts["cup"]
    self.state.characters[0].possessions.append(Canceller(DrawMonstersFromCup))

    open_gate = OpenGate("Square")
    self.state.event_stack.append(open_gate)
    self.resolve_until_done()

    self.assertTrue(open_gate.is_resolved())
    self.assertTrue(open_gate.spawn.is_cancelled())

    self.assertEqual(self.square.gate, self.gate)
    self.assertIsNone(self.woods.gate)
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Pluto1")
    self.assertEqual(self.state.characters[2].place.name, "Pluto1")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    self.assertEqual(monster_counts["cup"], cup_count)

  def testOpenGateSpawnCancelled(self):
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Square")
    self.assertEqual(self.state.characters[2].place.name, "Square")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    cup_count = monster_counts["cup"]
    self.state.characters[0].possessions.append(Canceller(MonsterSpawnChoice))

    open_gate = OpenGate("Square")
    self.state.event_stack.append(open_gate)
    self.resolve_until_done()

    self.assertTrue(open_gate.is_resolved())
    self.assertTrue(open_gate.spawn.is_cancelled())
    self.assertFalse(open_gate.spawn.is_resolved())

    self.assertEqual(self.square.gate, self.gate)
    self.assertIsNone(self.woods.gate)
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Pluto1")
    self.assertEqual(self.state.characters[2].place.name, "Pluto1")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    self.assertEqual(monster_counts["cup"], cup_count)


class MonsterSurgeTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.monsters.clear()
    self.state.monsters.extend([
        monsters.Cultist(), monsters.Ghost(), monsters.Maniac(), monsters.Vampire(),
        monsters.Warlock(), monsters.Witch(), monsters.Zombie(),
    ])
    for monster in self.state.monsters:
      monster.place = self.state.monster_cup
    self.state.gates.clear()
    self.info = places.OtherWorldInfo("Pluto", {"blue", "yellow"})
    self.gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["Woods"].gate = self.gate

    self.state.characters.clear()
    self.state.characters.append(characters.Character("A", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["A"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]
    self.state.characters.append(characters.Character("B", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["B"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]

  def monstersByPlace(self):
    counts = collections.defaultdict(int)
    for monster in self.state.monsters:
      counts[monster.place.name if monster.place is not None else "nowhere"] += 1
    return counts

  def testOnlyOneGate(self):
    surge = OpenGate("Woods")
    self.state.event_stack.append(surge)

    # With only one gate open, the surge does not present the user with a choice.
    self.resolve_until_done()
    self.assertEqual(surge.draw_monsters.count, 2)  # Number of characters
    self.assertEqual(surge.spawn.open_gates, ["Woods"])
    self.assertEqual(surge.spawn.max_count, 2)
    self.assertEqual(surge.spawn.min_count, 2)
    self.assertEqual(len(surge.spawn.terrors), 0)

    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Woods"], 2)
    self.assertEqual(monster_counts["cup"], 5)
    self.assertEqual(self.state.ancient_one.doom, 0)
    for idx in surge.draw_monsters.monsters:
      self.assertEqual(self.state.monsters[idx].place.name, "Woods")

  def testInvalidInputFormat(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)

    with self.assertRaisesRegex(InvalidInput, "must be a map"):
      surge.resolve(self.state, 5)
    with self.assertRaisesRegex(InvalidInput, "must be a map with one"):
      surge.resolve(self.state, {"Woods": 5, "Square": 1, "WitchHouse": 0})
    with self.assertRaisesRegex(InvalidInput, "must be a map of"):
      surge.resolve(self.state, {5: "Woods"})
    with self.assertRaisesRegex(InvalidInput, "map.*integer"):
      surge.resolve(self.state, {"Woods": "5"})
    self.assertFalse(surge.is_resolved())

  def testInvalidInput(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)

    with self.assertRaisesRegex(InvalidMove, "Invalid.*Isle"):
      surge.resolve(self.state, {"Isle": 0})
    self.assertEqual(surge.pending, {})
    with self.assertRaisesRegex(InvalidMove, "Invalid monster"):
      surge.resolve(self.state, {"WitchHouse": 6})
    self.assertEqual(surge.pending, {})
    surge.resolve(self.state, {"Woods": 5})
    surge.resolve(self.state, {"Square": 5})
    surge.resolve(self.state, {"WitchHouse": 5})
    self.assertEqual(surge.pending, {"WitchHouse": [5], "Woods": [], "Square": []})

  def testReset(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)

    surge.resolve(self.state, {"Woods": 5})
    surge.resolve(self.state, {"Square": 1})
    surge.resolve(self.state, {"WitchHouse": 0})
    self.assertEqual(surge.pending, {"WitchHouse": [0], "Woods": [5], "Square": [1]})
    surge.resolve(self.state, "reset")
    self.assertEqual(surge.pending, {})

  def testUndo(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)

    surge.resolve(self.state, {"Woods": 5})
    surge.resolve(self.state, {"Square": 1})
    surge.resolve(self.state, {"Square": 5})
    surge.resolve(self.state, {"cup": 1})
    self.assertEqual(surge.pending, {"Woods": [], "Square": [5]})

  def testInvalidConfirmation(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)

    surge.resolve(self.state, {"Woods": 5})
    surge.resolve(self.state, {"Square": 1})
    self.assertEqual(surge.pending, {"Woods": [5], "Square": [1]})
    with self.assertRaisesRegex(InvalidMove, "Place 3 monsters on gates"):
      surge.resolve(self.state, "confirm")

    surge.resolve(self.state, {"Woods": 1})
    surge.resolve(self.state, {"Woods": 0})
    self.assertEqual(surge.pending, {"Woods": [5, 1, 0], "Square": []})
    with self.assertRaisesRegex(InvalidMove, "maximum of 1"):
      surge.resolve(self.state, "confirm")

  def testMoreGatesThanCharacters(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(surge.draw_monsters.count, 3)  # Number of gates
    self.assertCountEqual(surge.open_gates, ["Woods", "WitchHouse", "Square"])
    self.assertEqual(surge.max_count, 1)
    self.assertEqual(surge.min_count, 1)
    self.assertEqual(surge.steps_remaining, 0)
    self.assertEqual(surge.to_spawn, [0, 1, 5])

    surge.resolve(self.state, {"Woods": 0})
    surge.resolve(self.state, {"Square": 1})
    surge.resolve(self.state, {"WitchHouse": 5})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["cup"], 4)
    self.assertEqual(self.state.monsters[0].place.name, "Woods")
    self.assertEqual(self.state.monsters[1].place.name, "Square")
    self.assertEqual(self.state.monsters[5].place.name, "WitchHouse")
    self.assertEqual(self.state.ancient_one.doom, 0)

  def testNotEnoughGatesForAllMonsters(self):
    # Total of four open gates
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["Isle"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.places["Cave"].gate = gates.Gate("Pluto", 2, -2, "circle")
    # And four monsters on the board
    self.state.monsters[2].place = self.state.places["Square"]
    self.state.monsters[3].place = self.state.places["Isle"]
    self.state.monsters[4].place = self.state.places["Cave"]
    self.state.monsters[6].place = self.state.places["Woods"]
    self.state.monsters.append(monsters.Cultist())  # Add one more to make sure we have enough.
    self.state.monsters[-1].place = self.state.monster_cup
    self.state.event_stack.append(OpenGate("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5, 7])):
      surge = self.resolve_to_choice(MonsterSpawnChoice)

    self.assertCountEqual(surge.open_gates, ["Woods", "Isle", "Square", "Cave"])
    self.assertEqual(surge.draw_monsters.count, 4)  # Number of gates
    self.assertEqual(surge.spawn_count, 1)
    self.assertEqual(surge.max_count, 1)
    self.assertEqual(surge.min_count, 0)
    self.assertEqual(surge.steps_remaining, 0)
    self.assertEqual(surge.to_spawn, [0, 1, 5, 7])
    self.assertEqual(surge.outskirts_count, 3)

    surge.resolve(self.state, {"Woods": 1})
    surge.resolve(self.state, {"Outskirts": 0})
    surge.resolve(self.state, {"Outskirts": 5})
    surge.resolve(self.state, {"Outskirts": 7})
    surge.resolve(self.state, "confirm")
    self.assertTrue(surge.is_resolved())
    self.resolve_until_done()
    self.assertEqual(self.state.ancient_one.doom, 0)

  def testUnevenGatesAndCharacters(self):
    self.state.characters.append(characters.Character("C", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["C"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]
    self.state.characters.append(characters.Character("D", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["D"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]

    self.state.places["Isle"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(surge.draw_monsters.count, 4)
    self.assertEqual(surge.steps_remaining, 0)
    surge.to_spawn = [0, 1, 5, 6]

    surge.resolve(self.state, {"Woods": 5})
    surge.resolve(self.state, {"Woods": 1})
    surge.resolve(self.state, {"WitchHouse": 0})
    surge.resolve(self.state, {"WitchHouse": 6})
    with self.assertRaisesRegex(InvalidMove, "minimum of 1"):
      surge.resolve(self.state, "confirm")
    surge.resolve(self.state, {"Isle": 1})
    with self.assertRaisesRegex(InvalidMove, "place 2 monsters on \\[Woods\\]"):
      surge.resolve(self.state, "confirm")
    surge.resolve(self.state, {"Woods": 0})
    surge.resolve(self.state, {"Woods": 6})
    with self.assertRaisesRegex(InvalidMove, "maximum of 2"):
      surge.resolve(self.state, "confirm")

    self.assertFalse(surge.is_resolved())
    surge.resolve(self.state, {"Woods": 1})
    surge.resolve(self.state, {"Isle": 0})
    surge.resolve(self.state, {"WitchHouse": 6})
    self.assertEqual(surge.pending, {"Woods": [5, 1], "Isle": [0], "WitchHouse": [6]})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()
    self.assertEqual(self.state.monsters[0].place.name, "Isle")
    self.assertEqual(self.state.monsters[1].place.name, "Woods")
    self.assertEqual(self.state.monsters[5].place.name, "Woods")
    self.assertEqual(self.state.monsters[6].place.name, "WitchHouse")
    self.assertEqual(self.state.ancient_one.doom, 0)

  def testAutoOutskirts(self):
    # Add 4 monsters to the outskirts.
    outskirt_monsters = [
        monsters.Cultist(), monsters.Maniac(), monsters.Vampire(), monsters.Witch(),
    ]
    self.state.monsters.extend(outskirt_monsters)
    for monster in outskirt_monsters:
      monster.place = self.state.places["Outskirts"]
    # Add 5 monsters to the board.
    board_monsters = [
        monsters.Cultist(), monsters.Ghost(), monsters.Maniac(), monsters.Ghost(), monsters.Witch(),
    ]
    for monster in board_monsters:
      monster.place = self.state.places["Square"]
    self.state.monsters.extend(board_monsters)

    self.assertEqual(self.state.monster_limit(), 5)
    self.assertEqual(self.state.outskirts_limit(), 6)

    self.state.event_stack.append(OpenGate("Woods"))
    self.resolve_until_done()

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 6)
    self.assertEqual(counts["Square"], 5)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 5)
    self.assertEqual(self.state.terror, 0)
    self.assertEqual(self.state.ancient_one.doom, 0)

  def testSendToOutskirts(self):
    # Add 4 monsters to the outskirts.
    outskirt_monsters = [
        monsters.Cultist(), monsters.Maniac(), monsters.Vampire(), monsters.Witch(),
    ]
    self.state.monsters.extend(outskirt_monsters)
    for monster in outskirt_monsters:
      monster.place = self.state.places["Outskirts"]
    # Add 4 monsters to the board.
    board_monsters = [
        monsters.Cultist(), monsters.Ghost(), monsters.Maniac(), monsters.Ghost(),
    ]
    for monster in board_monsters:
      monster.place = self.state.places["Square"]
    self.state.monsters.extend(board_monsters)

    self.assertEqual(self.state.monster_limit(), 5)
    self.assertEqual(self.state.outskirts_limit(), 6)

    self.state.event_stack.append(OpenGate("Woods"))
    surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(surge.draw_monsters.count, 2)
    self.assertEqual(surge.spawn_count, 1)
    self.assertEqual(surge.outskirts_count, 1)
    self.assertEqual(surge.min_count, 1)
    self.assertEqual(surge.max_count, 1)
    self.assertEqual(surge.steps_remaining, 0)
    surge.to_spawn = [0, 1]

    surge.resolve(self.state, {"Woods": 0})
    surge.resolve(self.state, {"Woods": 1})
    with self.assertRaisesRegex(InvalidMove, "1 in the outskirts"):
      surge.resolve(self.state, "confirm")
    surge.resolve(self.state, "reset")
    surge.resolve(self.state, {"Outskirts": 1})
    with self.assertRaisesRegex(InvalidMove, "1 in the outskirts"):
      surge.resolve(self.state, "confirm")

    surge.resolve(self.state, {"Woods": 0})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 5)
    self.assertEqual(counts["Square"], 4)
    self.assertEqual(counts["Woods"], 1)
    self.assertEqual(counts["cup"], 5)
    self.assertEqual(self.state.terror, 0)
    self.assertEqual(self.state.ancient_one.doom, 0)

  def testAllToCup(self):
    self.state.allies.extend([assets.Dog(), assets.Thief()])
    # Add 5 monsters to the outskirts.
    outskirt_monsters = [
        monsters.Cultist(), monsters.Maniac(), monsters.Ghost(), monsters.Witch(), monsters.Ghoul(),
    ]
    self.state.monsters.extend(outskirt_monsters)
    for monster in outskirt_monsters:
      monster.place = self.state.places["Outskirts"]
    # Add 5 monsters to the board.
    board_monsters = [
        monsters.Cultist(), monsters.Ghost(), monsters.Maniac(), monsters.Ghost(), monsters.Witch(),
    ]
    for monster in board_monsters:
      monster.place = self.state.places["Square"]
    self.state.monsters.extend(board_monsters)

    self.state.event_stack.append(OpenGate("Woods"))
    self.resolve_until_done()

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 0)
    self.assertEqual(counts["Square"], 5)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 12)
    self.assertEqual(self.state.terror, 1)
    self.assertEqual(len(self.state.allies), 1)

  def testOnlyCupAndOutskirts(self):
    # Add 5 monsters to the outskirts.
    outskirt_monsters = [monsters.Maniac(), monsters.Ghost(), monsters.Witch(), monsters.Ghoul()]
    self.state.monsters.extend(outskirt_monsters)
    for monster in outskirt_monsters:
      monster.place = self.state.places["Outskirts"]
    # Add 5 monsters to the board.
    board_monsters = [
        monsters.Cultist(), monsters.Ghost(), monsters.Maniac(), monsters.Ghost(), monsters.Witch(),
    ]
    for monster in board_monsters:
      monster.place = self.state.places["Square"]
    self.state.monsters.extend(board_monsters)

    self.state.places["Isle"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.places["Society"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(OpenGate("Woods"))
    surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(surge.draw_monsters.count, 4)
    self.assertEqual(surge.spawn_count, 0)
    self.assertEqual(surge.outskirts_count, 3)
    self.assertEqual(surge.min_count, 0)
    self.assertEqual(surge.max_count, 0)
    self.assertEqual(surge.steps_remaining, 1)
    surge.to_spawn = [0, 1, 2, 3]

    surge.resolve(self.state, {"Outskirts": 1})
    surge.resolve(self.state, {"Outskirts": 2})
    surge.resolve(self.state, {"Outskirts": 3})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 1)
    self.assertEqual(counts["Square"], 5)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 10)
    self.assertEqual(self.state.terror, 1)
    self.assertEqual(self.state.monsters[0].place.name, "Outskirts")

  def testSomeMonstersToEach(self):
    # There are a total of 6 characters
    for name in ["C", "D", "E", "F"]:
      self.state.characters.append(characters.Character(name, 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
      self.state.all_characters[name] = self.state.characters[-1]
      self.state.characters[-1].place = self.state.places["Square"]

    # Put one monster in the outskirts
    self.state.monsters.append(monsters.Cultist())
    self.state.monsters[-1].place = self.state.places["Outskirts"]

    # Put 7 monsters on the board
    for _ in range(7):
      self.state.monsters.append(monsters.Maniac())
      self.state.monsters[-1].place = self.state.places["WitchHouse"]

    self.state.event_stack.append(OpenGate("Woods"))
    surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(surge.draw_monsters.count, 6)
    self.assertEqual(surge.spawn_count, 2)
    self.assertEqual(surge.outskirts_count, 2)
    self.assertEqual(surge.min_count, 2)
    self.assertEqual(surge.max_count, 2)
    self.assertEqual(surge.steps_remaining, 1)
    surge.to_spawn = [1, 2, 3, 4, 5, 6]

    surge.resolve(self.state, {"Woods": 3})
    surge.resolve(self.state, {"Woods": 4})
    surge.resolve(self.state, {"Outskirts": 1})
    surge.resolve(self.state, {"Outskirts": 2})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()
    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 2)
    self.assertEqual(counts["WitchHouse"], 7)
    self.assertEqual(counts["Woods"], 2)
    self.assertEqual(counts["cup"], 4)
    self.assertEqual(self.state.terror, 1)
    self.assertEqual(self.state.monsters[1].place.name, "cup")
    self.assertEqual(self.state.monsters[5].place.name, "Outskirts")

  def testMultipleClears(self):
    # There are a total of 6 characters
    for name in ["C", "D", "E", "F"]:
      self.state.characters.append(characters.Character(name, 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
      self.state.all_characters[name] = self.state.characters[-1]
      self.state.characters[-1].place = self.state.places["Square"]

    # Put 9 monsters on the board
    for _ in range(9):
      self.state.monsters.append(monsters.Maniac())
      self.state.monsters[-1].place = self.state.places["WitchHouse"]

    self.state.event_stack.append(OpenGate("Woods"))
    surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(surge.draw_monsters.count, 6)
    self.assertEqual(surge.spawn_count, 0)
    self.assertEqual(surge.outskirts_count, 3)
    self.assertEqual(surge.min_count, 0)
    self.assertEqual(surge.max_count, 0)
    self.assertEqual(surge.steps_remaining, 1)
    surge.to_spawn = [1, 2, 3, 4, 5, 6]

    surge.resolve(self.state, {"Outskirts": 1})
    surge.resolve(self.state, {"Outskirts": 3})
    surge.resolve(self.state, {"Outskirts": 4})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 0)
    self.assertEqual(counts["WitchHouse"], 9)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 7)
    self.assertEqual(self.state.terror, 2)

  def testMonsterSurgeOnScientist(self):
    self.state.characters.append(characters.Scientist())
    self.state.all_characters["Scientist"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Woods"]

    self.state.event_stack.append(OpenGate("Woods"))
    self.resolve_until_done()  # Surge is prevented completely.
    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 0)
    self.assertEqual(counts["WitchHouse"], 0)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 7)
    self.assertEqual(self.state.terror, 0)

  def testMonsterSurgeWithScientistOnGate(self):
    self.state.characters.append(characters.Scientist())
    self.state.all_characters["Scientist"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]

    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["Society"].gate = gates.Gate("Pluto", 1, -2, "circle")

    self.state.event_stack.append(OpenGate("Woods"))
    surge = self.resolve_to_choice(MonsterSpawnChoice)
    self.assertEqual(len(surge.to_spawn), 3)  # Number of gates
    self.assertEqual(surge.spawn_count, 3)
    self.assertEqual(surge.outskirts_count, 0)
    self.assertEqual(surge.min_count, 1)
    self.assertEqual(surge.max_count, 2)
    self.assertEqual(surge.steps_remaining, 0)
    surge.to_spawn = [1, 2, 3]

    surge.resolve(self.state, {"Woods": 1})
    surge.resolve(self.state, {"Woods": 2})
    surge.resolve(self.state, {"Society": 3})
    surge.resolve(self.state, "confirm")
    self.resolve_until_done()
    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 0)
    self.assertEqual(counts["Society"], 1)
    self.assertEqual(counts["Woods"], 2)
    self.assertEqual(counts["cup"], 4)
    self.assertEqual(self.state.terror, 0)


class MonsterSpawnCountTest(unittest.TestCase):

  def testCounts(self):
    test_cases = [
        {
            "num_gates": 2, "num_chars": 3, "on_board": 3, "in_outskirts": 0,
            "board": 3, "outskirts": 0, "steps": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 3, "in_outskirts": 5,
            "board": 3, "outskirts": 0, "steps": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 6, "in_outskirts": 0,
            "board": 0, "outskirts": 3, "steps": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 5, "in_outskirts": 0,
            "board": 1, "outskirts": 2, "steps": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 5, "in_outskirts": 4,
            "board": 1, "outskirts": 2, "steps": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 5, "in_outskirts": 5,
            "board": 1, "outskirts": 1, "steps": 1,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 6, "in_outskirts": 2,
            "monster_limit": float("inf"), "board": 3, "outskirts": 0, "steps": 0,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 3, "in_outskirts": 0,
            "board": 3, "outskirts": 1, "steps": 0,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 5, "in_outskirts": 0,
            "board": 1, "outskirts": 3, "steps": 0,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 5, "in_outskirts": 4,
            "board": 1, "outskirts": 2, "steps": 1,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 5, "in_outskirts": 4,
            "monster_limit": float("inf"), "board": 4, "outskirts": 0, "steps": 0,
        },
        {
            "num_gates": 4, "num_chars": 7, "on_board": 9, "in_outskirts": 0,
            "board": 1, "outskirts": 2, "steps": 2,
        },
        {
            "num_gates": 4, "num_chars": 7, "on_board": 9, "in_outskirts": 1,
            "board": 1, "outskirts": 1, "steps": 3,
        },
        {
            "num_gates": 4, "num_chars": 8, "on_board": 11, "in_outskirts": 0,
            "board": 0, "outskirts": 1, "steps": 7,
        },
    ]

    for test_case in test_cases:
      with self.subTest(**test_case):
        num_gates, num_chars = test_case["num_gates"], test_case["num_chars"]
        on_board, in_outskirts = test_case["on_board"], test_case["in_outskirts"]
        monster_limit = test_case.get("monster_limit", 3 + num_chars)
        outskirts_limit = 8 - num_chars
        expected_board, expected_outskirts = test_case["board"], test_case["outskirts"]
        expected_additional_steps = test_case["steps"]

        board, outskirts, steps = MonsterSpawnChoice.spawn_counts(
            max(num_gates, num_chars), on_board, in_outskirts, monster_limit, outskirts_limit,
        )

        self.assertEqual(board, expected_board)
        self.assertEqual(outskirts, expected_outskirts)
        self.assertEqual(steps, expected_additional_steps)


class CloseGateTest(EventTest):

  def setUp(self):
    super().setUp()
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
      seal_choice = self.resolve_to_choice(SpendChoice)
    seal_choice.resolve(self.state, "No")
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
      seal_choice = self.resolve_to_choice(SpendChoice)
    seal_choice.resolve(self.state, "No")
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
      choice = self.resolve_to_choice(SpendChoice)
      choice.resolve(self.state, "Pass")
    seal_choice = self.resolve_to_choice(SpendChoice)
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
      choice = self.resolve_to_choice(SpendChoice)
      choice.resolve(self.state, "Pass")
    seal_choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 5, seal_choice)
    self.assertEqual(seal_choice.choices[0], "Yes")
    seal_choice.resolve(self.state, "Yes")
    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertFalse(self.square.gate)
    self.assertTrue(self.square.sealed)
    self.assertEqual(self.char.clues, 1)

  def testCloseChoiceCancelled(self):
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)
    self.char.possessions.append(Canceller(MultipleChoice))

    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertTrue(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(close.choice.is_cancelled())
    self.assertFalse(close.closed)

  def testCloseCheckCancelled(self):
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)
    self.char.possessions.append(Canceller(Check))

    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertTrue(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(close.check.is_cancelled())
    self.assertFalse(close.closed)

  def testCloseChosenGate(self):
    self.char.clues = 5
    self.char.place = self.state.places["Woods"]
    self.state.places["Woods"].gate = self.state.gates.popleft()
    choice = GateChoice(self.char, "choose")
    close = CloseGate(self.char, choice, can_take=True, can_seal=True)
    self.state.event_stack.append(Sequence([choice, close], self.char))
    gate_choice = self.resolve_to_choice(GateChoice)

    self.assertCountEqual(gate_choice.choices, ["Square", "Woods"])
    gate_choice.resolve(self.state, "Square")
    seal_choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 5, seal_choice)
    seal_choice.resolve(self.state, "Yes")
    self.resolve_until_done()

    self.assertIsNone(self.state.places["Square"].gate)
    self.assertIsNotNone(self.state.places["Woods"].gate)
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(close.sealed)
    self.assertTrue(self.state.places["Square"].sealed)

  def testCannotTakeOrSealGate(self):
    self.char.clues = 5
    self.char.place = self.state.places["Woods"]
    close = CloseGate(self.char, "Square", can_take=False, can_seal=False)
    self.state.event_stack.append(close)

    self.resolve_until_done()

    self.assertIsNone(self.state.places["Square"].gate)
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(self.char.clues, 5)
    self.assertFalse(close.sealed)
    self.assertFalse(self.state.places["Square"].sealed)

  def testCanTakeButCannotSeal(self):
    self.char.clues = 5
    self.char.place = self.state.places["Woods"]
    close = CloseGate(self.char, "Square", can_take=True, can_seal=False)
    self.state.event_stack.append(close)

    self.resolve_until_done()

    self.assertIsNone(self.state.places["Square"].gate)
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.clues, 5)
    self.assertFalse(close.sealed)
    self.assertFalse(self.state.places["Square"].sealed)

  def testCanSealButCannotTake(self):
    self.char.clues = 5
    self.char.place = self.state.places["Woods"]
    close = CloseGate(self.char, "Square", can_take=False, can_seal=True)
    self.state.event_stack.append(close)

    seal_choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 5, seal_choice)
    seal_choice.resolve(self.state, "Yes")
    self.resolve_until_done()

    self.assertIsNone(self.state.places["Square"].gate)
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(close.sealed)
    self.assertTrue(self.state.places["Square"].sealed)

  def testMonstersDisappearWhenClosed(self):
    self.state.monsters.clear()
    self.state.monsters.extend([
        monsters.Ghoul(), monsters.Pinata(), monsters.Ghoul(), monsters.Ghoul(),
    ])
    self.state.monsters[0].place = self.state.places["Uptown"]  # hex
    self.state.monsters[1].place = self.state.places["Sky"]  # circle
    self.state.monsters[2].place = self.state.places["Outskirts"]  # hex
    self.state.monsters[3].place = None  # representing a monster in someone's trophies or the box
    # close a hex gate
    close = CloseGate(self.char, "Square", can_take=False, can_seal=False)
    self.state.event_stack.append(close)
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "cup")
    self.assertEqual(self.state.monsters[1].place.name, "Sky")  # not a hex monster
    self.assertEqual(self.state.monsters[2].place.name, "cup")  # outskirts monsters disappear too
    self.assertIsNone(self.state.monsters[3].place)

  def testMonstersDisappearFromSkyWhenClosed(self):
    self.state.monsters.clear()
    self.state.monsters.extend([
        monsters.Ghoul(), monsters.Pinata(), monsters.Ghoul(), monsters.Pinata(),
    ])
    self.state.places["Square"].gate = self.state.gates.pop()  # circle gate
    self.state.monsters[0].place = self.state.places["Uptown"]  # hex
    self.state.monsters[1].place = self.state.places["Sky"]  # circle
    self.state.monsters[2].place = self.state.places["Outskirts"]  # hex
    self.state.monsters[3].place = None  # representing a monster in someone's trophies or the box
    close = CloseGate(self.char, "Square", can_take=False, can_seal=False)
    self.state.event_stack.append(close)
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Uptown")  # not a circle monster
    self.assertEqual(self.state.monsters[1].place.name, "cup")
    self.assertEqual(self.state.monsters[2].place.name, "Outskirts")  # not a circrle monster
    self.assertIsNone(self.state.monsters[3].place)

  def testSealChoiceCancelled(self):
    self.char.clues = 6
    close = CloseGate(self.char, "Square", can_take=True, can_seal=True)
    self.state.event_stack.append(close)
    self.char.possessions.append(Canceller(SpendChoice))

    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertIsNone(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 6)
    self.assertTrue(close.seal_choice.is_cancelled())
    self.assertFalse(close.sealed)


class SpawnClueTest(EventTest):

  def setUp(self):
    super().setUp()
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
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.state.event_stack.append(SpawnClue("Square"))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Buddy"])
    choice.resolve(self.state, "Buddy")
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 0)
    self.assertEqual(buddy.clues, 3)
    self.assertEqual(self.square.clues, 0)

  def testSpawnClueChoiceCancelled(self):
    self.char.place = self.square
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.square
    buddy.clues = 2
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)
    self.char.possessions.append(Canceller(MultipleChoice))

    self.state.event_stack.append(SpawnClue("Square"))
    self.resolve_until_done()

    self.assertEqual(self.char.clues, 1)
    self.assertEqual(buddy.clues, 2)
    self.assertEqual(self.square.clues, 0)


class MoveMonsterTest(EventTest):

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

  def testMovementDimensionsAndTypes(self):
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

  def testMonstersDontMoveFromPlayer(self):
    self.state.monsters.clear()
    self.state.monsters.extend([
        monsters.Cultist(), monsters.Ghost(), monsters.DimensionalShambler(), monsters.Ghoul(),
    ])

    for monster in self.state.monsters:
      monster.place = self.state.places["Rivertown"]
    self.char.place = self.state.places["Rivertown"]

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle", "moon"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Rivertown")
    self.assertEqual(self.state.monsters[1].place.name, "Rivertown")
    self.assertEqual(self.state.monsters[2].place.name, "Rivertown")
    self.assertEqual(self.state.monsters[3].place.name, "Rivertown")

  def testFastMonsterStopsMovingAtPlayer(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.DimensionalShambler())

    self.state.monsters[0].place = self.state.places["Rivertown"]
    self.char.place = self.state.places["FrenchHill"]

    move = MoveMonsters({"square"}, {"circle", "moon"})
    self.state.event_stack.append(move)
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "FrenchHill")
    move_fast = move.moves.events[0]
    self.assertTrue(move_fast.is_resolved())
    self.assertEqual(move_fast.destination.name, "FrenchHill")

  def testFlyingMonsterMovement(self):
    self.state.monsters.clear()
    self.state.monsters.extend([
        monsters.DreamFlier(),  # Slash
        monsters.Pinata(),  # Circle
        monsters.GiantInsect(),  # Circle
        monsters.FlameMatrix(),  # Star
        monsters.SubterraneanFlier(),  # Hex
        monsters.Pinata(),  # Circle
        monsters.DreamFlier(),  # Slash
    ])

    self.char.place = self.state.places["Merchant"]
    self.state.monsters[0].place = self.state.places["Merchant"]  # Next to player, will not move.
    self.state.monsters[1].place = self.state.places["Rivertown"]  # Will move to player (adjacent).
    self.state.monsters[2].place = self.state.places["Sky"]  # Will move to player from sky.
    self.state.monsters[3].place = self.state.places["Easttown"]  # Will move to sky.
    self.state.monsters[4].place = self.state.places["Cave"]  # Will not move (hex).
    self.state.monsters[5].place = self.state.places["Cave"]  # Will move to sky.
    self.state.monsters[6].place = self.state.places["Isle"]  # Will move to player.

    self.state.event_stack.append(MoveMonsters({"slash"}, {"circle", "star"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Merchant")
    self.assertEqual(self.state.monsters[1].place.name, "Merchant")
    self.assertEqual(self.state.monsters[2].place.name, "Merchant")
    self.assertEqual(self.state.monsters[3].place.name, "Sky")
    self.assertEqual(self.state.monsters[4].place.name, "Cave")
    self.assertEqual(self.state.monsters[5].place.name, "Sky")
    self.assertEqual(self.state.monsters[6].place.name, "Merchant")

  def testBreakTiesBasedOnSneak(self):
    self.state.monsters.clear()
    self.state.monsters.extend([monsters.DreamFlier(), monsters.Pinata(), monsters.GiantInsect()])

    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.place = self.state.places["Rivertown"]
    self.char.place = self.state.places["Downtown"]
    self.state.monsters[0].place = self.state.places["Merchant"]
    self.state.monsters[1].place = self.state.places["Northside"]
    self.state.monsters[2].place = self.state.places["Sky"]

    self.char.speed_sneak_slider = 2
    self.assertEqual(buddy.sneak(self.state), 1)
    self.assertEqual(self.char.sneak(self.state), 2)

    self.state.event_stack.append(MoveMonsters({"slash"}, {"circle", "star"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Rivertown")
    self.assertEqual(self.state.monsters[1].place.name, "Downtown")
    self.assertEqual(self.state.monsters[2].place.name, "Rivertown")

  def testFlyingMovementNobodyInStreets(self):
    self.state.monsters.clear()
    self.state.monsters.extend([monsters.DreamFlier(), monsters.Pinata()])
    self.state.monsters[0].place = self.state.places["Sky"]
    self.state.monsters[1].place = self.state.places["Isle"]
    self.char.place = self.state.places["Unnamable"]

    self.state.event_stack.append(MoveMonsters({"slash"}, {"circle", "star"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Sky")
    self.assertEqual(self.state.monsters[1].place.name, "Sky")

  def testBasicHoundMovement(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.Hound())
    self.state.monsters[0].place = self.state.places["Rivertown"]
    self.char.place = self.state.places["Newspaper"]

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Newspaper")

  def testHoundStaysInStreetIfNextToChar(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.Hound())
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.state.monsters[0].place = self.state.places["Rivertown"]
    buddy.place = self.state.places["Store"]
    self.char.place = self.state.places["Rivertown"]

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Rivertown")

  def testHoundMovementNoEligibleChars(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.Hound())
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.state.monsters[0].place = self.state.places["Rivertown"]
    buddy.place = self.state.places["Easttown"]
    self.char.place = self.state.places["Hospital"]

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Rivertown")

  def testHoundMovementBreakTies(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.Hound())
    self.state.monsters[0].place = self.state.places["Rivertown"]
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.place = self.state.places["Store"]
    self.char.place = self.state.places["Cave"]
    self.char.speed_sneak_slider = 2
    self.assertEqual(buddy.sneak(self.state), 1)
    self.assertEqual(self.char.sneak(self.state), 2)

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Store")

  def testHoundChoosesNearestChar(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.Hound())
    self.state.monsters[0].place = self.state.places["Easttown"]
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.place = self.state.places["Library"]  # 4 steps away
    self.char.place = self.state.places["Newspaper"]  # 3 steps away
    self.char.speed_sneak_slider = 2
    self.assertEqual(buddy.sneak(self.state), 1)
    self.assertEqual(self.char.sneak(self.state), 2)

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Newspaper")

  def testLandSquidMovement(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.LandSquid())
    self.state.monsters[0].place = self.state.places["Easttown"]
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.place = self.state.places["Library"]
    self.char.place = self.state.places["Newspaper"]

    self.state.event_stack.append(MoveMonsters({"triangle"}, {"hex"}))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Easttown")
    self.assertEqual(buddy.stamina, 4)
    self.assertEqual(self.char.stamina, 4)

    self.state.event_stack.append(MoveMonsters({"triangle"}, {"hex"}))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Easttown")
    self.assertEqual(buddy.stamina, 4)
    self.assertEqual(self.char.stamina, 4)

  def testLandSquidIgnoresOtherWorlds(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.LandSquid())
    self.state.monsters[0].place = self.state.places["Easttown"]
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.place = self.state.places["Square"]
    self.char.place = self.state.places["Dreamlands1"]

    self.state.event_stack.append(MoveMonsters({"triangle"}, {"hex"}))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Easttown")
    self.assertEqual(buddy.stamina, 4)
    self.assertEqual(self.char.stamina, 5)

  def testLandSquidAllCharactersInOtherWorlds(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.LandSquid())
    self.state.monsters[-1].idx = 0
    self.state.monsters[-1].place = self.state.places["Isle"]
    self.char.place = self.state.places["Another Dimension1"]
    self.state.event_stack.append(events.MoveMonsters({"hex"}, {"slash", "triangle", "star"}))
    # Assertions are made in resolve_until_done() that make sure a sequence with no events will
    # be resolved correctly and not corrupt the triggers stack.
    self.resolve_until_done()

  def testLandSquidMovementUnconscious(self):
    self.state.monsters.clear()
    self.state.monsters.append(monsters.LandSquid())
    self.state.monsters[0].place = self.state.places["Easttown"]
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.place = self.state.places["Library"]
    self.char.place = self.state.places["Newspaper"]
    self.char.stamina = 1

    self.state.event_stack.append(MoveMonsters({"triangle"}, {"hex"}))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      lose_choice = self.resolve_to_choice(ItemLossChoice)
    lose_choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "Easttown")
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")
    # Validate that even though the first player went unconscious, second player also lost stamina.
    self.assertEqual(buddy.stamina, 4)

  def testOneMovementCancelled(self):
    self.state.monsters.clear()
    self.state.monsters.extend([
        monsters.Cultist(), monsters.Maniac(), monsters.Maniac(), monsters.Witch(),
    ])

    for monster in self.state.monsters:
      monster.place = self.state.places["Rivertown"]

    move = MoveMonsters({"square"}, {"circle", "moon"})
    self.state.event_stack.append(move)
    self.char.possessions.append(Canceller(MoveMonster, 2))
    self.resolve_until_done()

    self.assertTrue(move.is_resolved())
    self.assertTrue(move.moves.is_resolved())
    self.assertFalse(move.moves.events[2].is_resolved())
    self.assertTrue(move.moves.events[2].is_cancelled())
    self.assertEqual(self.state.monsters[0].place.name, "Easttown")
    self.assertEqual(self.state.monsters[1].place.name, "Easttown")
    self.assertEqual(self.state.monsters[2].place.name, "Rivertown")
    self.assertEqual(self.state.monsters[3].place.name, "Easttown")

  def testMovementAfterSpawn(self):
    self.state.mythos.append(Mythos3())
    self.state.monsters.clear()
    shambler = monsters.DimensionalShambler()
    shambler.place = self.state.monster_cup
    self.state.monsters.append(shambler)

    self.state.event_stack.append(self.state.mythos[-1].create_event(self.state))
    self.resolve_until_done()

    # The monster will appear at the Square, but should immediately move after appearing.
    self.assertEqual(shambler.place.name, "Easttown")


class ReturnToCupTest(EventTest):

  def setUp(self):
    super().setUp()
    self.cultist = monsters.Cultist()
    self.maniac = monsters.Maniac()
    self.dream_flier = monsters.DreamFlier()
    self.zombie = monsters.Zombie()
    self.trophy = monsters.Zombie()
    self.furry_beast = monsters.FurryBeast()
    self.cultist.place = self.state.places["Southside"]
    self.maniac.place = self.state.places["Outskirts"]
    self.dream_flier.place = self.state.places["Sky"]
    self.furry_beast.place = self.state.places["Woods"]
    self.zombie.place = None
    self.trophy.place = None
    self.char.trophies.append(self.trophy)
    self.state.monsters.clear()
    self.state.monsters.extend([
        self.cultist, self.maniac, self.dream_flier, self.zombie, self.furry_beast, self.trophy
    ])

  def testReturnByName(self):
    ret = ReturnToCup(names={"Dream Flier", "Maniac", "Zombie"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 1)  # The outskirts don't count.

    self.assertEqual(self.dream_flier.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertIsNone(self.zombie.place)
    self.assertIsNone(self.trophy.place)
    self.assertIn(self.trophy, self.char.trophies)
    self.assertEqual(self.cultist.place.name, "Southside")

  def testReturnByLocation(self):
    ret = ReturnToCup(from_places={"Southside", "Woods"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 2)

    self.assertEqual(self.cultist.place, self.state.monster_cup)
    self.assertEqual(self.furry_beast.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")
    self.assertIsNone(self.zombie.place)
    self.assertIsNone(self.trophy.place)
    self.assertIn(self.trophy, self.char.trophies)

  def testReturnInStreets(self):
    ret = ReturnToCup(from_places={"streets"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 1)

    self.assertEqual(self.cultist.place, self.state.monster_cup)
    self.assertEqual(self.furry_beast.place.name, "Woods")
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")
    self.assertIsNone(self.trophy.place)
    self.assertIn(self.trophy, self.char.trophies)

  def testReturnInLocations(self):
    ret = ReturnToCup(from_places={"locations"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 1)

    self.assertEqual(self.cultist.place.name, "Southside")
    self.assertEqual(self.furry_beast.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")
    self.assertIsNone(self.trophy.place)
    self.assertIn(self.trophy, self.char.trophies)


class GlobalModifierTest(EventTest):

  def setUp(self):
    super().setUp()
    more_monsters = [monsters.Cultist(), monsters.Maniac()]
    for monster in more_monsters:
      monster.place = self.state.monster_cup
    self.state.monsters.extend(more_monsters)

  def testEnvironmentModifier(self):
    mythos = Mythos6()
    self.state.mythos.append(mythos)
    self.assertEqual(self.char.will(self.state), 1)
    self.state.event_stack.append(ActivateEnvironment(mythos))
    self.resolve_until_done()
    self.assertEqual(self.char.will(self.state), 0)

  def testEnvironmentModifierIgnoredInOtherWorld(self):
    mythos = Mythos6()
    self.state.mythos.append(mythos)
    self.char.place = self.state.places["Dreamlands1"]
    self.assertEqual(self.char.will(self.state), 1)
    self.state.event_stack.append(ActivateEnvironment(mythos))
    self.resolve_until_done()
    self.assertEqual(self.char.will(self.state), 1)

  def testReplaceEnvironment(self):
    mythos = Mythos6()
    headline = Mythos11()
    env = Mythos45()
    self.state.mythos.extend([env, headline, mythos])

    self.assertIsNone(self.state.environment)
    self.state.event_stack.append(mythos.create_event(self.state))
    self.resolve_until_done()
    self.assertEqual(self.state.environment, mythos)

    self.state.event_stack.append(headline.create_event(self.state))
    self.resolve_until_done()
    self.assertEqual(self.state.environment, mythos)

    self.state.event_stack.append(env.create_event(self.state))
    self.resolve_until_done()
    self.assertEqual(self.state.environment, env)

  def testEnvironmentActivationRemovesFromDeck(self):
    self.state.mythos.clear()
    self.state.mythos.extend([Mythos45(), Mythos6(), Mythos11(), ShuffleMythos()])
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()

    self.assertEqual(self.state.environment.name, "Mythos45")
    self.assertEqual(len(self.state.mythos), 3)
    self.assertNotIn("Mythos45", [card.name for card in self.state.mythos])

    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.environment.name, "Mythos6")
    self.assertIn("Mythos45", [card.name for card in self.state.mythos])
    self.assertNotIn("Mythos6", [card.name for card in self.state.mythos])


class EnvironmentTests(EventTest):

  def testMythos15Pass(self):
    self.state.environment = Mythos15()
    self.state.turn_phase = "movement"
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "Easttown")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertGreater(rand.call_count, 0)
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertIsNone(self.char.arrested_until)

  def testMythos15Fail(self):
    self.state.environment = Mythos15()
    self.state.turn_phase = "movement"
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "Easttown")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertGreater(rand.call_count, 0)
    self.assertEqual(self.char.place.name, "Police")
    self.assertTrue(self.char.arrested_until)

  def testMythos15NotInStreet(self):
    self.state.environment = Mythos15()
    self.state.turn_phase = "movement"
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 0)
    self.assertEqual(self.char.place.name, "Diner")
    self.assertIsNone(self.char.arrested_until)

  def testMythos15IgnoresDeputy(self):
    self.state.environment = Mythos15()
    self.state.turn_phase = "movement"
    self.state.event_stack.append(Movement(self.char))
    self.char.possessions.append(items.Deputy())
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "Easttown")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 0)
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertIsNone(self.char.arrested_until)

  def testMythos16(self):
    self.state.environment = Mythos16()
    self.char.possessions.append(items.SunkenCityRuby(0))
    self.state.unique.extend([items.SilverKey(0), items.OuterGodlyFlute(0)])
    self.char.dollars = 8
    self.advance_turn(1, "movement")
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, "Uptown")
    self.resolve_to_choice(CityMovement).resolve(self.state, "done")
    shop = self.resolve_to_choice(MultipleChoice)
    shop.resolve(self.state, "Yes")
    purchase = self.resolve_to_choice(MultipleChoice)
    self.spend("dollars", 8, purchase)
    purchase.resolve(self.state, "Flute")
    self.resolve_to_choice(MultipleChoice).resolve(self.state, "Nothing")
    self.resolve_until_done()

  def testMythos17Pass(self):
    self.state.environment = Mythos17()
    self.advance_turn(1, "movement")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "University")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testMythos17Fail(self):
    self.state.environment = Mythos17()
    self.advance_turn(1, "movement")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "University")
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testMythos35(self):
    et1 = monsters.ElderThing()
    et2 = monsters.ElderThing()
    et3 = monsters.ElderThing()
    other = monsters.Cultist()
    et1.place = self.state.monster_cup
    et2.place = self.state.places["Newspaper"]
    self.char.trophies.append(et3)
    self.char.trophies.append(other)

    self.state.mythos.appendleft(Mythos35())
    self.state.monsters.extend([et1, et2, et3, other])
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0])):
      self.advance_turn(1, "mythos")

    self.assertEqual(et1.place, self.state.monster_cup)
    self.assertEqual(et2.place.name, "Newspaper")
    self.assertEqual(et3.place.name, "Docks")
    self.assertListEqual(self.char.trophies, [other])

  def testMythos39(self):
    self.state.environment = Mythos39()
    gate = self.state.gates[0]
    self.char.place = self.state.places["Woods"]
    self.char.place.gate = gate
    gate.place = self.char.place
    self.char.clues = 5
    self.state.event_stack.append(GateCloseAttempt(self.char, "Woods"))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Close with fight")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Spend", "Pass"])
    choice.resolve(self.state, "Pass")
    self.resolve_until_done()

  def testMythos44(self):
    # Return fire vampires, no vampires can be spawned
    fm1 = monsters.FlameMatrix()
    fm2 = monsters.FlameMatrix()
    fm3 = monsters.FlameMatrix()
    self.state.monsters.extend([fm1, fm2, fm3])
    idxs = [idx for idx, mon in enumerate(self.state.monsters) if mon == fm1]
    fm1.place = self.state.monster_cup
    fm2.place = self.state.places["Woods"]
    self.char.trophies.append(fm3)
    self.state.mythos.appendleft(Mythos44())
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=idxs)):
      self.advance_turn(1, "encounter")

    self.assertEqual(fm1.place, self.state.monster_cup)
    self.assertEqual(fm2.place, self.state.monster_cup)
    self.assertIsNone(fm3.place)
    self.assertIn(fm3, self.char.trophies)
    self.assertFalse(self.state.get_override(fm1, "can_draw_to_board"))


class DrawMythosTest(EventTest):

  def testMythosShuffle(self):
    self.state.mythos.clear()
    self.state.mythos.extend([
        ShuffleMythos(), Mythos1(), Mythos2(), Mythos3(), Mythos4(), Mythos5(),
    ])
    draw = DrawMythosCard(self.char)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertTrue(draw.shuffled)
    card_names = [card.name for card in self.state.mythos]
    unshuffled_names = ["Mythos2", "Mythos3", "Mythos4", "Mythos5", "ShuffleMythos", "Mythos1"]
    self.assertCountEqual(card_names, unshuffled_names)
    self.assertNotEqual(card_names, unshuffled_names)  # NOTE: small chance of failing


class RumorTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.state.spells.extend(items.CreateSpells())
    self.char.place = self.state.places["Uptown"]
    self.state.monsters.clear()
    # Replace all monsters with stationary monsters so that none move during the mythos phase.
    self.state.monsters.extend([monsters.Ghost(), monsters.Ghost(), monsters.Warlock()])
    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
      monster.place = self.state.monster_cup

  def testActivateRumor13(self):
    self.state.mythos.append(Mythos13())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertTrue(self.state.rumor)
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.assertFalse(self.state.rumor.failed)
    self.assertNotIn(self.state.rumor, self.state.mythos)

  def testRumor13Progress(self):
    self.state.allies.extend(assets.CreateAllies()[:7])
    self.state.event_stack.append(IncreaseTerror(6))
    self.resolve_until_done()
    self.state.mythos.append(Mythos13())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.assertEqual(self.state.terror, 6)
    self.assertEqual(len(self.state.boxed_allies), 6)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.assertEqual(self.state.terror, 6)
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.state.boxed_allies), 6)
    self.assertFalse(self.state.rumor.failed)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[1])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.assertEqual(self.state.terror, 7)
    self.assertFalse(self.state.rumor.failed)
    self.assertEqual(len(self.state.boxed_allies), 7)
    self.assertFalse(self.state.allies)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.assertEqual(self.state.terror, 7)
    self.assertFalse(self.state.rumor.failed)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    self.assertFalse(self.state.allies)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[1])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.assertEqual(self.state.terror, 8)
    self.assertFalse(self.state.rumor.failed)
    self.assertEqual(len(self.state.boxed_allies), 7)
    self.assertFalse(self.state.allies)

  def testFailRumor13(self):
    rumor = Mythos13()
    self.state.mythos.append(rumor)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos13")
    self.state.event_stack.append(IncreaseTerror(9))
    self.resolve_until_done()

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[1])):
      # This turn starts the rumor, so you have to advance past the next mythos phase.
      self.advance_turn(self.state.turn_number+2, "upkeep")
    self.assertIsNone(self.state.rumor)
    self.assertTrue(rumor.failed)
    self.assertNotIn(rumor, self.state.other_globals)
    self.assertNotIn(rumor, self.state.mythos)

    self.assertEqual(self.char.bless_curse, -1)

  def testEndRumor13Choice(self):
    rumor = Mythos13()
    self.state.rumor = rumor
    self.state.turn_number = 1
    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["Rivertown"]
    self.char.trophies.append(self.state.gates.pop())
    self.char.trophies.append(self.state.gates.pop())
    self.char.trophies.append(self.state.gates.pop())
    self.state.event_stack.append(EncounterPhase(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.toggle_spend(0, self.char.trophies[0].handle, choice)
    self.toggle_spend(0, self.char.trophies[1].handle, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len([p for p in self.char.possessions if isinstance(p, items.Spell)]), 1)
    self.assertIsNone(self.state.rumor)
    self.assertEqual(self.char.bless_curse, 0)

  def testActivateRumor27(self):
    self.state.mythos.append(Mythos27())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()

    self.assertTrue(self.state.rumor)
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertEqual(self.state.rumor.progress, 6)
    self.assertFalse(self.state.rumor.failed)
    self.assertNotIn(self.state.rumor, self.state.mythos)

  def testRumor27Progress(self):
    self.state.places["Science"].sealed = True
    self.state.places["Roadhouse"].sealed = True

    self.state.mythos.append(Mythos27())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertEqual(self.state.rumor.progress, 6)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3, 3])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertEqual(self.state.rumor.progress, 6)
    self.assertFalse(self.state.rumor.failed)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[1, 2])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertEqual(self.state.rumor.progress, 8)
    self.assertFalse(self.state.rumor.failed)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3, 2])):
      self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertEqual(self.state.rumor.progress, 9)
    self.assertFalse(self.state.rumor.failed)

    self.assertTrue(self.state.places["Science"].sealed)
    self.assertTrue(self.state.places["Roadhouse"].sealed)

  def testFailRumor27(self):
    self.state.places["Science"].sealed = True
    self.state.places["Roadhouse"].sealed = True

    rumor = Mythos27()
    self.state.mythos.append(rumor)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.state.rumor.progress = 9

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3, 2])):
      # This turn starts the rumor, so you have to advance past the next mythos phase.
      self.advance_turn(self.state.turn_number+2, "upkeep")
    self.assertIsNone(self.state.rumor)
    self.assertTrue(rumor.failed)
    self.assertNotIn(rumor, self.state.other_globals)
    self.assertNotIn(rumor, self.state.mythos)

    self.assertFalse(self.state.places["Science"].sealed)
    self.assertFalse(self.state.places["Roadhouse"].sealed)

  def testEndRumor27Choice(self):
    rumor = Mythos27()
    rumor.progress = 3
    self.state.rumor = rumor
    self.state.turn_number = 1
    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["Easttown"]
    self.char.clues = 6
    self.state.event_stack.append(EncounterPhase(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 4, choice)
    with self.assertRaisesRegex(InvalidMove, "overspent 1 clues"):
      choice.resolve(self.state, "Spend")  # Cannot overspend
    self.spend("clues", -2, choice)
    choice.resolve(self.state, "Spend")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 4)
    self.assertEqual(self.state.rumor, rumor)
    self.assertEqual(rumor.progress, 1)

  def testEndRumor27(self):
    rumor = Mythos27()
    rumor.progress = 3
    self.state.rumor = rumor
    self.state.turn_number = 1
    self.state.turn_phase = "encounter"
    self.state.unique.extend([items.HolyWater(0), items.MagicLamp(0)])
    self.char.place = self.state.places["Easttown"]
    self.char.clues = 6
    self.state.event_stack.append(EncounterPhase(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 3, choice)
    choice.resolve(self.state, "Spend")
    self.resolve_until_done()
    self.assertIsNone(self.state.rumor)
    self.assertFalse(self.state.other_globals)
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(len(self.char.possessions), 1)

  def testActivateRumor59(self):
    self.state.mythos.append(Mythos59())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()

    self.assertTrue(self.state.rumor)
    self.assertEqual(self.state.rumor.name, "Mythos59")
    self.assertEqual(self.state.rumor.progress, 0)
    self.assertFalse(self.state.rumor.failed)
    self.assertNotIn(self.state.rumor, self.state.mythos)
    cultist = monsters.Cultist()
    warlock = monsters.Warlock()
    self.assertEqual(cultist.toughness(self.state, self.char), 3)
    self.assertEqual(warlock.toughness(self.state, self.char), 4)

  def testRumor59Progress(self):
    self.state.mythos.append(Mythos59())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos59")
    self.assertEqual(self.state.rumor.progress, 0)

    self.advance_turn(self.state.turn_number+1, "mythos")
    self.assertTrue(self.state.event_stack)
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos59")
    self.assertEqual(self.state.rumor.progress, 1)
    self.assertFalse(self.state.rumor.failed)

  def testFailRumor59(self):
    rumor = Mythos59()
    self.state.mythos.append(rumor)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos59")
    self.state.rumor.progress = 4

    self.advance_turn(self.state.turn_number+2, "upkeep")
    self.assertIsNone(self.state.rumor)
    self.assertTrue(rumor.failed)
    self.assertIn(rumor, self.state.other_globals)
    cultist = monsters.Cultist()
    self.assertEqual(cultist.toughness(self.state, self.char), 1)

  def testFailedRumor59(self):
    rumor = Mythos59()
    rumor.failed = True
    self.state.other_globals.append(rumor)
    self.state.mythos.extend([Mythos5(), Mythos11()])
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertIsNotNone(self.state.places["Square"].gate)
    self.assertIsNotNone(self.state.places["Cave"].gate)
    square_count = len([mon for mon in self.state.monsters if mon.place.name == "Square"])
    self.assertEqual(square_count, 1)

  def testEndRumor59Choice(self):
    rumor = Mythos59()
    rumor.progress = 3
    self.state.rumor = rumor
    self.state.turn_number = 1
    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["FrenchHill"]
    self.state.event_stack.append(EncounterPhase(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaisesRegex(InvalidMove, "at least 3 spells"):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.state.rumor, rumor)
    self.assertEqual(rumor.progress, 3)

  def testEndRumor59(self):
    rumor = Mythos59()
    rumor.progress = 3
    self.state.rumor = rumor
    self.state.turn_number = 1
    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["FrenchHill"]
    self.char.possessions.extend([
        items.Wither(0), items.Wither(1), items.FindGate(0), items.FindGate(1), items.Food(0),
    ])
    self.state.event_stack.append(EncounterPhase(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    discard_choice = self.resolve_to_choice(ItemCountChoice)
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      discard_choice.resolve(self.state, "Food0")
    self.choose_items(discard_choice, ["Wither0", "Wither1", "Find Gate1"])
    self.resolve_until_done()
    self.assertIsNone(self.state.rumor)
    self.assertFalse(self.state.other_globals)
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(len(self.char.possessions), 2)

  def testNoRumorProgressForFailedRumors(self):
    rumor59 = Mythos59()
    rumor59.failed = True
    rumor59.progress = 5
    self.state.other_globals.append(rumor59)
    rumor27 = Mythos27()
    self.state.mythos.append(rumor27)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertIn(rumor59, self.state.other_globals)
    rumor27.progress = 2

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.advance_turn(self.state.turn_number+2, "upkeep")

    self.assertEqual(rumor27.progress, 4)
    self.assertEqual(rumor59.progress, 5)
    self.assertEqual(len(self.state.other_globals), 1)

  def testCannotStartRumorWhenOneExists(self):
    self.state.rumor = Mythos27()
    self.state.mythos.append(Mythos59())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()

    self.assertTrue(self.state.rumor)
    self.assertEqual(self.state.rumor.name, "Mythos27")
    self.assertNotIn(self.state.rumor, self.state.mythos)
    self.assertEqual(self.state.mythos[-1].name, "Mythos59")
    self.assertEqual(self.state.mythos[-1].progress, 0)
    cultist = monsters.Cultist()
    self.assertEqual(cultist.toughness(self.state, self.char), 1)


class CityBonusTest(EventTest):
  def setUp(self):
    super().setUp()
    self.mythos = Mythos6()
    self.state.mythos.append(self.mythos)
    self.advance_turn(0, "mythos")
    self.resolve_until_done()
    self.assertEqual(self.mythos, self.state.environment)

  def testAppliesInCity(self):
    self.assertTrue(isinstance(self.char.place, places.CityPlace))
    bonus_check = Check(self.char, "sneak", -1)
    self.state.event_stack.append(bonus_check)
    self.resolve_until_done()
    self.assertEqual(len(bonus_check.dice.roll), 4 - self.char.speed_sneak_slider)
    penalty_check = Check(self.char, "will", 1)
    self.state.event_stack.append(penalty_check)
    self.resolve_until_done()
    self.assertEqual(len(penalty_check.dice.roll), 4 - self.char.fight_will_slider)

  def testDoesntApplyInOtherWorlds(self):
    self.char.place = self.state.places["Pluto2"]
    self.assertFalse(isinstance(self.char.place, places.CityPlace))
    bonus_check = Check(self.char, "sneak", 0)
    self.state.event_stack.append(bonus_check)
    self.resolve_until_done()
    self.assertEqual(len(bonus_check.dice.roll), 4 - self.char.speed_sneak_slider)
    penalty_check = Check(self.char, "will", 0)
    self.state.event_stack.append(penalty_check)
    self.resolve_until_done()
    self.assertEqual(len(penalty_check.dice.roll), 4 - self.char.fight_will_slider)


class ReleaseMonstersTest(EventTest):
  def testMonstersReleased(self):
    self.state.monsters = monsters.CreateMonsters()
    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
      monster.place = self.state.monster_cup
    mythos = Mythos23()
    self.state.mythos.append(mythos)
    self.advance_turn(1, "encounter")
    self.resolve_until_done()
    monsters_in_merchant = [mon for mon in self.state.monsters if mon.place.name == "Merchant"]
    self.assertTrue(len(monsters_in_merchant), 2)

  def testBoardIsFull(self):
    self.state.monsters = monsters.CreateMonsters()
    monster_limit = self.state.monster_limit()
    lodge = self.state.places["Lodge"]  # This is not a happy place

    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
      monster.place = lodge if idx < monster_limit - 2 else self.state.monster_cup
    mythos = Mythos23()
    self.state.mythos.appendleft(mythos)
    self.state.event_stack.append(Mythos(self.char))
    mock_ret1 = [monster_limit - 1]
    mock_ret2 = [monster_limit, monster_limit + 1]
    draws = mock_ret1, mock_ret2
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(side_effect=draws)):
      placement_choice = self.resolve_to_choice(MonsterSpawnChoice)
      placement_choice.resolve(self.state, {"Merchant": monster_limit})
      placement_choice.resolve(self.state, {"Outskirts": monster_limit+1})
      placement_choice.resolve(self.state, "confirm")
      self.resolve_until_done()


class ReturnMonstersTest(EventTest):
  def testMonstersReturned(self):
    mythos = Mythos5()
    self.state.mythos.append(mythos)
    monster = self.state.monsters[0]
    monster.place = self.state.places["Outskirts"]

    self.advance_turn(1, "movement")
    self.assertEqual(monster.place, self.state.monster_cup)


class Mythos7Test(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.mythos7 = None

  def drawMythos7(self):
    self.mythos7 = Mythos7()
    self.state.mythos.append(self.mythos7)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertIn(self.mythos7, self.state.other_globals)
    self.assertNotIn(self.mythos7, self.state.mythos)

  def testArrestedCharsReleased(self):
    self.state.event_stack.append(Arrested(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Police")
    self.assertEqual(self.char.arrested_until, 2)

    self.drawMythos7()

    self.assertIsNone(self.char.arrested_until)

  def testUnarrestedCharsUnaffected(self):
    self.char.place = self.state.places["Police"]
    self.state.event_stack.append(LoseTurn(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.lose_turn_until, 2)

    self.drawMythos7()

    self.assertEqual(self.char.lose_turn_until, 2)

  def testCantBeArrested(self):
    self.drawMythos7()
    place = self.char.place
    self.state.event_stack.append(Arrested(self.char))
    self.resolve_until_done()
    self.assertIsNone(self.char.arrested_until)
    self.assertEqual(self.char.place, place)

  def testCanBeArrestedLater(self):
    self.char.place = self.state.places["Rivertown"]
    self.drawMythos7()
    self.state.mythos.insert(0, Mythos15())
    self.advance_turn(self.state.turn_number + 2, "movement")
    self.assertNotIn(self.mythos7, self.state.other_globals)
    self.assertIn(self.mythos7, self.state.mythos)
    choice = self.resolve_to_choice(events.CityMovement)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Police")
    self.assertEqual(self.char.arrested_until, self.state.turn_number+2)


class Mythos8Test(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.mythos8 = Mythos8()
    self.state.mythos.append(self.mythos8)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.mythos8, self.state.environment)
    self.assertNotIn(self.mythos8, self.state.mythos)
    self.char.place = self.state.places["Rivertown"]
    self.advance_turn(self.state.turn_number, "movement")
    self.movement = self.resolve_to_choice(CityMovement)

  def testUseAliveLucky(self):
    self.assertEqual(self.char.place.name, self.mythos8.activity_location)
    self.movement.resolve(self.state, "done")
    m8_choice = self.resolve_to_choice(MultipleChoice)
    m8_choice.resolve(self.state, "Yes")
    rolls = [5, 5, 5, 1, 1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=rolls)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.clues, 3)

  def testUseAlive(self):
    self.assertEqual(self.char.place.name, self.mythos8.activity_location)
    self.movement.resolve(self.state, "done")
    m8_choice = self.resolve_to_choice(MultipleChoice)
    m8_choice.resolve(self.state, "Yes")
    rolls = [5, 1, 1, 1, 1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=rolls)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.clues, 3)

  def testUseDevoured(self):
    self.assertEqual(self.char.place.name, self.mythos8.activity_location)
    self.movement.resolve(self.state, "done")
    m8_choice = self.resolve_to_choice(MultipleChoice)
    m8_choice.resolve(self.state, "Yes")
    rolls = [1, 1, 1, 1, 1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=rolls)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)

  def testCantUseIfNotInRivertown(self):
    self.movement.resolve(self.state, "Uptown")
    end_turn = self.resolve_to_choice(CityMovement)
    end_turn.resolve(self.state, "done")


class Mythos14Test(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.mythos14 = Mythos14()
    self.state.mythos.append(self.mythos14)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.mythos14, self.state.environment)
    self.assertNotIn(self.mythos14, self.state.mythos)
    self.char.place = self.state.places["Northside"]
    self.advance_turn(self.state.turn_number, "movement")
    self.movement = self.resolve_to_choice(CityMovement)

  def testInsane(self):
    self.char.sanity = 1
    self.char.clues = 1
    self.movement.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      clues = self.resolve_to_choice(SpendChoice)
      self.assertEqual(self.char.clues, 2)
      clues.resolve(self.state, "Fail")
      loss = self.resolve_to_choice(ItemLossChoice)
    loss.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testNormal(self):
    self.char.sanity = 1
    self.char.fight_will_slider = 2
    self.assertEqual(self.char.clues, 0)
    self.movement.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      clues = self.resolve_to_choice(SpendChoice)
      clues.resolve(self.state, "Pass")
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Northside")
    self.assertEqual(self.char.clues, 1)


class Mythos18Test(EventTest):
  def setUp(self):
    super().setUp()
    self.mythos = Mythos18()
    self.state.mythos.append(self.mythos)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.char.sanity = 2

    specials = location_specials.CreateFixedEncounters()
    for location_name, fixed_encounters in specials.items():
      self.state.places[location_name].fixed_encounters.extend(fixed_encounters)
    self.state.places["Downtown"].encounters.extend(
        encounters.CreateEncounterCards()["Downtown"]
    )

  def testCanGainFromPsychology(self):
    self.char.possessions.append(abilities.Psychology())
    self.advance_turn(0, "upkeep")
    self.state.event_stack.append(SliderInput(self.char))
    psych = self.resolve_to_usable(0, "Psychology")
    self.state.event_stack.append(psych)
    char_choice = self.resolve_to_choice(MultipleChoice)
    char_choice.resolve(self.state, "Dummy")
    sliders = self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.sanity, 3)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testCanGainAtAsylum(self):
    self.char.dollars = 2
    self.char.place = self.state.places["Asylum"]
    self.advance_turn(0, "encounter")
    choice = self.resolve_to_choice(CardSpendChoice)
    choice.resolve(self.state, "Restore 1 Sanity")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.advance_turn(1, "encounter")
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Downtown Card", "Restore 1 Sanity", "Restore All Sanity"])
    self.spend("dollars", 2, choice)
    choice = self.resolve_to_choice(CardSpendChoice)
    choice.resolve(self.state, "Restore All Sanity")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)

  def testCantGainFromOthers(self):
    # TODO: Healing stone maybe shouldn't even be usable?
    self.char.possessions.append(items.HealingStone(0))
    self.advance_turn(0, "upkeep")
    self.state.event_stack.append(SliderInput(self.char))
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    sliders = self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.sanity, 2)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()
    self.state.event_stack.append(Gain(self.char, {"sanity": 3}))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testCanGainOtherStuff(self):
    self.state.event_stack.append(Gain(self.char, {"dollars": 1}))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)


class CloseLocationTest(EventTest):
  def setUp(self):
    super().setUp()
    self.store = self.state.places["Store"]
    self.shop = self.state.places["Shop"]
    self.shoppe = self.state.places["Shoppe"]
    self.char.possessions.append(items.SunkenCityRuby(0))
    self.char.place = self.store

    # Make sure there's enough monsters to draw twice
    matrix = monsters.FlameMatrix()
    matrix.place = self.state.monster_cup
    self.state.monsters.append(matrix)

    self.mythos = Mythos10()
    self.state.mythos.append(self.mythos)
    self.advance_turn(0, "mythos")
    self.resolve_until_done()
    self.assertEqual(self.store.closed_until, 2)
    self.assertEqual(self.shop.closed_until, 2)
    self.assertEqual(self.shoppe.closed_until, 2)
    self.assertIn(self.mythos, self.state.globals())
    self.assertNotIn(self.mythos, self.state.mythos)
    self.close_forever = False

  def tearDown(self):
    self.advance_turn(2, "movement")
    if self.close_forever:
      self.assertTrue(self.store.closed_until > 101)
    else:
      self.assertIsNone(self.store.closed_until)
    self.assertIsNone(self.shop.closed_until)
    self.assertIsNone(self.shoppe.closed_until)
    self.assertNotIn(self.mythos, self.state.globals())
    self.assertIn(self.mythos, self.state.mythos)
    choice = self.resolve_to_choice(CityMovement)
    if not self.close_forever:
      self.assertIn("Store", choice.choices)
    self.assertIn("Shop", choice.choices)
    self.assertIn("Shoppe", choice.choices)

  def testEvicted(self):
    self.advance_turn(1, "movement")
    self.assertEqual(self.char.place.name, "Rivertown")
    self.assertEqual(self.char.movement_points, 7)
    choice = self.resolve_to_choice(CityMovement)
    self.assertNotIn("Store", choice.choices)
    self.assertNotIn("Shop", choice.choices)
    self.assertNotIn("Shoppe", choice.choices)
    choice.resolve(self.state, "done")
    self.resolve_until_done()


class CloseStreetLocationTest(EventTest):
  def setUp(self):
    super().setUp()
    # Make sure there's enough monsters to draw twice
    matrix = monsters.FlameMatrix()
    matrix.place = self.state.monster_cup
    self.state.monsters.append(matrix)

    self.mythos = Mythos19()
    self.state.mythos.append(self.mythos)
    self.advance_turn(0, "mythos")
    self.resolve_until_done()
    self.merchant = self.state.places["Merchant"]
    self.assertEqual(self.merchant.closed_until, 2)
    self.assertIn(self.mythos, self.state.globals())

  def tearDown(self):
    self.advance_turn(2, "movement")
    self.assertIsNone(self.merchant.closed_until)
    self.assertNotIn(self.mythos, self.state.globals())

  def testCharacterStuckInStreets(self):
    self.char.place = self.merchant
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    self.assertEqual(choice.choices, ["Merchant"])
    choice.resolve(self.state, "done")

  def testCharacterCantMoveThrough(self):
    self.char.place = self.state.places["Northside"]
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    self.assertNotIn("Merchant", choice.choices)
    self.assertNotIn("University", choice.choices)
    self.assertEqual(self.char.movement_points, self.char.speed(self.state))
    choice.resolve(self.state, "done")

  def testEncounterSendsToStreets(self):
    self.char.place = self.state.places["Docks"]
    self.state.event_stack.append(encounters.Docks3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      choice = self.resolve_to_choice(MapChoice)
    self.assertListEqual(
        sorted(choice.choices),
        ["Downtown", "Isle", "Northside", "Rivertown", "University", "Unnamable"]
    )
    with self.assertRaises(InvalidMove):
      choice.resolve(self.state, "done")
    choice.resolve(self.state, "Unnamable")

  def testEncounterSendsToUnclosedStreets(self):
    self.state.event_stack.append(CloseLocation("Isle"))
    self.resolve_until_done()
    self.char.place = self.state.places["Docks"]
    self.assertTrue(self.state.places["Isle"].closed)
    self.state.event_stack.append(encounters.Docks3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      choice = self.resolve_to_choice(MapChoice)
    self.assertListEqual(
        sorted(choice.choices),
        ["Downtown", "Northside", "Rivertown", "University", "Unnamable"]
    )
    with self.assertRaises(InvalidMove):
      choice.resolve(self.state, "done")
    choice.resolve(self.state, "Unnamable")

  def testMonsterNotStuckInStreets(self):
    cultist = next(monster for monster in self.state.monsters if monster.name == "Cultist")
    cultist.place = self.merchant
    # Moon on white
    self.state.mythos.appendleft(Mythos5())
    self.advance_turn(1, "mythos")
    self.resolve_until_done()
    self.assertEqual(cultist.place.name, "Northside")


class ReturnAndIncreaseHeadlineTest(EventTest):
  def setUp(self):
    super().setUp()
    self.tentacle_trees = [monsters.TentacleTree() for _ in range(3)]
    self.state.monsters.extend(self.tentacle_trees)
    # But not in the cup so they can't be drawn
    self.mythos = Mythos22()
    self.assertTrue(isinstance(self.mythos, ReturnAndIncreaseHeadline))

  def drawMythos(self):
    self.state.mythos.append(self.mythos)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()

  def testNoMonstersReturned(self):
    self.drawMythos()
    self.assertEqual(self.state.terror, 0)

  def testOneMonsterReturned(self):
    self.tentacle_trees[0].place = self.state.places["Square"]
    self.drawMythos()
    self.assertEqual(self.state.terror, 1)
    self.assertEqual(self.tentacle_trees[0].place, self.state.monster_cup)

  def testTwoMonsterReturned(self):
    self.tentacle_trees[0].place = self.state.places["Square"]
    self.tentacle_trees[1].place = self.state.places["Woods"]
    self.drawMythos()
    self.assertEqual(self.state.terror, 1)
    self.assertEqual(self.tentacle_trees[0].place, self.state.monster_cup)
    self.assertEqual(self.tentacle_trees[1].place, self.state.monster_cup)

  def testNoMonstersReturnedFromOutskirts(self):
    self.tentacle_trees[0].place = self.state.places["Outskirts"]
    self.drawMythos()
    self.assertEqual(self.state.terror, 0)
    self.assertEqual(self.tentacle_trees[0].place.name, "Outskirts")


class Mythos38Test(EventTest):
  def testFewerCluesToSeal(self):
    self.state.environment = Mythos38()
    self.char.clues = 3
    place = "Woods"
    self.char.place = self.state.places[place]
    self.state.places[place].gate = gates.Gate("Dummy", 0, 0, "hex")
    self.state.event_stack.append(GateCloseAttempt(self.char, self.char.place.name))
    close_with = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(close_with.choices, ["Close with fight", "Close with lore", "Don't close"])
    close_with.resolve(self.state, "Close with fight")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      spend_choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(spend_choice.choices, ["Spend", "Pass"])
    spend_choice.resolve(self.state, "Pass")
    seal_choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(seal_choice.choices, ["Yes", "No"])
    self.spend("clues", 3, seal_choice)
    seal_choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertFalse(self.state.places[place].is_unstable(self.state))


class Mythos29Test(EventTest):
  def setUp(self):
    super().setUp()
    self.mythos = Mythos29()
    self.monster = monsters.Monster(
        "FakeMonster", "fast", "plus", {"evade": 0, "combat": 0}, {"combat": 1}, 1
    )
    self.monster.place = self.state.monster_cup
    self.state.monsters.append(self.monster)
    self.state.mythos.append(self.mythos)
    self.state.event_stack.append(Mythos(self.char))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[-1])):
      # Always draw FakeMonster
      self.resolve_until_done()

  def testInvestigatorsReceiveLessMovement(self):
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.movement_points, self.char.speed(self.state) - 1)

  def testFastMonstersMoveAsNormal(self):
    # Mythos ability doesn't happen until after monster movement, so it moved 2 after spawning
    self.assertEqual(self.monster.place.name, "Uptown")

    # Headline: plus moves on black
    self.state.mythos.append(Mythos5())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.monster.place.name, "Southside")
    self.assertEqual(self.monster.movement(self.state), "normal")


class Mythos42Test(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.mythos = Mythos42()
    self.state.mythos.append(self.mythos)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.mythos, self.state.environment)
    self.assertNotIn(self.mythos, self.state.mythos)

  def testCostIsZero(self):
    self.char.possessions.append(items.Voice(0))
    self.char.possessions.append(items.DreadCurse(0))
    self.advance_turn(0, "upkeep")
    self.assertEqual(self.char.sanity, 5)
    voice = self.resolve_to_usable(0, "Voice0")
    self.state.event_stack.append(voice)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      cast_choice = self.resolve_to_choice(MultipleChoice)
      cast_choice.resolve(self.state, "Voice")
      sliders = self.resolve_to_choice(SliderInput)
      sliders.resolve(self.state, "done", None)
      self.resolve_until_done()
      self.assertEqual(self.char.sanity, 5)

      self.state.event_stack.append(Combat(self.char, monsters.FormlessSpawn()))
      fight_evade = self.resolve_to_choice(FightOrEvadeChoice)
      fight_evade.resolve(self.state, "Fight")
      curse = self.resolve_to_usable(0, "Dread Curse0")
      self.state.event_stack.append(curse)
      cast_choice = self.resolve_to_choice(MultipleChoice)
      cast_choice.resolve(self.state, "Dread Curse")
      weapons = self.resolve_to_choice(CombatChoice)
      weapons.resolve(self.state, "done")
      self.resolve_until_done()
      self.assertEqual(self.char.sanity, 5)

  def testEnvironmentTakesPrecedence(self):
    # FAQ p. 10
    class Blight(GlobalEffect):
      def __init__(self):
        self.name = "TestEffect"

      def get_modifier(self, thing, attribute, state):
        if isinstance(thing, items.Spell) and attribute == "sanity_cost":
          return 1
        return 0

    self.state.other_globals.append(Blight())
    self.testCostIsZero()


class Mythos44Test(EventTest):

  def testReducesMovementPoints(self):
    self.assertEqual(self.char.speed(self.state), 4)
    self.state.environment = Mythos44()
    self.assertEqual(self.char.speed(self.state), 3)
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.movement_points, 3)


class Mythos51Test(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.mythos = Mythos51()
    self.state.mythos.append(self.mythos)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.mythos, self.state.environment)
    self.assertNotIn(self.mythos, self.state.mythos)

  def testCannotUse(self):
    self.char.possessions.append(items.Voice(0))
    self.char.possessions.append(items.DreadCurse(0))
    self.advance_turn(0, "upkeep")
    self.assertEqual(self.char.sanity, 5)
    sliders = self.resolve_to_choice(SliderInput)
    self.assertFalse(self.state.usables)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()
    self.state.event_stack.append(Combat(self.char, monsters.Cultist()))

    fight_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_evade.resolve(self.state, "Fight")
    weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.state.usables)
    weapons.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()


class Mythos55Test(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_number = 0
    self.state.turn_phase = "mythos"
    self.mythos = Mythos55()
    self.state.mythos.append(self.mythos)
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_until_done()
    self.assertEqual(self.mythos, self.state.environment)
    self.assertNotIn(self.mythos, self.state.mythos)

  def testUndeadIgnoredByRedSign(self):
    self.char.possessions.append(items.RedSign(0))
    self.char.possessions.append(items.EnchantedKnife(0))
    vampire = monsters.Vampire()
    self.assertEqual(vampire.toughness(self.state, self.char), 3)
    self.state.event_stack.append(Combat(self.char, vampire))
    fight_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_flee.resolve(self.state, "Fight")
    sign = self.resolve_to_usable(0, "Red Sign0")
    self.state.event_stack.append(sign)
    attr_to_cancel = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, attr_to_cancel)
    attr_to_cancel.resolve(self.state, "undead")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(vampire.has_attribute("undead", self.state, self.char))
    # TODO: Should the Red Sign undead cancelling get fed into the toughness calculation
    # self.assertEqual(vampire.toughness(self.state, self.char), 1)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 5, 1, 1])):
      weapons.resolve(self.state, "Enchanted Knife0")
      weapons.resolve(self.state, "done")
      self.resolve_until_done()
    self.assertEqual(vampire.toughness(self.state, self.char), 3)


class Mythos57Test(EventTest):
  def setUp(self):
    super().setUp()
    self.whiskey0 = items.Whiskey(0)
    self.whiskey1 = items.Whiskey(1)
    self.char.possessions.append(self.whiskey0)
    self.char.possessions.append(self.whiskey1)
    self.state.mythos.appendleft(Mythos57())

  def tearDown(self):
    self.assertEqual(self.state.places["Roadhouse"].closed_until, 2)

  def testLoseWhiskeyWhenArrested(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.advance_turn(1, "movement")
    self.assertFalse(self.char.possessions)
    self.assertEqual(self.char.place.name, "Police")
    self.assertEqual(self.char.arrested_until, 2)

  def testMultipleWhiskeyOneCheck(self):
    self.char.speed_sneak_slider -= 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1, ])):
      self.advance_turn(1, "movement")
    self.assertIsNone(self.char.arrested_until)
    self.assertListEqual(self.char.possessions, [self.whiskey0, self.whiskey1])


class Mythos58Test(EventTest):
  def setUp(self):
    super().setUp()
    self.spell = items.Voice(0)
    self.state.spells.append(self.spell)
    self.char.place = self.state.places["FrenchHill"]
    self.state.environment = Mythos58()
    self.advance_turn(0, "movement")
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, "done")
    deal = self.resolve_to_choice(events.MultipleChoice)
    deal.resolve(self.state, "Yes")

  def testWagerReward(self):
    self.char.sanity = 4
    rolls = [5, 5, 1, 1]
    self.assertEqual(self.char.sanity, len(rolls))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=rolls)):
      self.resolve_until_done()

    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)
    self.assertListEqual(self.char.possessions, [self.spell])

  def testDevoured(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)


class MythosPhaseTest(EventTest):

  def setUp(self):
    super().setUp()
    self.mythos = Mythos(self.char)
    self.state.event_stack.append(self.mythos)
    self.state.mythos.clear()
    self.state.mythos.append(Mythos6())

  def testMythos(self):
    self.resolve_until_done()
    self.assertTrue(self.mythos.is_resolved())
    self.assertTrue(self.mythos.action.is_resolved())

  def testCancelledEnvironment(self):
    self.char.possessions.append(Canceller(ActivateEnvironment))
    self.resolve_until_done()
    self.assertTrue(self.mythos.is_resolved())
    self.assertTrue(self.mythos.action.is_resolved())
    self.assertFalse(self.mythos.action.events[3].is_resolved())
    self.assertTrue(self.mythos.action.events[3].is_cancelled())

  def testCancelWholeMythos(self):
    self.char.possessions.append(Canceller(Sequence))
    self.resolve_until_done()
    self.assertTrue(self.mythos.is_resolved())
    self.assertFalse(self.mythos.action.is_resolved())
    self.assertTrue(self.mythos.action.is_cancelled())


if __name__ == "__main__":
  unittest.main()
