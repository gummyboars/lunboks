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
from eldritch import events
from eldritch.events import *
from eldritch import items
from eldritch import monsters
from eldritch import mythos
from eldritch import encounters
from eldritch.test_events import EventTest, Canceller


class CombatTest(EventTest):

  def testCombatFight(self):
    self.char.fight_will_slider = 0
    self.assertEqual(self.char.fight(self.state), 1)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertIn("or flee", fight_or_flee.prompt())
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1])):
      self.resolve_until_done()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertIsNone(combat.combat.damage)
    self.assertTrue(combat.is_resolved())
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0].name, "Cultist")

  def testCombatFightThenFlee(self):
    self.char.fight_will_slider = 0
    self.char.speed_sneak_slider = 0
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sneak(self.state), 4)
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_round = combat.combat
    evade_round = combat.evade
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

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
    self.assertEqual(len(self.char.trophies), 0)

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
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertIsNotNone(combat.horror)
    self.assertTrue(combat.horror.is_resolved())
    self.assertEqual(self.char.sanity, 4)

    combat_round = combat.combat
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

    # Fail the combat check. After this, we check that there is not a second horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertIsNotNone(combat_round.damage)
    self.assertTrue(combat_round.damage.is_resolved())
    self.assertEqual(len(self.char.trophies), 0)
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)  # Assert there wasn't a second horror check/loss.

    combat_round = combat.combat
    next_fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat_round.is_resolved())
    self.assertTrue(combat_round.defeated)
    self.assertIsNone(combat_round.damage)
    self.assertTrue(combat.is_resolved())

  def testCombatAgainstEndless(self):
    self.char.possessions.append(items.TommyGun(0))
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.fight(self.state), 4)
    self.assertEqual(self.char.will(self.state), 1)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    haunter = monsters.Haunter()
    combat = Combat(self.char, haunter)
    self.state.event_stack.append(combat)

    # The horror check happens here - they are guaranteed to fail becuse they have only 1 will.
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertIsNotNone(combat.horror)
    self.assertTrue(combat.horror.is_resolved())
    self.assertEqual(self.char.sanity, 3)

    combat_round = combat.combat
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Tommy Gun0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat_round.is_resolved())
    self.assertTrue(combat_round.defeated)
    self.assertIsNone(combat_round.damage)
    self.assertTrue(combat.is_resolved())
    self.assertNotIn(haunter, self.char.trophies)
    self.assertEqual(haunter.place.name, "cup")

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
    self.choose_items(choose_weapons, [])

    # Roll one success, but the maniac's toughness should be 2 because of the environment.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[5, 1])):
      self.resolve_until_done()

    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertIsNotNone(combat_round.damage)

  def testHorrorCheckCancelled(self):
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)
    self.char.possessions.append(Canceller(Check))

    self.resolve_to_choice(FightOrEvadeChoice)
    # If the horror check is cancelled, proceed as if it had 0 successes.
    self.assertIsNotNone(combat.horror)
    self.assertFalse(combat.horror.is_resolved())
    self.assertTrue(combat.horror.is_cancelled())
    self.assertTrue(combat.sanity_loss.is_resolved())
    self.assertEqual(self.char.sanity, 4)

  def testSanityLossCancelled(self):
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)
    self.char.possessions.append(Canceller(GainOrLoss))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)
    self.assertTrue(combat.horror.is_resolved())
    self.assertFalse(combat.sanity_loss.is_resolved())
    self.assertTrue(combat.sanity_loss.is_cancelled())
    self.assertEqual(self.char.sanity, 5)

  def testChoiceCancelled(self):
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)
    self.char.possessions.append(Canceller(FightOrEvadeChoice))

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      # We still expect to hit a FightOrEvadeChoice. The first one will be cancelled, but since we
      # have neither evaded nor defeated the monster, we will just start a new round of combat.
      self.resolve_to_choice(FightOrEvadeChoice)
    # TODO: assertions on the cancelled choice

  def testCancelledEvade(self):
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)
    self.char.possessions.append(Canceller(EvadeRound))

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")

    # Again, the evade round gets cancelled, but we have neither evaded nor defeated the monster,
    # so we end up back at another fight or flee choice.
    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 5)

  def testCancelledEvadeCheck(self):
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")

    # Cancel the next check (the evade check). The character will fail to evade and take damage.
    self.char.possessions.append(Canceller(Check))
    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 3)

  def testCancelledEvadeDamage(self):
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")
    first_evade = combat.evade

    # Cancel the next stamina loss from the evade check. We should end up back in combat.
    self.char.possessions.append(Canceller(GainOrLoss))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 5)
    self.assertTrue(first_evade.damage.is_cancelled())

  def testCancelledCombat(self):
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)
    self.char.possessions.append(Canceller(CombatRound))

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    first_combat = combat.combat

    # The combat round gets cancelled, but we have neither evaded nor defeated the monster,
    # so we end up back at another fight or flee choice.
    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 5)
    self.assertTrue(first_combat.is_cancelled())
    self.assertEqual(len(self.char.trophies), 0)

  def testCancelledCombatCheck(self):
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    first_combat = combat.combat

    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])

    # Cancel the check for the combat round.
    self.char.possessions.append(Canceller(Check))
    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 3)
    self.assertTrue(first_combat.check.is_cancelled())

  def testCancelledCombatChoice(self):
    self.assertEqual(self.char.stamina, 5)
    self.char.possessions.append(items.TommyGun(0))
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    first_combat = combat.combat

    # Cancel the choice of items to use.
    self.char.possessions.append(Canceller(CombatChoice))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(self.char.stamina, 3)
    self.assertTrue(first_combat.choice.is_cancelled())

  def testCancelledItemActivation(self):
    self.assertEqual(self.char.stamina, 5)
    self.char.possessions.append(items.TommyGun(0))
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Tommy Gun0"])

    # Cancel the choice of items to use.
    self.char.possessions.append(Canceller(ActivateChosenItems))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(self.char.stamina, 3)
    self.assertTrue(combat_choice.activate.is_cancelled())

  def testCancelledCombatDamage(self):
    self.assertEqual(self.char.stamina, 5)
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    first_combat = combat.combat

    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])

    # Cancel the choice of items to use.
    self.char.possessions.append(Canceller(GainOrLoss))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(self.char.stamina, 5)
    self.assertTrue(first_combat.is_resolved())
    self.assertTrue(first_combat.damage.is_cancelled())


class CombatOrEvadeTest(EventTest):

  def testEvadeMeansNoHorror(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.will(self.state), 1)
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    choice = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(choice)

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
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

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")

    # While here, they will fail the horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 3)

  def testAutoEvadeMonster(self):
    cultist = monsters.Cultist()
    choice = EvadeOrCombat(self.char, cultist, auto_evade=True)
    self.state.event_stack.append(choice)

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Ignore")
    # Make sure the character cannot pass an evade check to validate they are automatically evading.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

  def testCancelledEvade(self):
    zombie = monsters.Zombie()
    evade_or_combat = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(evade_or_combat)
    self.char.possessions.append(Canceller(EvadeRound))

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertCountEqual(fight_or_flee.choices, ["Fight", "Flee"])
    self.assertTrue(evade_or_combat.evade.is_cancelled())

  def testCancelledChoice(self):
    zombie = monsters.Zombie()
    evade_or_combat = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(evade_or_combat)
    self.char.possessions.append(Canceller(FightOrEvadeChoice))

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertCountEqual(fight_or_flee.choices, ["Fight", "Flee"])

    self.assertFalse(evade_or_combat.evade.is_done())

  def testCancelledCombat(self):
    zombie = monsters.Zombie()
    evade_or_combat = EvadeOrCombat(self.char, zombie)
    self.state.event_stack.append(evade_or_combat)
    self.char.possessions.append(Canceller(Combat))

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertCountEqual(fight_or_evade.choices, ["Fight", "Evade"])
    fight_or_evade.resolve(self.state, "Fight")
    self.resolve_until_done()

    self.assertTrue(evade_or_combat.is_resolved())
    self.assertFalse(evade_or_combat.combat.is_resolved())


class EvadeOrFightAllTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.speed_sneak_slider = 0

  def testEvadeSingleMonster(self):
    self.state.monsters[0].place = self.char.place
    fight_all = EvadeOrFightAll(self.char, self.state.monsters[:1])
    self.state.event_stack.append(fight_all)
    # When there is only one monster, it is chosen automatically.
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(fight_or_evade.monster, self.state.monsters[0])
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testDefeatTwoMonsters(self):
    self.state.monsters[0].place = self.char.place
    self.state.monsters[1].place = self.char.place
    fight_all = EvadeOrFightAll(self.char, self.state.monsters)
    self.state.event_stack.append(fight_all)

    monster_choice = self.resolve_to_choice(MonsterChoice)
    self.assertEqual(monster_choice.monsters, self.state.monsters)
    output = self.state.for_player(0)
    self.assertEqual(
        [monster["handle"] for monster in output["choice"]["monsters"]],
        [monster.handle for monster in self.state.monsters],
    )

    monster_choice.resolve(self.state, self.state.monsters[0].handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(fight_or_evade.monster, self.state.monsters[0])
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(fight_or_evade.monster, self.state.monsters[1])
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testDefeatOneFleeFromOne(self):
    self.state.monsters.extend([monsters.Witch(), monsters.FlameMatrix()])
    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
      monster.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, self.state.monsters)
    self.state.event_stack.append(fight_all)

    monster_choice = self.resolve_to_choice(MonsterChoice)
    self.assertEqual(monster_choice.monsters, self.state.monsters)
    output = self.state.for_player(0)
    self.assertEqual(
        [monster["handle"] for monster in output["choice"]["monsters"]],
        [monster.handle for monster in self.state.monsters],
    )

    # Start with the witch.
    monster_choice.resolve(self.state, self.state.monsters[2].handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(fight_or_evade.monster, self.state.monsters[2])
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])

    # Defeat the witch, come back to the monster choice.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      monster_choice = self.resolve_to_choice(MonsterChoice)
    self.assertEqual(monster_choice.monsters, self.state.monsters[:2] + self.state.monsters[3:])

    # Choose the maniac. Try to fight it, then flee from it.
    monster_choice.resolve(self.state, self.state.monsters[1].handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(fight_or_evade.monster, self.state.monsters[1])
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")

    # Flee from the maniac, come back to the monster choice.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      monster_choice = self.resolve_to_choice(MonsterChoice)
    # Because we fled from the maniac, it is still listed in the monster choice.
    self.assertEqual(monster_choice.monsters, self.state.monsters[:2] + self.state.monsters[3:])
    output = self.state.for_player(0)
    self.assertEqual(
        [monster["handle"] for monster in output["choice"]["monsters"]],
        ["Cultist0", "Maniac1", "Flame Matrix3"],
    )
    self.assertCountEqual(output["choice"]["invalid_choices"], [1])

    # Now, the cultist.
    monster_choice.resolve(self.state, self.state.monsters[0].handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(fight_or_evade.monster, self.state.monsters[0])
    fight_or_evade.resolve(self.state, "Evade")

    # Once we evade the cultist, there is only one monster left, so we get no choices.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(fight_or_evade.monster, self.state.monsters[3])
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testWithAutoEvade(self):
    self.state.monsters.extend([monsters.Witch(), monsters.FlameMatrix()])
    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
      monster.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, self.state.monsters, auto_evade=True)
    self.state.event_stack.append(fight_all)

    monster_choice = self.resolve_to_choice(MonsterChoice)
    self.assertEqual(monster_choice.monsters, self.state.monsters)
    output = self.state.for_player(0)
    self.assertEqual(
        [monster["handle"] for monster in output["choice"]["monsters"][:4]],
        [monster.handle for monster in self.state.monsters],
    )
    self.assertEqual(output["choice"]["monsters"][4], "Ignore All")

    monster_choice.resolve(self.state, self.state.monsters[0].handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Ignore")
    # Make sure the character is actually auto-evading by failing all checks.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      monster_choice = self.resolve_to_choice(MonsterChoice)

    monster_choice.resolve(self.state, "Ignore All")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

  def testStopsWhenLostInTimeAndSpace(self):
    self.state.monsters.append(monsters.DimensionalShambler())
    for idx, monster in enumerate(self.state.monsters):
      monster.idx = idx
      monster.place = self.char.place

    fight_all = EvadeOrFightAll(self.char, self.state.monsters)
    self.state.event_stack.append(fight_all)

    monster_choice = self.resolve_to_choice(MonsterChoice)
    monster_choice.resolve(self.state, self.state.monsters[-1].handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Lost")
    self.assertIsNotNone(self.char.lose_turn_until)
    self.assertEqual(self.char.stamina, 5)


class LoseCombatTest(EventTest):

  def testHorrorInsane(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.will(self.state), 1)
    self.char.sanity = 1
    zombie = monsters.Zombie()
    cultist = monsters.Cultist()
    zombie.place = self.char.place
    cultist.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, [zombie, cultist])
    self.state.event_stack.append(fight_all)

    self.assertEqual(self.char.place.name, "Diner")

    monster_choice = self.resolve_to_choice(MonsterChoice)
    monster_choice.resolve(self.state, zombie.handle)
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")
    # Character auto-fails the horror check.
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 1)
    self.assertTrue(fight_all.is_cancelled())

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
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")

    # Let them pass the horror check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
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

    choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Flee")
    # Cultist has a sneak difficulty of -3, so they auto-fail the evade check.
    next_choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 1)

    next_choice.resolve(self.state, "Flee")
    choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [])
    self.resolve_until_done()
    # They failed the next evade check, so they went unconscious.
    self.assertEqual(self.char.stamina, 1)
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.place.name, "Hospital")

  def testLostFromAnotherWorld(self):
    self.char.place = self.state.places["Dreamlands1"]
    self.state.monsters.clear()
    self.state.monsters.append(monsters.DimensionalShambler())
    self.state.monsters[0].idx = 0
    self.state.monsters[0].place = self.state.monster_cup

    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Lost")
    self.assertIsNotNone(self.char.lose_turn_until)
    self.assertEqual(self.char.stamina, 5)


class DreamFlierCombatTest(EventTest):

  def setUp(self):
    super().setUp()
    self.flier = monsters.DreamFlier()
    self.state.monsters.append(self.flier)
    self.state.monsters[-1].idx = len(self.state.monsters)-1

  def testWinCombat(self):
    self.char.place = self.state.places["Northside"]
    self.flier.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, [self.flier])
    self.state.event_stack.append(fight_all)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Northside")
    self.assertIn(self.flier, self.char.trophies)
    self.assertIsNone(self.flier.place)

  def testLoseCombatNoGates(self):
    self.char.place = self.state.places["Northside"]
    self.state.monsters[0].place = self.char.place
    self.flier.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, [self.flier, self.state.monsters[0]])
    self.state.event_stack.append(fight_all)
    monster_choice = self.resolve_to_choice(MonsterChoice)
    monster_choice.resolve(self.state, self.flier.handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    # Lose the combat. The combat should end with no effect.
    # We should continue by fighting the next monster.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(fight_or_evade.monster, self.state.monsters[0])
    self.assertEqual(self.char.place.name, "Northside")
    self.assertEqual(self.flier.place.name, "Northside")
    self.assertFalse(self.char.trophies)

    # Finish fighting the next monster, and validate that the EvadeOrFightAll ends.
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

  def testLoseCombatWithOpenGates(self):
    self.char.place = self.state.places["Northside"]
    # Two gates - one to the Abyss, and one to Pluto. The Abyss gate is closer than the Pluto gate.
    self.state.places["Isle"].gate = [gate for gate in self.state.gates if gate.name == "Abyss"][0]
    self.state.places["Woods"].gate = [gate for gate in self.state.gates if gate.name == "Pluto"][0]
    self.state.monsters[0].place = self.char.place
    self.flier.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, [self.flier, self.state.monsters[0]])
    self.state.event_stack.append(fight_all)
    monster_choice = self.resolve_to_choice(MonsterChoice)
    monster_choice.resolve(self.state, self.flier.handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    # After losing, the character should be pulled through to the Abyss, and should not fight the
    # rest of the monsters.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Abyss1")
    self.assertEqual(self.flier.place.name, "Northside")
    self.assertFalse(self.char.trophies)

  def testFailEvadeCheck(self):
    self.char.place = self.state.places["Northside"]
    self.state.places["Isle"].gate = self.state.gates.popleft()
    self.flier.place = self.char.place
    self.state.monsters[0].place = self.char.place

    fight_all = EvadeOrFightAll(self.char, [self.flier, self.state.monsters[0]])
    self.state.event_stack.append(fight_all)
    monster_choice = self.resolve_to_choice(MonsterChoice)
    monster_choice.resolve(self.state, self.flier.handle)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, self.state.places["Isle"].gate.name + "1")
    self.assertEqual(self.flier.place.name, "Northside")
    self.assertFalse(self.char.trophies)

  def testMultipleNearestGates(self):
    self.char.place = self.state.places["Northside"]
    # Two gates - one to the Abyss, and one to Pluto. The Abyss gate is closer than the Pluto gate.
    self.state.places["Roadhouse"].gate = [g for g in self.state.gates if g.name == "Abyss"][0]
    self.state.places["Cave"].gate = [gate for gate in self.state.gates if gate.name == "Pluto"][0]
    self.flier.place = self.char.place
    fight_all = EvadeOrFightAll(self.char, [self.flier])
    self.state.event_stack.append(fight_all)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    # After losing, the character should get a choice of which gate to go through.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      gate_choice = self.resolve_to_choice(NearestGateChoice)

    self.assertCountEqual(gate_choice.choices, ["Roadhouse", "Cave"])
    self.assertIsNone(gate_choice.none_choice)
    gate_choice.resolve(self.state, "Cave")
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Pluto1")
    self.assertEqual(self.flier.place.name, "Northside")
    self.assertFalse(self.char.trophies)

  def testAsMonsterAppears(self):
    self.state.places["Cave"].gate = self.state.gates.popleft()
    self.char.place = self.state.places["Graveyard"]
    # Make sure there is only the flier in the monster cup.
    for monster in self.state.monsters:
      monster.place = None
    self.flier.place = self.state.monster_cup

    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.char.place.name, self.state.places["Cave"].gate.name + "1")
    self.assertEqual(self.flier.place, self.state.monster_cup)

  def testInAnotherWorld(self):
    # Open gates to the same place at the Woods and the Isle, and one gate to elsewhere at the Cave.
    self.state.places["Woods"].gate = self.state.gates.popleft()
    self.state.places["Isle"].gate = self.state.gates.popleft()
    self.state.places["Cave"].gate = self.state.gates.popleft()
    self.assertEqual(self.state.places["Woods"].gate.name, self.state.places["Isle"].gate.name)
    self.assertNotEqual(self.state.places["Cave"].gate.name, self.state.places["Isle"].gate.name)
    self.char.place = self.state.places[self.state.places["Woods"].gate.name + "1"]
    # Make sure there is only the flier in the monster cup.
    for monster in self.state.monsters:
      monster.place = None
    self.flier.place = self.state.monster_cup

    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      gate_choice = self.resolve_to_choice(GateChoice)

    self.assertCountEqual(gate_choice.choices, ["Woods", "Isle"])
    self.assertIsNone(gate_choice.none_choice)
    gate_choice.resolve(self.state, "Woods")
    self.resolve_until_done()

    self.assertEqual(self.flier.place, self.state.monster_cup)
    self.assertEqual(self.char.place.name, "Woods")

  def testAnotherWorldNoOpenGates(self):
    # Make sure there is only the flier in the monster cup.
    for monster in self.state.monsters:
      monster.place = None
    self.flier.place = self.state.monster_cup
    # Place the character in another world with no open gates.
    self.state.places["Woods"].gate = self.state.gates.popleft()
    self.assertNotEqual(self.state.places["Woods"].gate.name, "Pluto")
    self.char.place = self.state.places["Pluto1"]

    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    self.assertEqual(self.flier.place, self.state.monster_cup)
    self.assertEqual(self.char.place.name, "Pluto1")


