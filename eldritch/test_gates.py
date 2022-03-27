#!/usr/bin/env python3

from collections import deque
import os
import sys
import unittest
import operator

from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

#Imports things from Eldritch
from eldritch import abilities 
from eldritch import gates
from eldritch import gate_encounters
from eldritch import events
from eldritch import items
from eldritch import values
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
    self.assertEqual(len(self.state.gate_cards), 4)
    gate_encounter = GateEncounter(self.char, "Anywhere", {"blue"})
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), 4)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate1")

  def testDrawColoredCard(self):
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char, "Nowhere", {"green"})
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate2")
    self.assertEqual(self.state.gate_cards[-2].name, "Gate1")
    self.assertFalse(any("shuffled" in log for log in self.state.event_log))

  def testDrawMultipleColors(self):
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char, "Somewhere", {"green", "red"})
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate2")
    self.assertFalse(any("shuffled" in log for log in self.state.event_log))

  def testDrawAndShuffle(self):
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char, "Someplace Else", {"yellow"})
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate3")
    self.assertTrue(any("shuffled" in log for log in self.state.event_log))

  def testDrawMultipleColorsWithShuffle(self):
    card_count = len(self.state.gate_cards)
    gate_encounter = GateEncounter(self.char, "Somewhere", {"red", "yellow"})
    self.state.event_stack.append(gate_encounter)
    self.resolve_until_done()
    self.assertEqual(len(self.state.gate_cards), card_count)
    self.assertEqual(self.state.gate_cards[-1].name, "Gate3")
    self.assertTrue(any("shuffled" in log for log in self.state.event_log))


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


class Gate2Test(GateEncounterTest):

  def testAbyss2(self):
    self.char.place = self.state.places["Abyss2"]
    self.state.event_stack.append(gate_encounters.Abyss2(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    
  def testPluto2Pass(self):
    self.char.fight_will_slider = 3
    self.char.place = self.state.places["Pluto1"]
    self.state.event_stack.append(gate_encounters.Pluto2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Pluto1")

  def testPluto2Fail(self):
    self.char.place = self.state.places["Pluto2"]
    self.state.event_stack.append(gate_encounters.Pluto2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")    

  def testOther2Pass(self):
    self.char.speed_sneak_slider = 3
    self.char.place = self.state.places["Dreamlands2"]
    self.state.gates.clear() #Throws away gate markers
    self.info = places.OtherWorldInfo("Dreamlands", {"blue", "yellow", "green", "red"}) #Defines colored encounters that can happen in Dreamlands
    self.gate = gates.Gate(self.info, 0) #Creates a gate marker of difficulty 0
    self.state.gates.append(self.gate) #Takes the gate marker created in the previous line and adds it to the pile of gates that was previously cleared in the line two above
    self.state.places["Square"].gate = self.state.gates.popleft() #At Independence Square, we are going to take a gate off of the gate pile defined above, that goes to the Dreamlands
    self.state.event_stack.append(gate_encounters.Other2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(GateChoice) #Resolve event stack until user/player has to choose which gate to come back through
    choice.resolve(self.state, "Square") #Player has to choose Square
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Square")    
    #TODO "In either event, you automatically close the gate you entered through

  def testOther2Fail(self):
    self.char.place = self.state.places["Dreamlands2"]
    self.state.event_stack.append(gate_encounters.Other2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")
    #TODO "In either event, you automatically close the gate you entered through


class Gate5Test(GateEncounterTest):

  def testDreamlands5(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Dreamlands5(self.char))
    self.resolve_until_done()
    
  def testAbyss5Pass(self):
    self.char.place = self.state.places["Abyss1"]
    self.state.unique.append(items.HolyWater()) #Adds "Holy Water" item to the unique pile
    self.state.event_stack.append(gate_encounters.Abyss5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 6)
    self.assertEqual(len(self.char.possessions), 1) #len refers to the "length" (or quantity) of entries in the character's possessions, which should be exactly 1; technically, this line is unnecessary with the next line
    self.assertEqual(self.char.possessions[0].name, "Holy Water") #"Real programmers use 0-index

  def testAbyss5Fail(self):
    self.char.place = self.state.places["Abyss1"]
    self.state.event_stack.append(gate_encounters.Abyss5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(len(self.char.possessions), 0)

  def testOther5Pass(self):
    self.assertEqual(self.char.luck(self.state), 3)
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Other5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)
    
  def testOther5Fail(self):
    self.assertEqual(self.char.luck(self.state), 3)
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Other5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)


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
