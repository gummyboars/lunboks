#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.abilities as abilities
import eldritch.assets as assets
import eldritch.encounters as encounters
import eldritch.events as events
import eldritch.places as places
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


class DrawEncounterTest(EncounterTest):

  def testDrawEncounter(self):
    self.char.place = self.state.places["Administration"]
    self.state.places["University"].encounters = [
        encounters.EncounterCard("University2", {"Administration": encounters.Administration2})]
    self.state.turn_idx = 0
    self.state.turn_phase = "movement"
    self.state.next_turn()
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)


class DinerTest(EncounterTest):

  def setUp(self):
    super(DinerTest, self).setUp()
    self.char.place = self.state.places["Diner"]

  def testDiner1DontPay(self):
    self.state.event_stack.append(encounters.Diner1(self.char))
    spend_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(spend_choice.choices, [0, 1, 2, 3])
    spend_choice.resolve(self.state, 0)

    stamina_choice = self.resolve_to_choice(MultipleChoice)
    # TODO: this is not ideal, but it will work.
    self.assertEqual(stamina_choice.choices, [0])
    stamina_choice.resolve(self.state, 0)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 3)

  def testDiner13Dollars(self):
    self.state.event_stack.append(encounters.Diner1(self.char))
    spend_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(spend_choice.choices, [0, 1, 2, 3])
    spend_choice.resolve(self.state, 3)

    stamina_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(stamina_choice.choices, [0, 1, 2, 3])
    stamina_choice.resolve(self.state, 3)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 0)

  def testDiner1Rich(self):
    self.char.dollars = 15
    self.state.event_stack.append(encounters.Diner1(self.char))
    spend_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(spend_choice.choices, [0, 1, 2, 3, 4, 5, 6])
    spend_choice.resolve(self.state, 4)

    stamina_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(stamina_choice.choices, [0, 1, 2, 3, 4])
    stamina_choice.resolve(self.state, 2)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.dollars, 11)

  def testDiner1Poor(self):
    self.char.dollars = 0
    self.state.event_stack.append(encounters.Diner1(self.char))
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 0)

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
    self.state.allies.append(assets.TravelingSalesman())
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testRoadhouse1Yes(self):
    self.char.clues = 3
    self.state.allies.append(assets.TravelingSalesman())
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Traveling Salesman")

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


class LodgeTest(EncounterTest):

  def setUp(self):
    super(LodgeTest, self).setUp()
    self.char.place = self.state.places["Lodge"]

  '''
  def testLodge1Pass(self):
    self.state.event_stack.append(encounters.Lodge1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state, "Whatever")
    self.assertEqual(len(self.char.possessions), 1)
    '''

  def testLodge1Fail(self):
    self.state.event_stack.append(encounters.Lodge1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)


