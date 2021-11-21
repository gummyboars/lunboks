#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import abilities
from eldritch import characters
from eldritch import events
from eldritch.events import *
from eldritch import items
from eldritch.test_events import EventTest


class ClueTokenTest(EventTest):

  def setUp(self):
    super().setUp()
    self.check = Check(self.char, "combat", 0)
    self.state.event_stack.append(self.check)

  def testSpendClues(self):
    self.char.clues = 3
    self.resolve_to_usable(0, "clues", SpendClue)
    self.assertTrue(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 1)
    self.assertEqual(self.state.event_stack[-1], self.check)
    self.assertEqual(len(self.state.usables), 1)
    old_successes = self.check.successes
    old_roll = self.check.roll[:]

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.state.event_stack.append(self.state.usables[0]["clues"])
      self.resolve_to_usable(0, "clues", SpendClue)

    new_successes = self.check.successes
    new_roll = self.check.roll
    self.assertEqual(len(new_roll), 1+len(old_roll))
    self.assertEqual(new_successes, old_successes+1)
    self.assertEqual(len(self.state.event_stack), 1)
    self.assertEqual(self.state.event_stack[-1], self.check)

    self.state.done_using[0] = True
    self.resolve_loop()

  def testNoCluesLeft(self):
    self.char.clues = 1
    self.resolve_to_usable(0, "clues", SpendClue)
    self.assertTrue(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 1)
    self.assertEqual(self.state.event_stack[-1], self.check)
    self.assertEqual(len(self.state.usables), 1)

    self.state.event_stack.append(self.state.usables[0]["clues"])
    self.resolve_loop()

    self.assertFalse(self.state.usables)

  def testBonusDieFromSkill(self):
    self.char.clues = 2
    self.char.possessions.append(abilities.Fight())
    self.resolve_to_usable(0, "clues", SpendClue)
    self.assertTrue(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 1)
    self.assertEqual(self.state.event_stack[-1], self.check)
    self.assertEqual(len(self.state.usables), 1)
    old_roll = self.check.roll[:]

    self.state.event_stack.append(self.state.usables[0]["clues"])
    self.resolve_to_usable(0, "clues", SpendClue)

    new_roll = self.check.roll[:]
    self.assertEqual(len(new_roll), 2+len(old_roll))

    self.assertEqual(len(self.state.event_stack), 1)
    self.state.event_stack.append(self.state.usables[0]["clues"])
    self.resolve_loop()

    last_roll = self.check.roll[:]
    self.assertEqual(len(last_roll), 2+len(new_roll))
    self.assertFalse(self.state.event_stack)


class RerollTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(abilities.Marksman())
    self.check = Check(self.char, "combat", 0)
    self.state.event_stack.append(self.check)

  def testReroll(self):
    self.resolve_to_usable(0, 0, Sequence)
    self.assertTrue(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 1)
    self.assertEqual(self.state.event_stack[-1], self.check)
    self.assertEqual(len(self.state.usables), 1)
    old_roll = self.check.roll[:]

    self.state.event_stack.append(self.state.usables[0][0])
    self.resolve_loop()

    self.assertTrue(self.check.is_resolved())
    self.assertFalse(self.state.usables)

    new_roll = self.check.roll
    self.assertNotEqual(old_roll, new_roll)  # TODO: 1 / 1296 chance of failing.


class OneshotItemTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.Dynamite())
    self.check = Check(self.char, "combat", 0)
    self.state.event_stack.append(self.check)

  def testUnusedItems(self):
    self.resolve_loop()
    self.assertTrue(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 0)
    self.assertEqual(len(self.check.roll), 4)

  def testUsedItems(self):
    self.char.possessions[0]._active = True  # pylint: disable=protected-access
    self.resolve_loop()
    self.assertTrue(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 0)
    self.assertEqual(len(self.check.roll), 12)
    self.assertEqual(len(self.char.possessions), 0)


class LossPreventionTest(EventTest):

  def setUp(self):
    super().setUp()
    self.food = items.Food()
    self.char.possessions.append(self.food)
    self.loss = Loss(self.char, {"stamina": 1})
    self.state.event_stack.append(self.loss)

  def testIsUsable(self):
    self.assertEqual(self.char.stamina, 5)

    self.resolve_to_usable(0, 0, Sequence)
    self.assertFalse(self.loss.is_resolved())
    self.assertCountEqual([0], self.state.usables.keys())

    self.state.done_using[0] = True
    self.resolve_loop()
    self.assertTrue(self.loss.is_resolved())
    self.assertEqual(self.char.stamina, 4)

  def testPreventLoss(self):
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(len(self.state.common), 0)

    self.resolve_to_usable(0, 0, Sequence)
    self.assertFalse(self.loss.is_resolved())

    self.state.event_stack.append(self.state.usables[0][0])
    self.resolve_loop()
    self.assertTrue(self.loss.is_resolved())
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(len(self.state.common), 1)

  def testPreventOnlyOne(self):
    self.assertEqual(self.char.stamina, 5)
    self.loss.losses["stamina"] = 2

    self.resolve_to_usable(0, 0, Sequence)
    self.assertFalse(self.loss.is_resolved())

    self.state.event_stack.append(self.state.usables[0][0])
    self.resolve_loop()
    self.assertTrue(self.loss.is_resolved())
    self.assertEqual(self.char.stamina, 4)


class MedicineTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Uptown"]
    self.char.possessions.append(abilities.Medicine())
    self.char.stamina = 3
    self.state.turn_phase = "upkeep"

  def testMedicine(self):
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, 0, Sequence)

    self.state.event_stack.append(self.state.usables[0][0])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "nobody"])
    choice.resolve(self.state, "Dummy")
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 4)
    self.assertTrue(self.char.possessions[0].exhausted)

  def testMultipleOptions(self):
    nun = characters.CreateCharacters()["Nun"]
    nun.stamina = 1
    nun.place = self.char.place
    self.state.all_characters["Nun"] = nun
    self.state.characters.append(nun)

    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, 0, Sequence)

    self.state.event_stack.append(self.state.usables[0][0])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Nun", "nobody"])
    choice.resolve(self.state, "Nun")
    self.resolve_until_done()

    self.assertEqual(nun.stamina, 2)
    self.assertEqual(self.char.stamina, 3)
    self.assertTrue(self.char.possessions[0].exhausted)


if __name__ == "__main__":
  unittest.main()
