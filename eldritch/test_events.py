#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.abilities as abilities
import eldritch.characters as characters
import eldritch.eldritch as eldritch
import eldritch.events as events
from eldritch.events import *
import eldritch.items as items
import eldritch.places as places


class EventTest(unittest.TestCase):

  def setUp(self):
    self.char = characters.Character("Dummy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Diner")
    self.state = eldritch.GameState()
    self.state.initialize()
    for attr in ["common", "unique", "spells", "skills", "allies"]:
      getattr(self.state, attr).clear()
    self.state.characters = [self.char]
    self.char.place = self.state.places[self.char.home]

  def resolve_loop(self):
    count = 0
    for thing in self.state.resolve_loop():  # It's a generator, so you have to loop through it.
      count += 1
      if count > 100:
        self.fail("Exceeded maximum number of events")

  def resolve_until_done(self):
    self.resolve_loop()
    self.assertFalse(self.state.event_stack)

  def resolve_to_choice(self, event_class):
    self.resolve_loop()
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], event_class)
    return self.state.event_stack[-1]

  def resolve_to_usable(self, char_idx, item_idx, event_class):
    self.resolve_loop()
    self.assertTrue(self.state.event_stack)
    self.assertIn(char_idx, self.state.usables)
    self.assertIn(item_idx, self.state.usables[char_idx])
    self.assertIsInstance(self.state.usables[char_idx][item_idx], event_class)
    return self.state.usables[char_idx][item_idx]


class DiceRollTest(EventTest):

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4]))
  def testDieRoll(self):
    die_roll = DiceRoll(self.char, 1)
    self.assertFalse(die_roll.is_resolved())
    self.assertIsNone(die_roll.roll)

    self.state.event_stack.append(die_roll)
    self.resolve_until_done()

    self.assertTrue(die_roll.is_resolved())
    self.assertListEqual(die_roll.roll, [4])

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 1, 5]))
  def testDiceRolls(self):
    dice_roll = DiceRoll(self.char, 3)
    self.assertFalse(dice_roll.is_resolved())
    self.assertIsNone(dice_roll.roll)

    self.state.event_stack.append(dice_roll)
    self.resolve_until_done()

    self.assertTrue(dice_roll.is_resolved())
    self.assertListEqual(dice_roll.roll, [4, 1, 5])

  def testNoRolls(self):
    dice_roll = DiceRoll(self.char, -1)
    self.assertFalse(dice_roll.is_resolved())
    self.assertIsNone(dice_roll.roll)

    self.state.event_stack.append(dice_roll)
    self.resolve_until_done()

    self.assertTrue(dice_roll.is_resolved())
    self.assertListEqual(dice_roll.roll, [])


class MovementTest(EventTest):

  def testMoveOneSpace(self):
    movement = Movement(self.char, [self.state.places["Easttown"]])
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertEqual(self.char.movement_points, 3)

  def testMoveMultipleSpaces(self):
    movement = Movement(
        self.char, [self.state.places[name] for name in ["Easttown", "Rivertown", "Graveyard"]])
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Graveyard")
    self.assertEqual(self.char.movement_points, 1)

  def testForceMovement(self):
    movement = ForceMovement(self.char, "Graveyard")
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Graveyard")
    self.assertEqual(self.char.movement_points, 4)

  def testLoseExploredOnMovement(self):
    self.char.place = self.state.places["Graveyard"]
    self.char.explored = True
    movement = Movement(self.char, [self.state.places["Rivertown"]])

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Rivertown")
    self.assertFalse(self.char.explored)

  def testLoseExploredOnForceMovement(self):
    self.char.place = self.state.places["Graveyard"]
    self.char.explored = True
    movement = ForceMovement(self.char, "Witch")

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Witch")
    self.assertFalse(self.char.explored)


