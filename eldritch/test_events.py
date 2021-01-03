#!/usr/bin/env python3

import collections
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.characters as characters
import eldritch.eldritch as eldritch
import eldritch.events as events
from eldritch.events import *
import eldritch.items as items
import eldritch.places as places


class EventTest(unittest.TestCase):

  def setUp(self):
    self.char = characters.Character("Dummy", 5, 5, 4, 4, 4, 4, 4, 4, 4, places.Diner)
    self.state = eldritch.GameState()

  def resolve_loop(self):
    count = 0
    for thing in self.state.resolve_loop():  # It's a generator, so you have to loop through it.
      count += 1
      if count > 100:
        self.fail("Exceeded maximum number of events")
    self.assertFalse(self.state.event_stack)


class DiceRollTest(EventTest):

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4]))
  def testDieRoll(self):
    die_roll = DiceRoll(self.char, 1)
    self.assertFalse(die_roll.is_resolved())
    self.assertIsNone(die_roll.roll)

    self.state.event_stack.append(die_roll)
    self.resolve_loop()

    self.assertTrue(die_roll.is_resolved())
    self.assertListEqual(die_roll.roll, [4])

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 1, 5]))
  def testDiceRolls(self):
    dice_roll = DiceRoll(self.char, 3)
    self.assertFalse(dice_roll.is_resolved())
    self.assertIsNone(dice_roll.roll)

    self.state.event_stack.append(dice_roll)
    self.resolve_loop()

    self.assertTrue(dice_roll.is_resolved())
    self.assertListEqual(dice_roll.roll, [4, 1, 5])

  def testNoRolls(self):
    dice_roll = DiceRoll(self.char, -1)
    self.assertFalse(dice_roll.is_resolved())
    self.assertIsNone(dice_roll.roll)

    self.state.event_stack.append(dice_roll)
    self.resolve_loop()

    self.assertTrue(dice_roll.is_resolved())
    self.assertListEqual(dice_roll.roll, [])


class MovementTest(EventTest):

  def testMoveOneSpace(self):
    movement = Movement(self.char, ["Easttown"])
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_loop()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertEqual(self.char.movement_points, 3)

  def testMoveMultipleSpaces(self):
    movement = Movement(self.char, ["Easttown", "Rivertown", "Graveyard"])
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_loop()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Graveyard")
    self.assertEqual(self.char.movement_points, 1)

  def testForceMovement(self):
    movement = ForceMovement(self.char, "Graveyard")
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_loop()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Graveyard")
    self.assertEqual(self.char.movement_points, 4)


class GainLossTest(EventTest):

  def testGain(self):
    gain = Gain(self.char, {"money": 2, "clues": 1})
    self.assertFalse(gain.is_resolved())
    self.assertEqual(self.char.money, 0)
    self.assertEqual(self.char.clues, 0)

    self.state.event_stack.append(gain)
    self.resolve_loop()

    self.assertTrue(gain.is_resolved())
    self.assertEqual(self.char.money, 2)
    self.assertEqual(self.char.clues, 1)
    self.assertDictEqual(gain.final_adjustments, {"money": 2, "clues": 1})

  def testLoss(self):
    loss = Loss(self.char, {"sanity": 2, "stamina": 1})
    self.assertFalse(loss.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)

    self.state.event_stack.append(loss)
    self.resolve_loop()

    self.assertTrue(loss.is_resolved())
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 4)
    self.assertDictEqual(loss.final_adjustments, {"sanity": -2, "stamina": -1})

  def testOvergain(self):
    gain = Gain(self.char, {"sanity": 2, "stamina": 1})
    self.assertFalse(gain.is_resolved())
    self.char.sanity = 4
    self.assertEqual(self.char.stamina, 5)

    self.state.event_stack.append(gain)
    self.resolve_loop()

    self.assertTrue(gain.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.assertDictEqual(gain.final_adjustments, {"sanity": 1, "stamina": 0})

  def testOverloss(self):
    loss = Loss(self.char, {"clues": 2, "money": 1})
    self.assertFalse(loss.is_resolved())
    self.char.money = 2
    self.char.clues = 1

    self.state.event_stack.append(loss)
    self.resolve_loop()

    self.assertTrue(loss.is_resolved())
    self.assertEqual(self.char.money, 1)
    self.assertEqual(self.char.clues, 0)
    self.assertDictEqual(loss.final_adjustments, {"clues": -1, "money": -1})

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 1]))
  def testDieRollLoss(self):
    # Use an ordered dict to make sure we lose 4 sanity and 1 stamina.
    loss = Loss(self.char, collections.OrderedDict([
      ("sanity", DiceRoll(self.char, 1)), ("stamina", DiceRoll(self.char, 1))]))
    self.assertFalse(loss.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)

    self.state.event_stack.append(loss)
    self.resolve_loop()

    self.assertTrue(loss.is_resolved())
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 4)
    self.assertDictEqual(loss.final_adjustments, {"sanity": -4, "stamina": -1})


