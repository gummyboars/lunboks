#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.assets as assets
import eldritch.encounters as encounters
import eldritch.events as events
from eldritch.events import *
import eldritch.items as items
from eldritch.test_events import EventTest


class EncounterTest(EventTest):

  def setUp(self):
    super(EncounterTest, self).setUp()
    self.char.place = self.state.places["Diner"]
    self.char.speed_sneak_slider = 1
    self.char.fight_will_slider = 1
    self.char.lore_luck_slider = 1
    self.char.stamina = 3
    self.char.sanity = 3
    self.char.dollars = 3
    # NOTE: never start the character with clues, since most encounters will get interrupted
    # asking the player if they wish to use clue tokens on their check.
    self.char.clues = 0


class DinerTest(EncounterTest):

  def setUp(self):
    super(DinerTest, self).setUp()
    self.char.place = self.state.places["Diner"]

  def testDiner1(self):
    self.state.event_stack.append(encounters.Diner1(self.char))
    self.resolve_until_done()

  def testDiner2Draw(self):
    self.state.common.append(items.Food())
    self.state.event_stack.append(encounters.Diner2(self.char))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 0)

  def testDiner2Empty(self):
    self.state.event_stack.append(encounters.Diner2(self.char))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testDiner3Poor(self):
    self.char.dollars = 0
    self.state.event_stack.append(encounters.Diner3(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testDiner3DontPay(self):
    self.state.event_stack.append(encounters.Diner3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Go Hungry")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testDiner3Pay(self):
    self.state.event_stack.append(encounters.Diner3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Pay $1")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testDiner4Pass(self):
    self.state.event_stack.append(encounters.Diner4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)

  def testDiner4Fail(self):
    self.state.event_stack.append(encounters.Diner4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testDiner5Pass(self):
    self.state.event_stack.append(encounters.Diner5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 1)

  def testDiner5Fail(self):
    self.state.event_stack.append(encounters.Diner5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testDiner6Pass(self):
    self.state.event_stack.append(encounters.Diner6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testDiner6Fail(self):
    self.state.event_stack.append(encounters.Diner6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)

  def testDiner7Pass(self):
    self.state.event_stack.append(encounters.Diner7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)
    self.assertEqual(self.char.place.name, "Diner")

  def testDiner7Fail(self):
    self.state.event_stack.append(encounters.Diner7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.place.name, "Easttown")


class RoadhouseTest(EncounterTest):

  def setUp(self):
    super(RoadhouseTest, self).setUp()
    self.char.place = self.state.places["Roadhouse"]

  def testRoadhouse1Clueless(self):
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testRoadhouse1No(self):
    self.char.clues = 3
    self.state.allies.append(assets.RoadhouseAlly())
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testRoadhouse1Yes(self):
    self.char.clues = 3
    self.state.allies.append(assets.RoadhouseAlly())
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "RoadhouseAlly")

  def testRoadhouse2Pass(self):
    self.state.event_stack.append(encounters.Roadhouse2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)
    self.assertEqual(self.char.place.name, "Roadhouse")

  def testRoadhouse2Fail(self):
    self.state.event_stack.append(encounters.Roadhouse2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.place.name, "Roadhouse")

  def testRoadhouse2Poor(self):
    self.char.dollars = 2
    self.assertEqual(self.char.stamina, 3)
    self.state.event_stack.append(encounters.Roadhouse2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.place.name, "Easttown")

  def testRoadhouse6Pass(self):
    self.state.event_stack.append(encounters.Roadhouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(self.char.place.name, "Roadhouse")

  def testRoadhouse6Fail(self):
    self.char.dollars = 23
    self.state.event_stack.append(encounters.Roadhouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.place.name, "Easttown")

  def testRoadhouse7Pass(self):
    self.state.event_stack.append(encounters.Roadhouse7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testRoadhouse7Fail(self):
    self.state.event_stack.append(encounters.Roadhouse7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)


class PoliceTest(EncounterTest):

  def setUp(self):
    super(PoliceTest, self).setUp()
    self.char.place = self.state.places["Police"]

  def testPolice1Pass(self):
    self.state.event_stack.append(encounters.Police1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.place.name, "Police")

  def testPolice1Fail(self):
    self.state.event_stack.append(encounters.Police1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.place.name, "Easttown")

  def testPolice2Pass(self):
    self.state.event_stack.append(encounters.Police2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testPolice2Fail(self):
    self.state.event_stack.append(encounters.Police2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)

  def testPolice3Pass(self):
    self.state.event_stack.append(encounters.Police3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)

  def testPolice3Fail(self):
    self.state.event_stack.append(encounters.Police3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testPolice4Pass(self):
    self.state.common.append(items.Revolver38())
    self.state.event_stack.append(encounters.Police4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testPolice4Empty(self):
    self.state.event_stack.append(encounters.Police4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testPolice4Fail(self):
    self.state.common.append(items.Revolver38())
    self.state.event_stack.append(encounters.Police4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testPolice7Pass(self):
    self.state.common.append(items.ResearchMaterials())
    self.state.event_stack.append(encounters.Police7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Research Materials")

  def testPolice7Empty(self):
    self.state.event_stack.append(encounters.Police7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testPolice7Fail(self):
    self.state.common.append(items.ResearchMaterials())
    self.state.event_stack.append(encounters.Police7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.char.possessions), 0)
