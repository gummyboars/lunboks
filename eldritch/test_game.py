#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import characters
from eldritch import eldritch
from eldritch import events
from eldritch import gate_encounters
from eldritch import mythos


class GateTravelTest(unittest.TestCase):

  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.characters = self.state.characters[:1]
    self.state.mythos.clear()
    self.state.mythos.append(mythos.Mythos5())
    self.state.handle_mythos()  # Opens at the Square.
    for _ in self.state.resolve_loop():
      pass
    # Return all monsters to the cup so the character doesn't have to fight/evade.
    for m in self.state.monsters:
      m.place = self.state.monster_cup

  def testMoveToOtherWorld(self):
    char = self.state.characters[0]
    self.assertTrue(self.state.places["Square"].gate)
    world_name = self.state.places["Square"].gate.name

    self.assertFalse(self.state.event_stack)
    self.state.turn_phase = "movement"
    char.place = self.state.places["Square"]
    self.state.event_stack.append(events.EndMovement(char))
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "movement")
    for _ in self.state.resolve_loop():
      if self.state.turn_idx != 0 or self.state.turn_phase not in ("movement", "encounter"):
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertEqual(char.place.name, world_name + "1")

  def testOtherWorldMovement(self):
    self.state.gate_cards.extend(gate_encounters.CreateGateCards())
    char = self.state.characters[0]
    char.place = self.state.places["City1"]
    self.state.turn_phase = "upkeep"
    self.state.event_stack.append(events.EndUpkeep(char))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertEqual(char.place.name, "City2")

  def testReturnFromOtherWorld(self):
    char = self.state.characters[0]
    world_name = self.state.places["Square"].gate.name
    char.place = self.state.places[world_name + "2"]
    self.state.turn_phase = "upkeep"
    self.state.event_stack.append(events.EndUpkeep(char))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_phase, "encounter")
    self.assertEqual(char.place.name, "Square")


class NextTurnTest(unittest.TestCase):

  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.characters = self.state.characters[:3]

  def testTurnProgression(self):
    self.assertEqual(self.state.first_player, 0)
    self.assertEqual(self.state.turn_number, 0)
    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "upkeep")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.state.next_turn()
    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "movement")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.state.next_turn()
    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "encounter")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.state.next_turn()
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 0)
    self.state.next_turn()
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)
    self.assertEqual(self.state.turn_number, 1)

  def testLoseTurnAndDelayed(self):
    # NOTE: we don't test lost turn on the first character because it's already their turn.
    self.state.characters[1].lose_turn_until = 1
    self.state.characters[2].delayed_until = 1

    self.assertEqual(self.state.first_player, 0)
    self.assertEqual(self.state.turn_number, 0)
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "upkeep")

    self.state.next_turn()
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.state.next_turn()
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "movement")
    self.state.next_turn()
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "encounter")
    self.state.next_turn()
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.turn_phase, "encounter")

    self.state.next_turn()
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.state.next_turn()
    self.assertIsNone(self.state.characters[1].lose_turn_until)

  def testLoseTurnAsFirstPlayer(self):
    self.state.characters[1].lose_turn_until = 1
    self.state.first_player = 1
    self.state.turn_phase = "encounter"
    self.assertEqual(self.state.turn_idx, 0)

    self.state.next_turn()
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)
    self.state.next_turn()
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.first_player, 2)
    self.assertIsNone(self.state.characters[1].lose_turn_until)

  def testAllPlayersLoseTurns(self):
    for turn_idx in range(3):
      self.state.characters[turn_idx].lose_turn_until = 2
    self.state.turn_phase = "mythos"
    self.state.turn_idx = 0
    self.assertEqual(self.state.first_player, 0)

    self.state.next_turn()
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)


class OutputTest(unittest.TestCase):

  def testCanProduceJSON(self):
    game = eldritch.EldritchGame()
    game.connect_user("session")
    game.for_player("session")


if __name__ == '__main__':
  unittest.main()
