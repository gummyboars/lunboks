#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import abilities
from eldritch import assets
from eldritch import encounters
from eldritch import events
from eldritch import gate_encounters
from eldritch.events import *
from eldritch import items
from eldritch import monsters
from eldritch.test_events import EventTest


class EncounterTest(EventTest):

  def setUp(self):
    super().setUp()
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

  def testDrawLodgeEncounter(self):
    self.char.place = self.state.places["Lodge"]
    self.state.places["FrenchHill"].encounters = [
        encounters.EncounterCard(
            "FrenchHill5", {"Lodge": encounters.Lodge5, "Sanctum": encounters.Sanctum5},
        )
    ]
    self.state.turn_idx = 0
    self.state.turn_phase = "movement"
    self.state.next_turn()
    self.assertEqual(self.char.clues, 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)

  def testDrawLodgeEncounterWithMembership(self):
    self.char.place = self.state.places["Lodge"]
    self.char.lodge_membership = True
    self.state.places["FrenchHill"].encounters = [
        encounters.EncounterCard(
            "FrenchHill5", {"Lodge": encounters.Lodge5, "Sanctum": encounters.Sanctum5},
        )
    ]
    self.state.turn_idx = 0
    self.state.turn_phase = "movement"
    self.state.next_turn()
    self.assertEqual(self.char.clues, 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testDrawEncounterFromChoice(self):
    self.char.place = self.state.places["Graveyard"]
    self.state.places["University"].encounters = [
        encounters.EncounterCard("University2", {"Administration": encounters.Administration2})]
    choice = PlaceChoice(self.char, "choose a place", choice_filters={"locations"})
    enc = Encounter(self.char, choice)
    self.state.event_stack.append(Sequence([choice, enc], self.char))
    loc_choice = self.resolve_to_choice(PlaceChoice)
    loc_choice.resolve(self.state, "Administration")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testDrawEncounterInStreet(self):
    self.char.place = self.state.places["Graveyard"]
    self.char.sanity = 3
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown6", {"Graveyard": encounters.Graveyard6})]
    choice = PlaceChoice(self.char, "choose a place", choice_filters={"locations", "streets"})
    enc = Encounter(self.char, choice)
    self.state.event_stack.append(Sequence([choice, enc], self.char))
    loc_choice = self.resolve_to_choice(PlaceChoice)
    loc_choice.resolve(self.state, "University")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)

  def testDrawEncounterNoChoices(self):
    self.char.place = self.state.places["Graveyard"]
    self.char.sanity = 3
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown6", {"Graveyard": encounters.Graveyard6})]
    choice = PlaceChoice(self.char, "choose a place", choice_filters={"closed"})
    enc = Encounter(self.char, choice)
    self.state.event_stack.append(Sequence([choice, enc], self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)

  # TODO: add a test for a gate.


class DinerTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Diner"]

  def testDiner1DontPay(self):
    self.state.event_stack.append(encounters.Diner1(self.char))
    spend_choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(spend_choice.choices, ["Spend", "No Thanks"])
    spend_choice.resolve(self.state, "No Thanks")

    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 3)

  def testDiner1ThreeDollars(self):
    self.state.event_stack.append(encounters.Diner1(self.char))
    spend_choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(spend_choice.choices, ["Spend", "No Thanks"])
    self.spend("dollars", 3, spend_choice)
    with self.assertRaises(AssertionError):
      spend_choice.spend("dollars")
    spend_choice.resolve(self.state, "Spend")

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
    spend_choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(spend_choice.choices, ["Spend", "No Thanks"])
    self.spend("dollars", 7, spend_choice)
    with self.assertRaises(AssertionError):  # You cannot choose to spend seven dollars.
      spend_choice.resolve(self.state, "Spend")
    self.spend("dollars", -3, spend_choice)
    spend_choice.resolve(self.state, "Spend")

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
    spend_choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(spend_choice.choices, ["Spend", "No Thanks"])
    with self.assertRaises(AssertionError):
      spend_choice.spend("dollars")
    spend_choice.resolve(self.state, "No Thanks")
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 0)

  def testDiner2Draw(self):
    self.state.common.append(items.Food(0))
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
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Pay $1")
    choice.resolve(self.state, "Go Hungry")
    self.assertEqual(self.char.stamina, 3)

  def testDiner3DontPay(self):
    self.state.event_stack.append(encounters.Diner3(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Go Hungry")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testDiner3Pay(self):
    self.state.event_stack.append(encounters.Diner3(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 1, choice)
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
    super().setUp()
    self.char.place = self.state.places["Roadhouse"]

  def testRoadhouse1Clueless(self):
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testRoadhouse1No(self):
    self.char.clues = 3
    self.state.allies.append(assets.TravelingSalesman())
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testRoadhouse1Yes(self):
    self.char.clues = 3
    self.state.allies.append(assets.TravelingSalesman())
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 3, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Traveling Salesman")

  def testRoadhouse1Reward(self):
    self.char.clues = 3
    self.state.common.extend([items.Revolver38(0), items.Food(0)])
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 3, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(self.char.possessions[1].name, "Food")

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

  def testRoadhouse6FailMoney(self):
    self.char.dollars = 23
    self.char.possessions.append(assets.Dog())
    self.state.event_stack.append(encounters.Roadhouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Item")  # The ally is not an item that can be lost.
    choice.resolve(self.state, "Money")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.place.name, "Easttown")

  def testRoadhouse6FailItem(self):
    self.char.dollars = 23
    self.char.possessions.append(items.Derringer18(0))
    self.state.event_stack.append(encounters.Roadhouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Item")
    choice = self.resolve_to_choice(ItemCountChoice)
    # Cannot avoid this even if the derringer is your only item, because you actively chose to lose
    # an item instead of choosing to lose all your money.
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "done")
    self.choose_items(choice, [".18 Derringer0"])
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 23)
    self.assertEqual(len(self.char.possessions), 0)
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
    super().setUp()
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
    self.state.common.append(items.Revolver38(0))
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
    self.state.common.append(items.Revolver38(0))
    self.state.event_stack.append(encounters.Police4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testPolice5Bribe(self):
    self.char.dollars = 10
    self.char.possessions.extend([assets.Dog(), items.HolyWater(0), items.Derringer18(0)])
    self.state.event_stack.append(encounters.Police5(self.char))
    choice = self.resolve_to_choice(SpendMixin)
    self.spend("dollars", 5, choice)
    choice.resolve(self.state, "Bribe ($5)")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(self.char.dollars, 5)

  def testPolice5Discard(self):
    self.char.dollars = 10
    self.char.possessions.extend([assets.Dog(), items.HolyWater(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Police5(self.char))
    choice = self.resolve_to_choice(SpendMixin)
    choice.resolve(self.state, "Discard Weapons")
    discard = self.resolve_to_choice(ItemChoice)
    discard.resolve(self.state, ".38 Revolver0")
    with self.assertRaises(AssertionError):
      discard.resolve(self.state, "done")
    discard.resolve(self.state, "Holy Water0")
    discard.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.dollars, 10)

  def testPolice5DiscardDerringer(self):
    self.char.dollars = 10
    self.char.possessions.extend([assets.Dog(), items.HolyWater(0), items.Derringer18(0)])
    self.state.event_stack.append(encounters.Police5(self.char))
    choice = self.resolve_to_choice(SpendMixin)
    choice.resolve(self.state, "Discard Weapons")
    discard = self.resolve_to_choice(ItemChoice)
    discard.resolve(self.state, ".18 Derringer0")
    with self.assertRaises(AssertionError):
      discard.resolve(self.state, "done")
    discard.resolve(self.state, ".18 Derringer0")  # Deselect
    discard.resolve(self.state, "Holy Water0")
    discard.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.dollars, 10)

  def testPolice6Pass(self):
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Police6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.possessions[0].name, "Holy Water")
    self.assertFalse(self.state.unique)

  def testPolice6Fail(self):
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Police6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertFalse(self.char.possessions)
    self.assertEqual(len(self.state.unique), 1)

  def testPolice7Pass(self):
    self.state.common.append(items.ResearchMaterials(0))
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
    self.state.common.append(items.ResearchMaterials(0))
    self.state.event_stack.append(encounters.Police7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.char.possessions), 0)


class LodgeTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Lodge"]

  def testLodge1Pass(self):
    self.state.event_stack.append(encounters.Lodge1(self.char))
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Cross", "Holy Water"])
    choice.resolve(self.state, "Cross")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)

  def testLodge1Fail(self):
    self.state.event_stack.append(encounters.Lodge1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testLodge2PassAlly(self):
    self.state.event_stack.append(encounters.Lodge2(self.char))
    self.state.allies.append(assets.Thief())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Thief")

  def testLodge2PassReward(self):
    self.state.event_stack.append(encounters.Lodge2(self.char))
    self.state.unique.append(items.HolyWater(0))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testLodge2Fail(self):
    self.state.event_stack.append(encounters.Lodge2(self.char))
    self.state.unique.append(items.HolyWater(0))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testLodge3Pass(self):
    self.state.event_stack.append(encounters.Lodge3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testLodge3Fail(self):
    self.state.event_stack.append(encounters.Lodge3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testLodge4Join(self):
    self.state.event_stack.append(encounters.Lodge4(self.char))
    self.char.dollars = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testLodge4DeclinePass(self):
    self.state.event_stack.append(encounters.Lodge4(self.char))
    self.char.dollars = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testLodge4DeclineFail(self):
    self.state.event_stack.append(encounters.Lodge4(self.char))
    self.char.stamina = 4
    self.char.dollars = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "FrenchHill")

  def testLodge4DeclineFailKO(self):
    self.state.event_stack.append(encounters.Lodge4(self.char))
    self.char.dollars = 3
    self.char.stamina = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testLodge5Pass(self):
    self.state.event_stack.append(encounters.Lodge5(self.char))
    self.assertEqual(self.char.clues, 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(self.char.place.name, "Lodge")

  def testLodge5Fail(self):
    self.state.event_stack.append(encounters.Lodge5(self.char))
    self.char.clues = 8
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      # They get the opportunity to spend clue tokens on this failed check, but don't.
      choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Done")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.place.name, "FrenchHill")

  def testLodge6Join(self):
    self.state.event_stack.append(encounters.Lodge6(self.char))
    self.char.dollars = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testLodge7Fail(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 2)

  def testLodge7PassCC(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 3, 3])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testLodge7PassCU(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 3, 5])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.state.unique), 1)

  def testLodge7PassUU(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 5, 5])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 0)

  def testSanctum1Pass(self):
    self.state.event_stack.append(encounters.Sanctum1(self.char))
    self.char.lore_luck_slider = 0
    self.state.unique.extend([items.Cross(0), items.HolyWater(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Cross", "Holy Water", "Tommy Gun"])
    choice.resolve(self.state, "Holy Water")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testSanctum1Fail(self):
    self.state.event_stack.append(encounters.Sanctum1(self.char))
    self.char.lore_luck_slider = 0
    self.state.unique.extend([items.Cross(0), items.HolyWater(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testSanctum2Decline(self):
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.assertEqual(self.char.sanity, 3)

  def testSanctum2Pass(self):
    self.state.monsters[1].place = self.state.places["Uptown"]
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MonsterOnBoardChoice)
    self.assertEqual(choice.choices, ["Maniac1"])
    choice.resolve(self.state, "Maniac1")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertIsNone(self.state.monsters[1].place)
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0].name, "Maniac")

  def testSanctum2PassNoMonsters(self):
    # TODO: if we decide they cannot choose yes when there are no monters, rewrite this test.
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertIsNotNone(self.state.monsters[0].place)
    self.assertIsNotNone(self.state.monsters[1].place)
    self.assertEqual(len(self.char.trophies), 0)

  def testSanctum2Fail(self):
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertIsNotNone(self.state.monsters[0].place)
    self.assertIsNotNone(self.state.monsters[1].place)
    self.assertEqual(len(self.char.trophies), 0)

  def testSanctum3OneSan(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Sanctum3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1])
    choice.resolve(self.state, 0)
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 1)

  def testSanctum3OneSanInsane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Sanctum3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1])
    choice.resolve(self.state, 1)
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)

  def testSanctum3TwoSanInsane(self):
    self.char.sanity = 2
    self.state.event_stack.append(encounters.Sanctum3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1, 2])
    choice.resolve(self.state, 2)
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)

  def testSanctum3FourSan(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.Sanctum3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1, 2, 3])
    choice.resolve(self.state, 3)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 3)

  def testSanctum4Poor(self):
    self.char.lodge_membership = True
    self.char.dollars = 2
    self.state.event_stack.append(encounters.Sanctum4(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 3, choice)
    self.spend("dollars", -2, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Spend $3")
    choice.resolve(self.state, "Decline")
    self.resolve_until_done()
    self.assertFalse(self.char.lodge_membership)
    self.assertEqual(self.char.sanity, 1)

  def testSanctum4Decline(self):
    self.char.lodge_membership = True
    self.char.dollars = 3
    self.state.event_stack.append(encounters.Sanctum4(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Decline")
    self.resolve_until_done()
    self.assertFalse(self.char.lodge_membership)
    self.assertEqual(self.char.sanity, 1)

  def testSanctum4Accept(self):
    self.char.lodge_membership = True
    self.char.dollars = 3
    self.state.event_stack.append(encounters.Sanctum4(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Spend $3")
    self.resolve_until_done()
    self.assertTrue(self.char.lodge_membership)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 0)

  def testSanctum5Pass(self):
    self.state.event_stack.append(encounters.Sanctum5(self.char))
    self.assertEqual(self.char.bless_curse, 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testSanctum5Fail(self):
    self.state.event_stack.append(encounters.Sanctum5(self.char))
    self.assertEqual(self.char.bless_curse, 0)
    self.assertEqual(self.char.luck(self.state), 3)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)
    self.assertEqual(self.char.place.name, "Lodge")

  def testSanctum6(self):
    self.state.event_stack.append(encounters.Sanctum6(self.char))
    # TODO: A monster appears

  def testSanctum7Poor(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("clues", 1, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()

  def testSanctum7Decline(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.char.clues = 2
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()

  def testSanctum7Fail(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.char.clues = 2
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 2, choice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 2)

  def testSanctum7Pass(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.char.clues = 2
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 2, choice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      # TODO: Choose gate to close
      self.resolve_until_done()


class WitchHouseTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["WitchHouse"]

  def testWitchHouse1Fail(self):
    self.state.allies.extend([assets.PoliceDetective()])
    self.state.event_stack.append(encounters.WitchHouse1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testWitchHouse1PassAlly(self):
    self.state.allies.extend([assets.PoliceDetective()])
    self.state.event_stack.append(encounters.WitchHouse1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Police Detective")

  def testWitchHouse1PassReward(self):
    # TODO: ally not available
    # self.state.event_stack.append(encounters.WitchHouse1(self.char))
    # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
    #   self.resolve_until_done()
    # self.assertEqual(len(self.char.possessions), 0)
    # self.assertEqual(self.char.clues, 2)
    pass

  def testWitchHouse2Pass(self):
    self.state.event_stack.append(encounters.WitchHouse2(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testWitchHouse2None(self):
    self.state.event_stack.append(encounters.WitchHouse2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testWitchHouse2Fail(self):
    self.state.event_stack.append(encounters.WitchHouse2(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testWitchHouse3Zero(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.WitchHouse3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)

  def testWitchHouse3ZeroInsane(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.WitchHouse3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testWitchHouse3One(self):
    self.char.lore_luck_slider = 3
    self.state.event_stack.append(encounters.WitchHouse3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)

  def testWitchHouse3Two(self):
    self.char.lore_luck_slider = 2
    self.char.stamina = 3
    self.state.event_stack.append(encounters.WitchHouse3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testWitchHouse3Three(self):
    self.char.lore_luck_slider = 1
    self.char.stamina = 2
    self.state.event_stack.append(encounters.WitchHouse3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testWitchHouse4(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.WitchHouse4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testWitchHouse4Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.WitchHouse4(self.char))
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testWitchHouse5(self):
    # TODO: A gate and monster appear
    pass

  def testWitchHouse6One(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.WitchHouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)

  def testWitchHouse6OneInsane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.WitchHouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)

  def testWitchHouse6Three(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.WitchHouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 3)

  def testWitchHouse6ThreeInsane(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.WitchHouse6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 2)

  def testWitchHouse7Pass(self):
    self.state.event_stack.append(encounters.WitchHouse7(self.char))
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testWitchHouse7Fail(self):
    self.state.event_stack.append(encounters.WitchHouse7(self.char))
    self.char.possessions.extend([
        abilities.Marksman(0), assets.Dog(), items.Food(0), items.TommyGun(0),
    ])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(events.ItemChoice)
    self.assertEqual(choice.choices, ["Food0", "Tommy Gun0"])
    self.choose_items(choice, ["Tommy Gun0"])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual([item.name for item in self.char.possessions], ["Marksman", "Dog", "Food"])


class SocietyTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Society"]
    # I cast GUN!
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])

  def testSociety1No(self):
    self.state.event_stack.append(encounters.Society1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Society")

  def testSociety1Yes(self):
    self.state.event_stack.append(encounters.Society1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.state.places["Uptown"].encounters = [
        encounters.EncounterCard(
            "Uptown1", {
                "Hospital": encounters.Hospital1,
                "Woods": encounters.Woods1,
                "Shoppe": encounters.Shoppe1,
            },
        ),
        encounters.EncounterCard(
            "Uptown2", {
                "Hospital": encounters.Hospital2,
                "Woods": encounters.Woods2,
                "Shoppe": encounters.Shoppe2,
            },
        ),
    ]

    choice2 = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice2.choices[0][0:6], "Uptown")
    self.assertEqual(choice2.choices[1][0:6], "Uptown")
    self.assertEqual(self.char.place.name, "Woods")

  def testSociety2Broke(self):
    self.state.event_stack.append(encounters.Society2(self.char))
    self.char.dollars = 2
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 3, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    self.spend("dollars", -2, choice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.place.name, "Southside")

  def testSociety2No(self):
    self.state.event_stack.append(encounters.Society2(self.char))
    self.char.dollars = 5
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.place.name, "Southside")

  def testSociety2YesPass(self):
    self.state.event_stack.append(encounters.Society2(self.char))
    self.char.dollars = 5
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(self.char.place.name, "Society")

  def testSociety2YesFail(self):
    self.state.event_stack.append(encounters.Society2(self.char))
    self.state.gate_cards.clear()
    self.state.gate_cards.append(gate_encounters.GateCard(
        "Gate10", {"blue"}, {"Other": gate_encounters.Dreamlands10}))
    self.char.dollars = 5
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.place.name, "Society")
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.delayed_until, self.state.turn_idx + 2)

  def testSociety3Pass(self):
    self.state.event_stack.append(encounters.Society3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Society")

  def testSociety3Fail(self):
    self.state.event_stack.append(encounters.Society3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Southside")
    self.assertEqual(self.char.bless_curse, -1)

  def testSociety3FailBless(self):
    self.state.event_stack.append(encounters.Society3(self.char))
    self.char.bless_curse = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Southside")
    self.assertEqual(self.char.bless_curse, 0)

  def testSociety3FailUnconcious(self):
    self.state.event_stack.append(encounters.Society3(self.char))
    self.char.stamina = 2
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")
    self.assertEqual(self.char.bless_curse, -1)

  def testSociety4Pass(self):
    self.state.event_stack.append(encounters.Society4(self.char))
    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Marksman")
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)
    self.assertEqual(len(self.state.skills), 1)

  def testSociety4Fail(self):
    self.state.event_stack.append(encounters.Society4(self.char))
    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
    self.char.lore_luck_slider = 2
    self.assertEqual(self.char.luck(self.state), 2)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(len(self.state.skills), 2)

  def testSociety5(self):
    self.state.event_stack.append(encounters.Society5(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testSociety5Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Society5(self.char))
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testSociety6NoTrophy(self):
    self.state.allies.append(assets.OldProfessor())
    self.state.event_stack.append(encounters.Society6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertNotIn(0, self.state.usables)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testSociety6TrophyNo(self):
    self.char.trophies.append(self.state.gates.popleft())
    self.state.allies.append(assets.OldProfessor())
    self.state.event_stack.append(encounters.Society6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testSociety6TrophyYesAlly(self):
    self.char.trophies.append(self.state.gates.popleft())
    self.state.allies.append(assets.OldProfessor())
    self.state.event_stack.append(encounters.Society6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.use_handle(0, self.char.trophies[0].handle)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Old Professor")

  def testSociety6TrohyYesNoAlly(self):
    self.char.trophies.append(self.state.gates.popleft())
    self.state.event_stack.append(encounters.Society6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.use_handle(0, self.char.trophies[0].handle)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testSociety7No(self):
    self.state.event_stack.append(encounters.Society7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Society")

  def testSociety7Yes(self):
    self.state.event_stack.append(encounters.Society7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")

    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard(
            "Rivertown1",  {
                "Cave": encounters.Cave1,
                "Store": encounters.Store1,
                "Graveyard": encounters.Graveyard1,
            },
        ),
        encounters.EncounterCard(
            "Rivertown2", {
                "Cave": encounters.Cave2,
                "Store": encounters.Store2,
                "Graveyard": encounters.Graveyard2,
            },
        ),
    ]

    choice2 = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice2.choices[0][0:9], "Rivertown")
    self.assertEqual(choice2.choices[1][0:9], "Rivertown")
    self.assertEqual(self.char.place.name, "Cave")


class HouseTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["House"]
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])

  def testHouse1Pass(self):
    self.state.event_stack.append(encounters.House1(self.char))
    self.state.gate_cards.clear()
    # This could use an actual dreamlands encounter where something happens
    self.state.gate_cards.append(gate_encounters.GateCard(
        "Gate10", {"blue"}, {"Other": gate_encounters.Other29}))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "House")
    self.assertEqual(self.char.stamina, 2)

  def testHouse1Fail(self):
    self.state.event_stack.append(encounters.House1(self.char))
    self.state.gate_cards.clear()
    self.state.gate_cards.append(gate_encounters.GateCard(
        "Gate10", {"blue"},
        {"Abyss": gate_encounters.Abyss10, "Other": gate_encounters.Dreamlands10},
    ))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "House")
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.delayed_until, self.state.turn_idx + 2)

  def testHouse2No(self):
    self.state.event_stack.append(encounters.House2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "House")

  def testHouse2Yes(self):
    self.state.event_stack.append(encounters.House2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.state.places["FrenchHill"].encounters = [
        encounters.EncounterCard(
            "FrenchHill1", {
                "Lodge": encounters.Lodge1,
                "WitchHouse": encounters.WitchHouse1,
                "Sanctum": encounters.Sanctum1,
            },
        ),
        encounters.EncounterCard(
            "FrenchHill2", {
                "Lodge": encounters.Lodge2,
                "WitchHouse": encounters.WitchHouse2,
                "Sanctum": encounters.Sanctum2,
            },
        ),
    ]
    choice2 = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice2.choices[0][0:10], "FrenchHill")
    self.assertEqual(choice2.choices[1][0:10], "FrenchHill")
    self.assertEqual(self.char.place.name, "Lodge")

  def testHouse3(self):
    self.state.event_stack.append(encounters.House3(self.char))
    self.char.stamina = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)

  def testHouse4No(self):
    self.state.event_stack.append(encounters.House4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.assertIsNone(self.char.delayed_until)

  def testHouse4YesFail(self):
    self.state.event_stack.append(encounters.House4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.delayed_until, self.state.turn_number+2)

  def testHouse5(self):
    self.state.event_stack.append(encounters.House5(self.char))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(len(self.state.common), 1)

  def testHouse6Pass(self):
    self.state.event_stack.append(encounters.House6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testHouse6FailSanity(self):
    self.state.event_stack.append(encounters.House6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Sanity")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 2)

  def testHouse6FailStamina(self):
    self.state.event_stack.append(encounters.House6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Stamina")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 3)

  def testHouse7Poor(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 2
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testHouse7No(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 5
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testHouse7Yes0(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 5
    self.char.sanity = 1
    self.char.stamina = 1
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    choice2 = self.resolve_to_choice(MultipleChoice)
    choice2.resolve(self.state, 0)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 1)

  def testHouse7Yes1(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 5
    self.char.sanity = 1
    self.char.stamina = 1
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    choice2 = self.resolve_to_choice(MultipleChoice)
    choice2.resolve(self.state, 1)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 2)

  def testHouse7Yes2(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 5
    self.char.sanity = 1
    self.char.stamina = 1
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    choice2 = self.resolve_to_choice(MultipleChoice)
    choice2.resolve(self.state, 2)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testHouse7Yes3(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 5
    self.char.sanity = 1
    self.char.stamina = 1
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    choice2 = self.resolve_to_choice(MultipleChoice)
    choice2.resolve(self.state, 3)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 4)

  def testHouse7Yes4(self):
    self.state.event_stack.append(encounters.House7(self.char))
    self.char.dollars = 5
    self.char.sanity = 1
    self.char.stamina = 1
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    choice2 = self.resolve_to_choice(MultipleChoice)
    choice2.resolve(self.state, 4)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 5)


class ChurchTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Church"]
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])

  def testChurch1(self):
    self.state.event_stack.append(encounters.Church1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testChurch1Insane(self):
    self.state.event_stack.append(encounters.Church1(self.char))
    self.char.sanity = 1
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testChurch2(self):
    self.state.event_stack.append(encounters.Church2(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 1)

  def testChurch2Curse(self):
    self.char.bless_curse = -1
    self.state.event_stack.append(encounters.Church2(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testChurch3Money(self):
    self.char.dollars = 7
    self.char.possessions.append(items.Food(0))
    self.state.event_stack.append(encounters.Church3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Money")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(len(self.char.possessions), 1)

  def testChurch3Items(self):
    self.char.dollars = 7
    self.char.possessions.extend([
        assets.Dog(), abilities.Marksman(0), items.Food(0), items.Food(1), items.TommyGun(0),
    ])
    self.state.event_stack.append(encounters.Church3(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Items")
    choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(choice, ["Food0", "Food1"])
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 7)
    self.assertEqual(len(self.char.possessions), 3)

  def testChurch4No(self):
    self.state.event_stack.append(encounters.Church4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testChurch4Yes(self):
    self.state.event_stack.append(encounters.Church4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")
    self.assertEqual(len(self.state.unique), 1)

  def testChurch5Fail(self):
    self.state.event_stack.append(encounters.Church5(self.char))
    self.char.sanity = 5
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.place.name, "Southside")

  def testChurch5Pass1(self):
    self.state.event_stack.append(encounters.Church5(self.char))
    self.char.lore_luck_slider = 3
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.place.name, "Southside")

  def testChurch5Pass2(self):
    self.state.event_stack.append(encounters.Church5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.place.name, "Church")

  def testChurch6NoClues(self):
    self.state.event_stack.append(encounters.Church6(self.char))
    self.assertEqual(self.char.clues, 0)
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("clues", 1, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testChurch6CluesNo(self):
    self.state.event_stack.append(encounters.Church6(self.char))
    self.char.clues = 2
    self.assertEqual(self.char.clues, 2)
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)

  def testChurch6CluesYesPass(self):
    self.state.ancient_one.doom = 2
    self.state.event_stack.append(encounters.Church6(self.char))
    self.char.clues = 2
    self.assertEqual(self.char.clues, 2)
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.state.ancient_one.doom, 1)

  def testChurch6CluesYesFail(self):
    self.state.ancient_one.doom = 2
    self.state.event_stack.append(encounters.Church6(self.char))
    self.char.clues = 2
    self.assertEqual(self.char.clues, 2)
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.state.ancient_one.doom, 2)

  def testChurch7Pass(self):
    self.state.event_stack.append(encounters.Church7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Southside")

  def testChurch7Fail(self):
    self.state.event_stack.append(encounters.Church7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Southside")


class AdministrationTest(EncounterTest):

  def setUp(self):
    super().setUp()
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
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
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
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
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
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
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
    super().setUp()
    self.char.place = self.state.places["Library"]

  def testLibrary1Fail(self):
    self.state.event_stack.append(encounters.Library1(self.char))
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "University")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testLibrary2Fail(self):
    self.state.event_stack.append(encounters.Library2(self.char))
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])
    self.state.spells.extend([items.HolyWater(1), items.Cross(1)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "University")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.state.spells), 2)

  def testLibrary2Pass2(self):
    self.state.event_stack.append(encounters.Library2(self.char))
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])
    self.state.spells.extend([items.HolyWater(1), items.Cross(1)])
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
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])
    # give me spells and I'll use them!
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state, ".38 Revolver")
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
    self.state.unique.extend([items.HolyWater(0), items.Cross(0)])
    # Yeah, yeah, these aren't spells
    self.state.spells.extend([items.Revolver38(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state, "Tommy Gun")
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

  def testLibrary3Devoured(self):
    self.char.sanity = 1
    self.char.stamina = 1
    self.state.event_stack.append(encounters.Library3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)

  def testLibrary4(self):
    self.state.event_stack.append(encounters.Library4(self.char))
    self.state.gate_cards.clear()
    self.state.gate_cards.append(gate_encounters.GateCard(
        "Gate10", {"blue"}, {"Other": gate_encounters.Dreamlands10}))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Library")
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.delayed_until, self.state.turn_idx + 2)

  def testLibrary5(self):
    self.state.event_stack.append(encounters.Library5(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testLibrary6Pass(self):
    self.char.dollars = 8
    self.state.event_stack.append(encounters.Library6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 4, choice)
    choice.resolve(self.state, "Pay $4")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)
    self.assertEqual(self.char.place.name, "Library")

  def testLibrary6Fail(self):
    self.state.event_stack.append(encounters.Library6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 4, choice)
    self.spend("dollars", -3, choice)
    choice.resolve(self.state, "Oops")
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
    super().setUp()
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
    self.state.spells.extend([items.Wither(0), items.Shrivelling(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Wither")

  def testScience2Fail(self):
    self.char.possessions.extend([items.Food(0), items.Food(1), items.Food(2), items.Food(3)])
    self.state.event_stack.append(encounters.Science2(self.char))
    self.state.spells.extend([items.Wither(0), items.Shrivelling(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(choice, ["Food2"])
    self.resolve_until_done()
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(len(self.char.possessions), 4)
    self.assertIn("Wither0", [item.handle for item in self.char.possessions])
    self.assertNotIn("Food2", [item.handle for item in self.char.possessions])

  def testScience3WithSpells(self):
    self.state.event_stack.append(encounters.Science3(self.char))
    self.char.possessions.extend([items.Wither(0), items.Wither(1), items.Shrivelling(0)])
    self.state.unique.append(items.HolyWater(0))
    self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(self.char.place.name, "Science")

  def testScience3WithOtherItems(self):
    self.state.event_stack.append(encounters.Science3(self.char))
    self.char.possessions.extend([items.Wither(0), items.Revolver38(0), items.TommyGun(0)])
    self.state.unique.append(items.HolyWater(0))
    self.resolve_until_done()
    self.assertFalse(self.state.unique)
    self.assertEqual(len(self.char.possessions), 4)
    self.assertEqual(self.char.possessions[3].name, "Holy Water")
    self.assertEqual(self.char.place.name, "University")

  def testScience3WithoutSpells(self):
    self.state.event_stack.append(encounters.Science3(self.char))
    self.char.possessions.extend([items.Wither(0), items.Shrivelling(0)])
    self.state.unique.append(items.HolyWater(0))
    self.resolve_until_done()
    self.assertFalse(self.state.unique)
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(self.char.possessions[2].name, "Holy Water")
    self.assertEqual(self.char.place.name, "University")

  def testScience4No(self):
    self.state.event_stack.append(encounters.Science4(self.char))
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
    self.state.allies.extend([assets.ArmWrestler()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Arm Wrestler")
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Science")

  def testScience4Reward(self):
    self.char.dollars = 3
    self.state.event_stack.append(encounters.Science4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Science")
    self.assertEqual(self.char.dollars, 8)

  def testScience4YesUnconcious(self):
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Science4(self.char))
    self.state.allies.extend([assets.ArmWrestler()])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
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
    self.assertEqual(choice.choices, [0, 1, 2, 3, 4, 5])
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
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")


class AsylumTest(EncounterTest):

  def setUp(self):
    super().setUp()
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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.place.name, "Asylum")

  def testAsylum2Fail(self):
    self.state.event_stack.append(encounters.Asylum2(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testAsylum4Fail(self):
    self.state.event_stack.append(encounters.Asylum4(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
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
    super().setUp()
    self.char.place = self.state.places["Bank"]

  def testBank1Move(self):
    self.state.event_stack.append(encounters.Bank1(self.char))
    choice = self.resolve_to_choice(PlaceChoice)

    self.state.places["University"].encounters = [
        encounters.EncounterCard("University2", {"Administration": encounters.Administration2})]
    choice.resolve(self.state, "Administration")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.char.place.name, "Administration")

  def testBank1NoThanks(self):
    self.state.event_stack.append(encounters.Bank1(self.char))
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "No thanks")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.place.name, "Bank")

  def testBank2NoMoney(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    self.char.dollars = 1
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 2, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Pay $2")
    self.spend("dollars", -1, choice)
    choice.resolve(self.state, "Let man and his family go hungry")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 0)

  def testBank2NoPay(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Let man and his family go hungry")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(len(self.char.possessions), 0)

  def testBank2PayPass(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 2, choice)
    choice.resolve(self.state, "Pay $2")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testBank2PayFail(self):
    self.state.event_stack.append(encounters.Bank2(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 2, choice)
    choice.resolve(self.state, "Pay $2")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testBank3Fail(self):
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testBank3HandsFail(self):
    self.char.fight_will_slider = 0
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])
    # this should fail because the fight is 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testBank3RevolverPass(self):
    self.char.fight_will_slider = 0
    self.char.possessions.append(items.Revolver38(0))
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    # choose to use the revolver
    self.choose_items(choose_weapons, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testBank3HandsPass(self):
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])
    # this should pass because the fight is 2
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testBank3Spell(self):
    self.char.possessions.extend([items.Wither(0), items.RedSign(0)])
    self.state.event_stack.append(encounters.Bank3(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertIn(0, self.state.usables)
    self.assertEqual(self.state.usables[0].keys(), {"Wither0"})  # Red Sign is unusable: no monster.
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Cast")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertTrue(self.char.possessions[0].active)
    self.choose_items(choose_weapons, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[0].in_use)

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
    super().setUp()
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

  def testSquare2PassReward(self):
    self.state.event_stack.append(encounters.Square2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(self.char.clues, 2)

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

  def testSquare3Devoured(self):
    self.char.stamina = 1
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Square3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)

  def testSquare4Pass(self):
    self.char.possessions.extend([items.Food(0), items.TommyGun(0)])
    self.state.event_stack.append(encounters.Square4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)

  def testSquare4Fail(self):
    self.char.possessions.extend([items.Food(0), items.TommyGun(0)])
    self.state.event_stack.append(encounters.Square4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)

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
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testSquare7Fail(self):
    self.state.event_stack.append(encounters.Square7(self.char))
    self.assertFalse(self.state.places["Square"].gate)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertTrue(self.state.places["Square"].gate)
    monster_count = len([
        mon for mon in self.state.monsters if mon.place and mon.place.name == "Square"])
    self.assertEqual(monster_count, 1)
    self.assertEqual(self.char.place.name, self.state.places["Square"].gate.name + "1")
    self.assertEqual(self.char.delayed_until, self.state.turn_idx + 2)


class ShopTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Shop"]

  def testShop1Success2(self):
    self.state.event_stack.append(encounters.Shop1(self.char))
    self.assertEqual(self.char.luck(self.state), 3)
    self.assertEqual(self.char.bless_curse, 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testShop1Success1(self):
    self.char.lore_luck_slider = 2
    self.assertEqual(self.char.luck(self.state), 2)
    self.state.event_stack.append(encounters.Shop1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testShop1Fail(self):
    self.state.event_stack.append(encounters.Shop1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testShop2Success(self):
    self.state.event_stack.append(encounters.Shop2(self.char))
    self.state.gate_cards.clear()
    self.state.gate_cards.append(gate_encounters.GateCard(
        "Gate29", {"red"}, {"Other": gate_encounters.Other29}))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Shop")
    self.assertEqual(self.char.stamina, 3)

  def testShop2Fail(self):
    self.state.event_stack.append(encounters.Shop2(self.char))
    self.state.gate_cards.clear()
    self.state.gate_cards.append(gate_encounters.GateCard(
        "Gate29", {"red"}, {"Other": gate_encounters.Other29}))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Shop")
    self.assertEqual(self.char.stamina, 2)

  def testShop3Common(self):
    self.char.dollars = 9
    self.state.common.extend([
        items.Food(0), items.DarkCloak(0), items.DarkCloak(1), items.TommyGun(0),
    ])
    self.state.event_stack.append(encounters.Shop3(self.char))
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["common", "unique"])
    choice.resolve(self.state, "common")
    choice = self.resolve_to_choice(CardSpendChoice)
    self.spend("dollars", 2, choice)
    choice.resolve(self.state, "Dark Cloak")
    self.resolve_until_done()  # Can only buy one item.
    self.assertEqual(self.char.dollars, 7)
    self.assertEqual(self.char.possessions[0].name, "Dark Cloak")

  def testShop3Unique(self):
    self.char.dollars = 9
    self.state.unique.extend([
        items.HolyWater(0), items.HolyWater(1), items.MagicLamp(0), items.EnchantedKnife(0),
    ])
    self.state.event_stack.append(encounters.Shop3(self.char))
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["common", "unique"])
    choice.resolve(self.state, "unique")
    choice = self.resolve_to_choice(CardSpendChoice)
    self.spend("dollars", 4, choice)
    choice.resolve(self.state, "Holy Water")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testShop3BuyNothing(self):
    self.char.dollars = 9
    self.state.common.extend([
        items.Food(0), items.DarkCloak(0), items.DarkCloak(1), items.TommyGun(0),
    ])
    self.state.event_stack.append(encounters.Shop3(self.char))
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["common", "unique"])
    choice.resolve(self.state, "common")
    choice = self.resolve_to_choice(CardSpendChoice)
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 9)
    self.assertFalse(self.char.possessions)

  def testShop4Pass(self):
    self.char.possessions.extend([items.Food(0), items.TommyGun(0)])
    self.state.event_stack.append(encounters.Shop4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)

  def testShop4Fail(self):
    self.char.possessions.extend([items.Food(0), items.TommyGun(0)])
    self.state.places["Northside"].encounters = [
        encounters.EncounterCard("Shop1", {"Shop": encounters.Newspaper7}),
    ]
    self.state.event_stack.append(encounters.Shop4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.sanity, 3)

  def testShop4FailNoItems(self):
    self.char.possessions.extend([assets.Dog(), abilities.Marksman(0)])
    self.state.places["Northside"].encounters = [
        encounters.EncounterCard("Shop1", {"Shop": encounters.Newspaper7}),
    ]
    self.state.event_stack.append(encounters.Shop4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.sanity, 2)


class NewspaperTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Newspaper"]

  def testNewspaper1Move(self):
    self.state.event_stack.append(encounters.Newspaper1(self.char))
    choice = self.resolve_to_choice(PlaceChoice)
    self.assertEqual(self.char.dollars, 5)

    self.state.places["University"].encounters = [
        encounters.EncounterCard("University2", {"Administration": encounters.Administration2})]
    choice.resolve(self.state, "Administration")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.char.place.name, "Administration")

  def testNewspaper1NoThanks(self):
    self.state.event_stack.append(encounters.Newspaper1(self.char))
    choice = self.resolve_to_choice(PlaceChoice)
    self.assertEqual(self.char.dollars, 5)
    choice.resolve(self.state, "No thanks")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.place.name, "Newspaper")

  def testNewspaper2(self):
    self.state.event_stack.append(encounters.Newspaper2(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)

  def testNewspaper3(self):
    self.state.event_stack.append(encounters.Newspaper3(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.retainer_start, self.state.turn_number+2)

  def testNewspaper4(self):
    self.state.event_stack.append(encounters.Newspaper4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.retainer_start, self.state.turn_number+2)

  def testNewspaper5Pass(self):
    self.state.event_stack.append(encounters.Newspaper5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)

  def testNewspaper5Fail(self):
    self.state.event_stack.append(encounters.Newspaper5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testNewspaper6Pass(self):
    self.state.event_stack.append(encounters.Newspaper6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testNewspaper6Fail(self):
    self.state.event_stack.append(encounters.Newspaper6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testNewspaper7(self):
    self.state.event_stack.append(encounters.Newspaper7(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)


class TrainTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Train"]
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    # maybe they're magic guns? I cast bullet!
    self.state.spells.extend([items.TommyGun(0), items.Revolver38(0)])
    self.state.common.extend([items.Dynamite(0), items.Revolver38(1)])

  def testTrain1Pass(self):
    self.state.event_stack.append(encounters.Train1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.place.name, "Train")
    self.assertEqual(self.char.dollars, 3)

  def testTrain1Fail(self):
    self.state.event_stack.append(encounters.Train1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(self.char.place.name, "Police")
    self.assertEqual(self.char.dollars, 2)

  def testTrain2Pass(self):
    self.char.speed_sneak_slider = 2
    self.assertEqual(self.char.speed(self.state), 3)
    self.state.event_stack.append(encounters.Train2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tommy Gun")
    self.assertEqual(self.char.sanity, 3)

  def testTrain2Fail(self):
    self.char.speed_sneak_slider = 1
    self.assertEqual(self.char.speed(self.state), 2)
    self.state.event_stack.append(encounters.Train2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 2)

  def testTrain2FailInsane(self):
    self.char.speed_sneak_slider = 1
    self.assertEqual(self.char.speed(self.state), 2)
    self.state.event_stack.append(encounters.Train2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

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

  def testTrain5Move(self):
    self.state.event_stack.append(encounters.Train5(self.char))
    choice = self.resolve_to_choice(PlaceChoice)

    self.state.places["University"].encounters = [
        encounters.EncounterCard("University2", {"Administration": encounters.Administration2})]
    choice.resolve(self.state, "Administration")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.char.place.name, "Administration")

  def testTrain5NoThanks(self):
    self.state.event_stack.append(encounters.Train5(self.char))
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "No thanks")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.place.name, "Train")

  def testTrain6NoMoney(self):
    self.state.event_stack.append(encounters.Train6(self.char))
    self.char.dollars = 2
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 3, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    self.spend("dollars", -2, choice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 2)

  def testTrain6MoneyRefuse(self):
    self.state.event_stack.append(encounters.Train6(self.char))
    self.char.dollars = 4
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 2)

  def testTrain6MoneyAcceptPass(self):
    self.state.event_stack.append(encounters.Train6(self.char))
    self.char.dollars = 4
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 1)

  def testTrain6MoneyAcceptFail(self):
    self.state.event_stack.append(encounters.Train6(self.char))
    self.char.dollars = 4
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    self.spend("dollars", 3, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dynamite")
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.state.unique), 2)

  def testTrain7Pass(self):
    self.state.event_stack.append(encounters.Train7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.unique), 1)

  def testTrain7Fail(self):
    self.state.event_stack.append(encounters.Train7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.place.name, "Train")

  def testTrain7FailUnconcious(self):
    self.state.event_stack.append(encounters.Train7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")


class DocksTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Docks"]

  def testDocks1Pass(self):
    self.state.event_stack.append(encounters.Docks1(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testDocks1Fail(self):
    self.state.event_stack.append(encounters.Docks1(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)

  def testDocks2Pass(self):
    self.state.event_stack.append(encounters.Docks2(self.char))
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0), items.Dynamite(0)])
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
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0), items.Dynamite(0)])
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
    self.assertEqual(self.char.dollars, 3)
    self.state.event_stack.append(encounters.Docks3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)
    self.assertEqual(self.char.dollars, 9)
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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.place.name, "Docks")

  def testDocks4FailSane(self):
    self.state.event_stack.append(encounters.Docks4(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testDocks4FailInsane(self):
    self.state.event_stack.append(encounters.Docks4(self.char))
    self.char.sanity = 2
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
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

  def testDocks6Pass(self):
    self.state.event_stack.append(encounters.Docks6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Docks")

  def testDocks6Fail(self):
    self.state.event_stack.append(encounters.Docks6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")

  def testDocks7Pass(self):
    self.state.event_stack.append(encounters.Docks7(self.char))
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)

  def testDocks7Fail(self):
    self.state.event_stack.append(encounters.Docks7(self.char))
    self.char.stamina = 4
    self.state.common.extend([items.Revolver38(0), items.TommyGun(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 2)

  def testDocks7Devoured(self):
    self.state.event_stack.append(encounters.Docks7(self.char))
    self.char.stamina = 3
    self.char.sanity = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)


class UnnamableTest(EncounterTest):

  def setUp(self):
    super().setUp()
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

  def testUnnamable1SaneReward(self):
    self.state.event_stack.append(encounters.Unnamable1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.clues, 3)

  def testUnnamable1InSane(self):
    # TODO: can't test clue token loss from going insane
    self.state.event_stack.append(encounters.Unnamable1(self.char))
    self.state.allies.extend([assets.BraveGuy()])
    self.char.sanity = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.allies), 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testUnnamable2YesPass(self):
    self.state.event_stack.append(encounters.Unnamable2(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.spells), 2)
    self.assertEqual(self.char.clues, 0)
    self.assertIsNone(self.char.delayed_until)

  def testUnnamable3(self):
    self.state.event_stack.append(encounters.Unnamable3(self.char))
    self.assertFalse(self.state.places["Unnamable"].gate)
    self.resolve_until_done()
    self.assertTrue(self.state.places["Unnamable"].gate)
    monster_count = len([
        mon for mon in self.state.monsters if mon.place and mon.place.name == "Unnamable"])
    self.assertEqual(monster_count, 1)
    self.assertEqual(self.char.place.name, self.state.places["Unnamable"].gate.name + "1")
    self.assertEqual(self.char.delayed_until, self.state.turn_idx + 2)

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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.unique), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")

  def testUnnamable5Fail(self):
    self.state.event_stack.append(encounters.Unnamable5(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testUnnamable6Pass(self):
    self.state.event_stack.append(encounters.Unnamable6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Unnamable")

  def testUnnamable6Fail(self):
    self.state.event_stack.append(encounters.Unnamable6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")

  def testUnnamable7Pass(self):
    self.state.event_stack.append(encounters.Unnamable7(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.unique), 1)

  def testUnnamable7Fail(self):
    self.state.event_stack.append(encounters.Unnamable7(self.char))
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)


class IsleTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Isle"]

  def testIsle1(self):
    self.state.event_stack.append(encounters.Isle1(self.char))
    # we know these aren't actually spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.spells), 1)

  def testIsle2Pass(self):
    self.state.event_stack.append(encounters.Isle2(self.char))
    self.state.allies.append(assets.PoliceInspector())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.allies), 0)
    self.assertEqual(self.char.possessions[0].name, "Police Inspector")

  def testIsle2PassReward(self):
    self.state.event_stack.append(encounters.Isle2(self.char))
    self.char.stamina = 1
    self.char.sanity = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # pylint: disable=protected-access
    self.assertEqual(self.char.sanity, self.char._max_sanity)
    self.assertEqual(self.char.stamina, self.char._max_stamina)

  def testIsle2Fail(self):
    self.state.event_stack.append(encounters.Isle2(self.char))
    self.state.allies.append(assets.PoliceInspector())
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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Asylum")

  def testHospital2Won(self):
    self.state.event_stack.append(encounters.Hospital2(self.char))
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])
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
    self.choose_items(choose_weapons, [])
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
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    self.state.event_stack.append(encounters.Hospital6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Cross")
    self.assertEqual(len(self.state.unique), 1)

  def testHospital6Fail(self):
    # we know these aren't actually unique items
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    self.state.event_stack.append(encounters.Hospital6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
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

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Woods"]

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
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods1One(self):
    self.char.lore_luck_slider = 3
    self.state.common.append(items.Food(0))
    self.state.unique.append(items.Cross(0))
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
    self.state.common.append(items.Food(0))
    self.state.unique.append(items.Cross(0))
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
    self.state.common.append(items.Food(0))
    self.state.unique.append(items.Cross(0))
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
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods3Pass(self):
    self.state.event_stack.append(encounters.Woods3(self.char))
    # TODO: implement shotgun
    # self.state.common.append((items.Shotgun(0)))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # self.assertEqual(len(self.state.common), 0)
    # self.assertEqual(len(self.char.common), 1)
    # self.assertEqual(self.char.common[0].name, "Shotgun")

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
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods4Pass(self):
    self.char.possessions.extend([items.HolyWater(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Woods4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.stamina, 3)

  def testWoods4FailThreePlus(self):
    self.char.possessions.extend([items.HolyWater(0), items.Revolver38(0), items.TommyGun(0)])
    self.state.event_stack.append(encounters.Woods4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      loss_choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(loss_choice, ["Holy Water0", "Tommy Gun0"])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.stamina, 1)

  def testWoods4FailTwoItem(self):
    self.char.possessions.extend([items.HolyWater(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Woods4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      loss_choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(loss_choice, ["Holy Water0", ".38 Revolver0"])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)

  def testWoods4FailOneItem(self):
    self.char.possessions.extend([items.HolyWater(0)])
    self.state.event_stack.append(encounters.Woods4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      loss_choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(loss_choice, ["Holy Water0"])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)

  def testWoods4FailZeroItem(self):
    self.state.event_stack.append(encounters.Woods4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      loss_choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(loss_choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)

  def testWoods4FailKO(self):
    self.char.possessions.extend([items.HolyWater(0), items.Revolver38(0)])
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Woods4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      loss_choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(loss_choice, ["Holy Water0", ".38 Revolver0"])
    # Have to choose again when you get knocked out.
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods5FoodAlly(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food(0))
    self.state.allies.append(assets.Dog())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dog")

  def testWoods5FoodReward(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food(0))
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 6)

  def testWoods5ChooseLuckAlly(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food(0))
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
    self.char.possessions.append(items.Food(0))
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
    self.char.possessions.append(items.Food(0))
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
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dog")

  def testWoods5ForceLuckReward(self):
    self.char.speed_sneak_slider = 2
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 6)

  def testWoods5ForceLuckFail(self):
    self.char.speed_sneak_slider = 2
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.dollars, 3)

  def testWoods6(self):
    self.state.event_stack.append(encounters.Woods6(self.char))
    self.assertFalse(self.state.places["Woods"].gate)
    self.resolve_until_done()
    self.assertTrue(self.state.places["Woods"].gate)
    monster_count = len([
        mon for mon in self.state.monsters if mon.place and mon.place.name == "Woods"])
    self.assertEqual(monster_count, 1)
    self.assertEqual(self.char.place.name, self.state.places["Woods"].gate.name + "1")
    self.assertEqual(self.char.delayed_until, self.state.turn_idx + 2)

  def testWoods7Decline(self):
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.clues, 0)
    self.assertIsNone(self.char.delayed_until)

  def testWoods7AcceptFail(self):
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
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
    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      pass_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(pass_choice.choices, ["A skill", "2 spells", "4 clues"])
    pass_choice.resolve(self.state, "A skill")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Marksman")
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  #  def testWoods7AcceptPassSpells(self):
  #    self.char.lore_luck_slider = 2
  #    self.state.event_stack.append(encounters.Woods7(self.char))
  #    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
  #    # We know these aren't spells
  #    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
  #    choice = self.resolve_to_choice(MultipleChoice)
  #    self.assertEqual(choice.choices, ["Yes", "No"])
  #    choice.resolve(self.state, "Yes")
  #    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
  #      pass_choice = self.resolve_to_choice(MultipleChoice)
  #    self.assertEqual(pass_choice.choices, ["A skill", "2 spells", "4 clues"])
  #    pass_choice.resolve(self.state, "2 spells")
  #    self.resolve_until_done()
  #    self.assertEqual(len(self.char.possessions), 2)
  #    self.assertEqual(self.char.possessions[0].name, "Cross")
  #    self.assertEqual(self.char.possessions[1].name, "HolyWater")
  #    self.assertEqual(self.char.clues, 3)
  #    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  def testWoods7AcceptPassClues(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Woods7(self.char))
    self.state.skills.extend([abilities.Marksman(0), abilities.Fight(0)])
    # We know these aren't spells
    self.state.spells.extend([items.Cross(0), items.HolyWater(0)])
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


class CaveTest(EncounterTest):

  # TODO: a monster appears
  #  def testCave1Zero(self):
  #    self.char.lore_luck_slider = 3
  #    self.state.common.append(items.Food(0))
  #    self.state.event_stack.append(encounters.Cave1(self.char))
  #    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
  #      raise NotImplementedError("A monster appears")
  #      self.resolve_until_monster()
  #    self.assertEqual(len(self.state.common), 1)
  #    self.assertEqual(self.char.sanity, 2)

  def testCave1ZeroInsane(self):
    self.char.lore_luck_slider = 3
    self.char.sanity = 1
    self.state.common.append(items.Food(0))
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave1One(self):
    self.char.lore_luck_slider = 3
    self.state.common.append(items.Food(0))
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.sanity, 2)

  def testCave1OneInsane(self):
    self.char.lore_luck_slider = 3
    self.char.sanity = 1
    self.state.common.append(items.Food(0))
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave1Two(self):
    self.char.lore_luck_slider = 2
    self.state.common.append(items.Food(0))
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")

  def testCave2(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.Cave2(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testCave2Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Cave2(self.char))
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave3Pass(self):
    self.state.event_stack.append(encounters.Cave3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testCave3Fail(self):
    self.state.event_stack.append(encounters.Cave3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testCave3FailKO(self):
    self.char.stamina = 1
    self.state.event_stack.append(encounters.Cave3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

# TODO: a monster appears
#  def testCave4(self):
#    self.state.event_stack.append(encounters.Cave4(self.char))
#    raise NotImplementedError("A monster appears!")
#    self.resolve_until_monster()

  def testCave5Pass(self):
    self.char.stamina = 3
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Cave5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(self.char.stamina, 3)

  def testCave5Fail(self):
    self.char.stamina = 3
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Cave5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)
    self.assertEqual(self.char.stamina, 2)

  def testCave5FailKO(self):
    self.char.stamina = 1
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Cave5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testCave6WhiskeyAlly(self):
    self.char.possessions.append(items.Whiskey(0))
    self.state.allies.append(assets.ToughGuy())
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tough Guy")

  def testCave6WhiskeyReward(self):
    self.char.possessions.append(items.Whiskey(0))
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testCave6DeclineAlly(self):
    self.char.possessions.append(items.Whiskey(0))
    self.state.allies.append(assets.ToughGuy())
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, "Whiskey")
    self.assertEqual(self.char.possessions[1].name, "Tough Guy")

  def testCave6DeclineReward(self):
    self.char.possessions.append(items.Whiskey(0))
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, "Whiskey")
    self.assertEqual(self.char.possessions[1].name, ".38 Revolver")

  def testCave6DeclineFail(self):
    self.char.possessions.append(items.Whiskey(0))
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Whiskey")

  def testCave6NoWhiskeyAlly(self):
    self.state.allies.append(assets.ToughGuy())
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tough Guy")

  def testCave6NoWhiskeyReward(self):
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testCave6NoWhiskeyFail(self):
    self.state.common.extend([items.Food(0), items.Revolver38(0)])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testCave7Decline(self):
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 3)

  def testCave7Zero(self):
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.stamina, 2)

  def testCave7ZeroInsane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave7ZeroKO(self):
    self.char.stamina = 1
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testCave7Devoured(self):
    self.char.stamina = 1
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)

  def testCave7One(self):
    self.char.lore_luck_slider = 3
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)

  def testCave7OneInsane(self):
    self.char.lore_luck_slider = 3
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Cave7(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave7Two(self):
    pass
# TODO: Draw first tome
#    self.char.lore_luck_slider = 2
#    self.state.event_stack.append(encounters.Cave7(self.char))
#    choice = self.resolve_to_choice(MultipleChoice)
#    self.assertEqual(choice.choices, ["Yes", "No"])
#    choice.resolve(self.state, "Yes")
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
#      self.resolve_until_done()
#    raise NotImplementedError("No Tomes implemented")


class StoreTest(EncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Store"]

  def testStore1(self):
    self.state.event_stack.append(encounters.Store1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)

  def testStore2(self):
    self.state.event_stack.append(encounters.Store2(self.char))
    self.resolve_until_done()
    # Nothing happens

  def testStore3(self):
    self.state.event_stack.append(encounters.Store3(self.char))
    self.char.possessions.append(items.Food(0))
    choice = self.resolve_to_choice(ItemChoice)
    self.assertEqual(choice.choices, ["Food0"])
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()
    self.assertFalse(self.char.possessions)
    self.assertEqual(self.char.dollars, 5)

  def testStore3IllegalSale(self):
    self.state.event_stack.append(encounters.Store3(self.char))
    self.char.possessions.append(items.Food(0))
    self.char.possessions.append(items.Food(1))
    choice = self.resolve_to_choice(ItemChoice)
    self.assertEqual(choice.choices, ["Food0", "Food1"])
    with self.assertRaises(AssertionError):
      self.choose_items(choice, ["Food0", "Food1"])

  def testStore4(self):
    self.state.event_stack.append(encounters.Store4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testStore4Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Store4(self.char))
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testStore5Pass(self):
    self.state.event_stack.append(encounters.Store5(self.char))
    self.state.common.extend([items.Dynamite(0), items.TommyGun(0), items.Food(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    choice.resolve(self.state, "Food")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 2)

  def testStore5Fail(self):
    self.state.event_stack.append(encounters.Store5(self.char))
    self.state.common.extend([items.Dynamite(0), items.TommyGun(0), items.Food(0)])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 3)

  def testStore5PassSalesman(self):
    # TODO: Implement the salesman drawing an extra card
    # raise NotImplementedError("Salesman should get to draw an extra common card")
    # self.character = characters.Salesman()
    # self.char.lore_luck_slider = 2
    # self.state.common.extend([
    #     items.Revolver38(0), items.Cross(0), items.TommyGun(0), items.Dynamite(0)])
    # self.state.event_stack.append(encounters.Store5(self.char))
    # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
    #   self.resolve_until_done()
    pass

  def testStore6Decline(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.clues, 0)
    self.assertIsNone(self.char.delayed_until)

  def testStore6Poor(self):
    self.char.lore_luck_slider = 2
    self.char.dollars = 0
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 1, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testStore6Pass(self):
    self.char.lore_luck_slider = 2
    self.char.dollars = 1
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    self.spend("dollars", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)

  def testStore6Fail(self):
    self.char.lore_luck_slider = 2
    self.char.dollars = 1
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    self.spend("dollars", 1, choice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testStore7(self):
    self.state.common.append(items.Dynamite(0))
    # Why does a young child have dynamite?
    self.state.event_stack.append(encounters.Store7(self.char))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dynamite")


class ShoppeTest(EncounterTest):
  def testShoppe1(self):
    self.state.event_stack.append(encounters.Shoppe1(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testShoppe1Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Shoppe1(self.char))
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testShoppe2(self):
    # raise NotImplementedError("Don't know how to test that a location deck is face up")
    # self.state.event_stack.append(encounters.Shoppe2(self.char))
    # choice = self.resolve_to_choice(MultipleChoice)
    # self.assertEqual(
    #   sorted(choice.choices),
    #   sorted([
    #     placename
    #     for placename, place in self.state.places.items()
    #     if isinstance(place, places.Street)
    #   ])
    # )
    # choice.resolve(self.state, "Uptown")
    pass

  def testShoppe3Poor(self):
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    with self.assertRaises(AssertionError):
      self.spend("dollars", 5, choice)
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, "Yes")
    self.spend("dollars", -3, choice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()

  def testShoppe3Decline(self):
    self.char.dollars = 5
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    buy = self.resolve_to_choice(SpendChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "No")
    self.resolve_until_done()

  def testShoppe3Empty(self):
    self.char.dollars = 5
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    buy = self.resolve_to_choice(SpendChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    self.spend("dollars", 5, buy)
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.char.possessions), 0)

  def testShoppe3Gold(self):
    self.char.dollars = 5
    self.char.lore_luck_slider = 3
    self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    buy = self.resolve_to_choice(SpendChoice)
    self.spend("dollars", 5, buy)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 10)
    self.assertEqual(len(self.char.possessions), 0)

  def testShoppe3Jackpot(self):
    # TODO: Drawing multiple items
    # self.char.dollars = 5
    # self.char.lore_luck_slider = 1
    # self.state.unique.extend([items.Cross(0), items.HolyWater(0)])
    # self.state.event_stack.append(encounters.Shoppe3(self.char))
    # buy = self.resolve_to_choice(MultipleChoice)
    # self.assertEqual(buy.choices, ["Yes", "No"])
    # self.spend("dollars", 5, choice)
    # buy.resolve(self.state, "Yes")
    # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
    #   self.resolve_until_done()
    # self.assertEqual(self.char.dollars, 0)
    # self.assertEqual(len(self.char.possessions), 2)
    pass

  def testShoppe4Pass(self):
    self.state.event_stack.append(encounters.Shoppe4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, 0)

  def testShoppe4Fail(self):
    self.state.event_stack.append(encounters.Shoppe4(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, -1)

  def testShoppe5(self):
    self.state.event_stack.append(encounters.Shoppe5(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testShoppe6Fail(self):
    self.state.event_stack.append(encounters.Shoppe6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()

  def testShoppe6PassDecline(self):
    # self.state.unique.append(items.Cross(0)) # Costs 3
    # self.state.event_stack.append(encounters.Shoppe6(self.char))
    # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
    #   buy = self.resolve_to_choice(MultipleChoice)
    # self.assertEqual(buy.choices, ["Yes", "No"])
    # buy.resolve(self.state, "No")
    # self.resolve_until_done()
    pass

  def testShoppe6PassAccept(self):
    # self.state.unique.append(items.Cross(0)) # Costs 3
    # self.state.event_stack.append(encounters.Shoppe6(self.char))
    # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
    #   buy = self.resolve_to_choice(MultipleChoice)
    # self.assertEqual(buy.choices, ["Yes", "No"])
    # buy.resolve(self.state, "Yes")
    # self.resolve_until_done()
    # self.assertEqual(self.char.dollars, 1)
    # self.assertEqual(len(self.char.possessions), 1)
    # self.assertEqual(self.char.possessions[0].name, "Cross")
    pass

  def testShoppe6PassPoor(self):
    self.char.dollars = 2
    self.state.event_stack.append(encounters.Shoppe6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)

  def testShoppe7(self):
    self.assertEqual(self.char.sanity, 3)
    self.state.event_stack.append(encounters.Shoppe7(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.place.name, "Uptown")

  def testShoppe7Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Shoppe7(self.char))
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")


class GraveyardTest(EncounterTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Graveyard"]

  def testGraveyard1(self):
    self.char.speed_sneak_slider = 0
    self.state.event_stack.append(encounters.Graveyard1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testGraveyard2Pass(self):
    self.state.event_stack.append(encounters.Graveyard2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)

  def testGraveyard2PassInsane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Graveyard2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.clues, 1)

  def testGraveyard2Fail(self):
    self.state.event_stack.append(encounters.Graveyard2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Rivertown")

  def testGraveyard3Pass(self):
    self.char.fight_will_slider = 2
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testGraveyard3FailOne(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testGraveyard3FailTwo(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testGraveyard3FailThree(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)

  def testGraveyard3FailFour(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 5
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)

  def testGraveyard3FailKO(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater(0))
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")
    self.assertEqual(self.char.stamina, 1)

  def testGraveyard4NoTrophies(self):
    self.state.event_stack.append(encounters.Graveyard4(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertNotIn(0, self.state.usables)
    self.assertEqual(choice.remaining_spend, [{"toughness": 5}, False])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertFalse(self.char.possessions)
    self.assertFalse(self.char.trophies)

  def testGraveyard4Ally(self):
    self.char.trophies.extend([monsters.Octopoid(), monsters.Vampire()])
    self.state.allies.append(assets.VisitingPainter())
    self.state.event_stack.append(encounters.Graveyard4(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.remaining_spend, [{"toughness": 5}, False])
    self.use_handle(0, self.char.trophies[0].handle)
    self.use_handle(0, self.char.trophies[1].handle)
    self.assertEqual(choice.remaining_spend, [False, {"toughness": -5}])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()

    self.assertEqual([pos.handle for pos in self.char.possessions], ["Visiting Painter"])
    self.assertFalse(self.char.trophies)
    self.assertFalse(self.state.allies)

  def testGraveyard4Reward(self):
    self.char.trophies.extend([monsters.Octopoid(), monsters.Vampire()])
    self.state.spells.append(items.Wither(0))
    self.state.event_stack.append(encounters.Graveyard4(self.char))
    choice = self.resolve_to_choice(SpendChoice)
    self.use_handle(0, self.char.trophies[0].handle)
    self.use_handle(0, self.char.trophies[1].handle)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()

    self.assertEqual([pos.handle for pos in self.char.possessions], ["Wither0"])
    self.assertFalse(self.char.trophies)
    self.assertFalse(self.state.spells)

  def testGraveyard5Fail(self):
    self.state.event_stack.append(encounters.Graveyard5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testGraveyard5PassStreet(self):
    self.state.event_stack.append(encounters.Graveyard5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(PlaceChoice)
    self.assertEqual(self.char.clues, 2)

    choice.resolve(self.state, "Downtown")
    self.resolve_until_done()

  def testGraveyard5PassNowhere(self):
    self.state.event_stack.append(encounters.Graveyard5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(PlaceChoice)
    self.assertEqual(self.char.clues, 2)

    choice.resolve(self.state, "No thanks")
    self.resolve_until_done()

  def testGraveyard5PassLocation(self):
    self.state.event_stack.append(encounters.Graveyard5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(PlaceChoice)
    self.assertEqual(self.char.clues, 2)

    self.state.places["University"].encounters = [
        encounters.EncounterCard("University2", {"Administration": encounters.Administration2})]
    choice.resolve(self.state, "Administration")
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)

  def testGraveyard6(self):
    self.state.event_stack.append(encounters.Graveyard6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)

  def testGraveyard6Cap(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.Graveyard6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)

  def testGraveyard7(self):
    self.state.event_stack.append(encounters.Graveyard7(self.char))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[1])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0], self.state.monsters[1])
    self.assertIsNone(self.state.monsters[1].place)


if __name__ == "__main__":
  unittest.main()
