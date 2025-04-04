#!/usr/bin/env python3

import json
import os
import sys
import unittest
from unittest import mock

# Hack to allow the test to be run directly instead of invoking python from the base dir.
if os.path.abspath(sys.path[0]) == os.path.dirname(os.path.abspath(__file__)):
  sys.path[0] = os.path.dirname(sys.path[0])

from eldritch.allies import base as allies
from eldritch.ancient_ones import base as ancient_ones
from eldritch.ancient_ones.core import DummyAncient
from eldritch import characters
from eldritch.characters import base as base_characters
from eldritch import eldritch
from eldritch.encounters.location.core import EncounterCard
from eldritch.encounters.location import base as encounters
from eldritch.encounters.gate.core import GateCard
from eldritch.encounters.gate import base as gate_encounters
from eldritch import events
from eldritch import items
from eldritch import location_specials
from eldritch.monsters import base as monsters
from eldritch.mythos import base as mythos
from eldritch.mythos.core import GlobalEffect
from eldritch.skills import base as skills
from eldritch import specials
from eldritch import values
import game


class NoMythos(GlobalEffect):
  def __init__(self):
    self.name = "NoMythos"

  def create_event(self, state):  # pylint: disable=unused-argument
    return events.Nothing()


class PauseMythos(GlobalEffect):
  def __init__(self):
    self.name = "PauseMythos"

  def create_event(self, state):  # pylint: disable=unused-argument
    return events.MultipleChoice(state.characters[0], "", ["PauseMythos"])


class DevourFirstPlayer(GlobalEffect):
  def __init__(self):
    self.name = "DevourFirstPlayer"

  def create_event(self, state):
    return events.Devoured(state.characters[0])


class FixedEncounterBaseTest(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.all_characters.update({"Nun": base_characters.Nun()})
    self.state.characters = [self.state.all_characters["Nun"]]
    self.char = self.state.characters[0]
    facilities = location_specials.CreateFixedEncounters()
    for location_name, fixed_encounters in facilities.items():
      self.state.places[location_name].fixed_encounters.extend(fixed_encounters)
    self.state.game_stage = "slumber"
    self.state.turn_phase = "encounter"
    self.state.turn_number = 0


class RestorationFixedEncounterTest(FixedEncounterBaseTest):
  def testRegainStamina(self):
    self.char.stamina = 3
    self.char.dollars = 2
    self.char.place = self.state.places["Hospital"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Uptown Card", "Restore 1 Stamina", "Restore All Stamina"])
    self.assertCountEqual(event.invalid_choices.keys(), [1, 2])
    self.assertEqual(event.remaining_spend, [False, False, {"dollars": 2}])
    self.char.stamina = 1
    for _ in self.state.resolve_loop():
      pass
    self.assertCountEqual(event.invalid_choices.keys(), [])
    self.assertEqual(event.remaining_spend, [False, False, {"dollars": 2}])
    event.resolve(self.state, "Restore 1 Stamina")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)
    self.assertEqual(self.char.stamina, 2)
    self.assertEqual(self.char.dollars, 2)

  def testRegainAllStamina(self):
    self.char.stamina = 1
    self.char.dollars = 2
    self.char.place = self.state.places["Hospital"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Uptown Card", "Restore 1 Stamina", "Restore All Stamina"])
    self.assertCountEqual(event.invalid_choices.keys(), [])
    self.assertEqual(event.remaining_spend, [False, False, {"dollars": 2}])
    for _ in range(2):
      event.spend("dollars")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(event.remaining_spend, [{"dollars": -2}, {"dollars": -2}, False])
    event.resolve(self.state, "Restore All Stamina")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.dollars, 0)

  def testIgnoreFixedEncounters(self):
    self.char.stamina = 1
    self.char.dollars = 2
    self.char.place = self.state.places["Hospital"]
    self.state.places["Uptown"].encounters.append(
      EncounterCard("Uptown5", {"Hospital": encounters.Shoppe5})
    )
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Uptown Card", "Restore 1 Stamina", "Restore All Stamina"])
    event.resolve(self.state, "Uptown Card")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)
    self.assertEqual(self.char.stamina, 1)
    self.assertEqual(self.char.dollars, 2)
    self.assertEqual(self.char.clues, 1)


