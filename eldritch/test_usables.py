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
from eldritch import characters
from eldritch import encounters
from eldritch import events
from eldritch.events import *
from eldritch import gates
from eldritch import gate_encounters
from eldritch import items
from eldritch import monsters
from eldritch.test_events import EventTest, Canceller

from game import InvalidMove


class ClueTokenTest(EventTest):

  def setUp(self):
    super().setUp()
    self.check = Check(self.char, "combat", 0)
    self.state.event_stack.append(self.check)

  def testSpendClues(self):
    self.char.clues = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)
    old_successes = self.check.successes
    old_roll = self.check.roll[:]

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("clues", 1, choice)
      choice.resolve(self.state, "Spend")
      choice = self.resolve_to_choice(SpendChoice)

    new_successes = self.check.successes
    new_roll = self.check.roll
    self.assertEqual(len(new_roll), 1+len(old_roll))
    self.assertEqual(new_successes, old_successes+1)
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)

    choice.resolve(self.state, "Done")
    self.resolve_until_done()

  def testSpendClueCancelledDie(self):
    self.char.clues = 3
    choice = self.resolve_to_choice(SpendChoice)
    self.char.possessions.append(Canceller(DiceRoll))
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)
    old_successes = self.check.successes
    old_roll = self.check.roll[:]

    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    choice = self.resolve_to_choice(SpendChoice)

    self.assertEqual(self.check.roll, old_roll)
    self.assertEqual(self.check.successes, old_successes)
    self.assertEqual(self.char.clues, 2)

  def testNoCluesLeft(self):
    self.char.clues = 1
    choice = self.resolve_to_choice(SpendChoice)
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)

    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    with self.assertRaisesRegex(InvalidMove, "Cannot spend more clues"):
      self.spend("clues", 1, choice)
    self.resolve_until_done()

  def testBonusDieFromSkill(self):
    self.char.clues = 2
    self.char.possessions.append(abilities.Fight(None))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)
    old_roll = self.check.roll[:]

    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    choice = self.resolve_to_choice(SpendChoice)

    new_roll = self.check.roll[:]
    self.assertEqual(len(new_roll), 2+len(old_roll))

    self.assertEqual(len(self.state.event_stack), 2)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    self.resolve_until_done()

    last_roll = self.check.roll[:]
    self.assertEqual(len(last_roll), 2+len(new_roll))


class RerollTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.clues = 2
    self.char.possessions.append(abilities.Marksman(0))
    self.check = Check(self.char, "combat", 0)
    self.state.event_stack.append(self.check)

  def testReroll(self):
    self.resolve_to_usable(0, "Marksman0", Sequence)
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)
    self.assertEqual(len(self.state.usables), 1)
    old_roll = self.check.roll[:]

    self.state.event_stack.append(self.state.usables[0]["Marksman0"])
    self.resolve_to_choice(SpendChoice)

    self.assertFalse(self.state.usables)

    new_roll = self.check.roll
    self.assertNotEqual(old_roll, new_roll)  # TODO: 1 / 1296 chance of failing.

  def testSpendClueThenReroll(self):
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    choice = self.resolve_to_choice(SpendChoice)
    old_roll = self.check.roll[:]

    self.state.event_stack.append(self.state.usables[0]["Marksman0"])
    choice = self.resolve_to_choice(SpendChoice)

    self.assertFalse(self.state.usables)

    new_roll = self.check.roll
    self.assertEqual(len(new_roll), len(old_roll))
    self.assertNotEqual(old_roll, new_roll)  # TODO: 1 / 1296 chance of failing.

  def testRerollDiceCancelled(self):
    self.resolve_to_usable(0, "Marksman0", Sequence)
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)
    self.assertEqual(len(self.state.usables), 1)
    self.char.possessions.append(Canceller(DiceRoll))
    old_roll = self.check.roll[:]
    old_successes = self.check.successes

    reroll = self.state.usables[0]["Marksman0"]
    self.state.event_stack.append(reroll)
    self.resolve_to_choice(SpendChoice)

    self.assertFalse(self.state.usables)

    self.assertFalse(reroll.events[1].is_resolved())
    self.assertTrue(reroll.events[1].is_cancelled())
    self.assertEqual(self.check.roll, old_roll)
    self.assertEqual(self.check.successes, old_successes)


