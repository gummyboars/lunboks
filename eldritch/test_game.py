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
    self.state.event_stack.append(events.Mythos(None))  # Opens at the Square.
    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
    # Return all monsters to the cup so the character doesn't have to fight/evade.
    for m in self.state.monsters:
      m.place = self.state.monster_cup
    self.state.test_mode = False

  def testMoveToOtherWorld(self):
    char = self.state.characters[0]
    self.assertTrue(self.state.places["Square"].gate)
    world_name = self.state.places["Square"].gate.name

    self.assertFalse(self.state.event_stack)
    self.state.turn_phase = "movement"
    char.place = self.state.places["Square"]
    movement = events.Movement(char)
    movement.done = True
    self.state.event_stack.append(movement)
    self.assertEqual(self.state.turn_idx, 0)

    for _ in self.state.resolve_loop():
      if self.state.turn_idx != 0 or self.state.turn_phase not in ("movement", "encounter"):
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertEqual(char.place.name, world_name + "1")
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.OtherWorldPhase)

  def testOtherWorldMovement(self):
    self.state.gate_cards.extend(gate_encounters.CreateGateCards())
    char = self.state.characters[0]
    char.place = self.state.places["City1"]
    self.state.turn_phase = "upkeep"
    upkeep = events.Upkeep(char)
    upkeep.done = True
    self.state.event_stack.append(upkeep)
    for _ in self.state.resolve_loop():
      if self.state.turn_idx != 0 or self.state.turn_phase in ("mythos", "otherworld"):
        break
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertEqual(char.place.name, "City2")

  def testReturnFromOtherWorld(self):
    char = self.state.characters[0]
    world_name = self.state.places["Square"].gate.name
    char.place = self.state.places[world_name + "2"]
    self.state.turn_phase = "upkeep"
    upkeep = events.Upkeep(char)
    upkeep.done = True
    self.state.event_stack.append(upkeep)
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_phase, "encounter")
    self.assertEqual(char.place.name, "Square")
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.assertEqual(self.state.event_stack[-1].prompt(), "Close the gate?")


class NextTurnTest(unittest.TestCase):

  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.characters = self.state.characters[:3]
    self.state.test_mode = False

  def testTurnProgression(self):
    self.assertEqual(self.state.first_player, 0)
    self.assertEqual(self.state.turn_number, 0)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.state.event_stack.append(events.Upkeep(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass

    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "upkeep")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.Upkeep)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.state.event_stack[-1].done = True
      # Will stop at each slider input. Last one will stop at CityMovement.
      for _ in self.state.resolve_loop():
        pass

    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "movement")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.Movement)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.state.event_stack[-1].done = True
      # Will stop at each CityMovement. Last one will stop when we leave the movement phase.
      for _ in self.state.resolve_loop():
        if self.state.turn_phase != "movement":
          break

    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "encounter")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.EncounterPhase)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.assertEqual(len(self.state.event_stack), 1)
      self.state.event_stack[0].done = True
      # Run the resolver just enough to put the next turn on the stack.
      for _ in self.state.resolve_loop():
        if self.state.event_stack and not self.state.event_stack[0].done:
          break

    # Run the resolver through to the mythos phase. Nothing should happen in other worlds.
    for _ in self.state.resolve_loop():
      if self.state.event_stack and isinstance(self.state.event_stack[0], events.Mythos):
        break
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 0)
    self.assertIsInstance(self.state.event_stack[0], events.Mythos)
    self.state.event_stack[0].done = True

    # Run the resolver once more to get to the next turn & next player's upkeep.
    for _ in self.state.resolve_loop():
      pass
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
    self.state.event_stack.append(events.Upkeep(self.state.characters[0]))
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.turn_phase, "upkeep")

    self.state.event_stack[-1].resolve(self.state, "done", None)
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "movement")

    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "encounter":
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "encounter")
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_idx == 2:
        break
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.turn_phase, "encounter")
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "mythos":
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.first_player, 1)
    self.assertEqual(self.state.turn_number, 1)
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertIsNone(self.state.characters[1].lose_turn_until)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[1])

  def testLoseTurnAsFirstPlayer(self):
    self.state.characters[1].lose_turn_until = 1
    self.state.first_player = 1
    self.state.turn_phase = "encounter"
    self.assertEqual(self.state.turn_idx, 0)
    self.state.event_stack.append(events.EncounterPhase(self.state.characters[0]))
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "mythos":
        break
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)
    self.assertIsInstance(self.state.event_stack[0], events.Mythos)

    self.state.event_stack[0].done = True
    for _ in self.state.resolve_loop():
      pass
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
    self.state.event_stack.append(events.Mythos(None))
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "mythos" and self.state.turn_idx == 1:
        break
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)


class InsaneTest(unittest.TestCase):

  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.characters = self.state.characters[:3]
    self.state.test_mode = False

  def testInsaneUpkeep(self):
    self.state.characters[0].sanity = 1
    self.state.event_stack.append(events.Upkeep(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.state.event_stack.append(events.Loss(self.state.characters[0], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[0], events.Upkeep)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[1])
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.turn_phase, "upkeep")

  def testInsaneMovement(self):
    self.state.characters[2].sanity = 1
    self.state.event_stack.append(events.Movement(self.state.characters[2]))
    self.state.turn_idx = 2
    self.state.turn_phase = "movement"
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.CityMovement)
    self.state.event_stack.append(events.Loss(self.state.characters[2], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "movement":
        break
    self.assertIsInstance(self.state.event_stack[0], events.EncounterPhase)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[0])
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "encounter")

  def testInsaneEncounter(self):
    self.state.characters[2].sanity = 1
    self.state.characters[0].place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(events.EncounterPhase(self.state.characters[2]))
    self.state.turn_idx = 2
    self.state.turn_phase = "encounter"
    self.state.characters[2].place.gate = self.state.gates.popleft()
    self.state.characters[2].explored = True
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.state.event_stack.append(events.Loss(self.state.characters[2], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "encounter":
        break
    self.assertIsInstance(self.state.event_stack[0], events.OtherWorldPhase)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[0])
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "otherworld")

  def testInsaneOtherWorld(self):
    self.state.characters[0].stamina = 1
    self.state.characters[0].place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(events.OtherWorldPhase(self.state.characters[0]))
    self.state.turn_idx = 0
    self.state.turn_phase = "otherworld"
    self.state.gate_cards.append(gate_encounters.GateCard(
      "Gate29", {"red"}, {"Other": gate_encounters.Other29}))  # lose one stamina
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "otherworld":
        break
    self.assertIsInstance(self.state.event_stack[0], events.Mythos)
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.characters[0].place.name, "Lost")

  def testInsaneMythos(self):
    self.state.characters[0].sanity = 1
    # both characters 0 and 1 may spend a clue token on the luck check from the mythos card.
    self.state.characters[0].clues = 1
    self.state.characters[1].clues = 1
    self.state.turn_idx = 0
    self.state.turn_phase = "mythos"
    self.state.mythos.append(mythos.Mythos1())
    self.state.event_stack.append(events.Mythos(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertIsInstance(self.state.event_stack[-1], events.Check)
    self.assertEqual(self.state.event_stack[-1].character, self.state.characters[0])
    self.state.event_stack.append(events.Loss(self.state.characters[0], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertIsInstance(self.state.event_stack[-1], events.Check)
    self.assertEqual(self.state.event_stack[-1].character, self.state.characters[1])


class OutputTest(unittest.TestCase):

  def testCanProduceJSON(self):
    game = eldritch.EldritchGame()
    game.connect_user("session")
    game.for_player("session")


if __name__ == '__main__':
  unittest.main()