class DrawCardsFixedEncounterTest(FixedEncounterBaseTest):
  def setUp(self):
    super().setUp()
    self.state.common.extend([items.Cross(0), items.Food(0), items.DarkCloak(0), items.TommyGun(0)])
    self.state.unique.extend([items.HolyWater(0), items.EnchantedKnife(0), items.MagicLamp(0)])

  def testDrawUniqueEncounter(self):
    self.char.dollars = 1
    self.char.place = self.state.places["Shop"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Northside Card", "unique"])
    self.assertFalse(event.invalid_choices)
    event.resolve(self.state, "unique")
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Holy Water", "Enchanted Knife", "Magic Lamp", "Nothing"])
    event.resolve(self.state, "Nothing")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)

  def testDrawCommonEncounter(self):
    self.char.dollars = 1
    self.char.place = self.state.places["Store"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Rivertown Card", "common"])
    event.resolve(self.state, "common")
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Cross", "Food", "Dark Cloak", "Nothing"])
    with self.assertRaisesRegex(game.InvalidMove, "must purchase"):
      event.resolve(self.state, "Nothing")
    event.spend("dollars")
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "Food")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)

  def testIgnoreDrawEncounter(self):
    self.char.dollars = 1
    self.char.place = self.state.places["Store"]
    self.state.places["Rivertown"].encounters.append(
      EncounterCard("Rivertown1", {"Store": encounters.Store1})
    )
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Rivertown Card", "common"])
    event.resolve(self.state, "Rivertown Card")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)
    self.assertEqual(self.char.dollars, 2)

  def testDrawEncounterInvalidWithoutMoney(self):
    self.char.dollars = 0
    self.char.place = self.state.places["Store"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Rivertown Card", "common"])
    self.assertCountEqual(event.invalid_choices.keys(), [1])


class SpendTrophiesEncounterTest(FixedEncounterBaseTest):
  def setUp(self):
    super().setUp()
    self.char.trophies.append(self.state.gates.popleft())

  def testGainDollars(self):
    self.char.dollars = 0
    self.char.place = self.state.places["Docks"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Merchant Card", "Gain $5"])
    with self.assertRaisesRegex(game.InvalidMove, "additional 5 toughness"):
      event.resolve(self.state, "Gain $5")

    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "Gain $5")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(self.char.dollars, 5)

  def testGainClues(self):
    self.char.place = self.state.places["Science"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["University Card", "Gain 2 clues"])
    with self.assertRaisesRegex(game.InvalidMove, "additional 5 toughness"):
      event.resolve(self.state, "Gain 2 clues")

    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "Gain 2 clues")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(self.char.clues, 2)

  def testGetBlessed(self):
    self.char.place = self.state.places["Church"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Southside Card", "Blessing"])
    with self.assertRaisesRegex(game.InvalidMove, "additional 5 toughness"):
      event.resolve(self.state, "Blessing")

    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "Blessing")
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    choice = self.state.event_stack[-1]
    self.assertIsInstance(choice, events.MultipleChoice)
    self.assertEqual(choice.choices, ["Nun"])
    choice.resolve(self.state, "Nun")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(self.char.bless_curse, 1)

  def testBlessSomeoneElse(self):
    dead = characters.Character("Dead", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Train")
    dead.gone = True  # Represents a currently devoured character.
    self.state.all_characters["Dead"] = dead
    self.state.characters.append(dead)
    buddy = characters.Character("Buddy", 5, 5, 4, 4, 4, 4, 4, 4, 4, "Square")
    buddy.place = self.state.places["Dreamlands1"]
    self.state.all_characters["Buddy"] = buddy
    self.state.characters.append(buddy)
    self.char.place = self.state.places["Church"]

    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    choice = self.state.event_stack[-1]
    self.assertEqual(choice.choices, ["Southside Card", "Blessing"])
    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    choice.resolve(self.state, "Blessing")
    for _ in self.state.resolve_loop():
      pass
    choice = self.state.event_stack[-1]
    self.assertIsInstance(choice, events.MultipleChoice)
    self.assertCountEqual(choice.choices, ["Nun", "Buddy"])
    choice.resolve(self.state, "Buddy")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(self.char.bless_curse, 0)
    self.assertEqual(buddy.bless_curse, 1)

  def testGainAlly(self):
    self.char.trophies.append(self.state.gates.popleft())
    self.char.place = self.state.places["House"]
    self.state.allies.extend([allies.Dog(), allies.ToughGuy(), allies.BraveGuy()])
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Southside Card", "allies"])
    with self.assertRaisesRegex(game.InvalidMove, "additional 10 toughness"):
      event.resolve(self.state, "allies")

    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    self.state.handle_use(0, self.char.trophies[1].handle)
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "allies")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(len(self.char.trophies), 0)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardChoice)
    self.assertNotIsInstance(event, events.SpendMixin)
    self.assertTrue(event.sort_uniq)
    event.resolve(self.state, "Dog")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)
    self.assertEqual(self.char.possessions[0].name, "Dog")

  def testBecomeDeputized(self):
    self.state.specials.append(specials.Deputy())
    self.state.tradables.extend([specials.DeputysRevolver(), specials.PatrolWagon()])
    self.char.trophies.append(self.state.gates.popleft())
    self.char.place = self.state.places["Police"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Easttown Card", "Deputy"])
    with self.assertRaisesRegex(game.InvalidMove, "additional 10 toughness"):
      event.resolve(self.state, "Deputy")

    self.state.handle_use(0, self.char.trophies[1].handle)
    for _ in self.state.resolve_loop():
      pass
    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "Deputy")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)
    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(len(self.char.possessions), 3)
    self.assertCountEqual(
      [card.name for card in self.char.possessions], ["Deputy", "Deputy's Revolver", "Patrol Wagon"]
    )

  def testCannotBecomeDeputyIfSomeoneElseIs(self):
    self.assertIn("Deputy", [c.name for c in self.state.specials])
    deputy = next(c for c in self.state.specials if c.name == "Deputy")
    self.state.specials.remove(deputy)

    self.state.tradables.extend([specials.DeputysRevolver(), specials.PatrolWagon()])
    self.char.trophies.append(self.state.gates.popleft())
    self.char.place = self.state.places["Police"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Easttown Card", "Deputy"])
    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    self.state.handle_use(0, self.char.trophies[1].handle)
    for _ in self.state.resolve_loop():
      pass
    with self.assertRaisesRegex(game.InvalidMove, "already the deputy"):
      event.resolve(self.state, "Deputy")

  def testBecomeDeputyMissingDeputyItems(self):
    self.state.specials.append(specials.Deputy())
    self.char.trophies.append(self.state.gates.popleft())
    self.char.place = self.state.places["Police"]
    self.state.event_stack.append(events.EncounterPhase(self.char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    event = self.state.event_stack[-1]
    self.assertIsInstance(event, events.CardSpendChoice)
    self.assertEqual(event.choices, ["Easttown Card", "Deputy"])

    self.state.handle_use(0, self.char.trophies[0].handle)
    for _ in self.state.resolve_loop():
      pass
    self.state.handle_use(0, self.char.trophies[1].handle)
    for _ in self.state.resolve_loop():
      pass
    event.resolve(self.state, "Deputy")
    for _ in self.state.resolve_loop():
      pass
    self.assertFalse(self.state.event_stack)

    self.assertEqual(len(self.char.trophies), 0)
    self.assertEqual(len(self.char.possessions), 1)
    self.assertEqual(self.char.possessions[0].name, "Deputy")


class GateTravelTest(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.all_characters.update({"Nun": base_characters.Nun()})
    self.state.characters = [self.state.all_characters["Nun"]]
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.mythos.clear()
    self.state.mythos.append(mythos.Mythos5())
    self.state.event_stack.append(events.Mythos(None))  # Opens at the Square.
    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
    # Return all monsters to the cup so the character doesn't have to fight/evade.
    for mon in self.state.monsters:
      mon.place = self.state.monster_cup
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
    self.state.test_mode = False

  def testMoveToOtherWorld(self):
    char = self.state.characters[0]
    self.assertTrue(self.state.places["Square"].gate)
    world_name = self.state.places["Square"].gate.name
    gate_handle = self.state.places["Square"].gate.handle

    self.assertFalse(self.state.event_stack)
    self.state.turn_phase = "movement"
    char.place = self.state.places["Square"]
    movement = events.Movement(char)
    movement.done = True
    self.state.event_stack.append(movement)
    self.assertEqual(self.state.turn_idx, 0)

    for _ in self.state.resolve_loop():
      if self.state.turn_idx != 0 or self.state.turn_phase not in ("movement", "encounter"):
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertEqual(char.place.name, world_name + "1")
    self.assertEqual(char.entered_gate, gate_handle)
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.OtherWorldPhase)

  def testOtherWorldMovement(self):
    self.state.gate_cards.extend(gate_encounters.CreateGateCards())
    char = self.state.characters[0]
    char.place = self.state.places["City1"]
    char.entered_gate = "Gate City0"
    self.state.turn_phase = "upkeep"
    upkeep = events.Upkeep(char)
    upkeep.done = True
    self.state.event_stack.append(upkeep)
    for _ in self.state.resolve_loop():
      if self.state.turn_idx != 0 or self.state.turn_phase in ("mythos", "otherworld"):
        break
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertEqual(char.place.name, "City2")
    self.assertEqual(char.entered_gate, "Gate City0")

  def testReturnFromOtherWorld(self):
    char = self.state.characters[0]
    world_name = self.state.places["Square"].gate.name
    char.place = self.state.places[world_name + "2"]
    char.entered_gate = f"Gate {world_name}0"
    self.state.turn_phase = "upkeep"
    upkeep = events.Upkeep(char)
    upkeep.done = True
    self.state.event_stack.append(upkeep)
    for _ in self.state.resolve_loop():
      pass

    self.assertEqual(self.state.turn_phase, "encounter")
    self.assertEqual(char.place.name, "Square")
    self.assertIsNone(char.entered_gate)
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.assertEqual(self.state.event_stack[-1].prompt(), "Close the gate?")

  def testReturnFromOtherWorldMultipleChoices(self):
    world_name = self.state.places["Square"].gate.name
    self.state.places["Graveyard"].gate = self.state.gates.popleft()
    self.assertEqual(self.state.places["Graveyard"].gate.name, world_name)

    char = self.state.characters[0]
    char.place = self.state.places[world_name + "2"]
    self.state.turn_phase = "upkeep"
    upkeep = events.Upkeep(char)
    upkeep.done = True
    self.state.event_stack.append(upkeep)
    for _ in self.state.resolve_loop():
      pass

    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.GateChoice)
    self.state.event_stack[-1].resolve(self.state, "Square")
    for _ in self.state.resolve_loop():
      pass

    self.assertEqual(self.state.turn_phase, "encounter")
    self.assertEqual(char.place.name, "Square")
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.assertEqual(self.state.event_stack[-1].prompt(), "Close the gate?")


class TradingTestBase(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    for name in ["Nun", "Gangster"]:
      self.state.all_characters[name] = getattr(base_characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    self.nun = self.state.characters[0]
    self.gangster = self.state.characters[1]
    self.nun.possessions.extend([items.Cross(0), skills.Bravery(0)])
    self.gangster.possessions.extend([items.TommyGun(0), skills.Marksman(0)])
    self.state.game_stage = "slumber"
    self.state.turn_phase = "movement"
    self.state.turn_number = 0
    self.state.test_mode = False
    self.state.event_stack.append(events.Movement(self.nun))


class TradingTest(TradingTestBase):
  def setUp(self):
    super().setUp()
    for char in self.state.characters:
      char.place = self.state.places["Southside"]
    for _ in self.state.resolve_loop():
      pass

  def testGiveItem(self):
    self.assertEqual(len(self.nun.possessions), 2)
    self.assertEqual(len(self.gangster.possessions), 2)
    self.state.handle_give(0, 1, "Cross0", None)
    self.assertEqual([pos.name for pos in self.nun.possessions], ["Bravery"])
    self.assertEqual(
      [pos.name for pos in self.gangster.possessions], ["Tommy Gun", "Marksman", "Cross"]
    )

  def testGiveDollars(self):
    self.nun.dollars = 3
    self.gangster.dollars = 2
    self.state.handle_give(0, 1, "dollars", 2)
    self.assertEqual(self.nun.dollars, 1)
    self.assertEqual(self.gangster.dollars, 4)

  def testGiveInvalidDollars(self):
    self.nun.dollars = 3
    self.gangster.dollars = 2
    with self.assertRaisesRegex(game.InvalidMove, "Invalid quantity"):
      self.state.handle_give(0, 1, "dollars", 4)
    with self.assertRaisesRegex(game.InvalidMove, "Invalid quantity"):
      self.state.handle_give(0, 1, "dollars", -1)
    with self.assertRaisesRegex(game.InvalidMove, "Invalid quantity"):
      self.state.handle_give(0, 1, "dollars", 1.5)
    with self.assertRaisesRegex(game.InvalidMove, "Invalid quantity"):
      self.state.handle_give(0, 1, "dollars", None)
    self.assertEqual(self.nun.dollars, 3)
    self.state.handle_give(0, 1, "dollars", 3)
    self.assertEqual(self.nun.dollars, 0)
    self.assertEqual(self.gangster.dollars, 5)

  def testGiveInvalidItem(self):
    with self.assertRaisesRegex(game.InvalidMove, "only trade items"):
      self.state.handle_give(0, 1, "Bravery0", None)
    with self.assertRaisesRegex(game.InvalidMove, "Invalid card"):
      self.state.handle_give(0, 1, "clues", 1)
    with self.assertRaisesRegex(game.InvalidMove, "Invalid card"):
      self.state.handle_give(0, 1, "nonsense", None)
    with self.assertRaisesRegex(game.InvalidMove, "Invalid card"):
      self.state.handle_give(0, 1, 0, None)
    self.assertEqual([pos.name for pos in self.nun.possessions], ["Cross", "Bravery"])
    self.assertEqual([pos.name for pos in self.gangster.possessions], ["Tommy Gun", "Marksman"])

  def testGiveInvalidRecipient(self):
    with self.assertRaisesRegex(game.InvalidMove, "trade with yourself"):
      self.state.handle_give(0, 0, "Cross0", None)
    with self.assertRaisesRegex(game.InvalidPlayer, "Invalid recipient"):
      self.state.handle_give(0, 2, "Cross0", None)
    with self.assertRaisesRegex(game.InvalidPlayer, "Invalid recipient"):
      self.state.handle_give(0, -1, "Cross0", None)
    with self.assertRaisesRegex(game.InvalidPlayer, "Invalid recipient"):
      self.state.handle_give(0, "Gangster", "Cross0", None)
    self.assertEqual([pos.name for pos in self.nun.possessions], ["Cross", "Bravery"])
    self.assertEqual([pos.name for pos in self.gangster.possessions], ["Tommy Gun", "Marksman"])

  def testGiveInvalidTime(self):
    self.state.monsters.append(monsters.Cultist())
    self.state.monsters[0].place = self.state.places["Southside"]
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      pass

    # Choice to fight or evade the cultist.
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    # Cannot trade items during combat.
    with self.assertRaisesRegex(game.InvalidMove, "at this time"):
      self.state.handle_give(0, 1, "Cross0", None)

  def testGiveOtherLocation(self):
    self.nun.place = self.state.places["Church"]
    with self.assertRaisesRegex(game.InvalidMove, "same place"):
      self.state.handle_give(0, 1, "Cross0", None)

  def testTradability(self):
    self.gangster.possessions.extend(
      [specials.Deputy(), specials.DeputysRevolver(), specials.PatrolWagon()]
    )
    self.assertEqual(len(self.nun.possessions), 2)
    self.assertEqual(len(self.gangster.possessions), 5)
    self.state.handle_give(1, 0, "Patrol Wagon", None)
    self.assertEqual(len(self.nun.possessions), 3)
    self.assertEqual(len(self.gangster.possessions), 4)
    self.assertEqual(self.nun.possessions[-1].name, "Patrol Wagon")
    self.state.handle_give(1, 0, "Deputy's Revolver", None)
    self.assertEqual(len(self.nun.possessions), 4)
    self.assertEqual(len(self.gangster.possessions), 3)
    self.assertEqual(self.nun.possessions[-1].name, "Deputy's Revolver")

    with self.assertRaisesRegex(game.InvalidMove, "only trade items"):
      self.state.handle_give(1, 0, "Deputy", None)
    self.assertEqual(len(self.nun.possessions), 4)
    self.assertEqual(len(self.gangster.possessions), 3)


class OtherWorldTradingTest(TradingTestBase):
  def testTradeBeforeMoving(self):
    for char in self.state.characters:
      char.place = self.state.places["Dreamlands1"]
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    self.assertTrue(self.state.usables)
    self.assertIn(0, self.state.usables)
    self.assertIn("trade", self.state.usables[0])
    self.state.handle_give(1, 0, "Tommy Gun0", None)
    self.assertEqual(len(self.nun.possessions), 3)
    self.assertEqual(len(self.gangster.possessions), 1)

  def testTradeAfterMoving(self):
    self.nun.place = self.state.places["Dreamlands1"]
    self.gangster.place = self.state.places["Dreamlands2"]
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.nun.place.name, "Dreamlands2")
    self.assertTrue(self.state.event_stack)
    self.assertTrue(self.state.usables)
    self.assertIn(0, self.state.usables)
    self.assertIn("trade", self.state.usables[0])
    self.state.done_using[0] = True
    for _ in self.state.resolve_loop():
      pass
    self.assertNotEqual(self.state.turn_idx, 0)

  def testTradeBeforeReturn(self):
    self.state.places["Square"].gate = self.state.gates.popleft()
    name = self.state.places["Square"].gate.name + "2"
    self.nun.place = self.state.places[name]
    self.gangster.place = self.state.places[name]
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.GateChoice)
    self.state.handle_give(0, 1, "Cross0", None)
    self.assertEqual([pos.name for pos in self.nun.possessions], ["Bravery"])
    self.assertEqual(
      [pos.name for pos in self.gangster.possessions], ["Tommy Gun", "Marksman", "Cross"]
    )

  def testTradeBeforeReturnMultipleGates(self):
    self.state.places["Square"].gate = self.state.gates.popleft()
    self.state.places["Isle"].gate = self.state.gates.popleft()
    self.assertEqual(self.state.places["Square"].gate.name, self.state.places["Isle"].gate.name)
    name = self.state.places["Isle"].gate.name + "2"
    self.nun.place = self.state.places[name]
    self.gangster.place = self.state.places[name]
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.GateChoice)
    self.state.handle_give(0, 1, "Cross0", None)
    self.assertEqual([pos.name for pos in self.nun.possessions], ["Bravery"])
    self.assertEqual(
      [pos.name for pos in self.gangster.possessions], ["Tommy Gun", "Marksman", "Cross"]
    )

  def testTradeOnReturn(self):
    self.state.places["Square"].gate = self.state.gates.popleft()
    name = self.state.places["Square"].gate.name + "2"
    self.nun.place = self.state.places[name]
    self.gangster.place = self.state.places["Square"]
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.nun.place.name, "Square")
    self.assertTrue(self.state.usables)
    self.assertIn(0, self.state.usables)
    self.assertIn("trade", self.state.usables[0])


