from unittest import mock

from eldritch.test_events import EventTest, InvalidMove
from eldritch.expansions.seaside import abilities
from eldritch.expansions.seaside import characters as seaside_characters
from eldritch import assets
from eldritch import characters
from eldritch import events
from eldritch import monsters
from eldritch.items import spells


class TestFarmhandAbility(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(abilities.ThickSkulled())

  def testCombatWithHorror(self):
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.fight(self.state), 4)
    self.assertEqual(self.char.will(self.state), 1)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    zombie = monsters.Zombie()
    combat = events.Combat(self.char, zombie)
    self.state.event_stack.append(combat)

    # The horror check normally happens here
    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    combat = next(
      event for event in reversed(self.state.event_stack) if isinstance(event, events.Combat)
    )
    self.assertIsNone(combat.horror)
    self.assertEqual(self.char.sanity, 5)

    combat_round = combat.combat
    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(events.CombatChoice)
    self.choose_items(choose_weapons, [])

    # Fail the combat check. After this, we check that there is a horror check.
    # They are guaranteed to fail because they have only 1 will.
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      next_fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)

    self.assertIsNotNone(combat.horror)
    self.assertTrue(combat_round.is_resolved())
    self.assertFalse(combat_round.defeated)
    self.assertIsNotNone(combat_round.damage)
    self.assertTrue(combat_round.damage.is_resolved())
    self.assertEqual(len(self.char.trophies), 0)
    self.assertFalse(combat.is_resolved())
    self.assertEqual(self.char.stamina, 3)
    self.assertEqual(self.char.sanity, 4)  # Assert there wasn't a second horror check/loss.

    self.assertTrue(combat.horror.is_resolved())

    combat_round = combat.combat
    next_fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(events.CombatChoice)
    self.choose_items(choose_weapons, [])
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      self.resolve_until_done()

    self.assertTrue(combat_round.is_resolved())
    self.assertTrue(combat_round.defeated)
    self.assertIsNone(combat_round.damage)
    self.assertTrue(combat.is_resolved())

  def testSpecialFailCombat(self):
    self.assertEqual(self.char.place.name, "Diner")
    self.char.place = self.state.places["Northside"]
    # Two gates - one to the Abyss, and one to Pluto. The Abyss gate is closer than the Pluto gate.
    self.state.places["Isle"].gate = next(gate for gate in self.state.gates if gate.name == "Abyss")
    self.state.places["Woods"].gate = next(gat for gat in self.state.gates if gat.name == "Pluto")
    self.char.fight_will_slider = 3
    self.assertEqual(self.char.fight(self.state), 4)
    self.assertEqual(self.char.will(self.state), 1)
    self.assertEqual(self.char.stamina, 5)
    self.assertEqual(self.char.sanity, 5)
    monster = monsters.DreamFlier()
    combat = events.Combat(self.char, monster)
    self.state.event_stack.append(combat)

    # The horror check normally happens here
    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    combat = next(
      event for event in reversed(self.state.event_stack) if isinstance(event, events.Combat)
    )
    self.assertIsNone(combat.horror)
    self.assertEqual(self.char.sanity, 5)

    fight_or_flee.resolve(self.state, "Fight")
    choose_weapons = self.resolve_to_choice(events.CombatChoice)
    self.choose_items(choose_weapons, [])

    # Fail the combat check, go through the gate
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()

    # Too dumb to realize what happened, no horror check
    self.assertIsNone(combat.horror)
    self.assertEqual(self.char.place.name, "Abyss1")


class TestSecretaryAbilities(EventTest):
  def doSynergyTest(self):
    self.char.possessions.append(abilities.Synergy())
    spell = spells.Spell("Dummy", 0, {}, 0, 0, 0)
    self.char.possessions.append(spell)

    self.char.lore_luck_slider = 0
    self.assertEqual(self.char.lore(self.state), self.char.base_lore() + 1)
    self.assertEqual(self.char.base_lore(), 1)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.state.event_stack.append(events.CastSpell(self.char, spell))
      choice = self.resolve_to_choice(events.MultipleChoice)
      choice.resolve(self.state, "Dummy")
      self.resolve_until_done()
      self.assertEqual(rand.call_count, self.char.base_lore() + 1)

    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)) as rand:
      self.state.event_stack.append(events.Check(self.char, "combat", 0))
      self.resolve_until_done()
      self.assertEqual(rand.call_count, self.char.base_fight() + 1)

  def testSynergyAlly(self):
    self.char.possessions.append(assets.Dog())
    self.doSynergyTest()

  def testSynergyInvestigator(self):
    nun = characters.Nun()
    nun.place = self.char.place
    self.state.characters.append(nun)
    self.doSynergyTest()

  def testNoSynergy(self):
    with self.assertRaises(AssertionError):
      self.doSynergyTest()

  def testTeamPlayer(self):
    self.char.place = self.state.places["Uptown"]
    self.char.possessions.append(abilities.TeamPlayer())
    self.state.specials.append(abilities.TeamPlayerBonus(0))
    self.state.turn_phase = "upkeep"
    nun = characters.Nun()
    nun.place = self.char.place
    self.state.all_characters["Nun"] = nun
    self.state.characters.append(nun)

    sliders = events.SliderInput(self.char)
    self.state.event_stack.append(sliders)
    team = self.resolve_to_choice(events.MultipleChoice)
    self.assertListEqual(team.choices, ["None", "Nun"])
    team.resolve(self.state, "Nun")
    sliders.resolve(self.state, "done", None)

    self.advance_turn(0, "movement")
    nun.place = self.state.places["Downtown"]

    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      combat = events.Check(nun, "combat", 0)
      self.state.event_stack.append(combat)
      self.resolve_until_done()
      self.assertEqual(rand.call_count, nun.base_fight() + 1)


class TestSpyAbilities(EventTest):
  def testFocusAndBreakingLimits(self):
    self.char = seaside_characters.Spy()
    self.char.place = self.state.places["Newspaper"]
    self.state.characters = [self.char]
    self.char.possessions.extend([abilities.AbnormalFocus(), abilities.BreakingTheLimits()])
    self.advance_turn(1, "upkeep")
    sliders = self.resolve_to_choice(events.SliderInput)
    self.assertLessEqual(sum(self.char.sliders().values()), self.char.slider_focus_available())
    self.assertEqual(self.char.slider_focus_available(), 5)
    usable = self.resolve_to_usable(0, "Breaking the Limits")
    self.state.event_stack.append(self.state.usables[0]["Breaking the Limits"])
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.spend("sanity", 1, choice)
    self.spend("stamina", 1, choice)
    choice.resolve(self.state, "Yes")
    usable = self.resolve_to_usable(0, "Breaking the Limits")
    self.assertEqual(self.char.slider_focus_available(), 7)
    self.assertTrue(self.state.usables)
    self.state.event_stack.append(usable)
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.spend("sanity", 1, choice)
    choice.resolve(self.state, "Yes")
    sliders = self.resolve_to_choice(events.SliderInput)
    self.assertEqual(self.char.slider_focus_available(), 8)
    self.assertFalse(self.state.usables)

    sliders.resolve(self.state, "fight_sneak", 3)
    sliders.resolve(self.state, "lore_will", 3)
    with self.assertRaisesRegex(InvalidMove, "enough focus"):
      sliders.resolve(self.state, "speed_luck", 3)
    sliders.resolve(self.state, "done", None)
    self.assertEqual(self.char.fight_sneak_slider, 3)
    self.assertEqual(self.char.lore_will_slider, 3)
    self.assertEqual(self.char.speed_luck_slider, 0)
