#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import assets
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
    self.assertEqual(maniac.toughness(self.state, self.char), 1)

    combat_round = CombatRound(self.char, maniac)
    self.state.event_stack.append(combat_round)
    # Intentionally initialize environment after creating the event to make sure the event does
    # not cache old values of toughness/difficulty/damage.
    self.state.environment = mythos.Mythos45()
    self.assertEqual(maniac.toughness(self.state, self.char), 2)
    self.assertIsNone(maniac.difficulty("horror", self.state, self.char))

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


class AmbushTest(EventTest):

  def testAmbush(self):
    ghoul = monsters.Ghoul()
    self.assertTrue(ghoul.has_attribute("ambush", self.state, self.char))
    combat = Combat(self.char, ghoul)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    # Should not be able to flee - it's an ambush monster.
    with self.assertRaises(AssertionError):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(self.char.stamina, 4)
    # Still should not be able to flee.
    with self.assertRaises(AssertionError):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")

  def testAmbushFromFailedEvade(self):
    ghoul = monsters.Ghoul()
    combat = EvadeOrCombat(self.char, ghoul)
    self.state.event_stack.append(combat)

    # Before you engage in combat, you may evade the ghoul.
    fight_or_evade = self.resolve_to_choice(MultipleChoice)
    fight_or_evade.resolve(self.state, "Evade")

    # Fail the evade check, validate that we go straight to the next combat round.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    with self.assertRaises(AssertionError):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")


class ResistanceAndImmunityTest(EventTest):

  def testMagicalResistance(self):
    self.char.possessions.extend([items.TommyGun(), items.EnchantedKnife(), items.EnchantedKnife()])
    witch = monsters.Witch()
    combat = Combat(self.char, witch)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1]) # choose a single enchanted knife
    self.assertEqual(self.char.fight(self.state), 4)
    self.assertEqual(witch.difficulty("combat", self.state, self.char), -3)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 3) # Fight of 4, -3 combat rating, +2 enchanted knife.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1, 2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      # Note that each knife gets its bonus of 3 cut in half and rounded up - they are calculated
      # separately as opposed to adding their bonuses together and then taking half.
      self.assertEqual(rand.call_count, 5) # Fight of 4, -3 combat rating, +2 per enchanted knife.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 7) # Fight of 4, -3 combat rating, +6 for tommy gun.

  def testMagicalImmunity(self):
    self.char.possessions.extend([items.Revolver38(), items.EnchantedKnife()])
    priest = monsters.HighPriest()
    combat = Combat(self.char, priest)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 2) # Fight of 4, -2 combat rating, +0 enchanted knife.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0, 1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      # Note that each knife gets its bonus of 3 cut in half and rounded up - they are calculated
      # separately as opposed to adding their bonuses together and then taking half.
      self.assertEqual(rand.call_count, 5) # Fight of 4, -2 combat rating, +3 revolver.

  def testOldProfessorNegatesMagicalResistance(self):
    self.char.possessions.extend([items.MagicLamp(), assets.OldProfessor()])
    witch = monsters.Witch()
    combat = Combat(self.char, witch)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6) # Fight of 4, -3 combat rating, +5 magic lamp.

  def testOldProfessorHasNoEffectOnMagicalImmunity(self):
    self.char.possessions.extend([items.MagicLamp(), assets.OldProfessor()])
    priest = monsters.HighPriest()
    combat = Combat(self.char, priest)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2) # Fight of 4, -2 combat rating, +0 magic lamp.

  def testPhysicalResistance(self):
    self.char.possessions.extend([items.Revolver38(), items.Revolver38(), items.EnchantedKnife()])
    vampire = monsters.Vampire()
    combat = Combat(self.char, vampire)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0, 1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 5) # Fight of 4, -3 combat rating, +2 per revolver.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1, 2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6) # Fight of 4, -3 combat rating, +3 knife, +2 revolver.

  def testPhysicalImmunity(self):
    self.char.possessions.extend([items.Revolver38(), items.Revolver38(), items.EnchantedKnife()])
    ghost = monsters.Ghost()
    combat = Combat(self.char, ghost)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0, 1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 1) # Fight of 4, -3 combat rating, +0 per revolver.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1, 2])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4) # Fight of 4, -3 combat rating, +3 knife, +0 revolver.

  def testPainterNegatesPhysicalResistance(self):
    self.char.possessions.extend([items.TommyGun(), assets.VisitingPainter()])
    vampire = monsters.Vampire()
    combat = Combat(self.char, vampire)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 7) # Fight of 4, -3 combat rating, +6 tommy gun.

  def testPainterHasNoEffectOnPhysicalImmunity(self):
    self.char.possessions.extend([items.TommyGun(), assets.VisitingPainter()])
    ghost = monsters.Ghost()
    combat = Combat(self.char, ghost)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 1) # Fight of 4, -3 combat rating, +0 tommy gun.