class InitializePlayersTest(unittest.TestCase):
  def testInitializePlayers(self):
    chars = characters.CreateCharacters(set())
    for name in chars:
      with self.subTest(char=name):
        state = eldritch.GameState()
        state.ancient_one = DummyAncient()
        state.handle_join(None, name)
        state.handle_start()
        science_clue_missing = name == "Scientist"
        self.assertEqual(state.places["Science"].clues, 1 - int(science_clue_missing))

  def testInitializeSquidFace(self):
    state = eldritch.GameState()
    state.ancient_one = ancient_ones.SquidFace()
    state.handle_join(None, "Researcher")
    state.handle_start()
    self.assertEqual(len(state.characters), 1)
    self.assertEqual(state.characters[0].max_stamina(state), 4)
    self.assertEqual(state.characters[0].max_sanity(state), 4)
    self.assertEqual(state.characters[0].stamina, 4)
    self.assertEqual(state.characters[0].sanity, 4)


class NextTurnBase(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    for name in ["Nun", "Doctor", "Archaeologist"]:
      self.state.all_characters[name] = getattr(base_characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
    self.state.test_mode = False


class NextTurnTest(NextTurnBase):
  def testTurnProgression(self):
    self.assertEqual(self.state.first_player, 0)
    self.assertEqual(self.state.turn_number, 0)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.state.event_stack.append(events.Upkeep(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass

    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "upkeep")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.Upkeep)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.state.event_stack[-1].done = True
      # Will stop at each slider input. Last one will stop at CityMovement.
      for _ in self.state.resolve_loop():
        pass

    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "movement")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.Movement)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.state.event_stack[-1].done = True
      # Will stop at each CityMovement. Last one will stop when we leave the movement phase.
      for _ in self.state.resolve_loop():
        if self.state.turn_phase != "movement":
          break

    for turn_idx in range(3):
      self.assertEqual(self.state.turn_phase, "encounter")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.EncounterPhase)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.assertEqual(len(self.state.event_stack), 1)
      self.state.event_stack[0].done = True
      # Run the resolver just enough to put the next turn on the stack.
      for _ in self.state.resolve_loop():
        if self.state.event_stack and not self.state.event_stack[0].done:
          break

    # Run the resolver through to the mythos phase. Nothing should happen in other worlds.
    for _ in self.state.resolve_loop():
      if self.state.event_stack and isinstance(self.state.event_stack[0], events.Mythos):
        break
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 0)
    self.assertIsInstance(self.state.event_stack[0], events.Mythos)
    self.state.event_stack[0].done = True

    # Run the resolver once more to get to the next turn & next player's upkeep.
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)
    self.assertEqual(self.state.turn_number, 1)

  def testLoseTurnAndDelayed(self):
    # NOTE: we don't test lost turn on the first character because it's already their turn.
    self.state.characters[1].lose_turn_until = 1
    self.state.characters[2].delayed_until = 1

    self.assertEqual(self.state.first_player, 0)
    self.assertEqual(self.state.turn_number, 0)
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.state.event_stack.append(events.Upkeep(self.state.characters[0]))
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.turn_phase, "upkeep")

    self.state.event_stack[-1].resolve(self.state, "done", None)
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "movement")

    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "encounter":
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "encounter")
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_idx == 2:
        break
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.turn_phase, "encounter")
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "mythos":
        break
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.first_player, 1)
    self.assertEqual(self.state.turn_number, 1)
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertIsNone(self.state.characters[1].lose_turn_until)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[1])

  def testLoseTurnAsFirstPlayer(self):
    self.state.characters[1].lose_turn_until = 1
    self.state.first_player = 1
    self.state.turn_phase = "encounter"
    self.assertEqual(self.state.turn_idx, 0)
    self.state.event_stack.append(events.EncounterPhase(self.state.characters[0]))
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "mythos":
        break
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)
    self.assertIsInstance(self.state.event_stack[0], events.Mythos)

    self.state.event_stack[0].done = True
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_idx, 2)
    self.assertEqual(self.state.first_player, 2)
    self.assertIsNone(self.state.characters[1].lose_turn_until)

  def testAllPlayersLoseTurns(self):
    for turn_idx in range(3):
      self.state.characters[turn_idx].lose_turn_until = 2
    self.state.turn_phase = "mythos"
    self.state.turn_idx = 0
    self.assertEqual(self.state.first_player, 0)
    self.state.event_stack.append(events.Mythos(None))
    self.state.event_stack[0].done = True

    for _ in self.state.resolve_loop():
      if self.state.turn_phase == "mythos" and self.state.turn_idx == 1:
        break
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)