class PinataCombatBaseTestMixin:

  def setUp(self):
    super().setUp()
    self.state.unique.extend([items.EnchantedKnife(0), items.HolyWater(0), items.MagicLamp(0)])
    self.char.place = self.state.places["Cave"]

  def testWin(self):
    combat = EvadeOrCombat(self.char, self.monster)
    self.state.event_stack.append(combat)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [item.handle for item in self.char.possessions])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertGains()
    self.assertIsNone(self.monster.place)
    self.assertNotIn(self.monster, self.char.trophies)

  def testFromMonsterAppears(self):
    for monster in self.state.monsters:
      monster.place = None
    self.monster.place = self.state.monster_cup
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [item.handle for item in self.char.possessions])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertGains()
    self.assertIsNone(self.monster.place)
    self.assertNotIn(self.monster, self.char.trophies)

  def testEvaded(self):
    self.char.speed_sneak_slider = 1
    combat = EvadeOrCombat(self.char, self.monster)
    self.state.event_stack.append(combat)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertNoGains()
    self.assertEqual(self.monster.place.name, "Cave")
    self.assertNotIn(self.monster, self.char.trophies)


class PinataCombatTest(PinataCombatBaseTestMixin, EventTest):

  def setUp(self):
    super().setUp()
    self.monster = monsters.Pinata()
    self.state.monsters.append(self.monster)
    self.state.monsters[-1].idx = len(self.state.monsters)-1
    self.state.monsters[-1].place = self.char.place

  def assertGains(self):
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].handle, "Enchanted Knife0")

  def assertNoGains(self):
    self.assertEqual(self.char.clues, 0)
    self.assertFalse(self.char.possessions)

  def testWithMythosActive(self):
    self.state.environment = mythos.Mythos2()
    combat = EvadeOrCombat(self.char, self.monster)
    self.state.event_stack.append(combat)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[0].name, "Enchanted Knife")
    self.assertEqual(self.char.possessions[1].name, "Holy Water")
    self.assertIsNone(self.monster.place)
    self.assertNotIn(self.monster, self.char.trophies)

  def testWithExtraDraw(self):
    self.char.possessions.append(abilities.Archaeology())
    combat = EvadeOrCombat(self.char, self.monster)
    self.state.event_stack.append(combat)
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      item_choice = self.resolve_to_choice(CardChoice)

    self.assertEqual(item_choice.choices, ["Enchanted Knife", "Holy Water"])
    item_choice.resolve(self.state, "Holy Water")
    self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual(self.char.possessions[1].handle, "Holy Water0")


class WarlockCombatTest(PinataCombatBaseTestMixin, EventTest):

  def setUp(self):
    super().setUp()
    self.monster = monsters.Warlock()
    self.state.monsters.append(self.monster)
    self.state.monsters[-1].idx = len(self.state.monsters)-1
    self.state.monsters[-1].place = self.char.place
    self.char.possessions.append(items.TommyGun(0))

  def assertGains(self):
    self.assertEqual(self.char.clues, 2)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].handle, "Tommy Gun0")

  def assertNoGains(self):
    self.assertEqual(self.char.clues, 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].handle, "Tommy Gun0")


class CombatOutputTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.extend([items.EnchantedKnife(0), items.Wither(0), items.Revolver38(0)])
    cultist = monsters.Cultist()
    self.combat = Combat(self.char, cultist)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

  def testCombatChoiceWithActivateItems(self):
    for _ in self.state.resolve_loop():
      if not isinstance(self.state.event_stack[-1], CombatChoice):
        data = self.state.for_player(0)
        self.assertIsNone(data["choice"])
    choose_weapons = self.state.event_stack[-1]
    self.assertIsInstance(choose_weapons, CombatChoice)
    data = self.state.for_player(0)
    self.assertIsNotNone(data["choice"])
    self.assertEqual(data["choice"].get("items"), ["Enchanted Knife0", ".38 Revolver0"])

    choose_weapons.resolve(self.state, "Enchanted Knife0")
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIsNotNone(data["choice"])
      self.assertEqual(data["choice"].get("items"), ["Enchanted Knife0", ".38 Revolver0"])
      self.assertIn("Enchanted Knife0", data["choice"].get("chosen"))

    choose_weapons = self.state.event_stack[-1]
    self.assertIsInstance(choose_weapons, CombatChoice)

    choose_weapons.resolve(self.state, ".38 Revolver0")
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIsNotNone(data["choice"])
      self.assertEqual(data["choice"].get("items"), ["Enchanted Knife0", ".38 Revolver0"])
      self.assertIn("Enchanted Knife0", data["choice"].get("chosen"))
      self.assertIn(".38 Revolver0", data["choice"].get("chosen"))

    choose_weapons = self.state.event_stack[-1]
    self.assertIsInstance(choose_weapons, CombatChoice)

    choose_weapons.resolve(self.state, "done")
    generator = self.state.resolve_loop()
    # These items should show up as chosen until we start processing the combat check.
    for _ in generator:
      data = self.state.for_player(0)
      if isinstance(self.state.event_stack[-1], CombatChoice) and self.state.event_stack[-1].done:
        break
      self.assertCountEqual(data["choice"]["chosen"], ["Enchanted Knife0", ".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      for _ in generator:
        data = self.state.for_player(0)
        self.assertIsNone(data["choice"])
        if isinstance(self.state.event_stack[-1], CombatRound) and self.state.event_stack[-1].done:
          break
        self.assertTrue(data["characters"][0]["possessions"][0].active)
        self.assertTrue(data["characters"][0]["possessions"][2].active)
        self.assertFalse(data["characters"][0]["possessions"][1].active)
    for _ in generator:
      self.assertIsNone(data["choice"])
    self.assertFalse(self.state.event_stack)


class ElderThingCombatTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.extend([items.Wither(0), items.Revolver38(0), items.DarkCloak(0)])
    self.thing = monsters.ElderThing()
    combat = EvadeOrCombat(self.char, self.thing)
    self.state.event_stack.append(combat)

  def testWeaponDeactivatesOnLoss(self):
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [".38 Revolver0"])
    # Lose the combat round.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      loss_choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    self.assertTrue(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertTrue(self.char.possessions[1].active)
    self.choose_items(loss_choice, [".38 Revolver0"])
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    # Validate that the player lost stamina, and that the revolver has been lost.
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertEqual([item.handle for item in self.char.possessions], ["Wither0", "Dark Cloak0"])
    # The spell should still be active, but not the revolver, which should be in the deck.
    self.assertTrue(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertFalse(self.char.possessions[1].active)  # The dark cloak.
    self.assertEqual(len(self.state.common), 1)
    self.assertEqual(self.state.common[0].name, ".38 Revolver")
    self.assertFalse(self.state.common[0].active)

  def testSpellDeactivatesOnLoss(self):
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [".38 Revolver0"])
    # Lose the combat round.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      loss_choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    self.assertTrue(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertTrue(self.char.possessions[1].active)
    self.choose_items(loss_choice, ["Wither0"])
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    # Validate that the player lost stamina, and that the wither spell has been lost.
    self.assertEqual(self.char.stamina, 4)
    self.assertEqual(len(self.char.possessions), 2)
    self.assertNotIn("Wither0", [item.handle for item in self.char.possessions])
    # Nothing should be active or exhausted.
    self.assertFalse(any(item.active for item in self.char.possessions))
    self.assertEqual(len(self.state.spells), 1)
    self.assertEqual(self.state.spells[0].name, "Wither")
    self.assertFalse(self.state.spells[0].active)
    self.assertFalse(self.state.spells[0].exhausted)

  def testDiscardOnEvadeFailure(self):
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      loss_choice = self.resolve_to_choice(WeaponOrSpellLossChoice)
    self.choose_items(loss_choice, ["Wither0"])
    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(len(self.char.possessions), 2)

  def testNoDiscardOnSuccess(self):
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)

    self.choose_items(combat_choice, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(len(self.char.trophies), 1)

  def testNoDiscardOnEvade(self):
    self.char.speed_sneak_slider = 0
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(len(self.char.possessions), 3)
    self.assertEqual(len(self.char.trophies), 0)

  def testNoDiscardableItems(self):
    self.char.possessions.clear()
    self.char.possessions.extend([assets.OldProfessor(), items.Deputy()])

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)

    self.choose_items(combat_choice, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)