class StatusChangeTest(EventTest):

  def testDelayed(self):
    status = StatusChange(self.char, "delayed", positive=True)
    self.assertFalse(status.is_resolved())
    self.assertFalse(self.char.delayed)

    self.state.event_stack.append(status)
    self.resolve_loop()

    self.assertTrue(status.is_resolved())
    self.assertTrue(self.char.delayed)
    self.assertEqual(status.status_change, 1)

  def testDoubleDelayed(self):
    status = StatusChange(self.char, "delayed", positive=True)
    self.assertFalse(status.is_resolved())
    self.char.delayed = True

    self.state.event_stack.append(status)
    self.resolve_loop()

    self.assertTrue(status.is_resolved())
    self.assertTrue(self.char.delayed)
    self.assertEqual(status.status_change, 0)

  def testLoseRetainer(self):
    status = StatusChange(self.char, "retainer", positive=False)
    self.assertFalse(status.is_resolved())
    self.char.retainer = True

    self.state.event_stack.append(status)
    self.resolve_loop()

    self.assertTrue(status.is_resolved())
    self.assertFalse(self.char.retainer)
    self.assertEqual(status.status_change, -1)

  def testDoubleBlessed(self):
    status = StatusChange(self.char, "bless_curse", positive=True)
    self.assertFalse(status.is_resolved())
    self.char.bless_curse = 1

    self.state.event_stack.append(status)
    self.resolve_loop()

    self.assertTrue(status.is_resolved())
    self.assertEqual(self.char.bless_curse, 1)
    self.assertEqual(status.status_change, 0)

  def testCursedWhileBlessed(self):
    status = StatusChange(self.char, "bless_curse", positive=False)
    self.assertFalse(status.is_resolved())
    self.char.bless_curse = 1

    self.state.event_stack.append(status)
    self.resolve_loop()

    self.assertTrue(status.is_resolved())
    self.assertEqual(self.char.bless_curse, 0)
    self.assertEqual(status.status_change, -1)


class DrawTest(EventTest):

  def testDrawFood(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.common.append(items.Food)

    self.state.event_stack.append(draw)
    self.resolve_loop()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertFalse(self.state.common)

  def testDrawFoodNoneLeft(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)

    self.state.event_stack.append(draw)
    self.resolve_loop()

    self.assertTrue(draw.is_resolved())
    self.assertFalse(self.char.possessions)

  def testDrawFoodTwoInDeck(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.common.append(items.Food)
    self.state.common.append(items.Food)

    self.state.event_stack.append(draw)
    self.resolve_loop()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 1)


class AttributePrerequisiteTest(EventTest):

  def testPrereq(self):
    prereq = AttributePrerequisite(self.char, "money", 2, "at least")
    self.assertEqual(self.char.money, 0)
    self.assertFalse(prereq.is_resolved())

    self.state.event_stack.append(prereq)
    self.resolve_loop()

    self.assertTrue(prereq.is_resolved())
    self.assertEqual(prereq.successes, 0)

  def testPrereq(self):
    prereq = AttributePrerequisite(self.char, "money", 2, "at least")
    self.char.money = 2
    self.assertFalse(prereq.is_resolved())

    self.state.event_stack.append(prereq)
    self.resolve_loop()

    self.assertTrue(prereq.is_resolved())
    self.assertEqual(prereq.successes, 1)


class CheckTest(EventTest):

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 5, 1, 3]))
  def testCheck(self):
    check = Check(self.char, "speed", 0)
    self.assertEqual(self.char.speed, 4)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_loop()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice_result)
    self.assertListEqual(check.dice_result.roll, [4, 5, 1, 3])
    self.assertEqual(check.successes, 1)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 4]))
  def testCheckWithModifier(self):
    check = Check(self.char, "will", 1)
    self.assertEqual(self.char.will, 1)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_loop()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice_result)
    self.assertListEqual(check.dice_result.roll, [4, 4])
    self.assertEqual(check.successes, 0)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4]))
  def testCheck(self):
    check = Check(self.char, "sneak", 0)
    self.assertEqual(self.char.sneak, 1)
    self.char.bless_curse = 1
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_loop()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice_result)
    self.assertListEqual(check.dice_result.roll, [4])
    self.assertEqual(check.successes, 1)


class ConditionalTest(EventTest):

  def createConditional(self):
    check = Check(self.char, "luck", 0)
    success_result = Gain(self.char, {"clues": 1})
    fail_result = Loss(self.char, {"sanity": 1})
    return Conditional(self.char, check, success_result=success_result, fail_result=fail_result)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5]))
  def testPassCondition(self):
    cond = self.createConditional()
    self.assertFalse(cond.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(cond)
    self.resolve_loop()

    self.assertTrue(cond.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.clues, 1)
    self.assertTrue(cond.success_map[1].is_resolved())
    self.assertFalse(cond.success_map[0].is_resolved())

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3]))
  def testFailCondition(self):
    cond = self.createConditional()
    self.assertFalse(cond.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(cond)
    self.resolve_loop()

    self.assertTrue(cond.is_resolved())
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(cond.success_map[0].is_resolved())
    self.assertFalse(cond.success_map[1].is_resolved())


if __name__ == '__main__':
  unittest.main()
