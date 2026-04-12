from unittest import mock

from eldritch.events import CombatChoice
from eldritch.test_events import EventTest
from eldritch.abilities import hilltown
from eldritch import events
from eldritch.encounters.location import base as encounters
from eldritch import characters, items
from eldritch.monsters.core import Monster
from eldritch.mythos import base as mythos


class EntertainerTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.extend(
      [
        hilltown.WitchBlood(),
        hilltown.ThirdEye(),
        # Tank: So what do you need, besides a miracle?
        # Neo: Guns. Lots of guns.
        items.TommyGun(0),
        items.Revolver38(0),
        items.Axe(0),
        items.Wither(0),
        items.DreadCurse(0),
        items.BindMonster(0),
      ]
    )

  def testWitchBlood(self):
    pass
    # TODO: Test second use after passing story
    pass

  def setUpCombat(self) -> tuple[Monster, events.CombatChoice]:
    monster: Monster = self.state.monsters[0]
    monster.place = self.char.place
    self.state.event_stack.append(events.Combat(self.char, monster))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
      fight_or_flee.resolve(self.state, "Fight")
      return monster, self.resolve_to_choice(events.CombatChoice)

  def test2W1S(self):
    monster, choose_weapons = self.setUpCombat()
    choose_weapons.resolve(self.state, "Tommy Gun0")

    # Cast the spell.
    self.assertIn("Wither0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(events.CardSpendChoice)
    cast.resolve(self.state, "Wither0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(events.CombatChoice)
      choose_weapons.resolve(self.state, "done")
      self.resolve_until_done()

  def test1W2S(self):
    monster, choose_weapons = self.setUpCombat()
    choose_weapons.resolve(self.state, ".38 Revolver0")

    # Cast the spell.
    self.assertIn("Dread Curse0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Dread Curse0"])
    cast = self.resolve_to_choice(events.CardSpendChoice)
    self.spend("sanity", 2, cast)
    cast.resolve(self.state, "Dread Curse0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(events.CombatChoice)
      choose_weapons.resolve(self.state, "done")
      self.resolve_until_done()

  def test2W2S(self):
    monster, choose_weapons = self.setUpCombat()

  def test2S2W(self):
    monster, choose_weapons = self.setUpCombat()

  def test3S(self):
    monster, choose_weapons = self.setUpCombat()

  def testAxeAndSpell(self):
    monster, choose_weapons = self.setUpCombat()
    choose_weapons.resolve(self.state, "Axe0")

    # Cast the spell.
    self.assertIn("Wither0", self.state.usables[0])
    self.state.event_stack.append(self.state.usables[0]["Wither0"])
    cast = self.resolve_to_choice(events.CardSpendChoice)
    cast.resolve(self.state, "Wither0")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)):
      choose_weapons = self.resolve_to_choice(events.CombatChoice)
      choose_weapons.resolve(self.state, "done")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as rand:
      self.resolve_until_done()
    self.assertEqual(
      rand.call_count,
      self.char.fight(self.state) + 3 + 3 + monster.difficulty("combat", self.state, self.char),
    )


class ExpeditionLeaderTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.append(hilltown.Leadership())
    self.other = characters.base.Nun()
    self.state.characters.append(self.other)

  def testSelfLoss(self):
    self.assertEqual(self.char.stamina, self.char.max_stamina(self.state))
    self.state.event_stack.append(events.Loss(self.char, {"stamina": 2, "sanity": 0}))
    self.resolve_to_usable(0, "Leadership")
    self.use_handle(0, "Leadership", resolve_to_spend=False)
    self.resolve_until_done()
    self.assertEqual(self.char.stamina, self.char.max_stamina(self.state) - 1)

  def testSanityOnly(self):
    self.assertEqual(self.other.sanity, self.other.max_sanity(self.state))
    self.state.event_stack.append(events.Loss(self.other, {"sanity": 2}))
    self.resolve_to_usable(0, "Leadership")
    self.use_handle(0, "Leadership", resolve_to_spend=False)
    self.resolve_until_done()
    self.assertEqual(self.other.sanity, self.other.max_sanity(self.state) - 1)

  def testStaminaOnly(self):
    self.assertEqual(self.other.stamina, self.other.max_stamina(self.state))
    self.state.event_stack.append(events.Loss(self.other, {"stamina": 2}))
    self.resolve_to_usable(0, "Leadership")
    self.use_handle(0, "Leadership", resolve_to_spend=False)
    self.resolve_until_done()
    self.assertEqual(self.other.stamina, self.other.max_stamina(self.state) - 1)

  def testBothOptions(self):
    self.assertEqual(self.other.sanity, self.other.max_sanity(self.state))
    self.assertEqual(self.other.stamina, self.other.max_stamina(self.state))
    self.state.event_stack.append(events.Loss(self.other, {"sanity": 1, "stamina": 1}))
    self.resolve_to_usable(0, "Leadership")
    self.use_handle(0, "Leadership", resolve_to_spend=False)
    choice = self.resolve_to_choice(events.MultipleChoice)
    self.assertListEqual(choice.choices, ["Sanity", "Stamina"])
    choice.resolve(self.state, "Sanity")
    self.resolve_until_done()
    self.assertEqual(self.other.sanity, self.other.max_sanity(self.state))
    self.assertEqual(self.other.stamina, self.other.max_stamina(self.state) - 1)

  def testLossPreventionConflict(self):
    self.other = characters.base.Professor()
    self.state.characters.append(self.other)
    self.assertEqual(self.other.sanity, self.other.max_sanity(self.state))
    self.assertEqual(self.other.stamina, self.other.max_stamina(self.state))
    loss = events.Loss(self.other, {"stamina": 1, "sanity": 1})
    self.state.event_stack.append(loss)
    self.resolve_to_usable(0, "Leadership")
    self.use_handle(0, "Leadership", resolve_to_spend=False)
    # No choice needed, since the Professor handles the Sanity loss
    self.resolve_until_done()
    self.assertEqual(self.other.sanity, self.other.max_sanity(self.state))
    self.assertEqual(self.other.stamina, self.other.max_stamina(self.state))


class PhychicTest(EventTest):
  def setUp(self):
    super().setUp()
    self.char.possessions.extend([hilltown.Precognition()])
    self.state.mythos.extend([mythos.Mythos2(), mythos.Mythos3(), mythos.Mythos1()])
    self.state.turn_phase = "mythos"

  def testNoCluesNoChoice(self):
    self.state.event_stack.append(events.Mythos(None))
    # with self.assertRaises(Exception):
    self.resolve_to_usable(0, "Precognition")

  def testHasCluesChooseNo(self):
    self.char.clues = 2
    self.state.event_stack.append(events.Mythos(None))
    self.resolve_to_usable(0, "Precognition")
    self.state.done_using[0] = True
    self.resolve_until_done()
    self.assertIn("Mythos2", [glob.name for glob in self.state.globals() if hasattr(glob, "name")])

  def testHasCluesChooseYes(self):
    self.char.clues = 2
    self.state.event_stack.append(events.Mythos(None))
    self.resolve_to_usable(0, "Precognition")
    choice = self.use_handle(0, "Precognition", resolve_to_spend=True)
    self.spend("clues", 2, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
    gnames = [glob.name for glob in self.state.globals() if hasattr(glob, "name")]
    self.assertNotIn("Mythos2", gnames)
    self.assertIn("Mythos3", gnames)

  def testShop7(self):
    self.state.turn_phase = "encounter"
    self.char.place = self.state.places["Shop"]
    self.state.event_stack.append(encounters.Shop7(self.char))
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=3)):
      self.resolve_until_done()
    # Should not trigger the ability
    self.assertEqual(self.char.place.name, "Woods")
    # In theory, there would be a woods event, but I think the state isn't set up for it.

  def testRumor59(self):
    m59 = mythos.Mythos59()
    m59.failed = True
    self.char.clues = 2
    self.state.other_globals.append(m59)
    self.state.event_stack.append(events.Mythos(None))
    self.resolve_to_usable(0, "Precognition")
    self.state.done_using[0] = True
    self.resolve_to_usable(0, "Precognition")
    self.use_handle(0, "Precognition")
    choice = self.resolve_to_choice(events.SpendChoice)
    self.spend("clues", 2, choice)
    choice.resolve(self.state, "Yes")
    self.resolve_until_done()
