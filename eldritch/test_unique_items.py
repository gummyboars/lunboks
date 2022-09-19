#!/usr/bin/env python3

import os
import sys
# import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import encounters
from eldritch import events
from eldritch import items
from eldritch import monsters
from eldritch.test_events import EventTest


class AncientTabletTest(EventTest):
  def setUp(self):
    super().setUp()
    self.tablet = items.AncientTablet(0)
    self.char.possessions = [self.tablet]
    self.advance_turn(0, "movement")
    self.state.spells.extend([items.spells.Wither(0), items.spells.FindGate(0)])

  def testNoSuccesses(self):
    self.assertIn(self.tablet, self.char.possessions)
    tablet = self.resolve_to_usable(0, "Ancient Tablet0")
    self.state.event_stack.append(tablet)
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[1, 1])):
      self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.clues, 4)
    self.assertNotIn(self.tablet, self.char.possessions)
    self.assertEqual(self.char.movement_points, 1)

  def testOneSuccess(self):
    tablet = self.resolve_to_usable(0, "Ancient Tablet0")
    self.state.event_stack.append(tablet)
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[1, 6])):
      self.resolve_to_choice(events.CityMovement)

    self.assertEqual(self.char.clues, 2)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Wither")
    self.assertEqual(self.char.movement_points, 1)

  def testTwoSuccesses(self):
    tablet = self.resolve_to_usable(0, "Ancient Tablet0")
    self.state.event_stack.append(tablet)
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 6])):
      self.resolve_to_choice(events.CityMovement)

    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, "Wither")
    self.assertEqual(self.char.possessions[1].name, "Find Gate")
    self.assertEqual(self.char.movement_points, 1)

  def testNotEnoughMovement(self):
    choice = self.resolve_to_choice(events.CityMovement)
    self.assertIn("Ancient Tablet0", self.state.usables.get(0, []))
    initial_choices = choice.choices
    self.state.event_stack.append(events.ChangeMovementPoints(self.char, -2))
    choice = self.resolve_to_choice(events.CityMovement)
    self.assertNotIn("Ancient Tablet0", self.state.usables.get(0, []))
    self.assertGreater(len(initial_choices), len(choice.choices))
    # with self.assertRaises(AssertionError):
    #   self.resolve_to_usable(0, "Ancient Tablet0")


class EnchantedJewelryTest(EventTest):
  def setUp(self):
    super().setUp()
    self.jewelry = items.EnchantedJewelry(0)
    self.char.possessions = [self.jewelry]

  def testSingleStamina(self):
    loss = events.Loss(self.char, {"stamina": 1})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.jewelry.tokens["stamina"], 1)
    self.assertEqual(self.char.stamina, 5)

  def testMultipleStaminaUnused(self):
    loss = events.Loss(self.char, {"stamina": 2})
    self.state.event_stack.append(loss)
    jewelry = self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(jewelry)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.done_using[0] = True
    self.resolve_until_done()
    self.assertEqual(self.jewelry.tokens["stamina"], 1)
    self.assertEqual(self.char.stamina, 4)

  def testMultipleStaminaUsed(self):
    loss = events.Loss(self.char, {"stamina": 2})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    print("appending Enchanted Jewelry")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.jewelry.tokens["stamina"], 2)
    self.assertEqual(self.char.stamina, 5)

  def testSingleStaminaMaxTokens(self):
    self.jewelry.tokens["stamina"] = 2
    loss = events.Loss(self.char, {"stamina": 1})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.jewelry, self.char.possessions)


class HealingStoneTest(EventTest):
  def setUp(self):
    super().setUp()
    self.stone = items.HealingStone(0)
    self.char.possessions = [self.stone]
    self.advance_turn(0, "upkeep")

  def testNotUsableWhenFull(self):
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    with self.assertRaises(AssertionError):
      self.resolve_to_usable(0, "Healing Stone0")

  def testNotUsableOutsideUpkeep(self):
    self.advance_turn(0, "movement")
    with self.assertRaises(AssertionError):
      self.resolve_to_usable(0, "Healing Stone0")

  def testSanityOnly(self):
    self.char.sanity = 3
    self.char.stamina = 5
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)

  def testStaminaOnly(self):
    self.char.sanity = 5
    self.char.stamina = 3
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 4)

  def testBothSanityAndStamina(self):
    self.char.sanity = 3
    self.char.stamina = 3
    upkeep = events.UpkeepActions(self.char)
    self.state.event_stack.append(upkeep)
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.assertEqual(choice.choices, ["1 Stamina", "1 Sanity"])
    choice.resolve(self.state, "1 Stamina")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 4)

  def testDiscardOnAwaken(self):
    self.assertIn(self.stone, self.char.possessions)
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.assertNotIn(self.stone, self.char.possessions)


