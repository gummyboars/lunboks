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
    self.assertEqual(self.char.luck, 2)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(len(self.state.skills), 2)


class AdministrationTest(EncounterTest):

  def setUp(self):
    super(AdministrationTest, self).setUp()
    self.char.place = self.state.places["Administration"]

  def testAdministration7Pass(self):
    self.char.dollars = 7
    self.state.event_stack.append(encounters.Administration7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 15)
    self.assertIsNone(self.char.lose_turn_until)
    self.assertEqual(self.char.place.name, "Administration")

  def testAdministration7Fail(self):
    self.char.dollars = 7
    self.state.event_stack.append(encounters.Administration7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)
    self.assertEqual(self.char.place.name, "Police")


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

if __name__ == '__main__':
  unittest.main()