class WitchTest(EncounterTest):

  def setUp(self):
    super(WitchTest, self).setUp()
    self.char.place = self.state.places["Witch"]

  def testWitch2Pass(self):
    self.state.event_stack.append(encounters.Witch2(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testWitch2None(self):
    self.state.event_stack.append(encounters.Witch2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testWitch2Fail(self):
    self.state.event_stack.append(encounters.Witch2(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)


class StoreTest(EncounterTest):

  def setUp(self):
    super(StoreTest, self).setUp()
    self.char.place = self.state.places["Store"]

  def testStore5Pass(self):
    self.state.event_stack.append(encounters.Store5(self.char))
    self.state.common.extend([items.Dynamite(), items.TommyGun(), items.Food()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state, "Food")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 2)

  def testStore5Fail(self):
    self.state.event_stack.append(encounters.Store5(self.char))
    self.state.common.extend([items.Dynamite(), items.TommyGun(), items.Food()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 3)


class SocietyTest(EncounterTest):

  def setUp(self):
    super(SocietyTest, self).setUp()
    self.char.place = self.state.places["Society"]

  def testSociety4Pass(self):
    self.state.event_stack.append(encounters.Society4(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Marksman")
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)
    self.assertEqual(len(self.state.skills), 1)

  def testSociety4Fail(self):
    self.state.event_stack.append(encounters.Society4(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    self.char.lore_luck_slider = 2
    self.assertEqual(self.char.luck(self.state), 2)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(len(self.state.skills), 2)


class AdministrationTest(EncounterTest):

  def setUp(self):
    super(AdministrationTest, self).setUp()
    self.char.place = self.state.places["Administration"]

  def testAdministration1Pass(self):
    self.state.event_stack.append(encounters.Administration1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)

  def testAdministration1Fail(self):
    self.state.event_stack.append(encounters.Administration1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testAdministration2(self):
    self.state.event_stack.append(encounters.Administration2(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testAdministration3Pass(self):
    self.state.event_stack.append(encounters.Administration3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.retainer_start, self.state.turn_number+2)

  def testAdministration3Fail(self):
    self.state.event_stack.append(encounters.Administration3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertIsNone(self.char.retainer_start)

  def testAdminiatration4NoHelp(self):
    self.state.event_stack.append(encounters.Administration4(self.char))
    # Is that what a spell is?
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")  
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.bless_curse, 0)

  def testAdministration4Pass(self):
    self.state.event_stack.append(encounters.Administration4(self.char))
    self.char.lore_luck_slider = 3
    # Is that what a spell is?
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")  
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(self.char.bless_curse, 0)

  def testAdministration4Fail(self):
    self.state.event_stack.append(encounters.Administration4(self.char))
    # Is that what a spell is?
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.bless_curse, -1)

  def testAdministration5(self):
    self.state.event_stack.append(encounters.Administration5(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")

  def testAdministration6Pass(self):
    self.state.event_stack.append(encounters.Administration6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)

  def testAdministration6Fail(self):
    self.state.event_stack.append(encounters.Administration6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testAdministration7Pass(self):
    self.char.dollars = 7
    self.state.event_stack.append(encounters.Administration7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 15)
    self.assertIsNone(self.char.lose_turn_until)
    self.assertEqual(self.char.place.name, "Administration")

  def testAdministration7Fail(self):
    self.char.dollars = 7
    self.state.event_stack.append(encounters.Administration7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)
    self.assertEqual(self.char.place.name, "Police")


class LibraryTest(EncounterTest):

  def setUp(self):
    super(LibraryTest, self).setUp()
    self.char.place = self.state.places["Library"]

  def testLibrary1Fail(self):
    self.state.event_stack.append(encounters.Library1(self.char))
    self.state.unique.extend([items.HolyWater(), items.Cross()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "University")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testLibrary2Fail(self):
    self.state.event_stack.append(encounters.Library2(self.char))
    self.state.unique.extend([items.HolyWater(), items.Cross()])
    self.state.spells.extend([items.HolyWater(), items.Cross()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "University")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.state.spells), 2)

  def testLibrary2Pass2(self):
    self.state.event_stack.append(encounters.Library2(self.char))
    self.state.unique.extend([items.HolyWater(), items.Cross()])
    self.state.spells.extend([items.HolyWater(), items.Cross()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Library")
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(len(self.state.spells), 2)

  def testLibrary2Pass1(self):
    self.state.event_stack.append(encounters.Library2(self.char))
    self.char.fight_will_slider = 3
    self.state.unique.extend([items.HolyWater(), items.Cross()])
    # give me spells and I'll use them!
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state,".38 Revolver")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Library")
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(self.state.spells[0].name, "Tommy Gun")

  def testLibrary2Pass1b(self):
    self.state.event_stack.append(encounters.Library2(self.char))
    self.char.fight_will_slider = 3
    self.state.unique.extend([items.HolyWater(), items.Cross()])
    # Yeah, yeah, these aren't spells
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state,"Tommy Gun")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Library")
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tommy Gun")
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(self.state.spells[0].name, ".38 Revolver")
    
  def testLibrary3Pass5(self):
    self.state.event_stack.append(encounters.Library3(self.char))
    self.char.lore_luck_slider = 2
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 5)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testLibrary3Pass6(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Library3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=6)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 6)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testLibrary3Fail(self):
    self.state.event_stack.append(encounters.Library3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 1)

  def testLibrary5(self):
    self.state.event_stack.append(encounters.Library5(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testLibrary6Pass(self):
    self.char.dollars = 8
    self.state.event_stack.append(encounters.Library6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)
    self.assertEqual(self.char.place.name, "Library")

  def testLibrary6Fail(self):
    self.state.event_stack.append(encounters.Library6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.place.name, "University")

  def testLibrary7Pass(self):
    self.state.event_stack.append(encounters.Library7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=6)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)

  def testLibrary7Fail(self):
    self.state.event_stack.append(encounters.Library7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

class ScienceTest(EncounterTest):

  def setUp(self):
    super(ScienceTest, self).setUp()
    self.char.place = self.state.places["Science"]

  def testScience1(self):
    self.state.event_stack.append(encounters.Science1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 1)

  def testScience1Bless(self):
    self.char.bless_curse = 1
    self.state.event_stack.append(encounters.Science1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 1)

  def testScience1Curse(self):
    self.char.bless_curse = -1
    self.state.event_stack.append(encounters.Science1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)
  
  def testScience2Pass(self):
    self.state.event_stack.append(encounters.Science2(self.char))
    # Yeah, yeah, these aren't spells
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testScience4No(self):
    self.state.event_stack.append(encounters.Science4(self.char))
    # Yeah, yeah, these aren't spells
    self.state.allies.extend([assets.ArmWrestler()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Science")

  def testScience4Yes(self):
    self.state.event_stack.append(encounters.Science4(self.char))
    # Yeah, yeah, these aren't spells
    self.state.allies.extend([assets.ArmWrestler()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Arm Wrestler")
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Science")

  def testScience4YesUnconcious(self):
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Science4(self.char))
    # Yeah, yeah, these aren't spells
    self.state.allies.extend([assets.ArmWrestler()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testScience5Fail(self):
    self.state.event_stack.append(encounters.Science5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 3)

  def testScience6Pass(self):
    self.state.event_stack.append(encounters.Science5(self.char))
    self.char.stamina = 1
    self.char.sanity = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1, 2, 3, 4 , 5])
    choice.resolve(self.state, 3)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 3)

  def testScience7NoHelp(self):
    self.state.event_stack.append(encounters.Science7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Science")

  def testScience7FailConcious(self):
    self.state.event_stack.append(encounters.Science7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.place.name, "Hospital")
  
  def testScience7FailUnconcious(self):
    self.state.event_stack.append(encounters.Science7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

class AsylumTest(EncounterTest):

  def setUp(self):
    super(AsylumTest, self).setUp()
    self.char.place = self.state.places["Asylum"]

  def testAsylum1Zero(self):
    self.state.event_stack.append(encounters.Asylum1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)

  def testAsylum1One(self):
    self.state.event_stack.append(encounters.Asylum1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.clues, 2)    

  def testAsylum1Three(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Asylum1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.clues, 3)

  def testAsylum2Pass(self):
    self.state.event_stack.append(encounters.Asylum2(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.place.name, "Asylum")

  def testAsylum2Fail(self):
    self.state.event_stack.append(encounters.Asylum2(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Downtown")
    self.assertEqual(len(self.char.possessions), 0)

  def testAsylum3Pass(self):
    self.state.event_stack.append(encounters.Asylum3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Downtown")
    self.assertEqual(self.char.dollars, 3)
    self.assertIsNone(self.char.lose_turn_until)

  def testASylum3Fail(self):
    self.state.event_stack.append(encounters.Asylum3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Police")
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  def testAsylum4Pass(self):
    self.state.event_stack.append(encounters.Asylum4(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testAsylum4Fail(self):
    self.state.event_stack.append(encounters.Asylum4(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)

  def testAsylum6Pass(self):
    # increase lore because it's a -2 check
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Asylum6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(self.char.stamina, 3)

  def testAsylum6Fail(self):
    # increase lore because it's a -2 check
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Asylum6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.stamina, 2)

  def testAsylum7No(self):
    self.state.event_stack.append(encounters.Asylum7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number+2)

  def testAsylum7YesPass(self):
    self.state.event_stack.append(encounters.Asylum7(self.char))
    self.char.fight_will_slider = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertIsNone(self.char.lose_turn_until)

  def testAsylum7YesFail(self):
    self.state.event_stack.append(encounters.Asylum7(self.char))
    self.char.fight_will_slider = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number+2)


class BankTest(EncounterTest):
  
  def setUp(self):
    super(BankTest, self).setUp()
    self.char.place = self.state.places["Bank"]

  def testBank2NoMoney(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    self.char.dollars = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testBank2NoPay(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Let man and his family go hungry")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(len(self.char.possessions), 0)

  def testBank2PayPass(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Pay $2")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testBank2PayFail(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Pay $2")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testBank3Fail(self):
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testBank3HandsFail(self):
    self.char.fight_will_slider = 0
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])
    # this should fail because the fight is 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testBank3RevolverPass(self):
    self.char.fight_will_slider = 0
    self.char.possessions.append(items.Revolver38())
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    # choose to use the revolver
    choose_weapons.resolve(self.state, [0])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testBank3HandsPass(self):
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])
    # this should pass because the fight is 2
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testBank4Pass(self):
    self.state.event_stack.append(encounters.Bank4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 1)

  def testBank4Fail(self):
    self.state.event_stack.append(encounters.Bank4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testBank4FailBless(self):
    self.char.bless_curse = 1
    self.state.event_stack.append(encounters.Bank4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testBank5Pass(self):
    self.state.event_stack.append(encounters.Bank5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)

  def testBank5Fail(self):
    self.state.event_stack.append(encounters.Bank5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testBank6(self):
    self.state.event_stack.append(encounters.Bank6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testBank7(self):
    self.state.event_stack.append(encounters.Bank7(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)
    self.assertEqual(self.char.sanity, 2)


class SquareTest(EncounterTest):

  def setUp(self):
    super(SquareTest, self).setUp()
    self.char.place = self.state.places["Square"]

  def testSquare1(self):
    self.state.event_stack.append(encounters.Square1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)

  def testSquare2Pass(self):
    self.state.event_stack.append(encounters.Square2(self.char))
    self.state.allies.append(assets.FortuneTeller())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(self.char.possessions[0].name, "Fortune Teller")
    
  def testSquare2Fail(self):
    self.state.event_stack.append(encounters.Square2(self.char))
    self.state.allies.append(assets.FortuneTeller())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testSquare3Pass(self):
    self.state.event_stack.append(encounters.Square3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testSquare3Fail(self):
    self.state.event_stack.append(encounters.Square3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)

  def testSquare5pass(self):
    self.state.event_stack.append(encounters.Square5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Square")

  def testSquare5Fail(self):
    self.state.event_stack.append(encounters.Square5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Downtown")

  def testSquare6NoInteract(self):
    self.state.event_stack.append(encounters.Square6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.bless_curse, 0)
    
  def testSquare6InteractFail(self):
    self.state.event_stack.append(encounters.Square6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.bless_curse, -1)

  def testSquare7Pass(self):
    self.state.event_stack.append(encounters.Square7(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    

class TrainTest(EncounterTest):

  def setUp(self):
    super(TrainTest, self).setUp()
    self.char.place = self.state.places["Train"]

  def testTrain3Stamina(self):
    self.state.event_stack.append(encounters.Train3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, 2)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 3)

  def testTrain3Split(self):
    self.state.event_stack.append(encounters.Train3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, 1)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)


class DocksTest(EncounterTest):

  def setUp(self):
    super(DocksTest, self).setUp()
    self.char.place = self.state.places["Docks"]

  def testDocks1Pass(self):
    self.state.event_stack.append(encounters.Docks1(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testDocks1Fail(self):
    self.state.event_stack.append(encounters.Docks1(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)

  def testDocks2Pass(self):
    self.state.event_stack.append(encounters.Docks2(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun(), items.Dynamite()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(self.char.possessions[1].name, "Tommy Gun")
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.place.name, "Docks")
    self.assertEqual(self.char.dollars, 3)  
    self.assertIsNone(self.char.lose_turn_until)

  def testDocks2Fail(self):
    self.state.event_stack.append(encounters.Docks2(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun(), items.Dynamite()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(self.char.possessions[1].name, "Tommy Gun")
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.place.name, "Police")
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  def testDocks3Pass(self):
    # TODO: needs to implement scaling money
    self.state.event_stack.append(encounters.Docks3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 6)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Docks")

  def testDocks3Fail(self):
    self.state.event_stack.append(encounters.Docks3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.place.name, "Merchant")

  def testDocks4PassSane(self):
    self.state.event_stack.append(encounters.Docks4(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.place.name, "Docks")

  def testDocks4FailSane(self):
    self.state.event_stack.append(encounters.Docks4(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Docks")

  def testDocks4PassInsane(self):
    self.state.event_stack.append(encounters.Docks4(self.char))
    self.char.sanity = 1
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testDocks4FailInsane(self):
    self.state.event_stack.append(encounters.Docks4(self.char))
    self.char.sanity = 2
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testDocks5Pass(self):
    self.state.event_stack.append(encounters.Docks5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)

  def testDocks5Fail(self):
    self.state.event_stack.append(encounters.Docks5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testDock7Pass(self):
    self.state.event_stack.append(encounters.Docks7(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testDock7Fail(self):
    self.state.event_stack.append(encounters.Docks7(self.char))
    self.char.stamina = 4
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 2)


class UnnamableTest(EncounterTest):

  def setUp(self):
    super(UnnamableTest, self).setUp()
    self.char.place = self.state.places["Unnamable"]

  def testUnnamable1No(self):
    self.state.event_stack.append(encounters.Unnamable1(self.char))
    self.state.allies.extend([assets.BraveGuy()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.allies), 1)

  def testUnnamable1Sane(self):
    self.state.event_stack.append(encounters.Unnamable1(self.char))
    self.state.allies.extend([assets.BraveGuy()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Brave Guy")
    self.assertEqual(len(self.state.allies), 0)

  def testUnnamable1InSane(self):
    # TODO: can't test clue token loss from going insane
    self.state.event_stack.append(encounters.Unnamable1(self.char))
    self.state.allies.extend([assets.BraveGuy()])
    self.char.sanity = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testUnnamable2YesPass(self):
    self.state.event_stack.append(encounters.Unnamable2(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(self.char.clues, 0)
    self.assertIsNone(self.char.delayed_until)

  def testUnnamable2YesFail(self):
    self.state.event_stack.append(encounters.Unnamable2(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)

  def testUnnamable2No(self):
    self.state.event_stack.append(encounters.Unnamable2(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.clues, 0)
    self.assertIsNone(self.char.delayed_until)

  def testUnnamable4Pass(self):
    self.state.event_stack.append(encounters.Unnamable4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Merchant")

  def testUnnamable4Fail(self):
    self.state.event_stack.append(encounters.Unnamable4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Unnamable")

  def testUnnamable5Pass(self):
    self.state.event_stack.append(encounters.Unnamable5(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testUnnamable5Fail(self):
    self.state.event_stack.append(encounters.Unnamable5(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testUnnamable7Pass(self):
    self.state.event_stack.append(encounters.Unnamable7(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.unique), 1)

  def testUnnamable7Fail(self):
    self.state.event_stack.append(encounters.Unnamable7(self.char))
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)


class IsleTest(EncounterTest):

  def setUp(self):
    super(IsleTest, self).setUp()
    self.char.place = self.state.places["Isle"]

  def testIsle1(self):
    self.state.event_stack.append(encounters.Isle1(self.char))
        # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testIsle2Pass(self):
    self.state.event_stack.append(encounters.Isle2(self.char))
    self.state.allies.append(assets.Mortician())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(self.char.possessions[0].name, "Mortician")
    
  def testIsle2Fail(self):
    self.state.event_stack.append(encounters.Isle2(self.char))
    self.state.allies.append(assets.Mortician())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.allies), 1)

  def testIsle3Pass(self):
    self.state.event_stack.append(encounters.Isle3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 3)

  def testIsle3Fail(self):
    self.state.event_stack.append(encounters.Isle3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)

  def testIsle4Pass(self):
    self.state.event_stack.append(encounters.Isle4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testIsle4Fail(self):
    self.state.event_stack.append(encounters.Isle4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testIsle5Pass(self):
    self.state.event_stack.append(encounters.Isle5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)

  def testIsle5Fail(self):
    self.state.event_stack.append(encounters.Isle5(self.char))
    self.char.sanity = 4
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)

  def testIsle6Fail(self):
    self.state.event_stack.append(encounters.Isle6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)

  def testIsle7Pass(self):
    self.state.event_stack.append(encounters.Isle7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)

  def testIsle7Fail(self):
    self.state.event_stack.append(encounters.Isle7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

class HospitalTest(EncounterTest):

  def testHospital1HasClues(self):
    self.char.clues = 1
    self.state.event_stack.append(encounters.Hospital1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testHospital1NoClues(self):
    self.char.clues = 0
    self.state.event_stack.append(encounters.Hospital1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testHospital2Insane(self):
    self.state.event_stack.append(encounters.Hospital2(self.char))
    self.char.sanity = 1
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Asylum")

  def testHospital2Won(self):
    self.state.event_stack.append(encounters.Hospital2(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.clues, 1)

  def testHospital2Loss(self):
    self.state.event_stack.append(encounters.Hospital2(self.char))
    self.char.sanity = 2
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.place.name, "Uptown")

  def testHospital3One(self):
    self.state.event_stack.append(encounters.Hospital3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)

  def testHospital3Two(self):
    self.state.event_stack.append(encounters.Hospital3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testHospital3Three(self):
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Hospital3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testHospital3ThreeCap(self):
    self.state.event_stack.append(encounters.Hospital3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testHospital3Four(self):
    self.state.event_stack.append(encounters.Hospital3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testHospital4Pass(self):
    self.state.event_stack.append(encounters.Hospital4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.dollars, 6)

  def testHospital4Fail(self):
    self.state.event_stack.append(encounters.Hospital4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)

  def testHospital5Pass(self):
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.Hospital5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testHospital5Fail(self):
    self.state.event_stack.append(encounters.Hospital5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testHospital6Pass(self):
    # we know these aren't actually unique items
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.Hospital6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.unique), 1)

  def testHospital6Fail(self):
    # we know these aren't actually unique items
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.Hospital6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(self.char.place.name, "Uptown")
    self.assertEqual(self.char.sanity, 2)

  def testHospital6FailInsane(self):
    # we know these aren't actually unique items
    self.char.sanity = 1
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.Hospital6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)

  def testHospital7Pass(self):
    self.state.event_stack.append(encounters.Hospital7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testHospital7Fail(self):
    self.state.event_stack.append(encounters.Hospital7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

class WoodsTest(EncounterTest):
  def testWoods1Ignore(self):
    self.state.event_stack.append(encounters.Woods1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods1Zero(self):
    self.state.event_stack.append(encounters.Woods1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods1ZeroInsane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Woods1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods1One(self):
    self.char.lore_luck_slider = 3
    self.state.common.append(items.Food())
    self.state.unique.append(items.Cross())
    self.state.event_stack.append(encounters.Woods1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(self.char.dollars, 3)



  def testWoods1Two(self):
    self.char.lore_luck_slider = 2
    self.state.common.append(items.Food())
    self.state.unique.append(items.Cross())
    self.state.event_stack.append(encounters.Woods1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.state.unique), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods1Three(self):
    self.char.lore_luck_slider = 1
    self.state.common.append(items.Food())
    self.state.unique.append(items.Cross())
    self.state.event_stack.append(encounters.Woods1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(self.char.dollars, 13)

  def testWoods2Pass(self):
    self.state.event_stack.append(encounters.Woods2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Uptown")

  def testWoods2Fail(self):
    self.state.event_stack.append(encounters.Woods2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Uptown")
    self.assertEqual(self.char.stamina, 1)

  def testWoods2FailKO(self):
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Woods2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods3Pass(self):
    self.state.event_stack.append(encounters.Woods3(self.char))
    #TODO: implement shotgun
    #self.state.common.append((items.Shotgun()))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    """
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.char.common), 1)
    self.assertEqual(self.char.common[0].name, "Shotgun")
    """

  def testWoods3Fail(self):
    self.state.event_stack.append(encounters.Woods3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Uptown")
    self.assertEqual(self.char.stamina, 1)

  def testWoods3FailKO(self):
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Woods3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods4Pass(self):
    self.char.possessions.extend([items.HolyWater(), items.Revolver38()])
    self.state.event_stack.append(encounters.Woods3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.stamina, 3)

  def testWoods4Fail(self):
    self.char.possessions.extend([items.HolyWater(), items.Revolver38()])
    self.state.event_stack.append(encounters.Woods3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.stamina, 1)

  def testWoods4FailKO(self):
    self.char.possessions.extend([items.HolyWater(), items.Revolver38()])
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Woods3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods5FoodAlly(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.allies.append(assets.Dog())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dog")


  def testWoods5FoodReward(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 6)

  def testWoods5ChooseLuckAlly(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.allies.append(assets.Dog())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(self.char.possessions[1].name, "Dog")

  def testWoods5ChooseLuckReward(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(self.char.dollars, 6)

  def testWoods5ChooseLuckFail(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(self.char.dollars, 3)

  def testWoods5ForceLuckAlly(self):
    self.char.speed_sneak_slider = 2
    self.state.allies.append(assets.Dog())
    self.state.event_stack.append(encounters.Woods5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dog")

  def testWoods5ForceLuckReward(self):
    self.char.speed_sneak_slider = 2
    self.state.event_stack.append(encounters.Woods5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 6)

  def testWoods5ForceLuckFail(self):
    self.char.speed_sneak_slider = 2
    self.state.event_stack.append(encounters.Woods5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods6(self):
    raise NotImplementedError("Don't know how to implement gate and monster test")
    #TODO: implement test for Gate and Monster

  def testWoods7Decline(self):
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.clues, 0)
    self.assertIsNone(self.char.delayed_until)



  def testWoods7AcceptFail(self):
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  def testWoods7AcceptPassSkill(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    #print('\n' * 3)
    #print(self.state.event_stack)
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      #print('\n'*3)
      #print(self.state.event_stack)
      pass_choice = self.resolve_to_choice(MultipleChoice)
      #print(self.state.event_stack)
    self.assertEqual(pass_choice.choices, ["A skill", "2 spells", "4 clues"])
    pass_choice.resolve(self.state, "A skill")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Marksman")
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  def testWoods7AcceptPassSpells(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      pass_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(pass_choice.choices, ["A skill", "2 spells", "4 clues"])
    pass_choice.resolve(self.state, "2 spells")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.possessions[1].name, "HolyWater")
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  def testWoods7AcceptPassClues(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      pass_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(pass_choice.choices, ["A skill", "2 spells", "4 clues"])
    pass_choice.resolve(self.state, "4 clues")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.clues, 4)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

class MagickShoppeTest(EncounterTest):
  def testMagickShoppe1(self):
    self.state.event_stack.append(encounters.MagickShoppe1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testMagickShoppe1Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.MagickShoppe1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testMagickShoppe2(self):
    self.state.event_stack.append(encounters.MagickShoppe2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(
      sorted(choice.choices),
      sorted([
        placename
        for placename, place in self.state.places.items()
        if isinstance(place, places.Street)
      ])
    )
    choice.resolve(self.state, "Uptown")
    raise NotImplementedError("Don't know how to test that a location deck is face up")

  def testMagickShoppe3Poor(self):
    self.state.event_stack.append(encounters.MagickShoppe3(self.char))
    self.resolve_until_done()

  def testMagickShoppe3Decline(self):
    self.char.dollars = 5
    self.state.event_stack.append(encounters.MagickShoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "No")
    self.resolve_until_done()

  def testMagickShoppe3Empty(self):
    self.char.dollars = 5
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.MagickShoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.char.possessions), 0)

  def testMagickShoppe3Gold(self):
    self.char.dollars = 5
    self.char.lore_luck_slider = 2
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.MagickShoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 10)
    self.assertEqual(len(self.char.possessions), 0)

  def testMagickShoppe3Jackpot(self):
    self.char.dollars = 5
    self.char.lore_luck_slider = 1
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.MagickShoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.char.possessions), 2)

  def testMagickShoppe4Pass(self):
    self.state.event_stack.append(encounters.MagickShoppe4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testMagickShoppe4Fail(self):
    self.state.event_stack.append(encounters.MagickShoppe4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testMagickShoppe5(self):
    self.state.event_stack.append(encounters.MagickShoppe5(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testMagickShoppe6Fail(self):
    self.state.event_stack.append(encounters.MagickShoppe6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()

  def testMagickShoppe6PassDecline(self):
    self.state.unique.append(items.Cross()) # Costs 3
    self.state.event_stack.append(encounters.MagickShoppe6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "No")
    self.resolve_until_done()

  def testMagickShoppe6PassAccept(self):
    self.state.unique.append(items.Cross()) # Costs 3
    self.state.event_stack.append(encounters.MagickShoppe6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
        buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testMagickShoppe6PassPoor(self):
    self.char.dollars = 2
    self.state.event_stack.append(encounters.MagickShoppe6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)

  def testMagickShoppe7(self):
    self.assertEqual(self.char.sanity, 3)
    self.state.event_stack.append(encounters.MagickShoppe7(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.place.name, "Uptown")

  def testMagickShoppe7Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.MagickShoppe7(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")


if __name__ == '__main__':
  unittest.main()