class BlueWatcherTest(EventTest):
  def setUp(self):
    super().setUp()
    self.watcher = items.BlueWatcher(0)
    self.char.possessions = [self.watcher]

  def testPassCombatMonster(self):
    pass

  def testPassCombatEncounter(self):
    self.state.event_stack.append(encounters.Bank3(self.char))
    watcher = self.resolve_to_usable(0, "Blue Watcher0")

  def testPassFightClose(self):
    pass

  def testFightLoreClose(self):
    pass

  def testCantUseOnOtherFightOrLore(self):
    self.state.event_stack.append(encounters.Science2(self.char))
    with self.assertRaises(AssertionError):
      self.resolve_to_usable(0, "Blue Watcher0")

  def testNotEnoughStamina(self):
    self.char.stamina = 1
    self.state.event_stack.append(events.Combat(self.char, monsters.Cultist()))
    with self.assertRaises(AssertionError):
      self.resolve_to_usable(0, "Blue Watcher0")


class RubyTest(EventTest):
  def setUp(self):
    super().setUp()
    self.advance_turn(0, "movement")

  def testDefaultBehavior(self):
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 4)

  def testGainMovement(self):
    ruby = items.SunkenCityRuby(0)
    self.char.possessions = [ruby]
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 7)
    self.assertTrue(ruby.exhausted)


class FluteTest(EventTest):
  def setUp(self):
    super().setUp()
    self.flute = items.OuterGodlyFlute(0)
    self.char.possessions = [self.flute]
    self.maniac = monsters.Maniac()
    self.cultist = monsters.Cultist()
    self.flier = monsters.SubterraneanFlier()
    self.state.monsters.extend([self.maniac, self.cultist, self.flier])

  def enterCombat(self, monster_idx=0):
    self.advance_turn(0, "movement")
    move = self.resolve_to_choice(events.CityMovement)
    move.resolve(self.state, "done")
    try:
      monster = self.resolve_to_choice(events.MonsterChoice)
      monster.resolve(self.state, monster.monsters[monster_idx].handle)
    except AssertionError:
      pass
    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

  def testNotEnoughSanity(self):
    self.maniac.place = self.char.place
    self.char.sanity = 2
    self.enterCombat()
    with self.assertRaises(AssertionError):
      self.resolve_to_usable(0, "Flute0")

  def testNotEnoughStamina(self):
    self.maniac.place = self.char.place
    self.char.stamina = 2
    self.enterCombat()
    with self.assertRaises(AssertionError):
      self.resolve_to_usable(0, "Flute0")

  def testDevouredButBeaten(self):
    self.maniac.place = self.char.place
    self.cultist.place = self.char.place
    self.char.stamina = 3
    self.char.sanity = 3
    self.enterCombat()
    flute = self.resolve_to_usable(0, "Flute0")
    self.state.event_stack.append(flute)
    self.resolve_until_event_type(events.Devoured)
    self.assertFalse(self.maniac.place)
    self.assertFalse(self.cultist.place)

  def testSingleMonsterNoHorror(self):
    self.maniac.place = self.char.place
    self.enterCombat()
    flute = self.resolve_to_usable(0, "Flute0")
    self.state.event_stack.append(flute)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)
    self.assertIn(self.maniac, self.char.trophies)
    self.assertNotIn(self.flute, self.char.possessions)

  def testMultiMonstersNoOverwhelming(self):
    self.maniac.place = self.char.place
    self.cultist.place = self.char.place
    self.enterCombat(0)
    flute = self.resolve_to_usable(0, "Flute0")
    self.state.event_stack.append(flute)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)
    self.assertIn(self.maniac, self.char.trophies)
    self.assertIn(self.cultist, self.char.trophies)
    self.assertNotIn(self.flute, self.char.possessions)


class ObsidianStatueTest(EventTest):
  def setUp(self):
    super().setUp()
    self.statue = items.ObsidianStatue(0)
    self.char.possessions = [self.statue]

  def testSingleSanity(self):
    self.state.event_stack.append(events.Loss(self.char, {"sanity": 1}))
    statue = self.resolve_to_usable(0, "Obsidian Statue0")
    self.state.event_stack.append(statue)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertNotIn(self.statue, self.char.possessions)

  def testMultipleSanity(self):
    self.state.event_stack.append(events.Loss(self.char, {"sanity": 2}))
    statue = self.resolve_to_usable(0, "Obsidian Statue0")
    self.state.event_stack.append(statue)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertNotIn(self.statue, self.char.possessions)

  def testSingleStamina(self):
    self.state.event_stack.append(events.Loss(self.char, {"stamina": 1}))
    statue = self.resolve_to_usable(0, "Obsidian Statue0")
    self.state.event_stack.append(statue)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.statue, self.char.possessions)

  def testMultipleStamina(self):
    self.state.event_stack.append(events.Loss(self.char, {"stamina": 2}))
    statue = self.resolve_to_usable(0, "Obsidian Statue0")
    self.state.event_stack.append(statue)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.statue, self.char.possessions)

  def testSanityAndStamina(self):
    self.state.event_stack.append(events.Loss(self.char, {"stamina": 2, "sanity": 2}))
    statue = self.resolve_to_usable(0, "Obsidian Statue0")
    self.state.event_stack.append(statue)
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Stamina")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 3)
    self.assertNotIn(self.statue, self.char.possessions)