class NextAwakenedTurnTestBase(NextTurnBase):
  ALIVE_COUNT = 3
  FIRST_ALIVE = 0

  def setUp(self):
    super().setUp()
    self.state.turn_phase = "upkeep"
    self.state.game_stage = "awakened"
    self.state.ancient_one.health = 1
    self.alive_count = self.ALIVE_COUNT
    self.first_alive = self.FIRST_ALIVE
    self.state.turn_idx = self.first_alive
    self.state.first_player = self.first_alive

  def testTurnProgression(self):
    self.assertEqual(self.state.first_player, self.first_alive)
    self.assertEqual(self.state.turn_idx, self.first_alive)
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.state.event_stack.append(events.Upkeep(self.state.characters[self.first_alive]))
    for _ in self.state.resolve_loop():
      pass

    for turn_idx in range(self.first_alive, self.first_alive + self.alive_count):
      self.assertEqual(self.state.turn_phase, "upkeep")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.Upkeep)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.assertFalse(self.state.usables)
      self.state.event_stack[-1].done = True
      # Will stop at each slider input. Last one will stop at Trading.
      for _ in self.state.resolve_loop():
        pass

    self.assertTrue(self.state.usables)
    # Characters who are still alive may trade.
    for turn_idx in range(3):
      if turn_idx in range(self.first_alive, self.first_alive + self.alive_count):
        self.assertIn(turn_idx, self.state.usables)
        self.assertIn("trade", self.state.usables[turn_idx])
      else:
        self.assertNotIn(turn_idx, self.state.usables)

    for turn_idx in range(self.first_alive, self.first_alive + self.alive_count):
      self.state.done_using[turn_idx] = True
    for _ in self.state.resolve_loop():
      pass

    for turn_idx in range(self.first_alive, self.first_alive + self.alive_count):
      self.assertEqual(self.state.turn_phase, "attack")
      self.assertEqual(self.state.turn_idx, turn_idx)
      self.assertIsInstance(self.state.event_stack[0], events.InvestigatorAttack)
      self.assertEqual(self.state.event_stack[0].character, self.state.characters[turn_idx])
      self.state.event_stack[-1].resolve(self.state, "done")
      # Will stop at each DiceRoll.
      for _ in self.state.resolve_loop():
        pass
      self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
      # Roll no successes so that the investigators don't win.
      with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
        self.state.event_stack[-1].resolve(self.state)
      # Will now stop at each SpendChoice.
      for _ in self.state.resolve_loop():
        pass
      self.assertIsInstance(self.state.event_stack[-1], events.SpendChoice)
      self.state.event_stack[-1].resolve(self.state, self.state.event_stack[-1].choices[1])
      # It should stop at the next player's combat choice (or stop for the ancient one's attack).
      for _ in self.state.resolve_loop():
        if self.state.turn_phase != "attack":
          break

    self.assertEqual(self.state.turn_phase, "ancient")
    self.assertEqual(self.state.turn_idx, self.first_alive)
    self.assertIsInstance(self.state.event_stack[0], events.AncientAttack)

    # Run the resolver once more to get to the next turn & next player's upkeep.
    for _ in self.state.resolve_loop():
      pass

    # Because of the way we've set things up, the next player will always be player 1.
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.first_player, 1)
    self.assertEqual(self.state.turn_number, 1)


class NextTurnAwakenedAllAliveTest(NextAwakenedTurnTestBase):
  ALIVE_COUNT = 3
  FIRST_ALIVE = 0


class NextTurnAwakenedLastPlayerDevouredTest(NextAwakenedTurnTestBase):
  ALIVE_COUNT = 2
  FIRST_ALIVE = 0

  def setUp(self):
    super().setUp()
    self.state.characters[2].gone = True


class NextTurnAwakenedOnePlayerLeftTest(NextAwakenedTurnTestBase):
  ALIVE_COUNT = 1
  FIRST_ALIVE = 1

  def setUp(self):
    super().setUp()
    self.state.characters[0].gone = True
    self.state.characters[2].gone = True


class TradingWhenAwakenedTest(NextTurnBase):
  def setUp(self):
    super().setUp()
    self.state.game_stage = "awakened"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
    self.state.turn_idx = 2
    self.state.test_mode = False
    self.state.characters[0].dollars = 10
    for char in self.state.characters:
      char.place = self.state.places["Battle"]

  def testCanTradeAtEndOfUpkeep(self):
    self.state.event_stack.append(events.Upkeep(self.state.characters[2]))
    for _ in self.state.resolve_loop():
      pass
    # Cannot trade while setting your sliders.
    with self.assertRaisesRegex(game.InvalidMove, "at this time"):
      self.state.handle_give(0, 1, "dollars", 10)
    self.state.event_stack[-1].done = True
    for _ in self.state.resolve_loop():
      pass

    # Can trade after the last player has set their sliders.
    self.state.handle_give(0, 1, "dollars", 7)
    self.assertEqual(self.state.characters[0].dollars, 3)
    self.assertEqual(self.state.characters[1].dollars, 7)
    self.assertEqual(self.state.characters[2].dollars, 0)

    # After a character says they are done trading, they can still trade until they're all done.
    self.state.done_using[1] = True
    self.state.handle_give(1, 2, "dollars", 4)
    self.assertEqual(self.state.characters[0].dollars, 3)
    self.assertEqual(self.state.characters[1].dollars, 3)
    self.assertEqual(self.state.characters[2].dollars, 4)

    self.state.done_using[0] = True
    self.state.done_using[2] = True
    for _ in self.state.resolve_loop():
      pass

    with self.assertRaisesRegex(game.InvalidMove, "at this time"):
      self.state.handle_give(1, 2, "dollars", 1)


class WinGameTest(NextTurnBase):
  def testWinBySealingGates(self):
    for place in ["Isle", "Cave", "Woods", "Square", "Science"]:
      self.state.places[place].sealed = True
    self.state.characters[0].place = self.state.places["Society"]
    self.state.places["Society"].gate = self.state.gates.popleft()
    self.state.characters[0].explored = True
    self.state.characters[0].clues = 5

    self.state.turn_phase = "encounter"
    self.state.event_stack.append(events.EncounterPhase(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.assertEqual(self.state.event_stack[-1].prompt(), "Close the gate?")
    self.state.event_stack[-1].resolve(self.state, "Close with lore")
    # Close the gate by passing a lore check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      for _ in self.state.resolve_loop():
        pass
      self.state.handle_roll(0)
      for _ in self.state.resolve_loop():
        pass
      self.state.event_stack[-1].resolve(self.state, "Pass")
      for _ in self.state.resolve_loop():
        pass

    # Spend five clue tokens to seal the gate.
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    for _ in range(5):
      self.state.event_stack[-1].spend("clues")
    for _ in self.state.resolve_loop():
      pass
    self.state.event_stack[-1].resolve(self.state, "Yes")
    for _ in self.state.resolve_loop():
      pass

    self.assertEqual(self.state.game_stage, "victory")

  def testWinByClosingAllGates(self):
    self.state.characters[1].trophies.append(self.state.gates.popleft())
    self.state.characters[2].trophies.append(self.state.gates.popleft())
    self.state.characters[0].place = self.state.places["Society"]
    self.state.places["Society"].gate = self.state.gates.popleft()
    self.state.characters[0].explored = True

    self.state.turn_phase = "encounter"
    self.state.event_stack.append(events.EncounterPhase(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.assertEqual(self.state.event_stack[-1].prompt(), "Close the gate?")
    self.state.event_stack[-1].resolve(self.state, "Close with lore")
    # Close the gate by passing a lore check.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      for _ in self.state.resolve_loop():
        pass
      self.state.handle_roll(0)
      for _ in self.state.resolve_loop():
        pass
      self.state.event_stack[-1].resolve(self.state, "Pass")
      for _ in self.state.resolve_loop():
        pass

    # Decline to seal the gate.
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.state.event_stack[-1].resolve(self.state, "No")
    for _ in self.state.resolve_loop():
      pass

    self.assertEqual(self.state.game_stage, "victory")

  def testDealFinalDamageToAncientOne(self):
    self.state.game_stage = "awakened"
    self.state.ancient_one.health = 1
    self.state.turn_phase = "attack"
    char = self.state.characters[self.state.turn_idx]
    self.state.event_stack.append(events.InvestigatorAttack(char))

    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.event_stack)
    # Choose no weapons to fight the ancient one.
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      pass
    # Roll successes on the attack roll.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.state.event_stack[-1].resolve(self.state)
    for _ in self.state.resolve_loop():
      pass
    # Don't spend any clue tokens.
    self.state.event_stack[-1].resolve(self.state, "Pass")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "victory")


class LoseGameTest(NextTurnBase):
  def testInstantDefeatFromAwakening(self):
    self.state.ancient_one = ancient_ones.ChaosGod()
    self.state.event_stack.append(events.AddDoom(count=float("inf")))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "defeat")

  def testAncientOneHasCorrectHealthWhenAwakened(self):
    self.state.event_stack.append(events.AddDoom(count=float("inf")))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.ancient_one.health, 30)

  def testLastCharacterDevoured(self):
    self.state.game_stage = "awakened"
    self.state.ancient_one.health = 1
    self.state.turn_phase = "ancient"
    char = self.state.characters[self.state.turn_idx]
    # Start with most characters already devoured.
    for character in self.state.characters:
      if character != char:
        character.gone = True
        character.place = None

    self.state.event_stack.append(events.AncientAttack(char))
    # The ancient one's attack devours the last character.

    def devour(state):  # pylint: disable=unused-argument
      return events.AncientOneAttack([events.Devoured(char)])

    with mock.patch.object(self.state.ancient_one, "attack", new=devour):
      for _ in self.state.resolve_loop():
        pass
    self.assertEqual(self.state.game_stage, "defeat")

  def testLastCharacterDevouredDuringUpkeep(self):
    self.state.game_stage = "awakened"
    self.state.ancient_one.health = 1
    self.state.turn_phase = "upkeep"
    char = self.state.characters[self.state.turn_idx]
    # Start with most characters already devoured.
    for character in self.state.characters:
      if character != char:
        character.gone = True
        character.place = None

    # One character starts with a heal spell
    char.possessions.append(items.Heal(0))
    char.sanity = 1

    self.state.event_stack.append(events.Upkeep(char))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.usables)
    self.assertIn(self.state.turn_idx, self.state.usables)
    self.assertIn("Heal0", self.state.usables[self.state.turn_idx])

    # Use the heal spell. It consumes this character's last sanity.
    self.state.event_stack.append(self.state.usables[self.state.turn_idx]["Heal0"])
    for _ in self.state.resolve_loop():
      pass
    spend_choice = self.state.event_stack[-1]
    spend_choice.spend("sanity")
    for _ in self.state.resolve_loop():
      pass
    spend_choice.resolve(self.state, "Heal0")
    for _ in self.state.resolve_loop():
      pass

    # Fail casting just so that we don't also have to choose a character.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.state.event_stack[-1].resolve(self.state)
    for _ in self.state.resolve_loop():
      pass
    # Don't spend any clue tokens.
    self.state.event_stack[-1].resolve(self.state, "Fail")
    for _ in self.state.resolve_loop():
      pass

    self.assertEqual(self.state.game_stage, "defeat")


