#!/usr/bin/env python3

import math
import os
import sys
import unittest
from unittest import mock
from typing import TypeVar, Type

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import abilities
from eldritch import assets
from eldritch import characters
from eldritch import eldritch
from eldritch import encounters
from eldritch import events
from eldritch.events import *
from eldritch import gate_encounters
from eldritch import items
from eldritch import mythos
from eldritch import places
from eldritch import values
from eldritch import monsters


ChoiceT = TypeVar("ChoiceT", bound=events.ChoiceEvent)


class NoMythos(mythos.GlobalEffect):

  def __init__(self):
    self.name = "NoMythos"

  def create_event(self, state):  # pylint: disable=unused-argument
    return events.Nothing()


class Canceller(assets.Asset):

  def __init__(self, event_type, count=0):
    super().__init__("canceller", None)
    self.event_type = event_type
    self.count = count
    self.seen = []

  def get_interrupt(self, event, owner, state):
    if not isinstance(event, self.event_type):
      return None
    if id(event) not in self.seen:
      self.seen.append(id(event))
    if self.seen.index(id(event)) == self.count:
      return CancelEvent(event)
    return None


class EventTest(unittest.TestCase):

  def setUp(self):
    self.char = characters.Character("Dummy", 5, 5, 4, 4, 4, 4, 4, 4, 2, "Diner")
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.all_characters["Dummy"] = self.char
    self.state.characters = [self.char]
    self.char.place = self.state.places[self.char.home]

  def resolve_loop(self):
    count = 0
    for _ in self.state.resolve_loop():  # It's a generator, so you have to loop through it.
      count += 1
      if count > 100:
        self.fail(f"Exceeded maximum number of events: {self.state.event_stack}")

  def resolve_until_event_type(self, event_class):
    count = 0
    for _ in self.state.resolve_loop():
      count += 1
      if count > 100:
        self.fail(f"Exceeded maximum number of events: {self.state.event_stack}")
      if isinstance(self.state.event_stack[-1], event_class):
        return
    self.fail(f"Did not encounter an event of class {event_class}")

  def resolve_until_done(self):
    self.resolve_loop()
    not_finished = {}
    if self.state.usables:
      not_finished["usables"] = self.state.usables
    if self.state.event_stack:
      not_finished["stack"] = self.state.event_stack
    self.assertFalse(not_finished)

  def resolve_to_choice(self, event_class: Type[ChoiceT]) -> ChoiceT:
    self.resolve_loop()
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], event_class)
    return self.state.event_stack[-1]

  def choose_items(self, choice, handles):
    self.assertIsInstance(choice, ItemChoice)
    for handle in handles:
      choice.resolve(self.state, handle)
    choice.resolve(self.state, "done")

  def spend(self, spend_type, count, choice_event):
    self.assertIsInstance(choice_event, SpendMixin)
    for _ in range(count):
      choice_event.spend(spend_type)
    for _ in range(-count):
      choice_event.unspend(spend_type)
    # Go through the event loop one more time to make sure compute_choices updates remaining_spend.
    self.resolve_to_choice(SpendMixin)

  def toggle_spend(self, char_idx, handle, choice_event):
    self.assertIsInstance(choice_event, SpendMixin)
    self.assertIn(char_idx, self.state.spendables)
    self.assertIn(handle, self.state.spendables[char_idx])
    self.state.handle_use(char_idx, handle)
    self.resolve_to_choice(SpendMixin)

  def resolve_to_usable(self, char_idx, handle, event_class=events.Event):
    self.resolve_loop()
    self.assertTrue(self.state.event_stack)
    self.assertIn(char_idx, self.state.usables)
    self.assertIn(handle, self.state.usables[char_idx])
    self.assertIsInstance(self.state.usables[char_idx][handle], event_class)
    return self.state.usables[char_idx][handle]

  def use_handle(self, char_idx, handle):
    self.assertIn(char_idx, self.state.usables)
    self.assertIn(handle, self.state.usables[char_idx])
    self.state.event_stack.append(self.state.usables[char_idx][handle])
    self.resolve_to_choice(SpendMixin)

  def advance_turn(self, target_turn, target_phase):
    self.state.mythos.extend([NoMythos()] * (target_turn - self.state.turn_number + 1))
    # TODO: should actually add a number of NoMythos - current turn - existing cards in mythos deck
    while True:
      for _ in self.state.resolve_loop():
        if self.state.turn_number >= target_turn and self.state.turn_phase == target_phase:
          break
      if self.state.turn_number >= target_turn and self.state.turn_phase == target_phase:
        break
      if not self.state.event_stack:
        self.state.next_turn()
        if self.state.turn_number >= target_turn and self.state.turn_phase == target_phase:
          break
        continue
      if self.state.turn_phase == "upkeep":
        self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
        self.state.event_stack[-1].resolve(self.state, "done", None)
      elif self.state.turn_phase == "movement":
        self.assertIsInstance(self.state.event_stack[-1], events.CityMovement)
        self.state.event_stack[-1].resolve(self.state, "done")

  def _formatMessage(self, msg, standardMsg):
    ret = super()._formatMessage(msg, standardMsg)
    return ret + "\n\n" + "\n".join(str(log) for log in self.state.event_log)


class SequenceTest(EventTest):

  def testSequence(self):
    seq = Sequence([DiceRoll(self.char, 1), Delayed(self.char), Gain(self.char, {"dollars": 1})])
    self.state.event_stack.append(seq)
    self.resolve_until_done()
    self.assertTrue(seq.is_resolved())
    self.assertFalse(seq.is_cancelled())
    self.assertTrue(seq.events[0].is_resolved())
    self.assertTrue(seq.events[1].is_resolved())
    self.assertTrue(seq.events[2].is_resolved())

  def testSequenceWithCancelledEvent(self):
    self.char.possessions.append(Canceller(DelayOrLoseTurn))
    seq = Sequence([DiceRoll(self.char, 1), Delayed(self.char), Gain(self.char, {"dollars": 1})])
    self.state.event_stack.append(seq)
    self.resolve_until_done()
    self.assertTrue(seq.is_resolved())
    self.assertFalse(seq.is_cancelled())
    self.assertTrue(seq.events[0].is_resolved())
    self.assertFalse(seq.events[1].is_resolved())
    self.assertTrue(seq.events[1].is_cancelled())
    self.assertTrue(seq.events[2].is_resolved())


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


class UpkeepTest(EventTest):

  def testReceiveFocus(self):
    self.char.focus_points = 0
    self.state.event_stack.append(Upkeep(self.char))
    self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.focus_points, 2)

  def testUpkeepRolls(self):
    pass  # TODO: blessings/curses, bank loans, retainers


class SliderTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.event_stack.append(Upkeep(self.char))
    self.sliders = self.resolve_to_choice(SliderInput)
    self.assertFalse(self.sliders.is_resolved())

  def testMoveSliders(self):
    self.sliders.resolve(self.state, "speed_sneak", 1)
    self.sliders.resolve(self.state, "done", None)
    self.assertTrue(self.sliders.is_resolved())
    self.assertEqual(self.char.focus_points, 0)
    self.assertEqual(self.char.speed_sneak_slider, 1)
    self.assertEqual(self.char.fight_will_slider, 3)
    self.assertEqual(self.char.lore_luck_slider, 3)

  def testTryOverspendFocus(self):
    with self.assertRaisesRegex(InvalidMove, "enough focus"):
      self.sliders.resolve(self.state, "speed_sneak", 0)

  def testChangeMindOnSliders(self):
    self.sliders.resolve(self.state, "speed_sneak", 1)
    with self.assertRaisesRegex(InvalidMove, "enough focus"):
      self.sliders.resolve(self.state, "fight_will", 2)
    self.sliders.resolve(self.state, "speed_sneak", 2)
    self.sliders.resolve(self.state, "fight_will", 2)
    self.sliders.resolve(self.state, "done", None)
    self.assertTrue(self.sliders.is_resolved())
    self.assertEqual(self.char.focus_points, 0)
    self.assertEqual(self.char.speed_sneak_slider, 2)
    self.assertEqual(self.char.fight_will_slider, 2)
    self.assertEqual(self.char.lore_luck_slider, 3)

  def testResetSliders(self):
    self.sliders.resolve(self.state, "speed_sneak", 2)
    self.sliders.resolve(self.state, "fight_will", 2)
    self.sliders.resolve(self.state, "reset", None)
    self.sliders.resolve(self.state, "done", None)
    self.assertTrue(self.sliders.is_resolved())
    self.assertEqual(self.char.focus_points, 2)
    self.assertEqual(self.char.speed_sneak_slider, 3)
    self.assertEqual(self.char.fight_will_slider, 3)
    self.assertEqual(self.char.lore_luck_slider, 3)

  def testFreeSliders(self):
    self.sliders.free = True
    self.sliders.resolve(self.state, "speed_sneak", 0)
    self.sliders.resolve(self.state, "fight_will", 0)
    self.sliders.resolve(self.state, "done", None)
    self.assertTrue(self.sliders.is_resolved())
    self.assertEqual(self.char.focus_points, 2)
    self.assertEqual(self.char.speed_sneak_slider, 0)
    self.assertEqual(self.char.fight_will_slider, 0)
    self.assertEqual(self.char.lore_luck_slider, 3)


class MovementPhaseTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.turn_phase = "movement"
    self.char.movement_points = 0
    self.movement = Movement(self.char)
    self.state.event_stack.append(self.movement)

  def testDelayed(self):
    self.char.delayed_until = self.state.turn_number + 1
    self.resolve_until_done()

    self.assertEqual(self.char.delayed_until, self.state.turn_number + 1)
    self.assertIsNone(self.movement.move)
    self.assertEqual(self.char.movement_points, 0)

  def testNoLongerDelayed(self):
    self.char.delayed_until = self.state.turn_number
    self.resolve_to_choice(CityMovement)

    self.assertIsNone(self.char.delayed_until)
    self.assertEqual(self.char.movement_points, 4)

  def testChoiceInCity(self):
    movement = self.resolve_to_choice(CityMovement)
    self.assertIn("Easttown", movement.choices)
    self.assertIn("Graveyard", movement.choices)

    annotations = movement.annotations(self.state)
    self.assertEqual(len(annotations), len(movement.choices))
    self.assertEqual(annotations[movement.choices.index("Easttown")], "Move (1)")
    self.assertEqual(annotations[movement.choices.index("Graveyard")], "Move (3)")

  def testMoveInOtherWorld(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Dreamlands2")

  def testCancelledMovement(self):
    self.char.possessions.append(Canceller(CityMovement))
    self.resolve_until_done()
    self.assertFalse(self.movement.move.is_resolved())
    self.assertTrue(self.movement.move.is_cancelled())
    self.assertTrue(self.movement.is_resolved())
    self.assertEqual(self.char.place.name, "Diner")

  def testCancelledOtherWorld(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.char.possessions.append(Canceller(ForceMovement))
    self.resolve_until_done()
    self.assertFalse(self.movement.move.is_resolved())
    self.assertTrue(self.movement.move.is_cancelled())
    self.assertTrue(self.movement.is_resolved())
    self.assertEqual(self.char.place.name, "Dreamlands1")

  def testLost(self):
    self.char.place = self.state.places["Lost"]
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")


class MovementPointsTest(EventTest):

  def testAddMovementPoints(self):
    self.state.turn_phase = "movement"
    self.char.movement_points = 2
    mov = ChangeMovementPoints(self.char, 3)
    self.assertFalse(mov.is_resolved())
    self.state.event_stack.append(mov)
    self.resolve_until_done()
    self.assertTrue(mov.is_resolved())
    self.assertEqual(mov.change, 3)

  def testLoseMovementPoints(self):
    self.state.turn_phase = "movement"
    self.char.movement_points = 3
    mov = ChangeMovementPoints(self.char, -2)
    self.state.event_stack.append(mov)
    self.resolve_until_done()
    self.assertEqual(mov.change, -2)

  def testMinZeroMovementPoints(self):
    self.state.turn_phase = "movement"
    self.char.movement_points = 2
    mov = ChangeMovementPoints(self.char, -3)
    self.state.event_stack.append(mov)
    self.resolve_until_done()
    self.assertEqual(mov.change, -2)


class LostInTimeAndSpaceTest(EventTest):

  def testNoReturnGatesMeansLost(self):
    self.char.clues = 6
    self.state.turn_phase = "movement"
    self.char.place = self.state.places["Dreamlands2"]
    self.state.event_stack.append(events.Movement(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Lost")
    self.assertEqual(self.char.clues, 6)  # You do not lose clues/items when lost in time and space.

  def testRecoverFromLostInTimeAndSpace(self):
    self.state.turn_phase = "movement"
    self.state.event_stack.append(LostInTimeAndSpace(self.char))
    self.resolve_until_done()
    self.advance_turn(self.state.turn_number+1, "movement")
    self.assertIsInstance(self.state.event_stack[-1], Movement)
    self.resolve_until_done()  # Player's turn is skipped.
    self.advance_turn(self.state.turn_number+1, "upkeep")
    self.assertIsInstance(self.state.event_stack[-1], Upkeep)

    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Uptown")
    self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.place.name, "Uptown")
    self.assertFalse(self.char.explored)


class MovementTest(EventTest):

  def testMoveOneSpace(self):
    movement = MoveOne(self.char, "Easttown")
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertEqual(self.char.movement_points, 3)

  def testEndMovementOnMonster(self):
    maniac = next(monster for monster in self.state.monsters if monster.name == "Maniac")
    self.char.speed_sneak_slider = 0
    self.char.place = self.state.places["Rivertown"]
    maniac.place = self.state.places["Easttown"]
    self.advance_turn(self.state.turn_number, "movement")
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, "Easttown")
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, "done")

    choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(choice.choices, ["Fight", "Evade"])
    choice.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testReturnFromGateToMonster(self):
    maniac = next(monster for monster in self.state.monsters if monster.name == "Maniac")
    gate = self.state.gates.popleft()
    self.state.places["Graveyard"].gate = gate
    self.char.place = self.state.places[gate.name + "2"]
    maniac.place = self.state.places["Graveyard"]
    self.advance_turn(self.state.turn_number, "movement")

    # When you return, you should get the choice to
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Ignore")
    self.resolve_until_done()

  def testReturnFromGateCard(self):
    maniac = next(monster for monster in self.state.monsters if monster.name == "Maniac")
    gate = self.state.gates.popleft()
    self.state.places["Graveyard"].gate = gate
    self.char.place = self.state.places[gate.name + "2"]
    maniac.place = self.state.places["Graveyard"]
    self.state.turn_phase = "otherworld"

    # Return during the otherworld encounter phase. The player does not encounter monsters.
    self.state.event_stack.append(gate_encounters.Dreamlands8(self.char))
    self.resolve_until_done()

  def testMoveOneSpaceToMonster(self):
    maniac = next(monster for monster in self.state.monsters if monster.name == "Maniac")
    self.char.place = self.state.places["Rivertown"]
    maniac.place = self.state.places["Easttown"]
    self.advance_turn(self.state.turn_number, "movement")
    # We give them a tome to make sure that it is not usable after they have fought the maniac.
    self.char.possessions.append(items.AncientTome(0))
    movement = self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.movement_points, 4)
    movement.resolve(self.state, "Easttown")
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, "Downtown")

    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Fight", "Evade"])
    choice.resolve(self.state, "Fight")

    next_choice = self.resolve_to_choice(MultipleChoice)
    self.assertCountEqual(next_choice.choices, ["Flee", "Fight"])
    next_choice.resolve(self.state, "Fight")

    third_choice = self.resolve_to_choice(CombatChoice)
    self.assertFalse(third_choice.choices)
    self.choose_items(third_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()  # You do not get to move again after fighting.

    self.assertEqual(self.char.place.name, "Easttown")
    self.assertIn(maniac, self.char.trophies)
    self.assertTrue(movement.is_done())

  def testMoveMultipleSpaces(self):
    movement = Sequence(
        [MoveOne(self.char, dest) for dest in ["Easttown", "Rivertown", "Graveyard"]], self.char)
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Graveyard")
    self.assertEqual(self.char.movement_points, 1)

  def testIllegalMoveMultipleSpaces(self):
    self.char.movement_points = 1
    movement = Sequence(
        [MoveOne(self.char, dest) for dest in ["Easttown", "Rivertown", "Graveyard"]],
        self.char,
    )
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 1)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertEqual(self.char.movement_points, 0)
    self.assertTrue(movement.events[0].moved)
    self.assertFalse(movement.events[1].moved)
    self.assertFalse(movement.events[2].moved)

  def testMoveMultipleThroughMonsterFight(self):
    # Like testMoveOneSpaceToMonster but starts with a multiple space move
    cultist = next(monster for monster in self.state.monsters if monster.name == "Cultist")
    cultist.place = self.state.places["Rivertown"]
    self.char.place = self.state.places["Downtown"]

    self.advance_turn(self.state.turn_number, "movement")
    movement = self.resolve_to_choice(CityMovement)
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)
    self.assertNotIn("Graveyard", movement.choices)
    self.assertIn("Rivertown", movement.choices)
    movement.resolve(self.state, "Rivertown")

    movement = self.resolve_to_choice(CityMovement)
    self.assertIn("Graveyard", movement.choices)
    movement.resolve(self.state, "Graveyard")

    choice = self.resolve_to_choice(MultipleChoice)

    self.assertEqual(choice.choices, ["Fight", "Evade"])
    choice.resolve(self.state, "Fight")

    next_choice = self.resolve_to_choice(MultipleChoice)
    self.assertCountEqual(next_choice.choices, ["Fight", "Flee"])
    next_choice.resolve(self.state, "Fight")

    third_choice = self.resolve_to_choice(CombatChoice)
    self.assertFalse(third_choice.choices)
    self.choose_items(third_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()  # Movement ends, do not get a CityMovement choice.

    self.assertTrue(movement.is_done())
    self.assertEqual(self.char.place.name, "Rivertown")
    self.assertIn(cultist, self.char.trophies)

  def testMoveMultipleThroughMonsterFailedEvade(self):
    zombie = monsters.Zombie()
    self.state.monsters.append(zombie)
    zombie.place = self.state.places["Rivertown"]
    self.char.place = self.state.places["Downtown"]

    self.advance_turn(self.state.turn_number, "movement")
    movement = self.resolve_to_choice(CityMovement)
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)
    self.assertNotIn("Graveyard", movement.choices)
    self.assertIn("Rivertown", movement.choices)
    movement.resolve(self.state, "Rivertown")

    movement = self.resolve_to_choice(CityMovement)
    self.assertIn("Graveyard", movement.choices)
    movement.resolve(self.state, "Graveyard")

    choice = self.resolve_to_choice(MultipleChoice)

    self.assertEqual(choice.choices, ["Fight", "Evade"])
    choice.resolve(self.state, "Evade")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_choice = self.resolve_to_choice(MultipleChoice)
    self.assertCountEqual(next_choice.choices, ["Fight", "Flee"])
    next_choice.resolve(self.state, "Flee")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # resolve_until_done tests that you don't have to re-evade the zombie

    self.assertTrue(movement.is_done())
    self.assertEqual(self.char.place.name, "Rivertown")

  def testMoveMultipleThroughTwoMonstersFailedEvade(self):
    self.char.speed_sneak_slider = 1
    self.char.possessions.append(items.AncientTome(0))
    cultist = next(monster for monster in self.state.monsters if monster.name == "Cultist")
    cultist.place = None  # Take one cultist as a trophy to test CityMovement's get_routes.
    maniac = next(monster for monster in self.state.monsters if monster.name == "Maniac")
    maniac.place = self.state.places["Easttown"]
    zombie = monsters.Zombie()
    zombie.idx = len(self.state.monsters)
    self.state.monsters.append(zombie)
    zombie.place = self.state.places["Easttown"]

    self.advance_turn(self.state.turn_number, "movement")
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)

    movement = self.resolve_to_choice(CityMovement)
    self.assertIn("Easttown", movement.choices)
    movement.resolve(self.state, "Easttown")
    self.assertEqual(self.char.movement_points, 2)

    movement = self.resolve_to_choice(CityMovement)
    self.assertIn("Rivertown", movement.choices)
    movement.resolve(self.state, "Rivertown")

    monster_choice = self.resolve_to_choice(MonsterChoice)
    self.assertCountEqual(monster_choice.monsters, [maniac, zombie])
    monster_choice.resolve(self.state, maniac.handle)

    choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(choice.choices, ["Fight", "Evade"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      choice.resolve(self.state, "Evade")
      next_choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertCountEqual(next_choice.choices, ["Fight", "Flee"])
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 5)
    next_choice.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      zombie_choice = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(zombie_choice.monster, zombie)
      self.assertEqual(zombie_choice.choices, ["Fight", "Evade"])
      zombie_choice.resolve(self.state, "Evade")
      self.resolve_until_done()

    self.assertTrue(movement.is_done())
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 5)

  # TODO: If you have a motorcycle, should not be able to exhaust for move movement.
  # TODO: Fight a dream flier, get sucked through a gate, cast find gate, and return.

  def testForceMovement(self):
    movement = ForceMovement(self.char, "Graveyard")
    self.assertFalse(movement.is_resolved())
    self.assertEqual(self.char.movement_points, 4)

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Graveyard")
    self.assertEqual(self.char.movement_points, 4)

  def testForceMovementFromChoice(self):
    choice = PlaceChoice(self.char, "choose a place", choice_filters={"locations"})
    movement = ForceMovement(self.char, choice)
    self.state.event_stack.append(Sequence([choice, movement], self.char))

    loc_choice = self.resolve_to_choice(PlaceChoice)
    loc_choice.resolve(self.state, "Woods")
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Woods")

  def testForceMovementNoChoices(self):
    self.assertEqual(self.char.place.name, "Diner")
    choice = PlaceChoice(self.char, "choose a place", choice_filters={"closed"})
    movement = ForceMovement(self.char, choice)
    self.state.event_stack.append(Sequence([choice, movement], self.char))

    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Diner")

  def testLoseExploredOnMovement(self):
    self.char.place = self.state.places["Graveyard"]
    self.char.explored = True
    movement = MoveOne(self.char, "Rivertown")

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "Rivertown")
    self.assertFalse(self.char.explored)

  def testLoseExploredOnForceMovement(self):
    self.char.place = self.state.places["Graveyard"]
    self.char.explored = True
    movement = ForceMovement(self.char, "WitchHouse")

    self.state.event_stack.append(movement)
    self.resolve_until_done()

    self.assertTrue(movement.is_resolved())
    self.assertEqual(self.char.place.name, "WitchHouse")
    self.assertFalse(self.char.explored)


class CityMovementTest(EventTest):

  def setUp(self):
    super().setUp()
    self.movement = CityMovement(self.char)
    self.state.event_stack.append(self.movement)
    self.resolve_to_choice(CityMovement)  # runs compute_choices

  def testAcceptableChoice(self):
    self.resolve_to_choice(CityMovement)
    self.movement.resolve(self.state, "Southside")
    self.resolve_to_choice(CityMovement)
    self.assertFalse(self.movement.is_resolved())
    self.assertEqual(self.char.movement_points, 0)

  def testChooseFarAway(self):
    with self.assertRaisesRegex(InvalidMove, "valid destination"):
      self.movement.resolve(self.state, "Woods")
    self.assertFalse(self.movement.is_resolved())

  def testCannotWalkPastMonster(self):
    self.state.monsters[0].place = self.state.places["Easttown"]
    self.resolve_to_choice(CityMovement)
    with self.assertRaisesRegex(InvalidMove, "valid destination"):
      self.movement.resolve(self.state, "Roadhouse")
    self.movement.resolve(self.state, "Easttown")
    self.resolve_to_choice(CityMovement)
    self.assertFalse(self.movement.is_resolved())

  def testNoMovementPoints(self):
    self.char.movement_points = 0
    self.resolve_to_choice(CityMovement)
    self.assertEqual(self.movement.choices, [])

  def testCannotMoveThroughClosedArea(self):
    self.state.event_stack.append(CloseLocation("Easttown"))
    self.resolve_to_choice(CityMovement)
    with self.assertRaisesRegex(InvalidMove, "valid destination"):
      self.movement.resolve(self.state, "Roadhouse")
    with self.assertRaisesRegex(InvalidMove, "valid destination"):
      self.movement.resolve(self.state, "Easttown")

  def testCannotMoveThroughDistantClosedArea(self):
    self.state.event_stack.append(CloseLocation("Rivertown"))
    self.resolve_to_choice(CityMovement)
    with self.assertRaisesRegex(InvalidMove, "valid destination"):
      self.movement.resolve(self.state, "Southside")


class EncounterPhaseTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.turn_phase = "encounter"
    self.encounter = EncounterPhase(self.char)
    self.state.event_stack.append(self.encounter)

  def testEncounterInLocation(self):
    self.char.place = self.state.places["Cave"]
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown7", {"Cave": encounters.Cave7}),
        encounters.EncounterCard("Rivertown6", {"Cave": encounters.Cave6}),
        encounters.EncounterCard("Rivertown5", {"Cave": encounters.Cave5}),
        encounters.EncounterCard("Rivertown4", {"Cave": encounters.Cave4}),
        encounters.EncounterCard("Rivertown3", {"Cave": encounters.Cave3}),
        encounters.EncounterCard("Rivertown2", {"Cave": encounters.Cave2}),
        encounters.EncounterCard("Rivertown1", {"Cave": encounters.Cave1}),
    ]
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Yes", "No"])
    orig_order = [f"Rivertown{x}" for x in range(7, 0, -1)]
    self.assertNotEqual(
        [card.name for card in self.state.places["Rivertown"].encounters], orig_order,
    )

  def testEncounterInLocationIsUnimplemented(self):
    self.char.place = self.state.places["Cave"]
    unimp_enc = mock.Mock(return_value=events.Unimplemented())
    encounter = gate_encounters.Other29
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown7", {"Cave": unimp_enc}),
        encounters.EncounterCard("Rivertown6", {"Cave": encounter}),
    ]
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertTrue(unimp_enc.called)
    self.assertEqual(len(self.state.places["Rivertown"].encounters), 2)

  def testEncounterInStreet(self):
    self.char.place = self.state.places["Rivertown"]
    self.resolve_until_done()
    self.assertIsInstance(self.encounter.action, events.Nothing)

  def testEncounterInOtherWorld(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.resolve_until_done()
    self.assertIsInstance(self.encounter.action, events.Nothing)

  def testEncounterWithGate(self):
    self.char.place = self.state.places["Cave"]
    self.state.places["Cave"].gate = self.state.gates.popleft()
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, self.state.places["Cave"].gate.name + "1")

  def testEncounterExploredGate(self):
    self.char.place = self.state.places["Cave"]
    self.char.explored = True
    self.state.places["Cave"].gate = self.state.gates.popleft()
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertIn("Don't close", choice.choices)

  def testCancelledEncounter(self):
    self.char.place = self.state.places["Cave"]
    self.char.possessions.append(Canceller(Encounter))
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown7", {"Cave": encounters.Cave7}),
    ]
    self.resolve_until_done()
    self.assertTrue(self.encounter.action.is_cancelled())

  def testCancelledDraw(self):
    self.char.place = self.state.places["Cave"]
    self.char.possessions.append(Canceller(DrawEncounter))
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown7", {"Cave": encounters.Cave7}),
    ]
    self.resolve_until_done()
    self.assertTrue(self.encounter.action.is_cancelled())

  def testCancelledEvent(self):
    self.char.place = self.state.places["Store"]
    self.char.possessions.append(Canceller(GainOrLoss))
    self.state.places["Rivertown"].encounters = [
        encounters.EncounterCard("Rivertown1", {"Store": encounters.Store1}),
    ]
    self.resolve_until_done()
    self.assertFalse(self.encounter.action.is_cancelled())
    self.assertTrue(self.encounter.action.encounter.is_cancelled())

  def testCancelledTravel(self):
    self.char.place = self.state.places["Cave"]
    self.state.places["Cave"].gate = self.state.gates.popleft()
    self.char.possessions.append(Canceller(Travel))
    self.resolve_until_done()
    self.assertTrue(self.encounter.action.is_cancelled())

  def testCancelledCloseAttempt(self):
    self.char.place = self.state.places["Cave"]
    self.state.places["Cave"].gate = self.state.gates.popleft()
    self.char.explored = True
    self.char.possessions.append(Canceller(GateCloseAttempt))
    self.resolve_until_done()
    self.assertTrue(self.encounter.action.is_cancelled())