class NightmarishOverwhelmingTest(EventTest):

  def testOverwhelmingAndNightmarish(self):
    self.char.fight_will_slider = 0
    self.char.possessions.extend([items.EnchantedKnife(), items.EnchantedKnife()])
    flier = monsters.SubterraneanFlier()
    combat = Combat(self.char, flier)
    self.state.event_stack.append(combat)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.will(self.state), 4)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    # Take sanity loss from nightmarish.
    self.assertTrue(combat.horror.is_resolved())
    self.assertTrue(combat.horror.successes)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0, 1]) # I gotta say, this is pretty teriffic.

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # Take stamina loss from overwhelming.
    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 4)

  def testOverwhelmingOnSecondRound(self):
    self.char.possessions.extend([items.EnchantedKnife(), items.EnchantedKnife()])
    beast = monsters.FurryBeast()
    combat = Combat(self.char, beast)
    self.state.event_stack.append(combat)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0, 1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    self.assertFalse(combat.combat.is_resolved())
    self.assertFalse(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 1)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0, 1])

    # Reset stamina to avoid dealing with going unconscious
    self.char.stamina = 5
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 4)

  def testBraveGuyNegatesNightmarish(self):
    self.char.fight_will_slider = 0
    self.char.possessions.extend([items.MagicLamp(), assets.BraveGuy()])
    flier = monsters.SubterraneanFlier()
    combat = Combat(self.char, flier)
    self.state.event_stack.append(combat)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    # No sanity loss from nightmarish.
    self.assertTrue(combat.horror.is_resolved())
    self.assertTrue(combat.horror.successes)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # Still take stamina loss from overwhelming.
    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 4)

  def testToughGuyNegatesOverwhelming(self):
    self.char.possessions.extend([items.MagicLamp(), assets.ToughGuy()])
    beast = monsters.FurryBeast()
    combat = Combat(self.char, beast)
    self.state.event_stack.append(combat)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 5)


class UndeadTest(EventTest):

  def testUseCrossAgainstUndead(self):
    self.char.possessions.extend([items.Cross()])
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 3) # Fight 4, -1 combat rating

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6) # Fight 4, -1 combat rating, +3 cross

  def testUseCrossAgainstLiving(self):
    self.char.possessions.extend([items.Cross()])
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5) # Fight 4, +1 combat rating