class InsaneTest(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    for name in ["Nun", "Doctor", "Archaeologist"]:
      self.state.all_characters[name] = getattr(base_characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
    self.state.test_mode = False

  def testInsaneUpkeep(self):
    self.state.characters[0].sanity = 1
    self.state.event_stack.append(events.Upkeep(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.state.event_stack.append(events.Loss(self.state.characters[0], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.ItemLossChoice)
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[0], events.Upkeep)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[1])
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.turn_phase, "upkeep")

  def testInsaneMovement(self):
    self.state.characters[2].sanity = 1
    self.state.event_stack.append(events.Movement(self.state.characters[2]))
    self.state.turn_idx = 2
    self.state.turn_phase = "movement"
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.CityMovement)
    self.state.event_stack.append(events.Loss(self.state.characters[2], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.ItemLossChoice)
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "movement":
        break
    self.assertIsInstance(self.state.event_stack[0], events.EncounterPhase)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[0])
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "encounter")

  def testInsaneEncounter(self):
    self.state.characters[2].sanity = 1
    self.state.characters[0].place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(events.EncounterPhase(self.state.characters[2]))
    self.state.turn_idx = 2
    self.state.turn_phase = "encounter"
    self.state.characters[2].place.gate = self.state.gates.popleft()
    self.state.characters[2].explored = True
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.state.event_stack.append(events.Loss(self.state.characters[2], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.ItemLossChoice)
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "encounter":
        break
    self.assertIsInstance(self.state.event_stack[0], events.OtherWorldPhase)
    self.assertEqual(self.state.event_stack[0].character, self.state.characters[0])
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "otherworld")

  def testInsaneOtherWorld(self):
    self.state.characters[0].stamina = 1
    self.state.characters[0].place = self.state.places["Dreamlands1"]
    self.state.event_stack.append(events.OtherWorldPhase(self.state.characters[0]))
    self.state.turn_idx = 0
    self.state.turn_phase = "otherworld"
    self.state.gate_cards.append(
      GateCard("Gate29", {"red"}, {"Other": gate_encounters.Other29})
    )  # lose one stamina
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "otherworld":
        break
    self.assertIsInstance(self.state.event_stack[-1], events.CardChoice)
    self.state.event_stack[-1].resolve(self.state, "Gate29")
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.ItemLossChoice)
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      if self.state.turn_phase != "otherworld":
        break
    self.assertIsInstance(self.state.event_stack[0], events.Mythos)
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertEqual(self.state.characters[0].place.name, "Lost")

  def testInsaneMythos(self):
    self.state.characters[0].sanity = 1
    # both characters 0 and 1 may spend a clue token on the luck check from the mythos card.
    self.state.characters[0].clues = 1
    self.state.characters[1].clues = 1
    self.state.turn_idx = 0
    self.state.turn_phase = "mythos"
    self.state.mythos.append(mythos.Mythos1())
    self.state.event_stack.append(events.Mythos(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    self.assertEqual(self.state.event_stack[-1].character, self.state.characters[0])
    self.state.event_stack.append(events.Loss(self.state.characters[0], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.ItemLossChoice)
    self.state.event_stack[-1].resolve(self.state, "done")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.turn_idx, 0)
    self.assertEqual(self.state.turn_phase, "mythos")
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    self.assertEqual(self.state.event_stack[-1].character, self.state.characters[1])

  def testLoseStaminaAndHealthMeansDevoured(self):
    self.state.characters[0].sanity = 1
    self.state.characters[0].stamina = 1
    self.state.turn_idx = 0
    self.state.turn_phase = "otherworld"
    self.state.event_stack.append(
      events.Loss(self.state.characters[0], {"sanity": 1, "stamina": 1})
    )
    for _ in self.state.resolve_loop():
      if self.state.turn_idx != 0:
        break
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.turn_phase, "otherworld")
    self.assertTrue(self.state.characters[0].gone)
    self.assertFalse(self.state.characters[1].gone)

  def testInsaneAgainstAncientOne(self):
    self.state.characters[0].sanity = 1
    self.state.turn_idx = 0
    self.state.game_stage = "awakened"
    self.state.turn_phase = "attack"
    self.state.event_stack.append(events.InvestigatorAttack(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    self.state.event_stack.append(events.Loss(self.state.characters[0], {"sanity": 1}))
    for _ in self.state.resolve_loop():
      pass
    self.assertTrue(self.state.characters[0].gone)
    self.assertEqual(self.state.turn_idx, 1)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "attack")


class OpenGateCountTest(unittest.TestCase):
  def testOpenGateCount(self):
    state = eldritch.GameState()
    expected = {1: 8, 2: 8, 3: 7, 4: 7, 5: 6, 6: 6, 7: 5, 8: 5}
    for num_players, expected_gate_limit in expected.items():
      with self.subTest(num_players=num_players):
        state.characters = [None] * num_players
        self.assertEqual(state.gate_limit(), expected_gate_limit)


class AwakenTest(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    self.state.all_characters["Gangster"] = base_characters.Gangster()
    self.state.characters.append(self.state.all_characters["Gangster"])
    self.state.characters[0].place = self.state.places["House"]
    self.state.game_stage = "slumber"
    self.state.turn_number = 100
    self.state.turn_phase = "mythos"
    self.state.test_mode = False

  def testGatesOpenCausesAwakeningTest(self):
    for place in ["Square", "Isle", "Woods", "WitchHouse", "Graveyard", "Cave", "Unnamable"]:
      self.state.places[place].gate = self.state.gates.popleft()
    self.state.event_stack.append(events.OpenGate("Science"))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.turn_number, 101)

  def testAddingLastDoomTokenAwakens(self):
    self.state.ancient_one.doom = self.state.ancient_one.max_doom - 1
    self.state.event_stack.append(events.OpenGate("Science"))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.ancient_one.doom, self.state.ancient_one.max_doom)

  def testDontAwakenForOtherDoomTokens(self):
    self.state.ancient_one.doom = self.state.ancient_one.max_doom - 2
    self.state.event_stack.append(events.OpenGate("Science"))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "slumber")
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.ancient_one.doom, self.state.ancient_one.max_doom - 1)

  def testCanAwakenFromAnyPhaseWithoutGate(self):
    self.state.ancient_one.doom = self.state.ancient_one.max_doom - 1
    self.state.event_stack.append(events.AddDoom())
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.ancient_one.doom, self.state.ancient_one.max_doom)

  def testCannotOverfillDoomTrack(self):
    self.state.ancient_one.doom = self.state.ancient_one.max_doom - 1
    self.state.event_stack.append(events.AddDoom(count=2))
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")
    self.assertEqual(self.state.ancient_one.doom, self.state.ancient_one.max_doom)

  def testAwakenIfNoMonstersLeftMonsterSurge(self):
    for place in ["Square", "Isle", "Woods"]:
      self.state.places[place].gate = self.state.gates.popleft()
    self.assertEqual(len(self.state.monsters), 2)
    # Trigger a monster surge - there are three open gates, so we want to draw 3 monsters. This
    # is larger than the number in the cup (2), so the ancient one should awaken.
    self.state.event_stack.append(events.OpenGate("Square"))
    for _ in self.state.resolve_loop():
      pass
    # Since the ancient one is awakening, we should not place monsters on gates.
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")
    # We should always fill the doom track when the ancient one awakens.
    self.assertEqual(self.state.ancient_one.doom, self.state.ancient_one.max_doom)

  def testAwakenIfNoMonstersLeftInEncounter(self):
    self.state.monsters.clear()
    self.state.characters[0].place = self.state.places["Graveyard"]
    self.state.turn_phase = "encounter"
    self.state.event_stack.append(encounters.Graveyard7(self.state.characters[0]))
    for _ in self.state.resolve_loop():
      pass
    # Since the ancient one is awakening, we should not place monsters on gates.
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")

  def testAwakenIfNoMonstersLeftOnlyCountsMonstersInCup(self):
    self.state.monsters[0].place = self.state.places["Square"]
    self.state.monsters[1].place = self.state.places["Woods"]
    self.state.event_stack.append(events.OpenGate("Isle"))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")

  def testAwakenIfDoubleNormalMonsterLimit(self):
    for _ in range(6):
      self.state.monsters.append(monsters.Cultist())
      self.state.monsters[-1].idx = len(self.state.monsters) - 1
      self.state.monsters[-1].place = self.state.monster_cup
    self.state.terror = 10
    for i in range(7):
      self.state.monsters[i].place = self.state.places["Isle"]
    self.state.event_stack.append(events.OpenGate("Isle"))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")

  def testAwakenIfNoGatesLeft(self):
    self.state.gates.clear()
    self.state.event_stack.append(events.OpenGate("Isle"))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")

  def testLostInvestigatorsAreDevoured(self):
    self.state.all_characters["Doctor"] = base_characters.Doctor()
    self.state.characters.append(self.state.all_characters["Doctor"])
    self.state.characters[1].place = self.state.places["Lost"]
    self.state.event_stack.append(events.AddDoom(count=float("inf")))
    for _ in self.state.resolve_loop():
      pass
    self.assertIsInstance(self.state.event_stack[-1], events.SliderInput)
    self.assertEqual(self.state.game_stage, "awakened")
    self.assertEqual(self.state.turn_phase, "upkeep")

    self.assertEqual(self.state.characters[0].place.name, "Battle")
    self.assertTrue(self.state.characters[1].gone)