class DeputyTest(EventTest):

  def testBecomingDeputyGivesItems(self):
    self.state.tradables.extend(items.CreateTradables())
    self.state.specials.extend(items.CreateSpecials())
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Deputy"))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertCountEqual(
        [pos.name for pos in self.char.possessions],
        ["Deputy", "Deputy's Revolver", "Patrol Wagon"],
    )

  def testGainADollarDuringUpkeep(self):
    self.char.possessions.append(assets.Deputy())
    self.assertEqual(self.char.dollars, 0)
    self.state.event_stack.append(Upkeep(self.char))
    self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.dollars, 1)

  def testCannotBeDeputyIfSomeoneElseIs(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.state.tradables.extend(items.CreateTradables())
    self.state.specials.extend(items.CreateSpecials())

    self.state.event_stack.append(DrawSpecific(buddy, "specials", "Deputy"))
    self.resolve_until_done()
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Deputy"))
    self.resolve_until_done()

    self.assertEqual(len(buddy.possessions), 3)
    self.assertEqual(len(self.char.possessions), 0)

  def testDeputyCardsReturnIfDevoured(self):
    self.state.tradables.extend([items.DeputysRevolver(), items.PatrolWagon()])
    self.state.specials.append(assets.Deputy())
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Deputy"))
    self.resolve_until_done()

    self.assertFalse(self.state.tradables)
    self.assertFalse(self.state.specials)

    self.state.event_stack.append(Devoured(self.char))
    self.resolve_until_done()

    self.assertEqual(len(self.state.tradables), 2)
    self.assertEqual(len(self.state.specials), 1)
    self.assertEqual(self.state.specials[0].name, "Deputy")


class WagonTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.PatrolWagon())
    self.state.turn_phase = "movement"

  def testCanWagonInsteadOfMove(self):
    self.char.place = self.state.places["Square"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.assertIn(0, self.state.usables)
    self.assertIn("Patrol Wagon", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    self.assertIn("Woods", choice.choices)
    self.assertIn("Easttown", choice.choices)
    # self.assertNotIn("Square", choice.choices)  TODO
    choice.resolve(self.state, "Woods")
    self.resolve_until_done()  # CityMovement should get cancelled
    self.assertEqual(self.char.place.name, "Woods")

  def testCanCancelWagon(self):
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Cancel")
    self.resolve_to_choice(CityMovement)
    self.assertIn("Patrol Wagon", self.state.usables[0])  # Can change your mind again and use it.

  def testCannotWagonAfterMoving(self):
    self.state.event_stack.append(Movement(self.char))
    move = self.resolve_to_choice(CityMovement)
    move.resolve(self.state, "Easttown")
    self.resolve_to_choice(CityMovement)
    self.assertNotIn(0, self.state.usables)

  def testCanUseTomeBeforeWagon(self):
    self.state.spells.append(items.Wither(0))
    self.char.possessions.append(items.AncientTome(0))
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Ancient Tome0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(CityMovement)
    self.assertIn(0, self.state.usables)
    self.assertIn("Patrol Wagon", self.state.usables[0])
    self.assertNotIn("Ancient Tome0", self.state.usables[0])
    self.assertIn("Wither", [card.name for card in self.char.possessions])
    self.assertNotIn("Ancient Tome", [card.name for card in self.char.possessions])

    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Woods")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Woods")

  def testCanUseTomeAfterWagon(self):
    self.state.spells.append(items.Wither(0))
    self.char.possessions.append(items.AncientTome(0))
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Woods")
    self.resolve_to_usable(0, "Ancient Tome0", Sequence)

    self.assertIsInstance(self.state.event_stack[-1], WagonMove)
    self.assertNotIn("Patrol Wagon", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Ancient Tome0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertIn("Wither", [card.name for card in self.char.possessions])
    self.assertNotIn("Ancient Tome", [card.name for card in self.char.possessions])

  def testEvadeMonstersAtWagonStart(self):
    self.char.speed_sneak_slider = 1
    self.state.monsters[1].place = self.char.place
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Woods")
    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Woods")

  def testCancelUsingWagonNearbyMonsters(self):
    self.state.monsters[0].place = self.char.place
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Cancel")
    # If there are monsters at your location, you should be able to cancel using the patrol wagon
    # without being asked to fight or evade them.
    self.resolve_to_choice(CityMovement)

  def testCaughtByMonstersAtWagonStart(self):
    self.state.monsters[0].place = self.char.place
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Woods")
    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    weapons = self.resolve_to_choice(CombatChoice)
    weapons.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      # After fighting, your movement is over; the wagon cannot be used.
      # Note that the dice roll of 5 also covers the roll to see if you lose the wagon.
      self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Diner")

  def testMustHandleMonstersAtEnd(self):
    self.state.monsters[0].place = self.state.places["Woods"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Woods")
    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(self.char.place.name, "Woods")  # Have already moved, now fighting cultist.
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    weapons = self.resolve_to_choice(CombatChoice)
    weapons.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    # You should not lose the patrol wagon after a combat round; only after the combat is over.
    self.assertEqual(len(self.char.possessions), 1)
    fight_or_flee.resolve(self.state, "Fight")
    weapons = self.resolve_to_choice(CombatChoice)
    weapons.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 1)

  def testLoseWagonAfterCombat(self):
    self.state.monsters[0].place = self.state.places["Woods"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Woods")
    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(self.char.place.name, "Woods")  # Have already moved, now fighting cultist.
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    weapons = self.resolve_to_choice(CombatChoice)
    weapons.resolve(self.state, "done")
    rolls = self.char.fight(self.state) * [5] + [5] + [1]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=rolls)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 0)
    self.assertFalse(self.state.tradables)

  def testPatrolWagonReturn(self):
    self.state.places["Isle"].gate = self.state.gates.popleft()
    self.char.place = self.state.places[self.state.places["Isle"].gate.name + "2"]
    self.state.event_stack.append(Movement(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=2)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 1)
    self.assertEqual(self.char.place.name, "Isle")
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Patrol Wagon")

  def testLosePatrolWagonReturn(self):
    self.state.places["Isle"].gate = self.state.gates.popleft()
    self.char.place = self.state.places[self.state.places["Isle"].gate.name + "2"]
    self.state.event_stack.append(Movement(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 1)
    self.assertEqual(self.char.place.name, "Isle")
    self.assertEqual(len(self.char.possessions), 0)
    self.assertNotIn("Patrol Wagon", [card.name for card in self.state.tradables])


class OneshotItemTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.Dynamite(0))
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


class TomeTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.turn_phase = "movement"
    self.char.place = self.state.places["Diner"]
    self.state.event_stack.append(Movement(self.char))

  def testCannotReadInsufficientMovement(self):
    self.char.possessions.append(items.AncientTome(0))
    self.char.speed_sneak_slider = 0
    self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.movement_points, 1)
    self.assertNotIn(0, self.state.usables)

  def testCannotReadInOtherWorlds(self):
    self.char.place = self.state.places["Dreamlands1"]
    # If the ancient tome is usable in the dreamlands, then the event loop will stop and ask
    # if the user wants to use it, which will cause resolve_until_done to fail.
    self.resolve_until_done()

  def testReadAncientTomeSuccess(self):
    self.char.speed_sneak_slider = 1
    self.char.possessions.append(items.AncientTome(0))
    self.state.spells.append(items.FindGate(0))
    self.resolve_to_choice(CityMovement)

    self.assertEqual(self.char.movement_points, 2)
    self.assertIn(0, self.state.usables)
    self.assertIn("Ancient Tome0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Ancient Tome0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(CityMovement)

    self.assertEqual(self.char.movement_points, 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Find Gate")
    self.assertEqual(len(self.state.common), 1)

  def testReadAncientTomeFailure(self):
    self.char.possessions.append(items.AncientTome(0))
    self.state.spells.append(items.FindGate(0))
    self.resolve_to_choice(CityMovement)

    self.state.event_stack.append(self.state.usables[0]["Ancient Tome0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(CityMovement)

    self.assertEqual(self.char.movement_points, 2)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Ancient Tome")
    self.assertEqual(len(self.state.common), 0)
    self.assertEqual(len(self.state.spells), 1)


class LossPreventionTest(EventTest):

  def setUp(self):
    super().setUp()
    self.food = items.Food(0)
    self.char.possessions.append(self.food)
    self.loss = Loss(self.char, {"stamina": 1})
    self.state.event_stack.append(self.loss)

  def testIsUsable(self):
    self.assertEqual(self.char.stamina, 5)

    self.resolve_to_usable(0, "Food0", Sequence)
    self.assertFalse(self.loss.is_resolved())
    self.assertCountEqual([0], self.state.usables.keys())

    self.state.done_using[0] = True
    self.resolve_loop()
    self.assertTrue(self.loss.is_resolved())
    self.assertEqual(self.char.stamina, 4)

  def testPreventLoss(self):
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(len(self.state.common), 0)

    self.resolve_to_usable(0, "Food0", Sequence)
    self.assertFalse(self.loss.is_resolved())

    self.state.event_stack.append(self.state.usables[0]["Food0"])
    self.resolve_loop()
    self.assertTrue(self.loss.is_resolved())
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(len(self.state.common), 1)

  def testPreventOnlyOne(self):
    self.assertEqual(self.char.stamina, 5)
    self.loss.losses["stamina"] = 2

    self.resolve_to_usable(0, "Food0", Sequence)
    self.assertFalse(self.loss.is_resolved())

    self.state.event_stack.append(self.state.usables[0]["Food0"])
    self.resolve_loop()
    self.assertTrue(self.loss.is_resolved())
    self.assertEqual(self.char.stamina, 4)


class FindGateTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.FindGate(0))
    self.info = places.OtherWorldInfo("Pluto", {"blue", "yellow"})
    self.gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.places["Woods"].gate = self.gate
    self.state.turn_phase = "movement"

  def testCastBeforeMovement(self):
    self.char.place = self.state.places["Pluto1"]
    self.state.places["Isle"].gate = gates.Gate("Pluto", 0, -2, "circle")
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_usable(0, "Find Gate0", CastSpell)

    self.assertEqual(self.char.place.name, "Pluto1")

    self.state.event_stack.append(self.state.usables[0]["Find Gate0"])
    spend_choice = self.resolve_to_choice(SpendMixin)
    self.spend("sanity", 1, spend_choice)
    spend_choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(GateChoice)
    choice.resolve(self.state, "Isle")
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Isle")
    self.assertTrue(self.char.explored)

  def testCastAfterMovement(self):
    self.char.place = self.state.places["Pluto1"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_usable(0, "Find Gate0", CastSpell)

    self.assertEqual(self.char.place.name, "Pluto1")
    self.state.done_using[0] = True
    self.resolve_to_usable(0, "Find Gate0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Find Gate0"])
    spend_choice = self.resolve_to_choice(SpendMixin)
    self.spend("sanity", 1, spend_choice)
    spend_choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Woods")
    self.assertTrue(self.char.explored)

  def testFailToCast(self):
    self.char.place = self.state.places["Pluto1"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_usable(0, "Find Gate0", CastSpell)

    self.assertEqual(self.char.place.name, "Pluto1")

    self.state.event_stack.append(self.state.usables[0]["Find Gate0"])
    spend_choice = self.resolve_to_choice(SpendMixin)
    self.spend("sanity", 1, spend_choice)
    spend_choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Pluto2")

  def testCannotBeCastOutsideOtherworldMovement(self):
    self.char.place = self.state.places["Woods"]
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    self.assertNotIn(0, self.state.usables)
    choice.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Woods")
    self.state.next_turn()
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Pluto1")

  # TODO: a test covering the ability to cast after travelling during the movement phase


class FleshWardTest(EventTest):
  def setUp(self):
    super().setUp()
    self.flesh_ward = items.FleshWard(0)
    self.char.possessions.append(self.flesh_ward)
    self.char.possessions.append(items.TommyGun(0))

  def testCombat(self):
    monster = monsters.Cultist()
    combat = Combat(self.char, monster)
    self.state.event_stack.append(combat)
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Flesh Ward0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertListEqual(choice.choices, ["Cast", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Cast")
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 4)

    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_choice(MultipleChoice)
      # no longer usable
      self.assertNotIn("Flesh Ward0", self.state.usables)
      self.assertFalse(self.state.usables)

  def testFailToCast(self):
    monster = monsters.Cultist()
    combat = Combat(self.char, monster)
    self.state.event_stack.append(combat)
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Flesh Ward0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertListEqual(choice.choices, ["Cast", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Cast")
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertTrue(self.flesh_ward.exhausted)

    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)

    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_choice(MultipleChoice)
      # no longer usable
      self.assertFalse(self.state.usables)

  def testOverwhelming(self):
    self.char.fight_will_slider = 2
    monster = monsters.GiantWorm()
    combat = Combat(self.char, monster)
    self.state.event_stack.append(combat)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      # pass horror check
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.assertEqual(self.char.sanity, 4)
    combat_choice.resolve(self.state, "Tommy Gun0")
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Flesh Ward0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertListEqual(choice.choices, ["Cast", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Cast")
      self.resolve_until_done()

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 3)

  def testNonCombat(self):
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    self.state.event_stack.append(encounters.Woods2(self.char))
    # Fail a sneak check, get worked over by gang
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Flesh Ward0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertListEqual(choice.choices, ["Cast", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Cast")
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 4)

  def testCombinedSanityStaminaLoss(self):
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    self.state.event_stack.append(Loss(self.char, {"sanity": 1, "stamina": 5}))
    self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Flesh Ward0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertListEqual(choice.choices, ["Cast", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Cast")
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    # -1 from the spell, -1 from the Loss()
    self.assertEqual(self.char.sanity, 3)

  def testNotUsableAfterDamageReduced(self):
    self.char.possessions.append(items.Food(0))
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    self.state.event_stack.append(Loss(self.char, {"stamina": 1}))
    self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Food0"])
    self.resolve_until_done()
    self.assertFalse(self.state.usables)
    self.assertEqual(self.char.stamina, 5)

  def testDiscardedIfAncientOneAwakens(self):
    self.state.turn_phase = "mythos"
    self.state.event_stack.append(AddDoom(count=float("inf")))
    self.resolve_until_done()
    self.assertNotIn("Flesh Ward", [card.name for card in self.char.possessions])


class HealTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Uptown"]
    self.char.possessions.append(items.Heal(0))
    self.char.stamina = 3
    self.state.turn_phase = "upkeep"

  def testHeal(self):
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Cast", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(
            events.random,
            "randint",
            new=mock.MagicMock(side_effect=[5, 1, 1, 1, 1, 1, 1])):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy"])
    choice.resolve(self.state, "Dummy")
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)

  def testHealCapped(self):
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Cast", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy"])
    choice.resolve(self.state, "Dummy")
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)

  def testHealFailCast(self):
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Cast", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_until_done()

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)

  def testMultipleOptions(self):
    all_chars = characters.CreateCharacters()
    nun = all_chars["Nun"]
    doctor = all_chars["Doctor"]
    nun.stamina = 1
    doctor.stamina = 1
    nun.place = self.char.place
    doctor.place = self.state.places["Woods"]
    self.state.all_characters["Nun"] = nun
    self.state.all_characters["Doctor"] = doctor
    self.state.characters.append(nun)
    self.state.characters.append(doctor)

    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Cast", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Nun"])
    choice.resolve(self.state, "Nun")
    self.resolve_until_done()

    self.assertEqual(nun.stamina, 3)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)


class PhysicianTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Uptown"]
    self.char.possessions.append(abilities.Physician())
    self.char.stamina = 3
    self.state.turn_phase = "upkeep"

  def testPhysician(self):
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    self.resolve_to_usable(0, "Physician", Sequence)

    self.state.event_stack.append(self.state.usables[0]["Physician"])
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
    self.resolve_to_usable(0, "Physician", Sequence)

    self.state.event_stack.append(self.state.usables[0]["Physician"])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Nun", "nobody"])
    choice.resolve(self.state, "Nun")
    self.resolve_until_done()

    self.assertEqual(nun.stamina, 2)
    self.assertEqual(self.char.stamina, 3)
    self.assertTrue(self.char.possessions[0].exhausted)


class ExtraDrawTest(EventTest):

  def testOtherDecksNotAffected(self):
    self.char.possessions.append(abilities.Studious())
    self.state.skills.extend([abilities.Marksman(0), abilities.Bravery(0)])
    self.state.common.extend([items.Food(0), items.DarkCloak(0)])
    self.state.event_stack.append(Draw(self.char, "skills", 1))
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Marksman", "Bravery"])
    choice.resolve(self.state, "Bravery")
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[1].handle, "Bravery0")
    self.assertEqual(len(self.state.skills), 1)

    # Should not affect other draw types
    self.state.event_stack.append(Draw(self.char, "common", 1))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(self.char.possessions[2].handle, "Food0")
    self.assertEqual(len(self.state.common), 1)

  def testDraw2Keep2BecomesDraw3(self):
    self.char.possessions.append(abilities.ShrewdDealer())
    self.state.common.extend([items.Food(0), items.DarkCloak(0), items.Cross(0), items.Whiskey(0)])
    self.state.event_stack.append(Draw(self.char, "common", 2, keep_count=2))

    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Food", "Dark Cloak", "Cross"])
    choice.resolve(self.state, "Cross")
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Food", "Dark Cloak"])
    choice.resolve(self.state, "Food")
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(
        [item.handle for item in self.char.possessions], ["Shrewd Dealer", "Cross0", "Food0"],
    )
    self.assertEqual(len(self.state.common), 2)
    self.assertEqual(self.state.common[-1].handle, "Dark Cloak0")

  def testDraw2Keep1BecomesDraw3(self):
    self.char.possessions.append(abilities.MagicalGift())
    self.state.spells.extend([items.Wither(0), items.Heal(0), items.Voice(0), items.Heal(1)])
    self.state.event_stack.append(Draw(self.char, "spells", 2, keep_count=1))

    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(choice.choices, ["Wither", "Heal", "Voice"])
    choice.resolve(self.state, "Heal")
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual([item.handle for item in self.char.possessions], ["Magical Gift", "Heal0"])
    self.assertEqual(len(self.state.spells), 3)
    self.assertEqual(self.state.spells[-2].handle, "Wither0")
    self.assertEqual(self.state.spells[-1].handle, "Voice0")

  def testDraw3Purchase1BecomesDraw4(self):
    self.char.possessions.append(abilities.Archaeology())
    self.char.dollars = 12
    self.state.unique.extend([
        items.HolyWater(0), items.MagicLamp(0), items.MagicPowder(0), items.SwordOfGlory(1),
    ])
    self.state.event_stack.append(Purchase(self.char, "unique", 3, keep_count=1))

    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(
        choice.choices, ["Holy Water", "Magic Lamp", "Magic Powder", "Sword of Glory", "Nothing"],
    )
    self.spend("dollars", 4, choice)
    choice.resolve(self.state, "Holy Water")
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual([item.name for item in self.char.possessions], ["Archaeology", "Holy Water"])
    self.assertEqual(len(self.state.unique), 3)
    self.assertEqual(self.char.dollars, 8)

  def testWithEncounters(self):
    self.char.possessions.append(abilities.HometownAdvantage())
    self.state.event_stack.append(EncounterPhase(self.char))
    self.state.places["Easttown"].encounters.extend([
        encounters.EncounterCard("Easttown2", {"Diner": encounters.Diner2}),
        encounters.EncounterCard("Easttown3", {"Diner": encounters.Store7}),
    ])
    self.state.common.extend([items.Whiskey(0), items.Food(0)])
    choice = self.resolve_to_choice(CardChoice)
    self.assertCountEqual(choice.choices, ["Easttown2", "Easttown3"])
    choice.resolve(self.state, "Easttown3")
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[-1].name, "Whiskey")

  def testOtherWorldEncounters(self):
    self.char.place = self.state.places["Plateau1"]
    self.char.possessions.append(abilities.PsychicSensitivity())
    self.state.event_stack.append(OtherWorldPhase(self.char))
    self.state.gate_cards.extend([
        gate_encounters.GateCard("Gate10", {"red"}, {"Other": gate_encounters.Other10}),
        gate_encounters.GateCard("Gate00", {"yellow"}, {"Other": gate_encounters.Dreamlands10}),
        gate_encounters.GateCard("Gate16", {"green"}, {"Other": gate_encounters.Plateau16}),
    ])
    choice = self.resolve_to_choice(CardChoice)
    # Gate00 is not a choice - wrong color
    self.assertCountEqual(choice.choices, ["Gate10", "Gate16"])
    choice.resolve(self.state, "Gate16")
    self.resolve_until_done()


