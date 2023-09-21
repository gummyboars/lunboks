from unittest import mock

from eldritch.test_events import EventTest, InvalidMove
from eldritch.expansions.seaside import abilities
from eldritch.expansions.seaside import characters as seaside_characters
from eldritch import assets
from eldritch import characters
from eldritch import events
from eldritch.items import spells


class TestSecretaryAbilities(EventTest):
  def doSynergyTest(self):
    self.char.possessions.append(abilities.Synergy())
    spell = spells.Spell("Dummy", 0, {}, 0, 0, 0)
    self.char.possessions.append(spell)

    self.char.lore_luck_slider = 0
    self.assertEqual(self.char.lore(self.state), self.char.base_lore()+1)
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

    with self.assertRaisesRegex(InvalidMove, "enough focus"):
      sliders.resolve(self.state, "fight_sneak", 3)
      sliders.resolve(self.state, "lore_will", 3)
      sliders.resolve(self.state, "speed_luck", 3)
    sliders.resolve(self.state, "done", None)
    self.assertEqual(self.char.fight_sneak_slider, 3)
    self.assertEqual(self.char.lore_will_slider, 3)
    self.assertEqual(self.char.speed_luck_slider, 0)