class RollDiceTest(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    for name in ["Nun", "Doctor"]:
      self.state.all_characters[name] = getattr(base_characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    for char in self.state.characters:
      char.place = self.state.places[char.home]
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
    self.state.test_mode = True

  def testGenericDiceRoll(self):
    roll = events.DiceRoll(self.state.characters[0], 1, name="Northside1", bad=[1, 2])
    self.state.event_stack.append(roll)
    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIn("roller", data["dice"])
      self.assertEqual(data["dice"]["roller"], 0)
      self.assertIn("roll", data["dice"])
      self.assertIsInstance(data["dice"]["roll"], (type(None), list))
      self.assertIn("name", data["dice"])
      self.assertEqual(data["dice"]["name"], "Northside1")
      self.assertIn("prompt", data["dice"])
      self.assertIn("rolls for [Northside1]", data["dice"]["prompt"])
      self.assertIn("bad", data["dice"])
      self.assertListEqual(data["dice"]["bad"], [1, 2])

      # TODO: figure out if we want to show the dice rolls to other players
      # other_data = self.state.for_player(1)
      # self.assertNotIn("dice", data)

    self.assertFalse(self.state.event_stack)

  def testValueDiceRoll(self):
    count = values.Calculation(self.state.characters[0], "stamina")
    roll = events.DiceRoll(self.state.characters[0], count)
    self.state.event_stack.append(roll)
    self.state.test_mode = False

    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIn("roller", data["dice"])
      self.assertEqual(data["dice"]["roller"], 0)
      self.assertIn("roll", data["dice"])
      self.assertIsInstance(data["dice"]["roll"], (type(None), list))

    # Player is about to roll the dice. They should be able to see how many dice they will roll.
    self.assertTrue(self.state.event_stack)
    self.assertIsInstance(data["dice"]["count"], int)
    self.assertFalse(data["dice"]["roll"])
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    self.state.event_stack[-1].resolve(self.state)
    self.state.test_mode = True  # Do not proceed to the next turn.

    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIsInstance(data["dice"]["count"], int)
      self.assertIn("roller", data["dice"])
      self.assertEqual(data["dice"]["roller"], 0)
      self.assertIn("roll", data["dice"])
      self.assertIsInstance(data["dice"]["roll"], (type(None), list))
    self.assertFalse(self.state.event_stack)

  def testCheckAndSpendAndReroll(self):
    self.state.test_mode = False
    self.state.characters[0].clues = 2
    self.state.characters[0].speed_sneak_slider = 1
    self.state.characters[0].possessions.append(skills.Stealth(0))
    check = events.Check(self.state.characters[0], "evade", 0, name="Land Squid")
    # Start with a basic check.
    self.state.event_stack.append(check)
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertEqual(data["dice"]["name"], "Land Squid")
      self.assertIn("roller", data["dice"])
      self.assertIn("count", data["dice"])
      self.assertIn("prompt", data["dice"])
      self.assertIn("makes a evade +0 check", data["dice"]["prompt"])
      self.assertIn("bad", data["dice"])
      self.assertIsNone(data["dice"]["bad"])
    # Stop at the first dice roll. Let the player roll the dice.
    data = self.state.for_player(0)
    self.assertEqual(data["dice"]["count"], 3)
    self.assertTrue(self.state.event_stack)  # Dice roll should be on top
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3, 5, 4])):
      self.state.event_stack[-1].resolve(self.state)

    # The next several updates should include the dice the player rolled.
    roll_started = False
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIn("roller", data["dice"])
      if data["dice"]["roll"] is not None:
        roll_started = True
      if roll_started:
        self.assertIsInstance(data["dice"]["roll"], list)
        self.assertIsInstance(data["dice"]["success"], list)
        self.assertEqual(len(data["dice"]["roll"]), len(data["dice"]["success"]))
        self.assertListEqual(data["dice"]["success"], [False, True, False])
    roll_length = len(data["dice"]["roll"])

    # The player chooses to spend one clue token.
    self.assertTrue(self.state.event_stack)  # Should have the spend event on top
    spend_choice = self.state.event_stack[-1]
    self.assertIsInstance(spend_choice, events.SpendMixin)
    spend_choice.spend("clues")
    for _ in self.state.resolve_loop():
      pass
    self.assertEqual(self.state.event_stack[-1], spend_choice)
    spend_choice.resolve(self.state, "Spend")
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIsInstance(data["dice"]["roll"], list)
    # Roll the extra die from the clue token.
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    self.state.event_stack[-1].resolve(self.state)

    # There should now be an additional die in the updates.
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIsInstance(data["dice"]["roll"], list)
    self.assertEqual(len(data["dice"]["roll"]), roll_length + 1)

    # The player decides to reroll this check.
    self.assertIn(0, self.state.usables)
    self.assertIn("Stealth0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Stealth0"])
    # The updates should go back to having no roll visible so that the player can reroll.
    reroll_started = False
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      if data["dice"]["roll"] is None:
        reroll_started = True
      if reroll_started:
        self.assertIsNone(data["dice"]["roll"])
      else:
        self.assertIsInstance(data["dice"]["roll"], list)
        self.assertEqual(len(data["dice"]["roll"]), roll_length + 1)

    # The player rolls the dice again.
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    self.state.event_stack[-1].resolve(self.state)

    # The new dice should show up in the following updates.
    roll_started = False
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertIn("roller", data["dice"])
      if data["dice"]["roll"] is not None:
        roll_started = True
      if roll_started:
        self.assertIsInstance(data["dice"]["roll"], list)

    # Done spending.
    next_spend = self.state.event_stack[-1]
    next_spend.resolve(self.state, next_spend.choices[1])
    for _ in self.state.resolve_loop():
      if not self.state.event_stack:
        break
      self.assertEqual(len(data["dice"]["roll"]), roll_length + 1)

  def testCheckAndRerollSpecific(self):
    self.state.test_mode = False
    self.state.characters[0].possessions.append(items.Bullwhip(0))
    check = events.Check(self.state.characters[0], "combat", -1, name="Cultist")
    # Start with a basic check.
    self.state.event_stack.append(check)
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertEqual(data["dice"]["name"], "Cultist")
      self.assertIn("count", data["dice"])
      self.assertIn("prompt", data["dice"])
      self.assertIn("makes a combat -1 check", data["dice"]["prompt"])
    # Stop at the first dice roll. Let the player roll the dice.
    data = self.state.for_player(0)
    self.assertEqual(data["dice"]["count"], 2)
    self.assertTrue(self.state.event_stack)  # Dice roll should be on top
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(side_effect=[3, 5])):
      self.state.event_stack[-1].resolve(self.state)

    # Skip ahead to the player choosing to spend clues or use the bullwhip.
    for _ in self.state.resolve_loop():
      pass

    self.assertIn(0, self.state.usables)
    self.assertIn("Bullwhip0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Bullwhip0"])

    # Dice should still be shown while the player is choosing which one to reroll.
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertListEqual(data["dice"]["roll"], [3, 5])

    self.assertTrue(self.state.event_stack)  # Choose a die to reroll should be on top.
    self.assertIsInstance(self.state.event_stack[-1], events.MultipleChoice)
    self.state.event_stack[-1].resolve(self.state, 3)

    # As we approach the reroll, the original roll of 3, 5 should become None, 5.
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      self.assertListEqual(data["dice"]["roll"], [None, 5])

    self.assertTrue(self.state.event_stack)  # Dice roll should be on top again.
    self.assertIsInstance(self.state.event_stack[-1], events.DiceRoll)
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=4)):
      self.state.event_stack[-1].resolve(self.state)

    # Now that we have rerolled, we should see the new value of the die.
    seen_new = False
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIn("dice", data)
      if data["dice"]["roll"][0] == 4:
        seen_new = True
      if seen_new:
        self.assertListEqual(data["dice"]["roll"], [4, 5])
    data = self.state.for_player(0)
    self.assertListEqual(data["dice"]["roll"], [4, 5])


