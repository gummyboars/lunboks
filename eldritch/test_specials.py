from unittest import mock
from eldritch.test_events import EventTest
from eldritch import assets
from eldritch import events


def mock_randint(return_value=None, side_effect=None):
  return mock.patch.object(
      events.random, "randint",
      new=mock.MagicMock(return_value=return_value, side_effect=side_effect)
  )


class CurseBlessTest(EventTest):
  def setUp(self):
    super().setUp()
    self.advance_turn(0, "encounter")
    self.resolve_until_done()
    self.dummy_possession = assets.SelfDiscardingCard("Fake Special", 0)
    self.char.possessions.append(self.dummy_possession)

  def doBlessingTest(self, bless_int):
    self.resolve_until_done()
    self.assertEqual(self.char.bless_curse, bless_int)
    self.assertEqual(
        len([p for p in self.char.possessions if isinstance(p, assets.BlessingOrCurse)]),
        bless_int
    )
    with mock_randint(return_value=4):
      roll = events.DiceRoll(self.char, 1)
      self.state.event_stack.append(roll)
      self.resolve_until_done()
      self.assertEqual(roll.successes, bless_int)

    # Ensure that any discarded Blessings/Curses will get a first-round pass when they're re-drawn
    for card in self.state.specials:
      if isinstance(card, assets.SelfDiscardingCard):
        self.assertEqual(card.tokens["must_roll"], 0)


class BlessingTest(CurseBlessTest):
  def testRollForBlessing(self):
    self.doBlessingTest(0)
    self.state.event_stack.append(events.Bless(self.char))
    self.resolve_until_done()
    blessing = next(p for p in self.char.possessions if isinstance(p, assets.BlessingOrCurse))
    self.assertFalse(blessing.tokens["must_roll"])
    self.doBlessingTest(1)

    with mock_randint(return_value=1):
      # Advance past Upkeep, and roll a 1 if we roll (which we shouldn't)
      self.advance_turn(1, "encounter")
      self.assertTrue(blessing.tokens["must_roll"])
    self.doBlessingTest(1)

    with mock_randint(side_effect=[6, 1]):
      # Dummy now has both a FakeSpecial from the CurseBlessTest parent and a blessing,
      # Keep the FakeSpecial, lose the Blessing
      self.advance_turn(2, "encounter")
      self.resolve_until_done()
    self.doBlessingTest(1)
    self.assertTrue(blessing.tokens["must_roll"])

    with mock_randint(side_effect=[1, 6]):
      self.advance_turn(3, "encounter")
      self.resolve_until_done()
    self.doBlessingTest(0)

  def testDoubleBlessed(self):
    self.state.event_stack.append(events.Bless(self.char))
    self.resolve_until_done()
    self.state.event_stack.append(events.AddToken(self.char.possessions[0], "must_roll"))
    self.resolve_until_done()

    bless = events.Bless(self.char)
    self.assertFalse(bless.is_resolved())
    self.state.event_stack.append(bless)
    self.resolve_until_done()

    self.assertTrue(bless.is_resolved())
    self.doBlessingTest(1)
    blessing = next(p for p in self.char.possessions if isinstance(p, assets.BlessingOrCurse))
    self.assertFalse(blessing.tokens["must_roll"])

    with mock_randint(return_value=1):
      self.advance_turn(1, "movement")

  def testCursedWhileBlessed(self):
    self.state.event_stack.append(events.Bless(self.char))
    self.resolve_until_done()

    curse = events.Curse(self.char)
    self.assertFalse(curse.is_resolved())

    self.state.event_stack.append(curse)
    self.resolve_until_done()

    self.assertTrue(curse.is_resolved())
    self.assertEqual(self.char.bless_curse, 0)
    self.assertListEqual(self.char.possessions, [self.dummy_possession])