class CombatWithItems(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.extend([items.TommyGun(0), items.Wither(0), items.Revolver38(0)])
    cultist = monsters.Cultist()
    self.combat = Combat(self.char, cultist)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

  def testCombatWithWeapon(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Tommy Gun0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(self.combat.combat.is_resolved())
    # Fight (4) + tommy gun (6) + cultist (1)
    self.assertEqual(len(self.combat.combat.check.roll), 11)
    self.assertFalse(self.char.possessions[0].active)

  def testCombatWithAxe(self):
    self.char.possessions.extend([items.Axe(0), items.Axe(1)])
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Axe0", ".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 10)  # Fight (4) + Axe (2) + Cultist (1) + Revolver (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Axe0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 8)  # Fight (4) + Axe (3) + Cultist (1)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Axe0", "Axe1"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 9)  # Fight (4) + Axe (2) + Axe (2) + Cultist (1)

    axe = self.char.possessions[-2]
    self.assertFalse(axe.active)
    self.assertEqual(axe.hands_used(), 0)

  def testFailedCombatWithAxe(self):
    self.char.stamina = 1
    axe = items.Axe(0)
    self.char.possessions.append(axe)
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Axe0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      lose_items = self.resolve_to_choice(ItemLossChoice)
      self.assertEqual(rand.call_count, 8)  # Fight (4) + Axe (3) + Cultist (1)

    self.choose_items(lose_items, [".38 Revolver0", "Wither0"])
    self.resolve_until_done()

    self.assertFalse(axe.active)
    self.assertEqual(axe.hands_used(), 0)

  def testCombatWithSpell(self):
    self.resolve_to_choice(CombatChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Wither0", self.state.usables[0])

    # Cast the spell.
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")

    # After casting the spell, we should return to our combat choice.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

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
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_weapons.resolve(self.state, "Wither0")

    self.state.event_stack.append(self.state.usables[0]["Wither0"])  # Cast the spell.
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")

    # After casting the spell, we should return to our combat choice.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    # Cannot choose the spell after using it.
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_weapons.resolve(self.state, "Wither0")

    self.assertEqual(self.char.hands_available(), 1)
    # Cannot choose a two-handed weapon when one hand is taken by a spell.
    with self.assertRaisesRegex(InvalidMove, "enough hands"):
      choose_weapons.resolve(self.state, "Tommy Gun0")

    choose_weapons.resolve(self.state, ".38 Revolver0")
    choose_weapons.resolve(self.state, "done")

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
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")

    # Fail to cast the spell - it should not be active, but it will still take hands.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    # Cannot choose a two-handed weapon when one hand is taken by a failed spell.
    with self.assertRaisesRegex(InvalidMove, "enough hands"):
      choose_weapons.resolve(self.state, "Tommy Gun0")

    self.choose_items(choose_weapons, [".38 Revolver0"])

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
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertFalse(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[1].in_use)
    self.assertTrue(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0"])

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
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")

    # Fail to cast the spell
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    self.assertFalse(self.state.usables)  # The spell should not be usable anymore.
    self.choose_items(choose_weapons, [])

    # Fail the combat check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertFalse(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Wither0", self.state.usables[0])

    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 2)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.choose_items(choose_weapons, ["Tommy Gun0"])

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
    revolver = self.char.possessions[2]
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(SpendChoice)
    cast.resolve(self.state, "Cast")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    self.assertTrue(self.char.possessions[1].active)
    self.choose_items(choose_weapons, [])

    # Fail the combat check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [".38 Revolver0"])
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Hospital")
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertNotIn(revolver, self.char.possessions)
    self.assertFalse(revolver.active)  # No longer in possessions, got discarded.

  def testInsaneBeforeCombat(self):
    self.char.possessions[1] = items.Shrivelling(0)
    revolver = self.char.possessions[2]
    self.char.sanity = 1

    self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0]["Shrivelling0"])
    cast = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, cast)
    cast.resolve(self.state, "Cast")

    # Attempting to spend your last sanity to cast this spell makes you go insane before combat.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, [".38 Revolver0"])
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Asylum")
    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertNotIn(revolver, self.char.possessions)
    self.assertFalse(revolver.active)

  def testNeedSanityToCast(self):
    # TODO: i think we can get rid of this now that we have SpendMixin
    self.char.possessions[1] = items.DreadCurse(0)
    self.char.sanity = 1

    self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.state.usables)

  def testCannotCastWithoutHands(self):
    choose_weapons = self.resolve_to_choice(CombatChoice)
    choose_weapons.resolve(self.state, "Tommy Gun0")
    self.resolve_to_choice(CombatChoice)

    self.assertEqual(choose_weapons.hands_used(), 2)
    self.assertNotIn(0, self.state.usables)

    choose_weapons.resolve(self.state, "Tommy Gun0")
    choose_weapons.resolve(self.state, ".38 Revolver0")
    self.resolve_to_choice(CombatChoice)

    self.assertEqual(choose_weapons.hands_used(), 1)
    self.assertIn(0, self.state.usables)
    self.assertIn("Wither0", self.state.usables[0])

  def testDontNeedSanityToDeactivate(self):
    self.char.possessions[1] = items.DreadCurse(0)
    self.char.sanity = 3

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.state.event_stack.append(self.state.usables[0]["Dread Curse0"])
    cast = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 2, cast)
    cast.resolve(self.state, "Cast")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.hands_available(), 0)
    self.assertFalse(self.state.usables)
    self.choose_items(choose_weapons, [])

    # Fail the combat check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_to_choice(FightOrEvadeChoice)  # fight or flee

    self.assertIn(0, self.state.usables)
    self.assertIn("Dread Curse0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Dread Curse0"])

    self.resolve_to_choice(FightOrEvadeChoice)
    self.assertFalse(self.state.usables)

    self.assertFalse(self.char.possessions[0].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertFalse(self.char.possessions[1].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[2].active)


class MonsterAppearsTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.place = self.state.places["Graveyard"]
    self.char.speed_sneak_slider = 2
    self.maniac = monsters.Maniac()
    self.state.monsters = [self.maniac]
    self.maniac.place = self.state.monster_cup

  def testEvadeMonster(self):
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(choice.monster, self.state.monsters[0])
    choice.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.state.monsters[0].place, self.state.monster_cup)
    self.assertFalse(self.char.trophies)

  def testFightMonster(self):
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(choice.monster, self.state.monsters[0])
    choice.resolve(self.state, "Fight")
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")
    choice = self.resolve_to_choice(CombatChoice)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertIsNone(self.state.monsters[0].place)
    self.assertEqual(len(self.char.trophies), 1)
    self.assertEqual(self.char.trophies[0], self.state.monsters[0])

  def testLoseToMonster(self):
    self.char.stamina = 1
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(choice.monster, self.state.monsters[0])
    choice.resolve(self.state, "Fight")
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")
    choice = self.resolve_to_choice(CombatChoice)
    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      loss_choice = self.resolve_to_choice(ItemChoice)
    loss_choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.state.monsters[0].place, self.state.monster_cup)
    self.assertFalse(self.char.trophies)
    self.assertEqual(self.char.place.name, "Hospital")

  def testNothingInSealedLocation(self):
    self.state.places["Graveyard"].sealed = True
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    self.resolve_until_done()

  def testNothingWithScientist(self):
    self.state.characters.append(self.state.all_characters["Scientist"])
    self.state.characters[-1].place = self.state.places["Graveyard"]
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    self.resolve_until_done()

  def testCanAppearInOtherWorlds(self):
    self.char.place = self.state.places["Dreamlands1"]
    appears = MonsterAppears(self.char)
    self.state.event_stack.append(appears)
    choice = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(choice.monster, self.state.monsters[0])
    choice.resolve(self.state, "Evade")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.state.monsters[0].place, self.state.monster_cup)
    self.assertFalse(self.char.trophies)


class AmbushTest(EventTest):

  def testAmbush(self):
    ghoul = monsters.Ghoul()
    self.assertTrue(ghoul.has_attribute("ambush", self.state, self.char))
    combat = Combat(self.char, ghoul)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    # Should not be able to flee - it's an ambush monster.
    output = self.state.for_player(0)
    self.assertEqual(output["choice"]["invalid_choices"], [1])
    self.assertIn("ambush", output["choice"]["monster"]["attributes"])
    with self.assertRaisesRegex(InvalidMove, "Ambush"):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 4)
    # Still should not be able to flee.
    with self.assertRaisesRegex(InvalidMove, "Ambush"):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")

  def testAmbushFromFailedEvade(self):
    ghoul = monsters.Ghoul()
    combat = EvadeOrCombat(self.char, ghoul)
    self.state.event_stack.append(combat)

    # Before you engage in combat, you may evade the ghoul.
    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Evade")

    # Fail the evade check, validate that we go straight to the next combat round.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    with self.assertRaisesRegex(InvalidMove, "Ambush"):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")


