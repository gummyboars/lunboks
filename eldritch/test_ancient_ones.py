#!/usr/bin/env python3

import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])
from eldritch.test_events import EventTest
from eldritch import ancient_ones, events, monsters
from eldritch.events import CityMovement


class TestAncientOnes(EventTest):
  def testWendigoStreet(self):
    self.state.ancient_one = ancient_ones.Wendigo()
    self.advance_turn(self.state.turn_number, "movement")
    self.char.place = self.state.places["Merchant"]
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    stamina = self.char.stamina
    self.advance_turn(self.state.turn_number+1, "upkeep")
    self.assertEqual(self.char.stamina, stamina -1)

  def testWendigoLocation(self):
    self.state.ancient_one = ancient_ones.Wendigo()
    self.advance_turn(self.state.turn_number, "movement")
    self.char.place = self.state.places["Woods"]
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    stamina = self.char.stamina
    self.advance_turn(self.state.turn_number+1, "upkeep")
    self.assertEqual(self.char.stamina, stamina)

  def testSquidFaceMaxSanStam(self):
    self.char.stamina = 5
    self.char.sanity = 5
    self.state.event_stack.append(events.Gain(self.char, {'sanity': 5, 'stamina': 5}))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.state.ancient_one = ancient_ones.SquidFace()
    self.char.stamina = 3
    self.char.sanity = 3
    self.state.event_stack.append(events.Gain(self.char, {'sanity': 5, 'stamina': 5}))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)

  def testSquidFaceMonsters(self):
    self.assertEqual(self.state.get_modifier(monsters.Cultist(), 'horror_damage'), 0)
    self.state.ancient_one = ancient_ones.SquidFace()
    self.assertEqual(self.state.get_modifier(monsters.Cultist(), 'horror'), -2)
    self.assertEqual(self.state.get_modifier(monsters.Cultist(), 'horror_damage'), 2)


if __name__ == "__main__":
  unittest.main()