class OtherWoldPhaseTest(EventTest):

  def setUp(self):
    super().setUp()
    self.other_world = OtherWorldPhase(self.char)
    self.state.event_stack.append(self.other_world)
    self.state.gate_cards.append(
        gate_encounters.GateCard("Gate29", {"red"}, {"Other": gate_encounters.Other29}),
    )

  def testNotInOtherWorld(self):
    self.resolve_until_done()
    self.assertIsInstance(self.other_world.action, events.Nothing)

  def testOtherWorldEncounter(self):
    self.assertEqual(self.char.stamina, 5)
    self.char.place = self.state.places["Abyss1"]
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)

  def testEncounterInWorldIsUnimplemented(self):
    unimp_enc = mock.Mock(return_value=events.Unimplemented())
    encounter = gate_encounters.Other29
    self.state.gate_cards.extendleft([
        gate_encounters.GateCard("FakeGate", {"red"}, {"Other": encounter}),
        gate_encounters.GateCard("UnimplementedGate", {"red"}, {"Other": unimp_enc}),
    ])
    self.char.place = self.state.places["Abyss1"]
    n_gate_cards = len(self.state.gate_cards)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertTrue(unimp_enc.called)
    self.assertEqual(len(self.state.gate_cards), n_gate_cards)

  def testCancelOtherWorldEncounter(self):
    self.char.possessions.append(Canceller(GateEncounter))
    self.char.place = self.state.places["Abyss1"]
    self.resolve_until_done()
    self.assertTrue(self.other_world.is_resolved())
    self.assertFalse(self.other_world.action.is_resolved())
    self.assertTrue(self.other_world.action.is_cancelled())

  def testCancelDrawEncounter(self):
    num_cards = len(self.state.gate_cards)
    self.char.possessions.append(Canceller(DrawGateCard))
    self.char.place = self.state.places["Abyss1"]
    self.resolve_until_done()
    self.assertTrue(self.other_world.is_resolved())
    self.assertFalse(self.other_world.action.is_resolved())
    self.assertTrue(self.other_world.action.is_cancelled())
    self.assertEqual(len(self.state.gate_cards), num_cards)

  def testCancelOtherWorldEvent(self):
    num_cards = len(self.state.gate_cards)
    self.char.possessions.append(Canceller(GainOrLoss))
    self.char.place = self.state.places["Abyss1"]
    self.resolve_until_done()
    self.assertTrue(self.other_world.is_resolved())
    self.assertTrue(self.other_world.action.is_resolved())
    self.assertFalse(self.other_world.action.encounter.is_resolved())
    self.assertTrue(self.other_world.action.encounter.is_cancelled())
    self.assertEqual(len(self.state.gate_cards), num_cards)


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
    sanity_die = DiceRoll(self.char, 1)
    stamina_die = DiceRoll(self.char, 1)
    loss = Loss(self.char, {"sanity": values.Die(sanity_die), "stamina": values.Die(stamina_die)})
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


class MaxSanityStaminaTest(EventTest):

  def testStaminaCannotExceedMaxStamina(self):
    self.char.possessions.append(assets.ArmWrestler())
    self.assertEqual(self.char.max_stamina(self.state), 6)

    self.char.stamina = 6
    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.char.possessions[0]]))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testLossPreventionDoesNotWorkOnMaxStamina(self):
    self.char.possessions.extend([assets.ArmWrestler(), abilities.StrongBody()])
    self.assertEqual(self.char.max_stamina(self.state), 6)

    self.char.stamina = 6
    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.char.possessions[0]]))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testDoNotLoseStaminaAtLessThanMax(self):
    self.char.possessions.append(assets.ArmWrestler())
    self.assertEqual(self.char.max_stamina(self.state), 6)

    self.char.stamina = 5
    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.char.possessions[0]]))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)

  def testDevouredIfReducedToZeroMax(self):
    terrible_curse = assets.Card("Frogurt", 0, "common", {}, {"max_stamina": -5})
    self.char.possessions.extend([assets.ArmWrestler(), terrible_curse])
    self.assertEqual(self.char.max_stamina(self.state), 1)

    self.char.stamina = 1
    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.char.possessions[0]]))
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 0)
    self.assertTrue(self.char.gone)


class CollectCluesTest(EventTest):

  def testCollectNoClues(self):
    collect = CollectClues(self.char, "Diner")
    self.state.event_stack.append(collect)
    self.resolve_until_done()
    self.assertEqual(collect.picked_up, 0)
    self.assertEqual(self.char.clues, 0)

  def testCollectTwoClues(self):
    collect = CollectClues(self.char, "Diner")
    self.state.event_stack.append(collect)
    self.state.places["Diner"].clues = 2
    self.resolve_until_done()
    self.assertEqual(collect.picked_up, 2)
    self.assertEqual(self.state.places["Diner"].clues, 0)
    self.assertEqual(self.char.clues, 2)

  def testCancelCollection(self):
    collect = CollectClues(self.char, "Diner")
    self.state.event_stack.append(collect)
    self.state.places["Diner"].clues = 2
    self.char.possessions.append(Canceller(GainOrLoss))
    self.resolve_until_done()
    self.assertFalse(collect.is_resolved())
    self.assertTrue(collect.is_cancelled())
    self.assertIsNone(collect.picked_up)
    self.assertEqual(self.state.places["Diner"].clues, 2)
    self.assertEqual(self.char.clues, 0)


class InsaneUnconsciousTest(EventTest):

  def testGoInsane(self):
    self.assertEqual(self.char.place.name, "Diner")
    self.char.possessions.extend([assets.Dog(), abilities.Marksman(0), items.Food(0)])
    self.char.sanity = 0
    self.char.clues = 3
    insane = Insane(self.char)

    self.state.event_stack.append(insane)
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()

    self.assertTrue(insane.is_resolved())
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 1)

  def testGoUnconscious(self):
    self.assertEqual(self.char.place.name, "Diner")
    self.char.possessions.extend([items.Food(0), items.TommyGun(0), items.Food(1)])
    self.char.stamina = 0
    self.char.clues = 1
    unconscious = Unconscious(self.char)

    self.state.event_stack.append(unconscious)
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()

    self.assertTrue(unconscious.is_resolved())
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.place.name, "Hospital")
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 1)

  def testInsaneInOtherWorld(self):
    self.char.place = self.state.places["Abyss1"]
    self.char.possessions.extend([assets.Dog(), abilities.Stealth(0), items.Food(0), items.Food(1)])
    self.char.sanity = 0
    self.char.clues = 2
    insane = Insane(self.char)

    self.state.event_stack.append(insane)
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()

    self.assertTrue(insane.is_resolved())
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Lost")
    self.assertEqual(self.char.clues, 1)
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5))
  def testInsaneClearsEvents(self):
    self.char.dollars = 0
    self.char.clues = 0
    self.char.sanity = 1
    seq = Sequence([
        Sequence([Loss(self.char, {"sanity": 1}), Gain(self.char, {"dollars": 1})], self.char),
        Gain(self.char, {"clues": 1})
    ], self.char)

    self.state.event_stack.append(seq)
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Asylum")
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.clues, 0)
    self.assertFalse(seq.events[1].is_resolved())

  def testDevouredCharacter(self):
    self.char.sanity = 2
    self.char.stamina = 2
    self.char.possessions.extend([
        assets.Dog(), abilities.Marksman(0), items.Cross(0), items.MagicLamp(0), items.Wither(0),
        assets.Deputy(), items.DeputysRevolver(), items.PatrolWagon(),
    ])
    self.state.event_stack.append(Loss(self.char, {"sanity": 2, "stamina": 3}))
    self.resolve_until_done()
    self.assertTrue(self.char.gone)
    self.assertIsNone(self.char.place)
    self.assertTrue(math.isinf(self.char.lose_turn_until))
    for deck in ["common", "unique", "spells", "skills", "allies"]:
      self.assertEqual(len(getattr(self.state, deck)), 1)
    self.assertCountEqual(
        [item.name for item in self.state.tradables], ["Deputy's Revolver", "Patrol Wagon"],
    )
    self.assertEqual([item.name for item in self.state.specials], ["Deputy"])


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
    split_gain = SplitGain(self.char, "stamina", "sanity", values.Die(die_roll))

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
    split_gain = SplitGain(
        self.char, "stamina", "sanity", values.Calculation(first_choice, "choice"))

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

  def testCancelledChoice(self):
    self.char.stamina = 1
    self.char.sanity = 1
    split_gain = SplitGain(self.char, "stamina", "sanity", 3)
    self.state.event_stack.append(split_gain)
    self.char.possessions.append(Canceller(MultipleChoice))
    self.resolve_until_done()
    self.assertFalse(split_gain.is_resolved())
    self.assertTrue(split_gain.is_cancelled())
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 1)

  def testCancelledGain(self):
    self.char.stamina = 1
    self.char.sanity = 1
    split_gain = SplitGain(self.char, "stamina", "sanity", 3)
    self.state.event_stack.append(split_gain)
    self.char.possessions.append(Canceller(GainOrLoss))
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, 2)
    self.resolve_until_done()
    self.assertTrue(split_gain.is_resolved())
    self.assertFalse(split_gain.is_cancelled())
    self.assertFalse(split_gain.gain.is_resolved())
    self.assertTrue(split_gain.gain.is_cancelled())
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.sanity, 1)


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
    self.assertEqual(self.char.place.name, "Diner")
    self.assertIsNone(self.char.lose_turn_until)
    arrest = Arrested(self.char)
    self.char.dollars = 5

    self.state.event_stack.append(arrest)
    self.resolve_until_done()

    self.assertEqual(self.char.arrested_until, self.state.turn_number + 2)
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.place.name, "Police")

    turn_phase = Movement(self.char)
    self.state.event_stack.append(turn_phase)
    self.resolve_until_done()
    self.assertTrue(turn_phase.cancelled)


class DrawTest(EventTest):

  def testDrawFood(self):
    draw = DrawSpecific(self.char, "common", "Food")
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.common.append(items.Food(0))

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
    self.state.common.append(items.Food(0))
    self.state.common.append(items.Food(1))

    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")
    self.assertEqual(len(self.state.common), 1)

  def testDrawNamedShufflesDeck(self):
    self.state.common.extend([
        items.Food(0), items.Food(1), items.TommyGun(0), items.TommyGun(1), items.Bullwhip(0),
        items.Cross(0), items.Cross(1), items.DarkCloak(0), items.DarkCloak(1), items.Dynamite(0),
    ])
    names = [item.name for item in self.state.common if item.name != "Bullwhip"]
    self.state.event_stack.append(DrawSpecific(self.char, "common", "Bullwhip"))
    self.resolve_until_done()
    new_names = [item.name for item in self.state.common]
    self.assertCountEqual(new_names, names)
    self.assertNotEqual(new_names, names)  # TODO: 1 in 9!/8 chance of failing


class DrawRandomTest(EventTest):

  def testDrawOneCard(self):
    draw = Draw(self.char, "common", 1)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
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
    dynamite = items.Dynamite(0)
    self.state.common.extend([
        items.Food(0), dynamite, items.Revolver38(0), items.TommyGun(0), items.Bullwhip(0)])

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
    food = items.Food(0)
    self.state.common.append(food)

    # Should be handled gracefully if you are instructed to draw more cards than are in the deck.
    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertEqual(self.char.possessions, [food])
    self.assertFalse(self.state.common)

  def testDrawSpecificTypeTop(self):
    draw = Draw(self.char, "common", 1, target_type=items.Weapon)
    tommygun = items.TommyGun(0)
    self.state.common.extend([tommygun, items.Food(0)])
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertEqual(self.char.possessions, [tommygun])
    self.assertEqual([item.name for item in self.state.common], ["Food"])

  def testDrawSpecificTypeMiddle(self):
    draw = Draw(self.char, "common", 1, target_type=items.Weapon)
    tommygun = items.TommyGun(0)
    self.state.common.extend([items.Food(0), tommygun, items.Dynamite(0)])
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertEqual(self.char.possessions, [tommygun])
    self.assertEqual([item.name for item in self.state.common], ["Dynamite", "Food"])

  def testDrawSpecificTypeNone(self):
    draw = Draw(self.char, "common", 1, target_type=items.ResearchMaterials)
    tommygun = items.TommyGun(0)
    self.state.common.extend([items.Food(0), tommygun, items.Dynamite(0)])
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.assertEqual(self.char.possessions, [])
    self.assertEqual([item.name for item in self.state.common], ["Food", "Tommy Gun", "Dynamite", ])

  def testDrawCancelled(self):
    draw = Draw(self.char, "common", 2)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.char.possessions.append(Canceller(DrawItems))
    self.state.common.extend([items.Food(0), items.Dynamite(0), items.Revolver38(0)])
    self.assertEqual(len(self.state.common), 3)

    self.state.event_stack.append(draw)
    self.resolve_until_done()
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertFalse(draw.events[0].is_resolved())
    self.assertTrue(draw.events[0].is_cancelled())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertIsInstance(self.char.possessions[0], Canceller)
    self.assertEqual(len(self.state.common), 3)

  def testChoiceCancelled(self):
    draw = Draw(self.char, "common", 2)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.char.possessions.append(Canceller(CardChoice))
    self.state.common.extend([items.Food(0), items.Dynamite(0), items.Revolver38(0)])
    self.assertEqual(len(self.state.common), 3)

    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertTrue(draw.events[0].is_resolved())
    self.assertFalse(draw.events[1].choice.is_resolved())
    self.assertTrue(draw.events[1].choice.is_cancelled())
    self.assertTrue(draw.events[1].is_cancelled())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertIsInstance(self.char.possessions[0], Canceller)
    self.assertEqual(len(self.state.common), 3)

  def testKeepCancelled(self):
    draw = Draw(self.char, "common", 2)
    self.assertFalse(draw.is_resolved())
    self.assertFalse(self.char.possessions)
    self.char.possessions.append(Canceller(KeepDrawn))
    self.state.common.extend([items.Food(0), items.Dynamite(0), items.Revolver38(0)])
    self.assertEqual(len(self.state.common), 3)

    self.state.event_stack.append(draw)
    self.resolve_until_done()

    self.assertTrue(draw.is_resolved())
    self.assertTrue(draw.events[0].is_resolved())
    self.assertFalse(draw.events[1].is_resolved())
    self.assertTrue(draw.events[1].is_cancelled())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertIsInstance(self.char.possessions[0], Canceller)
    self.assertEqual(len(self.state.common), 3)


