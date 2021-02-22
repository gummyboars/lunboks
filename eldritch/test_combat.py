#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

import eldritch.events as events
from eldritch.events import *
import eldritch.items as items
import eldritch.monsters as monsters
import eldritch.mythos as mythos
from eldritch.test_events import EventTest


class CombatTest(EventTest):

  def testCombatFight(self):
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.fight, 1)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    self.assertIn("or flee", fight_or_flee.prompt())
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1])):
      self.resolve_until_done()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertIsNone(combat.combat.damage)
    self.assertTrue(combat.is_resolved())

  def testCombatFightThenFlee(self):
    self.char.fight_will_slider = 0
    self.char.speed_sneak_slider = 0
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sneak, 4)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_round = combat.combat
    evade_round = combat.evade
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(evade_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertIsNotNone(combat_round.damage)
    self.assertTrue(combat_round.damage.is_resolved())
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.stamina, 4)

    next_fight_or_flee.resolve(self.state, "Flee")
    next_combat_round = combat.combat
    next_evade_round = combat.evade

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertFalse(next_combat_round.is_resolved())
    self.assertTrue(next_evade_round.is_resolved())
    self.assertTrue(next_evade_round.evaded)
    self.assertIsNone(next_evade_round.damage)
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
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    self.assertIsNotNone(combat.horror)
    self.assertTrue(combat.horror.is_resolved())
    self.assertEqual(self.char.sanity, 4)

    combat_round = combat.combat
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    # Fail the combat check. After this, we check that there is not a second horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertIsNotNone(combat_round.damage)
    self.assertTrue(combat_round.damage.is_resolved())
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)  # Assert there wasn't a second horror check/loss.

    combat_round = combat.combat
    next_fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat_round.is_resolved())
    self.assertTrue(combat_round.defeated)
    self.assertIsNone(combat_round.damage)
    self.assertTrue(combat.is_resolved())

  def testCombatRoundWithGlobal(self):
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.fight, 1)
    maniac = monsters.Maniac()
    self.assertEqual(maniac.toughness(self.state), 1)

    combat_round = CombatRound(self.char, maniac)
    self.state.event_stack.append(combat_round)
    # Intentionally initialize environment after creating the event to make sure the event does
    # not cache old values of toughness/difficulty/damage.
    self.state.environment = mythos.Mythos45()
    self.assertEqual(maniac.toughness(self.state), 2)
    self.assertIsNone(maniac.difficulty("horror", self.state))

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    # Roll one success, but the maniac's toughness should be 2 because of the environment.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1])):
      self.resolve_until_done()

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertIsNotNone(combat_round.damage)


class CombatOrEvadeTest(EventTest):

  def testEvadeMeansNoHorror(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.will, 1)
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    choice = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(choice)

    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

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

    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")

    # While here, they will fail the horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(MultipleChoice)

    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 3)


class LoseCombatTest(EventTest):

  def testHorrorInsane(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.will, 1)
    self.char.sanity = 1
    zombie = monsters.Zombie()
    cultist = monsters.Cultist()
    seq = EvadeOrFightAll(self.char, [zombie, cultist])
    self.state.event_stack.append(seq)
    comb1 = seq.events[0]
    comb2 = seq.events[1]

    self.assertEqual(self.char.place.name, "Diner")

    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Fight")
    # Character auto-fails the horror check.
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertFalse(comb2.is_resolved())
    self.assertFalse(comb1.is_resolved())
    self.assertFalse(comb1.combat.is_resolved())

    self.assertEqual(self.char.place.name, "Asylum")

  def testCombatUnconscious(self):
    self.helpTestCombatUnconscious(2)

  def testCombatUnconsciousOverkilled(self):
    self.helpTestCombatUnconscious(1)

  def helpTestCombatUnconscious(self, starting_stamina):
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.fight, 1)
    self.char.stamina = starting_stamina
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    self.assertEqual(self.char.place.name, "Diner")
    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Fight")

    # Let them pass the horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 1)
    self.assertFalse(combat.is_resolved())

    self.assertEqual(self.char.place.name, "Hospital")

  def testMultiRoundUnconscious(self):
    self.char.stamina = 2
    self.assertEqual(self.char.sneak, 1)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    choice = self.resolve_to_choice(MultipleChoice)
    choice.resolve(self.state, "Flee")
    # Cultist has a sneak difficulty of -3, so they auto-fail the evade check.
    next_choice = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(self.char.stamina, 1)

    next_choice.resolve(self.state, "Flee")
    self.resolve_until_done()
    # They failed the next evade check, so they went unconscious.
    self.assertEqual(self.char.stamina, 1)
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.place.name, "Hospital")


if __name__ == '__main__':
  unittest.main()