class ResistanceAndImmunityTest(EventTest):

  def testMagicalResistance(self):
    self.char.possessions.extend([
        items.TommyGun(0), items.EnchantedKnife(0), items.EnchantedKnife(1),
    ])
    witch = monsters.Witch()
    combat = Combat(self.char, witch)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    output = self.state.for_player(0)
    self.assertIn("magical resistance", output["choice"]["monster"]["attributes"])
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Enchanted Knife0"])  # choose a single enchanted knife
    self.assertEqual(self.char.fight(self.state), 4)
    self.assertEqual(witch.difficulty("combat", self.state, self.char), -3)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 3)  # Fight of 4, -3 combat rating, +2 enchanted knife.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Enchanted Knife0", "Enchanted Knife1"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      # Note that each knife gets its bonus of 3 cut in half and rounded up - they are calculated
      # separately as opposed to adding their bonuses together and then taking half.
      self.assertEqual(rand.call_count, 5)  # Fight of 4, -3 combat rating, +2 per enchanted knife.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Tommy Gun0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 7)  # Fight of 4, -3 combat rating, +6 for tommy gun.

  def testMagicalImmunity(self):
    self.char.possessions.extend([items.Revolver38(0), items.EnchantedKnife(0)])
    priest = monsters.HighPriest()
    combat = Combat(self.char, priest)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 2)  # Fight of 4, -2 combat rating, +0 enchanted knife.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0", "Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      # Note that each knife gets its bonus of 3 cut in half and rounded up - they are calculated
      # separately as opposed to adding their bonuses together and then taking half.
      self.assertEqual(rand.call_count, 5)  # Fight of 4, -2 combat rating, +3 revolver.

  def testOldProfessorNegatesMagicalResistance(self):
    self.char.possessions.extend([items.MagicLamp(0), assets.OldProfessor()])
    witch = monsters.Witch()
    combat = Combat(self.char, witch)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    output = self.state.for_player(0)
    self.assertNotIn("magical resistance", output["choice"]["monster"]["attributes"])
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Magic Lamp0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6)  # Fight of 4, -3 combat rating, +5 magic lamp.

  def testOldProfessorHasNoEffectOnMagicalImmunity(self):
    self.char.possessions.extend([items.MagicLamp(0), assets.OldProfessor()])
    priest = monsters.HighPriest()
    combat = Combat(self.char, priest)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Magic Lamp0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight of 4, -2 combat rating, +0 magic lamp.

  def testPhysicalResistance(self):
    self.char.possessions.extend([
        items.Revolver38(0), items.Revolver38(1), items.EnchantedKnife(0),
    ])
    vampire = monsters.Vampire()
    combat = Combat(self.char, vampire)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0", ".38 Revolver1"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 5)  # Fight of 4, -3 combat rating, +2 per revolver.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0", "Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6)  # Fight of 4, -3 combat rating, +3 knife, +2 revolver.

  def testPhysicalImmunity(self):
    self.char.possessions.extend([
        items.Revolver38(0), items.Revolver38(1), items.EnchantedKnife(0),
    ])
    ghost = monsters.Ghost()
    combat = Combat(self.char, ghost)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0", ".38 Revolver1"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 1)  # Fight of 4, -3 combat rating, +0 per revolver.

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver1", "Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight of 4, -3 combat rating, +3 knife, +0 revolver.

  def testPainterNegatesPhysicalResistance(self):
    self.char.possessions.extend([items.TommyGun(0), assets.VisitingPainter()])
    vampire = monsters.Vampire()
    combat = Combat(self.char, vampire)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Tommy Gun0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 7)  # Fight of 4, -3 combat rating, +6 tommy gun.

  def testPainterHasNoEffectOnPhysicalImmunity(self):
    self.char.possessions.extend([items.TommyGun(0), assets.VisitingPainter()])
    ghost = monsters.Ghost()
    combat = Combat(self.char, ghost)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Tommy Gun0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 1)  # Fight of 4, -3 combat rating, +0 tommy gun.


class NightmarishOverwhelmingTest(EventTest):

  def testOverwhelmingAndNightmarish(self):
    self.char.fight_will_slider = 0
    self.char.possessions.extend([items.EnchantedKnife(0), items.EnchantedKnife(1)])
    flier = monsters.SubterraneanFlier()
    combat = Combat(self.char, flier)
    self.state.event_stack.append(combat)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.will(self.state), 4)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    # Take sanity loss from nightmarish.
    self.assertTrue(combat.horror.is_resolved())
    self.assertTrue(combat.horror.successes)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)

    output = self.state.for_player(0)
    self.assertIn("overwhelming", output["choice"]["monster"]["attributes"])
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Enchanted Knife0", "Enchanted Knife1"])
    # I gotta say, this is pretty teriffic.

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # Take stamina loss from overwhelming.
    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 4)

  def testOverwhelmingOnSecondRound(self):
    self.char.possessions.extend([items.EnchantedKnife(0), items.EnchantedKnife(1)])
    beast = monsters.FurryBeast()
    combat = Combat(self.char, beast)
    self.state.event_stack.append(combat)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Enchanted Knife0", "Enchanted Knife1"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertFalse(combat.combat.is_resolved())
    self.assertFalse(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 1)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Enchanted Knife0", "Enchanted Knife1"])

    # Reset stamina to avoid dealing with going unconscious
    self.char.stamina = 5
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 4)

  def testBraveGuyNegatesNightmarish(self):
    self.char.fight_will_slider = 0
    self.char.possessions.extend([items.MagicLamp(0), assets.BraveGuy()])
    flier = monsters.SubterraneanFlier()
    combat = Combat(self.char, flier)
    self.state.event_stack.append(combat)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    # No sanity loss from nightmarish.
    self.assertTrue(combat.horror.is_resolved())
    self.assertTrue(combat.horror.successes)
    self.assertEqual(self.char.sanity, 5)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Magic Lamp0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    # Still take stamina loss from overwhelming.
    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 4)

  def testToughGuyNegatesOverwhelming(self):
    self.char.possessions.extend([items.MagicLamp(0), assets.ToughGuy()])
    beast = monsters.FurryBeast()
    combat = Combat(self.char, beast)
    self.state.event_stack.append(combat)
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    output = self.state.for_player(0)
    self.assertNotIn("overwhelming", output["choice"]["monster"]["attributes"])
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Magic Lamp0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat.combat.is_resolved())
    self.assertTrue(combat.combat.defeated)
    self.assertEqual(self.char.stamina, 5)


class UndeadTest(EventTest):

  def testUseCrossAgainstUndead(self):
    self.char.possessions.extend([items.Cross(0)])
    zombie = monsters.Zombie()
    combat = Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 3)  # Fight 4, -1 combat rating

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Cross0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6)  # Fight 4, -1 combat rating, +3 cross

  def testUseCrossAgainstLiving(self):
    self.char.possessions.extend([items.Cross(0)])
    cultist = monsters.Cultist()
    combat = Combat(self.char, cultist)
    self.state.event_stack.append(combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, ["Cross0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight 4, +1 combat rating


class CombatWithBullwhipTest(EventTest):

  def setUp(self):
    super().setUp()
    self.bullwhip = items.Bullwhip(0)
    self.char.possessions.extend([self.bullwhip, items.Axe(0), items.Knife(0)])

  def testUseBullwhip(self):
    priest = monsters.HighPriest()
    combat = Combat(self.char, priest)
    self.state.event_stack.append(combat)

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, ["Bullwhip0", "Axe0"])
    self.char.clues = 1
    # Fight (4) + Bullwhip (1) + Axe (2) + Priest (-2) = 5
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[3, 2, 4, 1, 5])):
      spend = self.resolve_to_choice(SpendChoice)
    self.assertIn(0, self.state.usables)
    self.assertIn("Bullwhip0", self.state.usables[0])
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 1)

    self.state.event_stack.append(self.state.usables[0]["Bullwhip0"])
    choose_die = self.resolve_to_choice(MultipleChoice)
    self.assertEqual(choose_die.choices, [3, 2, 4, 1, 5])
    choose_die.resolve(self.state, 1)
    with mock.patch.object(events.random, "randint", new=mock.Mock(return_value=4)):
      spend = self.resolve_to_choice(SpendChoice)
    self.assertEqual(check.roll, [3, 2, 4, 4, 5])
    self.assertEqual(check.successes, 1)
    # Now that the bullwhip has been used, its special ability cannot be used again.
    self.assertFalse(self.state.usables)
    spend.resolve(self.state, "Done")

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_evade.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    # You may still use the bullwhip in combat even when it is exhausted.
    self.choose_items(combat_choice, ["Bullwhip0", "Axe0"])
    with mock.patch.object(events.random, "randint", new=mock.Mock(return_value=6)) as rand:
      spend = self.resolve_to_choice(SpendChoice)
      self.assertEqual(rand.call_count, 5)
    self.assertFalse(self.state.usables)
    spend.resolve(self.state, "Done")
    self.resolve_until_done()


class CombatWithShotgunTest(EventTest):

  def setUp(self):
    super().setUp()
    self.shotgun = items.Shotgun(0)
    self.char.possessions.extend([self.shotgun, items.Axe(0), items.Knife(0)])

  def start(self, monster):
    # pylint: disable=attribute-defined-outside-init
    self.combat = Combat(self.char, monster)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choice = self.resolve_to_choice(CombatChoice)
    self.char.clues = 1
    return choice

  def testShotgunSixes(self):
    choice = self.start(monsters.Octopoid())
    self.choose_items(choice, ["Shotgun0"])
    # Fight (4) + Octopoid (-3) + Shotgun (4) = roll 5 dice
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 1, 1, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 2)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 2)  # Octopoid does 3 damage
    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Shotgun0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 6, 1, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 4)
    self.resolve_until_done()

  def testShotgunFives(self):
    choice = self.start(monsters.Octopoid())
    self.choose_items(choice, ["Shotgun0"])
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[5, 1, 1, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 1)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 2)
    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Shotgun0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[5, 4, 6, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 3)
    self.resolve_until_done()

  def testShotgunBlessed(self):
    self.char.bless_curse = 1
    choice = self.start(monsters.Octopoid())
    self.choose_items(choice, ["Shotgun0"])
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[5, 4, 1, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 2)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 2)
    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Shotgun0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[3, 4, 6, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 3)
    self.resolve_until_done()

  def testShotgunCursed(self):
    self.char.bless_curse = -1
    choice = self.start(monsters.Octopoid())
    self.choose_items(choice, ["Shotgun0"])
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 5, 1, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 2)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 2)
    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Shotgun0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 5, 6, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 4)
    self.resolve_until_done()

  def testNotHoldingShotgun(self):
    self.char.possessions.append(items.EnchantedBlade(0))
    choice = self.start(monsters.Octopoid())
    self.choose_items(choice, ["Enchanted Blade0"])
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 5, 4, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 2)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 2)
    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Enchanted Blade0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 5, 6, 1, 1])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 3)
    self.resolve_until_done()

  def testShotgunPhysicalImmunity(self):
    choice = self.start(monsters.FormlessSpawn())
    self.choose_items(choice, ["Shotgun0"])
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[5, 4])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 1)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    self.assertEqual(self.char.stamina, 3)
    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Shotgun0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 4])):
      spend = self.resolve_to_choice(SpendChoice)
      spend.resolve(self.state, "Done")
    check = self.state.event_stack[-2]
    self.assertIsInstance(check, Check)
    self.assertEqual(check.successes, 2)
    self.resolve_until_done()

  def testOtherChecksUnaffectedByShotgun(self):
    self.char.possessions.append(items.FleshWard(0))
    choice = self.start(monsters.FormlessSpawn())
    self.char.clues = 0
    self.choose_items(choice, ["Shotgun0"])

    # Fail the first combat check, and use flesh ward to avoid some stamina damage.
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[5, 4])):
      self.resolve_to_usable(0, "Flesh Ward0")
    cast = self.state.usables[0]["Flesh Ward0"]
    self.state.event_stack.append(cast)
    choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Cast")

    # Successfully cast flesh ward by rolling one 6.
    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 3])):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertIsNotNone(cast.check)
    self.assertEqual(cast.check.successes, 1)  # Shotgun has no effect on the spell check.
    self.assertEqual(self.char.stamina, 5)

    fight_or_flee.resolve(self.state, "Fight")
    weapon_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(weapon_choice, ["Shotgun0"])

    with mock.patch.object(events.random, "randint", new=mock.Mock(side_effect=[6, 4])):
      self.resolve_until_done()


