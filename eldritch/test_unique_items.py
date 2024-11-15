#!/usr/bin/env python3

import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch import ancient_ones
from eldritch import characters
from eldritch.abilities import base as abilities
from eldritch.characters import base as base_characters
from eldritch.encounters.gate import base as gate_encounters
from eldritch.encounters.gate.core import GateCard
from eldritch.encounters.location import base as encounters
from eldritch.encounters.location.core import EncounterCard
from eldritch import events
from eldritch import items
from eldritch.items import deputy
from eldritch.items.spells import base as spells
from eldritch import monsters
from eldritch import values
from eldritch.test_events import EventTest


class AncientTabletTest(EventTest):
  def setUp(self):
    super().setUp()
    self.tablet = items.AncientTablet(0)
    self.char.possessions = [self.tablet]
    self.advance_turn(0, "movement")
    self.state.spells.extend([spells.Wither(0), spells.FindGate(0)])

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

  def testNotUsableInOtherWorld(self):
    self.char.place = self.state.places["Abyss1"]
    self.advance_turn(0, "movement")
    self.resolve_until_done()
    self.assertFalse(self.state.usables)
    self.assertIn(self.tablet, self.char.possessions)
    self.assertEqual(self.char.place.name, "Abyss2")

  def testNotUsableWithPatrolWagon(self):
    self.char.possessions.append(deputy.PatrolWagon())
    wagon = self.resolve_to_usable(0, "Patrol Wagon")
    self.state.event_stack.append(wagon)
    self.resolve_to_choice(events.PlaceChoice)
    self.assertFalse(self.state.usables)
    self.assertIn(self.tablet, self.char.possessions)


class AlienStatueTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(items.AlienStatue(0))
    self.state.spells.append(spells.Wither(0))

  def testDeclineToUse(self):
    self.state.event_stack.append(events.Movement(self.char))
    statue = self.resolve_to_usable(0, "Alien Statue0")
    self.state.event_stack.append(statue)
    use_choice = self.resolve_to_choice(events.CardChoice)
    use_choice.resolve(self.state, "Cancel")
    self.resolve_to_choice(events.CityMovement)
    self.assertFalse(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.movement_points, 4)
    self.assertEqual(self.char.sanity, 5)
    self.assertIn(0, self.state.usables)
    self.assertIn("Alien Statue0", self.state.usables[0])

  def testUseAndFail(self):
    self.state.event_stack.append(events.Movement(self.char))
    statue = self.resolve_to_usable(0, "Alien Statue0")
    self.state.event_stack.append(statue)
    use_choice = self.resolve_to_choice(events.CardChoice)
    self.spend("sanity", 1, use_choice)
    use_choice.resolve(self.state, "Alien Statue0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(events.CityMovement)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.movement_points, 2)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 3)
    self.assertNotIn(0, self.state.usables)

  def testUseAndDraw(self):
    self.state.event_stack.append(events.Movement(self.char))
    statue = self.resolve_to_usable(0, "Alien Statue0")
    self.state.event_stack.append(statue)
    use_choice = self.resolve_to_choice(events.CardChoice)
    self.spend("sanity", 1, use_choice)
    use_choice.resolve(self.state, "Alien Statue0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(events.CardChoice)
    self.assertCountEqual(choice.choices, ["spells", "3 clues"])
    choice.resolve(self.state, "spells")
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.possessions[1].name, "Wither")
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(self.char.movement_points, 2)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)

  def testUseForClues(self):
    self.state.event_stack.append(events.Movement(self.char))
    statue = self.resolve_to_usable(0, "Alien Statue0")
    self.state.event_stack.append(statue)
    use_choice = self.resolve_to_choice(events.CardChoice)
    self.spend("sanity", 1, use_choice)
    use_choice.resolve(self.state, "Alien Statue0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(events.CardChoice)
    self.assertCountEqual(choice.choices, ["spells", "3 clues"])
    choice.resolve(self.state, "3 clues")
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertEqual(self.char.clues, 3)
    self.assertEqual(self.char.movement_points, 2)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)


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
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.jewelry.tokens["stamina"], 2)
    self.assertEqual(self.char.stamina, 5)

  def testMultipleStaminaMaxTokens(self):
    self.jewelry.tokens["stamina"] = 2
    loss = events.Loss(self.char, {"stamina": 2})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(self.state.usables[0]["Enchanted Jewelry0"])
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 4)
    self.assertNotIn(self.jewelry, self.char.possessions)