class GainLossTest(EventTest):

  def testGain(self):
    gain = Gain(self.char, {"dollars": 2, "clues": 1})
    self.assertFalse(gain.is_resolved())
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.clues, 0)

    self.state.event_stack.append(gain)
    self.resolve_until_done()

    self.assertTrue(gain.is_resolved())
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.clues, 1)
    self.assertDictEqual(gain.final_adjustments, {"dollars": 2, "clues": 1})

  def testLoss(self):
    loss = Loss(self.char, {"sanity": 2, "stamina": 1})
    self.assertFalse(loss.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)

    self.state.event_stack.append(loss)
    self.resolve_until_done()

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
    self.resolve_until_done()

    self.assertTrue(gain.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.assertDictEqual(gain.final_adjustments, {"sanity": 1, "stamina": 0})

  def testOverloss(self):
    loss = Loss(self.char, {"clues": 2, "dollars": 1})
    self.assertFalse(loss.is_resolved())
    self.char.dollars = 2
    self.char.clues = 1

    self.state.event_stack.append(loss)
    self.resolve_until_done()

    self.assertTrue(loss.is_resolved())
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(self.char.clues, 0)
    self.assertDictEqual(loss.final_adjustments, {"clues": -1, "dollars": -1})

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 1]))
  def testDieRollLoss(self):
    # Use an ordered dict to make sure we lose 4 sanity and 1 stamina.
    sanity_die = DiceRoll(self.char, 1)
    stamina_die = DiceRoll(self.char, 1)
    loss = Loss(self.char, {"sanity": sanity_die, "stamina": stamina_die})
    self.assertFalse(loss.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    event = Sequence([sanity_die, stamina_die, loss])

    self.state.event_stack.append(event)
    self.resolve_until_done()

    self.assertTrue(loss.is_resolved())
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 4)
    self.assertDictEqual(loss.final_adjustments, {"sanity": -4, "stamina": -1})


class SplitGainTest(EventTest):

  def testSplitNumber(self):
    self.char.stamina = 1
    self.char.sanity = 1
    split_gain = SplitGain(self.char, "stamina", "sanity", 3)

    self.state.event_stack.append(split_gain)
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1, 2, 3])
    self.assertIn("go to stamina", choice.prompt())
    choice.resolve(self.state, 2)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 2)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5))
  def testSplitDieRoll(self):
    self.char.stamina = 1
    self.char.sanity = 1
    die_roll = DiceRoll(self.char, 1)
    split_gain = SplitGain(self.char, "stamina", "sanity", die_roll)

    self.state.event_stack.append(Sequence([die_roll, split_gain], self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1, 2, 3, 4, 5])
    self.assertIn("go to stamina", choice.prompt())
    choice.resolve(self.state, 2)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)

  def testSplitChoice(self):
    self.char.stamina = 1
    self.char.sanity = 1
    first_choice = MultipleChoice(self.char, "prompt", [0, 1, 2, 3, 4, 5])
    split_gain = SplitGain(self.char, "stamina", "sanity", first_choice)

    self.state.event_stack.append(Sequence([first_choice, split_gain], self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice, first_choice)
    first_choice.resolve(self.state, 4)

    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, [0, 1, 2, 3, 4])
    self.assertIn("go to stamina", choice.prompt())
    choice.resolve(self.state, 3)
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 2)


class StatusChangeTest(EventTest):

  def testDelayed(self):
    delay = Delayed(self.char)
    self.assertFalse(delay.is_resolved())
    self.assertIsNone(self.char.delayed_until)

    self.state.event_stack.append(delay)
    self.resolve_until_done()

    self.assertTrue(delay.is_resolved())
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)
    self.assertEqual(delay.until, self.char.delayed_until)
    self.assertIsNone(self.char.lose_turn_until)

  def testDoubleDelayed(self):
    self.char.delayed_until = self.state.turn_number + 1
    delay = Delayed(self.char)
    self.assertFalse(delay.is_resolved())

    self.state.event_stack.append(delay)
    self.resolve_until_done()

    self.assertTrue(delay.is_resolved())
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)
    self.assertEqual(delay.until, self.char.delayed_until)
    self.assertIsNone(self.char.lose_turn_until)

  def testLoseTurn(self):
    lose_turn = LoseTurn(self.char)
    self.assertFalse(lose_turn.is_resolved())
    self.assertIsNone(self.char.lose_turn_until)

    self.state.event_stack.append(lose_turn)
    self.resolve_until_done()

    self.assertTrue(lose_turn.is_resolved())
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)
    self.assertEqual(lose_turn.until, self.char.lose_turn_until)
    self.assertIsNone(self.char.delayed_until)

  def testLoseRetainer(self):
    status = StatusChange(self.char, "retainer", positive=False)
    self.assertFalse(status.is_resolved())
    self.char.retainer_start = 2

    self.state.event_stack.append(status)
    self.resolve_until_done()

    self.assertTrue(status.is_resolved())
    self.assertIsNone(self.char.retainer_start)
    self.assertEqual(status.change, -1)

  def testBecomeMember(self):
    member = MembershipChange(self.char, True)
    self.assertFalse(self.char.lodge_membership)

    self.state.event_stack.append(member)
    self.resolve_until_done()

    self.assertTrue(self.char.lodge_membership)
    self.assertEqual(member.change, 1)

  def testDoubleBlessed(self):
    bless = Bless(self.char)
    self.assertFalse(bless.is_resolved())
    self.char.bless_curse = 1
    self.char.bless_curse_start = 1

    self.state.event_stack.append(bless)
    self.resolve_until_done()

    self.assertTrue(bless.is_resolved())
    self.assertEqual(self.char.bless_curse, 1)
    self.assertEqual(self.char.bless_curse_start, self.state.turn_number + 2)
    self.assertEqual(bless.change, 0)

  def testCursedWhileBlessed(self):
    curse = Curse(self.char)
    self.assertFalse(curse.is_resolved())
    self.char.bless_curse = 1
    self.char.bless_curse_start = 1

    self.state.event_stack.append(curse)
    self.resolve_until_done()

    self.assertTrue(curse.is_resolved())
    self.assertEqual(self.char.bless_curse, 0)
    self.assertIsNone(self.char.bless_curse_start)
    self.assertEqual(curse.change, -1)

  def testArrested(self):
    self.char.dollars = 5
    self.assertEqual(self.char.place.name, "Diner")
    self.assertIsNone(self.char.lose_turn_until)
    arrest = Arrested(self.char)

    self.state.event_stack.append(arrest)
    self.resolve_until_done()

    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.place.name, "Police")


