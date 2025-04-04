#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch.abilities import base as abilities
from eldritch.allies import base as allies
from eldritch import characters
from eldritch.encounters.location.core import EncounterCard
from eldritch.encounters.location import base as encounters
from eldritch.encounters.gate.core import GateCard
from eldritch.encounters.gate import base as gate_encounters
from eldritch import events
from eldritch.events import *
from eldritch import gates
from eldritch import items
from eldritch import location_specials
from eldritch.monsters import base as monsters
from eldritch.mythos import base as mythos
from eldritch.skills import base as skills
from eldritch import specials
from eldritch.test_events import EventTest, Canceller, NoMythos

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
    self.assertEqual(len(new_roll), 1 + len(old_roll))
    self.assertEqual(new_successes, old_successes + 1)
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)

    choice.resolve(self.state, "Pass")
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
    self.char.possessions.append(skills.Fight(None))
    choice = self.resolve_to_choice(SpendChoice)
    self.assertFalse(self.check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], self.check.spend)
    old_roll = self.check.roll[:]

    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    choice = self.resolve_to_choice(SpendChoice)

    new_roll = self.check.roll[:]
    self.assertEqual(len(new_roll), 2 + len(old_roll))

    self.assertEqual(len(self.state.event_stack), 2)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")
    self.resolve_until_done()

    last_roll = self.check.roll[:]
    self.assertEqual(len(last_roll), 2 + len(new_roll))


class RerollTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.clues = 2
    self.char.possessions.append(skills.Marksman(0))
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


class ResearchTest(EventTest):
  def testUseOnOwnCheck(self):
    self.char.clues = 2
    self.char.possessions.append(abilities.Research())
    check = Check(self.char, "speed", 0)
    self.state.event_stack.append(check)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Research", Sequence)
    self.assertFalse(check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], check.spend)
    self.assertEqual(len(self.state.usables), 1)
    self.assertEqual(check.roll, [4, 4, 4, 4])

    self.state.event_stack.append(self.state.usables[0]["Research"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(SpendChoice)

    self.assertFalse(self.state.usables)
    self.assertEqual(check.roll, [5, 5, 5, 5])

  def testUseOnSomeoneElsesCheck(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.clues = 2
    buddy.possessions.append(items.Shotgun(0))
    self.char.possessions.append(abilities.Research())

    cultist = self.add_monsters(monsters.Cultist())
    combat = CombatRound(buddy, cultist)
    self.state.event_stack.append(combat)
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Shotgun0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Research", Sequence)
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 0)
    self.assertNotIn(1, self.state.usables)

    self.state.event_stack.append(self.state.usables[0]["Research"])
    new_rolls = [6, 1, 4, 3, 2, 1, 3, 4, 4]
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=new_rolls)):
      spend = self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.successes, 2)  # 6s with the shotgun count for 2
    self.assertFalse(self.state.usables)

    spend.resolve(self.state, "Pass")
    self.resolve_until_done()

  def testDeclineToUse(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.clues = 2
    self.char.possessions.append(abilities.Research())

    check = Check(buddy, "speed", 0)
    self.state.event_stack.append(check)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      spend = self.resolve_to_choice(SpendChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Research", self.state.usables[0])
    self.assertEqual(check.successes, 0)
    self.assertNotIn(1, self.state.usables)

    # The player making the check may decide that they're done without waiting for the player with
    # the Research ability to decide not to use it.
    spend.resolve(self.state, "Fail")
    self.resolve_until_done()


class SpeedBoostTest(EventTest):
  def setUp(self):
    super().setUp()
    self.buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Diner")
    self.buddy.place = self.state.places["Diner"]
    self.state.characters.append(self.buddy)
    self.advance_turn(0, "movement")

  def testDefaultBehavior(self):
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 4)
    self.assertEqual(self.buddy.movement_points, 4)

  def testGainMovement(self):
    self.char.possessions = [items.Motorcycle(0)]
    motorcycle = self.resolve_to_usable(0, "Motorcycle0", Sequence)
    self.state.event_stack.append(motorcycle)
    move = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.state.usables, {})
    self.assertEqual(self.char.movement_points, 6)
    move.resolve(self.state, "done")
    self.resolve_until_done()

  def testDeclineToUse(self):
    self.char.possessions = [items.Motorcycle(0)]
    self.resolve_to_usable(0, "Motorcycle0", Sequence)
    move = self.resolve_to_choice(events.CityMovement)
    move.resolve(self.state, "done")
    self.resolve_until_done()

  def testUseAndGiveAway(self):
    self.char.possessions = [items.Motorcycle(0)]
    motorcycle = self.resolve_to_usable(0, "Motorcycle0", Sequence)
    self.state.event_stack.append(motorcycle)
    move = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.state.usables, {})
    self.assertEqual(self.char.movement_points, 6)
    self.state.handle_give(0, 1, "Motorcycle0", None)
    self.assertEqual(self.char.possessions, [])
    self.assertEqual(len(self.buddy.possessions), 1)
    move.resolve(self.state, "done")
    self.resolve_until_done()
    self.state.next_turn()
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.state.usables, {})
    self.assertEqual(self.buddy.movement_points, 4)


class CigaretteTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.CigaretteCase(0))

  def testUseOnOwnCheck(self):
    self.char.clues = 2
    check = Check(self.char, "speed", 0)
    self.state.event_stack.append(check)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_usable(0, "Cigarette Case0", Sequence)
    self.assertFalse(check.is_resolved())
    self.assertEqual(len(self.state.event_stack), 2)
    self.assertEqual(self.state.event_stack[-1], check.spend)
    self.assertEqual(len(self.state.usables), 1)
    self.assertEqual(check.roll, [4, 4, 4, 4])

    self.state.event_stack.append(self.state.usables[0]["Cigarette Case0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(SpendChoice)

    self.assertFalse(self.state.usables)
    self.assertEqual(check.roll, [5, 5, 5, 5])

  def testCantUseOnSomeoneElsesCheck(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    buddy.clues = 2
    buddy.possessions.append(items.Shotgun(0))

    cultist = self.add_monsters(monsters.Cultist())
    combat = CombatRound(buddy, cultist)
    self.state.event_stack.append(combat)
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Shotgun0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_choice(events.SpendChoice)
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 0)
    self.assertNotIn(0, self.state.usables)


class TrustFundTest(EventTest):
  def testGainADollarDuringUpkeep(self):
    self.char.possessions.append(abilities.TrustFund())
    self.assertEqual(self.char.dollars, 0)
    self.state.event_stack.append(Upkeep(self.char))
    self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.dollars, 1)


class DeputyTest(EventTest):
  def testBecomingDeputyGivesItems(self):
    self.state.tradables.extend(specials.CreateTradables())
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Deputy"))
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertCountEqual(
      [pos.name for pos in self.char.possessions], ["Deputy", "Deputy's Revolver", "Patrol Wagon"]
    )

  def testGainADollarDuringUpkeep(self):
    self.char.possessions.append(specials.Deputy())
    self.assertEqual(self.char.dollars, 0)
    self.state.event_stack.append(Upkeep(self.char))
    self.resolve_to_choice(SliderInput)
    self.assertEqual(self.char.dollars, 1)

  def testCannotBeDeputyIfSomeoneElseIs(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Square"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)

    self.state.tradables.extend(specials.CreateTradables())

    self.state.event_stack.append(DrawSpecific(buddy, "specials", "Deputy"))
    self.resolve_until_done()
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Deputy"))
    self.resolve_until_done()

    self.assertEqual(len(buddy.possessions), 3)
    self.assertEqual(len(self.char.possessions), 0)

  def testDeputyCardsReturnIfDevoured(self):
    self.state.tradables.extend([items.deputy.DeputysRevolver(), items.deputy.PatrolWagon()])
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Deputy"))
    self.resolve_until_done()

    self.assertFalse(self.state.tradables)
    self.assertNotIn("Deputy", [c.name for c in self.state.specials])

    self.state.event_stack.append(Devoured(self.char))
    self.resolve_until_done()

    self.assertEqual(len(self.state.tradables), 2)
    self.assertIn("Deputy", [c.name for c in self.state.specials])


class WagonTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.deputy.PatrolWagon())
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

  def testNoopIsSameAsCancel(self):
    self.char.place = self.state.places["Square"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.state.event_stack.append(self.state.usables[0]["Patrol Wagon"])
    choice = self.resolve_to_choice(PlaceChoice)
    choice.resolve(self.state, "Square")
    self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.place.name, "Square")
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
    spend_choice.resolve(self.state, "Find Gate0")
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
    spend_choice.resolve(self.state, "Find Gate0")
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
    spend_choice.resolve(self.state, "Find Gate0")
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

  def testCanCastAfterForceMovementToAnotherWorld(self):
    monster = self.add_monsters(monsters.DreamFlier())
    monster.place = self.state.places["Uptown"]
    self.char.place = self.state.places["Uptown"]
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    # Fail the combat check against the monster. It will pull the player into the gate, where they
    # should have the option to immediately cast Find Gate.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      find_gate = self.resolve_to_usable(0, "Find Gate0", events.CastSpell)
    self.state.event_stack.append(find_gate)
    cast_choice = self.resolve_to_choice(SpendMixin)
    self.spend("sanity", 1, cast_choice)
    cast_choice.resolve(self.state, "Find Gate0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Woods")
    self.assertTrue(self.char.explored)

  def testDeclineToCastAfterForceMovement(self):
    monster = self.add_monsters(monsters.DreamFlier())
    monster.place = self.state.places["Uptown"]
    self.char.place = self.state.places["Uptown"]
    self.state.event_stack.append(Movement(self.char))
    choice = self.resolve_to_choice(CityMovement)
    choice.resolve(self.state, "done")
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_usable(0, "Find Gate0", events.CastSpell)  # Get pulled through gate
    self.state.done_using[0] = True
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Pluto1")


class FleshWardTest(EventTest):
  def setUp(self):
    super().setUp()
    self.flesh_ward = items.FleshWard(0)
    self.char.possessions.append(self.flesh_ward)
    self.char.possessions.append(items.TommyGun(0))

  def testCombat(self):
    monster = self.add_monsters(monsters.Cultist())
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
    self.assertListEqual(choice.choices, ["Flesh Ward0", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Flesh Ward0")
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
    monster = self.add_monsters(monsters.Cultist())
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
    self.assertListEqual(choice.choices, ["Flesh Ward0", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Flesh Ward0")
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
    monster = self.add_monsters(monsters.GiantWorm())
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
    self.assertListEqual(choice.choices, ["Flesh Ward0", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Flesh Ward0")
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
    self.assertListEqual(choice.choices, ["Flesh Ward0", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Flesh Ward0")
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
    self.assertListEqual(choice.choices, ["Flesh Ward0", "Cancel"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.spend("sanity", 1, choice)
      choice.resolve(self.state, "Flesh Ward0")
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    # -1 from the spell, -1 from the Loss()
    self.assertEqual(self.char.sanity, 3)

  def testNotUsableAfterDamageReduced(self):
    self.char.possessions.append(items.ObsidianStatue(0))
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    self.state.event_stack.append(Loss(self.char, {"stamina": 1}))
    self.resolve_to_usable(0, "Flesh Ward0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Obsidian Statue0"])
    self.resolve_until_done()
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
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Heal0", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Heal0")
    with mock.patch.object(
      events.random, "randint", new=mock.MagicMock(side_effect=[5, 1, 1, 1, 1, 1, 1])
    ):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy"])
    choice.resolve(self.state, "Dummy")
    self.resolve_to_choice(events.SliderInput)

    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testHealCapped(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Heal0", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Heal0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy"])
    choice.resolve(self.state, "Dummy")
    self.resolve_to_choice(events.SliderInput)

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testHealFailCast(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Heal0", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Heal0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_choice(events.SliderInput)

    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testMultipleOptions(self):
    all_chars = characters.CreateCharacters(set())
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

    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Heal0", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Heal0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Nun"])
    choice.resolve(self.state, "Nun")
    self.resolve_to_choice(events.SliderInput)

    self.assertEqual(nun.stamina, 3)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testCanOnlyCastDuringOwnUpkeep(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.char.place
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)
    buddy.stamina = 1

    sliders = events.SliderInput(buddy)
    self.state.event_stack.append(sliders)
    self.resolve_to_choice(events.SliderInput)
    self.assertFalse(self.state.usables)

  def testDeclineToUse(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Heal0", CastSpell)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testCastAndGoInsane(self):
    self.char.sanity = 1
    self.char.stamina = 1
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Heal0", CastSpell)

    self.state.event_stack.append(self.state.usables[0]["Heal0"])
    choice = self.resolve_to_choice(SpendMixin)
    self.assertEqual(choice.choices, ["Heal0", "Cancel"])
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Heal0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Dummy")
    lose_items = self.resolve_to_choice(events.ItemLossChoice)
    lose_items.resolve(self.state, "done")
    self.resolve_until_done()

    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 1)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.place.name, "Asylum")


class VoiceTest(EventTest):
  def setUp(self):
    super().setUp()
    self.state.turn_phase = "upkeep"
    self.voice = items.Voice(0)
    self.char.possessions.append(self.voice)

  def testCastSuccess(self):
    self.state.event_stack.append(events.SliderInput(self.char))
    voice = self.resolve_to_usable(0, "Voice0", CastSpell)
    self.state.event_stack.append(voice)
    cast = self.resolve_to_choice(CardSpendChoice)
    self.spend("sanity", 1, cast)
    cast.resolve(self.state, "Voice0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      sliders = self.resolve_to_choice(SliderInput)

    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.sanity, 4)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

    # Validate that this applies to checks.
    self.state.event_stack.append(Check(self.char, "fight", 0))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)

    # Also validate that it does not apply to movement points.
    self.state.turn_phase = "movement"
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_choice(CityMovement)
    self.assertEqual(self.char.movement_points, 4)

  def testCastFailure(self):
    self.state.event_stack.append(events.SliderInput(self.char))
    voice = self.resolve_to_usable(0, "Voice0", CastSpell)
    self.state.event_stack.append(voice)
    cast = self.resolve_to_choice(CardSpendChoice)
    self.spend("sanity", 1, cast)
    cast.resolve(self.state, "Voice0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      sliders = self.resolve_to_choice(SliderInput)

    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.sanity, 4)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

    self.state.event_stack.append(Check(self.char, "fight", 0))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)

  def testDeactivatesAtEndOfTurn(self):
    self.char.place = self.state.places["Easttown"]
    self.state.event_stack.append(events.SliderInput(self.char))
    voice = self.resolve_to_usable(0, "Voice0", CastSpell)
    self.state.event_stack.append(voice)
    cast = self.resolve_to_choice(CardSpendChoice)
    self.spend("sanity", 1, cast)
    cast.resolve(self.state, "Voice0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      sliders = self.resolve_to_choice(SliderInput)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

    self.advance_turn(0, "mythos")
    self.assertTrue(self.char.possessions[0].exhausted)
    self.advance_turn(1, "upkeep")
    self.assertTrue(self.char.possessions[0].exhausted)  # Still exhausted - has not refreshed

    # Should now be usable again, since we refreshed it during upkeep.
    voice = self.resolve_to_usable(0, "Voice0", CastSpell)
    self.assertFalse(self.char.possessions[0].exhausted)

  def testStaysActiveAfterCombat(self):
    self.state.event_stack.append(events.SliderInput(self.char))
    voice = self.resolve_to_usable(0, "Voice0", CastSpell)
    self.state.event_stack.append(voice)
    cast = self.resolve_to_choice(CardSpendChoice)
    self.spend("sanity", 1, cast)
    cast.resolve(self.state, "Voice0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      sliders = self.resolve_to_choice(SliderInput)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

    cultist = self.add_monsters(monsters.Cultist())
    self.state.event_stack.append(Combat(self.char, cultist))
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertTrue(self.char.possessions[0].exhausted)

  def testDeclineToUse(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Voice0", CastSpell)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testStaysActiveAfterNoMoreSpell(self):
    self.state.event_stack.append(events.SliderInput(self.char))
    voice = self.resolve_to_usable(0, "Voice0", CastSpell)
    self.state.event_stack.append(voice)
    cast = self.resolve_to_choice(CardSpendChoice)
    self.spend("sanity", 1, cast)
    cast.resolve(self.state, "Voice0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      sliders = self.resolve_to_choice(SliderInput)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.voice]))
    self.resolve_until_done()

    self.state.event_stack.append(Check(self.char, "fight", 0))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)


class PhysicianTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Uptown"]
    self.char.possessions.append(abilities.Physician())
    self.char.stamina = 3
    self.state.turn_phase = "upkeep"

  def testPhysician(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Physician", Sequence)

    self.state.event_stack.append(self.state.usables[0]["Physician"])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Cancel"])
    choice.resolve(self.state, "Dummy")
    self.resolve_to_choice(SliderInput)

    self.assertEqual(self.char.stamina, 4)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testCancelUse(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Physician", Sequence)

    self.state.event_stack.append(self.state.usables[0]["Physician"])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Cancel"])
    choice.resolve(self.state, "Cancel")
    self.resolve_to_choice(SliderInput)

    self.assertEqual(self.char.stamina, 3)
    self.assertFalse(self.char.possessions[0].exhausted)
    self.assertIn(0, self.state.usables)
    self.assertIn("Physician", self.state.usables[0])
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testMultipleOptions(self):
    nun = characters.CreateCharacters(set())["Nun"]
    nun.stamina = 1
    nun.place = self.char.place
    self.state.all_characters["Nun"] = nun
    self.state.characters.append(nun)

    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Physician", Sequence)

    self.state.event_stack.append(self.state.usables[0]["Physician"])
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choice.choices, ["Dummy", "Nun", "Cancel"])
    choice.resolve(self.state, "Nun")
    self.resolve_to_choice(SliderInput)

    self.assertEqual(nun.stamina, 2)
    self.assertEqual(self.char.stamina, 3)
    self.assertTrue(self.char.possessions[0].exhausted)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testDeclineToUse(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Physician", Sequence)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()


class ExtraDrawTest(EventTest):
  def testOtherDecksNotAffected(self):
    self.char.possessions.append(abilities.Studious())
    self.state.skills.extend([skills.Marksman(0), skills.Bravery(0)])
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
      [item.handle for item in self.char.possessions], ["Shrewd Dealer", "Cross0", "Food0"]
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
    self.state.unique.extend(
      [items.HolyWater(0), items.MagicLamp(0), items.MagicPowder(0), items.SwordOfGlory(1)]
    )
    self.state.event_stack.append(Purchase(self.char, "unique", 3, keep_count=1))

    choice = self.resolve_to_choice(CardSpendChoice)
    self.assertEqual(
      choice.choices, ["Holy Water", "Magic Lamp", "Magic Powder", "Sword of Glory", "Nothing"]
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
    self.state.places["Easttown"].encounters.extend(
      [
        EncounterCard("Easttown2", {"Diner": encounters.Diner2}),
        EncounterCard("Easttown3", {"Diner": encounters.Store7}),
      ]
    )
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
    self.state.gate_cards.extend(
      [
        GateCard("Gate10", {"red"}, {"Other": gate_encounters.Other10}),
        GateCard("Gate00", {"yellow"}, {"Other": gate_encounters.Dreamlands10}),
        GateCard("Gate16", {"green"}, {"Other": gate_encounters.Plateau16}),
      ]
    )
    choice = self.resolve_to_choice(CardChoice)
    # Gate00 is not a choice - wrong color
    self.assertCountEqual(choice.choices, ["Gate10", "Gate16"])
    choice.resolve(self.state, "Gate16")
    self.resolve_until_done()


class PreventionTest(EventTest):
  def testPreventStaminaLoss(self):
    self.char.possessions.append(abilities.StrongBody())
    self.char.possessions.append(items.TommyGun(0))
    beast = self.add_monsters(monsters.FurryBeast())
    combat = EvadeOrCombat(self.char, beast)
    self.state.event_stack.append(combat)

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    # Fail the horror check
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.sanity, 3)  # No reduction of sanity loss.
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Tommy Gun0"])

    # Fail the combat check. It does 4 damage, so we should take 3 damage.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 2)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Tommy Gun0"])

    # Defeat the monster. It is overwhelming.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)  # Should not take any loss from overwhelming.

  def testPreventSanityLoss(self):
    self.char.possessions.append(abilities.StrongMind())
    self.char.possessions.append(items.TommyGun(0))
    beast = self.add_monsters(monsters.FurryBeast())
    combat = EvadeOrCombat(self.char, beast)
    self.state.event_stack.append(combat)

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    # Fail the horror check. 2 sanity damage.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.sanity, 4)  # Reduction of sanity loss to 1 damage.
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Tommy Gun0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)  # Stamina loss from overwhelming.

  def testSanityLossDoesntApplyToSpells(self):
    self.char.fight_will_slider = 2
    self.char.possessions.append(abilities.StrongMind())
    self.char.possessions.extend([items.TommyGun(0), items.EnchantWeapon(0)])
    beast = self.add_monsters(monsters.FurryBeast())
    combat = EvadeOrCombat(self.char, beast)
    self.state.event_stack.append(combat)

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.sanity, 5)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, enchant)
    self.choose_items(enchant, ["Tommy Gun0"])
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Tommy Gun0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 4)  # Spent on the enchant weapon cast.


class GuardianTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(abilities.GuardianAngel())
    self.char.place = self.state.places["Dreamlands1"]
    self.char.sanity = 3
    self.char.stamina = 3

  def testSanityLost(self):
    self.state.event_stack.append(Loss(self.char, {"sanity": 5}))
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertIsNone(self.char.delayed_until)

  def testStaminaLost(self):
    self.state.event_stack.append(Loss(self.char, {"stamina": 5}))
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Hospital")
    self.assertIsNone(self.char.delayed_until)

  def testGenericLost(self):
    self.state.event_stack.append(LostInTimeAndSpace(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Church")
    self.assertIsNone(self.char.delayed_until)


class HunchesTest(EventTest):
  def testAddsBonusDieToAnyCheck(self):
    self.char.possessions.append(abilities.Hunches())
    self.char.clues = 2

    self.state.event_stack.append(Check(self.char, "will", 1))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      choice = self.resolve_to_choice(SpendChoice)
      self.assertEqual(rand.call_count, 2)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)

  def testStacksWithOtherSkills(self):
    self.char.possessions.append(abilities.Hunches())
    self.char.possessions.append(skills.Speed(0))
    self.char.clues = 2

    self.state.event_stack.append(Check(self.char, "speed", 1))
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("clues", 1, choice)
    choice.resolve(self.state, "Spend")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      choice = self.resolve_to_choice(SpendChoice)
      self.assertEqual(rand.call_count, 3)
    choice.resolve(self.state, "Pass")


class MistsTest(EventTest):
  def setUp(self):
    super().setUp()
    self.mists = items.Mists(0)
    self.char.possessions.append(self.mists)

  def testCombatEvade(self):
    monster = self.add_monsters(monsters.Cultist())
    self.state.event_stack.append(EvadeOrCombat(self.char, monster))
    evade_choice = self.resolve_to_choice(MultipleChoice)
    evade_choice.resolve(self.state, "Evade")
    self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Mists0"])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Mists0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testDeclineToCast(self):
    self.char.clues = 1
    monster = self.add_monsters(monsters.Zombie())
    self.state.event_stack.append(EvadeOrCombat(self.char, monster))
    evade_choice = self.resolve_to_choice(MultipleChoice)
    evade_choice.resolve(self.state, "Evade")
    self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.done_using[0] = True
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      spend_clues = self.resolve_to_choice(SpendChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Mists0", self.state.usables[0])
    spend_clues.resolve(self.state, "Pass")
    self.resolve_until_done()

  def testFailToCast(self):
    monster = self.add_monsters(monsters.Cultist())
    self.state.event_stack.append(EvadeOrCombat(self.char, monster))
    evade_choice = self.resolve_to_choice(MultipleChoice)
    evade_choice.resolve(self.state, "Evade")
    self.resolve_to_usable(0, "Mists0", events.CastSpell)
    self.state.event_stack.append(self.state.usables[0]["Mists0"])
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Mists0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.resolve_to_choice(MultipleChoice)
      self.assertFalse(self.state.usables)
      self.assertTrue(self.mists.exhausted)

  def testCastAfterFail(self):
    monster = self.add_monsters(monsters.Cultist())
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
    choice.resolve(self.state, "Mists0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      spend_choice = self.resolve_to_choice(SpendChoice)
      self.assertIsInstance(self.state.event_stack[-2], Check)
      self.assertEqual(self.state.event_stack[-2].check_type, "spell")
    spend_choice.resolve(self.state, "Pass")
    self.resolve_until_done()

  # TODO: test Elusive monsters


class SpendingOutputTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.ResearchMaterials(0))
    self.char.clues = 2
    self.char.trophies.append(self.state.gates.popleft())

  def testSpendableItemOutput(self):
    spend = values.RangeSpendPrerequisite("clues", 1, 6)
    choice = SpendChoice(self.char, "choose", ["Yes", "No"], spends=[spend, None])
    self.state.event_stack.append(choice)

    started = False
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      if data["choice"] is not None and data["spendables"]:
        started = True
      if started:
        self.assertIsNotNone(data["choice"])
        self.assertEqual(data["choice"]["spendable"], ["clues"])
        self.assertIn("Research Materials0", data["spendables"])
    self.assertTrue(started, "research materials should be spendable")

    loop = self.state.handle(0, {"type": "spend", "spend_type": "clues"})
    for _ in loop:
      data = self.state.for_player(0)
      self.assertIsNotNone(data["choice"])
      self.assertEqual(data["choice"]["spendable"], ["clues"])
      self.assertIsNotNone(data["spendables"])
      self.assertIn("Research Materials0", data["spendables"])

    loop = self.state.handle(0, {"type": "use", "handle": "Research Materials0"})
    for _ in loop:
      data = self.state.for_player(0)
      self.assertIsNotNone(data["choice"])
      self.assertEqual(data["choice"]["spendable"], ["clues"])
      self.assertIsNotNone(data["spendables"])
      self.assertIn("Research Materials0", data["spendables"])

    loop = self.state.handle(0, {"type": "use", "handle": "Research Materials0"})
    for _ in loop:
      data = self.state.for_player(0)
      self.assertIsNotNone(data["choice"])
      self.assertEqual(data["choice"]["spendable"], ["clues"])
      self.assertIsNotNone(data["spendables"])
      self.assertIn("Research Materials0", data["spendables"])


class GetStatModifierTest(EventTest):
  def setUp(self):
    super().setUp()
    self.state.allies.append(allies.Dog())
    self.state.specials.append(specials.StaminaDecrease(0))
    self.state.specials.append(specials.SanityDecrease(0))

  def testGainStats(self):
    self.char.sanity = 4
    self.state.event_stack.append(DrawSpecific(self.char, "allies", "Dog"))
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.max_sanity(self.state), 6)

  def testGainAtMax(self):
    self.char.sanity = 5
    self.state.event_stack.append(Draw(self.char, "allies", 1))
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.sanity, 6)
    self.assertEqual(self.char.max_sanity(self.state), 6)

  def testLoseStats(self):
    self.char.stamina = 3
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Stamina Decrease"))
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.max_stamina(self.state), 4)

  def testLoseStatsAtMax(self):
    self.char.sanity = 5
    self.state.event_stack.append(DrawSpecific(self.char, "specials", "Sanity Decrease"))
    self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.max_sanity(self.state), 4)


class StatIncreaserTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(allies.Dog())

  def testUsableInUpkeep(self):
    self.state.turn_phase = "upkeep"
    self.state.event_stack.append(Upkeep(self.char))
    sliders = self.resolve_to_choice(SliderInput)
    self.assertIn("Dog", self.state.usables[0])
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testNotUsableInUpkeepIfTurnIsLost(self):
    self.state.turn_phase = "upkeep"
    self.char.lose_turn_until = self.state.turn_number + 3
    self.state.event_stack.append(Upkeep(self.char))
    self.resolve_until_done()

  def testUsableDuringCityMovement(self):
    self.state.turn_phase = "movement"
    self.state.event_stack.append(Movement(self.char))
    move = self.resolve_to_choice(CityMovement)
    self.assertIn("Dog", self.state.usables[0])
    move.resolve(self.state, "done")
    self.resolve_until_done()

  def testNotUsableWhenDelayed(self):  # FAQ page 5
    self.state.turn_phase = "movement"
    self.char.delayed_until = self.state.turn_number + 3
    self.state.event_stack.append(Movement(self.char))
    self.resolve_until_done()

  def testUsableMovingInOtherWorld(self):
    self.state.turn_phase = "movement"
    self.char.place = self.state.places["City1"]
    self.state.event_stack.append(Movement(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.state.done_using[0] = True
    self.resolve_until_done()

  def testUsableReturningFromOtherWorld(self):
    self.state.turn_phase = "movement"
    self.state.places["Isle"].gate = next(gate for gate in self.state.gates if gate.name == "City")
    self.char.place = self.state.places["City2"]
    self.state.event_stack.append(Movement(self.char))
    ret = self.resolve_to_choice(GateChoice)
    self.assertIn("Dog", self.state.usables[0])
    ret.resolve(self.state, "Isle")
    self.resolve_until_done()

  def testUsableBeforeEncounter(self):
    self.state.turn_phase = "encounter"
    self.state.event_stack.append(EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], DrawEncounter)
    self.state.done_using[0] = True
    self.resolve_until_done()

  def testUsableBeforeTravel(self):
    self.state.turn_phase = "encounter"
    self.state.places["Isle"].gate = next(gate for gate in self.state.gates if gate.name == "City")
    self.char.place = self.state.places["Isle"]
    self.state.event_stack.append(EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], Travel)
    self.state.done_using[0] = True
    self.resolve_until_done()

  def testNotUsableBeforeTravelInEncounter(self):
    self.state.turn_phase = "encounter"
    card = EncounterCard("Uptown6", {"Woods": encounters.Woods6})
    self.state.places["Uptown"].encounters.append(card)
    self.char.place = self.state.places["Woods"]
    self.state.event_stack.append(EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], DrawEncounter)
    self.state.done_using[0] = True
    self.resolve_until_done()

  def testUsableLocationSpecialChoice(self):
    facilities = location_specials.CreateFixedEncounters()
    for location_name, fixed_encounters in facilities.items():
      self.state.places[location_name].fixed_encounters.extend(fixed_encounters)

    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["Science"]
    self.state.event_stack.append(EncounterPhase(self.char))
    pick = self.resolve_to_choice(CardChoice)
    self.assertIn("Dog", self.state.usables[0])
    pick.resolve(self.state, "University Card")
    self.resolve_until_done()

  def testNotUsableInNestedEncounter(self):
    self.state.turn_phase = "encounter"
    card = EncounterCard("Southside1", {"Society": encounters.Society1})
    self.state.places["Southside"].encounters.append(card)
    self.char.place = self.state.places["Society"]
    self.state.event_stack.append(EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], DrawEncounter)
    self.state.done_using[0] = True
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()

  def testUsableBeforeClosingGate(self):
    self.state.turn_phase = "encounter"
    self.state.places["Isle"].gate = next(gate for gate in self.state.gates if gate.name == "City")
    self.char.place = self.state.places["Isle"]
    self.char.explored = True
    self.state.event_stack.append(EncounterPhase(self.char))
    choice = self.resolve_to_choice(MultipleChoice)
    self.assertIn("Dog", self.state.usables[0])
    choice.resolve(self.state, choice.choices[2])
    self.resolve_until_done()

  def testUsableBeforeGateEncounter(self):
    self.state.turn_phase = "otherworld"
    card = GateCard("Gate1", {"green"}, {"Other": gate_encounters.Pluto48})
    self.state.gate_cards.append(card)
    self.char.place = self.state.places["City1"]
    self.state.event_stack.append(OtherWorldPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], GateEncounter)
    self.state.done_using[0] = True
    self.resolve_until_done()

  def testUsableOnlyOnceDrawingTwoGateEncounters(self):
    self.state.turn_phase = "otherworld"
    for i in range(2):
      card = GateCard(f"Gate{i}", {"green"}, {"Other": gate_encounters.Pluto48})
      self.state.gate_cards.append(card)
    self.char.place = self.state.places["City1"]
    self.char.possessions.append(abilities.PsychicSensitivity())
    self.state.event_stack.append(OtherWorldPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], GateEncounter)
    self.state.done_using[0] = True
    choice = self.resolve_to_choice(CardChoice)
    self.assertEqual(self.state.usables, {})
    choice.resolve(self.state, choice.choices[0])
    self.resolve_until_done()

  def testUsableBeforeMythos(self):
    self.state.turn_phase = "mythos"
    self.state.mythos.append(NoMythos())
    self.state.event_stack.append(Mythos(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], DrawMythosCard)
    self.state.done_using[0] = True
    self.resolve_until_done()

  def testNotUsableOtherMythosCardDraw(self):
    self.state.turn_phase = "encounter"
    self.state.mythos.append(mythos.Mythos1())
    self.char.place = self.state.places["Shop"]
    card = EncounterCard("Northside7", {"Shop": encounters.Shop7})
    self.state.places["Northside"].encounters.append(card)
    self.state.event_stack.append(EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], DrawEncounter)
    self.state.done_using[0] = True
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()

  def testUsableWhileFightingMonsters(self):
    self.state.turn_phase = "movement"
    for mon in self.state.monsters:
      mon.place = self.state.places["Isle"]
    self.char.place = self.state.places["Isle"]
    self.state.event_stack.append(Movement(self.char))
    move = self.resolve_to_choice(CityMovement)
    move.resolve(self.state, "done")
    choice = self.resolve_to_choice(MonsterChoice)
    self.assertIn("Dog", self.state.usables[0])
    choice.resolve(self.state, choice.monsters[0].handle)

    fight = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertIn("Dog", self.state.usables[0])
    fight.resolve(self.state, "Fight")
    fight = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertIn("Dog", self.state.usables[0])
    fight.resolve(self.state, "Fight")

    combat = self.resolve_to_choice(CombatChoice)
    self.assertIn("Dog", self.state.usables[0])
    self.choose_items(combat, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(MonsterChoice)
    self.assertIn("Dog", self.state.usables[0])

  def testNotUsableWhileFightingMonsterInEncounter(self):
    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["Roadhouse"]
    card = EncounterCard("Easttown5", {"Roadhouse": encounters.Roadhouse5})
    self.state.places["Easttown"].encounters.append(card)
    self.state.event_stack.append(EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dog", Sequence)
    self.assertIsInstance(self.state.event_stack[-1], DrawEncounter)
    self.state.done_using[0] = True
    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.state.usables, {})


if __name__ == "__main__":
  unittest.main()