class MistsTest(EventTest):
  def setUp(self):
    super().setUp()
    self.mists = items.Mists(0)
    self.char.possessions.append(self.mists)

  def testCombatEvade(self):
    monster = monsters.Cultist()
    self.state.event_stack.append(EvadeOrCombat(self.char, monster))
    evade_choice = self.resolve_to_choice(MultipleChoice)
    evade_choice.resolve(self.state, "Evade")
    self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Mists0"])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testFailToCast(self):
    monster = monsters.Cultist()
    self.state.event_stack.append(EvadeOrCombat(self.char, monster))
    evade_choice = self.resolve_to_choice(MultipleChoice)
    evade_choice.resolve(self.state, "Evade")
    self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Mists0"])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_choice(MultipleChoice)
      self.assertFalse(self.state.usables)
      self.assertTrue(self.mists.exhausted)

  def testCastAfterFail(self):
    monster = monsters.Cultist()
    self.char.clues = 1
    self.state.event_stack.append(EvadeOrCombat(self.char, monster))
    evade_choice = self.resolve_to_choice(MultipleChoice)
    evade_choice.resolve(self.state, "Evade")
    self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.done_using[0] = True
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Mists0"])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      spend_choice = self.resolve_to_choice(SpendChoice)
      self.assertIsInstance(self.state.event_stack[-2], Check)
      self.assertEqual(self.state.event_stack[-2].check_type, "spell")
    spend_choice.resolve(self.state, "Done")
    self.resolve_until_done()

  # TODO: test Elusive monsters


if __name__ == "__main__":
  unittest.main()