class DrawTest(EventTest):

  def testDrawFood(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.common.append(items.Food())

    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertFalse(self.state.common)

  def testDrawFoodNoneLeft(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)

    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertFalse(self.char.possessions)

  def testDrawFoodTwoInDeck(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.common.append(items.Food())
    self.state.common.append(items.Food())

    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 1)


class DrawRandomTest(EventTest):

  def testDrawOneCard(self):
    draw = Draw(self.char, "common", 1)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food()
    self.state.common.append(food)

    # When you only draw one card, you do not get a choice.
    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(self.char.possessions, [food])
    self.assertFalse(self.state.common)

  def testDrawTwoKeepOne(self):
    draw = Draw(self.char, "common", 2)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    dynamite = items.Dynamite()
    self.state.common.extend([
      items.Food(), dynamite, items.Revolver38(), items.TommyGun(), items.Bullwhip()])

    self.state.event_stack.append(draw)
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Food", "Dynamite"])

    choice.resolve(self.state, "Dynamite")
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(self.char.possessions, [dynamite])
    # Since two items were drawn and one was discarded, the discarded item should go on bottom.
    self.assertEqual(
        [item.name for item in self.state.common],
        [".38 Revolver", "Tommy Gun", "Bullwhip", "Food"]
    )

  def testDrawTwoOnlyOneLeft(self):
    draw = Draw(self.char, "common", 2)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food()
    self.state.common.append(food)

    # Should be handled gracefully if you are instructed to draw more cards than are in the deck.
    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(self.char.possessions, [food])
    self.assertFalse(self.state.common)

  def testDrawSpecificTypeTop(self):
    draw = Draw(self.char, "common", 1, target_type=items.Weapon)
    tommygun = items.TommyGun()
    self.state.common.extend([tommygun, items.Food(), ])
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertEqual(self.char.possessions, [tommygun])
    self.assertEqual([item.name for item in self.state.common], ["Food"])

  def testDrawSpecificTypeMiddle(self):
    draw = Draw(self.char, "common", 1, target_type=items.Weapon)
    tommygun = items.TommyGun()
    self.state.common.extend([items.Food(), tommygun, items.Dynamite(), ])
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertEqual(self.char.possessions, [tommygun])
    self.assertEqual([item.name for item in self.state.common], ["Dynamite", "Food"])

  def testDrawSpecificTypeNone(self):
    draw = Draw(self.char, "common", 1, target_type=items.ResearchMaterials)
    tommygun = items.TommyGun()
    self.state.common.extend([items.Food(), tommygun, items.Dynamite(), ])
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertEqual(self.char.possessions, [])
    self.assertEqual([item.name for item in self.state.common], ["Food", "Tommy Gun", "Dynamite", ])



class DiscardNamedTest(EventTest):
  def testDiscardNamed(self):
    self.char.possessions.append(items.Food())
    self.char.possessions.append(items.TommyGun())
    discard = DiscardNamed(self.char, "Food")
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, 'Tommy Gun')
    self.assertEqual(len(self.state.common), 1)

  def testDontHave(self):
    self.char.possessions.append(items.TommyGun())
    discard = DiscardNamed(self.char, "Food")
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertEqual(discard.finish_str(), "Dummy did not have a Food to discard")


class AttributePrerequisiteTest(EventTest):

  def testPrereq(self):
    prereq = AttributePrerequisite(self.char, "dollars", 2, "at least")
    self.assertEqual(self.char.dollars, 0)
    self.assertFalse(prereq.is_resolved())

    self.state.event_stack.append(prereq)
    self.resolve_until_done()

    self.assertTrue(prereq.is_resolved())
    self.assertEqual(prereq.successes, 0)

  def testPrereq(self):
    prereq = AttributePrerequisite(self.char, "dollars", 2, "at least")
    self.char.dollars = 2
    self.assertFalse(prereq.is_resolved())

    self.state.event_stack.append(prereq)
    self.resolve_until_done()

    self.assertTrue(prereq.is_resolved())
    self.assertEqual(prereq.successes, 1)


