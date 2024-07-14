from unittest import mock

from eldritch.test_events import EventTest
from eldritch.expansions.clifftown import abilities
from eldritch import characters
from eldritch import events
from eldritch import monsters
from eldritch.items import unique


class TestUrchinAbilities(EventTest):
  def setUp(self):
    super().setUp()
    self.elder_sign = unique.ElderSign(0)
    self.minor = abilities.Minor()
    self.char.possessions.extend(
        [
            abilities.Streetwise(), abilities.BlessedIsTheChild(),
            self.minor, self.elder_sign,
        ]
    )

  def testEvadeInStreets(self):
    self.char.place = self.state.places["Northside"]
    cultist = monsters.Cultist()
    combat = events.Combat(self.char, cultist)
    self.state.event_stack.append(combat)
    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=1)) as dice:
      self.resolve_until_done()
      self.assertEqual(dice.call_count, 0)

  def testEvadeInLocation(self):
    self.char.speed_sneak_slider = 0
    cultist = monsters.Cultist()
    combat = events.Combat(self.char, cultist)
    self.state.event_stack.append(combat)
    fight_or_flee = self.resolve_to_choice(events.FightOrEvadeChoice)
    fight_or_flee.resolve(self.state, "Flee")
    with mock.patch.object(events.random, "randint", new=mock.MagicMock(return_value=5)) as dice:
      self.resolve_until_done()
      self.assertEqual(dice.call_count, 1)

  def testCannotCurse(self):
    curse = events.Curse(self.char)
    self.state.event_stack.append(curse)
    self.resolve_until_done()

    self.assertEqual(self.char.bless_curse, 0)
    self.assertTrue(curse.cancelled)

    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.elder_sign]))
    self.resolve_until_done()

    curse = events.Curse(self.char)
    self.state.event_stack.append(curse)
    self.resolve_until_done()

    self.assertEqual(self.char.bless_curse, -1)
    self.assertFalse(curse.cancelled)

  def testCannotBeArrested(self):
    arrested = events.Arrested(self.char)
    self.state.event_stack.append(arrested)
    self.resolve_until_done()

    self.assertIsNone(self.char.arrested_until)
    self.assertTrue(arrested.cancelled)

    self.state.event_stack.append(events.DiscardSpecific(self.char, [self.elder_sign]))
    self.resolve_until_done()

    arrested = events.Arrested(self.char)
    self.state.event_stack.append(arrested)
    self.resolve_until_done()

    self.assertIsNotNone(self.char.arrested_until)
    self.assertFalse(arrested.cancelled)

  def testMinorCredit(self):
    self.char.place = self.state.places["Bank"]
    self.advance_turn(0, "encounter")
    self.resolve_until_done()

    self.char.possessions.remove(self.minor)
    self.advance_turn(1, "encounter")
    self.resolve_until_done()
