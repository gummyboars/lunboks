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
from eldritch import monsters
from eldritch.mythos import *
from eldritch import places
from eldritch.test_events import EventTest, Canceller


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

  def testOpenGateSpawnCancelled(self):
    self.assertEqual(self.state.characters[0].place.name, "Diner")
    self.assertEqual(self.state.characters[1].place.name, "Square")
    self.assertEqual(self.state.characters[2].place.name, "Square")
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Square"], 0)
    self.assertEqual(monster_counts["Woods"], 0)
    cup_count = monster_counts["cup"]
    self.state.characters[0].possessions.append(Canceller(SpawnGateMonster))

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
    surge = MonsterSurge("Woods")
    self.state.event_stack.append(surge)

    # With only one gate open, the surge does not present the user with a choice.
    self.resolve_until_done()
    self.assertEqual(len(surge.to_spawn), 2)  # Number of characters
    self.assertEqual(surge.open_gates, ["Woods"])
    self.assertEqual(surge.max_count, 2)
    self.assertEqual(surge.min_count, 2)

    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["Woods"], 2)
    self.assertEqual(monster_counts["cup"], 5)
    for idx in surge.to_spawn:
      self.assertEqual(self.state.monsters[idx].place.name, "Woods")

  def testInvalidInputFormat(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(MonsterSurge("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSurge)

    with self.assertRaises(AssertionError):
      surge.resolve(self.state, 5)
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {5: "Woods", 1: "Square", 0: "WitchHouse"})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": 5, "Square": 1, "WitchHouse": 0})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": ["5"], "Square": [1], "WitchHouse": [0]})
    self.assertFalse(surge.is_resolved())

  def testInvalidInput(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(MonsterSurge("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSurge)

    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [5, 1, 0], "Square": [1], "WitchHouse": [0]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [5], "Square": [1], "WitchHouse": [6]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [0, 1, 5]})

  def testMoreGatesThanCharacters(self):
    self.state.places["Square"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(MonsterSurge("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5])):
      surge = self.resolve_to_choice(MonsterSurge)
    self.assertEqual(len(surge.to_spawn), 3)  # Number of gates
    self.assertCountEqual(surge.open_gates, ["Woods", "WitchHouse", "Square"])
    self.assertEqual(surge.max_count, 1)
    self.assertEqual(surge.min_count, 1)
    self.assertEqual(surge.to_spawn, [0, 1, 5])

    surge.resolve(self.state, {"Woods": [0], "Square": [1], "WitchHouse": [5]})
    monster_counts = self.monstersByPlace()
    self.assertEqual(monster_counts["cup"], 4)
    self.assertEqual(self.state.monsters[0].place.name, "Woods")
    self.assertEqual(self.state.monsters[1].place.name, "Square")
    self.assertEqual(self.state.monsters[5].place.name, "WitchHouse")

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
    self.state.event_stack.append(MonsterSurge("Woods"))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[0, 1, 5, 7])):
      surge = self.resolve_to_choice(MonsterSurge)

    self.assertCountEqual(surge.open_gates, ["Woods", "Isle", "Square", "Cave"])
    self.assertEqual(len(surge.to_spawn), 4)  # Number of gates
    self.assertEqual(surge.spawn_count, 1)
    self.assertEqual(surge.max_count, 1)
    self.assertEqual(surge.min_count, 0)
    self.assertEqual(surge.to_spawn, [0, 1, 5, 7])
    self.assertEqual(surge.outskirts_count, 3)

    surge.resolve(self.state, {"Woods": [1], "Outskirts": [0, 5, 7]})
    self.assertTrue(surge.is_resolved())

  def testUnevenGatesAndCharacters(self):
    self.state.characters.append(characters.Character("C", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["C"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]
    self.state.characters.append(characters.Character("D", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square"))
    self.state.all_characters["D"] = self.state.characters[-1]
    self.state.characters[-1].place = self.state.places["Square"]

    self.state.places["Isle"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["WitchHouse"].gate = gates.Gate("Pluto", 1, -2, "circle")
    self.state.event_stack.append(MonsterSurge("Woods"))
    surge = self.resolve_to_choice(MonsterSurge)
    self.assertEqual(len(surge.to_spawn), 4)
    surge.to_spawn = [0, 1, 5, 6]

    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [5, 1], "WitchHouse": [0, 6]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [5], "Isle": [1], "WitchHouse": [6, 0]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [0, 1, 5, 6]})

    self.assertFalse(surge.is_resolved())
    surge.resolve(self.state, {"Woods": [5, 1], "Isle": [0], "WitchHouse": [6]})
    self.assertTrue(surge.is_resolved())
    self.assertEqual(self.state.monsters[0].place.name, "Isle")
    self.assertEqual(self.state.monsters[1].place.name, "Woods")
    self.assertEqual(self.state.monsters[5].place.name, "Woods")
    self.assertEqual(self.state.monsters[6].place.name, "WitchHouse")

  def testSendToOutskirts(self):
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

    self.state.event_stack.append(MonsterSurge("Woods"))
    surge = self.resolve_to_choice(MonsterSurge)
    self.assertEqual(len(surge.to_spawn), 2)
    self.assertEqual(surge.spawn_count, 0)
    self.assertEqual(surge.outskirts_count, 2)
    self.assertEqual(surge.min_count, 0)
    self.assertEqual(surge.max_count, 0)
    surge.to_spawn = [0, 1]

    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [0, 1]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [0], "Outskirts": [1]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Outskirts": [1]})

    surge.resolve(self.state, {"Outskirts": [0, 1]})

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 6)
    self.assertEqual(counts["Square"], 5)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 5)

  def testAllToCup(self):
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

    self.state.event_stack.append(MonsterSurge("Woods"))
    surge = self.resolve_to_choice(MonsterSurge)
    self.assertEqual(len(surge.to_spawn), 2)
    self.assertEqual(surge.spawn_count, 0)
    self.assertEqual(surge.outskirts_count, 0)
    self.assertEqual(surge.min_count, 0)
    self.assertEqual(surge.max_count, 0)
    surge.to_spawn = [0, 1]

    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Woods": [0, 1]})
    with self.assertRaises(AssertionError):
      surge.resolve(self.state, {"Outskirts": [0, 1]})

    surge.resolve(self.state, {})

    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 0)
    self.assertEqual(counts["Square"], 5)
    self.assertEqual(counts["Woods"], 0)
    self.assertEqual(counts["cup"], 12)

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

    self.state.event_stack.append(MonsterSurge("Woods"))
    surge = self.resolve_to_choice(MonsterSurge)
    self.assertEqual(len(surge.to_spawn), 6)
    self.assertEqual(surge.spawn_count, 2)
    self.assertEqual(surge.outskirts_count, 2)
    self.assertEqual(surge.min_count, 2)
    self.assertEqual(surge.max_count, 2)
    surge.to_spawn = [1, 2, 3, 4, 5, 6]

    surge.resolve(self.state, {"Woods": [3, 4], "Outskirts": [5, 6]})
    counts = self.monstersByPlace()
    self.assertEqual(counts["Outskirts"], 2)
    self.assertEqual(counts["WitchHouse"], 7)
    self.assertEqual(counts["Woods"], 2)
    self.assertEqual(counts["cup"], 4)


class MonsterSpawnCountTest(unittest.TestCase):

  def testCounts(self):
    test_cases = [
        {
            "num_gates": 2, "num_chars": 3, "on_board": 3, "in_outskirts": 0,
            "board": 3, "outskirts": 0, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 3, "in_outskirts": 5,
            "board": 3, "outskirts": 0, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 6, "in_outskirts": 0,
            "board": 0, "outskirts": 3, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 5, "in_outskirts": 0,
            "board": 1, "outskirts": 2, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 5, "in_outskirts": 4,
            "board": 1, "outskirts": 0, "cup": 2, "clears": 1,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 5, "in_outskirts": 5,
            "board": 1, "outskirts": 1, "cup": 1, "clears": 1,
        },
        {
            "num_gates": 2, "num_chars": 3, "on_board": 6, "in_outskirts": 2,
            "monster_limit": float("inf"), "board": 3, "outskirts": 0, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 3, "in_outskirts": 0,
            "board": 3, "outskirts": 1, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 5, "in_outskirts": 0,
            "board": 1, "outskirts": 3, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 5, "in_outskirts": 4,
            "board": 1, "outskirts": 1, "cup": 2, "clears": 1,
        },
        {
            "num_gates": 4, "num_chars": 3, "on_board": 5, "in_outskirts": 4,
            "monster_limit": float("inf"), "board": 4, "outskirts": 0, "cup": 0, "clears": 0,
        },
        {
            "num_gates": 4, "num_chars": 7, "on_board": 9, "in_outskirts": 0,
            "board": 1, "outskirts": 0, "cup": 6, "clears": 3,
        },
        {
            "num_gates": 4, "num_chars": 7, "on_board": 9, "in_outskirts": 1,
            "board": 1, "outskirts": 1, "cup": 5, "clears": 3,
        },
        {
            "num_gates": 4, "num_chars": 8, "on_board": 11, "in_outskirts": 0,
            "board": 0, "outskirts": 0, "cup": 8, "clears": 8,
        },
    ]

    for test_case in test_cases:
      with self.subTest(**test_case):
        num_gates, num_chars = test_case["num_gates"], test_case["num_chars"]
        on_board, in_outskirts = test_case["on_board"], test_case["in_outskirts"]
        monster_limit = test_case.get("monster_limit", 3 + num_chars)
        outskirts_limit = 8 - num_chars
        expected_board, expected_outskirts = test_case["board"], test_case["outskirts"]
        expected_cup, expected_clears = test_case["cup"], test_case["clears"]

        board, outskirts, cup, clears = MonsterSurge.spawn_counts(
            max(num_gates, num_chars), on_board, in_outskirts, monster_limit, outskirts_limit,
        )

        self.assertEqual(board, expected_board)
        self.assertEqual(outskirts, expected_outskirts)
        self.assertEqual(cup, expected_cup)
        self.assertEqual(clears, expected_clears)
        self.assertEqual(cup, max(num_gates, num_chars) - board - outskirts)


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
      choice.resolve(self.state, "Done")
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
      choice.resolve(self.state, "Done")
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
    self.assertFalse(close.sealed)

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
    self.assertFalse(close.sealed)

  def testSealChoiceCancelled(self):
    self.char.clues = 6
    close = GateCloseAttempt(self.char, "Square")
    self.state.event_stack.append(close)
    self.char.possessions.append(Canceller(SpendChoice, 1))

    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Done")
    self.resolve_until_done()

    self.assertTrue(close.is_resolved())
    self.assertFalse(self.square.gate)
    self.assertFalse(self.square.sealed)
    self.assertEqual(self.char.clues, 6)
    self.assertFalse(close.choice.is_cancelled())
    self.assertFalse(close.check.is_cancelled())
    self.assertTrue(close.seal_choice.is_cancelled())
    self.assertTrue(close.closed)
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

    self.state.event_stack.append(MoveMonsters({"square"}, {"circle", "moon"}))
    self.resolve_until_done()

    self.assertEqual(self.state.monsters[0].place.name, "FrenchHill")

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
    super().setUp()
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
    ret = ReturnToCup(names={"Dream Flier", "Maniac", "Zombie"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 1)  # The outskirts don't count.

    self.assertEqual(self.dream_flier.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertIsNone(self.zombie.place)
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

  def testReturnInStreets(self):
    ret = ReturnToCup(from_places={"streets"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 1)

    self.assertEqual(self.cultist.place, self.state.monster_cup)
    self.assertEqual(self.furry_beast.place.name, "Woods")
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")

  def testReturnInLocations(self):
    ret = ReturnToCup(from_places={"locations"})
    self.state.event_stack.append(ret)
    self.resolve_until_done()

    self.assertEqual(ret.returned, 1)

    self.assertEqual(self.cultist.place.name, "Southside")
    self.assertEqual(self.furry_beast.place, self.state.monster_cup)
    self.assertEqual(self.maniac.place.name, "Outskirts")
    self.assertEqual(self.dream_flier.place.name, "Sky")


class GlobalModifierTest(EventTest):

  def setUp(self):
    super().setUp()
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