class CombatWithEnchantedWeapon(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.extend([items.DarkCloak(0), items.Revolver38(0), items.EnchantWeapon(0)])
    spawn = monsters.FormlessSpawn()
    self.combat = Combat(self.char, spawn)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

  def testSuccessfulCast(self):
    self.char.possessions.append(items.MagicLamp(0))
    choose_weapons = self.resolve_to_choice(CombatChoice)

    # Cannot choose either a spell or the dark cloak.
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_weapons.resolve(self.state, "Dark Cloak0")
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_weapons.resolve(self.state, "Enchant Weapon0")

    self.assertCountEqual(self.state.usables[0].keys(), {"Enchant Weapon0"})
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])  # Cast enchant weapon.

    # Before casting the spell, we should get a choice of items.
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)

    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_enchant.resolve(self.state, "Dark Cloak0")  # Cannot choose dark cloak.
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_enchant.resolve(self.state, "Enchant Weapon0")  # Cannot choose itself.
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_enchant.resolve(self.state, "Magic Lamp0")  # Cannot choose a magic weapon.
    self.choose_items(choose_enchant, [".38 Revolver0"])  # Enchant the revolver.

    # Now that we've chosen, successfully cast the spell.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertTrue(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)  # Enchant weapon is handless.

    # We already cast on the revolver, now choose to use it
    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight (4) + spawn (-2) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testFailedToCast(self):
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      # Failed to cast the spell, so we should come back to the combat choice.
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + spawn (-2) + 0 (physical immunity)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testChangeItemChoice(self):
    self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.sanity, 3)
    # Replace the cloak with another valid weapon.
    self.char.possessions[0] = items.Revolver38(1)
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    choose_enchant.resolve(self.state, ".38 Revolver1")
    # Validate that spending has not begun.
    self.assertFalse(choose_enchant.is_resolved())
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.state.event_stack[-1], choose_enchant)
    # Deselect the first revolver and select the second one.
    choose_enchant.resolve(self.state, ".38 Revolver1")
    choose_enchant.resolve(self.state, ".38 Revolver0")
    choose_enchant.resolve(self.state, "done")
    self.assertTrue(choose_enchant.is_resolved())

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertTrue(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)
    self.choose_items(choose_weapons, [".38 Revolver0"])  # Choose the enchanted one.

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight (4) + spawn (-2) + 3 (enchanted revolver)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testAgainstMagicalImmunity(self):
    priest = monsters.HighPriest()
    self.combat = Combat(self.char, priest)
    self.state.event_stack.clear()
    self.state.event_stack.append(self.combat)
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    self.resolve_to_choice(CombatChoice)

    # Cast enchant weapon on the revolver. This is stupid, because you're fighting a monster
    # with magical immunity, and the revolver would be better used as a physical weapon. However,
    # it is a perfectly valid play, so we test that it correctly makes the revolver useless.
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertTrue(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)

    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + priest (-2) + 0 (magical immunity)

  def testNoValidWeapons(self):
    self.char.possessions[1] = items.EnchantWeapon(1)  # Replace the revolver.
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])  # Cast enchant weapon.
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.assertFalse(choose_enchant.choices)
    self.spend("sanity", 1, choose_enchant)
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):  # Cannot choose the other spell.
      choose_enchant.resolve(self.state, "Enchant Weapon1")
    self.spend("sanity", -1, choose_enchant)
    self.choose_items(choose_enchant, [])

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.char.possessions[2].active)
    self.assertEqual(self.char.hands_available(), 2)
    self.choose_items(choose_weapons, [])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + spawn (-2)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertFalse(self.char.possessions[2].exhausted)

  def testTwoCopies(self):
    self.char.possessions.extend([items.EnchantWeapon(1), items.Revolver38(1)])
    self.resolve_to_choice(CombatChoice)

    # Both copies should be usable.
    self.assertCountEqual(self.state.usables[0].keys(), {"Enchant Weapon0", "Enchant Weapon1"})
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])

    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    # Finish casting on the revolver.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    # Now, only the remaining copy should be usable.
    self.assertCountEqual(self.state.usables[0].keys(), {"Enchant Weapon1"})
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon1"])

    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    # Cannot choose the same item again - it is now magical.
    with self.assertRaisesRegex(InvalidMove, "Invalid choice"):
      choose_enchant.resolve(self.state, ".38 Revolver0")
    self.choose_items(choose_enchant, [".38 Revolver1"])

    # Cast on the other revolver.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.choose_items(choose_weapons, [".38 Revolver0", ".38 Revolver1"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 8)  # Fight (4) + spawn (-2) + revolvers (2*3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)
    self.assertFalse(self.char.possessions[3].active)
    self.assertFalse(self.char.possessions[3].in_use)
    self.assertTrue(self.char.possessions[3].exhausted)

  def testDeactivateEnchantWeapon(self):
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])

    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.choose_items(choose_weapons, [".38 Revolver0"])

    # Lose the first round of combat
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 5)  # Fight (4) + spawn (-2) + revolver (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    # Enchant weapon should still be active in the second round
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 5)  # Fight (4) + spawn (-2) + revolver (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)

    # Deactivate enchant weapon
    self.assertCountEqual(self.state.usables[0].keys(), {"Enchant Weapon0"})
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.choose_items(choose_weapons, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + spawn (-2) + revolver (0)

  def testGoInsaneWhileCastingEnchantWeapon(self):
    self.char.sanity = 1
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, ["Dark Cloak0"])
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Asylum")
    self.assertFalse(self.combat.combat.is_resolved())

    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertTrue(self.char.possessions[1].exhausted)

    self.assertEqual(self.char.possessions[0].active_bonuses["magical"], 0)
    self.assertEqual(self.char.possessions[0].active_bonuses["physical"], 3)

  def testEnchantWeaponDeactivatesOnCombatLoss(self):
    self.char.stamina = 1
    self.resolve_to_choice(CombatChoice)

    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.choose_items(choose_weapons, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, ["Dark Cloak0"])
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Hospital")

    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertTrue(self.char.possessions[1].exhausted)

    self.assertEqual(self.char.possessions[0].active_bonuses["magical"], 0)
    self.assertEqual(self.char.possessions[0].active_bonuses["physical"], 3)

  def testCannotUseEnchantWeaponInNextCombat(self):
    self.char.sanity = 6  # Cheat to make sure they don't go insane
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertCountEqual(self.state.usables[0].keys(), {"Enchant Weapon0"})
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.choose_items(choose_weapons, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight (4) + spawn (-2) + revolver (3)

    self.state.event_stack.append(Combat(self.char, monsters.FormlessSpawn()))
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertNotIn(0, self.state.usables)  # They have nothing they can use
    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + spawn (-2) + physical immunity (0)


class CombatWithMagicPowderTest(EventTest):
  def setUp(self):
    super().setUp()
    self.powder = items.MagicPowder(0)
    self.char.possessions.append(self.powder)

  def start(self, monster):
    # pylint: disable=attribute-defined-outside-init
    self.combat = Combat(self.char, monster)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    return self.resolve_to_choice(CombatChoice)

  def testUsePowder(self):
    self.assertEqual(self.char.sanity, 5)
    cultist = monsters.Cultist()
    combat_choice = self.start(cultist)
    self.choose_items(combat_choice, ["Magic Powder0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 14)
    self.assertEqual(self.char.sanity, 4)
    self.assertIn(cultist, self.char.trophies)
    self.assertNotIn(self.powder, self.char.possessions)
    self.assertIn(self.powder, self.state.unique)

  def testUsePowderFail(self):
    self.assertEqual(self.char.sanity, 5)
    cultist = monsters.Cultist()
    combat_choice = self.start(cultist)
    combat_choice.resolve(self.state, "Magic Powder0")
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.assertNotIn("Magic Powder0", combat_choice.choices)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()
    self.assertEqual(self.char.sanity, 4)
    self.assertIn(cultist, self.char.trophies)
    self.assertNotIn(self.powder, self.char.possessions)

  def testPowderInsane(self):
    self.char.sanity = 1
    cultist = monsters.Cultist()
    combat_choice = self.start(cultist)
    combat_choice.resolve(self.state, "Magic Powder0")
    combat_choice.resolve(self.state, "done")
    choice = self.resolve_to_choice(ItemLossChoice)
    choice.resolve(self.state, "done")
    self.resolve_until_done()
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertFalse(self.char.possessions)
    self.assertFalse(self.char.trophies)

  def testPowderAndWhiskey(self):
    self.char.possessions.append(items.Whiskey(0))
    cultist = monsters.Cultist()
    combat_choice = self.start(cultist)
    combat_choice.resolve(self.state, "Magic Powder0")
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_to_usable(0, "Whiskey0")
      self.assertEqual(rand.call_count, 14)
    self.state.event_stack.append(self.state.usables[0]["Whiskey0"])
    self.resolve_until_done()
    self.assertEqual(self.char.sanity, 5)
    self.assertIn(cultist, self.char.trophies)
    self.assertNotIn(self.powder, self.char.possessions)


class CombatWithRedSignTest(EventTest):

  def setUp(self):
    super().setUp()
    self.char.possessions.extend([items.EnchantedKnife(0), items.Revolver38(0), items.RedSign(0)])

  def start(self, monster):
    # pylint: disable=attribute-defined-outside-init
    self.combat = Combat(self.char, monster)
    self.state.event_stack.append(self.combat)

    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")

    return self.resolve_to_choice(CombatChoice)

  def testReducesToughness(self):
    vampire = monsters.Vampire()
    self.char.fight_will_slider = 0
    choose_weapons = self.start(vampire)
    self.assertEqual(vampire.toughness(self.state, self.char), 2)
    self.assertEqual(self.char.fight(self.state), 1)

    self.assertCountEqual(self.state.usables[0].keys(), {"Red Sign0"})
    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["physical resistance", "undead", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "physical resistance")

    # Finish casting the spell.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(vampire.toughness(self.state, self.char), 1)
    self.choose_items(choose_weapons, [".38 Revolver0"])

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

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "none")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(land_squid.toughness(self.state, self.char), 2)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + squid (-3) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testCancelCasting(self):
    vampire = monsters.Vampire()
    self.start(vampire)
    self.assertEqual(vampire.toughness(self.state, self.char), 2)
    orig_sanity = self.char.sanity  # May have lost some sanity during the horror check.

    self.assertCountEqual(self.state.usables[0].keys(), {"Red Sign0"})
    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["physical resistance", "undead", "none", "Cancel"])
    choose_ignore.resolve(self.state, "Cancel")

    self.resolve_to_choice(CombatChoice)
    self.assertEqual(vampire.toughness(self.state, self.char), 2)
    self.assertEqual(self.char.sanity, orig_sanity)
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertFalse(self.char.possessions[2].exhausted)

  def testCastFutilely(self):
    giant_insect = monsters.GiantInsect()
    self.start(giant_insect)
    self.assertEqual(giant_insect.toughness(self.state, self.char), 1)

    self.assertNotIn("Red Sign0", self.state.usables.get(0, {}))

  def testIgnoresMagicalResistance(self):
    witch = monsters.Witch()
    choose_weapons = self.start(witch)
    self.assertEqual(witch.toughness(self.state, self.char), 1)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["magical resistance", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "magical resistance")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(witch.toughness(self.state, self.char), 1)
    self.choose_items(choose_weapons, ["Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + witch (-3) + knife (3)

  def testCannotIgnoreMagicalImmunity(self):
    priest = monsters.HighPriest()
    choose_weapons = self.start(priest)
    self.assertEqual(priest.toughness(self.state, self.char), 2)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "none")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(priest.toughness(self.state, self.char), 1)
    self.choose_items(choose_weapons, ["Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + priest (-2) + knife (0)

  def testIgnoresOverwhelming(self):
    beast = monsters.FurryBeast()
    choose_weapons = self.start(beast)
    self.assertEqual(beast.toughness(self.state, self.char), 3)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["overwhelming", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "overwhelming")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(beast.toughness(self.state, self.char), 2)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    self.assertEqual(self.char.stamina, 5)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 5)  # Fight (4) + beast (-2) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(self.char.stamina, 5)

  def testIgnoresAmbush(self):
    ghoul = monsters.Ghoul()
    self.char.speed_sneak_slider = 0
    combat = Combat(self.char, ghoul)
    self.state.event_stack.append(combat)
    fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    with self.assertRaisesRegex(InvalidMove, "Ambush"):
      fight_or_flee.resolve(self.state, "Flee")
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.choose_items(choose_weapons, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    # Cannot flee because of ambush.
    with self.assertRaisesRegex(InvalidMove, "Ambush"):
      fight_or_flee.resolve(self.state, "Flee")

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["ambush", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "ambush")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)

    # Now that we've successfully cast the spell to ignore ambush, we can flee.
    fight_or_flee.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertFalse(combat.combat.is_resolved())
    self.assertTrue(combat.evade.is_resolved())
    self.assertTrue(combat.evade.evaded)
    self.assertFalse(self.char.possessions[2].active)
    self.assertFalse(self.char.possessions[2].in_use)
    self.assertTrue(self.char.possessions[2].exhausted)

  def testIgnoresUndead(self):
    zombie = monsters.Zombie()
    self.char.possessions[1] = items.Cross(0)
    choose_weapons = self.start(zombie)
    self.assertEqual(zombie.toughness(self.state, self.char), 1)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["undead", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "undead")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(zombie.toughness(self.state, self.char), 1)
    self.choose_items(choose_weapons, ["Cross0"])

    # The cross provides no bonus against the zombie because we are ignoring its undead attribute.
    # This is a dumb thing to do, but is still perfectly valid.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 3)  # Fight (4) + zombie (-1) + cross (0)

    self.assertTrue(self.combat.combat.is_resolved())

  def testTwoCopies(self):
    self.char.possessions.extend([items.RedSign(1), items.Cross(1)])
    scary = monsters.Monster(  # Nightmarish overwhelming monster with 3 toughness.
        "Scary", "normal", "moon", {"evade": 0, "horror": 0, "combat": 0},
        {"horror": 2, "combat": 2}, 3, None, {"horror": 1, "combat": 1},
    )
    self.state.event_stack.append(EvadeOrCombat(self.char, scary))

    fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertCountEqual(self.state.usables[0].keys(), {"Red Sign0", "Red Sign1"})
    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.assertEqual(choose_ignore.choices, ["nightmarish", "overwhelming", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "nightmarish")

    # Cast the first one.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_evade = self.resolve_to_choice(FightOrEvadeChoice)

    self.assertEqual(scary.toughness(self.state, self.char), 2)
    fight_or_evade.resolve(self.state, "Fight")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertCountEqual(self.state.usables[0].keys(), {"Red Sign1"})
    self.state.event_stack.append(self.state.usables[0]["Red Sign1"])
    choose_ignore = self.resolve_to_choice(SpendChoice)

    # Now that we're already ignoring nightmarish, it should not be an option.
    self.assertEqual(choose_ignore.choices, ["overwhelming", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "overwhelming")

    # Successfully cast the second one.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(scary.toughness(self.state, self.char), 1)

    self.choose_items(choose_weapons, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + scary (-0)

    self.assertEqual(self.char.sanity, 3)  # Lost 1 per cast of red sign.
    self.assertEqual(self.char.stamina, 5)

  def testWithToughGuy(self):
    self.char.possessions.append(assets.ToughGuy())  # Ignores overwhelming
    self.char.fight_will_slider = 1
    self.assertEqual(self.char.will(self.state), 3)
    flier = monsters.SubterraneanFlier()

    # Pass the horror check, or you won't have enough sanity to cast.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.start(flier)
    self.assertEqual(flier.toughness(self.state, self.char), 3)
    self.assertEqual(self.char.sanity, 4)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    # Overwhelming should not be in the list because the tough guy already ignores it.
    self.assertEqual(
        choose_ignore.choices, ["nightmarish", "physical resistance", "none", "Cancel"],
    )
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "physical resistance")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(flier.toughness(self.state, self.char), 2)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    self.assertEqual(self.char.stamina, 5)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (2) + flier (-3) + revolver (3) + tough guy (2)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(self.char.stamina, 5)

  def testWithPainter(self):
    self.char.possessions.append(assets.VisitingPainter())  # Ignores physical resistance
    self.char.fight_will_slider = 1
    self.assertEqual(self.char.will(self.state), 3)
    flier = monsters.SubterraneanFlier()

    # Pass the horror check, or you won't have enough sanity to cast.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.start(flier)
    self.assertEqual(flier.toughness(self.state, self.char), 3)
    self.assertEqual(self.char.sanity, 4)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    # Overwhelming should not be in the list because the tough guy already ignores it.
    self.assertEqual(choose_ignore.choices, ["nightmarish", "overwhelming", "none", "Cancel"])
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "overwhelming")

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(flier.toughness(self.state, self.char), 2)
    self.choose_items(choose_weapons, [".38 Revolver0"])

    self.assertEqual(self.char.stamina, 5)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (2) + flier (-3) + revolver (3)

    self.assertTrue(self.combat.combat.is_resolved())
    self.assertEqual(self.char.stamina, 5)

  def testWithEnchantWeapon(self):
    self.char.possessions.append(items.EnchantWeapon(0))
    witch = monsters.Witch()
    choose_weapons = self.start(witch)

    # Because you're a genius, you're going to cast enchant weapon on the revolver, and then use
    # the red sign to ignore magical resistance. Pure genius.
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    choose_enchant = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, choose_enchant)
    self.choose_items(choose_enchant, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    # Here's the red sign.
    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "magical resistance")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.choose_items(choose_weapons, [".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 4)  # Fight (4) + witch (-3) + revolver (3)

  def testDeactivate(self):
    witch = monsters.Witch()
    choose_weapons = self.start(witch)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "magical resistance")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertEqual(self.char.hands_available(), 1)
    self.choose_items(choose_weapons, ["Enchanted Knife0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      self.assertEqual(rand.call_count, 4)  # Fight (4) + witch (-3) + knife (3)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(self.char.hands_available(), 1)

    # Now, deactivate the spell and validate you have both hands available again.
    self.assertCountEqual(self.state.usables[0].keys(), {"Red Sign0"})
    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_weapons = self.resolve_to_choice(CombatChoice)
    self.assertEqual(self.char.hands_available(), 2)

    self.choose_items(choose_weapons, ["Enchanted Knife0", ".38 Revolver0"])

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 6)  # Fight (4) + witch (-3) + revolver (3) + knife (2)

  def testDeactivatesOnCombatLoss(self):
    self.char.stamina = 1
    witch = monsters.Witch()
    choose_weapons = self.start(witch)

    self.state.event_stack.append(self.state.usables[0]["Red Sign0"])
    choose_ignore = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 1, choose_ignore)
    choose_ignore.resolve(self.state, "magical resistance")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(CombatChoice)

    self.assertFalse(witch.has_attribute("magical resistance", self.state, self.char))
    self.choose_items(choose_weapons, ["Enchanted Knife0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      choice = self.resolve_to_choice(ItemLossChoice)
    self.choose_items(choice, ["Enchanted Knife0"])
    self.resolve_until_done()

    self.assertEqual(self.char.place.name, "Hospital")

    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[1].in_use)
    self.assertTrue(self.char.possessions[1].exhausted)
    # Techincally, you wouldn't call this again because the combat has ended. But it's a good
    # check to make sure that the effects of the spell are done.
    self.assertTrue(witch.has_attribute("magical resistance", self.state, self.char))


class BindMonsterTest(EventTest):
  def setUp(self):
    super().setUp()
    self.bind_monster = items.BindMonster(0)
    self.char.possessions = [self.bind_monster]

  def start(self, monster):
    # pylint: disable=attribute-defined-outside-init
    self.combat = Combat(self.char, monster)
    self.state.event_stack.append(self.combat)

    with mock.patch.object(
        events.random, "randint", new=mock.MagicMock(return_value=5)
    ):
      fight_or_flee = self.resolve_to_choice(FightOrEvadeChoice)
      fight_or_flee.resolve(self.state, "Fight")

      return self.resolve_to_choice(CombatChoice)

  def testSanePass(self):
    self.char.sanity = 4
    self.char.fight_will_slider = 0
    worm = monsters.GiantWorm()
    combat_choice = self.start(worm)
    self.assertEqual(self.char.sanity, 3)
    self.assertEqual(self.char.stamina, 5)
    self.state.event_stack.append(self.state.usables[0]["Bind Monster0"])
    cast_choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 2, cast_choice)
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    # Assert that the rest of the combat was bypassed and not resolved.
    if combat_choice.activate:
      self.assertFalse(combat_choice.activate.is_resolved())
    if self.combat.combat.check:
      self.assertFalse(self.combat.combat.check.is_resolved())
    if self.combat.combat.damage:
      self.assertFalse(self.combat.combat.damage.is_resolved())

    self.assertIn(worm, self.char.trophies)
    self.assertEqual(self.char.sanity, 1)
    self.assertEqual(self.char.stamina, 4)  # overwhelming
    self.assertNotIn(self.bind_monster, self.char.possessions)

  def testSanePassWarlock(self):
    self.char.sanity = 4
    self.char.fight_will_slider = 0
    warlock = monsters.Warlock()
    self.start(warlock)
    self.assertEqual(self.char.sanity, 4)
    self.assertEqual(self.char.stamina, 5)
    self.state.event_stack.append(self.state.usables[0]["Bind Monster0"])
    cast_choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 2, cast_choice)
    cast_choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertNotIn(warlock, self.char.trophies)
    self.assertEqual(self.char.sanity, 2)
    self.assertEqual(self.char.stamina, 5)
    self.assertNotIn(self.bind_monster, self.char.possessions)
    self.assertEqual(self.char.clues, 2)

  def testInsanePass(self):
    self.char.sanity = 3
    self.char.fight_will_slider = 0
    worm = monsters.GiantWorm()
    combat_choice = self.start(worm)
    self.assertEqual(self.char.sanity, 2)  # Lost one to nightmarish
    self.assertEqual(self.char.stamina, 5)
    self.state.event_stack.append(self.state.usables[0]["Bind Monster0"])
    cast_choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 2, cast_choice)
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      insane_choice = self.resolve_to_choice(ItemLossChoice)
    insane_choice.resolve(self.state, "done")

    # Assert that the rest of the combat was bypassed and not resolved.
    if combat_choice.activate:
      self.assertFalse(combat_choice.activate.is_resolved())
    if self.combat.combat.check:
      self.assertFalse(self.combat.combat.check.is_resolved())
    if self.combat.combat.damage:
      self.assertFalse(self.combat.combat.damage.is_resolved())

    self.resolve_until_done()
    self.assertIn(worm, self.char.trophies)
    self.assertEqual(self.char.place.name, "Asylum")
    self.assertNotIn(self.bind_monster, self.char.possessions)
    self.assertEqual(self.char.stamina, 4)  # Overwhelming 1

  def testSaneFail(self):
    self.char.sanity = 3
    self.char.fight_will_slider = 0
    self.char.possessions.append(items.TommyGun(0))
    cultist = monsters.Cultist()
    self.start(cultist)
    self.assertEqual(self.char.sanity, 3)
    self.state.event_stack.append(self.state.usables[0]["Bind Monster0"])
    cast_choice = self.resolve_to_choice(SpendChoice)
    self.spend("sanity", 2, cast_choice)
    choice = self.resolve_to_choice(SpendChoice)
    choice.resolve(self.state, "Cast")
    with mock.patch.object(
        events.random, "randint", new=mock.MagicMock(return_value=4)
    ):
      choice = self.resolve_to_choice(CombatChoice)

    with self.assertRaisesRegex(InvalidMove, "enough hands"):
      # We already used our hands
      choice.resolve(self.state, "Tommy Gun0")

    choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)):
      choice = self.resolve_to_choice(FightOrEvadeChoice)
    choice.resolve(self.state, "Fight")

    self.state.event_stack.append(DeactivateSpell(self.char, self.bind_monster))
    choice = self.resolve_to_choice(CombatChoice)
    self.assertNotIn("Bind Monster0", choice.choices)
    self.assertFalse(self.state.usables)
    choice.resolve(self.state, "Tommy Gun0")
    choice.resolve(self.state, "done")

    with mock.patch.object(
        events.random, "randint", new=mock.MagicMock(return_value=5)
    ):
      self.resolve_until_done()
    self.assertIn(cultist, self.char.trophies)
    self.assertEqual(self.char.sanity, 1)
    self.assertIn(self.bind_monster, self.char.possessions)
    self.assertTrue(self.bind_monster.exhausted)

  def testNotUsableInBankRobbery(self):
    # Also presumably in the Hospital2 encounter
    self.state.event_stack.append(encounters.Bank3(self.char))
    self.resolve_to_choice(CombatChoice)
    self.assertNotIn("Bind Monster0", self.state.usables)

  # TODO: test when a successful cast drives you insane, and the monster is overwhelming,
  #  thus devouring you