class DiscardSpecificTest(EventTest):

  def testDiscardSpecific(self):
    self.char.possessions.extend([items.Food(0), items.TommyGun(0)])
    discard = DiscardSpecific(self.char, [self.char.possessions[0]])
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tommy Gun")
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].name, "Food")
    self.assertEqual(discard.discarded, [self.state.common[0]])

  def testDiscardSpecificDuplicateName(self):
    self.char.possessions.extend([items.Food(0), items.Food(1)])
    discard = DiscardSpecific(self.char, [self.char.possessions[1]])
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].handle, "Food0")
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].handle, "Food1")
    self.assertEqual(discard.discarded, [self.state.common[0]])

  def testDiscardNotPresent(self):
    self.char.possessions.extend([items.Food(0), items.Food(1)])
    self.state.common.append(items.Food(2))
    discard = DiscardSpecific(self.char, [self.state.common[0]])
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].handle, "Food2")
    self.assertEqual(discard.discarded, [])

  def testDiscardToBox(self):
    self.char.possessions.extend([items.Food(0), items.TommyGun(0)])
    discard = DiscardSpecific(self.char, [self.char.possessions[0]], to_box=True)
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual([card.name for card in discard.discarded], ["Food"])

  def testDiscardFromChoice(self):
    self.char.possessions.extend([items.Food(0), items.Food(1)])
    choice = ItemChoice(self.char, "")
    discard = DiscardSpecific(self.char, choice)
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(Sequence([choice, discard], self.char))
    choice = self.resolve_to_choice(ItemChoice)
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].handle, "Food0")
    self.assertEqual(discard.discarded, [self.state.common[0]])

  def testDiscardFromCancelledChoice(self):
    self.char.possessions.extend([items.Food(0), items.Food(1), Canceller(ItemChoice)])
    choice = ItemChoice(self.char, "")
    discard = DiscardSpecific(self.char, choice)
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(Sequence([choice, discard], self.char))
    self.resolve_until_done()
    self.assertFalse(discard.is_resolved())
    self.assertTrue(discard.is_cancelled())
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(len(self.state.common), 0)

  def testDiscardClearsTokens(self):
    silver_key = items.SilverKey(0)
    self.state.unique = [silver_key]
    self.state.event_stack.append(events.DrawSpecific(self.char, "unique", "Silver Key"))
    self.resolve_until_done()
    silver_key.tokens["stamina"] = 2
    self.state.event_stack.append(events.AddToken(silver_key, "stamina", character=self.char))
    self.resolve_until_done()
    self.assertNotIn(silver_key, self.char.possessions)
    self.state.event_stack.append(events.DrawSpecific(self.char, "unique", "Silver Key"))
    self.resolve_until_done()
    self.assertEqual(silver_key.tokens["stamina"], 0)


class DiscardNamedTest(EventTest):
  def testDiscardNamed(self):
    self.char.possessions.append(items.Food(0))
    self.char.possessions.append(items.TommyGun(0))
    discard = DiscardNamed(self.char, "Food")
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertTrue(discard.is_resolved())
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Tommy Gun")
    self.assertEqual(len(self.state.common), 1)

  def testDontHave(self):
    self.char.possessions.append(items.TommyGun(0))
    discard = DiscardNamed(self.char, "Food")
    self.assertFalse(discard.is_resolved())
    self.state.event_stack.append(discard)
    self.resolve_until_done()
    self.assertEqual(discard.log(self.state), "Dummy did not have a Food to discard")

  def testDiscardClearsTokens(self):
    silver_key = items.SilverKey(0)
    self.state.unique = [silver_key]
    self.state.event_stack.append(events.DrawSpecific(self.char, "unique", "Silver Key"))
    self.resolve_until_done()
    silver_key.tokens["stamina"] = 2
    self.state.event_stack.append(events.DiscardNamed(self.char, "Silver Key"))
    self.resolve_until_done()
    self.state.event_stack.append(events.DrawSpecific(self.char, "unique", "Silver Key"))
    self.resolve_until_done()
    self.assertEqual(silver_key.tokens["stamina"], 0)


class TakeTrophyTest(EventTest):

  def testTakeTrophy(self):
    take = TakeTrophy(self.char, self.state.monsters[0])
    self.state.event_stack.append(take)
    self.resolve_until_done()
    self.assertTrue(take.is_resolved())
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0], self.state.monsters[0])
    self.assertIsNone(self.state.monsters[0].place)
    self.assertEqual(self.state.monsters[1].place, self.state.monster_cup)

  def testTakeTrophyFromBoard(self):
    self.state.monsters[0].place = self.state.places["Graveyard"]
    self.state.monsters[1].place = self.state.places["Cave"]
    choose = MonsterOnBoardChoice(self.char, "choose")
    take = TakeTrophy(self.char, choose)
    self.state.event_stack.append(Sequence([choose, take], self.char))
    choice = self.resolve_to_choice(MonsterOnBoardChoice)
    self.assertCountEqual(choice.choices, ["Cultist0", "Maniac1"])
    choice.resolve(self.state, "Maniac1")
    self.resolve_until_done()
    self.assertTrue(take.is_resolved())
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0], self.state.monsters[1])
    self.assertIsNone(self.state.monsters[1].place)
    self.assertEqual(self.state.monsters[0].place, self.state.places["Graveyard"])

  def testTakeTrophyFromCup(self):
    draw = DrawMonstersFromCup(1, self.char)
    take = TakeTrophy(self.char, draw)
    self.state.event_stack.append(Sequence([draw, take], self.char))
    with mock.patch.object(events.random, "sample", new=mock.MagicMock(return_value=[1])):
      self.resolve_until_done()
    self.assertTrue(take.is_resolved())
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0], self.state.monsters[1])
    self.assertIsNone(self.state.monsters[1].place)
    self.assertEqual(self.state.monsters[0].place, self.state.monster_cup)


class ReturnMonstersAndGatesTest(EventTest):

  def testReturnMonster(self):
    cultist = monsters.Cultist()
    cultist.idx = 2
    zombie = monsters.Zombie()
    zombie.idx = 3
    cultist2 = monsters.Cultist()
    cultist2.idx = 4
    gate = self.state.gates.popleft()
    self.char.trophies.extend([cultist, gate, zombie, cultist2])
    self.state.event_stack.append(ReturnMonsterToCup(self.char, "Cultist4"))
    self.resolve_until_done()
    self.assertEqual(len(self.char.trophies), 3)
    trophy_handles = [trophy.handle for trophy in self.char.trophies]
    self.assertEqual(trophy_handles, ["Cultist2", "Gate Abyss0", "Zombie3"])
    self.assertEqual(cultist2.place.name, "cup")
    self.assertIsNone(cultist.place)

  def testReturnGate(self):
    self.char.trophies.append(self.state.gates.popleft())
    cultist = monsters.Cultist()
    cultist.idx = 2
    self.char.trophies.append(cultist)
    self.char.trophies.append(self.state.gates.popleft())

    old_length = len(self.state.gates)
    self.state.event_stack.append(ReturnGateToStack(self.char, "Gate Abyss1"))
    self.resolve_until_done()
    self.assertEqual(len(self.char.trophies), 2)
    trophy_handles = [trophy.handle for trophy in self.char.trophies]
    self.assertEqual(trophy_handles, ["Gate Abyss0", "Cultist2"])
    self.assertEqual(len(self.state.gates), old_length+1)


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
    self.char.possessions.append(abilities.Will(0))
    self.assertEqual(self.char.will(self.state), 2)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    self.resolve_until_done()

    self.assertTrue(check.is_resolved())
    self.assertIsNotNone(check.dice)
    self.assertListEqual(check.roll, [2, 4])

  def testCancelledRoll(self):
    check = Check(self.char, "fight", 0)
    self.char.possessions.append(Canceller(DiceRoll))

    self.state.event_stack.append(check)
    self.resolve_until_done()

    self.assertFalse(check.is_resolved())
    self.assertTrue(check.is_cancelled())
    self.assertIsNotNone(check.dice)
    self.assertIsNone(check.roll)


class RerollSpecificTest(EventTest):

  def testRerollOneDie(self):
    self.char.clues = 1
    check = Check(self.char, "speed", 0)
    self.assertEqual(self.char.speed(self.state), 4)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [3, 3, 3, 3])
    self.assertEqual(check.successes, 0)

    self.state.event_stack.append(RerollSpecific(self.char, check, [2]))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [3, 3, 5, 3])
    self.assertEqual(check.successes, 1)

  def testRerollUnsuccessfulDice(self):
    self.char.clues = 1
    check = Check(self.char, "speed", 0)
    self.assertEqual(self.char.speed(self.state), 4)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1, 6, 3])):
      self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [5, 1, 6, 3])
    self.assertEqual(check.successes, 2)

    bad_dice = values.UnsuccessfulDice(check)
    self.state.event_stack.append(RerollSpecific(self.char, check, bad_dice))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4, 5])):
      self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [5, 4, 6, 5])
    self.assertEqual(check.successes, 3)

  def testRerollChosenDie(self):
    self.char.clues = 1
    check = Check(self.char, "speed", 0)
    self.assertEqual(self.char.speed(self.state), 4)
    self.assertFalse(check.is_resolved())

    self.state.event_stack.append(check)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1, 6, 3])):
      self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [5, 1, 6, 3])
    self.assertEqual(check.successes, 2)

    choice = MultipleChoice(self.char, "", [5, 1, 6, 3])
    choice.resolve(self.state, 5)
    chosen = values.Calculation(choice, "choice_index")
    self.state.event_stack.append(RerollSpecific(self.char, check, chosen))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[4])):
      self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [4, 1, 6, 3])
    self.assertEqual(check.successes, 1)


class ConditionalTest(EventTest):

  def createConditional(self):
    check = Check(self.char, "luck", 0)
    success_result = Gain(self.char, {"clues": 1})
    fail_result = Loss(self.char, {"sanity": 1})
    cond = Conditional(self.char, check, "successes", {1: success_result, 0: fail_result})
    return Sequence([check, cond])

  def createValueConditional(self):
    val = values.Calculation(self.char, "dollars")
    success = Gain(self.char, {"clues": 1})
    fail = Loss(self.char, {"sanity": 1})
    mega = Gain(self.char, {"clues": 2})
    return Conditional(self.char, val, "anything", {1: success, 0: fail, 2: mega})

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

  def testCancelledCondition(self):
    seq = self.createConditional()
    check, cond = seq.events
    self.char.possessions.append(Canceller(Check))
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(seq)
    self.resolve_until_done()

    self.assertTrue(seq.is_resolved())
    self.assertFalse(check.is_resolved())
    self.assertTrue(check.is_cancelled())
    self.assertFalse(cond.is_resolved())
    self.assertTrue(cond.is_cancelled())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)
    self.assertFalse(cond.result_map[0].is_done())
    self.assertFalse(cond.result_map[1].is_done())

  @mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3))
  def testCancelledResult(self):
    seq = self.createConditional()
    cond = seq.events[1]
    self.char.possessions.append(Canceller(GainOrLoss))
    self.assertFalse(seq.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(seq)
    self.resolve_until_done()

    self.assertTrue(seq.is_resolved())
    self.assertTrue(cond.is_resolved())
    self.assertFalse(cond.result_map[0].is_resolved())
    self.assertTrue(cond.result_map[0].is_cancelled())
    self.assertFalse(cond.result_map[1].is_done())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

  def testPassValue(self):
    cond = self.createValueConditional()
    self.assertFalse(cond.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(cond)
    self.char.dollars = 1
    self.resolve_until_done()

    self.assertTrue(cond.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.clues, 1)
    self.assertFalse(cond.result_map[0].is_resolved())
    self.assertTrue(cond.result_map[1].is_resolved())
    self.assertFalse(cond.result_map[2].is_resolved())

  def testFailValue(self):
    cond = self.createValueConditional()
    self.assertFalse(cond.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(cond)
    self.char.dollars = 0
    self.resolve_until_done()

    self.assertTrue(cond.is_resolved())
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.clues, 0)
    self.assertTrue(cond.result_map[0].is_resolved())
    self.assertFalse(cond.result_map[1].is_resolved())
    self.assertFalse(cond.result_map[2].is_resolved())

  def testSuperPassValue(self):
    cond = self.createValueConditional()
    self.assertFalse(cond.is_resolved())
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.sanity, 5)

    self.state.event_stack.append(cond)
    self.char.dollars = 3
    self.resolve_until_done()

    self.assertTrue(cond.is_resolved())
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.clues, 2)
    self.assertFalse(cond.result_map[0].is_resolved())
    self.assertFalse(cond.result_map[1].is_resolved())
    self.assertTrue(cond.result_map[2].is_resolved())

  def testPassFailDifficulty(self):
    pass_event = events.Nothing()
    fail_event = events.Nothing()
    check = events.Check(self.char, "luck", -1)
    pf_event = events.PassFail(self.char, check, pass_event, fail_event, min_successes=2)

    self.state.event_stack.append(pf_event)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 3, 3, 3])):
      self.resolve_until_done()
    self.assertFalse(pass_event.is_resolved())
    self.assertTrue(fail_event.is_resolved())


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


