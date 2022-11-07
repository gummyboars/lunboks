#!/usr/bin/env python3

from collections import deque
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import abilities
from eldritch import gate_encounters
from eldritch import events
from eldritch.events import *
from eldritch import places
from eldritch.test_events import EventTest


class DrawGateEncounter(EventTest):

  def setUp(self):
    super().setUp()
    self.state.gate_cards = deque([
        gate_encounters.GateCard("Gate1", {"blue"}, {"Other": lambda char: Nothing()}),
        gate_encounters.GateCard("Gate2", {"green"}, {"Other": lambda char: Nothing()}),
        gate_encounters.GateCard("ShuffleGate", set(), {"Other": lambda char: Nothing()}),
        gate_encounters.GateCard("Gate3", {"yellow"}, {"Other": lambda char: Nothing()}),
    ])

  def testDrawCard(self):
    self.char.place = self.state.places["Abyss1"]  # blue and red
    self.assertEqual(len(self.state.gate_cards), 4)
    gate_encounter = GateEncounter(self.char)
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), 4)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate1")

  def testDrawColoredCard(self):
    self.char.place = self.state.places["Plateau1"]  # green and red
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char)
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate2")
    self.assertEqual(self.state.gate_cards[-2].name, "Gate1")
    self.assertFalse("shuffled" in str(self.state.event_log[0]))

  def testDrawMultipleColors(self):
    self.char.place = self.state.places["City1"]  # green and yellow
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char)
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate2")
    self.assertFalse("shuffled" in str(self.state.event_log[0]))

  def testDrawMultipleColorsWithShuffle(self):
    self.char.place = self.state.places["Sunken City1"]  # yellow and red
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char)
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate3")
    self.assertTrue("shuffled" in str(self.state.event_log[0]))


class GateEncounterTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.speed_sneak_slider = 1
    self.char.fight_will_slider = 1
    self.char.lore_luck_slider = 1
    self.char.stamina = 3
    self.char.sanity = 3
    self.char.dollars = 3
    self.char.clues = 0


class Gate10Test(GateEncounterTest):

  def testDreamlands10Pass(self):
    self.char.place = self.state.places["Dreamlands2"]
    self.state.event_stack.append(gate_encounters.Dreamlands10(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertIsNone(self.char.delayed_until)

  def testDreamlands10Fail(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Dreamlands10(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)

  def testAbyss10Pass(self):
    self.char.place = self.state.places["Abyss1"]
    self.state.event_stack.append(gate_encounters.Abyss10(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertIsNone(self.char.delayed_until)

  def testAbyss10Fail(self):
    self.char.place = self.state.places["Abyss2"]
    self.state.event_stack.append(gate_encounters.Abyss10(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)

  def testOther10Pass(self):
    self.char.place = self.state.places["City2"]
    self.state.event_stack.append(gate_encounters.Other10(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertIsNone(self.char.delayed_until)

  def testOther10Fail(self):
    self.char.place = self.state.places["City2"]
    self.state.event_stack.append(gate_encounters.Other10(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)


class Gate16Test(GateEncounterTest):

  def testGreatHall16Pass(self):
    self.state.skills.append(abilities.Stealth(0))
    self.state.event_stack.append(gate_encounters.GreatHall16(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].deck, "skills")

  def testGreatHall16Fail(self):
    self.state.skills.append(abilities.Stealth(0))
    self.state.event_stack.append(gate_encounters.GreatHall16(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testOther16Pass(self):
    self.state.event_stack.append(gate_encounters.Other16(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 6)
    self.assertEqual(self.char.stamina, 3)

  def testOther16Fail(self):
    self.state.event_stack.append(gate_encounters.Other16(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.stamina, 1)


class Gate29Test(GateEncounterTest):

  def testPlateau29Pass(self):
    self.char.stamina = 5
    self.state.event_stack.append(gate_encounters.Plateau29(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testPlateau29Fail(self):
    self.char.stamina = 5
    self.state.event_stack.append(gate_encounters.Plateau29(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testDreamlands29Pass(self):
    self.char.stamina = 5
    self.state.event_stack.append(gate_encounters.Dreamlands29(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testDreamlands29Fail(self):
    self.char.stamina = 5
    self.state.event_stack.append(gate_encounters.Dreamlands29(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testOther29(self):
    self.char.stamina = 5
    self.state.event_stack.append(gate_encounters.Other29(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)


if __name__ == "__main__":
  unittest.main()
