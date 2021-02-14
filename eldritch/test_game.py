#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.characters as characters
import eldritch.eldritch as eldritch


class NextTurnTest(unittest.TestCase):

  def setUp(self):
    self.state = eldritch.GameState()
    chars = characters.CreateCharacters()
    self.state.characters = chars[:3]
    for char in chars:
      char.place = self.state.places[char.home]

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


if __name__ == '__main__':
  unittest.main()