class PrereqChoiceTest(EventTest):

  def testMismatchedLengths(self):
    prereq = values.AttributePrerequisite(self.char, "dollars", 2, "at least")
    with self.assertRaises(AssertionError):
      MultipleChoice(self.char, "choose", ["Yes", "No"], [prereq])

  def testInvalidChoices(self):
    clues = values.AttributePrerequisite(self.char, "clues", 1, "at least")
    sanity = values.AttributePrerequisite(self.char, "sanity", 1, "at least")
    stamina = values.AttributePrerequisite(self.char, "stamina", 2, "at most")
    choices = ["Spend 1 clue", "Spend 1 sanity", "Gain stamina", "Do Nothing"]
    choice = MultipleChoice(self.char, "choose", choices, [clues, sanity, stamina, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(MultipleChoice)

    self.assertEqual(choice.choices, choices)
    self.assertCountEqual(choice.invalid_choices.keys(), [0, 2])

    with self.assertRaisesRegex(InvalidMove, "at least 1 clues"):
      choice.resolve(self.state, "Spend 1 clue")

    choice.resolve(self.state, "Spend 1 sanity")
    self.assertEqual(choice.choice_index, 1)


class MonsterChoiceTest(EventTest):

  def testChoice(self):
    all_monsters = self.state.monsters[:2]
    choice = MonsterChoice(self.char, "", all_monsters, [None, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(MonsterChoice)
    output = self.state.for_player(0)
    self.assertFalse(output["choice"]["invalid_choices"])
    self.assertEqual(output["choice"]["annotations"], [None, None])

    with self.assertRaisesRegex(InvalidMove, "Unknown monster"):
      choice.resolve(self.state, "somebody")
    self.assertFalse(choice.is_resolved())
    choice.resolve(self.state, self.state.monsters[0].handle)
    self.assertTrue(choice.is_resolved())
    self.resolve_until_done()

  def testAutoChoose(self):
    all_monsters = self.state.monsters[:2]
    choice = MonsterChoice(self.char, "", all_monsters, [None, "Evaded"])
    self.state.event_stack.append(choice)
    self.resolve_until_done()

  def testInvalidChoice(self):
    self.state.monsters.extend([monsters.Zombie(), monsters.Witch()])
    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
    choice = MonsterChoice(self.char, "", self.state.monsters, [None, None, "Evaded", None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(MonsterChoice)
    output = self.state.for_player(0)
    self.assertEqual(output["choice"]["invalid_choices"], [2])
    self.assertEqual(output["choice"]["annotations"], [None, None, "Evaded", None])

    with self.assertRaisesRegex(InvalidMove, "already"):
      choice.resolve(self.state, "Zombie2")
    self.assertFalse(choice.is_resolved())
    choice.resolve(self.state, self.state.monsters[0].handle)
    self.assertTrue(choice.is_resolved())
    self.resolve_until_done()

  def testMonsterChoiceIsPlayerSpecific(self):
    witch = monsters.Witch()
    choice = MonsterChoice(self.char, "", [witch, self.state.monsters[0]], [None, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(MonsterChoice)
    output = self.state.for_player(0)
    self.assertIn("magical resistance", output["choice"]["monsters"][0]["attributes"])
    self.char.possessions.append(assets.OldProfessor())
    output = self.state.for_player(0)
    self.assertNotIn("magical resistance", output["choice"]["monsters"][0]["attributes"])

  def testMonsterChoiceWithAutoEvade(self):
    all_monsters = self.state.monsters[:2]
    choice = MonsterChoice(self.char, "", all_monsters, [None, None], "Ignore All")
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(MonsterChoice)
    output = self.state.for_player(0)
    self.assertEqual(output["choice"]["invalid_choices"], [])
    self.assertEqual(output["choice"]["annotations"], [None, None])
    self.assertEqual(output["choice"]["monsters"][2], "Ignore All")

    choice.resolve(self.state, "Ignore All")
    self.resolve_until_done()


class SpendChoiceTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.dollars = 5

  def testBasicSpending(self):
    spend = values.ExactSpendPrerequisite({"dollars": 1})
    choice = SpendChoice(self.char, "choose", ["Food", "Nothing"], spends=[spend, None])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.remaining_spend, [{"dollars": 1}, False])
    with self.assertRaisesRegex(InvalidMove, "additional 1 dollars"):
      choice.resolve(self.state, "Food")
    self.assertFalse(choice.is_done())
    self.spend("dollars", 1, choice)
    choice.resolve(self.state, "Food")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 4)

  def testIncorrectSpendAmount(self):
    spend = values.ExactSpendPrerequisite({"dollars": 1})
    choice = SpendChoice(self.char, "choose", ["Food", "Nothing"], spends=[spend, None])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.remaining_spend, [{"dollars": 1}, False])
    with self.assertRaisesRegex(InvalidMove, "additional 1 dollars"):
      choice.resolve(self.state, "Food")

    self.spend("dollars", 2, choice)
    self.assertEqual(choice.remaining_spend, [{"dollars": -1}, {"dollars": -2}])
    with self.assertRaisesRegex(InvalidMove, "overspent 1 dollars"):
      choice.resolve(self.state, "Food")

    self.spend("dollars", -1, choice)
    self.assertEqual(choice.remaining_spend, [False, {"dollars": -1}])
    # Cannot choose something else if you've spent.
    with self.assertRaisesRegex(InvalidMove, "overspent 1 dollars"):
      choice.resolve(self.state, "Nothing")

    self.spend("dollars", -1, choice)
    self.assertEqual(choice.remaining_spend, [{"dollars": 1}, False])
    self.assertFalse(choice.is_done())
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)

  def testCannotOverOrUnderSpend(self):
    self.char.dollars = 1
    spend = values.ExactSpendPrerequisite({"dollars": 3})
    choice = SpendChoice(self.char, "choose", ["Lantern", "Nothing"], spends=[spend, None])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(SpendChoice)

    self.spend("dollars", 1, choice)
    with self.assertRaisesRegex(InvalidMove, "more dollars than you have"):
      self.spend("dollars", 1, choice)
    self.assertEqual(choice.spend_map["dollars"]["dollars"], 1)
    self.spend("dollars", -1, choice)
    with self.assertRaisesRegex(InvalidMove, "dollars that you have not spent"):
      self.spend("dollars", -1, choice)  # Cannot unspend something you did not spend.
    self.assertEqual(choice.spend_map["dollars"].get("dollars", 0), 0)

  def testRangeSpend(self):
    self.char.dollars = 6
    spend = values.RangeSpendPrerequisite("dollars", 2, 4)
    choice = SpendChoice(self.char, "choose", ["Yes", "No"], spends=[spend, None])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.remaining_spend, [{"dollars": 2}, False])
    with self.assertRaisesRegex(InvalidMove, "additional 2 dollars"):
      choice.resolve(self.state, "Yes")

    self.spend("dollars", 2, choice)
    self.assertEqual(choice.remaining_spend, [False, {"dollars": -2}])
    with self.assertRaisesRegex(InvalidMove, "overspent 2 dollars"):
      choice.resolve(self.state, "No")

    self.spend("dollars", 2, choice)
    self.assertEqual(choice.remaining_spend, [False, {"dollars": -4}])

    self.spend("dollars", 2, choice)
    self.assertEqual(choice.remaining_spend, [{"dollars": -2}, {"dollars": -6}])
    with self.assertRaisesRegex(InvalidMove, "overspent 2 dollars"):
      choice.resolve(self.state, "Yes")

    self.spend("dollars", -3, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 3)

  def testMultiSpend(self):
    spend = values.ExactSpendPrerequisite({"stamina": 1, "sanity": 1})
    choice = SpendChoice(self.char, "choose", ["Sign", "Nevermind"], spends=[spend, None])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.remaining_spend, [{"stamina": 1, "sanity": 1}, False])
    with self.assertRaisesRegex(InvalidMove, "1 (stamina|sanity), 1 (stamina|sanity)"):
      choice.resolve(self.state, "Sign")
    self.spend("stamina", 1, choice)
    self.assertEqual(choice.remaining_spend, [{"sanity": 1}, {"stamina": -1}])
    with self.assertRaisesRegex(InvalidMove, "additional 1 sanity"):
      choice.resolve(self.state, "Sign")
    self.spend("sanity", 1, choice)
    self.assertEqual(choice.remaining_spend, [False, {"sanity": -1, "stamina": -1}])
    choice.resolve(self.state, "Sign")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 4)

  def testMultilpeSpendInvalidatesSingle(self):
    stam = values.ExactSpendPrerequisite({"stamina": 1})
    san = values.ExactSpendPrerequisite({"sanity": 1})
    choice = SpendChoice(self.char, "choose", ["A", "B", "C"], spends=[stam, san, None])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(SpendChoice)

    choice.spend("stamina")
    choice.spend("sanity")
    self.resolve_to_choice(SpendChoice)
    self.assertEqual(
        choice.remaining_spend, [{"sanity": -1}, {"stamina": -1}, {"sanity": -1, "stamina": -1}],
    )
    choice.unspend("stamina")
    self.resolve_to_choice(SpendChoice)
    self.assertEqual(choice.remaining_spend, [{"sanity": -1, "stamina": 1}, False, {"sanity": -1}])

  def testSpendGateTrophies(self):
    spend_gate = values.ExactSpendPrerequisite({"gates": 1})
    choice = SpendChoice(self.char, "choose", ["A", "B"], spends=[spend_gate, None])
    orig_gates = len(self.state.gates)
    self.char.trophies.append(self.state.gates.popleft())
    self.char.trophies.append(self.state.gates.popleft())
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.remaining_spend, [{"gates": 1}, False])
    self.assertIn(0, self.state.spendables)
    self.assertCountEqual(self.state.spendables[0].keys(), ["Gate Abyss0", "Gate Abyss1"])
    self.toggle_spend(0, "Gate Abyss1", choice)
    self.assertEqual(choice.spent_handles(), {"Gate Abyss1"})
    self.assertEqual(choice.remaining_spend, [False, {"gates": -1}])

    self.assertIn(0, self.state.spendables)
    self.assertCountEqual(self.state.spendables[0].keys(), ["Gate Abyss0", "Gate Abyss1"])
    self.toggle_spend(0, "Gate Abyss0", choice)
    self.assertEqual(choice.spent_handles(), {"Gate Abyss1", "Gate Abyss0"})
    self.assertEqual(choice.remaining_spend, [{"gates": -1}, {"gates": -2}])

    self.assertIn(0, self.state.spendables)
    self.assertCountEqual(self.state.spendables[0].keys(), ["Gate Abyss0", "Gate Abyss1"])
    self.toggle_spend(0, "Gate Abyss1", choice)
    self.assertEqual(choice.spent_handles(), {"Gate Abyss0"})
    self.assertEqual(choice.remaining_spend, [False, {"gates": -1}])

    choice.resolve(self.state, "A")
    self.resolve_until_done()

    self.assertEqual([trophy.handle for trophy in self.char.trophies], ["Gate Abyss1"])
    self.assertEqual(len(self.state.gates), orig_gates-1)
    self.assertEqual(self.state.gates[-1].handle, "Gate Abyss0")

  def testSpendToughness(self):
    cultist = monsters.Cultist()
    vampire = monsters.Vampire()
    flier = monsters.DreamFlier()
    self.char.trophies.extend([cultist, vampire, flier])
    spend_toughness = values.ToughnessSpend(2)
    choice = SpendChoice(self.char, "choose", ["A", "B"], spends=[spend_toughness, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.remaining_spend, [{"toughness": 2}, False])
    self.assertIn(0, self.state.spendables)
    self.assertEqual(self.state.spendables[0].keys(), {"Cultist", "Vampire", "Dream Flier"})
    self.toggle_spend(0, "Cultist", choice)
    self.assertEqual(choice.spent_handles(), {"Cultist"})
    self.assertEqual(choice.remaining_spend, [{"toughness": 1}, {"toughness": -1}])

    self.toggle_spend(0, "Vampire", choice)
    self.assertEqual(choice.spent_handles(), {"Cultist", "Vampire"})
    self.assertEqual(choice.remaining_spend, [{"toughness": -1}, {"toughness": -3}])

    self.toggle_spend(0, "Cultist", choice)
    self.assertEqual(choice.spent_handles(), {"Vampire"})
    self.assertEqual(choice.remaining_spend, [False, {"toughness": -2}])

    choice.resolve(self.state, "A")
    self.resolve_until_done()

    self.assertEqual([trophy.handle for trophy in self.char.trophies], ["Cultist", "Dream Flier"])
    self.assertEqual(vampire.place, self.state.monster_cup)
    self.assertIsNone(cultist.place)
    self.assertIsNone(flier.place)

  def testSpendToughnessWithGlobals(self):
    maniac = monsters.Maniac()
    self.char.trophies.append(maniac)
    spend_toughness = values.ToughnessSpend(2)
    self.state.environment = mythos.Mythos45()  # Increases the maniac's toughness by 1.
    self.assertEqual(maniac.toughness(self.state, self.char), 2)
    choice = SpendChoice(self.char, "choose", ["A", "B"], spends=[spend_toughness, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.remaining_spend, [{"toughness": 2}, False])
    self.assertIn(0, self.state.spendables)
    self.assertEqual(self.state.spendables[0].keys(), {"Maniac"})
    self.toggle_spend(0, "Maniac", choice)
    self.assertEqual(choice.spent_handles(), {"Maniac"})
    self.assertEqual(choice.remaining_spend, [False, {"toughness": -2}])

  def testOtherCharactersCannotSpendTrophies(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.char.trophies.append(self.state.gates.popleft())
    buddy.trophies.append(self.state.gates.popleft())
    spend_gate = values.ExactSpendPrerequisite({"gates": 1})
    choice = SpendChoice(self.char, "choose", ["A", "B"], spends=[spend_gate, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SpendChoice)

    self.assertIn(0, self.state.spendables)
    self.assertNotIn(1, self.state.spendables)
    self.assertEqual(len(self.state.spendables[0]), 1)

    with self.assertRaisesRegex(InvalidMove, "at this time"):
      self.state.handle_use(1, self.char.trophies[0].handle)
    with self.assertRaisesRegex(InvalidMove, "at this time"):
      self.state.handle_use(1, buddy.trophies[0].handle)

  def testSpendItems(self):
    self.char.possessions.extend([items.ResearchMaterials(0), items.ResearchMaterials(1)])
    self.char.clues = 2
    check = Check(self.char, "lore", 0)
    self.state.event_stack.append(check)
    choice = self.resolve_to_choice(SpendChoice)

    self.assertEqual(choice.choices, ["Spend", "Done"])
    self.assertEqual(choice.remaining_spend, [{"clues": 1}, False])
    self.assertIn(0, self.state.spendables)
    self.assertEqual(self.state.spendables[0].keys(), {f"Research Materials{i}" for i in [0, 1]})

    self.toggle_spend(0, "Research Materials0", choice)
    self.assertEqual(choice.spent_handles(), {"Research Materials0"})
    self.assertEqual(choice.remaining_spend, [False, {"clues": -1}])

    self.assertEqual(self.state.spendables[0].keys(), {f"Research Materials{i}" for i in [0, 1]})
    self.toggle_spend(0, "Research Materials1", choice)
    self.assertEqual(choice.spent_handles(), {"Research Materials0", "Research Materials1"})
    self.assertEqual(choice.remaining_spend, [{"clues": -1}, {"clues": -2}])

    self.assertEqual(self.state.spendables[0].keys(), {f"Research Materials{i}" for i in [0, 1]})
    self.toggle_spend(0, "Research Materials0", choice)
    self.assertEqual(choice.spent_handles(), {"Research Materials1"})
    self.assertEqual(choice.remaining_spend, [False, {"clues": -1}])

    choice.resolve(self.state, "Spend")
    choice = self.resolve_to_choice(SpendChoice)
    self.assertEqual([pos.handle for pos in self.char.possessions], ["Research Materials0"])
    self.assertEqual([item.handle for item in self.state.common], ["Research Materials1"])
    self.assertEqual(self.char.clues, 2)

  def testOtherCharactersCannotSpendItems(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.char.possessions.append(items.ResearchMaterials(0))
    buddy.possessions.append(items.ResearchMaterials(1))
    spend_clue = values.ExactSpendPrerequisite({"clues": 1})
    choice = SpendChoice(self.char, "choose", ["A", "B"], spends=[spend_clue, None])
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SpendChoice)

    self.assertIn(0, self.state.spendables)
    self.assertNotIn(1, self.state.spendables)
    self.assertEqual(self.state.spendables[0].keys(), {"Research Materials0"})

    with self.assertRaisesRegex(InvalidMove, "at this time"):
      self.state.handle_use(1, "Research Materials0")
    with self.assertRaisesRegex(InvalidMove, "at this time"):
      self.state.handle_use(1, "Research Materials1")


class ItemChoiceTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.Revolver38(0))
    self.char.possessions.append(items.Food(0))
    self.char.possessions.append(items.HolyWater(0))

  def testChooseUnchoose(self):
    choice = ItemChoice(self.char, "choose")
    self.state.event_stack.append(choice)

    choice = self.resolve_to_choice(ItemChoice)
    choice.resolve(self.state, "Food0")
    self.assertFalse(choice.is_resolved())
    choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, "Food0")  # Deselect the food
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")

    self.assertTrue(choice.is_resolved())
    self.assertEqual([pos.handle for pos in choice.chosen], ["Holy Water0", ".38 Revolver0"])

  def testCountChoice(self):
    choice = ItemCountChoice(self.char, "choose 2", 2)
    self.state.event_stack.append(choice)

    self.resolve_to_choice(ItemCountChoice)

    choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, "Food0")
    self.assertFalse(choice.is_resolved())
    with self.assertRaisesRegex(InvalidMove, "Too many"):
      choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "Holy Water0")  # Deselect the holy water
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())
    self.assertCountEqual(choice.chosen, self.char.possessions[:2])
    self.assertEqual(choice.choice_count, 2)

    self.resolve_until_done()

  def testCountChoiceWithValues(self):
    choice = ItemCountChoice(self.char, "", values.ItemDeckCount(self.char, {"common"}))
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemCountChoice)

    # Simulate discarding an item after getting to this choice.
    self.char.possessions.remove(self.char.possessions[0])

    with self.assertRaisesRegex(InvalidMove, "Not enough"):
      choice.resolve(self.state, "done")
    self.assertFalse(choice.is_resolved())
    choice.resolve(self.state, "Food0")
    with self.assertRaisesRegex(InvalidMove, "Too many"):
      choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())
    self.assertListEqual(choice.chosen, self.char.possessions[:1])
    self.assertEqual(choice.choice_count, 1)

  def testNonItemsInPossessions(self):
    self.char.possessions.extend([assets.Dog(), abilities.Marksman(0)])
    choice = ItemChoice(self.char, "", None)
    self.state.event_stack.append(choice)

    # Test to make sure that you don't get attribute errors when not all your possessions are items.
    choice = self.resolve_to_choice(ItemChoice)
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Dog")
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Marksman0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()

  def testChoiceNotRestrictedToItems(self):
    self.char.possessions.extend([assets.Dog(), abilities.Marksman(0)])
    choice = ItemChoice(self.char, "", decks={"allies"})
    self.state.event_stack.append(choice)

    choice = self.resolve_to_choice(ItemChoice)
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Marksman0")
    choice.resolve(self.state, "Dog")
    choice.resolve(self.state, "done")
    self.resolve_until_done()

  def testCombatChoice(self):
    choice = CombatChoice(self.char, "choose combat items")
    self.state.event_stack.append(choice)
    self.resolve_to_choice(ItemChoice)

    choice.resolve(self.state, ".38 Revolver0")
    # Cannot use Food in combat.
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Food0")

    # Cannot use three hands in combat.
    with self.assertRaisesRegex(InvalidMove, "enough hands"):
      choice.resolve(self.state, "Holy Water0")

    # Deselecting the revolver frees up the hand.
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.choice_count, 1)


class LossChoiceTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.Revolver38(0))
    self.char.possessions.append(items.HolyWater(0))
    self.char.possessions.append(items.Derringer18(0))
    self.char.possessions.append(items.Derringer18(1))

  def testLossChoiceNormal(self):
    choice = ItemLossChoice(self.char, "choose", 2)
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())

  def testCanChooseLosableItems(self):
    choice = ItemLossChoice(self.char, "choose", 2)
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, ".18 Derringer0")
    choice.resolve(self.state, ".18 Derringer1")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())

  def testCanSkipLosableItems(self):
    choice = ItemLossChoice(self.char, "choose", 3)
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())

  def testRevolverIsNotLosable(self):
    self.char.possessions.append(items.DeputysRevolver())
    choice = ItemLossChoice(self.char, "choose", 3)
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "Holy Water0")
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())

  def testIrrelevantItemsDoNotCount(self):
    choice = ItemLossChoice(self.char, "choose", 2, decks={"common"})
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())

  def testChoosingLosableItemDoesNotDecreaseCount(self):
    choice = ItemLossChoice(self.char, "choose", 2, decks={"common"})
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, ".18 Derringer0")
    with self.assertRaisesRegex(InvalidMove, "Not enough"):
      choice.resolve(self.state, "done")
    self.assertFalse(choice.is_resolved())

    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())

  def testLoseAllItemsInDeck(self):
    choice = ItemLossChoice(self.char, "choose", float("inf"), decks={"common"})
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, ".38 Revolver0")
    choice.resolve(self.state, "done")
    self.assertTrue(choice.is_resolved())


class WeaponOrSpellLossChoiceTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.Derringer18(0))
    self.char.possessions.append(items.MagicLamp(0))
    self.char.possessions.append(items.DarkCloak(0))
    self.char.possessions.append(items.Wither(0))
    self.char.possessions.append(items.Voice(0))

  def testCanChooseSpell(self):
    self.state.event_stack.append(WeaponOrSpellLossChoice(self.char, "lose", 1))
    choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    with self.assertRaisesRegex(InvalidMove, "Not enough"):
      choice.resolve(self.state, "done")
    choice.resolve(self.state, "Wither0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.chosen, [self.char.possessions[3]])

  def testCanChooseWeapon(self):
    self.state.event_stack.append(WeaponOrSpellLossChoice(self.char, "lose", 1))
    choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Dark Cloak0")
    choice.resolve(self.state, "Magic Lamp0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.chosen, [self.char.possessions[1]])

  def testCanChooseUnlosableWeapon(self):
    self.state.event_stack.append(WeaponOrSpellLossChoice(self.char, "lose", 1))
    choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    choice.resolve(self.state, ".18 Derringer0")
    choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.chosen, [self.char.possessions[0]])

  def testCanIgnoreIfOnlyUnlosables(self):
    self.char.possessions.clear()
    self.char.possessions.append(items.Derringer18(0))
    self.state.event_stack.append(WeaponOrSpellLossChoice(self.char, "lose", 1))
    choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.chosen, [])

  def testSkipIfNoMatchingItems(self):
    self.char.possessions.clear()
    self.char.possessions.append(items.DarkCloak(0))
    choice = WeaponOrSpellLossChoice(self.char, "lose", 1)
    self.state.event_stack.append(choice)
    self.resolve_until_done()

    self.assertTrue(choice.is_done())
    self.assertTrue(choice.is_cancelled())
    self.assertFalse(choice.chosen)


class SinglePhysicalWeaponChoiceTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.Revolver38(0))
    self.char.possessions.append(items.TommyGun(0))

  def testChooseWithSpending(self):
    spend = values.ExactSpendPrerequisite({"sanity": 1})
    choice = SinglePhysicalWeaponChoice(self.char, "Choose", spend)
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SinglePhysicalWeaponChoice)

    # Cannot choose the revolver before spending.
    with self.assertRaisesRegex(InvalidMove, "additional 1 sanity"):
      choice.resolve(self.state, ".38 Revolver0")

    self.spend("sanity", 1, choice)
    choice.resolve(self.state, ".38 Revolver0")
    self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.assertFalse(choice.is_done())
    self.assertEqual(len(choice.chosen), 1)

    # Cannot choose a second item (count choice says max of 1).
    with self.assertRaisesRegex(InvalidMove, "Too many"):
      choice.resolve(self.state, "Tommy Gun0")

    # If you un-spend the sanity, you cannot confirm your choice.
    self.spend("sanity", -1, choice)
    with self.assertRaisesRegex(InvalidMove, "additional 1 sanity"):
      choice.resolve(self.state, "done")
    self.assertFalse(choice.is_done())
    self.assertEqual(len(choice.chosen), 1)

    # If you un-spend the sanity, you can de-select an item.
    choice.resolve(self.state, ".38 Revolver0")
    self.resolve_to_choice(SinglePhysicalWeaponChoice)

    # Since you've un-spent, you cannot choose the gun.
    with self.assertRaisesRegex(InvalidMove, "additional 1 sanity"):
      choice.resolve(self.state, "Tommy Gun0")

    # Re-spend the sanity.
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Tommy Gun0")
    self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.assertFalse(choice.is_done())
    self.assertEqual(len(choice.chosen), 1)

    # Confirm the final choic.
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertTrue(choice.is_done())
    self.assertEqual(len(choice.chosen), 1)
    self.assertEqual(self.char.sanity, 4)

  def testCancelAfterSpending(self):
    spend = values.ExactSpendPrerequisite({"sanity": 1})
    choice = SinglePhysicalWeaponChoice(self.char, "Choose", spend)
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(SinglePhysicalWeaponChoice)

    # Spend the sanity, but then change our mind and choose no items.
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertTrue(choice.is_cancelled())
    self.assertEqual(self.char.sanity, 5)


class PlaceChoiceTest(EventTest):

  def testChooseAnyLocation(self):
    choice = PlaceChoice(self.char, "choose place", choice_filters={"streets", "locations"})
    self.state.event_stack.append(choice)
    self.resolve_to_choice(PlaceChoice)

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "nowhere")

    choice.resolve(self.state, "Diner")

  def testChooseFromFixedLocations(self):
    choice = PlaceChoice(self.char, "choose place", choices=["Diner", "Southside", "Church"])
    self.state.event_stack.append(choice)
    self.resolve_to_choice(PlaceChoice)

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Bank")

    choice.resolve(self.state, "Diner")