class CheckTest(EventTest):

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 5, 1, 3]))
  def testCheck(self):
    check = Check(self.char, "speed", 0)
    self.assertEqual(self.char.speed(self.state), 4)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_until_done()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.dice.roll, [4, 5, 1, 3])
    self.assertEqual(check.successes, 1)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 4]))
  def testCheckWithModifier(self):
    check = Check(self.char, "will", 1)
    self.assertEqual(self.char.will(self.state), 1)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_until_done()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.dice.roll, [4, 4])
    self.assertEqual(check.successes, 0)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4]))
  def testCheckBlessed(self):
    check = Check(self.char, "sneak", 0)
    self.assertEqual(self.char.sneak(self.state), 1)
    self.char.bless_curse = 1
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_until_done()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.dice.roll, [4])
    self.assertEqual(check.successes, 1)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[2, 4]))
  def testSubCheck(self):
    check = Check(self.char, "horror", 0)
    self.char.possessions.append(abilities.Will())
    self.assertEqual(self.char.will(self.state), 2)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_until_done()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.roll, [2, 4])


class ConditionalTest(EventTest):

  def createConditional(self):
    check = Check(self.char, "luck", 0)
    success_result = Gain(self.char, {"clues": 1})
    fail_result = Loss(self.char, {"sanity": 1})
    cond = Conditional(self.char, check, "successes", {1: success_result, 0: fail_result})
    return Sequence([check, cond])

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5))
  def testPassCondition(self):
    seq = self.createConditional()
    cond = seq.events[1]
    self.assertFalse(seq.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(seq)
    self.resolve_until_done()

    self.assertTrue(seq.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.clues, 1)
    self.assertTrue(cond.result_map[1].is_resolved())
    self.assertFalse(cond.result_map[0].is_resolved())

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3))
  def testFailCondition(self):
    seq = self.createConditional()
    cond = seq.events[1]
    self.assertFalse(seq.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(seq)
    self.resolve_until_done()

    self.assertTrue(seq.is_resolved())
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(cond.result_map[0].is_resolved())
    self.assertFalse(cond.result_map[1].is_resolved())


class BinaryChoiceTest(EventTest):

  def createChoice(self):
    yes_result = Gain(self.char, {"dollars": 1})
    no_result = Loss(self.char, {"dollars": 1})
    return BinaryChoice(self.char, "Get Money?", "Yes", "No", yes_result, no_result)

  def testChoices(self):
    for chosen, expected_dollars in [("Yes", 4), ("No", 2)]:
      with self.subTest(choice=chosen):
        seq = self.createChoice()
        choice = seq.events[0]
        self.assertEqual(choice.prompt(), "Get Money?")
        self.assertFalse(seq.is_resolved())
        self.char.dollars = 3

        self.state.event_stack.append(seq)
        the_choice = self.resolve_to_choice(MultipleChoice)

        self.assertIs(the_choice, choice)
        choice.resolve(self.state, chosen)
        self.assertEqual(len(self.state.event_stack), 2)
        self.resolve_until_done()

        self.assertEqual(self.char.dollars, expected_dollars)


class ItemChoiceTest(EventTest):

  def setUp(self):
    super(ItemChoiceTest, self).setUp()
    self.char.possessions.append(items.Revolver38())
    self.char.possessions.append(items.Food())
    self.char.possessions.append(items.HolyWater())

  def testCountChoice(self):
    choice = ItemCountChoice(self.char, "choose 2", 2)
    self.state.event_stack.append(choice)

    self.resolve_to_choice(ItemCountChoice)

    with self.assertRaises(AssertionError):
      choice.resolve(self.state, [2])
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, [0, 1, 2])
    choice.resolve(self.state, [0, 1])
    self.assertListEqual(choice.choices, self.char.possessions[:2])

    self.resolve_until_done()
    self.assertFalse(self.state.event_stack)

  def testCombatChoice(self):
    choice = CombatChoice(self.char, "choose combat items")
    self.state.event_stack.append(choice)

    # Cannot use Food in combat.
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, [0, 1])

    # Cannot use three hands in combat.
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, [0, 2])

    choice.resolve(self.state, [2])
    self.resolve_until_done()

    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[2].active)


# TODO: add tests for going unconscious/insane during a mythos/encounter.


if __name__ == '__main__':
  unittest.main()
