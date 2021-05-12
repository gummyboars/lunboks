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
import eldritch.gate_encounters as gate_encounters
import eldritch.places as places
import eldritch.characters as characters
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

  def testRoadhouse1Reward(self):
    self.char.clues = 3
    self.state.common.extend([items.Revolver38(), items.Food()])
    self.state.event_stack.append(encounters.Roadhouse1(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
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

  def testLodge1Pass(self):
    self.state.event_stack.append(encounters.Lodge1(self.char))
    self.state.spells.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ['Cross', 'Holy Water'])
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
    self.state.unique.append(items.HolyWater())
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testLodge2Fail(self):
    self.state.event_stack.append(encounters.Lodge2(self.char))
    self.state.unique.append(items.HolyWater())
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
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testLodge4DeclinePass(self):
    self.state.event_stack.append(encounters.Lodge4(self.char))
    self.char.dollars = 3
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testLodge4DeclineFail(self):
    self.state.event_stack.append(encounters.Lodge4(self.char))
    self.char.stamina = 4
    self.char.dollars = 3
    choice = self.resolve_to_choice(MultipleChoice)
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
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
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
      use_clues = self.resolve_to_usable(0, -1, SpendClue)
    self.state.done_using[0] = True
    self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.place.name, "FrenchHill")

  def testLodge6Join(self):
    self.state.event_stack.append(encounters.Lodge6(self.char))
    self.char.dollars = 3
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testLodge7Fail(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 2)

  def testLodge7PassCC(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 3, 3])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.state.unique), 2)

  def testLodge7PassCU(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 3, 5])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(len(self.state.unique), 1)

  def testLodge7PassUU(self):
    self.state.event_stack.append(encounters.Lodge7(self.char))
    self.state.common.extend([items.Revolver38(), items.TommyGun()])
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 5, 5])):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 0)

  def testSanctum1Pass(self):
    self.state.event_stack.append(encounters.Sanctum1(self.char))
    self.char.lore_luck_slider = 0
    self.state.unique.extend([items.Cross(), items.HolyWater(), items.TommyGun()])
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
    self.state.unique.extend([items.Cross(), items.HolyWater(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testSanctum2Decline(self):
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.assertEqual(self.char.sanity, 3)


  def testSanctum2Pass(self):
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    # TODO: Choose monster on the board as a trophy
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)


  def testSanctum2Fail(self):
    self.state.event_stack.append(encounters.Sanctum2(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

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
    self.resolve_until_done()
    self.assertFalse(self.char.lodge_membership)
    self.assertEqual(self.char.sanity, 1)

  def testSanctum4Decline(self):
    self.char.lodge_membership = True
    self.char.dollars = 3
    self.state.event_stack.append(encounters.Sanctum4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Decline")
    self.resolve_until_done()
    self.assertFalse(self.char.lodge_membership)
    self.assertEqual(self.char.sanity, 1)

  def testSanctum4Accept(self):
    self.char.lodge_membership = True
    self.char.dollars = 3
    self.state.event_stack.append(encounters.Sanctum4(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
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
    #TODO: A monster appears

  def testSanctum7Poor(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.resolve_until_done()

  def testSanctum7Decline(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.char.clues = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "No")
    self.resolve_until_done()

  def testSanctum7Fail(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.char.clues = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 2)

  def testSanctum7Pass(self):
    self.state.event_stack.append(encounters.Sanctum7(self.char))
    self.char.clues = 2
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      #TODO: Choose gate to close
      self.resolve_until_done()


class WitchTest(EncounterTest):

  def setUp(self):
    super(WitchTest, self).setUp()
    self.char.place = self.state.places["Witch"]

  def testWitch1Fail(self):
    self.state.allies.extend([assets.PoliceDetective()])
    self.state.event_stack.append(encounters.Witch1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)

  def testWitch1PassAlly(self):
    self.state.allies.extend([assets.PoliceDetective()])
    self.state.event_stack.append(encounters.Witch1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Police Detective")

  def testWitch1PassReward(self):
    # TODO: ally not available
    # self.state.event_stack.append(encounters.Witch1(self.char))
    # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
    #   self.resolve_until_done()
    # self.assertEqual(len(self.char.possessions), 0)
    # self.assertEqual(self.char.clues, 2)
    pass

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

  def testWitch3Zero(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.Witch3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)

  def testWitch3ZeroInsane(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.Witch3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testWitch3One(self):
    self.char.lore_luck_slider = 3
    self.state.event_stack.append(encounters.Witch3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)

  def testWitch3Two(self):
    self.char.lore_luck_slider = 2
    self.char.stamina = 3
    self.state.event_stack.append(encounters.Witch3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testWitch3Three(self):
    self.char.lore_luck_slider = 1
    self.char.stamina = 2
    self.state.event_stack.append(encounters.Witch3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testWitch4(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.Witch4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testWitch4Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Witch4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testWitch5(self):
    #TODO: A gate and monster appear
    pass

  def testWitch6One(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.Witch6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 1)

  def testWitch6OneInsane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Witch6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)

  def testWitch6Three(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.Witch6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 3)

  def testWitch6ThreeInsane(self):
    self.char.sanity = 3
    self.state.event_stack.append(encounters.Witch6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 2)

  def testWitch7Pass(self):
    self.state.event_stack.append(encounters.Witch7(self.char))
    self.state.spells.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, '.38 Revolver')

  def testWitch7Fail(self):
    self.state.event_stack.append(encounters.Witch7(self.char))
    self.char.possessions.extend([items.Revolver38(), items.TommyGun()])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(events.ItemChoice)
    # TODO: Learn how to use ItemCountChoice
    # self.assertEqual(choice.choices, ['.38 Revolver', 'Tommy Gun'])
    # choice.resolve('Tommy Gun')
    # self.resolve_until_done()
    # self.assertEqual(len(self.char.possessions), 1)
    # self.assertEqual(self.char.possessions[0].name, '.38 Revolver')



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
    super(ShopTest, self).setUp()
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


class NewspaperTest(EncounterTest):

  def setUp(self):
    super(NewspaperTest, self).setUp()
    self.char.place = self.state.places["Newspaper"]

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
    super(TrainTest, self).setUp()
    self.char.place = self.state.places["Train"]
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    # maybe they're magic guns? I cast bullet!
    self.state.spells.extend([items.TommyGun(), items.Revolver38()])
    self.state.common.extend([items.Dynamite(), items.Revolver38()])

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

  def testTrain6NoMoney(self):
    self.state.event_stack.append(encounters.Train6(self.char))
    self.char.dollars = 2
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(len(self.state.unique), 2)

  def testTrain6MoneyRefuse(self):
    self.state.event_stack.append(encounters.Train6(self.char))
    self.char.dollars = 4
    choice = self.resolve_to_choice(MultipleChoice)
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
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
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
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
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
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(len(self.state.unique), 2)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")


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

  def testIsle2PassReward(self):
    self.state.event_stack.append(encounters.Isle2(self.char))
    self.char.stamina = 1
    self.char.sanity = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, self.char._max_sanity)
    self.assertEqual(self.char.stamina, self.char._max_stamina)

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

  def setUp(self):
    super(WoodsTest, self).setUp()
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

# TODO: Check these tests
#  def testWoods4Pass(self):
#    self.char.possessions.extend([items.HolyWater(), items.Revolver38()])
#    self.state.event_stack.append(encounters.Woods4(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 2)
#    self.assertEqual(self.char.stamina, 3)
#
#  def testWoods4FailThreePlus(self):
#    self.char.possessions.extend([items.HolyWater(), items.Revolver38(), items.TommyGun()])
#    self.state.event_stack.append(encounters.Woods4(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
#      self.resolve_to_choice(ItemChoice)
#    self.assertEqual(len(self.char.possessions), 1)
#    self.assertEqual(self.char.stamina, 1)
#
#  def testWoods4FailTwoItem(self):
#    self.char.possessions.extend([items.HolyWater(), items.Revolver38()])
#    self.state.event_stack.append(encounters.Woods4(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 0)
#    self.assertEqual(self.char.stamina, 1)
#
#  def testWoods4FailOneItem(self):
#    self.char.possessions.extend([items.HolyWater()])
#    self.state.event_stack.append(encounters.Woods4(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 0)
#    self.assertEqual(self.char.stamina, 1)
#
#  def testWoods4FailZeroItem(self):
#    self.state.event_stack.append(encounters.Woods4(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 0)
#    self.assertEqual(self.char.stamina, 1)
#
#  def testWoods4FailKO(self):
#    self.char.possessions.extend([items.HolyWater(), items.Revolver38()])
#    self.char.stamina = 2
#    self.state.event_stack.append(encounters.Woods4(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 0)
#    self.assertEqual(self.char.stamina, 1)
#    self.assertEqual(self.char.place.name, "Hospital")

  def testWoods5FoodAlly(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.allies.append(assets.Dog())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Dog")

  def testWoods5FoodReward(self):
    self.char.speed_sneak_slider = 2
    self.char.possessions.append(items.Food())
    self.state.event_stack.append(encounters.Woods5(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
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

#  def testWoods5ChooseLuckReward(self):
#    self.char.speed_sneak_slider = 2
#    self.char.possessions.append(items.Food())
#    self.state.event_stack.append(encounters.Woods5(self.char))
#    choice = self.resolve_to_choice(MultipleChoice)
#    choice.resolve(self.state, "No")
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 1)
#    self.assertEqual(self.char.possessions[0].name, "Food")
#    self.assertEqual(self.char.dollars, 6)

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

#  def testWoods5ForceLuckReward(self):
#    self.char.speed_sneak_slider = 2
#    self.state.event_stack.append(encounters.Woods5(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
#      self.resolve_until_done()
#    self.assertEqual(len(self.char.possessions), 0)
#    self.assertEqual(self.char.dollars, 6)

  def testWoods5ForceLuckFail(self):
    self.char.speed_sneak_slider = 2
    self.state.event_stack.append(encounters.Woods5(self.char))
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
  #    self.state.skills.extend([abilities.Marksman(), abilities.Fight()])
  #    # We know these aren't spells
  #    self.state.spells.extend([items.Cross(), items.HolyWater()])
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

class CaveTest(EncounterTest):

# TODO: a monster appears
#  def testCave1Zero(self):
#    self.char.lore_luck_slider = 3
#    self.state.common.append(items.Food())
#    self.state.event_stack.append(encounters.Cave1(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
#      raise NotImplementedError("A monster appears")
#      self.resolve_until_monster()
#    self.assertEqual(len(self.state.common), 1)
#    self.assertEqual(self.char.sanity, 2)

  def testCave1ZeroInsane(self):
    self.char.lore_luck_slider = 3
    self.char.sanity = 1
    self.state.common.append(items.Food())
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave1One(self):
    self.char.lore_luck_slider = 3
    self.state.common.append(items.Food())
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.sanity, 2)

  def testCave1OneInsane(self):
    self.char.lore_luck_slider = 3
    self.char.sanity = 1
    self.state.common.append(items.Food())
    self.state.event_stack.append(encounters.Cave1(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

  def testCave1Two(self):
    self.char.lore_luck_slider = 2
    self.state.common.append(items.Food())
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
      self.resolve_until_done()
    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testCave6WhiskeyAlly(self):
    self.char.possessions.append(items.Whiskey())
    self.state.allies.append(assets.ToughGuy())
    self.state.common.extend([items.Food(), items.Revolver38()])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tough Guy")

  def testCave6WhiskeyReward(self):
    self.char.possessions.append(items.Whiskey())
    self.state.common.extend([items.Food(), items.Revolver38()])
    self.state.event_stack.append(encounters.Cave6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testCave6DeclineAlly(self):
    self.char.possessions.append(items.Whiskey())
    self.state.allies.append(assets.ToughGuy())
    self.state.common.extend([items.Food(), items.Revolver38()])
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
    self.char.possessions.append(items.Whiskey())
    self.state.common.extend([items.Food(), items.Revolver38()])
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
    self.char.possessions.append(items.Whiskey())
    self.state.common.extend([items.Food(), items.Revolver38()])
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
    self.state.common.extend([items.Food(), items.Revolver38()])
    self.state.event_stack.append(encounters.Cave6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tough Guy")

  def testCave6NoWhiskeyReward(self):
    self.state.common.extend([items.Food(), items.Revolver38()])
    self.state.event_stack.append(encounters.Cave6(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, ".38 Revolver")

  def testCave6NoWhiskeyFail(self):
    self.state.common.extend([items.Food(), items.Revolver38()])
    self.state.event_stack.append(encounters.Cave6(self.char))
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
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")

  def testCave7Devoured(self):
#    self.char.stamina = 1
#    self.char.sanity = 1
#    self.state.event_stack.append(encounters.Cave7(self.char))
#    choice = self.resolve_to_choice(MultipleChoice)
#    self.assertEqual(choice.choices, ["Yes", "No"])
#    choice.resolve(self.state, "Yes")
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
#      self.resolve_until_done()
#    self.assertEqual(self.char.is_devoured, True)
    pass

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
    super(StoreTest, self).setUp()
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
    # TODO: Implement sale for twice the price

  def testStore4(self):
    self.state.event_stack.append(encounters.Store4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testStore4Insane(self):
    self.char.sanity = 1
    self.state.event_stack.append(encounters.Store4(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")

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

  def testStore5PassSalesman(self):
   # TODO: Implement the salesman drawing an extra card
   # raise NotImplementedError("Salesman should get to draw an extra common card")
   # self.character = characters.Salesman()
   # self.char.lore_luck_slider = 2
   # self.state.common.extend([items.Revolver38(), items.Cross(), items.TommyGun(), items.Dynamite()])
   # self.state.event_stack.append(encounters.Store5(self.char))
   # with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
   #   self.resolve_until_done()
   pass

  def testStore6Decline(self):
    self.char.lore_luck_slider = 2
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
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
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testStore6Pass(self):
    self.char.lore_luck_slider = 2
    self.char.dollars = 1
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)

  def testStore6Fail(self):
    self.char.lore_luck_slider = 2
    self.char.dollars = 1
    self.state.event_stack.append(encounters.Store6(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testStore7(self):
    self.state.common.append(items.Dynamite())
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
    self.resolve_until_done()

  def testShoppe3Decline(self):
    self.char.dollars = 5
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "No")
    self.resolve_until_done()

  def testShoppe3Empty(self):
    self.char.dollars = 5
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.char.possessions), 0)

  def testShoppe3Gold(self):
    self.char.dollars = 5
    self.char.lore_luck_slider = 3
    self.state.unique.extend([items.Cross(), items.HolyWater()])
    self.state.event_stack.append(encounters.Shoppe3(self.char))
    buy = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(buy.choices, ["Yes", "No"])
    buy.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 10)
    self.assertEqual(len(self.char.possessions), 0)

  def testShoppe3Jackpot(self):
    #TODO: Drawing multiple items
    # self.char.dollars = 5
    # self.char.lore_luck_slider = 1
    # self.state.unique.extend([items.Cross(), items.HolyWater()])
    # self.state.event_stack.append(encounters.Shoppe3(self.char))
    # buy = self.resolve_to_choice(MultipleChoice)
    # self.assertEqual(buy.choices, ["Yes", "No"])
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
#    self.state.unique.append(items.Cross()) # Costs 3
#    self.state.event_stack.append(encounters.Shoppe6(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
#      buy = self.resolve_to_choice(MultipleChoice)
#    self.assertEqual(buy.choices, ["Yes", "No"])
#    buy.resolve(self.state, "No")
#    self.resolve_until_done()
    pass

  def testShoppe6PassAccept(self):
    # self.state.unique.append(items.Cross()) # Costs 3
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
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")


class GraveyardTest(EncounterTest):

# TODO: Implement
#  def testGraveyard1(self):
#    raise NotImplementedError("A monster appears")

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
    self.state.unique.append(items.HolyWater())
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Holy Water")

  def testGraveyard3FailOne(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater())
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testGraveyard3FailTwo(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater())
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testGraveyard3FailThree(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater())
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)

  def testGraveyard3FailFour(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 5
    self.state.unique.append(items.HolyWater())
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)

  def testGraveyard3FailKO(self):
    self.char.fight_will_slider = 2
    self.char.stamina = 4
    self.state.unique.append(items.HolyWater())
    self.state.event_stack.append(encounters.Graveyard3(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")
    self.assertEqual(self.char.stamina, 1)

# Todo: Trophies
#  def testGraveyard4NoTrophies(self):
#    raise NotImplementedError("Count monster trophies")
#
#  def testGraveyardAlly(self):
#    raise NotImplementedError("Spend monster trophies")
#
#  def testGraveyardReward(self):
#    raise NotImplementedError("Spend monster trophies")
#    raise NotImplementedError("Ally not available")

  def testGraveyard5Fail(self):
    self.state.event_stack.append(encounters.Graveyard5(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

# Todo: move where you like
#  def testGraveyard5Pass(self):
#    self.state.event_stack.append(encounters.Graveyard5(self.char))
#    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
#      self.resolve_until_choice(MultipleChoice)
#    self.assertEqual(self.char.clues, 2)
#    raise NotImplementedError("Move to another location)

  def testGraveyard6(self):
    self.state.event_stack.append(encounters.Graveyard6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)

  def testGraveyard6Cap(self):
    self.char.sanity = 4
    self.state.event_stack.append(encounters.Graveyard6(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)

# TODO: Monster trophy
#  def testGraveyard7(self):
#    raise NotImplementedError("Take a monster trophy")


if __name__ == '__main__':
  unittest.main()
