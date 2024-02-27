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
from eldritch import encounters
from eldritch import events
from eldritch import items
from eldritch import monsters
from eldritch import values
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

  def testNotUsableInOtherWorld(self):
    self.char.place = self.state.places["Abyss1"]
    self.advance_turn(0, "movement")
    self.resolve_until_done()
    self.assertFalse(self.state.usables)
    self.assertIn(self.tablet, self.char.possessions)
    self.assertEqual(self.char.place.name, "Abyss2")

  def testNotUsableWithPatrolWagon(self):
    self.char.possessions.append(items.PatrolWagon())
    wagon = self.resolve_to_usable(0, "Patrol Wagon")
    self.state.event_stack.append(wagon)
    self.resolve_to_choice(events.PlaceChoice)
    self.assertFalse(self.state.usables)
    self.assertIn(self.tablet, self.char.possessions)


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
    monster = monsters.Hound()
    self.state.monsters.append(monster)
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
    monster = monsters.Cultist()
    self.state.monsters.append(monster)
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
    self.state.event_stack.append(events.Combat(self.char, monsters.Cultist()))
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
    pinata = monsters.Pinata()
    endless = monsters.Haunter()
    self.state.monsters.extend([pinata, endless])
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
    return next(
        gate for gate in self.state.gates
        if gate.name == gate_name
    )

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
    nun = characters.Nun()
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
    self.state.event_stack.append(events.Sequence(
        [die, loss], self.char
    ))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      statue = self.resolve_to_usable(0, "Obsidian Statue0")
      self.state.event_stack.append(statue)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.statue, self.char.possessions)

  def testLossIsZeroValueType(self):
    die = events.DiceRoll(self.char, 1)
    loss = events.Loss(self.char, {"stamina": values.Calculation(die, "successes")})
    self.state.event_stack.append(events.Sequence(
        [die, loss], self.char
    ))
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
    self.combat = events.Combat(
        self.char, monsters.Zombie()
    )
    self.state.event_stack.append(self.combat)
    evade_choice = self.resolve_to_choice(events.FightOrEvadeChoice)
    evade_choice.resolve(self.state, "Flee")

  def testEvade(self):
    key = self.resolve_to_usable(0, "Silver Key0")
    self.state.event_stack.append(key)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      self.resolve_until_done()
    self.assertEqual(self.key.tokens["stamina"], 1)
    self.assertIn(self.key, self.char.possessions)

  def testEvadeMaxTokens(self):
    self.key.tokens["stamina"] = 2
    key = self.resolve_to_usable(0, "Silver Key0")
    self.state.event_stack.append(key)
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
    fight_evade = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_evade.resolve(self.state, "Evade")
    key = self.resolve_to_usable(0, "Silver Key0")
    self.state.event_stack.append(key)
    self.resolve_to_choice(events.CityMovement)
    self.assertEqual(self.char.place.name, "Rivertown")
    self.assertEqual(self.char.movement_points, 2)
    self.assertEqual(self.key.tokens["stamina"], 1)

  def testDeclineToUsePass(self):
    self.resolve_to_usable(0, "Silver Key0")
    self.state.done_using[0] = True
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.key.tokens["stamina"], 0)
    self.assertIn(self.key, self.char.possessions)

  def testDeclineToUseFail(self):
    self.resolve_to_usable(0, "Silver Key0")
    self.state.done_using[0] = True
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      key = self.resolve_to_usable(0, "Silver Key0")
    self.state.event_stack.append(key)
    self.resolve_until_done()
    self.assertEqual(self.key.tokens["stamina"], 1)
    self.assertIn(self.key, self.char.possessions)


class WardingStatueTest(EventTest):
  def testCombatDamage(self):
    starting_stamina = self.char.stamina
    self.char.possessions.append(items.WardingStatue(0))
    monster = monsters.Cultist()
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
    monster = monsters.Cultist()
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
    self.state.ancient_one = ancient_ones.Wendigo()
    self.state.event_stack.append(events.Awaken())
    self.resolve_until_done()
    self.advance_turn(0, "ancient")
    self.state.event_stack.append(events.AncientAttack(None))
    self.resolve_to_usable(0, "Warding Statue0")


class TomeTest(EventTest):
  def testTomes(self):
    unique_tomes = [
        items.TibetanTome, items.BlackMagicTome, items.BlackBook, items.BookOfTheDead,
        items.MysticismTome, items.YellowPlay
    ]
    for i, tome_class in enumerate(unique_tomes):
      tome = tome_class(0)
      self.char.possessions = [tome]
      self.advance_turn(i, "movement")
      self.resolve_to_choice(events.CityMovement)
      self.assertIn(tome.handle, self.state.usables[0])


if __name__ == "__main__":
  unittest.main()
