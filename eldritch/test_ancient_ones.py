#!/usr/bin/env python3

import os
import sys
import unittest

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])
from eldritch.test_events import EventTest
from eldritch import ancient_ones, encounters, events, monsters
from eldritch.events import CityMovement


def CreateDummyEncounterCard():
  return encounters.EncounterCard("Dummy", {"Woods": lambda char: events.Nothing()})


class TestAncientOnes(EventTest):
  def testSquidFaceMaxSanStam(self):
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

  def testSquidFaceMonsters(self):
    self.assertEqual(monsters.Cultist().damage("horror", self.state, self.char), None)
    self.state.ancient_one = ancient_ones.SquidFace()
    self.assertEqual(self.state.get_modifier(monsters.Cultist(), "horrordifficulty"), -2)
    self.assertEqual(self.state.get_modifier(monsters.Cultist(), "horrordamage"), 2)
    self.assertEqual(monsters.Cultist().damage("horror", self.state, self.char), 2)

  def testYellowKingMonsters(self):
    self.state.ancient_one = ancient_ones.YellowKing()
    cultist = next(
        monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertTrue(cultist.has_attribute("flying", self.state, self.char))
    self.assertEqual(cultist.difficulty("combat", self.state, self.char), -2)

  def testChaosGodMonsters(self):
    self.state.ancient_one = ancient_ones.ChaosGod()
    maniac = next(
        monster for monster in self.state.monsters if isinstance(monster, monsters.Maniac)
    )
    self.assertEqual(maniac.toughness(self.state, self.char), 2)

  def testWendigoStreet(self):
    self.state.ancient_one = ancient_ones.Wendigo()
    self.advance_turn(self.state.turn_number, "movement")
    self.char.place = self.state.places["Merchant"]
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    stamina = self.char.stamina
    self.advance_turn(self.state.turn_number+1, "upkeep")
    self.assertEqual(self.char.stamina, stamina - 1)

  def testWendigoLocation(self):
    self.state.ancient_one = ancient_ones.Wendigo()
    self.advance_turn(self.state.turn_number, "movement")
    self.char.place = self.state.places["Woods"]
    self.state.places["Uptown"].encounters = [CreateDummyEncounterCard()]
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    stamina = self.char.stamina
    self.advance_turn(self.state.turn_number+1, "upkeep")
    self.assertEqual(self.char.stamina, stamina)

  # TODO: test wendigo weather
  # TODO: test cultist toughness

  def testBlackPharaohMonsters(self):
    self.state.ancient_one = ancient_ones.BlackPharaoh()
    cultist = next(
        monster for monster in self.state.monsters if isinstance(monster, monsters.Cultist)
    )
    self.assertTrue(cultist.has_attribute("endless", self.state, self.char))

# TODO: test ancient one awaken and attacks


if __name__ == "__main__":
  unittest.main()