class GateChoiceTest(EventTest):

  def testChooseOnlyGateLocations(self):
    choice = GateChoice(self.char, "choose place")
    self.state.event_stack.append(choice)
    self.state.places["Square"].gate = self.state.gates.popleft()
    self.state.places["Isle"].gate = self.state.gates.popleft()
    self.resolve_to_choice(GateChoice)

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Woods")

    choice.resolve(self.state, "Square")
    self.assertTrue(choice.is_resolved())

  def testAutoChooseIfOnlyOneGate(self):
    choice = GateChoice(self.char, "choose place")
    self.state.event_stack.append(choice)
    self.state.places["Cave"].gate = self.state.gates.popleft()
    self.resolve_until_done()
    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.choice, "Cave")

  def testChooseGateLocationsNoGates(self):
    choice = GateChoice(self.char, "choose place")
    self.state.event_stack.append(choice)
    self.resolve_until_done()

    self.assertTrue(choice.is_done())
    self.assertTrue(choice.is_cancelled())
    self.assertIsNone(choice.choice)

  def testChooseSpecificGateLocations(self):
    self.state.places["Square"].gate = self.state.gates.popleft()
    choice = GateChoice(self.char, "return", self.state.places["Square"].gate.name, None, "Return")

    self.state.places["Woods"].gate = self.state.gates.popleft()
    self.assertEqual(self.state.places["Square"].gate.name, self.state.places["Woods"].gate.name)
    self.state.places["WitchHouse"].gate = self.state.gates.popleft()
    self.assertNotEqual(
        self.state.places["WitchHouse"].gate.name, self.state.places["Woods"].gate.name)

    self.state.event_stack.append(choice)
    self.resolve_to_choice(GateChoice)

    self.assertEqual(choice.annotations(self.state), ["Return", "Return"])

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, None)

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "WitchHouse")

    choice.resolve(self.state, "Woods")
    self.assertTrue(choice.is_resolved())

  def testChooseNearestGate(self):
    self.char.place = self.state.places["Rivertown"]
    self.state.places["Square"].gate = self.state.gates.popleft()
    self.state.places["Science"].gate = self.state.gates.popleft()
    self.state.places["Society"].gate = self.state.gates.popleft()
    self.state.places["Woods"].gate = self.state.gates.popleft()

    choice = NearestGateChoice(self.char, "choose place", "choose")
    self.state.event_stack.append(choice)
    choice = self.resolve_to_choice(NearestGateChoice)
    self.assertCountEqual(choice.choices, ["Square", "Science", "Society"])

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Woods")
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, None)
    self.assertFalse(choice.is_done())
    choice.resolve(self.state, "Square")
    self.resolve_until_done()
    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.choice, "Square")

  def testChooseNearestNoGates(self):
    choice = NearestGateChoice(self.char, "choose place", "choose")
    self.state.event_stack.append(choice)
    self.resolve_until_done()
    self.assertTrue(choice.is_cancelled())
    self.assertIsNone(choice.choice)

  def testChooseNearestOnlyOneGate(self):
    self.char.place = self.state.places["Rivertown"]
    self.state.places["Square"].gate = self.state.gates.popleft()
    self.state.places["Science"].gate = self.state.gates.popleft()
    self.state.places["Society"].gate = self.state.gates.popleft()
    self.state.places["Cave"].gate = self.state.gates.popleft()

    choice = NearestGateChoice(self.char, "choose place", "choose")
    self.state.event_stack.append(choice)
    self.resolve_until_done()

    self.assertTrue(choice.is_resolved())
    self.assertEqual(choice.choice, "Cave")


class RefreshItemsTest(EventTest):

  def testRefreshItems(self):
    self.char.possessions.extend([
        items.Wither(0), items.Wither(1), items.Bullwhip(0), items.Cross(0),
    ])
    # pylint: disable=protected-access
    self.char.possessions[0]._exhausted = True
    self.char.possessions[2]._exhausted = True

    self.state.event_stack.append(RefreshAssets(self.char))
    self.resolve_until_done()
    self.assertFalse(self.char.possessions[0].exhausted)
    self.assertFalse(self.char.possessions[2].exhausted)

  def testRefreshNothing(self):
    self.char.possessions.clear()
    self.state.event_stack.append(RefreshAssets(self.char))
    self.resolve_until_done()

  def testOneItemRefreshCancelled(self):
    self.char.possessions.extend([
        items.Wither(0), items.Wither(1), items.Bullwhip(0), items.Cross(0),
    ])
    # pylint: disable=protected-access
    self.char.possessions[0]._exhausted = True
    self.char.possessions[1]._exhausted = True
    self.char.possessions[2]._exhausted = True

    refresh = RefreshAssets(self.char)
    self.state.event_stack.append(refresh)
    self.char.possessions.append(Canceller(RefreshAsset, 1))
    self.resolve_until_done()

    self.assertTrue(refresh.is_resolved())
    self.assertFalse(refresh.refreshes[1].is_resolved())
    self.assertTrue(refresh.refreshes[1].is_cancelled())
    self.assertFalse(self.char.possessions[0].exhausted)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].exhausted)


class ActivateItemsTest(EventTest):

  def testActivateItem(self):
    gun = items.TommyGun(0)
    self.char.possessions.append(gun)
    self.assertEqual(self.char.hands_available(), 2)
    self.assertEqual(self.char.combat(self.state, None), 4)

    activate = ActivateItem(self.char, gun)
    self.state.event_stack.append(activate)
    self.resolve_until_done()

    self.assertEqual(self.char.hands_available(), 0)
    self.assertEqual(self.char.combat(self.state, None), 10)

  def testDeactivateItem(self):
    gun = items.TommyGun(0)
    self.char.possessions.append(gun)
    gun._active = True  # pylint: disable=protected-access
    self.assertEqual(self.char.hands_available(), 0)
    self.assertEqual(self.char.combat(self.state, None), 10)

    deactivate = DeactivateItem(self.char, gun)
    self.state.event_stack.append(deactivate)
    self.resolve_until_done()

    self.assertEqual(self.char.hands_available(), 2)
    self.assertEqual(self.char.combat(self.state, None), 4)

  def testActivateChosenItems(self):
    self.char.possessions.extend([items.Bullwhip(0), items.TommyGun(0), items.Revolver38(0)])
    self.assertEqual(self.char.hands_available(), 2)
    self.assertEqual(self.char.combat(self.state, None), 4)

    item_choice = CombatChoice(self.char, "choose stuff")

    self.state.event_stack.append(item_choice)
    self.resolve_to_choice(CombatChoice)
    self.choose_items(item_choice, ["Bullwhip0", ".38 Revolver0"])
    self.resolve_until_done()

    self.assertEqual(self.char.hands_available(), 0)
    self.assertTrue(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[2].active)

  def testOneItemActivationCancelled(self):
    self.char.possessions.extend([items.Bullwhip(0), items.TommyGun(0), items.Revolver38(0)])
    item_choice = CombatChoice(self.char, "choose stuff")
    self.char.possessions.append(Canceller(ActivateItem))

    self.state.event_stack.append(item_choice)
    self.resolve_to_choice(CombatChoice)
    self.choose_items(item_choice, ["Bullwhip0", ".38 Revolver0"])
    self.resolve_until_done()

    self.assertTrue(item_choice.activate.is_resolved())
    self.assertFalse(item_choice.activate.activations[0].is_resolved())
    self.assertTrue(item_choice.activate.activations[0].is_cancelled())

    self.assertEqual(self.char.hands_available(), 1)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[2].active)

  def testActivationChoiceCancelled(self):
    self.char.possessions.extend([items.Bullwhip(0), items.TommyGun(0), items.Revolver38(0)])
    item_choice = CombatChoice(self.char, "choose stuff")
    self.char.possessions.append(Canceller(CombatChoice))

    self.state.event_stack.append(item_choice)
    self.resolve_until_done()

    self.assertIsNone(item_choice.activate)

    self.assertEqual(self.char.hands_available(), 2)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)

  def testDeactivateItems(self):
    self.char.possessions.extend([items.Bullwhip(0), items.TommyGun(0), items.Revolver38(0)])
    # pylint: disable=protected-access
    self.char.possessions[0]._active = True
    self.char.possessions[2]._active = True
    self.assertEqual(self.char.hands_available(), 0)

    deactivate = DeactivateItems(self.char)
    self.state.event_stack.append(deactivate)
    self.resolve_until_done()

    self.assertEqual(self.char.hands_available(), 2)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)

  def testOneDeactivationCancelled(self):
    self.char.possessions.extend([items.Bullwhip(0), items.TommyGun(0), items.Revolver38(0)])
    # pylint: disable=protected-access
    self.char.possessions[0]._active = True
    self.char.possessions[2]._active = True
    self.assertEqual(self.char.hands_available(), 0)
    self.char.possessions.append(Canceller(DeactivateItem))

    deactivate = DeactivateItems(self.char)
    self.state.event_stack.append(deactivate)
    self.resolve_until_done()

    self.assertTrue(deactivate.is_resolved())
    self.assertFalse(deactivate.deactivations[0].is_resolved())
    self.assertTrue(deactivate.deactivations[0].is_cancelled())
    self.assertTrue(deactivate.deactivations[1].is_resolved())
    self.assertEqual(self.char.hands_available(), 1)
    self.assertTrue(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)


class CastSpellTest(EventTest):

  def testCastSpell(self):
    shrivelling = items.Shrivelling(0)
    self.char.possessions.append(shrivelling)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.hands_available(), 2)

    self.state.event_stack.append(CastSpell(self.char, shrivelling))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(shrivelling.in_use)
    self.assertTrue(shrivelling.active)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.hands_available(), 1)

  def testFailToCastSpell(self):
    shrivelling = items.Shrivelling(0)
    self.char.possessions.append(shrivelling)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.hands_available(), 2)

    self.state.event_stack.append(CastSpell(self.char, shrivelling))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertTrue(shrivelling.in_use)
    self.assertFalse(shrivelling.active)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.hands_available(), 1)

  def testCancelledSpellCheck(self):
    shrivelling = items.Shrivelling(0)
    self.char.possessions.append(shrivelling)
    self.char.possessions.append(Canceller(Check))
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.hands_available(), 2)

    self.state.event_stack.append(CastSpell(self.char, shrivelling))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    self.resolve_until_done()

    self.assertTrue(shrivelling.in_use)
    self.assertFalse(shrivelling.active)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.hands_available(), 1)

  def testCancelledSpellCost(self):
    shrivelling = items.Shrivelling(0)
    self.char.possessions.append(shrivelling)
    self.char.possessions.append(Canceller(SpendChoice))
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.hands_available(), 2)

    cast = CastSpell(self.char, shrivelling)
    self.state.event_stack.append(cast)
    self.resolve_until_done()

    self.assertFalse(shrivelling.in_use)
    self.assertFalse(shrivelling.active)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.hands_available(), 2)
    self.assertFalse(cast.is_resolved())
    self.assertTrue(cast.is_cancelled())

  def testCancelledActivation(self):
    shrivelling = items.Shrivelling(0)
    self.char.possessions.append(shrivelling)
    self.char.possessions.append(Canceller(ActivateItem))
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.hands_available(), 2)

    cast = CastSpell(self.char, shrivelling)
    self.state.event_stack.append(cast)
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(shrivelling.in_use)
    self.assertFalse(shrivelling.active)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.hands_available(), 1)
    self.assertTrue(cast.is_resolved())
    self.assertTrue(cast.activation.is_cancelled())

  def testCastAndGoInsane(self):
    pass  # TODO: a spell that has a non-combat effect.


# TODO: add tests for going unconscious/insane during a mythos/encounter.


class PurchaseTest(EventTest):
  def testPurchaseOneAtList(self):
    buy = Purchase(self.char, "common", 1)
    self.char.dollars = 3
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.state.common.append(food)

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Nothing"])
    self.assertEqual(choice.annotations(self.state), ["1 dollars", ""])
    with self.assertRaisesRegex(InvalidMove, "additional 1 dollars"):
      choice.resolve(self.state, "Food")
    self.spend("dollars", 1, choice)
    choice.resolve(self.state, "Food")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.possessions, [food])
    self.assertFalse(self.state.common)

  def testPurchaseOneAtListDecline(self):
    buy = Purchase(self.char, "common", 1)
    self.char.dollars = 3
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.state.common.append(food)

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Nothing"])
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 3)
    self.assertFalse(self.char.possessions)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0], food)

  def testPurchaseOneAtListPoor(self):
    buy = Purchase(self.char, "common", 1)
    self.char.dollars = 0
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.state.common.append(food)

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Nothing"])
    with self.assertRaisesRegex(InvalidMove, "additional 1 dollars"):
      choice.resolve(self.state, "Food")
    with self.assertRaisesRegex(InvalidMove, "more dollars than you have"):
      choice.spend("dollars")
    with self.assertRaisesRegex(InvalidMove, "additional 1 dollars"):
      choice.resolve(self.state, "Food")  # Just making extra sure we didn't actually spend money.
    self.resolve_to_choice(CardSpendChoice)
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0], food)
    self.assertFalse(self.char.possessions)

  def testPurchaseTwoAtListAffordOne(self):
    buy = Purchase(self.char, "common", 2, keep_count=2)
    self.char.dollars = 3
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    gun = items.TommyGun(0)
    self.state.common.extend([gun, food])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Tommy Gun", "Food", "Nothing"])
    self.spend("dollars", 1, choice)
    self.assertEqual(choice.remaining_spend, [{"dollars": 6}, False, {"dollars": -1}])
    choice.resolve(self.state, "Food")

    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Tommy Gun", "Nothing"])
    self.assertEqual(choice.remaining_spend, [{"dollars": 7}, False])
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.possessions, [food])
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0], gun)

  def testPurchaseTwoAtList(self):
    buy = Purchase(self.char, "common", 2, keep_count=2)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    gun = items.TommyGun(0)
    self.state.common.extend([food, gun])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Tommy Gun", "Nothing"])
    self.assertEqual(choice.annotations(self.state), ["1 dollars", "7 dollars", ""])
    self.spend("dollars", 7, choice)
    self.assertEqual(choice.remaining_spend, [{"dollars": -6}, False, {"dollars": -7}])
    choice.resolve(self.state, "Tommy Gun")
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Nothing"])
    self.spend("dollars", 1, choice)
    choice.resolve(self.state, "Food")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.possessions, [gun, food])
    self.assertFalse(self.state.common)

  def testPurchaseTwoAtFixedDiscount(self):
    buy = Purchase(self.char, "common", 2, keep_count=2, discount=1)
    self.char.dollars = 6
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    gun = items.TommyGun(0)
    self.state.common.extend([food, gun])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Tommy Gun", "Nothing"])
    self.assertEqual(choice.annotations(self.state), ["0 dollars", "6 dollars", ""])
    self.spend("dollars", 6, choice)
    choice.resolve(self.state, "Tommy Gun")
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Nothing"])
    choice.resolve(self.state, "Food")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.possessions, [gun, food])
    self.assertFalse(self.state.common)

  def testPurchaseTwoAtHalfDiscount(self):
    buy = Purchase(self.char, "common", 2, keep_count=2, discount_type="rate", discount=.5)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    gun = items.TommyGun(0)
    self.state.common.extend([food, gun])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Tommy Gun", "Nothing"])
    self.assertEqual(choice.annotations(self.state), ["1 dollars", "4 dollars", ""])
    self.spend("dollars", 4, choice)
    choice.resolve(self.state, "Tommy Gun")
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Nothing"])
    self.spend("dollars", 1, choice)
    choice.resolve(self.state, "Food")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(self.char.possessions, [gun, food])
    self.assertFalse(self.state.common)

  def testPurchaseTwoAtExtraCost(self):
    buy = Purchase(self.char, "common", 2, keep_count=2, discount=-1)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    gun = items.TommyGun(0)
    self.state.common.extend([food, gun])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Tommy Gun", "Nothing"])
    self.assertEqual(choice.annotations(self.state), ["2 dollars", "8 dollars", ""])
    self.spend("dollars", 8, choice)
    choice.resolve(self.state, "Tommy Gun")
    choice = self.resolve_to_choice(CardSpendChoice)
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.possessions, [gun])
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0], food)

  def testDraw2Purchase1AtList(self):
    buy = Purchase(self.char, "common", 2, keep_count=1)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    gun = items.TommyGun(0)
    cross = items.Cross(0)
    self.state.common.extend([food, gun, cross])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Food", "Tommy Gun", "Nothing"])
    self.spend("dollars", 7, choice)
    choice.resolve(self.state, "Tommy Gun")
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(self.char.possessions, [gun])
    self.assertEqual(len(self.state.common), 2)
    self.assertSequenceEqual(self.state.common, [cross, food])

  def testDraw2MustPurchase1(self):
    buy = Purchase(self.char, "common", 2, keep_count=1, must_buy=True)
    self.char.dollars = 4
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    cross = items.Cross(0)
    gun = items.TommyGun(0)
    self.state.common.extend([cross, gun])

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(choice.choices, ["Cross", "Tommy Gun", "Nothing"])
    self.assertIn(2, choice.invalid_choices)
    with self.assertRaisesRegex(InvalidMove, "must purchase"):
      choice.resolve(self.state, "Nothing")
    self.char.dollars = 2
    choice = self.resolve_to_choice(CardSpendChoice)
    choice.resolve(self.state, "Nothing")
    self.resolve_until_done()

    self.assertFalse(self.char.possessions)

  def testCancelledDraw(self):
    buy = Purchase(self.char, "common", 2, keep_count=1)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    self.char.possessions.append(Canceller(DrawItems))
    self.state.common.extend([items.Food(0), items.TommyGun(0), items.Cross(0)])
    self.assertEqual(len(self.state.common), 3)

    self.state.event_stack.append(buy)
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertFalse(buy.events[0].is_resolved())
    self.assertTrue(buy.events[0].is_cancelled())
    self.assertFalse(buy.events[1].is_resolved())
    self.assertTrue(buy.events[1].is_cancelled())
    self.assertEqual(self.char.dollars, 8)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.common), 3)

  def testCancelledChoice(self):
    buy = Purchase(self.char, "common", 2, keep_count=1)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    self.char.possessions.append(Canceller(CardSpendChoice))
    self.state.common.extend([items.Food(0), items.TommyGun(0), items.Cross(0)])
    self.assertEqual(len(self.state.common), 3)

    self.state.event_stack.append(buy)
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertTrue(buy.events[0].is_resolved())
    self.assertFalse(buy.events[1].is_resolved())
    self.assertTrue(buy.events[1].is_cancelled())
    self.assertEqual(self.char.dollars, 8)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.common), 3)

  def testCancelledPurchase(self):
    buy = Purchase(self.char, "common", 2, keep_count=1)
    self.char.dollars = 8
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    self.char.possessions.append(Canceller(PurchaseDrawn))
    self.state.common.extend([items.Food(0), items.TommyGun(0), items.Cross(0)])
    self.assertEqual(len(self.state.common), 3)

    self.state.event_stack.append(buy)
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertTrue(buy.events[0].is_resolved())
    self.assertFalse(buy.events[1].is_resolved())
    self.assertTrue(buy.events[1].is_cancelled())
    self.assertEqual(self.char.dollars, 8)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(len(self.state.common), 3)