class MapChoiceTest(unittest.TestCase):
  def setUp(self):
    self.state = eldritch.GameState()
    self.state.initialize_for_tests()
    for name in ["Nun"]:
      self.state.all_characters[name] = getattr(base_characters, name)()
      self.state.characters.append(self.state.all_characters[name])
    self.state.game_stage = "slumber"
    self.state.turn_phase = "upkeep"
    self.state.turn_number = 0
    self.state.test_mode = True

  def testReturnChoice(self):
    self.state.places["Woods"].gate = self.state.gates.popleft()
    gate_name = self.state.places["Woods"].gate.name
    self.state.places["Square"].gate = self.state.gates.popleft()
    self.assertEqual(self.state.places["Square"].gate.name, gate_name)

    self.state.characters[0].place = self.state.places[gate_name + "2"]
    self.state.event_stack.append(events.Return(self.state.characters[0], gate_name))
    for _ in self.state.resolve_loop():
      if len(self.state.event_stack) < 2:
        continue
      data = self.state.for_player(0)
      self.assertIn("choice", data)
      self.assertIsInstance(data["choice"].get("places", None), list)

    return_choice = self.state.event_stack[-1]
    return_choice.resolve(self.state, "Woods")
    # Once resolved, the choice should not show up in the UI again.
    for _ in self.state.resolve_loop():
      data = self.state.for_player(0)
      self.assertIsNone(data.get("choice", None))
    self.assertFalse(self.state.event_stack)


class PlayerTest(unittest.TestCase):
  def setUp(self):
    self.game = eldritch.EldritchGame()
    self.game.game.ancient_one = DummyAncient()

    orig_spells = items.CreateSpells

    def spells(expansions):
      orig = orig_spells(expansions)
      # Remove these two spells from the pool of random spells. Otherwise, they can interrupt
      # the normal turn flow by asking the user if they wish to cast the spell during upkeep.
      return [spell for spell in orig if spell.name not in ("Voice", "Heal")]

    patcher = mock.patch("eldritch.items.CreateSpells", new=spells)
    patcher.start()
    self.addCleanup(patcher.stop)

  def handle(self, session, data):
    res = self.game.handle(session, data)
    if res is None:
      return
    for _ in res:
      pass


class ChooseAncientOneTest(PlayerTest):
  def setUp(self):
    super().setUp()
    self.game.game.ancient_one = None

  def testChoose(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "ancient", "ancient": "Wendigo"})
    with self.assertRaisesRegex(game.InvalidMove, "Unknown"):
      self.handle("A", {"type": "ancient", "ancient": "Taser Face"})
    self.handle("A", {"type": "ancient", "ancient": "Squid Face"})
    self.assertIsInstance(self.game.game.ancient_one, ancient_ones.SquidFace)

  def testBadChoices(self):
    self.game.connect_user("A")
    self.game.connect_user("B")
    with self.assertRaisesRegex(game.InvalidMove, "host"):
      self.handle("B", {"type": "ancient", "ancient": "Wendigo"})
    with self.assertRaisesRegex(game.InvalidMove, "Unknown"):
      self.handle("A", {"type": "ancient", "name": "Wendigo"})
    self.handle("A", {"type": "ancient", "ancient": "Wendigo"})
    self.handle("A", {"type": "join", "char": "Nun"})
    self.handle("A", {"type": "start"})
    with self.assertRaisesRegex(game.InvalidMove, "already started"):
      self.handle("A", {"type": "ancient", "ancient": "Wendigo"})


