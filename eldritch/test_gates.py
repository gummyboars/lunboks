#!/usr/bin/env python3

from collections import deque
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from game import InvalidMove
from eldritch import abilities
from eldritch import gate_encounters
from eldritch import events
from eldritch.events import *
from eldritch import items
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


class Gate3Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Pluto2"]
    self.state.event_stack.append(gate_encounters.Pluto3(self.char))

  def testPluto3Pass(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testPluto3FailOddItems(self):
    self.char.possessions.extend([
        items.Derringer18(0),
        items.EnchantedKnife(0),
        items.PatrolWagon(),
    ])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertEqual(choice.count.value(self.state), 1)
    self.assertListEqual(
        choice.choices,
        [".18 Derringer0", "Enchanted Knife0", "Patrol Wagon"]
    )
    choice.resolve(self.state, "Patrol Wagon")
    choice.resolve(self.state, "done")
    self.resolve_until_done()

  def testPluto3FailEvenItems(self):
    self.char.place = self.state.places["Pluto2"]
    self.char.possessions.extend([
        items.Derringer18(0),
        items.EnchantedKnife(0),
        items.PatrolWagon(),
        items.MagicPowder(0),
    ])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertEqual(choice.count.value(self.state), 2)
    self.assertListEqual(
        choice.choices,
        [".18 Derringer0", "Enchanted Knife0", "Patrol Wagon", "Magic Powder0"]
    )
    choice.resolve(self.state, ".18 Derringer0")
    choice.resolve(self.state, "Patrol Wagon")
    choice.resolve(self.state, "done")
    self.resolve_until_done()


class Abyss4Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Abyss2"]
    self.state.event_stack.append(gate_encounters.Abyss4(self.char))

  def testOneSuccess(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 3, 3, 3])):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Cave")

  def testTwoSuccesses(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 5, 3, 3])):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Dreamlands1")

  def testThreeSuccessesPass(self):
    side_effect = [5, 5, 5, 3] + [5, 3]
    key = items.SilverKey(0)
    self.state.unique.append(key)
    self.assertEqual(len(self.char.possessions), 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertListEqual(self.char.possessions, [key])
    self.assertEqual(self.char.place.name, "Abyss2")

  def testThreeSuccessesFail(self):
    side_effect = [5, 5, 5, 3] + [3, 3]
    self.assertEqual(len(self.char.possessions), 0)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertEqual(self.char.place.name, "Abyss2")


class Other5Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Great Hall1"]
    self.state.event_stack.append(gate_encounters.Other5(self.char))

  def testNoSuccesses(self):
    side_effect = [3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testOneSuccess(self):
    side_effect = [5, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testTwoSuccess(self):
    side_effect = [5, 5]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)


class Dreamlands6Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.init_money = 10
    self.char.dollars = self.init_money
    self.state.event_stack.append(gate_encounters.Dreamlands6(self.char))

  def testPass(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, self.init_money)

  def testFail(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    # Not that I'm too worried about it, but -inf doesn't mean we can never gain money
    self.state.event_stack.append(events.Gain(self.char, {"dollars": 5}))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)

  def testFailPoor(self):
    self.char.dollars = 0
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)


class Dreamlands9Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.tommy_gun = items.TommyGun(0)
    self.knife = items.EnchantedKnife(0)
    self.state.event_stack.append(gate_encounters.Dreamlands9(self.char))

  def testPassSneak(self):
    self.char.possessions.append(self.tommy_gun)
    self.char.dollars = 3
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertIn(self.tommy_gun, self.char.possessions)
    self.assertEqual(self.char.dollars, 3)

  def testLoseFromOneItem(self):
    self.char.possessions.append(self.tommy_gun)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertListEqual(choice.choices, ["Tommy Gun0"])
    self.assertEqual(choice.count.value(self.state), 1)
    choice.resolve(self.state, "Tommy Gun0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertNotIn(self.tommy_gun, self.char.possessions)

  def testLoseFromTwoItems(self):
    self.char.possessions.append(self.tommy_gun)
    self.char.possessions.append(self.knife)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertListEqual(choice.choices, ["Tommy Gun0", "Enchanted Knife0"])
    self.assertEqual(choice.count.value(self.state), 1)
    choice.resolve(self.state, "Tommy Gun0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertNotIn(self.tommy_gun, self.char.possessions)

  def testLoseFromOneDollar(self):
    self.char.dollars = 1
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertEqual(choice.count.value(self.state), 0)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)

  def testLoseFromTwoDollars(self):
    self.char.dollars = 2
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertEqual(choice.count.value(self.state), 0)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)

  def testLoseFromItemsAndDollars(self):
    self.char.dollars = 2
    self.char.possessions.append(self.tommy_gun)
    self.char.possessions.append(self.knife)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.assertListEqual(choice.choices, ["Tommy Gun0", "Enchanted Knife0"])
    self.assertEqual(choice.count.value(self.state), 1)
    choice.resolve(self.state, "Tommy Gun0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)


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


class GreatHall11Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Great Hall1"]
    self.state.event_stack.append(gate_encounters.GreatHall11(self.char))

  def testPassLuck(self):
    side_effect = [5, 3] + [3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertIsNone(self.char.delayed_until)

  def testFailLuckPassDie(self):
    side_effect = [3, 3] + [5]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.delayed_until, self.state.turn_number+2)

  def testFailLuckFailDie(self):
    side_effect = [3, 3] + [3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Fight", "Evade"])


class Pluto12Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Pluto1"]
    self.spell1 = items.spells.DreadCurse(0)
    self.spell2 = items.spells.Voice(0)
    self.char.possessions.append(self.spell1)
    self.state.event_stack.append(gate_encounters.Pluto12(self.char))

  def testPass(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertIn(self.spell1, self.char.possessions)

  def testOnlyOneSpell(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(MultipleChoice)
      self.assertListEqual(choice.choices, ["Lose 2 spells", "Lose 2 sanity"])
    with self.assertRaisesRegex(InvalidMove, "do not have at least 2 spell"):
      choice.resolve(self.state, "Lose 2 spells")
    choice.resolve(self.state, "Lose 2 sanity")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertIn(self.spell1, self.char.possessions)

  def testChoice(self):
    self.char.possessions.append(self.spell2)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(MultipleChoice)
      self.assertListEqual(choice.choices, ["Lose 2 spells", "Lose 2 sanity"])
    choice.resolve(self.state, "Lose 2 spells")
    item_choice = self.resolve_to_choice(ItemLossChoice)
    item_choice.resolve(self.state, self.spell1.handle)
    item_choice.resolve(self.state, self.spell2.handle)
    item_choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertFalse(self.char.possessions)

  def testChoiceInsane(self):
    self.char.possessions.append(self.spell2)
    self.char.sanity = 2
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(MultipleChoice)
      self.assertListEqual(choice.choices, ["Lose 2 spells", "Lose 2 sanity"])
    choice.resolve(self.state, "Lose 2 sanity")
    insane_loss = self.resolve_to_choice(ItemLossChoice)
    insane_loss.resolve(self.state, self.spell1.handle)
    insane_loss.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)


class Gate13Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.unique = items.HealingStone(0)
    self.state.unique.append(self.unique)

  def passCity(self):
    self.char.place = self.state.places["City2"]
    self.state.event_stack.append(gate_encounters.City13(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testCityPass(self):
    diner: places.Location = self.state.places["Diner"]
    diner.gate = next(gate for gate in self.state.gates if gate.name == "City")
    self.passCity()
    self.assertEqual(self.char.place.name, "Diner")
    self.assertListEqual(self.char.possessions, [self.unique])

  def testCityPassNoGate(self):
    self.passCity()
    self.assertEqual(self.char.place.name, "Lost")
    self.assertListEqual(self.char.possessions, [self.unique])

  def failCity(self, until_done):
    self.char.place = self.state.places["City2"]
    self.state.event_stack.append(gate_encounters.City13(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      if until_done:
        self.resolve_until_done()
        return None
      return self.resolve_to_choice(events.ItemLossChoice)

  def testCityFail(self):
    self.char.sanity = 5
    self.failCity(until_done=True)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)

  def testCityFailInsane(self):
    insane_choice = self.failCity(until_done=False)
    insane_choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")

  def testCityFailUnconscious(self):
    self.char.sanity = 5
    self.char.stamina = 1
    unconscious_choice = self.failCity(until_done=False)
    unconscious_choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")

  def testCityFailDevoured(self):
    self.char.stamina = 1
    self.failCity(until_done=True)
    self.assertTrue(self.char.gone)

  def plateauEncounter(self):
    self.char.place = self.state.places["Plateau1"]
    self.char.lore_luck_slider += 1
    self.state.event_stack.append(gate_encounters.Plateau13(self.char))

  def testPlateauDecline(self):
    self.assertEqual(self.char.dollars, 3)
    self.plateauEncounter()
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testPlateauPass(self):
    self.assertEqual(self.char.dollars, 3)
    self.plateauEncounter()
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 9)

  def testPlateauFail(self):
    self.assertEqual(self.char.dollars, 3)
    self.plateauEncounter()
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.place.name, "Lost")


class City14Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["City1"]
    self.state.event_stack.append(gate_encounters.City14(self.char))

  def testFail(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.bless_curse, 0)

  def testPassTake(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 13)
    self.assertEqual(self.char.bless_curse, -1)

  def testPassLeave(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertListEqual(choice.choices, ["Yes", "No"])
    choice.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.bless_curse, 0)


class GreatHall15Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Great Hall1"]
    self.state.event_stack.append(gate_encounters.GreatHall15(self.char))

  def testNoSuccess(self):
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 0)

  def testOneSuccess(self):
    side_effect = [5, 3, 3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 1)

  def testTwoSuccesses(self):
    side_effect = [5, 5, 3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 2)

  def testThreeSuccesses(self):
    side_effect = [5, 5, 5, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.clues, 3)


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


class Dreamlands22Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Dreamlands22(self.char))
    self.assertEqual(self.char.dollars, 3)

  def testFailWill(self):
    side_effect = [3, 3] + [1, 1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testPassLo(self):
    side_effect = [3, 5] + [1, 1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)

  def testPassMid(self):
    side_effect = [3, 5] + [1, 4]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 8)

  def testPassHi(self):
    side_effect = [3, 5] + [6, 6]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 15)


class Dreamlands23Test(GateEncounterTest):
  def testFail(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Dreamlands23(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Dreamlands1")

  def testPass1(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(gate_encounters.Dreamlands23(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Dreamlands2")

  def testPass2(self):
    self.char.place = self.state.places["Dreamlands2"]
    self.state.event_stack.append(gate_encounters.Dreamlands23(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")


class Abyss26Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Abyss1"]
    self.state.event_stack.append(gate_encounters.Abyss26(self.char))

  def testFailOne(self):
    side_effect = [3, 3] + [1]
    self.assertEqual(self.char.stamina, 3)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testFailUnconscious(self):
    side_effect = [3, 3] + [3]
    self.assertEqual(self.char.stamina, 3)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Lost")

  def testPassOne(self):
    side_effect = [5, 3] + [1]
    self.assertEqual(self.char.stamina, 3)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)

  def testPassMax(self):
    side_effect = [5, 3] + [3]
    self.assertEqual(self.char.stamina, 3)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)


class Other27Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.state.event_stack.append(gate_encounters.Other27(self.char))
    self.assertEqual(self.char.stamina, 3)
    self.char.place = self.state.places["Dreamlands1"]

  def testNoSuccesses(self):
    side_effect = [3, 3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Lost")
    self.assertEqual(self.char.clues, 0)

  def testOneSuccess(self):
    side_effect = [5, 3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.clues, 1)

  def testTwoSuccesses(self):
    side_effect = [5, 5, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.clues, 2)

  def testThreeSuccesses(self):
    side_effect = [5, 5, 5]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.clues, 3)


class PassOrLoseDiceTest(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Abyss1"]
    self.state.event_stack.append(gate_encounters.Abyss30(self.char))
    # Also Plateau31, SunkenCity36,

  def testPass(self):
    side_effect = [5, 5, 5]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testFail(self):
    side_effect = [3] + [1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)

  def testFailUnconscious(self):
    side_effect = [3] + [3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      loss = self.resolve_to_choice(ItemLossChoice)
    loss.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Lost")

  def testModifier(self):
    self.state.event_stack.pop()
    self.state.event_stack.append(gate_encounters.Pluto43(self.char))
    side_effect = [3, 3] + [3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)

  def testModifierClipped(self):
    self.state.event_stack.pop()
    self.state.event_stack.append(gate_encounters.Pluto43(self.char))
    side_effect = [3, 3] + [1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)

  def testDoubleBarrelledDevoured(self):
    self.state.event_stack.pop()
    self.state.event_stack.append(gate_encounters.Pluto43(self.char))
    side_effect = [3, 3] + [6]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertTrue(self.char.gone)


class SunkenCity41Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Sunken City1"]
    self.state.event_stack.append(gate_encounters.SunkenCity41(self.char))

  def testFail(self):
    side_effect = [1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)

  def testFailInsane(self):
    side_effect = [3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      loss = self.resolve_to_choice(ItemLossChoice)
    loss.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Lost")


class Other47Test(GateEncounterTest):
  def setUp(self):
    super().setUp()
    self.state.event_stack.append(gate_encounters.Other47(self.char))
    self.assertEqual(self.char.sanity, 3)
    self.char.place = self.state.places["Sunken City1"]

  def testNoSuccesses(self):
    side_effect = [3, 3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Lost")
    self.assertEqual(self.char.clues, 0)

  def testOneSuccess(self):
    side_effect = [5, 3, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.clues, 1)

  def testTwoSuccesses(self):
    side_effect = [5, 5, 3]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.clues, 2)

  def testThreeSuccesses(self):
    side_effect = [5, 5, 5]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=side_effect)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.clues, 3)


if __name__ == "__main__":
  unittest.main()
