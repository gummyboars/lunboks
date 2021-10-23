#!/usr/bin/env python3

import json
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
import game


class NoMythos(mythos.GlobalEffect):

  def create_event(self, state):
    return events.Nothing()


class PauseMythos(mythos.GlobalEffect):

  def create_event(self, state):
    return events.BinaryChoice(
        state.characters[state.first_player], "", "A", "B", events.Nothing(), events.Nothing())


class GateTravelTest(unittest.TestCase):

  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.all_characters.update({"Nun": characters.Nun()})
    self.state.characters = [self.state.all_characters["Nun"]]
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.mythos.clear()
    self.state.mythos.append(mythos.Mythos5())
    self.state.event_stack.append(events.Mythos(None))  # Opens at the Square.
    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
    # Return all monsters to the cup so the character doesn't have to fight/evade.
    for m in self.state.monsters:
      m.place = self.state.monster_cup
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
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

    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.GateChoice)
    self.state.event_stack[-1].resolve(self.state, "Square")
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
    for name in ["Nun", "Doctor", "Archaeologist"]:
      self.state.all_characters[name] = getattr(characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
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
    for name in ["Nun", "Doctor", "Archaeologist"]:
      self.state.all_characters[name] = getattr(characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
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


class PlayerJoinTest(unittest.TestCase):

  def setUp(self):
    self.game = eldritch.EldritchGame()

  def handle(self, session, data):
    res = self.game.handle(session, data)
    if res is None:
      return
    for _ in res:
      pass

  def testJoinJSON(self):
    self.game.connect_user("session")
    data = self.game.for_player("session")
    self.assertIsNone(json.loads(data)["player_idx"])
    self.assertIsNone(json.loads(data)["pending_name"])

    self.handle("session", {"type": "join", "char": "Nun"})
    data = self.game.for_player("session")
    self.assertIsNone(json.loads(data)["player_idx"])
    self.assertEqual(json.loads(data)["pending_name"], "Nun")

    self.handle("session", {"type": "start"})
    data = self.game.for_player("session")
    self.assertEqual(json.loads(data)["player_idx"], 0)
    self.assertIsNone(json.loads(data)["pending_name"])

  def testCannotStartWithoutPlayers(self):
    self.game.connect_user("A")
    with self.assertRaises(AssertionError):
      self.handle("A", {"type": "start"})

  def testCannotReuseCharacter(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.assertEqual(len(self.game.game.characters), 0)
    self.game.connect_user("B")

    # Cannot reuse a pending character.
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("B", {"type": "join", "char": "Nun"})

    self.handle("A", {"type": "start", "char": "Nun"})
    self.assertEqual(len(self.game.game.characters), 1)

    # Cannot reuse a character already playing.
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("B", {"type": "join", "char": "Nun"})

  def testCanSwitchCharacter(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.assertEqual(self.game.game.pending_chars, ["Nun"])
    self.handle("A", {"type": "join", "char": "Doctor"})
    self.assertEqual(self.game.game.pending_chars, ["Doctor"])

  def testClearPendingCharactersOnDisconnect(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.assertIn("A", self.game.pending_sessions)
    self.game.connect_user("B")
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("B", {"type": "join", "char": "Nun"})
    self.assertNotIn("B", self.game.pending_sessions)

    self.game.disconnect_user("A")
    self.assertNotIn("A", self.game.pending_sessions)
    self.handle("B", {"type": "join", "char": "Nun"})
    self.assertIn("B", self.game.pending_sessions)

  @mock.patch.object(mythos, "CreateMythos", return_value=[NoMythos(), PauseMythos()])
  def testJoinMidGame(self, _):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.handle("A", {"type": "start"})
    self.handle("A", {"type": "set_slider", "name": "done"})
    self.assertEqual(len(self.game.game.characters), 1)
    self.assertEqual(self.game.game.characters[0].name, "Nun")
    self.assertEqual(self.game.game.characters[0].place.name, "Church")

    self.assertEqual(self.game.game.game_stage, "slumber")
    self.assertEqual(self.game.game.turn_phase, "upkeep")

    self.game.connect_user("B")
    self.handle("B", {"type": "join", "char": "Doctor"})
    self.assertEqual(len(self.game.game.characters), 1)  # Should not be in the game yet.
    self.assertEqual(self.game.player_sessions, {"A": 0})
    self.handle("A", {"type": "set_slider", "name": "done"})

    # Move to the streets so that there is no encounter.
    self.handle("A", {"type": "choice", "choice": "Southside"})
    self.handle("A", {"type": "choice", "choice": "done"})

    # Should now be in the pause mythos, with A needing to make a choice. No new characters yet.
    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertEqual(len(self.game.game.characters), 1)

    self.game.connect_user("C")
    self.handle("C", {"type": "join", "char": "Gangster"})
    self.assertEqual(len(self.game.game.characters), 1)

    self.handle("A", {"type": "choice", "choice": "A"})
    self.assertEqual(self.game.game.turn_phase, "upkeep")

    self.assertEqual(len(self.game.game.characters), 3)
    self.assertEqual(self.game.game.characters[1].name, "Doctor")
    self.assertEqual(self.game.game.characters[2].name, "Gangster")
    # Now that new players have joined, they should enter the first player rotation.
    self.assertEqual(self.game.game.first_player, 1)
    self.assertEqual(self.game.game.turn_idx, 1)

    # Make sure the new characters get their starting equipment and are placed on the board.
    self.assertEqual(self.game.game.characters[1].place.name, "Hospital")
    self.assertEqual(self.game.game.characters[2].place.name, "House")

    self.assertIn("Medicine", {pos.name for pos in self.game.game.characters[1].possessions})
    self.assertIn("Tommy Gun", {pos.name for pos in self.game.game.characters[2].possessions})

    # Validate that new characters get a chance to set their sliders before upkeep.
    self.assertTrue(self.game.game.event_stack)
    self.assertIsInstance(self.game.game.event_stack[-1], events.SliderInput)
    self.assertTrue(self.game.game.event_stack[-1].free)

    self.handle("B", {"type": "set_slider", "name": "done"})
    self.handle("C", {"type": "set_slider", "name": "done"})

    # It is now the doctor's upkeep. They should be able to spend focus to move their sliders.
    self.assertTrue(self.game.game.event_stack)
    self.assertIsInstance(self.game.game.event_stack[-1], events.SliderInput)
    self.assertEqual(self.game.game.event_stack[-1].character, self.game.game.characters[1])
    self.assertFalse(self.game.game.event_stack[-1].free)


if __name__ == '__main__':
  unittest.main()