class CombatWithEnchantedWeapon(EventTest):

  def setUp(self):
    super(CombatWithEnchantedWeapon, self).setUp()
    self.char.possessions.extend([items.DarkCloak(), items.Revolver38(), items.EnchantWeapon()])
    spawn = monsters.FormlessSpawn()
    self.combat = Combat(self.char, spawn)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

  def testSuccessfulCast(self):
    self.char.possessions.append(items.MagicLamp())
    choose_weapons = self.resolve_to_choice(CombatChoice)

    # Cannot choose either a spell or the dark cloak.
    with self.assertRaises(AssertionError):
      choose_weapons.resolve(self.state, [0])
    with self.assertRaises(AssertionError):
      choose_weapons.resolve(self.state, [2])

    self.assertCountEqual(self.state.usables[0].keys(), {2})
    self.state.event_stack.append(self.state.usables[0][2])  # Cast enchant weapon.

    # Before casting the spell, we should get a choice of items.
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)

    with self.assertRaises(AssertionError):
      choose_enchant.resolve(self.state, [0]) # Cannot choose dark cloak.
    with self.assertRaises(AssertionError):
      choose_enchant.resolve(self.state, [2]) # Cannot choose itself.
    with self.assertRaises(AssertionError):
      choose_enchant.resolve(self.state, [3]) # Cannot choose a magic weapon.
    choose_enchant.resolve(self.state, [1]) # Enchant the revolver.

    # Now that we've chosen, successfully cast the spell.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertTrue(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)  # Enchant weapon is handless.

    choose_weapons.resolve(self.state, [1]) # We already cast on the revolver, now choose to use it.

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5) # Fight (4) + spawn (-2) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testFailedToCast(self):
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      # Failed to cast the spell, so we should come back to the combat choice.
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)
    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2) # Fight (4) + spawn (-2) + 0 (physical immunity)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testAgainstMagicalImmunity(self):
    priest = monsters.HighPriest()
    self.combat = Combat(self.char, priest)
    self.state.event_stack.clear()
    self.state.event_stack.append(self.combat)
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    self.resolve_to_choice(CombatChoice)

    # Cast enchant weapon on the revolver. This is stupid, because you're fighting a monster
    # with magical immunity, and the revolver would be better used as a physical weapon. However,
    # it is a perfectly valid play, so we test that it correctly makes the revolver useless.
    self.state.event_stack.append(self.state.usables[0][2])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertTrue(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)

    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2) # Fight (4) + priest (-2) + 0 (magical immunity)

  def testNoValidWeapons(self):
    self.char.possessions[1] = items.EnchantWeapon()  # Replace the revolver.
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0][2])  # Cast enchant weapon.
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    with self.assertRaises(AssertionError):
      choose_enchant.resolve(self.state, [1])
    choose_enchant.resolve(self.state, [])

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)
    choose_weapons.resolve(self.state, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2) # Fight (4) + spawn (-2)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertFalse(self.char.possessions[2].exhausted)

  def testTwoCopies(self):
    self.char.possessions.extend([items.EnchantWeapon(), items.Revolver38()])
    self.resolve_to_choice(CombatChoice)

    # Both copies should be usable.
    self.assertCountEqual(self.state.usables[0].keys(), {2, 3})
    self.state.event_stack.append(self.state.usables[0][2])

    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    # Finish casting on the revolver.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    # Now, only the remaining copy should be usable.
    self.assertCountEqual(self.state.usables[0].keys(), {3})
    self.state.event_stack.append(self.state.usables[0][3])

    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    # Cannot choose the same item again - it is now magical.
    with self.assertRaises(AssertionError):
      choose_enchant.resolve(self.state, [1])
    choose_enchant.resolve(self.state, [4])

    # Cast on the other revolver.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    choose_weapons.resolve(self.state, [1, 4])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 8) # Fight (4) + spawn (-2) + revolvers (2*3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)
    self.assertFalse(self.char.possessions[3].active)
    self.assertFalse(self.char.possessions[3].in_use)
    self.assertTrue(self.char.possessions[3].exhausted)

  def testDeactivateEnchantWeapon(self):
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0][2])

    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    choose_weapons.resolve(self.state, [1])

    # Lose the first round of combat
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 5) # Fight (4) + spawn (-2) + revolver (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1])

    # Enchant weapon should still be active in the second round
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 5) # Fight (4) + spawn (-2) + revolver (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)

    # Deactivate enchant weapon
    self.assertCountEqual(self.state.usables[0].keys(), {2})
    self.state.event_stack.append(self.state.usables[0][2])

    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, [1])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2) # Fight (4) + spawn (-2) + revolver (0)

  def testGoInsaneWhileCastingEnchantWeapon(self):
    self.char.sanity = 1
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Asylum")
    self.assertFalse(self.combat.combat.is_resolved())

    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

    self.assertEqual(self.char.possessions[1].active_bonuses["magical"], 0)
    self.assertEqual(self.char.possessions[1].active_bonuses["physical"], 3)

  def testEnchantWeaponDeactivatesOnCombatLoss(self):
    self.char.stamina = 1
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    choose_weapons.resolve(self.state, [1])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Hospital")

    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

    self.assertEqual(self.char.possessions[1].active_bonuses["magical"], 0)
    self.assertEqual(self.char.possessions[1].active_bonuses["physical"], 3)

  def testCannotUseEnchantWeaponInNextCombat(self):
    self.char.sanity = 6  # Cheat to make sure they don't go insane
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertCountEqual(self.state.usables[0].keys(), {2})
    self.state.event_stack.append(self.state.usables[0][2])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    choose_weapons.resolve(self.state, [1])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5) # Fight (4) + spawn (-2) + revolver (3)

    self.state.event_stack.append(Combat(self.char, monsters.FormlessSpawn()))
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertNotIn(0, self.state.usables) # They have nothing they can use
    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2) # Fight (4) + spawn (-2) + physical immunity (0)


