#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import events
from eldritch.events import *
from eldritch import items
from eldritch import monsters
from eldritch import mythos
from eldritch.test_events import EventTest


class CombatTest(EventTest):

  def testCombatFight(self):
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.fight(self.state), 1)
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
    self.assertEqual(self.char.sneak(self.state), 4)
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
    self.assertEqual(self.char.fight(self.state), 4)
    self.assertEqual(self.char.will(self.state), 1)
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
    self.assertEqual(self.char.fight(self.state), 1)
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
    self.assertEqual(self.char.will(self.state), 1)
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
    self.assertEqual(self.char.will(self.state), 1)
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
    self.assertEqual(self.char.will(self.state), 1)
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
    self.assertEqual(self.char.fight(self.state), 1)
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
    self.assertEqual(self.char.sneak(self.state), 1)
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


class CombatWithItems(EventTest):

  def setUp(self):
    super(CombatWithItems, self).setUp()
    self.char.possessions.extend([items.TommyGun(), items.Wither(), items.Revolver38()])
    cultist = monsters.Cultist()
    self.combat = Combat(self.char, cultist)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

  def testCombatWithWeapon(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    # Fight (4) + tommy gun (6) + cultist (1)
    self.assertEqual(len(self.combat.combat.check.roll), 11)
    self.assertFalse(self.char.possessions[0].active)

  def testCombatWithSpell(self):
    self.resolve_to_choice(CombatChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn(1, self.state.usables[0])

    # Cast the spell.
    self.state.event_stack.append(self.state.usables[0][1])

    # After casting the spell, we should return to our combat choice.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(len(self.combat.combat.check.roll), 8)  # Fight (4) + wither (3) + cultist (1)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testCombatWithSpellAndWeapon(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)

    # Cannot choose the spell - it must be used as a usable.
    with self.assertRaises(AssertionError):
      choose_weapons.resolve(self.state, [1])

    self.state.event_stack.append(self.state.usables[0][1])  # Cast the spell.

    # After casting the spell, we should return to our combat choice.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    # Cannot choose the spell after using it.
    with self.assertRaises(AssertionError):
      choose_weapons.resolve(self.state, [1])

    self.assertEqual(self.char.hands_available(), 1)
    # Cannot choose a two-handed weapon when one hand is taken by a spell.
    with self.assertRaises(AssertionError):
      choose_weapons.resolve(self.state, [0])

    choose_weapons.resolve(self.state, [2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    # Fight (4) + wither (3) + revolver (3) + cultist (1)
    self.assertEqual(len(self.combat.combat.check.roll), 11)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testCombatWithFailedSpell(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0][1])

    # Fail to cast the spell - it should not be active, but it will still take hands.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    # Cannot choose a two-handed weapon when one hand is taken by a failed spell.
    with self.assertRaises(AssertionError):
      choose_weapons.resolve(self.state, [0])

    choose_weapons.resolve(self.state, [2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    # Fight (4) + revolver (3) + cultist (1)
    self.assertEqual(len(self.combat.combat.check.roll), 8)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testMultiRoundCombatWithSpell(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0][1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    choose_weapons.resolve(self.state, [2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertFalse(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[1].in_use)
    self.assertTrue(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    # Fight (4) + wither (3) + revolver (3) + cultist (1)
    self.assertEqual(len(self.combat.combat.check.roll), 11)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testMultiRoundCombatDeactivateSpell(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0][1])

    # Fail to cast the spell
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    self.assertFalse(self.state.usables)  # The spell should not be usable anymore.
    choose_weapons.resolve(self.state, [])

    # Fail the combat check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertFalse(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn(1, self.state.usables[0])

    self.state.event_stack.append(self.state.usables[0][1])
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 2)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    # Fight (4) + tommy gun (6) + cultist (1)
    self.assertEqual(len(self.combat.combat.check.roll), 11)
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testUnconsciousDeactivatesSpells(self):
    self.char.stamina = 1
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0][1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    self.assertTrue(self.char.possessions[1].active)
    choose_weapons.resolve(self.state, [])

    # Fail the combat check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Hospital")
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testInsaneBeforeCombat(self):
    self.char.possessions[1] = items.Shrivelling()
    self.char.sanity = 1

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0][1])

    # Attempting to spend your last sanity to cast this spell makes you go insane before combat.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Asylum")
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)

  def testNeedSanityToCast(self):
    self.char.possessions[1] = items.DreadCurse()
    self.char.sanity = 1

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.state.usables)

  def testDontNeedSanityToDeactivate(self):
    self.char.possessions[1] = items.DreadCurse()
    self.char.sanity = 3

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0][1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.hands_available(), 0)
    self.assertFalse(self.state.usables)
    choose_weapons.resolve(self.state, [])

    # Fail the combat check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    self.assertIn(0, self.state.usables)
    self.assertIn(1, self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0][1])

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    self.assertFalse(self.state.usables)

    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)


if __name__ == '__main__':
  unittest.main()
