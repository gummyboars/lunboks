from unittest import mock

from eldritch.test_events import EventTest
from eldritch.expansions.seaside import abilities
from eldritch import assets
from eldritch import characters
from eldritch import events
from eldritch.items import spells


class TestSecretaryAbilities(EventTest):
  def testSynergy(self):
    self.char.possessions.append(abilities.Synergy())
    self.char.possessions.append(assets.Dog())
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
    may_use = self.resolve_to_usable(0, "Team Player")
    self.state.event_stack.append(may_use)

    team = self.resolve_to_choice(events.MultipleChoice)
    self.assertListEqual(team.choices, ["None", "Nun"])
    team.resolve(self.state, "Nun")

    self.advance_turn(0, "movement")
    nun.place = self.state.places["Downtown"]

    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.state.event_stack.append(events.Check(nun, "combat", 0))
      self.resolve_until_done()
      self.assertEqual(rand.call_count, nun.base_fight() + 1)