class HealingStoneTest(EventTest):
  def setUp(self):
    super().setUp()
    self.stone = items.HealingStone(0)
    self.char.possessions = [self.stone]
    self.advance_turn(0, "upkeep")

  def testNotUsableWhenFull(self):
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_choice(events.SliderInput)
    self.assertNotIn(0, self.state.usables)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testNotUsableOutsideUpkeep(self):
    self.advance_turn(0, "movement")
    self.resolve_to_choice(events.CityMovement)
    self.assertFalse(self.state.usables)

  def testSanityOnly(self):
    self.char.sanity = 3
    self.char.stamina = 5
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    self.resolve_to_choice(events.SliderInput)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testStaminaOnly(self):
    self.char.sanity = 5
    self.char.stamina = 3
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    self.resolve_to_choice(events.SliderInput)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 4)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testBothSanityAndStamina(self):
    self.char.sanity = 3
    self.char.stamina = 3
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    stone = self.resolve_to_usable(0, "Healing Stone0")
    self.state.event_stack.append(stone)
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.assertEqual(choice.choices, ["1 Stamina", "1 Sanity"])
    choice.resolve(self.state, "1 Stamina")
    self.resolve_to_choice(events.SliderInput)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 4)
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

  def testDeclineToUse(self):
    self.char.sanity = 5
    self.char.stamina = 3
    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    self.resolve_to_usable(0, "Healing Stone0")
    sliders.resolve(self.state, "done", None)
    self.resolve_until_done()

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
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.movement_points, 4)
    self.advance_turn(0, "movement")
    self.assertEqual(self.char.place.name, "Diner")
    monster = self.add_monsters(monsters.Hound())
    monster.place = self.state.places["Easttown"]
    movement = self.resolve_to_choice(events.CityMovement)
    movement.resolve(self.state, "Easttown")
    movement = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 3)
    movement.resolve(self.state, "Rivertown")

    fight_evade = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_evade.resolve(self.state, "Fight")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
      fight_flee.resolve(self.state, "Fight")
    watcher = self.resolve_to_usable(0, "Blue Watcher0")
    self.state.event_stack.append(watcher)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.place.name, "Easttown")
    self.assertIn(monster, self.char.trophies)
    self.assertNotIn(self.watcher, self.char.possessions)
    self.assertEqual(self.char.movement_points, 0)

  def testPassCombatEncounter(self):
    self.state.event_stack.append(encounters.Bank3(self.char))
    watcher = self.resolve_to_usable(0, "Blue Watcher0")
    self.state.event_stack.append(watcher)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertFalse(self.char.trophies)
    self.assertNotIn(self.watcher, self.char.possessions)

  def testDeclineToUseDuringCombat(self):
    monster = self.add_monsters(monsters.Cultist())
    monster.place = self.char.place
    self.state.event_stack.append(events.Combat(self.char, monster))
    self.char.possessions.append(items.Rifle(0))

    fight_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_flee.resolve(self.state, "Fight")
    choice = self.resolve_to_choice(events.CombatChoice)
    self.assertIn("Blue Watcher0", self.state.usables[0])
    self.choose_items(choice, ["Rifle0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.assertIn(monster, self.char.trophies)
    self.assertIn(self.watcher, self.char.possessions)

  def testCloseGateAfterRoll(self):
    self.char.clues = 1
    gate = self.state.gates.popleft()
    self.state.places["Diner"].gate = gate
    self.state.event_stack.append(events.GateCloseAttempt(self.char, "Diner"))
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Close with fight")
    self.resolve_to_usable(0, "Blue Watcher0")
    self.state.done_using[0] = True  # Decline to use before rolling the dice
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_to_choice(events.SpendChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Blue Watcher0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Blue Watcher0"])
    seal = self.resolve_to_choice(events.SpendChoice)
    self.assertListEqual(seal.choices, ["Yes", "No"])
    seal.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertNotIn(self.watcher, self.char.possessions)
    self.assertIn(gate, self.char.trophies)

  def testCloseGateBeforeRoll(self):
    self.char.clues = 1
    gate = self.state.gates.popleft()
    self.state.places["Diner"].gate = gate
    self.state.event_stack.append(events.GateCloseAttempt(self.char, "Diner"))
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Close with lore")
    self.resolve_to_usable(0, "Blue Watcher0")  # Use before rolling the dice
    self.state.event_stack.append(self.state.usables[0]["Blue Watcher0"])
    seal = self.resolve_to_choice(events.SpendChoice)
    self.assertListEqual(seal.choices, ["Yes", "No"])
    seal.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 3)
    self.assertNotIn(self.watcher, self.char.possessions)
    self.assertIn(gate, self.char.trophies)

  def testDeclineToUseGateClose(self):
    self.char.clues = 1
    gate = self.state.gates.popleft()
    self.state.places["Diner"].gate = gate
    self.state.event_stack.append(events.GateCloseAttempt(self.char, "Diner"))
    choice = self.resolve_to_choice(events.MultipleChoice)
    choice.resolve(self.state, "Close with fight")
    self.resolve_to_usable(0, "Blue Watcher0")
    self.state.done_using[0] = True
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(events.SpendChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Blue Watcher0", self.state.usables[0])
    choice.resolve(self.state, "Pass")
    seal = self.resolve_to_choice(events.SpendChoice)
    self.assertListEqual(seal.choices, ["Yes", "No"])
    seal.resolve(self.state, "No")
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertIn(self.watcher, self.char.possessions)
    self.assertIn(gate, self.char.trophies)

  def testCantUseOnOtherFightOrLore(self):
    self.state.event_stack.append(encounters.Science2(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testNotEnoughStamina(self):
    self.char.stamina = 1
    self.state.event_stack.append(events.Combat(self.char, self.add_monsters(monsters.Cultist())))
    fight_evade = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_evade.resolve(self.state, "Fight")
    self.resolve_to_choice(events.CombatChoice)
    self.assertFalse(self.state.usables)

  def testCantUseOnAncientOne(self):
    self.state.ancient_one.health = self.state.ancient_one.max_doom
    self.state.event_stack.append(events.InvestigatorAttack(self.char))
    weapons = self.resolve_to_choice(events.CombatChoice)
    self.assertFalse(self.state.usables)
    weapons.resolve(self.state, "done")
    self.resolve_until_done()


class RubyTest(EventTest):
  def setUp(self):
    super().setUp()
    self.buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    self.buddy.place = self.state.places["Square"]
    self.state.characters.append(self.buddy)
    self.advance_turn(0, "movement")

  def testDefaultBehavior(self):
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 4)

  def testGainMovement(self):
    ruby = items.SunkenCityRuby(0)
    self.char.possessions = [ruby]
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 7)

  def testOnlyGainOncePerTurn(self):
    ruby = items.SunkenCityRuby(0)
    self.char.possessions = [ruby]
    choice = self.resolve_to_choice(events.CityMovement)
    choice.resolve(self.state, "Roadhouse")
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 5)
    self.assertEqual(self.char.place.name, "Roadhouse")

  def testBuddyReceivesBonus(self):
    ruby = items.SunkenCityRuby(0)
    self.char.possessions = [ruby]
    movement = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 7)
    movement.resolve(self.state, "Square")
    movement = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 4)
    self.state.handle_give(0, 1, "Ruby0", 1)
    movement.resolve(self.state, "done")
    self.assertEqual(self.char, movement.character)
    self.resolve_until_done()
    self.state.next_turn()
    buddy_movement = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.buddy.movement_points, 7)
    self.assertEqual(buddy_movement.character, self.buddy)