class SellTest(EventTest):
  def testSellOneAtList(self):
    sell = Sell(self.char, {"common"}, 1)
    self.char.dollars = 3
    self.assertFalse(sell.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.char.possessions.append(food)

    self.state.event_stack.append(sell)
    choice = self.resolve_to_choice(ItemChoice)
    self.assertEqual(choice.choices, ["Food0"])
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()

    self.assertTrue(sell.is_resolved())
    self.assertEqual(self.char.dollars, 4)
    self.assertFalse(self.char.possessions)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].name, "Food")

  def testSellOneDecline(self):
    sell = Sell(self.char, {"common"}, 1)
    self.char.dollars = 3
    self.assertFalse(sell.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.char.possessions.append(food)

    self.state.event_stack.append(sell)
    choice = self.resolve_to_choice(ItemChoice)
    self.assertEqual(choice.choices, ["Food0"])
    self.choose_items(choice, [])
    self.resolve_until_done()

    self.assertTrue(sell.is_resolved())
    self.assertEqual(self.char.dollars, 3)
    self.assertFalse(self.state.common)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Food")

  def testSellOneDoublePrice(self):
    buy = Sell(self.char, {"common"}, 1, discount_type="rate", discount=-1)
    self.char.dollars = 3
    self.assertFalse(buy.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.char.possessions.append(food)

    self.state.event_stack.append(buy)
    choice = self.resolve_to_choice(ItemChoice)
    self.assertEqual(choice.choices, ["Food0"])
    self.choose_items(choice, ["Food0"])
    self.resolve_until_done()

    self.assertTrue(buy.is_resolved())
    self.assertEqual(self.char.dollars, 5)
    self.assertFalse(self.char.possessions)
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].name, "Food")

  def testInvalidSale(self):
    self.char.possessions = [items.Food(0), items.HolyWater(0)]
    sell = Sell(self.char, {"common"}, 1)
    self.state.event_stack.append(sell)
    choice = self.resolve_to_choice(ItemChoice)
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choice.resolve(self.state, "Holy Water0")

  def testSellChoiceCancelled(self):
    sell = Sell(self.char, {"common"}, 1)
    self.char.dollars = 3
    self.assertFalse(sell.is_resolved())
    self.assertFalse(self.char.possessions)
    food = items.Food(0)
    self.char.possessions.append(food)
    self.char.possessions.append(Canceller(ItemChoice))

    self.state.event_stack.append(sell)
    self.resolve_until_done()

    self.assertTrue(sell.is_resolved())
    self.assertFalse(sell.events[1].is_resolved())
    self.assertTrue(sell.events[1].is_cancelled())
    self.assertEqual(self.char.dollars, 3)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertFalse(self.state.common)


class CloseLocationTest(EventTest):
  def testCloseForever(self):
    place_name = "Woods"
    self.char.place = self.state.places["Woods"]
    self.state.event_stack.append(CloseLocation(place_name))
    # evict=True is implicit
    self.resolve_until_done()
    self.assertTrue(self.state.places[place_name].closed)
    self.assertEqual(self.char.place.name, "Uptown")
    self.state.event_stack.append(CloseLocation(place_name, for_turns=1))
    self.resolve_until_done()
    self.advance_turn(self.state.turn_number + 5, "mythos")
    self.resolve_until_done()
    self.assertTrue(self.state.places[place_name].closed)

  def testCloseWithGateForOneTurn(self):
    place_name = "Woods"
    self.char.place = self.state.places["Uptown"]  # Avoid encounters while advancing the turn.
    self.advance_turn(self.state.turn_number, "mythos")
    self.char.place = self.state.places[place_name]
    self.resolve_until_done()
    place = self.state.places[place_name]
    place.gate = self.state.gates.popleft()
    monster = next(iter(self.state.monsters))
    monster.place = place
    self.char.place = place
    self.state.event_stack.append(CloseLocation(place_name, 1))
    self.resolve_until_done()

    self.assertEqual(place.closed_until, self.state.turn_number + 2)
    self.assertEqual(self.char.place, place)
    self.assertEqual(monster.place, place)
    self.assertFalse(place.closed)

    self.state.event_stack.append(GateCloseAttempt(self.char, place_name))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_lore = self.resolve_to_choice(MultipleChoice)
      fight_lore.resolve(self.state, fight_lore.choices[0])
      seal_choice = self.resolve_to_choice(SpendChoice)
      seal_choice.resolve(self.state, "No")
      self.resolve_until_done()

    self.assertEqual(place.closed_until, self.state.turn_number + 2)
    self.assertEqual(self.char.place.name, "Uptown")
    self.assertEqual(monster.place.name, "Uptown")
    self.assertTrue(place.closed)

    self.advance_turn(self.state.turn_number + 1, "movement")
    movement = self.resolve_to_choice(CityMovement)
    movement.resolve(self.state, movement.none_choice)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      # Need to kill the cultist to advance through movement
      choice = self.resolve_to_choice(MultipleChoice)
      choice.resolve(self.state, "Fight")
      choice = self.resolve_to_choice(MultipleChoice)
      choice.resolve(self.state, "Fight")
      choice = self.resolve_to_choice(CombatChoice)
      self.choose_items(choice, [])
      self.resolve_until_done()

    self.assertEqual(place.closed_until, self.state.turn_number + 1)

    self.advance_turn(self.state.turn_number + 1, "movement")
    self.assertFalse(place.closed)

  def testMoveToClosedLocation(self):
    place_name = "Woods"
    self.state.event_stack.append(CloseLocation(place_name))
    self.resolve_until_done()
    self.char.place = self.state.places["Uptown"]

    self.advance_turn(self.state.turn_number + 1, "movement")
    movement = self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.place.name, "Uptown")
    self.assertEqual(self.char.movement_points, 4)
    self.assertNotIn(place_name, movement.choices)
    movement.resolve(self.state, movement.none_choice)
    self.resolve_until_done()

    self.advance_turn(self.state.turn_number + 5, "movement")
    movement = self.resolve_to_choice(CityMovement)
    self.assertNotIn(place_name, movement.choices)
    self.assertTrue(self.state.places[place_name].closed)

  def testMoveFromClosedLocation(self):
    place_name = "Merchant"
    place = self.state.places[place_name]
    self.char.place = place
    self.advance_turn(self.state.turn_number, "mythos")
    self.resolve_until_done()
    self.state.event_stack.append(CloseLocation(place_name, for_turns=1, evict=False))
    self.resolve_until_done()
    self.assertTrue(place.closed)
    self.assertEqual(self.char.place.name, place_name)
    self.advance_turn(self.state.turn_number + 1, "movement")
    movement = self.resolve_to_choice(CityMovement)
    self.assertNotIn("Downtown", movement.choices)
    self.assertTrue(place.closed)
    movement.resolve(self.state, movement.none_choice)
    self.resolve_until_done()

    self.advance_turn(self.state.turn_number + 1, "movement")
    movement = self.resolve_to_choice(CityMovement)
    self.assertIn("Downtown", movement.choices)
    self.assertFalse(place.closed)


class AddDoomTest(EventTest):
  def testAddDoom(self):
    self.state.ancient_one.doom = 8
    self.state.event_stack.append(AddDoom())
    self.resolve_until_done()
    self.assertEqual(self.state.ancient_one.doom, 9)

  def testAddDoomAwaken(self):
    self.state.ancient_one.doom = 9
    self.state.event_stack.append(AddDoom())
    self.resolve_until_event_type(Awaken)
    self.assertEqual(self.state.ancient_one.doom, 10)


class IncreaseTerrorTest(EventTest):
  def setUp(self):
    super().setUp()
    self.state.allies.extend(assets.CreateAllies())

  def testAddSingleTerror(self):
    self.assertEqual(self.state.terror, 0)
    n_allies = len(self.state.allies)
    self.state.event_stack.append(events.IncreaseTerror(1))
    self.resolve_until_done()
    self.assertEqual(self.state.terror, 1)
    self.assertEqual(len(self.state.allies), n_allies - 1)
    self.assertEqual(len(self.state.boxed_allies), 1)
    self.assertFalse(self.state.places["Store"].closed)

  def testAddMultipleTerror(self):
    self.assertEqual(self.state.terror, 0)
    n_allies = len(self.state.allies)
    self.state.event_stack.append(events.IncreaseTerror(3))
    self.resolve_until_done()
    self.assertEqual(self.state.terror, 3)
    self.assertEqual(len(self.state.allies), n_allies - 3)
    self.assertEqual(len(self.state.boxed_allies), 3)
    self.assertTrue(self.state.places["Store"].closed)

  def testAddToMaxedTrack(self):
    self.state.terror = 2
    n_allies = len(self.state.allies)
    self.state.event_stack.append(events.Sequence([events.IncreaseTerror(1) for _ in range(10)]))
    self.resolve_until_done()
    self.assertEqual(self.state.terror, 10)
    # For every point the terror level goes up, ...
    self.assertEqual(len(self.state.allies), n_allies - 8)
    self.assertEqual(len(self.state.boxed_allies), 8)
    self.assertEqual(self.state.ancient_one.doom, 2)
    self.assertGreater(self.state.monster_limit(), 100)
    self.assertTrue(self.state.places["Store"].closed)
    self.assertTrue(self.state.places["Shop"].closed)
    self.assertTrue(self.state.places["Shoppe"].closed)


class ClearStatusTest(EventTest):
  def testClearDelayed(self):
    self.state.event_stack.append(Delayed(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.delayed_until, self.state.turn_number + 2)
    self.state.event_stack.append(ClearStatus(self.char, "delayed"))
    self.resolve_until_done()
    self.assertIsNone(self.char.delayed_until)

  def testClearLoseTurn(self):
    self.state.event_stack.append(LoseTurn(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.lose_turn_until, self.state.turn_number + 2)
    self.state.event_stack.append(ClearStatus(self.char, "lose_turn"))
    self.resolve_until_done()
    self.assertIsNone(self.char.lose_turn_until)

  def testClearArrested(self):
    self.state.event_stack.append(Arrested(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.arrested_until, self.state.turn_number + 2)
    self.state.event_stack.append(ClearStatus(self.char, "arrested"))
    self.resolve_until_done()
    self.assertIsNone(self.char.arrested_until)


if __name__ == "__main__":
  unittest.main()