class CombatWithRedSignTest(EventTest):

  def setUp(self):
    super(CombatWithRedSignTest, self).setUp()
    self.char.possessions.extend([items.EnchantedKnife(), items.Revolver38(), items.RedSign()])

  def start(self, monster):
    self.combat = Combat(self.char, monster)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")

    return self.resolve_to_choice(CombatChoice)

  def testReducesToughness(self):
    vampire = monsters.Vampire()
    self.char.fight_will_slider = 0
    choose_weapons = self.start(vampire)
    self.assertEqual(vampire.toughness(self.state, self.char), 2)
    self.assertEqual(self.char.fight(self.state), 1)

    self.assertCountEqual(self.state.usables[0].keys(), {2})
    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["physical resistance", "undead", "none"])
    choose_ignore.resolve(self.state, "physical resistance")

    # Finish casting the spell.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(vampire.toughness(self.state, self.char), 1)
    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 1)  # Fight (1) + vampire (-3) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testNoValidChoices(self):
    land_squid = monsters.LandSquid()
    choose_weapons = self.start(land_squid)
    self.assertEqual(land_squid.toughness(self.state, self.char), 3)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["none"])
    choose_ignore.resolve(self.state, "none")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(land_squid.toughness(self.state, self.char), 2)
    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + squid (-3) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testToughnessCannotBeLessThanOne(self):
    giant_insect = monsters.GiantInsect()
    choose_weapons = self.start(giant_insect)
    self.assertEqual(giant_insect.toughness(self.state, self.char), 1)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["none"])
    choose_ignore.resolve(self.state, "none")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(giant_insect.toughness(self.state, self.char), 1)
    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 7)  # Fight (4) + insect 0 + revolver (3)

  def testIgnoresMagicalResistance(self):
    witch = monsters.Witch()
    choose_weapons = self.start(witch)
    self.assertEqual(witch.toughness(self.state, self.char), 1)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["magical resistance", "none"])
    choose_ignore.resolve(self.state, "magical resistance")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(witch.toughness(self.state, self.char), 1)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + witch (-3) + knife (3)

  def testCannotIgnoreMagicalImmunity(self):
    priest = monsters.HighPriest()
    choose_weapons = self.start(priest)
    self.assertEqual(priest.toughness(self.state, self.char), 2)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["none"])
    choose_ignore.resolve(self.state, "none")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(priest.toughness(self.state, self.char), 1)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + priest (-2) + knife (0)

  def testIgnoresOverwhelming(self):
    beast = monsters.FurryBeast()
    choose_weapons = self.start(beast)
    self.assertEqual(beast.toughness(self.state, self.char), 3)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["overwhelming", "none"])
    choose_ignore.resolve(self.state, "overwhelming")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(beast.toughness(self.state, self.char), 2)
    choose_weapons.resolve(self.state, [1])

    self.assertEqual(self.char.stamina, 5)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight (4) + beast (-2) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(self.char.stamina, 5)

  def testIgnoresAmbush(self):
    ghoul = monsters.Ghoul()
    self.char.speed_sneak_slider = 0
    self.combat = Combat(self.char, ghoul)
    self.state.event_stack.append(self.combat)
    fight_or_flee = self.resolve_to_choice(MultipleChoice)
    with self.assertRaises(AssertionError):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)

    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    # Cannot flee because of ambush.
    with self.assertRaises(AssertionError):
      fight_or_flee.resolve(self.state, "Flee")

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["ambush", "none"])
    choose_ignore.resolve(self.state, "ambush")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)

    # Now that we've successfully cast the spell to ignore ambush, we can flee.
    fight_or_flee.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertFalse(self.combat.combat.is_resolved())
    self.assertTrue(self.combat.evade.is_resolved())
    self.assertTrue(self.combat.evade.evaded)
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testIgnoresUndead(self):
    zombie = monsters.Zombie()
    self.char.possessions[1] = items.Cross()
    choose_weapons = self.start(zombie)
    self.assertEqual(zombie.toughness(self.state, self.char), 1)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["undead", "none"])
    choose_ignore.resolve(self.state, "undead")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(zombie.toughness(self.state, self.char), 1)
    choose_weapons.resolve(self.state, [1]) # Cross

    # The cross provides no bonus against the zombie because we are ignoring its undead attribute.
    # This is a dumb thing to do, but is still perfectly valid.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 3)  # Fight (4) + zombie (-1) + cross (0)

    self.assertTrue(self.combat.combat.is_resolved())

  def testTwoCopies(self):
    self.char.possessions.extend([items.RedSign(), items.Cross()])
    scary = monsters.Monster( # Nightmarish overwhelming monster with 3 toughness.
        "Scary", "normal", "moon", {"evade": 0, "horror": 0, "combat": 0},
        {"horror": 2, "combat": 2}, 3, None, {"horror": 1, "combat": 1},
    )
    self.state.event_stack.append(EvadeOrCombat(self.char, scary))

    fight_or_evade = self.resolve_to_choice(MultipleChoice)

    self.assertCountEqual(self.state.usables[0].keys(), {2, 3})
    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_ignore.choices, ["nightmarish", "overwhelming", "none"])
    choose_ignore.resolve(self.state, "nightmarish")

    # Cast the first one.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_evade = self.resolve_to_choice(MultipleChoice)

    self.assertEqual(scary.toughness(self.state, self.char), 2)
    fight_or_evade.resolve(self.state, "Fight")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertCountEqual(self.state.usables[0].keys(), {3})
    self.state.event_stack.append(self.state.usables[0][3])
    choose_ignore = self.resolve_to_choice(MultipleChoice)

    # Now that we're already ignoring nightmarish, it should not be an option.
    self.assertEqual(choose_ignore.choices, ["overwhelming", "none"])
    choose_ignore.resolve(self.state, "overwhelming")

    # Successfully cast the second one.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(scary.toughness(self.state, self.char), 1)

    choose_weapons.resolve(self.state, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + scary (-0)

    self.assertEqual(self.char.sanity, 3)  # Lost 1 per cast of red sign.
    self.assertEqual(self.char.stamina, 5)

  def testWithToughGuy(self):
    self.char.possessions.append(assets.ToughGuy()) # Ignores overwhelming
    self.char.fight_will_slider = 1
    self.assertEqual(self.char.will(self.state), 3)
    flier = monsters.SubterraneanFlier()

    # Pass the horror check, or you won't have enough sanity to cast.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.start(flier)
    self.assertEqual(flier.toughness(self.state, self.char), 3)
    self.assertEqual(self.char.sanity, 4)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    # Overwhelming should not be in the list because the tough guy already ignores it.
    self.assertEqual(choose_ignore.choices, ["nightmarish", "physical resistance", "none"])
    choose_ignore.resolve(self.state, "physical resistance")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(flier.toughness(self.state, self.char), 2)
    choose_weapons.resolve(self.state, [1])

    self.assertEqual(self.char.stamina, 5)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (2) + flier (-3) + revolver (3) + tough guy (2)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(self.char.stamina, 5)

  def testWithPainter(self):
    self.char.possessions.append(assets.VisitingPainter()) # Ignores physical resistance
    self.char.fight_will_slider = 1
    self.assertEqual(self.char.will(self.state), 3)
    flier = monsters.SubterraneanFlier()

    # Pass the horror check, or you won't have enough sanity to cast.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.start(flier)
    self.assertEqual(flier.toughness(self.state, self.char), 3)
    self.assertEqual(self.char.sanity, 4)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    # Overwhelming should not be in the list because the tough guy already ignores it.
    self.assertEqual(choose_ignore.choices, ["nightmarish", "overwhelming", "none"])
    choose_ignore.resolve(self.state, "overwhelming")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(flier.toughness(self.state, self.char), 2)
    choose_weapons.resolve(self.state, [1])

    self.assertEqual(self.char.stamina, 5)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (2) + flier (-3) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(self.char.stamina, 5)

  def testWithEnchantWeapon(self):
    self.char.possessions.append(items.EnchantWeapon())
    witch = monsters.Witch()
    choose_weapons = self.start(witch)

    # Because you're a genius, you're going to cast enchant weapon on the revolver, and then use
    # the red sign to ignore magical resistance. Pure genius.
    self.state.event_stack.append(self.state.usables[0][3])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    choose_enchant.resolve(self.state, [1])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    # Here's the red sign.
    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    choose_ignore.resolve(self.state, "magical resistance")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    choose_weapons.resolve(self.state, [1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + witch (-3) + revolver (3)

  def testDeactivate(self):
    witch = monsters.Witch()
    choose_weapons = self.start(witch)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    choose_ignore.resolve(self.state, "magical resistance")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    choose_weapons.resolve(self.state, [0])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(MultipleChoice)
      self.assertEqual(rand.call_count, 4)  # Fight (4) + witch (-3) + knife (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(self.char.hands_available(), 1)

    # Now, deactivate the spell and validate you have both hands available again.
    self.assertCountEqual(self.state.usables[0].keys(), {2})
    self.state.event_stack.append(self.state.usables[0][2])
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(self.char.hands_available(), 2)

    choose_weapons.resolve(self.state, [0, 1])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6)  # Fight (4) + witch (-3) + revolver (3) + knife (2)

  def testDeactivatesOnCombatLoss(self):
    self.char.stamina = 1
    witch = monsters.Witch()
    choose_weapons = self.start(witch)

    self.state.event_stack.append(self.state.usables[0][2])
    choose_ignore = self.resolve_to_choice(MultipleChoice)
    choose_ignore.resolve(self.state, "magical resistance")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertFalse(witch.has_attribute("magical resistance", self.state, self.char))
    choose_weapons.resolve(self.state, [0])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Hospital")

    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)
    # Techincally, you wouldn't call this again because the combat has ended. But it's a good
    # check to make sure that the effects of the spell are done.
    self.assertTrue(witch.has_attribute("magical resistance", self.state, self.char))


if __name__ == '__main__':
  unittest.main()
