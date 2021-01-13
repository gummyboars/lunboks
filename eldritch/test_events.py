#!/usr/bin/env python3

import collections
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
import eldritch.monsters as monsters
import eldritch.places as places


class EventTest(unittest.TestCase):

  def setUp(self):
    self.char = characters.Character("Dummy", 5, 5, 4, 4, 4, 4, 4, 4, 4, places.Diner)
    self.state = eldritch.GameState()
    self.state.characters = [self.char]

  def resolve_loop(self):
    count = 0
    for thing in self.state.resolve_loop():  # It's a generator, so you have to loop through it.
      count += 1
      if count > 100:
        self.fail("Exceeded maximum number of events")
    self.assertFalse(self.state.event_stack)

  def resolve_until(self, event_class):
    count = 0
    for thing in self.state.resolve_loop():
      count += 1
      if count > 100:
        self.fail("Exceeded maximum number of events")
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], event_class)
    return self.state.event_stack[-1]


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
    movement = Movement(self.char, [self.state.places["Easttown"]])
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_loop()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertEqual(self.char.movement_points, 3)

  def testMoveMultipleSpaces(self):
    movement = Movement(
        self.char, [self.state.places[name] for name in ["Easttown", "Rivertown", "Graveyard"]])
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
    gain = Gain(self.char, {"dollars": 2, "clues": 1})
    self.assertFalse(gain.is_resolved())
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.clues, 0)

    self.state.event_stack.append(gain)
    self.resolve_loop()

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
    loss = Loss(self.char, {"clues": 2, "dollars": 1})
    self.assertFalse(loss.is_resolved())
    self.char.dollars = 2
    self.char.clues = 1

    self.state.event_stack.append(loss)
    self.resolve_loop()

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
    self.state.common.append(items.Food())

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
    self.state.common.append(items.Food())
    self.state.common.append(items.Food())

    self.state.event_stack.append(draw)
    self.resolve_loop()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 1)


class AttributePrerequisiteTest(EventTest):

  def testPrereq(self):
    prereq = AttributePrerequisite(self.char, "dollars", 2, "at least")
    self.assertEqual(self.char.dollars, 0)
    self.assertFalse(prereq.is_resolved())

    self.state.event_stack.append(prereq)
    self.resolve_loop()

    self.assertTrue(prereq.is_resolved())
    self.assertEqual(prereq.successes, 0)

  def testPrereq(self):
    prereq = AttributePrerequisite(self.char, "dollars", 2, "at least")
    self.char.dollars = 2
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
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.dice.roll, [4, 5, 1, 3])
    self.assertEqual(check.successes, 1)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 4]))
  def testCheckWithModifier(self):
    check = Check(self.char, "will", 1)
    self.assertEqual(self.char.will, 1)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_loop()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.dice.roll, [4, 4])
    self.assertEqual(check.successes, 0)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4]))
  def testCheckBlessed(self):
    check = Check(self.char, "sneak", 0)
    self.assertEqual(self.char.sneak, 1)
    self.char.bless_curse = 1
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_loop()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.dice.roll, [4])
    self.assertEqual(check.successes, 1)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[2, 4]))
  def testSubCheck(self):
    check = Check(self.char, "horror", 0)
    self.char.possessions.append(abilities.Will())
    self.assertEqual(self.char.will, 2)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_loop()

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
    self.resolve_loop()

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
    self.resolve_loop()

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
        the_choice = self.resolve_until(MultipleChoice)

        self.assertIs(the_choice, choice)
        choice.resolve(self.state, chosen)
        self.assertEqual(len(self.state.event_stack), 2)
        self.resolve_loop()

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

    with self.assertRaises(AssertionError):
      self.resolve_loop()  # Cannot resolve a choice normally.

    with self.assertRaises(AssertionError):
      choice.resolve(self.state, [2])
    with self.assertRaises(AssertionError):
      choice.resolve(self.state, [0, 1, 2])
    choice.resolve(self.state, [0, 1])
    self.assertListEqual(choice.choices, self.char.possessions[:2])

    self.resolve_loop()
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
    self.resolve_loop()

    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[2].active)


class CombatTest(EventTest):

  def testCombatFight(self):
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.fight, 1)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_until(MultipleChoice)
    self.assertIn("or flee", fight_or_flee.prompt())
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_until(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1])):
      self.resolve_loop()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertFalse(combat.combat.damage.is_resolved())
    self.assertTrue(combat.is_resolved())

  def testCombatFightThenFlee(self):
    self.char.fight_will_slider = 0
    self.char.speed_sneak_slider = 0
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sneak, 4)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_until(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_round = combat.combat
    evade_round = combat.evade
    choose_weapons = self.resolve_until(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_until(MultipleChoice)

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(evade_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertTrue(combat_round.damage.is_resolved())
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.stamina, 4)

    next_fight_or_flee.resolve(self.state, "Flee")
    next_combat_round = combat.combat
    next_evade_round = combat.evade

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_loop()

    self.assertFalse(next_combat_round.is_resolved())
    self.assertTrue(next_evade_round.is_resolved())
    self.assertTrue(next_evade_round.evaded)
    self.assertFalse(next_evade_round.damage.is_resolved())
    self.assertTrue(combat.is_resolved())

  def testCombatWithHorror(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.fight, 4)
    self.assertEqual(self.char.will, 1)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    # The horror check happens here - they are guaranteed to fail becuse they have only 1 will.
    fight_or_flee = self.resolve_until(MultipleChoice)
    self.assertIsNotNone(combat.horror)
    self.assertTrue(combat.horror.is_resolved())
    self.assertEqual(self.char.sanity, 4)

    combat_round = combat.combat
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_until(CombatChoice)
    choose_weapons.resolve(self.state, [])

    # Fail the combat check. After this, we check that there is not a second horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_until(MultipleChoice)

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertTrue(combat_round.damage.is_resolved())
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)  # Assert there wasn't a second horror check/loss.

    combat_round = combat.combat
    next_fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_until(CombatChoice)
    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_loop()

    self.assertTrue(combat_round.is_resolved())
    self.assertTrue(combat_round.defeated)
    self.assertFalse(combat_round.damage.is_resolved())
    self.assertTrue(combat.is_resolved())

  def testEvadeMeansNoHorror(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.will, 1)
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    choice = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(choice)

    fight_or_evade = self.resolve_until(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_loop()

    self.assertFalse(choice.combat.is_resolved())
    self.assertTrue(choice.evade.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertTrue(choice.is_resolved())

  def testFailEvadeMeansCombat(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.will, 1)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    choice = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(choice)

    fight_or_evade = self.resolve_until(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")

    # While here, they will fail the horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until(MultipleChoice)

    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 3)


if __name__ == '__main__':
  unittest.main()