class ExpansionOptionsTest(PlayerTest):
  def testInitialState(self):
    # Test that all expansions are present in the initial options list.
    self.assertSetEqual(self.game.game.EXPANSIONS, set(self.game.game.options.keys()))
    # Test that expansion characters are available initially. TODO: expansion ancient ones.
    self.assertIn("Urchin", self.game.game.all_characters)
    self.assertIn("Farmhand", self.game.game.all_characters)

    # TODO: test for items/encounters/etc

  def testChangeOptions(self):
    self.assertSetEqual(
      self.game.game.options["seaside"], {"characters", "ancient_ones", "stories"}
    )
    self.game.connect_user("A")
    self.handle(
      "A", {"type": "option", "expansion": "seaside", "option": "monsters", "enabled": True}
    )
    self.assertSetEqual(
      self.game.game.options["seaside"], {"characters", "ancient_ones", "monsters", "stories"}
    )
    self.handle(
      "A", {"type": "option", "expansion": "seaside", "option": "characters", "enabled": False}
    )
    self.assertSetEqual(self.game.game.options["seaside"], {"ancient_ones", "monsters", "stories"})
    self.handle("A", {"type": "option", "expansion": "seaside", "enabled": True})
    self.assertSetEqual(
      self.game.game.options["seaside"],
      {"characters", "ancient_ones", "monsters", "mythos", "encounters", "stories", "rules"},
    )

  def testChangeAncientOne(self):
    self.game.game.ancient_one = None
    self.game.connect_user("A")
    self.handle(
      "A", {"type": "option", "expansion": "seaside", "option": "ancient_ones", "enabled": False}
    )

  def testForcedClifftownOptions(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "option", "expansion": "clifftown", "enabled": False})
    self.assertSetEqual(self.game.game.options["clifftown"], set())
    # Turning on the rules/board means you must use the encounters too
    self.handle(
      "A", {"type": "option", "expansion": "clifftown", "option": "rules", "enabled": True}
    )
    self.assertSetEqual(self.game.game.options["clifftown"], {"rules", "encounters"})

  def testForcedHilltownOptions(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "option", "expansion": "hilltown", "enabled": False})
    self.assertSetEqual(self.game.game.options["hilltown"], set())

    # Turning on the rules/board means you must use the encounters and mythos
    self.handle(
      "A", {"type": "option", "expansion": "hilltown", "option": "rules", "enabled": True}
    )
    self.assertSetEqual(self.game.game.options["hilltown"], {"rules", "encounters", "mythos"})

    # Turning off the rules/board means you cannot use thy mythos cards
    self.handle(
      "A", {"type": "option", "expansion": "hilltown", "option": "rules", "enabled": False}
    )
    self.assertSetEqual(self.game.game.options["hilltown"], {"encounters"})

    # Turning on the mythos cards means you must use the board/rules
    self.handle(
      "A", {"type": "option", "expansion": "hilltown", "option": "mythos", "enabled": True}
    )
    self.assertSetEqual(self.game.game.options["hilltown"], {"rules", "encounters", "mythos"})

    # Turning off the encounters means you cannot use the board/rules/mythos
    self.handle(
      "A", {"type": "option", "expansion": "hilltown", "option": "encounters", "enabled": False}
    )
    self.assertSetEqual(self.game.game.options["hilltown"], set())

  def testChangingOptionsRemovesCharacters(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "option", "expansion": "clifftown", "enabled": False})
    self.assertNotIn("Urchin", self.game.game.all_characters)

  def testCannotInvalidateExistingCharacters(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Urchin"})
    self.assertIn("Urchin", self.game.game.pending_chars)

    with self.assertRaisesRegex(game.InvalidMove, "before disabling"):
      self.handle("A", {"type": "option", "expansion": "clifftown", "enabled": False})
    self.assertIn("Urchin", self.game.game.all_characters)
    self.assertIn("Urchin", self.game.game.pending_chars)


class PlayerJoinTest(PlayerTest):
  def testJoinJSON(self):
    self.game.connect_user("session")
    data = self.game.for_player("session")
    self.assertIsNone(json.loads(data)["player_idx"])
    self.assertIsNone(json.loads(data)["pending_name"])

    self.handle("session", {"type": "join", "char": "Nun"})
    data = self.game.for_player("session")
    self.assertIsNone(json.loads(data)["player_idx"])
    self.assertEqual(json.loads(data)["pending_name"], "Nun")

    self.handle("session", {"type": "start"})
    data = self.game.for_player("session")
    self.assertEqual(json.loads(data)["player_idx"], 0)
    self.assertIsNone(json.loads(data)["pending_name"])

  def testCannotStartWithoutPlayers(self):
    self.game.connect_user("A")
    with self.assertRaisesRegex(game.InvalidMove, "At least one player"):
      self.handle("A", {"type": "start"})

  def testCannotReuseCharacter(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.assertEqual(len(self.game.game.characters), 0)
    self.game.connect_user("B")

    # Cannot reuse a pending character.
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("B", {"type": "join", "char": "Nun"})

    self.handle("A", {"type": "start", "char": "Nun"})
    self.assertEqual(len(self.game.game.characters), 1)

    # Cannot reuse a character already playing.
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("B", {"type": "join", "char": "Nun"})

  def testCanSwitchCharacter(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.assertEqual(self.game.game.pending_chars, {"Nun": None})
    self.handle("A", {"type": "join", "char": "Doctor"})
    self.assertEqual(self.game.game.pending_chars, {"Doctor": None})

  def testClearPendingCharactersOnDisconnect(self):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.assertIn("A", self.game.pending_sessions)
    self.game.connect_user("B")
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("B", {"type": "join", "char": "Nun"})
    self.assertNotIn("B", self.game.pending_sessions)

    self.game.disconnect_user("A")
    self.assertNotIn("A", self.game.pending_sessions)
    self.handle("B", {"type": "join", "char": "Nun"})
    self.assertIn("B", self.game.pending_sessions)

  @mock.patch.object(mythos, "CreateMythos", return_value=[PauseMythos(), PauseMythos()])
  def testJoinMidGame(self, _):
    self.game.connect_user("A")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.handle("A", {"type": "start"})
    self.handle("A", {"type": "set_slider", "name": "done"})
    self.handle("A", {"type": "choice", "choice": "PauseMythos"})
    self.assertEqual(len(self.game.game.characters), 1)
    self.assertEqual(self.game.game.characters[0].name, "Nun")
    self.assertEqual(self.game.game.characters[0].place.name, "Church")

    self.assertEqual(self.game.game.game_stage, "slumber")
    self.assertEqual(self.game.game.turn_phase, "upkeep")

    self.game.connect_user("B")
    self.handle("B", {"type": "join", "char": "Doctor"})
    self.assertEqual(len(self.game.game.characters), 1)  # Should not be in the game yet.
    self.assertEqual(self.game.player_sessions, {"A": 0})
    self.handle("A", {"type": "set_slider", "name": "done"})

    # Move to the streets so that there is no encounter.
    self.handle("A", {"type": "choice", "choice": "Southside"})
    self.handle("A", {"type": "choice", "choice": "done"})

    # Should now be in the mythos phase. No new characters yet.
    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertEqual(len(self.game.game.characters), 1)

    self.game.connect_user("C")
    self.handle("C", {"type": "join", "char": "Gangster"})
    self.assertEqual(len(self.game.game.characters), 1)

    self.handle("A", {"type": "choice", "choice": "PauseMythos"})

    # Validate that new characters get a chance to set their sliders before upkeep.
    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertTrue(self.game.game.event_stack)
    self.assertIsInstance(self.game.game.event_stack[-1], events.InitialSliders)

    self.handle("C", {"type": "set_slider", "name": "done"})
    self.handle("B", {"type": "set_slider", "name": "done"})

    # Now that they've set their sliders, the next upkeep phase can begin.
    self.assertEqual(self.game.game.turn_phase, "upkeep")
    self.assertEqual(len(self.game.game.characters), 3)
    self.assertEqual(self.game.game.characters[1].name, "Doctor")
    self.assertEqual(self.game.game.characters[2].name, "Gangster")
    # Now that new players have joined, they should enter the first player rotation.
    self.assertEqual(self.game.game.first_player, 1)
    self.assertEqual(self.game.game.turn_idx, 1)

    # Make sure the new characters get their starting equipment and are placed on the board.
    self.assertEqual(self.game.game.characters[1].place.name, "Hospital")
    self.assertEqual(self.game.game.characters[2].place.name, "House")

    self.assertIn("Physician", {pos.name for pos in self.game.game.characters[1].possessions})
    self.assertIn("Tommy Gun", {pos.name for pos in self.game.game.characters[2].possessions})

    # It is now the doctor's upkeep. They should be able to spend focus to move their sliders.
    self.assertTrue(self.game.game.event_stack)
    self.assertIsInstance(self.game.game.event_stack[-1], events.SliderInput)
    self.assertEqual(self.game.game.event_stack[-1].character, self.game.game.characters[1])
    self.assertFalse(self.game.game.event_stack[-1].free)


class DevouredPlayerJoinTest(PlayerTest):
  def setUp(self):
    super().setUp()
    self.game.connect_user("A")
    self.game.connect_user("B")
    self.handle("A", {"type": "join", "char": "Nun"})
    self.handle("B", {"type": "join", "char": "Doctor"})

  def startDevoured(self):
    with mock.patch.object(mythos, "CreateMythos", return_value=[DevourFirstPlayer(), NoMythos()]):
      with mock.patch.object(eldritch.random, "shuffle"):
        self.handle("A", {"type": "start"})
    self.handle("A", {"type": "set_slider", "name": "done"})
    with self.assertRaisesRegex(game.InvalidMove, "must choose new"):
      self.handle("B", {"type": "set_slider", "name": "done"})

  def startNormal(self):
    with mock.patch.object(mythos, "CreateMythos", return_value=[PauseMythos(), PauseMythos()]):
      self.handle("A", {"type": "start"})
    self.handle("B", {"type": "set_slider", "name": "done"})
    self.handle("A", {"type": "set_slider", "name": "done"})
    self.handle("A", {"type": "choice", "choice": "PauseMythos"})

  def testDevouredCharacterRejoin(self):
    self.startDevoured()
    self.assertEqual(self.game.game.characters[0].name, "Nun")
    self.assertTrue(self.game.game.characters[0].gone)
    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertEqual(self.game.game.turn_number, -1)
    self.handle("A", {"type": "join", "char": "Gangster"})

    # Have to set sliders for the new character that joined.
    self.handle("A", {"type": "set_slider", "name": "done"})

    self.assertEqual(self.game.game.turn_phase, "upkeep")
    self.assertEqual(self.game.game.turn_number, 0)
    self.assertEqual(self.game.game.characters[0].name, "Gangster")
    self.assertTrue(self.game.game.all_characters["Nun"].gone)

  def testInvalidNewCharacterChoice(self):
    self.startDevoured()
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("A", {"type": "join", "char": "Doctor"})
    with self.assertRaisesRegex(game.InvalidMove, "been devoured"):
      self.handle("A", {"type": "join", "char": "Nun"})
    with self.assertRaisesRegex(game.InvalidMove, "cannot choose"):
      self.handle("B", {"type": "join", "char": "Gangster"})

    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertEqual(self.game.game.turn_number, -1)
    self.assertFalse(self.game.game.event_stack)
    self.handle("A", {"type": "join", "char": "Gangster"})

  def testOtherPlayersJoinWhileDevoured(self):
    self.startDevoured()
    self.game.connect_user("C")
    self.handle("C", {"type": "join", "char": "Gangster"})
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("A", {"type": "join", "char": "Gangster"})
    self.handle("C", {"type": "join", "char": "Student"})
    self.handle("A", {"type": "join", "char": "Gangster"})

    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertEqual(self.game.game.turn_number, -1)
    self.assertTrue(self.game.game.event_stack)
    self.assertEqual(len(self.game.game.characters), 3)
    self.assertEqual(
      [char.name for char in self.game.game.characters], ["Gangster", "Doctor", "Student"]
    )

    self.handle("A", {"type": "set_slider", "name": "done"})
    self.handle("C", {"type": "set_slider", "name": "done"})

    self.assertEqual(self.game.game.turn_phase, "upkeep")
    self.assertEqual(self.game.game.turn_number, 0)

  def testOtherPlayersCannotChooseDevoured(self):
    self.startNormal()
    self.handle("A", {"type": "set_slider", "name": "done"})
    self.handle("B", {"type": "set_slider", "name": "done"})
    self.game.game.event_stack.append(events.Devoured(self.game.game.characters[0]))
    for _ in self.game.game.resolve_loop():
      pass
    self.handle("B", {"type": "choice", "choice": "Uptown"})
    self.handle("B", {"type": "choice", "choice": "done"})
    self.assertEqual(self.game.game.turn_phase, "mythos")
    self.assertEqual(self.game.game.turn_number, 0)
    self.handle("A", {"type": "join", "char": "Gangster"})
    self.game.connect_user("C")
    with self.assertRaisesRegex(game.InvalidMove, "been devoured"):
      self.handle("C", {"type": "join", "char": "Nun"})
    with self.assertRaisesRegex(game.InvalidMove, "already taken"):
      self.handle("C", {"type": "join", "char": "Gangster"})
    self.handle("C", {"type": "join", "char": "Scientist"})

  def testDevouredCharacterCanBeFirstPlayer(self):
    self.startNormal()
    self.game.game.event_stack.append(events.Devoured(self.game.game.characters[0]))
    for _ in self.game.game.resolve_loop():
      pass
    # First player is devoured, their upkeep ended.
    self.assertEqual(self.game.game.turn_phase, "upkeep")
    self.assertEqual(self.game.game.turn_idx, 1)
    self.assertEqual(self.game.game.event_stack[-1].character, self.game.game.characters[1])
    self.handle("B", {"type": "set_slider", "name": "done"})
    # First character also does not get a movement phase (or encounter).
    self.handle("B", {"type": "choice", "choice": "Uptown"})
    self.handle("B", {"type": "choice", "choice": "done"})
    self.assertEqual(self.game.game.turn_phase, "mythos")
    # Devoured players can still be first player during mythos.
    self.assertEqual(self.game.game.turn_idx, 0)
    self.game.handle("A", {"type": "choice", "choice": "NoMythos"})


if __name__ == "__main__":
  unittest.main()