class FluteTest(EventTest):
  def setUp(self):
    super().setUp()
    self.flute = items.OuterGodlyFlute(0)
    self.char.possessions = [self.flute]
    self.maniac = self.add_monsters(monsters.Maniac())
    self.cultist = self.add_monsters(monsters.Cultist())
    self.flier = self.add_monsters(monsters.SubterraneanFlier())

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
    self.resolve_to_choice(events.CombatChoice)
    self.assertFalse(self.state.usables)

  def testNotEnoughStamina(self):
    self.maniac.place = self.char.place
    self.char.stamina = 2
    self.enterCombat()
    self.resolve_to_choice(events.CombatChoice)
    self.assertFalse(self.state.usables)

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

  def testInsaneKeepTrophies(self):
    self.maniac.place = self.char.place
    self.cultist.place = self.char.place
    self.char.stamina = 4
    self.char.sanity = 3
    self.enterCombat()
    flute = self.resolve_to_usable(0, "Flute0")
    self.state.event_stack.append(flute)
    loss = self.resolve_to_choice(events.ItemLossChoice)
    loss.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertIn(self.maniac, self.char.trophies)
    self.assertIn(self.cultist, self.char.trophies)

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

  def testMultiMonstersNightmarishOverwhelming(self):
    self.maniac.place = self.char.place
    self.flier.place = self.char.place
    self.enterCombat(0)
    flute = self.resolve_to_usable(0, "Flute0")
    self.state.event_stack.append(flute)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)
    self.assertIn(self.maniac, self.char.trophies)
    self.assertIn(self.flier, self.char.trophies)
    self.assertNotIn(self.flute, self.char.possessions)

  def testEndlessOrPinataBehavior(self):
    pinata, endless = self.add_monsters(monsters.Pinata(), monsters.Haunter())
    holy_water = items.HolyWater(0)
    self.state.unique.append(holy_water)
    for monster in [self.maniac, pinata, endless]:
      monster.place = self.char.place

    self.enterCombat(0)
    flute = self.resolve_to_usable(0, "Flute0")
    self.state.event_stack.append(flute)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.sanity, 2)
    self.assertIn(self.maniac, self.char.trophies)
    self.assertNotIn(pinata, self.char.trophies)
    self.assertNotIn(endless, self.char.trophies)
    self.assertIsNone(pinata.place)
    self.assertEqual(endless.place, self.state.monster_cup)
    self.assertNotIn(self.flute, self.char.possessions)
    self.assertIn(holy_water, self.char.possessions)

  def testDeclineToUse(self):
    self.cultist.place = self.char.place
    self.enterCombat(0)
    choice = self.resolve_to_choice(events.CombatChoice)
    self.assertIn("Flute0", self.state.usables[0])
    self.choose_items(choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    self.assertIn(self.cultist, self.char.trophies)
    self.assertIn(self.flute, self.char.possessions)

  def testFriendCannotUse(self):
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.char.place
    self.state.characters.append(buddy)
    self.char.possessions.remove(self.flute)
    buddy.possessions.append(self.flute)

    self.cultist.place = self.char.place
    self.enterCombat(0)
    choice = self.resolve_to_choice(events.CombatChoice)
    self.assertFalse(self.state.usables)
    self.choose_items(choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()


class GateBoxTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions = [items.GateBox(0)]
    self.char.place = self.state.places["Sunken City2"]
    self.advance_turn(0, "movement")

  def get_gate(self, gate_name):
    return next(gate for gate in self.state.gates if gate.name == gate_name)

  def testTwoGates(self):
    self.state.places["Woods"].gate = self.get_gate("Sunken City")
    self.state.places["Diner"].gate = self.get_gate("Abyss")
    choice = self.resolve_to_choice(events.GateChoice)
    choice.resolve(self.state, "Diner")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Diner")

  def testNoChoiceOnOneGate(self):
    self.state.places["Woods"].gate = self.get_gate("Sunken City")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Woods")

  def testSaveLostInTimeAndSpace(self):
    self.state.places["Woods"].gate = self.get_gate("Abyss")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Woods")

  def testTradeBeforeReturnMultipleGates(self):
    self.state.places["Woods"].gate = self.get_gate("Sunken City")
    self.state.places["Diner"].gate = self.get_gate("Abyss")
    nun = base_characters.Nun()
    self.state.characters.append(nun)
    self.assertEqual(self.char.place.name, "Sunken City2")
    nun.place = self.char.place
    self.char.possessions.append(items.Cross(0))
    self.resolve_to_choice(events.GateChoice)
    self.assertIn("Gate Box0", self.state.usables[0])
    self.state.handle_give(0, 1, "Gate Box0", None)
    # Dummy now only has one choice, but it is not chosen for them - they still have the ability
    # to continue to trade if they wish.
    choice = self.resolve_to_choice(events.GateChoice)
    self.assertEqual(choice.choices, ["Woods"])
    choice.resolve(self.state, "Woods")
    self.resolve_until_done()
    self.state.next_turn()
    # Nun has no one to trade with, so automatically uses the gate box
    nun_choice = self.resolve_to_choice(events.GateChoice)
    self.assertRegex(nun_choice.prompt(), "any open gate")
    self.assertEqual(nun_choice.character, nun)
    self.assertSequenceEqual(nun_choice.choices, ["Diner", "Woods"])

    # TODO: what happens if they decide to give the gate box back?


class ObsidianStatueTest(EventTest):
  def setUp(self):
    super().setUp()
    self.statue = items.ObsidianStatue(0)
    self.char.possessions = [self.statue]

  def testClueLoss(self):
    self.state.event_stack.append(events.Loss(self.char, {"clues": 1}))
    self.resolve_until_done()

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

  def testLossIsValueType(self):
    die = events.DiceRoll(self.char, 1)
    loss = events.Loss(self.char, {"stamina": values.Calculation(die, "successes")})
    self.state.event_stack.append(events.Sequence([die, loss], self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      statue = self.resolve_to_usable(0, "Obsidian Statue0")
      self.state.event_stack.append(statue)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.statue, self.char.possessions)

  def testLossIsZeroValueType(self):
    die = events.DiceRoll(self.char, 1)
    loss = events.Loss(self.char, {"stamina": values.Calculation(die, "successes")})
    self.state.event_stack.append(events.Sequence([die, loss], self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertIn(self.statue, self.char.possessions)

  def testJewelryAndStatue(self):
    jewelry = items.EnchantedJewelry(0)
    self.char.possessions.append(jewelry)
    self.state.event_stack.append(events.Loss(self.char, {"stamina": 1}))
    jewelry_usable = self.resolve_to_usable(0, "Enchanted Jewelry0")
    self.state.event_stack.append(jewelry_usable)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertIn(self.statue, self.char.possessions)

  def testStatueAndJewelry(self):
    jewelry = items.EnchantedJewelry(0)
    self.char.possessions.append(jewelry)
    self.state.event_stack.append(events.Loss(self.char, {"stamina": 1}))
    statue_usable = self.resolve_to_usable(0, "Obsidian Statue0")
    self.state.event_stack.append(statue_usable)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertIn(jewelry, self.char.possessions)


class SilverKeyTest(EventTest):
  def setUp(self):
    super().setUp()
    self.key = items.SilverKey(0)
    self.char.possessions.append(self.key)
    self.combat = events.Combat(self.char, self.add_monsters(monsters.Zombie()))
    self.state.event_stack.append(self.combat)
    self.resolve_to_choice(events.FightOrEvadeChoice)

  def testEvade(self):
    self.assertIn("Silver Key0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Silver Key0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.key.tokens["stamina"], 1)
    self.assertIn(self.key, self.char.possessions)

  def testEvadeMaxTokens(self):
    self.key.tokens["stamina"] = 2
    self.state.event_stack.append(self.state.usables[0]["Silver Key0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertNotIn(self.key, self.char.possessions)

  def testKeyPreservesMovement(self):
    self.state.event_stack.clear()

    self.advance_turn(0, "movement")
    self.assertEqual(self.char.place.name, "Diner")
    monster = monsters.Hound()
    self.state.monsters.append(monster)
    monster.place = self.state.places["Easttown"]
    movement = self.resolve_to_choice(events.CityMovement)
    movement.resolve(self.state, "Easttown")
    movement = self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.movement_points, 3)
    movement.resolve(self.state, "Rivertown")
    self.resolve_to_choice(events.FightOrEvadeChoice)
    self.assertIn("Silver Key0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Silver Key0"])
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.place.name, "Rivertown")
    self.assertEqual(self.char.movement_points, 2)
    self.assertEqual(self.key.tokens["stamina"], 1)

  def testDeclineToUsePass(self):
    choice = self.resolve_to_choice(events.FightOrEvadeChoice)
    choice.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      roll = self.resolve_to_choice(events.DiceRoll)  # Also can be used here
      roll.resolve(self.state)
      self.resolve_until_done()
    self.assertEqual(self.key.tokens["stamina"], 0)
    self.assertIn(self.key, self.char.possessions)

  def testDeclineToUseFail(self):
    choice = self.resolve_to_choice(events.FightOrEvadeChoice)
    choice.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      roll = self.resolve_to_choice(events.DiceRoll)  # Also can be used here
      roll.resolve(self.state)
      choice = self.resolve_to_choice(events.FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 3)  # Failed the evade check
    self.assertIn("Silver Key0", self.state.usables[0])  # Can use it again

  def testUseOnCheck(self):
    self.state.event_stack.clear()

    gain = events.Gain(self.char, {"dollars": 5})
    check = events.Check(self.char, "evade", 0)
    self.state.event_stack.append(events.PassFail(self.char, check, gain, events.Nothing()))
    key = self.resolve_to_usable(0, "Silver Key0")
    self.state.event_stack.append(key)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 5)


class WardingStatueTest(EventTest):
  def testCombatDamage(self):
    starting_stamina = self.char.stamina
    self.char.possessions.append(items.WardingStatue(0))
    monster = self.add_monsters(monsters.Cultist())
    self.state.event_stack.append(events.Combat(self.char, monster))
    choice = self.resolve_to_choice(events.FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(events.CombatChoice)
    weapon_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      statue = self.resolve_to_usable(0, "Warding Statue0")
      self.state.event_stack.append(statue)
    fight_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(events.CombatChoice)
    weapon_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertFalse(self.char.possessions)
    self.assertEqual(self.char.stamina, starting_stamina)

  def testCombatDamageDontUse(self):
    starting_stamina = self.char.stamina
    statue = items.WardingStatue(0)
    self.char.possessions.append(statue)
    monster = self.add_monsters(monsters.Cultist())
    self.state.event_stack.append(events.Combat(self.char, monster))
    choice = self.resolve_to_choice(events.FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(events.CombatChoice)
    weapon_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      _ = self.resolve_to_usable(0, "Warding Statue0")
      self.state.done_using[0] = True
    fight_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(events.CombatChoice)
    weapon_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertListEqual(self.char.possessions, [statue])
    self.assertEqual(self.char.stamina, starting_stamina - 1)

  def testCancelAncientOne(self):
    self.char.possessions.append(items.WardingStatue(0))
    self.state.ancient_one = ancient_ones.SerpentGod()
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.advance_turn(0, "ancient")
    self.state.event_stack.append(events.AncientAttack(None))
    self.resolve_to_usable(0, "Warding Statue0")
    self.state.event_stack.append(self.state.usables[0]["Warding Statue0"])
    self.resolve_until_done()

    # If the ancient one attacks again, it the rating should not have increased.
    self.state.event_stack.append(events.AncientAttack(None))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Speed 4 + rating of +1 = 5


class DragonsEyeLocationTest(EventTest):
  def setUp(self):
    super().setUp()
    self.state.places["Rivertown"].encounters = [
      EncounterCard("Rivertown1", {"Store": encounters.Store1}),  # Gain $1
      EncounterCard("Rivertown2", {"Store": encounters.Store2}),  # No encounter
      EncounterCard("Rivertown4", {"Store": encounters.Store4}),  # Lose 1 sanity
    ]
    self.char.place = self.state.places["Store"]
    self.char.possessions.append(items.DragonsEye(0))

  def testOneMulligan(self):
    with mock.patch.object(events.random, "shuffle", new=mock.MagicMock()):
      self.state.event_stack.append(events.EncounterPhase(self.char))
      eye = self.resolve_to_usable(0, "Dragon's Eye0")
      self.state.event_stack.append(eye)
      with mock.patch.object(events.random, "choice", new=mock.MagicMock()) as rand:
        rand.side_effect = lambda choices: choices[0]
        self.resolve_until_done()
        self.assertEqual(rand.call_count, 1)
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.sanity, 4)
    self.assertTrue(self.char.possessions[0].exhausted)

  def testDeclineToUse(self):
    self.state.event_stack.append(events.EncounterPhase(self.char))
    self.resolve_to_usable(0, "Dragon's Eye0")
    self.state.event_stack[-1].resolve(self.state, "Rivertown1")
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(self.char.sanity, 5)

  def testMultipleCards(self):
    encounter = events.TravelOrEncounter(self.char, 2)
    self.state.event_stack.append(encounter)
    with mock.patch.object(events.random, "shuffle", new=mock.MagicMock()):
      eye = self.resolve_to_usable(0, "Dragon's Eye0")
      self.state.event_stack.append(eye)
      mulligan = self.resolve_to_choice(events.CardChoice)
      self.assertCountEqual(mulligan.choices, ["Rivertown1", "Rivertown2"])
      mulligan.resolve(self.state, "Rivertown2")
      new_choice = self.resolve_to_choice(events.CardChoice)
      self.assertCountEqual(new_choice.choices, ["Rivertown1", "Rivertown4"])
      new_choice.resolve(self.state, "Rivertown4")
      self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(self.char.sanity, 3)

  def testNotEnoughCardsForMulligan(self):
    for _ in range(2):
      self.state.places["Rivertown"].encounters.pop()
    self.state.event_stack.append(events.EncounterPhase(self.char))
    eye = self.resolve_to_usable(0, "Dragon's Eye0")
    self.state.event_stack.append(eye)
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(self.char.sanity, 4)  # You still lose 1 sanity, even if there's no cards left.

  def testCannotUseWhileExhausted(self):
    self.char.possessions[0]._exhausted = True  # pylint: disable=protected-access
    self.state.event_stack.append(events.EncounterPhase(self.char))
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 1)
    self.assertEqual(self.char.sanity, 5)

  def testGoInsane(self):
    for _ in range(2):
      self.state.places["Rivertown"].encounters.pop()
    self.char.sanity = 1
    self.state.event_stack.append(events.EncounterPhase(self.char))
    eye = self.resolve_to_usable(0, "Dragon's Eye0")
    self.state.event_stack.append(eye)
    choice = self.resolve_to_choice(events.ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.dollars, 0)  # Went insane before the encounter started
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.place.name, "Asylum")


class DragonsEyeGateTest(EventTest):
  def setUp(self):
    super().setUp()
    self.state.gate_cards.clear()
    self.state.gate_cards.extend(
      [
        GateCard("Gate15", {"green"}, {"Other": gate_encounters.Other15}),  # Gain $3
        GateCard("Gate5", {"blue"}, {"Other": gate_encounters.Dreamlands5}),  # No encounter
        GateCard("Gate3", {"blue"}, {"Other": gate_encounters.Other3}),  # Lose 1 sanity
      ]
    )
    self.char.place = self.state.places["Dreamlands1"]
    self.char.possessions.append(items.DragonsEye(0))

  def testOneMulligan(self):
    self.state.event_stack.append(events.OtherWorldPhase(self.char))
    eye = self.resolve_to_usable(0, "Dragon's Eye0")
    self.state.event_stack.append(eye)
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.dollars, 0)

  def testTwoCards(self):
    self.char.possessions.append(abilities.PsychicSensitivity())
    self.state.event_stack.append(events.OtherWorldPhase(self.char))
    eye = self.resolve_to_usable(0, "Dragon's Eye0")
    self.state.event_stack.append(eye)
    choice = self.resolve_to_choice(events.CardChoice)
    self.assertCountEqual(choice.choices, ["Gate15", "Gate5"])
    choice.resolve(self.state, "Gate5")
    new_choice = self.resolve_to_choice(events.CardChoice)
    self.assertCountEqual(new_choice.choices, ["Gate15", "Gate3"])
    new_choice.resolve(self.state, "Gate3")
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 0)

  def testShuffleIgnoresDrawnCards(self):
    def gate_sort(_):
      cards_to_sort = list(self.state.gate_cards)
      cards_to_sort.sort(key=lambda card: card.name)
      self.state.gate_cards.clear()
      self.state.gate_cards.extend(cards_to_sort)

    shuffle = GateCard("ShuffleGate", set(), {"Other": lambda char: events.Nothing()})
    self.state.gate_cards.insert(2, shuffle)

    self.char.possessions.append(abilities.PsychicSensitivity())
    self.state.event_stack.append(events.OtherWorldPhase(self.char))
    with mock.patch.object(events.random, "shuffle", new=mock.MagicMock(side_effect=gate_sort)):
      # Replace shuffle with sort. Order would be Gate15 < Gate3 < Gate5 < ShuffleGate
      # But Gate15 should be removed unless we made a mistake, so Gate3 should be on top.
      # Note that Gate5 goes back into the deck and can theoretically be drawn again.
      eye = self.resolve_to_usable(0, "Dragon's Eye0")
      self.state.event_stack.append(eye)
      choice = self.resolve_to_choice(events.CardChoice)
      choice.resolve(self.state, "Gate5")
      new_choice = self.resolve_to_choice(events.CardChoice)
      self.assertCountEqual(new_choice.choices, ["Gate15", "Gate3"])
      new_choice.resolve(self.state, "Gate3")
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.dollars, 0)
    self.assertEqual(len(self.state.gate_cards), 4)


class TomeTest(EventTest):
  def testTomes(self):
    unique_tomes = [
      items.TibetanTome,
      items.BlackMagicTome,
      items.BlackBook,
      items.BookOfTheDead,
      items.MysticismTome,
      items.YellowPlay,
    ]
    for i, tome_class in enumerate(unique_tomes):
      tome = tome_class(0)
      self.char.possessions = [tome]
      self.advance_turn(i, "movement")
      self.resolve_to_choice(events.CityMovement)
      self.assertIn(tome.handle, self.state.usables[0])


if __name__ == "__main__":
  unittest.main()