class FightAncientOneTest(EventTest):

  def setUp(self):
    super().setUp()
    self.state.game_stage = "awakened"
    self.state.turn_phase = "attack"
    self.state.ancient_one.health = 20
    self.state.ancient_one._combat_rating = -2  # pylint: disable=protected-access

  def testBasicCombat(self):
    self.state.event_stack.append(InvestigatorAttack(self.char))
    combat_choice = self.resolve_to_choice(CombatChoice)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)  # Fight (4) + combat rating (-2)
    self.assertEqual(self.state.ancient_one.health, 18)  # Two successes

  def testCombatResistances(self):
    self.state.ancient_one._attributes |= {"magical resistance", "physical resistance"}
    self.state.event_stack.append(InvestigatorAttack(self.char))
    self.char.possessions.extend([items.Revolver38(0), items.EnchantedKnife(0)])
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.choose_items(combat_choice, [".38 Revolver0", "Enchanted Knife0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      # Fight (4) + Combat rating (-2) + Revolver (2) + Knife (2)
      self.assertEqual(rand.call_count, 6)
    self.assertEqual(self.state.ancient_one.health, 14)

  def testCombatWithWeirdItems(self):
    self.state.event_stack.append(InvestigatorAttack(self.char))
    self.char.possessions.extend([items.RedSign(0), items.BindMonster(0), items.BlueWatcher(0)])
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.assertFalse(self.state.usables)
    combat_choice.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.resolve_until_done()
      self.assertEqual(rand.call_count, 2)
    self.assertEqual(self.state.ancient_one.health, 20)

  def testCombatWithNormalSpells(self):
    self.state.ancient_one._attributes |= {"physical resistance"}
    self.state.event_stack.append(InvestigatorAttack(self.char))
    self.char.possessions.extend([items.Wither(0), items.EnchantWeapon(0), items.Revolver38(0)])
    combat_choice = self.resolve_to_choice(CombatChoice)
    self.assertCountEqual(["Wither0", "Enchant Weapon0"], self.state.usables[0].keys())
    self.state.event_stack.append(self.state.usables[0]["Enchant Weapon0"])
    weapon_choice = self.resolve_to_choice(SinglePhysicalWeaponChoice)
    self.spend("sanity", 1, weapon_choice)
    self.choose_items(weapon_choice, [".38 Revolver0"])

    # Successfully cast
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      combat_choice = self.resolve_to_choice(CombatChoice)

    self.assertCountEqual(["Wither0"], self.state.usables[0].keys())
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast_choice = self.resolve_to_choice(MultipleChoice)
    cast_choice.resolve(self.state, "Cast")

    # Successfully cast
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      combat_choice = self.resolve_to_choice(CombatChoice)

    self.choose_items(combat_choice, [".38 Revolver0"])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
      # Fight (4) + combat rating (-2) + enchanted revolver (3) + wither (3)
      self.assertEqual(rand.call_count, 8)
    self.assertEqual(self.state.ancient_one.health, 12)

    self.assertTrue(self.char.possessions[0].exhausted)
    self.assertFalse(self.char.possessions[0].active)
    self.assertTrue(self.char.possessions[1].exhausted)
    self.assertFalse(self.char.possessions[1].active)
    self.assertFalse(self.char.possessions[2].active)


if __name__ == "__main__":
  unittest.main()
